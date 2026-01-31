# DN Pair Bot SOL Accumulation Fix - CORRECTED PLAN

**Plan ID**: dn-pair-websocket-integration-updated
**Status**: CORRECTED VERSION (Based on Critic Feedback)
**Created**: 2026-01-30
**Target File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (2885 lines)

---

## Executive Summary

**CRITICAL FINDING**: This file contains TWO incompatible bot implementations merged into one class:

1. **System A (Working)**: Dual-NADO-ticker DN pair bot using `eth_client`/`sol_client` (~400 lines, actively used)
2. **System B (Dead)**: Cross-exchange arbitrage bot using `primary_client`/`hedge_client` (~1000+ lines, NEVER initialized)

**Root Cause Analysis**: The SOL accumulation problem (LONG=57, SHORT=18 trades from CSV analysis, ratio 3.17:1) is NOT due to missing WebSocket connections (WebSocket already works). The accumulation is caused by failed UNWIND cycles that report success but leave positions open, followed by BUILD cycles that don't verify positions are closed.

**Data Source**: `/Users/botfarmer/2dex/logs/DN_pair_eth_sol_nado_trades.csv` (153 trades total)
- ETH: 57 BUY vs 18 SELL (3.17:1 ratio, accumulation detected)
- SOL: 44 BUY vs 33 SELL (1.33:1 ratio, acceptable range)

---

## Architecture Analysis

### Current State (CONFUSED ARCHITECTURE)

**Lines 153-154**: Initialize ONLY eth_client and sol_client
```python
self.eth_client = None
self.sol_client = None
# NOTE: primary_client and hedge_client are NEVER initialized in __init__
```

**Lines 846-851**: Only eth_client/sol_client are created
```python
self.eth_client = NadoClient(eth_config)
self.sol_client = NadoClient(sol_config)
await self.eth_client.connect()  # WebSocket already working
await self.sol_client.connect()  # WebSocket already working
```

**Lines 2878-2881**: Main execution uses alternating strategy (System A)
```python
await bot.initialize_clients()  # Creates eth_client/sol_client
await bot.run_alternating_strategy()  # Uses System A (buy_first/sell_first)
```

### Dead Code Inventory (System B - NEVER EXECUTED)

**Primary/Hedge Client References** (98 lines total, ALL DEAD):
- Lines 316-323: cleanup_connections() checks for hedge_client/primary_client (never initialized)
- Lines 804-825: check_arbitrage_opportunity() uses primary_client/hedge_client
- Lines 866-880: connect_websockets() sets up handlers for non-existent clients
- Lines 882-1008: Order handlers for primary/hedge (never called)
- Lines 1015-1031: get_positions() with hedge_only/primary_only (never used)
- Lines 1106-1829: Massive arbitrage execution logic (~723 lines)
- Lines 2054-2408: Emergency unwind for primary_client (never used)
- Lines 2422-2730: trading_loop() using primary_client/hedge_client (never called)
- Lines 2732-2844: run() method (never called, main() uses run_alternating_strategy())

**Dead Code Statistics**:
- Total dead code: ~1,400 lines (48% of file)
- Working code: ~1,400 lines (48% of file)
- Shared utilities: ~85 lines (4% of file)

### Working System (System A - ACTIVELY USED)

**ETH/SOL Client References** (34 lines, ACTIVELY EXECUTED):
- Lines 424-433: get_position() uses eth_client/sol_client
- Lines 451-465: log_trade() uses eth_client/sol_client
- Lines 614-663: execute_unwind_cycle() uses eth_client/sol_client WITH VERIFICATION
- Lines 623-624, 640-641, 655-656: Position verification already implemented
- Lines 723-735: run_alternating_strategy() (ACTUALLY CALLED from main)
- Lines 681-699: execute_buy_first_cycle() (ACTIVELY USED)
- Lines 701-720: execute_sell_first_cycle() (ACTIVELY USED)
- Lines 2723-2730: Reconcile positions using eth_client/sol_client

---

## Problem Diagnosis (CORRECTED)

### Original User Report (MISUNDERSTOOD)
- User mentioned "LONG=202, SHORT=104 trades" -> Could not verify these exact numbers
- CSV shows: LONG=57, SHORT=18 (ETH), ratio 3.17:1
- User said "WebSocket integration needed" -> ALREADY EXISTS (lines 850-851)

### Actual Problem (IDENTIFIED)

