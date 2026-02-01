# Tick Size Rounding Bug Fix Plan

**Created**: 2026-02-01  
**Priority**: CRITICAL (causes misleading error messages and prevents small orders)  
**Complexity**: MEDIUM (requires changes across multiple functions)  
**Iteration**: RALPLAN 2/5

---

## Context

### Problem Statement

When `raw_qty < tick_size`, the quantization calculation in `calculate_order_size_with_slippage()` produces `target_qty = 0`:

```python
# Line 324-326 in /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
raw_qty = self.target_notional / price
tick_size = client.config.tick_size
target_qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size
```

### Example Failure Case

```
raw_qty = 0.05, tick_size = 0.1 (ETH)
raw_qty / tick_size = 0.5
0.5.quantize(Decimal('1')) = 0
target_qty = 0 * tick_size = 0
```

### Current Broken Behavior Flow

1. **Line 326**: `target_qty = 0` due to quantization when `raw_qty < tick_size`
2. **Line 329**: `slippage = estimate_slippage(direction, 0)` is called with zero quantity
3. **Line 183 in nado_bookdepth_handler.py**: Returns `Decimal("0")` for zero quantity
4. **Lines 331-334**: Swallows the error - returns `(0, 0, True)` treating it as "no BookDepth data"
5. **Lines 411-417, 557-563**: Error message shows "slippage 0.0 bps > 10 bps threshold" - **MISLEADING!**

### Why Phase 2 (Early Return) is REQUIRED

The error propagation path without Phase 2 would be:

```
Phase 1 only (returns 999999 for zero quantity):
  Line 329: slippage = estimate_slippage(direction, 0) → returns 999999
  Line 331-334: if slippage >= 999999 → returns (0, 0, True)
  Lines 411-417: eth_qty == 0, eth_slippage_bps == 0
  Result: "ETH slippage 0.0 bps > 10 bps threshold" (STILL MISLEADING!)

Phase 2 (early return BEFORE slippage estimation):
  Line 326-327: if raw_qty < tick_size → returns (0, 999999, False)
  Lines 411-417: eth_qty == 0, eth_slippage_bps >= 999999
  Result: "ETH order size too small for exchange minimum" (CORRECT!)
```

**Critical Insight**: Lines 331-334 swallow error code 999999 by returning slippage=0 with `can_fill=True`. Only Phase 2's early return prevents this code path from being reached.

### Root Cause Analysis

The bug has TWO components:

1. **Quantity rounding to zero**: When `raw_qty < tick_size`, quantization produces 0
   - This is technically correct behavior for tick size enforcement
   - BUT we need to detect this case BEFORE slippage estimation

2. **Error code swallowing by lines 331-334**: This handler assumes 999999 means "no BookDepth data" and proceeds anyway
   - Returns `slippage=0` with `can_fill=True`, losing the error information
   - If Phase 1 returns 999999 for zero quantity, this code path would log "No BookDepth data" (misleading) and cause the same misleading error message downstream
   - **Phase 2's early return is required to bypass this problematic handler entirely**

### Affected Code Paths

**File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**
- Lines 295-359: `calculate_order_size_with_slippage()` function
- Lines 331-334: Error code handler that swallows 999999 (root cause of misleading message)
- Lines 400-422: POST_ONLY mode error handling (IOC mode)
- Lines 540-568: IOC mode error handling

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`**
- Line 183: `estimate_slippage()` zero quantity handling

---

## Work Objectives

### Core Objective

Fix the tick_size rounding bug by detecting when `raw_qty < tick_size` before quantization and returning appropriate error handling with accurate error messages.

### Deliverables

1. Modified `calculate_order_size_with_slippage()` to detect minimum quantity violations
2. Fixed error messages to distinguish between "size too small" and "excessive slippage"
3. Updated `estimate_slippage()` to return error code for zero quantity instead of 0
4. Verification that small orders are properly rejected with clear messaging

### Definition of Done

- Function detects `raw_qty < tick_size` before quantization
- Error messages clearly distinguish size issues from slippage issues
- Zero quantity passed to slippage estimator returns error code, not 0
- Both IOC and POST_ONLY error paths updated
- No regression in normal operation (when `raw_qty >= tick_size`)

---

## Must Have / Must NOT Have

### Must Have

- Detect `raw_qty < tick_size` BEFORE quantization (line 326)
- Return distinct error/skip path for minimum quantity violations
- **Phase 2 early return is REQUIRED** (not optional) to bypass lines 331-334 error code swallowing
- Update error messages in BOTH IOC (lines 557-563) and POST_ONLY (lines 411-417) paths
- Modify `estimate_slippage()` to return error code (Decimal(999999)) for zero quantity
- Log clear warning: "Order size {raw_qty} < minimum {tick_size} - CANNOT TRADE"
- Maintain existing function signature and return type

### Must NOT Have

- NO modification to `target_notional` or position sizing logic
- NO changing tick_size values (already correct from SDK)
- NO breaking existing callers of `calculate_order_size_with_slippage()`
- NO slippage estimation calls with zero quantity
- NO misleading "slippage 0.0 bps > threshold" error messages

---

## Detailed TODOs

### Phase 1: Fix estimate_slippage() Zero Quantity Handling

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`**

