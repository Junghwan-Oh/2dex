# Perp DEX Point Farming Bot Development Framework (Generic)

**Version**: v1.0 (DEX-Agnostic)
**Created**: 2025-11-08
**Scope**: Applicable to 20+ Perp DEX point farming bots
**Bot Types**: Trend-following, Volume bots, Hybrid strategies

---

## Framework Purpose

This framework provides a systematic, repeatable process for developing profitable point farming bots across multiple perpetual DEXs (Lighter, Apex Pro, Hyperliquid, dYdX, GMX, Gains Network, etc.).

**Validated Through**:
- Lighter DEX (2025-11): Phase 0 skip = 10 hours wasted
- Apex Pro (2025-01): Native TP/SL discovery = 15 hours saved

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

### Objectives
- Confirm API is publicly accessible
- Verify required endpoints work for your account type
- Detect Private Beta / waitlist blockers **BEFORE** implementation

### Key Validation Steps

#### 1. Authentication Test
```python
# Test basic authentication
try:
    client = DEXClient(api_key, api_secret)
    account = client.get_account()
    print(f"✅ Authentication successful: Account {account['id']}")
except Exception as e:
    print(f"❌ Authentication failed: {e}")
    # STOP HERE - NO-GO
```

#### 2. Order Placement Test (Critical)
```python
# Test order creation (testnet or minimum size)
try:
    order = client.create_order(
        symbol="BTC-USDT",
        side="BUY",
        type="LIMIT",
        size="0.001",  # Minimum size
        price=current_price * 0.95  # Far from market
    )
    print(f"✅ Order creation successful: {order['id']}")
    client.cancel_order(order['id'])  # Clean up
except Exception as e:
    print(f"❌ Order creation failed: {e}")
    # INVESTIGATE: Private Beta? Account type? Missing permissions?
```

#### 3. DEX-Specific Features Check
```python
# Check for native features (OCO, TP/SL, etc.)
try:
    # Example: Test native TP/SL
    order = client.create_order(
        symbol="BTC-USDT",
        side="BUY",
        type="LIMIT",
        size="0.001",
        price=current_price * 0.95,
        takeProfitPrice=current_price * 1.02,  # Test TP
        stopLossPrice=current_price * 0.98      # Test SL
    )
    print(f"✅ Native TP/SL supported: {order['id']}")
except Exception as e:
    print(f"⚠️ Native TP/SL not supported: {e}")
    # Note: Will need custom OCO logic
```

### Deliverables
- **GO**: Proceed to Phase 1 (all checks passed)
- **CONDITIONAL GO**: Proceed with documented limitations
- **NO-GO**: Stop immediately, try alternative DEX

### Common Blockers
| Blocker | Detection | Resolution |
|---------|-----------|------------|
| Private Beta | "Not authorized", "Invite only" | Request access OR switch DEX |
| API Key Type | "Invalid signature", "Wrong key type" | Generate correct key type |
| Account Restrictions | "Account not enabled", "KYC required" | Complete requirements OR switch DEX |
| Geographic Limits | "Region not supported" | Use VPN OR switch DEX |
| Testnet Unavailable | No testnet found | Use minimum position size ($10) |

---

## Phase 1: Strategy Research

**Duration**: 1-2 weeks
**Priority**: 🟡 IMPORTANT
**Owner**: PM + User

### Objectives
- Understand DEX point mechanism
- Generate 10-20 strategy candidates
- Select 5-10 for backtesting

### 1.1 Point Mechanism Research (2-3 days)

**Questions**:
1. How are points calculated?
   - Volume-based: $1 traded = X points
   - Position-based: $1 open interest × hours = X points
   - TVL-based: $1 liquidity provided × hours = X points
   - Hybrid: Combination of above

2. Are there multipliers?
   - Leverage multipliers (e.g., 5x leverage = 5x points)
   - Asset-specific (BTC = 1.5x, ETH = 1.2x)
   - Time-based (weekends = 2x, first month = 3x)
   - Maker/Taker differences

3. What is point-to-dollar efficiency?
   - Calculate: Points per $1000 volume
   - Historical data: Leaderboard analysis

### 1.2 Strategy Brainstorming (3-5 days)

**Trend-Following Strategies** (Sharpe-focused DEXs):
- Moving Average Crossover (MAC)
- RSI Divergence
- MACD
- Breakout/Breakdown
- Trailing Stop Loss optimization

**Volume Strategies** (Volume-focused DEXs):
- Grid Trading
- Market Making (dual-sided orders)
- Delta Neutral (long spot + short perp)
- Wash Trading (high frequency, zero net position)

**Hybrid Strategies**:
- Trend + Volume (follow trend, but with frequent rebalancing)

### 1.3 Initial Filtering (2-3 days)

**Filter Criteria**:
- ✅ Fits DEX point mechanism
- ✅ Acceptable risk (MDD < -30%, no liquidation)
- ✅ Feasible with API (rate limits, order types)
- ✅ Capital efficient (< $5000 per strategy)

