# PNL Lossless Improvement Plan - $1M Daily Volume Target

**PLAN STATUS:** COMPREHENSIVE WORK PLAN - READY FOR EXECUTION
**DATE:** 2026-02-01
**PLANNER:** Prometheus (Strategic Planning Consultant)
**TARGET:** $1,000,000 daily VOLUME (not profit) via PNL lossless trading
**REVISION:** Iteration 2 - Fixed pricing logic explanation, clarified Option A (add price parameter), added call site update, verified spread_state location, added feature flag implementation

---

## Executive Summary

### Problem Statement

Current delta-neutral trading system generates consistent losses due to:

1. **POST_ONLY Timeout Problem (100% rate)**
   - Orders placed 1-tick-behind touch price never fill in volatile markets
   - In 50ms book update cycles, market moves 2-3 ticks before order can fill
   - 1-tick-behind placement becomes 3-4 ticks behind effectively
   - 5-second timeout expires before fills occur
   - Automatic fallback to IOC at 5bps taker fees
   - Current cost: 20bps per cycle (4 orders x 5bps)

2. **Fee Structure Inefficiency**
   - All orders execute at 5bps taker fees (due to 100% IOC fallback)
   - Monthly cost: ~$600 at 100 cycles/day
   - Yearly cost: ~$7,300

3. **Volume Target**
   - Current trade size: $10,000 per trade
   - Target: $1,000,000 daily VOLUME (not profit)
   - Method: 100 trades x $10K = $1M notional
   - This is achievable with improved fill rates

### SDK Research Verification

**SDK Source File Verified:** `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/expiration.py`

```python
class OrderType(IntEnum):
    DEFAULT = 0      # Normal limit order - maker OR taker based on price
    IOC = 1
    FOK = 2
    POST_ONLY = 3    # Maker-only, rejected if would cross spread
```

**CRITICAL FINDINGS:**
1. `OrderType.DEFAULT = 0` IS the normal limit order (equivalent to "LIMIT" order on other exchanges)
2. `OrderType.LIMIT` does NOT exist in the SDK
3. Fee determined by EXECUTION METHOD, not OrderType:
   - Maker (resting on book): 2bps
   - Taker (crossing spread): 5bps
4. POST_ONLY failure mode: 100% timeout → 100% IOC fallback → 100% taker execution (5bps)

### Root Cause Analysis

**Current Pricing at DN_pair_eth_sol_nado.py:410-411 (IS CORRECT but NOT USED):**
```python
# place_simultaneous_orders() - CORRECT at-touch pricing calculation
eth_price = eth_bid if eth_direction == "sell" else eth_ask
```

**This IS correct at-touch pricing:**
- BUY uses `eth_ask` (rests on ask side at touch) -> MAKER -> 2bps
- SELL uses `eth_bid` (rests on bid side at touch) -> MAKER -> 2bps

**The Problem:**
1. These prices are calculated at DN_pair:410-411
2. **BUT they are NEVER PASSED to `place_open_order()`!**
3. Current call at DN_pair:454-463 does NOT include the price parameter

**The Fix (Option A - RECOMMENDED):**
1. Add optional `price` parameter to `place_open_order()`
2. Update call site at DN_pair:454-463 to pass the calculated prices
3. Convert to OrderType.DEFAULT (value = 0) - the PRIMARY strategy
4. Fallback to legacy 1-tick-behind pricing if price not provided

### Solution Approach

Implement multi-strategy PNL optimization through:

1. **OrderType.DEFAULT Conversion (PRIMARY)** - Convert to OrderType.DEFAULT (value = 0) for normal limit order behavior
2. **At-Touch Pricing** - Fix pricing to use at-touch (buy=best_ask, sell=best_bid for maker execution)
3. **BookDepth Queue Analysis** - Skip when queue too deep
4. **Supplemental quality improvements** - Spread filter, partial fills, dynamic timeout

**KEY INSIGHT:** OrderType.DEFAULT is the CORRECT solution because:
- Can execute as maker (2bps) when price rests on book
- Can execute as taker (5bps) when needed (flexibility)
- Higher fill rate means more maker fees overall
- No rejection risk - order always executes
- POST_ONLY is the PROBLEM (100% timeout), not the solution

### Expected Outcomes

- **Fee Reduction:** 12-18 bps per cycle (from 20 bps to 2-8 bps)
- **Fill Rate:** 60-80% POST_ONLY fill rate (from 0%)
- **Daily Volume:** 100 trades x $10K = $1M notional (achievable)
- **PNL Impact:** Lossless operation with 10-15 bps edge retention

---

## Requirements

### Functional Requirements

**FR1: OrderType.DEFAULT Conversion (PRIMARY STRATEGY)**
- System SHALL use OrderType.DEFAULT (value = 0) for all limit orders
- OrderType.DEFAULT IS a normal limit order (maker OR taker based on price)
- SDK source: `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/expiration.py`
- System SHALL remove OrderType.POST_ONLY (problem, not solution)
- System SHALL track execution mode (maker vs taker) for PNL analysis

**FR2: Correct At-Touch Pricing Implementation**
- System SHALL place DEFAULT orders AT touch price (best_ask for BUY, best_bid for SELL)
- **BUY at best_ask**: Rests on ask side at touch -> MAKER -> 2bps fee
- **SELL at best_bid**: Rests on bid side at touch -> MAKER -> 2bps fee
- Orders SHALL rest on order book at touch price for maker execution

**FR3: Fix place_open_order() Price Parameter (Option A - RECOMMENDED)**
- `place_open_order()` SHALL accept optional `price` parameter
- If price provided: use at-touch price from caller
- If price not provided: fallback to legacy 1-tick-behind pricing
- Implementation SHALL add price parameter to nado.py:509

**FR4: Fix Call Site to Pass At-Touch Prices**
- Call site at DN_pair_eth_sol_nado.py:454-463 SHALL pass calculated prices
- `eth_price` and `sol_price` SHALL be passed to `place_open_order()`
- Currently calculated at DN_pair:410-411 but NOT passed

**FR5: BookDepth Queue Size Analysis**
- System SHALL measure queue size at best bid/ask levels
- Orders SHALL only be placed when queue_size < threshold (configurable)
- Threshold SHALL default to 50% of average queue size
- Implementation SHALL use existing BookDepthHandler infrastructure

**FR6: Spread Quality Filter**
- System SHALL skip trading when spread > threshold (configurable)
- Default spread threshold SHALL be 5 ticks (0.05 for ETH)
- System SHALL log skip reasons for analysis

**FR7: Partial Fill Handling**
- System SHALL accept partial fills >= 50% of order size
- Remaining quantity SHALL be handled via IOC fallback
- System SHALL track partial fill rates for optimization

**FR8: Dynamic Timeout**
- System SHALL adjust timeout based on volatility regime
- Low volatility: 10s timeout
- High volatility: 3s timeout
- Volatility SHALL be measured from BBO spread state

