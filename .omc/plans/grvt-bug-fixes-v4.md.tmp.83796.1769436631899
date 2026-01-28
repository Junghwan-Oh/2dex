# GRVT Bot Bug Fixes - Implementation Plan V4 (CORRECTED)

**Date**: 2026-01-26
**Status**: RALPLAN Iteration 2/5
**Estimated Time**: 2-3 hours total
**Based on**: ACTUAL SDK research findings

---

## Executive Summary

This plan addresses critical bugs based on **SDK research findings**:

| Priority | Bug | Impact | Solution | Status | Time |
|----------|-----|--------|----------|--------|------|
| **P0** | REST API connection drops | Bot stops at cycle 29/100 | Use WebSocket RPC + REST verification | **READY** | 2-3 hours |
| ~~P1~~ | Session authentication | API key instability | **DEFERRED** - SDK uses cookie-based auth | N/A | - |
| ~~P3~~ | Close order aggressive pricing | -$0.015/cycle loss | **VERIFIED** - lines 885-982 in DN file | N/A | - |

**CRITICAL CORRECTIONS from V3:**
- ❌ V3 assumed `create_order()` returns order result → **WRONG** - returns request payload
- ✅ V4 uses **RPC + REST verification**: Send RPC request, then REST query for status
- ❌ V3 added `asyncio.run()` wrapper → **WRONG** - methods already async
- ✅ V4 uses **direct `await`** - no wrapper needed
- ✅ V4 implements 10-second timeout for RPC calls

---

## Context

### Research Findings

#### Finding 1: RPC returns request payload only

**File**: `pysdk/grvt_ccxt_ws.py` lines 615-639

```python
async def rpc_create_order(self, symbol, order_type, side, amount, price=None, params={}):
    payload = get_order_rpc_payload(order, self._private_key, self.env, self.markets)
    self._request_id += 1
    payload["id"] = self._request_id
    await self.send_rpc_message(GrvtWSEndpointType.TRADE_DATA_RPC_FULL, payload)
    return payload  # Returns SENT payload with request_id, NOT order result!
```

**What it returns:**
```python
{
    'jsonrpc': '2.0',
    'method': 'v1/create_order',
    'params': {...},
    'id': 2  # ← This is the request ID
}
```

**What the order result:**
```python
{
    'jsonrpc': '2.0',
    'result': {
        'result': {
            'order_id': '0x00',
            'state': {'status': 'OPEN'}
        }
    },
    'id': 2  # ← Matches request ID
}
```

**Problem:** The response arrives via WebSocket callback but is only logged to debug. Not accessible to caller.

#### Finding 2: REST API query available

**File**: `pysdk/grvt_ccxt.py` line 320

```python
# Query order by order_id
order_data = rest_client.fetch_order(id="order_123")

# Query by client_order_id
order_data = rest_client.fetch_order(params={"client_order_id": "client_456"})
```

**Solution:** Use REST API query for order verification.

#### Finding 3: SDK helper functions accessible

**File**: `pysdk/grvt_ccxt_ws.py` lines 630-634

```python
# SDK internally uses these
order = self._get_order_with_validations(...)  # Private method - accessible
payload = get_order_rpc_payload(order, ...)      # Function - accessible
```

**Status:** Both methods exist and are accessible from external code.

#### Finding 4: Timeout behavior

**WebSocket read timeout:** 5 seconds (configurable, line 37)
- Does NOT cancel pending requests
- SDK does NOT track pending requests
- Timeout only affects `recv()` call, not RPC operation

**Application timeout:** Can add 10-second timeout via `asyncio.wait_for()`.

---

## P0: WebSocket RPC Migration with REST Verification

### Objective

Migrate from REST API to WebSocket RPC with REST verification for order status.

### Success Criteria
- [ ] 0.5 ETH orders complete without connection drops
- [ ] Bot completes 100+ cycles without stopping
- [ ] Zero empty API response errors (`{}`)
- [ ] Order verification works via REST API
- [ ] 10-second timeout for RPC calls
- [ ] SDK reconnect integration (no duplicate loops)

### Implementation Steps

#### Step 1: Create Order Verification Wrapper

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After `_initialize_grvt_clients()` (after line 74)

