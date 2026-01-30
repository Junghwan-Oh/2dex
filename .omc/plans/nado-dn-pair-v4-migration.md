# Nado DN Pair V4 Migration - Research-First Implementation Plan

**Plan Created**: 2026-01-29
**Plan Refined**: Iteration 2 (Final - All Critic Improvements Implemented)
**Target**: Migrate V4 DN pair implementation (Backpack+GRVT) to Nado-only DN pair
**Methodology**: Research-First TDD (Test-Driven Development)
**Estimated Duration**: 51-74 hours across 5 phases (updated)

---

## Requirements Summary

### What We're Building

Migrate the proven V4 DN pair implementation (Backpack + GRVT) to Nado-only DN pair, maintaining 100% fill rate and 8s/cycle average performance while adding Nado-specific optimizations.

**Key V4 Features to Preserve:**
- V4 BBO routing with `extract_filled_quantity`, `calculate_timeout`
- Safety features: MAX_POSITION, MAX_DAILY_LOSS, _pre_trade_check
- Emergency unwind and net delta monitoring
- POST_ONLY and MARKET fallback logic
- Position reconciliation with auto-recovery
- Trade metrics tracking (WebSocket latency, REST latency, reconciliation time)

**Nado-Specific Requirements:**
- Replace all GRVT/Backpack references with Nado
- **IMPLEMENT WebSocket** ✅ COMPLETED (verified working via testing)
  - `nado_websocket_client.py` - WebSocket client implementation ✅
  - `nado_bbo_handler.py` - Real-time BBO with spread/momentum ✅
  - `nado_bookdepth_handler.py` - Order book with slippage estimation ✅
  - `nado.py` - NadoClient uses WebSocket BBO with REST fallback ✅
- Use WebSocket PRIMARY + REST fallback for queries
- WebSocket endpoints: `wss://gateway.test.nado.xyz/v1/subscribe` ✅ TESTED
- Public streams working: BBO (real-time), BookDepth (50ms) ✅ VERIFIED
- Authenticated streams (Fill, PositionChange): REQUIRE SUBACCOUNT ⚠️ BLOCKED
- EIP-712 StreamAuthentication: FORMAT DOCUMENTED (not tested - no subaccount)
- Nado order types: POST_ONLY, IOC, FOK, DEFAULT (verified)
- Nado product IDs: ETH=4, SOL=8 (verified)
- Tick sizes: ETH=0.1, SOL=0.1 (verified)
- Rate limits: 5 authenticated connections per wallet

**COMPLETED WORK (Added to Plan):**
- Phase 0.5: WebSocket Infrastructure Research & Implementation ✅
- Phase 1: WebSocket Public Stream Client ✅
  - WebSocket client with auto-reconnect ✅
  - BBO handler with spread/momentum detection ✅
  - BookDepth handler with slippage estimation ✅
  - NadoClient WebSocket integration ✅
  - Integration tests passing (5/6) ✅

**REMAINING WORK:**
- Phase 2: V4 Feature Porting (extract_filled_quantity, calculate_timeout)
- Phase 3: WebSocket + DN Pair Strategy Integration
- Phase 4: Production Testing & Deployment

### Success Criteria

1. **Functional**: 100% fill rate on BUILD cycles, 95%+ on CLOSE cycles
2. **Performance**: <10s average cycle time (target: 8s)
3. **Safety**: Position drift <1%, daily loss limit enforcement
4. **Reliability**: REST-based connection (WebSocket if available)
5. **Test Coverage**: >90% coverage for all critical paths

---

## Critical Finding: Existing Functions Analysis

### Functions Already Existing in Nado Implementation

**Current Nado DN Pair (`/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`)**:
- `place_simultaneous_orders()` - EXISTS (line 387) - NO NEED TO REIMPLEMENT
- `emergency_unwind` - EXISTS as `handle_emergency_unwind()` (line 489) - NO NEED TO REIMPLEMENT
- `wait_for_fill()` - EXISTS in `/Users/botfarmer/2dex/exchanges/nado.py` (line 468) - NO NEED TO REIMPLEMENT
- `wait_for_fill_by_position()` - EXISTS in `/Users/botfarmer/2dex/exchanges/nado.py` (line 411) - NO NEED TO REIMPLEMENT
- `_pre_trade_check()` - EXISTS (line 2150) - NO NEED TO REIMPLEMENT
- `reconcile_positions()` - EXISTS (line 918) - NO NEED TO REIMPLEMENT
- `place_ioc_order()` - EXISTS in `/Users/botfarmer/2dex/exchanges/nado.py` (line 224) - NO NEED TO REIMPLEMENT
- `place_open_order()` - EXISTS in `/Users/botfarmer/2dex/exchanges/nado.py` (line 157) - NO NEED TO REIMPLEMENT
- `place_close_order()` - EXISTS in `/Users/botfarmer/2dex/exchanges/nado.py` (line 310) - NO NEED TO REIMPLEMENT
- `cancel_order()` - EXISTS in `/Users/botfarmer/2dex/exchanges/nado.py` (line 385) - NO NEED TO REIMPLEMENT

**Current Nado Client (`/Users/botfarmer/2dex/exchanges/nado.py`)**:
- WebSocket infrastructure: DECLARED but NOT IMPLEMENTED (lines 56-61: _ws_task, _ws_stop, _ws_connected, _order_fill_events)
- `connect()` - EXISTS (line 70) but WebSocket NOT implemented
- `setup_order_update_handler()` - EXISTS (line 89) but placeholder implementation
- `fetch_bbo_prices()` - EXISTS (line 96) with REST API
- `get_order_info()` - EXISTS (line 546) with REST API
- `get_account_positions()` - EXISTS (line 682) with REST API
- `get_contract_attributes()` - EXISTS (line 707)

**WebSocket Implementation Required:**
- Nado official WebSocket: `wss://gateway.test.nado.xyz/v1/subscribe`
- Streams: Fill, PositionChange, BookDepth (50ms), BestBidOffer (real-time), OrderUpdate
- Authentication: EIP-712 StreamAuthentication format
- SDK: `nado-protocol` PyPI package provides WebSocket support

### V4 Functions to Port (NOT in Nado yet)

**From V4 Reference (`/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py`)**:
- `extract_filled_quantity()` - NEEDS TO PORT (line 50 in grvt.py)
- `calculate_timeout()` - NEEDS TO PORT (line 18 in grvt.py)
- Iterative market order routing (if not in Nado)

---

## Architecture Overview

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                     DNPairBot (Main Controller)             │
│  - Strategy orchestration (BUILD/CLOSE cycles)              │
│  - Safety checks (MAX_POSITION, daily loss)                 │
│  - Position reconciliation (EXISTS, enhance if needed)      │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
    ┌────────▼────────┐              ┌────────▼────────┐
    │  NadoClient ETH │              │  NadoClient SOL │
    │  - Product ID 4 │              │  - Product ID 8 │
    └────────┬────────┘              └────────┬────────┘
             │                                │
    ┌────────▼────────────────────────────────▼────────┐
    │         Nado SDK (nado_protocol)                  │
    │  ┌──────────────────┐    ┌──────────────┐        │
    │  │ WebSocket (PRI)  │    │ REST API     │        │
    │  │ - Fill stream    │    │ - Queries    │        │
    │  │ - PositionChange │    │ - Engine     │        │
    │  │ - BookDepth 50ms │    │ - Indexer    │        │
    │  │ - BBO real-time  │    │ - Fallback   │        │
    │  └──────────────────┘    └──────────────┘        │
    │  Endpoint: wss://gateway.test.nado.xyz/v1/subscribe│
    │  Auth: EIP-712 StreamAuthentication                │
    └──────────────────────────────────────────────────┘
