# Nado DN Pair Trading Bot - Comprehensive Implementation Plan

**Plan Created**: 2026-01-30
**Status**: Ready for Implementation
**Target**: Complete Nado DN Pair bot with WebSocket integration and V4 feature parity

---

## Executive Summary

### Current Status

**COMPLETED WORK:**
- Phase 0.5: WebSocket Infrastructure ✅
  - `nado_websocket_client.py` - WebSocket client with auto-reconnect, ping/pong
  - `nado_bbo_handler.py` - Real-time BBO with spread/momentum detection
  - `nado_bookdepth_handler.py` - Order book with slippage estimation
  - NadoClient WebSocket integration in `nado.py`
  - ticker_id format fix (ETH-PERP_USDT0, SOL-PERP_USDT0)
  - `place_ioc_order` with IOC order type
  - `_round_quantity_to_size_increment`
  - $100 hedge test successful - 4 second cycle time

**CURRENT ISSUES:**
1. **BookDepth slippage returns 999999 bps** - WebSocket connects but BookDepth handler not receiving data
2. **SOL trading verification needed** - Previous issue where SOL wasn't actually filling
3. **Fill monitoring requires subaccount** - User doesn't have one

**REMAINING FROM ORIGINAL PLAN:**
- Phase 2.1: V4 Helper Functions Port (`extract_filled_quantity`, `calculate_timeout`)
- Phase 3: Full WebSocket + DN Pair Strategy Integration
- Phase 4: Production Testing & Deployment

### Technical Context

**Files:**
- `/Users/botfarmer/2dex/exchanges/nado.py` - Nado exchange client
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - DN pair strategy
- `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py` - V4 reference

**Nado Configuration:**
- Testnet: `https://gateway.test.nado.xyz/v1/subscribe`
- Product IDs: ETH=4, SOL=8
- Target: $100 notional each side
- Current cycle time: ~4 seconds

**WebSocket Infrastructure:**
- Public streams: BBO, BookDepth (50ms), Trade
- Authenticated streams: Fill, PositionChange (REQUIRE SUBACCOUNT)
- No subaccount = Cannot use Fill/PositionChange streams

---

## Priority Task Matrix

| Priority | Task | Impact | Effort | Status |
|----------|------|--------|--------|--------|
| **P0** | Fix BookDepth data flow | HIGH | Medium | Blocked |
| **P0** | Verify SOL trading | HIGH | Low | Unknown |
| **P1** | Port V4 helper functions | MEDIUM | Low | Pending |
| **P1** | Production testing | HIGH | Medium | Pending |
| **P2** | Add fill monitoring (optional) | LOW | High | Blocked |

---

## Implementation Plan

### Phase 1: Critical Bug Fixes (Priority: P0)

#### Task 1.1: Fix BookDepth Data Flow

**Issue**: BookDepth handler connects but `estimate_slippage()` returns 999999 bps

**Root Cause Analysis Needed:**
1. WebSocket subscription to `book_depth` stream
2. Message parsing in `_on_bookdepth_message()`
3. Order book state management

**Investigation Steps:**
1. Add logging to BookDepth handler:
   - Log incoming messages
   - Log bid/ask updates
   - Log order book state after each update
2. Verify WebSocket subscription message format
3. Check if Nado testnet is sending BookDepth data
4. Test with manual WebSocket connection

**Acceptance Criteria:**
- BookDepth handler receives and parses messages
- `self.bids` and `self.asks` contain data
- `estimate_slippage()` returns realistic values (<100 bps)
- Integration test passes with $100 order

**Files to Modify:**
- `/Users/botfarmer/2dex/exchanges/nado_bookdepth_handler.py` - Add debug logging
- `/Users/botfarmer/2dex/exchanges/nado.py` - Verify subscription

**Estimated Time**: 2-4 hours

---

#### Task 1.2: Verify SOL Trading

**Issue**: Previous SOL orders may not have actually filled

**Verification Steps:**
1. Check SOL order size rounding
2. Verify SOL product_id=8 mapping
3. Test SOL IOC order placement
4. Monitor fill confirmation
5. Check position reconciliation

