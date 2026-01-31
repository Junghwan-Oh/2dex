# DN Pair Bot Liquidation Stabilization Plan V3

## Context

### Original Request
"DN Pair Bot 청산 로직 안정화 (Liquidation Stabilization)" - Stabilize the UNWIND (liquidation) logic for the DN Pair Bot to prevent position accumulation and manual intervention requirements.

### Background

**Critical Failure Scenario (Cycle 6 - 2026-01-31 01:27:46):**
- ETH buy IOC order: **FAILED to fill** (expired)
- SOL sell IOC order: **FILLED** (0.9 SOL @ $116.71)
- Emergency unwind triggered: "SOL filled but ETH failed, closing SOL position"
- **Bot stopped with SAFETY error**
- **User required manual intervention to close positions**

**Root Cause Analysis:**
1. **IOC orders have high failure rate** - No guaranteed fill mechanism
2. **Emergency unwind is NOT guaranteed** - Uses POST_ONLY orders which can fail
3. **No position verification** - Emergency unwind claims success but never verifies
4. **Missing retry logic** - Single IOC attempt with no fallback

### User Critical Feedback (V2 Rejection)

**Rate Limit:**
- "Rate Limit 처리=websocket 쓰면 해결됨. 참조해"
- **WebSocket already solves rate limit** - no token bucket needed

**Market Orders:**
- "시장가는 웬만하면 쓰지마. 속도는 빨라지지만 pnl 음수로 나옴"
- **DO NOT use MARKET orders** - they cause negative PNL

### Architect Analysis (V3 Foundation)

**WebSocket Implementation Status:**
- **File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py` (lines 199-204)
- BBO data via WebSocket: **ALREADY IMPLEMENTED**
- BookDepth via WebSocket: **ALREADY IMPLEMENTED**
- REST API calls for market data: **ELIMINATED**

**Rate Limit Solution:**
- WebSocket streams eliminate REST API calls for BBO (100% reduction)
- BookDepth provides slippage estimation without REST (100% reduction)
- Only REST calls are for order placement (not rate limited)
- **Token bucket rate limiter: UNNECESSARY**

**IOC Order Strategy:**
- Use WebSocket BBO for real-time pricing
- Use BookDepth for slippage-aware IOC pricing
- Add retry logic with price improvement
- **NO MARKET orders (per user directive)**

---

## Solution Strategy V3

### Core Philosophy: WebSocket-First, IOC-Only, Retry-Resilient

**V3 Changes from V2:**
1. **REMOVE** Token bucket rate limiter (WebSocket solves this)
2. **REMOVE** MARKET order implementation (user directive)
3. **ENHANCE** IOC orders with WebSocket data + retry logic
4. **ADD** Position verification for emergency unwind
5. **REDUCE** effort estimate from 13h to 8h

### Key Principles

1. **WebSocket-First** - All market data from WebSocket (no REST polling)
2. **IOC-Only Execution** - No MARKET orders (per user feedback)
3. **Retry-Resilient** - Multiple IOC attempts with price improvement
4. **Position-Verified** - All unwind actions verified with position checks
5. **Slippage-Aware** - Use BookDepth to estimate fill probability

---

## Implementation Plan V3

### Phase 0: Prerequisites (WebSocket Foundation)

**Status**: ALREADY IMPLEMENTED

**Evidence:**
- WebSocket BBO handler: `/Users/botfarmer/2dex/hedge/exchanges/nado_bbo_handler.py`
- WebSocket BookDepth handler: `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`
- NadoClient WebSocket integration: `/Users/botfarmer/2dex/hedge/exchanges/nado.py` (lines 100-161)

**Verification Tasks:**

#### Task 0.1: Verify WebSocket BBO Reliability (30 min)
**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Objective**: Ensure WebSocket BBO data is reliable for pricing

**Steps**:
1. Add BBO age tracking to `BBOHandler` class
2. Log warning if BBO data is stale (>1 second old)
3. Add fallback to REST if WebSocket BBO fails

**Code Changes**:
```python
# File: hedge/exchanges/nado_bbo_handler.py
class BBOData:
    def __init__(self, ...):
        self.received_at = time.time()  # Add timestamp

    @property
    def age_seconds(self) -> float:
        return time.time() - self.received_at

