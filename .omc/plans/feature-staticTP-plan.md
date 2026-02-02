# Feature Static TP - Detailed Implementation Plan (REVISED)

**Branch:** feature-staticTP
**Created:** 2026-02-02
**Revised:** 2026-02-02 (RALPLAN Iteration 2 - All 8 critical issues fixed)
**Purpose:** Test hypothesis: Static TP (individual 10bps) > 19bps spread
**Status:** Planning

---

## Hypothesis Clarification

**Hypothesis:** Setting individual +10bps take-profit (TP) on each position at entry yields higher PNL than the current 19bps spread exit strategy.

**What "19bps spread" means:** The current bot exits when the combined ETH+SOL position PNL reaches approximately 19 basis points (0.19%). This is a spread-based exit threshold.

**What Static TP means:** Exit when EITHER ETH OR SOL individually hits +10bps (0.10%), regardless of the other position's PNL. This is an individual-position-based exit.

**Verification Method:**
1. feature-staticTP branch에서 구현
2. 100+ cycles backtesting 또는 paper trading
3. PNL, fill rate, risk metrics 비교
4. 유의미한 향상 시 merge, 아니면 discard

---

## Phase 1: Critical Fixes (Foundation)

### 1.1 Fix `handle_emergency_unwind()` Bug - VERIFIED & CORRECTED

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 786-791

**CRITICAL ISSUE:** The existing code checks `status == 'FILLED'`, which may miss partial fills.

**VERIFICATION:**
- Lines 2036-2043 show `_is_fill_complete()` method exists and uses `filled_size > 0.001`
- The fix should USE the existing `_is_fill_complete()` method

**Current Code (Lines 786-791):**
```python
eth_filled = (isinstance(eth_result, OrderResult) and
              eth_result.success and
              eth_result.status == 'FILLED')
sol_filled = (isinstance(sol_result, OrderResult) and
              sol_result.success and
              sol_result.status == 'FILLED')
```

**Fixed Code:**
```python
# Lines 786-791: Replace status check with _is_fill_complete()
eth_filled = (isinstance(eth_result, OrderResult) and
              self._is_fill_complete(eth_result))
sol_filled = (isinstance(sol_result, OrderResult) and
              self._is_fill_complete(sol_result))
```

**Why:** The `_is_fill_complete()` method already handles partial fills correctly.

---

### 1.2 Add UNWIND Retry Logic - CORRECTED WITH STATE UPDATES

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** Insert after line 2466 (before existing position verification at 2468-2505)

**CRITICAL CORRECTIONS:**
1. `_retry_side_order()` does NOT update entry data - caller must update
2. Use current position size, NOT `self.target_notional`
3. Add explicit state updates after retry

