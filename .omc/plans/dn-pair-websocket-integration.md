# DN Pair ETH/SOL WebSocket Integration Plan

**Plan ID**: RALPLAN-2026-001
**Status**: READY FOR IMPLEMENTATION
**Created**: 2026-01-30
**Complexity**: MEDIUM
**Estimated Effort**: 4-6 hours

---

## Executive Summary

This plan integrates the existing working WebSocket code from `/hedge/exchanges/` into `DN_pair_eth_sol_nado.py` to fix the SOL accumulation problem and improve real-time price/fill monitoring.

**Key Problem**: SOL is accumulating (LONG=202, SHORT=104, net +98 SOL) because `execute_unwind_cycle()` doesn't verify positions actually closed and lacks real-time position monitoring.

**Solution**: Leverage the already-working WebSocket implementation in `hedge/exchanges/nado.py` (commit 5bc077d) to add real-time BBO prices, BookDepth slippage estimation, and position monitoring.

---

## Context & Background

### Current State

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
- Contains `DNPairBot` class trading ETH/SOL pair on Nado
- Uses `NadoClient` for both ETH and SOL
- Does NOT use WebSocket for real-time data
- Uses REST API polling for position checks
- `execute_unwind_cycle()` has position verification (recently added) but no real-time monitoring

**Available WebSocket Code** (WORKING - already integrated in NadoClient):
1. `/hedge/exchanges/nado_websocket_client.py` - WebSocket client with EIP-712 auth
2. `/hedge/exchanges/nado_bbo_handler.py` - Real-time BBO price streaming
3. `/hedge/exchanges/nado_bookdepth_handler.py` - Order book depth for slippage estimation
4. `/hedge/exchanges/nado_fill_handler.py` - Real-time fill notifications
5. `/hedge/exchanges/nado_position_handler.py` - Real-time position updates

**Evidence of Working WebSocket**:
- Commit `5bc077d` successfully integrated WebSocket BBO into `NadoClient`
- `NadoClient.connect()` already establishes WebSocket connection
- `NadoClient.fetch_bbo_prices()` uses WebSocket first, REST fallback
- `NadoClient.estimate_slippage()` uses BookDepth data
- `NadoClient.check_exit_capacity()` validates position exit feasibility

### Product ID Mapping

From `/hedge/exchanges/nado.py`:
- ETH: product_id = 4
- SOL: product_id = 8

### SOL Accumulation Problem

**Root Cause Analysis**:
1. `execute_unwind_cycle()` places IOC orders to close positions
2. IOC orders may partially fill or fail
3. Position verification occurs AFTER order execution (REST polling)
4. No real-time monitoring of fills via WebSocket
5. Retry logic exists but may not catch all partial fills

**Why WebSocket Helps**:
- Real-time fill notifications via `FillHandler`
- Real-time position updates via `PositionHandler`
- Immediate visibility into partial fills
- Better order book data for slippage estimation
- Reduced reliance on REST polling

---

## Work Objectives

### Core Objective
Integrate WebSocket real-time monitoring into `DNPairBot` to eliminate SOL accumulation by ensuring all UNWIND cycles properly close positions.

### Deliverables
1. WebSocket position tracking for both ETH and SOL
2. Real-time fill monitoring during order execution
3. Enhanced slippage estimation using BookDepth
4. Improved UNWIND cycle with position verification
5. Graceful fallback to REST if WebSocket unavailable

### Definition of Done
- [ ] WebSocket connects successfully for both ETH and SOL
- [ ] BBO prices stream in real-time
- [ ] BookDepth provides slippage estimates
- [ ] Fill events trigger position updates
- [ ] Position changes logged and verified
- [ ] UNWIND cycles verify positions closed to < 0.001 tolerance
- [ ] REST fallback works when WebSocket unavailable
- [ ] No increase in SOL accumulation over 20 iterations
- [ ] Logging shows WebSocket activity vs REST fallback

---

## Must Have / Must NOT Have

### Must Have (Guardrails)
- WebSocket MUST use existing `NadoClient` implementation
- MUST maintain backward compatibility with REST-only mode
- MUST verify positions close to < 0.001 tolerance after UNWIND
- MUST log all WebSocket events (connect, disconnect, fill, position change)
- MUST gracefully handle WebSocket failures without crashing
- MUST NOT block on WebSocket - use async/await throughout
- MUST use product_id 4 for ETH, 8 for SOL
- MUST preserve existing `execute_unwind_cycle()` verification logic