# File: hedge/exchanges/nado.py
async def fetch_bbo_prices(self, contract_id: str):
    if self._ws_connected and self._bbo_handler:
        bbo = self._bbo_handler.get_latest_bbo()
        if bbo and bbo.age_seconds < 1.0:  # Fresh data
            return bbo.bid_price, bbo.ask_price
        else:
            self.logger.log(f"Stale BBO (age={bbo.age_seconds:.2f}s), using REST fallback", "WARN")
    # Fallback to REST...
```

**Acceptance Criteria**:
- BBO age logged on every fetch
- Stale BBO (>1s) triggers REST fallback
- WebSocket reconnection on stale data

---

#### Task 0.2: Verify BookDepth Slippage Estimation (30 min)
**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`

**Objective**: Ensure BookDepth provides accurate slippage estimates

**Steps**:
1. Add unit tests for slippage estimation
2. Verify slippage estimates match actual fills
3. Add confidence metric based on order book depth

**Code Changes**:
```python
# File: hedge/exchanges/nado_bookdepth_handler.py
def estimate_slippage(self, side: str, quantity: Decimal) -> Tuple[Decimal, str]:
    slippage = # existing calculation
    confidence = "HIGH" if self.get_available_liquidity(side, 5) >= quantity * 2 else "LOW"
    return slippage, confidence
```

**Acceptance Criteria**:
- Slippage estimates within 10% of actual fills
- Low liquidity warning when confidence is "LOW"
- Unit tests pass

---

### Phase 1: IOC Order Enhancement (Core Execution)

**Goal**: Improve IOC fill rate using WebSocket data + retry logic

#### Task 1.0: Slippage-Aware IOC Pricing (2 hours)
**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Objective**: Use BookDepth to price IOC orders for maximum fill probability

**Current Implementation** (lines 516-532):
```python
# Current: Simple taker pricing
if direction == 'buy':
    order_price = self._round_price_to_increment(product_id_int, best_ask)
else:
    order_price = self._round_price_to_increment(product_id_int, best_bid)
```

**Enhanced Implementation**:
```python
async def place_ioc_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
    # Get BookDepth handler
    bookdepth = self.get_bookdepth_handler()

    if bookdepth:
        # Estimate slippage at desired quantity
        estimated_slippage_bps = bookdepth.estimate_slippage(direction, quantity)

        # Check if liquidity is sufficient
        can_exit, exitable_qty = bookdepth.estimate_exit_capacity(quantity, max_slippage_bps=20)

        if not can_exit:
            # Insufficient liquidity - reduce quantity or fail
            if exitable_qty == 0:
                return OrderResult(
                    success=False,
                    error_message=f'Insufficient liquidity: slippage would exceed 20 bps for {quantity}'
                )
            quantity = exitable_qty  # Reduce to exitable quantity
            self.logger.log(f"Reduced IOC quantity to {exitable_qty} due to liquidity", "WARN")

    # Calculate aggressive price based on slippage estimate
    best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

    if direction == 'buy':
        # Aggressive buy: slightly above best ask to ensure execution
        # Add 1-2 bps above best ask for aggressive fill
        slippage_buffer_bps = min(estimated_slippage_bps, Decimal('5'))  # Max 5 bps aggressive
        order_price = best_ask * (1 + slippage_buffer_bps / 10000)
    else:
        # Aggressive sell: slightly below best bid to ensure execution
        slippage_buffer_bps = min(estimated_slippage_bps, Decimal('5'))  # Max 5 bps aggressive
        order_price = best_bid * (1 - slippage_buffer_bps / 10000)

    # Round to price increment
    product_id_int = int(contract_id)
    order_price = self._round_price_to_increment(product_id_int, order_price)
    rounded_quantity = self._round_quantity_to_size_increment(product_id_int, quantity)

    # Log pricing decision
    self.logger.log(
        f"IOC {direction.upper()}: qty={rounded_quantity}, "
        f"bid={best_bid}, ask={best_ask}, price={order_price} "
        f"(aggressive: ~{slippage_buffer_bps} bps past {direction == 'buy' and 'ask' or 'bid'})",
        "INFO"
    )

    # Place IOC order...
    # (rest of existing implementation)
```

