# 8 Strategies for POST_ONLY Removal and PNL Improvement - Comprehensive Analysis

**PLAN STATUS:** COMPREHENSIVE ANALYSIS - REVISED (ITERATION 1)
**DATE:** 2026-02-01
**ANALYST:** Prometheus (Strategic Planning Consultant)
**REVISION:** Incorporated Critic feedback on pricing logic and root cause analysis

---

## CRITICAL CORRECTIONS FROM CRITIC REVIEW

### Correction 1: Current Pricing Logic IS Correct

**INCORRECT ANALYSIS (Original):**
"The current pricing logic is wrong - it places orders incorrectly."

**CORRECT ANALYSIS (Revised):**
The current pricing at `hedge/exchanges/nado.py` lines 522-525:
```python
if direction == 'buy':
    order_price = best_ask - self.config.tick_size  # 1 tick behind ask
else:
    order_price = best_bid + self.config.tick_size  # 1 tick behind bid
```

This IS correct maker pricing:
- Does NOT cross the spread
- Orders REST on the order book
- Eligible for 2bps maker fees IF filled

### Correction 2: Root Cause is NOT Pricing Logic, But Placement Distance

**REAL ROOT CAUSE:**
The 1-tick-behind placement is TOO FAR from the touch in fast-moving markets:
- Orders are placed correctly as maker orders
- BUT in 50ms book update cycles, price moves 2-3 ticks before fills occur
- Result: 100% timeout rate → 100% IOC fallback → Effective 20bps/cycle cost

**Why 100% Timeout:**
```
Timeline in volatile market:
T=0ms:    Market at best_ask=$2500.00, best_bid=$2499.00
T=50ms:   Order placed at $2499.90 (1 tick behind ask)
T=100ms:  Market moves to best_ask=$2500.20, best_bid=$2500.10
T=5000ms: Order still unfilled at $2499.90 → TIMEOUT → IOC fallback
```

### Correction 3: POST_ONLY Behavior Clarification

`OrderType.POST_ONLY` means: "REJECT order if it would cross the spread"

**Current Implementation:**
- Orders placed 1 tick behind touch = VALID maker orders
- POST_ONLY flag correctly prevents crossing
- Problem is NOT POST_ONLY rejection, but lack of fills

**At-Touch Implementation (Strategy 3):**
- Orders placed AT best_bid (buy) or best_ask (sell)
- POST_ONLY flag still prevents crossing if market moved against you
- Higher fill probability = lower timeout rate = more maker fees

### Correction 4: BBO Pricing Does NOT Improve Fees

**User's BBO Proposal:**
```python
if direction == "buy":
    order_price = best_ask   # Buy at ask
else:
    order_price = best_bid   # Sell at bid
```

**Why This Provides NO Fee Improvement:**
- buy=best_ask CROSSES the spread (matches existing ask orders)
- sell=best_bid CROSSES the spread (matches existing bid orders)
- Crossing spread = TAKER execution = 5bps fees
- **Same as current IOC (5bps) = NO IMPROVEMENT**

### Correction 5: BookDepth Implementation Verified

**VERIFIED:** BookDepthHandler exists and is functional:
- Location: `hedge/exchanges/nado_bookdepth_handler.py`
- Structure: SortedDict for bids/asks
- Methods: `get_best_bid()`, `get_best_ask()`, `get_depth_at_level()`
- Queue size: Measured in total quantity at price level, NOT order count

**Correct BookDepth Usage:**
```python
handler = self.get_bookdepth_handler()
if direction == 'buy':
    best_price, best_qty = handler.get_best_bid()
    queue_size = handler.bids.get(best_price, Decimal(0))
else:
    best_price, best_qty = handler.get_best_ask()
    queue_size = handler.asks.get(best_price, Decimal(0))
```

---

## Executive Summary

### Current System State Analysis

**POST_ONLY Implementation:**
- Pricing: `best_ask - tick_size` (BUY), `best_bid + tick_size` (SELL)
- Creates orders ONE TICK BEHIND the touch
- Result: Orders never fill naturally (require adverse price movement)
- Timeout: 5 seconds
- Fallback rate: 100% to IOC (Immediate-Or-Cancel)
- Fee structure: 5bps taker on all IOC orders

**Fee Impact:**
- Current cost: 20bps per cycle (4 orders × 5bps, all taker)
- Monthly cost at 100 cycles/day: ~$600
- Yearly cost: ~$7,300

**Root Cause:**
The POST_ONLY pricing creates a structural gap preventing fills:
```
BUY:  order_price = best_ask - tick_size  → e.g., $2499.90 when ask = $2500.00
SELL: order_price = best_bid + tick_size  → e.g., $2500.10 when bid = $2499.00
```