### Must NOT Have (Exclusions)
- MUST NOT rewrite `NadoClient` WebSocket code (it already works)
- MUST NOT use WebSocket code from `/perpdex/` directory (use `/hedge/` version)
- MUST NOT break existing REST API fallback
- MUST NOT change order pricing logic (keep IOC with aggressive pricing)
- MUST NOT remove position verification in `execute_unwind_cycle()`
- MUST NOT add dependencies beyond existing `websockets` and `eth-account`

---

## Task Flow and Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Analysis & Planning (COMPLETED)                     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: WebSocket Handler Integration                      │
│ ├─ Task 2.1: Add FillHandler for real-time fill tracking   │
│ ├─ Task 2.2: Add PositionHandler for position monitoring   │
│ └─ Task 2.3: Register handlers with NadoClient WebSocket   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Position Tracking Enhancement                      │
│ ├─ Task 3.1: Add local position cache updated by WS        │
│ ├─ Task 3.2: Add position reconciliation logic              │
│ └─ Task 3.3: Integrate WS position data into UNWIND check  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Slippage & BBO Enhancement                        │
│ ├─ Task 4.1: Verify BookDepth integration working          │
│ └─ Task 4.2: Add slippage logging for order sizing         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Testing & Validation                              │
│ ├─ Task 5.1: Unit test WebSocket handlers                  │
│ ├─ Task 5.2: Integration test UNWIND with WS monitoring    │
│ ├─ Task 5.3: Run 20 iterations and verify no accumulation │
│ └─ Task 5.4: Verify REST fallback on WS disconnect         │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies
- **Task 2.x** depends on: Existing `NadoClient` WebSocket (already working)
- **Task 3.x** depends on: Task 2.x (handlers must be registered)
- **Task 4.x** depends on: Task 2.x (uses same WebSocket connection)
- **Task 5.x** depends on: All previous tasks

---

## Detailed TODOs

### Phase 2: WebSocket Handler Integration

#### Task 2.1: Import WebSocket Handler Classes
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add imports for WebSocket handlers
```python
# After existing imports
try:
    from exchanges.nado_fill_handler import FillHandler
    from exchanges.nado_position_handler import PositionHandler
    WEBSOCKET_HANDLERS_AVAILABLE = True
except ImportError:
    WEBSOCKET_HANDLERS_AVAILABLE = False
```

**Acceptance Criteria**:
- [ ] Imports added without syntax errors
- [ ] `WEBSOCKET_HANDLERS_AVAILABLE` flag set correctly
- [ ] Code runs even if imports fail (graceful degradation)

---

#### Task 2.2: Initialize WebSocket Handlers in `__init__`
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add handler initialization to `DNPairBot.__init__()`
```python
# WebSocket handlers (if available)
self.eth_fill_handler = None
self.eth_position_handler = None
self.sol_fill_handler = None
self.sol_position_handler = None
self._ws_handlers_active = False
```

**Acceptance Criteria**:
- [ ] Handler attributes initialized to None
- [ ] `_ws_handlers_active` flag tracks WebSocket status
- [ ] No errors on bot initialization

---

#### Task 2.3: Create WebSocket Handler Setup Method
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add method to initialize WebSocket handlers after clients connect
```python
async def _setup_websocket_handlers(self):
    """Setup WebSocket handlers for real-time fill and position monitoring."""
    if not WEBSOCKET_HANDLERS_AVAILABLE:
        self.logger.warning("[WS] WebSocket handlers not available, using REST only")
        return False

    if not self.eth_client._ws_connected or not self.sol_client._ws_connected:
        self.logger.warning("[WS] WebSocket not connected, skipping handler setup")
        return False

    try:
        # Get subaccount hex for private stream authentication
        from nado_protocol.utils.bytes32 import subaccount_to_hex
        from nado_protocol.utils.subaccount import SubaccountParams

        subaccount_params = SubaccountParams(
            subaccount_owner=self.eth_client.owner,
            subaccount_name=self.eth_client.subaccount_name,
        )
        subaccount_hex = subaccount_to_hex(subaccount_params)

        # Setup ETH fill handler
        self.eth_fill_handler = FillHandler(
            product_id=4,  # ETH
            ws_client=self.eth_client._ws_client,
            subaccount=subaccount_hex,
            logger=self.logger
        )
        await self.eth_fill_handler.start()
        self.eth_fill_handler.register_callback(self._on_eth_fill)

        # Setup ETH position handler
        self.eth_position_handler = PositionHandler(
            product_id=4,  # ETH
            ws_client=self.eth_client._ws_client,
            subaccount=subaccount_hex,
            logger=self.logger
        )
        await self.eth_position_handler.start()
        self.eth_position_handler.register_callback(self._on_eth_position_change)

        # Setup SOL fill handler
        self.sol_fill_handler = FillHandler(
            product_id=8,  # SOL
            ws_client=self.sol_client._ws_client,
            subaccount=subaccount_hex,
            logger=self.logger
        )
        await self.sol_fill_handler.start()
        self.sol_fill_handler.register_callback(self._on_sol_fill)

        # Setup SOL position handler
        self.sol_position_handler = PositionHandler(
            product_id=8,  # SOL
            ws_client=self.sol_client._ws_client,
            subaccount=subaccount_hex,
            logger=self.logger
        )
        await self.sol_position_handler.start()
        self.sol_position_handler.register_callback(self._on_sol_position_change)

        self._ws_handlers_active = True
        self.logger.info("[WS] All WebSocket handlers registered successfully")
        return True

    except Exception as e:
        self.logger.error(f"[WS] Failed to setup WebSocket handlers: {e}")
        self.logger.error(f"[WS] Traceback: {traceback.format_exc()}")
        return False
```