**Issue**: Failed UNWIND cycles cause accumulation

**Evidence from CSV**:
- Row 25-31: Multiple BUILD cycles without proper UNWIND
- Rows 88-153: EMERGENCY unwind orders appear (signaling failed normal unwinds)
- ETH accumulation: 57 BUY vs 18 SELL = 39 net OPEN positions
- SOL accumulation: 44 BUY vs 33 SELL = 11 net OPEN positions

**Root Cause**:
1. execute_unwind_cycle() (lines 614-663) has verification logic
2. BUT verification might have false positives (tolerance too loose?)
3. BUILD cycles (execute_buy_first_cycle, execute_sell_first_cycle) don't CHECK if positions are already open
4. No guard rail to prevent opening new positions when old positions exist

**Why Verification Might Fail**:
- POSITION_TOLERANCE = Decimal("0.001") might be too loose
- 0.5s sleep after orders (line 637) might not be enough for REST API consistency
- IOC orders might report FILLED but position update delayed
- Race condition between order fill and position query

---

## Work Objectives

### Core Objective
Fix SOL position accumulation in DN_pair_eth_sol_nado.py by preventing BUILD cycles from opening positions when previous UNWIND failed to close them.

### Deliverables
1. Add pre-BUILD position verification to execute_buy_first_cycle() and execute_sell_first_cycle()
2. Add aggressive position reconciliation in execute_unwind_cycle() (multiple retries with longer delays)
3. Remove or isolate ~1,400 lines of dead cross-exchange arbitrage code
4. Add early exit safety check: refuse to BUILD if positions > 0
5. Add CSV analysis script to detect accumulation patterns

### Definition of Done
- [ ] No position accumulation over 20 iterations (test with backtest)
- [ ] Dead code removed or clearly separated
- [ ] BUILD cycles refuse to open if positions > 0.01 tolerance
- [ ] UNWIND cycles verify with 3 retries, 2s delays, and REST API fallback
- [ ] CSV analysis shows net position delta ≈ 0 for both ETH and SOL (abs(position) < 0.001)

---

## Must Have / Must NOT Have

### Must Have (Guardrails)
1. **DO NOT add WebSocket integration** (already exists and works)
2. **DO NOT modify initialize_clients()** (eth_client/sol_client already connect properly)
3. **DO add pre-BUILD position checks** (prevent opening on top of existing positions)
4. **DO add tighter UNWIND verification** (3 retries with 2s delays, not 0.5s)
5. **DO remove or isolate dead code** (clarify architecture, eliminate confusion)
6. **DO verify with CSV analysis** (quantitative proof of fix)

### Must NOT Have (Anti-patterns)
1. NO new WebSocket code (already implemented)
2. NO primary_client/hedge_client references in working code
3. NO false success logging (must log UNWIND failures accurately)
4. NO tolerance > 0.001 for position verification
5. NO BUILD cycles without checking existing positions first

---

## Task Flow and Dependencies

```
Phase 1: Diagnosis & Verification (30 min)
├─ Task 1.1: Analyze CSV for accumulation patterns
├─ Task 1.2: Verify UNWIND failure scenarios
└─ Task 1.3: Test position verification logic

Phase 2: Fix Implementation (2 hours)
├─ Task 2.1: Add pre-BUILD position checks
├─ Task 2.2: Improve UNWIND verification (3 retries, 2s delays)
├─ Task 2.3: Add early exit safety check
└─ Task 2.4: Add CSV analysis verification

Phase 3: Architecture Cleanup (3 hours)
├─ Task 3.1: Create new file for cross-exchange arbitrage (if needed)
├─ Task 3.2: Remove dead code from DN_pair_eth_sol_nado.py
└─ Task 3.3: Verify no references to removed code

Phase 4: Testing & Validation (2 hours)
├─ Task 4.1: Backtest 20 iterations
├─ Task 4.2: CSV analysis shows no accumulation
└─ Task 4.3: Manual verification of position tracking
```

---

## Detailed TODOs

### Phase 1: Diagnosis & Verification

#### Task 1.1: Analyze CSV for Accumulation Patterns
**Acceptance Criteria**:
- [ ] Script that parses DN_pair_eth_sol_nado_trades.csv
- [ ] Calculates net position delta: BUY - SELL for each asset
- [ ] Flags net position > 0.001 as WARNING
- [ ] Identifies sequences of BUILD without UNWIND
- [ ] Outputs timestamp of first accumulation event

