# Feature Static TP - Context Document

**Branch:** feature-staticTP
**Plan Reference:** `.omc/plans/feature-staticTP-plan.md`
**Created:** 2026-02-02
**Last Updated:** 2026-02-02 (Critical Bug: Entry data not saved during retry)

---

## Purpose

Test hypothesis: **Static TP (individual 10bps per position) > 19bps spread exit strategy**

- **19bps spread**: Current bot exits when combined ETH+SOL position PNL reaches ~19 basis points
- **Static TP**: Exit when EITHER ETH OR SOL individually hits +10bps (0.10%), regardless of the other position

---

## Current Status

### CRITICAL BUG - TP NOT WORKING (2026-02-02)

**Status:** BLOCKING - TP feature completely non-functional

**Issue:** `WARNING: [STATIC TP] No entry data available`

**Root Cause:** When emergency_unwind closes positions after partial fill, entry data from initial fill becomes invalid. Retry fills DO save new entry data (line 2938), but:
1. Initial ETH fill → entry_prices saved (line 873)
2. SOL timeout → emergency_unwind closes ETH position
3. SOL retry fill → entry_prices saved (line 2938)
4. But ETH entry_price is from CLOSED position (invalid)
5. TP check fails: "No entry data available"

**Fix Required:** Clear entry data in `handle_emergency_unwind()` so retry fills save fresh data for ACTUAL positions.

**Bug Report:** `.omc/plans/feature-staticTP-bug-report.md`

---

### Phase 1: CRITICAL FIXES - COMPLETED

**Implemented:**

1. **Fix `handle_emergency_unwind()` Bug** (Lines 784-789)
   - Changed from `status == 'FILLED'` to `self._is_fill_complete(eth_result)`
   - Now correctly detects partial fills

2. **Add UNWIND Retry Logic** (Lines 2467-2561)
   - MAX_ORDER_RETRIES = 3
   - ORDER_RETRY_DELAY = 2.0 seconds
   - Separate `_exit_quantities` and `_exit_prices` tracking (immutable entry data preserved)
   - Queue filter bypass on 3rd retry attempt

### Phase 2: Static TP Implementation - COMPLETED

**Implemented:**

1. **TP Leverage Correction** (Lines 2233-2234)
   - TP threshold = 10bps / leverage
   - For 5x leverage: 10bps / 5 = 2bps price threshold
   - Correctly accounts for leverage multiplier in PNL calculation

2. **Static TP Monitoring** (Lines 2124-2268)
   - `_monitor_static_individual_tp()` method
   - Checks each position independently
   - Closes individual position when TP threshold hit

3. **Individual Position Closing** (Lines 2270-2390)
   - `_close_individual_position()` method
   - Proper order sizing and unwinding
   - Updates tracking state

4. **CLI Parameters**
   - `--enable-static-tp`: Enable/disable static TP
   - `--tp-bps`: TP threshold in basis points (default: 10)
   - `--tp-timeout`: Timeout for TP monitoring (default: 30s)

5. **UNWIND Integration** (Lines 1347-1417)
   - TP monitoring integrated into UNWIND cycle
   - Proper state management and position tracking

---

## Test Results ($100, 3 iterations)

### Test 1: feature-staticTP branch (2026-02-01)
```
Cycle 1: FAILED
- SOL order timeout during BUILD phase
- 3 retries failed (positions showing 0.0 - settling delay issue)
- Bot stopped for safety
```

### Test 2: feature-staticTP branch (2026-02-01)
```
Cycle 1: SUCCESS (PNL -$0.09)
- Both orders filled initially
- UNWIND completed with 19bps spread exit

Cycle 2: FAILED
- SOL timeout during UNWIND phase
- Bot stopped for safety
```

### Test 3: feature-staticTP branch (2026-02-02)
```
Cycle 1: SUCCESS
- Both orders filled initially
- Static TP triggered: SOL hit 0.07% (>= 2bps with leverage)
- Positions closed properly, no residuals
- PNL: $0.00, Fees: $0.04

Cycle 2: SUCCESS
- ETH filled, SOL timeout (retry logic worked)
- Static TP triggered: ETH hit 0.15% (>= 2bps with leverage)
- Positions closed properly, no residuals
- PNL: $0.00, Fees: $0.02

Summary: 2/2 cycles successful, no position accumulation, TP working correctly with leverage correction
```

### Original branch (baseline comparison)
```
Similar SOL timeout issues observed
- Position imbalance due to one-sided entries
- Queue/Liquidity Filter causing SKIP
```

---

## Key Issue Identified

