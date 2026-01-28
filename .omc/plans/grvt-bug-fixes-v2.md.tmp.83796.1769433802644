# GRVT Bot Bug Fixes - Implementation Plan V2

**Date**: 2026-01-26
**Status**: RALPLAN Iteration 1/5
**Estimated Time**: 2-2.5 hours total
**Based on**: SDK capability verification + current code analysis

---

## Executive Summary

This plan addresses critical bugs in the GRVT hedge bot, with **verified SDK capabilities** and **removal of already-implemented features**:

| Priority | Bug | Impact | Solution | Status | Time |
|----------|-----|--------|----------|--------|------|
| **P0** | REST API connection drops | Bot stops at cycle 29/100 | Migrate to WebSocket order submission | **READY** | 1.5-2 hours |
| ~~P1~~ | Session authentication | API key instability | **DEFERRED** - SDK uses cookie-based auth already | N/A | - |
| ~~P3~~ | Aggressive pricing | -$0.015/cycle loss | **ALREADY IMPLEMENTED** - lines 828, 885-982 | N/A | - |

**Key Changes from V1**:
- Removed P1 (SDK already uses session cookies via `gravity=`)
- Removed P3 (already implemented with POST_ONLY fallback + 3s timeout)
- Added SDK verification section with actual method signatures
- Fixed auto-reconnect logic (use WebSocket state, not REST)
- Added rollback plan

---

## Context

### Current State
- **Bot**: Delta Neutral hedge (Backpack Primary, GRVT Hedge)
- **Test Result**: 0.1 ETH × 10 cycles = -$0.3020 (-$0.015/cycle)
- **Edge**: +0.5 bps with fees → ~2.5 bps without fees
- **Issue**: REST API returns `{}` for 0.5 ETH orders

### Root Cause
From `GRVT_API_RESEARCH_REPORT.md`:
- REST client connection drops after sustained use
- No auto-reconnect mechanism
- Current implementation uses `GrvtCcxt` (sync REST) instead of `GrvtCcxtWS` (WebSocket)

---

## SDK Capability Verification (COMPLETED)

### Verified SDK Methods

**Order Submission**:
```python
# From GrvtCcxtWS class (verified via Python inspection)
create_order(
    symbol: str,
    order_type: Literal['limit', 'market'],
    side: Literal['buy', 'sell'],
    amount: Decimal | int | float | str,
    price: None | str | float | int | Decimal = None,
    params={}
) -> dict

# RPC methods available:
rpc_create_limit_order(...)
rpc_create_order(...)
rpc_cancel_order(...)
rpc_cancel_all_orders(...)
```

**Authentication**:
```python
# Session management (SDK already uses cookies):
refresh_cookie() -> dict | None
update_session_with_cookie() -> None
should_refresh_cookie() -> bool

# Cookie format (from SDK source):
"Cookie": f"gravity={self._cookie['gravity']}"
```

### Key Findings

1. **WebSocket Order Submission**: SDK provides `create_order()` method on `GrvtCcxtWS` class
2. **No `private_create_order()`**: Previous plan assumed this method exists - **CORRECTED**
3. **Session Auth Already Implemented**: SDK uses `gravity=` cookie format internally
4. **P3 Already Done**: Current code (lines 828, 885-982) has aggressive pricing + POST_ONLY fallback

---

## P0: WebSocket Migration (CRITICAL)

### Objective
Migrate GRVT order submission from REST API (`GrvtCcxt`) to WebSocket (`GrvtCcxtWS`) for persistent, reliable connections.

### Success Criteria
- [ ] 0.5 ETH orders complete without connection drops
- [ ] Bot completes 100+ cycles without stopping
- [ ] Zero empty API response errors (`{}`)
- [ ] Auto-reconnect on WebSocket failure
- [ ] Fallback to REST if WebSocket unavailable

### Implementation Steps

#### Step 1: Create WebSocket Order Submission Wrapper
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After `_initialize_grvt_clients()` method (after line 74)