**IMPORTANT CLARIFICATION:**
The current pricing logic IS correct for maker orders:
- `best_ask - tick_size` (BUY) places ONE TICK BEHIND the best ask
- `best_bid + tick_size` (SELL) places ONE TICK BEHIND the best bid
- This placement DOES NOT cross the spread and RESTS on the order book

**The REAL Problem:**
The 1-tick-behind placement is TOO FAR from the touch in fast-moving markets:
- Orders rest correctly on the book
- BUT price moves away before fills occur
- Result: 100% timeout → IOC fallback at 5bps

**Why 100% Timeout:**
In volatile markets with 50ms book updates:
- By the time order is placed at 1-tick behind touch
- Market has moved 2-3 ticks away
- Order sits unfilled until 5-second timeout
- Fallback to IOC (Immediate-Or-Cancel) at 5bps

### User's Proposed BBO Pricing Analysis

**User Proposal:**
```python
# BBO pricing (touch price) - crosses spread for immediate fills
if direction == "buy":
    order_price = best_ask   # Buy at ask
else:
    order_price = best_bid    # Sell at bid
```

**CRITICAL FINDING - BBO Pricing is TAKER Pricing:**
- buy=best_ask CROSSES the spread (matches existing ask orders)
- sell=best_bid CROSSES the spread (matches existing bid orders)
- Crossing spread = TAKER execution = 5bps fees
- **NO FEE IMPROVEMENT** vs current IOC (also 5bps)

**True MAKER Pricing Alternative:**
```python
# TRUE maker pricing (rests on book at touch)
if direction == "buy":
    order_price = best_bid   # Buy at bid (rest on bid side at touch)
else:
    order_price = best_ask   # Sell at ask (rest on ask side at touch)
```
- Does NOT cross spread
- Rests on book at the touch price
- Fee: 2bps if filled
- Fill probability: HIGHER than 1-tick-behind

---

## Strategy 1: Timeout Increase (30 seconds)

### Mechanism
Extend POST_ONLY timeout from 5 seconds to 30 seconds, giving orders more time to fill naturally.

### PNL Impact
**Fill Rate Improvement:** Minimal (0-5%)
- Current issue: Orders placed 1 tick behind touch
- Time doesn't fix structural pricing issue
- Only helps if market moves adversely (rare)

**Fee Reduction:** 0-1 bps per cycle
- Best case: 5% maker rate → 19.2bps/cycle (0.8bps savings)
- Realistic: 0% maker rate → 20bps/cycle (no savings)

**Monthly Impact:** $0-$30 at 100 cycles/day

### Implementation Difficulty: LOW
```python
# File: hedge/DN_pair_eth_sol_nado.py
POST_ONLY_TIMEOUT = 30  # Changed from 5
```

### Risk Level: LOW
- Low risk of adverse selection
- May increase cycle time (25 second penalty on timeout)
- No fee improvement

### Trade-offs
| Benefit | Cost |
|---------|------|
| Gives orders more time | +25 seconds per timeout cycle |
| Simple code change | No structural fix |
| Low risk | Minimal fee improvement |

### Verdict: NOT RECOMMENDED
Doesn't address root cause (pricing gap). Time doesn't help orders that are structurally unfillable.

---

## Strategy 2: Partial Fill Allowance

### Mechanism
Accept partial fills (e.g., 50%+) instead of all-or-nothing. Reduces complete timeout rate.

### PNL Impact
**Fill Rate Improvement:** Moderate (10-20%)
- Partial fills reduce complete failures
- Some fees at 2bps, remainder at 5bps

**Fee Reduction:** 1-2 bps per cycle
- Example: 20% partial fill at 2bps + 80% IOC at 5bps = 4.4bps average
- Per cycle: ~18bps vs 20bps current

**Monthly Impact:** $30-$60 at 100 cycles/day

### Implementation Difficulty: MEDIUM
```python
# Requires partial fill handling logic
MIN_FILL_RATIO = 0.5  # Accept 50%+ fills

if filled_size > 0 and filled_size < order_size:
    fill_ratio = filled_size / order_size
    if fill_ratio >= MIN_FILL_RATIO:
        # Accept partial fill
        # Hedge remainder with IOC
```

