<!-- Powered by BMAD™ Core -->

# PM Checklist: Perp DEX Point Farming Bot

**Version**: v0.1 (Initial - Pre-validation)
**Owner**: PM Agent (John)
**Purpose**: Product requirements and strategy validation for point farming bots
**Scope**: Strategy research, backtesting, performance monitoring, continuous improvement

[[LLM: INITIALIZATION INSTRUCTIONS

This checklist is specifically for **Perp DEX Point Farming Bot** projects. It complements the standard pm-checklist.md with domain-specific validations.

**EXECUTION ORDER**:
1. ✅ Standard pm-checklist.md (if creating PRD from scratch)
2. ✅ THIS CHECKLIST (perp-dex-farming specific validations)

**REQUIRED CONTEXT**:
Before proceeding, ensure you have:
- Master framework: perp-dex-farming-framework.md
- Bot type identified: Trend-Following, Volume, or Hybrid
- DEX name and point mechanism documentation
- Target capital amount

**PM FOCUS AREAS** (from 9-phase framework):
- ✅ Phase 1: Strategy Research (your primary responsibility)
- ✅ Phase 2: Python Backtesting (collaboration with user)
- ⚠️ Phase 3: PineScript Validation (optional, your responsibility if needed)
- ✅ Phase 7: Post-Mortem (ongoing monitoring)
- ✅ Phase 8: Strategy Improvement (continuous optimization)

**ARCHITECT HANDLES**:
- Phase 0: API Feasibility
- Phase 4: Implementation
- Phase 5: QA
- Phase 6: Deployment

**VALIDATION APPROACH**:
For each section:
1. **User Collaboration** - These are research/strategy questions requiring user input
2. **Document Findings** - Create clear deliverables (strategy docs, backtest reports)
3. **Data-Driven** - All decisions backed by backtest results
4. **Risk Awareness** - Always assess liquidation risk, max drawdown

**EXECUTION MODE**:
Ask user which mode:
- **Interactive** - Work through each phase, get user feedback before proceeding
- **Comprehensive** - Complete all research/backtesting, present full results at end]]

---

## Section 1: Strategy Research (Phase 1)

[[LLM: This is your PRIMARY responsibility as PM. Work with user to understand DEX point mechanics and identify profitable farming strategies. This phase typically takes 1-2 weeks.]]

### 1.1 DEX Point Mechanism Research (2-3 days)

**Objective**: Fully understand how this DEX awards points

- [ ] **Point Calculation Formula**
  - How are points calculated? (volume-based, position-based, TVL-based, hybrid?)
  - What is the exact formula? (e.g., "1 point per $100 volume" or "points = √(volume × leverage)")
  - Evidence: [Link to official docs or community analysis]

- [ ] **Point Efficiency Analysis**
  - What is point-to-dollar ratio? ($1000 volume = ? points)
  - Are there diminishing returns? (e.g., first $10K volume worth more points)
  - What is the optimal capital efficiency? (minimum capital for max point rate)
  - Evidence: [Calculate from official docs or reverse-engineer from leaderboards]

- [ ] **Multipliers and Boosters**
  - Are there leverage multipliers? (e.g., 2x leverage = 2x points?)
  - Specific trading pair bonuses? (e.g., BTC/ETH worth more points?)
  - Time-based multipliers? (e.g., weekends, campaigns)
  - Referral or tier bonuses?
  - Evidence: [Document all multipliers and conditions]

- [ ] **Rebate Programs** (Critical for volume bots)
  - Are there maker fee rebates? (negative fees for providing liquidity)
  - Taker fee structure?
  - VIP tiers or volume-based fee discounts?
  - Evidence: [Fee schedule from official docs]

- [ ] **Point Mechanism Type Classification**
  - **Type A: Volume-Focused** (most DEXs)
    - Primary driver: Trading volume
    - Strategy implication: Grid, MM, DN (maximize volume)
  - **Type B: Trend-Focused** (rare, e.g., Lighter)
    - Primary driver: Position holding, smart trading
    - Strategy implication: MA Crossover, MACD (maximize Sharpe)
  - **Type C: Hybrid**
    - Combination of volume + other factors
    - Strategy implication: Balanced approach
  - Classification: [A/B/C with rationale]

- [ ] **Competitor Analysis**
  - Check DEX leaderboard: Who are top farmers?
  - Estimate their strategies: Volume? Position size? Frequency?
  - Twitter/Discord research: Any shared strategies?
  - Evidence: [Leaderboard screenshots, community insights]