**Key Changes**:
1. Use BookDepth to estimate required slippage
2. Add aggressive pricing buffer (max 5 bps past touch)
3. Reduce quantity if liquidity insufficient
4. Log pricing decisions for debugging

**Acceptance Criteria**:
- IOC orders use slippage-aware pricing
- Low liquidity detected before order placement
- Quantity reduced if slippage would exceed 20 bps
- Logs show aggressive pricing rationale

---

#### Task 1.1: IOC Retry Logic with Price Improvement (2 hours)
**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Objective**: Add retry mechanism for failed IOC orders

**Current Behavior**:
- Single IOC attempt
- If expired/fails, returns immediately
- No retry or price adjustment

**Enhanced Behavior**:
```python
async def place_ioc_order_with_retry(
    self,
    contract_id: str,
    quantity: Decimal,
    direction: str,
    max_retries: int = 3
) -> OrderResult:
    """
    Place IOC order with retry logic.

    Retry strategy:
    - Attempt 1: Aggressive pricing (5 bps past touch)
    - Attempt 2: More aggressive (10 bps past touch)
    - Attempt 3: Most aggressive (15 bps past touch)

    Returns:
        OrderResult with success=True if any attempt fills
    """
    best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

    for attempt in range(1, max_retries + 1):
        # Calculate aggressive price based on attempt number
        slippage_buffer_bps = Decimal(str(attempt * 5))  # 5, 10, 15 bps

        if direction == 'buy':
            order_price = best_ask * (1 + slippage_buffer_bps / 10000)
        else:
            order_price = best_bid * (1 - slippage_buffer_bps / 10000)

        # Round to increment
        product_id_int = int(contract_id)
        order_price = self._round_price_to_increment(product_id_int, order_price)

        self.logger.log(
            f"IOC retry {attempt}/{max_retries}: {direction.upper()} {quantity} @ {order_price} "
            f"({slippage_buffer_bps} bps aggressive)",
            "INFO"
        )

        # Place IOC order
        result = await self._place_ioc_order_internal(
            contract_id=contract_id,
            quantity=quantity,
            direction=direction,
            order_price=order_price
        )

        if result.success:
            self.logger.log(f"IOC filled on attempt {attempt}", "INFO")
            return result

        # Check if partially filled
        if result.status == 'PARTIALLY_FILLED' and result.filled_size > 0:
            # Retry remaining quantity
            remaining = quantity - result.filled_size
            self.logger.log(f"IOC partially filled {result.filled_size}/{quantity}, retrying {remaining}", "WARN")
            quantity = remaining
            continue  # Retry with remaining quantity

        # If no fill at all, retry with more aggressive price
        self.logger.log(f"IOC expired on attempt {attempt}, retrying with more aggressive price", "WARN")

    # All retries failed
    return OrderResult(
        success=False,
        error_message=f'IOC failed after {max_retries} retries (quantity: {quantity})'
    )

async def _place_ioc_order_internal(
    self,
    contract_id: str,
    quantity: Decimal,
    direction: str,
    order_price: Decimal
) -> OrderResult:
    """Internal IOC placement with pre-calculated price."""
    # Extract existing IOC logic from place_ioc_order (lines 543-601)
    # Use provided order_price instead of calculating it
    # ...
```

**Integration with DNPairBot**:
```python
# File: hedge/dn_pair_bot.py
async def execute_unwind(self, eth_client, sol_client):
    # OLD: Single IOC attempt
    # eth_order = await eth_client.place_ioc_order(...)

    # NEW: IOC with retry
    eth_order = await eth_client.place_ioc_order_with_retry(
        contract_id=eth_config.contract_id,
        quantity=eth_quantity,
        direction='buy',
        max_retries=3
    )
```

