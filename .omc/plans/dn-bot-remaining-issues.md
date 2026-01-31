# DN Bot Remaining Issues: IOC Order Fill Rate and Fee Impact

**Plan ID:** dn-bot-remaining-issues
**Date:** 2026-01-31
**Status:** READY FOR IMPLEMENTATION
**RALPLAN Iteration:** 3/5 (FINAL)

---

## Executive Summary

After recent bug fixes (commits 7e11a6f, 0ac7c57) that resolved subaccount address mismatch, close order IOC handling, and import paths, live testing revealed **critical remaining issues**:

1. **IOC Order Fill Rate**: ~50% failure rate with error 2056 "does not cross the book"
2. **Fee Impact CRITICAL**: 20 bps total fees (10 bps entry + 10 bps exit) with current 15 bps profit target means bot LOSES 5 bps per trade
3. **Safety Stops Triggering**: Partial fills from IOC failures trigger safety mechanism correctly but halt trading
4. **POST_ONLY Fallback Incomplete**: Current implementation treats 'OPEN' as filled, needs poll-and-wait loop
5. **Missing Rollback Strategy**: No clear criteria for detecting when to rollback changes

**Root Cause**:
- IOC orders priced at exact touch (bid/ask) have zero slippage tolerance
- Fee calculation WRONG: MIN_SPREAD_BPS=6 but breakeven is 20 bps for IOC (not 12 bps)
- POST_ONLY returns immediately with 'OPEN' status instead of polling for fills
- No volatility-regime-based slippage adjustment

**CRITICAL ECONOMICS ISSUE**:
- Current settings: 15 bps profit target, 20 bps total fees (5 bps x 4 legs)
- Result: Bot loses 5 bps on every trade
- Fix: Adjust profit targets OR use mode-aware MIN_SPREAD thresholds

---

---

## Fee Structure Documentation (CRITICAL)

### Complete Fee Breakdown

**Entry Fees (2 legs)**:
- ETH buy: 5 bps (IOC) or 2 bps (POST_ONLY)
- SOL sell: 5 bps (IOC) or 2 bps (POST_ONLY)
- **Entry Total**: 10 bps (IOC) or 4 bps (POST_ONLY)

**Exit Fees (2 legs)**:
- ETH sell: 5 bps (IOC) or 2 bps (POST_ONLY)
- SOL buy: 5 bps (IOC) or 2 bps (POST_ONLY)
- **Exit Total**: 10 bps (IOC) or 4 bps (POST_ONLY)

**Round-Trip Total**:
- IOC mode: 20 bps (5 bps x 4 legs)
- POST_ONLY mode: 8 bps (2 bps x 4 legs)

### MIN_SPREAD Breakeven Calculation

**Entry MIN_SPREAD** (must cover entry fees):
- IOC: MIN_SPREAD >= 10 bps (covers entry fees)
- POST_ONLY: MIN_SPREAD >= 4 bps (covers entry fees)

**Exit Thresholds** (must cover exit fees + minimum profit):
- IOC: profit_target >= 10 bps (exit fees) + 5 bps (min profit) = 15 bps minimum
- POST_ONLY: profit_target >= 4 bps (exit fees) + 5 bps (min profit) = 9 bps minimum

**Current Bug**:
- MIN_SPREAD_BPS = 6 allows entry at 6 bps
- Entry costs 10 bps (IOC mode)
- Bot is already -4 bps down before exit
- Exit at 15 bps profit - 10 bps exit fees = +5 bps
- Net: 6 - 10 + 15 - 10 = -1 bps (LOSS)

**After Fix**:
- IOC: MIN_SPREAD = max(6, 10) = 10 bps (covers entry fees)
- IOC: profit_target = 15 + 10 = 25 bps (covers exit fees + 5 bps profit)
- Net: 10 - 10 + 25 - 10 = +15 bps (PROFIT)

---

## Root Cause Analysis

### Issue 1: IOC Order Pricing Logic (Shared Pattern)

**Location**:
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py:597-603` - `place_ioc_order()`
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py:772-777` - `place_close_order()`

**Current Code (BOTH METHODS - IDENTICAL PATTERN)**:
```python
# place_ioc_order() lines 597-603:
if direction == 'buy':
    order_price = self._round_price_to_increment(product_id_int, best_ask)
else:
    order_price = self._round_price_to_increment(product_id_int, best_bid)

# place_close_order() lines 772-777:
if side.lower() == 'buy':
    order_price = self._round_price_to_increment(product_id_int, best_ask)
else:
    order_price = self._round_price_to_increment(product_id_int, best_bid)
```

**Problem**: Pricing at exact touch has zero slippage tolerance. Any latency or competition causes failure.

**Solution**: Add volatility-regime-based aggressive pricing:
- Base slippage: 1 bps (sound per Architect analysis)
- Volatility regimes: 0.5/1.0/2.0 bps based on spread state
- Apply to BOTH `place_ioc_order()` AND `place_close_order()`

### Issue 2: Fee Economics CRITICAL BUG

**Current Fee Structure**:
- IOC (taker): 5 bps per leg
- Round-trip: 4 legs x 5 bps = 20 bps total fees
- POST_ONLY (maker): 2 bps per leg = 8 bps total

**Breakeven Analysis (BEFORE Fix)**:
```
Entry: 5 bps (ETH buy) + 5 bps (SOL sell) = 10 bps
Exit:  5 bps (ETH sell) + 5 bps (SOL buy) = 10 bps
Total: 20 bps fees per cycle

Current profit target: 15 bps
Current MIN_SPREAD_BPS: 6 bps

Result: Bot LOSES 5 bps per trade (15 - 20 = -5)
```

**Breakeven Analysis (AFTER Fix)**:
```
IOC Mode:
- MIN_SPREAD = max(6, 20) = 20 bps (to cover fees)
- profit_target = 15 + 10 = 25 bps (fees + 5 bps profit)

POST_ONLY Mode:
- MIN_SPREAD = max(6, 8) = 8 bps (to cover fees)
- profit_target = 15 + 4 = 19 bps (fees + 5 bps profit)
```

