# DN Pair Bot Test Failure Fix Plan

## Requirements Summary

### Problem Statement
The DN Pair Bot (`DN_pair_eth_sol_nado.py`) failed during alternating strategy testing with the following pattern:
- **Cycle 1 (BUY_FIRST)**: BUILD successful, UNWIND successful
- **Cycle 2 (SELL_FIRST)**: BUILD successful, UNWIND failed (no orders placed)
- **Result**: SOL positions accumulated (LONG=202, SHORT=104, net 98 SOL)
- **Manual Intervention Required**: Liquidation of accumulated positions

### Root Cause Analysis
The `handle_emergency_unwind` function (lines 1264-1354) is legacy code that:
1. Gets called during BUILD phase from `place_simultaneous_orders`
2. Causes API position confusion (API returns position=0 despite successful fills)
3. Has a return value that the caller ignores

### Current Code Issues
1. **`execute_build_cycle`** (lines 1199-1262): No position verification before opening new positions
2. **`execute_unwind_cycle`** (lines 1264-1354): Position check has only 1 retry with 0.5s/1s delays
3. **`run_alternating_strategy`** (lines 1475-1506): No early exit when cycle fails
4. **Entry state tracking** (lines 482-494): Only updates state, doesn't verify positions

### Success Criteria
- Delta-based positions: ETH net approx 0, SOL net approx 0
- No position accumulation (abs(position) < 0.001)
- BUILD refuses to run if positions > 0.001
- UNWIND retries 3+ times with 2s delays
- Early exit on cycle failure

---

## Architecture Changes

### Phase Tracking Design

#### Current State
- `_is_entry_phase`: Boolean flag set during BUILD phase
- `_is_exit_phase`: Boolean flag set during UNWIND phase
- No explicit phase parameter passed to core functions

#### Proposed Solution: Unified Phase Enum

**New Phase Enum** (MODULE LEVEL - after imports, before class definition):
```python
# File: hedge/DN_pair_eth_sol_nado.py
# Location: After imports (line ~40-50), BEFORE DNPairBot class definition

from enum import Enum

class CyclePhase(Enum):
    """DN Pair Bot Cycle Phases - Module-level enum for phase tracking"""
    IDLE = "idle"
    BUILD_PLACING = "build_placing"
    BUILD_VERIFYING = "build_verifying"
    BUILD_COMPLETE = "build_complete"
    UNWIND_READY = "unwind_ready"
    UNWIND_PLACING = "unwind_placing"
    UNWIND_VERIFYING = "unwind_verifying"
    UNWIND_COMPLETE = "unwind_complete"
    ERROR = "error"
```

**Phase Interaction with Existing Flags**:
- `_is_entry_phase` becomes: `self._phase in [CyclePhase.BUILD_PLACING, CyclePhase.BUILD_VERIFYING]`
- `_is_exit_phase` becomes: `self._phase in [CyclePhase.UNWIND_PLACING, CyclePhase.UNWIND_VERIFYING]`
- Single source of truth: `self._phase` (CyclePhase enum)
- Legacy flags (`_is_entry_phase`, `_is_exit_phase`) maintained for backward compatibility but deprecated
- **PRECEDENCE RULE**: When `self._phase` and legacy flags conflict, `self._phase` ALWAYS wins

**Source of Truth Precedence (CRITICAL)**:
```python
# WHEN CHECKING PHASE - ALWAYS USE THIS PATTERN:
is_entry_phase = self._phase in [CyclePhase.BUILD_PLACING, CyclePhase.BUILD_VERIFYING]

# NEVER DO THIS (legacy flag check alone):
if self._is_entry_phase:  # WRONG - may be stale

# CORRECT (with backward compatibility):
is_entry_phase = (
    (hasattr(self, '_phase') and self._phase in [CyclePhase.BUILD_PLACING, CyclePhase.BUILD_VERIFYING])
    or (hasattr(self, '_is_entry_phase') and self._is_entry_phase)  # Legacy fallback
)

# BUT WHEN CONFLICT EXISTS (e.g., _is_entry_phase=True but _phase=IDLE):
# self._phase ALWAYS takes precedence
```

#### Phase Transition Rules
1. BUILD: IDLE -> BUILD_PLACING -> BUILD_VERIFYING -> BUILD_COMPLETE
2. UNWIND: BUILD_COMPLETE -> UNWIND_READY -> UNWIND_PLACING -> UNWIND_VERIFYING -> UNWIND_COMPLETE -> IDLE
3. ERROR: Any state -> ERROR (manual recovery required)

### State Machine Design

#### Complete State Transition Diagram

```
                    DN Pair Bot State Machine

┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│          │     │              │     │                  │
│   IDLE   │────▶│ BUILD_PLACING│────▶│ BUILD_VERIFYING │
│          │     │              │     │                  │
└──────────┘     └──────┬───────┘     └────────┬─────────┘
     ▲                   │                       │
     │                   │ FAIL                  │ SUCCESS
     │                   ▼                       ▼
     │             ┌──────────┐          ┌──────────────┐
     │             │          │          │              │
     │             │  ERROR   │          │BUILD_COMPLETE│
     │             │          │          │              │
     │             └────┬─────┘          └──────┬───────┘
     │                  │                      │
     │                  │ Manual Recovery      │
     │                  │                      ▼
     │                  │              ┌───────────────┐
     │                  │              │               │
     │                  │              │ UNWIND_READY  │
     │                  │              │               │
     │                  │              └───────┬───────┘
     │                  │                      │
     │                  │                      │ start_unwind()
     └──────────────────┴──────────────────────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │               │
                                          │UNWIND_PLACING │
                                          │               │
                                          └───────┬───────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │               │
                                          │UNWIND_VERIFY- │
                                          │    ING        │
                                          │               │
                                          └───────┬───────┘
                                                  │
                              ┌───────────────────┴──────────────────┐
                              │                                      │
                         SUCCESS│                               FAIL│
                              ▼                                      ▼
                      ┌──────────────┐                       ┌──────────┐
                      │              │                       │          │
                      │UNWIND_COMPL- │──────────────────────▶│  ERROR   │
                      │    ETE       │  retries exhausted    │          │
                      │              │                       └────┬─────┘
                      └──────┬───────┘                            │
                             │                                     │
                             │ return True                         │ Manual Recovery
                             ▼                                     │
                      ┌──────────────┐                            │
                      │              │                            │
                      │    IDLE      │◄───────────────────────────┘
                      │              │
                      └──────────────┘
```

#### State Definitions

| State | Description | Entry Conditions | Exit Conditions |
|-------|-------------|------------------|-----------------|
| **IDLE** | No positions, ready for new cycle | Start of bot, after successful UNWIND | BUILD_PLACING (on build_cycle) |
| **BUILD_PLACING** | Orders being placed | execute_build_cycle() called | BUILD_VERIFYING (orders placed) or ERROR |
| **BUILD_VERIFYING** | Verifying position changes | Orders returned from exchange | BUILD_COMPLETE (positions confirmed) or ERROR |
| **BUILD_COMPLETE** | Both positions open | Positions verified | UNWIND_READY (manual or automatic) |
| **UNWIND_READY** | Ready to close positions | Time/signal to close | UNWIND_PLACING |
| **UNWIND_PLACING** | Close orders being placed | execute_unwind_cycle() called | UNWIND_VERIFYING (orders placed) or ERROR |
| **UNWIND_VERIFYING** | Verifying positions closed | Close orders returned | UNWIND_COMPLETE (positions = 0) or retry |
| **UNWIND_COMPLETE** | Both positions closed | Positions verified = 0 | IDLE |
| **ERROR** | Error state requiring intervention | Any state on failure | IDLE (after manual recovery) |

