# Product Requirements Document (PRD)
## Volume Farming Bot - Avellaneda Market Making Strategy

**Version**: 1.0
**Date**: October 24, 2025
**Status**: Phase 7 - Testnet Deployment
**Owner**: Quantitative Trading Team

---

## 1. Executive Summary

### Vision
Develop an automated market making system that generates consistent returns through spread capture on perpetual DEX platforms (Apex Pro, Paradex) using academically validated Avellaneda-Stoikov optimal market making strategy.

### Mission
Achieve sustainable 0.20%+ monthly returns with minimal human intervention while maintaining strict risk controls and capital preservation.

### Success Metrics
- **Primary**: ≥ 0.20% monthly return (validated in backtest)
- **Secondary**: 95%+ uptime, < 20% max drawdown
- **Tertiary**: Dynamic parameters outperform static by ≥ 0.05%

---

## 2. Strategic Context

### 2.1 Problem Statement

**Current Situation**:
- Manual market making requires constant monitoring
- Emotional decision-making leads to inconsistent results
- Difficult to capture spreads efficiently 24/7
- Hard to validate strategy effectiveness before deployment

**Pain Points**:
1. **Opportunity Cost**: Missing profitable spreads during off-hours
2. **Risk Management**: Human error in position sizing and risk limits
3. **Strategy Validation**: No systematic way to test strategies before live deployment
4. **Parameter Optimization**: Manual parameter tuning is time-consuming and subjective

### 2.2 Solution Approach

**Avellaneda-Stoikov Market Making**:
- Academic foundation: "High-frequency trading in a limit order book" (2008)
- Mathematically optimal spread calculation
- Inventory risk management built-in
- Time-decay awareness (end-of-day position management)

**Why This Strategy?**:
- ✅ Proven theoretical foundation
- ✅ Backtest validation: +0.20% return over 30 days
- ✅ Robust to fee structure changes
- ✅ Configurable risk parameters
- ✅ No directional market bias (market-neutral)

### 2.3 Competitive Landscape

**Existing Solutions**:
1. **Manual Trading**: High effort, inconsistent results
2. **Grid Bots**: Simple but not inventory-aware, prone to drawdowns
3. **HFT Firms**: Sophisticated but capital-intensive, not accessible

**Our Differentiation**:
- Academic rigor (Avellaneda-Stoikov model)
- Adaptive parameters (Order Book Analyzer)
- Comprehensive risk management (daily loss, drawdown limits)
- Open-source transparency
- Low capital requirement ($100 testnet, $5,000 mainnet)

---

## 3. Product Goals & Objectives

### 3.1 Business Goals

**Phase 7 (Testnet - Current)**:
- Validate strategy in live market conditions
- Compare static vs dynamic parameter performance
- Achieve break-even or better (≥ 0% return)
- Prove risk management effectiveness

**Phase 8 (Mainnet - Future)**:
- Scale to $5,000 capital
- Achieve ≥ 0.20% monthly return
- Maintain < 20% max drawdown
- Run continuously for 3+ months

### 3.2 User Goals

**Primary User**: Quantitative trader seeking passive income

**User Needs**:
1. **Confidence**: Strategy must be backtested and validated
2. **Control**: Adjustable risk parameters (position limits, stop-loss)
3. **Transparency**: Real-time monitoring and logging
4. **Safety**: Automated risk management (no catastrophic losses)
5. **Simplicity**: Deploy and monitor, minimal intervention

### 3.3 Technical Goals

