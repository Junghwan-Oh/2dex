# 9-Stage DEX Integration Framework

**Version**: v1.0 (Extracted from Apex/Lighter experience)
**Purpose**: Systematic process for integrating any Perp DEX trading bot
**Status**: Proven framework with 2 DEX integrations (Lighter, Apex)

---

## 📋 Framework Overview

This framework provides a battle-tested process for integrating trading bots with Perpetual DEX platforms. It has been validated through:
- **Lighter**: Initial framework development (learned Phase 0 importance)
- **Apex**: Framework refinement (saved 13 hours + 3 weeks)

**Key Principle**: API connection first, strategy second

---

## 📊 Phase Progression

```
✅ Phase 0: API Connection Test (CRITICAL - Never skip)
   ↓
⏸️ Phase 1: Strategy Research (Can reuse across DEXs)
   ↓
⏸️ Phase 2: Python Backtesting (Can reuse across DEXs)
   ↓
⏸️ Phase 3: PineScript Validation (OPTIONAL if high confidence)
   ↓
🔄 Phase 4: Implementation (DEX-specific)
   ↓
⏸️ Phase 5: QA Testing
   ↓
⏸️ Phase 6: Deployment (Staged rollout)
   ↓
⏸️ Phase 7: Post-Mortem (Daily/weekly reviews)
   ↓
⏸️ Phase 8: Strategy Improvement (Ongoing optimization)
```

---

## Phase 0: API Connection Test

**Status**: ✅ MANDATORY - Never skip
**Duration**: 2-4 hours (saves 10+ hours later)
**Owner**: Architect
**Critical Principle**: Test API connection BEFORE building strategy

### ✅ Checklist

#### 1. Environment Setup
- [ ] Create `.env` file with API credentials
  - API Key/Secret (or Private Key)
  - Account/Wallet address
  - Testnet/Mainnet selection
- [ ] Verify environment variables load correctly
- [ ] Test basic SDK initialization

#### 2. Public API Tests
- [ ] Fetch ticker data (BTC, ETH prices)
- [ ] Fetch K-line/candle data (OHLCV)
  - Test all needed timeframes: 1m, 3m, 5m, 15m, 30m, 1h
- [ ] Fetch order book (depth data)
- [ ] Verify data quality (no gaps, correct timestamps)

#### 3. Private API Tests
- [ ] Authenticate successfully
- [ ] Fetch account balance
- [ ] Fetch positions (if any exist)
- [ ] Fetch order history
- [ ] Verify symbol configurations
  - Tick size (price precision)
  - Step size (quantity precision)
  - Minimum order size

#### 4. WebSocket vs REST Decision
- [ ] **WebSocket Testing**:
  - Test ticker stream
  - Test depth/orderbook stream
  - Test klines/candle stream
  - Test private streams (orders, positions)
  - Document channel formats that work/fail

- [ ] **REST Fallback**:
  - If WebSocket fails, validate REST polling
  - Test polling frequency (1Hz, 2Hz, etc.)
  - Verify data freshness acceptable for strategy

- [ ] **Make Decision**:
  - WebSocket (if reliable): Lower latency, real-time
  - REST polling (if WebSocket broken): Stable, proven
  - Hybrid: WebSocket + REST fallback

#### 5. Symbol Format Validation
- [ ] Identify REST API symbol format
  - Example: `BTC-USDT`, `BTC/USDT`, `BTCUSDT`
- [ ] Identify WebSocket symbol format (may differ!)
  - Example: WebSocket may use `BTCUSDT` (no hyphen)
- [ ] Create conversion logic if formats differ

#### 6. Order Execution Tests (Paper Trading)
- [ ] Test MARKET order (BUY)
  - Verify order accepted
  - Check position created
  - Validate tick/step size rounding
- [ ] Test LIMIT order (SELL)
  - Verify order placed
  - Check order status
- [ ] Test order cancellation
- [ ] Test position closing
- [ ] Document any SDK bugs/workarounds

#### 7. Rate Limit Verification
- [ ] Identify REST API rate limits
  - Public API: requests/second
  - Private API: requests/second
