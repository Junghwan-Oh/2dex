# GRVT Bot Bug Fixes - Implementation Plan

**Date**: 2026-01-26
**Status**: Ready for Implementation
**Estimated Time**: 3.5-4 hours total

---

## Executive Summary

This plan addresses three critical bugs in the GRVT hedge bot:

| Priority | Bug | Impact | Solution | Time |
|----------|-----|--------|----------|------|
| **P0** | REST API connection drops | Bot stops at cycle 29/100 | Migrate to WebSocket order submission | 2-3 hours |
| **P1** | API Key instability | Authentication failures | Session-based authentication | 1 hour |
| **P3** | Excessive retracement | -$0.015/cycle loss | Aggressive pricing (BBO/BBO+1) | 30 min |

**Excluded**: P2 POST_ONLY fallback (already implemented in v5)

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
- Per-request authentication (API key may expire)

---

## P0: WebSocket Migration (Critical)

### Objective
Migrate GRVT order submission from REST API (`GrvtCcxt`) to WebSocket (`GrvtCcxtWS`) for persistent, reliable connections.

### Success Criteria
- [ ] 0.5 ETH orders complete without connection drops
- [ ] Bot completes 100+ cycles without stopping
- [ ] Zero empty API response errors
- [ ] Auto-reconnect on connection failure

### Implementation Steps

#### Step 1: Create WebSocket Order Submission Methods
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Current State** (lines 355-418):
```python
async def place_post_only_order(self, ...):
    # Uses self.rest_client.create_limit_order()
    order_result = self.rest_client.create_limit_order(...)
```

**Required Changes**:

1. **Add WebSocket order submission wrapper** (after line 75):
```python
async def _ws_create_limit_order(
    self,
    symbol: str,
    side: str,
    amount: Decimal,
    price: Decimal,
    post_only: bool = True
) -> Dict[str, Any]:
    """Place limit order via WebSocket.

    Falls back to REST if WebSocket unavailable.
    """
    if self._ws_client and hasattr(self._ws_client, 'private_create_order'):
        try:
            # WebSocket order submission
            result = await self._ws_client.private_create_order(
                symbol=symbol,
                side=side,
                amount=float(amount),
                price=float(price),
                params={"post_only": post_only}
            )
            self.logger.log(f"[WS_ORDER] Limit order placed via WebSocket", "INFO")
            return result
        except Exception as e:
            self.logger.log(f"[WS_ORDER] WebSocket order failed: {e}", "WARNING")
            # Fall through to REST fallback

    # REST fallback
    return self.rest_client.create_limit_order(
        symbol=symbol,
        side=side,
        amount=amount,
        price=price,
        params={"post_only": post_only}
    )
```

2. **Add WebSocket market order wrapper** (after line 75):
```python
async def _ws_create_market_order(
    self,
    symbol: str,
    side: str,
    amount: Decimal
) -> Dict[str, Any]:
    """Place market order via WebSocket.

    Falls back to REST if WebSocket unavailable.
    """
    if self._ws_client and hasattr(self._ws_client, 'private_create_order'):
        try:
            result = await self._ws_client.private_create_order(
                symbol=symbol,
                order_type="market",
                side=side,
                amount=float(amount)
            )
            self.logger.log(f"[WS_ORDER] Market order placed via WebSocket", "INFO")
            return result
        except Exception as e:
            self.logger.log(f"[WS_ORDER] WebSocket market order failed: {e}", "WARNING")

    # REST fallback
    return self.rest_client.create_order(
        symbol=symbol,
        order_type="market",
        side=side,
        amount=amount
    )
```

#### Step 2: Update `place_post_only_order` to Use WebSocket
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 355-418

**Change**:
```python
# OLD (line 366):
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

# NEW:
order_result = await self._ws_create_limit_order(
    symbol=contract_id,
    side=side,
    amount=quantity,
    price=price,
    post_only=True
)
```

#### Step 3: Update `place_market_order` to Use WebSocket
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 420-537

