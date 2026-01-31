# WebSocket-Based PNL Optimization Plan for DN Bot

**Plan ID**: websocket-pnl-optimization-001
**Created**: 2026-01-31
**Status**: DRAFT
**Target**: Delta Neutral Pair Bot (ETH/SOL on Nado)

---

## Executive Summary

**Problem**: Bot loses $-0.20/cycle on average (IOC mode, $100 size, 3 cycles) with current simple spread filter (>= 6 bps). User insight: "spread filter 20bps is not the core PNL solution."

**Root Cause Analysis**:
1. Entry timing ignores momentum - entering during adverse price movement
2. Exit logic uses static thresholds (5/15/-30 bps) regardless of market conditions
3. BookDepth data exists but is only used for slippage estimation, not decision-making
4. BBO momentum detector exists but is NOT used for trading decisions

**Solution**: Leverage existing WebSocket BBO and BookDepth data to ACTIVELY IMPROVE PNL through:
1. **Momentum-based entry filtering** - Avoid entering during adverse price movement
2. **Liquidity-aware sizing** - Size positions based on available BookDepth liquidity
3. **Dynamic exit thresholds** - Adjust exit targets based on real-time spread state
4. **Spread timing optimization** - Wait for favorable spread conditions before exit

**Expected Impact**: Target improvement from $-0.20/cycle to $+0.10/cycle (avg +$0.30 improvement per cycle)

---

## Context

### Original Request
The user rejected a previous "100 lossless trades" plan because it only added superficial filters without addressing the core $-0.20/cycle loss problem. Key user insight:
- "Spread filter to 20bps infinite expansion is not the core of PNL. It sacrifices huge trading volume."
- "Think about PNL improvement using WebSocket data, especially bookdepth, bbo to the max."

### Current Situation
- **Mode**: IOC (Immediate-Or-Cancel), 5 bps taker fee, $100 size, 3 cycles
- **Entry Logic**: Simple spread >= 6 bps filter (line 694 in DN_pair_eth_sol_nado.py)
- **Exit Logic**: Static thresholds (line 1114-1119): 15 bps profit target, 5 bps small profit, -30 bps stop loss
- **Current PNL**: $-0.20/cycle average

### WebSocket Data Available (Already Implemented!)

**BBO Handler** (`nado_bbo_handler.py`):
- `MomentumDetector` (lines 100-142): Detects BULLISH/BEARISH/NEUTRAL momentum
- `SpreadMonitor` (lines 56-98): Detects WIDENING/NARROWING/STABLE spread state
- Both analyzers run on every BBO update BUT ARE NOT USED FOR TRADING DECISIONS

**BookDepth Handler** (`nado_bookdepth_handler.py`):
- Maintains real-time order book (50ms updates)
- `estimate_slippage()` (lines 167-234): Calculate slippage for any order size
- `get_available_liquidity()` (lines 236-264): Get total liquidity at any depth
- `estimate_exit_capacity()` (lines 266-303): Check if position can be exited without excessive slippage
- Currently used ONLY for slippage-aware sizing (lines 353-358 in DN_pair_eth_sol_nado.py)

### Current Trading Logic Issues

**Entry Logic** (`_check_spread_profitability()`, lines 668-707):
```python
# CURRENT: Simple spread threshold check only
is_profitable = eth_spread_bps >= MIN_SPREAD_BPS or sol_spread_bps >= MIN_SPREAD_BPS
```
- Ignores momentum direction
- Ignores spread state (widening/narrowing)
- Ignores liquidity conditions

**Exit Logic** (`_check_exit_timing()`, lines 1076-1122):
```python
# CURRENT: Static thresholds
if pnl_bps > 15:  # 15 bps profit target
    return True, f"profit_target_{pnl_bps:.1f}bps"
if pnl_bps > 5:  # Small profit, exit now
    return True, f"small_profit_{pnl_bps:.1f}bps"
if pnl_bps < -30:  # Stop loss
    return True, f"stop_loss_{pnl_bps:.1f}bps"
```
- Fixed thresholds regardless of market conditions
- Does not consider current spread state
- Does not consider liquidity for exit

**Entry Timing** (`_wait_for_optimal_entry()`, lines 1025-1074):
```python
# CURRENT: Waits for spread >= 25 bps (hardcoded)
if current_spread >= 25:
    return {...}
```
- Hardcoded 25 bps threshold
- Does not use momentum data
- Does not use spread state (widening/narrowing)

---

## Work Objectives

### Core Objective
Integrate WebSocket BBO and BookDepth data into trading decisions to ACTIVELY IMPROVE PNL per cycle.

### Critical Prerequisite (Task 0)
**IMPORTANT**: Task 0 must be completed FIRST before any other work. The plan initially referenced private attributes that are not accessible. Task 0 REPLACES existing methods with proper caching architecture:

**Current State**: `get_momentum()` and `get_spread_state()` methods EXIST at lines 272-282 of nado_bbo_handler.py but are IMPURE (they call `on_bbo()` which triggers analyzer state machine, causing side effects and potential state corruption).

**Architect Solution (BBOHandler Caching)**:
- Add `_cached_spread_state` and `_cached_momentum` to `BBOHandler.__init__()`
- Modify `_on_bbo_message()` to cache spread_state and momentum (not just calculate them)
- Add pure getter methods `get_spread_state()` and `get_momentum()` that return cached values
- **Critical**: Getters must NOT call `on_bbo()` (no side effects) - they return cached values
- **Why Pure Getters Matter**: Pure getters prevent accidental analyzer recalculation which would corrupt momentum/spread state by triggering the detector's state machine multiple times per BBO update

**NadoClient API**:
- `get_bbo_handler()` method in NadoClient (returns BBOHandler or None)

**Validation**: Phase 0 must pass before proceeding to Task 1-6.

### Deliverables
0. **Infrastructure with Caching** - Add BBO handler caching and public access methods (MUST BE FIRST)
1. **Momentum-aware entry filter** - For Long ETH/Short SOL: skip if ETH BEARISH OR SOL BULLISH
2. **Liquidity-based position sizing** - Fixed $100 size with skip when slippage too high (return qty=0)
3. **Dynamic exit thresholds** - Adjust profit/stop targets based on real-time spread and momentum
4. **Optimized entry timing** - Replace hardcoded 25 bps with dynamic threshold based on market state
5. **Pre-exit liquidity check** - Verify sufficient liquidity before attempting exit