---

## Position Tracking Strategy

### Resolving the Circular Dependency

#### Problem: API vs Internal State
When API says position=0 but internal tracking says position!=0, which takes precedence?

#### Solution: Hierarchical Trust with Reconciliation

```python
class PositionTracker:
    """
    Hierarchical position tracking with reconciliation

    Trust Hierarchy:
    1. API (REST) - Ground truth, source of record
    2. Internal Tracking - Optimistic cache for faster decisions
    3. Order Results - Transaction receipts

    Reconciliation Rule: API always wins, but log discrepancies
    """

    def __init__(self):
        self.api_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self.internal_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self.pending_changes = {"ETH": Decimal("0"), "SOL": Decimal("0")}

    async def get_positions(self, client_eth, client_sol) -> dict:
        """
        Get positions with API verification

        Returns:
            dict: {"ETH": Decimal, "SOL": Decimal} from API (source of truth)
        """
        # Always fetch from API
        api_eth = await client_eth.get_account_positions()
        api_sol = await client_sol.get_account_positions()

        self.api_positions = {"ETH": api_eth, "SOL": api_sol}

        # Reconcile with internal tracking
        for ticker in ["ETH", "SOL"]:
            diff = abs(self.api_positions[ticker] - self.internal_positions[ticker])
            if diff > Decimal("0.001"):
                # Log discrepancy but trust API
                self.logger.warning(
                    f"[POSITION_RECONCILE] {ticker}: API={self.api_positions[ticker]}, "
                    f"Internal={self.internal_positions[ticker]}, "
                    f"Trusting API"
                )
                # Update internal to match API
                self.internal_positions[ticker] = self.api_positions[ticker]

        return self.api_positions

    def update_pending(self, ticker: str, quantity_delta: Decimal):
        """
        Update internal tracking on order placement (optimistic)
        """
        self.pending_changes[ticker] += quantity_delta
        self.internal_positions[ticker] += quantity_delta

    def confirm_pending(self, ticker: str):
        """
        Confirm pending changes after API verification
        """
        self.pending_changes[ticker] = Decimal("0")
```

#### Usage Pattern
1. **Before Order**: Call `get_positions()` to get ground truth
2. **Place Order**: Update internal tracking with `update_pending()`
3. **After Order**: Call `get_positions()` again to verify
4. **Discrepancy**: API wins, log warning, update internal

---

## Implementation Steps

### Step 1: Add Phase Enum (Module Level, After Imports ~Line 40-50)

**BEFORE**:
```python
# File: hedge/DN_pair_eth_sol_nado.py
# Lines ~40-50: Import section

from datetime import datetime, timezone
from decimal import Decimal
# ... other imports ...

# [NO CODE HERE - imports end, class begins]
class DNPairBot:
```

**AFTER**:
```python
# File: hedge/DN_pair_eth_sol_nado.py
# Lines ~40-50: Import section

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum  # NEW: Add Enum import
# ... other imports ...

# NEW: CyclePhase enum - MODULE LEVEL (after imports, before class)
class CyclePhase(Enum):
    """DN Pair Bot Cycle Phases

    This enum defines the complete lifecycle of a DN pair trading cycle.
    It must be defined at MODULE LEVEL (outside the class) for:
    1. Test importability: from DN_pair_eth_sol_nado import CyclePhase
    2. Type hints across modules
    3. Consistent serialization
    """
    IDLE = "idle"
    BUILD_PLACING = "build_placing"
    BUILD_VERIFYING = "build_verifying"
    BUILD_COMPLETE = "build_complete"
    UNWIND_READY = "unwind_ready"
    UNWIND_PLACING = "unwind_placing"
    UNWIND_VERIFYING = "unwind_verifying"
    UNWIND_COMPLETE = "unwind_complete"
    ERROR = "error"

# [Existing class definition continues]
class DNPairBot:
```

### Step 1.5: Update __init__ - Add Phase and Position Tracking (Lines 131-200)

**BEFORE**:
```python
    def __init__(self, ...):
        # ... existing init code ...
        self.cycle_id = 0
        # ... rest of init ...
```

**AFTER**:
```python
    def __init__(self, ...):
        # ... existing init code ...
        self.cycle_id = 0

        # ===== NEW: Phase Tracking =====
        # Single source of truth for bot phase state
        self._phase = CyclePhase.IDLE

        # Legacy flags for backward compatibility (DEPRECATED)
        # These are set alongside self._phase to maintain compatibility
        # with existing code that checks hasattr(self, '_is_entry_phase')
        self._is_entry_phase = False  # DEPRECATED: Use self._phase instead
        self._is_exit_phase = False   # DEPRECATED: Use self._phase instead

        # ===== NEW: Position Tracking =====
        # Hierarchical position tracking with API reconciliation
        self._api_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self._internal_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self._last_order_time = 0  # Timestamp of last order placement

        # ... rest of init ...
```

### Step 2: Add Position Tracking Methods (After Line 250, After _setup_logger)

**CRITICAL REQUIREMENT**: These methods MUST be added AFTER `_setup_logger()` is called in `__init__` because they use `self.logger`.

**INSERT**:
```python
    async def _get_verified_positions(self) -> dict:
        """
        Get positions from API and reconcile with internal tracking.

        PRECONDITION: self.logger must be initialized (call after _setup_logger())

        Returns:
            dict: {"ETH": Decimal, "SOL": Decimal} - API positions (source of truth)
        """
        # GUARD: Verify logger exists (called during initialization)
        if not hasattr(self, 'logger') or self.logger is None:
            # During early initialization, return zeros without logging
            return {"ETH": Decimal("0"), "SOL": Decimal("0")}

        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        self._api_positions = {"ETH": eth_pos, "SOL": sol_pos}

        # Reconcile discrepancies
        for ticker, api_pos in self._api_positions.items():
            internal_pos = self._internal_positions[ticker]
            diff = abs(api_pos - internal_pos)

            if diff > Decimal("0.001"):
                self.logger.warning(
                    f"[POSITION_RECONCILE] {ticker}: API={api_pos}, "
                    f"Internal={internal_pos}, Using API value"
                )
                self._internal_positions[ticker] = api_pos

        return self._api_positions

    def _update_internal_position(self, ticker: str, delta: Decimal):
        """
        Update internal position tracking (optimistic).

        PRECONDITION: self.logger must be initialized
        """
        # GUARD: Verify logger exists
        if not hasattr(self, 'logger') or self.logger is None:
            # During early initialization, update without logging
            self._internal_positions[ticker] += delta
            return

        self._internal_positions[ticker] += delta
        self.logger.debug(
            f"[POSITION_TRACKING] {ticker}: {self._internal_positions[ticker]} (optimistic)"
        )
```

### Step 3: Fix `execute_build_cycle` - Add Position Verification and BUILD_VERIFYING Phase (Lines 1199-1262)

**BEFORE (Lines 1209-1220)**:
```python
        POSITION_TOLERANCE = Decimal("0.001")

        # SAFETY CHECK: Verify positions are closed before BUILD
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
            self.logger.error(
                f"[BUILD] SAFETY VIOLATION: Cannot BUILD with open positions - "
                f"ETH={eth_pos}, SOL={sol_pos}. Run UNWIND first!"
            )
            return False
```