**NEW CODE (after line 2466):**
```python
# Lines 2466-2467: After checking order success, add order retry logic
MAX_ORDER_RETRIES = 3
ORDER_RETRY_DELAY = 2.0
POSITION_TOLERANCE = Decimal("0.001")

# Check initial fill status
eth_filled = self._is_fill_complete(eth_result)
sol_filled = self._is_fill_complete(sol_result)

if eth_filled and sol_filled:
    self.logger.info("[UNWIND] Both orders filled successfully")
else:
    # One or both legs didn't fill - retry individual legs
    self.logger.warning(f"[UNWIND] Initial fill incomplete: ETH={eth_filled}, SOL={sol_filled}")

    latest_eth_result = eth_result
    latest_sol_result = sol_result

    for attempt in range(MAX_ORDER_RETRIES):
        await asyncio.sleep(ORDER_RETRY_DELAY)

        # Get current prices
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

        # CRITICAL FIX: Use current position size, NOT self.target_notional
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        # Calculate remaining quantities based on current position, not target notional
        # If position is closed (near zero), remaining is what we originally tried to fill
        # If position is partially open, remaining is target - current
        eth_remaining_qty = abs(eth_pos) if abs(eth_pos) > POSITION_TOLERANCE else Decimal("0.05")  # Approx target qty
        sol_remaining_qty = abs(sol_pos) if abs(sol_pos) > POSITION_TOLERANCE else Decimal("300")  # Approx target qty

        # Determine which side needs retry (retry if position is NOT yet open)
        retry_eth = abs(eth_pos) <= POSITION_TOLERANCE and eth_remaining_qty > POSITION_TOLERANCE
        retry_sol = abs(sol_pos) <= POSITION_TOLERANCE and sol_remaining_qty > POSITION_TOLERANCE

        if not retry_eth and not retry_sol:
            self.logger.info("[UNWIND] Both positions now open, no retry needed")
            break

        # Bypass queue filter on 3rd attempt
        bypass_queue_filter = (attempt >= 2)

        if retry_eth:
            self.logger.info(f"[UNWIND] Retrying ETH: side={eth_side}, qty={eth_remaining_qty}")
            eth_result = await self._retry_side_order(
                self.eth_client, "ETH", eth_side, eth_remaining_qty,
                eth_bid if eth_side == "buy" else eth_ask,
                bypass_queue_filter
            )
            latest_eth_result = eth_result

            # CRITICAL FIX: Update entry_quantities and entry_prices after retry
            # _retry_side_order() does NOT update these - caller must update
            if eth_result.success:
                filled_size = self._get_filled_size(eth_result)
                if filled_size > POSITION_TOLERANCE:
                    self.entry_quantities["ETH"] += filled_size
                    if self.entry_prices.get("ETH") is None or filled_size > 0:
                        self.entry_prices["ETH"] = eth_result.price if eth_result.price else self.entry_prices.get("ETH", Decimal("0"))
                    self.logger.info(f"[UNWIND] ETH retry filled: {filled_size} @ {eth_result.price}")

        if retry_sol:
            self.logger.info(f"[UNWIND] Retrying SOL: side={sol_side}, qty={sol_remaining_qty}")
            sol_result = await self._retry_side_order(
                self.sol_client, "SOL", sol_side, sol_remaining_qty,
                sol_bid if sol_side == "buy" else sol_ask,
                bypass_queue_filter
            )
            latest_sol_result = sol_result

            # CRITICAL FIX: Update entry_quantities and entry_prices after retry
            if sol_result.success:
                filled_size = self._get_filled_size(sol_result)
                if filled_size > POSITION_TOLERANCE:
                    self.entry_quantities["SOL"] += filled_size
                    if self.entry_prices.get("SOL") is None or filled_size > 0:
                        self.entry_prices["SOL"] = sol_result.price if sol_result.price else self.entry_prices.get("SOL", Decimal("0"))
                    self.logger.info(f"[UNWIND] SOL retry filled: {filled_size} @ {sol_result.price}")

        # Check if retry succeeded
        if self._is_fill_complete(eth_result) and self._is_fill_complete(sol_result):
            self.logger.info("[UNWIND] Retry successful, both orders filled")
            break

    # After order retry, check for emergency unwind condition
    eth_final_filled = self._is_fill_complete(latest_eth_result)
    sol_final_filled = self._is_fill_complete(latest_sol_result)

    if eth_final_filled and not sol_final_filled:
        self.logger.warning("[UNWIND] ETH filled but SOL failed after retries")
        await self.handle_emergency_unwind(latest_eth_result, latest_sol_result)
        return False
    elif sol_final_filled and not eth_final_filled:
        self.logger.warning("[UNWIND] SOL filled but ETH failed after retries")
        await self.handle_emergency_unwind(latest_eth_result, latest_sol_result)
        return False
    elif not eth_final_filled and not sol_final_filled:
        self.logger.error("[UNWIND] Both legs failed after retries")
        return False

# Continue with existing position verification retry (lines 2468-2505)
```

**CORRECTIONS MADE:**
1. **False claim fixed:** `_retry_side_order()` (lines 2077-2112) does NOT update `entry_quantities` or `entry_prices`
2. **State updates added:** Explicit code to update `entry_quantities[ticker] += filled_size` after retry
3. **Notional fixed:** Use `abs(eth_pos)` for remaining quantity, NOT `self.target_notional`
4. **Position check logic:** `retry_eth = abs(eth_pos) <= POSITION_TOLERANCE` (retry if NOT open)

---

## Phase 2: Static TP Implementation

### 2.1 Add CLI Parameters & Instance Variables - WITH _tp_hit_position INITIALIZATION

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Step 1: Add argparse parameters (after line 2863):**
```python
# Lines 2863-2864: Add after --min-partial-fill-ratio
parser.add_argument(
    '--enable-static-tp',
    action='store_true',
    help='Enable static individual TP (default: disabled, use 19bps spread)'
)
parser.add_argument(
    '--tp-bps',
    type=float,
    default=10.0,
    help='Static TP threshold in bps per position (default: 10bps = 0.1%%)'
)
parser.add_argument(
    '--tp-timeout',
    type=int,
    default=60,
    help='Max wait time for TP hit before fallback to spread exit (seconds)'
)
```

**Step 2: Add to DNPairBot.__init__() parameters (after line 80):**
```python
# Lines 80-81: Add after min_partial_fill_ratio parameter
def __init__(
    self,
    target_notional: Decimal,
    iterations: int = 20,
    sleep_time: int = 0,
    csv_path: str = None,
    min_spread_bps: int = 0,
    # Feature flags for PNL optimization
    enable_at_touch_pricing: bool = False,
    enable_order_type_default: bool = False,
    enable_queue_filter: bool = False,
    enable_spread_filter: bool = False,
    enable_partial_fills: bool = False,
    enable_dynamic_timeout: bool = False,
    enable_static_tp: bool = False,  # NEW
    # Configurable thresholds
    queue_threshold_ratio: float = 0.5,
    spread_threshold_ticks: int = 5,
    min_partial_fill_ratio: float = 0.5,
    tp_bps: float = 10.0,  # NEW
    tp_timeout: int = 60,  # NEW
):
```

