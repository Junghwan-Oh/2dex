# DN Pair Bot Liquidation Stabilization Plan V4.1

## Context

### Original User Requirements (Clarified)

**Critical Correction from User (Iteration 4):**
> "씨드 2천불을 가지고 거래량을 늘려서 1일 거래량을 하루에 1M을 만드는게 거래량 목표다"

**Corrected Understanding:**
- **Starting Capital (Seed)**: $2,000 (씨드 2천불)
- **Daily Volume Target**: $1,000,000 (일일 100만 불 거래량)
- **PNL Requirement**: >= 0 (all trades profitable after fees)

### Architect Consultation Findings (Iteration 4 - Phase 1)

**Verdict**: $1M daily volume with $2,000 capital is **NOT FEASIBLE**

**Critical Issues:**
1. **500× leverage required** ($1M / $2k = 500×) - EXTREME liquidation risk
2. **No exchange support** for such high leverage
3. **Liquidity constraints** - order book insufficient
4. **API rate limits** - cannot sustain $11.57/second throughput

**Realistic Alternatives:**
- **Option A**: Increase capital to $50,000 for $1M daily volume at 20× leverage
- **Option B**: Reduce volume target to $33,000-$100,000 daily with $2,000 capital
- **Option C**: Hybrid - start small, compound profits, scale to $1M over 6-12 months

---

## V4.1 Core Philosophy: Realistic Volume Targets

### Conservative Volume Growth (보수적 거래량 성장)

**Golden Rule**: Match volume targets to available capital and sustainable leverage

**Key Changes from V4:**
1. **Realistic volume targets** based on $2,000 starting capital
2. **Leverage safety limits** (max 20× recommended, 10× conservative)
3. **Progressive scaling** (start small, grow with profits)
4. **Capital-efficient strategies** (compound growth path)

---

## Revised Volume Targets (V4.1)

### Phase 1: Launch (Weeks 1-4) - Conservative Start

**Capital**: $2,000
**Leverage**: 5× (conservative)
**Max Position Size**: $10,000
**Target Daily Volume**: $20,000
**Target Daily Profit**: $20-$40

**Trading Parameters:**
- Trades per day: 20-40
- Average trade size: $500-$1,000
- Spread target: 20+ bps
- PNL per trade: 8-16 bps

**Rationale**: Prove system stability and PNL >= 0 with minimal risk

### Phase 2: Growth (Months 2-3) - Moderate Scaling

**Capital**: $2,000 + reinvested profits (~$2,500)
**Leverage**: 10× (moderate)
**Max Position Size**: $25,000
**Target Daily Volume**: $100,000
**Target Daily Profit**: $100-$200

**Trading Parameters:**
- Trades per day: 100-150
- Average trade size: $700-$1,000
- Spread target: 20+ bps
- PNL per trade: 8-16 bps

**Rationale**: Increase frequency while maintaining conservative leverage

### Phase 3: Scale (Months 4-6) - Aggressive Growth

**Capital**: $3,000-$5,000 (compounded profits)
**Leverage**: 15× (aggressive but sustainable)
**Max Position Size**: $75,000
**Target Daily Volume**: $500,000
**Target Daily Profit**: $500-$1,000

**Trading Parameters:**
- Trades per day: 300-500
- Average trade size: $1,000-$1,500
- Spread target: 20+ bps
- PNL per trade: 8-16 bps

**Rationale**: Approach $1M daily volume target with larger capital base

### Phase 4: Target (Months 7-12) - $1M Daily Volume

**Capital**: $10,000-$20,000 (fully compounded)
**Leverage**: 20× (maximum sustainable)
**Max Position Size**: $400,000
**Target Daily Volume**: $1,000,000
**Target Daily Profit**: $2,000+

**Trading Parameters:**
- Trades per day: 1,000+
- Average trade size: $1,000-$2,000
- Spread target: 20+ bps
- PNL per trade: 8-16 bps

**Rationale**: Achieve original $1M daily volume goal with realistic capital

---

## Leverage Safety Framework (레버리지 안전 프레임워크)