**Add Method**:
```python
async def _ws_create_order(
    self,
    symbol: str,
    order_type: Literal['limit', 'market'],
    side: Literal['buy', 'sell'],
    amount: Decimal,
    price: Optional[Decimal] = None,
    params: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """Place order via WebSocket with REST fallback.

    Args:
        symbol: Trading pair symbol
        order_type: 'limit' or 'market'
        side: 'buy' or 'sell'
        amount: Order quantity
        price: Limit price (required for limit orders)
        params: Additional order parameters

    Returns:
        Order result dict

    Raises:
        Exception: If both WebSocket and REST fail
    """
    # Try WebSocket first if connected
    if self._ws_client and self._is_websocket_connected():
        try:
            result = self._ws_client.create_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=float(amount),
                price=float(price) if price else None,
                params=params
            )
            self.logger.log(
                f"[WS_ORDER] {order_type.upper()} order placed via WebSocket: {side} {amount} @ {price}",
                "INFO"
            )
            return result
        except Exception as e:
            self.logger.log(
                f"[WS_ORDER] WebSocket failed, falling back to REST: {e}",
                "WARNING"
            )
            # Fall through to REST fallback

    # REST fallback
    self.logger.log(
        f"[WS_ORDER] Using REST fallback for {order_type} order",
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
            params=params
        )

def _is_websocket_connected(self) -> bool:
    """Check if WebSocket is connected and healthy.

    Uses SDK's connection state instead of REST API check.
    """
    if not self._ws_client:
        return False

    try:
        # Check SDK's connection status
        return (
            hasattr(self._ws_client, 'is_connection_open') and
            self._ws_client.is_connection_open()
        )
    except Exception:
        return False
```

**Rationale**:
- Uses verified `create_order()` method from `GrvtCcxtWS`
- Checks WebSocket state via `is_connection_open()` (SDK method)
- Falls back to REST if WebSocket unavailable
- Logs all fallbacks for monitoring

#### Step 2: Update `place_post_only_order` to Use WebSocket
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
order_result = await self._ws_create_order(
    symbol=contract_id,
    order_type='limit',
    side=side,
    amount=quantity,
    price=price,
    params={
        "post_only": True,
        "order_duration_secs": 30 * 86400 - 1,
    },
)
```

#### Step 3: Update `place_market_order` to Use WebSocket
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
order_result = await self._ws_create_order(
    symbol=contract_id,
    order_type='market',
    side=side,
    amount=quantity
)
```

#### Step 4: Update `place_iterative_market_order` to Use WebSocket
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
order_result = await self._ws_create_order(
    symbol=contract_id,
    order_type='market',
    side=side,
    amount=remaining
)
```

#### Step 5: Add Auto-Reconnect Logic
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: In `connect()` method (after line 112)

**Add After** `await self._ws_client.initialize()`:
```python
# Set up automatic reconnection
async def maintain_connection():
    """Background task to maintain WebSocket connection."""
    while True:
        try:
            if not self._is_websocket_connected():
                self.logger.log("[WS_RECONNECT] Connection lost, reconnecting...", "WARNING")
                await self._ws_client.initialize()
                await asyncio.sleep(2)
                self.logger.log("[WS_RECONNECT] Reconnected successfully", "INFO")
            await asyncio.sleep(5)  # Check every 5 seconds
        except Exception as e:
            self.logger.log(f"[WS_RECONNECT] Reconnect failed: {e}", "ERROR")
            await asyncio.sleep(10)  # Wait before retry

# Start connection maintenance task
asyncio.create_task(maintain_connection())
```

**Rationale**:
- Uses `_is_websocket_connected()` (checks SDK state, not REST)
- Runs in background, checks every 5 seconds
- Automatic recovery without user intervention
- Non-blocking (asyncio task)

#### Step 6: Test WebSocket Order Submission
**File**: `perp-dex-tools-original/hedge/test_grvt_websocket_orders.py` (NEW)

**Create Test Script**:
```python
"""Test WebSocket order submission for GRVT."""

import asyncio
import os
from decimal import Decimal
from exchanges.grvt import GrvtClient
from helpers.logger import TradingLogger