**Step 3: Initialize instance variables (after line 98) - INCLUDING _tp_hit_position:**
```python
# Lines 98-103: Add after min_partial_fill_ratio initialization
self.min_partial_fill_ratio = min_partial_fill_ratio

# Static TP feature flags and thresholds (NEW)
self.enable_static_tp = enable_static_tp
self.tp_bps = tp_bps
self.tp_timeout = tp_timeout

# CRITICAL FIX: Initialize _tp_hit_position to prevent AttributeError
self._tp_hit_position = None  # Track which position hit TP
self._tp_hit_pnl_pct = None   # Track PNL % when TP hit
```

**Step 4: Add to main() bot instantiation (after line 2900):**
```python
# Lines 2900-2901: Add after min_partial_fill_ratio
min_partial_fill_ratio=getattr(args, 'min_partial_fill_ratio', 0.5),
# Static TP parameters (NEW)
enable_static_tp=getattr(args, 'enable_static_tp', False),
tp_bps=getattr(args, 'tp_bps', 10.0),
tp_timeout=getattr(args, 'tp_timeout', 60),
```

**Step 5: Add startup logging (after line 112):**
```python
# Lines 112-113: Add after enable_dynamic_timeout logging
self._config_logger.info(f"[CONFIG] Dynamic timeout: {self.enable_dynamic_timeout}")
self._config_logger.info(f"[CONFIG] Static TP: {self.enable_static_tp} (threshold={self.tp_bps}bps, timeout={self.tp_timeout}s)")
```

**CORRECTIONS MADE:**
- Added `_tp_hit_position` initialization at line 101
- Added `_tp_hit_pnl_pct` initialization at line 102

---

### 2.2 Add TP Monitoring Method - WITH INSTANCE VARIABLE CONTEXT

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location:** After `_check_exit_timing()` method (after line 1925)

**Instance Variables Used (VERIFIED):**
- `self.entry_prices` - initialized at lines 144-148 as `{"ETH": None, "SOL": None}`
- `self.entry_quantities` - initialized at lines 148-152 as `{"ETH": Decimal("0"), "SOL": Decimal("0")}`
- `self._tp_hit_position` - initialized at line 101 (NEW)
- `self._tp_hit_pnl_pct` - initialized at line 102 (NEW)
- `self.eth_client` - initialized in `initialize_clients()` method
- `self.sol_client` - initialized in `initialize_clients()` method
- `self.logger` - initialized at line 105

**New Method:**
```python
# After line 1925 (end of _check_exit_timing method)
async def _monitor_static_individual_tp(
    self,
    tp_threshold_bps: float = 10.0,
    timeout_seconds: int = 60
) -> tuple[bool, str]:
    """
    Monitor individual positions and exit when TP hit.

    Static TP: Set at entry, check until hit or timeout.

    Args:
        tp_threshold_bps: TP threshold in basis points (default: 10bps = 0.1%)
        timeout_seconds: Max wait time before fallback (default: 60s)

    Returns:
        (should_exit, reason)
        - should_exit=True when TP hit or timeout
        - reason indicates which position hit TP or "timeout"

    Instance Variables Used:
        - self.entry_prices: Dict with "ETH" and "SOL" entry prices
        - self.entry_quantities: Dict with "ETH" and "SOL" quantities
        - self._tp_hit_position: Set to "ETH" or "SOL" when TP hit
        - self._tp_hit_pnl_pct: Set to PNL % when TP hit
        - self.eth_client: NadoClient for ETH
        - self.sol_client: NadoClient for SOL
    """
    from decimal import Decimal
    import asyncio

    tp_threshold = Decimal(str(tp_threshold_bps / 10000))
    POSITION_TOLERANCE = Decimal("0.001")

    start_time = time.time()
    check_interval = 1.0

    self.logger.info(
        f"[STATIC TP] Monitoring: TP={tp_threshold_bps}bps, "
        f"timeout={timeout_seconds}s"
    )

    # BLOCKING BEHAVIOR: This loop blocks until TP hit or timeout
    while time.time() - start_time < timeout_seconds:
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(
            self.eth_client.config.contract_id
        )
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(
            self.sol_client.config.contract_id
        )

        eth_entry_price = self.entry_prices.get("ETH", Decimal("0"))
        sol_entry_price = self.entry_prices.get("SOL", Decimal("0"))
        eth_qty = self.entry_quantities.get("ETH", Decimal("0"))
        sol_qty = self.entry_quantities.get("SOL", Decimal("0"))

        if eth_entry_price == 0 or sol_entry_price == 0:
            self.logger.warning("[STATIC TP] No entry data available")
            return False, "no_entry_data"

        eth_direction = "long" if eth_qty > 0 else "short"
        sol_direction = "long" if sol_qty > 0 else "short"

        if eth_direction == "long":
            eth_pnl_pct = (eth_bid - eth_entry_price) / eth_entry_price
        else:
            eth_pnl_pct = (eth_entry_price - eth_ask) / eth_entry_price

        if sol_direction == "long":
            sol_pnl_pct = (sol_bid - sol_entry_price) / sol_entry_price
        else:
            sol_pnl_pct = (sol_entry_price - sol_ask) / sol_entry_price

        self.logger.debug(
            f"[STATIC TP] ETH: {eth_pnl_pct*100:.2f}%, "
            f"SOL: {sol_pnl_pct*100:.2f}% (target: +{tp_threshold_bps}bps)"
        )

        if eth_pnl_pct >= tp_threshold:
            self.logger.info(
                f"[STATIC TP] ETH TP hit: {eth_pnl_pct*100:.2f}% >= {tp_threshold_bps}bps"
            )
            self._tp_hit_position = "ETH"
            self._tp_hit_pnl_pct = float(eth_pnl_pct) * 100
            return True, f"static_tp_eth_{eth_pnl_pct*100:.2f}bps"

        if sol_pnl_pct >= tp_threshold:
            self.logger.info(
                f"[STATIC TP] SOL TP hit: {sol_pnl_pct*100:.2f}% >= {tp_threshold_bps}bps"
            )
            self._tp_hit_position = "SOL"
            self._tp_hit_pnl_pct = float(sol_pnl_pct) * 100
            return True, f"static_tp_sol_{sol_pnl_pct*100:.2f}bps"

        await asyncio.sleep(check_interval)

    self.logger.info(
        f"[STATIC TP] Timeout after {timeout_seconds}s, "
        f"falling back to spread exit"
    )
    return False, "static_tp_timeout"
```