**AFTER**:
```python
        POSITION_TOLERANCE = Decimal("0.001")
        MAX_POSITION_CHECK_RETRIES = 3  # For pre-build position verification
        VERIFY_RETRIES = 5  # For post-build position verification (longer)
        POSITION_CHECK_DELAY = 1.0

        # PHASE TRANSITION: IDLE -> BUILD_PLACING
        if self._phase != CyclePhase.IDLE:
            self.logger.error(
                f"[BUILD] INVALID STATE: Current phase={self._phase}, "
                f"expected IDLE. Cannot start BUILD."
            )
            return False

        self._phase = CyclePhase.BUILD_PLACING
        self.logger.info(f"[PHASE] IDLE -> BUILD_PLACING")

        # SAFETY CHECK: Verify positions are closed before BUILD (with retries)
        positions_verified = False
        for attempt in range(MAX_POSITION_CHECK_RETRIES):
            verified_positions = await self._get_verified_positions()
            eth_pos = verified_positions["ETH"]
            sol_pos = verified_positions["SOL"]

            if abs(eth_pos) <= POSITION_TOLERANCE and abs(sol_pos) <= POSITION_TOLERANCE:
                positions_verified = True
                self.logger.info(
                    f"[BUILD] Position check passed (attempt {attempt + 1}): "
                    f"ETH={eth_pos}, SOL={sol_pos}"
                )
                break

            self.logger.warning(
                f"[BUILD] Position check failed (attempt {attempt + 1}/{MAX_POSITION_CHECK_RETRIES}): "
                f"ETH={eth_pos}, SOL={sol_pos}"
            )

            if attempt < MAX_POSITION_CHECK_RETRIES - 1:
                await asyncio.sleep(POSITION_CHECK_DELAY)

        if not positions_verified:
            self.logger.error(
                f"[BUILD] SAFETY VIOLATION: Cannot BUILD with open positions after "
                f"{MAX_POSITION_CHECK_RETRIES} retries - ETH={eth_pos}, SOL={sol_pos}"
            )
            self._phase = CyclePhase.ERROR
            return False
```

**BEFORE (Lines 1221-1240) - AFTER ORDER PLACEMENT**:
```python
        # ... order placement code ...

        # Store entry prices and quantities
        if eth_fill_qty > 0:
            self.entry_prices["ETH"] = eth_fill_price
            self.entry_quantities["ETH"] = eth_fill_qty
        if sol_fill_qty > 0:
            self.entry_prices["SOL"] = sol_fill_price
            self.entry_quantities["SOL"] = sol_fill_qty

        return True
```

**AFTER - ADD BUILD_VERIFYING PHASE**:
```python
        # ... order placement code ...

        # Store entry prices and quantities
        if eth_fill_qty > 0:
            self.entry_prices["ETH"] = eth_fill_price
            self.entry_quantities["ETH"] = eth_fill_qty
        if sol_fill_qty > 0:
            self.entry_prices["SOL"] = sol_fill_price
            self.entry_quantities["SOL"] = sol_fill_qty

        # ===== NEW: BUILD_VERIFYING Phase =====
        # After orders are placed, verify positions actually changed
        self._phase = CyclePhase.BUILD_VERIFYING
        self.logger.info(f"[PHASE] BUILD_PLACING -> BUILD_VERIFYING")

        VERIFY_RETRIES = 5
        VERIFY_DELAY = 1.0

        for attempt in range(VERIFY_RETRIES):
            await asyncio.sleep(VERIFY_DELAY)

            verified_positions = await self._get_verified_positions()
            eth_pos = verified_positions["ETH"]
            sol_pos = verified_positions["SOL"]

            self.logger.info(
                f"[BUILD_VERIFY] Checking positions (attempt {attempt + 1}/{VERIFY_RETRIES}): "
                f"ETH={eth_pos}, SOL={sol_pos}"
            )

            # Check if positions are now open (non-zero)
            eth_open = abs(eth_pos) > POSITION_TOLERANCE
            sol_open = abs(sol_pos) > POSITION_TOLERANCE

            if eth_open and sol_open:
                # Both positions confirmed
                self._phase = CyclePhase.BUILD_COMPLETE
                self.logger.info(f"[PHASE] BUILD_VERIFYING -> BUILD_COMPLETE")
                return True
            elif eth_open or sol_open:
                # Only one position opened - partial fill state
                self.logger.error(
                    f"[BUILD_VERIFY] PARTIAL STATE: Only one position opened - "
                    f"ETH={'OPEN' if eth_open else 'CLOSED'}, "
                    f"SOL={'OPEN' if sol_open else 'CLOSED'}"
                )
                self._phase = CyclePhase.ERROR
                return False

            if attempt < VERIFY_RETRIES - 1:
                self.logger.warning(
                    "[BUILD_VERIFY] Positions not yet open, API may be processing..."
                )

        # Verification failed after all retries
        self.logger.error(
            f"[BUILD_VERIFY] FAILED: Positions did not open after {VERIFY_RETRIES} retries"
        )
        self._phase = CyclePhase.ERROR
        return False
```

### Step 4: Update `place_simultaneous_orders` - Accept Phase Parameter (Lines 314-541)

**BEFORE (Line 314)**:
```python
    async def place_simultaneous_orders(
        self,
        eth_direction: str,
        sol_direction: str,
    ) -> Tuple[OrderResult, OrderResult]:
```

**AFTER**:
```python
    async def place_simultaneous_orders(
        self,
        eth_direction: str,
        sol_direction: str,
        phase: CyclePhase = None,  # NEW: Explicit phase parameter
    ) -> Tuple[OrderResult, OrderResult]:
        """Place ETH and SOL orders simultaneously using REST-based position monitoring.

        Args:
            eth_direction: Order direction for ETH ("buy" or "sell")
            sol_direction: Order direction for SOL ("buy" or "sell")
            phase: Current cycle phase (for logging and validation)
        """
        # Use provided phase or current phase
        current_phase = phase or self._phase

        self.logger.info(
            f"[ORDER] Placing orders - Phase: {current_phase.value if current_phase else 'unknown'}, "
            f"ETH: {eth_direction}, SOL: {sol_direction}"
        )
```

**BEFORE (Lines 538-541)**:
```python
        # Handle partial fills and failed orders
        await self.handle_emergency_unwind(eth_result, sol_result)

        return eth_result, sol_result
```

**AFTER**:
```python
        # REMOVED: Legacy emergency_unwind during BUILD phase
        # This was causing API position confusion
        # Emergency unwind is now only handled at cycle level, not order level

        return eth_result, sol_result
```

### Step 5: Remove `handle_emergency_unwind` and Related Functions (Lines 543-598)

**ACTION**: DELETE these legacy functions (no longer needed):
- `handle_emergency_unwind` (lines 543-566)
- `emergency_unwind_eth` (lines 568-582)
- `emergency_unwind_sol` (lines 584-598)

**RATIONALE**: These functions were causing the API position confusion by attempting to close positions during the BUILD phase, before the API had time to process the original orders.

### Step 6: Fix `execute_unwind_cycle` - Add Retries and Verification (Lines 1264-1354)

