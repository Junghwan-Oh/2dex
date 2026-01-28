# GRVT Iterative Order Fix - Implementation Plan v4

**Date**: 2026-01-27
**Status**: RALPLAN Iteration 4/5 (REVISED after Critic rejection v3)
**Task**: Implement smart routing to iterative orders for large orders on GRVT

## What Changed in v4

**Addressing Critic v3 feedback on FIND/REPLACE precision issues**:

1. **Conceptual over literal**: Describe WHAT to change, not exact line patterns
2. **Signature-based identification**: Use function/class signatures for location
3. **Verification steps**: Add post-change verification for each modification
4. **Explicit insertion points**: Clearly state WHERE to insert code
5. **Safeguard logic**: Add fallback/error handling for edge cases
6. **Implementation-focused**: Structure as executable tasks, not patterns

**Key principle**: Let the executor verify patterns, don't specify exact text matches.

---

## Root Cause Analysis (UNCHANGED)

### Problem Statement

Market orders for large quantities (1 ETH) on GRVT are:
1. ✅ Successfully placing (status: OPEN)
2. ❌ Not filling within timeout period
3. ❌ Causing bot to fail with "Order not filled within timeout" error

### Why Iterative Orders Aren't Working

**Issue**: `place_iterative_market_order()` exists but is **NOT being called**.

**Evidence**:

1. **`place_market_order()` (lines 663-754)**:
   - Places ONE market order for full quantity
   - Waits 30 seconds for fill
   - Does NOT split orders

2. **`place_iterative_market_order()` (lines 969-1172)**:
   - ✅ Correctly implemented to split orders
   - ✅ Handles partial fills by retrying at worse prices
   - ❌ **NEVER CALLED** in the failing hedge order flow

3. **Hedge order placement** calls `place_market_order()` directly:
   - No logic to check order size
   - No fallback to `place_iterative_market_order()`

---

## Implementation Specification v4

### Phase 1: Smart Routing in `place_market_order()` (HIGH PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Method**: `place_market_order()` (starts at line 663)

#### Task 1.1: Add Smart Routing Logic at Method Entry

**WHAT to do**:
Insert routing logic at the START of `place_market_order()` method, immediately after the docstring and any initial comments, BEFORE any existing logic.

**HOW to identify the location**:
- Find the method signature: `async def place_market_order(self, contract_id: str, quantity: Decimal, side: str) -> OrderResult:`
- The docstring starts with: `"""Place a market order with GRVT using official SDK.`
- Insert the new code AFTER the docstring block ends

**CODE TO INSERT**:
```python
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
```

**VERIFICATION STEP**:
After insertion, verify:
- The code is inserted AFTER the docstring, BEFORE existing logic
- There's a comment indicating small orders continue below
- Indentation matches the method (4 spaces per level)

---

#### Task 1.2: Update Timeout in Direct Market Order Path

**WHAT to do**:
Modify the timeout calculation in the polling loop to use the same proportional formula.

**HOW to identify the location**:
- Find the polling loop that waits for order fill
- Look for: `while order_status in ["PENDING", "OPEN"] and time.time() - start_time < timeout:`
- Just before this loop, find: `timeout = 30  # 30 seconds timeout for market order`

**CHANGE TO MAKE**:
Replace the fixed `timeout = 30` line with:
```python
        # Calculate proportional timeout for consistency with iterative routing
        timeout = 30 + int(30 * float(quantity))
        timeout = max(30, min(timeout, 90))  # Bound between 30s and 90s
        start_time = time.time()
```

**VERIFICATION STEP**:
After change, verify:
- Timeout is calculated dynamically based on quantity
- The formula matches the iterative routing formula
- Bounds are applied (30s minimum, 90s maximum)

---

### Phase 2: Store Iterative Order IDs (MEDIUM PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

#### Task 2.1: Add Instance Variable in `__init__`

**WHAT to do**:
Add an instance variable to track order IDs from iterative executions.

**HOW to identify the location**:
- Find the `__init__` method: `def __init__(self, config: Dict[str, Any]):`
- Look for existing instance variables (lines starting with `self._`)
- Find the last instance variable initialization before the method calls

**WHERE to insert**:
- After the last `self._` variable assignment
- Before the `self._initialize_grvt_clients()` call
- The location is around line 58, after `self._sync_interval = 1`

**CODE TO INSERT**:
```python
        # Track order IDs from iterative executions for debugging/lookup
        self._last_iterative_order_ids: List[str] = []
```

**VERIFICATION STEP**:
After insertion, verify:
- Variable is initialized as empty list
- Type hint is correct (List[str])
- Location is before any method calls that might use it

---

#### Task 2.2: Store Order IDs During Iterative Execution

**WHAT to do**:
Store each order ID when an iterative order is placed.

**HOW to identify the location**:
- Find the `place_iterative_market_order()` method
- Inside the main while loop, find where orders are placed
- Look for the call to `self._ws_rpc_submit_order()`
- After the order is placed, find where metadata is extracted

**WHERE to insert**:
- After this line: `client_order_id = metadata.get("client_order_id")`
- This is inside the while loop, around line 1098