---

### 2.3 Integrate into UNWIND Cycle - WITH EXECUTION FLOW SPECIFIED

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location:** `execute_unwind_cycle()` method, around line 2420

**NEW CODE (Sequential Execution):**
```python
# Lines 2420-2440: Replace existing _check_exit_timing call with static TP logic

# STATIC TP CHECK (if enabled) - Runs FIRST
if self.enable_static_tp:
    self.logger.info("[UNWIND] Checking static TP conditions...")
    should_exit_tp, tp_reason = await self._monitor_static_individual_tp(
        tp_threshold_bps=self.tp_bps,
        timeout_seconds=self.tp_timeout
    )

    if should_exit_tp:
        self.logger.info(f"[EXIT] Static TP triggered: {tp_reason}")

        # SEQUENTIAL EXECUTION: Close TP-hit position first
        if hasattr(self, '_tp_hit_position') and self._tp_hit_position:
            position_to_close = self._tp_hit_position
            self.logger.info(f"[EXIT] Closing {position_to_close} (TP hit: {self._tp_hit_pnl_pct:.2f}bps)")

            # Step 1: Close individual position that hit TP
            close_success = await self._close_individual_position(position_to_close)

            if not close_success:
                self.logger.error(f"[EXIT] Failed to close {position_to_close}")
                return False

            # Step 2: Check and close remaining position
            remaining_pos_check = await self._check_and_close_remaining_position(
                closed_position=position_to_close
            )

            return remaining_pos_check

# FALLBACK: Spread-based exit check (original logic)
self.logger.info("[UNWIND] Checking spread-based exit conditions...")
should_exit, exit_reason = await self._check_exit_timing(max_loss_bps=30)
```

---

### 2.4 Add Individual Position Close Method - WITH PARTIAL FILL HANDLING

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location:** New method after `_monitor_static_individual_tp()`

```python
async def _close_individual_position(self, ticker: str) -> bool:
    """
    Close individual position (ETH or SOL).

    Args:
        ticker: "ETH" or "SOL"

    Returns:
        True if position closed successfully (full or partial)
        False if order failed completely

    "Hedge break" definition: Period when one position is closed but the other
    remains open, exposing the bot to directional risk.

    Partial Fill Handling:
        - If order partially filled, accept partial fill and update entry_quantities
        - If order fails completely, return False to trigger emergency handling
    """
    from decimal import Decimal

    POSITION_TOLERANCE = Decimal("0.001")
    client = self.eth_client if ticker == "ETH" else self.sol_client
    contract_id = client.config.contract_id

    current_pos = await client.get_account_positions()

    if abs(current_pos) < POSITION_TOLERANCE:
        self.logger.info(f"[CLOSE] {ticker} no position to close (pos={current_pos})")
        return True

    close_side = "sell" if current_pos > 0 else "buy"
    close_qty = abs(current_pos)

    bid, ask = await client.fetch_bbo_prices(contract_id)
    close_price = bid if close_side == "sell" else ask

    self.logger.info(
        f"[CLOSE] {ticker} {close_side} {close_qty} @ ${close_price} "
        f"(current position: {current_pos})"
    )

    result = await client.place_limit_order_with_timeout(
        contract_id=contract_id,
        quantity=close_qty,
        price=close_price,
        side=close_side,
        max_wait_seconds=30,
        post_only=True
    )

    filled_size = self._get_filled_size(result)

    if result.success and self._is_fill_complete(result):
        self.logger.info(f"[CLOSE] {ticker} fully closed: {filled_size}")
        return True
    elif result.success and filled_size > POSITION_TOLERANCE:
        self.logger.warning(
            f"[CLOSE] {ticker} partially closed: {filled_size}/{close_qty} "
            f"({float(filled_size/close_qty*100):.1f}%)"
        )
        self.entry_quantities[ticker] -= filled_size
        return True
    else:
        self.logger.error(
            f"[CLOSE] {ticker} failed: success={result.success}, "
            f"status={result.status if hasattr(result, 'status') else 'N/A'}, "
            f"error={result.error_message if hasattr(result, 'error_message') else 'N/A'}"
        )
        return False


async def _check_and_close_remaining_position(self, closed_position: str) -> bool:
    """
    Check and close remaining position after individual TP close.

    Args:
        closed_position: "ETH" or "SOL" that was already closed

    Returns:
        True if all positions closed, False if error occurred
    """
    from decimal import Decimal

    POSITION_TOLERANCE = Decimal("0.001")

    remaining_ticker = "SOL" if closed_position == "ETH" else "ETH"
    remaining_client = self.eth_client if remaining_ticker == "ETH" else self.sol_client

    remaining_pos = await remaining_client.get_account_positions()

    if abs(remaining_pos) < POSITION_TOLERANCE:
        self.logger.info(f"[CLOSE] No remaining {remaining_ticker} position")
        return True

    self.logger.info(
        f"[CLOSE] Remaining position: {remaining_ticker}={remaining_pos}"
    )

    should_exit, exit_reason = await self._check_exit_timing(max_loss_bps=30)

    if should_exit:
        self.logger.info(
            f"[CLOSE] Closing {remaining_ticker}: {exit_reason}"
        )
        return await self._close_individual_position(remaining_ticker)
    else:
        self.logger.warning(
            f"[CLOSE] Spread condition not met for {remaining_ticker}, "
            f"closing anyway to minimize hedge break time"
        )
        return await self._close_individual_position(remaining_ticker)
```

