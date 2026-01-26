# Agent Failure Post-Mortem
**Date**: 2026-01-26
**Severity**: CRITICAL (Catastrophic potential)
**Status**: Documented & Prevented

---

## Executive Summary

Executor agents made **unauthorized changes** that flipped `buy`/`sell` directions in GRVT LIMIT order logic. This was NOT in the task requirements and would have caused **catastrophic position doubling** instead of delta-neutral hedging.

**Impact if deployed**: Primary LONG + Hedge LONG (instead of SHORT) = 2x delta exposure = catastrophic losses in volatile markets

**Detection**: User identified the issue during testing ("백팩만 롱 포지션, grvt=노 포지션" - only Backpack has long position, GRVT has no position)

**Root Cause**: Agent misunderstood POST_ONLY order mechanics and incorrectly thought "opposite side" meant flipping trade direction.

---

## What Happened

### Original Task Requirements

User requested TWO optimizations:
1. **Task 1**: "Remove Primary 10s timeout - speed up execution"
2. **Task 2**: "Change GRVT to LIMIT orders for maker fees"

**Neither task mentioned changing buy/sell directions.**

### What the Agents Did

```python
# AGENT'S BROKEN CODE (would have caused catastrophic losses):
if side == "buy":
    order_price = best_ask + self.hedge_tick_size
    post_only_side = "sell"  # ❌ WRONG! Should be "buy"
else:
    order_price = best_bid - self.hedge_tick_size
    post_only_side = "buy"   # ❌ WRONG! Should be "sell"
```

### Why This Was Catastrophic

**Correct Logic** (what we wanted):
- Primary: BUY @ $2925 (LONG)
- Hedge: SELL @ $2929 (SHORT)
- **Net Delta**: 0 (delta-neutral) ✅

**Agent's Broken Logic** (what would have happened):
- Primary: BUY @ $2925 (LONG)
- Hedge: BUY @ $2929 (LONG) ← WRONG! Should be SELL
- **Net Delta**: +0.02 ETH (DOUBLE LONG exposure) ❌

**Result**: Instead of hedging, the bot would have **doubled the position**. In a volatile market, this could have caused massive losses.

---

## Root Cause Analysis

### 1. Agent Misunderstanding of POST_ONLY Mechanics

**Agent's Flawed Reasoning**:
> "POST_ONLY orders are posted on opposite side"

**What Agent Thought**:
- "Opposite side" = flip the trade direction
- buy → sell, sell → buy

**Reality**:
- "Opposite side" refers to **order book side**, not trade direction
- POST_ONLY buy → places limit order on **bid** side (waiting to buy)
- POST_ONLY sell → places limit order on **ask** side (waiting to sell)
- The **trade direction** (buy/sell) should NEVER flip

### 2. Missing Agent Prompt Guardrails

The executor agent prompts did NOT include:
- ❌ "NEVER change buy/sell directions unless explicitly requested"
- ❌ "If implementing LIMIT orders, preserve the original trade direction"
- ❌ "Verify hedge direction: Primary LONG → Hedge SHORT, Primary SHORT → Hedge LONG"

### 3. No Pre-Flight Validation

The agents' code was NOT validated for:
- ❌ Hedge direction correctness
- ❌ Delta neutrality preservation
- ❌ Position doubling scenarios

### 4. User Testing Caught the Bug

**User Observation**: "백팩만 롱 포지션, grvt=노 포지션"
- Only Backpack had long position
- GRVT had no position (order failed due to incorrect side)

**This observation prevented catastrophic deployment.**

---

## Why the Previous Commit Was Working

**Commit**: `0b17cea` (BUILD_UNWIND_FIX_REPORT.md)

This commit had:
- ✅ Correct hedge direction logic
- ✅ GRVT using MARKET orders (no LIMIT order changes)
- ✅ All 4 BUILD/UNWIND scenarios handled correctly
- ✅ Scenario 2 emergency unwind working

**The agents' changes would have broken ALL of this.**

---

## Prevention Strategies

### 1. Agent Prompt Guardrails (HIGH PRIORITY)

**Add to executor agent prompts**:
```python
"""
CRITICAL TRADING SYSTEM CONSTRAINTS:
1. NEVER change buy/sell directions unless explicitly requested
2. For hedge orders: Preserve the opposite direction logic
   - Primary BUY (LONG) → Hedge must SELL (SHORT)
   - Primary SELL (SHORT) → Hedge must BUY (LONG)
3. If implementing new order types (LIMIT, POST_ONLY, etc.):
   - Only modify price/execution logic
   - NEVER modify trade direction
4. Post-validation: Verify net delta = 0 after any hedge order changes
"""
```

### 2. Pre-Flight Validation Tests

**Add to test suite**:
```python
def test_hedge_direction_correctness():
    """Verify hedge direction is ALWAYS opposite of primary"""
    # Primary BUY → Hedge must be SELL
    # Primary SELL → Hedge must be BUY
    assert hedge_direction != primary_direction
```

### 3. Manual Code Review Checklist

**Required for ANY agent changes**:
- [ ] Buy/sell directions unchanged (unless explicitly requested)
- [ ] Hedge direction is opposite of primary
- [ ] Net delta remains neutral
- [ ] No position doubling scenarios
- [ ] Emergency unwind logic preserved

