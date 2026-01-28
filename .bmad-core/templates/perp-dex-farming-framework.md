<!-- Powered by BMAD™ Core -->

# Perp DEX Point Farming Bot Development Framework

**Version**: v0.1 (Initial - Pre-validation)
**Created**: 2025-11-08
**Status**: DRAFT - To be validated through actual bot development
**Scope**: 20+ Perp DEX point farming bots (trend-following + volume bots)

---

## Framework Purpose

This framework provides a systematic, repeatable process for developing profitable point farming bots across multiple perpetual DEXs. It is designed to evolve through real-world experience.

**Initial Development Context**:
- Based on Lighter DEX experience (10-hour API failure + post-mortem)
- User's initial 9-phase proposal + Claude's inexperienced validation
- **Validation Plan**: Improve framework with each bot deployed (targeting 20+ DEXs)

**Bot Types Covered**:
1. **Trend-Following Bots** (e.g., Lighter): Optimize Sharpe ratio, ignore volume
2. **Volume Bots** (majority): Maximize trading volume via Grid/MM/Delta-Neutral
3. **Hybrid Bots**: Balance profit + volume

---

## Framework Overview (9 Phases)

```
Phase 0: API Feasibility Check (30-60 min) → GO/NO-GO
         ↓ GO
Phase 1: Strategy Research (1-2 weeks) → Strategy candidates
         ↓
Phase 2: Python Backtesting (1-2 weeks) → Top 3-5 strategies
         ↓
Phase 3: PineScript Validation (3-5 days, optional) → Final 1-2 strategies
         ↓
Phase 4: Implementation (3-5 days) → Working bot (paper trading)
         ↓
Phase 5: QA (1-2 days) → Production-ready bot
         ↓
Phase 6: Deployment (1 day) → Live bot ($100→$500→$2K+)
         ↓
Phase 7: Post-Mortem (ongoing) → Performance analysis
         ↓
Phase 8: Strategy Improvement (ongoing) → Evolved strategy v2.0
```

**Total Time**: 3-5 weeks (initial bot), 2-3 weeks (subsequent bots with framework)

---

## Phase 0: API Feasibility Check

**Duration**: 30-60 minutes
**Priority**: 🔴 CRITICAL - Skip this = 10+ hours wasted
**Owner**: Architect
**Validation**: ✅ Proven by Lighter failure case

### Objectives
- Confirm API is publicly accessible
- Verify required endpoints work for your account type
- Detect Private Beta / waitlist blockers **BEFORE** implementation

### Key Questions
1. **Public Access**: Is API in Private Beta? Invite-only? Geographic restrictions?
2. **Functionality**: Can you place orders with your account type?
3. **Community Validation**: Have others built bots successfully?
4. **Test Calls**: Do basic GET/POST requests work?

### Deliverables
- **GO**: Proceed to Phase 1 (all checks passed)
- **CONDITIONAL GO**: Proceed with documented limitations
- **NO-GO**: Stop immediately, try alternative DEX

### Success Criteria
- Authentication successful
- Test order placed (testnet/paper trading)
- No "Private Beta" or "Invite Only" blockers found

### Lighter Case Study
```yaml
What_Happened:
  - Skipped Phase 0 entirely
  - Implemented bot for 5 hours
  - Hit Error 21511: "invalid tx type for account"
  - Root Cause: Private Beta restriction
  - Time Wasted: 10 hours

What_Should_Have_Happened:
  - Phase 0: 30 min API test
  - Discovery: Private Beta blocker
  - Decision: NO-GO (switch to Hyperliquid)
  - Time Saved: 9.5 hours
```

**Reference**: See `architect-checklist-perp-dex-farming.md` Section 0

---

## Phase 1: Strategy Research

**Duration**: 1-2 weeks
**Priority**: 🟡 IMPORTANT
**Owner**: PM + User
**Validation**: ✅ Proven by Lighter (750 combinations tested)

### Objectives
- Understand DEX point mechanism (volume vs position vs TVL)
- Research successful farming strategies
- Generate 10-20 strategy candidates

### Sub-Phases

#### 1.1 Point Mechanism Research (2-3 days)
**Questions**:
- How are points calculated? (volume-based, position-based, TVL-based, hybrid?)
- What is point-to-dollar efficiency? (e.g., $1000 volume = ? points)
- Are there multipliers? (leverage, specific pairs, time-based)
- Is there a rebate program for market makers?

**Methods**:
- Read official docs (tokenomics, point campaigns)
- Discord/Telegram community research
- Twitter analysis (successful farmers)
- Reverse-engineer from leaderboards

**Deliverables**: Point mechanism summary document

#### 1.2 Strategy Brainstorming (3-5 days)
**Trend-Following Strategies** (for Sharpe-focused DEXs):
- Moving Average Crossover (Golden/Death Cross)
- MACD, RSI divergence
- Breakout strategies
- Trailing Stop Loss optimization

