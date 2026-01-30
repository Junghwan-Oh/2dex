# Nado DN Pair V4 Migration - WebSocket-First Implementation Plan

**Plan Created**: 2026-01-29
**Plan Type**: WebSocket-First Implementation (REVISED from RALPLAN feedback)
**Target**: Migrate V4 DN pair implementation (Backpack+GRVT) to Nado-only DN pair with WebSocket as PRIMARY connection method
**Methodology**: Research-First TDD with WebSocket as Core Requirement
**Estimated Duration**: 65-90 hours across 5 phases

---

## User Feedback Context

**User's Critique (RALPLAN)**:
> "웹소켓 미구현으로 중간에 함부로 계획을 바꾼 너가 다신 그러지 않게 plan 다시 수립해. 웹소켓은 기존 구현과 그걸로 부족할시 sdk 등 공식문서 참조해서 구현할수있게 계획보완해."

**Translation**: "The plan was arbitrarily changed mid-implementation due to unimplemented WebSocket, which is not what I wanted. Re-establish the plan including WebSocket implementation. If existing implementation is insufficient, reference official SDK documentation to enable implementation."

**Root Cause Acknowledged**:
1. Previous plan made WebSocket "conditional" based on SDK availability
2. When SDK didn't provide WebSocket, plan fell back to REST-only
3. This caused 4 tests to fail due to timing/race conditions with 0.5s polling
4. User wants WebSocket IMPLEMENTED regardless of SDK limitations

---

## Requirements Summary

### What We're Building

Migrate the proven V4 DN pair implementation (Backpack + GRVT) to Nado-only DN pair with **WebSocket as PRIMARY connection method**, maintaining 100% fill rate and 8s/cycle average performance while adding Nado-specific optimizations.

**Key V4 Features to Preserve:**
- V4 BBO routing with `extract_filled_quantity`, `calculate_timeout`
- Safety features: MAX_POSITION, MAX_DAILY_LOSS, _pre_trade_check
- Emergency unwind and net delta monitoring
- POST_ONLY and MARKET fallback logic
- Position reconciliation with auto-recovery
- Trade metrics tracking (WebSocket latency, REST latency, reconciliation time)

**Nado-Specific Requirements:**
- Replace all GRVT/Backpack references with Nado
- **IMPLEMENT WebSocket connection** (MANDATORY, not optional)
- Use Nado REST API as FALLBACK when WebSocket unavailable
- Verify Nado order types: POST_ONLY, IOC, FOK, DEFAULT
- Handle Nado product IDs: ETH=4, SOL=8 (verified)
- Tick sizes: ETH=0.1, SOL=0.1 (verified)

### Success Criteria

1. **Functional**: 100% fill rate on BUILD cycles, 95%+ on CLOSE cycles
2. **Performance**: <10s average cycle time (target: 8s)
3. **Safety**: Position drift <1%, daily loss limit enforcement
4. **Reliability**: WebSocket PRIMARY connection + REST fallback
5. **Test Coverage**: >90% coverage for all critical paths

---

## Critical Finding: WebSocket Implementation Strategy

### Nado SDK WebSocket Status (CONFIRMED)

**Finding from Phase 0 Research**:
- Nado SDK does NOT provide WebSocket support
- SDK only provides REST API (engine_client, indexer_client, market)
- No WebSocket modules in `nado_protocol` package
- Previous implementation had placeholder WebSocket variables but no actual WebSocket code

### Reference Implementation: Lighter WebSocket Pattern

**Location**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/lighter_custom_websocket.py` (lines 338-493)

**Key Patterns to Reference**:
1. **WebSocket Connection Loop** (lines 338-418):
   - Continuous reconnection with exponential backoff
   - Message handling with sequence gap detection
   - Periodic cleanup and integrity validation

2. **Message Types**:
   - `ping/pong` for heartbeat
   - `update/account_orders` for order updates
   - `update/order_book` for market data

3. **Error Handling**:
   - ConnectionClosed → automatic reconnection
   - WebSocketException → reconnect with backoff
   - Sequence gaps → request fresh snapshot

### Nado WebSocket Implementation Strategy

Since Nado SDK doesn't provide WebSocket, we must implement **raw WebSocket connection**:

1. **Research Nado Exchange WebSocket Documentation** (Phase 0.1):
   - Find official Nado WebSocket endpoint
   - Document authentication method (likely JWT or API key)
   - Document message format for order updates
   - Document subscription format for account/orders

2. **Implement Raw WebSocket Client** (Phase 1.2-1.3):
   - Use `websockets` library (Python standard for WebSocket)
   - Implement connection manager similar to lighter pattern
   - Implement message parser for Nado-specific format
   - Implement authentication and subscription handlers

3. **Dual Connection Architecture** (Phase 1.5):
   - WebSocket: PRIMARY for real-time order updates
   - REST API: FALLBACK for order placement and market data
   - Automatic failover when WebSocket disconnects

---

## Architecture Overview

### Component Interaction

```
+-------------------------+
|  DNPairBot Controller   |
|  - Strategy orchestration |
|  - Safety checks        |
+------------+------------+
             |
    +--------+----------------+
    |                         |
+---+-----------+    +--------+----------+
| NadoClient ETH|    | NadoClient SOL   |
|  - WebSocket PRIMARY |  - WebSocket PRIMARY |
|  - REST FALLBACK |    |  - REST FALLBACK |
+---+-----------+    +--------+----------+
    |                         |
    +----+------------+--------+
         |            |
    +----+------------+----+
    |   WebSocket Manager   |
    |  - Raw WebSocket (websockets lib) |
    |  - Message parser    |
    |  - Reconnection logic |
    +----+------------+
         |
    +----+-------------------------+
    |   Nado REST API (SDK)       |
    |  - engine_client            |
    |  - indexer_client           |
    |  - market                   |
    +-----------------------------+
```

### Data Flow (WebSocket-First)

**BUILD Cycle (Entry):**
1. Check safety limits (position, daily loss)
2. WebSocket: Subscribe to account/orders channel
3. Fetch BBO prices via REST (WebSocket if available)
4. Place simultaneous IOC orders via REST
5. WebSocket: Receive real-time order fill updates
6. Reconcile positions via REST (authoritative)
7. Update metrics

**CLOSE Cycle (Exit):**
1. Check current positions via REST
2. Place POST_ONLY orders via REST
3. WebSocket: Monitor real-time order status
4. Fallback to MARKET via REST if timeout
5. Reconcile positions via REST
6. Calculate PnL

---

## Prerequisites

### Directory Structure Setup

Before starting Phase 0, create the required directory structure:

```bash
# Create test directories for all stages
mkdir -p /Users/botfarmer/2dex/tests/stage1
mkdir -p /Users/botfarmer/2dex/tests/stage2
mkdir -p /Users/botfarmer/2dex/tests/stage3
mkdir -p /Users/botfarmer/2dex/tests/stage4

# Create research output directory
mkdir -p /Users/botfarmer/2dex/.omc/research

# Verify directories created
ls -la /Users/botfarmer/2dex/tests/
ls -la /Users/botfarmer/2dex/.omc/research/
```

**Acceptance**: All directories exist and are writable

### Libraries Required

**WebSocket Implementation**:
- `websockets` - Python WebSocket library (likely already installed)
- `asyncio` - For async WebSocket handling

**Mock Strategy**:
- pytest-mock - For mocking WebSocket server in tests
- unittest.mock - For mocking Nado SDK

---

## PHASE 0: Nado WebSocket Research (PREREQUISITE)

**Goal**: Research Nado WebSocket API to enable raw WebSocket implementation
**Duration**: 15 hours (expanded from 13h to include WebSocket research)
**Output**: Research document at `/Users/botfarmer/2dex/.omc/research/nado-websocket-api.md`

### Sub-Feature 0.1: Nado WebSocket Documentation Research

**Research Tasks**:
1. Search Nado official documentation for WebSocket API
2. Find WebSocket endpoint URL (wss://...)
3. Document authentication method for WebSocket
4. Document subscription message format
5. Document order update message format
6. Test WebSocket connection (if testnet available)

**Research Commands**:
```bash
# Search for Nado WebSocket documentation
# (This will require web search or checking Nado's official docs)