**Problem**: Current MIN_SPREAD_BPS=6 allows entries that are guaranteed to lose money.

### Issue 3: POST_ONLY Fallback Incomplete

**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py:450-462`

**Current Code**:
```python
# Check if both filled (POST_ONLY orders return with OPEN status)
eth_filled = isinstance(eth_result, OrderResult) and eth_result.success and eth_result.status in ('FILLED', 'OPEN')
sol_filled = isinstance(sol_result, OrderResult) and sol_result.success and sol_result.status in ('FILLED', 'OPEN')

if eth_filled and sol_filled:
    self.logger.info("[ORDER] Both POST_ONLY orders placed successfully")
    # For POST_ONLY orders that are OPEN, we need to wait for fills or cancel
    # For simplicity, we'll treat OPEN as success and let the exchange handle fills
    # In production, you'd monitor for fills or cancel after timeout
```

**Problem**: Treats 'OPEN' as filled, returns immediately. No poll-and-wait loop.

**Solution**: Implement 5-second poll-and-wait with asyncio.Event callback pattern.

### Issue 4: Retry Mechanism

**Location**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py:583-700`

**Current Behavior**:
- Max retries: 3
- Retry delay: 50ms
- No price adjustment on retry
- Same price used for all retry attempts

**Problem**: If first attempt fails at touch price, subsequent attempts with same price will also fail.

### Issue 5: Safety Stop Correctness

**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py:631-686`

**Current Implementation**: WORKING AS DESIGNED

The safety mechanism correctly:
- Detects partial fills (ETH failed, SOL filled)
- Triggers emergency unwind
- Stops further cycles
- Logs warnings

**This is NOT a bug** - it's working correctly to prevent position accumulation.

### Issue 6: Missing Rollback Strategy

**Problem**: No clear criteria for detecting when changes should be rolled back.

**Solution**: Define specific metrics and trigger thresholds.

### Issue 7: Partial Fill Handling Incomplete

**Current**: Safety stop triggers on any partial fill.
**Needed**: Hybrid approach based on fill ratio thresholds.

---

## Proposed Solutions

### Priority Classification

| Priority | Issue | Impact | Files |
|----------|-------|--------|-------|
| **P0** | CRITICAL: Fee calculation fix (bot losing money) | Critical (every trade loses 5 bps) | `DN_pair_eth_sol_nado.py:789` |
| **P0** | IOC pricing with slippage tolerance (BOTH methods) | Critical (causes 50% safety stops) | `nado.py:597-603, 772-777` |
| **P0** | Volatility-regime-based slippage adjustment | Critical (optimizes fill rate) | `nado.py:597-603, 772-777` |
| **P1** | POST_ONLY poll-and-wait with asyncio.Event | High (fixes incomplete fill detection) | `DN_pair_eth_sol_nado.py:450-462` |
| **P1** | POST_ONLY IOC fallback with retry counter | High (ensures execution) | `DN_pair_eth_sol_nado.py:462+` |
| **P1** | Fee-aware profit targets (mode-aware) | High (ensures profitability) | `DN_pair_eth_sol_nado.py:1010-1013` |
| **P2** | Partial fill hybrid handling | Medium (reduces unnecessary safety stops) | `DN_pair_eth_sol_nado.py:631-686` |
| **P2** | Rollback detection strategy | Medium (operational safety) | New monitoring code |

---

## Detailed Implementation Steps

### P0-1: CRITICAL FIX - Mode-Aware Fee Breakeven Calculation

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Method**: `_check_spread_profitability()` (line 789)

**CRITICAL ECONOMICS ISSUE**:
```
CURRENT (BROKEN):
MIN_SPREAD_BPS = self.min_spread_bps  # = 6 bps
IOC fees: 20 bps total (5 bps x 4 legs)
Profit target: 15 bps
Result: 15 - 20 = -5 bps LOSS per trade

AFTER FIX:
POST_ONLY: MIN_SPREAD = max(6, 8) = 8 bps (covers 8 bps fees)
IOC: MIN_SPREAD = max(6, 20) = 20 bps (covers 20 bps fees)
```

**Change**:
```python
# CURRENT (line 789):
MIN_SPREAD_BPS = self.min_spread_bps

# PROPOSED:
# CRITICAL: Mode-aware breakeven calculation
# POST_ONLY: 2 bps x 4 legs = 8 bps breakeven
# IOC: 5 bps x 4 legs = 20 bps breakeven
if self.use_post_only:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 8)  # Maker fees
else:
    MIN_SPREAD_BPS = max(self.min_spread_bps, 20)  # Taker fees - CRITICAL FIX
```

**PNL Comparison**:
```
BEFORE FIX (Current):
- Entry at 6 bps spread, exit at 15 bps profit
- Fees: 20 bps
- Net PNL: 15 - 20 = -5 bps (LOSS)

AFTER FIX:
- Entry at 20 bps spread (minimum), exit at 25 bps profit
- Fees: 20 bps
- Net PNL: 25 - 20 = +5 bps (PROFIT)
```

**Acceptance Criteria**:
- Bot only enters trades when profit > fees
- Minimum net profit: 5 bps after all fees
- No trades with negative expected value

### P0-2: Volatility-Regime-Based IOC Pricing (SHARED PATTERN)

**Files**:
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py` - `place_ioc_order()` (lines 597-603)
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py` - `place_close_order()` (lines 772-777)

**SHARED PATTERN - Both methods have IDENTICAL pricing logic that needs the SAME fix**:

#### BEFORE/AFTER: place_ioc_order() (lines 597-603)

**BEFORE (Current Code)**:
```python
# Lines 597-603 of nado.py
if direction == 'buy':
    order_price = self._round_price_to_increment(product_id_int, best_ask)
else:
    order_price = self._round_price_to_increment(product_id_int, best_bid)
```

**AFTER (Replace with this block)**:
```python
# Lines 597-603 of nado.py - REPLACEMENT BLOCK
# Volatility-regime-based slippage tolerance
# Base slippage: 1 bps (sound per Architect analysis)
slippage_bps = 1