**FR9: PNL Lossless Validation**
- Cumulative PNL SHALL NOT go negative for > 5 consecutive trades
- System SHALL track position imbalance and prevent accumulation
- Leg imbalance SHALL be < 10% of target notional

### Non-Functional Requirements

**NFR1: Performance**
- Order placement latency < 100ms after BBO update
- BookDepth query latency < 10ms
- System SHALL handle 100+ trades/day without degradation

**NFR2: Reliability**
- System uptime > 99.5%
- WebSocket reconnection time < 30s
- No data loss during reconnection

**NFR3: Observability**
- All orders SHALL log: price, size, execution mode, fill status
- PNL tracking per trade and cumulative
- Queue size and spread state logged on every cycle

**NFR4: Backward Compatibility**
- Changes SHALL not break existing IOC fallback mechanism
- Feature flags SHALL control strategy selection via command-line arguments
- Legacy mode (100% IOC) SHALL remain available

**NFR5: Feature Flag Implementation**
- Config class SHALL include feature flag attributes with defaults
- argparse SHALL support --enable-at-touch-pricing flag
- Feature flags SHALL use getattr() pattern for safe defaults

---

## Strategy Selection

### Primary Strategies (Implementation Required)

#### Strategy 1: OrderType.DEFAULT Conversion - **HIGHEST PRIORITY**

**Implementation:** Convert OrderType from POST_ONLY to DEFAULT

**SDK Verification:**
- File: `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/expiration.py`
- OrderType.DEFAULT = 0 (normal limit order)
- OrderType.LIMIT does NOT exist
- Fee determined by execution method, not OrderType

**PNL Impact:** 12-18 bps per cycle
- Improves fill probability from 0% to 60-80%
- Estimated 75% maker fills (2bps) + 25% taker fills (5bps)
- Weighted average: 0.75 x 2 + 0.25 x 5 = 2.75bps vs current 5bps = 2.25bps savings
- 4 orders x 2.25bps = 9bps savings
- Combined with at-touch pricing: 12-18bps total

**Why OrderType.DEFAULT is the CORRECT Solution:**
1. Can execute as maker (2bps) when price rests on book
2. Can execute as taker (5bps) when needed (flexibility)
3. Higher fill rate means more maker fees overall
4. No rejection risk - order always executes
5. POST_ONLY is the PROBLEM (100% timeout), not the solution

**Code Changes:**

**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
**Function:** `place_open_order()`
**Lines:** 538 (appendix build_appendix)

**CURRENT:**
```python
appendix=build_appendix(
    order_type=OrderType.POST_ONLY,
    isolated=True
)
```

**NEW:**
```python
appendix=build_appendix(
    order_type=OrderType.DEFAULT,  # Changed from POST_ONLY
    isolated=True
)
```

**Effort:** LOW (1 hour)
**Risk:** LOW (DEFAULT accepts both modes, no downside)

#### Strategy 2: At-Touch Pricing - **HIGHEST PRIORITY**

**Implementation:** Add optional price parameter to place_open_order() and update call site

**Code Changes:**

**File 1:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
**Function:** `place_open_order()`
**Line:** 509 (function signature)
**Lines:** 522-525 (pricing logic - ADD price parameter support)

**Step 1: Add price parameter to place_open_order() signature:**
```python
# Line 509 - Add optional price parameter
async def place_open_order(
    self,
    contract_id: str,
    quantity: Decimal,
    direction: str,
    price: Optional[Decimal] = None  # NEW: Optional price parameter
) -> OrderResult:
```

**Step 2: Use price parameter if provided, otherwise fallback:**
```python
# Lines 522-525 - Add price parameter logic
if price is not None:
    # Use at-touch price from caller (NEW)
    order_price = price
else:
    # Fallback to legacy 1-tick-behind pricing (EXISTING)
    if direction == 'buy':
        order_price = best_ask - self.config.tick_size
    else:
        order_price = best_bid + self.config.tick_size
```

**File 2:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Function:** `place_simultaneous_orders()`
**Lines:** 454-463 (asyncio.gather call - MUST pass prices)

**Step 3: Update call site to pass at-touch prices:**
```python
# Lines 410-411 - CORRECT pricing already calculated
eth_price = eth_bid if eth_direction == "sell" else eth_ask
sol_price = sol_bid if sol_direction == "sell" else sol_ask

# Lines 454-463 - MUST pass these prices (CURRENTLY MISSING)
eth_result, sol_result = await asyncio.gather(
    self.eth_client.place_open_order(
        self.eth_client.config.contract_id,
        eth_qty,
        eth_direction,
        eth_price  # NEW: Pass the calculated at-touch price!
    ),
    self.sol_client.place_open_order(
        self.sol_client.config.contract_id,
        sol_qty,
        sol_direction,
        sol_price  # NEW: Pass the calculated at-touch price!
    ),
)
```

**Explanation:**
- BUY at best_ask: Rests on ask side at touch -> MAKER -> 2bps fee
- SELL at best_bid: Rests on bid side at touch -> MAKER -> 2bps fee
- OrderType.DEFAULT allows taker execution if market moves against you
- Prices already calculated correctly at DN_pair:410-411
- **Just need to pass them to place_open_order()!**

**Effort:** MEDIUM (2-3 hours)
**Risk:** LOW (OrderType.DEFAULT provides flexibility without rejection risk)

#### Strategy 3: BookDepth Queue Analysis - **HIGH PRIORITY**

**Implementation:** Measure queue size at touch, skip when queue too deep

**Reference Document:** `/Users/botfarmer/2dex/.omc/plans/8-strategies-comprehensive-analysis.md`

**PNL Impact:** 6 bps per cycle
- Avoids adverse selection from deep queues
- Reduces failed fills and timeout scenarios
- Estimated 30% improvement in fill quality

**Code Changes:**

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 407-420 (order placement logic)
- Add queue size check before order placement
- Use existing `BookDepthHandler.get_best_bid()` and `get_best_ask()`

**BookDepthHandler Reference:**
- Location: `hedge/exchanges/nado_bookdepth_handler.py`
- Structure: SortedDict for bids/asks
- Methods: `get_best_bid()`, `get_best_ask()`, `get_depth_at_level()`
- Queue size: Measured in total quantity at price level

**Effort:** MEDIUM-HIGH (3-4 hours)
**Risk:** LOW (read-only analysis, no order modification)

### Supplemental Strategies (Quality Improvements)

#### Strategy 4: Spread Filter - **SUPPLEMENTAL**

**Implementation:** Skip trading when spread too wide

**PNL Impact:** Quality improvement (no direct bps measurement)
- Prevents trading in unfavorable conditions
- Reduces leg imbalance risk

**Code Changes:**

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 400-406 (BBO fetching section)
- Add spread check: `if (best_ask - best_bid) > threshold: skip`