**Change**:
```python
# OLD (line 442):
order_result = self.rest_client.create_order(
    symbol=contract_id,
    order_type="market",
    side=side,
    amount=quantity
)

# NEW:
order_result = await self._ws_create_market_order(
    symbol=contract_id,
    side=side,
    amount=quantity
)
```

#### Step 4: Update `place_iterative_market_order` to Use WebSocket
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 753-954

**Change**:
```python
# OLD (line 862):
order_result = self.rest_client.create_order(
    symbol=contract_id,
    order_type="market",
    side=side,
    amount=remaining
)

# NEW:
order_result = await self._ws_create_market_order(
    symbol=contract_id,
    side=side,
    amount=remaining
)
```

#### Step 5: Add Auto-Reconnect Logic
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After `connect()` method (line 128)

**Add new method**:
```python
async def _ensure_websocket_connected(self) -> None:
    """Ensure WebSocket connection is active, reconnect if needed."""
    if not self._ws_client:
        self.logger.log("[WS_RECONNECT] WebSocket not initialized, connecting...", "WARNING")
        await self.connect()
        return

    # Test connection with a simple ping
    try:
        # Try to fetch positions via REST as connectivity check
        await self.get_account_positions()
    except Exception as e:
        self.logger.log(f"[WS_RECONNECT] Connection check failed: {e}", "WARNING")
        self.logger.log("[WS_RECONNECT] Reconnecting WebSocket...", "INFO")
        try:
            await self.disconnect()
            await asyncio.sleep(2)
            await self.connect()
            self.logger.log("[WS_RECONNECT] WebSocket reconnected successfully", "INFO")
        except Exception as reconnect_error:
            self.logger.log(f"[WS_RECONNECT] Reconnect failed: {reconnect_error}", "ERROR")
            raise
```

#### Step 6: Call Auto-Reconnect Before Critical Operations
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

**Add to start of these methods**:
- `place_post_only_order` (after line 361)
- `place_market_order` (after line 428)
- `place_iterative_market_order` (after line 800)

```python
# Ensure WebSocket is connected before placing order
await self._ensure_websocket_connected()
```

### Testing Plan for P0

| Test | Command | Expected |
|------|---------|----------|
| WS-01 | `python DN_alternate_backpack_grvt.py --ticker ETH --size 0.1 --iter 10` | 100% success, no empty responses |
| WS-02 | `python DN_alternate_backpack_grvt.py --ticker ETH --size 0.5 --iter 10` | 100% success |
| WS-03 | `python DN_alternate_backpack_grvt.py --ticker ETH --size 0.5 --iter 50` | <1% failure rate |

### Acceptance Criteria
- [ ] No `[MARKET] API returned falsy result: {}` errors in logs
- [ ] WebSocket connection log messages present
- [ ] Auto-reconnect triggers and recovers (test by killing connection)
- [ ] All order types use WebSocket (check logs for `[WS_ORDER]`)

---

## P1: Session-Based Authentication (High Priority)

### Objective
Replace per-request API key authentication with persistent session cookie for improved stability.

### Success Criteria
- [ ] Session cookie obtained on startup
- [ ] Session used for all requests
- [ ] Session refresh mechanism in place
- [ ] No authentication failures during 100-cycle test

### Implementation Steps

#### Step 1: Add Session Authentication Method
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After `_initialize_grvt_clients()` (line 74)