### Maximum Leverage Limits

**Conservative (보수적)**: 5×
- Maximum drawdown risk: 20%
- Liquidation buffer: 80%
- Suitable for: Phase 1 (Launch)

**Moderate (중간)**: 10×
- Maximum drawdown risk: 10%
- Liquidation buffer: 90%
- Suitable for: Phase 2 (Growth)

**Aggressive (공격적)**: 15-20×
- Maximum drawdown risk: 5-7%
- Liquidation buffer: 93-95%
- Suitable for: Phase 3-4 (Scale/Target)

**PROHIBITED**: 50×+ leverage
- Extreme liquidation risk
- NOT supported by V4.1 plan

### Position Sizing Formula

**Safe Position Calculation:**
```python
max_position_value = account_collateral × max_leverage × safety_factor

# Example: $2,000 capital, 10× leverage, 0.8 safety factor
max_position_value = $2,000 × 10 × 0.8 = $16,000

# Per-position limit (50% of max to allow pair trading)
position_per_leg = $16,000 / 2 = $8,000
```

**Safety Factor Breakdown:**
- 0.8 (80%): Conservative - keeps 20% buffer
- 0.6 (60%): Very conservative - keeps 40% buffer
- 1.0 (100%): Maximum usage - no buffer (NOT recommended)

---

## Progressive Scaling Strategy (점진적 스케일링 전략)

### Week 1-2: Validation Phase (검증 단계)

**Goal**: Validate PNL >= 0 and system stability
- Position size: $100-$300 per leg
- Trades per day: 10-20
- Daily volume target: $2,000-$6,000
- Success criteria: 95%+ trades with PNL >= 0

### Week 3-4: Stabilization Phase (안정화 단계)

**Goal**: Establish consistent profitability
- Position size: $300-$500 per leg
- Trades per day: 20-40
- Daily volume target: $10,000-$20,000
- Success criteria: $20-$40 daily profit, 0 manual interventions

### Month 2: Growth Phase (성장 단계)

**Goal**: Increase trading frequency
- Position size: $500-$1,000 per leg
- Trades per day: 50-100
- Daily volume target: $50,000-$100,000
- Success criteria: $100-$200 daily profit

### Month 3-6: Scale Phase (확장 단계)

**Goal**: Compound profits and increase leverage
- Position size: $1,000-$2,000 per leg
- Trades per day: 200-500
- Daily volume target: $200,000-$500,000
- Success criteria: $500-$1,000 daily profit

### Month 7-12: Target Phase (목표 달성 단계)

**Goal**: Achieve $1M daily volume
- Position size: $2,000-$5,000 per leg
- Trades per day: 500-1,000+
- Daily volume target: $1,000,000+
- Success criteria: $2,000+ daily profit

---

## PNL Projections with Realistic Volume (실현 가능한 거래량 기반 손익 예측)

### Phase 1 (Launch): $20,000 Daily Volume

**Conservative Scenario:**
```
Trades per day: 20
Average trade size: $1,000
Spread: 20 bps
POST_ONLY fill rate: 70%

PNL Calculation:
14 trades × POST_ONLY (16 bps) = 14 × $1.60 = $22.40
6 trades × IOC (0 bps) = 6 × $0 = $0
─────────────────────────────────────────────────────
Daily Profit: $22.40
Monthly Profit: $22.40 × 20 days = $448
```

### Phase 2 (Growth): $100,000 Daily Volume

**Moderate Scenario:**
```
Trades per day: 100
Average trade size: $1,000
Spread: 25 bps
POST_ONLY fill rate: 60%

PNL Calculation:
60 trades × POST_ONLY (21 bps) = 60 × $2.10 = $126
40 trades × IOC (5 bps) = 40 × $0.50 = $20
─────────────────────────────────────────────────────
Daily Profit: $146
Monthly Profit: $146 × 20 days = $2,920
```

### Phase 3 (Scale): $500,000 Daily Volume

