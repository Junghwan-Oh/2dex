# GRVT Iterative Order Fix - Implementation Plan

**Date**: 2026-01-27  
**Status**: RALPLAN Iteration 3/5 (REVISED after Critic rejection v2)  
**Task**: Analyze why iterative orders aren't working for low liquidity situations and implement solution

**Changes from v2** (addressing Critic feedback):
- ✅ **FIXED**: Timeout implementation - exact code replacement specified
- ✅ **COMPLETED**: Phase 3 with precise insertion points (line numbers verified)
- ✅ **RESOLVED**: Order ID handling - return first real order_id, store others
- ✅ **CORRECTED**: Line number references use patterns for accuracy
- ✅ **CLARIFIED**: Verification path - two separate mechanisms identified

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

1. **`place_market_order()` (around line 663-754 in grvt.py)**:
   - Places ONE market order for full quantity
   - Waits 30 seconds for fill
   - Raises exception if not filled
   - Does NOT split orders

2. **`place_iterative_market_order()` (around line 969-1168 in grvt.py)**:
   - ✅ Correctly implemented to split orders
   - ✅ Handles partial fills by retrying at worse prices
   - ✅ Has safety limits (max_iterations=20, max_tick_offset=10)
   - ❌ **NEVER CALLED** in the failing hedge order flow

3. **Hedge order placement (around line 1177 in DN_alternate_backpack_grvt.py)**:
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

### Verification Mechanisms (IMPORTANT DISTINCTION)

**Two separate verification paths exist**:

1. **`_verify_order_status()`** (called by `_ws_rpc_submit_order()`):
   - Purpose: Verify WebSocket RPC orders via REST API
   - Has configurable timeout parameter (default 10s)
   - Used for: ALL orders placed via WebSocket RPC

2. **Direct polling loop** in `place_market_order()`:
   - Purpose: Wait for market order fill confirmation
   - Uses `get_order_info()` directly
   - Has fixed 30s timeout (line around 704)

**Key Insight**: When routing to iterative method, timeout applies to `place_iterative_market_order()`'s `max_fill_duration` parameter. The direct polling loop is NOT used for iterative orders.

---

## Implementation Specification

### Phase 1: Smart Routing in `place_market_order()` (HIGH PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_market_order()` method

**Step 1**: Add routing logic at START of method (after docstring, before any existing code)

**FIND this pattern** (near start of method):
```python
async def place_market_order(
    self, contract_id: str, quantity: Decimal, side: str
) -> OrderResult:
    """Place a market order with GRVT using official SDK."""
    # NOTE: Hard 0.2 ETH limit removed - using iterative market order approach instead
```

**REPLACE with**:
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
    
    # SMART ROUTING: Use iterative approach for large orders
    if quantity > LIQUIDITY_THRESHOLD:
        self.logger.log(
            f"[MARKET] Large order ({quantity} ETH > {LIQUIDITY_THRESHOLD} ETH threshold), "
            f"using iterative approach",
            "INFO"
        )
        
        # Calculate proportional timeout based on order size (Architect recommendation)
        # Formula: 30s base + 30s per ETH (e.g., 1.0 ETH = 60s, 0.5 ETH = 45s)
        timeout = 30 + int(30 * float(quantity))
        timeout = max(30, min(timeout, 90))  # Bound between 30s and 90s
        
        self.logger.log(f"[MARKET] Using {timeout}s timeout for {quantity} ETH order", "DEBUG")
        
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
        # IMPORTANT: Return first real order_id for compatibility with order lookups
        # Store all order_ids in instance variable for tracking
        if hasattr(self, '_last_iterative_order_ids'):
            first_order_id = self._last_iterative_order_ids[0] if self._last_iterative_order_ids else None
        else:
            first_order_id = f"iterative_{result['iterations']}orders"
        
        return OrderResult(
            success=True,
            order_id=first_order_id,
            side=side,
            size=result['total_filled'],  # Actual filled amount
            price=result['average_price'],
            status='FILLED',
            from_post_only=False
        )
    
    # SMALL ORDERS: Continue with existing direct market order logic below
    # ... (rest of existing code unchanged) ...