# Try to get spread state for volatility adjustment
try:
    if hasattr(self, 'get_bbo_handler') and self.get_bbo_handler():
        spread_state = self.get_bbo_handler().get_spread_state()
        if spread_state == "WIDENING":
            slippage_bps = 2  # More aggressive in volatile conditions
        elif spread_state == "NARROWING":
            slippage_bps = 0.5  # Less aggressive when spreads are tight
        # STABLE: use default 1 bps
except Exception as e:
    # WebSocket unavailable, use default 1 bps
    self.logger.debug(f"[IOC] Using default slippage: {e}")

# Apply slippage tolerance
if direction == 'buy':
    order_price_raw = best_ask * (Decimal('1') + Decimal(str(slippage_bps)) / Decimal('10000'))
else:
    order_price_raw = best_bid * (Decimal('1') - Decimal(str(slippage_bps)) / Decimal('10000'))
order_price = self._round_price_to_increment(product_id_int, order_price_raw)
```

#### BEFORE/AFTER: place_close_order() (lines 772-777)

**BEFORE (Current Code)**:
```python
# Lines 772-777 of nado.py
if side.lower() == 'buy':
    order_price = self._round_price_to_increment(product_id_int, best_ask)
else:
    order_price = self._round_price_to_increment(product_id_int, best_bid)
```

**AFTER (Replace with this block)**:
```python
# Lines 772-777 of nado.py - REPLACEMENT BLOCK
# Volatility-regime-based slippage tolerance
# Base slippage: 1 bps (sound per Architect analysis)
slippage_bps = 1

# Try to get spread state for volatility adjustment
try:
    if hasattr(self, 'get_bbo_handler') and self.get_bbo_handler():
        spread_state = self.get_bbo_handler().get_spread_state()
        if spread_state == "WIDENING":
            slippage_bps = 2  # More aggressive in volatile conditions
        elif spread_state == "NARROWING":
            slippage_bps = 0.5  # Less aggressive when spreads are tight
        # STABLE: use default 1 bps
except Exception as e:
    # WebSocket unavailable, use default 1 bps
    self.logger.debug(f"[CLOSE] Using default slippage: {e}")

# Apply slippage tolerance
if side.lower() == 'buy':
    order_price_raw = best_ask * (Decimal('1') + Decimal(str(slippage_bps)) / Decimal('10000'))
else:
    order_price_raw = best_bid * (Decimal('1') - Decimal(str(slippage_bps)) / Decimal('10000'))
order_price = self._round_price_to_increment(product_id_int, order_price_raw)
```

**Implementation Notes**:
1. This is a SHARED pattern - apply to BOTH methods
2. Volatility regimes: 0.5/1.0/2.0 bps based on spread state
3. Base slippage of 1 bps is sound per Architect analysis
4. Falls back to 1 bps if WebSocket unavailable
5. Exception handling prevents crashes if get_bbo_handler() fails

**Acceptance Criteria**:
- Both `place_ioc_order()` AND `place_close_order()` use same logic
- IOC orders fill on first attempt >90% of the time
- Safety stops reduced from ~50% to <10% of cycles
- Average slippage cost < $0.01 per $100 notional

### P0-3: Retry with Progressive Price Improvement

**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
**Methods**: `place_ioc_order()` (line 586), `place_close_order()` (line 761)

**Change**: Add progressive price improvement inside retry loop

```python
# Add inside retry loop, AFTER fetching best_bid/best_ask:
# place_ioc_order() - add after line 588
# place_close_order() - add after line 763

# Progressive price improvement on retry
# Attempt 0: base slippage (1 bps)
# Attempt 1: +2 bps (3 bps total)
# Attempt 2: +4 bps (5 bps total)
retry_improvement_bps = retry_count * 2  # 0, 2, 4 bps progressive improvement
total_slippage_bps = slippage_bps + retry_improvement_bps

# Apply combined slippage
if direction == 'buy':  # or side.lower() == 'buy'
    order_price_raw = best_ask * (Decimal('1') + Decimal(str(total_slippage_bps)) / Decimal('10000'))
else:
    order_price_raw = best_bid * (Decimal('1') - Decimal(str(total_slippage_bps)) / Decimal('10000'))
order_price = self._round_price_to_increment(product_id_int, order_price_raw)
```

**Acceptance Criteria**:
- Retry attempts succeed >50% of the time
- Maximum additional slippage: 4 bps ($0.02 per $100)
- No safety stops due to partial fills

### P1-1: POST_ONLY Poll-and-Wait with asyncio.Event

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Method**: `place_simultaneous_orders()` (lines 450-462)

**CRITICAL**: Current code treats 'OPEN' as filled. Need poll-and-wait loop.

```python
# CURRENT (lines 450-462):
eth_filled = isinstance(eth_result, OrderResult) and eth_result.success and eth_result.status in ('FILLED', 'OPEN')
sol_filled = isinstance(sol_result, OrderResult) and sol_result.success and sol_result.status in ('FILLED', 'OPEN')

if eth_filled and sol_filled:
    self.logger.info("[ORDER] Both POST_ONLY orders placed successfully")
    # For POST_ONLY orders that are OPEN, we need to wait for fills or cancel
    # For simplicity, we'll treat OPEN as success and let the exchange handle fills

# PROPOSED:
POST_ONLY_TIMEOUT = 5.0  # 5 seconds max wait
POLL_INTERVAL = 0.1  # 100ms between polls
eth_fill_event = asyncio.Event()
sol_fill_event = asyncio.Event()

async def poll_eth_fill():
    """Poll ETH order for fill with callback signaling."""
    try:
        for _ in range(int(POST_ONLY_TIMEOUT / POLL_INTERVAL)):
            if eth_result.order_id:
                order_info = await self.eth_client.get_order_info(eth_result.order_id)
                if order_info and order_info.remaining_size == 0:
                    eth_fill_event.set()
                    return
            await asyncio.sleep(POLL_INTERVAL)
    except Exception as e:
        self.logger.warning(f"[ORDER] Error polling ETH fill: {e}")