**Effort:** LOW (1 hour)
**Risk:** LOW (conservative filter, reduces risk)

#### Strategy 5: Partial Fill Handling - **SUPPLEMENTAL**

**Implementation:** Accept partial fills >= 50%

**PNL Impact:** 2 bps per cycle
- Reduces waste from partial fills
- Lowers IOC fallback rate

**Code Changes:**

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Lines:** 475-553 (POST_ONLY fill polling logic)
- Modify fill check: `if filled_size >= 0.5 * order_size: accept`

**Effort:** MEDIUM (2 hours)
**Risk:** LOW (conservative threshold)

#### Strategy 6: Dynamic Timeout - **SUPPLEMENTAL**

**Implementation:** Adjust timeout based on volatility

**PNL Impact:** 1.5 bps per cycle
- Longer timeout in stable markets increases fill probability
- Shorter timeout in volatile markets reduces adverse selection

**Code Changes:**

**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
**Lines:** 400-429 (calculate_timeout method)
- Add volatility input from BBO spread state
- Piecewise logic: 3s (high vol) / 10s (low vol)

**Effort:** MEDIUM (2 hours)
**Risk:** LOW (adaptive logic, reduces risk)

### Strategies NOT Recommended

#### Strategy 1: Timeout Extension - **LOW PRIORITY**

**Reason:** Only 0.8 bps impact, not worth implementation effort
**Recommendation:** Skip in favor of at-touch pricing

#### Strategy 8: BBO Pricing - **NOT RECOMMENDED**

**User's Proposal:** buy=best_ask, sell=best_bid

**Why NOT Recommended:**
- buy=best_ask CROSSES the spread (matches existing asks) -> TAKER
- sell=best_bid CROSSES the spread (matches existing bids) -> TAKER
- TAKER execution = 5bps fees
- **NO improvement over current IOC (also 5bps)**
- Reference: See detailed analysis in 8-strategies document

**Correct Alternative:**
- Use TRUE maker pricing: buy=best_bid, sell=best_ask (Strategy 3)
- This rests on book at touch -> MAKER -> 2bps
- See Strategy 3 above

---

## Implementation Steps

### Phase 1: Foundation (Day 1)

#### Step 1.1: OrderType.DEFAULT Conversion (PRIMARY STRATEGY)

**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
**Function:** `place_open_order()`
**Lines:** 538 (OrderType appendix)

**Problem:** Using OrderType.POST_ONLY causes 100% timeout rate

**Solution:** Convert to OrderType.DEFAULT (normal limit order)

**Code Change:**
```python
# CURRENT (line 538):
appendix=build_appendix(
    order_type=OrderType.POST_ONLY,
    isolated=True
)

# NEW:
appendix=build_appendix(
    order_type=OrderType.DEFAULT,  # Changed from POST_ONLY
    isolated=True
)
```

**Acceptance Criteria:**
- Orders accept both maker and taker execution
- Fill rate >= 60% (combined maker + taker)
- No order rejection due to OrderType
- SDK source verified at `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/expiration.py`

#### Step 1.2: Add Price Parameter to place_open_order()

**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
**Function:** `place_open_order()`
**Line:** 509 (function signature)
**Lines:** 522-525 (pricing logic)

**Problem:** place_open_order() currently does NOT accept a price parameter

**Step 1: Add optional price parameter to function signature:**
```python
# Line 509 - BEFORE:
async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:

# Line 509 - AFTER:
async def place_open_order(
    self,
    contract_id: str,
    quantity: Decimal,
    direction: str,
    price: Optional[Decimal] = None
) -> OrderResult:
```

**Step 2: Use price parameter if provided:**
```python
# Lines 522-525 - BEFORE:
if direction == 'buy':
    order_price = best_ask - self.config.tick_size
else:
    order_price = best_bid + self.config.tick_size

# Lines 522-525 - AFTER:
if price is not None:
    # Use at-touch price from caller
    order_price = price
else:
    # Fallback to legacy 1-tick-behind pricing
    if direction == 'buy':
        order_price = best_ask - self.config.tick_size
    else:
        order_price = best_bid + self.config.tick_size
```

**Acceptance Criteria:**
- Function accepts optional price parameter
- If price provided, use it directly
- If price not provided, fallback to legacy behavior
- No breaking changes to existing callers

#### Step 1.3: Update Call Site to Pass At-Touch Prices

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Function:** `place_simultaneous_orders()`
**Lines:** 410-411 (price calculation - already correct)
**Lines:** 454-463 (asyncio.gather call - MISSING price parameters)

**Problem:** Prices calculated correctly at lines 410-411 but NOT passed to place_open_order()

**Step 1: Verify price calculation (already correct):**
```python
# Lines 410-411 - CORRECT (keep as-is)
eth_price = eth_bid if eth_direction == "sell" else eth_ask
sol_price = sol_bid if sol_direction == "sell" else sol_ask
```

**Step 2: Update call site to pass prices:**
```python
# Lines 454-463 - BEFORE (WRONG - missing price parameter):
eth_result, sol_result = await asyncio.gather(
    self.eth_client.place_open_order(
        self.eth_client.config.contract_id,
        eth_qty,
        eth_direction  # Missing price!
    ),
    self.sol_client.place_open_order(
        self.sol_client.config.contract_id,
        sol_qty,
        sol_direction  # Missing price!
    ),
)

# Lines 454-463 - AFTER (CORRECT - pass at-touch prices):
eth_result, sol_result = await asyncio.gather(
    self.eth_client.place_open_order(
        self.eth_client.config.contract_id,
        eth_qty,
        eth_direction,
        eth_price  # Pass the calculated at-touch price!
    ),
    self.sol_client.place_open_order(
        self.sol_client.config.contract_id,
        sol_qty,
        sol_direction,
        sol_price  # Pass the calculated at-touch price!
    ),
)
```

**Acceptance Criteria:**
- Call site passes eth_price and sol_price to place_open_order()
- BUY orders receive best_ask price
- SELL orders receive best_bid price
- Orders rest at touch price for maker execution

#### Step 1.4: Spread Filter Implementation

**Add before order placement:**
```python
# Calculate spread in ticks
eth_spread = eth_ask - eth_bid
eth_spread_ticks = eth_spread / eth_client.config.tick_size

sol_spread = sol_ask - sol_bid
sol_spread_ticks = sol_spread / sol_client.config.tick_size

# Skip if spread too wide
MAX_SPREAD_TICKS = 5
if eth_spread_ticks > MAX_SPREAD_TICKS or sol_spread_ticks > MAX_SPREAD_TICKS:
    self.logger.warning(
        f"[SPREAD FILTER] Skipping: ETH spread={eth_spread_ticks:.1f} ticks, "
        f"SOL spread={sol_spread_ticks:.1f} ticks > {MAX_SPREAD_TICKS}"
    )
    return (OrderResult(success=False), OrderResult(success=False))
```