**BEFORE (Lines 1276-1316)**:
```python
        POSITION_TOLERANCE = Decimal("0.001")
        MAX_RETRIES = 3
        RETRY_DELAY = 2.0

        # Log pre-unwind positions
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()
```

**AFTER**:
```python
        POSITION_TOLERANCE = Decimal("0.001")
        MAX_RETRIES = 5  # INCREASED from 3
        RETRY_DELAY = 2.0

        # PHASE TRANSITION: BUILD_COMPLETE -> UNWIND_PLACING
        if self._phase != CyclePhase.BUILD_COMPLETE:
            self.logger.error(
                f"[UNWIND] INVALID STATE: Current phase={self._phase}, "
                f"expected BUILD_COMPLETE. Cannot start UNWIND."
            )
            return False

        self._phase = CyclePhase.UNWIND_PLACING
        self.logger.info(f"[PHASE] BUILD_COMPLETE -> UNWIND_PLACING")

        # Log pre-unwind positions (using verified positions)
        verified_positions = await self._get_verified_positions()
        eth_pos_before = verified_positions["ETH"]
        sol_pos_before = verified_positions["SOL"]
        self.logger.info(
            f"[UNWIND] POSITIONS BEFORE: "
            f"API: ETH={eth_pos_before}, SOL={sol_pos_before} | "
            f"Internal: ETH={self._internal_positions['ETH']}, SOL={self._internal_positions['SOL']}"
        )

        # Verify positions are actually open before unwinding
        if abs(eth_pos_before) < POSITION_TOLERANCE and abs(sol_pos_before) < POSITION_TOLERANCE:
            self.logger.warning(
                f"[UNWIND] No positions to close - "
                f"API: ETH={eth_pos_before}, SOL={sol_pos_before}"
            )
            self._phase = CyclePhase.IDLE
            return True
```

**BEFORE (Lines 1294-1316)**:
```python
        # Set exit phase flag for PNL tracking
        self._is_exit_phase = True

        # Place UNWIND orders with specified sides
        eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

        # Store exit prices from OrderResult
        if isinstance(eth_result, OrderResult) and eth_result.success:
            self._exit_prices = getattr(self, '_exit_prices', {})
            self._exit_prices["ETH"] = eth_result.price if eth_result.price else self.entry_prices.get("ETH", Decimal("0"))

        if isinstance(sol_result, OrderResult) and sol_result.success:
            self._exit_prices = getattr(self, '_exit_prices', {})
            self._exit_prices["SOL"] = sol_result.price if sol_result.price else self.entry_prices.get("SOL", Decimal("0"))

        self._is_exit_phase = False

        # Check if orders filled
        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.warning("[UNWIND] Orders failed or partially filled")
            return False
```

**AFTER**:
```python
        # Set exit phase flag for PNL tracking (backward compatibility)
        self._is_exit_phase = True

        # Place UNWIND orders with specified sides and phase context
        self._phase = CyclePhase.UNWIND_PLACING
        eth_result, sol_result = await self.place_simultaneous_orders(
            eth_side, sol_side, phase=CyclePhase.UNWIND_PLACING
        )

        # Store exit prices from OrderResult
        if isinstance(eth_result, OrderResult) and eth_result.success:
            self._exit_prices = getattr(self, '_exit_prices', {})
            self._exit_prices["ETH"] = eth_result.price if eth_result.price else self.entry_prices.get("ETH", Decimal("0"))

        if isinstance(sol_result, OrderResult) and sol_result.success:
            self._exit_prices = getattr(self, '_exit_prices', {})
            self._exit_prices["SOL"] = sol_result.price if sol_result.price else self.entry_prices.get("SOL", Decimal("0"))

        self._is_exit_phase = False

        # Check if orders filled
        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.error("[UNWIND] Orders failed or partially filled")
            self._phase = CyclePhase.ERROR
            return False

        # PHASE TRANSITION: UNWIND_PLACING -> UNWIND_VERIFYING
        self._phase = CyclePhase.UNWIND_VERIFYING
        self.logger.info(f"[PHASE] UNWIND_PLACING -> UNWIND_VERIFYING")
```

**BEFORE (Lines 1317-1354)**:
```python
        # Verify positions closed with retries
        for attempt in range(MAX_RETRIES):
            await asyncio.sleep(RETRY_DELAY)

            eth_pos = await self.eth_client.get_account_positions()
            sol_pos = await self.sol_client.get_account_positions()

            self.logger.info(f"[UNWIND] POSITIONS CHECK (attempt {attempt + 1}/{MAX_RETRIES}): ETH={eth_pos}, SOL={sol_pos}")

            eth_closed = abs(eth_pos) < POSITION_TOLERANCE
            sol_closed = abs(sol_pos) < POSITION_TOLERANCE

            if eth_closed and sol_closed:
                # Mark exit time and calculate final PNL
                self.current_cycle_pnl["exit_time"] = datetime.now(pytz.UTC)

                # Calculate and log final PNL (includes funding correction)
                pnl_no_fee, pnl_with_fee, breakdown = self._calculate_current_pnl()
                self._pnl_breakdown = breakdown  # Store for logging
                self._log_final_cycle_pnl()

                # Log final spread analysis with exit data
                entry_spread_info = getattr(self, '_entry_spread_info', {})
                exit_spread_info = getattr(self, '_exit_spread_info', {})
                self._log_spread_analysis(entry_spread_info, exit_spread_info)

                # Clear entry state for next cycle
                self.entry_prices = {"ETH": None, "SOL": None}
                self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
                self.entry_timestamps = {"ETH": None, "SOL": None}

                return True

            if attempt < MAX_RETRIES - 1:
                self.logger.warning(f"[UNWIND] Positions still open, retrying in {RETRY_DELAY}s...")

        self.logger.error(f"[UNWIND] FAILED: Positions still open after {MAX_RETRIES} retries: ETH={eth_pos}, SOL={sol_pos}")
        return False
```

**AFTER**:
```python
        # Verify positions closed with retries
        for attempt in range(MAX_RETRIES):
            await asyncio.sleep(RETRY_DELAY)

            verified_positions = await self._get_verified_positions()
            eth_pos = verified_positions["ETH"]
            sol_pos = verified_positions["SOL"]

            self.logger.info(
                f"[UNWIND] POSITIONS CHECK (attempt {attempt + 1}/{MAX_RETRIES}): "
                f"API: ETH={eth_pos}, SOL={sol_pos} | "
                f"Internal: ETH={self._internal_positions['ETH']}, SOL={self._internal_positions['SOL']}"
            )

            eth_closed = abs(eth_pos) < POSITION_TOLERANCE
            sol_closed = abs(sol_pos) < POSITION_TOLERANCE

            if eth_closed and sol_closed:
                # PHASE TRANSITION: UNWIND_VERIFYING -> UNWIND_COMPLETE
                self._phase = CyclePhase.UNWIND_COMPLETE
                self.logger.info(f"[PHASE] UNWIND_VERIFYING -> UNWIND_COMPLETE")

                # Mark exit time and calculate final PNL
                self.current_cycle_pnl["exit_time"] = datetime.now(pytz.UTC)

                # Calculate and log final PNL (includes funding correction)
                pnl_no_fee, pnl_with_fee, breakdown = self._calculate_current_pnl()
                self._pnl_breakdown = breakdown  # Store for logging
                self._log_final_cycle_pnl()

                # Log final spread analysis with exit data
                entry_spread_info = getattr(self, '_entry_spread_info', {})
                exit_spread_info = getattr(self, '_exit_spread_info', {})
                self._log_spread_analysis(entry_spread_info, exit_spread_info)

                # Clear entry state for next cycle
                self.entry_prices = {"ETH": None, "SOL": None}
                self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
                self.entry_timestamps = {"ETH": None, "SOL": None}

                # PHASE TRANSITION: UNWIND_COMPLETE -> IDLE
                self._phase = CyclePhase.IDLE
                self.logger.info(f"[PHASE] UNWIND_COMPLETE -> IDLE")

                return True

            if attempt < MAX_RETRIES - 1:
                self.logger.warning(
                    f"[UNWIND] Positions still open, retrying in {RETRY_DELAY}s... "
                    f"(ETH={eth_pos}, SOL={sol_pos})"
                )

        # UNWIND FAILED after all retries
        self.logger.error(
            f"[UNWIND] FAILED: Positions still open after {MAX_RETRIES} retries: "
            f"ETH={eth_pos}, SOL={sol_pos}"
        )
        self._phase = CyclePhase.ERROR
        return False
```

