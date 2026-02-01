# Nado Protocol SDK price_increment_x18 Research Report

**Date**: 2025-02-01
**Research Goal**: Investigate nado_protocol SDK price_increment_x18 values for ETH contract 4 and SOL contract 8

---

## Executive Summary

**ROOT CAUSE IDENTIFIED**: ETH trading fails with Error 2000 because the code uses a hardcoded tick size of 0.0001, but the actual exchange tick size is 0.1 - a **1000x mismatch**.

---

## Research Findings

### Stage 1: SDK Location and Structure

**SDK Installation**: `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/`

**Key Files**:
- `engine_client/types/models.py` - Defines `ProductBookInfo` with `price_increment_x18` field
- `engine_client/execute.py` - Uses `round_x18()` for order price rounding
- `utils/math.py` - Defines `round_x18(x, y) = x - (x % y)` (floor to nearest multiple)

### Stage 2: API vs Hardcoded Values

| Source | ETH price_increment_x18 | ETH Decimal | SOL price_increment_x18 | SOL Decimal |
|--------|------------------------|-------------|-------------------------|-------------|
| **Exchange API** (authoritative) | 10^17 | **0.1** | Unknown | Unknown |
| **Hardcoded in code** | 10^14 | 0.0001 | 10^16 | 0.01 |
| **Mismatch** | 1000x | ❌ | Unknown | ⚠️ |

### Stage 3: Exchange Contract Specifications

**ETH-PERP (Contract 4)**:
- Actual tick size from API: **0.1**
- Industry standard: ETH-PERP typically uses 0.1 tick size
- For ETH at ~$2500: 0.1 tick = 0.004% granularity (reasonable)

**SOL-PERP (Contract 8)**:
- Hardcoded value: 0.01
- API value: Not verified in this research
- Orders succeed, suggesting 0.01 may be correct

### Stage 4: Root Cause Analysis

**THE BUG**:

1. **Line 1122** (correct):
   ```python
   self.config.tick_size = Decimal(str(from_x18(tick_size_x18)))  # Sets 0.1 for ETH
   ```

2. **Lines 754-759** (incorrect):
   ```python
   # Hardcoded values IGNORE config.tick_size!
   price_increments = {
       4: Decimal("0.0001"),  # ETH - WRONG! Should be 0.1
       8: Decimal("0.01"),     # SOL
   }
   ```

**Impact**: Prices are rounded to 0.0001 increments, but exchange validates against 0.1 increments → Error 2000

---

## Recommendations

### Immediate Fix

1. **Remove hardcoded values** in `_round_price_to_increment()` (lines 754-762)
2. **Use `self.config.tick_size`** which is already correctly fetched from API
3. **Work in x18 space** throughout price calculation to avoid float precision loss

### Code Changes Required

```python
# BEFORE (broken)
def _round_price_to_increment(self, product_id: int, price: Decimal) -> Decimal:
    price_increments = {
        4: Decimal("0.0001"),  # WRONG!
        8: Decimal("0.01"),
    }
    price_increment = price_increments.get(product_id, Decimal("0.0001"))
    return (price / price_increment).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * price_increment

# AFTER (fixed)
def _round_price_to_increment(self, product_id: int, price: Decimal) -> Decimal:
    # Use API-fetched value already stored in config
    return self.round_to_tick(price)  # Uses self.config.tick_size
```

### For place_ioc_order

The x18 space calculation approach in `.omc/plans/eth-price-rounding-fix.md` is correct:
- Convert BBO to x18 directly
- Apply slippage using integer arithmetic
- Use `self.config.tick_size` converted to x18 for rounding
- Validate divisibility before submission

---

## Verification

**ETH API Value**:
```
price_increment_x18 = 100000000000000000 (10^17)
10^17 / 10^18 = 0.1 decimal ✓
```

**SOL Status**: Orders succeed, suggesting hardcoded 0.01 may match API value (needs verification)

---

## Conclusion

The ETH trading failure is caused by a 1000x mismatch between hardcoded tick size (0.0001) and actual exchange tick size (0.1). The code correctly fetches the API value but ignores it in the critical rounding function.

**Priority**: CRITICAL - Blocks all ETH trading

**Complexity**: LOW - Simple fix to use already-available API value

**Risk**: LOW - SOL continues working; ETH currently broken anyway