### Definition of Done
- Task 0 infrastructure completed and validated (Phase 0 passes)
- All WebSocket data (BBO momentum, spread state, BookDepth liquidity) used in trading decisions
- Proper null checks for WebSocket unavailability in all code
- Backtest validation showing PNL improvement (target +$0.30/cycle vs baseline)
- CSV logging includes decision factors (momentum, spread state, liquidity)
- No increase in failed or partial fills

---

## Must Have / Must NOT Have

### Must Have (Guardrails)
1. **NO new spread filter thresholds** - Do NOT just increase min_spread_bps from 6 to 20 (this was rejected)
2. **USE existing WebSocket data** - BBO momentum detector, spread monitor, BookDepth liquidity
3. **Maintain REST fallback** - If WebSocket unavailable, gracefully degrade to current behavior
4. **Preserve IOC mode** - Keep IOC order type (5 bps taker fee)
5. **Keep position sizing at $100 notional** - Do not change position size

### Must NOT Have
1. NO superficial filters (e.g., "wait for 50 bps spread")
2. NO hardcoded thresholds that sacrifice trading volume
3. NO changes to order type (stay IOC)
4. NO changes to position size ($100 notional)

---

## Technical Architecture

### Current Data Flow (Unused)
```
WebSocket BBO Stream -> BBOHandler -> MomentumDetector (returns BULLISH/BEARISH/NEUTRAL)
                                                    -> SpreadMonitor (returns WIDENING/NARROWING/STABLE)
                                                    -> get_latest_bbo() (NOT USED for trading)

WebSocket BookDepth Stream -> BookDepthHandler -> estimate_slippage() (USED for sizing)
                                                    -> get_available_liquidity() (NOT USED)
                                                    -> estimate_exit_capacity() (NOT USED)
```

### Target Data Flow (After Optimization)
```
WebSocket BBO Stream -> BBOHandler -> [USED IN] Entry decision (momentum filter)
                                     -> [USED IN] Entry timing (spread state)
                                     -> [USED IN] Exit decision (momentum-aware thresholds)

WebSocket BookDepth Stream -> BookDepthHandler -> [USED IN] Position sizing (liquidity-based)
                                                  -> [USED IN] Pre-exit check (capacity verification)
                                                  -> [USED IN] Dynamic slippage limits
```

---

## Detailed Tasks

### Task 0: Infrastructure - Add BBO Handler Caching and Public Access Methods

**Problem**: The plan references `self.eth_client._bbo_handler` but `_bbo_handler` is a private attribute without a public accessor method. Additionally, `get_momentum()` and `get_spread_state()` methods EXIST at lines 272-282 but are IMPURE (they call `on_bbo()` which triggers the analyzer state machine, causing side effects and potential state corruption). Task 0 REPLACES these impure methods with pure cached getters.

**Solution**:
1. Add `get_bbo_handler()` public method to `NadoClient` class
2. Add cached state variables to `BBOHandler.__init__()`
3. Modify `_on_bbo_message()` to cache spread state and momentum
4. Add pure getter methods `get_spread_state()` and `get_momentum()` that return cached values

**Implementation**:

1. Add public method to `NadoClient` class in `/Users/botfarmer/2dex/hedge/exchanges/nado.py`:

   ```python
   # In NadoClient class, add after get_bookdepth_handler() (around line 296)
   def get_bbo_handler(self) -> Optional['BBOHandler']:
       """Get the BBO handler for this client (if WebSocket is connected).

       Returns:
           BBOHandler instance if WebSocket is connected, None otherwise
       """
       return self._bbo_handler if self._ws_connected else None
   ```

2. Add cached state to `BBOHandler.__init__()` in `/Users/botfarmer/2dex/hedge/exchanges/nado_bbo_handler.py` (around line 179):

   ```python
   # In BBOHandler.__init__() - Add after line 179 (after momentum_detector init)
   # Cached state for public getters (avoids side effects in getter methods)
   self._cached_spread_state = "STABLE"
   self._cached_momentum = "NEUTRAL"
   ```

3. Modify `_on_bbo_message()` to cache state (around line 215 in nado_bbo_handler.py):

   ```python
   # In _on_bbo_message() - Replace lines 215-216
   # OLD CODE:
   # spread_state = self.spread_monitor.on_bbo(bbo)
   # momentum = self.momentum_detector.on_bbo(bbo)

   # NEW CODE (cache the results):
   self._cached_spread_state = self.spread_monitor.on_bbo(bbo)
   self._cached_momentum = self.momentum_detector.on_bbo(bbo)

   # Use cached values in callbacks
   for callback in self._callbacks:
       try:
           if asyncio.iscoroutinefunction(callback):
               await callback(bbo, self._cached_spread_state, self._cached_momentum)
           else:
               callback(bbo, self._cached_spread_state, self._cached_momentum)
       except Exception as e:
           self.logger.error(f"Error in BBO callback: {e}")
   ```

4. Add pure getter methods to `BBOHandler` class (after line 247 in nado_bbo_handler.py):

   ```python
   # Add after get_latest_bbo() method
   def get_spread_state(self) -> str:
       """Get current cached spread state (pure getter, no side effects).

       Returns:
           Current spread state: "WIDENING", "NARROWING", or "STABLE"
       """
       return self._cached_spread_state

   def get_momentum(self) -> str:
       """Get current cached momentum state (pure getter, no side effects).

       Returns:
           Current momentum state: "BULLISH", "BEARISH", or "NEUTRAL"
       """
       return self._cached_momentum
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py` - Add `get_bbo_handler()` method after line 296
- `/Users/botfarmer/2dex/hedge/exchanges/nado_bbo_handler.py` - Add cached state in `__init__()`, modify `_on_bbo_message()`, add pure getter methods

**Acceptance criteria**:
- `get_bbo_handler()` returns `BBOHandler` instance when WebSocket is connected
- `get_bbo_handler()` returns `None` when WebSocket is not connected
- `get_spread_state()` and `get_momentum()` return cached values without calling `on_bbo()` (no side effects)
- Multiple calls to getters return consistent values without triggering analyzer recalculation
- Cached state updates on every BBO message

**Validation checkpoint**:
- Run test script that calls `get_momentum()` and `get_spread_state()` 100 times consecutively
- Verify: All 100 calls return same cached value without any analyzer recalculation side effects
- Verify: Cached value updates only when new BBO message arrives
- Verify: No state corruption in momentum/spread detectors after multiple getter calls

---

### Task 1: Momentum-Aware Entry Filter

**Problem**: Currently entering trades regardless of price momentum, leading to adverse entries.