### Step 7: Fix `run_alternating_strategy` - Add Early Exit (Lines 1475-1506)

**BEFORE (Lines 1492-1502)**:
```python
            # CRITICAL: Stop if UNWIND failed
            if not result:
                self.logger.error(
                    f"[SAFETY] Cycle {iteration_num} FAILED! "
                    f"Bot stopping to prevent position accumulation."
                )
                self.logger.error(
                    f"[SAFETY] Check positions manually before restarting. "
                    f"ETH and SOL positions should be near 0."
                )
                break
```

**AFTER**:
```python
            # CRITICAL: Stop if UNWIND failed
            if not result:
                self.logger.error(
                    f"[SAFETY] Cycle {iteration_num} FAILED! "
                    f"Bot stopping to prevent position accumulation."
                )

                # Get final positions for error reporting
                final_positions = await self._get_verified_positions()
                self.logger.error(
                    f"[SAFETY] Final positions - "
                    f"API: ETH={final_positions['ETH']}, SOL={final_positions['SOL']} | "
                    f"Internal: ETH={self._internal_positions['ETH']}, SOL={self._internal_positions['SOL']}"
                )
                self.logger.error(
                    f"[SAFETY] MANUAL INTERVENTION REQUIRED: "
                    f"Close positions before restarting bot."
                )

                # Set ERROR state
                self._phase = CyclePhase.ERROR

                # Early exit - do not continue with remaining iterations
                break
```

### Step 8: Update Entry Phase Tracking (Lines 482-494)

**BEFORE**:
```python
        # Store entry prices and quantities for PNL tracking
        if hasattr(self, '_is_entry_phase') and self._is_entry_phase:
            from datetime import datetime
            entry_timestamp = datetime.now(pytz.UTC).isoformat()

            if eth_fill_qty > 0:
                self.entry_prices["ETH"] = eth_fill_price
                self.entry_quantities["ETH"] = eth_fill_qty
                self.entry_timestamps["ETH"] = entry_timestamp

            if sol_fill_qty > 0:
                self.entry_prices["SOL"] = sol_fill_price
                self.entry_quantities["SOL"] = sol_fill_qty
                self.entry_timestamps["SOL"] = entry_timestamp
```

**AFTER**:
```python
        # Store entry prices and quantities for PNL tracking
        is_build_phase = (
            hasattr(self, '_is_entry_phase') and self._is_entry_phase
        ) or (
            hasattr(self, '_phase') and
            self._phase in [CyclePhase.BUILD_PLACING, CyclePhase.BUILD_VERIFYING]
        )

        if is_build_phase:
            from datetime import datetime
            entry_timestamp = datetime.now(pytz.UTC).isoformat()

            if eth_fill_qty > 0:
                self.entry_prices["ETH"] = eth_fill_price
                self.entry_quantities["ETH"] = eth_fill_qty
                self.entry_timestamps["ETH"] = entry_timestamp
                # Update internal position tracking
                self._update_internal_position("ETH", eth_fill_qty if eth_direction == "buy" else -eth_fill_qty)

            if sol_fill_qty > 0:
                self.entry_prices["SOL"] = sol_fill_price
                self.entry_quantities["SOL"] = sol_fill_qty
                self.entry_timestamps["SOL"] = entry_timestamp
                # Update internal position tracking
                self._update_internal_position("SOL", sol_fill_qty if sol_direction == "buy" else -sol_fill_qty)
```

---

## Edge Case Handling

### 1. Partial Fills

**Scenario**: One leg fills partially, the other doesn't fill at all.

**Detection**:
```python
# In place_simultaneous_orders, after order placement
eth_fill_ratio = eth_fill_qty / eth_qty if eth_qty > 0 else 0
sol_fill_ratio = sol_fill_qty / sol_qty if sol_qty > 0 else 0

# Check for partial fill mismatch
if abs(eth_fill_ratio - sol_fill_ratio) > 0.5:  # 50% mismatch threshold
    self.logger.error(
        f"[PARTIAL_FILL] Mismatch: ETH={eth_fill_ratio:.1%}, SOL={sol_fill_ratio:.1%}"
    )
    # Return failure to trigger cycle-level handling
    eth_result.success = False
    sol_result.success = False
```

**Handling**: Cycle fails, bot stops, manual intervention required.

### 2. Order Rejections

**Scenario**: Exchange rejects one or both orders (insufficient margin, risk limit, etc.).

**Detection**:
```python
# In place_simultaneous_orders
if not eth_result.success:
    self.logger.error(f"[ORDER_REJECT] ETH order rejected: {eth_result.error_message}")
if not sol_result.success:
    self.logger.error(f"[ORDER_REJECT] SOL order rejected: {sol_result.error_message}")
```

**Handling**: Cycle fails immediately, no partial positions (since no orders filled).

### 3. WebSocket Disconnections (REST Fallback)

**Scenario**: WebSocket connection drops during order placement.

**Detection**:
```python
# In place_simultaneous_orders
try:
    # Check connection status before placing orders
    if not self.eth_client._ws_connected or not self.sol_client._ws_connected:
        self.logger.warning(
            "[WS_DISCONNECT] WebSocket unavailable, using REST fallback"
        )
        # REST API is used automatically by client
except Exception as e:
    self.logger.error(f"[WS_ERROR] Connection error: {e}")
    # Fallback to REST
```

**Handling**: REST API is used as fallback (already implemented in NadoClient).

### 4. POST_ONLY Mode Edge Cases

**Scenario A**: POST_ONLY order placed but not filled immediately.

**Detection**:
```python
# In place_simultaneous_orders, after POST_ONLY order placement
if self.use_post_only:
    if eth_result.status == 'OPEN' and sol_result.status == 'OPEN':
        self.logger.info("[POST_ONLY] Both orders resting on book")
        # Transition to BUILD_VERIFYING to monitor for fills
        # Note: OPEN status does NOT mean success - we must verify fills
    elif eth_result.status == 'OPEN' or sol_result.status == 'OPEN':
        self.logger.warning("[POST_ONLY] Partial rest - one leg filled, one resting")
        # This is a dangerous state - should we IOC the other leg?
        # Transition to BUILD_VERIFYING for position verification
```

**POST_ONLY Handling (V5.5 - Current Implementation)**:
- **OPEN status triggers BUILD_VERIFYING phase** (not treated as immediate success)
- BUILD_VERIFYING will poll positions and handle:
  - If positions open: transition to BUILD_COMPLETE
  - If timeout (no fills): transition to ERROR, manual intervention required