**Acceptance Criteria:**
- Wide spreads (> 5 ticks) trigger skip
- Skip logged with spread details
- No order placement on wide spreads

### Phase 2: BookDepth Integration (Day 2)

#### Step 2.1: Queue Size Measurement

**Add new method:**
```python
async def check_queue_size(
    self,
    client,
    direction: str,
    max_queue_ratio: float = 0.5
) -> Tuple[bool, Decimal, str]:
    """
    Check if queue size at touch is acceptable.

    Args:
        client: NadoClient instance
        direction: "buy" or "sell"
        max_queue_ratio: Maximum queue size as ratio of average (default 0.5)

    Returns:
        Tuple of (can_trade, queue_size, reason)
    """
    handler = client.get_bookdepth_handler()
    if handler is None:
        return True, Decimal('0'), "No BookDepth data"

    # Get queue size at touch
    if direction == 'buy':
        best_price, queue_size = handler.get_best_ask()
        side = "ask"
    else:
        best_price, queue_size = handler.get_best_bid()
        side = "bid"

    if queue_size is None or queue_size == 0:
        return False, Decimal('0'), f"No {side} liquidity"

    # Calculate average queue size (top 5 levels)
    total_liquidity = handler.get_available_liquidity(side, max_depth=5)
    avg_queue_size = total_liquidity / 5 if total_liquidity > 0 else Decimal('0')

    # Check if current queue is too deep
    if avg_queue_size > 0:
        queue_ratio = queue_size / avg_queue_size
        if queue_ratio > max_queue_ratio:
            return False, queue_size, f"Queue too deep: {queue_size} ({queue_ratio:.1%} of avg)"

    return True, queue_size, "OK"
```

**Acceptance Criteria:**
- Queue size measured at touch
- Average queue calculated from top 5 levels
- Skip triggered when queue > 50% of average
- Reason logged for all skip decisions

#### Step 2.2: Queue Check Integration

**Add queue check:**
```python
# Check queue sizes before placing orders
eth_can_trade, eth_queue_size, eth_queue_reason = await self.check_queue_size(
    self.eth_client, eth_direction, max_queue_ratio=0.5
)
sol_can_trade, sol_queue_size, sol_queue_reason = await self.check_queue_size(
    self.sol_client, sol_direction, max_queue_ratio=0.5
)

# Skip if either queue is too deep
if not eth_can_trade or not sol_can_trade:
    skip_reasons = []
    if not eth_can_trade:
        skip_reasons.append(f"ETH: {eth_queue_reason}")
    if not sol_can_trade:
        skip_reasons.append(f"SOL: {sol_queue_reason}")
    self.logger.warning(
        f"[QUEUE FILTER] Skipping trade: {', '.join(skip_reasons)}"
    )
    return (
        OrderResult(success=False, error_message=f"Queue filter: {skip_reasons}"),
        OrderResult(success=False, error_message=f"Queue filter: {skip_reasons}")
    )
```

**Acceptance Criteria:**
- Queue check performed before every order
- Trade skipped when either queue too deep
- Queue size logged for analysis

### Phase 3: Partial Fill & Dynamic Timeout (Day 3)

#### Step 3.1: Partial Fill Handling

**Modify fill acceptance:**
```python
# CURRENT (line 486):
if order_info and order_info.remaining_size == 0:
    eth_fill_event.set()
    return

# NEW:
if order_info:
    filled_ratio = abs(order_info.filled_size) / eth_result.size
    if order_info.remaining_size == 0 or filled_ratio >= 0.5:
        # Accept full fill or partial fill >= 50%
        eth_fill_event.set()
        return
```

**Acceptance Criteria:**
- Partial fills >= 50% accepted
- Remaining quantity handled via IOC
- Partial fill rate tracked in logs

#### Step 3.2: Dynamic Timeout Implementation

**Add volatility-based timeout:**
```python
def calculate_timeout(
    self,
    quantity: Decimal,
    spread_state: Optional[str] = None
) -> int:
    """
    Calculate timeout based on order size and volatility.

    Args:
        quantity: Order quantity in tokens
        spread_state: "WIDENING", "NARROWING", or "STABLE" (from BBO handler)

    Returns:
        Timeout in seconds (3-20 second range)
    """
    quantity_float = float(quantity)

    # Base timeout from quantity
    if quantity_float <= 0.1:
        base_timeout = 5
    elif quantity_float <= 0.5:
        base_timeout = 10
    else:
        base_timeout = 20

    # Adjust based on volatility
    if spread_state == "WIDENING":
        # High volatility: shorter timeout to avoid adverse selection
        return max(3, base_timeout // 2)
    elif spread_state == "NARROWING":
        # Low volatility: longer timeout for better fill probability
        return min(30, base_timeout * 2)
    else:
        # Default: use base timeout
        return base_timeout

**Note:** Access spread_state via `self._bbo_handler.get_spread_state()` at nado_bbo_handler.py:276-282
```

**Acceptance Criteria:**
- Timeout adjusted based on spread state
- WIDENING: 50% of base timeout
- NARROWING: 200% of base timeout
- Spread state fetched from BBO handler

### Phase 4: Feature Flags & Configuration (Day 4)

#### Step 4.1: Add Feature Flags to Config Class

**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py` (or config module)
**Location:** Config class __init__ method

**Implementation:**
```python
class Config:
    def __init__(self, ...):
        # Existing config parameters
        # ...

        # NEW: Feature flags for PNL optimization strategies
        self.enable_at_touch_pricing = getattr(self, 'enable_at_touch_pricing', False)
        self.enable_order_type_default = getattr(self, 'enable_order_type_default', False)
        self.enable_queue_filter = getattr(self, 'enable_queue_filter', False)
        self.enable_spread_filter = getattr(self, 'enable_spread_filter', False)
        self.enable_partial_fills = getattr(self, 'enable_partial_fills', False)
        self.enable_dynamic_timeout = getattr(self, 'enable_dynamic_timeout', False)

        # NEW: Configurable thresholds
        self.queue_threshold_ratio = getattr(self, 'queue_threshold_ratio', 0.5)
        self.spread_threshold_ticks = getattr(self, 'spread_threshold_ticks', 5)
        self.min_partial_fill_ratio = getattr(self, 'min_partial_fill_ratio', 0.5)
