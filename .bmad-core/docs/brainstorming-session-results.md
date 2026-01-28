# Brainstorming Session Results

**Session Date:** 2025-11-05
**Facilitator:** Business Analyst Mary
**Participant:** User

---

## Executive Summary

**Topic:** Building the Best Performing Point Farming Bot for Lighter Perp DEX

**Session Goals:** Maximize point farming with no loss or some profit on Lighter DEX, exploring various trading strategies with capital preservation as top priority.

**Techniques Used:** Progressive Technique Flow (Question Storming → Morphological Analysis → Strategy Comparison → Synthesis)

**Total Ideas Generated:** 25+ strategic concepts across architecture, risk management, position management, and coin selection

### Key Themes Identified:
- Snapshot-based point farming requires position quantity over raw volume
- Sharpe ratio >5 significantly increases point rewards (~20% boost)
- Newly listed coins offer 2-3x point multipliers but require careful risk management
- Adaptive learning systems outperform static strategies in dynamic farming environments
- 200-order architecture maximizes snapshot capture opportunities

---

## Technique Sessions

### Question Storming - 15 minutes

**Description:** Generated critical questions about Lighter's point farming mechanics to uncover strategic insights before solution generation.

#### Ideas Generated:

1. What exactly does Lighter's point algorithm reward beyond just volume?
2. Why would high Sharpe ratio matter more than raw profit in their system?
3. What defines a "minor coin" in Lighter's context?
4. How do random snapshots affect farming strategy compared to continuous volume?
5. What is the optimal position holding time for snapshot farming?
6. How does the fee-free environment change traditional market making economics?
7. What risk management is necessary for highly volatile newly listed coins?
8. Can sub-accounts be used for A/B testing different strategies?
9. How can API feedback inform real-time strategy optimization?
10. What is the relationship between trade size, holding time, and point rewards?

#### Insights Discovered:
- **Snapshot mechanics > volume:** Random snapshots mean position quantity and duration matter more than raw trading volume
- **Minor coins = newly listed:** Dedicated point allocation pools for new listings create 2-3x multiplier opportunities
- **Sharpe ratio as quality metric:** Lighter rewards consistent gainers (Sharpe >5) with ~20% point boost
- **Liquidations earn points:** Approximately 1 point per $1 liquidated (unexpected discovery)
- **MM allocation underutilized:** Season 2 allocates 20% to market making while LP pool ($500M HLP) is saturated

#### Notable Connections:
- Fee-free environment makes high-frequency strategies more viable than on traditional exchanges
- Snapshot farming connects to portfolio diversification (more positions = more snapshot opportunities)
- API-driven optimization mirrors machine learning feedback loops

---

### Morphological Analysis - 25 minutes

**Description:** Systematically explored strategy parameters by breaking down the bot architecture into key decision dimensions.

#### Ideas Generated:

**Parameter 1: Core Strategy Engine**
1. Grid Trading - Many orders generate volume + profit in ranging markets
2. Market Making (Avellaneda) - Baseline from Hummingbot, proven inventory management
3. Mean Reversion - Potentially highest Sharpe ratio strategy
4. Delta Neutral - Dropped (too few trades for volume requirements)
5. GDA (Gradual Dutch Auction) - Advanced MM alternative
6. Trend Following - High profit potential but low Sharpe and low volume
7. Momentum Strategies - Moderate across all metrics

**Parameter 2: Risk Management Layer**
1. Trailing stop orders - Dynamic exit protection
2. 200 small bots architecture - Diversification through $10/bot allocation
3. Sharpe +5 trigger close/reopen - Profit-taking based on quality metric
4. ATR-based spread adjustment - Volatility-adaptive positioning
5. Bollinger Band grid placement - Dynamic price level targeting
6. Breakeven trailing - Capital preservation once profitable
7. Time-decay stop tightening - Tighten stops on stagnant positions
8. Volatility kill-switch - Pause trading when volatility exceeds threshold

**Parameter 3: Position Management**
1. Time-based rebalancing - Periodic position adjustment
2. Volatility-adaptive spread widening - Adjust to market conditions
3. ATR-based spread adjustment - Statistical volatility measure
4. Bollinger Band grid placement - Mean reversion indicators
5. Volume-weighted positioning - Reduce size when liquidity drops
6. Breakeven trailing - Lock in no-loss once profitable