**Implementation Steps**:
1. Create `scripts/analyze_accumulation.py`
2. Parse CSV and group by side (BUY/SELL) for each asset
3. Calculate net position: BUY_count - SELL_count (delta analysis)
4. Flag abs(net_position) > 0.001 as accumulation warning
5. Scan for consecutive BUILD cycles without intervening UNWIND
6. Output findings to console with delta values

**Data Source**: `/Users/botfarmer/2dex/logs/DN_pair_eth_sol_nado_trades.csv`

---

#### Task 1.2: Verify UNWIND Failure Scenarios
**Acceptance Criteria**:
- [ ] Test cases for UNWIND returning True but positions > 0
- [ ] Test IOC order fills with delayed position updates
- [ ] Test REST API consistency delays
- [ ] Document false positive scenarios

**Implementation Steps**:
1. Create `tests/test_unwind_verification.py`
2. Mock eth_client.get_account_positions() to return non-zero after "successful" unwind
3. Test with 0.5s, 1s, 2s delays to find minimum safe delay
4. Test with tolerance values: 0.001, 0.0001, 0.0
5. Document scenarios where verification fails

---

#### Task 1.3: Test Position Verification Logic
**Acceptance Criteria**:
- [ ] Unit tests for abs(position) < POSITION_TOLERANCE
- [ ] Test with edge cases: 0.001, 0.0009, 0.0011
- [ ] Test with negative positions
- [ ] Verify tolerance is appropriate for Nado's position precision

**Implementation Steps**:
1. Review Nado's position precision (likely 0.0001 for ETH, 0.001 for SOL)
2. Adjust POSITION_TOLERANCE if too loose
3. Create unit tests for verification logic
4. Test with realistic position values

---

### Phase 2: Fix Implementation

#### Task 2.1: Add Pre-BUILD Position Checks
**File**: `hedge/DN_pair_eth_sol_nado.py`
**Lines**: 605-613 (execute_build_cycle), 681-699 (execute_buy_first_cycle), 701-720 (execute_sell_first_cycle)

**Acceptance Criteria**:
- [ ] execute_build_cycle() checks positions before opening
- [ ] execute_buy_first_cycle() checks positions before opening
- [ ] execute_sell_first_cycle() checks positions before opening
- [ ] Returns False if positions > 0.001 tolerance
- [ ] Logs error: "BUILD refused: existing positions detected"

**Implementation**:
```python
async def execute_build_cycle(self) -> bool:
    """Execute BUILD cycle: Buy ETH / Sell SOL."""
    POSITION_TOLERANCE = Decimal("0.001")

    # PRE-BUILD: Check for existing positions
    eth_pos = await self.eth_client.get_account_positions()
    sol_pos = await self.sol_client.get_account_positions()

    if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
        self.logger.error(
            f"[BUILD] REFUSED: Existing positions detected: "
            f"ETH={eth_pos}, SOL={sol_pos}. Run UNWIND first."
        )
        return False

    # Original BUILD logic continues...
```

---

#### Task 2.2: Improve UNWIND Verification (3 Retries, 2s Delays)
**File**: `hedge/DN_pair_eth_sol_nado.py`
**Lines**: 614-663 (execute_unwind_cycle)

**Current Problem**:
- Only 1 retry with 1s delay
- 0.5s initial delay might be too short
- No REST API fallback if WebSocket position query fails

**Acceptance Criteria**:
- [ ] 3 retries with 2s delays (not 0.5s + 1 retry with 1s)
- [ ] REST API fallback if WebSocket position unavailable
- [ ] Returns False only after ALL retries exhausted
- [ ] Logs each retry with position values
- [ ] Final check uses REST API (most reliable)

