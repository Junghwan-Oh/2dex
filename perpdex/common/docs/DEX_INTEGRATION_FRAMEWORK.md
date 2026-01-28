# 9-Stage DEX Integration Framework

**Version**: v2.2 (Complete Practical Volume Farming Guide - 95%+ Reflection Coverage)
**Purpose**: Systematic process for integrating any Perp DEX trading bot
**Status**: Proven framework with 2 DEX integrations (Lighter, Apex)

---

## 📋 Framework Overview

This framework provides a battle-tested process for integrating trading bots with Perpetual DEX platforms. It has been validated through:
- **Lighter**: Initial framework development (learned Phase 0 importance)
- **Apex**: Framework refinement (saved 13 hours + 3 weeks)
- **v2.0 Update**: Added strategy selection, point farming validation, multi-DEX scaling
- **v2.1 Update**: DN strategy 2 approaches, Lighter API constraint, Breakeven methodology
- **v2.2 Update**: DN popularity explanation, MM research process, detailed breakeven guides

**Key Principles**:
1. API connection first, strategy second
2. Strategy selection based on DEX point farming rules
3. Volume targets as important as profit targets

---

## 📊 Phase Progression

```
✅ Phase 0: API Connection Test (CRITICAL - Never skip)
   ↓
⏸️ Phase 1: Strategy Research (Can reuse across DEXs)
   ↓
🆕 Phase 1.5: Strategy Selection (Match DEX characteristics)
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
🆕 Phase 6.5: Point Farming Validation (Volume & trade frequency)
   ↓
⏸️ Phase 7: Post-Mortem (Daily/weekly reviews)
   ↓
⏸️ Phase 8: Strategy Improvement (Ongoing optimization)
   ↓
🆕 Phase 9: Multi-DEX Scaling (Scale to 20+ DEXes)
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

## Phase 1.5: Strategy Selection (NEW in v2.0)

**Status**: 🔴 CRITICAL for point farming
**Duration**: 1-2 hours
**Owner**: PM + User
**Critical Principle**: Match strategy to DEX characteristics

### Purpose

Select optimal trading strategy based on DEX point farming rules and fee structure.

**Why This Phase Matters**:
- Different DEXes reward different behaviors
- Wrong strategy = 96% gap in volume targets (Apex lesson learned)
- Right strategy = Point farming goals achievable

### ✅ Decision Matrix

#### Analyze DEX Characteristics

**1. Point Farming Metric**
```yaml
volume_based:
  Examples: Apex, dYdX, GMX
  Metric: Trading volume ($)
  Target: $1M/month
  → Recommended Strategy: Market Making (MM)

tvl_based:
  Examples: Lighter, Vertex
  Metric: Total Value Locked
  Target: High TVL + capital efficiency
  → Recommended Strategy: Delta Neutral (DN)

sharpe_bonus:
  Examples: Lighter, Hyperliquid
  Metric: Risk-adjusted returns
  Target: Sharpe ratio > 2.0
  → Recommended Strategy: Trend Following

hybrid:
  Examples: Paradex, Backpack
  Metric: Volume + TVL + Sharpe
  Target: Balanced approach
  → Recommended Strategy: MM + DN portfolio
```

**2. Fee Structure Analysis**
```yaml
maker_rebate:
  Fee: Maker < 0% (rebate)
  Examples: Paradex (-0.005%), GMX (-0.003%)
  → Primary: Delta Neutral (maximize maker rebates)
  → Secondary: Market Making

zero_maker_fee:
  Fee: Maker = 0%
  Examples: Apex (0%), Lighter (0%)
  → Primary: Market Making (no cost to provide liquidity)
  → Secondary: Grid Trading

positive_maker_fee:
  Fee: Maker > 0%
  Examples: dYdX (0.02% maker)
  → Primary: Trend Following (lower frequency)
  → Secondary: DN (3x/day only)
```

**3. Liquidity Depth**
```yaml
high_liquidity:
  Spread: < 2 bps
  → Market Making viable (tight spreads profitable)

medium_liquidity:
  Spread: 2-10 bps
  → Grid Trading (wider ranges needed)

low_liquidity:
  Spread: > 10 bps
  → Trend Following (avoid MM, too risky)
```

### Market Making DEX Research Process

**⚠️ CRITICAL**: MM 전략 채택 전 반드시 DEX별 정책을 리서치해야 합니다. 리서치 없이 전략 채택 시 수수료 손실, 특혜 미활용, volume 비효율이 발생합니다.

**Why MM Research is Critical**:
```yaml
dex마다_정책_상이:
  - GRVT: "MM이 모든 특혜 독점 (일반 트레이더는 불리)"
  - Lighter: "과거 무료 → 현재 MM 수수료 부과 시작"
  - Apex: "Maker fee 0%, Taker fee 0.025%"
  - Paradex: "Maker rebate -0.005% (받음)"
  - GMX: "Maker rebate -0.003% + volume bonus"

리서치_실패_시_리스크:
  - 수수료 손실: "Taker fee로 거래 → Maker rebate 못받음"
  - 특혜 미활용: "MM program 신청 안함 → 보너스 포기"
  - Volume 비효율: "높은 수수료 → 같은 자본으로 낮은 volume"
  - 기회비용: "더 유리한 DEX 놓침"

리서치_투자_대비_효과:
  - 리서치 시간: 2-4시간
  - 절약 효과: 월 수수료 $500-2000 절약
  - Volume 증가: 20-50% 향상 가능
  - ROI: 1,000%+ (2시간 → $500 절약)
```

**5-Step Research Process**:

**Step 1: Official Documentation Review**
```yaml
찾아볼_곳:
  - DEX 공식 웹사이트 (Trading Fees, Fee Structure)
  - Docs 섹션 (Market Making, Fee Tiers)
  - Blog/Medium (MM program announcement)

확인할_내용:
  - Maker fee (%, rebate 여부)
  - Taker fee (%)
  - Volume tiers (거래량별 할인)
  - MM program 존재 여부
  - Maker rebate 조건

예시:
  Paradex: "docs.paradex.trade → Trading → Fees"
  Apex: "pro.apex.exchange/fees"