**Deliverable**: **Point Mechanism Summary Document**
```markdown
# [DEX Name] Point Mechanism Analysis

## Formula
[Exact point calculation formula]

## Efficiency
- $1000 volume = X points
- Optimal capital: $Y for maximum point rate
- ROI estimate: Z points/day per $1000 capital

## Multipliers
- Leverage: [Yes/No, details]
- Pairs: [List boosted pairs]
- Time: [Campaign dates, multipliers]

## Classification
Type: [A/B/C]
Optimal Strategy Type: [Trend-Following / Volume / Hybrid]

## Competitor Insights
[Top 3 farmer strategies observed]
```

### 1.2 Strategy Brainstorming (3-5 days)

**Objective**: Generate 10-20 strategy candidates tailored to DEX point mechanism

- [ ] **Trend-Following Strategies** (if Type B or C)
  - [ ] Moving Average Crossover (Golden/Death Cross)
    - Parameters: MA periods (e.g., 50/200), timeframes (15m-1d)
    - Pros: Simple, proven, works in trending markets
    - Cons: Lags in sideways markets, whipsaws

  - [ ] MACD (Moving Average Convergence Divergence)
    - Parameters: (12,26,9) standard or custom
    - Pros: Early trend detection, momentum filter
    - Cons: False signals in choppy markets

  - [ ] RSI Divergence
    - Parameters: RSI period (14 standard), overbought/oversold levels
    - Pros: Catches reversals early
    - Cons: Can stay overbought/oversold for extended periods

  - [ ] Breakout Strategies
    - Parameters: Lookback period, breakout threshold
    - Pros: Captures strong trends early
    - Cons: Many false breakouts

  - [ ] Custom Combinations
    - [User-defined strategies]

- [ ] **Volume Strategies** (if Type A or C)
  - [ ] Grid Trading
    - Concept: Place buy/sell orders at fixed intervals in a price range
    - Parameters: Grid count (10-100), range (±2% to ±20%), rebalance frequency
    - Pros: High volume in sideways markets, simple
    - Cons: Trend breakout risk (one-sided inventory)
    - Best for: Range-bound markets, low volatility

  - [ ] Market Making
    - Concept: Provide liquidity on both bid and ask sides
    - Parameters: Spread (0.1%-2%), inventory limits, order size
    - Pros: Maker rebates, high volume, consistent points
    - Cons: Adverse selection risk, requires fast execution
    - Best for: Liquid markets, stable conditions

  - [ ] Delta Neutral (Long Spot + Short Perp)
    - Concept: Arbitrage funding rate while staying market-neutral
    - Parameters: Hedge ratio (0.8-1.1), rebalance threshold (5%-15%)
    - Pros: Low directional risk, funding rate profits
    - Cons: Rebalancing costs, basis risk
    - Best for: High funding rate environments

  - [ ] Hybrid Grid + Trend Filter
    - Concept: Grid trading only in sideways markets, pause in strong trends
    - Parameters: Trend filter (e.g., ADX < 25), grid params
    - Pros: Combines volume + risk management
    - Cons: More complex

  - [ ] Custom Combinations
    - [User-defined volume strategies]

- [ ] **Strategy Candidate List**
  - List 10-20 strategies with brief descriptions
  - Tag each: [Trend/Volume/Hybrid], [Risk: Low/Med/High]
  - Initial gut ranking: Top 5 most promising

**Deliverable**: **Strategy Brainstorming Document**
```markdown
# Strategy Candidates for [DEX Name]

## Trend-Following (if applicable)
1. MA Crossover (50/200) - 1h timeframe [Risk: Medium]
2. MACD (12,26,9) - 30m timeframe [Risk: Medium]
...

## Volume Strategies
1. Grid Trading (50 levels, ±10% range) [Risk: Low-Medium]
2. Market Making (0.5% spread) [Risk: Medium]
3. Delta Neutral (1.0 hedge ratio) [Risk: Low]
...

## Top 5 Initial Picks
1. [Strategy] - [Rationale]
2. ...
```

### 1.3 Initial Strategy Filtering (2-3 days)

**Objective**: Narrow down to 5-10 backtest-ready strategies

- [ ] **Feasibility Check**
  - Can this strategy be implemented with available API? (check with Architect)
  - Capital requirements: Minimum $X needed?
  - Monitoring requirements: 24/7 bot or periodic checks?