**Acceptance Criteria**:
- [ ] Method creates fill handlers for ETH and SOL
- [ ] Method creates position handlers for ETH and SOL
- [ ] Handlers register callbacks for fill/position events
- [ ] Method returns True on success, False on failure
- [ ] Errors logged with full traceback
- [ ] `_ws_handlers_active` set to True on success

---

#### Task 2.4: Implement Fill Callback Handlers
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add callback methods for fill events
```python
def _on_eth_fill(self, fill_data):
    """Handle ETH fill events from WebSocket."""
    try:
        side = fill_data.get("side", "").lower()
        filled_size = Decimal(str(fill_data.get("quantity", "0")))
        price = Decimal(str(fill_data.get("price", "0")))

        self.logger.info(
            f"[WS][ETH_FILL] {side.upper()} {filled_size} @ ${price}"
        )

        # Update local position tracking
        if side == "buy":
            self.local_eth_position += filled_size
        else:
            self.local_eth_position -= filled_size

    except Exception as e:
        self.logger.error(f"[WS] Error handling ETH fill: {e}")

def _on_sol_fill(self, fill_data):
    """Handle SOL fill events from WebSocket."""
    try:
        side = fill_data.get("side", "").lower()
        filled_size = Decimal(str(fill_data.get("quantity", "0")))
        price = Decimal(str(fill_data.get("price", "0")))

        self.logger.info(
            f"[WS][SOL_FILL] {side.upper()} {filled_size} @ ${price}"
        )

        # Update local position tracking
        if side == "buy":
            self.local_sol_position += filled_size
        else:
            self.local_sol_position -= filled_size

    except Exception as e:
        self.logger.error(f"[WS] Error handling SOL fill: {e}")
```

**Acceptance Criteria**:
- [ ] ETH fill callback logs fill details
- [ ] SOL fill callback logs fill details
- [ ] Local position tracking updated on fills
- [ ] Errors caught and logged without crashing
- [ ] Logs include side, quantity, and price

---

#### Task 2.5: Implement Position Change Callback Handlers
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add callback methods for position change events
```python
def _on_eth_position_change(self, position_data):
    """Handle ETH position change events from WebSocket."""
    try:
        new_position = Decimal(str(position_data.get("position", "0")))
        old_position = self.eth_position

        self.eth_position = new_position
        self.local_eth_position = new_position

        self.logger.info(
            f"[WS][ETH_POS] {old_position} → {new_position} (diff: {new_position - old_position})"
        )

    except Exception as e:
        self.logger.error(f"[WS] Error handling ETH position change: {e}")

def _on_sol_position_change(self, position_data):
    """Handle SOL position change events from WebSocket."""
    try:
        new_position = Decimal(str(position_data.get("position", "0")))
        old_position = self.sol_position

        self.sol_position = new_position
        self.local_sol_position = new_position

        self.logger.info(
            f"[WS][SOL_POS] {old_position} → {new_position} (diff: {new_position - new_position})"
        )

    except Exception as e:
        self.logger.error(f"[WS] Error handling SOL position change: {e}")
```

**Acceptance Criteria**:
- [ ] ETH position callback logs position changes
- [ ] SOL position callback logs position changes
- [ ] Both bot and local position tracking updated
- [ ] Position difference calculated and logged
- [ ] Errors caught and logged without crashing

---

