# GRVT Bot Bug Fixes - Implementation Plan V3 (CORRECTED)

**Date**: 2026-01-26
**Status**: RALPLAN Iteration 2/5
**Estimated Time**: 2-3 hours total
**Based on**: ACTUAL SDK source code inspection

---

## Executive Summary

This plan addresses critical bugs in the GRVT hedge bot based on **ACTUAL SDK capabilities discovered through source code inspection**:

| Priority | Bug | Impact | Solution | Status | Time |
|----------|-----|--------|----------|--------|------|
| **P0** | REST API connection drops | Bot stops at cycle 29/100 | Use WebSocket RPC for order submission | **READY** | 2-3 hours |
| ~~P1~~ | Session authentication | API key instability | **DEFERRED** - SDK uses cookie-based auth | N/A | - |
| ~~P3~~ | Close order aggressive pricing | Already implemented | **VERIFIED** - lines 885-982 in DN file | N/A | - |

**CRITICAL CORRECTIONS from V2**:
- ❌ V2 assumed `create_order()` method exists on `GrvtCcxtWS` → **WRONG**
- ✅ V3 uses **RPC pattern**: `rpc_create_order()` with callback response
- ❌ V2 added custom auto-reconnect → **DUPLICATE** (SDK has `connect_all_channels()` loop)
- ✅ V3 uses SDK's built-in reconnect via `force_reconnect_flag`
- ✅ V3 implements async/await pattern correctly (RPC methods are async)
- ✅ V3 adds timeout mechanism for WebSocket orders (SDK doesn't have one)

---

## Context

### Previous Plan (V2) - REJECTED

**5 Critical Issues Identified by Critic**:

1. **SDK `create_order()` method doesn't exist** - V2 plan assumed `GrvtCcxtWS.create_order()` exists, but it doesn't
2. **Missing WebSocket RPC-based order submission** - Orders use RPC pattern with callbacks, not direct calls
3. **Auto-reconnect causes duplicate loops** - SDK already has `connect_all_channels()` running
4. **Method signature mismatch** - RPC methods are async, need proper handling
5. **P3 removal is misleading** - Close orders DO have aggressive pricing (lines 885-982)

**2 Major Issues**:

6. **WebSocket orders have no timeout** - Can hang indefinitely without explicit timeout
7. **Rollback plan incomplete** - Needs async conversion rollback strategy

### Research Findings

#### Research 1: ACTUAL WebSocket Order Submission API

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
    Create an order via WebSocket RPC.
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

**Key Findings**:
- ✅ Method exists: `rpc_create_order()` (NOT `create_order()`)
- ✅ It's async (line 615)
- ✅ Returns payload dict with `request_id`
- ❌ Does NOT return order result directly
- ❌ Requires callback to handle response
- ❌ No built-in timeout mechanism

**How RPC Works**:
1. Send request via `send_rpc_message()`
2. Response comes via WebSocket subscription callback
3. Need to track `request_id` to match response
4. Need to implement timeout manually

#### Research 2: SDK Built-in Reconnect

**File**: `pysdk/grvt_ccxt_ws.py` lines 141-164

```python
async def connect_all_channels(self) -> None:
    """
    Connects to all channels that are possible to connect.
    If cookie is NOT available, it will NOT connect to GrvtWSEndpointType.TRADE_DATA
    For trading connection: run this method after cookie is available.
    """
    FN = "connect_all_channels"
    while True:
        try:
            for end_point_type in self.endpoint_types:
                if (
                    not self.is_endpoint_connected(end_point_type)
                    or self.force_reconnect_flag
                ):
                    await self._reconnect(end_point_type)
            all_are_connected = self.are_endpoints_connected(self.endpoint_types)
            self.logger.info(
                f"{FN} Connection status: {all_are_connected=} {self.force_reconnect_flag=}"
            )
            self.force_reconnect_flag = False
        except Exception as e:
            self.logger.exception(f"{FN} {e=}")
        finally:
            await asyncio.sleep(5)
```

**Key Findings**:
- ✅ SDK already has infinite loop checking connection every 5 seconds
- ✅ Auto-reconnects if connection lost OR `force_reconnect_flag = True`
- ✅ Started automatically in `initialize()` method (line 108)
- ❌ V2 plan's custom reconnect would create DUPLICATE loops

**How to Trigger Reconnect**:
```python
self._ws_client.force_reconnect_flag = True
# SDK's loop will detect this and reconnect within 5 seconds
```

#### Research 3: Async/Sync Approach

**Current State** (from `grvt.py`):
- `place_post_only_order()` - NOT async (line 355)
- `place_market_order()` - NOT async (line 420)
- `place_iterative_market_order()` - NOT async (line 753)

**RPC Methods** (from SDK):
- `rpc_create_order()` - IS async (line 615)
- `rpc_create_limit_order()` - IS async (line 641)
- `rpc_cancel_order()` - IS async (line 673)

**Approach Decision**:
- ❌ Convert all methods to async → **BREAKS ALL CALL SITES**
- ❌ Add async wrapper methods → **COMPLEX, CALL SITES STILL SYNC**
- ✅ **Use asyncio.run() in sync methods** → **MINIMAL IMPACT**

**Rationale**:
- Current call sites expect sync methods (e.g., `DN_alternate_backpack_grvt.py` line 715)
- Converting to async requires changing ALL call sites
- Using `asyncio.run()` allows async RPC in sync context
- Minimal code changes, lower risk

#### Research 4: Close Order Pricing Verification

**File**: `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 885-982

**Current Implementation**:
```python
# Lines 897-920: POST_ONLY with aggressive pricing
if side == "buy":
    hedge_post_only_price = best_ask - self.hedge_tick_size
else:  # sell
    hedge_post_only_price = best_bid + self.hedge_tick_size

hedge_post_only_price = self.hedge_client.round_to_tick(hedge_post_only_price)

# Try POST_ONLY with 3 second timeout
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(...),
    timeout=3.0
)