**Location**: Line 183

**Current Code**:
```python
if quantity == 0:
    return Decimal("0")
```

**Required Change**:
```python
if quantity == 0:
    return Decimal(999999)  # Error code: invalid quantity
```

**Rationale**: Zero quantity is an error condition, not a valid input. Returning 0 causes misleading error messages downstream. Using `Decimal(999999)` for consistency with existing error code convention at lines 189, 204, 226.

**Note**: Changed from `quantity <= 0` to `quantity == 0` since `raw_qty` and `tick_size` are always positive (calculated from positive `target_notional` and `price`), so negative quantities cannot occur in normal operation.

---

### Phase 2: Add Minimum Quantity Check in calculate_order_size_with_slippage()

**File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**

**Location**: REPLACE lines 323-329 with the following code

**Current Code** (lines 323-329):
```python
client = self.eth_client if ticker == "ETH" else self.sol_client
raw_qty = self.target_notional / price
tick_size = client.config.tick_size
target_qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

# Try to get slippage estimate from BookDepth
slippage = await client.estimate_slippage(direction, target_qty)
```

**Required Change** (REPLACE lines 323-329):
```python
client = self.eth_client if ticker == "ETH" else self.sol_client
raw_qty = self.target_notional / price
tick_size = client.config.tick_size

# MINIMUM QUANTITY CHECK: Detect order too small for exchange before quantization
if raw_qty < tick_size:
    self.logger.warning(
        f"[SLIPPAGE] {ticker} order size {raw_qty:.6f} < minimum {tick_size} - "
        f"CANNOT TRADE (notional=${self.target_notional}, price=${price:.2f})"
    )
    # Return zero quantity with error indicator (False = can't fill, 999999 = error code)
    return Decimal(0), Decimal(999999), False

target_qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

# Try to get slippage estimate from BookDepth
slippage = await client.estimate_slippage(direction, target_qty)
```

**Critical Rationale**: This early return is REQUIRED because:

1. **Bypasses error code swallowing**: Lines 331-334 catch `slippage >= 999999` and return `(target_qty, 0, True)`, losing the error information
2. **Prevents misleading log message**: Without early return, line 333 would log "No BookDepth data" which is misleading for a minimum size violation
3. **Ensures correct error propagation**: Early return preserves the error code (999999) and `can_fill=False` flag for downstream error message logic
4. **Detects problem before quantization**: Checking `raw_qty < tick_size` BEFORE line 326 prevents quantization from producing zero

**Why "REPLACE" not "INSERT"**: Line 326 IS the quantization line. The check must happen before `target_qty` is computed, so we replace the entire block from line 323 to 329 to insert the check at the correct position.

---

### Phase 3: Update Error Message Logic

**File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**

**Location 1**: Lines 411-417 (POST_ONLY mode)

**Current Code**:
```python
if eth_qty == 0:
    skip_reason.append(f"ETH slippage {eth_slippage_bps:.1f} bps > 10 bps threshold")
if sol_qty == 0:
    skip_reason.append(f"SOL slippage {sol_slippage_bps:.1f} bps > 10 bps threshold")
```