---

## Phase 2: Python Backtesting

**Duration**: 1-2 weeks
**Priority**: 🔴 CRITICAL
**Owner**: PM + Architect

### Objectives
- Build reusable backtesting framework
- Test 50-750 strategy combinations
- Select top 3-5 strategies

### 2.1 Data Collection (1-2 days)

**Sources**:
- Exchange REST API (free, rate-limited)
- CryptoDataDownload (free CSV files)
- ccxt library (unified API)
- Binance Public API (most liquid)

**Requirements**:
- Minimum: 3 months OHLCV data
- Recommended: 1 year+ for robustness
- Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d

### 2.2 Framework Setup (2-3 days)

**Core Modules**:
```python
backtest/
├── __init__.py              # Module exports
├── engine.py                # Backtesting core
├── metrics.py               # Performance calculations
├── data_manager.py          # Data loading/validation
├── strategies.py            # Strategy implementations
├── visualizer.py            # Charts and reports
└── README.md                # Usage documentation
```

**Key Features**:
- Fee modeling (maker/taker)
- Slippage simulation (0.01-0.05%)
- Leverage support
- Trailing stop loss
- Position flipping (long ↔ short)

### 2.3 Combinatorial Testing (5-7 days)

**Trend-Following Example**:
```python
coins = ['BTC', 'ETH', 'SOL']  # 3
timeframes = ['15m', '30m', '1h', '4h']  # 4
leverages = [1, 2, 3, 5]  # 4
stopLoss = [0.01, 0.02, 0.03, 0.05]  # 4

Total = 3 × 4 × 4 × 4 = 192 combinations
```

**Metrics Calculated**:
- Sharpe Ratio (risk-adjusted return)
- Max Drawdown (MDD)
- Win Rate (% profitable trades)
- Profit Factor (wins/losses ratio)
- Total Return (%)
- Trade count

### 2.4 Top Strategy Selection (1-2 days)

**Selection Criteria**:
- Top 20% by Sharpe Ratio (or volume for volume bots)
- MDD < -20% (safe) or < -40% (acceptable)
- Win Rate > 35%
- Profit Factor > 1.5

**Deliverables**:
- `results/phase2_backtest_summary.csv`
- `results/reports/` - Individual strategy reports
- `docs/PHASE2_BACKTEST_RESULTS.md`

---

## Phase 3: PineScript Validation (Optional)

**Duration**: 3-5 days
**Priority**: 🟢 RECOMMENDED (trend-following), ⚠️ SKIP (volume bots)

### When to Use
- ✅ Trend-following strategies (need visual confirmation)
- ✅ Need 2+ years backtest data
- ❌ Volume bots (grid, MM, delta-neutral)
- ❌ Already tested 500+ combinations in Phase 2

### Objectives
- Validate Python results with TradingView
- Visual confirmation of strategy behavior
- Catch edge cases in bear/bull markets

---

## Phase 4: Implementation

**Duration**: 3-5 days
**Priority**: 🔴 CRITICAL
**Owner**: Architect

### 4.1 Architecture Design (1 day)

**Core Components**:
```python
bot/
├── config.py                # Configuration management
├── price_monitor.py         # Real-time price data (WebSocket or REST)
├── strategy_bot.py          # Strategy logic (signals)
├── executor.py              # Order execution (DEX API)
├── risk_manager.py          # Risk controls (stop loss, limits)
└── main.py                  # Orchestrator
```

### 4.2 Protocol Selection (Critical)

**WebSocket (Real-Time)**:
- Use for: Trend-following bots (need instant signals)
- Examples: MAC, RSI, MACD
- Latency: <100ms

**REST Polling (Periodic)**:
- Use for: Volume bots (periodic rebalancing)
- Examples: Grid, MM, Delta Neutral
- Frequency: Every 5-60 seconds

### 4.3 DEX-Specific Integration (2-3 days)

**API Key Setup**:
```python
# Generic structure (adapt per DEX)
client = DEXClient(
    api_key=os.getenv('DEX_API_KEY'),
    api_secret=os.getenv('DEX_API_SECRET'),
    api_passphrase=os.getenv('DEX_API_PASSPHRASE'),  # Some DEXs
    network='mainnet'  # or 'testnet'
)
```

**Common Pitfalls**:
1. **Wrong API Key Type**
   - Example: Lighter needs Ed25519 signing keys, not REST keys
   - Example: Apex needs HttpPrivateSign, not HttpPrivate_v3
   - Solution: Read API docs carefully, test in Phase 0

2. **Missing Native Features**
   - Always check: Native TP/SL? OCO orders? Conditional orders?
   - If missing: Implement custom logic (WebSocket + order cancel)
   - Example: Apex has native TP/SL (`isOpenTpslOrder=True`)