**Acceptance Criteria**:
- IOC retries up to 3 times with increasing aggression
- Partial fills trigger retry with remaining quantity
- Aggressive pricing: 5 bps → 10 bps → 15 bps past touch
- Logs show retry attempts and pricing changes

---

### Phase 2: Emergency Unwind Verification

**Goal**: Ensure emergency unwind actually closes positions

#### Task 2.0: Position Verification After Unwind (1.5 hours)
**File**: `/Users/botfarmer/2dex/hedge/dn_pair_bot.py`

**Objective**: Verify position actually closed after emergency unwind

**Current Implementation** (UNWIND_LOGIC blocks):
```python
# Current: No verification
self.logger.log("SOL filled but ETH failed, closing SOL position", "WARN")
await sol_client.place_close_order(...)  # Assumes success
```

**Enhanced Implementation**:
```python
async def verify_position_closed(self, client, contract_id: str, expected_position: Decimal) -> bool:
    """
    Verify that position is actually closed.

    Args:
        client: Exchange client
        contract_id: Contract to check
        expected_position: Expected position (usually 0)

    Returns:
        True if position matches expected, False otherwise
    """
    max_retries = 5
    for attempt in range(max_retries):
        await asyncio.sleep(0.5)  # Wait for position update
        actual_position = await client.get_account_positions()

        if abs(actual_position - expected_position) < Decimal('0.0001'):
            self.logger.log(
                f"Position verified: {actual_position} (expected: {expected_position})",
                "INFO"
            )
            return True

        self.logger.log(
            f"Position mismatch: {actual_position} (expected: {expected_position}), "
            f"retry {attempt + 1}/{max_retries}",
            "WARN"
        )

    return False

async def execute_emergency_unwind(self, eth_client, sol_client, eth_config, sol_config):
    """
    Emergency unwind: Close the filled leg when other leg fails.

    NEW: Verify position actually closed.
    """
    self.logger.log("EXECUTING EMERGENCY UNWIND", "ERROR")

    # Determine which leg filled (from context)
    # For example: SOL filled, ETH failed
    side_to_close = 'sell'  # Close SOL long position

    # Place POST_ONLY close order
    close_result = await sol_client.place_close_order(
        contract_id=sol_config.contract_id,
        quantity=abs(sol_position),
        price=best_price,  # Calculate from BBO
        side=side_to_close
    )

    if not close_result.success:
        self.logger.log(f"Emergency unwind FAILED: {close_result.error_message}", "ERROR")
        return False

    # NEW: Verify position actually closed
    verified = await self.verify_position_closed(
        client=sol_client,
        contract_id=sol_config.contract_id,
        expected_position=Decimal('0')
    )

    if not verified:
        self.logger.log("Emergency unwind VERIFICATION FAILED - position still open", "ERROR")
        # Try again with more aggressive pricing
        self.logger.log("Retrying emergency unwind with IOC order", "WARN")

        # Use IOC with retry as last resort
        ioc_result = await sol_client.place_ioc_order_with_retry(
            contract_id=sol_config.contract_id,
            quantity=abs(sol_position),
            direction='sell',  # Close long
            max_retries=3
        )

        if not ioc_result.success:
            self.logger.log("Emergency unwind FAILED - manual intervention required", "ERROR")
            return False

        # Verify again
        verified = await self.verify_position_closed(
            client=sol_client,
            contract_id=sol_config.contract_id,
            expected_position=Decimal('0')
        )

        if not verified:
            self.logger.log("EMERGENCY UNWIND COMPLETE FAILURE - STOPPING BOT", "ERROR")
            return False

    self.logger.log("Emergency unwind SUCCESS - position verified closed", "INFO")
    return True
```

**Acceptance Criteria**:
- Position checked after emergency unwind
- Retry with IOC if verification fails
- Bot stops if verification fails twice
- Logs clearly show verification status

---