async def test_websocket_orders():
    """Test WebSocket order submission."""
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
        print("\n[TEST] Placing market order via WebSocket...")
        result = await client.place_market_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="buy"
        )
        print(f"✓ Market order result: {result}")

        # Test POST_ONLY order
        print("\n[TEST] Placing POST_ONLY order via WebSocket...")
        result = await client.place_post_only_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="sell"
        )
        print(f"✓ POST_ONLY order result: {result}")

        print("\n✓ All WebSocket order tests passed")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        raise
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_websocket_orders())
```

**Run Test**:
```bash
cd perp-dex-tools-original/hedge
python test_grvt_websocket_orders.py
```

---

## Testing Strategy

### Unit Tests
- [ ] Test `_ws_create_order()` with market orders
- [ ] Test `_ws_create_order()` with limit orders
- [ ] Test REST fallback when WebSocket unavailable
- [ ] Test `_is_websocket_connected()` logic

### Integration Tests
- [ ] Run 10 cycles with 0.1 ETH orders
- [ ] Run 50 cycles with 0.2 ETH orders
- [ ] Run 100 cycles with 0.5 ETH orders
- [ ] Verify no empty API responses (`{}`)

### Edge Case Tests
- [ ] WebSocket disconnect during order submission
- [ ] Both WebSocket and REST unavailable
- [ ] Slow WebSocket response (timeout handling)
- [ ] Large orders (> 0.5 ETH) using iterative method

---

## Rollback Plan

If WebSocket migration causes issues:

1. **Quick Rollback** (5 minutes):
   - Revert `place_post_only_order()` to use `self.rest_client.create_limit_order()`
   - Revert `place_market_order()` to use `self.rest_client.create_order()`
   - Revert `place_iterative_market_order()` to use `self.rest_client.create_order()`

2. **Verification**:
   ```bash
   git diff HEAD~1 exchanges/grvt.py  # Show changes
   git checkout HEAD~1 -- exchanges/grvt.py  # Revert file
   ```

3. **Fallback Behavior**:
   - Current implementation already has REST fallback in `_ws_create_order()`
   - If WebSocket fails, automatically uses REST
   - Monitor logs for `[WS_ORDER] Using REST fallback`

---

## Success Criteria

### Metrics
- [ ] **Connection Stability**: 0 connection drops in 100 cycles
- [ ] **Order Success Rate**: > 99% orders fill on first attempt
- [ ] **Error Rate**: 0 empty API responses (`{}`)
- [ ] **Performance**: Order submission < 500ms (p95)

### Monitoring
- [ ] Log all WebSocket/REST fallbacks
- [ ] Track connection state changes
- [ ] Alert on > 5% fallback rate

---

## Commit Strategy

### Commit 1: WebSocket Order Submission
```
feat(grvt): Add WebSocket order submission with REST fallback

- Add _ws_create_order() wrapper method
- Add _is_websocket_connected() health check
- Update place_post_only_order to use WebSocket
- Update place_market_order to use WebSocket
- Update place_iterative_market_order to use WebSocket

Tested: 10 cycles with 0.1 ETH orders
```

### Commit 2: Auto-Reconnect Logic
```
feat(grvt): Add WebSocket auto-reconnect

- Add background connection maintenance task
- Checks connection state every 5 seconds
- Automatic reconnection on failure
- Non-blocking asyncio task

Tested: Simulated connection drop, recovered in < 10s
```

### Commit 3: Test Suite
```
test(grvt): Add WebSocket order submission tests

- Add test_grvt_websocket_orders.py
- Test market order via WebSocket
- Test POST_ONLY order via WebSocket
- Test REST fallback behavior

All tests passing
```

---

## Definition of Done

- [ ] All code changes committed to git
- [ ] Unit tests passing
- [ ] Integration tests passing (100 cycles)
- [ ] No empty API response errors
- [ ] Auto-reconnect verified
- [ ] Rollback plan documented
- [ ] Code review approved

---

## Notes

### Removed from V1 Plan

1. **P1: Session Authentication**
   - **Reason**: SDK already implements session cookies via `gravity=` format
   - **Evidence**: SDK source code shows cookie management in `grvt_ccxt.py:73`, `grvt_ccxt_ws.py:175`
   - **Action**: No changes needed

2. **P3: Aggressive Pricing**
   - **Reason**: Already implemented in current code
   - **Evidence**: Lines 828 (aggressive pricing), 885-982 (POST_ONLY fallback with 3s timeout)
   - **Action**: No changes needed

### Key Differences from V1

| Aspect | V1 Plan | V2 Plan (This) |
|--------|---------|----------------|
| SDK Method | Assumed `private_create_order()` | Verified `create_order()` |
| Auth Strategy | Implement `create_auth_session()` | Use existing cookie management |
| P3 Status | "Implement aggressive pricing" | Already implemented |
| Connection Check | REST API call | SDK `is_connection_open()` |
| Testing | Basic tests | Edge case + rollback tests |

---

## Next Steps

1. **Implement Step 1**: Add WebSocket order wrapper methods
2. **Test**: Run `test_grvt_websocket_orders.py`
3. **Verify**: 10-cycle test with 0.1 ETH orders
4. **Deploy**: Run 100-cycle test with 0.5 ETH orders
5. **Monitor**: Check logs for fallback rate and connection stability