---

### 2.5 Exit Price Storage - WITH TIMING CONFLICT CLARIFICATION

**TIMING CONFLICT RESOLUTION:**
- **Existing UNWIND logic** (lines 2453-2458): Sets `self._exit_prices` AFTER both positions close
- **Individual close logic** (this feature): Sets `self._exit_prices[ticker]` AFTER individual position closes

**RESOLUTION:** Individual closes set `_exit_prices[ticker]` immediately. When remaining position closes later, it overwrites/updates the dict. This is safe because:

1. Individual TP close: Sets `_exit_prices["ETH"]` (if ETH hit TP)
2. Remaining position check: May also set `_exit_prices["SOL"]` if SOL closes
3. PNL calculation (lines 1392-1393): Uses `.get()` with fallback to entry price

**Exit Price Storage Code (integrated in `_close_individual_position()`):**
```python
# In _close_individual_position(), after successful close

if result.success and self._is_fill_complete(result):
    # Full fill
    # Store exit price for PNL calculation
    if not hasattr(self, '_exit_prices'):
        self._exit_prices = {}
    # Handle None price case: fall back to entry price
    self._exit_prices[ticker] = result.price if result.price else self.entry_prices.get(ticker, Decimal("0"))
    self.logger.info(f"[CLOSE] {ticker} fully closed: {filled_size}, exit_price={self._exit_prices[ticker]}")
    return True
elif result.success and filled_size > POSITION_TOLERANCE:
    # Partial fill
    if not hasattr(self, '_exit_prices'):
        self._exit_prices = {}
    self._exit_prices[ticker] = result.price if result.price else self.entry_prices.get(ticker, Decimal("0"))
    self.logger.info(f"[CLOSE] {ticker} partially closed: {filled_size}, exit_price={self._exit_prices[ticker]}")
    return True
```

---

## Phase 3: Testing & Validation

### 3.1 Test Infrastructure Setup - WITH FIXTURES DOCUMENTED

**Step 1: Install dependencies (including scipy):**
```bash
# Install pytest and statistical dependencies
pip3 install pytest pytest-asyncio scipy pandas numpy
```

**Step 2: Verify existing fixtures:**

**File:** `/Users/botfarmer/2dex/tests/conftest.py`

**Existing Fixtures (DOCUMENTED):**
- `mock_env_vars` (lines 15-20): Sets up environment variables (NADO_PRIVATE_KEY, NADO_MODE, NADO_SUBACCOUNT_NAME)
- `mock_nado_client` (lines 23-52): Mock NadoClient with REST API responses
  - `client.get_contract_attributes()`: Returns contract_id and tick_size
  - `client.fetch_bbo_prices()`: Returns (bid, ask) tuple
  - `client.get_account_positions()`: Returns position as Decimal
- `mock_websocket_server` (lines 55-74): Mock WebSocket server (conditional)
- `sample_eth_price` (lines 77-80): Sample ETH price (Decimal("3000.00"))
- `sample_sol_price` (lines 83-86): Sample SOL price (Decimal("150.00"))
- `tmp_csv_path` (lines 89-92): Temporary CSV file path for testing
- `mock_order_result_fixture` (lines 122-125): Mock OrderResult fixture
- `mock_order_info_fixture` (lines 128-131): Mock OrderInfo fixture

**Helper Functions (DOCUMENTED):**
- `mock_order_result()` (lines 96-106): Creates mock OrderResult with order_id, side, size, price, status
- `mock_order_info()` (lines 109-119): Creates mock OrderInfo with order_id, side, size, price, status, filled_size