```

**Step 2**: Update timeout in direct market order path

**FIND this pattern** (in the while loop, after `start_time = time.time()`):
```python
# Wait for fill confirmation
start_time = time.time()
timeout = 30  # 30 seconds timeout for market order
```

**REPLACE with**:
```python
# Wait for fill confirmation
# Calculate proportional timeout for consistency with iterative routing
timeout = 30 + int(30 * float(quantity))
timeout = max(30, min(timeout, 90))  # Bound between 30s and 90s
start_time = time.time()
```

---

### Phase 2: Store Iterative Order IDs (MEDIUM PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_iterative_market_order()` method (around line 969)

**Step 1**: Add instance variable initialization in `__init__` method (if not present)

**FIND** (in `GrvtClient.__init__`):
```python
def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    # ... existing init code ...
```

**ADD after existing instance variables**:
```python
    # Track order IDs from iterative executions for debugging/lookup
    self._last_iterative_order_ids: List[str] = []
```

**Step 2**: Store order IDs during iterative execution

**FIND this pattern** (in `place_iterative_market_order()`, inside the while loop, after successful order):
```python
# Extract order info
metadata = order_result.get("metadata", {})
client_order_id = metadata.get("client_order_id")
```

**ADD immediately after**:
```python
# Store order ID for tracking
self._last_iterative_order_ids.append(client_order_id)
```

---

### Phase 3: Improve Iterative Order Strategy (LOW PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Location**: `place_iterative_market_order()` method (around line 969)

**Enhancement 1: Use fixed chunk size**

**FIND this pattern** (inside while loop, before `_ws_rpc_submit_order` call):
```python
# Place market order
try:
    order_result = await self._ws_rpc_submit_order(
        symbol=contract_id,
        order_type='market',
        side=side,
        amount=remaining,  # Full remaining amount
        ...
    )
```

**REPLACE with**:
```python
# Place market order
try:
    # IMPORTANT: Use fixed chunk size for better liquidity consumption
    # Based on testing: 0.1 ETH = 50% of GRVT BBO (0.2 ETH)
    CHUNK_SIZE = Decimal("0.1")
    order_quantity = min(CHUNK_SIZE, remaining)
    
    order_result = await self._ws_rpc_submit_order(
        symbol=contract_id,
        order_type='market',
        side=side,
        amount=order_quantity,  # Chunked, not full remaining
        ...
    )
```

**Enhancement 2: Add partial fill tolerance check**

**FIND this pattern** (near end of method, before final return):
```python
# Should not reach here, but just in case
return {
    'total_filled': total_filled,
    'total_fees': total_fees,
    'average_price': sum(price_history) / len(price_history) if price_history else None,
    'iterations': iteration,
    'success': False,
    'reason': 'Exited loop without completion'
}
```

**REPLACE with**:
```python
# Check fill ratio before returning
MIN_FILL_RATIO = Decimal("0.95")
fill_ratio = total_filled / target_quantity if target_quantity > 0 else Decimal("0")

if fill_ratio >= MIN_FILL_RATIO:
    # Success with warning if partial
    if fill_ratio < Decimal("1.0"):
        self.logger.log(
            f"[ITERATIVE] Partial fill accepted: {fill_ratio:.1%} "
            f"({total_filled}/{target_quantity} ETH)",
            "WARNING"
        )
    
    avg_price = sum(price_history) / len(price_history) if price_history else None
    self.logger.log(
        f"[ITERATIVE] SUCCESS: Filled {total_filled} ETH @ avg ${avg_price:.2f} "
        f"in {iteration} iterations"
    )
    
    # Update local position
    if side == "buy":
        self._local_position += total_filled
    else:
        self._local_position -= total_filled
    
    return {
        'total_filled': total_filled,
        'total_fees': total_fees,
        'average_price': Decimal(str(avg_price)) if avg_price else None,
        'iterations': iteration,
        'success': True
    }
else:
    # Failure - below minimum tolerance
    reason = f'Fill ratio {fill_ratio:.1%} below minimum {MIN_FILL_RATIO:.1%}'
    self.logger.log(f"[ITERATIVE] {reason}", "ERROR")
    return {
        'total_filled': total_filled,
        'total_fees': total_fees,
        'average_price': sum(price_history) / len(price_history) if price_history else None,
        'iterations': iteration,
        'success': False,
        'reason': reason
    }
```