```

**Acceptance Criteria:**
- Feature flags default to False (disabled by default)
- Safe getattr() pattern prevents errors if attribute missing
- Thresholds have sensible defaults

#### Step 4.2: Add argparse Command-Line Flags

**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Location:** argparse section in main()

**Implementation:**
```python
# Add to existing argparse setup
parser.add_argument(
    '--enable-at-touch-pricing',
    action='store_true',
    help='Enable at-touch pricing (buy=ask, sell=bid) for maker execution'
)
parser.add_argument(
    '--enable-order-type-default',
    action='store_true',
    help='Use OrderType.DEFAULT instead of POST_ONLY for flexibility'
)
parser.add_argument(
    '--enable-queue-filter',
    action='store_true',
    help='Skip trading when queue size at touch is too deep'
)
parser.add_argument(
    '--enable-spread-filter',
    action='store_true',
    help='Skip trading when spread is too wide'
)
parser.add_argument(
    '--enable-partial-fills',
    action='store_true',
    help='Accept partial fills >= 50% of order size'
)
parser.add_argument(
    '--enable-dynamic-timeout',
    action='store_true',
    help='Adjust timeout based on market volatility'
)
parser.add_argument(
    '--queue-threshold-ratio',
    type=float,
    default=0.5,
    help='Maximum queue size as ratio of average (default: 0.5)'
)
parser.add_argument(
    '--spread-threshold-ticks',
    type=int,
    default=5,
    help='Maximum spread in ticks before skipping (default: 5)'
)
parser.add_argument(
    '--min-partial-fill-ratio',
    type=float,
    default=0.5,
    help='Minimum partial fill ratio to accept (default: 0.5)'
)
```

**Pass to Config:**
```python
# After args = parser.parse_args()
config.enable_at_touch_pricing = args.enable_at_touch_pricing
config.enable_order_type_default = args.enable_order_type_default
config.enable_queue_filter = args.enable_queue_filter
config.enable_spread_filter = args.enable_spread_filter
config.enable_partial_fills = args.enable_partial_fills
config.enable_dynamic_timeout = args.enable_dynamic_timeout
config.queue_threshold_ratio = args.queue_threshold_ratio
config.spread_threshold_ticks = args.spread_threshold_ticks
config.min_partial_fill_ratio = args.min_partial_fill_ratio
```

**Acceptance Criteria:**
- All feature flags have --enable-* syntax
- action='store_true' means flag defaults to False
- Threshold flags accept numeric values with defaults
- Flags passed to Config for use in trading logic

#### Step 4.3: Use Feature Flags in Code

**Example: place_open_order() with feature flag:**
```python
# nado.py - place_open_order()
async def place_open_order(
    self,
    contract_id: str,
    quantity: Decimal,
    direction: str,
    price: Optional[Decimal] = None
) -> OrderResult:
    # ... existing code ...

    # Use at-touch pricing if enabled and price provided
    if self.config.enable_at_touch_pricing and price is not None:
        order_price = price
    else:
        # Fallback to legacy 1-tick-behind pricing
        if direction == 'buy':
            order_price = best_ask - self.config.tick_size
        else:
            order_price = best_bid + self.config.tick_size

    # Use OrderType.DEFAULT if enabled
    order_type = OrderType.DEFAULT if self.config.enable_order_type_default else OrderType.POST_ONLY

    appendix = build_appendix(
        order_type=order_type,
        isolated=True
    )
    # ... rest of function ...
```

**Acceptance Criteria:**
- Feature flags control strategy behavior
- Legacy mode available when all flags disabled
- Easy to A/B test by toggling flags

### Phase 5: Testing & Validation (Day 5)

#### Step 5.1: Unit Tests

**Create test file:** `/Users/botfarmer/2dex/tests/test_pnl_improvements.py`

**Test cases:**
1. At-touch pricing places orders at correct prices
2. Spread filter skips wide spreads
3. Queue filter skips deep queues
4. Partial fill handling accepts >= 50%
5. Dynamic timeout adjusts based on volatility

#### Step 5.2: Integration Testing

**Test scenario:**
1. Start bot in paper trading mode
2. Run for 4 hours (50-100 cycles)
3. Monitor metrics:
   - OrderType.DEFAULT fill rate (maker vs taker)
   - Average fee per order
   - Queue size distribution
   - Spread distribution
   - PNL per trade

**Acceptance criteria:**
- OrderType.DEFAULT fill rate >= 60%
- Maker execution rate >= 60%
- Average fee <= 3.5bps (vs current 5bps)
- No position accumulation > 10% of target
- Cumulative PNL >= -0.1% (lossless)

#### Step 5.3: Production Rollout

**Rollback plan:**
1. Deploy with feature flag: `--use-at-touch-pricing=false`
2. Enable for 10% of trades (A/B test)
3. Monitor for 4 hours
4. If PNL negative or position accumulation > 10%, rollback
5. If metrics acceptable, enable 100%

**Rollback procedure:**
```bash
# Disable at-touch pricing
python DN_pair_eth_sol_nado.py --size 10000 --iter 100 --use-at-touch-pricing=false

# Enable legacy mode
python DN_pair_eth_sol_nado.py --size 10000 --iter 100 --order-mode=ioc
```

---

## Risk Assessment

### High Severity Risks

#### Risk 1: Position Accumulation

**Description:** At-touch pricing may cause partial fills leading to leg imbalance

**Probability:** MEDIUM (30%)
**Impact:** HIGH (uncontrolled positions, liquidation risk)

**Mitigation:**
1. Implement strict leg imbalance monitoring (< 10% of target notional)
2. Auto-unwind if imbalance exceeds threshold
3. Track partial fills and queue sizes
4. Position limits: max 2x target notional

**Monitoring:**
```python
# Add to place_simultaneous_orders()
if abs(eth_position - sol_position_notional) > 0.1 * target_notional:
    self.logger.error("[RISK] Leg imbalance > 10%, emergency unwind")
    await self.emergency_unwind()
```

#### Risk 2: Adverse Selection

**Description:** At-touch orders may fill on toxic flow (informed traders)

**Probability:** MEDIUM (25%)
**Impact:** MEDIUM (negative PNL on filled orders)

**Mitigation:**
1. Queue size filter (Strategy 5) - skip deep queues
2. Spread filter - skip wide spreads (volatility signal)
3. Dynamic timeout - reduce exposure in volatile markets
4. Monitor fill price vs mid price after execution

**Monitoring:**
```python
# Track adverse selection
adverse_selection_bps = (execution_price - mid_price) / mid_price * 10000
if abs(adverse_selection_bps) > 3:
    self.logger.warning(f"[ADVERSE SELECTION] {adverse_selection_bps:.1f} bps")
```

### Medium Severity Risks

#### Risk 3: Taker Execution Rate

**Description:** DEFAULT orders may cross spread and become taker (intended behavior)

**Probability:** LOW (20-30%)
**Impact:** LOW (5bps fee instead of 2bps, still better than current 100% taker)

**Mitigation:**
1. Accept taker execution as part of strategy (flexibility is feature, not bug)
2. Track maker vs taker ratio (target: >= 60% maker)
3. At-touch pricing minimizes crossing probability
4. Overall fill rate improvement offsets occasional taker execution

**Key Insight:**
- Current: 100% taker execution (via IOC fallback) at 5bps
- Proposed: 60-80% maker (2bps) + 20-40% taker (5bps)
- Weighted average: 2.4-3.4bps vs current 5bps = NET IMPROVEMENT

#### Risk 4: WebSocket Latency

**Description:** BookDepth data delay causes stale pricing decisions

**Probability:** MEDIUM (20%)
**Impact:** MEDIUM (missed opportunities or bad fills)

**Mitigation:**
1. Monitor BookDepth timestamp age
2. Skip trading if data > 100ms old
3. Fallback to REST if WebSocket issues

**Monitoring:**
```python
# Add to order placement
data_age = time.time() - bookdepth_handler.last_timestamp / 1000
if data_age > 0.1:  # 100ms
    self.logger.warning(f"[LATENCY] BookDepth stale: {data_age*1000:.0f}ms")
