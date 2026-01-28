# GRVT SDK Research Findings

**Date**: 2026-01-26
**Purpose**: Document actual SDK capabilities for GRVT bug fix plan
**Status**: COMPLETED

---

## Research Summary

Conducted comprehensive source code inspection of GRVT SDK to determine actual capabilities for order submission, reconnection, and WebSocket order management.

### SDK Locations
- **Primary SDK**: `perp-dex-tools-original/env/Lib/site-packages/pysdk/`
- **Key Files**:
  - `grvt_ccxt_ws.py` - WebSocket implementation
  - `grvt_ccxt.py` - REST implementation
  - `grvt_ccxt_utils.py` - Utility functions
  - `grvt_ccxt_env.py` - Environment configuration

---

## Research 1: WebSocket Order Submission API

### Question: Does `GrvtCcxtWS` have `create_order()` method?

**Answer**: NO ❌

### Finding: Actual Method is `rpc_create_order()`

**File**: `pysdk/grvt_ccxt_ws.py` lines 615-639

```python
async def rpc_create_order(
    self,
    symbol: str,
    order_type: GrvtOrderType,
    side: GrvtOrderSide,
    amount: float | Decimal | str | int,
    price: Num = None,
    params={},
) -> dict:
    """
    Create an order.
    """
    FN = f"{self._clsname} rpc_create_order"
    if not self.is_endpoint_connected(GrvtWSEndpointType.TRADE_DATA_RPC_FULL):
        raise GrvtInvalidOrder("Trade data connection not available.")
    order = self._get_order_with_validations(
        symbol, order_type, side, amount, price, params
    )
    self.logger.info(f"{FN} {order=}")
    payload = get_order_rpc_payload(order, self._private_key, self.env, self.markets)
    self._request_id += 1
    payload["id"] = self._request_id
    self.logger.info(f"{FN} {payload=}")
    await self.send_rpc_message(GrvtWSEndpointType.TRADE_DATA_RPC_FULL, payload)
    return payload
```

### Also Available: `rpc_create_limit_order()`

**File**: `pysdk/grvt_ccxt_ws.py` lines 641-649

```python
async def rpc_create_limit_order(
    self,
    symbol: str,
    side: GrvtOrderSide,
    amount: float | Decimal | str | int,
    price: Num,
    params={},
) -> dict:
    return await self.rpc_create_order(symbol, "limit", side, amount, price, params)
```

### Key Characteristics

| Property | Value | Implication |
|----------|-------|-------------|
| **Method Name** | `rpc_create_order()` | NOT `create_order()` |
| **Async** | Yes | Requires async/await |
| **Return Value** | `dict` with `request_id` | Does NOT return order result |
| **Response Mechanism** | WebSocket callback | Response comes asynchronously |
| **Timeout** | None | Can hang indefinitely |
| **Connection Check** | Required | `is_endpoint_connected()` |

### How RPC Order Submission Works

1. **Send Request**:
   ```python
   payload = await ws_client.rpc_create_order(symbol="ETH-USDT-PERP", ...)
   # Returns immediately with: {"id": 123, "jsonrpc": "2.0", ...}
   ```

2. **Response via Callback**:
   - Order status updates come via WebSocket subscription
   - Must subscribe to 'order' stream
   - Match responses by `request_id`

3. **Get Order Status**:
   - Query via REST API `fetch_order()`
   - Or wait for WebSocket callback

### Why V2 Plan Failed

V2 plan assumed:
```python
# V2 ASSUMPTION (WRONG):
result = ws_client.create_order(...)  # This method doesn't exist!
```

Actual SDK:
```python
# ACTUAL SDK:
payload = await ws_client.rpc_create_order(...)  # Returns request_id
# Response comes later via callback
```

---

## Research 2: SDK Built-in Reconnect

### Question: Does SDK have auto-reconnect?

**Answer**: YES ✅

### Finding: `connect_all_channels()` Infinite Loop

**File**: `pysdk/grvt_ccxt_ws.py` lines 141-164

```python
async def connect_all_channels(self) -> None:
    """
    Connects to all channels that are possible to connect.
    If cookie is NOT available, it will NOT connect to GrvtWSEndpointType.TRADE_DATA
    For trading connection: run this method after cookie is available.
    """
    FN = "connect_all_channels"
    while True:  # <-- INFINITE LOOP
        try:
            for end_point_type in self.endpoint_types:
                if (
                    not self.is_endpoint_connected(end_point_type)
                    or self.force_reconnect_flag  # <-- FLAG TRIGGERS RECONNECT
                ):
                    await self._reconnect(end_point_type)
            all_are_connected = self.are_endpoints_connected(self.endpoint_types)
            self.logger.info(
                f"{FN} Connection status: {all_are_connected=} {self.force_reconnect_flag=}"
            )
            self.force_reconnect_flag = False  # <-- RESET FLAG
        except Exception as e:
            self.logger.exception(f"{FN} {e=}")
        finally:
            await asyncio.sleep(5)  # <-- CHECKS EVERY 5 SECONDS
```

### How SDK Reconnect Works