- [ ] Identify WebSocket limits
  - Max connections
  - Max subscriptions per connection
- [ ] Plan request throttling strategy

### 📋 Deliverables

1. **GO/NO-GO Decision**: Can this DEX support the strategy?
2. **API Connection Guide**: Document all findings
3. **Test Scripts**: Save all connection tests for future reference
4. **Technical Decisions**:
   - WebSocket vs REST choice
   - Symbol format conversions
   - Order execution patterns
   - SDK bugs/workarounds

### 🎯 Success Criteria

- ✅ Public API returns valid market data
- ✅ Private API authenticates and returns account info
- ✅ At least one data source works (WebSocket OR REST)
- ✅ Test order executed successfully (even if tiny $10-30 order)
- ✅ All findings documented for implementation phase

### ⚠️ Failure Cases

**If Phase 0 fails, STOP immediately**:
- Cannot authenticate → Check API keys, permissions
- Cannot fetch market data → DEX API may be unstable
- Cannot execute orders → SDK incompatibility or API issues
- Rate limits too restrictive → Strategy may not be viable

**Time Saved**: 10+ hours by not building strategy on broken API

---

## Phase 1: Strategy Research

**Status**: Can reuse across DEXs (exchange-agnostic)
**Duration**: 1-3 weeks (first DEX), 0 hours (reusing)
**Owner**: PM + User

### ✅ Checklist

#### 1. Strategy Selection
- [ ] Define strategy type:
  - MA Crossover (EMA, SMA)
  - Momentum (RSI, MACD)
  - Mean Reversion (Bollinger Bands)
  - Grid Trading
  - Market Making
  - Delta Neutral
- [ ] Select indicators and parameters
- [ ] Define entry/exit rules

#### 2. Parameter Space Definition
- [ ] **Coins**: BTC, ETH, SOL, ARB, etc.
- [ ] **Timeframes**: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d
- [ ] **Leverage**: 1x, 2x, 3x, 5x, 10x
- [ ] **Stop Loss**: Fixed (2%, 3%, 5%) or Trailing
- [ ] **Position Sizing**: Fixed, percentage-based, Kelly Criterion

#### 3. TradingView Testing (Fast Iteration)
- [ ] Create PineScript strategy
- [ ] Test on TradingView (free, fast feedback)
- [ ] Narrow down parameter combinations
  - Initial: 100-1000 combinations
  - After filtering: 10-20 promising combinations
- [ ] Document top 5-10 strategies

### 📋 Deliverables

1. **Strategy List**: Top 5-10 parameter combinations
2. **Preliminary Metrics**: Win rate, profit factor, max drawdown
3. **Parameter Ranges**: Narrowed down from broad search
4. **Reusability**: Strategy logic is exchange-agnostic

### 🔄 Reusability Across DEXs

**Same Strategy Can Be Reused If**:
- OHLCV data source is standard (Binance, CoinGecko)
- Indicators are universal (EMA, RSI, MACD)
- Entry/exit logic doesn't depend on DEX-specific features

**DEX-Specific Adjustments**:
- Symbol format (BTC-USDT vs BTCUSDT)
- Fee structure (maker/taker fees differ)
- Slippage characteristics (liquidity varies)

---

## Phase 2: Python Backtesting

**Status**: Can reuse across DEXs (same data source)
**Duration**: 1-2 weeks (first DEX), 0 hours (reusing)
**Owner**: PM + Architect

### ✅ Checklist

#### 1. Backtest Engine Setup
- [ ] Create data fetcher (Binance Public API or other free source)
- [ ] Build candle aggregator (OHLCV processing)
- [ ] Implement indicator calculations (EMA, RSI, etc.)
- [ ] Create position tracker (LONG/SHORT/FLAT)
- [ ] Implement stop loss logic (trailing, fixed)

#### 2. Strategy Implementation
- [ ] Port TradingView strategy to Python
- [ ] Verify indicator calculations match TradingView
- [ ] Test on same historical data as TradingView
- [ ] Confirm results match (within 5% tolerance)