3. **Entry Price Uncertainty**
   - LIMIT orders: Don't know fill price until execution
   - Solution: Use MARKET orders OR add safety buffer
   - Example: Apex -8.43% loss due to wrong SL price

### 4.4 Paper Trading (1 day)

**Critical Validation**:
- Run with $10 capital for 1-7 days
- Test: Entry, exit, TP, SL, emergency stop
- Monitor: API errors, WebSocket disconnects, slippage

---

## Phase 5: QA

**Duration**: 1-2 days
**Priority**: 🔴 CRITICAL
**Owner**: Architect

### Testing Checklist

**Unit Tests**:
- [ ] Price monitor: Data accuracy, reconnection
- [ ] Strategy: Signal correctness, edge cases
- [ ] Executor: Order formatting, error handling
- [ ] Risk manager: Limit enforcement, kill switch

**Integration Tests**:
- [ ] Normal flow: Signal → Order → Position
- [ ] WebSocket disconnect/reconnect
- [ ] API errors (429, 500, timeout)
- [ ] Stop loss trigger
- [ ] Emergency shutdown

**Stress Tests**:
- [ ] Flash crash (50% drop in 1 minute)
- [ ] High volatility (100+ signals/hour)
- [ ] API rate limit testing
- [ ] 24h+ stability run

---

## Phase 6: Deployment

**Duration**: 1 day setup + 1-2 weeks validation
**Priority**: 🔴 CRITICAL
**Owner**: Architect

### Staged Rollout

**Stage 1: $10 Capital (1-3 days)**
- Goal: Validate basic operation
- Success: Sharpe > 2.5 (70% of backtest), No critical errors

**Stage 2: $100 Capital (3-5 days)**
- Goal: Validate scaling, point efficiency
- Success: Sharpe > 3.0 (80% of backtest), MDD < -25%

**Stage 3: $500 Capital (1-2 weeks)**
- Goal: Approach competition scale
- Success: Sharpe > 3.5 (95% of backtest), consistent points

**Stage 4: $2,000+ Capital**
- Condition: All previous stages successful
- Goal: Full-scale farming

### Monitoring Setup

**Logging**:
```python
logs/
├── bot.log              # All trades and decisions
├── error.log            # Errors only
└── performance.log      # Hourly metrics
```

**Alerts** (Discord/Telegram):
- Order fills
- API errors (consecutive failures > 5)
- Liquidation risk warnings
- Daily P&L summary

**Kill Switch**:
- Manual: Emergency stop button
- Auto: MDD > -15%, API errors > 10, liquidation risk

---

## Phase 7: Post-Mortem (Ongoing)

**Duration**: 15-30 min/day
**Priority**: 🟡 IMPORTANT
**Owner**: PM + User

### Daily Review (15 min)
- Points earned vs target
- P&L tracking
- Trade execution quality
- API/system errors

### Weekly Analysis (1 hour)
- Backtest vs live performance gap
- Slippage analysis (expected vs actual)
- Fee impact
- Execution delay impact

---

## Phase 8: Strategy Improvement (Ongoing)

**Duration**: Weekly/monthly iterations
**Priority**: 🟢 RECOMMENDED
**Owner**: PM + User

### Improvement Loop

**Real Data Analysis**:
- Slippage: Expected 0.01% → Actual ?%
- Fees: Maker/Taker ratio
- Execution delay: Backtest 0s → Live ?s

**Parameter Tuning**:
- Re-run Phase 2 with realistic parameters
- Optimize leverage, stop loss, timeframe
- A/B test: 50/50 capital split

**New Strategies**:
- Test with 10-20% capital
- Run parallel to main strategy
- Compare over 1-2 weeks

---

## Lessons Learned (Cross-DEX)

### DO ✅
1. **Always run Phase 0** (30 min can save 10+ hours)
2. **Research native features FIRST** (Apex: 15 hours saved)
3. **Test with minimum position size**
4. **Document every failure immediately**
5. **Account for entry price uncertainty**

### DON'T ❌
1. **Skip Phase 0** (Lighter: -10 hours)
2. **Build custom solutions before researching** (Apex: -15 hours)
3. **Trust SDK documentation blindly**
4. **Calculate TP/SL from unconfirmed entry** (Apex: -8.43% loss)
5. **Test on mainnet with real money first**

---

## Framework Metrics

**Success Criteria**:
- Phase 0 → Phase 6: 3-5 weeks (first bot)
- Phase 0 → Phase 6: 2-3 weeks (subsequent bots)
- Live performance: 70-95% of backtest metrics
- System uptime: >95%

**Failure Indicators**:
- Phase 0 skipped → 10+ hours wasted
- Live Sharpe < 50% of backtest → Strategy broken
- MDD > 150% of backtest → Risk management failed

---

**Version History**:
- v0.1 (2025-11-08): Initial draft based on Lighter experience
- v1.0 (2025-11-08): Generalized for all DEXs, validated with Apex learnings

**Next Review**: After 3rd DEX integration (target: 2025-12)