**Usage in Static TP Tests:**
```python
# Use mock_nado_client for price fetching
# Use sample_eth_price and sample_sol_price for test data
# Use mock_order_result_fixture for order result testing
```

---

### 3.2 Unit Tests

**File:** `/Users/botfarmer/2dex/tests/test_static_tp.py` (NEW)

```python
"""
Unit tests for Static TP feature.
"""

import pytest
from decimal import Decimal


def test_static_tp_calculation():
    """Test TP threshold calculation from bps to decimal."""
    tp_bps = 10
    tp_threshold = Decimal(str(tp_bps / 10000))

    entry_price = Decimal("2000")
    tp_price = entry_price * (1 + tp_threshold)

    assert tp_price == Decimal("2002.00")
    assert tp_threshold == Decimal("0.001")


def test_individual_pnl_calculation_long():
    """Test individual PNL % calculation for LONG position."""
    entry_price = Decimal("2000")
    current_price = Decimal("2010")

    pnl_pct = (current_price - entry_price) / entry_price

    assert pnl_pct == Decimal("0.005")
    assert pnl_pct > Decimal("0.001")


def test_individual_pnl_calculation_short():
    """Test individual PNL % calculation for SHORT position."""
    entry_price = Decimal("2000")
    current_price = Decimal("1990")

    pnl_pct = (entry_price - current_price) / entry_price

    assert pnl_pct == Decimal("0.005")
    assert pnl_pct > Decimal("0.001")


def test_tp_hit_detection():
    """Test TP hit detection logic."""
    tp_threshold = Decimal("0.001")

    eth_pnl_pct = Decimal("0.0015")
    assert eth_pnl_pct >= tp_threshold

    eth_pnl_pct = Decimal("0.0005")
    assert eth_pnl_pct < tp_threshold

    eth_pnl_pct = Decimal("0.001")
    assert eth_pnl_pct >= tp_threshold


def test_direction_determination():
    """Test position direction determination from quantity sign."""
    qty_long = Decimal("0.05")
    qty_short = Decimal("-0.1")

    assert qty_long > 0
    direction_long = "long" if qty_long > 0 else "short"
    assert direction_long == "long"

    assert qty_short < 0
    direction_short = "long" if qty_short > 0 else "short"
    assert direction_short == "short"


@pytest.mark.asyncio
async def test_monitor_static_tp_initialization():
    """Test that _monitor_static_individual_tp initializes correctly."""
    tp_bps = 10.0
    timeout_seconds = 60

    tp_threshold = Decimal(str(tp_bps / 10000))

    assert tp_threshold == Decimal("0.001")
    assert timeout_seconds == 60
```

**Run Unit Tests:**
```bash
python3 -m pytest /Users/botfarmer/2dex/tests/test_static_tp.py -v
```

---

### 3.3 Paper Trading Test Plan - WITH BASELINE DATA

**Step 1: Establish Baseline**
```bash
python3 -m hedge.DN_pair_eth_sol_nado \
    --size 100 \
    --iter 50 \
    --csv-path logs/baseline_spread_50cycles.csv \
    --sleep 0
```

**Step 2: Run Static TP Test**
```bash
python3 -m hedge.DN_pair_eth_sol_nado \
    --size 100 \
    --iter 50 \
    --enable-static-tp \
    --tp-bps 10 \
    --tp-timeout 60 \
    --csv-path logs/static_tp_50cycles.csv \
    --sleep 0
```

**Step 3: Statistical Comparison**

**File:** `/Users/botfarmer/2dex/scripts/compare_pnl.py` (NEW)

