# SOL Position Close Bug Fix - P0 ONLY (RALPLAN Iteration 3)

**Created**: 2026-01-30
**Status**: READY FOR IMPLEMENTATION
**Priority**: P0 CRITICAL - SOL Position Accumulation Bug
**Total Estimated Time**: 5 hours

---

## Executive Summary

### Critical Finding: SOL Position Accumulation Bug

**Evidence from CSV Analysis (124 lines):**
- SOL BUY entries: 28
- SOL SELL entries: 14 (2:1 ratio - positions accumulating)
- SOL EMERGENCY exits: 8
- ETH EMERGENCY exits: 0
- Net result: ~19 SOL position ($2184) vs 0.02 ETH ($57.79)

**User Confirmed Problem:**
"40배 차이... SOL 청산 로직이 작동하지 않아서 포지션 누적"
(40x difference... SOL close logic not working, positions accumulating)

**User Confirmed Working:**
"이번엔 Long-Short 제대로 됨" (This time Long-Short works correctly)
- DN direction is working correctly
- Only SOL close logic is broken

---

## Root Cause Analysis

### The Bug Location

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Function**: `emergency_unwind_sol()`
**Lines**: 1013-1024

**Current SOL Code (BUGGY):**
```python
result = await self.sol_client.place_ioc_order(...)
if result.success:
    self.logger.info(f"[EMERGENCY] SOL closed: {result.filled_size} @ ${result.price}")
    # Log to CSV - emergency unwind is always an EXIT
    if result.filled_size > 0:
        self.log_trade_to_csv(...)
else:
    self.logger.error(f"[EMERGENCY] SOL close failed: {result.error_message}")
```

**Problem:**
- Line 1013 checks `result.success` ONLY
- Does NOT check `result.filled_size > 0` before considering it successful
- When IOC order returns `success=True, filled_size=0`, it logs success but position remains open
- This causes SOL positions to accumulate over cycles

### ETH Comparison (WORKING CORRECTLY)

**File**: Same file
**Function**: `emergency_unwind_eth()`
**Lines**: 941-953

**Current ETH Code (CORRECT):**
```python
result = await self.eth_client.place_ioc_order(...)
if result.success and result.filled_size > 0:  # ← ETH checks BOTH conditions together
    self.logger.info(f"[EMERGENCY] ETH closed: {result.filled_size} @ ${result.price}")
    self.log_trade_to_csv(...)
else:
    self.logger.error(f"[EMERGENCY] ETH close failed: {result.error_message}")
```

**Why ETH Works:**
- ETH checks BOTH `result.success AND result.filled_size > 0` together
- SOL checks them separately, causing false success logging

---

## Implementation Plan

### Phase 0.5: Root Cause Investigation (1 hour)

**BEFORE fixing, verify the actual bug behavior**

**Goal**: Capture actual result object states to confirm `success=True, filled_size=0` occurs

#### Task 0.5.1: Add Diagnostic Logging

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: In `emergency_unwind_sol()`, after line 1012

**Add:**
```python
result = await self.sol_client.place_ioc_order(
    self.sol_client.config.contract_id,
    qty_to_close,
    side
)

# DIAGNOSTIC: Log full result object state
self.logger.info(f"[DIAGNOSTIC] SOL IOC result:")
self.logger.info(f"  success={result.success}")
self.logger.info(f"  filled_size={result.filled_size}")
self.logger.info(f"  price={result.price}")
self.logger.info(f"  error_message={result.error_message}")
```

**Acceptance:**
- Logs show actual result object state
- Can identify when `success=True, filled_size=0` occurs

#### Task 0.5.2: Run Test Cycles

**Command:**
```bash
# Run 5 test cycles with small size
python3 hedge/DN_pair_eth_sol_nado.py --size 10 --iter 5 --csv-path logs/test_diagnostic.csv
```

**Acceptance:**
- 5 cycles completed
- Diagnostic logs captured
- CSV generated for analysis

#### Task 0.5.3: Analyze Results

**Check:**
- Count occurrences of `success=True, filled_size=0`
- Compare with ETH emergency unwind results
- Confirm root cause hypothesis

**Acceptance:**
- Root cause confirmed or disproven
- Actual bug behavior documented
- Clear evidence for fix approach

---

### Phase 1: Fix SOL Position Close Bug (2 hours)

**CRITICAL: Start simple, match ETH exactly**

#### Task 1.1: Fix Line 1013 Success Check

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: Lines 1013-1024