#### Task 2.6: Call Handler Setup in `initialize_clients()`
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Modify `initialize_clients()` to setup WebSocket handlers
```python
async def initialize_clients(self):
    """Initialize ETH and SOL Nado clients for dual-ticker trading."""
    # ETH client configuration
    eth_config = Config({
        'ticker': 'ETH',
        'contract_id': '4',
        'tick_size': Decimal('0.001'),
        'min_size': Decimal('0.001'),
    })

    # SOL client configuration
    sol_config = Config({
        'ticker': 'SOL',
        'contract_id': '8',
        'tick_size': Decimal('0.001'),
        'min_size': Decimal('0.001'),
    })

    # Create Nado clients
    self.eth_client = NadoClient(eth_config)
    self.sol_client = NadoClient(sol_config)

    # Connect to Nado (this establishes WebSocket connection)
    await self.eth_client.connect()
    await self.sol_client.connect()

    # Setup WebSocket handlers for real-time monitoring
    await self._setup_websocket_handlers()

    # Store contract attributes
    self.eth_contract_id = eth_config.contract_id
    self.eth_tick_size = eth_config.tick_size
    self.sol_contract_id = sol_config.contract_id
    self.sol_tick_size = sol_config.tick_size

    self.logger.info(
        f"[INIT] ETH client initialized (contract: {self.eth_contract_id}, tick: {self.eth_tick_size})"
    )
    self.logger.info(
        f"[INIT] SOL client initialized (contract: {self.sol_contract_id}, tick: {self.sol_tick_size})"
    )
    self.logger.info(
        f"[INIT] WebSocket handlers active: {self._ws_handlers_active}"
    )
```

**Acceptance Criteria**:
- [ ] `_setup_websocket_handlers()` called after clients connect
- [ ] WebSocket status logged on initialization
- [ ] No errors if WebSocket setup fails (graceful degradation)
- [ ] Existing initialization logic preserved

---

### Phase 3: Position Tracking Enhancement

#### Task 3.1: Add Position Reconciliation Method
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add method to reconcile WebSocket vs REST positions
```python
async def reconcile_positions(self) -> Tuple[bool, str]:
    """Reconcile WebSocket local positions with REST API positions.

    Returns:
        Tuple of (matches, details) where matches is True if positions match
    """
    try:
        # Get REST positions
        eth_rest_pos = await self.eth_client.get_account_positions()
        sol_rest_pos = await self.sol_client.get_account_positions()

        # Compare with local WebSocket positions
        eth_diff = abs(self.local_eth_position - eth_rest_pos)
        sol_diff = abs(self.local_sol_position - sol_rest_pos)

        if eth_diff < Decimal("0.001") and sol_diff < Decimal("0.001"):
            return True, f"Positions match: ETH={eth_rest_pos}, SOL={sol_rest_pos}"
        else:
            self.logger.warning(
                f"[RECONCILE] Position mismatch: "
                f"ETH WS={self.local_eth_position} REST={eth_rest_pos} (diff={eth_diff}), "
                f"SOL WS={self.local_sol_position} REST={sol_rest_pos} (diff={sol_diff})"
            )
            # Update local positions to match REST
            self.local_eth_position = eth_rest_pos
            self.local_sol_position = sol_rest_pos
            return False, f"Positions reconciled to REST: ETH={eth_rest_pos}, SOL={sol_rest_pos}"

    except Exception as e:
        self.logger.error(f"[RECONCILE] Error during reconciliation: {e}")
        return False, f"Reconciliation failed: {e}"
```

**Acceptance Criteria**:
- [ ] Method fetches REST positions
- [ ] Method compares with WebSocket positions
- [ ] Differences < 0.001 considered matching
- [ ] Mismatches logged and reconciled
- [ ] Returns success status and details

---