**Solution**: Use cached momentum state from `BBOHandler` to filter entry based on momentum direction. For Long ETH/Short SOL strategy:
- **Worst case**: ETH BEARISH + SOL BULLISH (both legs against you)
- **Skip if**: ETH BEARISH (long falling) OR SOL BULLISH (short rising)
- **Ideal**: ETH BULLISH AND SOL BEARISH (both favorable)

**Implementation**:

1. Add entry condition check in `DN_pair_eth_sol_nado.py`:

   ```python
   # In _check_spread_profitability() or new _check_entry_conditions()
   async def _check_entry_conditions(self) -> tuple[bool, dict]:
       """Check if entry conditions are met using WebSocket data.

       Strategy: Long ETH / Short SOL
       - Ideal: ETH BULLISH (long rising) AND SOL BEARISH (short falling)
       - Acceptable: Any NEUTRAL combinations
       - Skip: ETH BEARISH (long falling) OR SOL BULLISH (short rising)

       Returns:
           (should_enter, context_dict)
       """

       # Get BBO handlers with null checks
       eth_bbo = self.eth_client.get_bbo_handler()
       sol_bbo = self.sol_client.get_bbo_handler()

       # Fallback: if WebSocket unavailable, use basic spread check only
       if eth_bbo is None or sol_bbo is None:
           self.logger.warning("[ENTRY] WebSocket BBO unavailable, using basic check")
           return True, {"reason": "websocket_unavailable_basic_check"}

       # Get cached momentum signal from BBO handler (pure getters, no side effects)
       eth_momentum = eth_bbo.get_momentum()
       sol_momentum = sol_bbo.get_momentum()

       # MOMENTUM FILTER: Skip if adverse conditions for Long ETH/Short SOL
       # Skip if ETH is BEARISH (we're long ETH, don't want falling price)
       if eth_momentum == "BEARISH":
           return False, {
               "reason": "bearish_eth_momentum",
               "eth_momentum": eth_momentum,
               "sol_momentum": sol_momentum,
               "filter_type": "momentum_adverse_long_leg"
           }

       # Skip if SOL is BULLISH (we're short SOL, don't want rising price)
       if sol_momentum == "BULLISH":
           return False, {
               "reason": "bullish_sol_momentum",
               "eth_momentum": eth_momentum,
               "sol_momentum": sol_momentum,
               "filter_type": "momentum_adverse_short_leg"
           }

       # Entry allowed: ETH not BEARISH AND SOL not BULLISH
       # Ideal case: ETH BULLISH AND SOL BEARISH (both legs favorable)
       if eth_momentum == "BULLISH" and sol_momentum == "BEARISH":
           return True, {
               "reason": "optimal_momentum_both_favorable",
               "eth_momentum": eth_momentum,
               "sol_momentum": sol_momentum,
               "filter_type": "momentum_optimal"
           }

       # Acceptable: At least one leg favorable, other neutral
       return True, {
           "reason": "acceptable_momentum",
           "eth_momentum": eth_momentum,
           "sol_momentum": sol_momentum,
           "filter_type": "momentum_acceptable"
       }
   ```

2. Integrate into entry timing logic:

   ```python
   # In _wait_for_optimal_entry() or run_dry_run()
   # Before entering position, check momentum conditions
   should_enter, entry_context = await self._check_entry_conditions()

   if not should_enter:
       self.logger.info(
           f"[ENTRY] Skipped due to momentum filter: {entry_context['reason']} "
           f"(ETH={entry_context['eth_momentum']}, SOL={entry_context['sol_momentum']})"
       )
       continue  # Wait for next opportunity
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add `_check_entry_conditions()` method with Long ETH/Short SOL momentum logic, integrate into entry flow

**Acceptance criteria**:
- Entry filter uses cached momentum state from BBO handler
- Skips entry when ETH is BEARISH (long leg adverse)
- Skips entry when SOL is BULLISH (short leg adverse)
- CSV logs include momentum state and filter reason at entry
- No increase in null reference errors (proper null checks for WebSocket unavailability)

**Validation checkpoint**:
- Log all entry attempts with momentum states for 100 cycles
- Count filtered entries by reason (ETH BEARISH vs SOL BULLISH)
- Verify: Filter rate is between 20-40% (not too restrictive, not too permissive)
- Verify: No entries when ETH BEARISH or SOL BULLISH

---

### Task 2: Liquidity-Based Position Sizing

**Problem**: Current sizing uses fixed $100 notional regardless of available liquidity, leading to slippage.

**Solution**: Use `BookDepthHandler.get_available_liquidity()` to check if $100 notional can be traded without excessive slippage. Return fixed size when liquidity sufficient, or qty=0 to skip trade when insufficient.

**Implementation**:

1. Add method to calculate safe position size with skip logic:
   ```python
   # In DN_pair_eth_sol_nado.py
   async def _calculate_liquidity_adjusted_size(
       self,
       ticker: str,
       target_notional: Decimal,
       max_slippage_bps: int = 10
   ) -> Decimal:
       """Calculate position size based on available liquidity.

       Strategy: Fixed $100 notional with skip when liquidity insufficient.
       Returns target_qty if exitable with acceptable slippage, else qty=0.

       Args:
           ticker: "ETH" or "SOL"
           target_notional: Target USD notional (e.g., $100)
           max_slippage_bps: Maximum acceptable slippage in bps (default 10)

       Returns:
           Position quantity (returns 0 if slippage too high)
       """
       client = self.eth_client if ticker == "ETH" else self.sol_client
       book_handler = client.get_bookdepth_handler()

       if book_handler is None:
           # Fallback to simple calculation when WebSocket unavailable
           self.logger.warning(f"[LIQUIDITY] {ticker}: WebSocket unavailable, using basic sizing")
           bid, ask = await client.fetch_bbo_prices(client.config.contract_id)
           return (target_notional / bid).quantize(client.config.tick_size)

       # Get current price
       bid, ask = await client.fetch_bbo_prices(client.config.contract_id)
       price = bid if ticker == "ETH" else ask

       # Calculate target quantity (fixed $100 notional)
       target_qty = (target_notional / price).quantize(client.config.tick_size)

       # Check if we can exit this quantity with acceptable slippage
       # ETH: Long position -> need to sell (check ask side liquidity)
       # SOL: Short position -> need to buy (check bid side liquidity)
       can_exit, exitable_qty = book_handler.estimate_exit_capacity(
           current_position=target_qty if ticker == "ETH" else -target_qty,
           max_slippage_bps=max_slippage_bps
       )

       if can_exit:
           # Liquidity sufficient for full size
           return target_qty
       else:
           # Liquidity insufficient - SKIP trade by returning 0
           self.logger.warning(
               f"[LIQUIDITY] {ticker}: Insufficient liquidity for {target_qty} "
               f"(can only exit {exitable_qty} within {max_slippage_bps} bps) - "
               f"SKIPPING TRADE"
           )
           return Decimal("0")  # Signal to skip trade
   ```

2. Integrate into order placement with skip check:
   ```python
   # In place_simultaneous_orders()
   # Calculate liquidity-adjusted sizes
   eth_qty = await self._calculate_liquidity_adjusted_size("ETH", self.target_notional)
   sol_qty = await self._calculate_liquidity_adjusted_size("SOL", self.target_notional)

   # Skip trade if either leg has insufficient liquidity (qty=0)
   if eth_qty == 0 or sol_qty == 0:
       self.logger.warning(
           f"[ENTRY] Insufficient liquidity - skipping entry "
           f"(ETH qty={eth_qty}, SOL qty={sol_qty})"
       )
       return None  # Skip this entry attempt

   # Proceed with order placement using calculated quantities
   # ... existing order placement code ...
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add `_calculate_liquidity_adjusted_size()` method with skip logic, integrate into order placement