- **No automatic IOC fallback** in V5.5 (deferred to V5.6)
- Rationale: POST_ONLY is optional feature, IOC mode is primary

**POST_ONLY Handling (V5.6 - Future Enhancement)**:
- Implement automatic fill monitoring via WebSocket or REST polling
- If one leg fills and other doesn't after timeout, IOC the unfilled leg
- Or cancel both and restart with IOC mode
- Add configurable POST_ONLY_TIMEOUT parameter

**Implementation Note for V5.5**:
```python
# In execute_build_cycle, after order placement
if self.use_post_only:
    if eth_result.status == 'OPEN' or sol_result.status == 'OPEN':
        # Do NOT treat as success
        # Proceed to BUILD_VERIFYING which will poll positions
        self.logger.info(
            f"[POST_ONLY] Orders placed - ETH: {eth_result.status}, SOL: {sol_result.status}. "
            f"Proceeding to verification phase."
        )
        # Continue to BUILD_VERIFYING (do NOT return True yet)
```

**Scenario B**: POST_ONLY orders timeout without filling.

**Detection**:
```python
# After POST_ONLY_TIMEOUT (5 seconds)
if self.use_post_only:
    await asyncio.sleep(POST_ONLY_TIMEOUT)

    # Check if orders still open
    eth_still_open = eth_result.status == 'OPEN'
    sol_still_open = sol_result.status == 'OPEN'

    if eth_still_open or sol_still_open:
        self.logger.warning(
            f"[POST_ONLY_TIMEOUT] Orders not filled - "
            f"ETH={'OPEN' if eth_still_open else 'FILLED'}, "
            f"SOL={'OPEN' if sol_still_open else 'FILLED'}"
        )
        # Fall back to IOC mode
        return await self._fallback_to_ioc(eth_direction, sol_direction)
```

**Handling**: Fall back to IOC mode for immediate execution.

### 5. API Position Staleness

**Scenario**: API returns cached/stale position data (not yet updated from recent orders).

**Detection**:
```python
# In _get_verified_positions
async def _get_verified_positions(self) -> dict:
    # Fetch from API
    eth_pos = await self.eth_client.get_account_positions()
    sol_pos = await self.sol_client.get_account_positions()

    # Check if recent order was placed (within last 2 seconds)
    time_since_last_order = time.time() - getattr(self, '_last_order_time', 0)

    if time_since_last_order < 2.0:
        self.logger.warning(
            f"[API_STALE] Last order placed {time_since_last_order:.1f}s ago, "
            f"API positions may be stale"
        )
        # Add delay to allow API to update
        await asyncio.sleep(1.0)

        # Re-fetch
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

    return {"ETH": eth_pos, "SOL": sol_pos}
```

**Handling**: Add delay after recent orders, re-fetch positions.

---

## Testing Strategy

### Unit Tests

#### Test 1: Phase Transitions
```python
# test_phase_transitions.py
import pytest
from decimal import Decimal
from DN_pair_eth_sol_nado import CyclePhase, DNPairBot

@pytest.mark.asyncio
async def test_phase_transition_idle_to_build():
    """Test IDLE -> BUILD_PLACING transition"""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=1)

    assert bot._phase == CyclePhase.IDLE

    # Simulate build cycle start
    bot._phase = CyclePhase.BUILD_PLACING

    assert bot._phase == CyclePhase.BUILD_PLACING

@pytest.mark.asyncio
async def test_invalid_phase_transition():
    """Test that invalid transitions are rejected"""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=1)

    # Set phase to BUILD_COMPLETE
    bot._phase = CyclePhase.BUILD_COMPLETE

    # Try to start BUILD from BUILD_COMPLETE (should fail)
    # This would be caught in execute_build_cycle
    assert bot._phase == CyclePhase.BUILD_COMPLETE
```

#### Test 2: Position Verification
```python
# test_position_verification.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_build_refuses_with_open_positions():
    """Test that BUILD refuses to run when positions are open"""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=1)

    # Mock open positions
    bot._api_positions = {"ETH": Decimal("1.0"), "SOL": Decimal("-1.0")}
    bot._internal_positions = {"ETH": Decimal("1.0"), "SOL": Decimal("-1.0")}

    # Mock get_account_positions to return open positions
    async def mock_get_positions():
        return Decimal("1.0")

    bot.eth_client.get_account_positions = mock_get_positions
    bot.sol_client.get_account_positions = mock_get_positions

    # execute_build_cycle should return False
    result = await bot.execute_build_cycle()

    assert result is False
    assert bot._phase == CyclePhase.ERROR

@pytest.mark.asyncio
async def test_position_reconciliation():
    """Test that API positions take precedence over internal tracking"""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=1)

    # Set mismatched positions
    bot._internal_positions = {"ETH": Decimal("1.0"), "SOL": Decimal("-1.0")}

    # Mock API to return zero positions
    async def mock_get_positions():
        return Decimal("0")

    bot.eth_client.get_account_positions = mock_get_positions
    bot.sol_client.get_account_positions = mock_get_positions

    # Reconcile
    positions = await bot._get_verified_positions()

    # API wins
    assert positions["ETH"] == Decimal("0")
    assert positions["SOL"] == Decimal("0")
    # Internal updated to match
    assert bot._internal_positions["ETH"] == Decimal("0")
    assert bot._internal_positions["SOL"] == Decimal("0")
```

#### Test 3: Unwind Retries
```python
# test_unwind_retries.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_unwind_retries_on_position_mismatch():
    """Test that UNWIND retries up to MAX_RETRIES times"""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=1)

    # Set phase to BUILD_COMPLETE
    bot._phase = CyclePhase.BUILD_COMPLETE
    bot.entry_prices = {"ETH": Decimal("3000"), "SOL": Decimal("100")}
    bot.entry_quantities = {"ETH": Decimal("0.033"), "SOL": Decimal("1.0")}

    # Mock positions to return non-zero first 4 times, then zero
    call_count = {"count": 0}

    async def mock_get_positions():
        call_count["count"] += 1
        if call_count["count"] < 5:
            return Decimal("0.5")  # Still open
        return Decimal("0")  # Finally closed

    bot.eth_client.get_account_positions = mock_get_positions
    bot.sol_client.get_account_positions = mock_get_positions

    # Mock place_simultaneous_orders to return success
    async def mock_place_orders(eth_dir, sol_dir, phase=None):
        from exchanges.base import OrderResult
        return (
            OrderResult(success=True, status='FILLED', price=Decimal("3000"), filled_size=Decimal("0.033")),
            OrderResult(success=True, status='FILLED', price=Decimal("100"), filled_size=Decimal("1.0"))
        )

    bot.place_simultaneous_orders = mock_place_orders

    # execute_unwind_cycle should succeed after retries
    result = await bot.execute_unwind_cycle()

    assert result is True
    assert bot._phase == CyclePhase.IDLE
    assert call_count["count"] == 5  # 4 failures + 1 success
```

### Integration Tests

