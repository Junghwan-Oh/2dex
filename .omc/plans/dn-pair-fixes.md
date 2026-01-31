# DN Pair Trading System Fixes - Implementation Plan

## Context

### Original Request
Create comprehensive implementation plan for DN pair trading system fixes addressing 3 P0 critical issues and verification tasks.

### Pre-Gathered Codebase Context

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (2844 lines total)

**Strategy Pattern:**
- BUY_FIRST cycle (i % 2 == 0): BUILD (Long ETH / Short SOL) -> UNWIND (Sell ETH / Buy SOL)
- SELL_FIRST cycle (i % 2 == 1): BUILD (Short ETH / Long SOL) -> UNWIND (Buy ETH / Sell SOL)

**CSV Logging:** Lines 522-541 in `place_simultaneous_orders()`
**Emergency Unwind:** Lines 573-595 (`emergency_unwind_eth()`), Lines 597-619 (`emergency_unwind_sol()`)
**BookDepth Handler:** `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_bookdepth_handler.py`

### Research Findings

1. **Alternating Logic Verification:** Code review confirms alternating logic is correct (i%2 check). BUY_FIRST for even iterations, SELL_FIRST for odd iterations.

2. **BookDepth Integration:** `nado_bookdepth_handler.py` provides `estimate_slippage()`, `get_available_liquidity()`, `estimate_exit_capacity()` methods but not currently used for hedging balance calculation.

3. **Order Sizing:** Line 377 in `calculate_order_size_with_slippage()` uses `self.target_notional / price` without validating actual fillable quantity against order book depth.

---

## Work Objectives

### Core Objective
Fix P0 critical bugs in DN pair trading system causing incorrect CSV logging and hedging imbalance, then add comprehensive verification.

### Deliverables
1. Correct CSV logging for both buy_first and sell_first directions
2. CSV logging for emergency_unwind operations
3. Hedging balance using BookDepth liquidity data
4. Comprehensive test suite for alternating execution
5. Metrics collection for slippage, fill rate, delta PnL

### Definition of Done
- All CSV logs correctly record entry/exit for both BUY_FIRST and SELL_FIRST
- Emergency unwind operations are fully logged
- Hedging imbalance is below 0.1% between ETH and SOL notionals
- Test suite validates alternating execution with 100% coverage
- Metrics are collected and exported for analysis
- All existing functionality remains intact

---

## Must Have / Must NOT Have

### Must Have (Guardrails)
- CSV logging MUST correctly identify entry vs exit for both BUY_FIRST and SELL_FIRST
- Emergency unwind MUST log to CSV with correct order_type
- Hedging balance MUST use actual liquidity data from BookDepth
- Tests MUST verify alternating execution (even=BUY_FIRST, odd=SELL_FIRST)
- Metrics collection MUST NOT interfere with trading performance
- All fixes MUST maintain backward compatibility

### Must NOT Have
- NO breaking changes to existing CSV format (fields documented below)
- NO changes to order execution logic (only logging and calculation)
- NO performance degradation in trading cycles
- NO hardcoded values (use configuration where applicable)
- NO blocking synchronous operations in async methods

**CSV Format Reference (from `_initialize_csv_file()` at Lines 212-231):**
Fields: `exchange`, `timestamp`, `side`, `price`, `quantity`, `order_type`, `mode`

**Mode Values:**
- Current code uses: "FILLED" (line 530), "PARTIAL" (line 530), empty string (default)
- New: "EMERGENCY" (for emergency unwind operations)

---

## Task Flow and Dependencies

```
Task 1: Fix CSV Logging in place_simultaneous_orders()
    │
    ├─→ Task 2: Add CSV Logging to emergency_unwind_eth()
    │
    ├─→ Task 3: Add CSV Logging to emergency_unwind_sol()
    │
    ├─→ Task 4: Implement Hedging Balance with BookDepth
    │       │
    │       └─→ Task 5: Add Metrics Collection (depends on Task 4 for balance data)
    │
    └─→ Task 6: Create Test Suite (write AFTER Task 1 completes to avoid signature mismatch)
```

**Critical Path:** Task 1 → Task 2 → Task 3 → Task 4 → Task 5
**Parallel Task:** Task 6 (developed alongside but written after Task 1)

---

## Detailed TODOs

### Task 1: Fix CSV Logging in place_simultaneous_orders()
**Priority:** P0 Critical
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 437-441 (signature), 522-541 (CSV logging), 630, 642, 699, 709 (callers)

**Problem:**
```python
# Current (WRONG) at Lines 529, 539:
order_type="entry" if eth_direction == "buy" else "exit"
order_type="entry" if sol_direction == "sell" else "exit"
```

For SELL_FIRST BUILD:
- ETH direction="sell" → logs as "exit" (should be "entry")
- SOL direction="buy" → logs as "exit" (should be "entry")

For SELL_FIRST UNWIND:
- ETH direction="buy" → logs as "entry" (should be "exit")
- SOL direction="sell" → logs as "entry" (should be "exit")

**Solution:**
Add `phase` parameter to `place_simultaneous_orders()` to distinguish BUILD vs UNWIND.

**Changes:**

1. **Line 437-441: Update signature**
   ```python
   async def place_simultaneous_orders(
       self,
       eth_direction: str,
       sol_direction: str,
       phase: str = "BUILD"  # "BUILD" or "UNWIND"
   ) -> Tuple[OrderResult, OrderResult]:
   ```

2. **Lines 522-541: Update CSV logging to use phase**
   ```python
   # Log actual fills to CSV
   if eth_fill_qty > 0:
       self.log_trade_to_csv(
           exchange="NADO",
           side=f"ETH-{eth_direction.upper()}",
           price=str(eth_fill_price),
           quantity=str(eth_fill_qty),
           order_type="entry" if phase == "BUILD" else "exit",
           mode="FILLED" if eth_filled else "PARTIAL"
       )

   if sol_fill_qty > 0:
       self.log_trade_to_csv(
           exchange="NADO",
           side=f"SOL-{sol_direction.upper()}",
           price=str(sol_fill_price),
           quantity=str(sol_fill_qty),
           order_type="entry" if phase == "BUILD" else "exit",
           mode="FILLED" if sol_filled else "PARTIAL"
       )
   ```