- [ ] **Risk Assessment**
  - Liquidation risk: What leverage, what's max drawdown?
  - Market risk: Works in all conditions or specific (Bull/Bear/Sideways)?
  - Operational risk: API failures, downtime impact?

- [ ] **Resource Requirements**
  - Capital: $X - $Y range
  - Development time: Complexity (simple/medium/complex)
  - Monitoring time: User involvement needed?

- [ ] **Filter Criteria Application**
  ✅ **PASS if**:
  - Fits DEX point mechanism (volume for Type A, Sharpe for Type B)
  - Acceptable risk (MDD <15% for trend, inventory <50% for volume)
  - Feasible with available API and capital
  - User willing to monitor/manage

  ❌ **FAIL if**:
  - Doesn't match point mechanism (e.g., low-volume strategy for Type A DEX)
  - Unacceptable risk (MDD >20%, liquidation likely)
  - Not implementable (missing API features)
  - Too complex for user to manage

- [ ] **Final Strategy Shortlist** (5-10 strategies)
  - Each strategy: Name, parameters, expected metrics, risk level
  - Sorted by: Potential point efficiency (best guess before backtesting)

**Deliverable**: **Filtered Strategy Shortlist**
```markdown
# Backtest-Ready Strategies for [DEX Name]

## Shortlist (5-10 strategies)

### 1. Grid Trading (50 levels, ±10%)
- **Point Mechanism Fit**: High volume generation (Type A)
- **Risk**: Medium (MDD ~10-15%)
- **Capital**: $5,000 minimum
- **Feasibility**: ✅ API supports limit orders
- **Expected Point Efficiency**: ~X points/day

### 2. MA Crossover (50/200, 1h, 2x leverage)
...

## Rejected Strategies
1. [Strategy X] - Reason: Too high risk (MDD >20%)
2. [Strategy Y] - Reason: API doesn't support needed functionality
...
```

---

## Section 2: Python Backtesting (Phase 2)

[[LLM: This is a COLLABORATION between you (PM) and the user. You provide structure and requirements, user implements backtesting code. This phase takes 1-2 weeks.]]

### 2.1 Backtesting Framework Setup (2-3 days)

**Objective**: Establish backtesting infrastructure

- [ ] **Data Collection**
  - Data source identified: [Exchange API / CryptoDataDownload / ccxt / Other]
  - Historical data range: [Start date] to [End date] (minimum 1 year)
  - Data quality verified: No gaps, outliers cleaned
  - Coins covered: [List, e.g., BTC, ETH, SOL]
  - Timeframes: [15m, 30m, 1h, 4h, 1d, etc.]

- [ ] **Backtesting Engine Selection**
  - Python library: [backtrader / vectorbt / bt / custom]
  - Rationale: [Why this library for this project]
  - Setup complete: ✅ Code runs, sample backtest successful

- [ ] **Slippage Modeling**
  - Slippage assumption: [e.g., 0.02% per trade]
  - Basis: [Market depth analysis / Conservative estimate / Historical data]
  - Validation: Compare to live trading if previous data available

- [ ] **Fee Modeling**
  - Maker fee: [e.g., 0.02% or -0.01% if rebate]
  - Taker fee: [e.g., 0.05%]
  - Source: [Official DEX fee schedule]
  - VIP tiers: [Any volume-based discounts applicable]

- [ ] **Position Sizing Logic**
  - Fixed size: $X per trade OR
  - Percentage: Y% of capital per trade OR
  - Kelly Criterion / Custom formula
  - Leverage: [1x, 2x, 5x, 10x options]

**Deliverable**: **Backtesting Framework Documentation**
```python
# Backtesting Config for [DEX Name]

DATA_SOURCE = "ccxt"  # or specific exchange
DATE_RANGE = ("2023-01-01", "2024-01-01")
COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TIMEFRAMES = ["15m", "30m", "1h", "4h", "1d"]

SLIPPAGE = 0.0002  # 0.02%
MAKER_FEE = -0.0001  # -0.01% (rebate)
TAKER_FEE = 0.0005  # 0.05%

POSITION_SIZE = 0.95  # 95% of capital
LEVERAGE_OPTIONS = [1, 2, 3, 5, 10]
```

### 2.2 Combinatorial Testing (5-7 days)

**Objective**: Test all strategy combinations systematically

[[LLM: The testing approach differs by bot type. Guide user through appropriate combinatorial testing for their DEX classification.]]