**Change FROM:**
```python
if result.success:
    self.logger.info(f"[EMERGENCY] SOL closed: {result.filled_size} @ ${result.price}")
    # Log to CSV - emergency unwind is always an EXIT
    if result.filled_size > 0:
        self.log_trade_to_csv(
            exchange="NADO",
            side=f"SOL-{side.upper()}",
            price=str(result.price),
            quantity=str(result.filled_size),
            order_type="exit",  # Emergency unwind always exits position
            mode="EMERGENCY"  # Special mode to identify emergency unwind
        )
else:
    self.logger.error(f"[EMERGENCY] SOL close failed: {result.error_message}")
```

**Change TO:**
```python
if result.success and result.filled_size > 0:  # ← Check BOTH conditions (match ETH)
    self.logger.info(f"[EMERGENCY] SOL closed: {result.filled_size} @ ${result.price}")
    # Log to CSV - emergency unwind is always an EXIT
    self.log_trade_to_csv(
        exchange="NADO",
        side=f"SOL-{side.upper()}",
        price=str(result.price),
        quantity=str(result.filled_size),
        order_type="exit",  # Emergency unwind always exits position
        mode="EMERGENCY"  # Special mode to identify emergency unwind
    )
else:
    # Log detailed failure information
    self.logger.error(
        f"[EMERGENCY] SOL close failed: "
        f"success={result.success}, "
        f"filled_size={result.filled_size}, "
        f"error={result.error_message}"
    )
```

**Acceptance Criteria:**
- SOL emergency unwind only logs success when BOTH conditions met
- Matches ETH unwind behavior exactly
- Logs detailed failure information

#### Task 1.2: Test with 10 Cycles

**Command:**
```bash
# Run 10 cycles with small size
python3 hedge/DN_pair_eth_sol_nado.py --size 10 --iter 10 --csv-path logs/test_fix.csv
```

**Acceptance:**
- 10 cycles completed
- CSV generated
- No errors during execution

#### Task 1.3: Verify No SOL Accumulation

**Check:**
```bash
# Analyze CSV for SOL accumulation
python3 << 'EOF'
import csv
from decimal import Decimal

with open('logs/test_fix.csv', 'r') as f:
    reader = csv.DictReader(f)
    sol_trades = [row for row in reader if 'SOL' in row['side']]

buys = sum(Decimal(row['quantity']) for row in sol_trades if 'BUY' in row['side'])
sells = sum(Decimal(row['quantity']) for row in sol_trades if 'SELL' in row['side'])

net = buys - sells
print(f"SOL Buys: {buys}, Sells: {sells}, Net: {net}")

if abs(net) < Decimal('0.1'):
    print("PASS: SOL position closed correctly")
else:
    print(f"FAIL: SOL position {net} not closed")
EOF
```

**Acceptance:**
- SOL position net < 0.1 after 10 cycles
- No significant accumulation
- Ratio of BUY to SELL entries approximately 1:1

---

### Phase 2: DN Direction Verification (1 hour)

**User confirmed DN works, add safeguards to prevent regression**

#### Task 2.1: Add DN Direction Assertion

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: In `place_simultaneous_orders()`, after successful order placement

**Add after line 843:**
```python
# Verify DN direction: positions must be opposite
if eth_result.success and sol_result.success:
    # Reconcile actual positions
    eth_pos = await self.eth_client.get_account_positions()
    sol_pos = await self.sol_client.get_account_positions()

    # DN assertion: positions must have opposite signs
    if (eth_pos > 0 and sol_pos > 0) or (eth_pos < 0 and sol_pos < 0):
        self.logger.error(f"[DN_ASSERTION] FAIL: Both positions same direction! ETH={eth_pos}, SOL={sol_pos}")
        self.logger.error("[DN_ASSERTION] This is NOT delta-neutral - forcing close")
        await self.force_close_all_positions()
        raise Exception("DN direction assertion failed: both positions same direction")
    else:
        self.logger.info(f"[DN_ASSERTION] PASS: ETH={eth_pos}, SOL={sol_pos} (opposite directions)")
```

**Acceptance:**
- DN direction checked after each successful cycle
- Assertion failure triggers force close
- Logged as PASS/FAIL for monitoring

#### Task 2.2: Add CSV Column for DN Tracking

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location**: In `log_trade_to_csv()`

**Add new column to CSV:**
- Column name: "dn_direction"
- Values: "LONG" (positive position), "SHORT" (negative position), "FLAT" (zero)

**Implementation:**
```python
# In log_trade_to_csv(), add:
dn_direction = "LONG" if side.endswith("BUY") else "SHORT" if side.endswith("SELL") else "FLAT"

# Update CSV header to include: "timestamp,exchange,side,price,quantity,order_type,mode,dn_direction"
```