#### 3. Performance Metrics
- [ ] Calculate comprehensive metrics:
  - **Returns**: Total return, annualized return
  - **Risk**: Sharpe ratio, Sortino ratio, Calmar ratio
  - **Drawdown**: Max drawdown, drawdown duration
  - **Win Rate**: Winning trades / total trades
  - **Profit Factor**: Gross profit / gross loss
- [ ] Compare against buy-and-hold benchmark

#### 4. Parameter Optimization
- [ ] Test top 10-20 combinations from Phase 1
- [ ] Run backtest on 3-6 month historical data
- [ ] Select top 2-3 strategies by Sharpe ratio
- [ ] Validate on out-of-sample period (walk-forward)

### 📋 Deliverables

1. **Backtest Engine**: Professional-grade Python framework
2. **Performance Report**: Metrics for top strategies
3. **Final Strategy Selection**: Top 2-3 strategies to deploy
4. **Reusability**: Framework works for any DEX (same OHLCV data)

### 🔄 Reusability Across DEXs

**Same Backtest Results Valid If**:
- Data source unchanged (Binance Public API)
- Strategy logic unchanged (EMA crossover, etc.)
- Fee structure similar (< 0.1% difference)

**DEX-Specific Adjustments**:
- Adjust fees in backtest (0.02% vs 0.05%)
- Adjust slippage model (high liquidity vs low)
- Re-run backtest with DEX-specific parameters

---

## Phase 3: PineScript Validation (OPTIONAL)

**Status**: ⏸️ OPTIONAL - Skip if high confidence
**Duration**: 1-3 days (if needed)
**Owner**: PM

### When to Skip

**Skip Phase 3 if**:
- ✅ Tested 100+ combinations in Phase 1
- ✅ Professional backtest in Phase 2
- ✅ Sharpe ratio > 3.0 consistently
- ✅ Simple, well-understood strategy (MA crossover, etc.)
- ✅ Reusing strategy from another DEX

**Complete Phase 3 if**:
- ❌ New, untested strategy
- ❌ Backtest Sharpe < 2.0 (need validation)
- ❌ Complex strategy (multiple indicators, conditions)
- ❌ First time deploying this type of strategy

### ✅ Checklist (If Needed)

- [ ] Port Python backtest to PineScript
- [ ] Run on TradingView with same historical period
- [ ] Compare Python vs PineScript results
- [ ] Verify results match within 5% tolerance
- [ ] Get visual confirmation of entry/exit points

---

## Phase 4: Implementation

**Status**: DEX-specific (cannot reuse code directly)
**Duration**: 2-3 hours (porting from previous DEX)
**Owner**: Architect

### ✅ Checklist

#### 1. Port Previous DEX Code
- [ ] **Price Monitor**:
  - Port REST polling or WebSocket monitor
  - Update symbol format (BTC-USDT vs BTCUSDT)
  - Update API endpoints (DEX-specific)
  - Implement candle aggregation
  - Calculate indicators (EMA, RSI, etc.)

- [ ] **Strategy Bot**:
  - Port position tracking logic (LONG/SHORT/FLAT)
  - Port entry/exit signal detection
  - Port trailing stop loss logic
  - Update for DEX-specific nuances

- [ ] **Order Executor**:
  - Port order creation logic
  - Update API methods (order_v1 vs create_order_v3)
  - Implement tick/step size rounding
  - Handle DEX-specific SDK bugs/workarounds

- [ ] **Main Orchestrator**:
  - Port multi-threaded bot management
  - Update configuration (BTC 1h 2x, ETH 30m 1x)
  - Implement state persistence (JSON)
  - Add monitoring and logging

#### 2. Bot Configuration
- [ ] Create bot configs based on Phase 2 results
  - Example: BTC_1h_2x (1h timeframe, 2x leverage)
  - Example: ETH_30m_1x (30m timeframe, 1x leverage)
- [ ] Set capital allocation per bot
- [ ] Configure risk limits (max position, max loss)
- [ ] Set up paper trading mode

