# GRVT Iterative Order Fix - Implementation Plan

**Date**: 2026-01-27  
**Status**: RALPLAN Iteration 1/5  
**Task**: Analyze why iterative orders aren't working for low liquidity situations and implement solution

---

## Root Cause Analysis

### Problem Statement

Market orders for large quantities (1 ETH) on GRVT are:
1. ✅ Successfully placing (status: OPEN)
2. ❌ Not filling within timeout period
3. ❌ Causing bot to fail with "Order not filled within timeout" error

### Why Iterative Orders Aren't Working

**Issue**: `place_iterative_market_order()` exists but is **NOT being called**.

**Evidence from code analysis**:

1. **`place_market_order()` (lines 662-753 in grvt.py)**:
   - Places ONE market order for full quantity
   - Waits 30 seconds for fill
   - Raises exception if not filled
   - Does NOT split orders

2. **`place_iterative_market_order()` (lines 969-1171 in grvt.py)**:
   - ✅ Correctly implemented to split orders
   - ✅ Handles partial fills by retrying at worse prices
   - ✅ Has safety limits (max_iterations, max_tick_offset)
   - ❌ **NEVER CALLED** in the failing hedge order flow

3. **Hedge order placement (line 1177 in DN_alternate_backpack_grvt.py)**:
   ```python
   order_info = await self.hedge_client.place_market_order(
       contract_id=self.hedge_contract_id,
       quantity=quantity,  # 1.0 ETH!
       side=order_side,
   )
   ```
   - Calls `place_market_order()` directly
   - No logic to check order size
   - No fallback to `place_iterative_market_order()`

### Secondary Issue: Verification Timeout

Even if iterative orders were called, the `_verify_order_status()` method has a **10-second timeout**. For illiquid markets, orders may take longer to fill even with iterative approach.

---

## Solution Options

### Option 1: Smart Routing in `place_market_order()` (RECOMMENDED)

**Approach**: Add intelligent order routing inside `place_market_order()`

**Implementation**:
```python
async def place_market_order(self, contract_id: str, quantity: Decimal, side: str) -> OrderResult:
    # Define liquidity threshold based on testing
    LARGE_ORDER_THRESHOLD = Decimal("0.5")  # ETH
    
    # Route to iterative method for large orders
    if quantity > LARGE_ORDER_THRESHOLD:
        self.logger.log(
            f"[MARKET] Large order ({quantity} ETH), using iterative approach",
            "INFO"
        )
        result = await self.place_iterative_market_order(
            contract_id=contract_id,
            target_quantity=quantity,
            side=side,
            max_iterations=20,
            max_tick_offset=10,
            max_fill_duration=60  # Increase timeout for large orders
        )
        
        if result['success']:
            # Convert iterative result to OrderResult
            return OrderResult(
                success=True,
                order_id=f"iterative_{result['iterations']}",
                side=side,
                size=result['total_filled'],
                price=result['average_price'],
                status='FILLED',
                from_post_only=False
            )
        else:
            raise Exception(f"[MARKET] Iterative order failed: {result['reason']}")
    else:
        # Use existing direct market order logic for small orders
        # ... existing code ...
```

**Pros**:
- ✅ Transparent to callers (DN file doesn't need changes)
- ✅ Centralized logic in one place
- ✅ Auto-detects large orders
- ✅ Maintains backward compatibility

**Cons**:
- ⚠️ Need to handle different return types

### Option 2: Modify Call Sites (NOT RECOMMENDED)

**Approach**: Update every call to `place_market_order()` to check order size

**Issues**:
- ❌ Requires changes in multiple locations (DN file)
- ❌ Duplicates logic across codebase
- ❌ Easy to miss some call sites
- ❌ Less maintainable

### Option 3: Enhance Iterative Order Handling

**Approach**: Improve `place_iterative_market_order()` to handle extreme illiquidity

**Enhancements needed**:
1. **Increase verification timeout** from 10s to 30s+ for large orders
2. **Add partial fill tolerance** - accept 90%+ filled as success
3. **Improve order size calculation** - start smaller for illiquid markets
4. **Add adaptive tick offset** - increase more aggressively when stuck

**Cons**:
- Doesn't solve the main issue (method not being called)
- Should be combined with Option 1

---

## Recommended Implementation

### Phase 1: Fix Smart Routing (HIGH PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_market_order()` method (line 662)

**Change**:
1. Add liquidity threshold check at start of method
2. Route to `place_iterative_market_order()` for large orders
3. Convert iterative result to OrderResult format
4. Increase timeout for large orders (60s instead of 30s)

### Phase 2: Enhance Verification (MEDIUM PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `_verify_order_status()` method (line 75)

**Changes**:
1. Make timeout configurable (parameter with default)
2. Add support for longer timeouts (up to 60s)
3. Add logging for partial fills

### Phase 3: Improve Iterative Strategy (LOW PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_iterative_market_order()` method (line 969)

**Enhancements**:
1. Add adaptive starting order size based on quantity
2. For 1 ETH orders: start with 0.1 ETH chunks
3. Increase tick offset more aggressively
4. Add partial fill tolerance (accept 90%+ as success)

---

## Success Criteria

- [ ] Orders > 0.5 ETH automatically use iterative approach
- [ ] No "Order not filled within timeout" errors for 1 ETH orders
- [ ] Verification timeout configurable (up to 60s)
- [ ] Test passes with 1 ETH for 20 iterations
- [ ] Backward compatibility maintained (small orders still work)

---

## Testing Strategy

### Unit Tests
1. Test smart routing with different order sizes (0.1, 0.5, 1.0 ETH)
2. Test iterative result to OrderResult conversion
3. Test timeout configuration

### Integration Tests
1. Run test with 0.2 ETH (should use direct market order)
2. Run test with 1 ETH (should use iterative)
3. Run test with 10 iterations
4. Verify no timeout errors

### Edge Cases
1. Order exactly at threshold (0.5 ETH)
2. Extremely illiquid market conditions
3. Partial fills at various percentages

---

## Rollback Plan

If issues occur:
1. Remove smart routing logic from `place_market_order()`
2. Restore original direct market order behavior
3. Use explicit `place_iterative_market_order()` calls as fallback

---

## Open Questions for Architect

1. **Liquidity Threshold**: Is 0.5 ETH the right threshold? Should it be configurable?
2. **Timeout Values**: 30s for normal, 60s for iterative - appropriate?
3. **Partial Fill Tolerance**: Should we accept 90% filled as success?
4. **Order Chunks**: Should iterative start with smaller chunks (0.1 ETH) for 1 ETH orders?

---

## Implementation Order

1. ✅ **Analyze issue** (Root cause identified)
2. ⏳ **Consult Architect** (Answer open questions)
3. ⏳ **Implement Phase 1** (Smart routing)
4. ⏳ **Implement Phase 2** (Verification timeout)
5. ⏳ **Implement Phase 3** (Iterative improvements)
6. ⏳ **Test thoroughly**
7. ⏳ **Document changes**

---

**End of Implementation Plan**