**Acceptance:**
- CSV includes DN direction for each trade
- Easy to verify DN correctness in post-analysis
- Can detect LONG-LONG or SHORT-SHORT cycles

---

### Phase 3: Validation (1 hour)

**Final validation before deployment**

#### Task 3.1: Run 20 Test Cycles

**Command:**
```bash
# Run 20 cycles with normal size
python3 hedge/DN_pair_eth_sol_nado.py --size 50 --iter 20 --csv-path logs/test_validation.csv
```

**Acceptance:**
- 20 cycles completed without errors
- CSV generated with dn_direction column

#### Task 3.2: Verify SOL Position

**Check:**
```bash
# Analyze SOL position after 20 cycles
python3 << 'EOF'
import csv
from decimal import Decimal

with open('logs/test_validation.csv', 'r') as f:
    reader = csv.DictReader(f)
    sol_trades = [row for row in reader if 'SOL' in row['side']]

buys = sum(Decimal(row['quantity']) for row in sol_trades if 'BUY' in row['side'])
sells = sum(Decimal(row['quantity']) for row in sol_trades if 'SELL' in row['side'])

net = buys - sells
print(f"SOL Buys: {buys}, Sells: {sells}, Net: {net}")

if abs(net) < Decimal('0.1'):
    print("PASS: SOL position closed correctly")
else:
    print(f"FAIL: SOL position {net} not closed")
EOF
```

**Acceptance:**
- SOL position net < 0.1 after 20 cycles
- No significant accumulation

#### Task 3.3: Verify DN Direction

**Check:**
```bash
# Verify DN direction from CSV
python3 << 'EOF'
import csv

with open('logs/test_validation.csv', 'r') as f:
    reader = csv.DictReader(f)

    dn_failures = 0
    total_cycles = 0

    for i, row in enumerate(reader):
        if i % 2 == 0:  # Pair trades
            eth_trade = row
            try:
                sol_trade = next(reader)
            except StopIteration:
                break

            eth_dn = eth_trade.get('dn_direction', 'UNKNOWN')
            sol_dn = sol_trade.get('dn_direction', 'UNKNOWN')

            total_cycles += 1

            if eth_dn == sol_dn:
                dn_failures += 1
                print(f"FAIL: Cycle {total_cycles} - Both {eth_dn}")
            else:
                print(f"PASS: Cycle {total_cycles} - ETH {eth_dn}, SOL {sol_dn}")

    print(f"\nDN Direction: {total_cycles - dn_failures}/{total_cycles} cycles correct")

    if dn_failures == 0:
        print("PASS: DN direction 100% correct")
    else:
        print(f"FAIL: {dn_failures} cycles with wrong DN direction")
EOF
```

**Acceptance:**
- DN direction 100% correct (opposite signs)
- No LONG-LONG or SHORT-SHORT cycles detected

---

## Success Criteria

### Phase 0.5 Success (Root Cause Investigation)
- Actual result object states captured in logs
- Occurrences of `success=True, filled_size=0` documented
- Root cause confirmed with real data

### Phase 1 Success (SOL Position Fix)
- SOL emergency unwind only logs success when filled_size > 0
- SOL position net < 0.1 after 10 cycles
- No SOL position accumulation
- Matches ETH unwind behavior exactly

### Phase 2 Success (DN Verification)
- DN direction assertion passes on 100% of cycles
- CSV shows correct DN direction (LONG-SHORT or SHORT-LONG)
- No LONG-LONG or SHORT-SHORT cycles detected

### Phase 3 Success (Validation)
- SOL position net < 0.1 after 20 cycles
- DN direction 100% correct
- No emergency unwinds in normal operation
- CSV logs show correct modes (entry/exit/EMERGENCY)

---

## Commit Strategy

### Commit 1: Add Diagnostic Logging (Phase 0.5)
```
feat(diagnostic): Add SOL emergency unwind logging

Root cause investigation for SOL position accumulation

Add diagnostic logging to capture actual result object states:
- Log success, filled_size, price, error_message
- Identify when success=True, filled_size=0 occurs
- Compare with ETH behavior

This commit adds logging only, no behavior changes.

Files modified:
- hedge/DN_pair_eth_sol_nado.py (emergency_unwind_sol)

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

### Commit 2: Fix SOL Position Close Bug (Phase 1)
```
fix(sol): Fix emergency_unwind_sol false success bug

CRITICAL: SOL positions accumulating due to false success logging

