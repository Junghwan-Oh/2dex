# DN Bot Minimum Spread Filter Fix Plan

## Context

### Original Problem
The recently implemented fee economics fix (commit aca55d2) is TOO STRICT - the bot cannot trade at all.

### Current Implementation (BROKEN) - Lines 931-937
```python
# CRITICAL: Mode-aware breakeven calculation
# POST_ONLY: 2 bps x 4 legs = 8 bps breakeven
# IOC: 5 bps x 4 legs = 20 bps breakeven
if self.use_post_only:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 8)  # Maker fees
else:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 20)  # Taker fees - CRITICAL FIX
```

### Test Results
- Current market spread: 0.4-0.9 bps
- POST_ONLY minimum: 8 bps -> NO TRADES
- IOC minimum: 20 bps -> NO TRADES
- Bot log: "SPREAD FILTER SKIP: Spread below threshold"

### Root Cause Analysis
1. The previous plan assumed: entry spread must cover entry fees
2. Reality: market spreads (0.4-0.9 bps) are far below fees (8-20 bps)
3. The misunderstanding: Profit comes from SPREAD GAINS + FEE REBATES, not just entry spread
4. Profitability depends on price movement AFTER entry, not just the initial spread

## VERIFIED Fee Economics (From Code Analysis)

### Actual Fee Structure (Lines 390-392)
```python
FEE_RATE = Decimal("0.0002") if self.use_post_only else Decimal("0.0005")
fee_bps = float(FEE_RATE * 10000)
# POST_ONLY = 2 bps, IOC = 5 bps
```

### Fee Application in PNL Calculation (Lines 1159-1173)
```python
# Entry fees ALREADY PAID: 10 bps (IOC) or 4 bps (POST_ONLY)
# Exit fees REMAINING: 10 bps (IOC) or 4 bps (POST_ONLY)
remaining_exit_fees_bps = 10 if not self.use_post_only else 4

BASE_PROFIT = 15
MIN_NET_PROFIT = 5

profit_target = BASE_PROFIT + remaining_exit_fees_bps  # 25 for IOC, 19 for POST_ONLY
quick_exit = MIN_NET_PROFIT + remaining_exit_fees_bps  # 15 for IOC, 9 for POST_ONLY
```

**CRITICAL FINDING**: The code comments say "10 bps (IOC) or 4 bps (POST_ONLY)" which means:
- IOC: 5 bps per leg x 2 legs = 10 bps (already proven by FEE_RATE at line 390)
- POST_ONLY: 2 bps per leg x 2 legs = 4 bps (already proven by FEE_RATE at line 390)

Total for 4 legs (2 entries + 2 exits):
- POST_ONLY: 4 bps entry + 4 bps exit = 8 bps total
- IOC: 10 bps entry + 10 bps exit = 20 bps total

### PNL Calculation Logic (Lines 1240-1289)
```python
def _calculate_current_pnl(self) -> tuple[Decimal, Decimal, dict]:
    # Calculate ETH PNL (Long: exit - entry)
    eth_pnl = (eth_exit_price - eth_entry_price) * eth_entry_qty

    # Calculate SOL PNL (Short: entry - exit)
    sol_pnl = (sol_entry_price - sol_exit_price) * sol_entry_qty

    # Total PNL without fees
    pnl_no_fee = eth_pnl + sol_pnl

    # Total fees paid
    total_fees = self.current_cycle_pnl.get("total_fees", Decimal("0"))

    # PNL with fees (before funding correction)
    pnl_with_fee = pnl_no_fee - total_fees
```

**VERIFIED**: PNL comes from price movements AFTER entry (exit_price - entry_price), not from entry spread.

## Work Objectives

### Core Objective
Fix the minimum spread filter to allow the bot to trade in current market conditions (0.4-0.9 bps spreads) while maintaining profitability.

### Deliverables
1. Reverted minimum spread logic to allow trading at current market spreads
2. Updated profitability guardrails to focus on exit conditions instead
3. Risk mitigation: monitoring and rollback strategy
4. Documentation explaining the verified economics model

### Definition of Done
- Bot can enter positions when spreads are 0.4-0.9 bps
- POST_ONLY mode is the default (as user suggested)
- Profitability is maintained through exit strategy, not entry filter
- CSV logging captures the economics data
- Risk mitigation is in place

## Must Have / Must NOT Have