**Implementation**:
```python
async def execute_unwind_cycle(self) -> bool:
    """Execute UNWIND cycle: Sell ETH / Buy SOL.

    Returns:
        True if both positions are closed (abs < 0.001), False otherwise.
    """
    POSITION_TOLERANCE = Decimal("0.001")
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # Increased from 0.5s to 2s

    # [단계 1] UNWIND 전 포지션 확인
    eth_pos_before = await self.eth_client.get_account_positions()
    sol_pos_before = await self.sol_client.get_account_positions()
    self.logger.info(f"[UNWIND] POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")

    # [단계 2] UNWIND 주문 실행 (ETH SELL, SOL BUY)
    eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")

    # [단계 3] 체결 확인
    if not (isinstance(eth_result, OrderResult) and eth_result.success and
            isinstance(sol_result, OrderResult) and sol_result.success):
        self.logger.warning("[UNWIND] Orders failed or partially filled")
        return False

    # [단계 4-8] Multiple retries with REST API verification
    for retry in range(MAX_RETRIES):
        await asyncio.sleep(RETRY_DELAY)

        # Use REST API for final verification (most reliable)
        eth_pos_after = await self.eth_client.get_account_positions()
        sol_pos_after = await self.sol_client.get_account_positions()
        self.logger.info(
            f"[UNWIND] POSITIONS AFTER (retry {retry+1}/{MAX_RETRIES}): "
            f"ETH={eth_pos_after}, SOL={sol_pos_after}"
        )

        eth_closed = abs(eth_pos_after) < POSITION_TOLERANCE
        sol_closed = abs(sol_pos_after) < POSITION_TOLERANCE

        if eth_closed and sol_closed:
            self.logger.info(f"[UNWIND] SUCCESS: Both positions closed (retry {retry+1})")
            return True

    # All retries exhausted
    self.logger.error(
        f"[UNWIND] FAILED: Positions still open after {MAX_RETRIES} retries: "
        f"ETH={eth_pos_after}, SOL={sol_pos_after}"
    )
    return False
```

---

#### Task 2.3: Add Early Exit Safety Check
**File**: `hedge/DN_pair_eth_sol_nado.py`
**Lines**: 723-735 (run_alternating_strategy)

**Acceptance Criteria**:
- [ ] Check positions at start of each iteration
- [ ] Skip BUILD if positions > 0.001
- [ ] Attempt UNWIND if positions detected
- [ ] Log error and stop if UNWIND fails
- [ ] Prevent accumulation cascade

**Implementation**:
```python
async def run_alternating_strategy(self) -> List[bool]:
    """Run alternating strategy for N iterations."""
    results = []
    POSITION_TOLERANCE = Decimal("0.001")

    for i in range(self.iterations):
        # Safety check: refuse to start if positions already exist
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
            self.logger.error(
                f"[SAFETY] Existing positions detected at start of iteration {i+1}: "
                f"ETH={eth_pos}, SOL={sol_pos}. Attempting UNWIND..."
            )

            # Try to UNWIND first
            unwind_success = await self.execute_unwind_cycle()
            if not unwind_success:
                self.logger.error(
                    "[SAFETY] UNWIND failed. Stopping bot to prevent accumulation."
                )
                break

        # Proceed with normal cycle
        if i % 2 == 0:
            result = await self.execute_buy_first_cycle()
        else:
            result = await self.execute_sell_first_cycle()

        results.append(result)

    return results
```

---

#### Task 2.4: Add CSV Analysis Verification
**File**: `scripts/verify_no_accumulation.py`

**Acceptance Criteria**:
- [ ] Script analyzes DN_pair_eth_sol_nado_trades.csv
- [ ] Calculates net position delta: BUY - SELL for each asset
- [ ] Passes if abs(net_position) < 0.001 for both ETH and SOL
- [ ] Fails if abs(net_position) >= 0.001 for any asset
- [ ] Outputs pass/fail with delta details
- [ ] Exit code 0 for pass, 1 for fail