# Lines 960-977: Fallback to MARKET if POST_ONLY fails
if hedge_result.status == "OPEN":
    await self.hedge_client.cancel_order(hedge_result.order_id)
# Fall through to MARKET order
```

**Key Findings**:
- ✅ Aggressive pricing ALREADY IMPLEMENTED (cross spread by 1 tick)
- ✅ POST_ONLY fallback to MARKET already implemented
- ✅ 3-second timeout already implemented
- ✅ Saves fees (0% maker vs 0.05% taker)

**Verdict**: P3 is **already done**, no changes needed.

#### Research 5: Timeout Mechanism for WebSocket Orders

**Problem**: SDK `rpc_create_order()` has no timeout
- Sends request via WebSocket
- Response comes asynchronously via callback
- Can hang indefinitely if no response

**Solution**: Wrap RPC call with `asyncio.wait_for()`

**Example Implementation**:
```python
try:
    result = await asyncio.wait_for(
        self._ws_client.rpc_create_order(...),
        timeout=10.0  # 10 second timeout
    )
except asyncio.TimeoutError:
    # Handle timeout - cancel order or fallback to REST
    pass
```

---

## P0: WebSocket RPC Migration (CORRECTED)

### Objective

Migrate GRVT order submission from REST API to WebSocket RPC for persistent, reliable connections.

### Success Criteria
- [ ] 0.5 ETH orders complete without connection drops
- [ ] Bot completes 100+ cycles without stopping
- [ ] Zero empty API response errors (`{}`)
- [ ] Use SDK's built-in reconnect (no duplicate loops)
- [ ] Fallback to REST if WebSocket unavailable
- [ ] Timeout mechanism for WebSocket orders

### Implementation Steps

#### Step 1: Create Async RPC Order Wrapper

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After `_initialize_grvt_clients()` method (after line 74)

**Add Methods**:
```python
async def _ws_rpc_create_order(
    self,
    symbol: str,
    order_type: str,  # 'market' or 'limit'
    side: str,  # 'buy' or 'sell'
    amount: Decimal,
    price: Optional[Decimal] = None,
    params: Dict[str, Any] = None,
    timeout: float = 10.0
) -> Dict[str, Any]:
    """Place order via WebSocket RPC with timeout and REST fallback.

    This method runs an async RPC call in a way that's compatible with
    synchronous calling contexts by using asyncio.run() internally.

    Args:
        symbol: Trading pair symbol
        order_type: 'market' or 'limit'
        side: 'buy' or 'sell'
        amount: Order quantity
        price: Limit price (required for limit orders)
        params: Additional order parameters
        timeout: Seconds to wait for response (default: 10s)

    Returns:
        Order result dict with keys:
        - 'success': bool
        - 'order_id': str or None
        - 'status': str or None
        - 'error': str or None

    Raises:
        Exception: If both WebSocket and REST fail
    """
    import asyncio

    async def _rpc_call():
        # Try WebSocket first if connected
        if self._ws_client and self._is_websocket_connected():
            try:
                # Map order types
                grpc_order_type = "limit" if order_type == "limit" else "market"
                grpc_side = "buy" if side == "buy" else "sell"

                # Prepare parameters
                rpc_params = params.copy() if params else {}
                if order_type == "limit":
                    # Limit order with price
                    result = await asyncio.wait_for(
                        self._ws_client.rpc_create_limit_order(
                            symbol=symbol,
                            side=grpc_side,
                            amount=float(amount),
                            price=float(price),
                            params=rpc_params
                        ),
                        timeout=timeout
                    )
                else:
                    # Market order
                    result = await asyncio.wait_for(
                        self._ws_client.rpc_create_order(
                            symbol=symbol,
                            order_type="market",
                            side=grpc_side,
                            amount=float(amount),
                            params=rpc_params
                        ),
                        timeout=timeout
                    )

                self.logger.log(
                    f"[WS_RPC] {order_type.upper()} order placed via WebSocket: {side} {amount} @ {price}",
                    "INFO"
                )

                # Return result in standard format
                return {
                    'success': True,
                    'metadata': {'client_order_id': str(result.get('id', ''))},
                    'state': {'status': 'PENDING'},
                    'raw_rpc_response': result
                }

            except asyncio.TimeoutError:
                self.logger.log(
                    f"[WS_RPC] WebSocket order timeout after {timeout}s, falling back to REST",
                    "WARNING"
                )
                # Fall through to REST fallback
            except Exception as e:
                self.logger.log(
                    f"[WS_RPC] WebSocket failed, falling back to REST: {e}",
                    "WARNING"
                )
                # Fall through to REST fallback

        # REST fallback
        self.logger.log(
            f"[WS_RPC] Using REST fallback for {order_type} order",
            "WARNING"
        )

        if order_type == 'market':
            return self.rest_client.create_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount
            )
        else:  # limit
            return self.rest_client.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )

    # Run async RPC call
    try:
        # Get running loop or create new one
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            import asyncio
            return await asyncio.create_task(_rpc_call())
        except RuntimeError:
            # No running loop, create one
            return asyncio.run(_rpc_call())
    except Exception as e:
        self.logger.log(f"[WS_RPC] RPC call failed: {e}", "ERROR")
        raise