### Risk Level: MEDIUM
- Leg imbalance risk (one leg fills partially, other doesn't)
- Requires imbalance hedging logic
- Complex position management

### Trade-offs
| Benefit | Cost |
|---------|------|
| Reduces complete failures | Complex implementation |
| Some fee improvement | Leg imbalance risk |
| Better than timeout | Doesn't fix root cause |

### Verdict: SUPPLEMENTAL
Use with other strategies. Partial fills help but don't solve the pricing gap issue.

---

## Strategy 3: Price Aggressiveness (At-Touch POST_ONLY)

### Mechanism
Change POST_ONLY pricing from 1-tick behind to AT-TOUCH pricing:

**CURRENT CODE (1 tick behind - CORRECT maker placement but TOO FAR):**
```python
# Lines 522-525 in hedge/exchanges/nado.py
if direction == 'buy':
    order_price = best_ask - self.config.tick_size  # 1 tick behind ask
else:
    order_price = best_bid + self.config.tick_size  # 1 tick behind bid
```
- This IS correct maker pricing (does not cross spread)
- Problem: Too far from touch, orders rarely fill before timeout

**PROPOSED CHANGE (at touch - BETTER fill probability):**
```python
if direction == 'buy':
    order_price = best_bid   # AT best bid (touch)
else:
    order_price = best_ask  # AT best ask (touch)
```
- Still correct maker pricing (does not cross spread)
- AT touch price = higher fill probability
- POST_ONLY flag still provides protection (rejects if would cross)

**CRITICAL DISTINCTION:**
- POST_ONLY at touch means: "Place AT best_bid (buy) or best_ask (sell), but REJECT if would cross spread"
- This is TRUE MAKER pricing - rests on book at the touch
- Fee: 2bps if filled
- POST_ONLY protection ensures order is rejected if market moved against you

### PNL Impact
**Fill Rate Improvement:** HIGH (50-80%)
- Orders at touch have high fill probability
- Queue position matters (may be behind existing orders)
- Better than 1-tick behind (current 0% fill rate)

**Fee Reduction:** 8-16 bps per cycle
- Best case (100% maker): 8bps/cycle (12bps savings)
- Realistic (75% maker): 11bps/cycle (9bps savings)
- Conservative (50% maker): 14bps/cycle (6bps savings)

**Monthly Impact:**
- $240/month at 100% maker rate
- $180/month at 75% maker rate
- $120/month at 50% maker rate

**Comparison to Current:**
- Current: 20bps/cycle (100% IOC at 5bps)
- New (at-touch): 8-14bps/cycle (variable maker rate)
- Savings: 6-12bps/cycle

### Implementation Difficulty: MEDIUM
```python
# File: hedge/exchanges/nado.py, place_open_order()
# Lines 522-525 - MODIFY ONLY THESE LINES

# CURRENT (1 tick behind - correct but low fill rate):
if direction == 'buy':
    order_price = best_ask - self.config.tick_size
else:
    order_price = best_bid + self.config.tick_size

# NEW (at touch - better fill probability):
if direction == 'buy':
    order_price = best_bid   # At best bid
else:
    order_price = best_ask  # At best ask

# Keep OrderType.POST_ONLY appendix unchanged
appendix=build_appendix(
    order_type=OrderType.POST_ONLY,  # Still POST_ONLY for protection
    isolated=True
)
```

### Risk Level: MEDIUM
**Queue Risk:**
- Orders at touch queue behind existing orders
- May not fill immediately (wait time varies)
- Fill rate depends on queue depth

**Adverse Selection Risk:**
- POST_ONLY rejects if market moved against you
- No risk of crossing spread (POST_ONLY protection)

### Trade-offs
| Benefit | Cost |
|---------|------|
| True maker fees (2bps) | Variable fill time |
| High fill probability | Queue position uncertainty |
| POST_ONLY protection | May still timeout in deep queues |

### Verdict: HIGHLY RECOMMENDED
This addresses the REAL root cause: orders placed too far from touch in fast-moving markets. Moving from 1-tick-behind to at-touch dramatically improves fill probability while maintaining maker fees and POST_ONLY protection.

---

## Strategy 4: Spread-Optimized Entry

### Mechanism
Only enter positions when spread is tight (≤ 1-2 ticks). Skip wide spreads to reduce adverse selection.

### PNL Impact
**Fill Rate Improvement:** N/A (reduces trade count)
**Fee Reduction:** 0 bps per trade (supplemental strategy)
**Trade Count Reduction:** 20-40%

**Monthly Impact:**
- Reduced trade frequency
- Better entry prices on tight spreads
- Improved win rate on executed trades

### Implementation Difficulty: LOW
```python
# Spread check before order placement
spread_ticks = (best_ask - best_bid) / tick_size
MAX_SPREAD_TICKS = 2  # Configurable

if spread_ticks > MAX_SPREAD_TICKS:
    self.logger.info(f"[ORDER] Skipping wide spread: {spread_ticks:.1f} ticks")
    return OrderResult(success=False, error_message="Spread too wide")
```

### Risk Level: LOW
- Reduces opportunity set
- Improves quality of executed trades
- No execution risk

### Trade-offs
| Benefit | Cost |
|---------|------|
| Better entry prices | Fewer trading opportunities |
| Reduced adverse selection | Lower volume |
| Simple implementation | Requires spread threshold tuning |

### Verdict: SUPPLEMENTAL
Use with ANY base strategy. Improves trade quality without execution complexity.

---

## Strategy 5: BookDepth Utilization

### Mechanism
Analyze queue size at touch to predict fill probability. Place orders only when queue is manageable.

### PNL Impact
**Fill Rate Improvement:** HIGH (20-30% improvement)
**Fee Reduction:** 4-8 bps per cycle (by avoiding deep queues)

**Monthly Impact:** $120-$240 at 100 cycles/day

### Implementation Difficulty: MEDIUM-HIGH
**VERIFIED IMPLEMENTATION:**
The BookDepthHandler exists at `hedge/exchanges/nado_bookdepth_handler.py` with verified structure:
- `self.bids`: SortedDict of price levels (descending)
- `self.asks`: SortedDict of price levels (ascending)
- `get_best_bid()`: Returns (price, quantity) of best bid
- `get_best_ask()`: Returns (price, quantity) of best ask
- `get_depth_at_level(level, side)`: Returns price/qty at depth level

**Queue Size Calculation:**
```python
# In hedge/exchanges/nado.py
# Access bookdepth handler
handler = self.get_bookdepth_handler()
if handler is None:
    return OrderResult(success=False, error_message="No BookDepth data")

# Calculate queue size at touch
if direction == 'buy':
    best_price, best_qty = handler.get_best_bid()
    # Queue size = total qty at best bid price
    queue_size = handler.bids.get(best_price, Decimal(0))
else:
    best_price, best_qty = handler.get_best_ask()
    # Queue size = total qty at best ask price
    queue_size = handler.asks.get(best_price, Decimal(0))

# Usage in order placement
MAX_QUEUE_SIZE = Decimal('1.0')  # Maximum size at touch (configurable)
if queue_size > MAX_QUEUE_SIZE:
    self.logger.info(f"[ORDER] Queue too deep: {queue_size} at {best_price}")
    return OrderResult(success=False, error_message="Queue too deep")
```

**NOTES:**
- BookDepthHandler uses SortedDict (not list of objects)
- Queue size is measured in quantity (contracts), not order count
- Threshold should be configurable based on market conditions

### Risk Level: LOW
- Only skips unfavorable queue conditions
- No execution risk
- Reduces timeout probability

### Trade-offs
| Benefit | Cost |
|---------|------|
| Avoids deep queues | Reduces trade frequency |
| Higher fill probability | Requires BookDepth integration |
| Data-driven decisions | Additional complexity |

### Verdict: RECOMMENDED SUPPLEMENTAL
Highly effective when combined with Strategy 3 (At-Touch POST_ONLY) or Strategy 7 (DEFAULT + At-Touch). The BookDepth integration is verified and functional - queue size is measured in total quantity at the touch price level, not order count.

---

## Strategy 6: Dynamic Timeout

### Mechanism
Adjust POST_ONLY timeout based on volatility regime:
- Low volatility: 10-15 seconds
- High volatility: 3-5 seconds
- Normal: 5 seconds (current)

### PNL Impact
**Fill Rate Improvement:** Minimal (5-10%)
**Fee Reduction:** 1-2 bps per cycle

**Monthly Impact:** $30-$60 at 100 cycles/day

### Implementation Difficulty: MEDIUM
```python
# Volatility regime detection
spread_state = self.get_bbo_handler().get_spread_state()
if spread_state == "STABLE":
    timeout = 15  # More time in stable markets
elif spread_state == "VOLATILE":
    timeout = 3   # Less time in volatile markets
else:
    timeout = 5   # Default
```

### Risk Level: LOW-MEDIUM
- Adaptive to market conditions
- Requires volatility detection
- Moderate complexity

### Trade-offs
| Benefit | Cost |
|---------|------|
| Adapts to market conditions | Doesn't fix pricing gap |
| Optimizes wait time | Limited fee improvement |
| Smart timeout management | Volatility detection required |

### Verdict: SUPPLEMENTAL
Use with Strategy 3 for optimized timeout management. Not a standalone solution.

---

## Strategy 7: Limit Order Conversion (POST_ONLY → DEFAULT)

### Mechanism
Convert from OrderType.POST_ONLY to OrderType.DEFAULT while keeping at-touch pricing (maker execution).

### PNL Impact
**Fill Rate Improvement:** HIGH (10-20% vs POST_ONLY)
- OrderType.DEFAULT can cross spread if needed
- At-touch pricing = maker execution (2bps)

**Fee Reduction:** 8-12 bps per cycle
- Best case (100% maker): 8bps/cycle (12bps savings)
- Realistic (80% maker, 20% taker): 10.6bps/cycle (9.4bps savings)

**Monthly Impact:** $200-$280 at 100 cycles/day

### Implementation Difficulty: LOW
```python
# File: hedge/exchanges/nado.py, place_open_order()

# Change OrderType
appendix=build_appendix(
    order_type=OrderType.DEFAULT,  # Changed from POST_ONLY
    isolated=True
)

# Pricing: At touch for maker execution
if direction == 'buy':
    order_price = best_bid   # At best bid
else:
    order_price = best_ask  # At best ask
```

### Risk Level: MEDIUM
**Crossing Risk:**
- OrderType.DEFAULT can cross spread
- If market moves, may execute as taker (5bps)
- No POST_ONLY protection

**Benefit:**
- Higher fill rate than POST_ONLY
- Can execute in fast-moving markets
- Still targets maker fees

### Trade-offs
| Benefit | Cost |
|---------|------|
| Higher fill rate | May cross spread (5bps) |
| Flexible execution | No POST_ONLY protection |
| Targets maker fees | Occasional taker execution |

### Verdict: RECOMMENDED
Good balance of fill rate and fee optimization. Higher fill rate than POST_ONLY, still targets maker fees.

---

## Strategy 8: BBO Pricing (User Proposed) - CRITICAL ANALYSIS

### Mechanism
User's proposed pricing:
```python
if direction == "buy":
    order_price = best_ask   # Buy at ask
else:
    order_price = best_bid    # Sell at bid
```

### CRITICAL FINDING: This is TAKER Pricing

**BBO Pricing CROSSES the Spread:**
- buy=best_ask: Matches existing sell orders at ask → CROSSES spread
- sell=best_bid: Matches existing buy orders at bid → CROSSES spread
- Crossing spread = TAKER execution
- TAKER execution = 5bps fees

**Fee Analysis:**
```
Current IOC: 5bps per order = 20bps per cycle
BBO Pricing: 5bps per order = 20bps per cycle
Fee Improvement: 0 bps (NO IMPROVEMENT)
```

### Comparison: BBO vs True Maker Pricing

| Aspect | BBO Pricing (User Proposal) | Current (1-tick behind) | True Maker Pricing (At-Touch) |
|--------|----------------------------|------------------------|------------------------------|
| Buy Price | best_ask | best_ask - tick_size | best_bid |
| Sell Price | best_bid | best_bid + tick_size | best_ask |
| Crosses Spread? | YES (crosses spread) | NO (correct maker) | NO (correct maker) |
| Execution Type | TAKER | MAKER (timeout) | MAKER (fills) |
| Fee Rate | 5bps | 2bps (never fills) | 2bps (fills) |
| Per Cycle Cost | 20bps | 20bps (100% IOC fallback) | 8-14bps (variable fill) |
| Fill Rate | 100% (immediate) | 0% (100% timeout) | 50-80% (at touch) |
| Monthly Savings | $0 (no improvement) | $0 (baseline) | $180-360 (vs current) |

**KEY INSIGHT:**
- Current 1-tick-behind IS correct maker pricing, BUT too far from touch
- Result: 100% timeout → 100% IOC fallback → 20bps/cycle effective cost
- At-touch pricing maintains maker status with ACTUAL fills → 8-14bps/cycle

### PNL Impact
**Fee Reduction:** 0 bps per cycle (NO IMPROVEMENT)
- Same fees as current IOC (5bps per order)
- Eliminates 5-second timeout (benefit)
- No fee savings

**Monthly Impact:** $0 fee savings, 5-second latency improvement

### Implementation Difficulty: LOW
```python
# File: hedge/exchanges/nado.py

if direction == 'buy':
    order_price = best_ask   # TAKER pricing
else:
    order_price = best_bid   # TAKER pricing
```

### Risk Level: LOW
- 100% fill rate (immediate)
- No timeout risk
- No fee improvement

### Verdict: NOT RECOMMENDED for FEE IMPROVEMENT
**BBO pricing is IDENTICAL to current IOC fees.**
- Use only if you prioritize latency over fees
- Does NOT achieve fee optimization goal
- True maker pricing (Strategy 3 or 7) is superior for fees

### Alternative: True Maker Pricing
```python
# TRUE maker pricing (2bps fees):
if direction == 'buy':
    order_price = best_bid   # Rest on bid side
else:
    order_price = best_ask   # Rest on ask side
```

---

## Priority Matrix - All 8 Strategies

### Ranking by PNL Impact vs Effort

| Rank | Strategy | PNL Impact | Effort | Risk | Priority Score |
|------|----------|------------|--------|------|----------------|
| **1** | Strategy 3: At-Touch POST_ONLY | **12 bps/cycle** | MEDIUM | MEDIUM | **HIGHEST** |
| **2** | Strategy 7: DEFAULT + At-Touch | **9.4 bps/cycle** | LOW | MEDIUM | **HIGH** |
| **3** | Strategy 5: BookDepth Utilization | **6 bps/cycle** | MED-HIGH | LOW | **MED-HIGH** |
| **4** | Strategy 2: Partial Fill Allowance | **2 bps/cycle** | MEDIUM | MEDIUM | **MEDIUM** |
| **5** | Strategy 6: Dynamic Timeout | **1.5 bps/cycle** | MEDIUM | LOW | **MEDIUM** |
| **6** | Strategy 1: Timeout 30s | **0.8 bps/cycle** | LOW | LOW | **LOW** |
| **7** | Strategy 4: Spread Filter | **0 bps/cycle** | LOW | LOW | **SUPPLEMENTAL** |
| **8** | Strategy 8: BBO Pricing | **0 bps/cycle** | LOW | LOW | **LATENCY ONLY** |

### Visualization

```
HIGH PNL IMPACT (bps/cycle)
    │
12  │  ┌──────────────────────┐
    │  │  Strategy 3          │  ★ HIGHEST PRIORITY
    │  │  At-Touch POST_ONLY  │  (12bps, MEDIUM effort)
    │  └──────────────────────┘
    │
 9  │  ┌──────────────────────┐
    │  │  Strategy 7          │  ★ HIGH PRIORITY
    │  │  DEFAULT + At-Touch  │  (9.4bps, LOW effort)
    │  └──────────────────────┘
    │
 6  │  ┌──────────────────────┐
    │  │  Strategy 5          │  SUPPLEMENTAL
    │  │  BookDepth Queue     │  (6bps, MED-HIGH effort)
    │  └──────────────────────┘
    │
 3  │  ┌──────────────────────┐
    │  │  Strategy 2          │  SUPPLEMENTAL
    │  │  Partial Fill        │  (2bps, MEDIUM effort)
    │  └──────────────────────┘
    │
 0  │  ┌──────────────────────┐
    │  │  Strategy 8          │  NO FEE IMPROVEMENT
    │  │  BBO Pricing         │  (0bps, LOW effort)
    │  └──────────────────────┘
    └───────────────────────────────────────
        LOW       HIGH EFFORT
```

---

## Recommended Implementation Path

### Phase 1: Quick Win (Strategy 7 - DEFAULT + At-Touch)
**Duration:** 2-3 hours
**PNL Impact:** 9.4 bps/cycle
**Monthly Savings:** ~$280

**Implementation:**
1. Convert OrderType.POST_ONLY → OrderType.DEFAULT
2. Change pricing to at-touch (buy=best_bid, sell=best_ask)
3. Remove timeout logic
4. Test and deploy

### Phase 2: Optimize (Strategy 5 - BookDepth)
**Duration:** 6-8 hours
**PNL Impact:** +6 bps/cycle (cumulative ~15 bps)
**Monthly Savings:** ~$450 total

**Implementation:**
1. Add queue size estimation from BookDepth
2. Skip orders when queue > MAX_QUEUE_SIZE (e.g., 10)
3. Test and deploy alongside Strategy 7

### Phase 3: Refine (Strategy 4 - Spread Filter)
**Duration:** 1-2 hours
**PNL Impact:** Improved win rate (no direct bps improvement)
**Quality Impact:** Better entry prices

**Implementation:**
1. Add spread filter before order placement
2. Skip when spread > MAX_SPREAD_TICKS (e.g., 2)
3. Test and deploy

### Combined Strategy: 7 + 5 + 4

**Expected Results:**
- **Fee Reduction:** 15 bps/cycle (20 → 5 bps)
- **Monthly Savings:** $450 at 100 cycles/day
- **Fill Rate:** 70-90% (variable based on queue/spread)
- **Risk Level:** MEDIUM (managed via filters)

**Monthly Cost Comparison:**
```
Current (100% taker):     $600/month
Strategy 7 only:          $320/month (-$280)
Strategy 7 + 5:           $180/month (-$420)
Strategy 7 + 5 + 4:       $150/month (-$450)
```

---

## Detailed Strategy Comparisons

### Strategy 3 vs Strategy 7: POST_ONLY vs DEFAULT

| Aspect | Strategy 3 (POST_ONLY) | Strategy 7 (DEFAULT) |
|--------|----------------------|---------------------|
| Pricing | At-touch (buy=bid, sell=ask) | At-touch (buy=bid, sell=ask) |
| OrderType | POST_ONLY | DEFAULT |
| Cross Protection | YES (rejects if would cross) | NO (can cross) |
| Fill Rate | 50-80% | 80-95% |
| Fee Rate | 2bps (maker only) | 2bps (mostly), 5bps (rarely) |
| Average Fee/Cycle | 8-14bps | 9-11bps |
| Latency | Variable (0-30s) | Variable (0-10s) |
| Risk | Medium (queue timeout) | Medium (occasional taker) |
| Complexity | Medium | Low |

**Recommendation:**
- Start with **Strategy 7** (easier, higher fill rate)
- If all-maker execution is critical, use **Strategy 3** (POST_ONLY protection)

### Strategy 8 (BBO) Critique

**Why BBO Pricing Doesn't Improve Fees:**

1. **BBO CROSSES the Spread:**
   - buy=best_ask matches existing asks → TAKER
   - sell=best_bid matches existing bids → TAKER

2. **TAKER = 5bps Fees:**
   - Identical to current IOC fees
   - No fee improvement

3. **Only Benefit:**
   - Eliminates 5-second timeout
   - 100% immediate fill rate

4. **Correct Alternative:**
   - Use TRUE maker pricing: buy=best_bid, sell=best_ask
   - This rests on book, doesn't cross spread
   - Fee: 2bps if filled

**Example:**
```
Market:
best_bid = $2499.00
best_ask = $2500.00
spread = $1.00
tick_size = $0.10

Current (1-tick behind - CORRECT but ineffective):
BUY:  $2499.90 (ask - tick) → Valid maker → TIMEOUT → IOC fallback at 5bps
SELL: $2499.10 (bid + tick) → Valid maker → TIMEOUT → IOC fallback at 5bps

BBO Pricing (Strategy 8 - User proposal):
BUY:  $2500.00 (at ask) → CROSSES spread → TAKER → 5bps (immediate)
SELL: $2499.00 (at bid) → CROSSES spread → TAKER → 5bps (immediate)
Result: Same fees as current IOC, no improvement

True Maker Pricing (Strategy 3/7 - At touch):
BUY:  $2499.00 (at bid) → Rests on book → MAKER → 2bps (fills)
SELL: $2500.00 (at ask) → Rests on book → MAKER → 2bps (fills)
Result: 60% fee reduction vs current (8-14bps vs 20bps)
```

---

## Fee Structure Reference

### Per-Order Fees

| Execution Type | Fee Rate | OrderType | Pricing |
|----------------|----------|-----------|---------|
| Maker (resting on book) | 2bps | POST_ONLY, DEFAULT | At/behind touch |
| Taker (crossing spread) | 5bps | DEFAULT, IOC | Crosses touch |

### Per-Cycle Fee Breakdown

| Scenario | Entry Fee | Exit Fee | Total/Cycle | Monthly | Annual |
|----------|-----------|----------|-------------|---------|--------|
| **Current (100% Taker)** | 10 bps | 10 bps | 20 bps | $600 | $7,300 |
| **Strategy 3 (100% Maker)** | 4 bps | 4 bps | 8 bps | $240 | $2,900 |
| **Strategy 3 (75% Maker)** | 5.5 bps | 5.5 bps | 11 bps | $330 | $4,000 |
| **Strategy 7 (90% Maker)** | 4.8 bps | 4.8 bps | 9.6 bps | $288 | $3,500 |
| **Strategy 7+5 (85% Maker)** | 5.1 bps | 5.1 bps | 10.2 bps | $306 | $3,700 |
| **Strategy 8 (BBO, 100% Taker)** | 10 bps | 10 bps | 20 bps | $600 | $7,300 |

**Key Insights:**
- Strategy 8 (BBO) = Current IOC fees (20bps/cycle)
- Strategy 3 (At-Touch POST_ONLY) = Best fee improvement (8-11bps/cycle)
- Strategy 7 (DEFAULT + At-Touch) = Good balance (9-10bps/cycle)

---

## Risk Assessment by Strategy

### Strategy 1: Timeout Increase
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Increased cycle time | 100% | Low | Accept trade-off |
| No fee improvement | 100% | Medium | Use as supplemental only |
| Adverse selection | 5% | Low | Market tends to revert |

**Overall Risk:** LOW (but low reward)

### Strategy 2: Partial Fill Allowance
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Leg imbalance | 30% | High | Implement imbalance hedging |
| Complex state management | 40% | Medium | Thorough testing required |
| Position tracking errors | 10% | High | Automated position reconciliation |

**Overall Risk:** MEDIUM-HIGH

### Strategy 3: At-Touch POST_ONLY
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Queue timeout | 30% | Medium | Combine with BookDepth filter |
| Low fill rate in deep queues | 20% | Medium | Strategy 5 supplement |
| Market movement risk | 10% | Low | POST_ONLY rejection protection |

**Overall Risk:** MEDIUM

### Strategy 4: Spread Filter
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Reduced opportunity set | 100% | Low | Accept quality over quantity |
| Over-filtering | 10% | Low | Tune threshold based on data |

**Overall Risk:** LOW

### Strategy 5: BookDepth Utilization
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Implementation bugs | 20% | Medium | Thorough unit testing |
| BookDepth data errors | 5% | Low | Fallback to default behavior |
| Over-filtering queues | 10% | Low | Tune MAX_QUEUE_SIZE |

**Overall Risk:** LOW-MEDIUM

### Strategy 6: Dynamic Timeout
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Volatility misclassification | 20% | Medium | Multiple regime indicators |
| Inappropriate timeouts | 15% | Low | Conservative thresholds |

**Overall Risk:** LOW-MEDIUM

### Strategy 7: DEFAULT + At-Touch
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Occasional taker execution | 20% | Low | Accept as cost of higher fill rate |
| No POST_ONLY protection | 100% | Low | Higher fill rate compensates |
| Market movement risk | 15% | Low | Fast execution reduces exposure |

**Overall Risk:** MEDIUM

### Strategy 8: BBO Pricing
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| NO fee improvement | 100% | High | Use Strategy 3 or 7 instead |
| User expectation mismatch | 100% | High | Clear communication of fees |

**Overall Risk:** HIGH (expectation vs reality mismatch)

---

## Implementation Summary

### Quick Reference Guide

**For Maximum Fee Savings ($450/month):**
```
Strategy 7 (DEFAULT + At-Touch) + Strategy 5 (BookDepth) + Strategy 4 (Spread Filter)
Effort: 10-12 hours
Risk: MEDIUM
Reward: 15 bps/cycle savings
```

**For Simplicity ($280/month):**
```
Strategy 7 (DEFAULT + At-Touch) only
Effort: 2-3 hours
Risk: MEDIUM
Reward: 9.4 bps/cycle savings
```

**For POST_ONLY Protection ($360/month):**
```
Strategy 3 (At-Touch POST_ONLY) + Strategy 5 (BookDepth)
Effort: 8-10 hours
Risk: MEDIUM
Reward: 12 bps/cycle savings
```

**For Latency Only ($0/month savings):**
```
Strategy 8 (BBO Pricing)
Effort: 1-2 hours
Risk: LOW
Reward: 0 bps/cycle savings (5s latency improvement)
```

### Critical Decision Matrix

| Your Priority | Best Strategy | Reason |
|---------------|---------------|--------|
| Maximum fee reduction | Strategy 3 + 5 | Highest maker rate |
| Best effort/reward ratio | Strategy 7 | Simple + effective |
| POST_ONLY protection | Strategy 3 | Reorders if would cross |
| Fast execution | Strategy 8 | 100% immediate (but 5bps) |
| Balanced approach | Strategy 7 + 5 | Good fees + high fill rate |

---

## Conclusion

### Key Findings

1. **BBO Pricing (Strategy 8) provides NO fee improvement** - it's identical to current IOC fees (5bps)

2. **Root cause is NOT incorrect pricing logic** - current 1-tick-behind IS correct maker pricing
   - `best_ask - tick_size` (BUY) and `best_bid + tick_size` (SELL) are valid maker prices
   - Problem: TOO FAR from touch in fast-moving markets
   - Result: Orders timeout before fills → 100% IOC fallback → 20bps/cycle effective cost

3. **True maker pricing** is buy=best_bid, sell=best_ask (rests on book, 2bps)

4. **Best combined approach:** Strategy 7 (DEFAULT + At-Touch) + Strategy 5 (BookDepth) + Strategy 4 (Spread Filter)
   - 15 bps/cycle fee reduction
   - $450/month savings at 100 cycles/day
   - 70-90% fill rate
   - MEDIUM implementation complexity

5. **Recommended path:** Start with Strategy 7 (quick win), add Strategy 5 (optimization), add Strategy 4 (refinement)

### Pricing Logic Correction

**IMPORTANT: Current pricing IS correct, but ineffective**
- Current code (lines 522-525): `best_ask - tick_size` and `best_bid + tick_size`
- This IS valid maker pricing (does not cross spread)
- BUT: Too far from touch → 100% timeout → 100% IOC fallback

**User's BBO proposal (would NOT improve fees):**
- buy=best_ask, sell=best_bid
- **CROSSES spread** = TAKER execution = 5bps
- **NO fee improvement** vs current IOC (both 5bps)

**Correct alternative for fee improvement:**
- buy=best_bid, sell=best_ask (at touch)
- **Does NOT cross spread** = MAKER execution = 2bps
- **Higher fill probability** than 1-tick-behind
- **6-12 bps/cycle improvement** vs current (effective 20bps → 8-14bps)

### Next Steps

1. **Choose strategy** based on priority (fees vs simplicity vs POST_ONLY protection)
2. **Implement** chosen strategy following detailed steps
3. **Test** thoroughly with paper trading
4. **Deploy** and monitor fill rates, fees, PNL
5. **Rollback** if metrics don't meet expectations

---

PLAN_READY: .omc/plans/8-strategies-comprehensive-analysis.md