#### Task 2.1: Enhanced Emergency Unwind with IOC Fallback (1.5 hours)
**File**: `/Users/botfarmer/2dex/hedge/dn_pair_bot.py`

**Objective**: Use IOC as fallback if POST_ONLY unwind fails

**Implementation**:
```python
async def execute_emergency_unwind_with_fallback(
    self,
    client,
    contract_id: str,
    position: Decimal,
    direction: str
) -> bool:
    """
    Execute emergency unwind with multiple fallback strategies.

    Strategy hierarchy:
    1. POST_ONLY limit order (best price, low fill probability)
    2. IOC order with retry (good price, high fill probability)
    3. FOK order (aggressive price, guaranteed fill or cancel)

    Returns:
        True if position closed, False otherwise
    """
    abs_position = abs(position)
    close_side = 'sell' if position > 0 else 'buy'

    # Strategy 1: POST_ONLY limit order
    self.logger.log(f"Emergency unwind Strategy 1: POST_ONLY {close_side} {abs_position}", "WARN")

    best_bid, best_ask = await client.fetch_bbo_prices(contract_id)
    if close_side == 'sell':
        limit_price = best_bid + client.config.tick_size  # Maker order
    else:
        limit_price = best_ask - client.config.tick_size  # Maker order

    post_only_result = await client.place_close_order(
        contract_id=contract_id,
        quantity=abs_position,
        price=limit_price,
        side=close_side
    )

    # Wait and verify
    await asyncio.sleep(1.0)
    current_position = await client.get_account_positions()

    if abs(current_position) < Decimal('0.0001'):
        self.logger.log("Emergency unwind SUCCESS (POST_ONLY)", "INFO")
        return True

    # Strategy 2: IOC with retry
    self.logger.log(f"Emergency unwind Strategy 2: IOC with retry (current pos: {current_position})", "WARN")

    ioc_result = await client.place_ioc_order_with_retry(
        contract_id=contract_id,
        quantity=abs(current_position),
        direction=close_side,
        max_retries=3
    )

    if ioc_result.success:
        # Verify
        await asyncio.sleep(0.5)
        current_position = await client.get_account_positions()

        if abs(current_position) < Decimal('0.0001'):
            self.logger.log("Emergency unwind SUCCESS (IOC)", "INFO")
            return True

    # Strategy 3: FOK (Fill-Or-Kill) - most aggressive
    self.logger.log(f"Emergency unwind Strategy 3: FOK (last resort)", "ERROR")

    # FOK with aggressive pricing (20 bps past touch)
    if close_side == 'buy':
        fok_price = best_ask * Decimal('1.002')  # 20 bps above ask
    else:
        fok_price = best_bid * Decimal('0.998')  # 20 bps below bid

    fok_result = await client.place_fok_order(
        contract_id=contract_id,
        quantity=abs(current_position),
        price=fok_price,
        side=close_side
    )

    # Final verification
    await asyncio.sleep(0.5)
    final_position = await client.get_account_positions()

    if abs(final_position) < Decimal('0.0001'):
        self.logger.log("Emergency unwind SUCCESS (FOK)", "INFO")
        return True
    else:
        self.logger.log(f"EMERGENCY UNWIND FAILED - position: {final_position}", "ERROR")
        return False
```

**Acceptance Criteria**:
- Three-tier fallback: POST_ONLY → IOC → FOK
- Position verification after each strategy
- Clear logs of which strategy succeeded
- Bot stops only if all strategies fail

---

### Phase 3: WebSocket Health Monitoring

**Goal**: Ensure WebSocket reliability for real-time data

#### Task 3.0: WebSocket Health Monitoring (1 hour)
**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Objective**: Monitor WebSocket connection health and auto-recover