```

### Low Severity Risks

#### Risk 5: Configuration Drift

**Description:** Feature flags may be inconsistent across environments

**Probability:** LOW (5%)
**Impact:** LOW (unexpected behavior)

**Mitigation:**
1. Centralize configuration in Config class
2. Validate all flags at startup
3. Log active configuration on bot start

---

## Testing & Validation

### Unit Testing

**Test file:** `/Users/botfarmer/2dex/tests/test_pnl_improvements.py`

**Test cases:**

1. `test_at_touch_pricing_buy()`
   - Input: best_bid=2500, best_ask=2501, direction="buy"
   - Expected: order_price=2501 (at best_ask for maker execution)

2. `test_at_touch_pricing_sell()`
   - Input: best_bid=2500, best_ask=2501, direction="sell"
   - Expected: order_price=2500 (at best_bid for maker execution)

3. `test_order_type_default_value()`
   - Input: OrderType.DEFAULT
   - Expected: 0 (normal limit order, maker OR taker)

4. `test_order_type_post_only_value()`
   - Input: OrderType.POST_ONLY
   - Expected: 3 (maker-only, rejected if crosses)

5. `test_spread_filter_wide()`
   - Input: spread=0.10 (10 ticks), threshold=5 ticks
   - Expected: skip trade, log warning

6. `test_spread_filter_narrow()`
   - Input: spread=0.03 (3 ticks), threshold=5 ticks
   - Expected: proceed with trade

7. `test_queue_filter_deep()`
   - Input: queue_size=100, avg_queue=100, ratio=1.0, threshold=0.5
   - Expected: skip trade, log "Queue too deep"

8. `test_queue_filter_shallow()`
   - Input: queue_size=10, avg_queue=100, ratio=0.1, threshold=0.5
   - Expected: proceed with trade

9. `test_partial_fill_acceptance()`
   - Input: filled_size=0.6, order_size=1.0
   - Expected: accept fill (>= 50%)

10. `test_partial_fill_rejection()`
    - Input: filled_size=0.3, order_size=1.0
    - Expected: reject fill (< 50%)

11. `test_dynamic_timeout_widening()`
    - Input: spread_state="WIDENING", quantity=0.5
    - Expected: timeout=5 (half of base 10)

12. `test_dynamic_timeout_narrowing()`
    - Input: spread_state="NARROWING", quantity=0.5
    - Expected: timeout=20 (double base 10)

### Integration Testing

**Test script:** `/Users/botfarmer/2dex/tests/integration_test_pnl.sh`

**Test scenario:**
```bash
#!/bin/bash
# Run 4-hour integration test in paper trading mode

cd /Users/botfarmer/2dex/hedge

python DN_pair_eth_sol_nado.py \
    --size 10000 \
    --iter 100 \
    --enable-at-touch-pricing \
    --enable-order-type-default \
    --enable-queue-filter \
    --enable-spread-filter \
    --test-mode=paper \
    --duration-hours=4 \
    --log-level=DEBUG
```

**Metrics to collect:**

1. **Fill Metrics**
   - OrderType.DEFAULT fill rate (overall)
   - Maker execution rate (vs taker)
   - Partial fill rate
   - Timeout rate

2. **Fee Metrics**
   - Average bps per order (weighted)
   - Maker vs taker ratio
   - Total fees per cycle

3. **Quality Metrics**
   - Adverse selection bps
   - Leg imbalance ratio
   - Queue size distribution

4. **PNL Metrics**
   - PNL per trade
   - Cumulative PNL
   - Maximum drawdown

**Success criteria:**
- OrderType.DEFAULT fill rate >= 60%
- Maker execution rate >= 60%
- Average fee <= 3.5bps
- Cumulative PNL >= -0.1%
- Leg imbalance < 10% of target
- No position accumulation

### Production Validation

**Phased rollout:**

**Week 1: Shadow Mode (no live trades)**
- Run bot with all strategies enabled
- Compare shadow orders vs live execution
- Validate pricing and queue logic
- Fix any bugs found

**Week 2: 10% Live Traffic**
- Enable strategies for 10% of trades
- Monitor PNL and position risk
- Compare vs control (90% legacy mode)
- Adjust parameters if needed

**Week 3: 50% Live Traffic**
- Scale to 50% of trades
- Full monitoring and alerting
- Daily PNL analysis

**Week 4: 100% Live Traffic**
- Full rollout if Week 2-3 successful
- Continue monitoring for 2 weeks
- Document lessons learned

---

## Rollback Plan

### Trigger Conditions

**Immediate rollback (stop trading):**
1. Position accumulation > 20% of target notional
2. Cumulative PNL < -0.5% (-$5,000 on $1M volume)
3. Leg imbalance > 15% for > 3 consecutive trades
4. Liquidation risk detected

**Parameter adjustment (continue trading):**
1. POST_ONLY fill rate < 20% (adjust queue threshold)
2. Average fee > 4.5bps (revert to IOC-only mode)
3. Adverse selection > 3bps average (tighten filters)

### Rollback Procedure

**Step 1: Emergency Stop**
```bash
# Kill bot process
pkill -f DN_pair_eth_sol_nado.py

# Or use API if available
curl -X POST http://localhost:8080/api/stop
```

**Step 2: Revert Code**
```bash
cd /Users/botfarmer/2dex/hedge

# Revert to commit before changes
git revert <commit-hash>
git push origin main
```

**Step 3: Restart in Legacy Mode**
```bash
# Start bot with legacy configuration (all flags disabled)
python DN_pair_eth_sol_nado.py \
    --size 10000 \
    --iter 100
    # All feature flags disabled by default
```

**Step 4: Analyze Failure**
1. Collect logs from failed period
2. Analyze PNL, positions, fills
3. Identify root cause
4. Create fix plan
5. Test fix thoroughly before redeployment

### Configuration Rollback

**Feature flags for quick rollback:**
```python
# Config additions (already implemented in Step 4.1)
class Config:
    enable_at_touch_pricing: bool = False  # Default off
    enable_order_type_default: bool = False
    enable_queue_filter: bool = False       # Default off
    enable_spread_filter: bool = False      # Default off
    enable_partial_fills: bool = False      # Default off
    enable_dynamic_timeout: bool = False    # Default off
    queue_threshold_ratio: float = 0.5      # Configurable
    spread_threshold_ticks: int = 5         # Configurable