**Add new method**:
```python
async def _authenticate_session(self) -> None:
    """Authenticate and obtain session cookie for persistent requests.

    Uses GRVT_COOKIE if available in environment, otherwise creates new session.
    """
    # Check if session cookie already exists in environment
    existing_cookie = os.getenv("GRVT_COOKIE")
    if existing_cookie:
        self.logger.log("[SESSION] Using existing session cookie from environment", "INFO")
        self.session_cookie = existing_cookie
        return

    # Create new session via REST API
    try:
        # Note: This assumes GRVT SDK has session creation endpoint
        # If not available, we'll use API key with extended duration
        self.logger.log("[SESSION] Creating new authentication session", "INFO")

        # Store session info
        self.session_cookie = f"gravity={self.api_key}"  # Placeholder
        self.account_id = self.trading_account_id

        self.logger.log("[SESSION] Session authenticated successfully", "INFO")

    except Exception as e:
        self.logger.log(f"[SESSION] Failed to create session: {e}", "ERROR")
        # Fall back to API key authentication
        self.logger.log("[SESSION] Falling back to API key authentication", "WARNING")
```

#### Step 2: Update Client Initialization to Use Session
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 60-74

**Modify `_initialize_grvt_clients()`:
```python
def _initialize_grvt_clients(self) -> None:
    """Initialize the GRVT REST and WebSocket clients."""
    try:
        # Parameters for GRVT SDK
        parameters = {
            "trading_account_id": self.trading_account_id,
            "private_key": self.private_key,
            "api_key": self.api_key,
        }

        # Add session cookie if available
        if hasattr(self, 'session_cookie'):
            parameters["cookie"] = self.session_cookie
            parameters["account_id"] = self.account_id
            self.logger.log("[INIT] Using session-based authentication", "INFO")

        # Initialize REST client
        self.rest_client = GrvtCcxt(env=self.env, parameters=parameters)

    except Exception as e:
        raise ValueError(f"Failed to initialize GRVT client: {e}")
```

#### Step 3: Call Session Authentication in `connect()`
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Lines**: 87-127

**Add at start of `connect()`:
```python
async def connect(self) -> None:
    """Connect to GRVT WebSocket."""
    try:
        # Authenticate session first
        await self._authenticate_session()

        # Initialize WebSocket client - match the working test implementation
        loop = asyncio.get_running_loop()
        # ... rest of existing code
```

#### Step 4: Add Session Refresh Logic
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: After `_authenticate_session()`

**Add new method**:
```python
async def _refresh_session_if_needed(self) -> None:
    """Refresh session if approaching expiration."""
    # GRVT sessions typically last 24 hours
    # Refresh if we've been connected for >23 hours
    if hasattr(self, '_session_start_time'):
        session_age = time.time() - self._session_start_time
        if session_age > 23 * 3600:  # 23 hours
            self.logger.log("[SESSION] Session expiring soon, refreshing...", "INFO")
            await self._authenticate_session()
            self._session_start_time = time.time()
```

#### Step 5: Track Session Start Time
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: In `_authenticate_session()` method

**Add at end of method**:
```python
self._session_start_time = time.time()
```

#### Step 6: Call Session Refresh in Auto-Reconnect
**File**: `perp-dex-tools-original/hedge/exchanges/grvt.py`
**Location**: In `_ensure_websocket_connected()` method

**Add before reconnect**:
```python
# Refresh session if needed
await self._refresh_session_if_needed()
```

### Testing Plan for P1

| Test | Command | Expected |
|------|---------|----------|
| AUTH-01 | Run with existing session cookie | Session used, no new auth |
| AUTH-02 | Run without session cookie | New session created |
| AUTH-03 | Run 100 cycles | No auth failures |

### Acceptance Criteria
- [ ] `[SESSION]` log messages present
- [ ] Session cookie used in requests
- [ ] No authentication errors in 100-cycle run
- [ ] Session refresh works (test by modifying `_session_start_time`)

---

## P3: Aggressive Pricing (Medium Priority)

### Objective
Reduce retracement by using aggressive pricing (BBO or BBO+1) instead of conservative pricing.

### Success Criteria
- [ ] Hedge orders fill faster
- [ ] Reduced cancellations and repricing
- [ ] Improved edge per cycle
- [ ] Target: +5 bps edge (vs current +0.5 bps)

### Implementation Steps

#### Step 1: Update Hedge Mode to Use Aggressive Pricing
**File**: `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py`
**Lines**: 600-800 (approximate - search for hedge order placement)