```

### Data Flow (With WebSocket Implementation)

**BUILD Cycle (Entry):**
1. Check safety limits (position, daily loss) - EXISTS, verify completeness
2. Fetch BBO prices from WebSocket BestBidOffer stream - NEEDS IMPLEMENTATION
3. Place simultaneous IOC orders - EXISTS, verify implementation
4. Monitor fills via WebSocket Fill stream - NEEDS IMPLEMENTATION
5. Reconcile positions via WebSocket PositionChange stream - EXISTS, enhance with WebSocket
6. Update metrics - PARTIALLY EXISTS, verify V4 parity

**CLOSE Cycle (Exit):**
1. Check current positions via PositionChange stream - EXISTS
2. Fetch BBO prices from WebSocket - NEEDS IMPLEMENTATION
3. Place POST_ONLY orders - EXISTS, verify timeout logic
4. Fallback to MARKET if timeout - NEEDS VERIFICATION
5. Monitor fills via WebSocket Fill stream - NEEDS IMPLEMENTATION
6. Reconcile positions, calculate PnL - EXISTS

---

## Prerequisites

### Directory Structure Setup

**Before starting Phase 0**, create the required directory structure:

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

### Mock Strategy

**Library**: pytest-mock + unittest.mock

**Mock Interface Design**:
- Mock Nado SDK based on Phase 0 research findings
- Create mock fixtures for all NadoClient methods
- Mock WebSocket server (if WebSocket available)
- Mock REST API responses

**Example Mock Fixtures**:

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock
from decimal import Decimal

@pytest.fixture
def mock_nado_client():
    """Mock NadoClient with REST API responses"""
    client = Mock()
    client.context = Mock()
    client.context.engine_client = Mock()
    client.context.indexer_client = Mock()
    client.market = Mock()

    # Mock contract attributes (verified from Nado documentation)
    client.get_contract_attributes = Mock(return_value={
        'contract_id': 4,  # ETH product ID (verified)
        'tick_size': Decimal('0.1')  # ETH tick size (verified)
    })

    # Mock BBO prices
    client.fetch_bbo_prices = Mock(return_value=(Decimal('3000.00'), Decimal('3000.50')))

    # Mock positions
    client.get_account_positions = Mock(return_value=Decimal('0'))

    return client

@pytest.fixture
def mock_websocket_server():
    """Mock WebSocket server for testing (if WebSocket available)"""
    import asyncio
    from unittest.mock import MagicMock

    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.connected = True

    return ws
```

**Mock Usage Pattern**:
- Use `mock_nado_client` for all REST API tests
- Use `mock_websocket_server` for WebSocket tests (if applicable)
- Update mock responses based on Phase 0 research findings
- Verify all mock calls match actual SDK behavior

---

## PHASE 0: WebSocket & REST Integration Research (COMPLETED)

**Goal**: Verify Nado SDK capabilities before ANY implementation
**Duration**: 8 hours (reduced - key info already verified from official docs)
**Status**: Research information verified from official Nado documentation

### Already Verified Information

**WebSocket Capabilities** (VERIFIED):
- WebSocket Gateway: `wss://gateway.test.nado.xyz/v1/ws`
- Subscriptions: `wss://gateway.test.nado.xyz/v1/subscribe`
- Authentication: EIP-712 StreamAuthentication format
- SDK: `nado-protocol` PyPI package provides WebSocket support
- Available Streams: OrderUpdate, Fill, PositionChange, BookDepth, BestBidOffer, Trade

**Order Types** (VERIFIED):
- POST_ONLY: Maker-only orders
- IOC: Immediate-Or-Cancel
- FOK: Fill-Or-Kill
- DEFAULT: Standard limit order

**Product IDs** (VERIFIED):
- ETH: Product ID 4
- SOL: Product ID 8
- Tick sizes: ETH=0.1, SOL=0.1

**Rate Limits** (VERIFIED):
- 5 authenticated connections per wallet
- 100 connections per IP

### Sub-Feature 0.1: WebSocket Integration Testing

**Testing Tasks**:
1. Install and test `nado-protocol` SDK WebSocket functionality
2. Create test connection to `wss://gateway.test.nado.xyz/v1/subscribe`
3. Implement EIP-712 authentication signing
4. Test subscription to Fill stream
5. Test subscription to BookDepth stream
6. Test subscription to BBO stream
7. Validate message formats

**Estimated Time**: 3 hours

---

### Sub-Feature 0.2: BookDepth & BBO Stream Testing

**Testing Tasks**:
1. Subscribe to BookDepth for ETH (product_id=4)
2. Parse incremental deltas (new_qty vs 0 = delete)
3. Maintain local order book state
4. Subscribe to BBO for ETH and SOL
5. Calculate spread in real-time
6. Measure actual update frequencies

**Estimated Time**: 2 hours

---

### Sub-Feature 0.3: REST API Method Testing

**Testing Tasks**:
1. Test `get_order_info()` for order status queries
2. Test `get_account_positions()` for position data
3. Test `fetch_bbo_prices()` for current prices
4. Verify REST API rate limits
5. Document REST fallback strategy

**Estimated Time**: 2 hours

---

### Sub-Feature 0.4: Research Documentation Output

**Output File**: `/Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md`

**Document Structure**:
```markdown
# Nado SDK Capabilities Research (UPDATED)

## Executive Summary
- WebSocket Support: YES (verified)
- Endpoints: wss://gateway.test.nado.xyz/v1/subscribe
- Authentication: EIP-712 StreamAuthentication
- Order Types: POST_ONLY, IOC, FOK, DEFAULT (verified)
- Product IDs: ETH=4, SOL=8 (verified)
- REST API Status: Verified working

## 1. WebSocket Capabilities
- Availability: YES - Nado provides full WebSocket API
- Endpoints:
  - Gateway: wss://gateway.test.nado.xyz/v1/ws
  - Subscriptions: wss://gateway.test.nado.xyz/v1/subscribe
- Streams:
  - Fill: Order fill notifications
  - PositionChange: Position updates
  - BookDepth: 50ms order book updates
  - BestBidOffer: Real-time top-of-book
  - OrderUpdate: Order status changes

## 2. BookDepth Stream (Market Making Critical)
- Update frequency: 50ms batches
- Message format: incremental deltas
- Uses: Order placement, liquidity analysis, slippage estimation

## 3. BBO Stream (Real-Time Pricing)
- Update frequency: Instantaneous
- Message format: bid_price, bid_qty, ask_price, ask_qty
- Uses: Spread monitoring, momentum detection, fair value

## 4. Authentication
- Format: EIP-712 StreamAuthentication
- Requires: Wallet signature
- Public streams: No authentication required

## 5. Rate Limits
- Authenticated: 5 per wallet
- Unauthenticated: 100 per IP

## 6. Code Examples
- WebSocket connection: [Working code]
- EIP-712 signing: [Working code]
- Stream subscription: [Working code]
- Message parsing: [Working code]

## 7. Recommendations
- Use WebSocket for: Fill, Position, BookDepth, BBO
- Use REST for: Queries, historical data, fallback
- Primary connection: WebSocket (mandatory for rate limit reasons)
```