**Implementation**:
```python
class WebSocketHealthMonitor:
    """Monitor WebSocket connection health."""

    def __init__(self, logger, stale_threshold_seconds: float = 2.0):
        self.logger = logger
        self.stale_threshold = stale_threshold_seconds
        self.last_message_time = time.time()
        self.message_count = 0

    def on_message(self):
        """Called on each WebSocket message."""
        self.last_message_time = time.time()
        self.message_count += 1

    def is_healthy(self) -> bool:
        """Check if WebSocket is healthy."""
        age = time.time() - self.last_message_time
        return age < self.stale_threshold

    def get_age_seconds(self) -> float:
        """Get time since last message."""
        return time.time() - self.last_message_time

# In NadoClient.__init__
self._ws_health = WebSocketHealthMonitor(self.logger.logger)

# In BBOHandler._on_bbo_message
self.ws_client._ws_health.on_message()

# In NadoClient.fetch_bbo_prices
if self._ws_connected:
    if not self._ws_health.is_healthy():
        self.logger.log(
            f"WebSocket unhealthy: last message {self._ws_health.get_age_seconds():.2f}s ago",
            "WARN"
        )
        # Trigger reconnection
        await self._reconnect_websocket()
```

**Acceptance Criteria**:
- WebSocket age logged on every BBO fetch
- Auto-reconnection triggered on stale data
- Health status visible in logs

---

#### Task 3.1: WebSocket Auto-Reconnection (1 hour)
**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Objective**: Automatically reconnect WebSocket on failure

**Implementation**:
```python
async def _reconnect_websocket(self):
    """Reconnect WebSocket with exponential backoff."""
    max_attempts = 5
    base_delay = 1.0

    for attempt in range(1, max_attempts + 1):
        try:
            self.logger.log(f"WebSocket reconnection attempt {attempt}/{max_attempts}", "WARN")

            # Disconnect existing
            if self._ws_client:
                await self._ws_client.disconnect()
            self._ws_connected = False

            # Reconnect
            await self._connect_websocket()

            # Verify data flow
            await asyncio.sleep(0.5)
            bbo = self._bbo_handler.get_latest_bbo()
            if bbo and bbo.age_seconds < 1.0:
                self.logger.log("WebSocket reconnection SUCCESS", "INFO")
                return True

        except Exception as e:
            self.logger.log(f"WebSocket reconnection attempt {attempt} failed: {e}", "ERROR")

        # Exponential backoff
        delay = base_delay * (2 ** (attempt - 1))
        await asyncio.sleep(min(delay, 30))  # Max 30s delay

    self.logger.log("WebSocket reconnection FAILED after all attempts", "ERROR")
    return False
```

**Acceptance Criteria**:
- WebSocket reconnects on failure
- Exponential backoff between attempts
- Verification after reconnection
- Logs show reconnection attempts

---

## Testing Strategy

### Unit Tests

**Test 1: Slippage Estimation**
- Mock BookDepth data
- Verify slippage calculations
- Test edge cases (zero liquidity, large orders)

**Test 2: IOC Retry Logic**
- Mock order responses (expired, partial fill, filled)
- Verify retry behavior
- Test aggressive pricing progression

**Test 3: Position Verification**
- Mock position queries
- Test verification retries
- Simulate stale position data

### Integration Tests

**Test 1: WebSocket Reliability**
- Run bot for 1 hour
- Monitor WebSocket reconnections
- Verify BBO data freshness

**Test 2: IOC Fill Rate**
- Execute 100 IOC orders
- Measure fill rate (target: >95%)
- Analyze failed orders

**Test 3: Emergency Unwind**
- Simulate failed leg scenario
- Verify emergency unwind execution
- Confirm position verification

### Simulation Tests

**Test 1: Market Stress**
- High volatility (spread widening)
- Low liquidity scenarios
- Verify graceful degradation

**Test 2: Network Issues**
- WebSocket disconnection
- REST API latency
- Verify fallback behavior

---

## Effort Estimate (V3)

| Phase | Task | Duration |
|-------|------|----------|
| Phase 0 | Task 0.1: WebSocket BBO Reliability | 0.5h |
| Phase 0 | Task 0.2: BookDepth Verification | 0.5h |
| Phase 1 | Task 1.0: Slippage-Aware IOC Pricing | 2h |
| Phase 1 | Task 1.1: IOC Retry Logic | 2h |
| Phase 2 | Task 2.0: Position Verification | 1.5h |
| Phase 2 | Task 2.1: Enhanced Emergency Unwind | 1.5h |
| Phase 3 | Task 3.0: WebSocket Health Monitor | 1h |
| Phase 3 | Task 3.1: WebSocket Auto-Reconnection | 1h |
| **Total** | | **8h** |