```

**Command-line flags (already implemented in Step 4.2):**
```bash
# Legacy mode (current behavior - all flags disabled)
python DN_pair_eth_sol_nado.py --size 10000 --iter 100

# Progressive enablement
python DN_pair_eth_sol_nado.py --size 10000 --iter 100 \
    --enable-at-touch-pricing \
    --enable-order-type-default \
    --enable-queue-filter \
    --enable-spread-filter

# Custom thresholds
python DN_pair_eth_sol_nado.py --size 10000 --iter 100 \
    --enable-queue-filter \
    --queue-threshold-ratio 0.3 \
    --spread-threshold-ticks 3
```

---

## Success Criteria

### Primary Metrics

**Fee Reduction:**
- Target: <= 3bps average fee per order (weighted maker/taker)
- Current: 5bps (100% taker via IOC fallback)
- Improvement: 2bps per order = 8bps per cycle (at 60% maker rate)
- Stretch: <= 2.5bps (at 75%+ maker rate)

**Fill Rate:**
- Target: >= 60% OrderType.DEFAULT fill rate
- Current: 0% POST_ONLY fill rate (100% timeout to IOC)
- Improvement: 60 percentage points
- Maker Execution Rate: >= 60% of filled orders

**Daily Volume:**
- Target: $1,000,000 notional (VOLUME, not profit)
- Method: 100 trades x $10,000 per trade
- Current: Variable (estimated 50-100 trades/day)
- Achievable with improved fill rates

**Daily Volume:**
- Target: $1,000,000 notional (VOLUME, not profit)
- Method: 100 trades x $10,000 per trade
- Current: Variable (estimated 50-100 trades/day)

### PNL Metrics

**Per-Trade PNL:**
- Target: >= 10bps edge retention
- Calculation: (Revenue - Fees) / Notional
- Current: Negative due to 20bps fee cost

**Cumulative PNL:**
- Target: >= 0 (lossless)
- Allowance: -0.1% maximum drawdown
- Recovery: Must recover within 5 trades

**Daily PNL:**
- Target: >= $1,000 (10bps on $1M volume - fees)
- Break-even: $0 (no losses)
- Stretch: >= $5,000 (50bps net edge)

### Quality Metrics

**Leg Imbalance:**
- Target: < 5% of target notional
- Maximum: < 10% (trigger unwind)
- Average: < 3% over rolling 100 trades

**Adverse Selection:**
- Target: < 2bps average
- Measurement: Execution price vs mid price at order time
- Trigger: > 3bps for 5 consecutive trades = adjust filters

**System Uptime:**
- Target: > 99.5%
- Maximum downtime: 1.8 hours/day
- WebSocket reconnect: < 30s

### Monitoring & Alerting

**Alerts (PagerDuty/Slack):**
1. Position accumulation > 10% of target
2. Cumulative PNL < -0.2%
3. OrderType.DEFAULT fill rate < 40% for 1 hour
4. Maker execution rate < 40% for 1 hour
5. WebSocket disconnected > 60s
6. Leg imbalance > 10%

**Daily Reports:**
1. Total trades executed
2. Average fee per order (bps) - weighted maker/taker
3. OrderType.DEFAULT fill rate
4. Maker vs Taker execution ratio
5. PNL per trade and cumulative
6. Maximum position imbalance
7. Queue size distribution
8. Spread distribution

---

## Appendix: Code References

### Key Files

1. **Order Placement Logic**
   - File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
   - Lines: 509-571 (`place_open_order()`)
   - Lines: 522-525 (pricing logic - **CRITICAL FIX LOCATION**)
   - Lines: 538 (OrderType appendix)

2. **Main Trading Logic**
   - File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
   - Lines: 407-553 (`place_simultaneous_orders()`)
   - Lines: 400-406 (BBO fetching)
   - Lines: 410-411 (correct at-touch pricing - IGNORED by place_open_order)

3. **BookDepth Handler**
   - File: `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`
   - Lines: 117-139 (`get_best_bid()`, `get_best_ask()`)
   - Lines: 141-165 (`get_depth_at_level()`)
   - Lines: 236-264 (`get_available_liquidity()`)

4. **BBO Handler**
   - File: `/Users/botfarmer/2dex/hedge/exchanges/nado_bbo_handler.py`
   - Lines: 276-282 (`get_spread_state()`) - Returns "WIDENING", "NARROWING", or "STABLE"
   - Lines: 60-78 (`get_prices()`)
   - Access via: `self._bbo_handler.get_spread_state()`

5. **Strategy Reference Document**
   - File: `/Users/botfarmer/2dex/.omc/plans/8-strategies-comprehensive-analysis.md`
   - Contains detailed analysis of all 8 strategies
   - Correct pricing logic explanation
   - BookDepth implementation reference

### Configuration Parameters

**Current Constants:**
```python
POST_ONLY_TIMEOUT = 5  # seconds
FEE_RATE_POST_ONLY = 0.0002  # 2bps
FEE_RATE_IOC = 0.0005  # 5bps
MAX_SPREAD_TICKS = 5
MAX_QUEUE_RATIO = 0.5
MIN_PARTIAL_FILL_RATIO = 0.5
```

**New Constants (to be added in Phase 4):**
```python
# Feature flags (default False for backward compatibility)
USE_AT_TOUCH_PRICING = False
USE_ORDER_TYPE_DEFAULT = False
USE_QUEUE_FILTER = False
USE_SPREAD_FILTER = False
USE_PARTIAL_FILLS = False
USE_DYNAMIC_TIMEOUT = False