**Volume Strategies** (for volume-focused DEXs):
- **Grid Trading**: Buy low, sell high in range
- **Market Making**: Provide liquidity on both sides
- **Delta Neutral**: Long spot + Short perp (funding arbitrage)

**Hybrid Strategies**:
- Combine trend + volume elements

**Deliverables**: 10-20 strategy candidates with descriptions

#### 1.3 Initial Filtering (2-3 days)
**Filter Criteria**:
- Fits DEX point mechanism
- Acceptable risk (liquidation, max drawdown)
- Feasible with API capabilities
- Resource requirements (capital, monitoring)

**Deliverables**: Top 5-10 strategies to backtest

### Success Criteria
- Point mechanism fully understood
- 5-10 backtest-ready strategies identified
- Risk assessment completed

### Lighter Case Study
```yaml
What_Happened:
  - ✅ Comprehensive strategy research
  - Tested 750 combinations (5 coins × 6 timeframes × 5 leverage × 5 SL)
  - Selected: BTC 1h 2x + ETH 30m 1x
  - Sharpe 4.26, +22.6% return, -6.5% MDD

Result: FINAL_STRATEGY_SELECTION.md (successful)
```

**Reference**: See `pm-checklist-perp-dex-farming.md` Section 1

---

## Phase 2: Python Backtesting

**Duration**: 1-2 weeks
**Priority**: 🔴 CRITICAL
**Owner**: PM + Architect
**Validation**: ✅ Proven by Lighter

### Objectives
- Build backtesting framework
- Test all strategy combinations systematically
- Select top 3-5 strategies based on metrics

### Sub-Phases

#### 2.1 Framework Setup (2-3 days)
**Data Collection**:
- 1 year OHLCV data (minimum)
- Source: Exchange API, CryptoDataDownload, ccxt

**Backtesting Engine**:
- Python libraries: `backtrader`, `vectorbt`, or custom
- Slippage modeling (0.02-0.05% typical)
- Fee modeling (maker/taker fees)
- Position sizing logic

**Deliverables**: Working backtesting framework

#### 2.2 Combinatorial Testing (5-7 days)

**For Trend-Following Bots**:
```python
# Example: Lighter-style testing
coins = ['BTC', 'ETH', 'SOL', 'ARB', 'OP']  # 5
timeframes = ['15m', '30m', '1h', '4h', '1d', '1w']  # 6
leverage = [1, 2, 3, 5, 10]  # 5
stop_loss = [0.01, 0.02, 0.03, 0.05, 0.10]  # 5

Total combinations = 5 × 6 × 5 × 5 = 750
```

**Metrics**:
- Sharpe Ratio (primary)
- Max Drawdown
- Win Rate
- Profit Factor
- Total Return

**For Volume Bots**:
```python
# Grid Trading
grid_intervals = [10, 20, 30, 50, 100]  # 5
price_ranges = ['±2%', '±5%', '±10%', '±20%']  # 4
rebalance_freq = ['1h', '4h', '1d']  # 3

Total combinations = 5 × 4 × 3 = 60

# Market Making
spreads = [0.001, 0.002, 0.005, 0.01, 0.02]  # 5
inventory_limits = [0.1, 0.25, 0.5, 1.0]  # 4

Total combinations = 5 × 4 = 20

# Delta Neutral
hedge_ratios = [0.8, 0.9, 1.0, 1.1]  # 4
rebalance_threshold = [0.05, 0.10, 0.15]  # 3

Total combinations = 4 × 3 = 12
```

**Metrics**:
- Total Trading Volume (primary for volume bots)
- Point Efficiency (points per $1000 volume)
- Net P&L (after fees)
- Slippage Cost
- Risk-Adjusted Return

**Deliverables**: Backtesting results spreadsheet/report

#### 2.3 Top Strategy Selection (1-2 days)
**Selection Criteria**:
- Top 20% by primary metric (Sharpe or Volume)
- Robustness across market conditions (Bull/Bear/Sideways)
- Acceptable risk metrics (MDD, volatility)

**Deliverables**: Top 3-5 strategies with detailed reports

### Success Criteria
- All combinations tested
- Top strategies statistically significant
- Results reproducible

### Lighter Case Study
```yaml
What_Happened:
  - ✅ Tested 750 combinations
  - Winner: BTC 1h 2x (Sharpe 4.26)
  - Runner-up: ETH 30m 1x (diversification)
  - Documented in FINAL_STRATEGY_SELECTION.md

Result: Clear winning strategy identified
```

**Reference**: See `pm-checklist-perp-dex-farming.md` Section 2

---

## Phase 3: PineScript Validation (Optional)

**Duration**: 3-5 days
**Priority**: 🟢 RECOMMENDED (trend-following), ⚠️ OPTIONAL (volume bots)
**Owner**: PM
**Validation**: ⚠️ Not tested in Lighter (strategy already confirmed)