**Reliability**:
- 95%+ uptime (auto-reconnect on WebSocket disconnect)
- Graceful error handling (log and continue, don't crash)
- Emergency shutdown on risk limit breach

**Performance**:
- < 1s order placement latency
- Real-time spread calculation
- Minimal slippage (maker-only orders)

**Observability**:
- Structured logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Real-time metrics (P&L, position, spreads)
- Trade history for post-analysis

---

## 4. Product Philosophy & Design Principles

### 4.1 Core Philosophy

**Evidence-Based Trading**:
- All strategies must be backtested before deployment
- Decisions driven by data, not intuition
- Continuous validation through A/B testing (static vs dynamic)

**Risk-First Mindset**:
- Preservation of capital is priority #1
- Returns are secondary to risk management
- Better to miss opportunities than take excessive risk

**Simplicity Over Complexity**:
- Clear, understandable strategy (Avellaneda MM)
- Minimal parameters (gamma, sigma, k)
- No black-box magic, transparent logic

### 4.2 Design Principles

**1. Composability**
```
System = Strategy + Analyzer + Client + Logger
```
- Each component can be tested independently
- Easy to swap components (e.g., different analyzers)
- Reusable across strategies

**2. Configuration Over Code**
```python
# Good: Configurable
params = AvellanedaParameters(gamma=0.1, use_dynamic_params=True)

# Bad: Hardcoded
GAMMA = 0.1  # Can't change without redeploying
```

**3. Fail-Safe Defaults**
```python
# Conservative defaults
max_daily_loss: float = 5.0      # 5% of capital
max_total_drawdown: float = 20.0  # Stop at -20%
apex_maker_fee: float = 0.0002   # Assume standard fee, not optimistic
```

**4. Logging Over Debugging**
```python
# Every decision logged
self.logger.info(f"BID placed at ${price:.2f} (spread: {spread*100:.3f}%)")
self.logger.critical(f"RISK LIMIT BREACHED: {reason}")
```

**5. Graceful Degradation**
```python
# If Order Book Analyzer fails, fall back to static params
if self.analyzer:
    kappa = self.analyzer.get_dynamic_parameters()['kappa']
else:
    kappa = self.params.k  # Static fallback
```

---

## 5. Functional Requirements

### 5.1 Core Features (MVP - Phase 7)

#### F1: Market Data Ingestion
**Requirement**: Real-time order book and trade data via WebSocket
- **Input**: Apex Pro WebSocket feed
- **Output**: `OrderBookSnapshot` with bids/asks, `last_price`
- **Frequency**: Real-time (< 100ms latency)
- **Reliability**: Auto-reconnect on disconnect

#### F2: Spread Calculation
**Requirement**: Calculate optimal bid/ask spreads using Avellaneda-Stoikov formula
- **Input**: Volatility, inventory, time remaining, risk aversion (gamma), liquidity (kappa)
- **Output**: `(bid_spread, ask_spread)` as percentages
- **Constraints**: `min_spread ≤ spread ≤ max_spread`
- **Formula**:
  ```
  base_spread = γσ²τ + (2/γ)ln(1 + γ/k)
  bid_spread = base_spread × time_factor × (1 + position_skew)
  ask_spread = base_spread × time_factor × (1 - position_skew)
  ```

#### F3: Order Placement (Maker-Only)
**Requirement**: Place limit orders on both sides of the order book
- **Type**: LIMIT orders only (never MARKET)
- **Flag**: `POST_ONLY=True` to ensure maker fee
- **Pricing**: Bid < best_bid, Ask > best_ask (never cross spread)
- **Size**: Configurable (default $100 per side)
- **Frequency**: Every 60 seconds (cancel and replace)

#### F4: Position Tracking
**Requirement**: Monitor inventory and calculate net position
- **Input**: API account data
- **Output**: `inventory_balance` (positive = long, negative = short)
- **Frequency**: Every iteration (5 seconds)
- **Action**: Trigger rebalancing if `|inventory| > position_limit`

#### F5: Risk Management
**Requirement**: Enforce position and loss limits
- **Daily Loss Limit**: Stop trading if daily P&L < -$5 (5%)
- **Total Drawdown Limit**: Stop if drawdown > 20% from peak
- **Position Limit**: Cancel orders if position > 150% of limit
- **Action**: Emergency shutdown (cancel all orders, exit loop)

#### F6: Logging & Monitoring
**Requirement**: Comprehensive activity logging
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Destinations**: Console (INFO+), File (DEBUG+)
- **Content**: Order placements, risk checks, errors, metrics
- **Retention**: Daily log files in `logs/` directory

### 5.2 Enhanced Features (Phase 7.2+)

#### F7: Dynamic Parameter Adaptation
**Requirement**: Real-time parameter calculation from order book
- **Component**: `OrderBookAnalyzer`
- **Inputs**: Order book bids/asks, trade history
- **Outputs**: `alpha` (arrival rate), `kappa` (liquidity), `sigma` (volatility)
- **Mode**: Optional (enabled via `use_dynamic_params=True`)
- **Hypothesis**: 5-15% performance improvement over static parameters

#### F8: Performance Metrics
**Requirement**: Real-time P&L and performance tracking
- **Metrics**: Total equity, unrealized P&L, realized P&L, inventory, open orders
- **Frequency**: Every iteration
- **Storage**: In-memory (daily reset for daily P&L)
- **Output**: `get_performance_metrics()` method

### 5.3 Future Features (Phase 8+)

#### F9: Multi-Exchange Arbitrage
**Requirement**: Capture price discrepancies between Apex and Paradex
- **Status**: NOT IMPLEMENTED (YAGNI principle)
- **Reason**: Single-exchange MM already profitable

#### F10: Machine Learning Parameter Tuning
**Requirement**: Optimize gamma, sigma, k via reinforcement learning
- **Status**: NOT IMPLEMENTED (YAGNI principle)
- **Reason**: Static parameters already validated

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Order Latency | < 1 second | < 5 seconds |
| WebSocket Reconnect | < 10 seconds | < 30 seconds |
| Spread Calculation | < 100ms | < 500ms |
| Risk Check Latency | < 50ms | < 200ms |
| Memory Usage | < 100MB | < 500MB |

### 6.2 Reliability

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Uptime | 95% | 90% |
| Error Rate | < 1% of operations | < 5% |
| Data Loss | 0% (all trades logged) | 0% |
| Recovery Time | < 1 minute | < 5 minutes |

### 6.3 Security

**API Credentials**:
- Store in `.env` file (never commit to git)
- Load via `python-dotenv`
- Validate on startup (check ZK keys present)

**Risk Controls**:
- Hard position limits (cannot be exceeded)
- Emergency shutdown on breach
- No leverage (1x only for testnet)

### 6.4 Maintainability

**Code Quality**:
- ✅ SOLID principles compliance (98% score)
- ✅ Type hints on all methods
- ✅ Docstrings on all classes and methods
- ✅ Structured logging throughout

**Documentation**:
- ✅ PRD (this document)
- ✅ Development methodology analysis
- ✅ Phase-specific implementation summaries
- ✅ Fee verification documentation
- ✅ Deployment plan

---

## 7. User Stories

### Epic 1: Strategy Development

**US-1.1**: As a quant trader, I want to backtest the Avellaneda MM strategy on historical data so that I can validate performance before deployment.
- **Acceptance**: Backtest shows +0.20% return over 30 days
- **Status**: ✅ DONE (Phase 1-3)

**US-1.2**: As a developer, I want to verify fee structures via API documentation so that my backtest assumptions are accurate.
- **Acceptance**: Confirmed Apex 0.02% maker fee, Paradex 0% retail
- **Status**: ✅ DONE (Phase 4-5)

### Epic 2: Parameter Optimization

**US-2.1**: As a quant, I want to test dynamic parameter adaptation so that the strategy can respond to changing market conditions.
- **Acceptance**: Order Book Analyzer integrated and tested
- **Status**: ✅ DONE (Phase 6)

**US-2.2**: As a quant, I want to compare static vs dynamic parameters so that I can measure the value of real-time adaptation.
- **Acceptance**: A/B test deployed on testnet with $100 each
- **Status**: 🔄 IN PROGRESS (Phase 7.2)

### Epic 3: Testnet Deployment

**US-3.1**: As a trader, I want to deploy the bot on testnet with real market data so that I can validate it works in live conditions.
- **Acceptance**: Bot runs for 1 week without crashes, ≥ 0% return
- **Status**: 🔄 IN PROGRESS (Phase 7)

**US-3.2**: As a trader, I want real-time monitoring of P&L and risk metrics so that I can intervene if needed.
- **Acceptance**: Dashboard shows equity, P&L, position, spreads
- **Status**: ⏳ PENDING (Phase 7.3)

**US-3.3**: As a developer, I want comprehensive logging of all trading activity so that I can debug issues and analyze performance.
- **Acceptance**: All orders, errors, risk events logged with timestamps
- **Status**: ✅ DONE (Phase 7.2)

### Epic 4: Risk Management

**US-4.1**: As a trader, I want automated position limits so that I never exceed my risk tolerance.
- **Acceptance**: Bot stops trading if position > limit
- **Status**: ✅ DONE (Phase 7.2)

**US-4.2**: As a trader, I want daily loss limits so that I don't lose more than X% in a single day.
- **Acceptance**: Bot pauses if daily P&L < -$5
- **Status**: ✅ DONE (Phase 7.2)

**US-4.3**: As a trader, I want total drawdown limits so that I can cut losses if strategy isn't working.
- **Acceptance**: Bot shuts down if drawdown > 20%
- **Status**: ✅ DONE (Phase 7.2)

---

## 8. Technical Architecture

### 8.1 System Components

```
┌─────────────────────────────────────────────────────────┐
│                   USER INTERFACE                        │
│  (Future: Dashboard, CLI, API)                         │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              TRADING CLIENT                             │
│  AvellanedaApexClient                                  │
│  - WebSocket Management                                 │
│  - Order Placement (Maker-Only)                        │
│  - Position Tracking                                    │
│  - Risk Management                                      │
└─┬──────────┬─────────────┬───────────────┬─────────────┘
  │          │             │               │
  ▼          ▼             ▼               ▼
┌─────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐
│ WS  │  │Strategy│  │  Order   │  │   Risk       │
│Feed │  │Engine  │  │  Book    │  │  Manager     │
│     │  │        │  │ Analyzer │  │              │
└─────┘  └────────┘  └──────────┘  └──────────────┘
                         │
                         ▼
                    ┌──────────────────┐
                    │ Dynamic Params   │
                    │ (alpha, kappa,   │
                    │  sigma)          │
                    └──────────────────┘
```

### 8.2 Data Flow

```
Market Data → WebSocket → Order Book Snapshot
                ↓
            Analyzer (if dynamic) → alpha, kappa, sigma
                ↓
        Calculate Optimal Spread → bid_spread, ask_spread
                ↓
        Calculate Order Prices → bid_price, ask_price
                ↓
        Place Maker Orders → POST_ONLY limit orders
                ↓
        Monitor Fills → Update inventory
                ↓
        Check Risk Limits → Emergency shutdown if breach
                ↓
        Log Everything → File + Console
```

### 8.3 Technology Stack

**Language**: Python 3.10+
**Libraries**:
- `apexomni`: Apex Pro SDK
- `websocket-client`: WebSocket connections
- `numpy`: Numerical computations
- `python-dotenv`: Environment variables
- `asyncio`: Async trading loop

**Infrastructure**:
- **Testnet**: Apex Pro Omni Testnet (BNB Chain)
- **Mainnet**: Apex Pro Omni Mainnet (Arbitrum)
- **Logs**: Local filesystem (`logs/` directory)
- **Monitoring**: Console + log files (Dashboard in Phase 7.3)

---

## 9. Success Criteria

### 9.1 Phase 7 (Testnet) - Current

**Minimum Viable**:
- [ ] Both versions run for 1 week without crashes
- [ ] Static version achieves ≥ 0% return (no loss)
- [ ] All risk limits tested and working
- [ ] Comprehensive logs captured

**Target**:
- [ ] Static version achieves ≥ +0.15% return
- [ ] No critical errors in logs
- [ ] 95%+ uptime (accounting for maintenance)
- [ ] Risk limits activate as expected

**Stretch**:
- [ ] Static version matches backtest (+0.20%)
- [ ] Dynamic version outperforms static by ≥ 0.05%
- [ ] Zero manual interventions needed

### 9.2 Phase 8 (Mainnet) - Future

**Minimum Viable**:
- [ ] Run for 1 month without losses
- [ ] Maintain < 15% max drawdown
- [ ] 90%+ uptime

**Target**:
- [ ] Achieve +0.20% monthly return
- [ ] Maintain < 10% max drawdown
- [ ] 95%+ uptime
- [ ] Sharpe ratio > 1.0

**Stretch**:
- [ ] Achieve +0.30%+ monthly return
- [ ] Maintain < 5% max drawdown
- [ ] 99%+ uptime
- [ ] Sharpe ratio > 2.0

---

## 10. Risks & Mitigations

### 10.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket disconnect | High | Medium | Auto-reconnect with exponential backoff |
| API rate limiting | Medium | Low | Rate limiter, queue requests |
| Order rejection | Medium | Low | Retry logic, log and continue |
| Calculation errors | Low | High | Unit tests, backtest validation |
| Memory leak | Low | Medium | Monitor memory, restart daily |

### 10.2 Market Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Low liquidity | Medium | Medium | Min spread = 0.01%, skip if spread too wide |
| High volatility | Medium | High | Wider spreads (sigma-based), position limits |
| One-sided market | Medium | Medium | Inventory skew adjustments, rebalancing |
| Flash crash | Low | High | Emergency shutdown on -20% drawdown |
| Exchange downtime | Low | High | Multiple exchange support (future) |

### 10.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Credential leak | Low | Critical | `.env` in `.gitignore`, never commit |
| Configuration error | Medium | High | Validation on startup, fail-safe defaults |
| Missed opportunity | High | Low | Acceptable (risk-first mindset) |
| Over-optimization | Medium | Medium | Simple strategy, backtest validation |

---

## 11. Timeline & Milestones

### Phase 7: Testnet Deployment (Current)

| Milestone | Status | Target Date | Actual Date |
|-----------|--------|-------------|-------------|
| 7.1 API Credentials | ✅ DONE | Oct 22 | Oct 22 |
| 7.2 Trading Client | ✅ DONE | Oct 24 | Oct 24 |
| 7.3 Monitoring Dashboard | 🔄 IN PROGRESS | Oct 25 | - |
| 7.4 Data Logger | ⏳ PENDING | Oct 26 | - |
| 7.5 Testing & Validation | ⏳ PENDING | Oct 27 | - |
| 7.6 Testnet Deployment | ⏳ PENDING | Oct 28 | - |

### Phase 8: Mainnet Scaling (Future)

| Milestone | Status | Target Date |
|-----------|--------|-------------|
| 8.1 Testnet Results Analysis | ⏳ PENDING | Nov 5 |
| 8.2 Mainnet Capital Preparation | ⏳ PENDING | Nov 10 |
| 8.3 Mainnet Deployment | ⏳ PENDING | Nov 15 |
| 8.4 1-Month Validation | ⏳ PENDING | Dec 15 |
| 8.5 Scale to Full Capital | ⏳ PENDING | Jan 1, 2026 |

---

## 12. Appendix

### 12.1 References

**Academic**:
- Avellaneda, M., & Stoikov, S. (2008). High-frequency trading in a limit order book. *Quantitative Finance*, 8(3), 217-224.

**Documentation**:
- `docs/FEE_VERIFICATION_2025.md` - Fee structure analysis
- `docs/TESTNET_DEPLOYMENT_PLAN.md` - Deployment strategy
- `docs/DYNAMIC_PARAMS_ANALYSIS.md` - Order Book Analyzer evaluation
- `docs/DEVELOPMENT_METHODOLOGY.md` - SDD & SOLID analysis
- `docs/FINAL_STRATEGY_COMPARISON.md` - Avellaneda vs Cross-DEX

### 12.2 Glossary

| Term | Definition |
|------|------------|
| **Avellaneda-Stoikov** | Optimal market making model from 2008 paper |
| **Maker Fee** | Fee paid for providing liquidity (limit orders) |
| **Taker Fee** | Fee paid for taking liquidity (market orders) |
| **Grid Bot** | UI-only feature on Apex (NOT available via API) |
| **RPI** | Retail Price Improvement (Paradex Pro MM rebate) |
| **kappa (κ)** | Liquidity parameter (order book depth coefficient) |
| **alpha (α)** | Order arrival intensity (trades per second) |
| **gamma (γ)** | Risk aversion parameter (0.01 to 1.0) |
| **sigma (σ)** | Volatility estimate (annualized) |

### 12.3 Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Oct 24, 2025 | Initial PRD creation |

---

**Document Owner**: Quantitative Trading Team
**Last Updated**: October 24, 2025
**Next Review**: After Phase 7 Testnet Completion