3. **Update all callers with search pattern: `await self\.place_simultaneous_orders\(`**
   - Line 630: `await self.place_simultaneous_orders("buy", "sell", "BUILD")`
   - Line 642: `await self.place_simultaneous_orders("sell", "buy", "UNWIND")`
   - Line 699: `await self.place_simultaneous_orders("sell", "buy", "BUILD")`
   - Line 709: `await self.place_simultaneous_orders("buy", "sell", "UNWIND")`

**Acceptance Criteria:**
- BUY_FIRST BUILD (Long ETH/Short SOL): ETH buy→entry, SOL sell→entry
- BUY_FIRST UNWIND (Sell ETH/Buy SOL): ETH sell→exit, SOL buy→exit
- SELL_FIRST BUILD (Short ETH/Long SOL): ETH sell→entry, SOL buy→entry
- SELL_FIRST UNWIND (Buy ETH/Sell SOL): ETH buy→exit, SOL sell→exit

---

### Task 2: Add CSV Logging to emergency_unwind_eth()
**Priority:** P0 Critical
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 573-595

**Problem:** Emergency unwind does not log to CSV, causing data loss for failed SELL_FIRST cycles.

**Solution:** Add CSV logging with correct order_type based on position being closed.

**Changes:**
```python
async def emergency_unwind_eth(self):
    """Emergency unwind ETH position - handle both long and short."""
    if self.eth_client:
        try:
            current_pos = await self.eth_client.get_account_positions()
            if abs(current_pos) < Decimal("0.001"):
                return  # No position to close

            # Determine side based on position
            side = "sell" if current_pos > 0 else "buy"
            self.logger.info(f"[EMERGENCY] Closing ETH position: {current_pos} ({side})")

            result = await self.eth_client.place_ioc_order(
                self.eth_client.config.contract_id,
                abs(current_pos),
                side
            )
            if result.success:
                self.logger.info(f"[EMERGENCY] ETH closed: {result.filled_size} @ ${result.price}")
                # ADD CSV LOGGING HERE (after line 591, before line 592)
                if result.filled_size > 0:
                    # Log to CSV - emergency unwind is always an EXIT
                    self.log_trade_to_csv(
                        exchange="NADO",
                        side=f"ETH-{side.upper()}",
                        price=str(result.price),
                        quantity=str(result.filled_size),
                        order_type="exit",  # Emergency unwind always exits position
                        mode="EMERGENCY"  # Special mode to identify emergency unwind
                    )
            else:
                self.logger.error(f"[EMERGENCY] ETH close failed: {result.error_message}")
        except Exception as e:
            self.logger.error(f"[EMERGENCY] ETH unwind error: {e}")
```

**Acceptance Criteria:**
- Emergency unwind logs to CSV with order_type="exit"
- Mode="EMERGENCY" to distinguish from normal unwinds
- Logs only if order succeeds and fills
- Logs for both long and short positions

---

### Task 3: Add CSV Logging to emergency_unwind_sol()
**Priority:** P0 Critical
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 597-619

**Problem:** Same as Task 2 but for SOL.

**Solution:** Identical to Task 2 but for SOL client.

**Changes:**
```python
async def emergency_unwind_sol(self):
    """Emergency unwind SOL position - handle both long and short."""
    if self.sol_client:
        try:
            current_pos = await self.sol_client.get_account_positions()
            if abs(current_pos) < Decimal("0.001"):
                return  # No position to close

            # Determine side based on position
            side = "sell" if current_pos > 0 else "buy"
            self.logger.info(f"[EMERGENCY] Closing SOL position: {current_pos} ({side})")

            result = await self.sol_client.place_ioc_order(
                self.sol_client.config.contract_id,
                abs(current_pos),
                side
            )
            if result.success:
                self.logger.info(f"[EMERGENCY] SOL closed: {result.filled_size} @ ${result.price}")
                # ADD CSV LOGGING HERE (after line 615, before line 616)
                if result.filled_size > 0:
                    # Log to CSV - emergency unwind is always an EXIT
                    self.log_trade_to_csv(
                        exchange="NADO",
                        side=f"SOL-{side.upper()}",
                        price=str(result.price),
                        quantity=str(result.filled_size),
                        order_type="exit",  # Emergency unwind always exits position
                        mode="EMERGENCY"  # Special mode to identify emergency unwind
                    )
            else:
                self.logger.error(f"[EMERGENCY] SOL close failed: {result.error_message}")
        except Exception as e:
            self.logger.error(f"[EMERGENCY] SOL unwind error: {e}")
```

**Acceptance Criteria:**
- Same as Task 2 but for SOL

---

### Task 4: Implement Hedging Balance with BookDepth
**Priority:** P0 Critical
**Files:**
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (main changes)
- `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_bookdepth_handler.py` (reference only)

**Problem:** Order sizing uses target notional without checking actual liquidity, causing 5.7% imbalance (ETH $101.12 vs SOL $105.69 for $100 target).

**Root Cause:** Line 377 `calculate_order_size_with_slippage()` calculates quantity but doesn't ensure both legs can fill at same notional level.

**API Contract Reference:**

NadoClient provides `estimate_slippage()` method (Lines 213-233 in `nado.py`) which proxies to BookDepthHandler:

```python
# In NadoClient (nado.py:213-233):
async def estimate_slippage(
    self,
    side: str,
    quantity: Decimal
) -> Decimal:
    """
    Estimate slippage for a given order quantity using BookDepth data.

    Args:
        side: "buy" or "sell"
        quantity: Order quantity

    Returns:
        Slippage in basis points, or 999999 if insufficient liquidity
    """
    handler = self.get_bookdepth_handler()
    if handler is None:
        return Decimal(999999)  # No WebSocket data

    return handler.estimate_slippage(side, quantity)
```

BookDepthHandler `estimate_slippage()` (Lines 167-234 in `nado_bookdepth_handler.py`) does the actual calculation.

Access pattern: `await self.eth_client.estimate_slippage(side, quantity)`