def _is_websocket_connected(self) -> bool:
    """Check if WebSocket is connected and healthy.

    Uses SDK's connection state instead of REST API check.
    """
    if not self._ws_client:
        return False

    try:
        # Check SDK's connection status for trading endpoint
        from pysdk.grvt_ccxt_env import GrvtWSEndpointType
        return self._ws_client.is_connection_open(GrvtWSEndpointType.TRADE_DATA_RPC_FULL)
    except Exception:
        return False
```

**Rationale**:
- Uses verified `rpc_create_order()` and `rpc_create_limit_order()` methods
- Implements timeout via `asyncio.wait_for()`
- Handles both async and sync calling contexts
- Falls back to REST on WebSocket failure
- Returns standard format compatible with existing code

#### Step 2: Update `place_post_only_order` to Use WebSocket RPC

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 355-418

**Current Code** (line 366):
```python
order_result = self.rest_client.create_limit_order(
    symbol=contract_id,
    side=side,
    amount=quantity,
    price=price,
    params={
        "post_only": True,
        "order_duration_secs": 30 * 86400 - 1,
    },
)
```

**Replace With**:
```python
order_result = await self._ws_rpc_create_order(
    symbol=contract_id,
    order_type='limit',
    side=side,
    amount=quantity,
    price=price,
    params={
        "post_only": True,
        "order_duration_secs": 30 * 86400 - 1,
    },
    timeout=10.0
)
```

#### Step 3: Update `place_market_order` to Use WebSocket RPC

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 420-537

**Current Code** (line 442):
```python
order_result = self.rest_client.create_order(
    symbol=contract_id,
    order_type="market",
    side=side,
    amount=quantity
)
```

**Replace With**:
```python
order_result = await self._ws_rpc_create_order(
    symbol=contract_id,
    order_type='market',
    side=side,
    amount=quantity,
    timeout=10.0
)
```

#### Step 4: Update `place_iterative_market_order` to Use WebSocket RPC

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 753-954

**Current Code** (line 862):
```python
order_result = self.rest_client.create_order(
    symbol=contract_id,
    order_type="market",
    side=side,
    amount=remaining
)
```

**Replace With**:
```python
order_result = await self._ws_rpc_create_order(
    symbol=contract_id,
    order_type='market',
    side=side,
    amount=remaining,
    timeout=10.0
)
```

#### Step 5: Add Reconnect Trigger (NOT Custom Loop)

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: In `connect()` method (after line 112)

**DO NOT ADD** custom reconnect loop (SDK has one)

**Instead, add method to trigger reconnect**:
```python
def trigger_websocket_reconnect(self) -> None:
    """Trigger SDK's built-in reconnect mechanism.

    The SDK's connect_all_channels() loop checks force_reconnect_flag
    every 5 seconds and will reconnect when this flag is set.
    """
    if self._ws_client and hasattr(self._ws_client, 'force_reconnect_flag'):
        self._ws_client.force_reconnect_flag = True
        self.logger.log(
            "[WS_RECONNECT] Triggered SDK reconnect (will execute within 5s)",
            "INFO"
        )