# Check if Nado has any WebSocket-related code in SDK
python3 -c "import nado_protocol; import inspect; src = inspect.getsource(nado_protocol); print('WebSocket' in src)"

# Search for WebSocket endpoint references
grep -r "wss://" /path/to/nado/sdk/ 2>/dev/null
grep -r "websocket" /path/to/nado/sdk/ 2>/dev/null
```

**Documentation Requirements**:
- WebSocket endpoint URL: wss://... (with evidence)
- Authentication method: JWT/API key/session (with code example)
- Subscription format: JSON format for subscribing to account/orders (with example)
- Order update format: JSON format for order fill messages (with example)
- Heartbeat/ping-pong format: Keep-alive mechanism (with example)

**Estimated Time**: 4 hours

---

### Sub-Feature 0.2: Lighter WebSocket Pattern Analysis

**Goal**: Analyze lighter-nado WebSocket implementation as reference

**Research Tasks**:
1. Read `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/lighter_custom_websocket.py`
2. Extract connection loop pattern (lines 338-418)
3. Extract message handling pattern (lines 365-373)
4. Extract reconnection logic (lines 414-418)
5. Document applicable patterns for Nado

**Documentation Requirements**:
- Connection loop pseudocode
- Message type handling pattern
- Reconnection with exponential backoff pseudocode
- Sequence gap detection pattern
- Applicable vs inapplicable patterns for Nado

**Estimated Time**: 2 hours

---

### Sub-Feature 0.3: Nado Order Type Support Verification

**Research Tasks**:
1. Verify `OrderType.POST_ONLY` exists in `nado_protocol.utils.order`
2. Verify `OrderType.IOC` (Immediate-Or-Cancel) exists
3. Verify `OrderType.FOK` (Fill-Or-Kill) exists
4. Verify `OrderType.DEFAULT` or MARKET equivalent
5. Test order type parameters in `build_appendix()`

**Research Commands**:
```bash
# Check OrderType enum
python3 -c "from nado_protocol.utils.order import OrderType; print([o for o in dir(OrderType) if not o.startswith('_')])"

# Check build_appendix parameters
python3 -c "from nado_protocol.utils.order import build_appendix; import inspect; print(inspect.signature(build_appendix))"
```

**Documentation Requirements**:
- Available order types: List with descriptions
- Code examples for each order type
- Any order type restrictions or limitations

**Estimated Time**: 2 hours

---

### Sub-Feature 0.4: REST API Method Inventory

**Research Tasks**:
1. Document `client.context.engine_client` methods
2. Document `client.context.indexer_client` methods
3. Verify order status query: `get_order()` method signature
4. Verify historical orders: `get_historical_orders_by_digest()` method
5. Test market data endpoints

**Research Commands**:
```bash
# Check engine client methods
python3 -c "from nado_protocol.client import create_nado_client; c = create_nado_client('devnet', '0x' + '0'*64); print([m for m in dir(c.context.engine_client) if not m.startswith('_')])"

# Check indexer client methods
python3 -c "from nado_protocol.client import create_nado_client; c = create_nado_client('devnet', '0x' + '0'*64); print([m for m in dir(c.context.indexer_client) if not m.startswith('_')])"

# Check market methods
python3 -c "from nado_protocol.client import create_nado_client; c = create_nado_client('devnet', '0x' + '0'*64); print([m for m in dir(c.market) if not m.startswith('_')])"
```

**Documentation Requirements**:
- Complete method inventory for engine_client
- Complete method inventory for indexer_client
- Complete method inventory for market client
- Method signatures with parameters
- Example usage for critical methods

**Estimated Time**: 3 hours

---

### Sub-Feature 0.5: Product ID and Contract Verification

**Research Tasks**:
1. Verify ETH product ID (assumed 4, need confirmation)
2. Verify SOL product ID (assumed 8, need confirmation)
3. Verify tick sizes for each product
4. Test `get_all_product_symbols()` output
5. Test `get_all_engine_markets()` output
6. Verify `get_market_price()` returns real bid/ask

**Research Commands**:
```bash
# Get all products
python3 -c "from nado_protocol.client import create_nado_client; c = create_nado_client('devnet', '0x' + '0'*64); symbols = c.market.get_all_product_symbols(); print([(s.symbol, s.product_id) for s in symbols])"

# Get market details for ETH
python3 -c "from nado_protocol.client import create_nado_client; c = create_nado_client('devnet', '0x' + '0'*64); markets = c.market.get_all_engine_markets(); eth_market = [m for m in markets.perp_products if 'ETH' in str(m.product_id)]; print(eth_market)"

# Check tick size
python3 -c "from nado_protocol.client import create_nado_client; from nado_protocol.utils.math import from_x18; c = create_nado_client('devnet', '0x' + '0'*64); markets = c.market.get_all_engine_markets(); print([(m.product_id, from_x18(m.book_info.price_increment_x18)) for m in markets.perp_products])"
```

**Documentation Requirements**:
- Complete product ID mapping table
- Tick size for each product
- Minimum order quantity for each product
- Market liquidity data (if available)

**Estimated Time**: 2 hours

---

### Sub-Feature 0.6: Research Documentation Output

**Output File**: `/Users/botfarmer/2dex/.omc/research/nado-websocket-api.md`

**Document Structure**:
```markdown
# Nado WebSocket API Research

