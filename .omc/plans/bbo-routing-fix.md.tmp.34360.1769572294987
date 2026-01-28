# BBO Routing Fix Plan

## Issues Summary

### Issue 1: BBO Level Spacing Too Large (90 USD gap)

**Root Cause**: [grvt.py:1343](grvt.py#L1343) uses `tick_size=10`
```python
current_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
```

**Effect**: 10 iterations × $0.10 = $1.00 gap per iteration → 90 USD total gap

### Issue 2: Chunk Size Too Small

**Root Cause**: [grvt.py:1348](grvt.py#L1348) uses single level size
```python
current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']
chunk_size = current_level_size  # 0.02 ETH
```

**Effect**: Never fills target (0.02 × 10 = 0.2 < 0.5 target)

---

## Fix Strategy

### Fix 1: Follow available liquidity (BBO, BBO+1, BBO+2...)

**Change**: Use BAO-based incremental pricing, not fixed 10->1 increments

```python
# grvt.py:1225 - Keep tick_size for price increments
tick_size: int = 10  # Price increment for BAO levels

# grvt.py:1343 - Calculate current price following liquidity
current_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
```

**Effect**: Follows available liquidity levels (BAO, BAO+1, BAO+2...) instead of fixed gaps

### Fix 2: Try to fill ALL remaining quantity each iteration

**Change**: In each iteration, try to place order for entire remaining quantity

```python
# grvt.py:1348-1381 - Replace chunk_size calculation
current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']

# Try to fill entire remaining quantity at current level
if current_level_size >= remaining:
    # Try to fill all remaining at current BBO level
    order_result = await self._ws_rpc_submit_order(
        symbol=contract_id,
        order_type='market',
        side=side,
        amount=remaining,  # ALL remaining quantity
        price=current_price,
        verify_with_rest=True
    )

    filled = extract_filled_quantity(order_result)
    remaining -= filled

    if remaining <= Decimal('0'):
        # Fully filled
        return order_result
    else:
        # Partial fill - move to next level and try again
        tick_offset += 1
        continue
else:
    # Not enough liquidity at current level - move to next level
    tick_offset += 1
    continue
```

**Effect**: Each iteration tries to fill entire remaining quantity, not 0.02 ETH chunks

---

## Expected Results

### Before Fix
| Metric | Value |
|--------|-------|
| BBO price gap | 90 USD |
| Chunk size | 0.02 ETH |
| Fill attempts | 10 iterations |
| Total filled | 0.2 ETH (40%) |
| Result | **FAILED** |

### After Fix
| Metric | Expected Value |
|--------|----------------|
| BBO price gap | Follows liquidity (dynamic) |
| Chunk size | Entire remaining each iteration |
| Fill attempts | 1-2 iterations max |
| Total filled | 100% (fills to target) |
| Result | **SUCCESS** |

---

## Implementation Steps

### Step 1: Keep tick_size=10 for price increments
**File**: [grvt.py:1225](grvt.py#L1225)
```python
tick_size: int = 10,  # Price increment for BAO levels
```

### Step 2: Update chunk size calculation
**File**: [grvt.py:1348-1381](grvt.py#L1348)
Replace fixed chunk_size with remaining quantity try.

### Step 3: Update DN_alternate_backpack_grvt.py
**Files**: [DN_alternate_backpack_grvt.py:909](DN_alternate_backpack_grvt.py#L909), [1109](DN_alternate_backpack_grvt.py#L1109)
Ensure `tick_size=10` is passed (or use default).