### Must Have
- Allow trading at current market spreads (0.4-0.9 bps)
- Use POST_ONLY as default mode (lower fees: 2 bps vs 5 bps)
- Maintain profitability through exit conditions
- Log spread data for analysis
- Risk mitigation: monitor cumulative PNL, stop if loss exceeds threshold

### Must NOT Have
- Minimum spread thresholds that block all trades
- IOC as default (unless explicitly requested)
- Assumption that entry spread must cover all fees

## Economics Analysis (VERIFIED)

### How Profit is Actually Calculated (Lines 1240-1289)

```python
# Entry phase: pay fees
total_fees = eth_entry_fee + sol_entry_fee  # 4 bps POST_ONLY, 10 bps IOC

# Exit phase: pay more fees, calculate PNL
eth_pnl = (eth_exit_price - eth_entry_price) * eth_entry_qty  # Can be positive or negative
sol_pnl = (sol_entry_price - sol_exit_price) * sol_entry_qty  # Can be positive or negative
pnl_no_fee = eth_pnl + sol_pnl  # Profit from price movements
pnl_with_fee = pnl_no_fee - total_fees  # Final profit after all fees
```

**Key Insight**: Profit comes from `exit_price - entry_price`, NOT from `entry_ask - entry_bid`.

### Real Breakeven Calculation (POST_ONLY)

For a $100 position:
- Entry fees: 2 bps x 2 legs = 4 bps ($4)
- Exit fees: 2 bps x 2 legs = 4 bps ($4)
- Total fees: 8 bps ($8)

To break even, you need:
- Price movement favorably: ETH up, SOL down
- OR spread convergence
- OR combination

With a 0.5 bps entry spread, you only need:
- Additional 7.5 bps of favorable price movement or spread convergence
- This is VERY achievable in volatile markets

### Why 1 bps is the Right Minimum

**Decision: Use 1 bps as min_spread_bps**

**Reasoning**:
1. Current market: 0.4-0.9 bps (spreads are consistently tight)
2. 0 bps would allow data errors or crossed quotes to pass
3. 1 bps filters data errors while allowing 100% of valid trades
4. Entry spread does NOT determine profitability - exit conditions do
5. Exit thresholds (lines 1163-1167) already account for remaining fees

**Expected Outcomes**:
- At 0.5 bps entry spread: 100% trade acceptance (no filter skips)
- At 0.9 bps entry spread: 100% trade acceptance
- Bot can now enter positions and profit from post-entry movements

## Proposed Solution

### Implementation: Set min_spread_bps to 1

```python
# In __init__ parameter (Line 57)
min_spread_bps: int = 1,  # Changed from 6 to 1 (sanity check only)

# In _check_spread_profitability (Lines 931-937)
# OLD:
if self.use_post_only:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 8)  # Maker fees
else:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 20)  # Taker fees

# NEW:
# Minimum spread is a sanity check, not a breakeven requirement
# Profit comes from spread convergence and price movement AFTER entry
# Mode affects fees, but entry spread doesn't need to cover them
MIN_SPREAD_BPS = self.min_spread_bps  # Configurable, default 1 bps
```

## Task Flow and Dependencies

```
Phase 1: Core Fix (CRITICAL)
  |_ Task 1.1: Change min_spread_bps default from 6 to 1 (Line 57)
  |_ Task 1.2: Remove mode-specific minimum spread overrides (Lines 931-937)
  |_ Task 1.3: Update documentation explaining economics model
  |_ Task 1.4: Add risk mitigation monitoring

Phase 2: Testing
  |_ Task 2.1: Run bot with --size 10 --iter 1 to verify trades execute
  |_ Task 2.2: Verify CSV logs show spread data
  |_ Task 2.3: Confirm no "SPREAD FILTER SKIP" messages

Phase 3: Monitoring
  |_ Task 3.1: Monitor first 5 cycles for profitability
  |_ Task 3.2: Implement rollback if unprofitable
```

## Detailed TODOs

### Task 1.1: Change min_spread_bps Default
**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: Line 57

**BEFORE**:
```python
min_spread_bps: int = 6,  # Minimum spread in bps to enter trade (configurable)
```

**AFTER**:
```python
min_spread_bps: int = 1,  # Minimum spread in bps - sanity check only, profit comes from post-entry movements
```

**Acceptance Criteria**: Default min_spread_bps is 1, not 6

### Task 1.2: Remove Mode-Specific Overrides
**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: Lines 931-937