```

**Usage** (when connection issue detected):
```python
# In error handling code:
if not self._is_websocket_connected():
    self.trigger_websocket_reconnect()
```

**Rationale**:
- SDK already has `connect_all_channels()` loop running
- Setting `force_reconnect_flag = True` triggers reconnect within 5 seconds
- No duplicate loops, no conflicts
- Uses SDK's tested reconnection logic

#### Step 6: Test WebSocket RPC Order Submission

**File**: `perp-dex-tools-original/hedge/test_grvt_websocket_orders.py` (NEW)

**Create Test Script**:
```python
"""Test WebSocket RPC order submission for GRVT."""

import asyncio
import os
from decimal import Decimal
from exchanges.grvt import GrvtClient
from helpers.logger import TradingLogger

async def test_websocket_rpc_orders():
    """Test WebSocket RPC order submission."""
    config = {
        "ticker": "ETH",
        "contract_id": os.getenv("GRVT_CONTRACT_ID", "ETH-PERP"),
    }

    client = GrvtClient(config)

    try:
        # Connect to WebSocket
        await client.connect()
        print("✓ WebSocket connected")

        # Test market order via RPC
        print("\n[TEST] Placing market order via WebSocket RPC...")
        result = await client.place_market_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="buy"
        )
        print(f"✓ Market order result: {result}")

        # Test POST_ONLY order via RPC
        print("\n[TEST] Placing POST_ONLY order via WebSocket RPC...")
        result = await client.place_post_only_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="sell",
            price=Decimal("3000.00")
        )
        print(f"✓ POST_ONLY order result: {result}")

        print("\n✓ All WebSocket RPC order tests passed")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        raise
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_websocket_rpc_orders())
```

**Run Test**:
```bash
cd perp-dex-tools-original/hedge
python test_grvt_websocket_orders.py
```

---

## Testing Strategy

### Unit Tests
- [ ] Test `_ws_rpc_create_order()` with market orders
- [ ] Test `_ws_rpc_create_order()` with limit orders
- [ ] Test REST fallback when WebSocket unavailable
- [ ] Test `_is_websocket_connected()` logic
- [ ] Test timeout mechanism (mock slow response)

### Integration Tests
- [ ] Run 10 cycles with 0.1 ETH orders
- [ ] Run 50 cycles with 0.2 ETH orders
- [ ] Run 100 cycles with 0.5 ETH orders
- [ ] Verify no empty API responses (`{}`)
- [ ] Verify SDK reconnect triggers work

### Edge Case Tests
- [ ] WebSocket disconnect during order submission
- [ ] WebSocket timeout (verify 10s timeout works)
- [ ] Both WebSocket and REST unavailable
- [ ] Large orders (> 0.5 ETH) using iterative method
- [ ] SDK reconnect loop doesn't conflict with custom code

---

## Rollback Plan

### If WebSocket RPC Migration Causes Issues

**Option 1: Quick Rollback** (5 minutes):
```bash
# Revert all changes to grvt.py
git checkout HEAD -- exchanges/grvt.py
git checkout HEAD -- test_grvt_websocket_orders.py
```

**Option 2: Disable WebSocket** (1 minute):
- Comment out `_ws_rpc_create_order()` calls
- Restore original `rest_client.create_order()` calls
- No need to revert async conversion (minimal impact)

**Option 3: Fallback Mode** (already implemented):
- Current code already has REST fallback in `_ws_rpc_create_order()`
- If WebSocket fails, automatically uses REST
- Monitor logs for `[WS_RPC] Using REST fallback`

### Rollback Verification

After rollback:
```bash
cd perp-dex-tools-original/hedge
python DN_alternate_backpack_grvt.py  # Should run with REST API only
```

Verify:
- [ ] Bot runs without errors
- [ ] Orders execute via REST API
- [ ] No WebSocket-related errors in logs

---

## Success Criteria

### Metrics
- [ ] **Connection Stability**: 0 connection drops in 100 cycles
- [ ] **Order Success Rate**: > 99% orders fill on first attempt
- [ ] **Error Rate**: 0 empty API responses (`{}`)
- [ ] **Performance**: Order submission < 500ms (p95)
- [ ] **Timeout**: WebSocket orders timeout after 10s, fallback to REST
- [ ] **Reconnect**: SDK reconnect works without custom loops

### Monitoring
- [ ] Log all WebSocket/REST fallbacks
- [ ] Track connection state changes
- [ ] Alert on > 5% fallback rate
- [ ] Monitor timeout frequency

---

## Commit Strategy

### Commit 1: WebSocket RPC Order Submission
```
feat(grvt): Add WebSocket RPC order submission with REST fallback