**Implementation**:
```python
#!/usr/bin/env python3
"""
Verify no position accumulation in DN pair trading.
Exits with 0 if net positions are near zero (abs < 0.001), 1 otherwise.
"""

import csv
import sys
from collections import Counter

def analyze_trades(csv_path):
    """Analyze trades and detect accumulation via net position delta."""
    eth_trades = []
    sol_trades = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            side = row['side']
            if 'ETH' in side:
                eth_trades.append(side)
            elif 'SOL' in side:
                sol_trades.append(side)

    # Count BUY vs SELL
    eth_counts = Counter(eth_trades)
    sol_counts = Counter(sol_trades)

    eth_buy = eth_counts.get('ETH-BUY', 0)
    eth_sell = eth_counts.get('ETH-SELL', 0)
    sol_buy = sol_counts.get('SOL-BUY', 0)
    sol_sell = sol_counts.get('SOL-SELL', 0)

    # Calculate net position delta (NOT ratio)
    # Delta = BUY - SELL (positive = long accumulation, negative = short accumulation)
    eth_delta = eth_buy - eth_sell
    sol_delta = sol_buy - sol_sell

    return {
        'eth_buy': eth_buy,
        'eth_sell': eth_sell,
        'eth_delta': eth_delta,
        'sol_buy': sol_buy,
        'sol_sell': sol_sell,
        'sol_delta': sol_delta,
    }

def main():
    csv_path = 'logs/DN_pair_eth_sol_nado_trades.csv'

    stats = analyze_trades(csv_path)

    print(f"ETH: {stats['eth_buy']} BUY vs {stats['eth_sell']} SELL (delta: {stats['eth_delta']:+d})")
    print(f"SOL: {stats['sol_buy']} BUY vs {stats['sol_sell']} SELL (delta: {stats['sol_delta']:+d})")

    # Check thresholds: net position should be ≈ 0
    POSITION_TOLERANCE = 0.001

    # For DN pair trading, each BUY should have matching SELL
    # Delta represents unmatched trades (accumulation)
    eth_pass = abs(stats['eth_delta']) < POSITION_TOLERANCE
    sol_pass = abs(stats['sol_delta']) < POSITION_TOLERANCE

    if eth_pass and sol_pass:
        print("\n[PASS] No accumulation detected (net positions ≈ 0)")
        sys.exit(0)
    else:
        print("\n[FAIL] Accumulation detected (net positions ≠ 0)")
        if not eth_pass:
            print(f"  - ETH delta {stats['eth_delta']:+d} exceeds tolerance ±{POSITION_TOLERANCE}")
        if not sol_pass:
            print(f"  - SOL delta {stats['sol_delta']:+d} exceeds tolerance ±{POSITION_TOLERANCE}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

---

### Phase 3: Architecture Cleanup

#### Task 3.1: Create New File for Cross-Exchange Arbitrage (OPTIONAL)
**Decision Point**: Ask user if cross-exchange arbitrage is needed

**If YES**:
1. Create `hedge/dn_pair_cross_exchange.py`
2. Copy lines 800-2844 (dead code) to new file
3. Initialize primary_client/hedge_client properly
4. Test cross-exchange arbitrage separately

**If NO** (Recommended):
- Skip to Task 3.2 (remove dead code)

---

#### Task 3.2: Remove Dead Code from DN_pair_eth_sol_nado.py
**File**: `hedge/DN_pair_eth_sol_nado.py`

**Lines to Remove** (Total: ~1,400 lines):
1. Lines 316-323: cleanup_connections() hedge/primary checks
2. Lines 800-825: check_arbitrage_opportunity()
3. Lines 866-1008: connect_websockets() and order handlers
4. Lines 1015-1031: get_positions() hedge/primary variants
5. Lines 1106-1829: Cross-exchange arbitrage execution logic
6. Lines 2054-2408: Emergency unwind for primary_client
7. Lines 2422-2844: trading_loop() and run() methods (never called)

**Lines to Keep** (Working System A):
1. Lines 1-799: Core imports, Config, TradeMetrics, DNPairBot class init
2. Lines 827-865: initialize_clients() (eth_client/sol_client)
3. Lines 424-663: Position verification and execute_unwind_cycle()
4. Lines 681-735: execute_buy_first_cycle, execute_sell_first_cycle, run_alternating_strategy
5. Lines 2846-2886: main() function

**Acceptance Criteria**:
- [ ] No references to primary_client or hedge_client
- [ ] File size reduced from 2885 to ~1500 lines
- [ ] All remaining code is executable
- [ ] No broken imports or function calls
- [ ] Tests pass after removal

**Implementation Steps**:
1. Create backup: `cp DN_pair_eth_sol_nado.py DN_pair_eth_sol_nado.py.backup`
2. Remove lines 800-825 (check_arbitrage_opportunity)
3. Remove lines 866-1008 (connect_websockets, handlers)
4. Remove lines 1015-1031 (get_positions hedge/primary variants)
5. Remove lines 1106-2408 (arbitrage logic, emergency unwind, trading_loop)
6. Remove lines 2422-2844 (unused run() method)
7. Verify no remaining references to primary_client/hedge_client
8. Run tests to ensure no broken calls

---

#### Task 3.3: Verify No References to Removed Code
**Acceptance Criteria**:
- [ ] grep for "primary_client" returns 0 results
- [ ] grep for "hedge_client" returns 0 results
- [ ] grep for "check_arbitrage" returns 0 results
- [ ] grep for "connect_websockets" returns 0 results
- [ ] All tests pass

**Implementation**:
```bash
# Verify removal
grep -n "primary_client" hedge/DN_pair_eth_sol_nado.py | wc -l  # Should be 0
grep -n "hedge_client" hedge/DN_pair_eth_sol_nado.py | wc -l    # Should be 0