### Objectives
- Validate Python results with TradingView long-term data (2+ years)
- Catch edge cases in different market cycles
- Visual confirmation of strategy behavior

### When to Use

**✅ Recommended**:
- Trend-following bots (MA, MACD, RSI)
- Need visual validation
- Long-term data (2+ years) desired

**⚠️ Optional/Skip**:
- Volume bots (Grid, MM, DN) - Python is more accurate
- Strategy already highly confident
- Complex logic hard to port to PineScript

### Sub-Phases

#### 3.1 PineScript Porting (1-2 days)
- Convert Python strategy → PineScript
- Verify indicator calculations match
- Test on 1-week sample data

#### 3.2 Long-Term Backtesting (1-2 days)
- Run on 2+ years data
- Test across Bull (2021), Bear (2022), Sideways (2023) markets
- Compare results to Python

#### 3.3 Final Validation (1 day)
- Python vs PineScript result consistency check
- Identify and fix discrepancies
- Document edge cases

### Deliverables
- PineScript strategy code
- TradingView backtest results
- Consistency validation report

### Success Criteria
- Python ≈ PineScript results (±5% acceptable)
- Strategy works across market cycles
- No critical edge cases found

### Lighter Case Study
```yaml
What_Happened:
  - ❌ Skipped Phase 3
  - Reason: Strategy already confirmed (750 combos)
  - PineScript not needed for this case

Decision: Phase 3 is OPTIONAL when confidence is high
```

**Reference**: See `pm-checklist-perp-dex-farming.md` Section 3

---

## Phase 4: Implementation

**Duration**: 3-5 days
**Priority**: 🔴 CRITICAL
**Owner**: Architect
**Validation**: ⚠️ Partial (Lighter blocked by API)

### Objectives
- Design bot architecture
- Implement core components
- Validate with paper trading

### Sub-Phases

#### 4.1 Architecture Design (1 day)
**Core Components**:
1. **Price Monitor**: Real-time market data (WebSocket)
2. **Strategy Engine**: Signal generation (Golden Cross, Grid logic, etc.)
3. **Order Executor**: Order placement and management
4. **Risk Manager**: Stop loss, position sizing, kill switch

**Data Flow**:
```
WebSocket → Price Monitor → Strategy Engine → Order Executor → DEX API
                                    ↓
                              Risk Manager (validates all orders)
```

**Deliverables**: Architecture diagram, component specifications

#### 4.2 Core Implementation (2-3 days)
**Price Monitor**:
- WebSocket connection with auto-reconnect
- Real-time price updates
- Historical data caching

**Strategy Engine**:
- Indicator calculation (MA, RSI, Grid levels)
- Signal generation (BUY/SELL/HOLD)
- Position state tracking

**Order Executor**:
- Order placement (market, limit)
- Order cancellation
- Position management (close, update SL)

**Risk Manager**:
- Position size limits
- Stop loss enforcement
- Drawdown monitoring
- Emergency kill switch

**Deliverables**: Working bot code

#### 4.3 Paper Trading (1 day)
**Virtual Balance Testing**:
- Start with virtual $10,000
- Run bot for 24-48 hours
- Monitor for bugs, errors

**Validation**:
- Strategy executes correctly
- Risk limits enforced
- No crashes or hangs

**Deliverables**: Paper trading log, bug fixes

### Success Criteria
- Bot runs continuously for 24+ hours
- Strategy signals match backtest logic
- All error scenarios handled gracefully

### Lighter Case Study
```yaml
What_Happened:
  - ⚠️ Implemented BOT_ARCHITECTURE.md
  - ⚠️ Built components (Price Monitor, Executor, etc.)
  - ❌ Blocked by API (Error 21511)
  - Result: Working code, but can't execute orders

Lesson: Phase 0 prevents this scenario
```

**Reference**: See `architect-checklist-perp-dex-farming.md` Section 4

---

## Phase 5: QA (Quality Assurance)

**Duration**: 1-2 days
**Priority**: 🟡 IMPORTANT
**Owner**: Architect
**Validation**: ❌ Not executed in Lighter

### Objectives
- Comprehensive testing before production
- Ensure production-grade reliability
- Document all test results

### Sub-Phases

#### 5.1 Unit Testing (0.5 day)
**Component Tests**:
- Price Monitor: Data accuracy, reconnection logic
- Strategy Engine: Signal correctness, edge cases
- Order Executor: Order formatting, API error handling
- Risk Manager: Limit enforcement, kill switch

**Coverage Target**: 80%+ code coverage

**Deliverables**: Unit test suite (pytest, unittest)

#### 5.2 Integration Testing (0.5 day)
**End-to-End Scenarios**:
- Normal operation: Signal → Order → Position
- WebSocket disconnect/reconnect
- API errors (rate limit, 500 errors)
- Stop loss trigger
- Emergency shutdown

**Deliverables**: Integration test results