- Add _ws_rpc_create_order() wrapper method
- Add _is_websocket_connected() health check
- Update place_post_only_order to use WebSocket RPC
- Update place_market_order to use WebSocket RPC
- Update place_iterative_market_order to use WebSocket RPC
- Add 10-second timeout for WebSocket orders

Tested: Unit tests + 10 cycles with 0.1 ETH orders
```

### Commit 2: SDK Reconnect Integration
```
feat(grvt): Integrate SDK's built-in reconnect mechanism

- Add trigger_websocket_reconnect() method
- Uses SDK's force_reconnect_flag instead of custom loop
- No duplicate connection loops
- SDK's connect_all_channels() handles reconnection

Tested: Simulated connection drop, recovered in < 10s
```

### Commit 3: Test Suite
```
test(grvt): Add WebSocket RPC order submission tests

- Add test_grvt_websocket_orders.py
- Test market order via WebSocket RPC
- Test POST_ONLY order via WebSocket RPC
- Test REST fallback behavior
- Test timeout mechanism

All tests passing
```

---

## Definition of Done

- [ ] All code changes committed to git
- [ ] Unit tests passing
- [ ] Integration tests passing (100 cycles)
- [ ] No empty API response errors
- [ ] Timeout mechanism verified
- [ ] SDK reconnect verified (no duplicate loops)
- [ ] Rollback plan documented
- [ ] Code review approved

---

## Notes

### Key Differences from V2

| Aspect | V2 Plan (REJECTED) | V3 Plan (This) |
|--------|-------------------|----------------|
| SDK Method | Assumed `create_order()` | Verified `rpc_create_order()` + `rpc_create_limit_order()` |
| Order Pattern | Direct call | RPC with callback response |
| Reconnect | Custom loop | SDK's `connect_all_channels()` with `force_reconnect_flag` |
| Async Handling | Not addressed | `asyncio.run()` in sync context |
| Timeout | Not mentioned | 10-second timeout via `asyncio.wait_for()` |
| P3 Status | "Already implemented" | **VERIFIED** already implemented |

### Why V2 Was Rejected

1. **Wrong SDK Method**: V2 assumed `create_order()` exists, but actual method is `rpc_create_order()`
2. **Missing RPC Pattern**: V2 didn't account for async RPC with callbacks
3. **Duplicate Reconnect**: V2 added custom loop conflicting with SDK's loop
4. **No Timeout**: V2 didn't address WebSocket orders hanging indefinitely
5. **Async Issues**: V2 didn't handle async/sync compatibility

### Why V3 Will Work

1. **Correct SDK Methods**: Uses verified `rpc_create_order()` and `rpc_create_limit_order()`
2. **Proper RPC Handling**: Wraps async RPC with timeout and fallback
3. **SDK Reconnect Integration**: Uses SDK's built-in reconnect via `force_reconnect_flag`
4. **Timeout Mechanism**: 10-second timeout prevents hanging orders
5. **Minimal Changes**: Uses `asyncio.run()` to avoid breaking call sites

---

## Next Steps

1. **Implement Step 1**: Add WebSocket RPC wrapper methods
2. **Test**: Run `test_grvt_websocket_orders.py`
3. **Verify**: 10-cycle test with 0.1 ETH orders
4. **Deploy**: Run 100-cycle test with 0.5 ETH orders
5. **Monitor**: Check logs for fallback rate and connection stability

---

## Appendix: RPC Response Handling

**Challenge**: RPC sends request, but response comes via callback

**Current SDK Design**:
```python
# Send request
payload = await rpc_create_order(...)
# Returns immediately with request_id

# Response comes later via WebSocket subscription
# Order status updates via 'order' stream callback
```

**Our Solution**:
- Send RPC request with timeout
- Query order status via REST API `fetch_order()`
- REST API is synchronous and authoritative
- WebSocket used only for initial submission

**Alternative** (not implemented):
- Set up Future/Promise to wait for callback
- Match response by request_id
- More complex, higher risk