**tick_size Access Pattern Reference (from `nado.py` Line 869 in connect_websockets method):**
```python
self.config.tick_size = Decimal(str(from_x18(tick_size_x18)))
```
Access via: `self.eth_client.config.tick_size` or `self.sol_client.config.tick_size`

Note: The tick_size assignment happens within the `connect_websockets()` method at line 869, but the tick_size value is initialized earlier in the NadoClient initialization and stored in `self.config.tick_size`. DN_pair_bot can access it directly via the client's config object.

**Solution:** Implement two-pass approach - first calculate target quantities, then find minimum fillable notional across both legs.

**Implementation Steps:**

1. **Add helper method to calculate actual notional:**
   Location: After `calculate_order_size_with_slippage()` (after Line 405)

   ```python
   async def calculate_balanced_order_sizes(
       self,
       eth_price: Decimal,
       sol_price: Decimal,
       eth_direction: str,
       sol_direction: str,
       max_slippage_bps: int = 20
   ) -> Tuple[Decimal, Decimal, Decimal]:
       """
       Calculate balanced order sizes ensuring equal notionals.

       Uses BookDepth to find maximum quantity both legs can fill
       while maintaining hedging balance within tolerance.

       Returns:
           Tuple of (eth_qty, sol_qty, actual_notional)
       """
       # Calculate initial target quantities
       eth_raw_qty = self.target_notional / eth_price
       sol_raw_qty = self.target_notional / sol_price

       # Round to tick sizes (access pattern from nado.py:869)
       eth_tick_size = self.eth_client.config.tick_size
       sol_tick_size = self.sol_client.config.tick_size

       eth_target_qty = (eth_raw_qty / eth_tick_size).quantize(Decimal('1')) * eth_tick_size
       sol_target_qty = (sol_raw_qty / sol_tick_size).quantize(Decimal('1')) * sol_tick_size

       # Check slippage for both legs (NadoClient.estimate_slippage proxies to BookDepthHandler)
       eth_slippage = await self.eth_client.estimate_slippage(eth_direction, eth_target_qty)
       sol_slippage = await self.sol_client.estimate_slippage(sol_direction, sol_target_qty)

       # If both can fill at target with acceptable slippage
       if eth_slippage < 999999 and sol_slippage < 999999:
           if eth_slippage <= max_slippage_bps and sol_slippage <= max_slippage_bps:
               # Both can fill - verify notional balance
               eth_notional = eth_target_qty * eth_price
               sol_notional = sol_target_qty * sol_price
               notional_diff_pct = abs(eth_notional - sol_notional) / ((eth_notional + sol_notional) / 2) * 100

               if notional_diff_pct <= 0.1:  # 0.1% tolerance
                   return eth_target_qty, sol_target_qty, max(eth_notional, sol_notional)

       # Need to balance - find common notional both can fill
       # Binary search for maximum balanced notional
       low_notional = Decimal("10")
       high_notional = self.target_notional

       for _ in range(10):  # 10 iterations enough
           mid_notional = (low_notional + high_notional) / 2

           # Calculate quantities at this notional
           test_eth_qty = (mid_notional / eth_price / eth_tick_size).quantize(Decimal('1')) * eth_tick_size
           test_sol_qty = (mid_notional / sol_price / sol_tick_size).quantize(Decimal('1')) * sol_tick_size

           # Check if both can fill
           test_eth_slippage = await self.eth_client.estimate_slippage(eth_direction, test_eth_qty)
           test_sol_slippage = await self.sol_client.estimate_slippage(sol_direction, test_sol_qty)

           if test_eth_slippage <= max_slippage_bps and test_sol_slippage <= max_slippage_bps:
               low_notional = mid_notional
           else:
               high_notional = mid_notional

       # Return balanced quantities
       final_eth_qty = (low_notional / eth_price / eth_tick_size).quantize(Decimal('1')) * eth_tick_size
       final_sol_qty = (low_notional / sol_price / sol_tick_size).quantize(Decimal('1')) * sol_tick_size

       # VALIDATION: Verify returned quantities meet slippage limits
       final_eth_slippage = await self.eth_client.estimate_slippage(eth_direction, final_eth_qty)
       final_sol_slippage = await self.sol_client.estimate_slippage(sol_direction, final_sol_qty)

       if final_eth_slippage > max_slippage_bps or final_sol_slippage > max_slippage_bps:
           self.logger.warning(
               f"[BALANCE] Could not achieve balanced sizing within slippage limits. "
               f"ETH slippage: {final_eth_slippage:.1f} bps, SOL slippage: {final_sol_slippage:.1f} bps. "
               f"Returning zero quantities to prevent executing orders that violate slippage limits."
           )
           # Return zero quantities - caller should handle this case (e.g., skip this cycle, reduce size)
           return Decimal("0"), Decimal("0"), Decimal("0")

       return final_eth_qty, final_sol_qty, low_notional
   ```

2. **Update place_simultaneous_orders() to use balanced sizing:**
   Replace Lines 464-469:

   ```python
   # Calculate balanced order sizes using BookDepth
   eth_qty, sol_qty, actual_notional = await self.calculate_balanced_order_sizes(
       eth_price, sol_price, eth_direction, sol_direction, max_slippage_bps=20
   )

   # Calculate slippage for logging (reuse existing method)
   _, eth_slippage_bps, _ = await self.calculate_order_size_with_slippage(
       eth_price, "ETH", eth_direction, max_slippage_bps=20
   )
   _, sol_slippage_bps, _ = await self.calculate_order_size_with_slippage(
       sol_price, "SOL", sol_direction, max_slippage_bps=20
   )

   self.logger.info(
       f"[ORDER] Placing orders: "
       f"ETH {eth_direction} {eth_qty} @ ~${eth_price} (${eth_qty * eth_price:.2f} notional), "
       f"SOL {sol_direction} {sol_qty} @ ~${sol_price} (${sol_qty * sol_price:.2f} notional), "
       f"Target: ${actual_notional:.2f}"
   )
   ```