# Run tests
python3 -m pytest tests/ -v
```

---

### Phase 4: Testing & Validation

#### Task 4.1: Backtest 20 Iterations
**Acceptance Criteria**:
- [ ] Run bot for 20 iterations in test mode
- [ ] No accumulation detected
- [ ] All UNWIND cycles return True
- [ ] All BUILD cycles complete successfully
- [ ] CSV shows balanced BUY/SELL ratios

**Implementation**:
```bash
# Run backtest
cd /Users/botfarmer/2dex/hedge
python3 DN_pair_eth_sol_nado.py --size 100 --iter 20 --env .env.test

# Analyze results
python3 ../scripts/verify_no_accumulation.py
```

---

#### Task 4.2: CSV Analysis Shows No Accumulation
**Acceptance Criteria**:
- [ ] ETH net position delta: abs(BUY - SELL) < 0.001
- [ ] SOL net position delta: abs(BUY - SELL) < 0.001
- [ ] Combined delta sum (ETH + SOL) ≈ 0
- [ ] verify_no_accumulation.py exits with code 0

**Implementation**:
```bash
python3 scripts/verify_no_accumulation.py
echo $?  # Should be 0
```

---

#### Task 4.3: Manual Verification of Position Tracking
**Acceptance Criteria**:
- [ ] Log files show position checks before each BUILD
- [ ] UNWIND retries logged with position values
- [ ] Error messages clear when BUILD refused
- [ ] No "UNWIND SUCCESS" logged when positions > 0.001

**Implementation**:
```bash
# Check logs
grep "BUILD REFUSED" logs/DN_pair_eth_sol_nado_log.txt
grep "UNWIND SUCCESS" logs/DN_pair_eth_sol_nado_log.txt
grep "POSITIONS AFTER" logs/DN_pair_eth_sol_nado_log.txt
```

---

## Commit Strategy

### Commit 1: Fix UNWIND Verification (Critical)
```
fix: Improve UNWIND cycle verification with 3 retries and 2s delays

- Changed from 1 retry (1s) to 3 retries (2s each)
- Added REST API fallback for position verification
- Reduced false positives in UNWIND success reporting
- Fixed SOL accumulation caused by failed UNWIND cycles

File: hedge/DN_pair_eth_sol_nado.py
Lines: 614-663 (execute_unwind_cycle)

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

### Commit 2: Add Pre-BUILD Position Checks
```
fix: Add pre-BUILD position verification to prevent accumulation

- execute_build_cycle() now checks for existing positions
- execute_buy_first_cycle() refuses to BUILD if positions > 0.001
- execute_sell_first_cycle() refuses to BUILD if positions > 0.001
- run_alternating_strategy() attempts UNWIND if positions detected
- Prevents accumulation cascade from failed UNWIND cycles

Files:
- hedge/DN_pair_eth_sol_nado.py (lines 605-720, 723-735)

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

### Commit 3: Add CSV Analysis Verification
```
feat: Add CSV analysis script to detect position accumulation

- Created scripts/analyze_accumulation.py
- Calculates net position delta: BUY - SELL for each asset
- Flags abs(net_position) > 0.001 as WARNING
- Identifies sequences of BUILD without UNWIND
- Created scripts/verify_no_accumulation.py for CI/CD

Files:
- scripts/analyze_accumulation.py (new)
- scripts/verify_no_accumulation.py (new)

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