async def poll_sol_fill():
    """Poll SOL order for fill with callback signaling."""
    try:
        for _ in range(int(POST_ONLY_TIMEOUT / POLL_INTERVAL)):
            if sol_result.order_id:
                order_info = await self.sol_client.get_order_info(sol_result.order_id)
                if order_info and order_info.remaining_size == 0:
                    sol_fill_event.set()
                    return
            await asyncio.sleep(POLL_INTERVAL)
    except Exception as e:
        self.logger.warning(f"[ORDER] Error polling SOL fill: {e}")

# Start polling both orders concurrently
poll_task = asyncio.gather(poll_eth_fill(), poll_sol_fill())

# Wait for both to fill or timeout
try:
    await asyncio.wait_for(asyncio.gather(
        eth_fill_event.wait(),
        sol_fill_event.wait()
    ), timeout=POST_ONLY_TIMEOUT)
    self.logger.info("[ORDER] Both POST_ONLY orders filled successfully")
    # Cancel polling tasks
    poll_task.cancel()
except asyncio.TimeoutError:
    self.logger.warning("[ORDER] POST_ONLY timeout, checking fill status...")
    # Check actual fill status
    eth_order_info = await self.eth_client.get_order_info(eth_result.order_id) if eth_result.order_id else None
    sol_order_info = await self.sol_client.get_order_info(sol_result.order_id) if sol_result.order_id else None

    eth_filled = eth_order_info and eth_order_info.remaining_size == 0
    sol_filled = sol_order_info and sol_order_info.remaining_size == 0

    if not (eth_filled and sol_filled):
        # Fall back to IOC (see P1-2)
        pass
```

**Acceptance Criteria**:
- POST_ONLY orders poll for actual fills (not just 'OPEN' status)
- 5-second timeout with 100ms poll intervals
- asyncio.Event callback pattern for signaling

### P1-2: POST_ONLY IOC Fallback with Recursive Retry

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Method**: `place_simultaneous_orders()` (after line 462)

**Change**: Add attempt counter and mode flag for recursive fallback

```python
# Add method parameter for attempt tracking:
async def place_simultaneous_orders(
    self,
    eth_direction: str,
    sol_direction: str,
    attempt_count: int = 0  # NEW: Track attempts for recursion
) -> tuple[OrderResult, OrderResult]:

# ... existing POST_ONLY placement code ...

# After poll-and-wait (line 462), add:
if not (eth_filled and sol_filled):
    # Cancel any open POST_ONLY orders
    if eth_result.status == 'OPEN' and eth_result.order_id:
        await self.eth_client.cancel_order(eth_result.order_id)
    if sol_result.status == 'OPEN' and sol_result.order_id:
        await self.sol_client.cancel_order(sol_result.order_id)

    # Recursive fallback with attempt limit
    if attempt_count < 2:
        self.logger.warning(
            f"[ORDER] POST_ONLY incomplete (attempt {attempt_count + 1}/2), "
            f"falling back to IOC"
        )
        # Switch to IOC mode and retry
        original_mode = self.use_post_only
        self.use_post_only = False
        try:
            return await self.place_simultaneous_orders(
                eth_direction, sol_direction, attempt_count + 1
            )
        finally:
            self.use_post_only = original_mode  # Restore mode
    else:
        self.logger.error("[ORDER] Max attempts exceeded, aborting cycle")
        return (
            OrderResult(success=False, error_message="POST_ONLY and IOC both failed"),
            OrderResult(success=False, error_message="POST_ONLY and IOC both failed")
        )
```

**Acceptance Criteria**:
- Max 2 attempts (POST_ONLY + IOC fallback)
- Mode flag restored after recursion
- Clear error on max attempts exceeded

### P1-3: Fee-Aware Exit Thresholds (Mode-Aware)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Method**: `_calculate_dynamic_exit_thresholds()` (lines 1010-1013)

**Change**: Factor in REMAINING exit fees when calculating profit targets

**IMPORTANT CLARIFICATION**: By the time we exit, we have ALREADY PAID entry fees. The exit thresholds must account for REMAINING exit fees only.

**Fee Structure Breakdown**:
```
Entry Phase (already paid when we reach exit logic):
- ETH buy: 5 bps (IOC) or 2 bps (POST_ONLY)
- SOL sell: 5 bps (IOC) or 2 bps (POST_ONLY)
- Entry Total: 10 bps (IOC) or 4 bps (POST_ONLY) - ALREADY PAID

Exit Phase (yet to be paid):
- ETH sell: 5 bps (IOC) or 2 bps (POST_ONLY)
- SOL buy: 5 bps (IOC) or 2 bps (POST_ONLY)
- Exit Total: 10 bps (IOC) or 4 bps (POST_ONLY) - REMAINING

Round-Trip Total: 20 bps (IOC) or 8 bps (POST_ONLY)
```

**Why Exit Thresholds Account for Remaining Fees Only**:
- Entry at 20 bps spread (covers 10 bps entry fees)
- Current position: +10 bps unrealized (before exit fees)
- Exit at X bps profit
- Net = 10 (entry spread) + X (exit profit) - 10 (exit fees) = X bps
- Therefore: exit_threshold = desired_net_profit + remaining_exit_fees

```python
# CURRENT (lines 1010-1013):
profit_target = 15
quick_exit = 5
stop_loss = 30

# PROPOSED:
# Fee-aware profit targets (remaining fees only)
# Entry fees ALREADY PAID: 10 bps (IOC) or 4 bps (POST_ONLY)
# Exit fees REMAINING: 10 bps (IOC) or 4 bps (POST_ONLY)
remaining_exit_fees_bps = 10 if not self.use_post_only else 4

# Ensure minimum 5 bps profit AFTER remaining exit fees
BASE_PROFIT = 15  # Base profit target
MIN_NET_PROFIT = 5  # Minimum profit after fees

profit_target = BASE_PROFIT + remaining_exit_fees_bps  # 25 for IOC, 19 for POST_ONLY
quick_exit = MIN_NET_PROFIT + remaining_exit_fees_bps  # 15 for IOC, 9 for POST_ONLY
stop_loss = 30  # Stop loss remains absolute