Root Cause:
- emergency_unwind_sol checked result.success separately from filled_size
- IOC orders returning success=True, filled_size=0 logged as success
- Positions remained open, accumulated over cycles

Fix:
- Check BOTH result.success AND result.filled_size > 0 together
- Match ETH emergency_unwind_eth behavior exactly
- Log detailed failure information

Evidence:
- 28 SOL BUY entries vs 14 SELL entries in CSV
- 8 SOL EMERGENCY exits, 0 ETH EMERGENCY exits
- Net position: ~19 SOL ($2184)

Fixes: SOL position accumulation bug
Related: User request "SOL 청산 로직이 작동하지 않아서 포지션 누적"

Files modified:
- hedge/DN_pair_eth_sol_nado.py (emergency_unwind_sol)

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

### Commit 3: Add DN Direction Verification (Phase 2)
```
feat(dn): Add DN direction assertion and CSV column

Prevent LONG-LONG or SHORT-SHORT cycles

Features:
- DN assertion after each cycle (positions must be opposite)
- CSV column: dn_direction (LONG/SHORT/FLAT)
- Assertion failure triggers force close
- Logged as PASS/FAIL for monitoring

User confirmed: "이번엔 Long-Short 제대로 됨"
This commit prevents regressions and adds monitoring.

Files modified:
- hedge/DN_pair_eth_sol_nado.py (place_simultaneous_orders, log_trade_to_csv)

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Root cause different than expected | Low | Medium | Phase 0.5 investigation confirms hypothesis |
| Fix breaks SOL emergency unwind | Low | Critical | Test with small size first (10 cycles) |
| DN assertion too strict | Low | Medium | Force close prevents trading with wrong DN |
| CSV column breaks parsing | Low | Low | Add column at end, backward compatible |

---

## Rollback Plan

### If Phase 1 Fails

**Symptoms:**
- SOL positions still accumulate after fix
- Emergency unwinds stop working entirely

**Rollback:**
1. Revert to original code
2. Investigate deeper root cause
3. Consider switching to ETH-only trading temporarily

### If Phase 2 Fails

**Symptoms:**
- DN assertion fails repeatedly
- System cannot trade

**Rollback:**
1. Change assertion to warning only
2. Keep CSV column for monitoring
3. Investigate DN direction logic

---

## Files Modified

### Core Files
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
  - `emergency_unwind_sol()` - Add diagnostic logging, fix success check
  - `place_simultaneous_orders()` - Add DN assertion
  - `log_trade_to_csv()` - Add dn_direction column

### Test Output Files
- `/Users/botfarmer/2dex/logs/test_diagnostic.csv` - Phase 0.5 output
- `/Users/botfarmer/2dex/logs/test_fix.csv` - Phase 1 output
- `/Users/botfarmer/2dex/logs/test_validation.csv` - Phase 3 output

---

## Excluded from This Plan (P1 Tasks)

**Intentionally EXCLUDED from this P0-only plan:**

1. Hedging imbalance fix (4.9% → <0.5% target)
2. Size increment confusion (tick_size vs size_increment)
3. BookDepth slippage (999999 bps issue)
4. V4 migration

**Reason**: These are P1 tasks that dilute focus from the critical SOL position bug. They will be addressed in separate plans after P0 fix is validated.

---

## Next Steps

1. **IMMEDIATE (P0 - Phase 0.5):** Add diagnostic logging, run 5 test cycles - 1 hour
2. **TODAY (P0 - Phase 1):** Fix success check, test with 10 cycles - 2 hours
3. **TODAY (P0 - Phase 2):** Add DN verification - 1 hour
4. **TODAY (P0 - Phase 3):** Validate with 20 cycles - 1 hour

**Total Estimated Time**: 5 hours

**Risk Level**: LOW (simple fix matching working ETH behavior)

---

## Plan Summary

**Scope**: P0 ONLY - SOL position close bug fix
**Files**: 1 file modified (DN_pair_eth_sol_nado.py)
**Estimated Time**: 5 hours
**Complexity**: LOW (simple fix, match ETH behavior)
**Risk**: LOW (test with small size first)

**Focus**: Fix the critical SOL position accumulation bug that prevents safe trading
**Exclude**: P1 tasks (hedging, size increment, BookDepth, V4)

---

**Plan Status**: READY FOR IMPLEMENTATION
**Priority**: P0 CRITICAL BUG ONLY
**Blockers**: None
**Based On**: RALPLAN Iteration 3 feedback - P0 focus, root cause investigation, simple fix