#### 5.3 Stress Testing (0.5 day)
**Extreme Scenarios**:
- Rapid price movement (flash crash)
- High volatility (100+ signals/hour)
- API rate limit testing
- Memory leak testing (24h+ run)

**Deliverables**: Stress test report

### Success Criteria
- All tests pass
- No critical bugs found
- Bot stable under stress

### Lighter Case Study
```yaml
What_Happened:
  - ❌ Skipped due to API blocker

Note: Phase 5 would have caught API issues earlier if Phase 0 was done
```

**Reference**: See `architect-checklist-perp-dex-farming.md` Section 5

---

## Phase 6: Deployment

**Duration**: 1 day (initial) + ongoing monitoring
**Priority**: 🔴 CRITICAL
**Owner**: Architect
**Validation**: ❌ Not executed in Lighter

### Objectives
- Safe staged rollout ($100 → $500 → $2K+)
- Production monitoring setup
- Emergency controls ready

### Sub-Phases

#### 6.1 Staged Rollout (1 day setup, 1-2 weeks validation)
**Stage 1**: $100 capital
- Duration: 1-3 days
- Goal: Validate basic operation
- Risk: Minimal ($100 max loss)

**Stage 2**: $500 capital
- Duration: 3-5 days
- Goal: Validate scaling, point efficiency
- Risk: Low ($500 max loss)

**Stage 3**: $2,000+ capital
- Condition: Stage 1+2 successful, no critical bugs
- Goal: Full-scale farming
- Risk: Managed by stop loss

**Deliverables**: Staged deployment plan

#### 6.2 Monitoring Setup (0.5 day)
**Logging**:
- All trades logged to file
- Hourly performance summary
- Error logs with stack traces

**Alerts**:
- Discord/Telegram notifications
- Error alerts (API failures, crashes)
- Liquidation risk warnings
- Daily P&L summary

**Dashboard** (optional):
- Real-time position display
- Point accumulation tracking
- Strategy performance metrics

**Deliverables**: Monitoring system

#### 6.3 Kill Switch (0.5 day)
**Manual Override**:
- Emergency stop button
- Close all positions
- Prevent new orders

**Automatic Triggers**:
- Max drawdown exceeded (e.g., -15%)
- API errors sustained (>10 failures)
- Liquidation risk > threshold

**Deliverables**: Kill switch mechanism

### Success Criteria
- Bot runs 24/7 without intervention
- Monitoring alerts working
- Kill switch tested and functional

### Lighter Case Study
```yaml
What_Happened:
  - ❌ Never reached deployment (API blocker)

Planned_Approach:
  - $100 → $2,000 staged rollout
  - Logging to logs/bot.log
  - Risk Manager as kill switch
```

**Reference**: See `architect-checklist-perp-dex-farming.md` Section 6

---

## Phase 7: Post-Mortem (Ongoing)

**Duration**: Daily reviews (15-30 min/day)
**Priority**: 🟡 IMPORTANT
**Owner**: PM + User
**Validation**: ✅ Proven by Lighter (POST_MORTEM_ANALYSIS.md)

### Objectives
- Track actual vs expected performance
- Identify issues early
- Document learnings

### Daily Activities

#### 7.1 Performance Review (15 min/day)
**Metrics Tracking**:
- Points earned vs target
- P&L (profit & loss)
- Trading volume
- Strategy execution accuracy (signals vs orders)

**Comparison**:
- Backtest results vs live results
- Expected point rate vs actual

**Deliverables**: Daily performance log

#### 7.2 Issue Tracking (as needed)
**Bug Logging**:
- WebSocket disconnections
- API errors
- Strategy anomalies (unexpected trades)

**Root Cause Analysis**:
- Why did error occur?
- How to prevent recurrence?

**Deliverables**: Issue tracker (GitHub, Notion, etc.)

#### 7.3 Learning Documentation (weekly)
**Success Patterns**:
- What worked better than expected?
- Which strategies outperformed?

**Failure Patterns**:
- What underperformed?
- Unexpected edge cases?

**Improvement Ideas**:
- Parameter tuning opportunities
- New strategy variants

**Deliverables**: Weekly learnings document

### Success Criteria
- Performance tracked systematically
- Issues documented and resolved
- Continuous improvement mindset

### Lighter Case Study
```yaml
What_Happened:
  - ✅ Comprehensive post-mortem created
  - Analyzed 10-hour failure in detail
  - Documented: POST_MORTEM_ANALYSIS.md
  - Key finding: Skipping Phase 0 cost 10 hours

Result: This framework was born from post-mortem
```

**Reference**: See `pm-checklist-perp-dex-farming.md` Section 7

---

## Phase 8: Strategy Improvement (Ongoing)

**Duration**: Weekly/monthly iterations
**Priority**: 🟢 RECOMMENDED
**Owner**: PM + User
**Validation**: ❌ Not executed in Lighter (blocked)