**Acceptance Criteria**:
- All research tasks completed
- Document saved with all sections filled
- Code examples tested and verified
- Clear recommendations provided

**Estimated Time**: 2 hours

**Estimated Time**: 2 hours

---

### Sub-Feature 0.6: Research Validation

**Goal**: Validate research findings with executable code examples
**Duration**: 1 hour

**Test File**: `/Users/botfarmer/2dex/tests/stage1/test_phase0_research_validation.py`

**Test Cases**:

```python
# Test 1: Research document exists at specified path
GIVEN: Phase 0 research complete
WHEN: test_research_document_exists() called
THEN: File exists at /Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md

# Test 2: All 6 sections of research document are complete
GIVEN: Research document exists
WHEN: test_research_document_complete() called
THEN: All sections (Executive Summary, WebSocket, Order Types, REST API, Products, Recommendations) contain content

# Test 3: Code examples from research execute successfully
GIVEN: Code examples from research document
WHEN: test_code_examples_execute() called
THEN: All Python code snippets run without errors

# Test 4: Product IDs match actual SDK output
GIVEN: Research document specifies product IDs
WHEN: test_product_ids_match() called
THEN: Documented ETH/SOL product IDs match get_all_product_symbols() output

# Test 5: Order types verified against SDK enum
GIVEN: Research document lists order types
WHEN: test_order_types_verified() called
THEN: Documented order types match nado_protocol.utils.order.OrderType enum

# Test 6: REST API methods documented accurately
GIVEN: Research document lists REST methods
WHEN: test_rest_methods_accurate() called
THEN: All documented methods exist in actual SDK
```

**Validation Commands**:

```bash
# Run validation tests
pytest /Users/botfarmer/2dex/tests/stage1/test_phase0_research_validation.py -v

# Verify research document completeness
python -c "
import re
with open('/Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md', 'r') as f:
    content = f.read()
    sections = re.findall(r'^## \d+\.\s+(.+)$', content, re.MULTILINE)
    print(f'Found {len(sections)} sections: {sections}')
    assert len(sections) >= 6, 'Missing sections in research document'
"

# Test code examples from research
python -c "
# Execute code examples extracted from research document
# (This will be a comprehensive test of all code snippets)
"
```

**Acceptance Criteria**:
- All 6 validation tests pass
- Research document is complete and accurate
- All code examples execute successfully
- Product IDs and order types verified against actual SDK

**Dependencies**: Sub-Features 0.1-0.5 complete

**Estimated Time**: 1 hour

**Total Phase 0 Time**: 13 hours (updated from 12 hours)

---

## PHASE 1: Connection Infrastructure (UPDATED based on Phase 0)

**Goal**: Establish reliable connection based on ACTUAL SDK capabilities
**Duration**: 8-12 hours (UPDATED based on research)
**Test Coverage**: >95% for connection logic

### Sub-Feature 1.1: REST API Connection Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_rest_connection.py`

**Test Cases** (Given-When-Then format):

```python
# Test 1: Client initialization with valid credentials
GIVEN: Valid NADO_PRIVATE_KEY in environment
WHEN: NadoClient is instantiated
THEN: Client initializes successfully with owner address

# Test 2: Contract attributes retrieval (VERIFY product IDs from Phase 0)
GIVEN: Initialized NadoClient for ETH
WHEN: get_contract_attributes() is called
THEN: Returns contract_id=[FROM_PHASE0] and tick_size=[FROM_PHASE0]

# Test 3: Contract attributes for SOL (VERIFY from Phase 0)
GIVEN: Initialized NadoClient for SOL
WHEN: get_contract_attributes() is called
THEN: Returns contract_id=[FROM_PHASE0] and tick_size=[FROM_PHASE0]

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

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py` (VERIFY existing, enhance if needed)

**Methods to Verify/Enhance**:
- `_validate_config()` - VERIFY validation for NADO_PRIVATE_KEY format
- `get_contract_attributes()` - VERIFY product ID mapping from Phase 0
- `fetch_bbo_prices()` - VERIFY retry logic exists (line 96)

**Acceptance Criteria**:
- All 6 tests pass
- Product IDs from Phase 0 research confirmed
- Tick sizes from Phase 0 research confirmed
- Mock Nado SDK responses for isolated testing

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_rest_connection.py -v
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_rest_connection.py --cov=exchanges.nado --cov-report=term-missing
```

**Dependencies**: Phase 0 complete

**Estimated Time**: 2 hours

---

### Sub-Feature 1.2: WebSocket Connection (CONDITIONAL - based on Phase 0)

**IMPORTANT**: This sub-feature is ONLY implemented if Phase 0 confirms WebSocket availability.

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_websocket.py`

**Test Cases** (IF WebSocket available):

```python
# Test 1: WebSocket connection establishment
GIVEN: Initialized NadoClient
WHEN: connect() is called with WebSocket enabled
THEN: WebSocket connects successfully

# Test 2: WebSocket order update handler registration
GIVEN: Connected WebSocket
WHEN: setup_order_update_handler() is called with callback
THEN: Handler is registered and receives order updates

# Test 3: WebSocket disconnection handling
GIVEN: Connected WebSocket
WHEN: Connection is closed
THEN: _ws_connected flag set to False

# Test 4: WebSocket auto-reconnection
GIVEN: Disconnected WebSocket
WHEN: 60 seconds pass
THEN: Automatic reconnection attempted

# Test 5: WebSocket message parsing
GIVEN: Connected WebSocket receiving order update
WHEN: Order fill message received
THEN: Correctly extracts order_id, filled_size, price

# Test 6: WebSocket fallback to REST
GIVEN: WebSocket connection fails
WHEN: Any API method called
THEN: Automatically uses REST API
```

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py`

**Methods to Add/Enhance** (IF WebSocket available):
- `connect()` - ENHANCE existing (line 70) to add WebSocket
- `_ws_message_handler()` - Add if WebSocket available
- `_ws_order_update_router()` - Add if WebSocket available
- `_start_ws_monitor()` - Add if WebSocket available
- `_ws_reconnect()` - Add if WebSocket available

**Acceptance Criteria** (IF WebSocket available):
- All 6 tests pass with mock WebSocket server
- Real WebSocket connection tested against Nado testnet
- Message parsing handles all order statuses (OPEN, FILLED, CANCELLED)

**Acceptance Criteria** (IF NO WebSocket):
- REST API is primary connection method
- No WebSocket code added
- Documentation updated to reflect REST-only approach

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_websocket.py -v
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_websocket.py --cov=exchanges.nado --cov-report=term-missing
```

**Dependencies**: Sub-Feature 1.1, Phase 0 (WebSocket confirmation)