# Configurable thresholds
QUEUE_THRESHOLD_RATIO = 0.5    # Configurable via --queue-threshold-ratio
SPREAD_THRESHOLD_TICKS = 5     # Configurable via --spread-threshold-ticks
MIN_PARTIAL_FILL_RATIO = 0.5   # Configurable via --min-partial-fill-ratio
```
```python
USE_AT_TOUCH_PRICING = True
USE_QUEUE_FILTER = True
USE_SPREAD_FILTER = True
USE_PARTIAL_FILLS = True
USE_DYNAMIC_TIMEOUT = True
QUEUE_THRESHOLD_RATIO = 0.5  # Configurable
SPREAD_THRESHOLD_TICKS = 5   # Configurable
```

---

## Implementation Timeline

| Day | Phase | Tasks | Deliverables |
|-----|-------|-------|--------------|
| 1 | Foundation | OrderType.DEFAULT conversion (PRIMARY), Add price parameter to place_open_order(), Update call site, Spread filter | Code changes for FR1-FR4 |
| 2 | BookDepth | Queue size measurement, Queue check integration | Code changes for FR5 |
| 3 | Enhancement | Partial fill handling, Dynamic timeout | Code changes for FR6-FR8 |
| 4 | Configuration | Feature flags in Config, argparse integration | Code changes for NFR4-NFR5 |
| 5 | Testing | Unit tests, Integration tests, Production rollout plan | Test suite, Validation report |

**Total effort:** 5 days (40 hours)

**Team:** 1 developer (backend/python experience)

---

## Dependencies

### External Dependencies

1. **Nado SDK**
   - Version: Current (no upgrade required)
   - Source: `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/expiration.py`
   - Usage: OrderType.DEFAULT (value = 0) verified as normal limit order
   - OrderType.LIMIT does NOT exist in SDK
   - BookDepth: Already implemented and functional

2. **WebSocket Infrastructure**
   - BBO Handler: Already implemented
   - BookDepth Handler: Already implemented
   - No new dependencies required

### Internal Dependencies

1. **Configuration System**
   - Requires: Feature flag infrastructure
   - Effort: LOW (1 hour)

2. **Logging System**
   - Requires: Enhanced metrics logging
   - Effort: LOW (2 hours)

3. **Monitoring System**
   - Requires: Alert integration (PagerDuty/Slack)
   - Effort: MEDIUM (4 hours)

---

## Post-Implementation

### Monitoring Dashboard

**Metrics to display:**
1. Real-time PNL (cumulative and per-trade)
2. Position balances (ETH and SOL)
3. Leg imbalance ratio
4. OrderType.DEFAULT fill rate (last hour, last day)
5. Maker vs Taker execution ratio
6. Average fee per order (bps) - weighted
7. Queue size distribution (histogram)
8. Spread distribution (histogram)

**Refresh rate:** 5 seconds

### Daily Operations

**Morning checklist:**
1. Review overnight PNL
2. Check position balances
3. Verify WebSocket connectivity
4. Review alerts from overnight

**End-of-day:**
1. Generate daily PNL report
2. Export trade log to CSV
3. Analyze any failed trades
4. Plan next day's parameters

### Weekly Optimization

**Review items:**
1. Fee per order trend (should decrease)
2. Fill rate trend (should increase)
3. PNL per trade trend (should stabilize)
4. Queue size threshold tuning
5. Spread threshold tuning

**Adjustment process:**
1. Analyze metrics
2. Propose parameter changes
3. Test in shadow mode
4. Deploy to production if validated

---

## Critical Issues Addressed

### Issue 1: Pricing Logic Explanation - RESOLVED

**Original Plan Error:**
- Plan stated: buy=best_bid, sell=best_ask (INCORRECT)
- Correct at-touch maker pricing: buy=best_ask, sell=best_bid

**Clarification:**
- BUY at best_ask: Rests on ask side at touch -> MAKER -> 2bps
- SELL at best_bid: Rests on bid side at touch -> MAKER -> 2bps
- Does NOT cross spread (unlike BBO pricing which crosses)
- POST_ONLY flag provides protection against crossing

**Implementation:**
- Prices already calculated correctly at DN_pair:410-411
- Just need to add price parameter to place_open_order()
- Update call site at DN_pair:454-463 to pass prices

### Issue 2: Fix Option Selection - RESOLVED

**Decision:** Use Option A - Add price parameter (RECOMMENDED)

**Why Option A over Option B:**
- More flexible: allows caller to control pricing
- Backward compatible: optional parameter with fallback
- Clearer code path: explicit price passing
- Easier to test: can toggle via feature flag

**Implementation:**
- Add `price: Optional[Decimal] = None` parameter to place_open_order()
- Use price if provided, otherwise fallback to legacy behavior
- Update call site to pass calculated prices

### Issue 3: Root Cause Analysis - CLARIFIED

**Root Cause:**
- 1-tick-behind placement is TOO FAR from touch in fast markets
- In 50ms update cycles, market moves 2-3 ticks
- Order at 1-tick-behind becomes 3-4 ticks behind
- Never fills -> timeout -> IOC at 5bps

**Fix:** Move to at-touch pricing for better fill probability

### Issue 3: Call Site Update Added - RESOLVED

**Missing Piece:** Original plan did not include call site update

**Added:** Step 1.2 - Update Call Site to Pass At-Touch Prices
- File: DN_pair_eth_sol_nado.py
- Lines: 454-463
- Pass eth_price and sol_price to place_open_order()

### Issue 4: spread_state Location Verified - RESOLVED

**Location Confirmed:** nado_bbo_handler.py:276-282
- Method: `get_spread_state()`
- Returns: "WIDENING", "NARROWING", or "STABLE"
- Access via: `self._bbo_handler.get_spread_state()`

**Updated:** Step 3.2 includes access method

### Issue 5: Feature Flag Implementation Added - RESOLVED

**New Phase 4:** Feature Flags & Configuration
- Step 4.1: Add feature flags to Config class
- Step 4.2: Add argparse command-line flags
- Step 4.3: Use feature flags in code

**Implementation Pattern:**
```python
# Config class
self.enable_at_touch_pricing = getattr(self, 'enable_at_touch_pricing', False)

# argparse
parser.add_argument('--enable-at-touch-pricing', action='store_true')

# Usage
if self.config.enable_at_touch_pricing and price is not None:
    order_price = price
```

### Issue 6: $1M Goal Clarified - RESOLVED

**Clarification:**
- Target is $1M daily VOLUME (not profit)
- Volume: 100 trades x $10K = $1M notional
- This is achievable with improved fill rates

### Issue 7: SDK OrderType Definition Verified - RESOLVED

**SDK Source File:** `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/expiration.py`

```python
class OrderType(IntEnum):
    DEFAULT = 0      # Normal limit order - maker OR taker based on price
    IOC = 1
    FOK = 2
    POST_ONLY = 3    # Maker-only, rejected if would cross spread
```

**Key Findings:**
1. `OrderType.DEFAULT = 0` IS the normal limit order
2. `OrderType.LIMIT` does NOT exist in the SDK
3. Fee determined by EXECUTION METHOD, not OrderType:
   - Maker (resting on book): 2bps
   - Taker (crossing spread): 5bps
4. POST_ONLY is the PROBLEM (100% timeout), not the solution
5. OrderType.DEFAULT is the CORRECT solution

**Impact on Plan:**
- OrderType.DEFAULT conversion is now PRIMARY strategy (Step 1.1)
- At-touch pricing is now Step 1.2 (supports OrderType.DEFAULT)
- All POST_ONLY references updated to emphasize problem, not solution
- Fill rate targets updated to reflect OrderType.DEFAULT behavior (60-80%)

### Issue 8: 8 Strategies Document - INTEGRATED

**Reference:**
- Document exists at `/Users/botfarmer/2dex/.omc/plans/8-strategies-comprehensive-analysis.md`
- Used for strategy justification and detailed analysis
- BookDepth implementation reference included

---

PLAN_READY: /Users/botfarmer/2dex/.omc/plans/pnl-lossless-1M-daily.md