**Add Method**:
```python
async def _verify_order_status(
    self,
    symbol: str,
    client_order_id: str,
    timeout: float = 10.0
) -> Optional[Dict[str, Any]]:
    """Verify order status via REST API.

    After sending RPC request, use REST API to verify order execution.

    Args:
        symbol: Trading pair
        client_order_id: Client order ID from RPC response
        timeout: Seconds to wait for order to fill (default: 10s)

    Returns:
        Order status dict or None if timeout/failed
    """
    if not self.rest_client:
        return None

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Query order status via REST API
            order_info = self.rest_client.fetch_order(params={"client_order_id": client_order_id})

            if order_info:
                status = order_info.get('state', {}).get('status', 'UNKNOWN')
                self.logger.log(
                    f"[ORDER_VERIFICATION] Order {client_order_id} status: {status}",
                    "DEBUG"
                )

                if status in ["FILLED", "CANCELLED", "REJECTED"]:
                    return order_info
                elif status in ["OPEN", "PENDING"]:
                    await asyncio.sleep(0.1)  # Check every 100ms
                    continue
                else:
                    return order_info  # UNKNOWN status

        except Exception as e:
            self.logger.warning(f"[ORDER_VERIFICATION] Error: {e}")
            await asyncio.sleep(0.1)

    # Timeout
    self.logger.warning(
        f"[ORDER_VERIFICATION] Order {client_order_id} timeout after {timeout}s"
    )
    return None
```

**Rationale**:
- Uses REST API for authoritative order status
- Polls every 100ms for efficiency
- Returns on terminal states (FILLED, CANCELLED, REJECTED)
- Times out after 10 seconds

#### Step 2: Create WebSocket RPC Order Submission Wrapper

**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After Step 1 (after line 204)

**Add Method**:
```python
async def _ws_rpc_submit_order(
    self,
    symbol: str,
    order_type: str,
    side: str,
    amount: Decimal,
    price: Optional[Decimal] = None,
    params: Dict[str, Any] = None,
    verify_with_rest: bool = True
) -> Dict[str, Any]:
    """Submit order via WebSocket RPC with REST verification.

    Uses RPC for order submission and REST API for verification.

    Args:
        symbol: Trading pair
        order_type: 'market' or 'limit'
        side: 'buy' or 'sell'
        amount: Order quantity
        price: Limit price (required for limit orders)
        params: Additional order parameters
        verify_with_rest: Whether to verify order status via REST (default: True)

    Returns:
        Standard order result dict with keys:
        - 'success': bool
        - 'order_id': str or None (client order ID)
        - 'status': str or None
        - 'error': str or None
    """
    if not self._ws_client:
        self.logger.warning("[WS_RPC] WebSocket client not available, using REST fallback")
        return self.rest_client.create_order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=params or {}
        )

    # Map order types
    grpc_order_type = "limit" if order_type == "limit" else "market"
    grpc_side = "buy" if side == "buy" else "sell"

    # Prepare parameters
    rpc_params = params.copy() if params else {}

    try:
        # Send RPC request with 10-second timeout
        self.logger.log(
            f"[WS_RPC] Submitting {order_type.upper()} order via WebSocket: {side} {amount} @ {price}",
            "INFO"
        )

        result = await asyncio.wait_for(
            self._ws_client.rpc_create_limit_order(
                symbol=symbol,
                side=grpc_side,
                amount=float(amount),
                price=float(price) if price else None,
                params=rpc_params
            ),
            timeout=10.0
        )

        # Get client order ID from response
        client_order_id = str(result.get('id', ''))

        self.logger.log(
            f"[WS_RPC] RPC request sent with client_order_id: {client_order_id}",
            "INFO"
        )

        # Verify order status via REST API (if enabled)
        if verify_with_rest:
            self.logger.log(
                f"[WS_RPC] Verifying order status via REST API...",
                "DEBUG"
            )

            order_info = await self._verify_order_status(
                symbol=symbol,
                client_order_id=client_order_id,
                timeout=10.0
            )

            if not order_info:
                self.logger.warning(
                    f"[WS_RPC] Order verification failed (timeout or error)"
                )
                # Fall back to REST submission
                return self.rest_client.create_order(
                    symbol=symbol,
                    order_type=order_type,
                    side=side,
                    amount=amount,
                    price=price,
                    params=params or {}
                )

            # Get status from REST API response
            status = order_info.get('state', {}).get('status', 'OPEN')

            self.logger.log(
                f"[WS_RPC] Order verification: {status}",
                "INFO"
            )

            return {
                'success': True,
                'metadata': {'client_order_id': client_order_id},
                'state': {'status': status},
                'raw_rpc_response': result,
                'raw_rest_response': order_info
            }

        # No verification - return immediately
        return {
            'success': True,
            'metadata': {'client_order_id': client_order_id},
            'state': {'status': 'PENDING'},
            'raw_rpc_response': result
        }

    except asyncio.TimeoutError:
        self.logger.warning(
            f"[WS_RPC] WebSocket order timeout after 10s, falling back to REST"
        )
        # Fall back to REST
        return self.rest_client.create_order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=params or {}
        )

    except Exception as e:
        self.logger.error(
            f"[WS_RPC] WebSocket RPC failed: {e}, falling back to REST"
        )
        # Fall back to REST
        return self.rest_client.create_order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=params or {}
        )
```