#### 3. Integration with Phase 0 Findings
- [ ] Use WebSocket or REST based on Phase 0 decision
- [ ] Apply symbol format conversions discovered
- [ ] Implement SDK bug workarounds documented
- [ ] Follow rate limit strategy defined

### 📋 Deliverables

1. **Working Bot Code**: All components ported and integrated
2. **Configuration Files**: Bot configs, risk limits, capital allocation
3. **Test Scripts**: Quick validation scripts for each component

### 🔄 Porting Efficiency

**Time Saved by Reusing**:
- First DEX: 1-2 weeks (build from scratch)
- Second DEX: 2-3 hours (port and adjust)
- Third+ DEX: 1-2 hours (port and adjust)

**What Changes Per DEX**:
- Symbol formats
- API method names
- SDK-specific quirks
- Tick/step sizes

**What Stays the Same**:
- Strategy logic (EMA crossover, etc.)
- Position tracking (LONG/SHORT/FLAT)
- Stop loss logic (trailing stop)
- Multi-threading architecture

---

## Phase 5: QA Testing

**Status**: Required for every DEX
**Duration**: 1-2 days
**Owner**: Architect

### ✅ Checklist

#### 1. Unit Testing (Target: 80% coverage)
- [ ] **Price Monitor Tests**:
  - REST polling accuracy
  - WebSocket message handling (if used)
  - Candle aggregation correctness
  - Indicator calculation (EMA, RSI)

- [ ] **Strategy Bot Tests**:
  - Signal detection (Golden Cross, Death Cross)
  - Position tracking (LONG → FLAT → SHORT)
  - Trailing stop updates
  - Entry/exit logic correctness

- [ ] **Executor Tests**:
  - Order creation with correct parameters
  - Tick/step size rounding
  - SDK bug workarounds
  - Error handling (API failures)

- [ ] **Risk Manager Tests**:
  - Position limits enforced
  - Max loss kill switch
  - Emergency shutdown

#### 2. Integration Testing
- [ ] **Normal Operation**:
  - Signal detection → Order placement → Position tracking
  - Multiple bots running simultaneously (BTC + ETH)
  - State persistence (save/load across restarts)

- [ ] **Error Scenarios**:
  - API connection failures (retry logic)
  - WebSocket reconnection (if used)
  - Order rejection handling
  - Rate limit errors

- [ ] **Stop Loss Scenarios**:
  - Trailing stop triggers correctly
  - Emergency kill switch works
  - Position closes properly

#### 3. Paper Trading Validation
- [ ] Run bot in paper trading mode (no real money)
- [ ] Test with small capital ($30-50)
- [ ] Run for 24-48 hours minimum
- [ ] Verify:
  - Orders execute as expected
  - PnL tracking accurate
  - No unexpected errors
  - System uptime > 95%

### 📋 Deliverables

1. **Test Suite**: Unit + integration tests (80%+ coverage)
2. **Test Report**: Pass/fail results, coverage metrics
3. **Paper Trading Results**: 24-48h validation data
4. **Bug Fixes**: All critical issues resolved

---

## Phase 6: Deployment (Staged Rollout)

**Status**: Required for every DEX
**Duration**: 1 day setup + 1-2 weeks validation
**Owner**: Architect

### ✅ Staged Rollout Strategy

#### Stage 1: Small Capital ($30-100)
- [ ] **Duration**: 1-3 days
- [ ] **Capital**: Start with $30-100
- [ ] **Goal**: Validate basic operation
- [ ] **Success Criteria**:
  - System uptime > 95%
  - No critical errors
  - Orders execute correctly
  - Stop loss triggers when expected

#### Stage 2: Medium Capital ($100-500)
- [ ] **Duration**: 3-5 days
- [ ] **Capital**: Increase to $100-500
- [ ] **Goal**: Validate scaling and performance
- [ ] **Success Criteria**:
  - Sharpe ratio > 70% of backtest (e.g., 2.5 vs 3.6)
  - Max drawdown < 150% of backtest (e.g., -25% vs -16.8%)
  - Consistent execution quality

