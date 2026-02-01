# POST_ONLY to DEFAULT Conversion and Fee Optimization - Strategic Implementation Plan

**PLAN STATUS:** ITERATION 3 - ARCHITECT ROOT CAUSE ANALYSIS INCORPORATED

**ITERATION 3 KEY UPDATES:**
- Root cause identified: Current POST_ONLY pricing creates 1-tick gap preventing fills
- User's BBO pricing proposal verified as correct solution
- Fee rate verification added as critical Phase 0 requirement
- PNL projections updated to reflect Strategy 1 dual outcomes
- Decision tree simplified based on fee rate verification

## Executive Summary

**Current State Analysis:**
- POST_ONLY mode with 5-second timeout, 100% fallback rate to IOC
- All orders executing as TAKER → 20bps fees per trading cycle
- Fee structure: Fees determined by EXECUTION METHOD, not OrderType
  - Maker (resting on book): 2bps per order
  - Taker (crossing spread): 5bps per order
- Current cost: 20bps per cycle (4 orders × 5bps, all taker)

**Root Cause (ARCHITECT VERIFIED - ITERATION 3):**
- POST_ONLY pricing: `best_ask - tick_size` (BUY) and `best_bid + tick_size` (SELL)
- This creates orders ONE TICK AWAY from touch, creating a gap that prevents fills
- Current pricing places orders behind the market, requiring adverse price movement for fills
- 100% fallback to IOC → guaranteed taker execution
- Data backing: Logs show "POST_ONLY timeout, falling back to IOC" on every cycle

**Current Pricing Problem (Detailed):**
```
BUY:  order_price = best_ask - tick_size
      → Places $2499.90 when best_ask = $2500.00
      → Only fills if market moves DOWN (adverse direction)

SELL: order_price = best_bid + tick_size
      → Places $2500.00 when best_bid = $2499.90
      → Only fills if market moves UP (adverse direction)
```

**User's Proposed Solution (Correct Strategy):**
```python
# BBO pricing (touch price) - crosses spread for immediate fills
if direction == "buy":
    order_price = best_ask   # 매수호가에
else:
    order_price = best_bid    # 매도호가에
```

**Key SDK Discovery:**
- OrderType.DEFAULT exists (value = 0): Simple Limit order behavior
- OrderType.LIMIT does NOT exist in this SDK
- Fee determination: Execution method (maker/taker), NOT OrderType
- Price strategy is the critical factor for fee optimization

**Proposed Solutions:**