**Rationale**:
- Uses verified `rpc_create_limit_order()` method
- Implements 10-second timeout
- Falls back to REST on failure
- Verifies order status via REST API
- Returns standard format compatible with existing code
- No async wrapper needed (methods are already async)

#### Step 3: Update `place_post_only_order` to Use WebSocket RPC

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
order_result = await self._ws_rpc_submit_order(
    symbol=contract_id,
    order_type='limit',
    side=side,
    amount=quantity,
    price=price,
    params={
        "post_only": True,
        "order_duration_secs": 30 * 86400 - 1,
    },
    verify_with_rest=True
)
```

#### Step 4: Update `place_market_order` to Use WebSocket RPC

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
order_result = await self._ws_rpc_submit_order(
    symbol=contract_id,
    order_type='market',
    side=side,
    amount=quantity,
    verify_with_rest=True
)
```

#### Step 5: Update `place_iterative_market_order` to Use WebSocket RPC

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
order_result = await self._ws_rpc_submit_order(
    symbol=contract_id,
    order_type='market',
    side=side,
    amount=remaining,
    verify_with_rest=True
)
```

#### Step 6: Add Reconnect Trigger (Not Custom Loop)

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
    else:
        self.logger.warning(
            "[WS_RECONNECT] Cannot trigger reconnect: _ws_client or force_reconnect_flag not available"
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

#### Step 7: Test WebSocket RPC Order Submission

**File**: `perp-dex-tools-original/hedge/test_grvt_websocket_rpc_orders.py` (NEW)

**Create Test Script**:
```python
"""Test WebSocket RPC order submission for GRVT with REST verification."""

import asyncio
import os
from decimal import Decimal
from exchanges.grvt import GrvtClient
from helpers.logger import TradingLogger

async def test_websocket_rpc_orders():
    """Test WebSocket RPC order submission with REST verification."""
    config = {
        "ticker": "ETH",
        "contract_id": os.getenv("GRVT_CONTRACT_ID", "ETH-PERP"),
    }

    client = GrvtClient(config)

    try:
        # Connect to WebSocket
        await client.connect()
        print("✓ WebSocket connected")

        # Test market order
        print("\n[TEST] Placing market order via WebSocket RPC...")
        result = await client.place_market_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="buy"
        )
        print(f"✓ Market order result: {result}")
        print(f"  Success: {result.get('success')}")
        print(f"  Order ID: {result.get('metadata', {}).get('client_order_id')}")

        # Test POST_ONLY order
        print("\n[TEST] Placing POST_ONLY order via WebSocket RPC...")
        result = await client.place_post_only_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="sell"
        )
        print(f"✓ POST_ONLY order result: {result}")
        print(f"  Success: {result.get('success')}")
        print(f"  Order ID: {result.get('metadata', {}).get('client_order_id')}")

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
python test_grvt_websocket_rpc_orders.py
```

---

## Testing Strategy

### Unit Tests
- [ ] Test `_verify_order_status()` with different order states
- [ ] Test timeout behavior (verify after 10 seconds)
- [ ] Test REST fallback when WebSocket fails
- [ ] Test reconnect trigger

### Integration Tests
- [ ] Run 10 cycles with 0.1 ETH orders
- [ ] Run 50 cycles with 0.2 ETH orders
- [ ] Run 100 cycles with 0.5 ETH orders
- [ ] Verify no empty API responses (`{}`)
- [ ] Verify order verification works

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
git checkout HEAD -- test_grvt_websocket_rpc_orders.py
```