3. **Add BookDepth connection verification:**
   Add after `calculate_balanced_order_sizes()` method:

   ```python
   async def verify_bookdepth_connection(self) -> bool:
       """Verify BookDepth WebSocket is connected and receiving data."""
       # Access BookDepthHandler via NadoClient.get_bookdepth_handler()
       eth_handler = self.eth_client.get_bookdepth_handler()
       sol_handler = self.sol_client.get_bookdepth_handler()

       if not eth_handler or not sol_handler:
           self.logger.warning("[BOOKDEPTH] BookDepth handlers not initialized")
           return False

       # Check if we have order book data
       eth_bid = eth_handler.get_best_bid()
       eth_ask = eth_handler.get_best_ask()
       sol_bid = sol_handler.get_best_bid()
       sol_ask = sol_handler.get_best_ask()

       # get_best_bid() and get_best_ask() return tuples of (price, quantity)
       if eth_bid[0] is None or eth_ask[0] is None or sol_bid[0] is None or sol_ask[0] is None:
           self.logger.warning("[BOOKDEPTH] No order book data available")
           return False

       return True
   ```

**Acceptance Criteria:**
- Hedging imbalance < 0.1% between ETH and SOL notionals
- Falls back gracefully if BookDepth unavailable
- Logs actual notional for both legs
- Verifies BookDepth connection before using it
- Final validation ensures returned quantities meet slippage limits
- If validation fails, returns (0, 0, 0) to prevent executing orders that violate limits

---

### Task 5: Add Metrics Collection
**Priority:** P1 High
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Goal:** Collect metrics for slippage, fill rate, delta PnL analysis.

**Implementation:**

1. **Add metrics dataclass after TradeMetrics (after Line 73):**
   ```python
   @dataclass
   class CycleMetrics:
       """Metrics collected per trading cycle."""
       cycle_number: int
       direction: str  # "BUY_FIRST" or "SELL_FIRST"

       # Order metrics
       eth_target_qty: Decimal
       eth_fill_qty: Decimal
       eth_fill_price: Decimal
       eth_slippage_bps: Decimal

       sol_target_qty: Decimal
       sol_fill_qty: Decimal
       sol_fill_price: Decimal
       sol_slippage_bps: Decimal

       # Hedging metrics
       eth_notional: Decimal
       sol_notional: Decimal
       notional_imbalance_pct: Decimal

       # Fill metrics
       eth_fill_rate: Decimal  # filled/target
       sol_fill_rate: Decimal

       # Emergency unwind
       emergency_unwind: bool
       emergency_unwind_leg: str  # "ETH", "SOL", or "NONE"

       def to_dict(self):
           """Convert to dictionary for CSV export."""
           from decimal import Decimal
           return {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(self).items()}
   ```

2. **Initialize metrics list in `__init__()` (find line with `self.trade_metrics_list = []` and add nearby):**
   ```python
   self.cycle_metrics_list: List[CycleMetrics] = []
   ```

3. **Collect metrics in place_simultaneous_orders() (after Line 520, after fill confirmation):**
   ```python
   # Collect cycle metrics
   metrics = CycleMetrics(
       cycle_number=self.completed_cycles,
       direction="BUY_FIRST" if phase == "BUILD" and eth_direction == "buy" else "SELL_FIRST",

       eth_target_qty=eth_qty,
       eth_fill_qty=eth_fill_qty,
       eth_fill_price=eth_fill_price,
       eth_slippage_bps=eth_slippage_bps,

       sol_target_qty=sol_qty,
       sol_fill_qty=sol_fill_qty,
       sol_fill_price=sol_fill_price,
       sol_slippage_bps=sol_slippage_bps,

       eth_notional=eth_fill_qty * eth_fill_price if eth_fill_qty > 0 else Decimal("0"),
       sol_notional=sol_fill_qty * sol_fill_price if sol_fill_qty > 0 else Decimal("0"),
       notional_imbalance_pct=abs(eth_fill_qty * eth_fill_price - sol_fill_qty * sol_fill_price) /
                               ((eth_fill_qty * eth_fill_price + sol_fill_qty * sol_fill_price) / 2) * 100
                               if (eth_fill_qty > 0 and sol_fill_qty > 0) else Decimal("0"),

       eth_fill_rate=eth_fill_qty / eth_qty if eth_qty > 0 else Decimal("0"),
       sol_fill_rate=sol_fill_qty / sol_qty if sol_qty > 0 else Decimal("0"),

       emergency_unwind=False,
       emergency_unwind_leg="NONE"
   )

   self.cycle_metrics_list.append(metrics)
   ```

4. **Export metrics to CSV (add method after `export_trade_metrics()` at Line 273):**
   ```python
   def export_cycle_metrics(self):
       """Export cycle metrics to CSV for analysis."""
       if not self.cycle_metrics_list:
           self.logger.info("[METRICS] No cycle metrics to export")
           return

       timestamp_str = datetime.now(pytz.UTC).strftime("%Y%m%d_%H%M%S")
       metrics_filename = f"logs/cycle_metrics_{timestamp_str}.csv"

       try:
           with open(metrics_filename, "w", newline="") as csvfile:
               fieldnames = CycleMetrics.__dataclass_fields__.keys()
               writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
               writer.writeheader()

               for metrics in self.cycle_metrics_list:
                   writer.writerow(metrics.to_dict())

           self.logger.info(f"[METRICS] Exported {len(self.cycle_metrics_list)} cycle metrics to {metrics_filename}")
       except Exception as e:
           self.logger.error(f"[METRICS] Failed to export cycle metrics: {e}")
           import traceback
           self.logger.error(f"[METRICS] Traceback: {traceback.format_exc()}")
   ```

5. **Call export in cleanup() or at end of run_strategy() (find where `export_trade_metrics()` is called):**
   ```python
   self.export_cycle_metrics()
   ```

**Acceptance Criteria:**
- Metrics collected for every cycle
- Exported to CSV on completion
- Includes slippage, fill rate, notional imbalance
- Emergency unwind events tracked

---

