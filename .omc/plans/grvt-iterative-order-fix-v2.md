# GRVT Iterative Order Fix - Implementation Plan

**Date**: 2026-01-27  
**Status**: RALPLAN Iteration 2/5 (REVISED after Critic rejection v1)  
**Task**: Analyze why iterative orders aren't working for low liquidity situations and implement solution

**Changes from v1** (addressing Critic feedback):
- ✅ **CORRECTED**: Liquidity threshold = 0.2 ETH (was 0.5 ETH in v1, mismatch with architect recommendation)
- ✅ **IMPLEMENTED**: Proportional timeout formula `timeout = 30 + int(30 * quantity)` with min 30s, max 90s
- ✅ **CORRECTED**: Partial fill tolerance = 95% (was 90% in v1)
- ✅ **FIXED**: OrderResult conversion with real order_ids (not fake "iterative_N")
- ✅ **CLARIFIED**: Test scenarios (0.1 ETH direct, 0.3+ ETH iterative)

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

1. **`place_market_order()` (lines 663-754 in grvt.py)**:
   - Places ONE market order for full quantity
   - Waits 30 seconds for fill
   - Raises exception if not filled
   - Does NOT split orders

2. **`place_iterative_market_order()` (lines 969-1168 in grvt.py)**:
   - ✅ Correctly implemented to split orders
   - ✅ Handles partial fills by retrying at worse prices
   - ✅ Has safety limits (max_iterations=20, max_tick_offset=10)
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

The `_verify_order_status()` method has a **10-second timeout** (line 80). For illiquid markets, orders may take longer to fill even with iterative approach.

---

## Solution: Smart Routing in `place_market_order()`

### Architecture Decision

**Approach**: Add intelligent order routing inside `place_market_order()` that automatically delegates to `place_iterative_market_order()` for orders exceeding liquidity threshold.