1. **Automatic Start**:
   - Started in `initialize()` method (line 108)
   - Runs as background task
   - Never stops

2. **Reconnect Triggers**:
   - Connection lost: `not is_endpoint_connected()`
   - Manual flag: `force_reconnect_flag = True`

3. **Reconnect Process**:
   - Calls `_reconnect()` for each endpoint type
   - Resets `force_reconnect_flag = False` after reconnect
   - Logs connection status

### How to Trigger Reconnect

```python
# Set flag to trigger reconnect
ws_client.force_reconnect_flag = True

# SDK's loop will detect this within 5 seconds
# and automatically reconnect
```

### Why V2 Plan Failed

V2 plan added:
```python
# V2 CUSTOM LOOP (DUPLICATE):
async def maintain_connection():
    while True:
        if not connected:
            await reconnect()
        await asyncio.sleep(5)

asyncio.create_task(maintain_connection())
```

**Problem**: SDK already has this loop!

- Creates duplicate loops
- Both trying to manage connection
- Race conditions and conflicts

**Correct Approach**:
```python
# V3 CORRECT (USE SDK):
def trigger_reconnect():
    ws_client.force_reconnect_flag = True
    # SDK's existing loop handles the rest
```

---

## Research 3: Async/Sync Approach

### Question: Should we convert methods to async?

**Answer**: NO - Use `asyncio.run()` wrapper

### Current State

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

```python
# Line 355: NOT async
async def place_post_only_order(...) -> OrderResult:
    # But actually uses await inside!
    order_result = self.rest_client.create_limit_order(...)

# Line 420: NOT async
async def place_market_order(...) -> OrderResult:
    # Also uses await
    order_result = self.rest_client.create_order(...)
```

**Observation**: Methods are ALREADY marked `async`, even though they don't need to be!

### Call Site Analysis

**File**: `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py`

```python
# Line 715: Call site expects async
order_result = await self.primary_client.place_post_only_order(...)

# Line 913: Also expects async
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(...),
    timeout=3.0
)
```

**Conclusion**: Code is ALREADY using async pattern!

### Implementation Approach

**Option 1**: Convert all to async
- ✅ Consistent with current pattern
- ✅ No breaking changes to call sites
- ✅ Clean code

**Option 2**: Use `asyncio.run()` in sync methods
- ❌ Unnecessary complexity
- ❌ Call sites already expect async
- ❌ Inconsistent with current code

**Decision**: Use Option 1 - Keep methods async (they already are!)

### Why V2 Plan Failed

V2 plan didn't address async/sync compatibility:
- Didn't check current method signatures
- Didn't check call site expectations
- Assumed conversion was needed

**V3 Finding**: No conversion needed - already async!

---

## Research 4: Close Order Aggressive Pricing

### Question: Do close orders have aggressive pricing?

**Answer**: YES ✅ - Already implemented

### Finding: POST_ONLY with Aggressive Pricing

**File**: `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 885-982

```python
# Lines 897-900: Aggressive pricing (cross spread)
if side == "buy":
    hedge_post_only_price = best_ask - self.hedge_tick_size
else:  # sell
    hedge_post_only_price = best_bid + self.hedge_tick_size

# Line 904: Round to tick
hedge_post_only_price = self.hedge_client.round_to_tick(hedge_post_only_price)

# Lines 912-920: POST_ONLY with 3-second timeout
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(
        contract_id=self.hedge_contract_id,
        quantity=quantity,
        price=hedge_post_only_price,
        side=order_side
    ),
    timeout=3.0
)

# Lines 960-977: Fallback to MARKET if POST_ONLY fails
if hedge_result.status == "OPEN":
    self.logger.warning(
        f"[CLOSE] POST_ONLY not filled within 3s, canceling..."
    )
    await self.hedge_client.cancel_order(hedge_result.order_id)
    # Fall through to MARKET order
```

### How It Works

1. **Calculate Aggressive Price**:
   - Buy: `best_ask - 1 tick` (crosses spread)
   - Sell: `best_bid + 1 tick` (crosses spread)

2. **Try POST_ONLY**:
   - Places at aggressive price
   - Waits 3 seconds for fill
   - Saves 0.05% fee (maker vs taker)

3. **Fallback to MARKET**:
   - If POST_ONLY not filled, cancel
   - Use MARKET order instead
   - Pays 0.05% taker fee

### Why V2 Plan Failed

V2 plan claimed:
> "P3 Already Done: Current code (lines 828, 885-982) has aggressive pricing + POST_ONLY fallback"

**But** V2 removed P3 from the implementation table:
```markdown
| ~~P3~~ | Aggressive pricing | -$0.015/cycle loss | **ALREADY IMPLEMENTED** | N/A | - |
```

**Critic Feedback**: "P3 removal is misleading"

**V3 Correction**: P3 is VERIFIED as already implemented, no action needed.

---

## Research 5: Timeout Mechanism

### Question: Does WebSocket have timeout for orders?

**Answer**: NO ❌ - Must implement manually

### Finding: SDK `rpc_create_order()` Has No Timeout

**File**: `pysdk/grvt_ccxt_ws.py` line 615-639

```python
async def rpc_create_order(...) -> dict:
    # ... validation ...
    payload = get_order_rpc_payload(...)
    await self.send_rpc_message(GrvtWSEndpointType.TRADE_DATA_RPC_FULL, payload)
    return payload  # <-- Returns immediately, no timeout!