**Option 2: Disable WebSocket** (1 minute):
- Comment out `_ws_rpc_submit_order()` calls
- Restore original `rest_client.create_order()` calls
- No need to revert async conversion (minimal impact)

**Option 3: Fallback Mode** (already implemented):
- Current code already has REST fallback in `_ws_rpc_submit_order()`
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
- [ ] **Verification**: Order status verified via REST API

### Monitoring
- [ ] Log all WebSocket/REST fallbacks
- [ ] Track connection state changes
- [ ] Alert on > 5% fallback rate
- [ ] Monitor timeout frequency

---

## Commit Strategy

### Commit 1: WebSocket RPC with REST Verification
```
feat(grvt): Add WebSocket RPC order submission with REST verification

- Add _verify_order_status() method
- Add _ws_rpc_submit_order() wrapper with 10s timeout
- Update place_post_only_order to use WebSocket RPC
- Update place_market_order to use WebSocket RPC
- Update place_iterative_market_order to use WebSocket RPC
- Add SDK reconnect trigger

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

- Add test_grvt_websocket_rpc_orders.py
- Test market order via WebSocket RPC
- Test POST_ONLY order via WebSocket RPC
- Test REST fallback behavior
- Test order verification

All tests passing
```

---

## Definition of Done

- [ ] All code changes committed to git
- [ ] Unit tests passing
- [ ] Integration tests passing (100 cycles)
- [ ] No empty API response errors
- [ ] Order verification verified
- [ ] SDK reconnect verified (no duplicate loops)
- [ ] Rollback plan documented
- [ ] Code review approved

---

## Key Differences from V3

| Aspect | V3 (REJECTED) | V4 (This) |
|--------|---------------|-----------|
| RPC Return | Assumed order result | Returns request payload only |
| Order Verification | Not addressed | REST API query for status |
| Async Handling | `asyncio.run()` wrapper (wrong) | Direct `await` (correct) |
| Timeout | Not mentioned | 10-second timeout via `asyncio.wait_for()` |
| Request Matching | Missing | REST query with client_order_id |
| Response Loss | Not addressed | REST verification restores data |

---

## Next Steps

1. **Implement Step 1**: Add `_verify_order_status()` method
2. **Implement Step 2**: Add `_ws_rpc_submit_order()` wrapper
3. **Test**: Run `test_grvt_websocket_rpc_orders.py`
4. **Verify**: 10-cycle test with 0.1 ETH orders
5. **Deploy**: Run 100-cycle test with 0.5 ETH orders
6. **Monitor**: Check logs for fallback rate and connection stability

---

## Appendix: Why This Approach Works

### RPC Response Problem

The `rpc_create_order()` method returns the **request payload** (with `request_id`), NOT the order result. The order result arrives asynchronously via WebSocket callback but is only logged to debug.

### Solution: REST API Verification

The REST API has a `fetch_order()` method that queries order status by `client_order_id`. This provides:

1. **Synchronous API** - Returns immediately with order status
2. **Authoritative source** - REST API is the source of truth
3. **No race condition** - Can verify order exists before proceeding
4. **Simple implementation** - Poll every 100ms until terminal state

### Timeout Handling

Using `asyncio.wait_for()` with 10-second timeout:
- If RPC takes longer than 10 seconds, raises `asyncio.TimeoutError`
- Falls back to REST API submission
- Prevents indefinite hangs

### REST Fallback

If WebSocket fails:
1. `asyncio.TimeoutError` caught
2. Logs warning
3. Calls `rest_client.create_order()` for the same order
4. Order may be duplicated - but this is safer than hanging

---

**End of Implementation Plan V4**