### Objectives
- Bridge backtest-to-live gap
- Optimize based on real data
- Evolve strategy to v2.0+

### Activities

#### 8.1 Real Data Analysis (weekly)
**Backtest vs Live Gap Analysis**:
- Slippage: Expected 0.02% → Actual ?%
- Fees: Maker/Taker rates vs reality
- Execution delay: Signal → Order fill time

**Adjustments**:
- Update backtest assumptions
- Re-test with realistic parameters

**Deliverables**: Gap analysis report

#### 8.2 Parameter Tuning (monthly)
**Optimization Targets**:
- Trend-Following: Leverage, Stop Loss, Timeframe
- Volume Bots: Grid intervals, Spread, Rebalance frequency

**Method**:
- Re-run Phase 2 with updated constraints
- A/B test: Old params vs new params (50/50 capital split)

**Deliverables**: Updated strategy parameters

#### 8.3 A/B Testing (as needed)
**New Strategy Variants**:
- Test with 10-20% of capital
- Run parallel to main strategy
- Compare performance over 1-2 weeks

**Decision**:
- Better → Full migration
- Worse → Discard
- Unclear → Extend test period

**Deliverables**: A/B test results

### Success Criteria
- Strategy improves over time
- Point efficiency increases
- Risk metrics remain acceptable

### Lighter Case Study
```yaml
What_Happened:
  - ❌ Never reached Phase 8 (API blocker)

Planned_Approach:
  - Weekly performance review
  - Monthly parameter re-optimization
  - Quarterly major strategy upgrades
```

**Reference**: See `pm-checklist-perp-dex-farming.md` Section 8

---

## Communication Protocol Selection Guide

**Purpose**: Choose optimal REST vs WebSocket protocol based on bot type and strategy requirements.

**Decision Timing**: Phase 0 (API Feasibility Check) - Decided early to inform architecture design.

### Protocol Decision Matrix

| Bot Type | Strategy | Update Freq | **Primary Protocol** | Secondary | Latency | Rationale |
|----------|----------|-------------|---------------------|-----------|---------|-----------|
| **Trend-Following** | MA Crossover | Real-time | ✅ **WebSocket** | REST fallback | <100ms | Golden/Death Cross needs instant price updates |
| **Trend-Following** | MACD, RSI | Real-time | ✅ **WebSocket** | REST fallback | <100ms | Divergence detection requires continuous monitoring |
| **Volume** | Grid Trading | 15m-1h | ✅ **REST** | WS optional | <5s | Periodic rebalancing sufficient (polling every 15-60min) |
| **Volume** | Market Making | Real-time | ✅ **WebSocket** + REST | N/A | <100ms | WS for order book depth, REST for order placement |
| **Volume** | Delta Neutral | 15m-1h | ✅ **REST** | WS optional | <5s | Periodic hedge ratio check (every 15min-1h) |
| **Hybrid** | Trend + Volume | Variable | ✅ **Hybrid** (WS+REST) | N/A | <500ms | Both real-time data and periodic operations needed |

### Protocol Specifications

#### WebSocket (Real-time Strategies)

**Best For**:
- Trend-Following bots (MA Crossover, MACD, RSI)
- Market Making bots (order book depth monitoring)
- Any strategy requiring <5 minute update frequency

**Requirements**:
- Stable WebSocket connection (>95% uptime validated in Phase 0)
- Auto-reconnect logic with exponential backoff (3s → 6s → 12s → 24s → 60s)
- Message rate limit acceptable (check Phase 0.5)
- State management (track connection status, buffer during reconnect)

**Data Types**:
```python
# Futures WebSocket Streams
futures_price = "futures/ticker@{symbol}"  # Real-time price
futures_candles = "futures/kline@{symbol}_{timeframe}"  # OHLCV
futures_orderbook = "futures/depth@{symbol}"  # Order book (for MM)
futures_account = "futures/account"  # Position updates, order fills
```

**Architecture Components**:
- WebSocket Manager (connection, subscriptions, reconnect)
- Message Queue (buffer messages during disconnection)
- Heartbeat/Ping (keep-alive, detect dead connections)
- State Recovery (resubscribe on reconnect, catch up missed data)

**Pros**:
- ✅ Real-time updates (<100ms latency)
- ✅ Push-based (no polling overhead)
- ✅ Efficient (single connection for multiple streams)
- ✅ Account updates included (order fills, position changes)

**Cons**:
- ❌ Complex reconnect logic
- ❌ State management overhead
- ❌ Debugging harder (asynchronous events)
- ❌ Potential data loss during disconnection

**Example Use Case** (Trend-Following):
```
WebSocket: BTC-PERP 1h candles stream
    ↓
Strategy Engine: Calculate MA(50), MA(200) on each candle close
    ↓
Signal: Golden Cross detected → BUY signal
    ↓
Order Executor: Place market buy order via REST
```

---

#### REST (Periodic Strategies)