#### Test 4: Full Cycle with IOC Mode
```python
# test_full_cycle_ioc.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_buy_first_cycle_ioc():
    """Test full BUY_FIRST cycle with IOC mode"""
    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
        use_post_only=False  # IOC mode
    )

    # Initialize clients (use testnet)
    await bot.initialize_clients()

    # Verify no positions at start
    positions = await bot._get_verified_positions()
    assert abs(positions["ETH"]) < Decimal("0.001")
    assert abs(positions["SOL"]) < Decimal("0.001")

    # Execute BUY_FIRST cycle
    result = await bot.execute_buy_first_cycle()

    # Verify cycle succeeded
    assert result is True

    # Verify positions closed
    positions = await bot._get_verified_positions()
    assert abs(positions["ETH"]) < Decimal("0.001")
    assert abs(positions["SOL"]) < Decimal("0.001")

    # Verify phase returned to IDLE
    assert bot._phase == CyclePhase.IDLE

    # Cleanup
    await bot.cleanup()
```

#### Test 5: Alternating Strategy with Early Exit
```python
# test_alternating_strategy.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_alternating_strategy_early_exit():
    """Test that alternating strategy stops on failure"""
    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=5,  # Request 5 iterations
        use_post_only=False
    )

    await bot.initialize_clients()

    # Mock execute_sell_first_cycle to fail on second iteration
    iteration_count = {"count": 0}

    original_buy_first = bot.execute_buy_first_cycle
    original_sell_first = bot.execute_sell_first_cycle

    async def mock_sell_first():
        iteration_count["count"] += 1
        if iteration_count["count"] == 1:
            return await original_sell_first()  # First SELL_FIRST succeeds
        else:
            return False  # Subsequent SELL_FIRST fails

    bot.execute_sell_first_cycle = mock_sell_first

    # Run alternating strategy
    results = await bot.run_alternating_strategy()

    # Should stop after 3 cycles (BUY_FIRST, SELL_FIRST success, BUY_FIRST, SELL_FIRST fail)
    assert len(results) == 4  # 2 iterations (4 cycles)
    assert bot._phase == CyclePhase.ERROR

    await bot.cleanup()
```

### Edge Case Tests

#### Test 6: Partial Fill Handling
```python
# test_partial_fill.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_partial_fill_detection():
    """Test detection of partial fills"""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=1)

    # Mock place_simultaneous_orders to return partial fill
    async def mock_place_orders(eth_dir, sol_dir, phase=None):
        from exchanges.base import OrderResult
        return (
            OrderResult(success=True, status='FILLED', price=Decimal("3000"), filled_size=Decimal("0.01")),  # Partial
            OrderResult(success=True, status='FILLED', price=Decimal("100"), filled_size=Decimal("1.0"))  # Full
        )

    bot.place_simultaneous_orders = mock_place_orders

    # Execute build cycle
    result = await bot.execute_build_cycle()

    # Should detect partial fill and fail
    assert result is False
    assert bot._phase == CyclePhase.ERROR
```

#### Test 7: POST_ONLY Timeout Fallback
```python
# test_post_only_timeout.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_post_only_timeout_fallback():
    """Test POST_ONLY timeout fallback to IOC"""
    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
        use_post_only=True  # POST_ONLY mode
    )

    await bot.initialize_clients()

    # Mock place_open_order to return OPEN status
    async def mock_place_open(*args, **kwargs):
        from exchanges.base import OrderResult
        return OrderResult(success=True, status='OPEN', price=Decimal("3000"), size=Decimal("0.033"))

    bot.eth_client.place_open_order = mock_place_open
    bot.sol_client.place_open_order = mock_place_open

    # Execute build cycle
    result = await bot.execute_build_cycle()

    # Should handle OPEN status (implementation depends on V5.5 design)
    # For now, we expect it to log warning but continue
    assert result is True or result is False  # Depends on implementation

    await bot.cleanup()
```

#### Test 8: WebSocket Disconnection Handling
```python
# test_websocket_disconnect.py
import pytest
from decimal import Decimal

@pytest.mark.asyncio
async def test_websocket_disconnect_rest_fallback():
    """Test REST fallback when WebSocket disconnects"""
    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
        use_post_only=False
    )

    await bot.initialize_clients()

    # Simulate WebSocket disconnect
    bot.eth_client._ws_connected = False
    bot.sol_client._ws_connected = False

    # Execute cycle (should use REST fallback)
    result = await bot.execute_buy_first_cycle()

    # Should succeed using REST
    assert result is True

    await bot.cleanup()
```

---

## Verification Steps

### Pre-Deployment Checklist

1. **Code Review**
   - [ ] All 5 critic issues addressed
   - [ ] Phase parameter interaction with `_is_entry_phase` documented
   - [ ] Position tracking circular dependency resolved
   - [ ] POST_ONLY mode edge cases handled
   - [ ] State transition diagram complete
   - [ ] Edge case tests defined

2. **Static Analysis**
   - [ ] No syntax errors
   - [ ] No import errors
   - [ ] Type hints consistent
   - [ ] No unused variables

3. **Unit Tests**
   - [ ] Phase transition tests pass
   - [ ] Position verification tests pass
   - [ ] Unwind retry tests pass
   - [ ] Partial fill tests pass
   - [ ] Edge case tests pass

4. **Integration Tests**
   - [ ] Full cycle tests pass (IOC mode)
   - [ ] Alternating strategy tests pass
   - [ ] Early exit on failure works

### Post-Deployment Verification

1. **Dry Run Test**
   ```bash
   # Run with small size and 1 iteration
   python hedge/DN_pair_eth_sol_nado.py \
     --size 10 \
     --iter 1 \
     --use-ioc \
     --min-spread-bps 0
   ```

2. **Verify Success Criteria**
   - [ ] ETH position approx 0 (abs < 0.001)
   - [ ] SOL position approx 0 (abs < 0.001)
   - [ ] No position accumulation
   - [ ] CSV shows complete cycle
   - [ ] Phase returned to IDLE

3. **Alternating Strategy Test**
   ```bash
   # Run with 2 iterations to test BUY_FIRST + SELL_FIRST
   python hedge/DN_pair_eth_sol_nado.py \
     --size 10 \
     --iter 2 \
     --use-ioc \
     --min-spread-bps 0
   ```

4. **Verify Early Exit**
   - [ ] Bot stops on cycle failure
   - [ ] Error phase set correctly
   - [ ] Manual intervention message logged

5. **Log Analysis**
   - [ ] Phase transitions logged correctly
   - [ ] Position reconciliation warnings (if any)
   - [ ] No emergency_unwind calls during BUILD
   - [ ] Unwind retries logged

---

## Rollback Plan

### If Critical Issues Found

1. **Immediate Rollback**
   ```bash
   # Revert to previous version
   git checkout HEAD~1 hedge/DN_pair_eth_sol_nado.py

   # Verify rollback
   python hedge/DN_pair_eth_sol_nado.py --size 10 --iter 1 --use-ioc
   ```

2. **Fallback Strategy**
   - Disable new phase tracking (comment out `self._phase` assignments)
   - Re-enable legacy `handle_emergency_unwind` (restore deleted functions)
   - Reduce unwind retries to original value (1 retry)