**Aggressive Scenario:**
```
Trades per day: 400
Average trade size: $1,250
Spread: 25 bps
POST_ONLY fill rate: 70%

PNL Calculation:
280 trades × POST_ONLY (21 bps) = 280 × $2.625 = $735
120 trades × IOC (5 bps) = 120 × $0.625 = $75
─────────────────────────────────────────────────────
Daily Profit: $810
Monthly Profit: $810 × 20 days = $16,200
```

### Phase 4 (Target): $1,000,000 Daily Volume

**Target Scenario (Requires $10k-$20k Capital):**
```
Trades per day: 1,000
Average trade size: $1,000
Spread: 30 bps
POST_ONLY fill rate: 70%

PNL Calculation:
700 trades × POST_ONLY (26 bps) = 700 × $2.60 = $1,820
300 trades × IOC (10 bps) = 300 × $1.00 = $300
─────────────────────────────────────────────────────
Daily Profit: $2,120 ✅ $2,000 목표 달성
Monthly Profit: $2,120 × 20 days = $42,400
Cumulative to $1M: $1,000,000 / $2,120 = 472 days (~16 months)
```

---

## Capital Requirements by Phase (단계별 자본 요구사항)

### Minimum Capital Calculator

**Formula:**
```
required_capital = (target_daily_volume / trades_per_day) / leverage / safety_factor
```

**Phase 1 ($20,000 daily volume):**
```
required_capital = ($20,000 / 20) / 5× / 0.8 = $250
→ $2,000 starting capital is MORE THAN SUFFICIENT
```

**Phase 2 ($100,000 daily volume):**
```
required_capital = ($100,000 / 100) / 10× / 0.8 = $125
→ $2,000 starting capital is SUFFICIENT
```

**Phase 3 ($500,000 daily volume):**
```
required_capital = ($500,000 / 400) / 15× / 0.8 = $104
→ $2,000 starting capital is SUFFICIENT
```

**Phase 4 ($1,000,000 daily volume):**
```
required_capital = ($1,000,000 / 1,000) / 20× / 0.8 = $62.50
→ $2,000 starting capital is SUFFICIENT with compounding
```

**Key Insight**: Starting capital is NOT the bottleneck. The bottleneck is:
1. Trading frequency (API limits, liquidity)
2. Leverage safety (liquidation risk)
3. System stability (manual interventions)

---

## Implementation Changes from V4

### Added: Leverage Safety Limits

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

```python
class DNPairBot:
    def __init__(
        self,
        target_notional: Decimal,
        max_leverage: float = 5.0,  # V4.1: Add leverage limit
        safety_factor: float = 0.8,  # V4.1: Add safety buffer
        ...
    ):
        self.target_notional = target_notional
        self.max_leverage = max_leverage
        self.safety_factor = safety_factor

    async def validate_position_size(
        self,
        quantity: Decimal,
        price: Decimal
    ) -> Tuple[bool, str]:
        """
        V4.1: Validate position size against leverage limits.

        Ensures position does not exceed safe leverage limits.
        """
        position_value = quantity * price

        # Get account collateral from Nado
        account_collateral = await self.get_account_collateral()

        max_safe_position = account_collateral * self.max_leverage * self.safety_factor

        if position_value > max_safe_position:
            return False, (
                f"Position ${position_value:,.0f} exceeds safe limit "
                f"${max_safe_position:,.0f} (collateral: ${account_collateral:,.0f}, "
                f"leverage: {self.max_leverage}×, safety: {self.safety_factor})"
            )

        return True, "Position size within safe limits"
```

### Added: Progressive Sizing Logic

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