**Acceptance Criteria:**
- SOL order quantity rounds correctly (0.1 SOL increment)
- SOL IOC orders fill within 1 second
- Position reconciliation shows SOL position
- Test trade completes successfully

**Files to Modify:**
- `/Users/botfarmer/2dex/exchanges/nado.py` - Verify `_round_quantity_to_size_increment()`
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add SOL-specific logging

**Estimated Time**: 1-2 hours

---

### Phase 2: V4 Feature Porting (Priority: P1)

#### Task 2.1: Port V4 Helper Functions

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py`

**Functions to Port:**

1. **`calculate_timeout(quantity: Decimal) -> int`** (lines 18-47)
   - Piecewise timeout calculation
   - 0.1 ETH → 5s, 0.5 ETH → 10s, 1.0 ETH → 20s

2. **`extract_filled_quantity(order_result: dict) -> Decimal`** (lines 50-88)
   - Extract filled quantity from various order result formats
   - Handles: `state/traded_size`, `size`, list format, metadata

**Implementation Location:**
- Add to `/Users/botfarmer/2dex/exchanges/nado.py` as standalone functions
- Use in DN pair strategy for timeout handling

**Acceptance Criteria:**
- Functions ported from V4 reference
- Unit tests for all edge cases
- Integration with DN pair strategy
- Timeout logic matches V4 behavior

**Files to Modify:**
- `/Users/botfarmer/2dex/exchanges/nado.py` - Add functions
- `/Users/botfarmer/2dex/tests/test_v4_helpers.py` - Create unit tests

**Estimated Time**: 2 hours

---

### Phase 3: Production Testing (Priority: P1)

#### Task 3.1: End-to-End Testing

**Test Scenarios:**

1. **Small Size Test** ($10 notional)
   - BUILD cycle: ETH + SOL entry
   - CLOSE cycle: Exit both positions
   - Verify: Fill rate, PnL calculation, position reconciliation

2. **Target Size Test** ($100 notional)
   - 5 consecutive cycles
   - Verify: Cycle time, slippage, fees
   - Target: <10s per cycle

3. **Stress Test** ($200 notional)
   - 10 cycles with market volatility
   - Verify: No failed orders, accurate PnL

**Acceptance Criteria:**
- 100% fill rate on BUILD cycles
- >95% fill rate on CLOSE cycles
- Average cycle time <10s
- Position drift <1%
- PnL accurate to ±$0.01

**Files to Modify:**
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add test modes
- `/Users/botfarmer/2dex/tests/test_integration.py` - Create integration tests

**Estimated Time**: 3-4 hours

---

### Phase 4: Optional Enhancements (Priority: P2)

#### Task 4.1: Fill Monitoring (Requires Subaccount)

**Blocker**: User doesn't have subaccount

**Implementation Steps:**
1. Create Nado subaccount
2. Implement EIP-712 StreamAuthentication
3. Subscribe to Fill stream
4. Subscribe to PositionChange stream
5. Implement fill monitoring logic

**Acceptance Criteria:**
- Fill stream receives order updates
- PositionChange stream tracks positions
- Fill detection <100ms via WebSocket
- Position reconciliation via WebSocket

**Files to Modify:**
- `/Users/botfarmer/2dex/exchanges/nado.py` - Add authenticated stream support
- `/Users/botfarmer/2dex/exchanges/nado_websocket_client.py` - Add authentication

**Estimated Time**: 4-6 hours

---

## Detailed Task Breakdown

### Task 1.1: BookDepth Debug Plan

**Step 1: Add Logging to BookDepth Handler**

```python
# In nado_bookdepth_handler.py
async def _on_bookdepth_message(self, message: Dict) -> None:
    self.logger.debug(f"BookDepth message: {message}")

    # Log after processing
    self.logger.debug(f"Bids count: {len(self.bids)}, Asks count: {len(self.asks)}")
    if self.bids:
        best_bid, bid_qty = self.get_best_bid()
        self.logger.debug(f"Best bid: {best_bid} ({bid_qty})")
    if self.asks:
        best_ask, ask_qty = self.get_best_ask()
        self.logger.debug(f"Best ask: {best_ask} ({ask_qty})")