**Parameter 4: Coin Selection Logic**
1. Risk-tiered approach - 70% major coins, 20% new coins, 10% ultra-new
2. Manual whitelist - Research and pre-approve coins
3. Automated filtering (market cap, liquidity, listing age)
4. Hybrid alert system - Bot notifies, human approves
5. **API-driven adaptive optimization** - Weekly performance measurement and strategy pivoting
6. Multi-account A/B testing - Simultaneous strategy comparison (if sub-accounts allowed)

#### Insights Discovered:
- **200 orders, not instances:** 40 orders × 5 coins = optimal snapshot coverage
- **Coin selection clarity:** 3 major (BTC/ETH/SOL) + 2 new listed (MMT/ASTER)
- **Capital allocation strategy:** Major coins with 5x-10x leverage, new coins with strict capital preservation
- **Meta-strategy insight:** Learning system that optimizes itself > perfect Day 1 strategy

#### Notable Connections:
- 200-order architecture directly addresses snapshot farming mechanics
- Risk tiering balances point multipliers (new coins) with capital safety (majors)
- Adaptive optimization creates a self-improving system rather than static bot

---

### Strategy Comparison Matrix - 20 minutes

**Description:** Comparative analysis of strategy approaches against Lighter-specific success criteria.

#### Strategy Performance Matrix:

| Strategy | Sharpe Potential | Volume | Capital Preservation | Implementation | Lighter Fit |
|----------|-----------------|---------|---------------------|----------------|-------------|
| Mean Reversion | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | Medium | TBD (backtest) |
| Grid Trading | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Easy | ⭐⭐⭐⭐ |
| MM (Avellaneda) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium | ⭐⭐⭐⭐ |
| Grid+MM Hybrid | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Hard | ⭐⭐⭐⭐⭐ |
| Adaptive Multi-Strategy | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Very Hard | ⭐⭐⭐⭐⭐ |
| Trend Following | ⭐⭐ | ⭐⭐ | ⭐⭐ | Medium | ⭐⭐ |

#### Key Findings:
- **Mean Reversion** may achieve highest Sharpe but needs backtesting validation
- **Grid Trading** offers best implementation ease-to-performance ratio
- **Market Making** maximizes volume but moderate Sharpe
- **Hybrid approaches** score highest across all metrics but require more development
- **Trend Following** unsuitable for Lighter's snapshot + high Sharpe requirements

---

## Idea Categorization

### Immediate Opportunities
*Ideas ready to implement now*

1. **Mean Reversion Strategy Backtesting**
   - Description: Test existing Python mean reversion code on Lighter historical data for BTC/ETH/SOL
   - Why immediate: Code already exists, only requires data collection and backtesting execution
   - Resources needed: Lighter API historical data, backtesting framework (Backtrader/Zipline), 2-3 days execution time
   - Expected outcome: Validate Sharpe +5 potential and identify optimal parameters

### Future Innovations
*Ideas requiring development/research*

1. **Grid + MM Hybrid Strategy**
   - Description: 200-order architecture combining grid trading logic with Avellaneda market making inventory management
   - Development needed:
     - Integrate Grid logic with MM algorithms
     - Implement ATR-based spread adjustment
     - Build Bollinger Band grid placement system
     - Create breakeven trailing stop mechanism
     - Lighter API full integration
   - Timeline estimate: 2-3 weeks development + 1 week testing
   - Prerequisites: Mean Reversion backtest results analyzed

2. **Risk-Tiered Multi-Coin Portfolio**
   - Description:
     - Tier 1 (70% capital): BTC/ETH/SOL with 5x leverage, aggressive strategies
     - Tier 2 (20% capital): New coins with decent liquidity, conservative approach
     - Tier 3 (10% capital): Ultra-new listings, breakeven-only mode
   - Development needed: Portfolio management system, per-tier risk parameters, capital rebalancing logic
   - Timeline estimate: 1-2 weeks

3. **Advanced Risk Management Suite**
   - Description: Volatility-adaptive position management with ATR spreads, Bollinger Band grids, and breakeven trailing
   - Development needed: Real-time volatility calculations, dynamic spread adjustments, automated stop placement
   - Timeline estimate: 1 week

### Moonshots
*Ambitious, transformative concepts*