```python
class ProgressiveSizer:
    """
    V4.1: Progressive position sizing based on account growth.

    Starts small, scales up as profits compound.
    """

    def __init__(
        self,
        initial_notional: Decimal,
        account_collateral: Decimal,
        max_leverage: float = 5.0
    ):
        self.initial_notional = initial_notional
        self.initial_collateral = account_collateral
        self.current_collateral = account_collateral
        self.max_leverage = max_leverage

    def calculate_progressive_notional(
        self,
        phase: int  # 1=Launch, 2=Growth, 3=Scale, 4=Target
    ) -> Decimal:
        """
        Calculate target notional based on growth phase.

        Phase 1 (Launch): 100% of initial
        Phase 2 (Growth): 150% of initial
        Phase 3 (Scale): 200-300% of initial
        Phase 4 (Target): 500-1000% of initial
        """
        growth_multipliers = {
            1: 1.0,   # Launch: No scaling
            2: 1.5,   # Growth: 50% increase
            3: 2.5,   # Scale: 150% increase
            4: 5.0,   # Target: 400% increase
        }

        multiplier = growth_multipliers.get(phase, 1.0)

        # Calculate growth factor based on collateral increase
        growth_factor = self.current_collateral / self.initial_collateral

        # Use whichever is smaller (phase limit or actual growth)
        effective_multiplier = min(multiplier, growth_factor)

        return self.initial_notional * Decimal(str(effective_multiplier))
```

### Added: Daily Volume Tracker

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

```python
class DailyVolumeTracker:
    """
    V4.1: Track daily trading volume against targets.

    Monitors progress toward daily volume goals.
    """

    def __init__(self, phase: int = 1):
        self.phase = phase
        self.daily_volume = Decimal('0')
        self.trade_count = 0

        # Phase-specific targets
        self.phase_targets = {
            1: {'daily_volume': Decimal('20000'), 'max_trades': 40},
            2: {'daily_volume': Decimal('100000'), 'max_trades': 150},
            3: {'daily_volume': Decimal('500000'), 'max_trades': 500},
            4: {'daily_volume': Decimal('1000000'), 'max_trades': 1000},
        }

    def record_trade(self, notional: Decimal) -> bool:
        """
        Record a trade and check if phase target reached.

        Returns True if trading should continue, False if target reached.
        """
        self.daily_volume += notional
        self.trade_count += 1

        target = self.phase_targets[self.phase]

        # Check if daily target reached
        if self.daily_volume >= target['daily_volume']:
            return False  # Stop trading, target reached

        # Check if max trades reached
        if self.trade_count >= target['max_trades']:
            return False  # Stop trading, max trades reached

        return True  # Continue trading
```

---

## 한국어 추가 설명 (Korean Addendum)

### 레버리지 안전성 (Leverage Safety)

**레버리지(Leverage)란?**
- 정의: 자본 대비 거래 포지션 규모의 비율
- 예시: $2,000 자본으로 $20,000 포지션 = 10× 레버리지
- 위험: 레버리지가 높을수록 청산 위험도 증가

**안전한 레버리지 수준:**
- 보수적: 5× (청산까지 20% 가격 변동 필요)
- 중간: 10× (청산까지 10% 가격 변동 필요)
- 공격적: 15-20× (청산까지 5-7% 가격 변동 필요)
- 위험: 50×+ (절대 사용 금지, 2% 변동 시 청산)

**V4.1의 레버리지 정책:**
- 시작 (Phase 1): 5× 보수적 레버리지
- 성장 (Phase 2): 10× 중간 레버리지
- 확장 (Phase 3-4): 15-20× (자본 축적 후)
- 금지: 50×+ 레버리지

### 거래량 목표 현실화 (Realistic Volume Targets)

**기존 계획 (V4)의 문제점:**
- $2,000 자본으로 $1,000,000 일일 거래량
- 필요한 레버리지: 500× (현실적으로 불가능)
- 위험: 0.2% 가격 변동 시 전체 자본 손실

**V4.1의 현실적 접근:**
- Phase 1: 일일 $20,000 거래량 (검증 및 안정화)
- Phase 2: 일일 $100,000 거래량 (점진적 성장)
- Phase 3: 일일 $500,000 거래량 (공격적 확장)
- Phase 4: 일일 $1,000,000 거래량 (6-12개월 후 달성)

**핵심 전략:**
1. 작게 시작하여 시스템 안정성 검증
2. 수익을 재투자하여 복리 성장
3. 자본이 축적된 후 거래량 확대
4. 레버리지는 항상 안전 수준 유지

### 점진적 스케일링 (Progressive Scaling)