```

**Problem**:
- Sends request via WebSocket
- Response comes asynchronously via callback
- No built-in timeout
- Can hang indefinitely

### Solution: Wrap with `asyncio.wait_for()`

```python
try:
    result = await asyncio.wait_for(
        ws_client.rpc_create_order(...),
        timeout=10.0  # 10 second timeout
    )
except asyncio.TimeoutError:
    # Handle timeout
    logger.log("WebSocket order timeout, falling back to REST")
    # Use REST fallback
```

### Recommended Timeout Values

| Order Type | Timeout | Rationale |
|------------|---------|-----------|
| POST_ONLY | 10 seconds | Allow time for maker fill |
| MARKET | 5 seconds | Should fill immediately |
| Iterative | 10 seconds per iteration | Consume liquidity depth |

### Why V2 Plan Failed

V2 plan didn't mention timeout mechanism:
- No discussion of WebSocket order timeout
- No implementation of `asyncio.wait_for()`
- No handling of `TimeoutError`

**V3 Addition**: Explicit timeout for all WebSocket orders

---

## Summary of Findings

| Question | Answer | Impact on Plan |
|----------|--------|----------------|
| **Q1**: Does `create_order()` exist? | NO ❌ | Use `rpc_create_order()` instead |
| **Q2**: Does SDK have auto-reconnect? | YES ✅ | Use `force_reconnect_flag`, don't add custom loop |
| **Q3**: Convert methods to async? | NO - Already async | Keep current async pattern |
| **Q4**: Close orders aggressive pricing? | YES ✅ | P3 already done, no action needed |
| **Q5**: WebSocket timeout mechanism? | NO ❌ | Must implement `asyncio.wait_for()` |

---

## Critical Corrections from V2 to V3

### Correction 1: SDK Method Name
- **V2**: Assumed `create_order()`
- **V3**: Use `rpc_create_order()` and `rpc_create_limit_order()`

### Correction 2: Reconnect Strategy
- **V2**: Add custom `maintain_connection()` loop
- **V3**: Use SDK's `force_reconnect_flag` (no duplicate loops)

### Correction 3: Response Handling
- **V2**: Assumed direct response from `create_order()`
- **V3**: RPC returns `request_id`, response via callback

### Correction 4: Async Conversion
- **V2**: Not addressed
- **V3**: Keep methods async (already are async)

### Correction 5: Timeout
- **V2**: Not mentioned
- **V3**: Implement 10-second timeout via `asyncio.wait_for()`

### Correction 6: P3 Status
- **V2**: Removed from table (misleading)
- **V3**: Clearly marked as "ALREADY IMPLEMENTED, NO ACTION NEEDED"

---

## Recommended Implementation Approach

Based on research findings:

1. **Use RPC Methods**: `rpc_create_order()` and `rpc_create_limit_order()`
2. **Implement Timeout**: Wrap with `asyncio.wait_for(timeout=10.0)`
3. **Query Status via REST**: Use `fetch_order()` to get order result
4. **Use SDK Reconnect**: Set `force_reconnect_flag = True` when needed
5. **Keep Methods Async**: Already async, no conversion needed
6. **P3 Already Done**: No changes to close order pricing

---

## Files Modified

1. **`exchanges/grvt.py`**:
   - Add `_ws_rpc_create_order()` method
   - Add `_is_websocket_connected()` method
   - Add `trigger_websocket_reconnect()` method
   - Update `place_post_only_order()` to use RPC
   - Update `place_market_order()` to use RPC
   - Update `place_iterative_market_order()` to use RPC

2. **`test_grvt_websocket_orders.py`** (NEW):
   - Test market order via RPC
   - Test POST_ONLY order via RPC
   - Test REST fallback
   - Test timeout mechanism

---

## Testing Checklist

- [ ] Unit test: `_ws_rpc_create_order()` with market orders
- [ ] Unit test: `_ws_rpc_create_order()` with limit orders
- [ ] Unit test: REST fallback when WebSocket unavailable
- [ ] Unit test: Timeout mechanism (mock slow response)
- [ ] Integration test: 10 cycles with 0.1 ETH orders
- [ ] Integration test: 50 cycles with 0.2 ETH orders
- [ ] Integration test: 100 cycles with 0.5 ETH orders
- [ ] Edge case: WebSocket disconnect during order
- [ ] Edge case: WebSocket timeout
- [ ] Edge case: Both WebSocket and REST unavailable

---

## Conclusion

This research identified critical flaws in V2 plan and provides corrected approach based on ACTUAL SDK capabilities:

- ✅ Uses correct SDK methods (`rpc_create_order()`)
- ✅ Integrates with SDK's reconnect (no duplicate loops)
- ✅ Implements timeout for WebSocket orders
- ✅ Verifies P3 already implemented
- ✅ Minimal changes, lower risk

**Next Step**: Implement V3 plan with these corrected findings.