**Enhancement 3: Improve tick offset strategy**

**FIND this pattern** (after partial fill detected):
```python
# Partial fill: increment tick offset for next attempt
if filled_quantity < remaining:
    tick_offset += 1
```

**REPLACE with**:
```python
# Partial fill: increment tick offset for next attempt
if filled_quantity < remaining:
    # More aggressive increment when completely unfilled
    if filled_quantity == Decimal("0"):
        tick_offset += 2  # Jump 2 ticks when no fill at all
        self.logger.debug(f"[ITERATIVE] No fill, increasing tick offset to {tick_offset}")
    else:
        tick_offset += 1  # Normal increment for partial fills
        self.logger.debug(f"[ITERATIVE] Partial fill, increasing tick offset to {tick_offset}")
```

---

## Success Criteria

- [ ] **Smart routing activates**: Orders > 0.2 ETH route to iterative method
- [ ] **Small orders unchanged**: Orders ≤ 0.2 ETH use direct market order
- [ ] **Proportional timeout works**: 0.5 ETH uses 45s timeout, 1.0 ETH uses 60s timeout
- [ ] **No timeout errors**: 1 ETH orders complete within calculated timeout
- [ ] **Partial fills handled**: 95%+ fill ratio accepted with warning logged
- [ ] **Order IDs tracked**: First real order_id returned, all IDs stored in instance variable
- [ ] **Chunking works**: Iterative orders use 0.1 ETH chunks instead of full remaining
- [ ] **Test passes**: 1 ETH for 20 iterations completes successfully
- [ ] **No regression**: 0.1 ETH orders still work with direct method

---

## Testing Strategy

### Unit Tests

| Test Case | Input | Expected Output |
|----------|-------|-----------------|
| Small order (direct) | 0.1 ETH | Uses direct polling loop, timeout = 33s |
| Threshold order (boundary) | 0.2 ETH | Uses direct method (0.2 is NOT > 0.2) |
| Large order (iterative) | 0.3 ETH | Routes to iterative, timeout = 39s |
| Extra large order | 1.0 ETH | Routes to iterative, timeout = 60s |
| Timeout calculation | 0.5 ETH | Timeout = 30 + 30*0.5 = 45s |
| Timeout upper bound | 3.0 ETH | Timeout capped at 90s |

### Integration Tests

1. **Small order test** (0.1 ETH, 10 iterations):
   ```bash
   python DN_alternate_backpack_grvt.py --ticker ETH --size 0.1 --iter 10
   ```
   Expected: Direct market order, no iterative routing, all cycles complete

2. **Large order test** (0.3 ETH, 10 iterations):
   ```bash
   python DN_alternate_backpack_grvt.py --ticker ETH --size 0.3 --iter 10
   ```
   Expected: Routes to iterative, 0.1 ETH chunks, all cycles complete

3. **Full size test** (1.0 ETH, 20 iterations):
   ```bash
   python DN_alternate_backpack_grvt.py --ticker ETH --size 1.0 --iter 20
   ```
   Expected: Routes to iterative, 60s timeout, 95% fill tolerance works

4. **Boundary test** (0.2 ETH, 10 iterations):
   ```bash
   python DN_alternate_backpack_grvt.py --ticker ETH --size 0.2 --iter 10
   ```
   Expected: Direct method (not > 0.2), backward compatibility

### Edge Cases

| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Exact threshold | 0.2 ETH | Direct method (0.2 is NOT > 0.2) |
| Just above threshold | 0.2001 ETH | Iterative method |
| Partial fill at 95% | 0.95 filled | Success with warning |
| Partial fill at 94% | 0.94 filled | Failure with error |
| Timeout extreme | 3.0 ETH | Timeout = min(30+30*3, 90) = 90s |
| Zero fill on first attempt | Any size | Tick offset += 2 (aggressive) |

---

## Rollback Plan

If issues occur:

1. **Quick rollback** (5 minutes):
   ```bash
   git checkout HEAD -- perp-dex-tools-original/hedge/exchanges/grvt.py
   ```

2. **Manual verification**:
   ```bash
   cd perp-dex-tools-original/hedge
   python DN_alternate_backpack_grvt.py --ticker ETH --size 0.1 --iter 5
   ```

3. **Alternative**: Use explicit iterative calls as temporary workaround:
   ```python
   # In DN file, temporarily use:
   result = await self.hedge_client.place_iterative_market_order(...)
   ```

---

## Implementation Checklist

Phase 1 - Smart Routing:
- [ ] Add liquidity threshold check (0.2 ETH)
- [ ] Calculate proportional timeout formula
- [ ] Add routing logic to call iterative method
- [ ] Add 95% fill tolerance check
- [ ] Convert iterative result to OrderResult
- [ ] Add logging for routing decisions

Phase 1 - Direct Order Timeout:
- [ ] Find and update timeout=30 line
- [ ] Replace with proportional formula
- [ ] Add min/max bounds (30s, 90s)

Phase 2 - Order ID Tracking:
- [ ] Add `_last_iterative_order_ids` instance variable
- [ ] Store order_ids during iterative execution
- [ ] Return first order_id for compatibility

Phase 3 - Iterative Improvements:
- [ ] Add CHUNK_SIZE constant (0.1 ETH)
- [ ] Replace `amount=remaining` with chunked amount
- [ ] Add MIN_FILL_RATIO check (95%)
- [ ] Add partial fill warning log
- [ ] Improve tick offset strategy (aggressive on zero fill)
- [ ] Add debug logging for tick offset changes

Testing:
- [ ] Run 0.1 ETH test (verify direct method)
- [ ] Run 0.3 ETH test (verify iterative)
- [ ] Run 1.0 ETH test (verify full solution)
- [ ] Run 0.2 ETH test (verify boundary)
- [ ] Verify no regression in existing functionality

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
[MARKET] Large order (1.0 ETH > 0.2 ETH threshold), using iterative approach
[MARKET] Using 60s timeout for 1.0 ETH order
[ITERATIVE] Starting SELL 1.0 ETH fill
[ITERATIVE] Iteration 1: Filled 0.1 @ $2905.83 (total: 0.1/1.0)
[ITERATIVE] Iteration 2: Filled 0.1 @ $2905.84 (total: 0.2/1.0)
...
[ITERATIVE] Iteration 10: Filled 0.1 @ $2905.92 (total: 1.0/1.0)
[ITERATIVE] SUCCESS: Filled 1.0 ETH @ avg $2905.87 in 10 iterations
[MARKET] Filled: SELL 1.0000 @ $2905.87 (pos: -1.0, synced with REST API)
```

---

## Key Implementation Notes

1. **Timeout applies to different places**:
   - For iterative orders: `max_fill_duration` parameter
   - For direct orders: polling loop timeout variable
   - Both use same formula: `30 + int(30 * quantity)`

2. **Order ID compatibility**:
   - Return first real order_id for lookups
   - Store all IDs in `_last_iterative_order_ids` for tracking
   - Composite format only used as fallback

3. **Verification paths remain separate**:
   - `_verify_order_status()`: Used by `_ws_rpc_submit_order()` (configurable timeout)
   - Direct polling: Used by `place_market_order()` for small orders

---

**End of Implementation Plan v3**