**Acceptance criteria**:
- Returns fixed $100 notional quantity when liquidity sufficient
- Returns qty=0 when slippage would exceed threshold (signals skip)
- CSV logs include liquidity metrics and skip reason
- No partial fills due to insufficient liquidity (trade skipped instead)
- Maintains $100 notional constraint when trade proceeds

**Validation checkpoint**:
- Log liquidity check results for 100 entry attempts
- Count skipped trades due to insufficient liquidity
- Verify: Skip rate is <10% (liquidity usually sufficient)
- Verify: All trades that proceed have <10 bps slippage on exit
- Verify: No partial fills due to insufficient liquidity (trade skipped instead)

---

### Task 3: Dynamic Exit Thresholds

**Problem**: Current exit uses fixed thresholds (15/5/-30 bps) regardless of market conditions, missing opportunities or stopping out early.

**Solution**: Use BBO spread state and momentum to adjust exit thresholds dynamically.

**Implementation**:

1. Add dynamic threshold calculation with WebSocket fallback:
   ```python
   # In DN_pair_eth_sol_nado.py
   def _calculate_dynamic_exit_thresholds(self) -> dict:
       """Calculate dynamic exit thresholds based on market state.

       Returns:
           dict with 'profit_target_bps', 'small_profit_bps', 'stop_loss_bps', and market state data
       """
       # Get BBO handlers with null checks
       eth_bbo = self.eth_client.get_bbo_handler()
       sol_bbo = self.sol_client.get_bbo_handler()

       # Default values when WebSocket unavailable
       eth_spread_state = "STABLE"
       sol_spread_state = "STABLE"
       eth_momentum = "NEUTRAL"
       sol_momentum = "NEUTRAL"

       # Get spread state and momentum if WebSocket available
       if eth_bbo is not None:
           eth_spread_state = eth_bbo.get_spread_state()
           eth_momentum = eth_bbo.get_momentum()

       if sol_bbo is not None:
           sol_spread_state = sol_bbo.get_spread_state()
           sol_momentum = sol_bbo.get_momentum()

       # Base thresholds
       profit_target = 15  # bps
       small_profit = 5    # bps
       stop_loss = -30     # bps

       # Adjust based on spread state
       if eth_spread_state == "WIDENING" or sol_spread_state == "WIDENING":
           # Volatility increasing - wider targets, wider stops
           profit_target += 10  # 25 bps
           small_profit += 5    # 10 bps
           stop_loss -= 10      # -40 bps

       # Adjust based on momentum
       if eth_momentum == "BULLISH" and sol_momentum == "BULLISH":
           # Favorable momentum - tighter profit target (quick exit)
           profit_target -= 5  # 10 bps
       elif eth_momentum == "BEARISH" and sol_momentum == "BEARISH":
           # Adverse momentum - wider profit target (wait for reversal)
           profit_target += 10  # 25 bps

       return {
           "profit_target_bps": profit_target,
           "small_profit_bps": small_profit,
           "stop_loss_bps": stop_loss,
           "eth_spread_state": eth_spread_state,
           "sol_spread_state": sol_spread_state,
           "eth_momentum": eth_momentum,
           "sol_momentum": sol_momentum,
           "websocket_available": eth_bbo is not None and sol_bbo is not None
       }
   ```