**Estimated Time**: 4 hours (if WebSocket available), 0 hours (if not)

---

### Sub-Feature 1.3: Order Placement Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_order_placement.py`

**Test Cases**:

```python
# Test 1: POST_ONLY order placement (VERIFY from Phase 0)
GIVEN: Connected client (WebSocket or REST)
WHEN: place_open_order() called with POST_ONLY
THEN: Order placed, confirmation received

# Test 2: IOC order placement (VERIFY from Phase 0)
GIVEN: Connected client
WHEN: place_ioc_order() called
THEN: Immediate fill detection within 500ms

# Test 3: Order placement via REST (always works)
GIVEN: REST connection available
WHEN: place_open_order() called
THEN: Order placed via REST API

# Test 4: Order cancellation
GIVEN: Open order
WHEN: cancel_order() called
THEN: Cancellation confirmed

# Test 5: Concurrent order placement (ETH + SOL)
GIVEN: Two NadoClient instances (ETH, SOL)
WHEN: Orders placed simultaneously
THEN: Both orders placed without interference

# Test 6: Order type verification
GIVEN: Multiple order types available
WHEN: Each order type tested
THEN: All supported order types work correctly
```

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py`

**Methods to Verify/Enhance**:
- `place_open_order()` - VERIFY existing (line 157)
- `place_ioc_order()` - VERIFY existing (line 224)
- `place_close_order()` - VERIFY existing (line 310)
- `cancel_order()` - VERIFY existing (line 385)

**Acceptance Criteria**:
- All 6 tests pass
- Orders confirmed within appropriate time (WebSocket: 500ms, REST: 2s)
- No race conditions in concurrent placement
- All verified order types from Phase 0 work

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_order_placement.py -v
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_order_placement.py --cov=exchanges.nado --cov-report=term-missing
```

**Dependencies**: Sub-Features 1.1, 1.2 (if applicable)

**Estimated Time**: 3 hours

---

### Sub-Feature 1.4: Connection Monitoring and Metrics

**Test File**: `/Users/botfarmer/2dex/tests/stage2/test_nado_connection_metrics.py`

**Test Cases**:

```python
# Test 1: REST API latency measurement
GIVEN: Using REST connection
WHEN: Order placed
THEN: Latency measured and logged (<500ms expected)

# Test 2: WebSocket latency measurement (IF available)
GIVEN: Using WebSocket connection
WHEN: Order placed
THEN: Latency measured and logged (<100ms expected)

# Test 3: Connection uptime tracking
GIVEN: Connection active
WHEN: 60 seconds pass
THEN: Uptime percentage calculated

# Test 4: Failover event logging (IF WebSocket available)
GIVEN: WebSocket fails
WHEN: Fallback to REST triggered
THEN: Failover event logged with timestamp

# Test 5: Reconnection success tracking (IF WebSocket available)
GIVEN: REST fallback active
WHEN: WebSocket reconnects
THEN: Reconnection event logged

# Test 6: Connection health summary
GIVEN: Connection active
WHEN: get_connection_health() called
THEN: Returns dict with status, latency, uptime
```

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py`

**New Methods** (IF not exists):
- `_track_latency()` - Add if not exists
- `_log_failover()` - Add if WebSocket available
- `_calculate_uptime()` - Add if not exists
- `get_connection_health()` - Add if not exists

**Acceptance Criteria**:
- All 6 tests pass
- Latency measured for all operations
- Health metrics exported for monitoring
- WebSocket-specific tests only run if WebSocket available

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_connection_metrics.py -v
pytest /Users/botfarmer/2dex/tests/stage2/test_nado_connection_metrics.py --cov=exchanges.nado --cov-report=term-missing
```

**Dependencies**: Sub-Feature 1.3

**Estimated Time**: 2 hours

**Total Phase 1 Time**: 8-13 hours (depending on WebSocket availability)

---

## PHASE 2: Entry Logic Enhancement (BUILD Cycles)

**Goal**: Verify and enhance existing entry logic for V4 parity
**Duration**: 10-14 hours
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

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py`

**New Functions** (PORT from V4):
- `extract_filled_quantity()` - PORT from `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py` (line 50)
- `calculate_timeout()` - PORT from `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py` (line 18)

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py` lines 18-49, 50-91

**Acceptance Criteria**:
- All 6 tests pass
- Functions handle Nado-specific order result formats
- Timeout calculation matches V4 reference
- Extracted quantity accurate for all order states

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage3/test_v4_helpers.py -v
pytest /Users/botfarmer/2dex/tests/stage3/test_v4_helpers.py --cov=exchanges.nado --cov-report=term-missing
```

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

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Method to Verify**:
- `_pre_trade_check()` - VERIFY existing (line 2150)

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 1847-1890

**Acceptance Criteria**:
- All 7 tests pass
- Safety checks enforce limits strictly
- Daily reset works correctly across UTC midnight
- Net delta monitoring active and accurate

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage3/test_pre_trade_checks.py -v
pytest /Users/botfarmer/2dex/tests/stage3/test_pre_trade_checks.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

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

# Test 4: Partial fill detection
GIVEN: One order fills, other partial
WHEN: Fill status checked
THEN: Correctly identifies partial fill state

# Test 5: Order cancellation on partial fill
GIVEN: One order fills fully, other partial
WHEN: Partial fill detected
THEN: Unfilled portion cancelled

# Test 6: Order timeout handling
GIVEN: Both orders placed
WHEN: Timeout expires (e.g., 5s)
THEN: Both orders cancelled
```

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Method to Verify**:
- `place_simultaneous_orders()` - VERIFY existing (line 387)

**Acceptance Criteria**:
- All 6 tests pass
- Orders placed concurrently using asyncio.gather()
- Failure handling cancels both orders
- Timeout mechanism works correctly

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage3/test_simultaneous_orders.py -v
pytest /Users/botfarmer/2dex/tests/stage3/test_simultaneous_orders.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

**Dependencies**: Sub-Feature 2.2

**Estimated Time**: 2 hours

---

### Sub-Feature 2.4: IOC Order Fill Detection Verification

**Test File**: `/Users/botfarmer/2dex/tests/stage3/test_ioc_fill_detection.py`

**Test Cases**:

```python
# Test 1: REST polling detects fill (VERIFY existing)
GIVEN: IOC order placed via REST
WHEN: Order fills
THEN: Fill detected via REST polling within 500ms

# Test 2: WebSocket detects immediate fill (IF available from Phase 0)
GIVEN: IOC order placed via WebSocket
WHEN: Order fills immediately
THEN: Fill detected via WebSocket within 100ms

# Test 3: Partial fill detection
GIVEN: IOC order partially fills
WHEN: Fill status checked
THEN: Correctly reports partial fill amount

# Test 4: No fill detection
GIVEN: IOC order placed
WHEN: Timeout expires (5s)
THEN: Reports no fill, order cancelled

# Test 5: Fill price extraction
GIVEN: Order fills at specific price
WHEN: Fill detected
THEN: Correctly extracts fill price

# Test 6: Position-based fill detection (VERIFY existing)
GIVEN: IOC order placed
WHEN: Position changes
THEN: wait_for_fill_by_position() detects fill
```

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py`

**Methods to Verify**:
- `wait_for_fill()` - VERIFY existing (line 468)
- `wait_for_fill_by_position()` - VERIFY existing (line 411)
- `place_ioc_order()` - VERIFY existing (line 224)

**Acceptance Criteria**:
- All 6 tests pass
- WebSocket detection <100ms (if available)
- REST polling <500ms
- Position-based detection as fallback

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage3/test_ioc_fill_detection.py -v
pytest /Users/botfarmer/2dex/tests/stage3/test_ioc_fill_detection.py --cov=exchanges.nado --cov-report=term-missing
```

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