**CODE TO INSERT**:
```python
                # Store order ID for tracking
                self._last_iterative_order_ids.append(client_order_id)
```

**VERIFICATION STEP**:
After insertion, verify:
- Code is inside the while loop
- Code is after client_order_id is extracted
- Order ID is appended to the list (not overwritten)

---

### Phase 3: Improve Iterative Order Strategy (LOW PRIORITY)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Method**: `place_iterative_market_order()`

#### Task 3.1: Use Fixed Chunk Size for Orders

**WHAT to do**:
Replace the strategy of placing the full remaining amount with a fixed chunk size.

**HOW to identify the location**:
- In `place_iterative_market_order()` method
- Inside the while loop
- Find the call to `await self._ws_rpc_submit_order()`
- Look for the `amount` parameter

**WHERE to make the change**:
- Before the `_ws_rpc_submit_order()` call
- Around line 1079-1083

**CHANGE TO MAKE**:
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
                    verify_with_rest=True
                )
```

**VERIFICATION STEP**:
After change, verify:
- CHUNK_SIZE is defined as 0.1 ETH
- order_quantity uses min(CHUNK_SIZE, remaining)
- The amount parameter uses order_quantity, not remaining

---

#### Task 3.2: Add Partial Fill Tolerance Check

**WHAT to do**:
Add a check before the final return to accept 95%+ fill ratio as success.

**HOW to identify the location**:
- At the end of `place_iterative_market_order()` method
- Find the fallback return statement: `# Should not reach here, but just in case`
- This is around line 1164

**WHAT TO REPLACE**:
Replace the entire fallback return block with:

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

**VERIFICATION STEP**:
After replacement, verify:
- MIN_FILL_RATIO is 0.95 (95%)
- Success case returns success=True
- Failure case returns success=False with reason
- Local position is updated on success

---

#### Task 3.3: Improve Tick Offset Strategy

**WHAT to do**:
Make the tick offset increment more aggressive when orders don't fill at all.

**HOW to identify the location**:
- In `place_iterative_market_order()` method
- After checking if `filled_quantity < remaining`
- Look for: `tick_offset += 1`
- This is around line 1146

**WHAT TO REPLACE**:
Replace the simple increment with:

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

**VERIFICATION STEP**:
After replacement, verify:
- Zero fill triggers += 2 increment
- Partial fill triggers += 1 increment
- Debug logging shows the new tick offset value

---

## Success Criteria (UNCHANGED)

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

## Testing Strategy (UNCHANGED)

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
   cd perp-dex-tools-original/hedge
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

## Rollback Plan (UNCHANGED)

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

### Phase 1 - Smart Routing
- [ ] Locate `place_market_order()` method (line 663)
- [ ] Identify docstring end location
- [ ] Insert smart routing logic (threshold check, timeout calc, routing)
- [ ] Verify insertion point is correct (after docstring, before existing logic)
- [ ] Locate polling loop timeout calculation
- [ ] Replace fixed timeout with proportional formula
- [ ] Verify timeout formula matches iterative routing

### Phase 2 - Order ID Tracking
- [ ] Locate `__init__` method
- [ ] Find last instance variable initialization
- [ ] Insert `_last_iterative_order_ids` instance variable
- [ ] Locate `place_iterative_market_order()` method
- [ ] Find where client_order_id is extracted in while loop
- [ ] Insert code to append order_id to list
- [ ] Verify order_ids are tracked correctly

### Phase 3 - Iterative Improvements
- [ ] Locate `_ws_rpc_submit_order()` call in iterative method
- [ ] Add CHUNK_SIZE constant before order placement
- [ ] Replace amount=remaining with amount=order_quantity
- [ ] Verify chunking logic is correct
- [ ] Locate fallback return statement at end of method
- [ ] Replace with partial fill tolerance check
- [ ] Verify 95% threshold is implemented
- [ ] Locate tick_offset increment logic
- [ ] Replace with aggressive increment for zero fills
- [ ] Verify debug logging is added

### Testing
- [ ] Run 0.1 ETH test (verify direct method)
- [ ] Run 0.3 ETH test (verify iterative routing)
- [ ] Run 1.0 ETH test (verify full solution)
- [ ] Run 0.2 ETH test (verify boundary behavior)
- [ ] Verify no regression in existing functionality
- [ ] Check logs for routing decisions
- [ ] Verify order ID tracking works
- [ ] Confirm timeout calculations are correct

---

## Expected Results (UNCHANGED)

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

1. **Conceptual over literal**: Each task describes WHAT to change and HOW to identify the location, not exact FIND patterns
2. **Signature-based identification**: Use method/function signatures to locate code
3. **Verification steps**: Each task includes post-change verification
4. **Explicit insertion points**: Clearly state WHERE to insert code (before/after specific markers)
5. **Safeguard logic**: Error handling and edge cases are explicit
6. **Executor autonomy**: Executor verifies patterns and makes precise changes

**Why this approach works better**:
- Resilient to code formatting changes
- Focuses on intent over exact text
- Lets executor use context to make precise changes
- Includes verification for each change
- Clear success criteria for each task

---

**End of Implementation Plan v4**