### Task 6: Create Test Suite
**Priority:** P1 High
**Test Directory Structure:**
- Create new directory: `/Users/botfarmer/2dex/tests/stage4/dn_pair/`
- Test files: `test_dn_pair_csv_logging.py`, `test_dn_pair_alternating.py`, `test_dn_pair_hedging_balance.py`

**Rationale:** Existing tests are in `/Users/botfarmer/2dex/tests/stage4/` (e.g., `test_alternating.py`). New tests should be in a subdirectory to organize DN pair specific tests separately from other stage4 tests.

**IMPORTANT:** Write tests AFTER Task 1 completion to avoid mocking old signature.

**Test Files to Create:**

1. **`/Users/botfarmer/2dex/tests/stage4/dn_pair/test_dn_pair_csv_logging.py`:**
   ```python
   """Test CSV logging for DN pair trading bot."""

   import pytest
   from decimal import Decimal
   from unittest.mock import Mock, AsyncMock, patch
   from hedge.DN_pair_eth_sol_nado import DNPairBot

   @pytest.fixture
   def bot():
       config = {
           "target_notional": Decimal("100"),
           "iterations": 4,
           "sleep_time": 0,
           "eth_ticker": "ETH",
           "sol_ticker": "SOL",
           "eth_contract_id": "4",
           "sol_contract_id": "8",
           "eth_tick_size": Decimal("0.001"),
           "sol_tick_size": Decimal("0.1"),
           "mode": "ALTERNATING"
       }
       return DNPairBot(config)

   @pytest.mark.asyncio
   async def test_buy_first_build_csv_logging(bot):
       """Test BUY_FIRST BUILD logs correctly (Long ETH/Short SOL)."""
       # Mock clients with NEW signature (phase parameter)
       bot.eth_client = Mock()
       bot.sol_client = Mock()
       bot.eth_client.config.tick_size = Decimal("0.001")
       bot.sol_client.config.tick_size = Decimal("0.1")

       # Mock order results
       eth_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('0.05'),  # ~0.05 ETH @ $2000 = $100
           price=Decimal('2000')
       )
       sol_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('100'),  # 100 SOL @ $1 = $100
           price=Decimal('1')
       )

       bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
       bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
       bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
       bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))

       # Mock calculate_order_size_with_slippage
       bot.calculate_order_size_with_slippage = AsyncMock(
           side_effect=[(Decimal('0.05'), Decimal('5'), True), (Decimal('100'), Decimal('5'), True)]
       )

       with patch.object(bot, 'log_trade_to_csv') as mock_log:
           # Simulate order placement with NEW signature
           await bot.place_simultaneous_orders("buy", "sell", "BUILD")

           # Verify ETH buy logged as entry
           assert any(
               call[1]['side'] == "ETH-BUY" and call[1]['order_type'] == "entry"
               for call in mock_log.call_args_list
           ), "ETH BUY in BUILD phase should log as entry"

           # Verify SOL sell logged as entry
           assert any(
               call[1]['side'] == "SOL-SELL" and call[1]['order_type'] == "entry"
               for call in mock_log.call_args_list
           ), "SOL SELL in BUILD phase should log as entry"

   @pytest.mark.asyncio
   async def test_buy_first_unwind_csv_logging(bot):
       """Test BUY_FIRST UNWIND logs correctly (Sell ETH/Buy SOL)."""
       bot.eth_client = Mock()
       bot.sol_client = Mock()
       bot.eth_client.config.tick_size = Decimal("0.001")
       bot.sol_client.config.tick_size = Decimal("0.1")

       eth_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('0.05'),
           price=Decimal('2000')
       )
       sol_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('100'),
           price=Decimal('1')
       )

       bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
       bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
       bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
       bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
       bot.calculate_order_size_with_slippage = AsyncMock(
           side_effect=[(Decimal('0.05'), Decimal('5'), True), (Decimal('100'), Decimal('5'), True)]
       )

       with patch.object(bot, 'log_trade_to_csv') as mock_log:
           await bot.place_simultaneous_orders("sell", "buy", "UNWIND")

           # Verify ETH sell logged as exit
           assert any(
               call[1]['side'] == "ETH-SELL" and call[1]['order_type'] == "exit"
               for call in mock_log.call_args_list
           ), "ETH SELL in UNWIND phase should log as exit"

           # Verify SOL buy logged as exit
           assert any(
               call[1]['side'] == "SOL-BUY" and call[1]['order_type'] == "exit"
               for call in mock_log.call_args_list
           ), "SOL BUY in UNWIND phase should log as exit"

   @pytest.mark.asyncio
   async def test_sell_first_build_csv_logging(bot):
       """Test SELL_FIRST BUILD logs correctly (Short ETH/Long SOL)."""
       bot.eth_client = Mock()
       bot.sol_client = Mock()
       bot.eth_client.config.tick_size = Decimal("0.001")
       bot.sol_client.config.tick_size = Decimal("0.1")

       eth_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('0.05'),
           price=Decimal('2000')
       )
       sol_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('100'),
           price=Decimal('1')
       )

       bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
       bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
       bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
       bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
       bot.calculate_order_size_with_slippage = AsyncMock(
           side_effect=[(Decimal('0.05'), Decimal('5'), True), (Decimal('100'), Decimal('5'), True)]
       )

       with patch.object(bot, 'log_trade_to_csv') as mock_log:
           await bot.place_simultaneous_orders("sell", "buy", "BUILD")

           # Verify ETH sell logged as entry (SELL_FIRST BUILD)
           assert any(
               call[1]['side'] == "ETH-SELL" and call[1]['order_type'] == "entry"
               for call in mock_log.call_args_list
           ), "ETH SELL in SELL_FIRST BUILD should log as entry"

           # Verify SOL buy logged as entry (SELL_FIRST BUILD)
           assert any(
               call[1]['side'] == "SOL-BUY" and call[1]['order_type'] == "entry"
               for call in mock_log.call_args_list
           ), "SOL BUY in SELL_FIRST BUILD should log as entry"

   @pytest.mark.asyncio
   async def test_sell_first_unwind_csv_logging(bot):
       """Test SELL_FIRST UNWIND logs correctly (Buy ETH/Sell SOL)."""
       bot.eth_client = Mock()
       bot.sol_client = Mock()
       bot.eth_client.config.tick_size = Decimal("0.001")
       bot.sol_client.config.tick_size = Decimal("0.1")

       eth_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('0.05'),
           price=Decimal('2000')
       )
       sol_result = Mock(
           success=True,
           status='FILLED',
           filled_size=Decimal('100'),
           price=Decimal('1')
       )

       bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
       bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
       bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
       bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
       bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
       bot.calculate_order_size_with_slippage = AsyncMock(
           side_effect=[(Decimal('0.05'), Decimal('5'), True), (Decimal('100'), Decimal('5'), True)]
       )

       with patch.object(bot, 'log_trade_to_csv') as mock_log:
           await bot.place_simultaneous_orders("buy", "sell", "UNWIND")

           # Verify ETH buy logged as exit (SELL_FIRST UNWIND)
           assert any(
               call[1]['side'] == "ETH-BUY" and call[1]['order_type'] == "exit"
               for call in mock_log.call_args_list
           ), "ETH BUY in SELL_FIRST UNWIND should log as exit"

           # Verify SOL sell logged as exit (SELL_FIRST UNWIND)
           assert any(
               call[1]['side'] == "SOL-SELL" and call[1]['order_type'] == "exit"
               for call in mock_log.call_args_list
           ), "SOL SELL in SELL_FIRST UNWIND should log as exit"

   @pytest.mark.asyncio
   async def test_emergency_unwind_logging(bot):
       """Test emergency unwind logs to CSV."""
       bot.eth_client = Mock()
       bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0.05'))
       bot.eth_client.place_ioc_order = AsyncMock(
           return_value=Mock(success=True, status='FILLED', filled_size=Decimal('0.05'), price=Decimal('2000'))
       )
       bot.eth_client.config.contract_id = "4"

       with patch.object(bot, 'log_trade_to_csv') as mock_log:
           await bot.emergency_unwind_eth()

           # Verify logged as exit with EMERGENCY mode
           assert mock_log.called, "Emergency unwind should log to CSV"
           call_kwargs = mock_log.call_args[1]
           assert call_kwargs['order_type'] == "exit", "Emergency unwind should be exit"
           assert call_kwargs['mode'] == "EMERGENCY", "Should have EMERGENCY mode"
   ```