self.logger.info(
    f"[EXIT] Fee-aware thresholds: profit_target={profit_target}bps, "
    f"quick_exit={quick_exit}bps (remaining_exit_fees={remaining_exit_fees_bps}bps)"
)
```

**PNL Examples**:
```
IOC Mode:
- Entry at 20 bps spread (paid 10 bps entry fees, +10 bps unrealized)
- Exit at 25 bps profit
- Remaining exit fees: 10 bps
- Net: 10 (entry spread) + 25 (exit profit) - 10 (exit fees) = +25 bps

POST_ONLY Mode:
- Entry at 8 bps spread (paid 4 bps entry fees, +4 bps unrealized)
- Exit at 19 bps profit
- Remaining exit fees: 4 bps
- Net: 4 (entry spread) + 19 (exit profit) - 4 (exit fees) = +19 bps
```

**Acceptance Criteria**:
- Exit thresholds ensure minimum 5 bps profit AFTER remaining exit fees
- Mode-aware calculation (POST_ONLY vs IOC)
- No unprofitable exits
- Documentation clarifies entry fees are already paid

### P2-1: Partial Fill Hybrid Handling with Complete Retry Logic

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Method**: Safety stop handling (around line 631-686)

**Change**: Implement hybrid approach based on fill ratio with COMPLETE retry logic

```python
# Add new method to DN_pair_eth_sol_nado.py
def _handle_partial_fill(
    self,
    eth_filled: bool,
    sol_filled: bool,
    eth_fill_qty: Decimal,
    sol_fill_qty: Decimal,
    eth_target_qty: Decimal,
    sol_target_qty: Decimal,
    eth_direction: str,
    sol_direction: str
) -> tuple[bool, str, Optional[Coroutines]]:
    """
    Hybrid partial fill handling with complete retry logic.

    Fill ratio thresholds:
    - < 20% filled: Abort and unwind
    - 20-80% filled: Retry remaining quantities
    - > 80% filled: Accept and proceed
    - > 50% imbalance: Emergency unwind

    Returns:
        (should_proceed, reason, retry_coroutine)
    """
    eth_fill_ratio = float(eth_fill_qty / eth_target_qty) if eth_target_qty > 0 else 0
    sol_fill_ratio = float(sol_fill_qty / sol_target_qty) if sol_target_qty > 0 else 0
    avg_fill_ratio = (eth_fill_ratio + sol_fill_ratio) / 2

    # Check for dangerous imbalance
    imbalance = abs(eth_fill_ratio - sol_fill_ratio)
    if imbalance > 0.5:
        return False, f"Dangerous fill imbalance: ETH={eth_fill_ratio:.1%}, SOL={sol_fill_ratio:.1%}", None

    # Hybrid decision logic
    if avg_fill_ratio < 0.2:
        return False, f"Insufficient fill: {avg_fill_ratio:.1%} < 20%", None
    elif avg_fill_ratio < 0.8:
        # Retry remaining quantities - COMPLETE IMPLEMENTATION
        retry_qty_eth = eth_target_qty - eth_fill_qty
        retry_qty_sol = sol_target_qty - sol_fill_qty

        self.logger.info(
            f"[PARTIAL] {avg_fill_ratio:.1%} filled, retrying remaining: "
            f"ETH={retry_qty_eth}, SOL={retry_qty_sol}"
        )

        # Create retry coroutine using existing entry logic
        async def retry_remaining():
            return await self.execute_entry(retry_qty_eth, retry_qty_sol)

        return True, "Partial fill accepted, retrying remaining", retry_remaining()
    else:
        # > 80% filled: accept and proceed
        return True, f"Fill acceptable: {avg_fill_ratio:.1%}", None

# Use in safety check (replace existing partial fill handling):
should_proceed, reason, retry_task = self._handle_partial_fill(
    eth_filled=eth_filled,
    sol_filled=sol_filled,
    eth_fill_qty=eth_filled_qty if eth_filled else Decimal('0'),
    sol_fill_qty=sol_filled_qty if sol_filled else Decimal('0'),
    eth_target_qty=eth_expected_qty,
    sol_target_qty=sol_expected_qty,
    eth_direction='buy' if self.position_eth == 0 else 'sell',
    sol_direction='sell' if self.position_sol == 0 else 'buy'
)

if not should_proceed:
    # Trigger safety unwind
    self.logger.error(f"[SAFETY] {reason}, triggering emergency unwind")
    await self._emergency_unwind()
    return
elif retry_task:
    # Execute retry for remaining quantities
    self.logger.info(f"[RETRY] Executing retry task: {reason}")
    try:
        await retry_task
    except Exception as e:
        self.logger.error(f"[RETRY] Failed: {e}")
        await self._emergency_unwind()
        return
```

**Complete Retry Logic Specification**:
1. Calculate remaining quantities: `retry_qty = target_qty - filled_qty`
2. Call `execute_entry()` with remaining quantities
3. Use same direction parameters as original attempt
4. If retry fails, trigger emergency unwind
5. Log all retry attempts with quantities

**Acceptance Criteria**:
- < 20% filled: Abort and unwind
- 20-80% filled: Retry remaining quantities via `execute_entry()`
- > 80% filled: Accept and proceed
- > 50% imbalance: Emergency unwind
- Retry uses existing `execute_entry()` method with calculated quantities

### P2-2: Rollback Detection Strategy

**File**: New monitoring module or add to `DN_pair_eth_sol_nado.py`

**Metrics to Monitor**:
```python
class RollbackMonitor:
    """Monitor for rollback trigger conditions."""

    # Rollback triggers
    SAFETY_STOP_THRESHOLD = 0.30  # 30% safety stop rate
    NEGATIVE_PNL_THRESHOLD = -10  # -10 bps avg PNL per cycle
    MIN_FILLS_FOR_ROLLBACK = 5  # Need at least 5 cycles

    def __init__(self):
        self.cycle_count = 0
        self.safety_stop_count = 0
        self.pnl_history = []

    def record_cycle(self, had_safety_stop: bool, pnl_bps: float):
        """Record cycle results."""
        self.cycle_count += 1
        if had_safety_stop:
            self.safety_stop_count += 1
        self.pnl_history.append(pnl_bps)

    def should_rollback(self) -> tuple[bool, str]:
        """Check if rollback should be triggered."""
        if self.cycle_count < self.MIN_FILLS_FOR_ROLLBACK:
            return False, "Insufficient data"

        # Check safety stop rate
        safety_stop_rate = self.safety_stop_count / self.cycle_count
        if safety_stop_rate > self.SAFETY_STOP_THRESHOLD:
            return True, (
                f"Rollback: Safety stop rate {safety_stop_rate:.1%} > "
                f"{self.SAFETY_STOP_THRESHOLD:.1%} threshold"
            )

        # Check average PNL
        avg_pnl = sum(self.pnl_history) / len(self.pnl_history)
        if avg_pnl < self.NEGATIVE_PNL_THRESHOLD:
            return True, (
                f"Rollback: Avg PNL {avg_pnl:.1f} bps < "
                f"{self.NEGATIVE_PNL_THRESHOLD} bps threshold"
            )

        return False, "Metrics healthy"