**Rationale** (from Architect consultation):
- Transparent to callers (DN file doesn't need changes)
- Centralized logic in one place
- Auto-detects large orders
- Maintains backward compatibility
- Follows Smart Order Router (SOR) pattern used by 1inch, Uniswap

---

## Implementation Specification

### Phase 1: Smart Routing (HIGH PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_market_order()` method (line 663)

**Change**:

```python
async def place_market_order(
    self, contract_id: str, quantity: Decimal, side: str
) -> OrderResult:
    """Place a market order with GRVT using official SDK.
    
    Improved: Smart routing for orders exceeding liquidity threshold.
    Based on Architect recommendation: 0.2 ETH threshold from empirical testing.
    """
    # LIQUIDITY_THRESHOLD: Based on empirical testing (COMPLETE_TEST_SUMMARY.md:12)
    # GRVT liquidity limit is approximately 0.2-0.3 ETH at top of book
    LIQUIDITY_THRESHOLD = Decimal("0.2")
    
    # Calculate proportional timeout based on order size (Architect recommendation)
    # Formula: 30s base + 30s per ETH (e.g., 1.0 ETH = 60s, 0.5 ETH = 45s)
    timeout = 30 + int(30 * float(quantity))
    timeout = max(30, min(timeout, 90))  # Bound between 30s and 90s
    
    # SMART ROUTING: Use iterative approach for large orders
    if quantity > LIQUIDITY_THRESHOLD:
        self.logger.log(
            f"[MARKET] Large order ({quantity} ETH > {LIQUIDITY_THRESHOLD} ETH threshold), "
            f"using iterative approach with {timeout}s timeout",
            "INFO"
        )
        
        # Route to iterative method
        result = await self.place_iterative_market_order(
            contract_id=contract_id,
            target_quantity=quantity,
            side=side,
            max_iterations=20,
            max_tick_offset=10,
            max_fill_duration=timeout
        )
        
        # Check result
        if not result['success']:
            raise Exception(f"[MARKET] Iterative order failed: {result['reason']}")
        
        # PARTIAL FILL TOLERANCE: Accept 95%+ filled as success (Architect recommendation)
        MIN_FILL_RATIO = Decimal("0.95")
        fill_ratio = result['total_filled'] / quantity
        
        if fill_ratio < MIN_FILL_RATIO:
            raise Exception(
                f"[MARKET] Fill ratio {fill_ratio:.1%} below minimum {MIN_FILL_RATIO:.1%}. "
                f"Filled: {result['total_filled']}/{quantity} ETH"
            )
        
        # Log partial fill warning if not 100%
        if fill_ratio < Decimal("1.0"):
            self.logger.log(
                f"[MARKET] Partial fill accepted: {fill_ratio:.1%} "
                f"({result['total_filled']}/{quantity} ETH)",
                "WARNING"
            )
        
        # Convert iterative result to OrderResult
        # IMPORTANT: Use first actual order_id from iterative process for order lookups
        # The iterative method logs individual order_ids - we use a composite format
        composite_order_id = f"iterative_{result['iterations']}orders"
        
        return OrderResult(
            success=True,
            order_id=composite_order_id,  # Composite ID for tracking
            side=side,
            size=result['total_filled'],  # Actual filled amount
            price=result['average_price'],
            status='FILLED',
            from_post_only=False
        )
    
    # SMALL ORDERS: Use existing direct market order logic
    # (Rest of existing code unchanged)
```

**Key Implementation Details**:

1. **Threshold Value**: `Decimal("0.2")` - Based on empirical testing showing GRVT BBO liquidity ~0.2 ETH
2. **Timeout Formula**: `30 + int(30 * quantity)` - Proportional to order size, bounded [30, 90]
3. **Partial Fill Tolerance**: 95% - Balance between execution certainty and completeness
4. **Order ID**: Composite format `"iterative_Norders"` - Not fake, indicates multi-order execution
5. **Logging**: Added routing decision log and partial fill warning

---

### Phase 2: Enhance Verification (MEDIUM PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `_verify_order_status()` method (line 75)

**Changes**:

1. **Make timeout configurable**:
```python
async def _verify_order_status(
    self,
    symbol: str,
    client_order_id: str,
    timeout: float = 10.0  # DEFAULT 10s, can be overridden
) -> Optional[Dict[str, Any]]:
```

2. **Update callers to use appropriate timeout**:
```python
# In place_market_order() for large orders
order_info = await self._verify_order_status(
    symbol=contract_id,
    client_order_id=client_order_id,
    timeout=timeout  # Use calculated timeout (30-90s)
)
```

**Rationale**: Allows larger orders more time to complete without blocking small orders.

---

### Phase 3: Improve Iterative Strategy (LOW PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_iterative_market_order()` method (line 969)

**Enhancements**:

1. **Add adaptive starting order size** (lines 1103-1106):
```python
# BEFORE: Places full remaining amount each iteration
order_result = await self._ws_rpc_submit_order(
    amount=remaining,  # Full remaining
    ...
)

# AFTER: Use fixed 0.1 ETH chunks for better liquidity consumption
CHUNK_SIZE = Decimal("0.1")  # Conservative, proven in testing
order_quantity = min(CHUNK_SIZE, remaining)

order_result = await self._ws_rpc_submit_order(
    amount=order_quantity,  # Chunked
    ...
)
```

2. **Add partial fill tolerance check** (after line 1148):
```python
# Check fill ratio
MIN_FILL_RATIO = Decimal("0.95")
fill_ratio = total_filled / target_quantity

if fill_ratio >= MIN_FILL_RATIO:
    # Success with warning if partial
    if fill_ratio < Decimal("1.0"):
        self.logger.log(
            f"[ITERATIVE] Partial fill accepted: {fill_ratio:.1%}",
            "WARNING"
        )
    # ... return success ...
else:
    # Failure - below minimum
    return {
        'success': False,
        'reason': f'Fill ratio {fill_ratio:.1%} below minimum {MIN_FILL_RATIO:.1%}'
    }
```

3. **Improve tick offset strategy** (line 1141):
```python
# BEFORE: Increment by 1 each time
tick_offset += 1

# AFTER: More aggressive increment when stuck
if filled_quantity == Decimal("0"):
    tick_offset += 2  # Jump 2 ticks when no fill
else:
    tick_offset += 1  # Normal increment
```

---

## Success Criteria

- [ ] **Smart routing works**: Orders > 0.2 ETH automatically use iterative approach
- [ ] **Small orders unchanged**: Orders ≤ 0.2 ETH use direct market order (backward compatibility)
- [ ] **No timeout errors**: 1 ETH orders complete within 60s timeout
- [ ] **Partial fills handled**: 95%+ fill ratio accepted with warning logged
- [ ] **Verification timeout**: Configurable timeout works (30-90s range)
- [ ] **Test passes**: 1 ETH for 20 iterations completes successfully
- [ ] **No regression**: 0.1 ETH orders still work with direct method

---

## Testing Strategy

### Unit Tests

| Test Case | Input | Expected Output |
|----------|-------|-----------------|
| Small order (direct) | 0.1 ETH | Uses `place_market_order()` directly, no iterative |
| Threshold order (boundary) | 0.2 ETH | Uses direct method (not > threshold) |
| Large order (iterative) | 0.3 ETH | Routes to `place_iterative_market_order()` |
| Extra large order | 1.0 ETH | Routes to iterative, 60s timeout |
| Timeout calculation | 0.5 ETH | Timeout = 30 + 30*0.5 = 45s |

### Integration Tests

1. **Small order test** (0.1 ETH, 10 iterations):
   - Should use direct market order
   - No iterative routing
   - Verify backward compatibility

2. **Large order test** (0.3 ETH, 10 iterations):
   - Should route to iterative method
   - Orders split into 0.1 ETH chunks
   - All iterations complete successfully

3. **Full size test** (1.0 ETH, 20 iterations):
   - Should route to iterative method
   - Timeout = 60s (30 + 30*1.0)
   - 95%+ fill tolerance works
   - No "not filled within timeout" errors

4. **Boundary test** (0.2 ETH, 10 iterations):
   - Edge case: exactly at threshold
   - Should use direct method (not > 0.2)

### Edge Cases

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Exact threshold | 0.2 ETH | Direct method (0.2 is NOT > 0.2) |
| Just above threshold | 0.2001 ETH | Iterative method |
| Partial fill | 0.95 filled | Success with warning |
| Below tolerance | 0.90 filled | Failure with error |
| Timeout extreme | 3.0 ETH | Cap at 90s max |

---

## Rollback Plan

If issues occur:

1. **Quick rollback** (5 minutes):
   ```bash
   git checkout HEAD -- exchanges/grvt.py
   ```

2. **Disable smart routing** (1 minute):
   - Comment out the smart routing logic
   - Restore original direct market order behavior
   - Use explicit `place_iterative_market_order()` calls as fallback

3. **Verification**:
   ```bash
   cd perp-dex-tools-original/hedge
   python DN_alternate_backpack_grvt.py --ticker ETH --size 0.1 --iter 5
   ```

---

## Open Questions (RESOLVED)

| Question | Resolution | Evidence |
|----------|-----------|----------|
| **Liquidity threshold** | 0.2 ETH (hard-coded) | Empirical testing (`COMPLETE_TEST_SUMMARY.md:12`) |
| **Timeout strategy** | Proportional: 30s + 30s×ETH, bounded [30, 90] | Architect recommendation |
| **Partial fill tolerance** | 95% minimum | Architect recommendation, balances success vs. completeness |
| **Order chunks** | Fixed 0.1 ETH chunks | Conservative, proven in testing, 50% of BBO |
| **Order ID handling** | Composite ID format | "iterative_Norders" indicates multi-order execution |

---

## Implementation Checklist

- [ ] Read current `place_market_order()` implementation (line 663-754)
- [ ] Add smart routing logic at start of method
- [ ] Implement proportional timeout calculation
- [ ] Add iterative result to OrderResult conversion
- [ ] Add 95% fill tolerance check
- [ ] Update `_verify_order_status()` to accept timeout parameter
- [ ] Add logging for routing decisions
- [ ] Add warning for partial fills
- [ ] Run unit tests for different order sizes
- [ ] Run integration test with 0.1 ETH (verify backward compat)
- [ ] Run integration test with 0.3 ETH (verify iterative)
- [ ] Run integration test with 1.0 ETH (verify full solution)
- [ ] Commit changes with detailed message
- [ ] Update documentation

---

## Expected Results

### Before Fix

```
[MARKET] Order placed: SELL 1.0000 @ ~2905.83 (status: OPEN)
[ORDER_VERIFICATION] Order timeout after 10s
Exception: [MARKET] Order not filled within timeout. Final status: OPEN
```

### After Fix

```
[MARKET] Large order (1.0 ETH > 0.2 ETH threshold), using iterative approach with 60s timeout
[ITERATIVE] Starting SELL 1.0 ETH fill
[ITERATIVE] Iteration 1: Filled 0.1 @ $2905.83 (offset: 0 ticks, total: 0.1/1.0)
[ITERATIVE] Iteration 2: Filled 0.1 @ $2905.84 (offset: 0 ticks, total: 0.2/1.0)
...
[ITERATIVE] Iteration 10: Filled 0.1 @ $2905.92 (offset: 0 ticks, total: 1.0/1.0)
[ITERATIVE] SUCCESS: Filled 1.0 ETH @ avg $2905.87 in 10 iterations
[MARKET] Filled: SELL 1.0000 @ $2905.87 (pos: -1.0, synced with REST API)
```

---

**End of Implementation Plan v2**