# Test 5: WebSocket position vs REST position (IF WebSocket available)
GIVEN: WebSocket and REST positions differ
WHEN: Both sources checked
THEN: Uses REST as authoritative

# Test 6: Reconciliation metrics logging
GIVEN: Position reconciliation complete
WHEN: Metrics logged
THEN: Includes drift amount, sync status, latency
```

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Method to Verify**:
- `reconcile_positions()` - VERIFY existing (line 918)

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 648-736

**Acceptance Criteria**:
- All 6 tests pass
- REST API used as authoritative source
- Auto-recovery triggers at 1% drift threshold
- Net delta monitoring active

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage3/test_entry_reconciliation.py -v
pytest /Users/botfarmer/2dex/tests/stage3/test_entry_reconciliation.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

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

# Test 3: Order-to-fill latency
GIVEN: Order placed
WHEN: Fill detected
THEN: Records order_to_fill_eth, order_to_fill_sol

# Test 4: WebSocket vs REST latency (IF WebSocket available)
GIVEN: Both connections active
WHEN: Fill detected
THEN: Records websocket_latency, rest_latency

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
THEN: CSV contains all metrics fields
```

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Dataclass to Verify**:
- `TradeMetrics` - VERIFY existing (line 50)
- `export_trade_metrics()` - VERIFY existing (line 249)

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 46-86, 249-272

**Acceptance Criteria**:
- All 7 tests pass
- All V4 metrics captured
- CSV export matches V4 format
- Total cycle time <8s target tracked

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage3/test_entry_metrics.py -v
pytest /Users/botfarmer/2dex/tests/stage3/test_entry_metrics.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

**Dependencies**: Sub-Feature 2.5

**Estimated Time**: 2 hours

**Total Phase 2 Time**: 10-14 hours

---

## PHASE 3: Unwind Logic Enhancement (CLOSE Cycles)

**Goal**: Verify and enhance existing exit logic for V4 parity
**Duration**: 8-12 hours
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

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py`

**Method to Verify**:
- `place_close_order()` - VERIFY existing (line 310), ENHANCE if needed

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 941-999

**Acceptance Criteria**:
- All 6 tests pass
- POST_ONLY timeout = 3s (VERIFY)
- Fallback to MARKET on timeout (VERIFY or ADD)
- Fee savings tracked (VERIFY or ADD)

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage4/test_post_only_orders.py -v
pytest /Users/botfarmer/2dex/tests/stage4/test_post_only_orders.py --cov=exchanges.nado --cov-report=term-missing
```

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

**Implementation File**: `/Users/botfarmer/2dex/exchanges/nado.py` or `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Method to Verify/Add**:
- `place_iterative_market_order()` - VERIFY if exists, ADD if not

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 904-940

**Acceptance Criteria**:
- All 6 tests pass
- Iterative routing for orders >0.2 ETH (VERIFY or ADD)
- Slippage <0.1%
- Fallback logged

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage4/test_market_fallback.py -v
pytest /Users/botfarmer/2dex/tests/stage4/test_market_fallback.py --cov=exchanges.nado --cov-report=term-missing
```

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

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Methods to Verify**:
- `handle_emergency_unwind()` - VERIFY existing (line 489)
- `emergency_unwind_eth()` - VERIFY existing (line 514)
- `emergency_unwind_sol()` - VERIFY existing (line 530)

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 139-143, 874-883

**Acceptance Criteria**:
- All 6 tests pass
- Triggers on daily loss OR net delta >2%
- Uses MARKET orders only
- Timeout = 10s

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage4/test_emergency_unwind.py -v
pytest /Users/botfarmer/2dex/tests/stage4/test_emergency_unwind.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

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

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Methods to Verify**:
- `print_trade_summary()` - VERIFY existing (line 274)
- `TradeMetrics` - VERIFY exit fields (line 50)

**Reference**: `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` lines 274-311, 62-73

**Acceptance Criteria**:
- All 7 tests pass
- PnL calculations accurate to 4 decimal places
- CSV export includes all V4 fields
- Cumulative tracking works correctly

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage4/test_exit_metrics.py -v
pytest /Users/botfarmer/2dex/tests/stage4/test_exit_metrics.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

**Dependencies**: Sub-Feature 3.3

**Estimated Time**: 2 hours

---

### Sub-Feature 3.5: Integration Test - Full Cycle

**Test File**: `/Users/botfarmer/2dex/tests/stage4/test_full_cycle_integration.py`

**Test Cases**:

```python
# Test 1: Complete BUILD cycle
GIVEN: No open positions
WHEN: execute_buy_first_cycle() or execute_sell_first_cycle() called
THEN: Positions opened, metrics recorded

# Test 2: Complete CLOSE cycle
GIVEN: Open positions from BUILD
WHEN: execute_unwind_cycle() called
THEN: Positions closed, PnL calculated

# Test 3: Multiple sequential cycles
GIVEN: Initial state
WHEN: 5 cycles executed
THEN: All cycles complete, cumulative PnL tracked

# Test 4: Cycle failure recovery
GIVEN: Cycle fails mid-execution
WHEN: Next cycle attempted
THEN: State cleaned up, new cycle starts

# Test 5: Daily reset across cycles
GIVEN: Cycles running across UTC midnight
WHEN: Midnight passes
THEN: Daily PnL reset to 0

# Test 6: Emergency stop during cycle
GIVEN: Cycle in progress
WHEN: Emergency triggered
THEN: Cycle halted, positions unwound
```

**Implementation File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Methods to Verify**:
- `execute_build_cycle()` - VERIFY existing (line 546)
- `execute_unwind_cycle()` - VERIFY existing (line 555)
- `execute_dn_pair_cycle()` - VERIFY existing (line 564)
- `run()` - VERIFY existing (line 2631)

**Acceptance Criteria**:
- All 6 tests pass
- Full cycle time <10s average
- State management correct
- Recovery works after failures

**Verification Commands**:
```bash
pytest /Users/botfarmer/2dex/tests/stage4/test_full_cycle_integration.py -v
pytest /Users/botfarmer/2dex/tests/stage4/test_full_cycle_integration.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=term-missing
```

**Dependencies**: All previous sub-features

**Estimated Time**: 2 hours

**Total Phase 3 Time**: 8-12 hours

---

## Phase Handoff Criteria

### Phase 0 → Phase 1 Handoff Checklist

**Before starting Phase 1 implementation**, verify:

- [ ] Research document complete at `/Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md`
- [ ] All 6 sections of research document filled with verified information
- [ ] Code examples from research tested and execute successfully
- [ ] Product IDs documented (ETH=?, SOL=?) and verified against SDK
- [ ] Order types verified (POST_ONLY, IOC, FOK, DEFAULT) match SDK enum
- [ ] WebSocket availability confirmed (YES/NO with evidence)
- [ ] REST API methods inventory complete with signatures
- [ ] Research validation test (Sub-Feature 0.6) passes all 6 test cases
- [ ] Plan reviewed and approved based on ACTUAL SDK capabilities

**Handoff Trigger**: Run `/Users/botfarmer/2dex/tests/stage1/test_phase0_research_validation.py` and ensure 100% pass rate

### Phase 1 → Phase 2 Handoff Checklist

**Before starting Phase 2 implementation**, verify:

- [ ] All Phase 1 tests pass (test_nado_rest_connection.py, test_nado_websocket.py, test_nado_order_placement.py, test_nado_connection_metrics.py)
- [ ] Test coverage >95% for connection infrastructure
- [ ] REST API connection stable with verified product IDs
- [ ] WebSocket connection working (if available from Phase 0)
- [ ] Order placement tested with all verified order types
- [ ] Connection metrics tracking functional
- [ ] Mock fixtures validated against actual SDK behavior

**Handoff Trigger**: Run `pytest /Users/botfarmer/2dex/tests/stage2/ -v --cov=exchanges.nado --cov-report=term` and ensure >95% coverage

### Phase 2 → Phase 3 Handoff Checklist

**Before starting Phase 3 implementation**, verify:

- [ ] All Phase 2 tests pass (test_v4_helpers.py, test_pre_trade_checks.py, test_simultaneous_orders.py, test_ioc_fill_detection.py, test_entry_reconciliation.py, test_entry_metrics.py)
- [ ] Test coverage >90% for entry logic
- [ ] BUILD cycle completes successfully with <8s average time
- [ ] Position reconciliation accurate with <1% drift
- [ ] Safety checks (MAX_POSITION, daily loss, net delta) functional
- [ ] V4 helper functions ported and tested
- [ ] Entry metrics collection matches V4 format

**Handoff Trigger**: Run `pytest /Users/botfarmer/2dex/tests/stage3/ -v --cov=hedge.DN_pair_eth_sol_nado --cov-report=term` and ensure >90% coverage

### Phase 3 → Production Handoff Checklist

**Before production deployment**, verify:

- [ ] All Phase 3 tests pass (test_post_only_orders.py, test_market_fallback.py, test_emergency_unwind.py, test_exit_metrics.py, test_full_cycle_integration.py)
- [ ] Test coverage >90% for exit logic
- [ ] CLOSE cycle completes successfully with <10s average time
- [ ] Emergency unwind functional and tested
- [ ] Full cycle integration test passes
- [ ] PnL calculations accurate to 4 decimal places
- [ ] Configuration validated for production (see Sub-Feature 4.0)
- [ ] All 4 phases complete with documented verification
- [ ] Overall test coverage >85%

**Handoff Trigger**: Run `pytest /Users/botfarmer/2dex/tests/ -v --cov=. --cov-report=term --cov-fail-under=85` and ensure 100% pass rate

---

## PHASE 4: Production Configuration (NEW)

**Goal**: Prepare production configuration with validated settings from Phase 0
**Duration**: 2 hours

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
THEN: ETH and SOL product IDs match Phase 0 research findings

# Test 3: Production config uses verified tick sizes from Phase 0
GIVEN: Production configuration file
WHEN: Tick sizes loaded
THEN: ETH and SOL tick sizes match Phase 0 research findings

# Test 4: Order type configuration matches Phase 0 findings
GIVEN: Production configuration file
WHEN: Order types loaded
THEN: Only order types verified in Phase 0 are used

# Test 5: Connection configuration matches Phase 0 capabilities
GIVEN: Production configuration file
WHEN: Connection settings loaded
THEN: WebSocket enabled/disabled based on Phase 0 findings

# Test 6: Risk limits within acceptable ranges
GIVEN: Production configuration file
WHEN: Risk limits loaded
THEN: MAX_POSITION, MAX_DAILY_LOSS, NET_DELTA_THRESHOLD set appropriately
```

**Implementation Tasks**:

1. **Update NADO_PRIVATE_KEY documentation**
   - Document required format: EVM wallet address (0x + 40 hex characters)
   - Add validation function to check format at startup
   - File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

2. **Create production configuration with Phase 0 values**
   - ETH_PRODUCT_ID: [FROM_PHASE0_RESEARCH]
   - SOL_PRODUCT_ID: [FROM_PHASE0_RESEARCH]
   - ETH_TICK_SIZE: [FROM_PHASE0_RESEARCH]
   - SOL_TICK_SIZE: [FROM_PHASE0_RESEARCH]
   - WEBSOCKET_ENABLED: [FROM_PHASE0_RESEARCH]
   - File: `/Users/botfarmer/2dex/config/production_config.json`

3. **Add configuration validation test**
   - Test file: `/Users/botfarmer/2dex/tests/stage4/test_production_config.py`
   - Verify all config values match Phase 0 research
   - Test configuration loading and validation

**Acceptance Criteria**:
- All 6 configuration tests pass
- Production config uses only verified values from Phase 0
- NADO_PRIVATE_KEY format validated at startup
- Configuration documented with all Phase 0 findings

**Verification Commands**:

```bash
# Run configuration validation tests
pytest /Users/botfarmer/2dex/tests/stage4/test_production_config.py -v

# Verify production config exists
cat /Users/botfarmer/2dex/config/production_config.json

# Test configuration loading
python -c "
import json
with open('/Users/botfarmer/2dex/config/production_config.json', 'r') as f:
    config = json.load(f)
    print('ETH Product ID:', config['ETH_PRODUCT_ID'])
    print('SOL Product ID:', config['SOL_PRODUCT_ID'])
    print('WebSocket Enabled:', config['WEBSOCKET_ENABLED'])
"
```

**Dependencies**: Phase 0 complete (all research findings available)

**Estimated Time**: 2 hours

**Total Phase 4 Time**: 2 hours

---

## Risk Mitigation

### What Could Go Wrong

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|---------------------|
| **Nado SDK WebSocket unavailable** | High | Medium | Phase 0 research will confirm, REST is primary |
| **Nado order types not supported** | High | Low | Phase 0 research will verify, fallback to MARKET |
| **Position reconciliation drift** | High | Medium | Strict 1% tolerance, auto-recovery (EXISTS, verify) |
| **Daily loss limit not enforced** | Critical | Low | Triple-check implementation (EXISTS, verify) |
| **Net delta monitoring fails** | High | Medium | Multi-source validation (EXISTS, verify) |
| **Concurrent order race conditions** | Medium | Medium | Use asyncio.gather() (EXISTS, verify) |
| **Test environment differs from production** | Medium | Medium | Use Nado testnet, mock only where necessary |
| **V4 functions don't port cleanly** | Medium | Low | Phase 0 research will identify gaps early |

### Testing Strategy for Risk Mitigation

**Pre-Deployment Testing**:
1. **Phase 0 Research**: All SDK capabilities verified before implementation
2. **Nado Testnet**: All tests run against Nado testnet first
3. **Small Size Tests**: Start with 0.01 ETH/SOL sizes
4. **Manual Override**: Include emergency stop in all integration tests
5. **Position Limits**: Enforce strict limits during testing (MAX_POSITION = 0.1)

**Production Rollout**:
1. **Canary Deployment**: Run 1 cycle, verify all metrics
2. **Gradual Scale**: Increase from 0.01 → 0.05 → 0.1 ETH sizes
3. **24h Monitoring**: Continuous monitoring for first day
4. **Rollback Plan**: Keep existing Nado code as fallback

---

## Verification Steps

### Phase 0 Verification

```bash
# Check research document exists
cat /Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md