#### Stage 3: Full Capital ($500+)
- [ ] **Duration**: 1-2 weeks
- [ ] **Capital**: Scale to target allocation
- [ ] **Goal**: Full-scale validation
- [ ] **Success Criteria**:
  - Sharpe ratio > 80% of backtest
  - Max drawdown < 120% of backtest
  - Stable long-term performance

### 📋 Deliverables

1. **Stage 1 Report**: 1-3 day results ($30-100)
2. **Stage 2 Report**: 3-5 day results ($100-500)
3. **Stage 3 Report**: 1-2 week results (full capital)
4. **GO/NO-GO Decision**: Continue or pause deployment

### ⚠️ Rollback Triggers

**Pause deployment if**:
- Sharpe ratio < 50% of backtest (e.g., < 1.8 vs 3.6)
- Max drawdown > 200% of backtest (e.g., > -33% vs -16.8%)
- System uptime < 90%
- Critical bugs discovered

---

## Phase 7: Post-Mortem (Ongoing)

**Status**: Required for every DEX
**Duration**: 15-30 min/day (ongoing)
**Owner**: PM + User

### ✅ Daily Review Checklist

- [ ] **PnL Tracking**:
  - Total PnL across all bots
  - Individual bot performance
  - Compare to backtest expectations

- [ ] **Trade Execution**:
  - Entry/exit accuracy
  - Slippage analysis
  - Fee impact analysis

- [ ] **System Health**:
  - API connection stability (WebSocket or REST)
  - Error rate (API failures, timeouts)
  - Uptime percentage

- [ ] **Risk Monitoring**:
  - Current drawdown vs max acceptable
  - Position sizes within limits
  - Leverage compliance

### ✅ Weekly Analysis Checklist

- [ ] **Performance Analysis**:
  - Backtest vs live performance gap
  - Sharpe ratio trend
  - Win rate consistency

- [ ] **Strategy Validation**:
  - Are entry/exit signals correct?
  - Is trailing stop working optimally?
  - Any pattern changes in market?

- [ ] **System Optimization**:
  - API performance (latency, errors)
  - Resource usage (CPU, memory)
  - Logging and monitoring effectiveness

### 📋 Deliverables

1. **Daily Log**: Brief notes on PnL, trades, issues
2. **Weekly Report**: Performance summary, issues, observations
3. **Improvement Ideas**: Optimization opportunities identified

---

## Phase 8: Strategy Improvement (Ongoing)

**Status**: Required for every DEX
**Duration**: Weekly/monthly iterations
**Owner**: PM + User

### ✅ Optimization Checklist

#### 1. Real-World Data Analysis
- [ ] **Live vs Backtest Gap**:
  - Identify sources of performance difference
  - Slippage: REST polling vs WebSocket latency
  - Fees: Actual vs backtested
  - Execution delay: REST 1Hz vs real-time

- [ ] **Market Regime Changes**:
  - Is strategy still performing in current market?
  - Volatility changes requiring parameter adjustment?
  - Correlation changes (BTC/ETH relationship)

#### 2. Parameter Tuning
- [ ] **DEX-Specific Optimization**:
  - Leverage adjustment (2x vs 3x)
  - Trailing stop optimization (2% vs 3% vs 5%)
  - Timeframe testing (1h vs 30m vs 15m)
  - Polling frequency (1Hz vs 2Hz for REST)

- [ ] **A/B Testing**:
  - Run two variants simultaneously
  - Compare performance over 1-2 weeks
  - Adopt better-performing variant

#### 3. New Strategy Research
- [ ] **Alternative Strategies**:
  - Grid trading
  - Market making
  - Delta neutral
  - Mean reversion

- [ ] **Multi-Strategy Diversification**:
  - Run multiple uncorrelated strategies
  - Reduce overall portfolio volatility
  - Improve risk-adjusted returns

### 📋 Deliverables

1. **Optimization Report**: Results of parameter tuning
2. **A/B Test Results**: Performance comparison
3. **New Strategy Research**: Potential additions to portfolio

---

## 🎯 Framework Validation Metrics

### Success Indicators