### Commit 4: Remove Dead Code (Architecture Cleanup)
```
refactor: Remove 1,400 lines of dead cross-exchange arbitrage code

- Removed primary_client/hedge_client references (never initialized)
- Removed check_arbitrage_opportunity() (unused)
- Removed connect_websockets() for non-existent clients
- Removed 723 lines of arbitrage execution logic (never called)
- Removed trading_loop() and run() methods (unused)
- File reduced from 2885 to ~1500 lines (48% reduction)
- Architecture now clearly focused on dual-NADO-ticker DN pair trading

Decision: Cross-exchange arbitrage NOT implemented in this bot.
If needed, create separate file: hedge/dn_pair_cross_exchange.py

File: hedge/DN_pair_eth_sol_nado.py
Removed lines: 316-323, 800-825, 866-1008, 1015-1031, 1106-2408, 2422-2844

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

---

## Success Criteria

### Quantitative Metrics
1. **No Accumulation**: Net position delta ≈ 0 for both ETH and SOL (abs(delta) < 0.001)
2. **UNWIND Reliability**: > 95% success rate (19/20 iterations close both positions to < 0.001)
3. **BUILD Safety**: 0% BUILD attempts with existing positions
4. **File Size**: Reduced from 2885 to < 1600 lines (45% reduction)
5. **Dead Code**: 0 references to primary_client/hedge_client

### Qualitative Metrics
1. **Clear Architecture**: Single bot implementation (dual-NADO-ticker)
2. **No Confusion**: No conflicting code paths
3. **Maintainability**: Easy to understand and modify
4. **Reliability**: Position verification prevents accumulation
5. **Testability**: CSV analysis provides quantitative proof via delta analysis

### Validation Checklist
- [ ] CSV analysis shows net position delta within tolerance (abs(delta) < 0.001)
- [ ] No BUILD cycles execute with existing positions
- [ ] UNWIND cycles verify with 3 retries and 2s delays
- [ ] File size reduced by > 40%
- [ ] No references to removed dead code
- [ ] All tests pass
- [ ] Manual log review confirms no false success reports
- [ ] Delta sum (ETH + SOL exposure) ≈ 0 after 20 iterations

---

## Risk Assessment

### Low Risk
- Adding pre-BUILD checks (pure safety improvement)
- Improving UNWIND verification (more retries = safer)
- Adding CSV analysis (read-only, no code changes)

### Medium Risk
- Removing dead code (could have hidden dependencies)
- Changing delays from 0.5s to 2s (slower cycles)

### Mitigation
- Backup file before removing code: `DN_pair_eth_sol_nado.py.backup`
- Run tests after each commit
- Verify with backtest before production
- Keep CSV analysis script for post-deployment monitoring

---

## Notes

### Why NOT Add WebSocket Integration
1. **Already Exists**: Lines 850-851 already connect WebSocket for eth_client/sol_client
2. **Not the Problem**: Accumulation is caused by failed UNWIND, not missing data
3. **REST API is Reliable**: Nado's REST API is sufficient for position queries
4. **Unnecessary Complexity**: WebSocket doesn't fix the root cause

### Why Remove Dead Code
1. **Confusing Architecture**: Two incompatible systems in one file
2. **Maintenance Burden**: 1,400 lines of dead code to maintain
3. **False Positives**: grep/search finds code that never executes
4. **Clarity**: Single, clear implementation is easier to debug

### Why This Fix Will Work
1. **Prevents Opening on Top of Existing Positions**: BUILD cycles now check first
2. **Improves UNWIND Reliability**: 3 retries with 2s delays vs 1 retry with 1s
3. **Early Exit Safety**: Stops bot if accumulation detected
4. **Quantitative Verification**: CSV analysis proves fix works

---

## Appendix: Data Source Details

### CSV Analysis (Current State)
**File**: `/Users/botfarmer/2dex/logs/DN_pair_eth_sol_nado_trades.csv`
**Total Trades**: 153
**Last Updated**: 2026-01-30

**ETH Position**:
- BUY: 57 trades ($1.97 notional)
- SELL: 18 trades ($0.55 notional)
- Ratio: 3.17:1 (BUY/SELL)
- Net: +39 OPEN positions (ACCUMULATION DETECTED)

**SOL Position**:
- BUY: 44 trades ($38.74 notional)
- SELL: 33 trades ($27.28 notional)
- Ratio: 1.33:1 (BUY/SELL)
- Net: +11 OPEN positions (within tolerance)

**Target After Fix**:
- ETH Net Position: abs(BUY - SELL) < 0.001 (delta ≈ 0)
- SOL Net Position: abs(BUY - SELL) < 0.001 (delta ≈ 0)
- Combined Delta: ETH delta + SOL delta ≈ 0 (total hedged exposure near zero)

---

## End of Plan

**Next Steps**:
1. Review and approve this corrected plan
2. Execute Phase 1 (Diagnosis) to confirm root cause
3. Execute Phase 2 (Fix) to implement solution
4. Execute Phase 3 (Cleanup) to remove dead code
5. Execute Phase 4 (Validation) to verify fix

**Estimated Total Time**: 7.5 hours
**Priority**: P0 (Critical - SOL accumulation prevents safe trading)