```

**Step 2: Community Intelligence**
```yaml
채널:
  - Discord (official server, #trading or #market-making channel)
  - Telegram (official group, ask admins)
  - Twitter (search "@dex_name market making")
  - Reddit (r/cryptocurrency, r/defi)

질문_템플릿:
  "Is there a market making program on [DEX]?"
  "What are the maker/taker fees for [DEX]?"
  "Any volume-based fee discounts available?"
  "How do I apply for MM program?"

주의사항:
  - 공식 답변만 신뢰 (admins, mods)
  - 커뮤니티 의견은 참고만 (검증 필요)
  - Scam DM 조심 (공식 채널만 사용)
```

**Step 3: API Documentation Analysis**
```yaml
확인할_API:
  - POST /order (maker/taker 구분 가능한지)
  - GET /account/fees (현재 fee tier 확인)
  - GET /trading-rewards (rebate 내역)

중요_파라미터:
  - timeInForce: "POST_ONLY" (maker 보장)
  - orderType: "LIMIT" vs "MARKET"
  - Fee structure response (maker vs taker)

예시_코드:
  # Check if maker/taker differentiation exists
  response = api.get_account_info()
  if 'makerFeeRate' in response and 'takerFeeRate' in response:
      print("Maker/Taker differentiation: YES")
      print(f"Maker: {response['makerFeeRate']}")
      print(f"Taker: {response['takerFeeRate']}")
```

**Step 4: Test Order Execution**
```yaml
테스트_시나리오:
  1. "작은 금액 ($10-50) POST_ONLY 주문"
  2. "체결 후 fee 확인 (maker인지 taker인지)"
  3. "Rebate 발생 여부 확인 (음수 fee)"
  4. "API response로 fee 구조 검증"

검증_항목:
  - [ ] POST_ONLY 주문이 maker로 처리되는가?
  - [ ] Fee가 예상대로 부과/환급되는가?
  - [ ] API에서 maker/taker 구분되는가?
  - [ ] Rebate가 실제로 적립되는가?

예시:
  Order: BTC $100K POST_ONLY, Size: $50
  Expected: Maker fee = 0% or negative
  Result: Fee = -$0.025 (rebate) ✅
```

**Step 5: Sub-Account Comparison Testing**
```yaml
목적: "일반 계정 vs MM program 계정 비교"

설정:
  - Sub-account A: 일반 계정 (no MM program)
  - Sub-account B: MM program 신청 완료
  - 같은 전략, 같은 자본 ($1K-5K)

측정_지표:
  - Daily volume (A vs B)
  - Total fees paid/received
  - Maker ratio (%)
  - Net PnL after fees

기간: "1주일 테스트"

결과_해석:
  - B의 volume이 20%+ 높으면 → MM program 효과 있음 ✅
  - B의 net fees가 음수면 → Rebate 효과 있음 ✅
  - 차이 없으면 → MM program 불필요 (일반 계정 사용)
```

**Research Checklist**:
```yaml
before_strategy_adoption:
  - [ ] Step 1: Official docs reviewed (30 min)
  - [ ] Step 2: Community asked (discord/telegram, 30 min)
  - [ ] Step 3: API docs checked (30 min)
  - [ ] Step 4: Test order executed (1 hour)
  - [ ] Step 5: Sub-account comparison (1 week)

decision_criteria:
  go_mm:
    - Maker fee ≤ 0%
    - Maker rebate available
    - High liquidity (< 2 bps spread)
    - MM program benefits confirmed

  no_go_mm:
    - Maker fee > 0.01%
    - No maker/taker differentiation
    - Low liquidity (> 10 bps spread)
    - MM program unavailable
```

---

### Strategy Performance Profiles

| Strategy | Trade Freq | Monthly Volume | Profit Target | Risk | Farming Score |
|----------|-----------|----------------|---------------|------|---------------|
| **Market Making** | 50-100/day | $1M+ | 0.05-0.10% | Low | ⭐⭐⭐⭐⭐ |
| **Delta Neutral (Funding Sniper)** | 3-10/day | $300K-500K | 1.5-3% | Very Low | ⭐⭐⭐⭐ |
| **Delta Neutral (Volume Focus)** | 50-200/day | $1M-2M | 0.5-1% | Very Low | ⭐⭐⭐⭐⭐ |
| **Grid Trading** | 10-30/day | $500K-800K | 2-5% | Medium | ⭐⭐⭐ |
| **Trend Following** | 1-10/day | $40K-300K | 15-25% | High | ⭐⭐ |

### Delta Neutral Strategy: Two Approaches

**⚠️ IMPORTANT**: DN은 거래량봇 커뮤니티에서 가장 많이 채택된 전략이나, **두 가지 접근법**이 존재합니다. 각 DEX 특성에 맞는 접근법 선택이 필수입니다.

#### Why DN is Most Popular in Volume Farming

**거래량봇에서 DN이 가장 많이 채택되는 이유**:
```yaml
무손실_거래_최적화:
  - Market-neutral 포지션 → 가격 변동 위험 없음
  - 안정적 volume 생성 (predictable trade frequency)
  - 자본 보존 + volume 동시 달성

Maker_rebate_활용:
  - Maker rebate DEX (Paradex, GMX)에서 특히 유리
  - 거래할 때마다 수수료 받음 (음수 수수료)
  - Example: Paradex -0.005% maker = $10K volume당 $0.50 수익

낮은_진입장벽:
  - MM보다 구현 간단 (양쪽 orderbook 관리 불필요)
  - Grid보다 자본 효율 높음 (전체 range 커버 불필요)
  - Trend보다 안정적 (방향성 예측 불필요)

검증된_전략:
  - 거래량봇 커뮤니티에서 실전 검증됨
  - 200-4000 trades/day 달성 가능
  - $10K → $100M volume 사례 다수
```

**Current Status & Learning Priority**:
```yaml
⚠️_현재_이해도:
  - Funding Sniping DN: 50% (개념 이해, 구현 전)
  - Volume-Focused DN: 30% (이론만 알고 있음)
  - 2-DEX hedging 메커니즘: 40% (추가 학습 필요)

🔴_학습_우선순위:
  priority: HIGH (MM 다음 우선순위)
  reason: "거래량봇에서 가장 많이 채택 + 구현 난이도 중간"

  learning_path:
    1. "Funding arbitrage 메커니즘 이해 (Binance, OKX 펀딩비 추적)"
    2. "2-DEX API integration (Paradex + Apex)"
    3. "Hedge ratio 계산 로직 (delta-neutral 유지)"
    4. "Rebalancing trigger 최적화 (drift threshold)"
    5. "백테스트 (historical funding rates 데이터)"

  implementation_order:
    - Phase 2: Funding Sniping DN backtest (simpler, proven)
    - Phase 3: Volume-Focused DN backtest (complex, experimental)
    - Phase 4: Paradex + Apex hedging implementation
    - Phase 6: Sub-account A/B testing (DN vs MM)

success_criteria:
  - Sharpe ratio > 1.5 (DN은 낮은 수익률, 안정성 중시)
  - Max drawdown < 5% (market-neutral이므로 매우 낮아야 함)
  - Daily volume: $30K-100K (capital에 따라)
  - Maker ratio > 80% (rebate 최대화)
```

#### Approach 1: Funding Rate Sniping (펀딩비 스나이핑)

**목적**: 높은 수익률, 안정적 수익

**특징**:
```yaml
trade_frequency: 3-10 trades/day
execution_timing: Funding intervals (8h 간격)
monthly_volume: $300K-500K
profit_target: 1.5-3% monthly
risk: Very Low (market-neutral)

mechanism:
  1. Monitor funding rates across 2+ DEXes
  2. Enter hedged position before funding
  3. Collect funding payment
  4. Exit position after funding
  5. Wait for next opportunity

optimal_for:
  - Maker rebate DEXes (Paradex, GMX)
  - Low frequency point programs
  - High funding rate volatility markets
```

**Example**:
```python
# Funding Sniping DN
def should_enter_position(dex1_funding, dex2_funding, threshold=0.01):
    """
    Enter when funding rate differential > 1% annualized
    """
    rate_diff = abs(dex1_funding - dex2_funding)
    time_to_funding = get_time_to_next_funding()

    if rate_diff > threshold and time_to_funding < 1800:  # 30 min before
        return True, rate_diff
    return False, 0

# Result: 3-6 trades/day, $300K-500K volume, 1.5-3% return
```

#### Approach 2: Volume-Focused DN (거래량 중심)

**목적**: 거래량 최대화, Point farming 최적화

**특징**:
```yaml
trade_frequency: 50-200 trades/day
execution_timing: Continuous rebalancing
monthly_volume: $1M-2M
profit_target: 0.5-1% monthly
risk: Very Low (market-neutral)

mechanism:
  1. Maintain hedged position across 2 DEXes continuously
  2. Rebalance frequently to stay delta-neutral
  3. Each rebalance = 2 trades (1 per DEX)
  4. Profit from spread + funding + maker rebates
  5. High frequency = high volume

optimal_for:
  - Volume-based point programs (Apex, dYdX)
  - Maker rebate DEXes with tight spreads
  - High liquidity markets (BTC, ETH)
```

**Example**:
```python
# Volume-Focused DN
def rebalance_if_needed(long_pos, short_pos, threshold=0.02):
    """
    Rebalance when delta drift > 2%
    """
    delta_drift = abs(long_pos + short_pos) / long_pos

    if delta_drift > threshold:
        rebalance_amount = (long_pos + short_pos) / 2
        # Trade on both DEXes
        dex1.adjust_position(rebalance_amount)
        dex2.adjust_position(-rebalance_amount)
        return True
    return False

# With 2% drift threshold: ~100 rebalances/day = 200 trades/day
# Result: $1M-2M volume, 0.5-1% return, ⭐⭐⭐⭐⭐ farming score
```

#### DN Strategy Selection Matrix

| DEX Characteristic | Recommended Approach | Rationale |
|--------------------|---------------------|-----------|
| Volume-based points | **Volume-Focused DN** | Maximize trade count |
| Maker rebate + volume | **Volume-Focused DN** | Rebate + volume = best combo |
| Low frequency points | **Funding Sniping DN** | Quality > quantity |
| High funding volatility | **Funding Sniping DN** | Maximize profit per trade |
| Tight spreads (< 2 bps) | **Volume-Focused DN** | Low slippage cost |
| Wide spreads (> 5 bps) | **Funding Sniping DN** | Reduce rebalancing cost |

#### Current Status & Learning Priority

**⚠️ Gap Identified**:
- **Current understanding**: 부족 (두 접근법 모두 미구현)
- **Learning priority**: 🔴 HIGH (MM 다음 우선순위)
- **Implementation order**:
  1. Funding Sniping DN (simpler, proven)
  2. Volume-Focused DN (complex, experimental)

**Action Items**:
```yaml
phase_2_backtest:
  - [ ] Backtest Funding Sniping DN (2-DEX arbitrage)
  - [ ] Backtest Volume-Focused DN (continuous rebalancing)
  - [ ] Compare volume efficiency (trades/day, $/trade)

phase_4_implementation:
  - [ ] Implement Funding Sniping DN first (Paradex + Apex)
  - [ ] Test Volume-Focused DN with sub-accounts
  - [ ] Measure actual farming efficiency

decision_criteria:
  - If volume > profit: Volume-Focused DN
  - If profit > volume: Funding Sniping DN
  - If both important: Test both approaches
```

### Selection Process

**Step 1: Identify Primary Metric**
```python
def get_primary_metric(dex_config):
    """Determine what DEX optimizes for"""
    if dex_config['points']['metric'] == 'volume':
        return 'volume_farming'
    elif dex_config['fees']['maker'] < 0:
        return 'maker_rebate'
    elif 'sharpe_bonus' in dex_config['points']:
        return 'profit_optimization'
    else:
        return 'balanced'
```

**Step 2: Select Strategy**
```python
def select_strategy(primary_metric, dex_config):
    """Choose optimal strategy"""
    if primary_metric == 'volume_farming':
        return {
            'primary': 'Market Making',
            'backup': 'Grid Trading',
            'expected_volume': '$1M+/month',
            'trade_freq': '50-100/day'
        }

    elif primary_metric == 'maker_rebate':
        return {
            'primary': 'Delta Neutral',
            'backup': 'Market Making',
            'expected_volume': '$300K-500K/month',
            'trade_freq': '3/day'
        }

    elif primary_metric == 'profit_optimization':
        return {
            'primary': 'Trend Following',
            'backup': 'Delta Neutral',
            'expected_volume': '$100K-300K/month',
            'trade_freq': '1-10/day'
        }

    else:  # balanced
        return {
            'primary': 'Multi-Strategy Portfolio',
            'strategies': ['MM', 'DN', 'Trend'],
            'expected_volume': '$500K-1M/month',
            'trade_freq': '20-50/day'
        }
```

**Step 3: Validate Capital Requirements**
```yaml
market_making:
  min_capital: $10,000
  reason: "Need inventory for both sides"

delta_neutral:
  min_capital: $5,000 per DEX (2 DEXes needed)
  reason: "Hedged positions across 2 platforms"

grid_trading:
  min_capital: $3,000
  reason: "Multiple grid levels"

trend_following:
  min_capital: $500
  reason: "Single directional position"
```

### 📋 Deliverables

1. **Strategy Selection Document**
   - Primary strategy chosen
   - Backup strategy identified
   - Expected monthly volume
   - Expected trade frequency
   - Capital requirements

2. **Point Farming Projection**
   - Volume target: $X/month
   - Trade frequency: Y/day
   - Expected ranking: Top Z%
   - Point value estimate: $A-$B/month

3. **Implementation Roadmap**
   - Phase 2 backtest focus
   - Phase 4 implementation priorities
   - Phase 6.5 validation metrics

### 🎯 Success Criteria

- ✅ Strategy matches DEX primary metric
- ✅ Capital requirements validated
- ✅ Volume target achievable (≥ $1M/month for volume-based)
- ✅ Trade frequency realistic for bot automation

### ⚠️ Common Mistakes

**❌ Using Trend-Following for Volume Farming**
```yaml
Problem:
  Trend strategy: 1-10 trades/day
  Volume achieved: $40K/month
  Volume needed: $1M/month
  Gap: 96%

Solution:
  Switch to MM or Grid for volume DEXes
```

**❌ Ignoring Maker Rebates**
```yaml
Problem:
  DEX offers -0.005% maker rebate
  Using taker-heavy strategy (Trend)
  Missing rebate income: $500+/month

Solution:
  Implement DN or MM strategy
  Maximize maker orders
```

### Real Example: Apex

**Apex Characteristics**:
```yaml
point_metric: volume
maker_fee: 0.00%
taker_fee: 0.025%
liquidity: high (< 2 bps spread)
target_volume: $1M/month
```

**Initial Strategy** (Wrong):
```yaml
strategy: Trend Following
trade_freq: 1-10/day
monthly_volume: $40K
gap: 96% below target ❌
```

**Corrected Strategy** (Right):
```yaml
strategy: Market Making
trade_freq: 50-100/day
monthly_volume: $1M+
achievement: 100%+ of target ✅
```

**Lesson**: Always complete Phase 1.5 before proceeding to Phase 2.

#### Apex Strategy Evolution

```yaml
apex_transition:
  current: Trend Following (EMA Crossover)
  reason: "빠른 검증 + 안정적 성능"

  next_strategy_evaluation:
    - Market Making: Volume 최적화 (50-100 trades/day)
    - Grid Trading: 안정적 volume (10-30 trades/day)
    - Delta Neutral (Volume Focus): 최고 volume (50-200 trades/day)

  decision_timeline: "1개월 실전 검증 후 결정"

lighter_preparation:
  keep: Trend Following
  reason: "Lighter는 Sharpe bonus 제공 (Sharpe > 5 시 30% 포인트 보너스)"
  why_trend_for_lighter: "Volume보다 Risk-adjusted return 중요, 거래수수료 무료 → 낮은 거래수도 OK"
  constraint: "⚠️ API Private Beta Permission 대기 중"
  why_apex_testing: "Permission 획득 즉시 배포 위해 Apex에서 완성도 높이기"
  status: "Apex 1개월 실전 검증 후 Lighter 배포 준비 완료"

  completion_criteria_detailed:
    backtest_validation:
      - Sharpe ratio > 3.0 (목표: 5.0 for 30% bonus)
      - Max drawdown < 15%
      - Win rate > 55%
      - Profit factor > 1.5
      - Monthly return > 10% (consistent)

    apex_실전_검증:
      - 1개월 실전 운영 (안정성 확인)
      - Sharpe > 3.0 유지 (실전에서도)
      - Max drawdown < 15% (실전에서도)
      - 시스템 안정성 (crashes, errors < 1%)
      - Trade execution quality (slippage < 0.1%)

    lighter_배포_준비:
      - API private beta permission 승인 대기 중
      - 승인 즉시 코드 배포 가능 (Apex 검증 완료)
      - 예상 Sharpe: 3.0-5.0 (Lighter fee-free 환경)
      - 포인트 보너스 목표: 30% (Sharpe > 5 달성 시)

    success_probability:
      - Apex 검증 통과 시 Lighter 성공 확률 > 80%
      - Sharpe 5.0 달성 시 Top 10% ranking 예상
      - Volume은 낮지만 ($40K-100K/month) point efficiency 높음
```



---

## Phase 1.5: Strategy Selection (NEW in v2.0)

**Status**: 🔴 CRITICAL for point farming
**Duration**: 1-2 hours
**Owner**: PM + User
**Critical Principle**: Match strategy to DEX characteristics

### Purpose

Select optimal trading strategy based on DEX point farming rules and fee structure.

**Why This Phase Matters**:
- Different DEXes reward different behaviors
- Wrong strategy = 96% gap in volume targets (Apex lesson learned)
- Right strategy = Point farming goals achievable

### ✅ Decision Matrix

#### Analyze DEX Characteristics

**1. Point Farming Metric**
```yaml
volume_based:
  Examples: Apex, dYdX, GMX
  Metric: Trading volume ($)
  Target: $1M/month
  → Recommended Strategy: Market Making (MM)

tvl_based:
  Examples: Lighter, Vertex
  Metric: Total Value Locked
  Target: High TVL + capital efficiency
  → Recommended Strategy: Delta Neutral (DN)

sharpe_bonus:
  Examples: Lighter, Hyperliquid
  Metric: Risk-adjusted returns
  Target: Sharpe ratio > 2.0
  → Recommended Strategy: Trend Following

hybrid:
  Examples: Paradex, Backpack
  Metric: Volume + TVL + Sharpe
  Target: Balanced approach
  → Recommended Strategy: MM + DN portfolio
```

**2. Fee Structure Analysis**
```yaml
maker_rebate:
  Fee: Maker < 0% (rebate)
  Examples: Paradex (-0.005%), GMX (-0.003%)
  → Primary: Delta Neutral (maximize maker rebates)
  → Secondary: Market Making

zero_maker_fee:
  Fee: Maker = 0%
  Examples: Apex (0%), Lighter (0%)
  → Primary: Market Making (no cost to provide liquidity)
  → Secondary: Grid Trading

positive_maker_fee:
  Fee: Maker > 0%
  Examples: dYdX (0.02% maker)
  → Primary: Trend Following (lower frequency)
  → Secondary: DN (3x/day only)
```

**3. Liquidity Depth**
```yaml
high_liquidity:
  Spread: < 2 bps
  → Market Making viable (tight spreads profitable)

medium_liquidity:
  Spread: 2-10 bps
  → Grid Trading (wider ranges needed)

low_liquidity:
  Spread: > 10 bps
  → Trend Following (avoid MM, too risky)
```


### Strategy Performance Profiles

| Strategy | Trade Freq | Monthly Volume | Profit Target | Risk | Farming Score |
|----------|-----------|----------------|---------------|------|---------------|
| **Market Making** | 50-100/day | $1M+ | 0.05-0.10% | Low | ⭐⭐⭐⭐⭐ |
| **Delta Neutral (Funding Sniper)** | 3-10/day | $300K-500K | 1.5-3% | Very Low | ⭐⭐⭐⭐ |
| **Delta Neutral (Volume Focus)** | 50-200/day | $1M-2M | 0.5-1% | Very Low | ⭐⭐⭐⭐⭐ |
| **Grid Trading** | 10-30/day | $500K-800K | 2-5% | Medium | ⭐⭐⭐ |
| **Trend Following** | 1-10/day | $40K-300K | 15-25% | High | ⭐⭐ |

### Delta Neutral Strategy: Two Approaches

**⚠️ IMPORTANT**: DN은 거래량봇 커뮤니티에서 가장 많이 채택된 전략이나, **두 가지 접근법**이 존재합니다. 각 DEX 특성에 맞는 접근법 선택이 필수입니다.


### Selection Process

**Step 1: Identify Primary Metric**
```python
def get_primary_metric(dex_config):
    """Determine what DEX optimizes for"""
    if dex_config['points']['metric'] == 'volume':
        return 'volume_farming'
    elif dex_config['fees']['maker'] < 0:
        return 'maker_rebate'
    elif 'sharpe_bonus' in dex_config['points']:
        return 'profit_optimization'
    else:
        return 'balanced'
```

**Step 2: Select Strategy**
```python
def select_strategy(primary_metric, dex_config):
    """Choose optimal strategy"""
    if primary_metric == 'volume_farming':
        return {
            'primary': 'Market Making',
            'backup': 'Grid Trading',
            'expected_volume': '$1M+/month',
            'trade_freq': '50-100/day'
        }

    elif primary_metric == 'maker_rebate':
        return {
            'primary': 'Delta Neutral',
            'backup': 'Market Making',
            'expected_volume': '$300K-500K/month',
            'trade_freq': '3/day'
        }

    elif primary_metric == 'profit_optimization':
        return {
            'primary': 'Trend Following',
            'backup': 'Delta Neutral',
            'expected_volume': '$100K-300K/month',
            'trade_freq': '1-10/day'
        }

    else:  # balanced
        return {
            'primary': 'Multi-Strategy Portfolio',
            'strategies': ['MM', 'DN', 'Trend'],
            'expected_volume': '$500K-1M/month',
            'trade_freq': '20-50/day'
        }
```

**Step 3: Validate Capital Requirements**
```yaml
market_making:
  min_capital: $10,000
  reason: "Need inventory for both sides"

delta_neutral:
  min_capital: $5,000 per DEX (2 DEXes needed)
  reason: "Hedged positions across 2 platforms"

grid_trading:
  min_capital: $3,000
  reason: "Multiple grid levels"

trend_following:
  min_capital: $500
  reason: "Single directional position"
```

### 📋 Deliverables

1. **Strategy Selection Document**
   - Primary strategy chosen
   - Backup strategy identified
   - Expected monthly volume
   - Expected trade frequency
   - Capital requirements

2. **Point Farming Projection**
   - Volume target: $X/month
   - Trade frequency: Y/day
   - Expected ranking: Top Z%
   - Point value estimate: $A-$B/month

3. **Implementation Roadmap**
   - Phase 2 backtest focus
   - Phase 4 implementation priorities
   - Phase 6.5 validation metrics

### 🎯 Success Criteria

- ✅ Strategy matches DEX primary metric
- ✅ Capital requirements validated
- ✅ Volume target achievable (≥ $1M/month for volume-based)
- ✅ Trade frequency realistic for bot automation

### ⚠️ Common Mistakes

**❌ Using Trend-Following for Volume Farming**
```yaml
Problem:
  Trend strategy: 1-10 trades/day
  Volume achieved: $40K/month
  Volume needed: $1M/month
  Gap: 96%

Solution:
  Switch to MM or Grid for volume DEXes
```

**❌ Ignoring Maker Rebates**
```yaml
Problem:
  DEX offers -0.005% maker rebate
  Using taker-heavy strategy (Trend)
  Missing rebate income: $500+/month

Solution:
  Implement DN or MM strategy
  Maximize maker orders
```

### Real Example: Apex

**Apex Characteristics**:
```yaml
point_metric: volume
maker_fee: 0.00%
taker_fee: 0.025%
liquidity: high (< 2 bps spread)
target_volume: $1M/month
```

**Initial Strategy** (Wrong):
```yaml
strategy: Trend Following
trade_freq: 1-10/day
monthly_volume: $40K
gap: 96% below target ❌
```

**Corrected Strategy** (Right):
```yaml
strategy: Market Making
trade_freq: 50-100/day
monthly_volume: $1M+
achievement: 100%+ of target ✅
```

**Lesson**: Always complete Phase 1.5 before proceeding to Phase 2.

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

## Phase 6.5: Point Farming Validation (NEW in v2.0)

**Status**: 🟡 IMPORTANT for PRD compliance
**Duration**: 1 week monitoring
**Owner**: PM + User
**Critical Principle**: Validate volume targets, not just profit targets

### Purpose

Verify that deployed bot achieves point farming goals (volume, trade frequency, ranking).

**Why This Phase Matters**:
- Profit-making strategy ≠ Point farming strategy
- Trend Following: Great for profit, poor for volume ($40K vs $1M target)
- Without validation: Miss point farming rewards entirely

### ✅ Monitoring Metrics

#### 0. Breakeven Trades: The Core Principle

**⚠️ CRITICAL**: Volume farming 성공의 핵심은 **무손실/약익절 일일 거래수 최대화**

**Why Breakeven Trades Matter**:
```yaml
loss_impact:
  - 손실 거래 1회 = 수익 거래 10-50회 상쇄
  - Example: -$100 loss requires 100 trades × $1 profit to recover
  - Volume farming: PnL보다 거래수 최대화가 목표

capital_preservation:
  - 무손실 거래 = 자본 보존 + volume 생성
  - $10K capital → 1000 breakeven trades = $10M volume
  - vs $10K capital → 10 trades with -5% loss = $9.5K capital (volume decreased)

compounding_effect:
  - Day 1: 100 trades, -$50 → Capital: $9,950
  - Day 2: 100 trades, -$50 → Capital: $9,900
  - Day 30: Capital depleted, volume stops ❌

  vs

  - Day 1-30: 100 trades/day, $0 P&L → Capital preserved
  - Month 2-12: Continue with same capital ✅
```

**How to Achieve Breakeven Trades**:

**⚠️ CRITICAL**: 각 전략마다 무손실 거래를 달성하는 메커니즘이 다릅니다. 전략별 핵심 원리를 이해하고 최적화해야 합니다.

**Market Making Approach**:
```yaml
spread_optimization:
  - Too tight (< 1 bp): High win rate but losses on adverse selection
  - Too wide (> 10 bp): No fills, no volume
  - Optimal: 2-5 bps depending on volatility

  calculation:
    bid = mid_price × (1 - spread/2)
    ask = mid_price × (1 + spread/2)
    profit_per_round_trip = spread - fees

inventory_management:
  - Max inventory skew: ±50% of position limit
  - Rebalance when: abs(long - short) > 0.5 × max_position
  - Avoid: One-sided inventory (exposure to adverse moves)

mid_price_accuracy:
  - Use: Volume-weighted mid-price (VWAP)
  - Update frequency: Every 100ms (WebSocket)
  - Avoid: Simple (bid + ask) / 2 (stale pricing)

example_config:
  spread_bps: 5  # 0.05%
  max_inventory: 0.5  # 50% skew
  position_size: $1000
  expected_pnl_per_trade: $0.50 (after fees)
  daily_trades: 100
  daily_pnl: $50 (1% capital preservation)
```

**MM 무손실 거래 상세 가이드**:
```yaml
핵심_원리:
  - Bid/Ask spread로 profit capture
  - Mid-price tracking으로 adverse selection 방지
  - Inventory management로 directional risk 제거

단계별_최적화:
  step_1_spread_calibration:
    문제: "Spread 너무 좁으면 → Adverse selection loss"
    문제: "Spread 너무 넓으면 → 체결 안됨, volume 없음"
    해결: "Historical volatility 기반 동적 spread"
    공식: "optimal_spread = volatility × multiplier + base_spread"
    예시: "BTC 변동성 2% → spread = 2% × 0.5 + 0.02% = 1.02%"

  step_2_mid_price_accuracy:
    문제: "Simple (bid+ask)/2 → Stale pricing, loss"
    해결: "VWAP (Volume-Weighted Average Price) 사용"
    구현: "WebSocket ticker stream → 100ms update"
    검증: "Backtest로 mid-price vs actual execution 비교"

  step_3_inventory_management:
    문제: "Long skew → Price drop 손실"
    문제: "Short skew → Price rise 손실"
    해결: "±50% max skew, 초과 시 rebalance"
    예시: "Max position $10K, Long $7K Short $3K → $2K rebalance 필요"

실전_체크리스트:
  - [ ] Spread가 fee의 2배 이상인가? (최소 수익 확보)
  - [ ] Mid-price update가 100ms 이내인가? (WebSocket 필수)
  - [ ] Inventory skew가 실시간 모니터링되는가?
  - [ ] Adverse selection loss가 spread의 50% 이하인가?
  - [ ] 일일 win rate가 70% 이상인가?
```

**Grid Trading Approach**:
```yaml
grid_spacing_optimization:
  - Volatility-based: spacing = ATR × multiplier
  - Too tight: Over-trading, high fees
  - Too wide: Low volume, missed opportunities
  - Optimal: 0.2-0.5% for BTC, 0.5-1% for ETH

range_setting:
  - Support/Resistance analysis
  - Bollinger Bands (2 std dev)
  - Avoid: Range too wide (no fills)

rebalancing_frequency:
  - Price moves outside range: Reset grid
  - Profit target hit: Take profit, reset
  - Loss threshold: Stop and reassess

example_config:
  grid_levels: 20
  grid_spacing: 0.3%  # $100K BTC: $300 per level
  range: $98K - $102K (4% range)
  position_per_level: $500
  expected_fills: 10-30/day
  pnl_per_fill: $1.50 (after fees)
```

**Grid 무손실 거래 상세 가이드**:
```yaml
핵심_원리:
  - Range-bound 시장에서 buy low, sell high 반복
  - Grid 간격이 profit margin 결정
  - Mean-reversion 가정 (가격은 평균으로 회귀)

단계별_최적화:
  step_1_range_setting:
    문제: "Range 너무 넓으면 → 체결 안됨"
    문제: "Range 너무 좁으면 → Breakout 손실"
    해결: "Bollinger Bands (2 std dev) 또는 Support/Resistance"
    예시: "BTC $100K ± 2% = $98K-$102K range"
    검증: "Historical data로 range 이탈 빈도 확인 (<20%)"

  step_2_grid_spacing:
    문제: "간격 너무 좁으면 → Over-trading, 높은 수수료"
    문제: "간격 너무 넓으면 → 체결 빈도 낮음"
    해결: "ATR (Average True Range) × multiplier"
    공식: "spacing = ATR(14) × 0.5"
    예시: "BTC ATR $600 → spacing = $300 (0.3%)"

  step_3_rebalancing:
    문제: "가격이 range 이탈 → 한쪽 포지션만 남음"
    해결: "Range 이탈 시 즉시 grid reset"
    트리거: "Price > upper_bound × 1.02 OR Price < lower_bound × 0.98"
    액션: "모든 주문 취소 → 새 range 설정 → grid 재배치"

실전_체크리스트:
  - [ ] Grid spacing이 fee의 3배 이상인가?
  - [ ] Range가 최근 30일 변동성 기반인가?
  - [ ] Range 이탈 빈도가 20% 이하인가? (백테스트)
  - [ ] 일일 체결 횟수가 10회 이상인가?
  - [ ] Grid reset 로직이 자동화되어 있는가?
```

**Delta Neutral Approach**:

**Funding Sniping**:
```yaml
funding_threshold:
  - Minimum rate differential: 0.01% (1% annualized)
  - Optimal entry: 30 min before funding
  - Optimal exit: 5 min after funding

hedge_ratio_accuracy:
  - Target: 1:1 delta neutral
  - Tolerance: ±2% delta drift
  - Monitor: Real-time position tracking

example:
  position_size: $10K long (Apex) + $10K short (Paradex)
  funding_collected: $10 (0.1%)
  fees_paid: $2 (taker fees)
  net_profit: $8 per round
  frequency: 3x/day = $24/day
```

**Funding Sniping DN 무손실 거래 상세 가이드**:
```yaml
핵심_원리:
  - 2개 DEX 간 funding rate 차이로 profit
  - Market-neutral이므로 가격 변동 영향 없음
  - Funding interval (8h)마다 수익 발생

단계별_최적화:
  step_1_funding_monitoring:
    대상: "Binance, OKX, Apex, Paradex, dYdX"
    지표: "Funding rate (8h 기준)"
    임계값: "Differential > 0.01% (연 1% 이상)"
    도구: "API polling 1분마다 or WebSocket stream"

  step_2_entry_timing:
    최적: "Funding 30분 전 포지션 진입"
    이유: "너무 일찍 → 가격 변동 노출, 너무 늦으면 → 체결 못함"
    검증: "Slippage < 0.005% (체결 품질 확인)"

  step_3_hedge_accuracy:
    목표: "Delta = 0 (완전 중립)"
    허용: "Delta drift < 2%"
    모니터링: "실시간 position tracking"
    조정: "Drift > 2% 시 즉시 rebalance"

  step_4_exit_timing:
    최적: "Funding 후 5분 이내 청산"
    이유: "Funding 받으면 목적 달성, 더 보유 = 불필요한 위험"
    조건: "Slippage 낮을 때만 청산 (급등락 시 대기)"

실전_체크리스트:
  - [ ] 2개 이상 DEX에서 funding rate API 연동 완료?
  - [ ] Hedge ratio가 자동 계산되는가?
  - [ ] Delta drift 모니터링이 실시간인가?
  - [ ] Entry/Exit slippage가 0.01% 이하인가?
  - [ ] Funding collection이 자동 확인되는가?
```

**Volume-Focused**:
```yaml
rebalancing_threshold:
  - Delta drift > 2%: Immediate rebalance
  - Time interval: Every 30 min (even if < 2%)
  - Result: 50-100 rebalances/day = 100-200 trades

spread_capture:
  - Buy at bid (DEX1), Sell at ask (DEX2)
  - Profit: Spread - fees
  - Optimal: Maker orders only (0% fee or rebate)

example:
  rebalance_frequency: 100/day
  profit_per_rebalance: $0.20
  daily_profit: $20
  monthly_volume: $2M
```

**Volume-Focused DN 무손실 거래 상세 가이드**:
```yaml
핵심_원리:
  - 지속적인 delta-neutral 유지로 고빈도 거래
  - Rebalancing마다 spread capture
  - Maker rebate 최대 활용

단계별_최적화:
  step_1_rebalance_trigger:
    방법_1_delta_drift: "abs(delta) > 2% → rebalance"
    방법_2_time_interval: "30분마다 무조건 rebalance"
    방법_3_hybrid: "Delta > 2% OR 30min 중 먼저 도달"
    권장: "Hybrid (volume 최대화)"

  step_2_spread_capture:
    전략: "Buy at bid (DEX1), Sell at ask (DEX2)"
    조건: "Both maker orders (0% fee or rebate)"
    예시: "BTC $100K bid, $100.05K ask → $50 profit per $10K"
    최적화: "Post-only orders로 maker 보장"

  step_3_frequency_optimization:
    Target: "100-200 rebalances/day"
    실현: "Delta 2% threshold + 30min interval"
    검증: "Trade log 분석 (실제 빈도 vs target)"
    조정: "Threshold 조정 (1%-3% 테스트)"

실전_체크리스트:
  - [ ] Rebalancing이 자동화되어 있는가?
  - [ ] Maker ratio가 90% 이상인가? (post-only 필수)
  - [ ] 일일 rebalance 횟수가 50회 이상인가?
  - [ ] Spread capture가 fee보다 큰가?
  - [ ] Delta monitoring이 실시간인가?
```

**Success Metrics**:
```yaml
target_metrics:
  win_rate: > 80% (breakeven or profit)
  avg_trade_pnl: > $0 (even $0.01 acceptable)
  daily_capital_change: -1% to +1% (preservation)
  volume_per_dollar: > $100 volume per $1 capital

red_flags:
  - Daily loss > $50 (re-evaluate strategy)
  - Win rate < 70% (spread/grid too tight)
  - Capital depletion > 5%/week (unsustainable)
```

---

#### 1. Volume Tracking

**Daily Volume**:
```python
def calculate_daily_volume(trades):
    """Sum all trade volumes for the day"""
    total = sum(trade['price'] * trade['size'] for trade in trades)
    return total

# Target:
# - MM strategy: $30K-40K/day → $1M/month ✅
# - DN strategy: $10K-20K/day → $300K-500K/month ✅
# - Trend: $1K-10K/day → $40K-300K/month ⚠️
```

**Monthly Projection**:
```python
def project_monthly_volume(daily_avg, days_elapsed):
    """Project full month volume from partial data"""
    monthly_projection = daily_avg * 30
    return monthly_projection

# Example:
# Day 3: $35K/day avg → $1.05M/month projected ✅
# Day 7: $8K/day avg → $240K/month projected ⚠️
```

#### 2. Trade Frequency

**Trades Per Day**:
```yaml
market_making:
  target: 50-100 trades/day
  acceptable: > 30 trades/day
  red_flag: < 20 trades/day

delta_neutral:
  target: 3 trades/day (funding intervals)
  acceptable: 2-4 trades/day
  red_flag: < 1 trade/day

grid_trading:
  target: 10-30 trades/day
  acceptable: > 5 trades/day
  red_flag: < 3 trades/day

trend_following:
  target: 1-10 trades/day
  acceptable: Any (strategy-dependent)
  note: NOT suitable for volume farming
```

**Alert Triggers**:
```python
def check_trade_frequency(trades_today, strategy_type):
    """Alert if trade frequency below threshold"""
    thresholds = {
        'MM': 30,
        'DN': 1,
        'Grid': 5,
        'Trend': 1
    }

    if trades_today < thresholds[strategy_type]:
        send_alert(f"⚠️ Low trade freq: {trades_today} < {thresholds[strategy_type]}")
        return False
    return True
```

#### 3. Point Ranking Estimate

**Ranking Calculation** (if DEX provides leaderboard):
```python
def estimate_ranking(my_volume, total_participants):
    """Estimate ranking based on volume"""
    # Example: Apex Pro leaderboard shows top 100
    # Your volume: $35K/day = $1.05M/month
    # Top 1% volume threshold: ~$500K/month
    # → Estimated rank: Top 0.5% ✅

    if my_volume > top_1_percent_threshold:
        return "Top 1%"
    elif my_volume > top_5_percent_threshold:
        return "Top 5%"
    else:
        return "Below Top 5%"
```

#### 4. Fee Optimization

**Maker vs Taker Ratio**:
```yaml
target_ratio:
  maker_rebate_dex: 90% maker, 10% taker
  zero_maker_fee: 70% maker, 30% taker
  positive_maker_fee: 50% maker, 50% taker

tracking:
  maker_orders: count + volume
  taker_orders: count + volume
  maker_ratio: maker_volume / total_volume
```

**Fee Impact Analysis**:
```python
def calculate_fee_impact(trades, fee_structure):
    """Calculate total fees paid/earned"""
    maker_fees = sum(
        trade['volume'] * fee_structure['maker']
        for trade in trades if trade['is_maker']
    )

    taker_fees = sum(
        trade['volume'] * fee_structure['taker']
        for trade in trades if not trade['is_maker']
    )

    total_fees = maker_fees + taker_fees

    # Example:
    # Apex MM: $1M volume, 100% maker, 0% fee = $0 ✅
    # Paradex DN: $300K volume, 90% maker, -0.005% = -$13.50 (rebate!) ✅
    # Trend: $100K volume, 30% maker, 0.025% taker = $17.50 cost ⚠️

    return total_fees
```

### 📋 Week 1 Validation Checklist

**Day 1-3: Initial Assessment**
- [ ] Measure daily volume
- [ ] Count trades per day
- [ ] Check maker/taker ratio
- [ ] Project monthly volume
- [ ] Compare vs target ($1M for volume DEXes)

**Day 4-7: Trend Analysis**
- [ ] Calculate 7-day average volume
- [ ] Identify volume patterns (weekday vs weekend)
- [ ] Analyze trade distribution (time of day)
- [ ] Estimate point ranking
- [ ] Decide: GO for full capital OR adjust strategy

### 🎯 Success Criteria

**Volume-Based DEXes** (Apex, dYdX, GMX):
- ✅ Daily volume ≥ $30K/day
- ✅ Monthly projection ≥ $1M
- ✅ Trade frequency ≥ 30/day (MM) or ≥ 5/day (Grid)
- ✅ Estimated ranking: Top 1-5%

**Maker Rebate DEXes** (Paradex, GMX):
- ✅ Daily volume ≥ $10K/day
- ✅ Maker ratio ≥ 80%
- ✅ Positive rebate income (fees < 0)
- ✅ Trade frequency: 3/day (DN)

**Sharpe Bonus DEXes** (Lighter, Hyperliquid):
- ✅ Sharpe ratio ≥ 2.0 (backtest 70%+ achieved)
- ✅ Max drawdown ≤ 120% of backtest
- ✅ Trade frequency: 1-10/day (acceptable)

### ⚠️ Adjustment Triggers

**Trigger 1: Volume Below Target**
```yaml
problem:
  daily_volume: < $20K/day
  monthly_projection: < $600K

actions:
  1. Increase position sizes (2x)
  2. Add more coins (BTC + ETH + SOL)
  3. Consider switching to MM strategy
  4. Test higher leverage (2x → 3x)
```

**Trigger 2: Low Trade Frequency**
```yaml
problem:
  trades_per_day: < 10 (for MM/Grid)

actions:
  1. Tighten grid spacing (Grid)
  2. Reduce spread (MM)
  3. Check liquidity availability
  4. Verify order execution working
```

**Trigger 3: High Taker Ratio**
```yaml
problem:
  taker_ratio: > 50% (for maker rebate DEX)

actions:
  1. Switch to limit orders only
  2. Increase order placement frequency
  3. Improve mid-price calculation
  4. Reduce urgency (accept slower fills)
```

### Real Example: Apex Week 1

**Day 1 Results**:
```yaml
strategy: Trend Following (BTC 1h, ETH 30m)
daily_volume: $2,500
trades: 3
monthly_projection: $75,000
gap: 92.5% below $1M target ❌
```

**Adjustment Decision**:
```yaml
problem: Trend strategy unsuitable for volume farming
decision: Switch to MM strategy

implementation:
  - Phase 1.5: Select MM strategy
  - Phase 2: Backtest MM parameters
  - Phase 4: Implement MM bot
  - Phase 6.5: Re-validate with MM

expected_result:
  daily_volume: $35K
  trades: 60-80/day
  monthly_projection: $1.05M ✅
```

### 📊 Dashboard Metrics

**Telegram Notifications** (Every 10 min while position open):
```
📊 Point Farming Status

💰 Volume (24h): $32,450 / $33,333 target
📈 Projection: $973,500/month (97% of $1M)
⚡ Trades Today: 67 / 50+ target
📊 Maker Ratio: 78% (target: 70%+)
🏆 Est. Ranking: Top 1%

Status: ✅ ON TRACK
```

**Web Dashboard** (Optional):
```
Metrics to Display:
- Volume: Daily, weekly, monthly
- Trade count: Hourly breakdown
- Maker/Taker split: Pie chart
- Fee impact: Cumulative graph
- Ranking estimate: Percentile gauge
- Target achievement: Progress bars
```

### 📋 Deliverables

1. **Week 1 Report**
   - Daily volume data (7 days)
   - Trade frequency analysis
   - Maker/taker ratio
   - Point ranking estimate
   - GO/NO-GO decision for full capital

2. **Strategy Adjustment Plan** (if needed)
   - Identified gaps
   - Proposed changes
   - Expected impact
   - Timeline to implement

3. **Scaling Recommendation**
   - Current capital: $X
   - Recommended scale: $Y
   - Risk assessment
   - Expected monthly volume at scale

### 🎯 Phase 6.5 Outcome

**GO Decision Criteria**:
- ✅ Volume ≥ 80% of target
- ✅ Trade frequency meeting expectations
- ✅ No critical issues discovered
- → Proceed to full capital deployment

**ADJUST Decision Criteria**:
- ⚠️ Volume 50-80% of target
- ⚠️ Strategy tweaks needed
- → Implement adjustments, re-validate

**NO-GO Decision Criteria**:
- ❌ Volume < 50% of target
- ❌ Fundamental strategy mismatch
- → Return to Phase 1.5, select different strategy

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



---

## Phase 9: Multi-DEX Scaling (NEW in v2.0)

**Status**: 🟢 RECOMMENDED for 20-DEX portfolio
**Duration**: 1 week per 5 DEXes
**Owner**: Architect
**Critical Principle**: Automate Phase 0, parallelize testing

### Purpose

Scale from single DEX to 20+ DEX portfolio with systematic batch testing.

**Why This Phase Matters**:
- Single DEX: 3-6 hours per integration (manual)
- 20 DEXes: 60-120 hours (sequential) = 2-3 weeks
- With automation: 15-20 hours (parallel) = 2-3 days ✅

### ✅ Batch Testing Strategy

#### Batch Structure

**Batch 1: Priority 1 DEXes** (Week 1)
```yaml
dexes: [Apex, Paradex]
characteristics:
  - Phase: initial/extreme_early
  - Point programs: Active
  - Capital allocation: 10% each
  - Strategy: MM (Apex), DN (Paradex)

timeline:
  monday: Phase 0 testing (both DEXes parallel)
  tuesday: Implementation (port from Apex template)
  wednesday: QA testing
  thursday: Deploy Stage 1 ($100 each)
  friday: Phase 6.5 validation
```

**Batch 2: Priority 2 DEXes** (Week 2)
```yaml
dexes: [Lighter, Backpack, Aster]
capital_allocation: 5% each
expected_phase_0_success: 60% (3/5 may fail)
```

**Batch 3-6: Scale to 20** (Weeks 3-6)
```yaml
batch_size: 5 DEXes per week
total_weeks: 4-6 weeks
success_rate: 50-70%
final_count: 10-15 operational DEXes
```

### 🔧 Automation Framework

#### Automated Phase 0 Test Suite

**Script: automated_phase0.py**
```python
class AutomatedPhase0:
    """
    Automated Phase 0 testing for multiple DEXes in parallel
    """

    def __init__(self, dex_configs):
        self.dex_configs = dex_configs
        self.results = {}

    def run_all_tests_parallel(self):
        """Test all DEXes in parallel"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.test_single_dex, name, config): name
                for name, config in self.dex_configs.items()
            }

            for future in as_completed(futures):
                dex_name = futures[future]
                try:
                    result = future.result()
                    self.results[dex_name] = result
                except Exception as e:
                    self.results[dex_name] = {'status': 'FAILED', 'error': str(e)}

        return self.results

    def test_single_dex(self, dex_name, config):
        """Run Phase 0 checkpoints for single DEX"""
        results = {
            'dex': dex_name,
            'checkpoint1': self.checkpoint1_basic(config),
            'checkpoint2': self.checkpoint2_orders(config),
            'checkpoint3': self.checkpoint3_realtime(config),
            'decision': None,
            'quirks': []
        }

        # GO/NO-GO decision
        if all([results['checkpoint1']['passed'],
                results['checkpoint2']['passed']]):
            results['decision'] = 'GO'
        else:
            results['decision'] = 'NO-GO'

        return results

    def checkpoint1_basic(self, config):
        """Phase 0 Checkpoint 1: Basic connection"""
        try:
            client = create_dex_client(config)
            client.authenticate()
            balance = client.get_balance()
            ticker = client.get_ticker('BTC-USDT')

            return {
                'passed': True,
                'balance': balance,
                'ticker': ticker['price']
            }
        except Exception as e:
            return {
                'passed': False,
                'error': str(e)
            }

    def checkpoint2_orders(self, config):
        """Phase 0 Checkpoint 2: Order execution"""
        try:
            client = create_dex_client(config)

            # Small test order ($10-30)
            test_order = client.create_market_order(
                symbol='BTC-USDT',
                side='BUY',
                size=0.0001  # ~$10
            )

            # Close position
            close_order = client.create_market_order(
                symbol='BTC-USDT',
                side='SELL',
                size=0.0001
            )

            return {
                'passed': True,
                'test_order_id': test_order['id'],
                'pnl': close_order['pnl']
            }
        except Exception as e:
            return {
                'passed': False,
                'error': str(e)
            }

    def checkpoint3_realtime(self, config):
        """Phase 0 Checkpoint 3: WebSocket test"""
        try:
            client = create_dex_client(config)
            ws_working = client.test_websocket(['BTC-USDT'])

            return {
                'passed': ws_working,
                'architecture': 'Hybrid' if ws_working else 'REST-only'
            }
        except Exception as e:
            return {
                'passed': False,
                'architecture': 'REST-only',
                'error': str(e)
            }
```

**Usage**:
```python
# Load DEX configurations
dex_configs = load_dex_configs('dex_config.yaml')

# Run automated Phase 0 for 5 DEXes
tester = AutomatedPhase0(dex_configs)
results = tester.run_all_tests_parallel()

# Results:
# {
#   'apex': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...},
#   'paradex': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...},
#   'lighter': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...},
#   'backpack': {'decision': 'NO-GO', 'checkpoint1': {'passed': False}, ...},
#   'aster': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...}
# }

# Time: 15-30 minutes (parallel) vs 3-4 hours (sequential)
```

### 📊 Capital Allocation Strategy

#### Portfolio Structure

**Total Capital**: $200,000 (example)

**Tier 1: Priority DEXes** (30% = $60K)
```yaml
apex:
  allocation: 10% ($20K)
  strategy: Market Making
  expected_volume: $1M/month
  expected_return: 2-5%

paradex:
  allocation: 10% ($20K)
  strategy: Delta Neutral
  expected_volume: $500K/month
  expected_return: 1.5-3%

lighter:
  allocation: 10% ($20K)
  strategy: Trend Following
  expected_volume: $200K/month
  expected_return: 15-25%
```

**Tier 2: Growth DEXes** (40% = $80K)
```yaml
allocation: 5% each ($10K per DEX)
count: 8 DEXes
strategy: Mix (MM, DN, Grid)
expected_volume: $3-5M total
expected_return: 5-15%
```

**Tier 3: Experimental** (20% = $40K)
```yaml
allocation: 2-3% each ($4-6K per DEX)
count: 7-10 DEXes
strategy: Test new approaches
expected_volume: $1-2M total
expected_return: 0-10% (learning focus)
```

**Reserve** (10% = $20K)
```yaml
purpose: Emergency fund, new opportunities
allocation: Unallocated
```

### 🎯 Portfolio Risk Management

#### Diversification Rules

**1. DEX Phase Diversification**
```yaml
extreme_early: Max 20% of capital
initial: Max 40% of capital
mature: Unlimited (stable platforms)

rationale: Newer DEXes higher risk of rug pull, API changes
```

**2. Strategy Diversification**
```yaml
market_making: 30-40%
delta_neutral: 20-30%
trend_following: 15-25%
grid_trading: 10-20%

rationale: Uncorrelated strategies reduce portfolio volatility
```

**3. Geographic Diversification**
```yaml
arbitrum_dexes: Max 30%
optimism_dexes: Max 30%
polygon_dexes: Max 20%
other_chains: Unlimited

rationale: Chain-specific risks (downtime, congestion)
```

#### Portfolio-Wide Limits

**Maximum Drawdown**:
```python
def check_portfolio_drawdown():
    """Kill switch if portfolio MDD > 15%"""
    current_nav = calculate_portfolio_nav()
    all_time_high = get_all_time_high()

    drawdown = (all_time_high - current_nav) / all_time_high

    if drawdown > 0.15:  # 15% portfolio MDD
        emergency_shutdown_all_dexes()
        send_alert("🚨 Portfolio MDD > 15%! All bots stopped.")
```

**Daily Loss Limit**:
```python
def check_daily_loss():
    """Pause trading if daily loss > $2,000"""
    today_pnl = sum(dex.get_today_pnl() for dex in active_dexes)

    if today_pnl < -2000:
        pause_all_trading()
        send_alert("⚠️ Daily loss limit hit: ${today_pnl}")
```

### 📋 Week-by-Week Roadmap

**Week 1: Batch 1 (Apex, Paradex)**
```yaml
monday:
  - Automated Phase 0: Both DEXes ✅
  - Results: Apex GO, Paradex GO

tuesday:
  - Port Apex code to Paradex
  - Implement DN strategy for Paradex
  - QA testing

wednesday-friday:
  - Deploy Stage 1 ($100 each)
  - Phase 6.5 validation
  - Scale to full capital if validated
```

**Week 2: Batch 2 (Lighter, Backpack, Aster)**
```yaml
monday:
  - Automated Phase 0: 3 DEXes parallel
  - Results: Lighter GO, Backpack NO-GO, Aster GO

tuesday-thursday:
  - Implement Lighter (Trend), Aster (MM)
  - Skip Backpack (API issues)
  - QA + Deploy

friday:
  - Phase 6.5 validation
  - Portfolio review
```

**Weeks 3-6: Scale to 20 DEXes**
```yaml
batch_3: Hyperliquid, dYdX, GMX, Kwenta, Gains
batch_4: Vela, Level, MUX, Vertex, Rage Trade
batch_5: Polynomial, Pika, SynFutures, Tigris, Equation
batch_6: (Future DEXes as they launch)
```

### 🔧 Portfolio Management Tools

**Multi-DEX Orchestrator**
```python
class DexPortfolioManager:
    """Manage 20+ DEXes with unified interface"""

    def __init__(self, total_capital):
        self.total_capital = total_capital
        self.active_dexes = {}
        self.performance_tracker = PerformanceTracker()

    def initialize_dex(self, dex_name, config):
        """Add new DEX to portfolio"""
        capital = self.total_capital * config['allocation']
        strategy = select_strategy(config)  # Phase 1.5

        self.active_dexes[dex_name] = {
            'client': create_dex_client(config),
            'strategy': strategy,
            'capital': capital,
            'bot': TradingBot(strategy, capital)
        }

    def get_portfolio_metrics(self):
        """Aggregate metrics across all DEXes"""
        return {
            'total_pnl': sum(dex['bot'].pnl for dex in self.active_dexes.values()),
            'total_volume': sum(dex['bot'].volume for dex in self.active_dexes.values()),
            'total_trades': sum(dex['bot'].trades for dex in self.active_dexes.values()),
            'roi': self.calculate_portfolio_roi(),
            'sharpe': self.calculate_portfolio_sharpe(),
            'max_drawdown': self.calculate_max_drawdown()
        }

    def rebalance_capital(self):
        """Rebalance based on performance"""
        # TODO: Move capital from underperforming to outperforming DEXes
        pass
```

### 📊 Success Metrics

**After Week 1** (2 DEXes):
- ✅ 2 DEXes operational
- ✅ $40K deployed
- ✅ $1.5M+ monthly volume projected
- ✅ Portfolio PnL positive

**After Week 2** (4 DEXes):
- ✅ 4 DEXes operational
- ✅ $60K deployed
- ✅ $3M+ monthly volume projected

**After Week 6** (10-15 DEXes):
- ✅ 10-15 DEXes operational
- ✅ $150K-180K deployed
- ✅ $10M+ monthly volume
- ✅ Portfolio ROI 15-25% monthly
- ✅ Max drawdown < 15%

### 📋 Deliverables

1. **Automated Phase 0 Suite**
   - Python script for parallel testing
   - Results parser and reporting
   - GO/NO-GO decision automation

2. **Multi-DEX Configuration File**
   - YAML with 20 DEX configs
   - Capital allocation strategy
   - Risk limits per DEX

3. **Portfolio Dashboard**
   - Aggregate P&L across all DEXes
   - Volume tracking per DEX
   - Risk metrics (drawdown, exposure)
   - Strategy distribution

4. **Scaling Report**
   - DEXes tested: 20
   - DEXes operational: 10-15
   - Success rate: 50-70%
   - Total volume: $10M+/month
   - Portfolio ROI: 15-25%


---

## 🔄 Framework Updates

**Version History**:
- v0.1 (2025-11-08): Initial framework from Lighter experience
- v0.2 (2025-11-09): Added Phase 0 (learned from Lighter failure)
- v1.0 (2025-11-09): Extracted to common framework (proven with 2 DEXs)
- v2.0 (2025-11-09): Added Phase 1.5 (Strategy Selection), Phase 6.5 (Point Farming Validation), Phase 9 (Multi-DEX Scaling)
- v2.1 (2025-11-09): Added DN strategy 2 approaches, Lighter API constraint, Breakeven trades methodology
- v2.2 (2025-11-09): Added DN popularity explanation, MM research process, detailed breakeven guides, Lighter completion criteria (85% → 95%+ reflection)

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