1. **Adaptive Multi-Strategy Optimization System**
   - Description: Self-optimizing bot that runs multiple strategies simultaneously, measures point efficiency via API, and automatically reallocates capital to winning approaches weekly
   - Transformative potential:
     - Eliminates need for perfect initial strategy selection
     - Continuously adapts to Lighter's evolving point algorithm
     - Learns from market regime changes
     - Scales winning strategies automatically
   - Challenges to overcome:
     - Complex architecture design (strategy module system)
     - Full Lighter API integration (leaderboard, point tracking, position management)
     - Strategy performance comparison and ranking logic
     - Intelligent capital reallocation algorithm
     - Sub-account management (if platform allows)
     - Weekly optimization scheduler with safety checks
   - Timeline: 1-2 months full implementation
   - Prerequisites: Mean Reversion + Grid/MM results, comprehensive Lighter API documentation

2. **Multi-Account A/B Testing Framework**
   - Description: Run different strategies on separate sub-accounts simultaneously to empirically determine optimal approach
   - Transformative potential: Real-world validation faster than sequential testing
   - Challenges: Sub-account availability unclear, requires sophisticated orchestration
   - Timeline: 2-3 weeks (if sub-accounts allowed)

### Insights & Learnings
*Key realizations from the session*

- **Volume ≠ Points in Lighter:** Unlike traditional exchanges, Lighter's random snapshot system means position quantity and duration matter more than raw trading volume. This fundamentally changes optimal strategy selection.

- **Sharpe Ratio as First-Class Metric:** Lighter explicitly rewards consistent profitability (Sharpe >5 earns ~20% point boost), making mean reversion and grid strategies potentially superior to high-volatility approaches like trend following.

- **New Coin Multiplier Effect:** Newly listed coins offer 2-3x point multipliers due to dedicated point allocation pools, but extreme volatility requires strict capital preservation measures (breakeven trailing, tight stops).

- **200-Order Architecture Insight:** Spreading capital across many small positions (40 orders × 5 coins) maximizes snapshot capture opportunities while maintaining diversification. At $10/order with $2,000 capital, this is perfectly feasible.

- **Adaptive > Static Strategy:** The meta-insight that a learning system with API feedback loops will outperform any static strategy over time. Weekly performance measurement and strategy pivoting creates competitive advantage.

- **Capital Preservation Primacy:** For $2,000 seed capital, no-loss priority supersedes point maximization. Breakeven trailing and conservative position sizing on volatile new coins are non-negotiable.

- **Backtesting Essential for Strategy Selection:** Theoretical comparison of Mean Reversion vs Grid vs MM strategies cannot determine Sharpe ratio performance without empirical data. Backtesting is mandatory before capital deployment.

---

## Action Planning

### Top 3 Priority Ideas

#### #1 Priority: Mean Reversion Strategy Backtesting

**Rationale:**
- Fastest path to execution (existing Python code)
- Highest theoretical Sharpe potential (⭐⭐⭐⭐⭐)
- Validates core assumption: mean reversion achieves Sharpe >5
- Low risk investment (time only, no capital)
- Provides empirical data for strategy comparison

**Next Steps:**
1. Locate and review Mean Reversion Python code
2. Collect Lighter historical data (BTC/ETH/SOL, minimum 3 months)
3. Set up backtesting environment (Backtrader, Zipline, or custom framework)
4. Execute backtest with key metrics: Sharpe ratio, max drawdown, win rate, average trade duration
5. Parameter optimization (entry/exit thresholds, position sizing, stop-loss levels)
6. Analyze results for Lighter point farming suitability (Sharpe >5? Sufficient trade frequency? Capital preservation?)
7. Document findings and compare to Grid/MM theoretical performance

**Resources Needed:**
- Lighter API access or alternative historical data source (CryptoDataDownload, exchange exports)
- Backtesting framework installation and configuration
- Python environment setup (2-3 hours)
- Analysis time (1-2 days)

**Timeline:** 3-5 days

---

#### #2 Priority: Grid + MM Hybrid Strategy Development

**Rationale:**
- Optimal balance of volume generation (MM) and Sharpe ratio (Grid)
- 200-order architecture directly addresses snapshot farming mechanics
- Leverages proven Hummingbot Avellaneda codebase
- Complements Mean Reversion (applies to different market conditions)
- Scalable to both major coins (BTC/ETH/SOL) and new listings

**Next Steps:**
1. Deep dive into Hummingbot Avellaneda source code
   - Understand inventory management logic
   - Identify spread calculation mechanism
   - Review order placement strategies
2. Design Grid bot logic
   - 40 orders per coin with optimized spread (e.g., $0.01K for BTC)
   - Dynamic grid range based on volatility (ATR or Bollinger Bands)
   - Order refresh logic when price moves out of range