```

**Acceptance Criteria**:
- Monitor safety stop rate and average PNL
- Trigger rollback if:
  - Safety stop rate > 30%
  - Average PNL < -10 bps
- Minimum 5 cycles before rollback decision

---

## Verification Methods

### 1. Unit Tests

Create `/Users/botfarmer/2dex/tests/test_ioc_pricing.py`:

```python
# Test slippage tolerance calculation
def test_ioc_pricing_with_slippage():
    # Verify 1 bps slippage is applied correctly

# Test retry price improvement
def test_retry_price_improvement():
    # Verify 0, 2, 4 bps improvement on retries

# Test POST_ONLY fallback
def test_post_only_fallback_to_ioc():
    # Verify fallback triggers after timeout

# Test mode-aware fee calculation
def test_mode_aware_min_spread():
    # Verify POST_ONLY: 8 bps, IOC: 20 bps
```

### 2. Integration Tests

Create `/Users/botfarmer/2dex/tests/test_dn_pair_fill_rate.py`:

```python
async def test_ioc_fill_rate():
    # Run 20 cycles, measure fill rate
    # Target: >90% first-attempt fills

async def test_post_only_fee_savings():
    # Run 10 POST_ONLY cycles
    # Verify fee reduction vs IOC

async def test_volatility_regime_adjustment():
    # Verify slippage adjusts based on spread state
```

### 3. Paper Trading Test

**Test Plan**:
1. Run 20 cycles with $100 notional
2. Measure:
   - IOC fill rate (target >90%)
   - Safety stop rate (target <10%)
   - Average fees per cycle
   - Profitability AFTER fees (target >5 bps net)

### 4. Live Trading Test (Small Size)

**After paper trading success**:
1. Run 5 cycles with $100 notional on mainnet
2. Monitor:
   - No safety stops
   - Fees correct per mode
   - Net profitability >0

---

## Success Metrics

| Metric | Current | Target | Measurement | CSV Field |
|--------|---------|--------|-------------|-----------|
| IOC First-Attempt Fill Rate | ~50% | >90% | Count fills / total attempts | `ioc_first_attempt_fill_rate` |
| Safety Stop Rate | ~50% | <10% | Count safety stops / total cycles | `safety_stop_rate` |
| Net Profit per Cycle (IOC) | -5 bps | >5 bps | PNL with fees | `net_profit_bps` |
| Net Profit per Cycle (POST_ONLY) | N/A | >10 bps | PNL with fees | `net_profit_bps` |
| Retry Success Rate | N/A | >50% | Retries that fill / total retries | `retry_success_rate` |
| POST_ONLY Fill Rate | N/A | >70% | Fills / placed | `post_only_fill_rate` |
| Average Slippage Cost | N/A | <$0.01/$100 | Per $100 notional | `slippage_cost_usd` |
| POST_ONLY Avg Wait Time | N/A | <2s | Seconds to fill | `post_only_avg_wait_time` |
| Gross Profit (before fees) | 15 bps | >=25 bps (IOC) | Spread captured | `gross_profit_bps` |
| Total Fees (IOC) | 20 bps | 20 bps | Entry (10) + Exit (10) | `total_fees_bps` |
| Total Fees (POST_ONLY) | N/A | 8 bps | Entry (4) + Exit (4) | `total_fees_bps` |

**CRITICAL**: Current bot loses 5 bps per trade. After fix, minimum 5 bps profit per trade.

---

## Risk Mitigation

### Risk 1: Increased Slippage Costs

**Mitigation**: Start with 1 bps slippage tolerance (P0-2), monitor actual slippage via CSV logs. Volatility-regime adjustment caps at 2 bps in extreme conditions.

### Risk 2: POST_ONLY Lower Fill Rate

**Mitigation**: Implement IOC fallback (P1-2) with 5-second timeout and max 2 attempts.

### Risk 3: Price Improvement Too Aggressive

**Mitigation**: Cap improvement at 4 bps (2 retries * 2 bps = 4 bps total).

### Risk 4: Fee Calculation Changes Reduce Trade Frequency

**Mitigation**: Monitor skip rate. If >30%, consider adjusting MIN_SPREAD_BPS base value.

---

## Rollback Plan

### Automated Rollback Triggers

Use `RollbackMonitor` class (P2-2) to detect:
- Safety stop rate > 30%
- Average PNL < -10 bps over 5+ cycles

### Manual Rollback Steps

If issues arise after deployment:

1. **Revert P0-1**: Set MIN_SPREAD_BPS back to 6 (WARNING: will lose money)
2. **Revert P0-2**: Set slippage_bps = 0 (original behavior)
3. **Revert P0-3**: Remove price improvement logic
4. **Disable POST_ONLY**: Set `use_post_only=False` in bot config
5. **Restore Original Thresholds**: Revert P1-3 changes

**Rollback Command**:
```bash
git revert <commit-hash>
```

**IMPORTANT**: Rolling back P0-1 (fee fix) will cause bot to lose money on every trade. Only rollback if new issues are worse than losing 5 bps per trade.

---

## Edge Cases and Error Handling

### Edge Case 1: get_bbo_handler() Returns None

**Location**: P0-2 (both `place_ioc_order()` and `place_close_order()`)

**Condition**: `self.get_bbo_handler()` returns None or method doesn't exist

**Fallback Behavior**:
```python
# Try to get spread state for volatility adjustment
try:
    if hasattr(self, 'get_bbo_handler') and self.get_bbo_handler():
        spread_state = self.get_bbo_handler().get_spread_state()
        # ... regime adjustment ...
    else:
        # Handler not available, use default 1 bps
        slippage_bps = 1