- [ ] **For Trend-Following Bots (Type B)**

  **Testing Matrix**:
  ```python
  coins = [list from 2.1]  # e.g., 5 coins
  timeframes = [list from 2.1]  # e.g., 6 timeframes
  leverage = [1, 2, 3, 5, 10]  # 5 options
  stop_loss = [0.01, 0.02, 0.03, 0.05, 0.10]  # 5 options

  # Total combinations = 5 × 6 × 5 × 5 = 750
  ```

  **Primary Metrics**:
  - ✅ **Sharpe Ratio** (primary for ranking)
  - Max Drawdown (MDD)
  - Win Rate
  - Profit Factor
  - Total Return

  **Testing Execution**:
  - [ ] Run all 750 (or N) combinations
  - [ ] Record results in spreadsheet/database
  - [ ] Identify top 20% by Sharpe Ratio
  - [ ] Filter by risk: MDD < 15% (or user threshold)

  **Deliverable**: Backtesting results CSV/Excel
  ```csv
  Coin,Timeframe,Leverage,StopLoss,Sharpe,MDD,WinRate,TotalReturn
  BTC,1h,2,0.02,4.26,-6.5%,58%,+22.6%
  ETH,30m,1,0.03,3.82,-8.1%,54%,+18.3%
  ...
  ```

- [ ] **For Volume Bots (Type A)**

  **Grid Trading Testing**:
  ```python
  grid_intervals = [10, 20, 30, 50, 100]  # 5 options
  price_ranges = [0.02, 0.05, 0.10, 0.20]  # ±2%, ±5%, ±10%, ±20%
  rebalance_freq = ['1h', '4h', '1d']  # 3 options

  # Total combinations = 5 × 4 × 3 = 60
  ```

  **Market Making Testing**:
  ```python
  spreads = [0.001, 0.002, 0.005, 0.01, 0.02]  # 0.1% to 2%
  inventory_limits = [0.1, 0.25, 0.5, 1.0]  # 10% to 100% capital

  # Total combinations = 5 × 4 = 20
  ```

  **Delta Neutral Testing**:
  ```python
  hedge_ratios = [0.8, 0.9, 1.0, 1.1]  # 4 options
  rebalance_threshold = [0.05, 0.10, 0.15]  # 5%, 10%, 15%

  # Total combinations = 4 × 3 = 12
  ```

  **Primary Metrics**:
  - ✅ **Total Trading Volume** (primary for volume bots)
  - Point Efficiency (points per $1000 volume, estimated)
  - Net P&L (after fees and slippage)
  - Slippage Cost
  - Inventory Risk / Max Exposure

  **Testing Execution**:
  - [ ] Run all combinations for each strategy type
  - [ ] Record results with volume and P&L
  - [ ] Identify top strategies by volume (while P&L ≥ breakeven)
  - [ ] Check point efficiency estimates

  **Deliverable**: Backtesting results by strategy type
  ```csv
  # Grid Trading Results
  GridLevels,Range,RebalanceFreq,TotalVolume,NetPL,SlippageCost,PointEfficiency
  50,±10%,4h,$2.5M,+$120,-$500,High
  ...

  # Market Making Results
  Spread,InventoryLimit,TotalVolume,NetPL,InventoryRisk,PointEfficiency
  0.5%,50%,$5.0M,+$800,Medium,VeryHigh
  ...
  ```

- [ ] **For Hybrid Bots (Type C)**

  **Multi-Objective Optimization**:
  - Define combined score: `Score = α × Sharpe + β × (Volume / 1M)`
  - Where `α + β = 1` (user-defined weights, e.g., 0.6/0.4)
  - Test strategies with combined scoring

  **Deliverable**: Results sorted by combined score

### 2.3 Top Strategy Selection (1-2 days)

**Objective**: Select top 3-5 strategies for deeper validation

- [ ] **Selection Criteria Definition**
  - **For Trend-Following**:
    - Sharpe Ratio > [threshold, e.g., 2.5]
    - MDD < [threshold, e.g., 12%]
    - Win Rate > [threshold, e.g., 50%]
    - Works in multiple market conditions (Bull/Bear/Sideways)

  - **For Volume Bots**:
    - Volume meets target: >[e.g., $50K/day minimum]
    - P&L ≥ breakeven (after all costs)
    - Point efficiency acceptable
    - Low slippage cost (<0.05% average)

  - **For Hybrid**:
    - Combined score in top 20%
    - Acceptable Sharpe (>1.5) AND acceptable volume (>target)