**V2 → V3 Reductions:**
- Remove MARKET order implementation: -4h
- Remove token bucket rate limiter: -3h
- Add WebSocket health monitoring: +2h
- **Net reduction: 13h → 8h (38% reduction)**

---

## Success Metrics

### Primary Metrics

1. **Emergency Unwind Success Rate**: 100% (verified position close)
2. **IOC Fill Rate**: >95% (with retry logic)
3. **Manual Interventions**: 0 per week
4. **WebSocket Uptime**: >99.5%

### Secondary Metrics

1. **Slippage on IOC Orders**: <10 bps average
2. **Position Verification Time**: <2 seconds
3. **WebSocket Reconnection Time**: <5 seconds
4. **Bot Uptime**: >95% (no SAFETY stops)

---

## Risk Mitigation

### Risk 1: IOC Still Fails After Retry

**Mitigation**:
- FOK order as final fallback (Strategy 3 in Task 2.1)
- Manual alert only after all strategies exhausted

### Risk 2: WebSocket Data Stale

**Mitigation**:
- Health monitoring (Task 3.0)
- Auto-reconnection (Task 3.1)
- REST fallback if WebSocket unavailable

### Risk 3: Negative PNL from Aggressive Pricing

**Mitigation**:
- Limit aggressive pricing to max 15 bps (3 retries × 5 bps)
- Use slippage estimation to avoid over-aggressive pricing
- Monitor PNL impact in simulation tests

### Risk 4: Position Verification False Positive

**Mitigation**:
- Multiple verification attempts (5 retries)
- 0.5s delay between checks
- Confirm with order status queries

---

## Rollout Plan

### Phase A: Testing (2 hours)
- Unit tests for all new components
- Integration tests with testnet
- Simulation tests with historical data

### Phase B: Staging (1 day)
- Deploy to staging environment
- Monitor WebSocket health
- Execute test unwinds

### Phase C: Production (gradual)
- Deploy to production with monitoring
- Lower position size initially (50%)
- Increase to 100% after successful unwinds

---

## Monitoring Requirements

### Metrics to Track

1. **WebSocket Health**
   - Connection uptime
   - Message latency
   - Reconnection frequency

2. **IOC Performance**
   - Fill rate (by attempt number)
   - Slippage distribution
   - Retry frequency

3. **Emergency Unwind**
   - Trigger frequency
   - Success rate (by strategy)
   - Time to close position

4. **Bot Health**
   - SAFETY stop frequency
   - Manual interventions
   - PNL impact

### Alerts

1. **WebSocket Down**: Alert if disconnected >30 seconds
2. **IOC Fill Rate <90%**: Alert if fill rate drops
3. **Emergency Unwind Failed**: Page on-call immediately
4. **Position Mismatch**: Alert if verification fails

---

## Conclusion

V3 plan simplifies the solution by:

1. **Leveraging existing WebSocket infrastructure** - No token bucket needed
2. **Removing MARKET orders** - Per user directive to avoid negative PNL
3. **Enhancing IOC orders** - Slippage-aware pricing + retry logic
4. **Adding position verification** - Ensure unwind actually works
5. **Monitoring WebSocket health** - Proactive reconnection

**Key Insight**: WebSocket already solves rate limit. The real issue is IOC fill rate, which we improve with:
- Better pricing (slippage-aware)
- Retry logic (3 attempts with increasing aggression)
- Verification (confirm position closed)

**Effort**: 8 hours (down from 13 hours in V2)

**Expected Outcome**: 100% reliable emergency unwind with >95% IOC fill rate, zero manual interventions.

---

**Status**: PLAN_READY
**Next Step**: Execute Phase 0 (Prerequisites verification)