except Exception as e:
    # Any error, use default 1 bps
    slippage_bps = 1
    self.logger.debug(f"[SLIPPAGE] Using default 1 bps: {e}")
```

**Result**: Always falls back to 1 bps default if WebSocket unavailable

### Edge Case 2: Only One POST_ONLY Order Fills

**Location**: P1-1 (POST_ONLY poll-and-wait)

**Condition**: ETH fills immediately, SOL remains open after timeout

**Handling**:
```python
# After timeout, check individual fill status
eth_filled = eth_order_info and eth_order_info.remaining_size == 0
sol_filled = sol_order_info and sol_order_info.remaining_size == 0

if not (eth_filled and sol_filled):
    # Cancel any remaining open orders
    if not eth_filled and eth_result.order_id:
        await self.eth_client.cancel_order(eth_result.order_id)
    if not sol_filled and sol_result.order_id:
        await self.sol_client.cancel_order(sol_result.order_id)

    # Fall back to IOC for BOTH legs (ensures balanced position)
    self.logger.warning("[POST_ONLY] Partial fill, canceling and falling back to IOC")
    # Trigger P1-2 fallback logic
```

**Result**: Both legs retried via IOC to ensure position balance

### Edge Case 3: WebSocket Disconnects During Order

**Location**: P0-2 (volatility regime detection)

**Condition**: WebSocket disconnects while fetching spread state

**Handling**:
```python
try:
    if hasattr(self, 'get_bbo_handler') and self.get_bbo_handler():
        spread_state = self.get_bbo_handler().get_spread_state()
        # ... regime adjustment ...
except Exception as e:
    # WebSocket unavailable or disconnected
    slippage_bps = 1  # Safe default
    self.logger.warning(f"[WEBSOCKET] Disconnected, using default slippage: {e}")
```

**Alternative**: Use REST API BBO as fallback (if available):
```python
# Fallback to REST API BBO
try:
    bbo = await self.eth_client.get_bbo_rest(product_id)
    spread_bps = (bbo['ask'] - bbo['bid']) / bbo['bid'] * 10000
    if spread_bps > 2:  # Wide spread indicates volatility
        slippage_bps = 2
except:
    slippage_bps = 1
```

**Result**: Order continues with conservative default slippage

### Edge Case 4: Order Not Found on Poll

**Location**: P1-1 (POST_ONLY poll-and-wait)

**Condition**: `get_order_info()` returns None or raises "order not found"

**Handling**:
```python
async def poll_eth_fill():
    try:
        for _ in range(int(POST_ONLY_TIMEOUT / POLL_INTERVAL)):
            if eth_result.order_id:
                order_info = await self.eth_client.get_order_info(eth_result.order_id)
                if order_info and order_info.remaining_size == 0:
                    eth_fill_event.set()
                    return
                elif order_info is None:
                    # Order not found, assume canceled or rejected
                    self.logger.warning(f"[POLL] ETH order {eth_result.order_id} not found")
                    return
            await asyncio.sleep(POLL_INTERVAL)
    except Exception as e:
        self.logger.warning(f"[POLL] Error polling ETH: {e}")
        # Don't set event, will trigger timeout fallback
```

**Result**: Timeout triggers IOC fallback after 5 seconds

### Edge Case 5: Cancel Order Fails During Fallback

**Location**: P1-2 (POST_ONLY IOC fallback)

**Condition**: Attempting to cancel open POST_ONLY order fails

**Handling**:
```python
# Cancel any open POST_ONLY orders
try:
    if eth_result.status == 'OPEN' and eth_result.order_id:
        await self.eth_client.cancel_order(eth_result.order_id)
except Exception as e:
    self.logger.error(f"[CANCEL] Failed to cancel ETH order: {e}")
    # Proceed with IOC anyway, exchange will reject if order already filled

try:
    if sol_result.status == 'OPEN' and sol_result.order_id:
        await self.sol_client.cancel_order(sol_result.order_id)
except Exception as e:
    self.logger.error(f"[CANCEL] Failed to cancel SOL order: {e}")
```

**Result**: IOC attempt proceeds, exchange handles duplicate/cancelled orders

### Edge Case 6: Price Rounding Error After Slippage

**Location**: P0-2 (slippage calculation)

**Condition**: Slippage-adjusted price rounds to same value as original

**Handling**:
```python
order_price_raw = best_ask * (Decimal('1') + Decimal(str(slippage_bps)) / Decimal('10000'))
order_price = self._round_price_to_increment(product_id_int, order_price_raw)

# Verify price actually moved
if direction == 'buy' and order_price <= best_ask:
    # Rounding caused no change, add one tick
    order_price = self._round_price_to_increment(
        product_id_int,
        order_price_raw * Decimal('1.0001')  # Add small increment
    )
    self.logger.debug(f"[SLIPPAGE] Rounding adjusted price upward")