2. **`/Users/botfarmer/2dex/tests/stage4/dn_pair/test_dn_pair_alternating.py`:**
   ```python
   """Test alternating execution of DN pair bot."""

   import pytest
   from decimal import Decimal
   from unittest.mock import Mock, AsyncMock, patch
   from hedge.DN_pair_eth_sol_nado import DNPairBot

   @pytest.mark.asyncio
   async def test_alternating_execution_order():
       """Test that alternating strategy executes BUY_FIRST then SELL_FIRST."""
       config = {
           "target_notional": Decimal("100"),
           "iterations": 4,
           "sleep_time": 0,
           "mode": "ALTERNATING"
       }
       bot = DNPairBot(config)

       execution_order = []

       async def mock_buy_first():
           execution_order.append("BUY_FIRST")
           return True

       async def mock_sell_first():
           execution_order.append("SELL_FIRST")
           return True

       with patch.object(bot, 'execute_buy_first_cycle', side_effect=mock_buy_first):
           with patch.object(bot, 'execute_sell_first_cycle', side_effect=mock_sell_first):
               await bot.run_alternating_strategy()

       # Verify alternating pattern: BUY_FIRST, SELL_FIRST, BUY_FIRST, SELL_FIRST
       assert execution_order == ["BUY_FIRST", "SELL_FIRST", "BUY_FIRST", "SELL_FIRST"], \
           f"Expected alternating pattern, got {execution_order}"

   @pytest.mark.asyncio
   async def test_buy_first_cycle_phases():
       """Test BUY_FIRST executes BUILD then UNWIND."""
       config = {"target_notional": Decimal("100"), "iterations": 1}
       bot = DNPairBot(config)

       phases = []

       original_place = bot.place_simultaneous_orders
       async def track_phases(eth_dir, sol_dir, phase="BUILD"):
           phases.append(phase)
           return Mock(success=True, status='FILLED'), Mock(success=True, status='FILLED')

       bot.place_simultaneous_orders = track_phases

       await bot.execute_buy_first_cycle()

       assert phases == ["BUILD", "UNWIND"], f"BUY_FIRST should BUILD then UNWIND, got {phases}"

   @pytest.mark.asyncio
   async def test_sell_first_cycle_phases():
       """Test SELL_FIRST executes BUILD then UNWIND."""
       config = {"target_notional": Decimal("100"), "iterations": 1}
       bot = DNPairBot(config)

       phases = []

       async def track_phases(eth_dir, sol_dir, phase="BUILD"):
           phases.append(phase)
           return Mock(success=True, status='FILLED'), Mock(success=True, status='FILLED')

       bot.place_simultaneous_orders = track_phases

       await bot.execute_sell_first_cycle()

       assert phases == ["BUILD", "UNWIND"], f"SELL_FIRST should BUILD then UNWIND, got {phases}"
   ```

3. **`/Users/botfarmer/2dex/tests/stage4/dn_pair/test_dn_pair_hedging_balance.py`:**
   ```python
   """Test hedging balance calculation."""

   import pytest
   from decimal import Decimal
   from unittest.mock import Mock, AsyncMock
   from hedge.DN_pair_eth_sol_nado import DNPairBot

   @pytest.mark.asyncio
   async def test_hedging_balance_calculation():
       """Test that balanced order sizing ensures equal notionals."""
       config = {"target_notional": Decimal("100")}
       bot = DNPairBot(config)

       # Mock clients with BookDepth
       bot.eth_client = Mock()
       bot.sol_client = Mock()
       bot.eth_client.config.tick_size = Decimal("0.001")
       bot.sol_client.config.tick_size = Decimal("0.1")

       # Mock slippage estimates (NadoClient.estimate_slippage proxies to BookDepthHandler)
       bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))  # 5 bps
       bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))  # 5 bps

       eth_price = Decimal('2000')  # ETH $2000
       sol_price = Decimal('100')   # SOL $100

       eth_qty, sol_qty, actual_notional = await bot.calculate_balanced_order_sizes(
           eth_price, sol_price, "buy", "sell", max_slippage_bps=20
       )

       # Calculate actual notionals
       eth_notional = eth_qty * eth_price
       sol_notional = sol_qty * sol_price

       # Verify balance < 0.1%
       imbalance_pct = abs(eth_notional - sol_notional) / ((eth_notional + sol_notional) / 2) * 100
       assert imbalance_pct < 0.1, f"Hedging imbalance {imbalance_pct:.2f}% exceeds 0.1%"

       # Verify quantities are tick-aligned
       assert eth_qty % bot.eth_client.config.tick_size == 0, "ETH qty should align to tick size"
       assert sol_qty % bot.sol_client.config.tick_size == 0, "SOL qty should align to tick size"
   ```