- [ ] **Robustness Testing**
  - Test top strategies across market conditions:
    - Bull market period (e.g., Q4 2023)
    - Bear market period (e.g., Q2 2022)
    - Sideways market period (e.g., Q3 2023)
  - Consistency check: Does strategy work in all conditions or specialized?

- [ ] **Statistical Significance**
  - Number of trades: >30 (minimum for statistical validity)
  - Backtest period: ≥1 year (covers multiple market cycles)
  - Sharpe Ratio t-test: Statistically significant (p < 0.05)?

- [ ] **Final Top 3-5 Strategies**
  - Rank by primary metric (Sharpe or Volume)
  - Document strengths/weaknesses of each
  - Recommend #1 strategy with #2 as backup

**Deliverable**: **Top Strategy Selection Report**
```markdown
# Top Strategies for [DEX Name]

## Rank 1: [Strategy Name + Parameters]
- **Primary Metric**: Sharpe 4.26 / Volume $2.5M daily
- **Secondary Metrics**: MDD -6.5%, Win Rate 58%, P&L +$800/month
- **Robustness**: Works in Bull/Sideways, weaker in Bear
- **Statistical Significance**: 127 trades, Sharpe t-stat 3.8 (p<0.001)
- **Strengths**: Excellent risk-adjusted returns, consistent
- **Weaknesses**: Underperforms in strong bear markets
- **Recommendation**: ✅ PRIMARY STRATEGY

## Rank 2: [Strategy Name + Parameters]
- ...
- **Recommendation**: ⚠️ BACKUP STRATEGY

## Rank 3: [Strategy Name + Parameters]
- ...
- **Recommendation**: DIVERSIFICATION OPTION
```

---

## Section 3: PineScript Validation (Phase 3) [OPTIONAL]

[[LLM: This phase is OPTIONAL and depends on bot type and confidence level from Phase 2.

**Execute Phase 3 if**:
- Trend-following bot (recommended for long-term validation)
- User wants visual validation
- Access to 2+ years data via TradingView
- Moderate confidence from Phase 2 (want extra validation)

**Skip Phase 3 if**:
- Volume bot (Grid/MM/DN harder to model in PineScript)
- High confidence from Phase 2 (750 combos tested, clear winner)
- Time constraints
- Python results already very robust

Ask user whether to proceed with Phase 3 before starting.]]

### 3.1 PineScript Porting (1-2 days) [If Executing Phase 3]

**Objective**: Convert Python strategy to PineScript

- [ ] **Strategy Translation**
  - Python strategy code → PineScript v5
  - All indicators ported: MA, MACD, RSI, etc.
  - Entry/exit logic identical
  - Position sizing and leverage settings matched

- [ ] **Indicator Verification**
  - Compare indicator values: Python vs PineScript on same data
  - Tolerance: ±0.1% acceptable for floating point differences
  - Major discrepancies investigated and resolved

- [ ] **Sample Test** (1 week of data)
  - Run PineScript backtest on 1-week sample
  - Compare to Python backtest on same period
  - Entry/exit points should match exactly

**Deliverable**: PineScript strategy code (tested on sample data)

### 3.2 Long-Term Backtesting (1-2 days)

**Objective**: Validate with 2+ years of TradingView data

- [ ] **Extended Backtest Period**
  - Test period: [Start date] to [End date] (2+ years)
  - Market cycles covered:
    - Bull market: [Date range]
    - Bear market: [Date range]
    - Sideways market: [Date range]

- [ ] **Results Recording**
  - Sharpe Ratio: [X.XX]
  - Max Drawdown: [X.X%]
  - Win Rate: [XX%]
  - Total Return: [±XX%]
  - Number of trades: [NNN]

- [ ] **Comparison to Python Results**
  - Python Sharpe: [X.XX] vs PineScript Sharpe: [X.XX]
  - Difference: [X%] (acceptable if <10%)
  - Explanation for discrepancies: [data differences, execution assumptions, etc.]

**Deliverable**: TradingView backtest screenshot + results summary

### 3.3 Final Validation (1 day)

**Objective**: Confirm strategy readiness

- [ ] **Consistency Check**
  - Python results ≈ PineScript results (within 10%)
  - If major discrepancy (>10%), investigate and resolve
  - Document any known differences (e.g., PineScript uses different slippage model)

- [ ] **Edge Case Review**
  - Low liquidity periods: How does strategy behave?
  - Flash crashes: Stop loss triggers correctly?
  - Exchange downtime: Strategy resilient to data gaps?