```

**Result**: Ensures aggressive pricing even with rounding artifacts

---

## Instrumentation and Monitoring

### Required Metrics to Log

#### 1. IOC First-Attempt Fill Rate

**Log Format**:
```python
self.logger.info(
    f"[METRICS] IOC first-attempt fill rate: "
    f"{first_attempt_fills}/{first_attempt_total} = {fill_rate:.1%}"
)
```

**CSV Fields**:
- `ioc_first_attempt_fills` - Count of successful first attempts
- `ioc_first_attempt_total` - Total first attempts
- `ioc_first_attempt_fill_rate` - Percentage (0.0-1.0)

**Target**: >90% fill rate on first attempt

#### 2. Slippage Cost Tracking

**Log Format**:
```python
# After order fills
expected_price = best_ask if direction == 'buy' else best_bid
slippage_cost = abs(actual_price - expected_price) * quantity
self.logger.info(
    f"[METRICS] Slippage cost: ${slippage_cost:.4f} "
    f"(expected: ${expected_price}, actual: ${actual_price}, qty: {quantity})"
)
```

**CSV Fields**:
- `slippage_cost_usd` - Actual slippage cost in USD
- `slippage_bps` - Slippage in basis points
- `slippage_volatility_regime` - STABLE/NARROWING/WIDENING

**Target**: Average < $0.01 per $100 notional (1 bps)

#### 3. POST_ONLY Fill Rate

**Log Format**:
```python
self.logger.info(
    f"[METRICS] POST_ONLY fill rate: "
    f"{post_only_fills}/{post_only_total} = {fill_rate:.1%}, "
    f"avg_wait_time: {avg_wait_time:.2f}s"
)
```

**CSV Fields**:
- `post_only_fills` - Count of POST_ONLY orders that filled
- `post_only_total` - Total POST_ONLY orders placed
- `post_only_fill_rate` - Percentage (0.0-1.0)
- `post_only_avg_wait_time` - Average seconds to fill

**Target**: >70% fill rate, <2s average wait time

#### 4. Safety Stop Rate

**Log Format**:
```python
self.logger.info(
    f"[METRICS] Safety stop rate: "
    f"{safety_stops}/{total_cycles} = {stop_rate:.1%}"
)
```

**CSV Fields**:
- `safety_stops` - Count of safety stops triggered
- `total_cycles` - Total trading cycles attempted
- `safety_stop_rate` - Percentage (0.0-1.0)
- `safety_stop_reason` - Partial fill / imbalance / timeout

**Target**: <10% safety stop rate

#### 5. Fee-Aware Profit Tracking

**Log Format**:
```python
self.logger.info(
    f"[METRICS] Cycle PNL (fee-aware): "
    f"gross_profit={gross_profit_bps}bps, "
    f"fees={total_fees_bps}bps, "
    f"net_profit={net_profit_bps}bps, "
    f"mode={'POST_ONLY' if use_post_only else 'IOC'}"
)
```

**CSV Fields**:
- `gross_profit_bps` - Profit before fees
- `entry_fees_bps` - Fees paid on entry (10 or 4 bps)
- `exit_fees_bps` - Fees paid on exit (10 or 4 bps)
- `total_fees_bps` - Total fees (20 or 8 bps)
- `net_profit_bps` - Profit after fees
- `order_mode` - IOC or POST_ONLY

**Target**: Minimum +5 bps net profit per cycle

#### 6. Retry Success Rate

**Log Format**:
```python
self.logger.info(
    f"[METRICS] Retry success rate: "
    f"{retry_successes}/{retry_attempts} = {retry_rate:.1%}, "
    f"avg_retry_attempts: {avg_retries:.2f}"
)
```

**CSV Fields**:
- `retry_attempts` - Count of retry attempts
- `retry_successes` - Retries that resulted in full fill
- `retry_success_rate` - Percentage (0.0-1.0)
- `avg_retry_count` - Average retries per cycle

**Target**: >50% retry success rate

### CSV Log Structure

**New File**: `/Users/botfarmer/2dex/logs/dn_bot_metrics.csv`

**Columns**:
```
timestamp,cycle_id,order_mode,ioc_first_attempt_fill,slippage_cost_usd,
slippage_bps,volatility_regime,post_only_fill_rate,post_only_wait_time,
safety_stop,safety_stop_reason,gross_profit_bps,entry_fees_bps,
exit_fees_bps,net_profit_bps,retry_attempt,retry_success
```

**Example Row**:
```
2026-01-31T12:34:56Z,123,IOC,1,0.005,1.0,STABLE,0.85,1.2,0,,
18,10,10,8,0,1
```

### Alert Thresholds

**Warning Level** (log warning):
- IOC fill rate < 80%
- Slippage cost > $0.02 per $100
- Safety stop rate > 15%

**Critical Level** (log error + consider rollback):
- IOC fill rate < 50%
- Safety stop rate > 30%
- Average net profit < -5 bps over 5 cycles

---

## Definition of Done

- [ ] P0-1: Mode-aware MIN_SPREAD_BPS calculation (20 bps IOC, 8 bps POST_ONLY)
- [ ] P0-2: Volatility-regime-based slippage in BOTH `place_ioc_order()` AND `place_close_order()`
- [ ] P0-3: Progressive price improvement on retry (0, 2, 4 bps)
- [ ] P1-1: POST_ONLY poll-and-wait with asyncio.Event (5-second timeout)
- [ ] P1-2: POST_ONLY IOC fallback with recursive retry (max 2 attempts)
- [ ] P1-3: Fee-aware exit thresholds (mode-aware profit targets)
- [ ] P2-1: Partial fill hybrid handling (fill ratio thresholds)
- [ ] P2-2: Rollback detection strategy with monitoring
- [ ] Unit tests created and passing
- [ ] Paper trading: 20 cycles with >90% fill rate, >5 bps net profit
- [ ] Live trading: 5 cycles with no safety stops, positive PNL
- [ ] CSV logs verify fee calculation and profitability
- [ ] Code reviewed and documented

---

## File Change Summary

| File | Lines Changed | Type | Priority |
|------|---------------|------|----------|
| `hedge/exchanges/nado.py` | 597-603, 772-777 | Modify (P0) | P0 |
| `hedge/DN_pair_eth_sol_nado.py` | 789 | Modify (P0) | P0 |
| `hedge/DN_pair_eth_sol_nado.py` | 450-462+ | Modify (P1) | P1 |
| `hedge/DN_pair_eth_sol_nado.py` | 1010-1013 | Modify (P1) | P1 |
| `hedge/DN_pair_eth_sol_nado.py` | 631-686 | Modify (P2) | P2 |
| `tests/test_ioc_pricing.py` | New | Create | - |
| `tests/test_dn_pair_fill_rate.py` | New | Create | - |

---

---

**PLAN_READY: .omc/plans/dn-bot-remaining-issues.md**