2. Integrate into exit check:
   ```python
   # In _check_exit_timing()
   async def _check_exit_timing(self, max_loss_bps: int = 30) -> tuple[bool, str]:
       # ... existing code ...

       # Get dynamic thresholds
       thresholds = self._calculate_dynamic_exit_thresholds()

       # Use dynamic thresholds instead of hardcoded
       if pnl_bps > thresholds["profit_target_bps"]:
           return True, f"profit_target_{pnl_bps:.1f}bps"
       if pnl_bps > thresholds["small_profit_bps"]:
           return True, f"small_profit_{pnl_bps:.1f}bps"
       if pnl_bps < thresholds["stop_loss_bps"]:
           return True, f"stop_loss_{pnl_bps:.1f}bps"

       # Log dynamic thresholds for analysis
       self.logger.info(
           f"[EXIT] Dynamic thresholds: profit={thresholds['profit_target_bps']}, "
           f"small={thresholds['small_profit_bps']}, stop={thresholds['stop_loss_bps']}, "
           f"PNL={pnl_bps:.1f}, ws_available={thresholds['websocket_available']}"
       )

       return False, f"waiting_{pnl_bps:.1f}bps"
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add dynamic threshold calculation with WebSocket fallback, integrate into exit logic

**Acceptance criteria**:
- Exit thresholds adjust based on real-time market state
- CSV logs include dynamic thresholds used for each exit decision
- Wider thresholds during widening spreads, tighter during favorable momentum

---

### Task 4: Optimized Entry Timing

**Problem**: Current entry timing uses hardcoded 25 bps threshold (line 1055), missing better entry opportunities at lower spreads during favorable conditions.

**Solution**: Replace hardcoded threshold with dynamic threshold based on momentum and spread state.

**Implementation**:

1. Add dynamic entry threshold calculation with WebSocket fallback:
   ```python
   # In DN_pair_eth_sol_nado.py
   def _calculate_entry_threshold(self) -> dict:
       """Calculate dynamic entry threshold based on market state.

       Returns:
           dict with 'min_spread_bps', 'optimal_spread_bps', 'reason', and market state data
       """
       # Get BBO handlers with null checks
       eth_bbo = self.eth_client.get_bbo_handler()
       sol_bbo = self.sol_client.get_bbo_handler()

       # Default values when WebSocket unavailable
       eth_spread_state = "STABLE"
       sol_spread_state = "STABLE"
       eth_momentum = "NEUTRAL"
       sol_momentum = "NEUTRAL"

       # Get spread state and momentum if WebSocket available
       if eth_bbo is not None:
           eth_spread_state = eth_bbo.get_spread_state()
           eth_momentum = eth_bbo.get_momentum()

       if sol_bbo is not None:
           sol_spread_state = sol_bbo.get_spread_state()
           sol_momentum = sol_bbo.get_momentum()

       # Base threshold (from config, default 6 bps)
       min_spread = self.min_spread_bps
       optimal_spread = 25  # Current hardcoded value

       # Adjust based on spread state
       if eth_spread_state == "WIDENING" or sol_spread_state == "WIDENING":
           # Spread widening - lower threshold to catch entries before spread widens further
           min_spread = max(min_spread - 2, 4)  # Reduce by 2 bps, min 4
           optimal_spread = 20  # Lower optimal threshold

       # Adjust based on momentum
       if eth_momentum == "BULLISH" and sol_momentum != "BEARISH":
           # Favorable momentum for long ETH - enter at lower spread
           optimal_spread = 18
       elif eth_momentum == "BEARISH" or sol_momentum == "BEARISH":
           # Adverse momentum - wait for better spread
           optimal_spread = 30

       return {
           "min_spread_bps": min_spread,
           "optimal_spread_bps": optimal_spread,
           "eth_spread_state": eth_spread_state,
           "sol_spread_state": sol_spread_state,
           "eth_momentum": eth_momentum,
           "sol_momentum": sol_momentum,
           "websocket_available": eth_bbo is not None and sol_bbo is not None
       }
   ```

2. Integrate into entry timing:
   ```python
   # In _wait_for_optimal_entry()
   async def _wait_for_optimal_entry(self, timeout: int = 30) -> dict:
       # ... existing code ...

       while time.time() - start_time < timeout:
           # Get current spread and market state
           entry_thresholds = self._calculate_entry_threshold()
           optimal_spread = entry_thresholds["optimal_spread_bps"]

           # ... existing spread check ...

           # Enter if spread meets dynamic optimal threshold
           if current_spread >= optimal_spread:
               self.logger.info(
                   f"[ENTRY] Optimal spread detected: {current_spread:.1f}bps "
                   f"(threshold={optimal_spread}bps, "
                   f"spread_state={entry_thresholds['eth_spread_state']}, "
                   f"momentum={entry_thresholds['eth_momentum']}, "
                   f"ws_available={entry_thresholds['websocket_available']})"
               )
               return {
                   "waited_seconds": time.time() - start_time,
                   "entry_spread_bps": current_spread,
                   "reason": "optimal_spread",
                   "thresholds": entry_thresholds
               }
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add dynamic entry threshold calculation with WebSocket fallback, integrate into entry timing

**Acceptance criteria**:
- Entry threshold adjusts based on real-time market state
- Lower threshold during favorable momentum (more entries)
- Higher threshold during adverse momentum (better entries)
- CSV logs include dynamic threshold used for entry

---

### Task 5: Pre-Exit Liquidity Check

**Problem**: Exit attempts may fail due to insufficient liquidity, leading to partial fills and PNL drag.

**Solution**: Use `BookDepthHandler.estimate_exit_capacity()` to verify sufficient liquidity before attempting exit.

**Implementation**:

1. Add pre-exit liquidity check with WebSocket fallback:
   ```python
   # In DN_pair_eth_sol_nado.py
   async def _verify_exit_liquidity(self) -> tuple[bool, str]:
       """Verify sufficient liquidity for exit before attempting.

       Returns:
           (can_exit, message)
       """
       # Get current positions
       eth_pos = await self.eth_client.get_account_positions()
       sol_pos = await self.sol_client.get_account_positions()

       # Check ETH exit capacity (long position -> sell)
       eth_book = self.eth_client.get_bookdepth_handler()
       if eth_book is None:
           self.logger.warning("[EXIT] ETH WebSocket unavailable, skipping liquidity check")
       elif eth_pos > 0:
           can_exit_eth, exitable_eth = eth_book.estimate_exit_capacity(
               current_position=eth_pos,
               max_slippage_bps=20
           )
           if not can_exit_eth:
               return False, f"insufficient_ETH_liquidity_can_exit_{exitable_eth}/{eth_pos}"

       # Check SOL exit capacity (short position -> buy)
       sol_book = self.sol_client.get_bookdepth_handler()
       if sol_book is None:
           self.logger.warning("[EXIT] SOL WebSocket unavailable, skipping liquidity check")
       elif sol_pos < 0:
           can_exit_sol, exitable_sol = sol_book.estimate_exit_capacity(
               current_position=sol_pos,
               max_slippage_bps=20
           )
           if not can_exit_sol:
               return False, f"insufficient_SOL_liquidity_can_exit_{exitable_sol}/{abs(sol_pos)}"

       return True, "sufficient_liquidity"
   ```