- [ ] **Final Go/No-Go Decision**
  - ✅ GO: Results confirmed, strategy validated for implementation
  - ⚠️ CONDITIONAL: Minor issues found, proceed with caution
  - ❌ NO-GO: Major discrepancies, return to Phase 2

**Deliverable**: **PineScript Validation Report** (if Phase 3 executed)
```markdown
# PineScript Validation for [Strategy Name]

## Test Period
2022-01-01 to 2024-01-01 (2 years)

## Results Comparison
| Metric | Python | PineScript | Difference |
|--------|--------|------------|------------|
| Sharpe | 4.26 | 4.18 | -1.9% ✅ |
| MDD | -6.5% | -7.1% | +9.2% ✅ |
| Win Rate | 58% | 57% | -1.7% ✅ |
| Total Return | +22.6% | +21.8% | -3.5% ✅ |

## Market Cycle Performance
- Bull (2023 Q4): +8.2%
- Bear (2022 Q2): -2.1%
- Sideways (2023 Q3): +5.6%

## Edge Cases
- Flash crash (2023-08-17): Stop loss triggered correctly ✅
- Low liquidity: Strategy reduced position size appropriately ✅

## Decision
✅ GO - Strategy validated, ready for implementation
```

---

## Section 4: Post-Mortem & Monitoring (Phase 7)

[[LLM: This section is for ONGOING monitoring after bot deployment. Work with user to track performance daily and identify issues early.]]

### 4.1 Daily Performance Monitoring (15-30 min/day)

**Objective**: Track bot performance vs expectations

- [ ] **Performance Metrics Dashboard** (setup once, check daily)
  - Points earned today: [X points]
  - Points earned this week: [X points]
  - Points earned this month: [X points]
  - P&L today: $[±X]
  - P&L this week: $[±X]
  - P&L this month: $[±X]
  - Trading volume today: $[X]
  - Number of trades today: [N]

- [ ] **Comparison to Backtest** (weekly review)
  - Expected Sharpe: [X.XX] vs Actual Sharpe (rolling 30d): [X.XX]
  - Expected volume: $[X]/day vs Actual volume: $[X]/day
  - Expected point rate: [X]/day vs Actual point rate: [X]/day
  - Gap analysis: Why is actual different from expected?

- [ ] **Strategy Execution Accuracy** (weekly review)
  - Signals generated: [N]
  - Orders placed: [N] (should match signals)
  - Orders filled: [N] (check slippage, failed orders)
  - False signals / bugs: [List any anomalies]

**Deliverable**: Daily performance log (CSV or Google Sheet)
```csv
Date,PointsEarned,PL_USD,Volume_USD,Trades,SharpeRolling30d,Notes
2024-11-08,125,+$18,$8500,12,3.95,"Normal operation"
2024-11-09,98,-$5,$7200,9,3.89,"Lower volume, market sideways"
...
```

### 4.2 Issue Tracking (as needed)

**Objective**: Document problems for resolution

- [ ] **Error Log** (maintain continuously)
  - WebSocket disconnections: [Count, timestamps]
  - API errors: [Error codes, frequency]
  - Strategy anomalies: [Unexpected trades, missed signals]
  - Example format:
    ```
    [2024-11-08 14:23] WebSocket disconnected, reconnected after 5s
    [2024-11-08 18:45] API Error 429 (rate limit), order delayed 10s
    [2024-11-09 09:12] False signal (MA crossover in choppy market)
    ```

- [ ] **Root Cause Analysis** (for recurring issues)
  - Issue: [Description]
  - Frequency: [How often]
  - Impact: [Missed trades, lower points, cost]
  - Root cause: [Why it happened]
  - Fix: [How to prevent]
  - Example:
    ```markdown
    **Issue**: WebSocket disconnects 2-3 times per day
    **Frequency**: ~2.5/day average
    **Impact**: Missed 2 signals this week, ~50 points lost
    **Root Cause**: DEX WebSocket server unstable
    **Fix**: Implement exponential backoff reconnect logic (done 2024-11-09)
    ```

- [ ] **Bug Tracker** (GitHub Issues, Notion, etc.)
  - Track open bugs
  - Prioritize by impact (Critical/High/Medium/Low)
  - Assign to fix (Architect or user)

**Deliverable**: Issue tracker with resolutions

### 4.3 Learning Documentation (weekly summary)