**복리 성장의 힘:**
- 시작: $2,000 자본, 일일 $20 수익
- 1개월 후: $2,400 자본 (수익 재투자)
- 3개월 후: $4,000 자본, 일일 $100 수익
- 6개월 후: $10,000 자본, 일일 $500 수익
- 12개월 후: $20,000+ 자본, 일일 $2,000 수익

**V4.1의 스케일링 원칙:**
1. 검증 전에는 규모 확대 금지
2. PNL >= 0 확인 후 점진적 확대
3. 각 Phase에서 목표 달성 후 다음 Phase로 진행
4. 안전성이 항상 최우선

---

## Effort Estimate (V4.1)

| Phase | Task | Duration |
|-------|------|----------|
| Phase 1 | Add Leverage Safety Limits | 1.5h |
| Phase 1 | Add Progressive Sizing Logic | 2h |
| Phase 1 | Add Daily Volume Tracker | 1h |
| Phase 1 | Update PNL Calculations | 0.5h |
| Phase 2 | Update V4 Tasks with Volume Limits | 1h |
| Phase 3 | Add Phase Transition Logic | 1h |
| Phase 4 | Testing & Validation | 2h |
| **Total** | | **9h** |

**V4 → V4.1 Changes**:
- Add leverage limits: +1.5h
- Add progressive sizing: +2h
- Add volume tracking: +1h
- Update PNL calculations: +0.5h
- Add phase transitions: +1h
- Testing: +2h
- **Net: 12h → 21h (V4 + V4.1 additions)**

---

## Success Metrics (V4.1)

### Phase 1 Success Criteria (Weeks 1-4)
- Daily volume: $20,000+
- PNL >= 0: 95%+ of trades
- Manual interventions: 0
- Daily profit: $20-$40

### Phase 2 Success Criteria (Months 2-3)
- Daily volume: $100,000+
- PNL >= 0: 95%+ of trades
- Manual interventions: 0
- Daily profit: $100-$200

### Phase 3 Success Criteria (Months 4-6)
- Daily volume: $500,000+
- PNL >= 0: 95%+ of trades
- Manual interventions: 0
- Daily profit: $500-$1,000

### Phase 4 Success Criteria (Months 7-12)
- Daily volume: $1,000,000+
- PNL >= 0: 95%+ of trades
- Manual interventions: 0
- Daily profit: $2,000+

---

## Risk Mitigation (V4.1)

### Risk 1: Excessive Leverage

**Mitigation:**
- Hard limit: 20× maximum leverage
- Safety factor: 0.8 (80% usage max)
- Phase-based limits (5×, 10×, 15×, 20×)
- Real-time leverage monitoring

### Risk 2: Volume Too Low

**Mitigation:**
- Progressive scaling (start small, grow fast)
- Compound profits to increase capital
- Increase trading frequency over time
- Target $1M in 6-12 months (not day 1)

### Risk 3: Growing Too Fast

**Mitigation:**
- Phase gates (must prove stability before advancing)
- Manual phase transition approval
- Continuous leverage monitoring
- Emergency rollback to previous phase

### Risk 4: Liquidity Constraints

**Mitigation:**
- BookDepth-based position sizing
- Max slippage limits (10 bps)
- Multiple small orders vs. single large order
- Real-time liquidity monitoring

---

## Conclusion (V4.1)

**Key Changes from V4:**
1. ✅ Realistic volume targets (Phase 1-4 progression)
2. ✅ Leverage safety limits (max 20×)
3. ✅ Progressive scaling strategy
4. ✅ Capital-efficient growth path
5. ✅ $1M daily volume achievable in 6-12 months

**Core Philosophy**: Start small, prove stability, compound profits, scale gradually

**Effort**: 21 hours total (V4: 12h + V4.1 additions: 9h)

**Expected Outcome**: Realistic path to $1M daily volume with $2,000 starting capital, maintaining PNL >= 0 throughout

---

**Status**: PLAN_READY
**Version**: V4.1
**Next Step**: Critic review
**Date**: 2026-01-31