```

**Step 2: Verify WebSocket Subscription**

```python
# In nado.py - Check subscription
await self._bookdepth_handler.start()
self.logger.log(f"BookDepth subscriptions: {self._ws_client._subscriptions}", "INFO")
```

**Step 3: Manual WebSocket Test**

```bash
# Connect to Nado WebSocket manually
wscat -c wss://gateway.test.nado.xyz/v1/subscribe
# Send subscription message
{"method": "subscribe", "stream": {"type": "book_depth", "product_id": 4}, "id": 1}
# Observe if messages arrive
```

**Possible Root Causes:**
1. Wrong stream type name (should be `book_depth` not `bookdepth`)
2. Product ID mismatch
3. Nado testnet not sending BookDepth data
4. Message format mismatch

**Resolution Strategy:**
- If stream name wrong: Fix subscription
- If product ID wrong: Update mapping
- If no data: Use REST API fallback
- If format wrong: Update parser

---

### Task 2.1: V4 Helper Functions Implementation

**Function 1: `calculate_timeout()`**

```python
def calculate_timeout(quantity: Decimal) -> int:
    """
    Calculate timeout based on order size with realistic microstructure awareness.

    Piecewise logic for predictable timeout values:
    - 0.1 ETH → 5s (quick fills at BBO)
    - 0.5 ETH → 10s (moderate spread)
    - 1.0 ETH → 20s (must look deeper)
    """
    quantity_float = float(quantity)

    if quantity_float <= 0.1:
        return 5
    elif quantity_float <= 0.5:
        return 10
    else:
        return 20
```

**Function 2: `extract_filled_quantity()`**

```python
def extract_filled_quantity(order_result: dict) -> Decimal:
    """
    Extract filled quantity from order result.

    Handles various order result formats:
    - dict with 'state/traded_size'
    - dict with 'size'
    - list/tuple format [price, size]
    - dict with 'metadata' (market orders return 0)
    """
    try:
        # Try direct key access first
        if 'state' in order_result and 'traded_size' in order_result['state']:
            return Decimal(order_result['state']['traded_size'])

        # Try metadata access (WebSocket format)
        if 'metadata' in order_result:
            return Decimal('0')

        # Try list format [price, size]
        if isinstance(order_result, (list, tuple)) and len(order_result) >= 2:
            return Decimal(order_result[1])

        # Try dict format {'price': ..., 'size': ...}
        if isinstance(order_result, dict):
            if 'size' in order_result:
                return Decimal(order_result['size'])
            if 'traded_size' in order_result:
                return Decimal(order_result['traded_size'])

        return Decimal('0')

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return Decimal('0')
```

**Integration Points:**
- Use `calculate_timeout()` in `place_close_order()` for POST_ONLY timeout
- Use `extract_filled_quantity()` in `wait_for_fill()` for fill detection

---

## Testing Strategy

### Unit Tests

```python
# tests/test_v4_helpers.py
def test_calculate_timeout_small():
    assert calculate_timeout(Decimal('0.05')) == 5
    assert calculate_timeout(Decimal('0.1')) == 5

def test_calculate_timeout_medium():
    assert calculate_timeout(Decimal('0.3')) == 10
    assert calculate_timeout(Decimal('0.5')) == 10

def test_calculate_timeout_large():
    assert calculate_timeout(Decimal('1.0')) == 20
    assert calculate_timeout(Decimal('2.0')) == 20

def test_extract_filled_quantity_full():
    result = {'state': {'traded_size': '1000000000000000000'}}
    assert extract_filled_quantity(result) == Decimal('1.0')

def test_extract_filled_quantity_partial():
    result = {'state': {'traded_size': '500000000000000000'}}
    assert extract_filled_quantity(result) == Decimal('0.5')

def test_extract_filled_quantity_zero():
    result = {'metadata': {}}
    assert extract_filled_quantity(result) == Decimal('0')