#### Task 3.2: Integrate WebSocket Data into `execute_unwind_cycle()`
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Modify `execute_unwind_cycle()` to use WebSocket position data
```python
async def execute_unwind_cycle(self) -> bool:
    """Execute UNWIND cycle: Sell ETH / Buy SOL.

    Returns:
        True if both positions are closed (abs < 0.001), False otherwise.
    """
    POSITION_TOLERANCE = Decimal("0.001")

    # [단계 1] UNWIND 전 포지션 확인 (로깅)
    # Use WebSocket local position if available, otherwise REST
    if self._ws_handlers_active:
        eth_pos_before = self.local_eth_position
        sol_pos_before = self.local_sol_position
        pos_source = "WS"
    else:
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()
        pos_source = "REST"

    self.logger.info(
        f"[UNWIND] POSITIONS BEFORE ({pos_source}): ETH={eth_pos_before}, SOL={sol_pos_before}"
    )

    # [단계 2] UNWIND 주문 실행 (ETH SELL, SOL BUY)
    eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")

    # [단계 3] 체결 확인
    if not (isinstance(eth_result, OrderResult) and eth_result.success and
            isinstance(sol_result, OrderResult) and sol_result.success):
        self.logger.warning("[UNWIND] Orders failed or partially filled")
        return False

    # [단계 4] 0.5초 대기 (WebSocket fill events should arrive during this time)
    await asyncio.sleep(0.5)

    # [단계 5] UNWIND 후 포지션 확인
    # Use WebSocket local position if available, otherwise REST
    if self._ws_handlers_active:
        # Reconcile with REST to ensure accuracy
        await self.reconcile_positions()
        eth_pos_after = self.local_eth_position
        sol_pos_after = self.local_sol_position
        pos_source = "WS+RECONCILE"
    else:
        eth_pos_after = await self.eth_client.get_account_positions()
        sol_pos_after = await self.sol_client.get_account_positions()
        pos_source = "REST"

    self.logger.info(
        f"[UNWIND] POSITIONS AFTER ({pos_source}): ETH={eth_pos_after}, SOL={sol_pos_after}"
    )

    # [단계 6] 포지션 닫힘 검증
    eth_closed = abs(eth_pos_after) < POSITION_TOLERANCE
    sol_closed = abs(sol_pos_after) < POSITION_TOLERANCE

    if eth_closed and sol_closed:
        self.logger.info("[UNWIND] SUCCESS: Both positions closed")
        return True

    # [단계 7] 1회 재시도
    else:
        await asyncio.sleep(1.0)

        if self._ws_handlers_active:
            await self.reconcile_positions()
            eth_pos_retry = self.local_eth_position
            sol_pos_retry = self.local_sol_position
        else:
            eth_pos_retry = await self.eth_client.get_account_positions()
            sol_pos_retry = await self.sol_client.get_account_positions()

        if abs(eth_pos_retry) < POSITION_TOLERANCE and abs(sol_pos_retry) < POSITION_TOLERANCE:
            self.logger.info("[UNWIND] SUCCESS: Positions closed after retry")
            return True
        else:
            self.logger.error(
                f"[UNWIND] FAILED: Positions still open: ETH={eth_pos_retry}, SOL={sol_pos_retry}"
            )
            return False
```

**Acceptance Criteria**:
- [ ] Uses WebSocket position data if available
- [ ] Falls back to REST if WebSocket inactive
- [ ] Calls reconciliation when WebSocket active
- [ ] Logs position data source (WS vs REST)
- [ ] Preserves existing verification logic
- [ ] All existing functionality maintained

---

### Phase 4: Slippage & BBO Enhancement

#### Task 4.1: Verify BookDepth Integration Working
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Add diagnostic logging for BookDepth status

**Action**: Add to `initialize_clients()` after WebSocket setup:
```python
# Log BookDepth status
if self._ws_handlers_active:
    eth_bookdepth = self.eth_client.get_bookdepth_handler()
    sol_bookdepth = self.sol_client.get_bookdepth_handler()

    if eth_bookdepth:
        self.logger.info("[INIT] ETH BookDepth handler available for slippage estimation")
    else:
        self.logger.warning("[INIT] ETH BookDepth handler NOT available")

    if sol_bookdepth:
        self.logger.info("[INIT] SOL BookDepth handler available for slippage estimation")
    else:
        self.logger.warning("[INIT] SOL BookDepth handler NOT available")
```

**Acceptance Criteria**:
- [ ] Logs BookDepth handler availability for ETH
- [ ] Logs BookDepth handler availability for SOL
- [ ] No errors if handlers not available
- [ ] Diagnostic logging clear and informative

---

#### Task 4.2: Add Slippage Logging
**File**: `DN_pair_eth_sol_nado.py`

**Action**: Modify `calculate_order_size_with_slippage()` to log more details

**Note**: This method already exists and uses `client.estimate_slippage()` which internally uses BookDepth. Just add logging.

**Action**: Add detailed logging after slippage check:
```python
async def calculate_order_size_with_slippage(
    self,
    price: Decimal,
    ticker: str,
    direction: str,
    max_slippage_bps: int = 20
) -> Tuple[Decimal, Decimal, bool]:
    """Calculate order size with slippage check using BookDepth data."""
    client = self.eth_client if ticker == "ETH" else self.sol_client
    raw_qty = self.target_notional / price
    tick_size = client.config.tick_size
    target_qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

    # Check BookDepth availability
    bookdepth = client.get_bookdepth_handler()
    if bookdepth:
        self.logger.info(
            f"[SLIPPAGE][{ticker}] BookDepth available, estimating slippage for {direction} {target_qty}"
        )
    else:
        self.logger.warning(
            f"[SLIPPAGE][{ticker}] BookDepth NOT available, using target quantity {target_qty}"
        )
        return target_qty, Decimal(0), True

    # Try to get slippage estimate from BookDepth
    slippage = await client.estimate_slippage(direction, target_qty)

    self.logger.info(
        f"[SLIPPAGE][{ticker}] Estimated slippage: {slippage:.1f} bps for {direction} {target_qty}"
    )

    if slippage >= Decimal(999999):
        self.logger.warning(f"[SLIPPAGE][{ticker}] Insufficient liquidity, using target quantity")
        return target_qty, Decimal(0), True

    # Check if slippage is acceptable
    if slippage <= max_slippage_bps:
        self.logger.info(
            f"[SLIPPAGE][{ticker}] Slippage acceptable: {slippage:.1f} bps <= {max_slippage_bps} bps"
        )
        return target_qty, slippage, True
    else:
        self.logger.warning(
            f"[SLIPPAGE][{ticker}] Slippage too high: {slippage:.1f} bps > {max_slippage_bps} bps"
        )
        # Find max quantity within limit
        can_exit, exitable_qty = await client.check_exit_capacity(
            target_qty if direction == "sell" else -target_qty,
            max_slippage_bps
        )
        if not can_exit:
            self.logger.warning(
                f"[SLIPPAGE][{ticker}] Reducing quantity from {target_qty} to {exitable_qty}"
            )
            return exitable_qty, slippage, False

        return target_qty, slippage, True
```