**Required Change**:
```python
if eth_qty == 0:
    if eth_slippage_bps >= Decimal(999999):
        skip_reason.append(f"ETH order size too small for exchange minimum")
    else:
        skip_reason.append(f"ETH slippage {eth_slippage_bps:.1f} bps > 10 bps threshold")
if sol_qty == 0:
    if sol_slippage_bps >= Decimal(999999):
        skip_reason.append(f"SOL order size too small for exchange minimum")
    else:
        skip_reason.append(f"SOL slippage {sol_slippage_bps:.1f} bps > 10 bps threshold")
```

**Location 2**: Lines 557-563 (IOC mode)

**Current Code**:
```python
if eth_qty == 0:
    skip_reason.append(f"ETH slippage {eth_slippage_bps:.1f} bps > 10 bps threshold")
if sol_qty == 0:
    skip_reason.append(f"SOL slippage {sol_slippage_bps:.1f} bps > 10 bps threshold")
```

**Required Change**: (Same as POST_ONLY mode)
```python
if eth_qty == 0:
    if eth_slippage_bps >= Decimal(999999):
        skip_reason.append(f"ETH order size too small for exchange minimum")
    else:
        skip_reason.append(f"ETH slippage {eth_slippage_bps:.1f} bps > 10 bps threshold")
if sol_qty == 0:
    if sol_slippage_bps >= Decimal(999999):
        skip_reason.append(f"SOL order size too small for exchange minimum")
    else:
        skip_reason.append(f"SOL slippage {sol_slippage_bps:.1f} bps > 10 bps threshold")
```

**Rationale**: 
- Distinguishes between size errors (999999) and slippage errors (actual bps value)
- Provides accurate error messages for operators
- Uses `Decimal(999999)` for consistency with Phase 1
- Uses `>=` comparison for robustness

---

## Commit Strategy

### Commit Message

```
fix: detect minimum order size violations before tick_size quantization

- Add check for raw_qty < tick_size in calculate_order_size_with_slippage()
- Return distinct error code (999999) for size vs slippage issues
- Update error messages to distinguish "size too small" from "excessive slippage"
- Fix estimate_slippage() to return error code for zero quantity

Fixes misleading "slippage 0.0 bps > threshold" error when actual issue is
order size below exchange minimum (e.g., 0.05 ETH < 0.1 tick_size).

Critical fix: Early return required to bypass error code swallowing at
lines 331-334 which would otherwise lose the error information.

Files modified:
- hedge/DN_pair_eth_sol_nado.py (lines 323-329, 411-417, 557-563)
- hedge/exchanges/nado_bookdepth_handler.py (line 183)

Tested: Verified error messages now correctly identify size vs slippage issues
```

### Files Changed