3. Integrate risk management layers
   - ATR-based spread adjustment for volatility adaptation
   - Bollinger Band grid placement for mean reversion targeting
   - Breakeven trailing stops for capital preservation
   - Position size limits per coin tier
4. Lighter API integration
   - Order placement and cancellation
   - Position monitoring and PnL tracking
   - Point tracking (if API available)
5. Paper trading / testnet validation
   - Run strategy without real capital
   - Validate order logic, risk management, API connectivity
   - Measure simulated Sharpe ratio and volume generation

**Resources Needed:**
- Hummingbot repository analysis (20 hours)
- Grid trading algorithm implementation (20 hours)
- Risk management module development (15 hours)
- Lighter API integration (10 hours)
- Testing and debugging (15 hours)
- Lighter testnet access or minimal capital test ($50-100)

**Timeline:** 2-3 weeks

---

#### #3 Priority: Adaptive Multi-Strategy Optimization Framework

**Rationale:**
- Ultimate goal: self-optimizing system that adapts to Lighter's evolving point algorithm
- Integrates learnings from Mean Reversion + Grid/MM testing
- Competitive advantage through continuous improvement
- Maximizes long-term point farming efficiency
- Future-proofs against Lighter platform changes

**Next Steps:**
1. **Architecture Design (Week 1-2)**
   - Strategy module system (plug-and-play strategy components)
   - Performance measurement framework (Sharpe, points/capital, volume efficiency)
   - Capital allocation engine (dynamic rebalancing based on performance)
   - API integration layer (unified interface to Lighter)

2. **API Feedback Loop Implementation (Week 3-4)**
   - Leaderboard scraping or API endpoint integration
   - Point tracking per strategy module
   - Real-time performance dashboard
   - Automated data collection and storage

3. **Strategy Comparison Logic (Week 5-6)**
   - Normalized performance metrics across strategies
   - Statistical significance testing (avoid noise-driven decisions)
   - Risk-adjusted returns calculation
   - Strategy correlation analysis (diversification value)

4. **Capital Reallocation Algorithm (Week 7)**
   - Weekly optimization scheduler
   - Gradual rebalancing (avoid sudden shifts)
   - Minimum allocation floors (keep learning on all strategies)
   - Safety checks (max drawdown limits, Sharpe thresholds)

5. **Multi-Account Orchestration (Week 8, if available)**
   - Sub-account creation and management
   - Strategy assignment to accounts
   - Consolidated performance reporting
   - Account-level risk limits

6. **Testing and Validation (Week 9-10)**
   - Simulated multi-week performance
   - Edge case testing (extreme volatility, API failures)
   - Gradual capital deployment ($100 → $500 → $2000)

**Resources Needed:**
- Full-stack development time (100-150 hours)
- Lighter API comprehensive documentation
- Strategy orchestration framework (custom build or adapt existing)
- Performance analytics tools (Grafana, custom dashboard)
- Multi-account capability (platform dependent)
- Testing capital ($100-200 for gradual deployment)

**Timeline:** 1-2 months

---

## Reflection & Follow-up

### What Worked Well
- Progressive technique flow matched the complexity progression (broad → focused → prioritized)
- Question Storming uncovered critical Lighter-specific mechanics early
- Morphological Analysis systematically explored solution space without premature convergence
- Real-world constraints ($2K budget, Python, capital preservation) kept ideas grounded
- User's deep research on Lighter's point mechanics provided essential strategic foundation

### Areas for Further Exploration

- **Lighter API Deep Dive:** Comprehensive documentation review to identify all available endpoints, especially point tracking, leaderboard access, and sub-account management

- **Mean Reversion Strategy Variations:** Explore Bollinger Band mean reversion, Z-score based approaches, and potential cointegration-based pairs trading if multiple correlated coins exist

- **Execution Optimization:** Order placement timing to avoid obvious bot patterns, slippage minimization techniques, and gas/network cost considerations (if applicable to Lighter)

- **Funding Rate Farming:** Investigate how Lighter's funding rate mechanism works and whether holding positions to capture funding can complement point farming

- **Risk Management Advanced Topics:** Dynamic position sizing using Kelly Criterion adapted for crypto, correlation-based portfolio diversification, and volatility regime detection

### Recommended Follow-up Techniques

- **Five Whys:** When backtesting reveals unexpected results, drill down into root causes with systematic "why" questioning

- **Assumption Reversal:** Challenge core beliefs about strategy performance (e.g., "What if high volume actually hurts points?" or "What if new coins aren't worth the risk?")