# Verify all sections filled
grep -E "## [0-9]\." /Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md

# Verify code examples tested
python -c "# Run code examples from research document"
```

**Acceptance**: Research document complete, all code examples tested, clear recommendations provided

### Phase 1 Verification

```bash
# Run all Phase 1 tests
pytest /Users/botfarmer/2dex/tests/stage2/ -v

# Check coverage
pytest /Users/botfarmer/2dex/tests/stage2/ --cov=exchanges.nado --cov-report=html --cov-report=term

# Manual verification
python -c "from exchanges.nado import NadoClient; import asyncio; asyncio.run(NadoClient({'ticker': 'ETH'}))"
```

**Acceptance**: All tests pass, coverage >95%, connection stable

### Phase 2 Verification

```bash
# Run all Phase 2 tests
pytest /Users/botfarmer/2dex/tests/stage3/ -v

# Check coverage
pytest /Users/botfarmer/2dex/tests/stage3/ --cov=hedge.DN_pair_eth_sol_nado --cov-report=html --cov-report=term

# Integration test
python /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py --size 1 --iter 1 --test-mode
```

**Acceptance**: All tests pass, coverage >90%, BUILD cycle completes <8s

### Phase 3 Verification

```bash
# Run all Phase 3 tests
pytest /Users/botfarmer/2dex/tests/stage4/ -v

# Check coverage
pytest /Users/botfarmer/2dex/tests/stage4/ --cov=exchanges.nado --cov=hedge.DN_pair_eth_sol_nado --cov-report=html --cov-report=term

# Full cycle test
python /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py --size 10 --iter 5

# Metrics validation
python -c "import csv; f = open('logs/DN_pair_eth_sol_nado_trades.csv'); print(csv.DictReader(f).fieldnames)"
```

**Acceptance**: All tests pass, coverage >90%, full cycle <10s

### Final Verification

```bash
# Complete test suite
pytest /Users/botfarmer/2dex/tests/ -v --tb=short

# Coverage report
pytest /Users/botfarmer/2dex/tests/ --cov=. --cov-report=html --cov-report=term --cov-fail-under=85

# Performance benchmark
python /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py --size 10 --iter 20 --benchmark

# Log validation
tail -100 /Users/botfarmer/2dex/logs/DN_pair_eth_sol_nado_log.txt | grep -E "(BUILD|CLOSE|PnL)"
```

**Acceptance Criteria**:
- All tests pass (100%)
- Coverage >85% overall, >90% for critical paths
- Average cycle time <10s, target 8s
- Fill rate >95%
- Position drift <1%
- No critical errors in logs

---

## Implementation Sequence

### Order of Implementation (Numbered Steps)

**Phase 0: Nado SDK Research (PREREQUISITE)**
1. Sub-Feature 0.1: WebSocket Capability Investigation (3h)
2. Sub-Feature 0.2: Order Type Support Verification (2h)
3. Sub-Feature 0.3: REST API Method Inventory (3h)
4. Sub-Feature 0.4: Product ID and Contract Verification (2h)
5. Sub-Feature 0.5: Research Documentation Output (2h)
6. Sub-Feature 0.6: Research Validation (1h) - NEW

**Phase 1: Connection Infrastructure**
6. Sub-Feature 1.1: REST API Connection Verification (2h)
7. Sub-Feature 1.2: WebSocket Connection (4h or 0h based on Phase 0)
8. Sub-Feature 1.3: Order Placement Verification (3h)
9. Sub-Feature 1.4: Connection Monitoring and Metrics (2h)

**Phase 2: Entry Logic (BUILD Cycles)**
10. Sub-Feature 2.1: V4 Helper Functions Port (2h)
11. Sub-Feature 2.2: Pre-Trade Safety Checks Verification (2h)
12. Sub-Feature 2.3: Simultaneous Order Placement Verification (2h)
13. Sub-Feature 2.4: IOC Order Fill Detection Verification (2h)
14. Sub-Feature 2.5: Position Reconciliation Verification (2h)
15. Sub-Feature 2.6: Entry Metrics Collection Verification (2h)

**Phase 3: Unwind Logic (CLOSE Cycles)**
16. Sub-Feature 3.1: POST_ONLY Order Placement Verification (2h)
17. Sub-Feature 3.2: MARKET Order Fallback Verification (2h)
18. Sub-Feature 3.3: Emergency Unwind Logic Verification (2h)
19. Sub-Feature 3.4: Exit Metrics and PnL Calculation Verification (2h)
20. Sub-Feature 3.5: Integration Test - Full Cycle (2h)

**Phase 4: Production Configuration (NEW)**
21. Sub-Feature 4.0: Production Configuration Validation (2h) - NEW

### Dependencies Between Steps

```
Phase 0 (Research) ──> REQUIRED BEFORE ALL IMPLEMENTATION

0.1 (WebSocket) ─────┐
0.2 (Order Types) ───┤
0.3 (REST API) ───────┼──> 0.5 (Research Doc) ──> Phase 1
0.4 (Products) ───────┘

Phase 1 Complete ──> 2.1 (V4 Helpers) ──> 2.2 (Safety) ──> 2.3 (Simultaneous)
                                                              │
                        2.3 ──> 2.4 (IOC Fill) ──> 2.5 (Reconcile) ──> 2.6 (Metrics)
                                                              │
Phase 2 Complete ──────────────────────────────────────────────┘
                        │
                        └──> 3.1 (POST_ONLY) ──> 3.2 (MARKET)
                                                   │
                                      3.2 ──> 3.3 (Emergency)
                                                   │
                                      3.3 ──> 3.4 (Exit Metrics)
                                                   │
                                      3.4 ──> 3.5 (Full Cycle) ──> DONE