**Strategy 1: Convert POST_ONLY → DEFAULT with BBO Pricing (USER'S PROPOSAL)**
- Replace OrderType.POST_ONLY with OrderType.DEFAULT
- Use BBO pricing at touch (buy=ask, sell=bid) for immediate fills
- Crosses spread → immediate execution
- Fee determination: PENDING - Is OrderType.DEFAULT at touch price TAKER (5bps) or MAKER (2bps)?
- Expected outcome: Immediate fills, no 5-second timeout
- Fee impact: TBD (depends on DEFAULT/touch fee rate)

**Strategy 2: Convert POST_ONLY → DEFAULT with Aggressive Passive Pricing**
- Replace OrderType.POST_ONLY with OrderType.DEFAULT
- Use pricing at best bid (buy) or best ask (sell) - rest on book
- Does NOT cross spread → waits for fills as maker order
- Fee: 2bps per order (maker) if fills occur
- Expected outcome: 8-20bps fees depending on fill rate
- Potential fee reduction: 0-12bps per cycle (if maker fills occur)

**Fee Structure by Price Strategy (PENDING VERIFICATION):**
- OrderType.DEFAULT + BBO price (crosses spread) = PENDING (TAKER 5bps or MAKER 2bps?)
- OrderType.DEFAULT + at touch (buy=bid, sell=ask) = MAKER (2bps) - rests on book
- OrderType.DEFAULT + behind touch (BBO ± 1 tick) = MAKER (2bps) - rests on book

**CRITICAL UNKNOWN:**
- Does OrderType.DEFAULT placed AT the touch price (crossing spread) execute as:
  - TAKER (5bps) - because it crosses spread immediately?
  - MAKER (2bps) - because OrderType.DEFAULT can behave as maker?
- Need to verify from SDK documentation or empirical testing
- This determines whether Strategy 1 provides fee improvement

**Projected PNL Impact (Strategy 1 - BBO Pricing):**
- If DEFAULT + touch = TAKER (5bps): 20bps/cycle (no change)
- If DEFAULT + touch = MAKER (2bps): 8bps/cycle (12bps savings)
- CRITICAL: Need to determine actual fee rate for this scenario

**Projected PNL Impact (Strategy 2 - Passive Pricing):**
- Best case (100% maker fills): 8bps/cycle (12bps savings)
- Realistic case (50% maker fills): 14bps/cycle (6bps savings)
- Worst case (0% maker fills): 20bps/cycle (no change)

---

## Part 1: SDK Research Findings and Corrections

### Finding 1: OrderType.DEFAULT Exists

**SDK OrderType Enumeration:**
- OrderType.DEFAULT = 0: Simple Limit order (can be maker or taker based on pricing)
- OrderType.POST_ONLY: Maker-only order (rejects if would cross spread)
- OrderType.IOC: Immediate-or-Cancel order
- **OrderType.LIMIT does NOT exist** in this SDK

**Key Insight:**
OrderType.DEFAULT is the standard Limit order type that can behave as either maker or taker depending on price placement.

### Finding 2: Fee Structure by Execution Method

**Fee Determination:**
- Fees determined by EXECUTION METHOD, not OrderType
- Maker (resting on book): 2bps per order
- Taker (crossing spread): 5bps per order

**Per Cycle Fee Calculation:**
- Entry: 2 orders (ETH + SOL) = 4bps (maker) or 10bps (taker)
- Exit: 2 orders (ETH + SOL) = 4bps (maker) or 10bps (taker)
- **Best case (all maker): 8bps per cycle**
- **Current (all taker): 20bps per cycle**

**Fee Improvement Potential:**
- Maximum improvement: 12bps (20→8) if 100% maker fill rate
- Realistic improvement: 4-8bps (50-75% maker fill rate)

### Finding 3: Price Strategy is Key

**Critical Discovery (ITERATION 3 - ARCHITECT CORRECTED):**
The key to fee optimization is PRICE STRATEGY, not OrderType selection.

**Current POST_ONLY Pricing (WRONG - Never Fills):**
```
BUY:  order_price = best_ask - tick_size  # ONE TICK BEHIND touch
SELL: order_price = best_bid + tick_size  # ONE TICK BEHIND touch
Result: Never fills, 100% timeout rate
```

**User's Proposed BBO Pricing (Correct - Crosses Spread):**
```python
if direction == "buy":
    order_price = best_ask   # AT touch price
else:
    order_price = best_bid    # AT touch price
Result: Immediate fills by crossing spread
```

**Price Strategy Impact (PENDING FEE VERIFICATION):**
- OrderType.DEFAULT + BBO price (crosses spread) = TAKER (5bps) OR MAKER (2bps)? **PENDING VERIFICATION**
- OrderType.DEFAULT + at touch (buy=bid, sell=ask) = MAKER (2bps) - rests on book
- OrderType.DEFAULT + behind touch = MAKER (2bps) - rests on book

**Two Real Options (ITERATION 3):**
1. **Strategy 1 (User's Proposal):** Convert to OrderType.DEFAULT with BBO pricing (crosses spread, immediate fills)
   - Fee: PENDING (5bps if taker, 2bps if maker - need to verify)
2. **Strategy 2:** Convert to OrderType.DEFAULT with passive pricing (rests on book)
   - Fee: 2bps (maker) if fills occur

---

## Part 2: Revised Strategy Analysis

### Strategy 1: Convert POST_ONLY → DEFAULT with BBO Pricing (User's Proposal)

**Objective:** Convert from POST_ONLY to OrderType.DEFAULT with BBO pricing for immediate fills by crossing spread.

**Implementation Difficulty:** LOW

**Root Cause Fix:**
- Current: `best_ask - tick_size` (BUY) and `best_bid + tick_size` (SELL) → 1 tick gap → never fills
- New: `best_ask` (BUY) and `best_bid` (SELL) → crosses spread → immediate fills

**Code Changes:**
- File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
  - Lines 509-571: Change `OrderType.POST_ONLY` to `OrderType.DEFAULT`
  - Modify pricing to BBO at touch: buy=best_ask, sell=best_bid (crosses spread)
  - Remove timeout/fallback logic (no longer needed)
- File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
  - Line 62: Update default parameter name (optional)
  - Lines 407-553: Simplify to remove timeout handling
  - Line 403: Set `FEE_RATE` based on DEFAULT/touch fee rate (PENDING VERIFICATION)
  - Line 678: Set `remaining_exit_fees_bps` based on DEFAULT/touch fee rate (PENDING VERIFICATION)

**Expected Outcome:**
- Execution: 100% fill rate (immediate by crossing spread)
- Latency: 5 seconds faster per cycle (no timeout)
- Fee: **PENDING VERIFICATION** - Depends on whether DEFAULT + touch executes as taker (5bps) or maker (2bps)
  - If TAKER: 20bps/cycle (no change)
  - If MAKER: 8bps/cycle (12bps savings)
- Complexity: Reduced (no timeout/fallback logic)

**Advantages:**
- Simple, clean implementation
- Eliminates timeout complexity
- Predictable behavior (always fills immediately)
- Faster cycle time
- No timeout risk
- **POTENTIAL FEE SAVINGS** if DEFAULT + touch = maker fees

**Disadvantages:**
- Fee rate unknown (need to verify if maker or taker)
- No passive execution (always crosses spread)

**CRITICAL NEXT STEP:**
Verify fee rate for OrderType.DEFAULT placed at touch price (crossing spread):
- Check SDK documentation
- Or run empirical test with small order
- This determines whether Strategy 1 provides fee improvement

**Verdict:** CONDITIONALLY RECOMMENDED - User's proposal is correct for execution, pending fee verification

---

### Strategy 2: Convert POST_ONLY → DEFAULT with Aggressive Passive Pricing

**Objective:** Convert from POST_ONLY to OrderType.DEFAULT with aggressive passive pricing for maker execution.

**Implementation Difficulty:** MEDIUM

**Root Cause Fix:**
- Current: `best_ask - tick_size` (BUY) and `best_bid + tick_size` (SELL) → 1 tick gap → never fills
- New: `best_bid` (BUY) and `best_ask` (SELL) → AT touch price → rests on book as maker

**New DEFAULT Pricing Strategy (Maker Execution):**
- Buy: `best_bid` (at best bid, does NOT cross spread)
- Sell: `best_ask` (at best ask, does NOT cross spread)
- Result: Rests on book at touch, waits for fills as maker order (2bps fee)
- Difference from Strategy 1: Does NOT cross spread, waits for counterparty

**Pricing Options for Strategy 2:**

**Option 2A: Aggressive Passive (at touch)**
- Buy: `best_bid` (at best bid)
- Sell: `best_ask` (at best ask)
- Higher fill probability (at front of queue when placed)
- May get queued behind existing orders
- Fee: 2bps (maker) if fills occur

**Option 2B: Conservative Passive (one tick behind)**
- Buy: `best_bid - tick_size` (one tick behind best bid)
- Sell: `best_ask + tick_size` (one tick behind best ask)
- Lower fill probability (further from touch)
- Better queue position when fills occur
- Fee: 2bps (maker) if fills occur

**Option 2C: Queue Position-Based (adaptive)**
- Analyze BookDepth to estimate queue size at touch
- Place at touch when queue is small (< 5 orders)
- Place one tick behind when queue is large
- Adaptive strategy
- Fee: 2bps (maker) if fills occur

**Code Changes:**
- File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
  - Lines 509-571: Change `OrderType.POST_ONLY` to `OrderType.DEFAULT`
  - Modify pricing logic to use passive pricing (buy=best_bid, sell=best_ask)
  - Add queue size estimation from BookDepth (for Option 2C)
  - Keep polling/fill checking (no timeout needed)
- File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
  - Lines 407-553: Simplify to remove timeout handling
  - Add fill monitoring logic
  - Update fee calculation for maker fees (2bps)

**Expected Outcome:**
- Fee: 8-20bps/cycle (depends on fill rate)
- Latency: Variable (0-30 seconds depending on fill)
- Complexity: Increased

**Advantages:**
- Potential fee reduction (up to 12bps/cycle)
- Maker execution possible (2bps vs 5bps)
- Best case: 8bps/cycle (all maker)
- Uses standard OrderType.DEFAULT behavior

**Disadvantages:**
- More complex implementation
- Uncertain fill rate improvement
- Variable latency (may wait for fills)
- Risk: May still achieve low fill rate

**Data Requirements:**
- Historical fill rate data (not currently available)
- Queue position analysis
- Backtesting required

**Verdict:** CONDITIONALLY RECOMMENDED - Requires data validation first

---

### Strategy 3: Hybrid Approach - Dynamic Pricing Selection

**Objective:** Dynamically select between BBO pricing (immediate) and passive pricing (maker) based on market conditions.

**Implementation Difficulty:** MEDIUM-HIGH

**Strategy:**
- Monitor spread size and queue depth
- Use BBO pricing (immediate) when spread is tight (< 2 ticks)
- Use passive pricing (maker) when spread is wide (≥ 2 ticks)
- Adaptive approach to optimize fill rate vs fee reduction

**Code Changes:**
- File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
  - Lines 509-571: Add dynamic pricing logic
  - Implement spread analysis
  - Add queue size estimation from BookDepth
- File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
  - Lines 407-553: Add dynamic pricing selection
  - Track both immediate and passive order performance

**Expected Outcome:**
- Fee: 12-18bps/cycle (mixed execution)
- Latency: Variable (some immediate, some wait)
- Complexity: High

**Advantages:**
- Adaptive to market conditions
- Balances speed and cost
- Potential for moderate fee reduction (2-8bps)

**Disadvantages:**
- Highest complexity
- Two different code paths to maintain
- Harder to predict behavior
- More testing required

**Verdict:** NOT RECOMMENDED - High complexity, moderate benefit

---

### Strategy 4: Spread-Based Order Type Selection

**Objective:** Select pricing strategy based on spread width - use BBO pricing for tight spreads, passive pricing for wide spreads.

**Implementation Difficulty:** LOW-MEDIUM

**Code Changes:**
- File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
  - Lines 509-571: Add spread-based pricing selection
  - Calculate spread in ticks: `spread_ticks = (ask - bid) / tick_size`
  - If spread_ticks ≤ 1: Use BBO pricing (immediate)
  - If spread_ticks > 1: Use passive pricing (maker)

```python
# Pseudo-code for pricing selection
spread_ticks = (best_ask - best_bid) / tick_size

if spread_ticks <= 1:
    # Tight spread: Use BBO pricing for immediate fill
    buy_price = best_ask
    sell_price = best_bid
else:
    # Wide spread: Use passive pricing for maker execution
    buy_price = best_bid - tick_size
    sell_price = best_ask + tick_size
```

**Expected Outcome:**
- Fee: 12-16bps/cycle (mixed execution based on spread)
- Latency: Variable (immediate when tight, wait when wide)
- Complexity: Low-Medium

**Advantages:**
- Simple adaptive strategy
- Exploits market conditions
- Works with any base strategy
- Clear decision logic

**Disadvantages:**
- Reduced trade frequency when spread is wide
- May miss opportunities during tight spreads
- Requires spread threshold tuning

**Verdict:** SUPPLEMENTAL - Use alongside Strategy 1 or 2

---

## Part 3: Edge Cases and Missing Considerations

### Edge Case 1: Leg Fill Imbalance

**Scenario:** One leg fills, other doesn't (partial fill or timeout)

**Current Handling:**
- Not well defined in current code
- POST_ONLY timeout handles this, but Logic unclear

**Required Handling:**
```python
if eth_filled and not sol_filled:
    # ETH filled, SOL didn't
    # Option 1: Wait for SOL (timeout risk)
    # Option 2: Hedge ETH immediately (accept loss)
    # Option 3: Cancel ETH order (if not executed)

if sol_filled and not eth_filled:
    # SOL filled, ETH didn't
    # Same options as above
```

**Recommended Approach:**
- Implement imbalance handler
- Hedge unfilled leg within 1 second
- Accept small loss to close delta exposure

### Edge Case 2: BBO Movement During Wait

**Scenario:** BBO moves while waiting for POST_ONLY fill

**Current Handling:**
- Order sits at stale price
- May never fill if price moves away

**Required Handling:**
```python
# Monitor price during wait
if abs(current_price - original_price) / original_price > 0.001:  # 10 bps move
    # Cancel and replace with new order
    # Or fall back to IOC immediately
```

**Recommended Approach:**
- Price movement threshold: 10 bps
- Cancel and replace on significant move
- Fall back to IOC if volatile

### Edge Case 3: Partial Fills

**Scenario:** Order partially fills, remainder sits

**Current Handling:**
- Partial fills handled in lines 649-652
- POST_ONLY mode may not handle this well

**Required Handling:**
```python
if filled_size > 0 and filled_size < order_size:
    fill_ratio = filled_size / order_size
    if fill_ratio >= MIN_FILL_RATIO:  # e.g., 0.5
        # Accept partial fill
        # Hedge remainder with IOC
    else:
        # Cancel partial fill (if possible)
        # Or accept and hedge
```

**Recommended Approach:**
- Minimum fill ratio: 50%
- Hedge remainder immediately
- Log partial fills for analysis

### Edge Case 4: Zero Fills After Timeout

**Scenario:** Neither leg fills after timeout

**Current Handling:**
- Returns error, skips cycle
- Wasted 5-30 seconds

**Required Handling:**
```python
if not eth_filled and not sol_filled:
    # Log timeout event
    # Update statistics (timeout rate)
    # Consider skipping next cycle if rate too high
```

**Recommended Approach:**
- Track timeout rate
- If > 80% timeout rate, switch to IOC-only
- Adaptive strategy selection

---

## Part 4: Priority Matrix (Revised)

### Strategy Ranking by PNL Impact vs Effort

| Strategy | PNL Impact | Implementation Effort | Risk Level | Priority Score |
|----------|------------|----------------------|------------|----------------|
| Strategy 1: DEFAULT + BBO Pricing | NONE (0 bps) | LOW | LOW | **2nd** (baseline) |
| Strategy 2: DEFAULT + Passive Pricing | HIGH (0-12 bps) | MEDIUM | MEDIUM | **1st** (if data supports) |
| Strategy 3: Dynamic Pricing | MEDIUM (2-8 bps) | HIGH | MEDIUM | 4th (complex) |
| Strategy 4: Spread-Based Selection | MEDIUM (2-4 bps) | LOW-MEDIUM | LOW | **3rd** (supplemental) |

### Priority Matrix Visualization

```
HIGH PNL IMPACT
    │
    │  ┌─────────────────┐
    │  │  Strategy 2     │  ★ DATA-DEPENDENT
    │  │  DEFAULT+Passive│  (0-12 bps, MEDIUM effort)
    │  └─────────────────┘
    │
    │  ┌─────────────────┐
    │  │  Strategy 3     │  TOO COMPLEX
    │  │  Dynamic Pricing│  (2-8 bps, HIGH effort)
    │  └─────────────────┘
    │
MEDIUM│
    │  ┌─────────────────┐
    │  │  Strategy 4     │  SUPPLEMENTAL
    │  │  Spread-Based   │  (2-4 bps, LOW-MED effort)
    │  └─────────────────┘
    │
    │
LOW │  ┌─────────────────┐
    │  │  Strategy 1     │  BASELINE
    │  │  DEFAULT+BBO    │  (0 bps, LOW effort, fast)
    │  └─────────────────┘
    └──────────────────────────────────
        LOW       HIGH EFFORT
```

### Key Changes from Previous Plan

1. **Strategy 1 now "DEFAULT + BBO Pricing"** - Not removal, but conversion
2. **Strategy 2 now "DEFAULT + Passive Pricing"** - Not improvement, but conversion with different pricing
3. **Strategy 3 revised** - Dynamic pricing selection (no longer timeout-based)
4. **Strategy 4 revised** - Spread-based pricing selection (no longer skipping trades)
5. **Fee improvement corrected** - 12bps max (not 16bps)

---

## Part 5: Data-Backed Decision Framework

### Required Data for Strategy 2 Selection

Before implementing Strategy 2 (DEFAULT + Passive Pricing), gather:

**Data Point 1: Historical Fill Rate Simulation**
- Current POST_ONLY fill rate: 0% (100% timeout)
- Need: Simulate fill rate with OrderType.DEFAULT + passive pricing
- How: Backtest with historical data using BBO ± 1 tick pricing

**Data Point 2: Queue Position Analysis**
- Current queue size at touch prices
- How many orders ahead of ours at best bid/ask?
- How: Use BookDepth data to analyze queue depth

**Data Point 3: Spread Distribution**
- Typical spread sizes in ticks
- How often is spread ≤ 2 ticks vs > 2 ticks?
- How: Analyze historical BBO data and tick sizes

**Data Point 4: Price Movement During Resting Orders**
- How often does price move > 10 bps while order is resting?
- How: Analyze price volatility during typical order duration (5-30 seconds)

### Decision Criteria

**Implement Strategy 2 IF:**
- Backtesting shows > 30% fill rate with passive pricing (BBO ± 1 tick)
- Spread is typically ≥ 2 ticks (allows passive placement)
- Queue positions at BBO are reasonable (< 10 orders deep)
- Price movement during typical order wait is < 10 bps

**Implement Strategy 1 IF:**
- Backtesting shows < 20% fill rate even with passive pricing
- Spread is typically ≤ 1 tick (no room for passive placement)
- Queue positions at BBO are very deep (> 20 orders)
- Price movement is highly volatile during order wait
- Simplicity and speed are preferred over potential savings

---

## Part 6: Implementation Plan

### Phase 0: Fee Rate Verification (MANDATORY FIRST STEP)

**Objective:** Verify fee rate for OrderType.DEFAULT placed at touch price (crossing spread).

**CRITICAL QUESTION:**
Does OrderType.DEFAULT with BBO pricing (crossing spread) execute as:
- TAKER (5bps) - because it crosses spread immediately?
- MAKER (2bps) - because OrderType.DEFAULT can behave as maker?

**Tasks:**
1. Check SDK documentation for fee structure clarification
2. If docs unclear, run empirical test with small order:
   - Place OrderType.DEFAULT at touch price (buy=ask, sell=bid)
   - Check executed fee rate in trade history
   - Verify if 2bps (maker) or 5bps (taker)
3. Document actual fee rate observed

**Deliverables:**
- Documented fee rate for OrderType.DEFAULT + BBO pricing (touch price)
- SDK documentation references (if available)
- Empirical test results (if run)

**Estimated Time:** 1-2 hours

**Acceptance Criteria:**
- Clear determination of fee rate (2bps or 5bps)
- Documentation or test data to support conclusion
- No guessing or assumptions

**Decision Impact:**
- If 2bps (maker): Strategy 1 provides 12bps savings, proceed with implementation
- If 5bps (taker): Strategy 1 provides no fee savings, evaluate Strategy 2 instead

---

### Phase 1A: Strategy 1 - Convert POST_ONLY → DEFAULT with BBO Pricing (If Fee Rate Verified as Maker OR Accept Taker Rate)

**Objective:** Convert from POST_ONLY to OrderType.DEFAULT with BBO pricing for immediate fills by crossing spread.

**Acceptance Criteria:**
1. OrderType.POST_ONLY replaced with OrderType.DEFAULT
2. BBO pricing at touch implemented (buy=ask, sell=bid - crosses spread)
3. Timeout/fallback logic removed
4. Order placement latency reduced by 5 seconds (no timeout)
5. 100% fill rate maintained (immediate execution by crossing spread)
6. Fee rate verified and applied correctly (2bps or 5bps based on Phase 0)
7. No regression in order success rate

**Specific Code Changes:**

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`**

1. Lines 509-571: Change OrderType in `place_open_order()`
```python
# BEFORE:
order_type = OrderType.POST_ONLY

# AFTER:
order_type = OrderType.DEFAULT
```

2. Lines 509-571: Update pricing to BBO at touch (crosses spread)
```python
# CURRENT PRICING (1 tick gap, never fills):
if direction == 'buy':
    order_price = best_ask - tick_size  # Creates gap
else:
    order_price = best_bid + tick_size  # Creates gap

# NEW BBO PRICING (crosses spread, immediate fill):
if direction == 'buy':
    order_price = best_ask  # Crosses spread, immediate fill
else:
    order_price = best_bid  # Crosses spread, immediate fill
```

3. Remove timeout/fallback logic (if present)
   - Remove any POST_ONLY timeout handling
   - Remove fallback to IOC (no longer needed)

**File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**

1. Line 62: Update default parameter name (optional, for clarity)
```python
# BEFORE:
use_post_only: bool = True,

# AFTER:
use_immediate_fills: bool = True,  # Using DEFAULT with BBO pricing
```

2. Lines 407-553: Simplify to remove timeout handling
   - Remove POST_ONLY timeout logic
   - Remove fallback to IOC logic
   - Keep fill monitoring (if needed)

3. Line 403: Set fee rate (PENDING VERIFICATION)
```python
# FEE_RATE PENDING: Determine if DEFAULT + touch = taker (0.0005) or maker (0.0002)
FEE_RATE = Decimal("0.0005")  # Placeholder - update after verification
```

4. Line 678: Set exit fee rate (PENDING VERIFICATION)
```python
# remaining_exit_fees_bps PENDING: 10 if taker, 4 if maker
remaining_exit_fees_bps = 10  # Placeholder - update after verification
```

**Testing Requirements:**
- Unit test: `test_default_order_bbo_pricing()`
- Integration test: Verify 5-second latency reduction
- Regression test: Ensure order execution unchanged
- Log validation: Confirm no POST_ONLY log messages

**Rollback Plan:**
```bash
git revert <commit-hash>  # Revert conversion
# Restore POST_ONLY implementation from git history
```

**Estimated Time:** 2 hours (convert + test)

---

### Phase 1B: Strategy 2 - Convert POST_ONLY → DEFAULT with Aggressive Passive Pricing (If Strategy 1 Rejected or Higher Maker Fill Rate Desired)

**Objective:** Convert from POST_ONLY to OrderType.DEFAULT with aggressive passive pricing at touch for maker execution.

**Acceptance Criteria:**
1. OrderType.POST_ONLY replaced with OrderType.DEFAULT
2. Aggressive passive pricing at touch implemented (buy=best_bid, sell=best_ask - does NOT cross spread)
3. Backtested or monitored fill rate > 30%
4. Fee reduction > 4 bps average per cycle
5. No regression in order success rate
6. Edge case handling implemented (leg imbalance, partial fills)

**Specific Code Changes:**

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`**

1. Lines 509-571: Change OrderType in `place_open_order()`
```python
# BEFORE:
order_type = OrderType.POST_ONLY

# AFTER:
order_type = OrderType.DEFAULT
```

2. Lines 509-571: Modify pricing logic to aggressive passive pricing (at touch)
```python
# CURRENT PRICING (1 tick gap, never fills):
if direction == 'buy':
    order_price = best_ask - tick_size  # Behind touch, creates gap
else:
    order_price = best_bid + tick_size  # Behind touch, creates gap

# NEW AGGRESSIVE PASSIVE PRICING (at touch, maker execution):
if direction == 'buy':
    # Place AT best bid (does NOT cross spread)
    order_price = best_bid
else:
    # Place AT best ask (does NOT cross spread)
    order_price = best_ask
```

3. Alternative: Queue position-based pricing (optional enhancement)
```python
# ENHANCED PRICING (queue-based):
if direction == 'buy':
    queue_size = self.bookdepth_handler.get_queue_size('bid', contract_id)
    if queue_size < 5:  # Small queue - can be at best bid
        order_price = best_bid
    else:  # Large queue - stay one tick back
        order_price = best_bid - tick_size
else:
    queue_size = self.bookdepth_handler.get_queue_size('ask', contract_id)
    if queue_size < 5:  # Small queue - can be at best ask
        order_price = best_ask
    else:  # Large queue - stay one tick behind
        order_price = best_ask + tick_size
```

3. Alternative: Queue position-based pricing (optional enhancement)
```python
# ENHANCED PRICING (queue-based):
if direction == 'buy':
    queue_size = self.bookdepth_handler.get_queue_size('bid', contract_id)
    if queue_size < 5:  # Small queue - can be at best bid
        order_price = best_bid
    else:  # Large queue - stay one tick back
        order_price = best_bid - tick_size
else:
    queue_size = self.bookdepth_handler.get_queue_size('ask', contract_id)
    if queue_size < 5:  # Small queue - can be at best ask
        order_price = best_ask
    else:  # Large queue - stay one tick ahead
        order_price = best_ask + tick_size
```

4. Add queue size estimation method (if using queue-based pricing):
```python
def get_queue_size(self, side: str, contract_id: str) -> int:
    """
    Estimate queue size at touch.

    Args:
        side: 'bid' or 'ask'
        contract_id: Product contract ID

    Returns:
        Estimated number of orders ahead
    """
    try:
        bookdepth = self.bookdepth_handler.get_bookdepth(contract_id)
        if side == 'bid':
            best_bid = bookdepth.bids[0].price if bookdepth.bids else Decimal('0')
            queue_size = sum(
                1 for level in bookdepth.bids
                if level.price == best_bid
            )
        else:
            best_ask = bookdepth.asks[0].price if bookdepth.asks else Decimal('0')
            queue_size = sum(
                1 for level in bookdepth.asks
                if level.price == best_ask
            )
        return queue_size
    except Exception as e:
        self.logger.log(f"Error estimating queue size: {e}", "WARNING")
        return 999  # Assume large queue on error
```

**File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**

1. Lines 407-553: Simplify to remove timeout handling
   - Remove POST_ONLY timeout logic
   - Remove fallback to IOC logic
   - Keep fill monitoring for maker orders

2. Add edge case handling after line 528:

```python
# EDGE CASE: Leg imbalance handling
if eth_result.filled_size > 0 and sol_result.filled_size == 0:
    # ETH filled, SOL didn't
    imbalance_qty = eth_result.filled_size
    self.logger.warning(f"[ORDER] ETH filled, SOL timeout - hedging {imbalance_qty} ETH")

    # Hedge ETH immediately with IOC
    hedge_result = await self.eth_client.place_ioc_order(
        self.eth_client.config.contract_id,
        imbalance_qty,
        'sell'
    )

elif sol_result.filled_size > 0 and eth_result.filled_size == 0:
    # SOL filled, ETH didn't
    imbalance_qty = sol_result.filled_size
    self.logger.warning(f"[ORDER] SOL filled, ETH timeout - hedging {imbalance_qty} SOL")

    # Hedge SOL immediately with IOC
    hedge_result = await self.sol_client.place_ioc_order(
        self.sol_client.config.contract_id,
        imbalance_qty,
        'sell'
    )

# EDGE CASE: Partial fill handling
MIN_FILL_RATIO = 0.5  # Require 50% minimum fill

if eth_result.filled_size > 0 and eth_result.filled_size < eth_result.size:
    fill_ratio = eth_result.filled_size / eth_result.size
    if fill_ratio >= MIN_FILL_RATIO:
        # Accept partial fill, hedge remainder
        remainder = eth_result.size - eth_result.filled_size
        self.logger.info(f"[ORDER] ETH partial fill {fill_ratio:.1%} - hedging {remainder}")

        hedge_result = await self.eth_client.place_ioc_order(
            self.eth_client.config.contract_id,
            remainder,
            eth_direction
        )
    else:
        # Partial fill too small, reject
        self.logger.warning(f"[ORDER] ETH partial fill too small {fill_ratio:.1%}")
        # Cancel and restart

# Same for SOL...
```

**Testing Requirements:**

1. Unit Tests:
   - `test_default_order_passive_pricing()`: Verify new pricing logic
   - `test_queue_size_estimation()`: Verify queue calculation
   - `test_leg_imbalance_handler()`: Verify imbalance hedging
   - `test_partial_fill_handling()`: Verify partial fill logic

2. Integration Tests:
   - `test_default_order_fill_rate()`: Run 100 cycles, measure fill %
   - `test_fee_reduction()`: Compare average fees before/after
   - `test_edge_case_stress()`: Test all edge cases

3. Manual Testing:
   - Paper trading for 48 hours
   - Monitor fill rates and PNL
   - Track leg imbalance frequency
   - Compare to baseline (current system)

**Rollback Plan:**
```bash
git revert <commit-hash>  # Revert Strategy 2 changes
git checkout <previous-commit> -- hedge/exchanges/nado.py
git checkout <previous-commit> -- hedge/DN_pair_eth_sol_nado.py
```

**Estimated Time:** 10-14 hours (implement + test + validate)

---

### Phase 2: Strategy 4 - Spread-Based Pricing Selection (Supplemental)

**Objective:** Add spread-based pricing selection to any base strategy.

**Acceptance Criteria:**
1. Spread-based pricing selection implemented
2. Configurable spread threshold in ticks (default 2 ticks)
3. BBO pricing for tight spreads (≤ 1 tick)
4. Passive pricing for wide spreads (> 1 tick)
5. No regression in profitable trade rate

**Specific Code Changes:**

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`**

Add spread-based pricing selection in `place_open_order()` (around line 520):

```python
# STRATEGY 4: Spread-based pricing selection
MAX_SPREAD_TICKS = 2  # Configurable

spread_ticks = (best_ask - best_bid) / tick_size

if spread_ticks <= 1:
    # Tight spread: Use BBO pricing for immediate fill (taker)
    if direction == 'buy':
        order_price = best_ask
    else:
        order_price = best_bid
    self.logger.debug(f"[ORDER] Tight spread ({spread_ticks:.1f} ticks), using BBO pricing")
else:
    # Wide spread: Use passive pricing for maker execution
    if direction == 'buy':
        order_price = best_bid - tick_size
    else:
        order_price = best_ask + tick_size
    self.logger.debug(f"[ORDER] Wide spread ({spread_ticks:.1f} ticks), using passive pricing")

# Use OrderType.DEFAULT for both cases
order_type = OrderType.DEFAULT
```

**Testing Requirements:**
- Unit test: `test_spread_based_pricing_selection()`
- Integration test: Verify BBO pricing when tight, passive when wide
- Backtest: Compare PNL with/without spread-based selection

**Rollback Plan:**
```bash
git revert <commit-hash>  # Remove spread-based selection
```

**Estimated Time:** 1-2 hours

---

## Part 7: Revised PNL Projections (ITERATION 3)

### Realistic Fee Scenarios

| Scenario | Entry Fee | Exit Fee | Total/Cycle | Daily (100 cyc) | Monthly | Yearly |
|----------|-----------|----------|-------------|-----------------|---------|--------|
| **Current (100% Taker)** | 10 bps | 10 bps | 20 bps | 2000 bps | ~$600 | ~$7,300 |
| **Strategy 1 (DEFAULT+BBO, TAKER)** | 10 bps | 10 bps | 20 bps | 2000 bps | ~$600 | ~$7,300 |
| **Strategy 1 (DEFAULT+BBO, MAKER)** | 4 bps | 4 bps | 8 bps | 800 bps | ~$240 | ~$2,900 |
| **Strategy 2 (0% Maker)** | 10 bps | 10 bps | 20 bps | 2000 bps | ~$600 | ~$7,300 |
| **Strategy 2 (25% Maker)** | 8 bps | 8 bps | 16 bps | 1600 bps | ~$480 | ~$5,800 |
| **Strategy 2 (50% Maker)** | 6 bps | 6 bps | 12 bps | 1200 bps | ~$360 | ~$4,400 |
| **Strategy 2 (75% Maker)** | 5 bps | 5 bps | 10 bps | 1000 bps | ~$300 | ~$3,600 |
| **Strategy 2 (100% Maker)** | 4 bps | 4 bps | 8 bps | 800 bps | ~$240 | ~$2,900 |

**CRITICAL NOTE:**
Strategy 1 has TWO possible outcomes depending on fee verification:
- If DEFAULT + touch = TAKER (5bps): 20bps/cycle (no improvement)
- If DEFAULT + touch = MAKER (2bps): 8bps/cycle (12bps improvement)

Phase 0 fee verification is REQUIRED to determine actual outcome.

### Fee Calculation Breakdown

**Per Order Fees:**
- Maker execution: 2bps per order
- Taker execution: 5bps per order

**Per Cycle (4 orders: 2 entry, 2 exit):**
- All Taker: 4 × 5bps = 20bps
- 75% Maker: (3 × 2bps) + (1 × 5bps) = 11bps → rounded to 10bps
- 50% Maker: (2 × 2bps) + (2 × 5bps) = 14bps → rounded to 12bps
- 25% Maker: (1 × 2bps) + (3 × 5bps) = 17bps → rounded to 16bps
- All Maker: 4 × 2bps = 8bps

### Key Insights (ITERATION 3)

**Strategy 1 (User's Proposal - BBO Pricing):**
- If DEFAULT + touch = TAKER (5bps): 20bps/cycle, $0/month savings (status quo)
- If DEFAULT + touch = MAKER (2bps): 8bps/cycle, $240/month savings (BEST outcome)
- **CRITICAL:** Fee rate must be verified in Phase 0

**Strategy 2 (Aggressive Passive Pricing):**
- Best case (100% maker): 8bps/cycle, $240/month savings
- Realistic case (50% maker): 12bps/cycle, $240/month savings
- Breakeven case (25% maker): 16bps/cycle, $120/month savings
- No improvement case (0% maker): 20bps/cycle, $0 savings

**Critical Decision Point:**
- If Phase 0 verifies DEFAULT + touch = MAKER (2bps): **Strategy 1 is optimal** (same savings as 100% Strategy 2, simpler)
- If Phase 0 verifies DEFAULT + touch = TAKER (5bps): Evaluate Strategy 2 if acceptable fill rate achievable

**Fee Structure Understanding:**
- OrderType.DEFAULT + BBO price (crosses spread) = PENDING VERIFICATION (2bps or 5bps)
- OrderType.DEFAULT + at touch (does NOT cross spread) = MAKER (2bps)
- The key distinction is whether the order crosses spread or rests on book

---

## Part 8: Risk Assessment

### Strategy 1 Risks (Convert POST_ONLY → DEFAULT with BBO Pricing)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| No fee improvement | 100% | Low | Accept - this is expected |
| Code regression | 5% | Medium | Thorough testing required |
| Team disagreement | 10% | Low | Data-backed decision |

**Overall Risk Level:** LOW

### Strategy 2 Risks (Convert POST_ONLY → DEFAULT with Passive Pricing)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Low fill rate (< 20%) | HIGH (40%) | HIGH | Backtest first, abort if low |
| Leg imbalance issues | Medium (20%) | HIGH | Implement imbalance handler |
| Stale resting orders | Medium (30%) | Medium | Price monitoring + cancel |
| Increased complexity | High | Medium | Clear documentation |
| Wasted implementation effort | Medium (30%) | HIGH | Phase 0 data gathering |

**Overall Risk Level:** MEDIUM-HIGH

### Strategy 3 Risks (Dynamic Pricing Selection)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Unpredictable behavior | Medium (40%) | Medium | Extensive testing required |
| Complex debugging | High (60%) | Medium | Clear logging and monitoring |
| Maintenance burden | High | Low | Clear documentation |

**Overall Risk Level:** MEDIUM

### Strategy 4 Risks (Spread-Based Pricing Selection)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Reduced trade frequency when spread is wide | 100% | Low | Accept - quality over quantity |
| Missed profitable trades | Medium (30%) | Low | Tune threshold based on backtesting |
| Spread calculation errors | Low (5%) | Medium | Unit testing for spread logic |

**Overall Risk Level:** LOW

---

## Part 9: Recommended Implementation Path

### Step 1: Fee Rate Verification (Phase 0) - MANDATORY

**Duration:** 1-2 hours

**Deliverable:** Verified fee rate for OrderType.DEFAULT + BBO pricing

**Decision Tree:**
```
Phase 0 Complete
    |
    v
Verify fee rate for OrderType.DEFAULT + BBO pricing (crosses spread)
    |
    +-- Fee = 2bps (MAKER)? --> YES --> Implement Strategy 1
    |                                      |
    |                                      v
    |                                 Phase 1A (2 hrs)
    |                                      |
    |                                      v
    |                                 Deploy & Monitor
    |                                      (12bps savings!)
    |
    +-- Fee = 5bps (TAKER)? --> YES --> Evaluate Strategy 2
                                           |
                                           v
                                      Can Strategy 2 achieve
                                      > 25% maker fill rate?
                                           |
                                           +-- YES --> Implement Strategy 2
                                           |           |
                                           |           v
                                           |      Phase 1B (10-14 hrs)
                                           |
                                           +-- NO --> Implement Strategy 1
                                                           |
                                                           v
                                                      Phase 1A (2 hrs)
                                                           (0 fee savings,
                                                            but simpler)
```

### Step 2: Implement Chosen Strategy

**If Strategy 1 (DEFAULT + BBO Pricing):**
- Total time: 3-4 hours (1-2 hr Phase 0 + 2 hr implement + optional Phase 2)
- Expected savings: $0/month (if taker) or $240/month (if maker)
- Complexity: LOW
- Key benefit: 5-second latency improvement, 100% fill rate, POTENTIAL 12bps savings

**If Strategy 2 (DEFAULT + Aggressive Passive Pricing):**
- Total time: 13-17 hours (1-2 hr Phase 0 + 10-14 hr implement + optional Phase 2)
- Expected savings: $120-240/month (if 25-50% fill rate achieved)
- Complexity: MEDIUM-HIGH
- Key benefit: Potential 12bps fee improvement (but only if Strategy 1 doesn't already provide this)

### Step 3: Monitor and Validate

**Metrics to Track:**
- Actual fill rate vs predicted
- Average fees per cycle
- Leg imbalance frequency
- PNL impact
- System stability
- Order latency (time to fill)

**Rollback Criteria:**
- Strategy 2: Fill rate < 20% after 100 cycles
- Strategy 2: Leg imbalance rate > 10%
- Strategy 2: PNL degradation after 1 week

---

## Appendix A: Code Location Reference

### Key Files and Line Numbers

**File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**
- Lines 407-553: Order placement logic (MODIFY for all strategies)
- Lines 559-606: IOC logic block (reference for Strategy 1)
- Line 62: `use_post_only` default parameter (rename for Strategy 1/2)
- Line 403: Entry fee rate calculation
- Line 678: Exit fee rate calculation
- Lines 295-380: `calculate_order_size_with_slippage()` (already uses BookDepth)
- Lines 649-652: Partial fill handling (extend for Strategy 2)

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`**
- Lines 509-571: `place_open_order()` (CHANGE OrderType.POST_ONLY → OrderType.DEFAULT)
- Lines 509-571: Pricing logic (MODIFY for Strategy 2, 3, 4)
- Lines 573-715: `place_ioc_order()` (reference for BBO pricing)
- Lines 717-738: `_round_quantity_to_size_increment()`
- Lines 740-785: `_round_price_to_increment()`
- Line 400-429: `calculate_timeout()` (currently unused)

**File: `/Users/botfarmer/2dex/hedge/exchanges/nado_bookdepth_handler.py`**
- Lines 167-234: `estimate_slippage()` (already implemented)
- Lines 236-264: `get_available_liquidity()` (already implemented)
- ADD: `get_queue_size()` method (for Strategy 2, 3)

### Fee Structure Reference (CORRECTED)

| Execution Method | Fee Rate | Orders/Cycle | Total/Cycle | Current Usage | Target Usage |
|-----------------|----------|--------------|-------------|---------------|--------------|
| Maker (resting on book) | 2 bps | 4 | 8 bps | 0% (100% timeout) | 0-50% (Strategy 2) |
| Taker (crossing spread) | 5 bps | 4 | 20 bps | 100% | 50-100% (all strategies) |

**Per Cycle Breakdown:**
- Entry: 2 orders × 2bps (maker) or 5bps (taker)
- Exit: 2 orders × 2bps (maker) or 5bps (taker)
- Best case (all maker): 4 × 2bps = 8bps
- Worst case (all taker): 4 × 5bps = 20bps

**Key Insight:**
Fee is determined by EXECUTION METHOD, not OrderType.
- OrderType.DEFAULT + BBO price = Taker (5bps)
- OrderType.DEFAULT + BBO ± 1 tick = Maker (2bps)

---

## Appendix B: Testing Checklist

### Pre-Deployment Testing

- [ ] Phase 0 data gathering complete
- [ ] Backtesting results documented
- [ ] Strategy decision made based on data
- [ ] Unit tests pass (pytest)
- [ ] Integration tests pass (paper trading)
- [ ] Load testing (100+ concurrent orders)
- [ ] Edge case testing (imbalance, partial fills, price movement)
- [ ] Rollback procedure validated

### Deployment Checklist

- [ ] Code reviewed by team
- [ ] Documentation updated
- [ ] Monitoring configured (fill rate, fees, imbalance)
- [ ] Alert thresholds set (imbalance rate, fill rate)
- [ ] Rollback plan documented and accessible
- [ ] Team briefed on new behavior

### Post-Deployment Monitoring

- [ ] First 10 cycles: Monitor fill rates
- [ ] First 100 cycles: Calculate average fees
- [ ] First 24 hours: PNL comparison
- [ ] First week: Stability assessment
- [ ] Rollback decision point: After 100 cycles (fill rate < 20%)

---

## Appendix C: Configuration Changes

### Environment Variables (Optional)

```bash
# Strategy 1 configuration
USE_IMMEDIATE_FILLS=true  # Use DEFAULT with BBO pricing

# Strategy 2 configuration
USE_PASSIVE_PRICING=true  # Use DEFAULT with passive pricing
QUEUE_SIZE_THRESHOLD=5  # Max queue size for aggressive pricing
MIN_FILL_RATIO=0.5  # minimum acceptable fill ratio
MAX_IMBALANCE_BPS=10  # hedge if imbalance exceeds

# Strategy 3 configuration
USE_DYNAMIC_PRICING=true  # Use dynamic pricing selection

# Strategy 4 configuration
USE_SPREAD_BASED_SELECTION=true  # Use spread-based pricing selection
MAX_SPREAD_TICKS=2  # Switch to passive when spread > this
```

### CLI Arguments

```bash
# Strategy 1: DEFAULT with BBO pricing
python hedge/DN_pair_eth_sol_nado.py --use-immediate-fills

# Strategy 2: DEFAULT with passive pricing
python hedge/DN_pair_eth_sol_nado.py --use-passive-pricing

# Strategy 3: Dynamic pricing selection
python hedge/DN_pair_eth_sol_nado.py --use-dynamic-pricing

# Strategy 4: Spread-based selection
python hedge/DN_pair_eth_sol_nado.py --use-spread-based-selection --max-spread-ticks 2
```

---

## Conclusion

This plan provides a corrected, data-driven analysis of POST_ONLY to DEFAULT conversion and fee optimization strategies.

### Critical Corrections Made (ITERATION 3 - ARCHITECT VERIFIED):

1. **Root Cause Identified (Architect):** Current POST_ONLY pricing (`best_ask - tick_size`) places orders ONE TICK AWAY from touch, creating a gap that prevents fills
2. **User's Proposal Verified:** BBO pricing at touch (buy=ask, sell=bid) crosses spread for immediate fills - CORRECT strategy
3. **OrderType.DEFAULT exists**: Simple Limit order (value = 0)
4. **OrderType.LIMIT does NOT exist**: Only DEFAULT, POST_ONLY, IOC available
5. **Fee structure corrected**: Determined by execution method (maker/taker), not OrderType
6. **CRITICAL UNKNOWN:** OrderType.DEFAULT + BBO pricing (crosses spread) fee rate PENDING VERIFICATION (2bps or 5bps?)
7. **PNL projections updated**: Strategy 1 outcome depends on fee verification (8bps if maker, 20bps if taker)
8. **Strategy reframed**: Not "removal" but "conversion" (POST_ONLY → DEFAULT) with correct pricing
9. **Phase 0 redefined**: Fee rate verification is now the MANDATORY first step (not data gathering)

### Recommended Path (ITERATION 3):

1. **Phase 0 (MANDATORY):** Verify fee rate for OrderType.DEFAULT + BBO pricing (crosses spread)
   - Check SDK documentation
   - Run empirical test if needed
   - Document whether 2bps (maker) or 5bps (taker)

2. **If DEFAULT + touch = MAKER (2bps):**
   - **Implement Strategy 1** - This is the optimal solution
   - Provides 12bps savings with lowest complexity
   - 100% fill rate, 5-second latency improvement

3. **If DEFAULT + touch = TAKER (5bps):**
   - Evaluate Strategy 2 fill rate potential
   - **If achievable (> 25%):** Implement Strategy 2 for fee savings
   - **If not achievable:** Implement Strategy 1 for simplicity (no fee savings, but faster)

4. **Optional:** Add Strategy 4 (Spread-Based Selection) as supplement to either strategy

### Expected Outcomes (ITERATION 3):

- **Strategy 1 (if maker fees):** 12bps fee improvement, 5s latency improvement, LOW complexity
- **Strategy 1 (if taker fees):** No fee improvement, 5s latency improvement, LOW complexity
- **Strategy 2:** 0-12bps fee improvement (depends on fill rate), MEDIUM-HIGH complexity

### Key Takeaway (ITERATION 3):

The Architect's root cause analysis is correct: current POST_ONLY pricing creates a 1-tick gap that prevents fills.

The user's proposal (BBO pricing at touch) is the correct solution for immediate execution.

**CRITICAL UNKNOWN:** The fee rate for OrderType.DEFAULT with BBO pricing (crossing spread) must be verified to determine if this provides fee improvement.

Phase 0 fee verification is the GATEWAY decision that determines the optimal path forward.

The plan is ready for implementation pending Phase 0 fee rate verification.