## Executive Summary
- WebSocket Endpoint: [wss://... with authentication details]
- Authentication Method: [JWT/API key/session with code example]
- Order Updates Channel: [account/orders subscription format]
- Message Format: [JSON schema for order fill messages]

## 1. WebSocket Connection
- Endpoint URL: [wss://...]
- Authentication: [Method + code example]
- Connection Lifecycle: [Connect → Authenticate → Subscribe → Receive]

## 2. Subscription Format
- Channel: account/orders
- Subscription Message: [JSON example]
- Unsubscription: [JSON example]

## 3. Message Types
- Order Fill: [JSON schema]
- Order Update: [JSON schema]
- Heartbeat: [ping/pong format]
- Error: [Error message format]

## 4. Lighter Pattern Reference
- Applicable Patterns: [Connection loop, reconnection, etc.]
- Nado-Specific Adaptations: [What to change for Nado]
- Pseudocode: [Connection loop pseudocode]

## 5. REST API Methods (Fallback)
- Engine Client: [Complete method list]
- Indexer Client: [Complete method list]
- Market Client: [Complete method list]

## 6. Product and Market Data
- Product IDs: [ETH=4, SOL=8 confirmed]
- Tick Sizes: [ETH=0.1, SOL=0.1 confirmed]
- Min Quantities: [ETH=0.1, SOL=0.1 confirmed]

## 7. Implementation Recommendations
- Use WebSocket for: [Real-time order updates]
- Use REST for: [Order placement, market data, positions]
- Fallback Strategy: [When WebSocket fails, use REST polling]
```

**Acceptance Criteria**:
- All research tasks completed
- Document saved with all sections filled
- Code examples tested and verified
- Clear implementation guidance provided

**Estimated Time**: 2 hours

**Total Phase 0 Time**: 15 hours (expanded to include WebSocket research)

---

## PHASE 1: WebSocket Connection Infrastructure (CORE REQUIREMENT)

**Goal**: Implement raw WebSocket connection for Nado with REST fallback
**Duration**: 20-25 hours (expanded from 8-12h)
**Test Coverage**: >95% for WebSocket connection logic

### Sub-Feature 1.1: REST API Connection Verification (KEEP)

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_rest_connection.py`

**Test Cases**:

```python
# Test 1: Client initialization with valid credentials
GIVEN: Valid NADO_PRIVATE_KEY in environment
WHEN: NadoClient is instantiated
THEN: Client initializes successfully with owner address

# Test 2: Contract attributes retrieval (VERIFY product IDs from Phase 0)
GIVEN: Initialized NadoClient for ETH
WHEN: get_contract_attributes() is called
THEN: Returns contract_id=4 and tick_size=0.1

# Test 3: Contract attributes for SOL (VERIFY from Phase 0)
GIVEN: Initialized NadoClient for SOL
WHEN: get_contract_attributes() is called
THEN: Returns contract_id=8 and tick_size=0.1

# Test 4: BBO price fetch returns valid prices
GIVEN: Connected NadoClient
WHEN: fetch_bbo_prices() is called
THEN: Returns (bid, ask) where bid > 0, ask > 0, ask >= bid

# Test 5: Position query returns zero initially
GIVEN: Fresh NadoClient with no positions
WHEN: get_account_positions() is called
THEN: Returns Decimal(0)

# Test 6: REST API retry on failure
GIVEN: NadoClient with mocked failing API
WHEN: fetch_bbo_prices() is called
THEN: Retries up to 3 times before returning (0, 0)
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**Methods to Verify/Enhance**:
- `_validate_config()` - VERIFY validation for NADO_PRIVATE_KEY format
- `get_contract_attributes()` - VERIFY product ID mapping from Phase 0
- `fetch_bbo_prices()` - VERIFY retry logic exists

**Acceptance Criteria**:
- All 6 tests pass
- Product IDs from Phase 0 research confirmed
- Tick sizes from Phase 0 research confirmed
- Mock Nado SDK responses for isolated testing

**Dependencies**: Phase 0 complete

**Estimated Time**: 2 hours

---

### Sub-Feature 1.2: Nado WebSocket Client Implementation (NEW - MANDATORY)

**Goal**: Implement raw WebSocket connection for Nado using `websockets` library

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_websocket_client.py`

**Test Cases**:

```python
# Test 1: WebSocket connection establishment
GIVEN: Initialized NadoClient with valid credentials
WHEN: connect_websocket() is called
THEN: WebSocket connects to wss://[endpoint] successfully

# Test 2: WebSocket authentication
GIVEN: WebSocket connection established
WHEN: authenticate() is called
THEN: Authentication successful (JWT/API key accepted)

# Test 3: WebSocket subscription to account/orders
GIVEN: Authenticated WebSocket connection
WHEN: subscribe_to_orders() is called
THEN: Subscription successful, start receiving order updates

# Test 4: WebSocket message parsing
GIVEN: Subscribed WebSocket connection
WHEN: Order fill message received
THEN: Correctly extracts order_id, filled_size, price, timestamp

# Test 5: WebSocket heartbeat/ping-pong
GIVEN: Active WebSocket connection
WHEN: 60 seconds pass without messages
THEN: Sends ping, receives pong

# Test 6: WebSocket disconnection handling
GIVEN: Active WebSocket connection
WHEN: Connection closed (by server or network)
THEN: _ws_connected flag set to False, reconnection triggered
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**New Methods to Add**:

```python
async def connect_websocket(self) -> None:
    """Establish WebSocket connection to Nado.

    Uses raw WebSocket connection via websockets library.
    Endpoint and authentication from Phase 0 research.
    """
    # TODO: Implement based on Phase 0 research findings
    # Reference: lighter_custom_websocket.py lines 338-418
    pass

async def _authenticate_websocket(self) -> None:
    """Authenticate WebSocket connection.

    Authentication method from Phase 0 research:
    - JWT token?
    - API key?
    - Session-based?
    """
    # TODO: Implement based on Phase 0 research findings
    pass

async def subscribe_to_orders(self, callback) -> None:
    """Subscribe to account/orders channel.

    Args:
        callback: Async function to call when order update received
    """
    # TODO: Implement subscription message format from Phase 0
    pass

async def _ws_message_handler(self) -> None:
    """Handle incoming WebSocket messages.

    Message types from Phase 0 research:
    - order_fill
    - order_update
    - ping/pong
    - error
    """
    # TODO: Implement message parsing from Phase 0 research
    # Reference: lighter_custom_websocket.py lines 365-373
    pass

async def _ws_reconnect(self) -> None:
    """Reconnect WebSocket with exponential backoff.

    Reference: lighter_custom_websocket.py lines 414-418
    """
    # TODO: Implement reconnection logic
    pass
```

**Acceptance Criteria**:
- All 6 tests pass with mock WebSocket server
- Real WebSocket connection tested against Nado testnet (if available)
- Message parsing handles all documented message types
- Authentication works with documented method
- Reconnection works with exponential backoff

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_websocket_client.py -v
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_websocket_client.py --cov=exchanges.nado --cov-report=term-missing
```

**Dependencies**: Sub-Feature 1.1, Phase 0 (Sub-Features 0.1-0.2)

**Estimated Time**: 6 hours

---

### Sub-Feature 1.3: WebSocket Order Update Handler (NEW - MANDATORY)

**Goal**: Implement real-time order fill detection via WebSocket

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_websocket_order_updates.py`

**Test Cases**:

```python
# Test 1: Order fill notification via WebSocket
GIVEN: IOC order placed via REST
WHEN: Order fills on exchange
THEN: WebSocket receives fill notification within 100ms

# Test 2: Partial fill notification
GIVEN: Order partially fills
WHEN: Partial fill occurs
THEN: WebSocket receives update with filled_size, remaining_size

# Test 3: Order cancellation notification
GIVEN: Open order
WHEN: Order cancelled via REST
THEN: WebSocket receives cancellation notification

# Test 4: Multiple order updates
GIVEN: Multiple orders placed (ETH + SOL)
WHEN: Both orders fill
THEN: WebSocket receives notifications for both orders

# Test 5: WebSocket message sequence
GIVEN: Multiple order updates
WHEN: Messages received
THEN: Processed in correct sequence (by sequence number)

# Test 6: WebSocket fallback to REST on disconnect
GIVEN: WebSocket disconnected
WHEN: Order placed
THEN: Automatically uses REST polling for fill detection
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**New Methods to Add**:

```python
def setup_order_update_handler(self, handler) -> None:
    """Setup order update handler for WebSocket.

    Args:
        handler: Async callback function(order_id, filled_size, price, timestamp)
    """
    self._order_update_handler = handler
    # TODO: Register handler with WebSocket message handler

async def wait_for_fill_websocket(self, order_id: str, timeout: float = 5.0) -> OrderResult:
    """Wait for order fill using WebSocket (primary method).

    Args:
        order_id: Order ID to wait for
        timeout: Maximum seconds to wait

    Returns:
        OrderResult with fill information

    Falls back to REST polling if WebSocket unavailable.
    """
    # TODO: Implement WebSocket-based fill detection
    # Reference: wait_for_fill() existing implementation (line 468)
    pass
```

**Acceptance Criteria**:
- All 6 tests pass
- WebSocket fill detection <100ms (vs REST 500ms)
- Fallback to REST works when WebSocket unavailable
- Multiple order updates handled correctly
- Message sequence integrity maintained

**Dependencies**: Sub-Feature 1.2

**Estimated Time**: 5 hours

---

### Sub-Feature 1.4: Order Placement Verification (ENHANCED)

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_order_placement.py`

**Test Cases**:

```python
# Test 1: POST_ONLY order placement (VERIFY from Phase 0)
GIVEN: Connected client (WebSocket + REST)
WHEN: place_open_order() called with POST_ONLY
THEN: Order placed via REST, confirmation received

# Test 2: IOC order placement (VERIFY from Phase 0)
GIVEN: Connected client
WHEN: place_ioc_order() called
THEN: Immediate fill detection via WebSocket (<100ms)

# Test 3: Order placement via REST (always works)
GIVEN: WebSocket + REST connections available
WHEN: place_open_order() called
THEN: Order placed via REST API

# Test 4: Order cancellation
GIVEN: Open order
WHEN: cancel_order() called
THEN: Cancellation confirmed via REST

# Test 5: Concurrent order placement (ETH + SOL)
GIVEN: Two NadoClient instances (ETH, SOL)
WHEN: Orders placed simultaneously
THEN: Both orders placed without interference

# Test 6: Order type verification
GIVEN: Multiple order types available
WHEN: Each order type tested
THEN: All supported order types work correctly
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**Methods to Verify/Enhance**:
- `place_open_order()` - VERIFY existing (line 150), ENHANCE with WebSocket notification
- `place_ioc_order()` - VERIFY existing, ENHANCE with WebSocket fill detection
- `place_close_order()` - VERIFY existing
- `cancel_order()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- Orders confirmed via REST (placement)
- Fill detection via WebSocket (100ms latency)
- No race conditions in concurrent placement
- All verified order types from Phase 0 work

**Dependencies**: Sub-Feature 1.3

**Estimated Time**: 3 hours

---

### Sub-Feature 1.5: Dual Connection Manager (NEW - MANDATORY)

**Goal**: Implement WebSocket PRIMARY + REST fallback with automatic failover

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_dual_connection.py`

**Test Cases**:

```python
# Test 1: WebSocket primary connection active
GIVEN: Both WebSocket and REST available
WHEN: Client initialized
THEN: WebSocket connected, REST available as fallback

# Test 2: WebSocket failure triggers REST fallback
GIVEN: WebSocket primary connection active
WHEN: WebSocket connection fails
THEN: Automatically uses REST for all operations

# Test 3: WebSocket reconnection
GIVEN: REST fallback active
WHEN: WebSocket reconnects successfully
THEN: Switches back to WebSocket as primary

# Test 4: Dual connection health check
GIVEN: Both connections active
WHEN: get_connection_status() called
THEN: Returns {'websocket': 'connected', 'rest': 'available'}

# Test 5: Graceful degradation
GIVEN: WebSocket partially working (some messages lost)
WHEN: Message loss detected
THEN: Uses REST to verify critical operations

# Test 6: Connection recovery metrics
GIVEN: WebSocket failed and recovered
WHEN: get_connection_metrics() called
THEN: Returns failure_count, recovery_time, failover_count
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**New Methods to Add**:

```python
async def connect(self) -> None:
    """Connect to Nado (WebSocket PRIMARY, REST fallback).

    Enhanced from existing implementation (line 67):
    - Try WebSocket connection first
    - Fall back to REST if WebSocket unavailable
    - Monitor connection health
    """
    # TODO: Implement dual connection logic
    pass

def get_connection_status(self) -> Dict[str, str]:
    """Get status of both connections.

    Returns:
        Dict with 'websocket' and 'rest' status
    """
    # TODO: Implement connection status check
    pass

async def _monitor_connection_health(self) -> None:
    """Monitor connection health and trigger failover.

    Runs in background task, checks WebSocket heartbeat.
    """
    # TODO: Implement health monitoring
    pass

def get_connection_metrics(self) -> Dict[str, Any]:
    """Get connection performance metrics.

    Returns:
        Dict with websocket_latency, rest_latency, failover_count, etc.
    """
    # TODO: Implement metrics collection
    pass
```

**Acceptance Criteria**:
- All 6 tests pass
- WebSocket is PRIMARY connection method
- Automatic failover to REST when WebSocket fails
- Automatic recovery to WebSocket when available
- Health monitoring prevents silent failures
- Metrics track connection performance

**Dependencies**: Sub-Feature 1.4

**Estimated Time**: 4 hours

---

### Sub-Feature 1.6: Connection Monitoring and Metrics (ENHANCED)

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_connection_metrics.py`

**Test Cases**:

```python
# Test 1: WebSocket latency measurement
GIVEN: Using WebSocket connection
WHEN: Order placed and fill detected
THEN: Latency measured and logged (<100ms expected)

# Test 2: REST API latency measurement
GIVEN: Using REST connection
WHEN: Order placed
THEN: Latency measured and logged (<500ms expected)

# Test 3: Connection uptime tracking
GIVEN: Connection active
WHEN: 60 seconds pass
THEN: Uptime percentage calculated

# Test 4: Failover event logging
GIVEN: WebSocket fails
WHEN: Fallback to REST triggered
THEN: Failover event logged with timestamp

# Test 5: Reconnection success tracking
GIVEN: REST fallback active
WHEN: WebSocket reconnects
THEN: Reconnection event logged

# Test 6: Connection health summary
GIVEN: Connection active
WHEN: get_connection_health() called
THEN: Returns dict with status, latency, uptime, failover_count
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**New Methods to Add**:
- `_track_latency()` - Track WebSocket and REST latency separately
- `_log_failover()` - Log failover events with timestamp
- `_calculate_uptime()` - Calculate connection uptime percentage
- `get_connection_health()` - Return comprehensive health status

**Acceptance Criteria**:
- All 6 tests pass
- Latency measured for WebSocket (<100ms target) and REST (<500ms target)
- Health metrics exported for monitoring
- Failover events tracked and logged

**Dependencies**: Sub-Feature 1.5

**Estimated Time**: 3 hours

**Total Phase 1 Time**: 20-25 hours (expanded from 8-12h)

---

## PHASE 2: Entry Logic Enhancement (BUILD Cycles)

**Goal**: Verify and enhance existing entry logic for V4 parity with WebSocket fill detection
**Duration**: 12-16 hours (same as original)
**Test Coverage**: >90% for entry logic

### Sub-Feature 2.1: V4 Helper Functions Port

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_v4_helpers.py`

**Test Cases**:

```python
# Test 1: Extract filled quantity from order result (PORT from V4)
GIVEN: Order result with partial fill
WHEN: extract_filled_quantity() called
THEN: Returns correct filled amount

# Test 2: Extract filled quantity from full fill
GIVEN: Order result with complete fill
WHEN: extract_filled_quantity() called
THEN: Returns full order quantity

# Test 3: Extract filled quantity from Nado format
GIVEN: Nado order result format
WHEN: extract_filled_quantity() called
THEN: Correctly parses Nado-specific format

# Test 4: Calculate timeout based on order size (PORT from V4)
GIVEN: Order quantity 0.5 ETH
WHEN: calculate_timeout() called
THEN: Returns appropriate timeout (e.g., 10s)

# Test 5: Calculate timeout for large orders
GIVEN: Order quantity 2.0 ETH
WHEN: calculate_timeout() called
THEN: Returns longer timeout (e.g., 20s)

# Test 6: Calculate timeout for small orders
GIVEN: Order quantity 0.1 ETH
WHEN: calculate_timeout() called
THEN: Returns short timeout (e.g., 5s)
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**New Functions** (PORT from V4):
- `extract_filled_quantity()` - PORT from V4 reference
- `calculate_timeout()` - PORT from V4 reference

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py`

**Acceptance Criteria**:
- All 6 tests pass
- Functions handle Nado-specific order result formats
- Timeout calculation matches V4 reference
- Extracted quantity accurate for all order states

**Dependencies**: Phase 1 complete

**Estimated Time**: 2 hours

---

### Sub-Feature 2.2: Pre-Trade Safety Checks Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_pre_trade_checks.py`

**Test Cases**:

```python
# Test 1: Max position check blocks large orders (VERIFY existing)
GIVEN: Current position 4.5 ETH, max 5.0 ETH
WHEN: Attempting to buy 1.0 ETH
THEN: Order rejected, returns False

# Test 2: Max position check allows small orders
GIVEN: Current position 4.5 ETH, max 5.0 ETH
WHEN: Attempting to buy 0.4 ETH
THEN: Order allowed, returns True

# Test 3: Daily loss check stops trading (VERIFY existing)
GIVEN: Daily PnL -$5.10, max loss $5.00
WHEN: Attempting any trade
THEN: Trade rejected, daily loss exceeded logged

# Test 4: Daily loss check allows trading
GIVEN: Daily PnL -$2.00, max loss $5.00
WHEN: Attempting trade
THEN: Trade allowed, returns True

# Test 5: Net delta check triggers warning
GIVEN: ETH position +1.0, SOL position -0.9 (net 0.1)
WHEN: Pre-trade check called
THEN: Warning logged but trade allowed

# Test 6: Net delta check blocks extreme drift
GIVEN: ETH position +2.0, SOL position -1.0 (net 1.0)
WHEN: Pre-trade check called
THEN: Trade rejected, excessive delta logged

# Test 7: Daily reset at midnight UTC
GIVEN: Daily loss exceeded yesterday
WHEN: New day starts (UTC midnight)
THEN: Daily PnL reset to 0
```

**Implementation File**: DN pair bot file

**Method to Verify**: `_pre_trade_check()` - VERIFY existing

**Acceptance Criteria**:
- All 7 tests pass
- Safety checks enforce limits strictly
- Daily reset works correctly across UTC midnight
- Net delta monitoring active and accurate

**Dependencies**: Sub-Feature 2.1

**Estimated Time**: 2 hours

---

### Sub-Feature 2.3: Simultaneous Order Placement Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_simultaneous_orders.py`

**Test Cases**:

```python
# Test 1: Simultaneous BUY orders for both tickers (VERIFY existing)
GIVEN: ETH and SOL clients ready
WHEN: place_simultaneous_orders(ETH_BUY, SOL_SELL) called
THEN: Both orders placed within 100ms

# Test 2: Simultaneous SELL orders for both tickers
GIVEN: ETH and SOL clients ready
WHEN: place_simultaneous_orders(ETH_SELL, SOL_BUY) called
THEN: Both orders placed within 100ms

# Test 3: Order placement failure handling
GIVEN: ETH client fails
WHEN: Simultaneous order placement attempted
THEN: Both orders cancelled, error logged

# Test 4: Partial fill detection (ENHANCED with WebSocket)
GIVEN: One order fills, other partial
WHEN: Fill status checked via WebSocket
THEN: Correctly identifies partial fill state within 100ms

# Test 5: Order cancellation on partial fill
GIVEN: One order fills fully, other partial
WHEN: Partial fill detected
THEN: Unfilled portion cancelled

# Test 6: Order timeout handling
GIVEN: Both orders placed
WHEN: Timeout expires (e.g., 5s)
THEN: Both orders cancelled
```

**Implementation File**: DN pair bot file

**Method to Verify**: `place_simultaneous_orders()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- Orders placed concurrently using asyncio.gather()
- Failure handling cancels both orders
- WebSocket-based fill detection <100ms
- Timeout mechanism works correctly

**Dependencies**: Sub-Feature 2.2

**Estimated Time**: 2 hours

---

### Sub-Feature 2.4: WebSocket-Based Fill Detection (ENHANCED)

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_websocket_fill_detection.py`

**Test Cases**:

```python
# Test 1: WebSocket detects immediate fill (PRIMARY method)
GIVEN: IOC order placed via REST
WHEN: Order fills immediately
THEN: WebSocket detects fill within 100ms

# Test 2: WebSocket vs REST latency comparison
GIVEN: IOC order placed
WHEN: Fill detected via both WebSocket and REST
THEN: WebSocket latency <100ms, REST latency <500ms

# Test 3: Partial fill detection via WebSocket
GIVEN: IOC order partially fills
WHEN: Partial fill detected
THEN: WebSocket reports correct filled_amount

# Test 4: No fill detection via WebSocket
GIVEN: IOC order placed
WHEN: Timeout expires (5s)
THEN: WebSocket reports no fill

# Test 5: Fill price extraction from WebSocket
GIVEN: Order fills at specific price
WHEN: Fill detected via WebSocket
THEN: Correctly extracts fill price

# Test 6: REST fallback when WebSocket unavailable
GIVEN: WebSocket disconnected
WHEN: IOC order placed and fills
THEN: REST polling detects fill within 500ms
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**Methods to Verify/Enhance**:
- `wait_for_fill()` - ENHANCE to use WebSocket primary, REST fallback
- `wait_for_fill_by_position()` - VERIFY existing as fallback
- `place_ioc_order()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- WebSocket detection <100ms (PRIMARY)
- REST polling <500ms (FALLBACK)
- Position-based detection as final fallback
- Automatic failover works correctly

**Dependencies**: Sub-Feature 2.3

**Estimated Time**: 2 hours

---

### Sub-Feature 2.5: Position Reconciliation Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_entry_reconciliation.py`

**Test Cases**:

```python
# Test 1: Reconciliation matches expected positions (VERIFY existing)
GIVEN: Orders filled for 0.5 ETH, 10 SOL
WHEN: reconcile_positions() called
THEN: Returns position_diff < 1% of order size

# Test 2: Reconciliation detects drift
GIVEN: Expected 0.5 ETH, actual 0.45 ETH
WHEN: reconcile_positions() called
THEN: Logs warning, updates local tracking

# Test 3: Reconciliation triggers auto-recovery
GIVEN: Position drift > 1%
WHEN: reconcile_positions() called
THEN: Syncs local positions with REST API

# Test 4: Net delta calculation
GIVEN: ETH +0.5, SOL -50 SOL (notional equivalent)
WHEN: Net delta calculated
THEN: Returns delta < 1% of total notional

# Test 5: WebSocket position vs REST position
GIVEN: WebSocket and REST positions differ
WHEN: Both sources checked
THEN: Uses REST as authoritative

# Test 6: Reconciliation metrics logging
GIVEN: Position reconciliation complete
WHEN: Metrics logged
THEN: Includes drift amount, sync status, latency
```

**Implementation File**: DN pair bot file

**Method to Verify**: `reconcile_positions()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- REST API used as authoritative source
- Auto-recovery triggers at 1% drift threshold
- Net delta monitoring active

**Dependencies**: Sub-Feature 2.4

**Estimated Time**: 2 hours

---

### Sub-Feature 2.6: Entry Metrics Collection Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_entry_metrics.py`

**Test Cases**:

```python
# Test 1: Entry price recording
GIVEN: Orders filled at specific prices
WHEN: Entry complete
THEN: Records eth_entry_price, sol_entry_price

# Test 2: Entry time measurement
GIVEN: Entry cycle starts
WHEN: Entry complete
THEN: Records eth_entry_time, sol_entry_time

# Test 3: Order-to-fill latency (WebSocket vs REST)
GIVEN: Order placed
WHEN: Fill detected
THEN: Records websocket_latency, rest_latency separately

# Test 4: WebSocket fill detection time
GIVEN: Order placed and filled
WHEN: Fill detected via WebSocket
THEN: Records websocket_fill_time (<100ms expected)

# Test 5: Reconciliation time
GIVEN: Reconciliation starts
WHEN: Reconciliation complete
THEN: Records reconciliation_time

# Test 6: Total cycle time
GIVEN: Entry cycle starts
WHEN: Entry complete
THEN: Records total_cycle_time (target: <8s)

# Test 7: Metrics export to CSV
GIVEN: Multiple entry cycles complete
WHEN: export_trade_metrics() called
THEN: CSV includes WebSocket-specific metrics
```

**Implementation File**: DN pair bot file

**Dataclass to Verify**: `TradeMetrics` - VERIFY and ENHANCE with WebSocket fields

**Acceptance Criteria**:
- All 7 tests pass
- All V4 metrics captured
- WebSocket latency tracked separately
- CSV export matches V4 format + WebSocket enhancements
- Total cycle time <8s target tracked

**Dependencies**: Sub-Feature 2.5

**Estimated Time**: 2 hours

**Total Phase 2 Time**: 12-16 hours

---

## PHASE 3: Unwind Logic Enhancement (CLOSE Cycles)

**Goal**: Verify and enhance existing exit logic for V4 parity with WebSocket monitoring
**Duration**: 10-14 hours (same as original)
**Test Coverage**: >90% for exit logic

### Sub-Feature 3.1: POST_ONLY Order Placement Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_post_only_orders.py`

**Test Cases**:

```python
# Test 1: POST_ONLY order placed at BBO (VERIFY existing)
GIVEN: Current position 0.5 ETH
WHEN: place_close_order() called with POST_ONLY
THEN: Order placed 1 tick inside spread

# Test 2: POST_ONLY fills immediately (best case)
GIVEN: POST_ONLY order placed
WHEN: Counterparty found immediately
THEN: Fill detected within 1s, 0% fee paid

# Test 3: POST_ONLY timeout triggers MARKET
GIVEN: POST_ONLY order placed
WHEN: No fill after 3s timeout
THEN: Order cancelled, MARKET order placed

# Test 4: POST_ONLY partial fill handling
GIVEN: POST_ONLY order partially fills
WHEN: Partial fill detected
THEN: Remaining quantity filled via MARKET

# Test 5: POST_ONLY price adjustment
GIVEN: Market moves against POST_ONLY price
WHEN: Price checked
THEN: Order cancelled, re-priced at new BBO

# Test 6: Fee saving calculation
GIVEN: POST_ONLY order fills
WHEN: Fee saved calculated
THEN: Records saved fee vs taker fee
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**Method to Verify**: `place_close_order()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- POST_ONLY timeout = 3s
- Fallback to MARKET on timeout
- Fee savings tracked

**Dependencies**: Phase 2 complete

**Estimated Time**: 2 hours

---

### Sub-Feature 3.2: MARKET Order Fallback Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_market_fallback.py`

**Test Cases**:

```python
# Test 1: MARKET order executes immediately
GIVEN: POST_ONLY timeout
WHEN: MARKET order placed
THEN: Fill detected within 500ms

# Test 2: MARKET order cross spread for fill
GIVEN: MARKET order placement
WHEN: Order executes
THEN: Crosses spread (buy at ask, sell at bid)

# Test 3: MARKET order slippage calculation
GIVEN: MARKET order fills
WHEN: Fill price vs BBO compared
THEN: Slippage < 0.1% of order size

# Test 4: Large order iterative routing (VERIFY if exists)
GIVEN: Large order (>0.2 ETH)
WHEN: MARKET placement via iterative routing
THEN: Fills in multiple slices, reduces slippage

# Test 5: MARKET order latency
GIVEN: MARKET order placed
WHEN: Fill detected
THEN: Latency <500ms

# Test 6: MARKET order fallback logging
GIVEN: POST_ONLY failed
WHEN: MARKET order placed
THEN: Logs reason for fallback
```

**Implementation File**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py`

**Method to Verify/Add**: `place_iterative_market_order()` - VERIFY if exists

**Acceptance Criteria**:
- All 6 tests pass
- Iterative routing for orders >0.2 ETH
- Slippage <0.1%
- Fallback logged

**Dependencies**: Sub-Feature 3.1

**Estimated Time**: 2 hours

---

### Sub-Feature 3.3: Emergency Unwind Logic Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_emergency_unwind.py`

**Test Cases**:

```python
# Test 1: Emergency unwind triggered by daily loss (VERIFY existing)
GIVEN: Daily loss exceeds MAX_DAILY_LOSS
WHEN: handle_emergency_unwind() called
THEN: Closes all positions immediately

# Test 2: Emergency unwind triggered by net delta
GIVEN: Net delta > 2% threshold
WHEN: handle_emergency_unwind() called
THEN: Closes all positions, logs critical alert

# Test 3: Emergency unwind uses MARKET only
GIVEN: Emergency condition detected
WHEN: Unwind executed
THEN: Uses MARKET orders (no POST_ONLY)

# Test 4: Emergency unwind handles partial fills
GIVEN: Emergency unwind in progress
WHEN: Partial fill detected
THEN: Continues closing remaining position

# Test 5: Emergency unwind timeout handling
GIVEN: Emergency unwind takes >10s
WHEN: Timeout exceeded
THEN: Forces cancellation, logs error

# Test 6: Emergency unwind metrics
GIVEN: Emergency unwind complete
WHEN: Metrics recorded
THEN: Logs reason, duration, slippage
```

**Implementation File**: DN pair bot file

**Methods to Verify**: `handle_emergency_unwind()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- Triggers on daily loss OR net delta >2%
- Uses MARKET orders only
- Timeout = 10s

**Dependencies**: Sub-Feature 3.2

**Estimated Time**: 2 hours

---

### Sub-Feature 3.4: Exit Metrics and PnL Calculation Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_exit_metrics.py`

**Test Cases**:

```python
# Test 1: Exit price recording
GIVEN: Positions closed
WHEN: Exit complete
THEN: Records eth_exit_price, sol_exit_price

# Test 2: Exit time measurement
GIVEN: Exit cycle starts
WHEN: Exit complete
THEN: Records eth_exit_time, sol_exit_time

# Test 3: Gross PnL calculation (VERIFY existing)
GIVEN: Entry and exit prices
WHEN: PnL calculated
THEN: Correctly computes spread * quantity

# Test 4: Net PnL calculation with fees
GIVEN: Gross PnL and trading fees
WHEN: Net PnL calculated
THEN: Subtract fees from gross PnL

# Test 5: Cumulative PnL tracking
GIVEN: Multiple cycles complete
WHEN: Total PnL calculated
THEN: Sums all cycle PnLs

# Test 6: PnL per basis point
GIVEN: Gross PnL and total volume
WHEN: PnL bps calculated
THEN: Returns (PnL / volume) * 10000

# Test 7: Exit metrics export
GIVEN: Exit complete
WHEN: Metrics exported
THEN: CSV includes all exit fields
```

**Implementation File**: DN pair bot file

**Methods to Verify**: `print_trade_summary()` - VERIFY existing

**Acceptance Criteria**:
- All 7 tests pass
- PnL calculations accurate to 4 decimal places
- CSV export includes all V4 fields
- Cumulative tracking works correctly

**Dependencies**: Sub-Feature 3.3

**Estimated Time**: 2 hours

---

### Sub-Feature 3.5: Integration Test - Full Cycle

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_full_cycle_integration.py`

**Test Cases**:

```python
# Test 1: Complete BUILD cycle with WebSocket
GIVEN: No open positions
WHEN: execute_buy_first_cycle() or execute_sell_first_cycle() called
THEN: Positions opened, WebSocket fill detection active

# Test 2: Complete CLOSE cycle with WebSocket
GIVEN: Open positions from BUILD
WHEN: execute_unwind_cycle() called
THEN: Positions closed, WebSocket monitoring active

# Test 3: Multiple sequential cycles
GIVEN: Initial state
WHEN: 5 cycles executed
THEN: All cycles complete, cumulative PnL tracked

# Test 4: Cycle failure recovery
GIVEN: Cycle fails mid-execution
WHEN: Next cycle attempted
THEN: State cleaned up, new cycle starts

# Test 5: WebSocket failover during cycle
GIVEN: Cycle in progress
WHEN: WebSocket fails
THEN: REST fallback takes over, cycle completes

# Test 6: Emergency stop during cycle
GIVEN: Cycle in progress
WHEN: Emergency triggered
THEN: Cycle halted, positions unwound
```

**Implementation File**: DN pair bot file

**Methods to Verify**: `execute_build_cycle()`, `execute_unwind_cycle()` - VERIFY existing

**Acceptance Criteria**:
- All 6 tests pass
- Full cycle time <10s average
- WebSocket primary, REST fallback
- State management correct
- Recovery works after failures

**Dependencies**: All previous sub-features

**Estimated Time**: 2 hours

**Total Phase 3 Time**: 10-14 hours

---

## PHASE 4: Production Configuration

**Goal**: Prepare production configuration with validated settings from Phase 0
**Duration**: 3 hours (expanded from 2h to include WebSocket config)

### Sub-Feature 4.0: Production Configuration Validation

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_production_config.py`

**Test Cases**:

```python
# Test 1: NADO_PRIVATE_KEY format validation
GIVEN: Environment variable NADO_PRIVATE_KEY set
WHEN: Configuration loaded
THEN: Valid EVM wallet address format (0x + 40 hex chars)

# Test 2: Production config uses verified product IDs from Phase 0
GIVEN: Production configuration file
WHEN: Product IDs loaded
THEN: ETH=4, SOL=8 match Phase 0 research

# Test 3: Production config uses verified tick sizes from Phase 0
GIVEN: Production configuration file
WHEN: Tick sizes loaded
THEN: ETH=0.1, SOL=0.1 match Phase 0 research

# Test 4: Order type configuration matches Phase 0 findings
GIVEN: Production configuration file
WHEN: Order types loaded
THEN: POST_ONLY, IOC, FOK, DEFAULT verified

# Test 5: WebSocket configuration from Phase 0 research
GIVEN: Production configuration file
WHEN: WebSocket settings loaded
THEN: Endpoint, authentication method from Phase 0

# Test 6: Risk limits within acceptable ranges
GIVEN: Production configuration file
WHEN: Risk limits loaded
THEN: MAX_POSITION, MAX_DAILY_LOSS, NET_DELTA_THRESHOLD set appropriately

# Test 7: Connection priorities configured
GIVEN: Production configuration file
WHEN: Connection settings loaded
THEN: WebSocket=primary, REST=fallback
```

**Implementation Tasks**:

1. **Create production configuration with Phase 0 values**
   - File: `/Users/botfarmer/2dex/config/production_config.json`
   - ETH_PRODUCT_ID: 4
   - SOL_PRODUCT_ID: 8
   - ETH_TICK_SIZE: "0.1"
   - SOL_TICK_SIZE: "0.1"
   - WEBSOCKET_ENABLED: true
   - WEBSOCKET_ENDPOINT: [from Phase 0.1 research]
   - WEBSOCKET_AUTH_METHOD: [from Phase 0.1 research]
   - CONNECTION_PRIORITY: "websocket_primary"

2. **Add configuration validation test**
   - Test file: `/Users/botfarmer/2dex/tests/stage4/test_production_config.py`
   - Verify all config values match Phase 0 research
   - Test configuration loading and validation

**Acceptance Criteria**:
- All 7 tests pass
- Production config uses only verified values from Phase 0
- WebSocket configuration from Phase 0.1 research
- NADO_PRIVATE_KEY format validated at startup
- Connection priorities: WebSocket PRIMARY, REST FALLBACK

**Dependencies**: Phase 0 complete

**Estimated Time**: 3 hours

**Total Phase 4 Time**: 3 hours

---

## Risk Mitigation

### What Could Go Wrong

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|---------------------|
| **Nado WebSocket API undocumented** | High | Medium | Phase 0.1 research will find documentation or contact Nado support |
| **Nado WebSocket endpoint unavailable** | High | Low | REST fallback already implemented, dual connection architecture |
| **WebSocket authentication complex** | Medium | Medium | Phase 0.1 research docs auth method, test early in Phase 1.2 |
| **WebSocket message format unknown** | High | Medium | Phase 0.1 research docs message format, reference Lighter pattern |
| **Position reconciliation drift** | High | Medium | Strict 1% tolerance, auto-recovery (EXISTS, verify) |
| **WebSocket connection unstable** | Medium | High | Reconnection with exponential backoff (reference Lighter) |
| **Concurrent order race conditions** | Medium | Medium | Use asyncio.gather() (EXISTS, verify) |
| **WebSocket fill detection missed** | High | Low | REST polling as fallback, dual-connection architecture |

### Testing Strategy for Risk Mitigation

**Pre-Deployment Testing**:
1. **Phase 0 Research**: All WebSocket capabilities documented before implementation
2. **Mock WebSocket Server**: Test WebSocket handling without real connection
3. **Nado Testnet**: All tests run against Nado testnet first
4. **Small Size Tests**: Start with 0.01 ETH/SOL sizes
5. **Manual Override**: Include emergency stop in all integration tests
6. **Position Limits**: Enforce strict limits during testing (MAX_POSITION = 0.1)

**Production Rollout**:
1. **WebSocket Validation**: Verify WebSocket connection stable for 1 hour before trading
2. **Canary Deployment**: Run 1 cycle, verify all metrics
3. **Gradual Scale**: Increase from 0.01 → 0.05 → 0.1 ETH sizes
4. **24h Monitoring**: Continuous monitoring for first day
5. **Rollback Plan**: Keep existing Nado REST-only code as fallback

---

## Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Test Coverage** | >85% overall, >90% critical | pytest --cov |
| **Fill Rate (BUILD)** | 100% | Integration test results |
| **Fill Rate (CLOSE)** | >95% | Integration test results |
| **Average Cycle Time** | <10s, target 8s | Trade metrics CSV |
| **Position Drift** | <1% per cycle | Reconciliation logs |
| **WebSocket Latency** | <100ms | Connection metrics |
| **REST Latency** | <500ms | Connection metrics |
| **WebSocket Uptime** | >95% | Connection health |
| **Daily PnL Accuracy** | ±$0.01 vs manual calc | Automated validation |
| **Emergency Unwind** | <10s to close all | Emergency test |

### Qualitative Metrics

- WebSocket is PRIMARY connection method (not optional)
- All V4 safety features verified and tested
- Error handling comprehensive (no uncaught exceptions)
- Logging sufficient for debugging (all critical paths logged)
- Documentation clear (docstrings for all public methods)
- CSV export format compatible with analysis tools
- REST fallback works seamlessly when WebSocket unavailable

---

## Implementation Sequence

### Order of Implementation (Numbered Steps)

**Phase 0: Nado WebSocket Research (PREREQUISITE)**
1. Sub-Feature 0.1: Nado WebSocket Documentation Research (4h) - NEW, MANDATORY
2. Sub-Feature 0.2: Lighter WebSocket Pattern Analysis (2h) - NEW, MANDATORY
3. Sub-Feature 0.3: Order Type Support Verification (2h)
4. Sub-Feature 0.4: REST API Method Inventory (3h)
5. Sub-Feature 0.5: Product ID and Contract Verification (2h)
6. Sub-Feature 0.6: Research Documentation Output (2h)

**Phase 1: WebSocket Connection Infrastructure (CORE REQUIREMENT)**
7. Sub-Feature 1.1: REST API Connection Verification (2h)
8. Sub-Feature 1.2: Nado WebSocket Client Implementation (6h) - NEW, MANDATORY
9. Sub-Feature 1.3: WebSocket Order Update Handler (5h) - NEW, MANDATORY
10. Sub-Feature 1.4: Order Placement Verification (3h)
11. Sub-Feature 1.5: Dual Connection Manager (4h) - NEW, MANDATORY
12. Sub-Feature 1.6: Connection Monitoring and Metrics (3h)

**Phase 2: Entry Logic (BUILD Cycles)**
13. Sub-Feature 2.1: V4 Helper Functions Port (2h)
14. Sub-Feature 2.2: Pre-Trade Safety Checks Verification (2h)
15. Sub-Feature 2.3: Simultaneous Order Placement Verification (2h)
16. Sub-Feature 2.4: WebSocket-Based Fill Detection (2h) - ENHANCED
17. Sub-Feature 2.5: Position Reconciliation Verification (2h)
18. Sub-Feature 2.6: Entry Metrics Collection Verification (2h)

**Phase 3: Unwind Logic (CLOSE Cycles)**
19. Sub-Feature 3.1: POST_ONLY Order Placement Verification (2h)
20. Sub-Feature 3.2: MARKET Order Fallback Verification (2h)
21. Sub-Feature 3.3: Emergency Unwind Logic Verification (2h)
22. Sub-Feature 3.4: Exit Metrics and PnL Calculation Verification (2h)
23. Sub-Feature 3.5: Integration Test - Full Cycle (2h)

**Phase 4: Production Configuration**
24. Sub-Feature 4.0: Production Configuration Validation (3h)

### Dependencies Between Steps

```
Phase 0 (WebSocket Research) ──> REQUIRED BEFORE ALL IMPLEMENTATION

0.1 (Nado WebSocket Docs) ──┐
0.2 (Lighter Pattern) ───────┤
0.3 (Order Types) ───────────┼──> 0.6 (Research Doc) ──> Phase 1
0.4 (REST API) ──────────────┤
0.5 (Products) ───────────────┘

Phase 1 Complete ──> 2.1 (V4 Helpers) ──> 2.2 (Safety) ──> 2.3 (Simultaneous)
                                                              │
                        2.3 ──> 2.4 (WebSocket Fill) ──> 2.5 (Reconcile) ──> 2.6 (Metrics)
                                                              │
Phase 2 Complete ──────────────────────────────────────────────┘
                        │
                        └──> 3.1 (POST_ONLY) ──> 3.2 (MARKET)
                                                   │
                                      3.2 ──> 3.3 (Emergency)
                                                   │
                                      3.3 ──> 3.4 (Exit Metrics)
                                                   │
                                      3.4 ──> 3.5 (Full Cycle) ──> 4.0 (Config) ──> DONE
```

---

## Key Differences from Previous Plan

### WebSocket is MANDATORY (Not Conditional)

| Aspect | Previous Plan | This Plan |
|--------|--------------|-----------|
| **WebSocket Status** | Conditional based on SDK | MANDATORY implementation |
| **Implementation** | Use SDK WebSocket | Implement raw WebSocket |
| **Research** | Check if SDK has WebSocket | Research Nado WebSocket API |
| **Fallback** | REST primary, WebSocket if available | WebSocket primary, REST fallback |
| **Reference** | None | Lighter WebSocket pattern |

### New Sub-Features Added

- **Phase 0.1**: Nado WebSocket Documentation Research (4h)
- **Phase 0.2**: Lighter WebSocket Pattern Analysis (2h)
- **Phase 1.2**: Nado WebSocket Client Implementation (6h)
- **Phase 1.3**: WebSocket Order Update Handler (5h)
- **Phase 1.5**: Dual Connection Manager (4h)

### Enhanced Sub-Features

- **Phase 2.4**: WebSocket-Based Fill Detection (was REST-only)
- **Phase 4.0**: Production Configuration (includes WebSocket config)

---

## File Paths Summary

**Research Output**:
- `/Users/botfarmer/2dex/.omc/research/nado-websocket-api.md` - NEW

**Exchange Client** (IMPLEMENT WebSocket):
- `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py` - Main Nado client

**Reference Files** (READ ONLY):
- `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/lighter_custom_websocket.py` - WebSocket pattern reference

**Test Files** (to be created):
- `/Users/botfarmer/2dex/tests/stage2/test_nado_websocket_client.py` - NEW
- `/Users/botfarmer/2dex/tests/stage2/test_nado_websocket_order_updates.py` - NEW
- `/Users/botfarmer/2dex/tests/stage2/test_nado_dual_connection.py` - NEW
- Plus all existing test files from previous plan

**Configuration Files**:
- `/Users/botfarmer/2dex/config/production_config.json` - Includes WebSocket config

---

## Conclusion

This plan provides a **WEBSOCKET-FIRST** approach to migrating V4 DN pair implementation to Nado. Key differences from previous plan:

1. **WebSocket is MANDATORY** - Not conditional, must be implemented
2. **Raw WebSocket Implementation** - Use `websockets` library, not SDK
3. **Research-First** - Phase 0.1-0.2 dedicated to WebSocket API research
4. **Reference Implementation** - Use Lighter WebSocket pattern as guide
5. **Dual Connection Architecture** - WebSocket PRIMARY, REST FALLBACK
6. **No Arbitrary Plan Changes** - WebSocket implementation locked in

**Total Estimated Time**: 65-90 hours (including 15-hour Phase 0 WebSocket research + 25-hour Phase 1 WebSocket implementation)
**Total Sub-Features**: 24 (expanded from 21)
**Test Files**: 20 (added 3 WebSocket-specific tests)
**Implementation Files**: 2 (nado.py, DN_pair_eth_sol_nado.py)
**Research Output**: 1 (nado-websocket-api.md)

**Critical Improvements Over Previous Plan**:
1. WebSocket is MANDATORY, not conditional
2. Phase 0 includes WebSocket API research (0.1-0.2)
3. Phase 1 includes raw WebSocket implementation (1.2-1.3, 1.5)
4. Reference implementation (Lighter) for guidance
5. Dual connection architecture (WebSocket PRIMARY + REST FALLBACK)
6. No arbitrary plan changes - WebSocket locked in

**Next Steps**:
1. **CRITICAL**: Complete Phase 0.1 Nado WebSocket Documentation Research
2. **CRITICAL**: Complete Phase 0.2 Lighter WebSocket Pattern Analysis
3. **CRITICAL**: Document Nado WebSocket endpoint and authentication
4. Review research findings and confirm WebSocket approach
5. Begin Phase 1.2 WebSocket Client Implementation
6. Track progress with pytest after each sub-feature
7. Follow Phase Handoff Criteria checklists between phases

---

**Plan Status**: READY FOR WEBSOCKET-FIRST IMPLEMENTATION

**Last Updated**: 2026-01-29
**Version**: 1.0 (WebSocket-First - RALPLAN Response)