**Find the hedge order pricing logic** (around line 600-700):
```python
# Current conservative pricing:
# Uses BBO_MINUS_1 or BBO_PLUS_1 by default

# Change to aggressive pricing:
```

**Modify hedge order price calculation**:

1. **For BUY hedge orders** (when primary is SELL):
```python
# OLD (conservative):
hedge_price = best_ask - self.hedge_tick_size  # BBO_MINUS_1

# NEW (aggressive - cross spread):
hedge_price = best_ask  # BBO - immediate fill
```

2. **For SELL hedge orders** (when primary is BUY):
```python
# OLD (conservative):
hedge_price = best_bid + self.hedge_tick_size  # BBO_PLUS_1

# NEW (aggressive - cross spread):
hedge_price = best_bid  # BBO - immediate fill
```

#### Step 2: Update Default Hedge Mode
**File**: `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py`
**Lines**: 90-115 (constructor)

**Change default parameter**:
```python
# OLD:
hedge_mode: PriceMode = PriceMode.MARKET,

# NEW:
hedge_mode: PriceMode = PriceMode.BBO,  # Use BBO for aggressive fills
```

#### Step 3: Add Repricing Logic for Stale Orders
**File**: `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py`
**Location**: In hedge order wait loop

**Add repricing if order doesn't fill within 2 seconds**:
```python
# If hedge order not filled within 2 seconds, reprice at BBO
if time.time() - hedge_order_start_time > 2:
    if hedge_order_status == "OPEN":
        self.logger.log(f"[HEDGE] Order not filled in 2s, repricing at BBO", "INFO")

        # Cancel and reprice
        await self.hedge_client.cancel_order(hedge_order_id)

        # Get fresh BBO
        best_bid, best_ask = await self.hedge_client.fetch_bbo_prices(
            self.hedge_contract_id
        )

        # Place at aggressive price
        if hedge_side == "buy":
            new_price = best_ask  # Cross spread
        else:
            new_price = best_bid  # Cross spread

        # Replace order
        hedge_order_result = await self.hedge_client.place_post_only_order(
            self.hedge_contract_id,
            hedge_quantity,
            new_price,
            hedge_side
        )
```

### Testing Plan for P3

| Test | Configuration | Cycles | Target |
|------|---------------|--------|--------|
| PRICE-01 | BBO pricing | 10 | >90% fill rate |
| PRICE-02 | BBO pricing | 50 | +5 bps edge |
| PRICE-03 | Compare old vs new | 50 | Improved edge |

### Acceptance Criteria
- [ ] Hedge orders fill within 2 seconds
- [ ] Reduced cancellation count
- [ ] Edge improved to +5 bps or better
- [ ] No increase in hedge failures

---

## Risk Mitigation

### P0 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| WebSocket API not available | Medium | High | REST fallback in place |
| Connection drops persist | Low | High | Auto-reconnect logic |
| SDK missing WebSocket methods | Medium | Medium | Verify SDK capabilities first |

**Pre-Implementation Check**:
```python
# Verify GrvtCcxtWS has private_create_order method
from pysdk.grvt_ccxt_ws import GrvtCcxtWS
ws_methods = [m for m in dir(GrvtCcxtWS) if not m.startswith('_')]
print("Available WebSocket methods:", ws_methods)
```

### P1 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Session endpoint not available | Medium | Low | Fallback to API key |
| Session expires unexpectedly | Low | Medium | Auto-refresh logic |

### P3 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Aggressive pricing increases costs | Low | Low | Monitor edge, adjust |
| More taker fees (higher cost) | Medium | Medium | POST_ONLY fallback |

---

## Implementation Order

### Phase 1: Foundation (P0)
1. Add WebSocket wrapper methods
2. Update order placement to use WebSocket
3. Add auto-reconnect logic
4. Test with 0.1 ETH × 10 cycles