**Phase 0 Application**:
- ✅ Time saved by testing API first: 10+ hours
- ✅ Critical issues discovered before strategy build
- ✅ GO/NO-GO decision made early

**Phase 1-2 Reusability**:
- ✅ Time saved by reusing strategies: 1-3 weeks
- ✅ Backtest results portable across DEXs
- ✅ Same data source = same results

**Phase 4 Porting Efficiency**:
- ✅ First DEX: 1-2 weeks
- ✅ Second DEX: 2-3 hours (85% time reduction)
- ✅ Third+ DEX: 1-2 hours (90% time reduction)

### Framework Effectiveness

**Lighter (First DEX)**:
- ❌ Phase 0 skipped: 10 hours wasted building on broken API
- ✅ Phase 1-2: Strategy research and backtest complete
- ❌ Phase 4: Blocked by Phase 0 failure

**Apex (Second DEX)**:
- ✅ Phase 0 done first: Saved 10 hours, API validated
- ✅ Phase 1-2 reused: Saved 3 weeks
- ✅ Phase 4 porting: 2-3 hours (vs 1-2 weeks)
- **Total Time Saved**: 13 hours + 3 weeks

**Framework ROI**: Proven valuable with 2 DEX integrations

---

## 📚 Related Documents

### Common Framework Documents
- **DEX_BOT_DEVELOPMENT_CHECKLIST.md**: Operational requirements
  - Version management system
  - Telegram alert integration
  - GitHub commit automation
  - Testing and deployment procedures

- **IMPLEMENTATION_PLAN_COMMON.md**: Technical implementation
  - BaseDexClient architecture
  - RiskManager implementation
  - Common library structure

### DEX-Specific Documents
- **apex/APEX_INTEGRATION_STATUS.md**: Apex-specific progress and findings
- **lighter/LIGHTER_INTEGRATION_STATUS.md**: Lighter-specific progress and lessons
- **apex/docs/API_CONNECTION_GUIDE.md**: Apex API connection details
- **apex/LESSONS_LEARNED_APEX_INTEGRATION.md**: Apex-specific learnings

---

## 🔄 Framework Updates

**Version History**:
- v0.1 (2025-11-08): Initial framework from Lighter experience
- v0.2 (2025-11-09): Added Phase 0 (learned from Lighter failure)
- v1.0 (2025-11-09): Extracted to common framework (proven with 2 DEXs)

**Update Process**:
1. Learn from each DEX integration
2. Document lessons in DEX-specific files
3. Extract common patterns to this framework
4. Update version number and changelog

---

## 💡 Key Learnings

### Critical Principles

1. **API Connection First**: ALWAYS complete Phase 0 before strategy
   - Saves 10+ hours of wasted effort
   - Identifies blockers early (WebSocket broken, SDK bugs, etc.)
   - Validates GO/NO-GO decision

2. **Strategy Portability**: Reuse strategies across DEXs
   - Same OHLCV data = same results
   - Saves 1-3 weeks of research/backtesting
   - Only adjust for DEX-specific parameters (fees, slippage)

3. **Code Portability**: Port working code from previous DEX
   - Saves 85-90% of implementation time
   - Proven architecture and patterns
   - Only update API-specific integration points

### Common Pitfalls

**❌ Skipping Phase 0**:
- Risk: Build strategy on broken/incompatible API
- Cost: 10+ hours wasted + frustration
- Solution: ALWAYS test API connection first

**❌ Re-researching Strategy**:
- Risk: Waste 1-3 weeks testing same combinations
- Cost: Opportunity cost, delayed deployment
- Solution: Recognize strategy portability, reuse Phase 1-2 results

**❌ Building from Scratch**:
- Risk: Reinvent the wheel, repeat mistakes
- Cost: 1-2 weeks vs 2-3 hours
- Solution: Port working code, update DEX-specific parts only

---

**Framework Status**: ✅ Battle-tested and proven valuable (Lighter + Apex)
**Recommendation**: Follow this framework for all future DEX integrations
**Expected ROI**: Save 10+ hours + 3 weeks per DEX (after first DEX)
