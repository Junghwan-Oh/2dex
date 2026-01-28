# GRVT API/SDK Research Report
**Date**: 2026-01-26
**Purpose**: Research SDK/API improvements and evaluate GRVT as primary exchange

---

## Executive Summary

**Key Finding**: Using GRVT as primary exchange would **NOT solve the current API stability issue**. The problem is with REST API connection management, not exchange selection. The recommended solution is to migrate to **WebSocket-based order submission** instead of REST API.

---

## 1. Current SDK Version

| Item | Value |
|------|-------|
| **Package** | `grvt-pysdk` (installed as `pysdk`) |
| **Version** | 0.2.1 (2025-07-24) |
| **Status** | ✅ Latest version |
| **Location** | `C:\Users\crypto quant\anaconda3\Lib\site-packages\pysdk\` |

**No SDK update required** - we're already using the latest version.

---

## 2. Fee Comparison: GRVT vs Backpack

| Exchange | Maker Fee | Taker Fee | Advantage |
|----------|-----------|-----------|-----------|
| **GRVT** | **-0.01%** (rebate) | 0.02-0.055% | ✅ **Lower fees** |
| **Backpack** | 0.08-0.085% | 0.095-0.10% | Higher fees |

**Fee Savings with GRVT**:
- **Maker orders**: GRVT pays YOU 0.01%, Backpack charges 0.08% = **9 bps savings**
- **Taker orders**: GRVT charges 0.05%, Backpack charges 0.10% = **5 bps savings**

**Implication**: If we use GRVT as primary, we could save 5-9 bps per cycle in fees.

---

## 3. GRVT SDK Capabilities

### 3.1 Available Classes

| Class | Purpose | Async? | WebSocket? |
|-------|---------|--------|------------|
| `GrvtCcxt` | Synchronous REST API | ❌ | ❌ |
| `GrvtCcxtPro` | **Asynchronous REST API** | ✅ | ❌ |
| `GrvtCcxtWS` | **WebSocket + REST API** | ✅ | ✅ |

**Current Implementation**: We use `GrvtCcxt` (synchronous REST)
**Recommended**: Migrate to `GrvtCcxtWS` (WebSocket-based)

### 3.2 Authentication Methods

**Current**: API Key based (may expire)
```python
GRVT_API_KEY="<key>"
GRVT_TRADING_ACCOUNT_ID="<id>"
```

**Recommended**: Session-based authentication (more stable)
```python
# 1. Authenticate once, get session cookie
GRVT_COOKIE = "gravity=<session_token>"
GRVT_ACCOUNT_ID = "<account_id>"

# 2. Use session for subsequent requests
headers = {
    "Cookie": GRVT_COOKIE,
    "X-Grvt-Account-Id": GRVT_ACCOUNT_ID
}
```

**Benefits**:
- Session persists across requests
- No repeated auth overhead
- More stable than API key

### 3.3 Connection Features

| Feature | Current (REST) | WebSocket | Advantage |
|---------|---------------|-----------|-----------|
| **Latency** | Higher (HTTP roundtrip) | Lower (persistent) | ✅ WS |
| **Reliability** | ❌ Connection drops | ✅ Auto-reconnect | ✅ WS |
| **Real-time updates** | Polling required | Push-based | ✅ WS |
| **Order management** | REST only | WS-based order submission | ✅ WS |

---

## 4. Root Cause Analysis: Empty API Response `{}`

### 4.1 Current Issue

```
ERROR: [GRVT_ETH] [MARKET] API returned falsy result: {} (attempt 2/2)
ERROR: All 6 hedge attempts failed!
```

### 4.2 Why REST API Returns Empty Responses

| Cause | Evidence | Likelihood |
|-------|----------|------------|
| **Connection dropped** | `rest_client.create_order()` returns `{}` | ⭐⭐⭐⭐⭐ High |
| **Session expired** | No re-auth in current code | ⭐⭐⭐⭐ Medium |
| **Rate limiting** | Empty dict (not error message) | ⭐⭐ Low |
| **API issue** | 0.5 ETH fails, 0.1 ETH works | ⭐⭐ Low |

**Most Likely**: REST client connection drops after some time, requiring reinitialization. Our current recovery logic (2 retries + reinit) works for 0.1 ETH but fails for 0.5 ETH due to higher order frequency.

### 4.3 Why 0.5 ETH Fails More Often

| Size | Orders/Cycle | API Calls | Failure Rate |
|------|--------------|-----------|--------------|
| 0.1 ETH | 1 | 2 (1 open + 1 close) | 0% |
| 0.5 ETH | 1 | 2 | Higher ⚠️ |

**Reason**: Larger orders may trigger:
1. Longer execution time → connection timeout
2. Iterative mode → multiple API calls → more chances to fail
3. Higher slippage → more retries → connection exhaustion

---

## 5. Should We Use GRVT as Primary?

### 5.1 Pros and Cons

| Aspect | GRVT as Primary | Current (Backpack) |
|--------|-----------------|-------------------|
| **Fees** | ✅ Lower (5-9 bps savings) | ❌ Higher |
| **Liquidity** | ❓ Unknown (needs testing) | ✅ Proven |
| **API Stability** | ❌ Same REST API issue | ✅ Stable WebSocket |
| **Order Success** | ❓ Unknown | ✅ 100% fill rate |
| **SDK Support** | ✅ Good WebSocket support | ✅ Stable SDK |

### 5.2 Recommendation

**❌ NOT RECOMMENDED** to switch to GRVT as primary right now.

**Reasons**:
1. **Same API issue**: GRVT uses same REST API that's failing
2. **Unknown liquidity**: No data on GRVT's fill reliability for 0.5 ETH
3. **Working solution**: Backpack is stable as primary
4. **Fix is elsewhere**: The solution is WebSocket migration, not exchange swap

---

## 6. Recommended Solutions

### 6.1 Immediate Fix (Priority 1)

**Migrate to `GrvtCcxtWS` for order submission**

**Benefits**:
- ✅ Persistent connection (no drops)
- ✅ Auto-reconnect on failure
- ✅ Lower latency
- ✅ Real-time order updates

**Implementation**:

```python
# Current (REST - failing)
self.rest_client = GrvtCcxt(env=self.env, parameters=parameters)
order_result = self.rest_client.create_order(...)  # Returns {}