**BEFORE**:
```python
# CRITICAL: Mode-aware breakeven calculation
# POST_ONLY: 2 bps x 4 legs = 8 bps breakeven
# IOC: 5 bps x 4 legs = 20 bps breakeven
if self.use_post_only:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 8)  # Maker fees
else:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 20)  # Taker fees - CRITICAL FIX
```

**AFTER**:
```python
# Minimum spread is a sanity check, not a breakeven requirement
# Verified from _calculate_current_pnl() (lines 1240-1289): profit comes from
# (exit_price - entry_price) movements AFTER entry, NOT from entry spread
#
# Mode affects fees via FEE_RATE (line 390):
# - POST_ONLY: 2 bps per leg = 8 bps total for 4 legs
# - IOC: 5 bps per leg = 20 bps total for 4 legs
#
# But profitability is determined by exit conditions (lines 1163-1167), not entry spread
MIN_SPREAD_BPS = self.min_spread_bps  # Configurable, default 1 bps
```

**Acceptance Criteria**: No mode-specific minimum spread logic, code references verified economics

### Task 1.3: Update Docstring
**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: Lines 920-930 (docstring of _check_spread_profitability)

**BEFORE**:
```python
"""
Check if spread is profitable given current market conditions.

Returns:
    is_profitable: bool - True if spread is >= minimum threshold
    info: dict with:
        - eth_spread_bps: ETH spread in bps
        - sol_spread_bps: SOL spread in bps
        - min_spread_bps: Minimum required spread (configurable, default 6)
        - max_spread_bps: Maximum of ETH/SOL spreads in bps
        - reason: Skip reason if not profitable
"""
```

**AFTER**:
```python
"""
Check if spread is acceptable for entry.

IMPORTANT: This is a sanity check, NOT a profitability filter.
Verified from _calculate_current_pnl() (lines 1240-1289):
- Profit = (exit_price - entry_price) * qty - fees
- Profit comes from POST-ENTRY price movements, NOT entry spread
- Exit thresholds (lines 1163-1167) enforce profitability

Minimum spread prevents:
- Data errors (0 or negative spreads from bad quotes)
- Obviously poor entry conditions

Returns:
    is_profitable: bool - True if spread >= minimum threshold
    info: dict with:
        - eth_spread_bps: ETH spread in bps
        - sol_spread_bps: SOL spread in bps
        - min_spread_bps: Minimum required spread (configurable, default 1)
        - max_spread_bps: Maximum of ETH/SOL spreads in bps
        - reason: Skip reason if not profitable
"""
```

**Acceptance Criteria**: Docstring references actual PNL calculation code

### Task 1.4: Add Risk Mitigation Monitoring
**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: Add new method after _calculate_current_pnl (around line 1320)

**ADD**:
```python
def _check_cumulative_pnl_health(self) -> tuple[bool, str]:
    """
    Check if cumulative PNL indicates strategy issues.

    Risk mitigation for relaxed entry filter:
    - If first 3 cycles unprofitable, may need to adjust min_spread_bps
    - Stop if cumulative loss exceeds threshold

    Returns:
        (is_healthy, message): tuple of health status and explanation
    """
    total_cycles = self.daily_pnl_summary.get("total_cycles", 0)
    total_pnl = self.daily_pnl_summary.get("total_pnl_with_fee", Decimal("0"))
    losing_cycles = self.daily_pnl_summary.get("losing_cycles", 0)

    # Risk threshold: $50 maximum cumulative loss
    MAX_CUMULATIVE_LOSS = Decimal("50")

    # Check cumulative loss
    if total_pnl < -MAX_CUMULATIVE_LOSS:
        return False, f"Cumulative loss ${-total_pnl:.2f} exceeds threshold ${MAX_CUMULATIVE_LOSS}"

    # Check if first 3 cycles are all unprofitable
    if 3 <= total_cycles <= 5 and losing_cycles == total_cycles:
        return False, f"First {total_cycles} cycles all unprofitable - consider increasing min_spread_bps to 2-3"

    # Check win rate after 10 cycles
    if total_cycles >= 10:
        win_rate = (total_cycles - losing_cycles) / total_cycles
        if win_rate < 0.3:
            return False, f"Win rate {win_rate*100:.0f}% below 30% after {total_cycles} cycles"

    return True, "Cumulative PNL within acceptable range"
```

**Call this method**: Add to main loop after each cycle completion (around line 1390)

**Acceptance Criteria**: Risk checks prevent unlimited losses from relaxed filter

### Task 1.5: Update CLI Help Text
**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: Line 2381