**Objective**: Capture insights for Phase 8 improvements

- [ ] **Success Patterns** (what worked well)
  - Strategy X performed better than expected in [market condition]
  - Leverage adjustment to [X]x improved Sharpe by [Y%]
  - Grid rebalancing every [Z hours] reduced slippage
  - [Any other positive discoveries]

- [ ] **Failure Patterns** (what didn't work)
  - Strategy underperformed in [market condition]
  - False signals increased during [specific event, e.g., high volatility]
  - Slippage higher than expected on [pair]
  - [Any other issues]

- [ ] **Improvement Ideas** (for Phase 8)
  - Parameter tuning: Try [different stop loss / leverage / timeframe]
  - New strategy variant: Combine [strategy A] with [strategy B]
  - Risk management: Add [specific risk control]
  - [Other optimization ideas]

**Deliverable**: Weekly learnings summary
```markdown
# Week of 2024-11-04 Learnings

## Successes
- BTC 1h strategy Sharpe hit 4.5 (above backtest 4.26) ✅
- Lower leverage (1.5x) in high volatility worked well
- Point efficiency 10% better than expected

## Failures
- ETH 30m strategy underperformed (Sharpe 2.1 vs backtest 3.8)
- Reason: Higher slippage on ETH than modeled (0.05% vs 0.02%)

## Improvement Ideas
- Reduce ETH position size to minimize slippage
- Test 45m timeframe for ETH (between 30m and 1h)
- Add volatility filter: reduce leverage when ATR > threshold
```

---

## Section 5: Strategy Improvement (Phase 8)

[[LLM: This is ONGOING optimization work. Collaborate with user monthly or as needed to evolve the strategy based on real-world data.]]

### 5.1 Backtest-to-Live Gap Analysis (monthly)

**Objective**: Understand why live results differ from backtest

- [ ] **Slippage Analysis**
  - Backtest assumption: [X%]
  - Actual slippage: [Y%] (from live data)
  - Gap: [Y - X]%
  - Reason: [Market depth, order size, timing]
  - Action: Update backtest model with realistic slippage

- [ ] **Fee Analysis**
  - Backtest fees: Maker [X%], Taker [Y%]
  - Actual fees: Maker [A%], Taker [B%] (including rebates, VIP tiers)
  - Gap: [A - X]% maker, [B - Y]% taker
  - Action: Adjust backtest fee model

- [ ] **Execution Delay Analysis**
  - Backtest assumption: Instant execution
  - Actual delay: [X seconds] from signal to fill
  - Impact: Price slippage of [Y%] on average
  - Action: Add execution delay to backtest model

- [ ] **Updated Backtest** (with realistic parameters)
  - Re-run Phase 2 backtesting with:
    - Actual slippage: [X%]
    - Actual fees: Maker [X%], Taker [Y%]
    - Execution delay: [X seconds]
  - New expected metrics: [Document]
  - Compare to live performance: Gap should be <5% now

**Deliverable**: Gap analysis report + updated backtest results

### 5.2 Parameter Tuning (monthly or as needed)

**Objective**: Optimize strategy parameters based on live data

- [ ] **Identify Tuning Candidates**
  - Which parameters impact performance most?
    - Trend-following: Leverage, stop loss, timeframe, MA periods
    - Volume bots: Grid intervals, spread, rebalance frequency
  - Which parameters have shown suboptimal performance?
  - User intuition: What might improve results?

- [ ] **Re-Backtesting** (with current data)
  - Use last 3-6 months of live data
  - Test parameter variations around current settings
  - Example: If current SL is 2%, test [1.5%, 2%, 2.5%, 3%]
  - Identify optimal parameters for recent market conditions

- [ ] **A/B Testing Plan** (before full rollout)
  - New parameters: [Document]
  - Test allocation: 50% old params, 50% new params
  - Test duration: 1-2 weeks
  - Success criteria: New params outperform by >X% (e.g., 10%)

- [ ] **Rollout Decision**
  - If A/B test successful → Full migration to new parameters
  - If A/B test inconclusive → Extend test period
  - If A/B test failed → Revert to old parameters, try different tuning

**Deliverable**: Parameter tuning report + A/B test results

### 5.3 New Strategy Variants (quarterly or as needed)

**Objective**: Test completely new strategies or major modifications

- [ ] **Variant Ideation**
  - Based on Phase 7 learnings: [Specific insight leading to new idea]
  - New strategy concept: [Description]
  - Hypothesis: This will improve [metric] by [X%] because [reason]

- [ ] **Rapid Backtesting** (Phase 2 lite)
  - Quick backtest on last 6 months data
  - Compare to current strategy
  - If promising (>20% improvement) → Proceed to A/B test
  - If not promising → Document and discard

- [ ] **A/B Testing** (small scale)
  - Allocate 10-20% of capital to new variant
  - Run parallel to main strategy for 2-4 weeks
  - Compare: Points, P&L, Sharpe, Volume
  - Decision criteria: [Define upfront]

- [ ] **Migration or Discard**
  - ✅ Success: Migrate more capital (50% → 100% gradually)
  - ⚠️ Mixed results: Continue testing or try hybrid approach
  - ❌ Failure: Discard variant, document learnings

**Deliverable**: New variant backtest + A/B test results + decision

### 5.4 Strategy Evolution Tracking

**Objective**: Maintain history of strategy versions

- [ ] **Version Control**
  - v1.0: Initial deployment ([Date])
  - v1.1: Parameter tuning ([Date], [Changes])
  - v1.2: Slippage model update ([Date], [Changes])
  - v2.0: Major strategy variant ([Date], [Changes])
  - [Continue versioning]

- [ ] **Performance Comparison Across Versions**
  ```markdown
  | Version | Sharpe | Volume/day | Points/day | Notes |
  |---------|--------|------------|------------|-------|
  | v1.0 | 4.26 | $8K | 120 | Initial |
  | v1.1 | 4.45 | $8.5K | 128 | Tuned SL to 1.8% |
  | v1.2 | 4.38 | $8.2K | 125 | Added volatility filter |
  | v2.0 | 4.82 | $12K | 180 | Grid hybrid variant |
  ```

**Deliverable**: Strategy evolution log

---

## PM Success Criteria (Overall)

**Research Quality (Phase 1)**:
- ✅ DEX point mechanism fully understood and documented
- ✅ 10+ strategy candidates generated
- ✅ Top 5-10 strategies filtered and ready for backtesting

**Backtesting Rigor (Phase 2)**:
- ✅ All strategy combinations tested systematically (100+ tests minimum)
- ✅ Results documented with clear metrics
- ✅ Top 3-5 strategies selected with statistical significance
- ✅ Backtest assumptions (slippage, fees) realistic

**Validation (Phase 3, if executed)**:
- ✅ PineScript results consistent with Python (<10% difference)
- ✅ Strategy works across multiple market cycles
- ✅ No critical edge cases discovered

**Monitoring & Improvement (Phase 7-8)**:
- ✅ Daily performance tracked vs expectations
- ✅ Issues documented and resolved
- ✅ Strategy improves over time (v1.0 → v2.0+)
- ✅ Backtest-to-live gap minimized (<5%)

**Documentation**:
- ✅ All deliverables created (Point Mechanism doc, Strategy reports, Backtest results, etc.)
- ✅ Findings shared with Architect for implementation
- ✅ Continuous learning documented for future bots

---

## Appendix: PM-Architect Collaboration Points

**PM Provides to Architect**:
- Phase 1 Output: Strategy requirements, point mechanism summary
- Phase 2 Output: Winning strategy parameters, backtest results
- Phase 3 Output: PineScript validation (if done)
- Ongoing: Performance monitoring data, improvement requests

**Architect Provides to PM**:
- Phase 0 Output: API feasibility report (GO/NO-GO)
- Phase 4 Output: Implemented bot ready for testing
- Ongoing: Technical constraints, implementation feasibility feedback

**Handoff Points**:
1. After Phase 2 → PM hands off strategy spec to Architect for implementation (Phase 4)
2. After Phase 6 → Architect hands off deployed bot to PM for monitoring (Phase 7)
3. After Phase 8 tuning → PM hands off updated parameters to Architect for deployment

---

## Checklist Metadata

**Version**: v0.1
**Status**: DRAFT - Awaiting validation through first deployment
**Owner**: PM Agent (John)
**Created**: 2025-11-08
**Related Documents**:
- `perp-dex-farming-framework.md` - Master framework (all 9 phases)
- `architect-checklist-perp-dex-farming.md` - Architect's checklist (Phases 0, 4, 5, 6)
- `FINAL_STRATEGY_SELECTION.md` - Example from Lighter (750 combinations tested)

**Validation Plan**: Refine after each bot deployment (targeting 20+ DEXs)

---

**END OF PM CHECKLIST v0.1**