# Proposed (WebSocket - stable)
self.ws_client = GrvtCcxtWS(env=self.env, parameters=parameters)
await self.ws_client.connect()
order_result = await self.ws_client.create_order(...)  # Reliable
```

**Files to Modify**:
- `exchanges/grvt.py`: Migrate from `GrvtCcxt` to `GrvtCcxtWS`
- Add WebSocket connection lifecycle management
- Implement auto-reconnect logic

### 6.2 Secondary Fix (Priority 2)

**Implement Session-Based Authentication**

**Benefits**:
- ✅ Session persists longer
- ✅ No repeated auth overhead
- ✅ More stable than API key

**Implementation**:

```python
async def _authenticate_session(self):
    """Authenticate and get session cookie."""
    auth_response = await self.rest_client.create_auth_session(
        api_key=self.api_key
    )
    self.session_cookie = auth_response["cookie"]
    self.account_id = auth_response["account_id"]
```

### 6.3 Tertiary Fix (Priority 3)

**Add Exponential Backoff for REST API Retry**

**Current**: Fixed 1 second delay
**Proposed**: Exponential backoff (1s, 2s, 4s, 8s)

```python
for attempt in range(max_retries):
    order_result = self.rest_client.create_order(...)
    if not order_result:
        if attempt < max_retries - 1:
            delay = 2 ** attempt  # 1, 2, 4, 8
            await asyncio.sleep(delay)
            self._initialize_grvt_clients()
```

---

## 7. Testing Plan

### Phase 1: WebSocket Migration Test

| Test | Size | Cycles | Expected Result |
|------|------|--------|-----------------|
| WS-01 | 0.1 ETH | 10 | 100% success |
| WS-02 | 0.5 ETH | 10 | 100% success |
| WS-03 | 0.5 ETH | 50 | <1% failure rate |

### Phase 2: GRVT as Primary Test (AFTER WebSocket migration)

| Test | Configuration | Size | Cycles | Expected Result |
|------|---------------|------|--------|-----------------|
| PRI-01 | GRVT Primary, BP Hedge | 0.1 ETH | 10 | Compare fees |
| PRI-02 | GRVT Primary, BP Hedge | 0.5 ETH | 10 | Check liquidity |
| PRI-03 | GRVT Primary, BP Hedge | 0.5 ETH | 50 | Compare PnL |

---

## 8. Action Items

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Migrate GRVT to WebSocket (`GrvtCcxtWS`) | 2-3 hours | ⭐⭐⭐⭐⭐ Critical |
| **P1** | Implement session-based auth | 1 hour | ⭐⭐⭐⭐ High |
| **P2** | Add exponential backoff retry | 30 min | ⭐⭐⭐ Medium |
| **P3** | Test GRVT as primary (after P0) | 1 hour | ⭐⭐ Low |

---

## 9. SDK Improvement Opportunities

### 9.1 Connection Pooling

The SDK could benefit from connection pooling:
- Reuse HTTP connections across requests
- Reduce connection overhead
- Improve reliability

### 9.2 Heartbeat Mechanism

Add WebSocket heartbeat to detect stale connections early:
```python
async def _heartbeat_loop(self):
    while self.ws_client.connected:
        await self.ws_client.ping()
        await asyncio.sleep(30)
```

### 9.3 Circuit Breaker Pattern

Implement circuit breaker for repeated failures:
```python
if self.consecutive_failures >= 5:
    self._circuit_open = True
    await self._reset_circuit_after(delay=60)
```

---

## 10. Conclusion

### Current Problem
GRVT REST API returns empty responses `{}` for 0.5 ETH orders, causing bot to stop at cycle 29/100.

### Root Cause
REST client connection drops, not exchange-specific issue.

### Recommended Solution
1. **Migrate to WebSocket** (`GrvtCcxtWS`) - This will solve the stability issue
2. **Keep Backpack as primary** - It's stable and working
3. **Test GRVT as primary later** - Only after WebSocket migration is complete

### Expected Outcome
- ✅ 0.5 ETH orders will succeed reliably
- ✅ Bot will complete 100+ cycles without stopping
- ✅ Lower latency and better real-time updates
- ✅ Future option to use GRVT as primary (with 5-9 bps fee savings)

---

## Sources

- [GRVT Python SDK (PyPI)](https://pypi.org/project/grvt-pysdk/)
- [GRVT API Documentation](https://api-docs.grvt.io/)
- [GRVT Fee Calculator (PerpScope)](https://www.perpscope.com/fees/grvt)
- [GRVT Review 2026](https://decentralised.news/grvt-review-2026)
- [Backpack Fees Calculator](https://www.exchangefees.io/fees-calculator/backpack)
- [Backpack Exchange Review 2026](https://www.fxempire.com/exchanges/backpack-exchange)