**Acceptance Criteria**:
- [ ] Logs BookDepth availability
- [ ] Logs estimated slippage in bps
- [ ] Logs whether slippage is acceptable
- [ ] Logs quantity reductions when slippage too high
- [ ] All existing functionality preserved

---

### Phase 5: Testing & Validation

#### Task 5.1: Test WebSocket Handler Registration
**File**: Test script (new)

**Action**: Create test script `test_dn_pair_websocket.py`
```python
#!/usr/bin/env python3
"""Test WebSocket handler registration for DN_pair_bot."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from hedge.DN_pair_eth_sol_nado import DNPairBot

async def test_websocket_setup():
    """Test WebSocket handler initialization."""
    load_dotenv()

    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
    )

    await bot.initialize_clients()

    # Check if WebSocket handlers are active
    assert bot._ws_handlers_active, "WebSocket handlers should be active"

    # Check if handlers are registered
    assert bot.eth_fill_handler is not None, "ETH fill handler should be registered"
    assert bot.eth_position_handler is not None, "ETH position handler should be registered"
    assert bot.sol_fill_handler is not None, "SOL fill handler should be registered"
    assert bot.sol_position_handler is not None, "SOL position handler should be registered"

    # Check WebSocket client status
    assert bot.eth_client._ws_connected, "ETH WebSocket should be connected"
    assert bot.sol_client._ws_connected, "SOL WebSocket should be connected"

    # Check BookDepth handlers
    eth_bookdepth = bot.eth_client.get_bookdepth_handler()
    sol_bookdepth = bot.sol_client.get_bookdepth_handler()

    assert eth_bookdepth is not None, "ETH BookDepth handler should be available"
    assert sol_bookdepth is not None, "SOL BookDepth handler should be available"

    print("✓ All WebSocket handlers registered successfully")
    print("✓ BookDepth handlers available")

    await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(test_websocket_setup())
```

**Acceptance Criteria**:
- [ ] Test script runs without errors
- [ ] All assertions pass
- [ ] WebSocket handlers verified active
- [ ] BookDepth handlers verified available
- [ ] Cleanup completes successfully

---

#### Task 5.2: Test Position Reconciliation
**File**: Test script (new)

**Action**: Create test script `test_dn_pair_reconciliation.py`
```python
#!/usr/bin/env python3
"""Test position reconciliation for DN_pair_bot."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from hedge.DN_pair_eth_sol_nado import DNPairBot

async def test_position_reconciliation():
    """Test position reconciliation logic."""
    load_dotenv()

    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
    )

    await bot.initialize_clients()

    # Test reconciliation
    matches, details = await bot.reconcile_positions()

    print(f"Reconciliation result: {matches}")
    print(f"Details: {details}")

    # Positions should match initially (both zero)
    assert matches, f"Positions should match initially: {details}"

    # Get positions from both sources
    eth_rest = await bot.eth_client.get_account_positions()
    sol_rest = await bot.sol_client.get_account_positions()

    print(f"REST positions: ETH={eth_rest}, SOL={sol_rest}")
    print(f"WS positions: ETH={bot.local_eth_position}, SOL={bot.local_sol_position}")

    await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(test_position_reconciliation())
```

**Acceptance Criteria**:
- [ ] Test script runs without errors
- [ ] Reconciliation succeeds initially (zero positions)
- [ ] REST and WebSocket positions match
- [ ] Details logged correctly

---

#### Task 5.3: Integration Test - 20 Iterations
**File**: Test script (new)