2. Integrate into exit logic:
   ```python
   # In execute_unwind_cycle()
   async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
       # ... existing code ...

       # NEW: Verify exit liquidity before placing orders
       can_exit, liquidity_msg = await self._verify_exit_liquidity()
       if not can_exit:
           self.logger.warning(f"[UNWIND] Pre-exit liquidity check failed: {liquidity_msg}")
           # Wait and retry or adjust position size
           await asyncio.sleep(2)  # Wait for liquidity to improve
           can_exit, liquidity_msg = await self._verify_exit_liquidity()
           if not can_exit:
               self.logger.error(f"[UNWIND] Still insufficient liquidity: {liquidity_msg}")
               return False

       # Proceed with exit orders
       # ... existing code ...
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add pre-exit liquidity check with WebSocket fallback, integrate into unwind logic

**Acceptance criteria**:
- Pre-exit liquidity check runs before every exit attempt
- Exit attempts delayed if liquidity insufficient
- CSV logs include liquidity check results
- Reduced partial fills on exit

---

### Task 6: Enhanced CSV Logging

**Problem**: Current CSV does not include WebSocket decision factors, making analysis difficult.

**Solution**: Add new CSV fields for WebSocket-based decision factors.

**Implementation**:

1. Add new CSV columns (in `_initialize_csv_file()`):
   ```python
   # New columns to add:
   "entry_momentum_eth", "entry_momentum_sol",
   "entry_spread_state_eth", "entry_spread_state_sol",
   "entry_liquidity_eth", "entry_liquidity_sol",
   "exit_momentum_eth", "exit_momentum_sol",
   "exit_spread_state_eth", "exit_spread_state_sol",
   "exit_liquidity_eth", "exit_liquidity_sol",
   "dynamic_exit_threshold_profit", "dynamic_exit_threshold_stop",
   "entry_threshold_used"
   ```

2. Capture data during entry and exit with null checks:
   ```python
   # In execute_build_cycle()
   # After entry success, capture WebSocket state
   eth_bbo = self.eth_client.get_bbo_handler()
   sol_bbo = self.sol_client.get_bbo_handler()

   # Get momentum data with fallback to "UNKNOWN"
   entry_momentum_eth = eth_bbo.get_momentum() if eth_bbo else "UNKNOWN"
   entry_momentum_sol = sol_bbo.get_momentum() if sol_bbo else "UNKNOWN"
   entry_spread_state_eth = eth_bbo.get_spread_state() if eth_bbo else "UNKNOWN"
   entry_spread_state_sol = sol_bbo.get_spread_state() if sol_bbo else "UNKNOWN"

   # Get liquidity data
   eth_book = self.eth_client.get_bookdepth_handler()
   sol_book = self.sol_client.get_bookdepth_handler()
   entry_liquidity_eth = eth_book.get_available_liquidity("ask", 5) if eth_book else Decimal("0")
   entry_liquidity_sol = sol_book.get_available_liquidity("bid", 5) if sol_book else Decimal("0")

   # Store in instance variables for CSV logging
   self._entry_websocket_state = {
       "momentum_eth": entry_momentum_eth,
       "momentum_sol": entry_momentum_sol,
       "spread_state_eth": entry_spread_state_eth,
       "spread_state_sol": entry_spread_state_sol,
       "liquidity_eth": entry_liquidity_eth,
       "liquidity_sol": entry_liquidity_sol,
       "websocket_available": eth_bbo is not None and sol_bbo is not None
   }
   ```

**Files to modify**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Add new CSV columns, capture WebSocket state at entry/exit with null checks

**Acceptance criteria**:
- All WebSocket decision factors logged to CSV
- Can analyze PNL vs momentum/spread state/liquidity
- Can debug decision-making process

---

## Task Flow and Dependencies

```
Task 0: Infrastructure - BBO Handler Caching and Public Access
    ├─ Add get_bbo_handler() to NadoClient
    ├─ Add _cached_spread_state and _cached_momentum to BBOHandler.__init__()
    ├─ Modify _on_bbo_message() to cache spread_state and momentum
    ├─ Add pure getter methods get_spread_state() and get_momentum()
    └─ CRITICAL PREREQUISITE for all subsequent tasks
    └─ No dependencies (must be first)

Task 1: Momentum-Aware Entry Filter
    ├─ Add _check_entry_conditions() with Long ETH/Short SOL logic
    └─ Integrate into entry logic with null checks
    ├─ Depends on: Task 0 (get_bbo_handler, get_momentum access)

Task 2: Liquidity-Based Position Sizing
    ├─ Add _calculate_liquidity_adjusted_size() with fixed size + skip
    └─ Integrate into order placement
    ├─ No dependencies (uses existing get_bookdepth_handler)

Task 3: Dynamic Exit Thresholds
    ├─ Add dynamic threshold calculation
    └─ Integrate into exit check
    ├─ Depends on: Task 0 (momentum access via get_bbo_handler)

Task 4: Optimized Entry Timing
    ├─ Add dynamic entry threshold calculation
    └─ Integrate into entry timing
    ├─ Depends on: Task 0 (momentum access via get_bbo_handler)

Task 5: Pre-Exit Liquidity Check
    ├─ Add pre-exit liquidity check
    └─ Integrate into unwind logic
    ├─ Depends on: Task 2 (liquidity access)

Task 6: Enhanced CSV Logging
    ├─ Add new CSV columns
    └─ Capture WebSocket state
    ├─ Depends on: All previous tasks (capture all data)
