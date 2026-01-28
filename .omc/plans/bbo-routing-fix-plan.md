# BBO Routing Fix Plan

## Issues Identified

### Issue 1: BBO Level Spacing Too Large (90 USD gap)

**Location**: [grvt.py:1343](grvt.py#L1343)
**Current**: `tick_size=10` creates $0.10 increments per level
**Effect**: 10 iterations × $0.10 = $1.00 gap per iteration → 90 USD total gap

### Issue 2: Chunk Size Too Small

**Location**: [grvt.py:1348](grvt.py#L1348)
**Current**: Uses single level size (0.02 ETH)
**Effect**: Never fills target quantity (0.5 ETH)

---

## Fix Strategy

### Fix 1: Reduce BBO Level Spacing

**Option A: Use market price decimals**
- Set `tick_size=1` for 1 cent increments
- 10 iterations × $0.01 = $0.10 gap per iteration → 10 USD total gap

**Option B: Calculate dynamic increments**
- Use order book price spread as increment
- More adaptive pricing

**Decision**: Use `tick_size=1` (1 cent) as it provides good balance between speed and cost

### Fix 2: Use Cumulative Depth for Chunks

**Current Logic**:
```python
current_level_size = bbo['best_ask_size']  # Single level
chunk_size = current_level_size  # 0.02 ETH
```

**New Logic**:
```python
# Use cumulative size from price_levels
if side == 'buy':
    for level in price_levels:
        if level['cumulative'] >= remaining:
            chunk_size = remaining
            break
else:
    for level in reversed(price_levels):
        if level['cumulative'] >= remaining:
            chunk_size = remaining
            break
```

This ensures the first iteration tries to fill the entire remaining quantity at the current BBO level.

---

## Implementation Steps

### Step 1: Update `place_iterative_market_order` signature

**File**: [grvt.py:1218](grvt.py#L1218)

```python
# OLD
async def place_iterative_market_order(
    self,
    contract_id: str,
    target_quantity: Decimal,
    side: str,
    max_iterations: int = 20,
    max_slippage_bps: int = 5,
    tick_size: int = 10,  # Too large
) -> dict:

# NEW
async def place_iterative_market_order(
    self,
    contract_id: str,
    target_quantity: Decimal,
    side: str,
    max_iterations: int = 20,
    max_slippage_bps: int = 5,
    tick_size: int = 1,  # Reduced from 10 to 1 (1 cent increments)
) -> dict:
```

### Step 2: Update price calculation in BBO loop

**File**: [grvt.py:1343-1345](grvt.py#L1343)

```python
# OLD
if side == 'buy':
    current_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
else:
    current_price = bbo['best_bid_price'] + (Decimal(tick_size) * Decimal(tick_offset))

# NEW - Use BBO price levels from analyze_order_book_depth
# The price_levels array already has the sorted prices with cumulative sizes
# Just reference the current level's price directly
```

### Step 3: Update chunk size calculation

**File**: [grvt.py:1348-1381](grvt.py#L1348)

```python
# OLD
current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']

# NEW - Use cumulative depth
price_levels = analysis['price_levels']
chunk_size = Decimal('0')

if side == 'buy':
    for level in price_levels:
        if level['cumulative'] >= remaining:
            chunk_size = remaining
            current_price = level['price']
            break
else:
    for level in reversed(price_levels):
        if level['cumulative'] >= remaining:
            chunk_size = remaining
            current_price = level['price']
            break
```

### Step 4: Update DN_alternate_backpack_grvt.py signature

**File**: [DN_alternate_backpack_grvt.py:909, 1109](DN_alternate_backpack_grvt.py#L909)

```python
# OLD
result = await self.hedge_client.place_iterative_market_order(
    ...,
    tick_size=10  # V4 signature - too large
)

# NEW
result = await self.hedge_client.place_iterative_market_order(
    ...,
    tick_size=1  # 1 cent increments
)
```

---

## Expected Results

### Before Fix
| Metric | Value |
|--------|-------|
| BBO price gap | 90 USD (over 10 iterations) |
| Chunk size | 0.02 ETH |
| Total iterations | 10+ |
| Fill rate | Failed (0.02 × 10 = 0.2 < 0.5 target) |

### After Fix
| Metric | Expected Value |
|--------|----------------|
| BBO price gap | 10 USD (over 10 iterations, 1 cent increments) |
| Chunk size | 0.5 ETH (entire remaining) |
| Total iterations | 1-2 |
| Fill rate | 100% (fills in 1 iteration at BBO) |

---

## Acceptance Criteria

- [ ] BBO level spacing uses `tick_size=1` (1 cent increments)
- [ ] First iteration places full remaining quantity at current BBO level
- [ ] Total price gap over max_iterations is <= 10 USD
- [ ] Test with 0.5 ETH target: fills in 1 iteration at BBO
- [ ] Test with 2 ETH target: fills in 1-2 iterations with reasonable slippage

---

## Testing Plan

1. Test with 0.5 ETH: Should fill at current BBO level in 1 iteration
2. Test with 2 ETH: Should fill first 0.5 at BBO, then remaining at level 1
3. Verify price gap is <= 10 USD over max_iterations
4. Verify fill rate is 100%

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Orders may cross spread | Use POST_ONLY mode for limit orders |
| Small accounts may not have deep liquidity | Check `check_grvt_liquidity()` before placing |
| Fills too slow | Increase `max_iterations` if needed |

---

## References

- Test output: [V4_MERGE_TEST_REPORT.md](perp-dex-tools-original/hedge/V4_MERGE_TEST_REPORT.md#소요-시간-분석)
- Code location: [exchanges/grvt.py:1218-1433](exchanges/grvt.py#L1218-L1433)