**Acceptance Criteria:**
- All tests pass
- Coverage > 90% for modified code
- Tests verify CSV logging for all 4 scenarios
- Tests verify alternating execution pattern
- Tests verify hedging balance calculation
- Tests use NEW signature (with phase parameter)

---

## Commit Strategy

### Commit 1: Fix CSV Logging (Tasks 1-3)
```
fix(dn-pair): correct CSV logging for BUY_FIRST and SELL_FIRST

- Add phase parameter to place_simultaneous_orders()
- Fix order_type determination based on BUILD/UNWIND phase
- Add CSV logging to emergency_unwind_eth() (after line 591, before line 592)
- Add CSV logging to emergency_unwind_sol() (after line 615, before line 616)
- All emergency unwinds now log with order_type="exit", mode="EMERGENCY"
- CSV logging only occurs if result.filled_size > 0

Fixes:
- BUY_FIRST BUILD: ETH buy→entry, SOL sell→entry
- BUY_FIRST UNWIND: ETH sell→exit, SOL buy→exit
- SELL_FIRST BUILD: ETH sell→entry, SOL buy→entry
- SELL_FIRST UNWIND: ETH buy→exit, SOL sell→exit

File: hedge/DN_pair_eth_sol_nado.py
Lines: 437-441 (signature), 522-541 (logging), 573-619 (emergency)
```

### Commit 2: Implement Hedging Balance (Task 4)
```
feat(dn-pair): add BookDepth-based hedging balance

- Add calculate_balanced_order_sizes() method
- Binary search for maximum balanced notional both legs can fill
- Verify BookDepth connection before using liquidity data
- Add final validation that returned quantities meet slippage limits
- Return (0, 0, 0) if validation fails to prevent violating slippage limits
- Log actual notionals for both legs

Ensures < 0.1% imbalance between ETH and SOL notionals.

References:
- nado.py:209-233 (NadoClient.estimate_slippage proxy method)
- nado_bookdepth_handler.py:167-234 (BookDepthHandler.estimate_slippage implementation)
- nado.py:869 (tick_size assignment in connect_websockets)

Access patterns:
- Tick size: self.eth_client.config.tick_size
- Slippage: await self.eth_client.estimate_slippage(side, qty)
- BookDepth: self.eth_client.get_bookdepth_handler()

File: hedge/DN_pair_eth_sol_nado.py
Lines: ~406-500 (new method), ~464-475 (updated), ~500-520 (verification)
```

### Commit 3: Add Metrics Collection (Task 5)
```
feat(dn-pair): add cycle metrics collection

- Add CycleMetrics dataclass
- Collect slippage, fill rate, notional imbalance per cycle
- Export metrics to CSV on completion
- Track emergency unwind events
- Initialize cycle_metrics_list in __init__

File: hedge/DN_pair_eth_sol_nado.py
Lines: ~74-100 (dataclass), ~150-170 (init), ~520-550 (collection), ~275-295 (export)
```

### Commit 4: Add Test Suite (Task 6)
```
test(dn-pair): add comprehensive test suite

- test_dn_pair_csv_logging.py: verify CSV logging for all scenarios
- test_dn_pair_alternating.py: verify alternating execution pattern
- test_dn_pair_hedging_balance.py: verify balance calculation

Tests use NEW signature with phase parameter.
Directory: tests/stage4/dn_pair/

Coverage > 90% for modified code.
```

---

## Success Criteria

### Functional Requirements
- CSV logs correctly identify entry/exit for both BUY_FIRST and SELL_FIRST
- Emergency unwind operations are logged with order_type="exit", mode="EMERGENCY"
- Hedging imbalance < 0.1% between ETH and SOL notionals
- Alternating execution verified: even iterations=BUY_FIRST, odd=SELL_FIRST

### Quality Requirements
- Test coverage > 90% for modified code
- All tests pass
- No regression in existing functionality
- Performance degradation < 5%

### Data Requirements
- CSV format unchanged (backward compatible)
  - Fields: exchange, timestamp, side, price, quantity, order_type, mode
  - New mode value: "EMERGENCY"
- Metrics exported for analysis
- All trading cycles logged

### Risk Mitigation
- BookDepth unavailable → fall back to target notional with warning
- Slippage too high → reduce quantity but maintain balance
- Emergency unwind → always log and close positions
- Final validation → verify returned quantities meet slippage limits

---

## Risk Mitigation Strategies

### Risk 1: BookDepth Data Unavailable
**Mitigation:**
- Check `estimate_slippage() == 999999` to detect no data
- Fall back to target notional calculation
- Log warning when falling back
- Graceful degradation, no failures

### Risk 2: Slippage Exceeds Limits
**Mitigation:**
- Binary search for maximum fillable quantity
- Reduce both legs proportionally to maintain balance
- Log when quantity is reduced
- Final validation step ensures returned quantities meet slippage limits
- If validation fails, return (0, 0, 0) to prevent executing orders that violate limits
- Caller must check for zero quantities and handle appropriately (skip cycle, reduce target size)

### Risk 3: Emergency Unwind Fails
**Mitigation:**
- Log attempt even if order fails
- Set 100ms timeout on IOC orders
- Force close positions in force_close_all_positions()
- Multiple retry attempts with aggressive pricing