**BEFORE**:
```python
min_spread_bps=getattr(args, 'min_spread_bps', 6),  # Min spread filter (default 6 bps)
```

**AFTER**:
```python
min_spread_bps=getattr(args, 'min_spread_bps', 1),  # Min spread sanity check - profit from post-entry movements (default 1 bps)
```

**Also update argparse help** (around line 2357):
```python
parser.add_argument('--min-spread-bps', type=int, default=1,
    help='Minimum spread in bps - sanity check only, NOT breakeven. Profit comes from post-entry spread convergence and price movement. (default: 1)')
```

**Acceptance Criteria**: Help text explains real purpose of min_spread_bps

### Task 2.1: Quick Smoke Test
**Command**:
```bash
cd /Users/botfarmer/2dex/hedge && python DN_pair_eth_sol_nado.py --size 10 --iter 1
```

**Acceptance Criteria**:
- Bot executes without "SPREAD FILTER SKIP" errors
- At least one trade cycle completes
- CSV log is created with data
- Entry spread ~0.5-0.9 bps is accepted

### Task 2.2: Verify Spread Data Logging
**Check**: CSV file contains columns:
- `entry_spread_bps` (or max_spread_bps)
- `pnl_with_fee`
- `total_fees`

**Acceptance Criteria**: Spread data is captured for analysis

### Task 3.1: Monitor First 5 Cycles
**Run**: `python DN_pair_eth_sol_nado.py --size 100 --iter 5`

**Track**:
```bash
# Check logs for spread convergence data
grep "SPREAD FILTER" dn_bot_*.log  # Should be empty or very few
grep "profit_target\|quick_exit" dn_bot_*.log  # Should show exit thresholds
grep "total_fees\|pnl_with_fee" dn_bot_*.log  # Should track economics
```

**Expected PNL Outcomes**:
- For $100 position, entry at 0.5 bps, exit at 8 bps spread gain:
  - Gross profit: 8 bps = $8
  - Total fees: 8 bps = $8 (POST_ONLY)
  - Net profit: ~$0 (breakeven)
- For exit at 15 bps spread gain:
  - Gross profit: 15 bps = $15
  - Total fees: 8 bps = $8
  - Net profit: $7 (7% return)

**Acceptance Criteria**:
- All cycles enter positions (no filter skips)
- CSV shows spread data and PNL breakdown
- Net profit trend is positive or neutral

### Task 3.2: Implement Rollback Strategy
**If unprofitable after 5 cycles**:

**Option 1**: Increase min_spread_bps to 2-3
```bash
python DN_pair_eth_sol_nado.py --size 100 --min-spread-bps 2
```

**Option 2**: Revert changes
```bash
git revert HEAD  # Revert the fix
```

**Option 3**: Adjust exit thresholds (lines 1163-1167)
```python
# Increase profit_target from 15+remaining_fees to 20+remaining_fees
```

**Acceptance Criteria**: Clear rollback path documented

## Commit Strategy

```bash
# Commit message
git commit -m "fix(dn-bot): Relax minimum spread filter - verify economics model

Problem: Fee economics fix (aca55d2) made min spread too strict (8/20 bps),
resulting in NO TRADES in current market conditions (0.4-0.9 bps spreads).

Root Cause Verification:
- Read _calculate_current_pnl() lines 1240-1289
- Profit = (exit_price - entry_price) * qty - fees
- Profit comes from POST-ENTRY movements, NOT entry spread
- Entry spread is just the starting point, not the profit source

Fee Structure Verification (lines 390-392):
- FEE_RATE = 0.0002 (POST_ONLY: 2 bps) or 0.0005 (IOC: 5 bps)
- Total for 4 legs: POST_ONLY = 8 bps, IOC = 20 bps
- Confirmed by exit threshold calculations (lines 1159-1167)

Changes:
- Change min_spread_bps default from 6 to 1 bps
- Remove mode-specific minimum spread overrides (8/20 bps)
- Add _check_cumulative_pnl_health() for risk mitigation
- Update docstrings to reference verified PNL calculation

Economics Reality:
- Entry spread 0.5 bps: profit comes from post-entry movements
- Exit at 8 bps gain: $8 gross - $8 fees = $0 net (breakeven)
- Exit at 15 bps gain: $15 gross - $8 fees = $7 net (7% return)
- Tight entry spreads don't prevent profitable exits

Risk Mitigation:
- Stop if cumulative loss exceeds $50
- Alert if first 3 cycles all unprofitable
- Clear rollback strategy documented

Fixes: Bot now trades at current market spreads (0.4-0.9 bps)
Refs: User correctly identified filter was too strict and POST_ONLY should be used"
```