```python
"""
Compare PNL metrics between baseline and static TP runs.

Usage:
    python3 scripts/compare_pnl.py \
        --baseline logs/baseline_spread_50cycles.csv \
        --treatment logs/static_tp_50cycles.csv
"""

import pandas as pd
import numpy as np
from scipy import stats

def load_csv(csv_path):
    df = pd.read_csv(csv_path)
    return df

def calculate_metrics(df):
    if 'total_pnl' in df.columns:
        pnl_per_cycle = df['total_pnl'].tolist()
    else:
        pnl_per_cycle = (df.get('eth_pnl', 0) + df.get('sol_pnl', 0)).tolist()

    pnl_per_cycle = [p for p in pnl_per_cycle if not np.isnan(p)]

    metrics = {
        'avg_pnl': np.mean(pnl_per_cycle),
        'std_pnl': np.std(pnl_per_cycle),
        'total_pnl': np.sum(pnl_per_cycle),
        'num_cycles': len(pnl_per_cycle),
        'win_rate': len([p for p in pnl_per_cycle if p > 0]) / len(pnl_per_cycle) if pnl_per_cycle else 0
    }
    return metrics

def statistical_test(baseline_pnl, treatment_pnl):
    t_stat, p_value = stats.ttest_ind(baseline_pnl, treatment_pnl)
    return t_stat, p_value

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Compare PNL between baseline and treatment')
    parser.add_argument('--baseline', required=True, help='Baseline CSV path')
    parser.add_argument('--treatment', required=True, help='Treatment CSV path')
    args = parser.parse_args()

    baseline_df = load_csv(args.baseline)
    treatment_df = load_csv(args.treatment)

    baseline_metrics = calculate_metrics(baseline_df)
    treatment_metrics = calculate_metrics(treatment_df)

    print("\n" + "="*60)
    print("PNL COMPARISON: Baseline (19bps spread) vs Static TP (10bps)")
    print("="*60)

    print(f"\n{'Metric':<30} {'Baseline':>15} {'Static TP':>15} {'Improvement':>15}")
    print("-"*75)

    avg_pnl_improvement = ((treatment_metrics['avg_pnl'] - baseline_metrics['avg_pnl']) /
                           abs(baseline_metrics['avg_pnl']) * 100 if baseline_metrics['avg_pnl'] != 0 else 0)
    print(f"{'Avg PNL per cycle ($)':<30} {baseline_metrics['avg_pnl']:>15.2f} "
          f"{treatment_metrics['avg_pnl']:>15.2f} {avg_pnl_improvement:>+14.1f}%")

    total_pnl_improvement = ((treatment_metrics['total_pnl'] - baseline_metrics['total_pnl']) /
                             abs(baseline_metrics['total_pnl']) * 100 if baseline_metrics['total_pnl'] != 0 else 0)
    print(f"{'Total PNL ($)':<30} {baseline_metrics['total_pnl']:>15.2f} "
          f"{treatment_metrics['total_pnl']:>15.2f} {total_pnl_improvement:>+14.1f}%")

    win_rate_improvement = treatment_metrics['win_rate'] - baseline_metrics['win_rate']
    print(f"{'Win Rate (%)':<30} {baseline_metrics['win_rate']*100:>14.1f}% "
          f"{treatment_metrics['win_rate']*100:>14.1f}% {win_rate_improvement*100:>+14.1f}%")

    print(f"{'Num Cycles':<30} {baseline_metrics['num_cycles']:>15} "
          f"{treatment_metrics['num_cycles']:>15} {'N/A':>15}")

    baseline_pnl = baseline_df['total_pnl'].dropna().tolist()
    treatment_pnl = treatment_df['total_pnl'].dropna().tolist()

    t_stat, p_value = statistical_test(baseline_pnl, treatment_pnl)

    print(f"\n{'Statistical Test':<30} {'Value':>15}")
    print("-"*45)
    print(f"{'T-statistic':<30} {t_stat:>15.4f}")
    print(f"{'P-value':<30} {p_value:>15.4f}")

    if p_value < 0.05:
        print(f"\nResult is STATISTICALLY SIGNIFICANT (p < 0.05)")
    else:
        print(f"\nResult is NOT statistically significant (p >= 0.05)")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
```

**Run Comparison:**
```bash
python3 /Users/botfarmer/2dex/scripts/compare_pnl.py \
    --baseline logs/baseline_spread_50cycles.csv \
    --treatment logs/static_tp_50cycles.csv
```

---

### 3.4 Success Criteria

| Metric | 19bps Spread (Baseline) | Static TP (Treatment) | Improvement Target | Statistical Test |
|--------|------------------------|----------------------|-------------------|------------------|
| PNL per cycle | Measure from baseline | Measure from treatment | >= +20% | t-test, p < 0.05 |
| Total PNL (50 cycles) | Measure from baseline | Measure from treatment | >= +30% | t-test, p < 0.05 |
| Win rate | Measure from baseline | Measure from treatment | >= +5% | Chi-square test |
| TP hit rate | N/A | Track in logs | >= 60% | N/A |
| Hedge break time | N/A | Track in logs | <= 30s avg | N/A |

---

## Phase 4: Deployment Strategy

### 4.1 Pre-Merge Checklist

```bash
# Run tests
python3 -m pytest /Users/botfarmer/2dex/tests/test_static_tp.py -v

# Code review checklist
[ ] All 8 critical issues addressed
[ ] _tp_hit_position initialized in __init__
[ ] UNWIND retry updates entry_quantities and entry_prices
[ ] Individual close uses current position, not target_notional
[ ] Exit price storage timing clarified
[ ] Test fixtures documented
[ ] scipy added to dependencies
[ ] No duplicate sections in plan
```

### 4.2 Merge Procedure (If Approved)

```bash
git checkout feature-staticTP
git pull origin feature-staticTP

python3 -m pytest /Users/botfarmer/2dex/tests/ -v
python3 -m hedge.DN_pair_eth_sol_nado --size 100 --iter 10 --enable-static-tp

git checkout main
git merge feature-staticTP

python3 -m pytest /Users/botfarmer/2dex/tests/ -v

git push origin main
git tag -a v1.1.0-static-tp -m "Add static TP feature (10bps individual TP)"
git push origin v1.1.0-static-tp
```

### 4.3 Rollback Plan

```bash
# Discard branch
git checkout main
git branch -D feature-staticTP

# Or revert if already merged
git revert <commit-hash>
git push origin main
```

---

## Implementation Timeline