**Best For**:
- Grid Trading bots (periodic rebalancing every 15min-1h)
- Delta Neutral bots (periodic hedge ratio check)
- Any strategy with >15 minute update frequency

**Requirements**:
- Acceptable rate limits (>10 requests/min, validated in Phase 0.5)
- Reasonable latency (<500ms per request)
- Polling interval respects rate limits

**Endpoints Used**:
```python
# Futures REST Endpoints
GET /futures/candles?symbol=BTC-PERP&interval=1h&limit=200
GET /futures/ticker?symbol=BTC-PERP
GET /futures/positions
GET /futures/balance
POST /futures/orders
DELETE /futures/orders/{orderId}
```

**Architecture Components**:
- Polling Scheduler (asyncio timer, cron, or while loop with sleep)
- Request Queue (rate limit management, FIFO)
- Response Cache (cache OHLCV for 1-5min to reduce calls)
- Retry Logic (exponential backoff for 429/500 errors)

**Pros**:
- ✅ Simple implementation (stateless)
- ✅ Reliable (no connection drops)
- ✅ Easy debugging (synchronous, request/response)
- ✅ No state management needed

**Cons**:
- ❌ Polling overhead (unnecessary API calls)
- ❌ Not real-time (latency 500ms-5s)
- ❌ Higher rate limit usage
- ❌ May miss rapid price movements

**Example Use Case** (Grid Trading):
```python
# Every 15 minutes
while True:
    # 1. Get current price (REST)
    price = api.get_ticker("BTC-PERP")["lastPrice"]

    # 2. Calculate grid levels
    grid_levels = strategy.calculate_grid(price, range=10%, levels=50)

    # 3. Rebalance orders (REST - batch if available)
    api.cancel_all_orders()
    api.create_batch_orders(grid_levels)  # 50 orders in 1 request

    # 4. Sleep 15 minutes
    time.sleep(900)
```

---

#### Hybrid (Advanced - Market Making)

**Best For**:
- Market Making strategies (need both order book depth AND order placement)
- Advanced strategies combining real-time data with periodic control

**Pattern**:
- **WebSocket**: Real-time order book depth, price updates (data layer)
- **REST**: Order placement, cancellation, position queries (control layer)
- **Rationale**: WebSocket for continuous data, REST for occasional actions

**Architecture**:
```
WebSocket Stream (order book depth, 100ms updates)
     ↓
Strategy Engine: Calculate optimal bid/ask spread
     ↓
Decision: Spread changed >threshold?
     ↓ (if yes)
REST API: Cancel old orders + Place new orders
```

**Pros**:
- ✅ Best of both worlds (real-time data + reliable control)
- ✅ Optimal performance for MM strategies
- ✅ Reduce rate limit usage (WS for data, REST only for orders)

**Cons**:
- ❌ Most complex implementation
- ❌ Requires both WS and REST infrastructure
- ❌ Coordination layer needed (sync WS data with REST actions)
- ❌ Higher development/maintenance cost

**Example Use Case** (Market Making):
```python
# WebSocket handler
async def on_orderbook_update(orderbook):
    best_bid = orderbook["bids"][0]["price"]
    best_ask = orderbook["asks"][0]["price"]

    # Calculate optimal spread
    optimal_bid, optimal_ask = strategy.calculate_spread(best_bid, best_ask)

    # If spread changed significantly, update orders (REST)
    if abs(optimal_bid - current_bid) > threshold:
        await rest_api.cancel_orders()
        await rest_api.create_orders([
            {"side": "buy", "price": optimal_bid, ...},
            {"side": "sell", "price": optimal_ask, ...}
        ])
```

---

### Decision Flow Chart

```
Start: Identify bot type and strategy from PM's Phase 2 selection
  ↓
Bot Type?
├─ Trend-Following? → Update Freq: Real-time → Protocol: WebSocket
├─ Grid Trading? → Update Freq: 15min-1h → Protocol: REST
├─ Market Making? → Need: Order book depth → Protocol: WebSocket + REST
├─ Delta Neutral? → Update Freq: 15min-1h → Protocol: REST
└─ Hybrid? → Combination → Protocol: Hybrid

  ↓
Validate in Phase 0:
├─ WebSocket stable? (12h uptime test)
├─ REST rate limits OK? (>10 req/min)
└─ Endpoints available?

  ↓
Final Decision: [WebSocket / REST / Hybrid]
  ↓
Document in Phase 0 Report (Section 0.6)
  ↓
Pass to Phase 4 Implementation
```

### Protocol Selection Checklist (Phase 0.6)

Use this in `architect-checklist-perp-dex-farming.md` Section 0.6:

- [ ] **Identify Bot Type**: [From PM's strategy selection]
- [ ] **Determine Update Frequency**: [Real-time / 1-5min / 15min-1h / >1h]
- [ ] **Consult Decision Matrix**: [Use table above]
- [ ] **Validate Availability**: [WebSocket stable? REST rate limits OK?]
- [ ] **Select Protocol**: [WebSocket / REST / Hybrid]
- [ ] **Document Rationale**: [Brief explanation for choice]
- [ ] **Identify Components**: [List architecture components needed for Phase 4]

---

## Bot Type Variations

### Type A: Trend-Following Bots

**Characteristics**:
- **Goal**: Maximize Sharpe ratio, ignore volume
- **DEX Examples**: Lighter (trend-based points)
- **Strategies**: MA Crossover, MACD, Breakout
- **Capital**: $2,000 - $10,000

**Phase Differences**:
```yaml
Phase_1_Research:
  - Focus on Sharpe ratio optimization
  - Historical trend persistence analysis

Phase_2_Backtesting:
  Primary_Metrics:
    - Sharpe Ratio (primary)
    - Max Drawdown
    - Win Rate
    - Profit Factor

  Combinatorial_Testing:
    - Coins: 3-5
    - Timeframes: 6 (15m to 1w)
    - Leverage: 5 (1x to 10x)
    - Stop Loss: 5 (1% to 10%)
    Total: ~750 combinations

Phase_3_PineScript:
  - ✅ RECOMMENDED (long-term validation crucial)

Phase_8_Improvement:
  - Focus on signal accuracy
  - Stop loss optimization
  - Timeframe adaptation
```

**Success Metrics**:
- Sharpe Ratio > 3.0
- Max Drawdown < 10%
- Win Rate > 50%
- Consistent monthly returns

**Lighter Case Study**:
- Winner: BTC 1h 2x (Sharpe 4.26, +22.6%, MDD -6.5%)
- Runner-up: ETH 30m 1x (diversification)

---

### Type B: Volume Bots

**Characteristics**:
- **Goal**: Maximize trading volume → Point farming
- **DEX Examples**: Most DEXs (volume-based points)
- **Strategies**: Grid Trading, Market Making, Delta Neutral
- **Capital**: $5,000 - $50,000 (higher capital = more volume)

**Phase Differences**:
```yaml
Phase_1_Research:
  Critical_Questions:
    - Point calculation: Points per $1000 volume?
    - Rebate program: Maker fee rebates?
    - Volume multipliers: Leverage, specific pairs?

  Strategy_Focus:
    - Grid Trading: Range-bound markets
    - Market Making: Provide liquidity
    - Delta Neutral: Funding rate arbitrage

Phase_2_Backtesting:
  Primary_Metrics:
    - Total Trading Volume (primary)
    - Point Efficiency (points per $1000 volume)
    - Net P&L after fees
    - Slippage Cost
    - Inventory Risk (for MM)

  Grid_Trading_Testing:
    - Grid Intervals: 5 (10 to 100 levels)
    - Price Ranges: 4 (±2% to ±20%)
    - Rebalance Freq: 3 (1h, 4h, 1d)
    Total: 60 combinations

  Market_Making_Testing:
    - Spreads: 5 (0.1% to 2%)
    - Inventory Limits: 4 (10% to 100%)
    Total: 20 combinations

  Delta_Neutral_Testing:
    - Hedge Ratios: 4 (0.8 to 1.1)
    - Rebalance Threshold: 3 (5%, 10%, 15%)
    Total: 12 combinations

Phase_3_PineScript:
  - ⚠️ OPTIONAL (Python more accurate for complex volume strategies)
  - Grid Trading: Maybe
  - Market Making: No (order book dynamics not in PineScript)
  - Delta Neutral: Maybe (funding rates need real API data)

Phase_8_Improvement:
  - Focus on volume efficiency (more volume, less capital)
  - Slippage reduction
  - Fee optimization (maker rebates)
  - Inventory management
```

**Success Metrics**:
- Daily Volume: $50K - $500K+ (depending on capital)
- Point Efficiency: >X points per $1000 volume (DEX-specific)
- Net P&L: Break-even or slightly positive (after fees)
- Low Slippage: <0.05% average

**Strategy-Specific Considerations**:

#### Grid Trading
- Works best in range-bound (sideways) markets
- Risk: Trend breakout (one-sided inventory)
- Mitigation: Stop loss, trend filter

#### Market Making
- Requires fast execution, low latency
- Risk: Inventory imbalance, adverse selection
- Mitigation: Inventory limits, spread widening

#### Delta Neutral
- Profits from funding rate arbitrage
- Risk: Rebalancing costs, basis risk
- Mitigation: Optimal rebalancing threshold

---

### Type C: Hybrid Bots

**Characteristics**:
- **Goal**: Balance profit (Sharpe) + volume (points)
- **DEX Examples**: DEXs with mixed point incentives
- **Strategies**: Trend-following + Volume generation
- **Capital**: $5,000 - $20,000

**Phase Differences**:
```yaml
Phase_1_Research:
  - Analyze point mechanism weighting (trend vs volume)
  - Design hybrid scoring function

Phase_2_Backtesting:
  Multi_Objective_Optimization:
    Primary_Metrics:
      - Combined Score = α × Sharpe + β × Volume
      - Where α + β = 1 (user-defined weights)

    Secondary_Metrics:
      - Sharpe Ratio
      - Trading Volume
      - Point Efficiency
      - Max Drawdown

Phase_3_PineScript:
  - ✅ RECOMMENDED (trend component needs validation)

Phase_8_Improvement:
  - Adjust α/β weights based on point accrual
  - Balance risk vs volume
```

**Success Metrics**:
- Combined score optimization (user-defined)
- Acceptable Sharpe (e.g., >1.5)
- Sufficient volume (e.g., $10K+ daily)

---

## Framework Evolution Plan

**v0.1** (Current - Pre-validation):
- Based on Lighter experience + theoretical analysis
- All 9 phases defined
- Bot type variations outlined

**v1.0** (After 1st bot deployment):
- Validate/refine with actual deployment (Lighter or Hyperliquid)
- Add real-world timings, effort estimates
- Document unexpected issues

**v1.1** (After 2-3 bots):
- Separate trend-following vs volume bot templates
- DEX-specific checklists (e.g., Hyperliquid, dYdX)
- Common pitfall catalog

**v2.0** (After 5-10 bots):
- Mature framework with proven patterns
- Automated tooling (scripts, templates)
- Best practices database

**v3.0** (After 20+ bots):
- Comprehensive DEX knowledge base
- Strategy library (pre-tested configurations)
- Advanced optimization techniques

---

## Success Metrics (Framework Level)

**Development Efficiency**:
- Time to first bot: 3-5 weeks (v0.1) → 2-3 weeks (v1.0) → 1-2 weeks (v2.0)
- Failure rate: <10% (with Phase 0 validation)
- Code reuse: >60% across bots

**Bot Performance**:
- Trend-Following: Sharpe >3.0, MDD <10%
- Volume Bots: Daily volume targets met, positive/neutral P&L
- Point Efficiency: Top 20% of farmers on each DEX

**Framework Quality**:
- Each phase validated by real deployment
- Continuous improvement based on experience
- Documentation accuracy >90%

---

## Appendix: Quick Reference

### When to Use Each Phase

| Phase | Always | Conditional | Skip |
|-------|--------|-------------|------|
| 0: API Check | ✅ | Never | Never (learned the hard way) |
| 1: Research | ✅ | Never | Never |
| 2: Backtesting | ✅ | Never | Never |
| 3: PineScript | Trend-following | Volume bots | High confidence |
| 4: Implementation | ✅ | Never | Never |
| 5: QA | ✅ | Small capital (<$500) | Never in production |
| 6: Deployment | ✅ | Never | Never |
| 7: Post-Mortem | ✅ | Never | Never |
| 8: Improvement | ✅ | Never | Deprecated bots |

### Phase Dependencies

```
Phase 0 (GO) → Phase 1 → Phase 2 → Phase 3* → Phase 4 → Phase 5 → Phase 6 → Phase 7 & 8
                                      ↓ (optional)
                                  Can skip to Phase 4

* Phase 3 optional based on bot type and confidence
```

### Estimated Total Timeline

**First Bot** (learning curve):
- Weeks 1-2: Phase 0-1 (API + Research)
- Weeks 2-3: Phase 2 (Backtesting)
- Week 4: Phase 3* (PineScript, optional)
- Week 4-5: Phase 4-5 (Implementation + QA)
- Week 5: Phase 6 (Deployment)
- Ongoing: Phase 7-8 (Monitoring + Improvement)

Total: **4-5 weeks to live bot**

**Subsequent Bots** (with framework):
- Week 1: Phase 0-1 (faster with templates)
- Week 2: Phase 2 (reuse backtesting code)
- Week 2-3: Phase 3*-4 (reuse architecture)
- Week 3: Phase 5-6 (streamlined QA)
- Ongoing: Phase 7-8

Total: **2-3 weeks to live bot**

---

## Framework Metadata

**Version**: v0.1
**Status**: DRAFT - Awaiting first deployment validation
**Authors**: User (9-phase proposal) + Claude (validation & documentation)
**Date**: 2025-11-08
**Validation Plan**: Improve with each of 20+ DEX bot deployments
**License**: Internal use (User's proprietary framework)

**Related Documents**:
- `POST_MORTEM_ANALYSIS.md` - Lighter failure analysis (source of Phase 0)
- `PERP_DEX_INTEGRATION_CHECKLIST.md` - Original API integration checklist
- `pm-checklist-perp-dex-farming.md` - PM Agent checklist
- `architect-checklist-perp-dex-farming.md` - Architect Agent checklist

**Feedback Loop**:
- After each bot deployment, update this framework
- Document deviations, unexpected issues
- Share learnings across all DEX projects

---

**END OF FRAMEWORK v0.1**