```

**Recommended Execution Order**:
1. **Task 0 (FIRST - CRITICAL)** - Infrastructure prerequisite, must pass Phase 0 validation
2. Task 6 (early) - Add CSV columns early to capture baseline data
3. Task 1 & Task 2 (parallel) - Core decision improvements
4. Task 3 & Task 4 (after 1 & 2) - Advanced optimizations
5. Task 5 (last) - Safety check

---

## Validation Strategy

### Phase 0: Infrastructure Validation (CRITICAL - Before All Testing)

**Validation Checkpoint: BBO Handler Public Method Access**

Before any trading logic testing, verify the infrastructure is properly set up:

1. **Verify `get_bbo_handler()` exists and works**:
   ```python
   # Test script to run before Phase 1
   async def test_bbo_handler_access():
       eth_bbo = eth_client.get_bbo_handler()
       sol_bbo = sol_client.get_bbo_handler()

       # Check 1: Returns None when WebSocket disconnected
       assert eth_bbo is None or isinstance(eth_bbo, BBOHandler)
       assert sol_bbo is None or isinstance(sol_bbo, BBOHandler)

       # Check 2: When connected, can access methods
       if eth_bbo is not None:
           momentum = eth_bbo.get_momentum()
           assert momentum in ["BULLISH", "BEARISH", "NEUTRAL"]

           spread_state = eth_bbo.get_spread_state()
           assert spread_state in ["WIDENING", "NARROWING", "STABLE"]
   ```

2. **Verify `get_bookdepth_handler()` works**:
   ```python
   # Already exists, but verify null handling
   eth_book = eth_client.get_bookdepth_handler()
   if eth_book is None:
       print("WebSocket disconnected - proper fallback behavior")
   else:
       liquidity = eth_book.get_available_liquidity("ask", 5)
   ```

3. **Verify getter purity** (no side effects):
   ```python
   # Test that getters are pure (no analyzer recalculation)
   initial_momentum = eth_bbo.get_momentum()
   initial_spread = eth_bbo.get_spread_state()

   # Call 100 times - should return exact same values
   for _ in range(100):
       assert eth_bbo.get_momentum() == initial_momentum
       assert eth_bbo.get_spread_state() == initial_spread

   # Verify no state corruption in detectors
   assert eth_bbo.momentum_detector._state == initial_momentum
   assert eth_bbo.spread_monitor._state == initial_spread
   ```

4. **Validation criteria**:
   - No AttributeError when calling `get_bbo_handler()`
   - Proper `None` return when WebSocket disconnected
   - All public methods on handlers work when connected
   - Getters are pure (no side effects, no state corruption)
   - Multiple getter calls return identical values

**Only proceed to Phase 1 after Phase 0 passes.**

---

### Phase 1: Dry Run Validation (1-2 days)
1. Run bot in simulation mode with WebSocket data logging
2. Log all decision factors without executing trades
3. Analyze:
   - How many entries would be filtered by momentum check?
   - How would dynamic thresholds affect exit timing?
   - What is the liquidity profile at different times?
   - **Verify null handling works when WebSocket unavailable**

**Task-Level Validation Checkpoints**:

*Task 0 Validation (BBO Handler Caching)*:
- Run test script calling `get_momentum()` and `get_spread_state()` 100 times consecutively
- Verify: All 100 calls return same cached value (no analyzer recalculation side effects)
- Verify: Cached value updates only when new BBO message arrives
- Verify: No AttributeError when calling `get_bbo_handler()`
- Verify: No state corruption in momentum/spread detectors after multiple getter calls

*Task 1 Validation (Momentum Filter)*:
- Log all entry attempts with momentum states for 100 cycles
- Count filtered entries by reason (ETH BEARISH vs SOL BULLISH)
- Verify: Filter rate is between 20-40% (not too restrictive, not too permissive)
- Verify: No entries when ETH BEARISH or SOL BULLISH

*Task 2 Validation (Liquidity Sizing)*:
- Log liquidity check results for 100 entry attempts
- Count skipped trades due to insufficient liquidity
- Verify: Skip rate is <10% (liquidity usually sufficient)
- Verify: All trades that proceed have <10 bps slippage on exit

*Task 3 Validation (Dynamic Exit Thresholds)*:
- Log dynamic thresholds used for each exit decision
- Verify: Thresholds adjust based on market state (WIDENING/NARROWING/STABLE)
- Verify: No exits stuck waiting indefinitely

*Task 4 Validation (Dynamic Entry Timing)*:
- Log dynamic entry thresholds used
- Verify: Entry threshold adjusts based on momentum and spread state
- Verify: Lower threshold during favorable momentum, higher during adverse

*Task 5 Validation (Pre-Exit Liquidity Check)*:
- Log pre-exit liquidity check results
- Verify: No failed exits due to insufficient liquidity
- Verify: Exit delay <2 seconds when waiting for liquidity

### Phase 2: Small Scale Test (3-5 days)
1. Run bot with reduced size ($50 instead of $100)
2. Run 20-30 cycles
3. Compare:
   - Avg PNL per cycle vs baseline (-$0.20)
   - Win rate vs baseline
   - Partial fill rate vs baseline

### Phase 3: Full Scale Test (1 week)
1. Run bot at full size ($100)
2. Run 100+ cycles
3. Metrics to track:
   - Avg PNL per cycle (target: +$0.10)
   - Win rate (target: >60%)
   - Avg hold time (expect: similar or reduced)
   - Partial fill rate (target: <5%)

### PNL Validation Methodology

**Intermediate Metrics to Track**:

1. *Entry Quality Metrics*:
   - Avg spread at entry (bps) - lower is better with momentum filter
   - Momentum state distribution at entry (BULLISH/NEUTRAL/BEARISH)
   - Entry filter rate (%) - should be 20-40%

2. *Exit Quality Metrics*:
   - Avg spread at exit (bps) - should improve with dynamic timing
   - Dynamic threshold adjustment frequency
   - Exit reason distribution (profit_target/small_profit/stop_loss)

3. *Liquidity Metrics*:
   - Avg slippage on entry (bps)
   - Avg slippage on exit (bps)
   - Trade skip rate due to liquidity (%)

4. *Market Condition Correlation*:
   - PNL vs spread state at entry (WIDENING/NARROWING/STABLE)
   - PNL vs momentum at entry (BULLISH/NEUTRAL/BEARISH)
   - PNL vs time of day

**Distinguishing Market Conditions vs Strategy Effectiveness**:

To determine if PNL changes are due to strategy improvements vs market conditions:

1. *Control Group Analysis*:
   - Compare filtered trades (would have been taken in baseline) vs actual trades
   - If filtered trades would have lost money, momentum filter is working

2. *Volatility Regime Analysis*:
   - Group cycles by volatility (low/medium/high based on spread state)
   - Compare PNL per regime before and after optimization
   - Strategy improvement should show consistent PNL gain across regimes

3. *Counterfactual Analysis*:
   - For each trade, simulate what baseline logic would have done
   - Calculate PNL difference: Actual PNL - Baseline PNL
   - Sum differences to isolate strategy contribution from market effects

**What Constitutes "Failed" Test Requiring Rollback**:

1. *Statistical Failure Criteria* (after 100+ cycles):
   - Avg PNL per cycle < -$0.15 (worse than baseline by >25%)
   - Win rate < 40% (significant degradation)
   - Partial fill rate > 10% (new problem introduced)
   - Trade frequency drop > 50% (too aggressive filtering)

2. *Technical Failure Criteria* (immediate rollback):
   - Increase in exceptions or errors
   - WebSocket connection stability issues
   - Order submission failures
   - Null reference errors in production

3. *Market Condition Failure Criteria*:
   - If PNL only improves during specific market conditions (e.g., only during low volatility)
   - If strategy degrades during other conditions
   - This indicates overfitting to current market regime

**Rollback Triggers and Procedure**:

*Immediate Rollback* (technical issues):
- Stop bot immediately if any Technical Failure Criterion is met
- Revert to baseline code
- Investigate root cause before retry

*Gradual Rollback* (performance issues):
- If Statistical Failure Criteria met after 100 cycles
- Disable most recent feature (e.g., Task 5 if just added)
- Run another 50 cycles to isolate problematic feature
- Continue peeling back features until PNL stabilizes

*Data-Driven Rollback Decision*:
- Analyze counterfactual PNL differences
- If filtered trades would have been profitable, momentum filter is too aggressive
- If dynamic thresholds cause premature exits, revert to static
- Keep only features that show consistent positive PNL contribution

### Success Criteria
- **Primary**: Avg PNL per cycle >= $0.00 (breakeven or profitable)
- **Secondary**: Avg PNL per cycle >= $0.10 (target improvement)
- **Tertiary**: Win rate > 60%

### Rollback Plan
If PNL does not improve after Phase 3:
1. Analyze counterfactual data to identify problematic features
2. Disable momentum filter (Task 1) if over-filtering
3. Revert to static thresholds (Task 3) if dynamic timing fails
4. Keep liquidity-based sizing (Task 2) - likely beneficial regardless
5. Use intermediate metrics to guide targeted rollback

---

## Commit Strategy

### Feature Branches
1. `feature/pnl-infrastructure` - Task 0 (CRITICAL - must be merged first)
2. `feature/pnl-momentum-filter` - Task 1
3. `feature/pnl-liquidity-sizing` - Task 2
4. `feature/pnl-dynamic-exit` - Task 3
5. `feature/pnl-dynamic-entry` - Task 4
6. `feature/pnl-exit-check` - Task 5
7. `feature/pnl-csv-logging` - Task 6

### Commit Pattern
```
[PNL-OPT] Task N: Brief description

