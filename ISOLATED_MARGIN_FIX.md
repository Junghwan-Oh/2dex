# Isolated Margin Fix - Success Report

## Problem

Isolated margin orders were failing with `error_code 2006: "Insufficient account health"` despite having sufficient collateral (18,658 USDT0).

### Root Cause Analysis

The issue had two components:

1. **Missing Parameter**: `isolated_margin` was calculated but never passed to `build_appendix()`
2. **Wrong Precision**: SDK requires **x6 precision (6 decimal places)**, not x18

### Investigation Process

1. SDK source code analysis revealed:
   - `build_appendix()` encodes `isolated_margin` in **bits 127..64** of the 128-bit appendix
   - SDK expects **6 decimal places** (x6 precision)
   - For $100 margin: `isolated_margin = 100 * 10^6 = 100000000`

2. Previous attempts failed because:
   - Used plain integer (no precision scaling)
   - Used x18 precision instead of x6
   - Didn't pass `isolated_margin` parameter to `build_appendix()`

## Solution

**File**: `hedge/exchanges/nado.py:606-624`

### Before (Broken)
```python
# Calculate isolated margin: 90% of notional + 20% safety buffer
notional_value = float(str(rounded_quantity)) * float(str(order_price))
isolated_margin = int(notional_value * 0.90 * 1.2)  # Plain int (not x18 scaled)

# Build order parameters
appendix=build_appendix(
    order_type=OrderType.IOC,
    isolated=True  # isolated_margin NOT passed!
)
```

### After (Working)
```python
# Calculate isolated margin for 5x leverage (margin = notional / leverage)
# SDK requires x6 precision (6 decimal places) for isolated_margin parameter
notional_value = float(str(rounded_quantity)) * float(str(order_price))
leverage = 5.0
isolated_margin = int(notional_value / leverage * 10**6)  # x6 precision

# Build order parameters with isolated margin
appendix=build_appendix(
    order_type=OrderType.IOC,
    isolated=True,
    isolated_margin=isolated_margin  # CRITICAL: Must pass x6-precision margin
)
```

## Verification

### Test Results (3 cycles, $100 size, IOC mode)

All cycles completed successfully:

```
[DEBUG ISOLATED] notional=100.73, leverage=5.0x, margin=20.15, isolated_margin_x6=20145319
error_code=None  # No more error 2006!
status=<ResponseStatus.SUCCESS: 'success'>
```

| Cycle | Result | Leverage | Error Code |
|-------|--------|----------|------------|
| 1 | Success | 5.0x | None |
| 2 | Success | 5.0x | None |
| 3 | Success | 5.0x | None |

## Key Learnings

1. **SDK Documentation Gap**: The SDK doesn't clearly document the x6 precision requirement
2. **Bit Layout**: The 128-bit appendix field contains:
   - Bits 127..64: Isolated margin amount (x6 precision)
   - Bit 8: Isolated mode flag
   - Bits 0-7: Version

3. **Margin Calculation**:
   ```
   For 5x leverage:
   margin = notional / leverage
   isolated_margin = margin * 10^6

   Example: $100 notional, 5x leverage
   margin = 100 / 5 = $20
   isolated_margin = 20 * 10^6 = 20000000
   ```

## References

- SDK Source: `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/order.py:163-187`
- Nado API Documentation: Official docs specify x6 precision for isolated margin
- Appendix Bit Layout: Isolated margin encoded in upper 64 bits of 128-bit appendix

## Status

- ✅ Isolated margin working with 5x leverage
- ✅ Error 2006 resolved
- ✅ Tested with 3 cycles, all successful
- ✅ BUILD/UNWIND both using isolated margin
