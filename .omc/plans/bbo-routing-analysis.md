# BBO Routing Analysis & Fix Plan

## Test Output Analysis

### Issues Confirmed

#### Issue 1: BBO Level Spacing (90 USD gap)
From test output log:
```
Iteration 1: Placing chunk 0.02 at 3024.31 (BBO level 0)
Iteration 2: Placing chunk 0.02 at 3014.31 (BBO level 1)  <- 10 gap
Iteration 3: Placing chunk 0.02 at 3004.31 (BBO level 2)  <- 10 gap
...
Iteration 10: Placing chunk 0.02 at 2934.31 (BBO level 9) <- 90 gap total
```

**Root Cause**: `tick_size=10` in grvt.py line 1225 creates $0.10 increments per level.

**Impact**: 90 USD price gap over 10 iterations - highly detrimental to PnL.

#### Issue 2: Chunk Size (0.02 ETH)
From test output:
```
Iteration 1: Placing chunk 0.02 at 3024.31, remaining: 0.5000
Iteration 2: Placing chunk 0.02 at 3014.31, remaining: 0.5000
...
```

**Root Cause**: Line 1348 uses single level size:
```python
current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']
```

**Impact**: Never fills target quantity (0.02 × 10 = 0.2 < 0.5 target).

---

## Root Cause Code Locations

### File: exchanges/grvt.py

#### Issue 1: tick_size parameter (line 1225)
```python
async def place_iterative_market_order(
    self,
    ...
    tick_size: int = 10,  # <-- TOO LARGE
) -> dict:
```

#### Issue 2: Price calculation (lines 1342-1345)
```python
# Uses tick_offset to create 10-cent increments
if side == 'buy':
    current_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
else:
    current_price = bbo['best_bid_price'] + (Decimal(tick_size) * Decimal(tick_offset))
```

#### Issue 3: Chunk size calculation (line 1348)
```python
# Uses single level size (0.02 ETH)
current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']
```

#### Issue 4: Default signature in DN file (lines 909, 1109)
```python
# DN_alternate_backpack_grvt.py passes tick_size=10
result = await self.hedge_client.place_iterative_market_order(
    ...,
    tick_size=10  # <-- TOO LARGE
)
```

---

## Proposed Fix

### Fix 1: Reduce tick_size from 10 to 1

**Change**: Use 1 cent increments instead of 10 cent increments

```python
# Before
tick_size: int = 10,  # 10 cents = $0.10

# After
tick_size: int = 1,  # 1 cent = $0.01
```

**Effect**: 10 iterations × $0.01 = $0.10 gap per iteration → 10 USD total gap (vs 90 USD)

### Fix 2: Use cumulative depth for chunks

**Change**: Calculate chunk size from cumulative liquidity instead of single level

```python
# Before (line 1348)
current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']
chunk_size = current_level_size  # 0.02 ETH

# After - Use price_levels from analyze_order_book_depth
price_levels = analysis['price_levels']
chunk_size = Decimal('0')

if side == 'buy':
    for level in price_levels:
        if level['cumulative'] >= remaining:
            chunk_size = remaining  # Try to fill entire remaining quantity
            current_price = level['price']
            break
else:
    for level in reversed(price_levels):
        if level['cumulative'] >= remaining:
            chunk_size = remaining
            current_price = level['price']
            break
```

**Effect**: First iteration tries to fill entire remaining quantity (0.5 ETH), not 0.02 ETH.

---

## Expected Results

### Before Fix
| Metric | Value |
|--------|-------|
| BBO price gap | 90 USD (over 10 iterations) |
| Chunk size | 0.02 ETH |
| Fill attempts | 10 iterations |
| Total filled | 0.2 ETH (40% of target) |
| Result | **FAILED** |

### After Fix
| Metric | Expected Value |
|--------|----------------|
| BBO price gap | 10 USD (over 10 iterations) |
| Chunk size | 0.5 ETH (full remaining) |
| Fill attempts | 1-2 iterations |
| Total filled | 0.5 ETH (100% of target) |
| Result | **SUCCESS** |

---

## Implementation Plan

### Step 1: Update grvt.py default tick_size
**File**: [grvt.py:1225](grvt.py#L1225)
```python
tick_size: int = 1,  # Reduced from 10
```

### Step 2: Update price calculation
**File**: [grvt.py:1342-1345](grvt.py#L1342)
Keep using `tick_offset` but now with `tick_size=1` for 1-cent increments.

### Step 3: Update chunk size calculation
**File**: [grvt.py:1348](grvt.py#L1348)
Use cumulative depth from `price_levels` instead of single level size.

### Step 4: Update DN_alternate_backpack_grvt.py
**Files**: [DN_alternate_backpack_grvt.py:909](DN_alternate_backpack_grvt.py#L909), [1109](DN_alternate_backpack_grvt.py#L1109)
Ensure `tick_size=1` is passed (or use default which will now be 1).

---

## Testing Plan

1. Test with 0.5 ETH target
   - Should fill in 1 iteration at BBO level 0
   - Price gap should be < $0.10

2. Test with 2 ETH target
   - Should fill 0.5 ETH at BBO level 0
   - Then fill remaining 1.5 ETH at level 1
   - Total price gap < $0.10

3. Verify
   - BBO level increments are 1 cent, not 10 cents
   - Chunk size matches remaining quantity (not fixed 0.02)
   - Fill rate is 100%

---

## Acceptance Criteria

- [ ] `tick_size` defaults to 1 (not 10)
- [ ] First iteration places full remaining quantity at current BBO
- [ ] BBO level price gap is <= 10 USD over max_iterations
- [ ] Test with 0.5 ETH: fills in 1 iteration
- [ ] Test with 2 ETH: fills in 1-2 iterations with reasonable slippage