**Action**: Create integration test `test_dn_pair_integration.py`
```python
#!/usr/bin/env python3
"""Integration test for DN_pair_bot with WebSocket monitoring."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from hedge.DN_pair_eth_sol_nado import DNPairBot

async def test_20_iterations():
    """Run 20 iterations and verify no SOL accumulation."""
    load_dotenv()

    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=20,
        sleep_time=1,
    )

    await bot.initialize_clients()

    # Record initial positions
    eth_initial = await bot.eth_client.get_account_positions()
    sol_initial = await bot.sol_client.get_account_positions()

    print(f"Initial positions: ETH={eth_initial}, SOL={sol_initial}")

    # Run alternating strategy
    results = await bot.run_alternating_strategy()

    # Record final positions
    eth_final = await bot.eth_client.get_account_positions()
    sol_final = await bot.sol_client.get_account_positions()

    print(f"Final positions: ETH={eth_final}, SOL={sol_final}")

    # Check for accumulation
    eth_diff = abs(eth_final - eth_initial)
    sol_diff = abs(sol_final - sol_initial)

    print(f"Position drift: ETH={eth_diff}, SOL={sol_diff}")

    # Verify minimal accumulation (< 0.1 tolerance)
    assert eth_diff < Decimal("0.1"), f"ETH accumulated too much: {eth_diff}"
    assert sol_diff < Decimal("0.1"), f"SOL accumulated too much: {sol_diff}"

    # Check success rate
    success_count = sum(1 for r in results if r)
    success_rate = success_count / len(results)

    print(f"Success rate: {success_count}/{len(results)} ({success_rate*100:.1f}%)")

    await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(test_20_iterations())
```

**Acceptance Criteria**:
- [ ] Test runs 20 iterations without crashing
- [ ] Final positions within 0.1 of initial positions
- [ ] Success rate > 80%
- [ ] No SOL accumulation (> 0.1 net drift)
- [ ] WebSocket events logged throughout run

---

#### Task 5.4: Test REST Fallback
**File**: Test script (new)

**Action**: Create test for graceful degradation
```python
#!/usr/bin/env python3
"""Test REST fallback when WebSocket unavailable."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from hedge.DN_pair_eth_sol_nado import DNPairBot

async def test_rest_fallback():
    """Test that bot works with REST-only mode."""
    load_dotenv()

    # Mock WebSocket handlers as unavailable
    with patch('hedge.DN_pair_eth_sol_nado.WEBSOCKET_HANDLERS_AVAILABLE', False):
        bot = DNPairBot(
            target_notional=Decimal("100"),
            iterations=1,
        )

        await bot.initialize_clients()

        # Verify WebSocket handlers NOT active
        assert not bot._ws_handlers_active, "WebSocket handlers should be inactive"

        # Verify REST still works
        eth_bid, eth_ask = await bot.eth_client.fetch_bbo_prices("4")
        sol_bid, sol_ask = await bot.sol_client.fetch_bbo_prices("8")

        assert eth_bid > 0, "ETH bid should be valid"
        assert eth_ask > 0, "ETH ask should be valid"
        assert sol_bid > 0, "SOL bid should be valid"
        assert sol_ask > 0, "SOL ask should be valid"

        print("✓ REST fallback working correctly")

        await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(test_rest_fallback())
```

**Acceptance Criteria**:
- [ ] Test runs with WebSocket handlers disabled
- [ ] Bot initializes successfully
- [ ] REST API calls work (BBO prices valid)
- [ ] No crashes or errors
- [ ] Graceful degradation confirmed

---

## File Modifications Summary

### Files to Modify
1. `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
   - Add WebSocket handler imports
   - Add handler initialization in `__init__`
   - Add `_setup_websocket_handlers()` method
   - Add fill callback methods (`_on_eth_fill`, `_on_sol_fill`)
   - Add position callback methods (`_on_eth_position_change`, `_on_sol_position_change`)
   - Modify `initialize_clients()` to setup handlers
   - Add `reconcile_positions()` method
   - Modify `execute_unwind_cycle()` to use WebSocket data
   - Add BookDepth diagnostic logging
   - Enhance slippage logging in `calculate_order_size_with_slippage()`

### Files to Create
1. `/Users/botfarmer/2dex/tests/test_dn_pair_websocket.py` - WebSocket registration test
2. `/Users/botfarmer/2dex/tests/test_dn_pair_reconciliation.py` - Position reconciliation test
3. `/Users/botfarmer/2dex/tests/test_dn_pair_integration.py` - 20 iteration integration test
4. `/Users/botfarmer/2dex/tests/test_dn_pair_rest_fallback.py` - REST fallback test

### Files to Reference (NOT MODIFY)
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py` - Already has WebSocket integrated
- `/Users/botfarmer/2dex/hedge/exchanges/nado_websocket_client.py` - Use as-is
- `/Users/botfarmer/2dex/hedge/exchanges/nado_bbo_handler.py` - Use as-is
- `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py` - Use as-is
- `/Users/botfarmer/2dex/hedge/exchanges/nado_fill_handler.py` - Use as-is
- `/Users/botfarmer/2dex/hedge/exchanges/nado_position_handler.py` - Use as-is