### Risk 4: Test Coverage Gaps
**Mitigation:**
- Use pytest-asyncio for async test support
- Mock all external dependencies (NadoClient, WebSocket)
- Parameterized tests for all scenarios
- Integration tests with testnet
- Write tests AFTER Task 1 to use correct signature

### Risk 5: Performance Impact
**Mitigation:**
- Binary search limited to 10 iterations (fast)
- All BookDepth calls are async (non-blocking)
- Metrics collection is lightweight (dataclass)
- No additional synchronous I/O

---

## Implementation Order

### Phase 1: Critical Bug Fixes (Days 1-2)
1. Task 1: Fix CSV Logging in place_simultaneous_orders()
2. Task 2: Add CSV Logging to emergency_unwind_eth()
3. Task 3: Add CSV Logging to emergency_unwind_sol()
4. Manual testing with 2-3 iterations
5. Commit 1

### Phase 2: Hedging Balance (Days 3-4)
1. Task 4: Implement calculate_balanced_order_sizes()
2. Update place_simultaneous_orders() to use balanced sizing
3. Add verify_bookdepth_connection()
4. Add final validation step
5. Manual testing with bookdepth data
6. Commit 2

### Phase 3: Metrics & Tests (Days 5-6)
1. Task 5: Add CycleMetrics dataclass and collection
2. Export metrics functionality
3. Task 6: Create test suite (AFTER Task 1 complete)
4. Run all tests
5. Commits 3 & 4

### Phase 4: Verification (Day 7)
1. End-to-end testing with 10 iterations
2. Verify CSV logs are correct
3. Verify hedging balance < 0.1%
4. Performance benchmarking
5. Documentation updates

---

## Testing Plan

### Unit Tests (pytest)
```bash
# Run all DN pair tests
pytest tests/stage4/dn_pair/test_dn_pair_*.py -v

# Run with coverage
pytest tests/stage4/dn_pair/test_dn_pair_*.py --cov=hedge.DN_pair_eth_sol_nado --cov-report=html

# Specific test
pytest tests/stage4/dn_pair/test_dn_pair_csv_logging.py::test_sell_first_build_csv_logging -v
```

### Integration Tests (testnet)
```bash
# Small scale test (2 iterations)
python hedge/DN_pair_eth_sol_nado.py --size 100 --iter 2

# Verify CSV output
cat logs/dn_pair_eth_sol_nado_trades_*.csv

# Check metrics
cat logs/cycle_metrics_*.csv
```

### Manual Verification Checklist
- [ ] BUY_FIRST BUILD: CSV shows ETH-BUY entry, SOL-SELL entry
- [ ] BUY_FIRST UNWIND: CSV shows ETH-SELL exit, SOL-BUY exit
- [ ] SELL_FIRST BUILD: CSV shows ETH-SELL entry, SOL-BUY entry
- [ ] SELL_FIRST UNWIND: CSV shows ETH-BUY exit, SOL-SELL exit
- [ ] Emergency unwind: CSV shows order_type=exit, mode=EMERGENCY
- [ ] Hedging balance: ETH notional ≈ SOL notional (within 0.1%)
- [ ] Alternating: Iteration 0=BUY_FIRST, 1=SELL_FIRST, 2=BUY_FIRST, 3=SELL_FIRST
- [ ] Metrics: All cycles exported to cycle_metrics_*.csv
- [ ] Validation: Final quantities meet slippage limits

---

## Rollback Plan

If critical issues arise after deployment:

1. **Revert Commits:**
   ```bash
   git revert <commit-hash-4> <commit-hash-3> <commit-hash-2> <commit-hash-1>
   ```

2. **Verify Rollback:**
   - Run 2 iteration test
   - Check CSV logs
   - Confirm positions close correctly

3. **Fix Issues:**
   - Create bug fix branch
   - Address issues separately
   - Re-apply with additional testing

---

## Post-Implementation

### Monitoring
- Monitor CSV logs for correctness
- Track hedging imbalance metrics
- Alert on emergency unwind frequency
- Monitor slippage and fill rates

### Documentation
- Update README with new CSV format (EMERGENCY mode)
- Document BookDepth integration
- Add metrics reference guide
- Update runbook for troubleshooting

### Future Improvements
- Dynamic notional sizing based on volatility
- Multi-ticker pair trading
- Advanced slippage prediction models
- Real-time PnL dashboard

---

## References

### Code References
- CSV Format: `_initialize_csv_file()` method at Lines 212-231
- CSV Logging: `log_trade_to_csv()` method at Lines 233-247
- Emergency ETH: `emergency_unwind_eth()` at Lines 573-595 (add CSV logging after line 591)
- Emergency SOL: `emergency_unwind_sol()` at Lines 597-619 (add CSV logging after line 615)
- Order Placement: `place_simultaneous_orders()` at Lines 437-546
- Callers: Lines 630, 642, 699, 709

### External References
- NadoClient.estimate_slippage: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py` Lines 213-233 (async proxy method)
- BookDepthHandler.estimate_slippage: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_bookdepth_handler.py` Lines 167-234 (implementation)
- NadoClient.get_bookdepth_handler: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado.py` Line 209
- tick_size Access: `self.eth_client.config.tick_size` (assigned in nado.py line 869 within connect_websockets method)
- Test Directory: `/Users/botfarmer/2dex/tests/stage4/` (existing tests)

### Critical Issues Fixed (from Critic Review)
1. **tick_size Reference**: Clarified that line 869 is in connect_websockets() method, but tick_size is accessed via `self.eth_client.config.tick_size`
2. **Binary Search Validation Bug**: Fixed logic to return (0, 0, 0) when validation fails instead of returning quantities that violate slippage limits
3. **Emergency Unwind CSV Location**: Specified exact location - add CSV logging AFTER line 591 for ETH, AFTER line 615 for SOL, with `if result.filled_size > 0` check
4. **BookDepth Method Access Pattern**: Documented that NadoClient has estimate_slippage() proxy method (Lines 213-233) which calls BookDepthHandler, so correct access is `await self.eth_client.estimate_slippage(side, qty)`