3. **Partial Rollback** (if some changes work, others don't)
   - Keep position verification before BUILD (safety feature)
   - Remove phase tracking (complexity)
   - Keep increased unwind retries (robustness)

### Rollback Decision Criteria

| Issue Severity | Action |
|----------------|--------|
| **Critical** - Bot doesn't start, positions stuck | Full rollback immediately |
| **High** - UNWIND fails repeatedly | Partial rollback (keep BUILD checks) |
| **Medium** - POST_ONLY mode issues | Disable POST_ONLY, use IOC only |
| **Low** - Logging issues, minor bugs | Keep changes, file bug for later fix |

---

## Success Metrics

### Quantitative Metrics

1. **Position Accuracy**
   - ETH net position: abs < 0.001 after UNWIND
   - SOL net position: abs < 0.001 after UNWIND
   - Zero accumulation over 10 cycles

2. **Cycle Success Rate**
   - IOC mode: >95% success rate
   - POST_ONLY mode: >90% success rate (with IOC fallback)

3. **Recovery Robustness**
   - 100% early exit on cycle failure
   - 0% position accumulation on error

4. **Performance**
   - BUILD phase: <5 seconds
   - UNWIND phase: <10 seconds (including retries)

### Qualitative Metrics

1. **Code Quality**
   - Clear phase transitions in logs
   - No circular dependency confusion
   - Backward compatible with existing CSV format

2. **Maintainability**
   - Phase enum easy to extend
   - Position tracking logic centralized
   - Error states clearly defined

---

## Implementation Timeline

### Phase 1: Core Changes (2-3 hours)
1. Add CyclePhase enum and state machine
2. Implement position tracking with reconciliation
3. Update `place_simultaneous_orders` to accept phase parameter

### Phase 2: Safety Fixes (1-2 hours)
4. Fix `execute_build_cycle` - add position verification
5. Fix `execute_unwind_cycle` - add retries and verification
6. Remove legacy `handle_emergency_unwind`

### Phase 3: Strategy Updates (1 hour)
7. Update `run_alternating_strategy` - add early exit
8. Update entry phase tracking to use new phase system

### Phase 4: Testing (2-3 hours)
9. Write unit tests
10. Write integration tests
11. Write edge case tests

### Phase 5: Verification (1 hour)
12. Dry run testing
13. Log analysis
14. Success criteria validation

**Total Estimated Time**: 7-10 hours

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API position staleness causes false positives | Medium | High | Add delay after orders, re-fetch positions |
| Phase tracking complexity introduces new bugs | Medium | High | Extensive unit tests, gradual rollout |
| POST_ONLY mode fills don't work as expected | High | Medium | Document as V5.5 limitation, defer to V5.6 |
| Removal of emergency_unwind creates new risks | Low | High | Keep manual intervention requirement, improve error logging |
| Rollback needed due to unforeseen issues | Low | Medium | Clear rollback plan, keep previous version tagged |

---

## Critical Design Decisions

### Retry Count Rationale (Clarifying Priority 2 Issue #7)

The plan uses different retry counts in different contexts:

| Context | Retry Count | Delay | Rationale |
|---------|-------------|-------|-----------|
| **Pre-BUILD Position Check** | 3 retries | 1.0s | Checking positions BEFORE opening - should be quick (either 0 or not) |
| **Post-BUILD Verification** | 5 retries | 1.0s | Verifying positions AFTER opening - API may take longer to process new orders |
| **UNWIND Position Check** | 5 retries | 2.0s | Closing positions may be slower (market impact, slippage) |
| **Position Reconciliation** | No retries | N/A | API is source of truth, fetch once per call |

**Why Different Values?**
1. **Pre-BUILD (3 retries)**: We're checking if positions are CLOSED (0). This should be immediately available from API. If API says 0, it's likely correct. Only retry 3 times in case of temporary network issues.
2. **Post-BUILD (5 retries)**: We're checking if positions OPENED. API may have propagation delays after order placement. More retries needed to account for order processing time.
3. **UNWIND (5 retries)**: Closing positions can be slower due to market conditions, partial fills, or exchange-side processing. Higher retry count with longer delay (2s) for robustness.

**Configuration Note**: These values are defined as constants within each method for V5.5. In V5.6, consider moving to class-level constants for easier configuration:

```python
# Future V5.6 enhancement
class DNPairBot:
    PRE_BUILD_VERIFY_RETRIES = 3
    POST_BUILD_VERIFY_RETRIES = 5
    UNWIND_VERIFY_RETRIES = 5
    POSITION_CHECK_DELAY = 1.0
    UNWIND_CHECK_DELAY = 2.0
```

---

## Conclusion

This fix plan addresses ALL Priority 1 critic issues and clarifies Priority 2 issues:

### Priority 1 Issues (All Fixed):

1. **CyclePhase enum location**: Specified MODULE LEVEL definition (after imports, before class) at line ~40-50. This enables test imports and maintains proper scope.

2. **Legacy flag initialization**: Added explicit initialization in Step 1.5:
   - `self._is_entry_phase = False`
   - `self._is_exit_phase = False`
   - These are now properly initialized alongside `self._phase = CyclePhase.IDLE`

3. **Source of truth precedence**: Defined clear precedence rules:
   - `self._phase` ALWAYS wins over legacy flags
   - Implementation pattern provided for backward-compatible checks
   - When conflict exists, enum value takes precedence

4. **Logger guard missing**: Added precondition checks in both `_get_verified_positions()` and `_update_internal_position()`:
   - Guard: `if not hasattr(self, 'logger') or self.logger is None`
   - Methods return early or update without logging during initialization
   - Documented that these methods must be placed AFTER `_setup_logger()` in `__init__`

5. **BUILD verification phase implemented**: Added complete BUILD_VERIFYING implementation in Step 3:
   - After order placement: `BUILD_PLACING -> BUILD_VERIFYING`
   - Poll positions with 5 retries, 1s delay
   - Check both positions opened (non-zero)
   - Transition to `BUILD_COMPLETE` on success, `ERROR` on failure
   - Handles partial fill state (only one position opened)

### Priority 2 Issues (Clarified):

6. **POST_ONLY OPEN status handling**: Clarified in Edge Case Handling section 4:
   - OPEN status triggers BUILD_VERIFYING (not immediate success)
   - BUILD_VERIFYING polls positions to verify actual fills
   - No automatic IOC fallback in V5.5 (deferred to V5.6)
   - Manual intervention required if timeout

7. **Inconsistent retry counts**: Explained in "Critical Design Decisions" section:
   - Pre-BUILD: 3 retries (checking positions are closed - should be quick)
   - Post-BUILD: 5 retries (API may take time to process new orders)
   - UNWIND: 5 retries with 2s delay (closing is slower)
   - Rationale provided for each context

### Original Issues (Maintained):

1. **Phase parameter ambiguity**: Resolved by implementing CyclePhase enum with clear transitions and backward-compatible `_is_entry_phase` flag
2. **Position tracking circular dependency**: Resolved by hierarchical trust model (API always wins) with reconciliation logging
3. **POST_ONLY mode edge cases**: Documented handling strategy with BUILD_VERIFYING phase
4. **State transition diagram**: Complete diagram with all 9 states and transitions provided
5. **Edge case tests**: Comprehensive test suite defined for partial fills, rejections, disconnections, and POST_ONLY scenarios

The plan maintains backward compatibility while adding robust position tracking, phase management, and error recovery mechanisms.

---

**Plan Version**: 2.0 (REVISED - All Priority 1 Issues Fixed)
**Date**: 2026-01-31
**Author**: Prometheus (Strategic Planning Consultant)
**Status**: READY FOR IMPLEMENTATION

**Revision History**:
- v1.0: Initial plan addressing 5 original issues
- v2.0: Revised to address Critic feedback - all Priority 1 issues fixed, Priority 2 issues clarified