## Success Criteria (QUANTIFIED)

### Functional Success
- Bot enters positions when spreads are 0.4-0.9 bps: 100% trade acceptance
- No "SPREAD FILTER SKIP" errors in normal market conditions
- CSV logs show complete trade data (entry_spread_bps, pnl_with_fee, total_fees)

### Economic Success (Quantified)
- **For $100 position with POST_ONLY**:
  - Entry at 0.5 bps spread, exit at 8 bps gain: Expected PNL ~$0 (breakeven)
  - Entry at 0.5 bps spread, exit at 15 bps gain: Expected PNL ~$7 (7% return)
  - Entry at 0.9 bps spread, exit at 8 bps gain: Expected PNL ~$3 (3% return)

- **Minimum acceptable metrics**:
  - >$2 profit per cycle average (2% return on $100)
  - <5 cycles with cumulative loss >$20 before intervention
  - >30% win rate after 10 cycles

- **Maximum acceptable loss**:
  - <$5 per cycle (5% of $100 position)
  - <$50 cumulative before forced stop

### Code Quality
- Code is simpler (removed mode-specific logic)
- Documentation references actual PNL calculation code (lines 1240-1289)
- Default values match current market reality
- Risk mitigation prevents unlimited losses

## Risk Mitigation Strategy

### Risk 1: Increased Trade Frequency
- **Risk**: More trades = more fee cost
- **Mitigation**: Track cumulative PNL, stop at $50 loss threshold
- **Monitor**: `grep "total_fees\|total_pnl_with_fee" logs`

### Risk 2: Poor Entry Conditions
- **Risk**: 1 bps filter may allow bad entries
- **Mitigation**: Exit thresholds (lines 1163-1167) enforce profitability
- **Monitor**: `grep "profit_target\|quick_exit\|stop_loss" logs`

### Risk 3: Spread Doesn't Converge
- **Risk**: Enter at tight spread, spread widens further
- **Mitigation**: Stop-loss at 30 bps (line 1168) limits downside
- **Monitor**: Track spread convergence in CSV

### Rollback Triggers
1. **Immediate rollback**: Cumulative loss >$50
2. **Adjust filter**: First 3 cycles all unprofitable
3. **Revert commit**: Win rate <30% after 10 cycles

### Rollback Procedure
```bash
# Option 1: Increase min_spread_bps
python DN_pair_eth_sol_nado.py --min-spread-bps 3

# Option 2: Revert commit
git revert HEAD

# Option 3: Adjust exit thresholds
# Edit lines 1163-1167: increase profit_target
```

## Implementation Order

1. **Do Task 1.1** - Change default min_spread_bps from 6 to 1 (Line 57)
2. **Do Task 1.2** - Remove mode-specific overrides (Lines 931-937)
3. **Do Task 1.3** - Update docstring (Lines 920-930)
4. **Do Task 1.4** - Add risk mitigation monitoring (New method)
5. **Do Task 1.5** - Update CLI help text (Line 2357, 2381)
6. **Do Task 2.1** - Run smoke test to verify trades execute
7. **Do Task 2.2** - Verify CSV logging
8. **Do Task 3.1** - Monitor first 5 cycles with quantified metrics
9. **Do Task 3.2** - Execute rollback if needed

## Notes

### Code Verification Summary
- **Fee structure**: Lines 390-392 confirm 2 bps (POST_ONLY) and 5 bps (IOC)
- **Exit thresholds**: Lines 1159-1173 confirm 4 bps (POST_ONLY) and 10 bps (IOC) remaining
- **PNL calculation**: Lines 1240-1289 confirm profit from (exit_price - entry_price)
- **Total fees**: 8 bps POST_ONLY, 20 bps IOC (verified across multiple sections)

### Key Decisions
1. **1 bps minimum**: Filters data errors while allowing all valid trades
2. **POST_ONLY default**: Lower fees (8 bps vs 20 bps) as user suggested
3. **Risk mitigation**: $50 cumulative loss threshold, 3-cycle check
4. **Exit-focused profitability**: Entry spread doesn't need to cover fees

### Expected Outcomes
- 100% trade acceptance at current spreads (0.4-0.9 bps)
- Breakeven at 8 bps post-entry spread gain
- Profitable at 15+ bps post-entry spread gain
- Risk mitigation prevents unlimited losses