### 4. Integration Tests

**Add to test suite**:
```python
async def test_delta_neutrality():
    """Verify bot maintains delta-neutral position"""
    bot = DNHedgeBot(...)
    await bot.build_position()

    # Verify positions
    assert bot.primary_position == +0.01  # LONG
    assert bot.hedge_position == -0.01    # SHORT
    assert bot.primary_position + bot.hedge_position == 0  # Net neutral
```

### 5. Git Diff Verification

**Before committing agent changes**:
```bash
# Check for unauthorized buy/sell changes
git diff | grep -E "^\+.*side\s*=\s*['\"] (buy|sell)"

# If ANY matches → MANUAL REVIEW REQUIRED
```

---

## Lessons Learned

### 1. Agents Don't Understand Domain Context

The agent didn't understand:
- **Delta-neutral strategy**: Primary and hedge must be OPPOSITE directions
- **Hedge mechanics**: The purpose is to offset risk, not add more exposure
- **Trading fundamentals**: LONG + SHORT = neutral, LONG + LONG = doubled risk

**Solution**: Add domain knowledge to agent prompts explicitly.

### 2. "Opposite Side" Ambiguity

The phrase "POST_ONLY orders are posted on opposite side" is **ambiguous**:
- Could mean "opposite side of order book" (correct)
- Could mean "opposite trade direction" (WRONG)

**Solution**: Use precise language:
- "POST_ONLY buy orders place limit bids on the bid side"
- "POST_ONLY sell orders place limit asks on the ask side"

### 3. User Testing is Critical

**User's observation caught the bug**: "백팩만 롱 포지션, grvt=노 포지션"

**Without this observation**:
- Agent code would have been committed
- Would have deployed to production
- Would have caused catastrophic losses

**Solution**: Always test with small sizes (0.01 ETH) before full deployment.

### 4. Working Code > Optimized Code

**Commit 0b17cea was working correctly**:
- All scenarios handled
- Emergency unwind working
- GRVT cold start workaround functional

**Agent's "optimization" would have broken everything**:
- Buy/sell directions flipped
- No delta neutrality
- Catastrophic risk

**Solution**: If agents make changes outside task requirements → REVERT immediately.

---

## Correct Approach for Future LIMIT Order Implementation

If implementing LIMIT orders for maker fees:

### Step 1: Preserve Trade Direction

```python
# CORRECT: Trade direction NEVER changes
if side == "buy":   # We want to BUY
    order_price = best_ask - tick_size  # Slightly below ask
    order_side = "buy"  # ✅ CORRECT: Still buying!
else:  # side == "sell"
    order_price = best_bid + tick_size  # Slightly above bid
    order_side = "sell"  # ✅ CORRECT: Still selling!
```

### Step 2: Use POST_ONLY Flag

```python
# Place order with POST_ONLY flag (maker order)
order_result = await exchange.place_limit_order(
    contract_id=contract_id,
    quantity=quantity,
    price=order_price,
    side=order_side,  # CORRECT: Original direction preserved
    post_only=True    # This flag makes it a maker order
)
```

### Step 3: Verify Delta Neutrality

```python
# After order fills, verify:
primary_pos = self.primary_position  # +0.01 (LONG)
hedge_pos = self.hedge_position      # -0.01 (SHORT)
net_delta = primary_pos + hedge_pos   # 0 (neutral)

assert abs(net_delta) < Decimal("0.001"), "Delta not neutral!"
```

---

## Timeline

| Time | Event | Status |
|------|-------|--------|
| 2026-01-26 07:30 | Executor agents make unauthorized changes | ❌ BROKEN |
| 2026-01-26 07:45 | User identifies issue during testing | ✅ DETECTED |
| 2026-01-26 08:00 | Code reverted to clean state | ✅ FIXED |
| 2026-01-26 08:30 | RALPLAN session started for post-mortem + 5s timeout plan | ✅ IN PROGRESS |
| 2026-01-26 08:45 | Critic approved plan (2 iterations, 10 issues fixed) | ✅ APPROVED |

---

## Recommendations

### Immediate Actions

1. ✅ **REVERT**: Done - code reverted to commit 0b17cea
2. ✅ **DOCUMENT**: Done - this post-mortem
3. **COMMIT**: Commit post-mortem to git for permanent record
4. **IMPLEMENT**: Apply approved 5s timeout plan (NOT full removal)

### Long-Term Actions

1. **Add agent prompt guardrails** (see Prevention Strategy #1)
2. **Create integration test suite** (see Prevention Strategy #4)
3. **Manual review checklist** for all agent changes
4. **Git diff verification** before commits

---

## Conclusion

**This was a near-miss catastrophic event.**

The agent's changes would have caused:
- Position doubling (2x delta exposure)
- Massive losses in volatile markets
- Complete loss of delta-neutral protection

**User testing caught the bug before deployment.**

**Key takeaway**: For trading systems, **working code > optimized code**. Any agent changes outside explicit task requirements must be reverted immediately.

---

**Status**: ✅ Documented, lessons learned, prevention strategies defined.
**Next**: Implement 5s timeout optimization per approved plan (with all safeguards in place).