1. `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
   - Lines 323-329: Replace with minimum quantity check before quantization
   - Lines 411-417: Update POST_ONLY error messages
   - Lines 557-563: Update IOC error messages

2. `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`
   - Line 183: Return error code for zero quantity

---

## Risk Analysis

### Potential Issues

1. **Breaking existing callers**: Function signature unchanged, but error code path changed
   - **Mitigation**: Check all callers already handle `qty=0` case (they do - lines 409, 555)

2. **Error code collision**: Using 999999 for both "no liquidity" and "size too small"
   - **Mitigation**: Acceptable - both mean "cannot trade", error message distinguishes the reason

3. **Regression in normal operation**: When `raw_qty >= tick_size`, behavior should be unchanged
   - **Mitigation**: New check only triggers when `raw_qty < tick_size` (error case anyway)

4. **Edge case**: What if `raw_qty == tick_size` exactly?
   - **Mitigation**: `raw_qty >= tick_size` passes through to normal logic (correct behavior)

### Testing Considerations

1. **Test Case 1**: Small notional ($100) with high price (ETH $3000)
   - Input: `target_notional=100, price=3000, tick_size=0.1`
   - Expected: `raw_qty=0.0333 < 0.1` → early return with slippage=999999
   - Result: Error message "size too small"

2. **Test Case 2**: Large notional ($1000) with normal price (ETH $3000)
   - Input: `target_notional=1000, price=3000, tick_size=0.1`
   - Expected: `raw_qty=0.333 >= 0.1` → normal slippage estimation
   - Result: Normal operation (regression test)

3. **Test Case 3**: SOL with small notional ($10, price $100)
   - Input: `target_notional=10, price=100, tick_size=0.01`
   - Expected: `raw_qty=0.1 >= 0.01` (SOL tick smaller)
   - Result: Normal operation

4. **Test Case 4: Boundary case**: `raw_qty == tick_size`
   - Input: `target_notional=300, price=3000, tick_size=0.1`
   - Expected: `raw_qty=0.1 == 0.1` → passes check, normal quantization
   - Result: `target_qty=0.1`, normal operation

---

## Success Criteria

### Verification Steps

1. **Code Review**: 
   - Minimum quantity check placed BEFORE quantization (before line 326)
   - Error code (Decimal(999999)) used consistently for size errors
   - Both IOC and POST_ONLY paths updated
   - Early return bypasses lines 331-334 error code swallowing

2. **Unit Testing** (if available):
   - Test `raw_qty < tick_size` returns early with error code 999999
   - Test `raw_qty >= tick_size` flows through normally
   - Test error message logic distinguishes size from slippage
   - Test boundary case `raw_qty == tick_size`

3. **Integration Testing**:
   - Run bot with small notional ($100) - verify clear error message
   - Run bot with normal notional ($1000) - verify no regression
   - Check logs for accurate error descriptions

4. **Manual Verification**:
   - Error message shows "size too small" when applicable
   - Error message shows actual slippage bps when slippage is the issue
   - No more "slippage 0.0 bps > threshold" misleading messages

### Expected Behavior After Fix

**Before (Misleading)**:
```
[ORDER] SKIPPING TRADE due to insufficient liquidity: ETH slippage 0.0 bps > 10 bps threshold
```

**After (Accurate)**:
```
[SLIPPAGE] ETH order size 0.033333 < minimum 0.1 - CANNOT TRADE (notional=$100, price=$3000.00)
[ORDER] SKIPPING TRADE due to insufficient liquidity: ETH order size too small for exchange minimum
```

---

## Edge Cases and Considerations

### What to Do When Order Size is Too Small

**Current Behavior**: Skip the trade (correct)

**Question**: Should we increase the order size to meet minimum?

**Answer**: NO - This would break the notional-based strategy:
- Strategy requires same USD notional for both legs
- Increasing one leg's size would create delta imbalance
- Correct behavior is to skip and wait for better conditions (larger notional or lower price)

### Alternative Approaches Considered

1. **Round up to tick_size instead of down**
   - Rejected: Would violate notional constraint
   - Example: $100 notional would become $3000 * 0.1 = $300 notional

2. **Accumulate small orders until minimum reached**
   - Rejected: Outside scope of this fix
   - Would require significant strategy changes

3. **Use maker orders to work around size limits**
   - Rejected: POST_ONLY already used, still subject to tick_size
   - Exchange rejects orders below minimum regardless of order type

---

## Implementation Order

1. **Step 1**: Modify `estimate_slippage()` in nado_bookdepth_handler.py (line 183)
   - Change zero quantity return from 0 to Decimal(999999)
   - Lowest risk change, establishes error code convention
   - Use `Decimal(999999)` for type consistency

2. **Step 2**: Add minimum quantity check in `calculate_order_size_with_slippage()` (REPLACE lines 323-329)
   - Check `raw_qty < tick_size` BEFORE quantization
   - Return early with error code (999999) and `can_fill=False`
   - Critical: Bypasses lines 331-334 error code swallowing

3. **Step 3**: Update error messages (lines 411-417, 557-563)
   - Add conditional logic to distinguish size vs slippage errors
   - Use `Decimal(999999)` for consistency
   - Test both IOC and POST_ONLY paths

4. **Step 4**: Verify with log inspection
   - Run bot with small notional
   - Confirm error messages are accurate
   - Confirm no regression in normal operation

---

## Notes

- The `target_notional` configuration is intentionally fixed (e.g., $100) for strategy consistency
- Exchange tick sizes are fetched from SDK and are correct (ETH=0.1, SOL=0.01)
- The bug is purely in the detection and error reporting logic
- Fix maintains all existing behavior for valid order sizes
- No changes to position sizing, notional calculations, or strategy logic
- Lines 331-334 error code swallowing is the root cause of misleading messages
- Phase 2 early return is REQUIRED to bypass this problematic handler