```

### Integration Tests

```python
# tests/test_bookdepth_integration.py
async def test_bookdepth_slippage_estimation():
    """Test that BookDepth provides realistic slippage estimates."""
    # Create NadoClient
    client = NadoClient({'ticker': 'ETH'})
    await client.connect()

    # Wait for BookDepth data
    await asyncio.sleep(2)

    # Estimate slippage for small order
    slippage = await client.estimate_slippage('buy', Decimal('0.01'))

    # Verify realistic value
    assert slippage < Decimal(100)  # Should be <100 bps
    assert slippage >= Decimal(0)

    await client.disconnect()
```

---

## Success Criteria

### Phase 1 Success (Critical Bugs Fixed)
- BookDepth slippage returns <100 bps for $100 orders
- SOL trading verified with successful fills
- Integration test passes with both ETH and SOL

### Phase 2 Success (V4 Features)
- `calculate_timeout()` correctly scales with order size
- `extract_filled_quantity()` handles all Nado formats
- Unit tests achieve >90% coverage

### Phase 3 Success (Production Ready)
- 5 consecutive cycles complete successfully
- Average cycle time <10s
- 100% fill rate on BUILD cycles
- Position drift <1%

### Phase 4 Success (Optional)
- Fill stream detects fills <100ms
- PositionChange stream tracks positions
- WebSocket fill monitoring replaces REST polling

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| BookDepth stream unavailable | HIGH | Use REST API fallback |
| SOL not actually trading | HIGH | Verify with test orders |
| No subaccount for fill streams | LOW | Use REST polling (current) |
| V4 functions don't port | LOW | Adapt to Nado format |
| Testnet differs from mainnet | MEDIUM | Document differences |

---

## Rollback Plan

If any phase fails:

1. **BookDepth Fix Failure**: Use REST API for slippage estimation (current fallback)
2. **SOL Trading Failure**: Disable SOL, trade ETH only
3. **V4 Port Failure**: Keep existing timeout/fill logic
4. **Production Test Failure**: Reduce position size, add more logging

---

## File Reference Summary

**Implementation Files:**
- `/Users/botfarmer/2dex/exchanges/nado.py` - Nado exchange client
- `/Users/botfarmer/2dex/exchanges/nado_websocket_client.py` - WebSocket client
- `/Users/botfarmer/2dex/exchanges/nado_bbo_handler.py` - BBO handler
- `/Users/botfarmer/2dex/exchanges/nado_bookdepth_handler.py` - BookDepth handler
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - DN pair strategy

**Reference Files:**
- `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py` - V4 helpers (lines 18-88)

**Test Files:**
- `/Users/botfarmer/2dex/tests/test_v4_helpers.py` - V4 helper unit tests
- `/Users/botfarmer/2dex/tests/test_bookdepth_integration.py` - BookDepth integration tests
- `/Users/botfarmer/2dex/tests/test_production.py` - Production scenario tests

---

## Next Steps

1. **IMMEDIATE**: Fix BookDepth data flow (Task 1.1)
2. **IMMEDIATE**: Verify SOL trading (Task 1.2)
3. **SHORT-TERM**: Port V4 helper functions (Task 2.1)
4. **MEDIUM-TERM**: Production testing (Task 3.1)
5. **OPTIONAL**: Fill monitoring with subaccount (Task 4.1)

**Estimated Total Time**: 12-18 hours (excluding optional fill monitoring)

---

## Completion Checklist

- [ ] BookDepth handler receives and parses messages
- [ ] `estimate_slippage()` returns realistic values
- [ ] SOL trading verified with test orders
- [ ] V4 helper functions ported and tested
- [ ] Production testing completed successfully
- [ ] 5 consecutive cycles with <10s average time
- [ ] 100% fill rate on BUILD cycles
- [ ] Position drift <1%
- [ ] Documentation updated
- [ ] Rollback plan tested

---

**Plan Status**: Ready for implementation
**Priority**: P0 bugs first, then P1 features
**Blockers**: None (except subaccount for fill monitoring)