---

## Testing Strategy

### Unit Testing
- Test WebSocket handler registration
- Test position reconciliation logic
- Test fill callback handlers
- Test position change callbacks

### Integration Testing
- Test full BUILD/UNWIND cycle with WebSocket monitoring
- Test 20 iterations with position verification
- Test slippage estimation using BookDepth

### Regression Testing
- Test REST fallback when WebSocket unavailable
- Test with existing test suite (ensure no breaks)
- Test backward compatibility

### Manual Testing
1. Start bot with WebSocket logging enabled
2. Monitor logs for WebSocket connection events
3. Verify fill events logged in real-time
4. Verify position changes logged in real-time
5. Check for SOL accumulation after 20 iterations

---

## Rollback Plan

### If WebSocket Integration Fails

**Option 1: Disable WebSocket Handlers**
- Set `WEBSOCKET_HANDLERS_AVAILABLE = False` in imports
- Bot will use REST-only mode (existing behavior)
- No code changes required

**Option 2: Git Revert**
```bash
git revert <commit-hash>
# Or reset to working commit
git reset --hard <working-commit-hash>
```

**Option 3: Feature Flag**
- Add environment variable `USE_WEBSOCKET=false`
- Wrap WebSocket setup in conditional check
- Easy toggle without code changes

### Rollback Criteria
- SOL accumulation > 0.5 after 20 iterations
- WebSocket crashes the bot
- Success rate drops below 70%
- Position reconciliation fails consistently

---

## Success Metrics

### Primary Metrics
- **SOL Accumulation**: Net SOL position change < 0.1 after 20 iterations
- **UNWIND Success Rate**: > 90% of UNWIND cycles close positions to < 0.001
- **WebSocket Uptime**: > 95% connection stability during runs

### Secondary Metrics
- **Fill Detection Latency**: < 100ms for WebSocket fill events
- **Position Update Latency**: < 200ms for position changes
- **Slippage Accuracy**: Estimated vs actual slippage within 5 bps

---

## Risk Assessment

### High Risk
- **WebSocket Authentication Failure**: EIP-712 signing may fail
  - **Mitigation**: Existing NadoClient already handles this
  - **Fallback**: REST-only mode

### Medium Risk
- **Position Tracking Drift**: WebSocket positions may diverge from REST
  - **Mitigation**: Reconciliation logic in Task 3.1
  - **Fallback**: REST verification in UNWIND cycle

### Low Risk
- **BookDepth Unavailable**: Slippage estimation falls back to simple sizing
  - **Mitigation**: Graceful degradation in Task 4.1
  - **Fallback**: Target quantity without slippage check

---

## Implementation Notes

### Key Insights
1. **NadoClient already has WebSocket**: Commit 5bc077d integrated WebSocket into NadoClient
2. **Just add handlers**: Need to register FillHandler and PositionHandler callbacks
3. **Preserve REST fallback**: All WebSocket features have REST fallbacks
4. **Position verification is key**: UNWIND already has verification, just enhance with WS data

### Product IDs
- ETH: 4
- SOL: 8

### WebSocket Streams
- Public: `best_bid_offer`, `book_depth`
- Private: `fill`, `position_change` (require EIP-712 authentication)

### Dependencies
- `websockets` library (already in NadoClient)
- `eth-account` library (already in NadoClient)
- `sortedcontainers` for BookDepth (already required)

---

## Post-Implementation Checklist

- [ ] All tests pass (unit, integration, regression)
- [ ] 20 iterations run without SOL accumulation
- [ ] WebSocket connection stable throughout run
- [ ] Fill events logged in real-time
- [ ] Position changes logged in real-time
- [ ] REST fallback verified working
- [ ] Code reviewed and committed
- [ ] Documentation updated
- [ ] Log files reviewed for errors

---

## References

- **Git Commit 5bc077d**: WebSocket BBO integration into NadoClient
- **Git Commit 23d89e2**: WebSocket public stream client implementation
- **Nado SDK Documentation**: https://docs.nado.xyz (hypothetical)
- **EIP-712 Specification**: https://eips.ethereum.org/EIPS/eip-712

---

**End of Plan**

**Next Steps**:
1. Review and approve this plan
2. Run `/oh-my-claudecode:start-work dn-pair-websocket-integration` to begin implementation
3. Monitor progress and validate success criteria