- **SCAMPER Method:** Apply to successful strategies (Substitute, Combine, Adapt, Modify, Put to other use, Eliminate, Reverse) to generate incremental improvements

### Questions That Emerged

1. **Lighter API Capabilities:** Does Lighter provide real-time point tracking API? What endpoints are available for programmatic access?

2. **Sub-Account Policy:** Are sub-accounts officially allowed for A/B testing different strategies? Is there a sybil detection system that would flag this?

3. **Mean Reversion Code Source:** Where was the existing Python mean reversion code obtained? (Hummingbot? Custom implementation? Open source library?)

4. **New Listing Notifications:** How are newly listed coins announced? Is there an API event or notification system for automated detection?

5. **Funding Rate Mechanics:** How does Lighter's funding rate system work? Is there farming opportunity in holding positions to capture funding?

6. **Snapshot Timing:** Is there any pattern or predictability to Lighter's snapshot timing? Or is it truly random?

7. **Point Calculation Transparency:** Does Lighter publish the exact point calculation formula? Or is it reverse-engineered from leaderboard data?

8. **Historical Point Data:** Can historical point data be accessed to backtest point farming strategies alongside price/volume backtests?

---

## Next Session Planning

**Suggested Topics:**
1. **Mean Reversion Backtest Results Review** - Analyze Sharpe ratio, drawdowns, and point farming suitability
2. **Grid + MM Architecture Deep Dive** - Detailed technical design of 200-order hybrid system
3. **Lighter API Integration Strategy** - Comprehensive API documentation review and integration planning
4. **Real-World Testing Protocol** - Small-capital validation plan before full $2K deployment

**Recommended Timeframe:**
1 week (after Mean Reversion backtesting completion)

**Preparation Needed:**
1. Execute Mean Reversion backtesting on BTC/ETH/SOL with Lighter historical data
2. Read Lighter API documentation thoroughly
3. Review Hummingbot Avellaneda source code (market making logic, inventory management)
4. Collect examples of successful point farmers' strategies from Lighter community/Discord

---

## Backtesting & Real-World Validation Plan

### Backtesting Roadmap

**Phase 1: Mean Reversion Backtesting (Days 1-5)**
- Coins: BTC, ETH, SOL
- Data: Minimum 3 months historical (ideally 6 months)
- Metrics: Sharpe ratio, max drawdown, win rate, avg trade duration, total return
- Goal: Validate Sharpe >5 achievability
- Decision: Proceed to real-world test if Sharpe >4.0

**Phase 2: Grid Trading Backtesting (Days 6-10)**
- Coins: BTC, ETH, SOL (major), MMT, ASTER (new listings)
- Configuration: 40 orders per coin, varying spread widths
- Metrics: Same as Phase 1, plus volume generation
- Goal: Compare Sharpe vs Mean Reversion, validate volume output
- Decision: Select Grid vs MM vs Hybrid based on data

**Phase 3: Grid + MM Hybrid Backtesting (Days 11-15)**
- Only if Grid shows promise in Phase 2
- Combine Grid order placement with Avellaneda inventory management
- Goal: Validate that hybrid improves both Sharpe and volume
- Decision: Finalize strategy for real-world deployment

### Real-World Validation Plan

**Stage 1: Minimal Capital Test ($100, Week 1)**
- Deploy selected strategy (likely Mean Reversion or Grid)
- Coins: 1 major (BTC or ETH) only
- Goal: Validate API integration, order execution, no critical bugs
- Success Criteria: No major losses, API functions correctly, bot runs 24/7

**Stage 2: Multi-Coin Test ($500, Week 2-3)**
- Deploy to 3 coins: BTC, ETH, and 1 new listing
- Implement full risk management (trailing stops, position limits)
- Goal: Test diversification, measure actual point generation
- Success Criteria: Sharpe >3.0, no capital loss, points accumulating

**Stage 3: Full Deployment ($2,000, Week 4+)**
- Deploy 200-order architecture across 5 coins
- Activate adaptive optimization (if implemented)
- Weekly performance reviews and strategy adjustments
- Success Criteria: Sharpe >5.0, top 20% on leaderboard, capital preserved or growing

**Stage 4: Adaptive Multi-Strategy (Month 2+)**
- Deploy multiple strategies simultaneously
- API feedback loop measures point efficiency
- Weekly capital reallocation to winning strategies
- Success Criteria: Continuous improvement, top 10% leaderboard, profitable

---

*Session facilitated using the BMAD-METHOD™ brainstorming framework*