### Problem: Position Check Timing / Settling Delay

**Symptom:**
```
INFO: [BUILD] Remaining quantities: ETH=4.311645755184754020609666710E-30, SOL=0.9849305623953511277454939427
INFO: [BUILD] Current positions: ETH=0.0, SOL=0.0
```

**Root Cause:**
- Retry logic calculates `remaining_qty` based on `abs(eth_pos)`
- Position check shows `0.0` because orders haven't settled yet
- This causes incorrect retry quantities (ETH showing ~4.3E-30 instead of actual fill)

**The Fix Needed:**
Retry logic should track fills via `OrderResult.filled_size` instead of relying on `get_account_positions()` for calculating remaining quantities.

---

## Hypothesis Validation Status

| Metric | Target | Current Status |
|--------|--------|----------------|
| Phase 1 complete | Critical fixes only | COMPLETED |
| Phase 2 complete | Static TP implementation | COMPLETED |
| TP functionality | Working correctly | **BLOCKED** - Entry data bug |
| Test 50+ cycles | 100+ cycles recommended | **BLOCKED** by bug |
| PNL comparison | Static TP > 19bps spread | **BLOCKED** by bug |
| Fill rate comparison | Measure both | **BLOCKED** by bug |

**Conclusion:** **BLOCKED by critical bug**. TP feature non-functional when retry is needed (common case). Fix required before testing can continue.

See: `.omc/plans/feature-staticTP-bug-report.md`

---

## Code References

### Modified File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Phase 1 Changes:**
- Lines 784-789: `handle_emergency_unwind()` fix
- Lines 2446-2450: Exit tracking initialization
- Lines 2467-2561: UNWIND retry logic

**Phase 2 Changes:**
- Lines 784-789: `handle_emergency_unwind()` fix
- Lines 1347-1417: UNWIND cycle TP integration
- Lines 2036-2043: `_is_fill_complete()` fill detection
- Lines 2124-2268: `_monitor_static_individual_tp()` TP monitoring
- Lines 2270-2390: `_close_individual_position()` position closing
- Lines 2446-2450: Exit tracking initialization
- Lines 2467-2561: UNWIND retry logic

**Key Methods:**
- `_is_fill_complete()`: Lines 2036-2043
- `_retry_side_order()`: Lines 2077-2112
- `_get_filled_size()`: Used for fill detection

---

## Recent Fixes (2026-02-02)

### Critical Bug Fixes

1. **TP Leverage Calculation** (Lines 2233-2234)
   - Fixed: TP threshold = 10bps / leverage (not raw 10bps)
   - For 5x leverage: 10bps / 5 = 2bps price movement triggers TP
   - This correctly accounts for leverage multiplier in PNL

2. **None Handling Pattern** (Multiple locations)
   - Fixed: Using `or Decimal("0")` pattern for safe None handling
   - Prevents NoneType errors in position calculations
   - Applied to: `entry_prices`, `exit_quantities`, `exit_prices`

3. **Fill Detection** (Lines 2036-2043)
   - Fixed: `_is_fill_complete()` checks `status == 'FILLED'`
   - Properly distinguishes between partial and complete fills
   - Critical for retry logic accuracy

4. **Position Accumulation** (Lines 2124-2390)
   - Fixed: All critical bugs causing position accumulation
   - Proper state management in `_close_individual_position()`
   - Correct position tracking after individual closes

---

## Next Steps

**CRITICAL - Fix Required First:**

1. **Fix Entry Data Bug** - Clear entry data in `handle_emergency_unwind()` (line ~990)
   - Add: `self.entry_prices = {"ETH": None, "SOL": None}`
   - Add: `self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}`
   - Add: `self.entry_timestamps = {"ETH": None, "SOL": None}`

2. **Test Fix** - Run 1-cycle test with intentional timeout
   - Verify TP triggers without "No entry data available" warning
   - Verify positions close properly

3. **Run 50+ cycle tests** - Compare 19bps spread vs Static TP PNL
4. **Statistical analysis** - Determine if hypothesis is valid (p < 0.05)
5. **Fill rate measurement** - Compare fill rates between strategies
6. **Decision** - Merge to main if statistically significant improvement

---

## Decision Criteria

**Merge to main IF:**
- [ ] Fix entry data bug
- [ ] Statistically significant PNL improvement (p < 0.05)
- [ ] Fill rate >= 85%
- [ ] No critical bugs

**Discard branch IF:**
- [ ] Bug cannot be fixed
- [ ] No significant improvement after fix
- [ ] Higher risk/loss
- [ ] Inconclusive results after 100 cycles