- Change 1
- Change 2

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Integration Branch
- `integration/websocket-pnl-optimization` - Merge all feature branches here for testing

---

## Success Metrics

### Quantitative Metrics
1. **Avg PNL per cycle**: Target $+0.10 (from current $-0.20)
2. **Win rate**: Target >60% (from current ~50%)
3. **Avg hold time**: Maintain <30 seconds
4. **Partial fill rate**: Target <5%

### Qualitative Metrics
1. All WebSocket data sources actively used in decisions
2. No increase in complexity (bot remains easy to understand)
3. Graceful degradation when WebSocket unavailable
4. Comprehensive logging for analysis

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| WebSocket connection loss | Medium | Low | REST fallback already implemented |
| Incorrect momentum signals | High | Medium | Dry run validation, gradual rollout |
| Liquidity check delays exit | Low | Low | Timeout on liquidity check (2s max) |
| Increased complexity | Medium | High | Comprehensive documentation, clear code structure |

### Business Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Reduced trade frequency | Medium | Medium | Lower entry threshold during favorable conditions |
| PNL does not improve | High | Low | Phased validation, rollback plan |
| Increased latency | Low | Low | All checks are synchronous and fast |

---

## Open Questions

1. **Momentum filter aggressiveness**: The Architect specified skipping when ETH BEARISH OR SOL BULLISH. Should we tighten or relax based on Phase 1 validation data?
   - **Current (Architect specification)**: Skip if ETH BEARISH (long adverse) OR SOL BULLISH (short adverse)
   - **Adjustment protocol**: If filter rate >40% in Phase 1, consider relaxing to allow NEUTRAL on adverse leg

2. **Dynamic threshold ranges**: What are reasonable min/max values for dynamic thresholds?
   - **Recommendation**: Profit target: 10-30 bps, Stop loss: -25 to -50 bps.
   - **Validation needed**: Confirm ranges are appropriate for Nado market conditions

3. **Liquidity skip threshold**: Current plan returns qty=0 when slippage would exceed 10 bps. Is this the right threshold?
   - **Architect specification**: Fixed size with skip (return qty=0)
   - **Validation needed**: Monitor skip rate in Phase 1, adjust threshold if >10% skip rate

4. **Market regime detection**: Should we add explicit market regime detection (low/medium/high volatility) to tune parameters?
   - **Consideration**: Current plan uses spread state (WIDENING/NARROWING/STABLE) as proxy
   - **Decision**: Defer to Phase 2 if needed based on PNL vs volatility correlation analysis

---

## Appendix: Code Analysis

### Infrastructure Changes (Task 0)

**Current State**:
- `_bbo_handler` is a private attribute in NadoClient (line 76)
- `_bookdepth_handler` is a private attribute in NadoClient (line 77)
- `get_bookdepth_handler()` public method exists (line 294-296)
- `get_bbo_handler()` public method DOES NOT EXIST
- `get_momentum()` and `get_spread_state()` EXIST but are IMPURE (call `on_bbo()` causing side effects)
- `_on_bbo_message()` calculates spread_state and momentum but does NOT cache them

**Required Changes**:
1. Add `get_bbo_handler()` public method to NadoClient (after line 296)
2. Add `_cached_spread_state` and `_cached_momentum` to BBOHandler.__init__() (around line 179)
3. Modify `_on_bbo_message()` to cache spread_state and momentum (around line 215)
4. Add pure getter methods `get_spread_state()` and `get_momentum()` to BBOHandler

**BBOHandler Caching Pattern** (Architect Solution):
```python
# In BBOHandler.__init__() - Add after line 179
self._cached_spread_state = "STABLE"
self._cached_momentum = "NEUTRAL"

# In _on_bbo_message() - Replace lines 215-216
# OLD (WRONG - has side effects):
# spread_state = self.spread_monitor.on_bbo(bbo)
# momentum = self.momentum_detector.on_bbo(bbo)

# NEW (CORRECT - cache results):
self._cached_spread_state = self.spread_monitor.on_bbo(bbo)
self._cached_momentum = self.momentum_detector.on_bbo(bbo)

# Pure getters (no side effects):
def get_spread_state(self) -> str:
    return self._cached_spread_state

def get_momentum(self) -> str:
    return self._cached_momentum
```

**Access Pattern After Task 0**:
```python
# CORRECT: Use public methods with null checks
eth_bbo = self.eth_client.get_bbo_handler()
if eth_bbo is not None:
    momentum = eth_bbo.get_momentum()  # Returns cached value, no side effects
    spread_state = eth_bbo.get_spread_state()  # Returns cached value, no side effects
else:
    # WebSocket unavailable - use fallback logic
    momentum = "NEUTRAL"
    spread_state = "STABLE"

# INCORRECT: Direct private attribute access (BLOCKED)
# momentum = self.eth_client._bbo_handler.get_momentum()  # DON'T DO THIS

# INCORRECT: Calling on_bbo() from getter (has side effects)
# momentum = eth_bbo.momentum_detector.on_bbo(bbo)  # DON'T DO THIS
```

### Current WebSocket Usage
- **BBOHandler**: Created and started, momentum calculated but NOT used for decisions
- **BookDepthHandler**: Created and started, slippage estimation used for sizing
- **Gap**: Momentum, spread state, liquidity data available but not integrated into trading logic

### Files to Modify
1. `/Users/botfarmer/2dex/hedge/exchanges/nado.py` - Add `get_bbo_handler()` public method (Task 0)
2. `/Users/botfarmer/2dex/hedge/exchanges/nado_bbo_handler.py` - Add `get_momentum()` and `get_spread_state()` public methods (Task 0)
3. `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Integrate all WebSocket data into trading decisions with null checks

### Files to Read (Reference)
1. `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py` - Understand BookDepth API
2. `/Users/botfarmer/2dex/hedge/exchanges/nado_websocket_client.py` - Understand WebSocket connection management

---

**End of Plan**