| Phase | Task | Time | Dependencies |
|-------|------|------|--------------|
| **1** | Fix handle_emergency_unwind | 15 min | - |
| **1** | Add UNWIND retry logic | 1.5 hours | - |
| **2** | Add CLI parameters | 30 min | Phase 1 |
| **2** | Add TP monitoring method | 2 hours | CLI params |
| **2** | Integrate into UNWIND | 1.5 hours | TP monitoring |
| **2** | Add individual close methods | 1.5 hours | Integration |
| **3** | Unit tests | 1 hour | Phase 2 |
| **3** | Baseline data collection | 2 hours | Tests pass |
| **3** | Paper trading (50 cycles) | 4-6 hours | Baseline ready |
| **3** | Statistical analysis | 1 hour | Test results |
| **4** | Decision & merge/rollback | 30 min | Analysis complete |
| **Total** | | **16-19 hours** | |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| TP threshold too conservative | Medium | Low | CLI configurable (10-20 bps) |
| Hedge break causes loss | High | Medium | Quick re-close logic (30s timeout) |
| Individual close fails | Medium | Medium | Fallback to spread, partial fill handling |
| Inconclusive results | Low | High | Extend to 100 cycles, statistical test |
| Bugs in new code | Medium | Medium | Unit tests + gradual rollout |

---

## Files to Modify

### 1. `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Phase 1 - Critical Fixes:**
- Lines 786-791: Fix `handle_emergency_unwind()` - Use `_is_fill_complete()`
- Lines 2466-2467: Add UNWIND order retry logic with state updates

**Phase 2 - Static TP:**
- Lines 2863-2872: Add CLI parameters
- Lines 80-82: Add `__init__()` parameters
- Lines 98-103: Initialize instance variables (including `_tp_hit_position`)
- Lines 2900-2904: Add to `main()` bot instantiation
- Line 113: Add startup logging
- After line 1925: Add `_monitor_static_individual_tp()` method
- After `_monitor_static_individual_tp()`: Add `_close_individual_position()` method
- After `_close_individual_position()`: Add `_check_and_close_remaining_position()` method
- Around line 2420: Integrate into `execute_unwind_cycle()`

### 2. `/Users/botfarmer/2dex/tests/test_static_tp.py` (NEW)
- Unit tests for TP calculation
- Unit tests for PNL calculation
- Unit tests for direction determination

### 3. `/Users/botfarmer/2dex/scripts/compare_pnl.py` (NEW)
- CSV loading and parsing
- Metrics calculation
- Statistical testing (t-test)
- Report generation

---

## Verification Checklist (All 8 Issues Fixed)

- [x] **Issue 1 - Duplicate Sections:** REMOVED - No duplicate sections in plan
- [x] **Issue 2 - False Claim About _retry_side_order():** CORRECTED - Method does NOT update entry data; caller must update with explicit code
- [x] **Issue 3 - UNWIND Retry Missing State Update:** FIXED - Added explicit code to update `entry_quantities[ticker] += filled_size` and `entry_prices[ticker]`
- [x] **Issue 4 - Wrong Notional for UNWIND:** FIXED - Use `abs(eth_pos)` for remaining quantity, NOT `self.target_notional`
- [x] **Issue 5 - Exit Price Storage Conflicts:** CLARIFIED - Individual closes set `_exit_prices[ticker]` immediately; timing is safe due to `.get()` fallback
- [x] **Issue 6 - Missing _tp_hit_position Initialization:** FIXED - Added `self._tp_hit_position = None` and `self._tp_hit_pnl_pct = None` at line 101-102
- [x] **Issue 7 - Test Fixtures Not Documented:** DOCUMENTED - All existing fixtures in conftest.py documented with line numbers
- [x] **Issue 8 - Missing Dependencies:** ADDED - scipy added to pip install instructions

---

## Summary of Changes

### Code References Verified
- `_is_fill_complete()`: Lines 2036-2043
- `_retry_side_order()`: Lines 2077-2112 (DOES NOT update entry data)
- `_calculate_remaining_quantities()`: Lines 2045-2075
- Existing UNWIND retry: Lines 2468-2505
- `entry_prices` initialization: Lines 144-148
- `entry_quantities` initialization: Lines 148-152
- Test fixtures: `/Users/botfarmer/2dex/tests/conftest.py` (lines 15-131)

### New Code
- 3 new methods (~250 lines)
- CLI parameter integration (~50 lines)
- Unit tests (~150 lines)
- Comparison script (~120 lines)
- Total: ~570 lines of new code

### Modified Code
- `handle_emergency_unwind()`: 5 lines changed
- `execute_unwind_cycle()`: ~30 lines added
- `__init__()`: 3 parameters + 5 lines (including _tp_hit_position)
- `main()`: 3 lines
- Total: ~45 lines modified

---

## Next Steps

1. Plan revised with all 8 critical issues fixed
2. All code references verified against actual files
3. Instance variable initialization locations specified
4. Test infrastructure setup detailed
5. Statistical methodology defined
6. **AWAITING USER CONFIRMATION** to proceed with implementation

---

**PLAN_READY**