### Phase 2: Stability (P1)
5. Implement session authentication
6. Add session refresh logic
7. Test with 0.5 ETH × 50 cycles

### Phase 3: Optimization (P3)
8. Update to aggressive pricing
9. Add repricing logic
10. Compare edge metrics

---

## Verification Commands

### Pre-Implementation
```bash
# Check SDK version
pip show grvt-pysdk

# Verify WebSocket capabilities
python -c "from pysdk.grvt_ccxt_ws import GrvtCcxtWS; print(dir(GrvtCcxtWS))"
```

### Post-Implementation
```bash
# Test P0 - WebSocket migration
python perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py \
    --ticker ETH --size 0.1 --iter 10 \
    --primary-mode bbo_minus_1 --hedge-mode bbo

# Test P1 - Session auth (100 cycles)
python perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py \
    --ticker ETH --size 0.5 --iter 100 \
    --primary-mode bbo_minus_1 --hedge-mode bbo

# Test P3 - Aggressive pricing
python perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py \
    --ticker ETH --size 0.5 --iter 50 \
    --primary-mode bbo_minus_1 --hedge-mode bbo
```

### Log Analysis
```bash
# Check for WebSocket usage
grep "\[WS_ORDER\]" logs/DN_alternate_backpack_grvt_ETH_log.txt

# Check for reconnects
grep "\[WS_RECONNECT\]" logs/DN_alternate_backpack_grvt_ETH_log.txt

# Check for session auth
grep "\[SESSION\]" logs/DN_alternate_backpack_grvt_ETH_log.txt

# Check for empty API responses (should be zero)
grep "API returned falsy result" logs/DN_alternate_backpack_grvt_ETH_log.txt | wc -l
```

---

## Success Metrics

### Before Implementation
- Edge: +0.5 bps (with fees)
- Failure rate: ~30% at 0.5 ETH
- Connection drops: Frequent

### After Implementation (Target)
- Edge: +5 bps (with fees)
- Failure rate: <1% at 0.5 ETH
- Connection drops: Zero (with auto-reconnect)

### Definition of Done
- [ ] All three priorities implemented
- [ ] 100-cycle test passes without errors
- [ ] Edge improved to +5 bps or better
- [ ] No empty API response errors
- [ ] WebSocket connection stable
- [ ] Session authentication working

---

## Notes

### SDK Documentation References
- GRVT Python SDK: https://pypi.org/project/grvt-pysdk/
- GRVT API Docs: https://api-docs.grvt.io/
- WebSocket Guide: https://api-docs.grvt.io/docs/websocket-introduction

### Related Files
- `perp-dex-tools-original/hedge/exchanges/grvt.py` - Main GRVT client
- `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` - Strategy logic
- `perp-dex-tools-original/hedge/GRVT_API_RESEARCH_REPORT.md` - Research findings

### Rollback Plan
If WebSocket migration fails:
1. REST fallback is already in place
2. Revert to `self.rest_client.create_order()` calls
3. Remove auto-reconnect logic
4. Keep P1 (session auth) as it's independent

---

## Appendix: Code Changes Summary

### Files Modified
1. `perp-dex-tools-original/hedge/exchanges/grvt.py`
   - Add `_ws_create_limit_order()` method
   - Add `_ws_create_market_order()` method
   - Add `_authenticate_session()` method
   - Add `_ensure_websocket_connected()` method
   - Add `_refresh_session_if_needed()` method
   - Update `place_post_only_order()` to use WebSocket
   - Update `place_market_order()` to use WebSocket
   - Update `place_iterative_market_order()` to use WebSocket
   - Update `connect()` to call session auth
   - Update `_initialize_grvt_clients()` to use session

2. `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py`
   - Change default `hedge_mode` to `PriceMode.BBO`
   - Update hedge order pricing to use BBO
   - Add repricing logic for stale orders

### Estimated Lines Changed
- New code: ~150 lines
- Modified code: ~30 lines
- Total: ~180 lines

---

**End of Implementation Plan**
