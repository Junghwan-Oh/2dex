# GRVT Order Status Verification Research

Generated: 2026-01-26

## Executive Summary

GRVT SDK provides **two mechanisms** for order status verification: (1) REST API polling via `fetch_order()` and (2) WebSocket push notifications via `subscribe()`. The REST API is the authoritative source and should be used for verification after RPC submission. WebSocket provides real-time updates but may miss messages during reconnections.

---

## Research Objectives

Investigate how to verify order status after RPC submission in GRVT SDK:
1. How order status is tracked in the SDK
2. Methods to query order status
3. Whether SDK has automatic order status updates
4. REST API query capabilities after RPC submission

---

## Key Findings

### Finding 1: REST API - Primary Verification Method

**GRVT SDK provides `fetch_order()` method for polling order status via REST API.**

**Location:** `pysdk/grvt_ccxt.py:320` and `pysdk/grvt_ccxt_pro.py:354`

**Method Signature:**
```python
# Synchronous version (GrvtCcxt)
def fetch_order(
    self,
    id: str | None = None,
    params: dict = {},
) -> dict

# Asynchronous version (GrvtCcxtPro)  
async def fetch_order(
    self,
    id: str | None = None,
    params: dict = {},
) -> dict
```

**Usage Examples:**
```python
# Query by order_id
order_data = rest_client.fetch_order(id="order_123")

# Query by client_order_id
order_data = rest_client.fetch_order(params={"client_order_id": "client_456"})
```

**Response Structure:**
```python
{
    "result": {
        "order_id": "order_123",
        "legs": [{
            "instrument": "ETH_USDT_Perp",
            "is_buying_asset": True,
            "size": "1.5",
            "limit_price": "2500.50"
        }],
        "state": {
            "status": "FILLED",  # OPEN, FILLED, CANCELLED, REJECTED, PENDING
            "traded_size": ["1.5"],
            "book_size": ["0.0"],
            "avg_fill_price": ["2500.50"]
        },
        "metadata": {
            "client_order_id": "client_456"
        }
    }
}
```

**Status Values:**
- `PENDING` - Order submitted, waiting for processing
- `OPEN` - Order active on the book
- `FILLED` - Order completely filled
- `PARTIALLY_FILLED` - Order partially filled (derived from OPEN + traded_size > 0)
- `CANCELLED` - Order cancelled
- `REJECTED` - Order rejected by exchange

---

### Finding 2: WebSocket - Real-Time Order Updates

**GRVT SDK provides WebSocket subscription for order status push notifications.**

**Location:** `pysdk/grvt_ccxt_ws.py:414` (subscribe method)

**Method Signature:**
```python
async def subscribe(
    self,
    stream: str,  # "order"
    callback: Callable,  # Function to handle order updates
    ws_end_point_type: GrvtWSEndpointType | None = None,
    params: dict = {},  # {"instrument": "ETH_USDT_Perp"}
) -> None
```

**Usage Example (from hedge/exchanges/grvt.py:321-336):**
```python
async def _subscribe_to_orders(self, callback):
    await self._ws_client.subscribe(
        stream="order",
        callback=callback,
        ws_end_point_type=GrvtWSEndpointType.TRADE_DATA_RPC_FULL,
        params={"instrument": self.config.contract_id},
    )
```

**WebSocket Message Structure:**
```python
{
    "feed": {
        "order_id": "order_123",
        "legs": [{
            "instrument": "ETH_USDT_Perp",
            "is_buying_asset": True,
            "size": "1.5",
            "limit_price": "2500.50"
        }],
        "state": {
            "status": "FILLED",
            "traded_size": ["1.5"],
            "book_size": ["0.0"],
            "avg_fill_price": ["2500.50"]
        }
    },
    "stream": "v1.order",
    "selector": "instrument=ETH_USDT_Perp"
}
```

---

### Finding 3: Hybrid Approach - WebSocket + REST API Polling

**The production implementation uses WebSocket for real-time updates with REST API polling as fallback and verification.**

**Implementation Pattern (from hedge/exchanges/grvt.py:355-418):**

```python
async def place_post_only_order(
    self, contract_id: str, quantity: Decimal, price: Decimal, side: str
) -> OrderResult:
    # 1. Submit order via REST API
    order_result = self.rest_client.create_limit_order(
        symbol=contract_id, side=side, amount=quantity, price=price,
        params={"post_only": True, "order_duration_secs": 30 * 86400 - 1},
    )
    
    # 2. Extract order identifiers
    client_order_id = order_result.get("metadata").get("client_order_id")
    order_status = order_result.get("state").get("status")
    
    # 3. Poll REST API for status updates
    while order_status in ["PENDING"] and time.time() - order_status_start_time < 10:
        await asyncio.sleep(0.05)
        order_info = await self.get_order_info(client_order_id=client_order_id)
        if order_info is not None:
            order_status = order_info.status
    
    return order_info
```

---

## Recommendations

### 1. Use REST API for Verification (Authoritative Source)

**ALWAYS use REST API `fetch_order()` to verify order status after submission.**

### 2. Use WebSocket for Real-Time Updates (Optimization)

**SUBSCRIBE to WebSocket for faster updates, but STILL verify with REST API.**

### 3. Hybrid Approach - Best of Both Worlds

**COMBINE WebSocket for speed + REST API for reliability.**

### 4. Error Recovery - Handle Empty Responses

**GRVT SDK may return empty responses - implement retry logic.**

---

## Limitations

- **WebSocket Reliability**: WebSocket messages may be lost during reconnections - always verify with REST API
- **REST API Latency**: Polling interval of 50-100ms adds latency - not suitable for HFT strategies
- **Order History Limits**: `fetch_order_history()` has pagination (max 1000 orders per query)
- **No Webhook Support**: GRVT does not provide webhook callbacks - must use WebSocket or polling
- **Rate Limiting**: Excessive REST API polling may trigger rate limits (implement backoff)

---

## Code References

**Primary SDK Files:**
- `pysdk/grvt_ccxt.py:320-351` - REST API `fetch_order()` implementation
- `pysdk/grvt_ccxt_pro.py:354-387` - Async REST API `fetch_order()` implementation
- `pysdk/grvt_ccxt_ws.py:414-453` - WebSocket `subscribe()` implementation
- `pysdk/grvt_ccxt_ws.py:282-350` - WebSocket message reader and callback dispatcher

**Production Implementation:**
- `hedge/exchanges/grvt.py:355-418` - `place_post_only_order()` with verification
- `hedge/exchanges/grvt.py:420-537` - `place_market_order()` with fill confirmation
- `hedge/exchanges/grvt.py:972-1019` - `get_order_info()` helper
- `hedge/exchanges/grvt.py:321-336` - WebSocket subscription setup
- `hedge/exchanges/grvt.py:179-298` - WebSocket callback handler

**API Documentation:**
- [GRVT Trading API - Get Order](https://api-docs.grvt.io/trading_api/#get-order)
- [GRVT Trading API - Order History](https://api-docs.grvt.io/trading_api/#order-history)
- [GRVT Trading API - Open Orders](https://api-docs.grvt.io/trading_api/#open-orders)

---

*Generated by Scientist Agent using research of GRVT SDK codebase*