```

### File Paths Summary

**Research Output**:
- `/Users/botfarmer/2dex/.omc/research/nado-sdk-capabilities.md`

**Exchange Client** (VERIFY and ENHANCE):
- `/Users/botfarmer/2dex/exchanges/nado.py` - Main Nado client implementation

**Bot Logic** (VERIFY and ENHANCE):
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - DN pair bot main logic

**Reference Files** (READ ONLY):
- `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py` - V4 reference
- `/Users/botfarmer/2dex/perp-dex-tools-original/hedge/exchanges/grvt.py` - V4 helpers

**Test Files** (to be created):
- `/Users/botfarmer/2dex/tests/stage1/test_phase0_research_validation.py` - NEW
- `/Users/botfarmer/2dex/tests/stage2/test_nado_rest_connection.py`
- `/Users/botfarmer/2dex/tests/stage2/test_nado_websocket.py`
- `/Users/botfarmer/2dex/tests/stage2/test_nado_order_placement.py`
- `/Users/botfarmer/2dex/tests/stage2/test_nado_connection_metrics.py`
- `/Users/botfarmer/2dex/tests/stage3/test_v4_helpers.py`
- `/Users/botfarmer/2dex/tests/stage3/test_pre_trade_checks.py`
- `/Users/botfarmer/2dex/tests/stage3/test_simultaneous_orders.py`
- `/Users/botfarmer/2dex/tests/stage3/test_ioc_fill_detection.py`
- `/Users/botfarmer/2dex/tests/stage3/test_entry_reconciliation.py`
- `/Users/botfarmer/2dex/tests/stage3/test_entry_metrics.py`
- `/Users/botfarmer/2dex/tests/stage4/test_post_only_orders.py`
- `/Users/botfarmer/2dex/tests/stage4/test_market_fallback.py`
- `/Users/botfarmer/2dex/tests/stage4/test_emergency_unwind.py`
- `/Users/botfarmer/2dex/tests/stage4/test_exit_metrics.py`
- `/Users/botfarmer/2dex/tests/stage4/test_full_cycle_integration.py`
- `/Users/botfarmer/2dex/tests/stage4/test_production_config.py` - NEW

**Configuration Files** (to be created):
- `/Users/botfarmer/2dex/config/production_config.json` - NEW

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
| **REST Latency** | <500ms | Connection metrics |
| **WebSocket Latency** | <100ms (if available) | Connection metrics |
| **Daily PnL Accuracy** | ±$0.01 vs manual calc | Automated validation |
| **Emergency Unwind** | <10s to close all | Emergency test |

### Qualitative Metrics

- Code readability matches V4 reference style
- All V4 safety features verified and tested
- Error handling comprehensive (no uncaught exceptions)
- Logging sufficient for debugging (all critical paths logged)
- Documentation clear (docstrings for all public methods)
- CSV export format compatible with analysis tools

---

## Conclusion

This plan provides a RESEARCH-FIRST, test-driven approach to migrating V4 DN pair implementation to Nado. Each sub-feature is:

1. **Research-Backed**: Phase 0 verifies ALL SDK capabilities before implementation
2. **Reuse-Aware**: Acknowledges existing functions, avoids reimplementation
3. **Verification-Focused**: VERIFY existing code before enhancing
4. **Time-Bounded**: 1-4 hours per sub-feature after Phase 0
5. **Dependency-Aware**: Clear ordering and dependencies
6. **Risk-Mitigated**: Multiple fallback strategies
7. **Verification-Ready**: Specific test commands and acceptance criteria

**Total Estimated Time**: 51-74 hours (including 13-hour Phase 0 research + 2-hour Phase 4 config)
**Total Sub-Features**: 21 (6 in Phase 0, 5 in Phase 1, 6 in Phase 2, 4 in Phase 3, 1 in Phase 4)
**Test Files**: 17 (added test_phase0_research_validation.py, test_production_config.py)
**Implementation Files**: 2 (nado.py, DN_pair_eth_sol_nado.py) - VERIFY and ENHANCE
**Research Output**: 1 (nado-sdk-capabilities.md)
**Configuration Files**: 1 (production_config.json)

**Critical Improvements Over Original Plan**:
1. **Phase 0 research first** - No assumptions about SDK capabilities
2. **Existing functions acknowledged** - No wasted effort reimplementing
3. **Conditional WebSocket** - Only implement if SDK supports it
4. **Absolute file paths** - All paths are explicit
5. **V4 references explicit** - Clear line numbers and file locations
6. **Realistic estimates** - Based on research-first approach
7. **Phase 0 validation tests** - Sub-Feature 0.6 ensures research accuracy
8. **Directory structure prerequisites** - Explicit setup commands before Phase 0
9. **Mock strategy defined** - pytest-mock with example fixtures provided
10. **Phase handoff criteria** - Clear checklists between each phase
11. **Production configuration** - Phase 4 ensures config matches research
12. **Comprehensive validation** - 21 sub-features with 17 test files

**Next Steps**:
1. **CRITICAL**: Set up directory structure (see Prerequisites section)
2. **CRITICAL**: Complete Phase 0 research first
3. **CRITICAL**: Run Phase 0 validation tests (Sub-Feature 0.6)
4. Review research findings with team
5. Adjust Phases 1-4 based on ACTUAL SDK capabilities
6. Begin Phase 1 implementation
7. Track progress with pytest after each sub-feature
8. Follow Phase Handoff Criteria checklists between phases
9. Complete Phase 4 production configuration before deployment

---

## Final Checklist - All 5 Critic Improvements Implemented

- [X] **Sub-Feature 0.6: Research Validation** - Added to Phase 0 (1 hour)
  - Test file: `/Users/botfarmer/2dex/tests/stage1/test_phase0_research_validation.py`
  - 6 test cases to validate research document completeness and accuracy
  - Validates code examples execute successfully
  - Verifies product IDs and order types against actual SDK

- [X] **Directory Structure Prerequisites** - Added before Phase 0
  - Commands to create `/Users/botfarmer/2dex/tests/stage1-4`
  - Commands to create `/Users/botfarmer/2dex/.omc/research`
  - Verification commands to ensure directories exist

- [X] **Mock Strategy Section** - Added with pytest-mock examples
  - Library: pytest-mock + unittest.mock
  - Mock fixtures for NadoClient and WebSocket
  - Example code in `/Users/botfarmer/2dex/tests/conftest.py`
  - Mock usage patterns for all test stages

- [X] **Phase Handoff Criteria** - Added for all phase transitions
  - Phase 0 → Phase 1: 9-item checklist before starting implementation
  - Phase 1 → Phase 2: 7-item checklist for connection infrastructure
  - Phase 2 → Phase 3: 7-item checklist for entry logic
  - Phase 3 → Production: 9-item checklist before deployment
  - Handoff triggers with specific pytest commands

- [X] **Sub-Feature 4.0: Production Configuration** - Added as new phase
  - Test file: `/Users/botfarmer/2dex/tests/stage4/test_production_config.py`
  - 6 test cases for configuration validation
  - Production config file: `/Users/botfarmer/2dex/config/production_config.json`
  - NADO_PRIVATE_KEY format documentation
  - Uses only verified values from Phase 0 research

- [X] **Time Estimates Updated** - Reflect all additions
  - Phase 0: 12 hours → 13 hours (+1 hour for validation)
  - Phase 4: NEW - 2 hours for production configuration
  - Total: 48-68 hours → 51-74 hours

- [X] **All Paths Still Absolute** - Verified all file paths use absolute paths

- [X] **No Existing Functions Marked for Reimplementation** - All existing functions marked as "VERIFY" or "ENHANCE", never "REIMPLEMENT"

---

---

**Plan Status**: FINAL - ALL 5 CRITIC IMPROVEMENTS IMPLEMENTED - 100% READY

**Last Updated**: 2026-01-29
**Version**: 3.0 (Iteration 2 - Final Refinement - All Critic Improvements Complete)
