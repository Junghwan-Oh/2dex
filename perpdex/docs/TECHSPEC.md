# TECHSPEC.md - Volume Farming via Market Making
**기술 명세서 (Technical Specification)**

> "극초기 Perpetual DEX에서 학술적으로 검증된 전략으로 거래량을 극대화하여 에어드랍 포인트를 선점"

**Version**: 2.0
**Last Updated**: 2025-10-25
**Status**: Strategic Direction Approved
**Consensus**: All AI Models + Human Engineer

---

## 📚 Executive Summary

### 프로젝트 정의
**포인트 파밍을 위한 거래량 극대화 시스템**
- Perpetual DEX 에어드랍 포인트 선점
- 학술적으로 검증된 Market Making 전략 활용
- 극초기 DEX에서 씨드 희석 전 최대 포인트 확보

### 북극성 (North Star)
**"손실 없이 최대 거래량을 생성하여 극초기 DEX 포인트 파밍에서 상위 1% 진입"**

---

## 🎯 Goals & Non-Goals

### Goals (핵심 목표)

#### 1. 포인트 파밍 최적화
```
Primary Metric: 월 거래량
- Target: DEX당 $1M USD/월 (기본)
- Stretch: DEX당 $5-10M USD/월 (Top 50 진입)

Secondary Metric: 포인트 효율
- Target: 상위 1% 랭킹
- 극초기 진입 (씨드 희석 전)
```

#### 2. 손실 방지 (≥0% 수익)
```
Risk-First Philosophy:
- 거래 수익: ≥0% (손실만 없으면 성공)
- 포인트 가치: TBD (에어드랍 발표 후)
- 전체 수익 = 거래 수익 + 포인트 가치
```

#### 3. 극초기 DEX 선점
```
DEX Selection Criteria:
1. 프로젝트 단계: 극초기 > 초기 > 성숙기
2. API 제공: 필수 조건 (API 없으면 제외)
3. 수수료 구조: Maker Rebate 우선
4. 씨드 희석도: 경쟁자 수 / 총 씨드
```

### Non-Goals (하지 않을 것)

1. **수익 극대화** - 거래 수익은 부차적 목표
2. **완벽한 타이밍** - 거래량이 더 중요
3. **복잡한 전략** - 단순하고 검증된 전략 선호
4. **성숙한 DEX** - 이미 희석된 시장은 배제

---

## 🧠 Core Strategy: Avellaneda-Stoikov Market Making

### 왜 이 전략인가?

#### 학술적 검증
```
Paper: "High-frequency trading in a limit order book" (2008)
Authors: Marco Avellaneda, Sasha Stoikov
Validation: 백테스트 +0.20% 수익 (30일, 693 trades)
```

#### 전략 핵심 속성
1. **델타 뉴트럴**: 시장 방향성에 무관 (가격 리스크 제거)
2. **인벤토리 관리**: 포지션 불균형 자동 조정
3. **동적 스프레드**: 변동성/유동성에 적응
4. **시간 인식**: 종료 시점 리스크 관리

### 포인트 파밍 적합성

#### 거래량 극대화
```
High-Frequency Characteristics:
- 양방향 주문 (Bid + Ask)
- 짧은 보유 시간 (분 단위)
- 작은 스프레드 (0.01-0.05%)
- 높은 회전율 (15-25회/일)

결과:
- 월 거래 횟수: 450-750회
- 월 거래량: $1-5M (포지션 크기 조정 가능)
```

#### 손실 방지
```
Risk Management Built-in:
- 스프레드 수익: 매 거래마다 확보
- 포지션 제한: 불균형 자동 조정
- Stop-loss: 일일 손실 한도
- EOD 청산: 오버나잇 리스크 제거

예상 결과:
- 거래 수익: +0.15-0.30% (보수적)
- 최대 손실: -5% (일일 한도)
```

#### 수수료 최적화
```
Maker-Only Strategy:
- POST_ONLY 주문만 사용
- Taker 주문 금지 (수수료 높음)
- Maker Rebate DEX 우선 (Paradex -0.005%)

효과:
- Apex: 0% Maker Fee
- Paradex: -0.005% Rebate
- 순수수료: 거의 0 또는 음수 (수익)
```

### 전략 공식

```python
# Optimal Spread Calculation
base_spread = γσ²τ + (2/γ)ln(1 + γ/k)

# Inventory Skew Adjustment
bid_spread = base_spread × time_factor × (1 + position_skew)
ask_spread = base_spread × time_factor × (1 - position_skew)

# Parameters:
# γ (gamma) = 리스크 회피 계수 (0.01-1.0)
# σ (sigma) = 변동성 (annualized)
# τ (tau) = 남은 시간 (EOD까지)
# k (kappa) = 유동성 계수 (order book depth)
```

---

## 🏗️ System Architecture (High-Level)

### 핵심 컴포넌트

```
┌─────────────────────────────────────────────────────┐
│              VOLUME FARMING SYSTEM                   │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
    ▼                             ▼
┌────────────────┐        ┌────────────────┐
│  AVELLANEDA    │        │   VOLUME       │
│  MARKET MAKER  │◄──────►│   TRACKER      │
│                │        │                │
│ - Spread Calc  │        │ - $1M/월 목표  │
│ - Order Place  │        │ - 랭킹 모니터  │
│ - Inventory    │        │ - 진행률 추적  │
└────────┬───────┘        └────────────────┘
         │
         ▼
┌────────────────┐
│  RISK MANAGER  │
│                │
│ - P&L ≥ 0%     │
│ - Daily Loss   │
│ - Position     │
└────────────────┘
```

### 데이터 플로우

```
Market Data → Spread Calculation → Order Placement
                    ↓
            Inventory Check → Position Rebalance
                    ↓
            Fill Confirmation → Volume Recording
                    ↓
            P&L Tracking → Risk Check
                    ↓
    Monthly Volume Target → Ranking Update
```

---

## 📊 Target DEX Portfolio

### Phase 1: Apex Pro + Paradex (현재)

#### Apex Pro
```
Status: 극초기 (메인넷 6개월)
API: ✅ REST + WebSocket + Python SDK
Fee Structure:
  - Maker: 0%
  - Taker: 0.025%
Strategy: High-Frequency Market Making
Target Volume: $1M/월
```

#### Paradex
```
Status: 초기 (Paradigm 백업)
API: ✅ REST + WebSocket
Fee Structure:
  - Maker Rebate: -0.005% (수익!)
  - Taker: 0.03%
Strategy: Delta Neutral + Funding Arbitrage
Target Volume: $1M/월
```

### Phase 2: Expansion (3-5개 DEX)
```
Candidates:
- Lighter
- Backpack
- Aster
- (시장 상황에 따라)

Selection Criteria:
1. 극초기 단계
2. API 제공
3. 포인트 프로그램 존재
4. 낮은 경쟁자 수
```

### Phase 3: Scale (20개 DEX)
```
Long-term Vision:
- 20개 DEX 동시 운영
- DEX당 $1-5M/월
- 총 거래량: $20-100M/월
- 포트폴리오 다각화
```

---

## 💰 Economics & ROI

### 수익 구조

#### 1. 거래 수익 (Trading Edge)
```
Avellaneda MM 백테스트 결과:
- 수익률: +0.20% (30일)
- 거래 횟수: 693회/월
- 거래량: $100.8M
- 자본: $5,000

실제 기대치 (보수적):
- 수익률: +0.15-0.30%/월
- 월 수익: $7.5-15 (자본 $5,000 기준)
```

#### 2. 수수료 비용/수익
```
Apex Pro:
- Maker Fee: 0% (무료!)
- 월 비용: $0

Paradex:
- Maker Rebate: -0.005%
- 월 수익: +$50-250 (거래량에 비례)

순수수료: +$50-250 (수익)
```

#### 3. 포인트 가치 (Primary Revenue)
```
Assumptions:
- 월 거래량: $1M (DEX당)
- 포인트 적립: 거래량 기반
- 랭킹: 상위 1%
- TGE 가치: TBD

Historical Examples (참고):
- dYdX: ~$2-5/포인트
- Blur: ~$0.5-1/포인트
- Paradigm: 알려지지 않음

Conservative Estimate:
- 포인트 수익: 월 $100-500
- 연환산: $1,200-6,000
- ROI: 24-120% (자본 $5,000 기준)
```

#### Total Expected Return
```
월 수익:
- 거래 수익: $10-15
- 수수료 수익: $50-250
- 포인트 가치: $100-500
- 합계: $160-765/월

연환산:
- 최소: $1,920 (38% ROI)
- 중간: $3,600 (72% ROI)
- 최대: $9,180 (184% ROI)

Risk-Adjusted:
- Sharpe Ratio: >1.5 목표
- Max Drawdown: <15%
```

---

## 🎯 Success Metrics & KPIs

### Primary Metrics (포인트 파밍)

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| **월 거래량 (DEX당)** | $1M | $2-5M | $10M+ |
| **포인트 랭킹** | Top 5% | Top 1% | Top 50 |
| **DEX 수** | 2개 | 5개 | 20개 |
| **씨드 진입 타이밍** | 초기 | 극초기 | 론칭 1주 |

### Secondary Metrics (손실 방지)

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| **월 수익률** | ≥0% | +0.15% | +0.30% |
| **Max Drawdown** | <20% | <15% | <10% |
| **Sharpe Ratio** | >0.5 | >1.0 | >2.0 |
| **가동률** | 90% | 95% | 99% |

### Operational Metrics

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| **일일 거래 횟수** | 10회 | 15-25회 | 50회+ |
| **평균 보유 시간** | <30분 | <15분 | <5분 |
| **Maker 비율** | 90% | 95% | 99% |
| **API 성공률** | 95% | 98% | 99.9% |

---

## 🚀 Strategic Milestones

### Milestone 1: Single DEX Validation (1-2주)
```
Goal: Apex Pro에서 전략 검증
Success Criteria:
  ✅ 거래량: 주 $250K (월 $1M 페이스)
  ✅ 수익: ≥0% (손실 없음)
  ✅ 포인트: 적립 확인
  ✅ 가동률: 90%+

Deliverables:
  - Avellaneda MM 작동 검증
  - Volume Tracker 구현
  - Risk Manager 검증
  - 포인트 적립 확인
```

### Milestone 2: Dual DEX Operation (2-3주)
```
Goal: Paradex 추가, 델타 뉴트럴 검증
Success Criteria:
  ✅ 거래량: 총 주 $500K (2개 DEX)
  ✅ 델타 뉴트럴: 펀딩비 차익 확인
  ✅ Maker Rebate: Paradex 수익 확인
  ✅ 랭킹: 각 DEX 상위 5%

Deliverables:
  - Paradex 통합
  - Cross-DEX Manager
  - Funding Arbitrage
  - 수수료 수익 검증
```

### Milestone 3: Portfolio Expansion (1-2개월)
```
Goal: 5개 DEX로 확장
Success Criteria:
  ✅ 거래량: 총 월 $5-10M
  ✅ 포인트: 평균 상위 1%
  ✅ 수익: 각 DEX ≥0%
  ✅ 자동화: 95% 가동률

Deliverables:
  - 3-5개 신규 DEX 통합
  - 멀티 DEX 오케스트레이션
  - 포트폴리오 리밸런싱
  - 통합 대시보드
```

### Milestone 4: Scale & Optimize (3-6개월)
```
Goal: 20개 DEX, 최적화
Success Criteria:
  ✅ 거래량: 총 월 $20-100M
  ✅ 포인트: 다수 DEX Top 50
  ✅ ROI: 연 50-100%+
  ✅ 자동화: 99% 가동률

Deliverables:
  - 20개 DEX 통합 완료
  - 동적 자본 배분
  - 포인트 가치 추적
  - TGE 모니터링
```

---

## ⚖️ Risk Management Philosophy

### Risk-First Mindset

```
Priority Order:
1. 자본 보존 (Capital Preservation)
2. 손실 방지 (Loss Prevention)
3. 거래량 극대화 (Volume Maximization)
4. 수익 창출 (Profit Generation)
```

### 핵심 리스크 제어

#### 1. 포지션 리스크
```
Kelly Criterion 기반 포지션 사이징:
- Win Rate: 58-60%
- Avg Win/Loss: 0.2-0.3%
- Kelly Fraction: ~40%
- Conservative: 20% (Kelly / 2)

결과:
- Max Position: 자본의 20%
- 청산가 여유: >30%
```

#### 2. 일일 손실 한도
```
Daily Loss Limit:
- Threshold: 자본의 2-5%
- Action: 당일 거래 중단
- Reset: 익일 자동 재개

Rationale:
- 연속 손실 방지
- 감정적 판단 차단
- 자본 보존 우선
```

#### 3. DEX 리스크 분산
```
Portfolio Allocation:
- Single DEX Max: 30%
- Top 3 DEX Max: 70%
- Long-tail DEX: 30%

Benefits:
- DEX 다운타임 대응
- 포인트 희석 리스크 분산
- TGE 실패 대비
```

---

## 📋 Key Assumptions & Validations

### Critical Assumptions

1. **포인트 프로그램 존재**
   - Assumption: 모든 타겟 DEX가 포인트 제공
   - Validation: 공식 발표 확인
   - Mitigation: 포인트 없으면 해당 DEX 제외

2. **API 안정성**
   - Assumption: 99% API 가동률
   - Validation: Testnet/Mainnet 테스트
   - Mitigation: Fallback DEX, Manual Override

3. **수수료 구조 유지**
   - Assumption: Maker 0% / Rebate 유지
   - Validation: 정기적 수수료 확인
   - Mitigation: 수수료 변경 시 전략 조정

4. **충분한 유동성**
   - Assumption: 최소 $100K 오더북 깊이
   - Validation: 실시간 유동성 모니터링
   - Mitigation: 유동성 부족 시 포지션 축소

### Success Prerequisites

- [x] Avellaneda MM 백테스트 통과
- [ ] Apex API 접근 확보
- [ ] Paradex API 접근 확보
- [ ] Volume Tracker 구현
- [ ] Risk Manager 구현
- [ ] 포인트 적립 확인

---

## 🎓 Strategic Principles

### 1. 극초기 진입 (First-Mover Advantage)
```
Why It Matters:
- 씨드 희석 전 최대 포인트 확보
- 경쟁자 적음 → 높은 랭킹
- 얼리 어답터 보너스

Execution:
- DEX 론칭 2주 이내 진입
- 메인넷 출시 6개월 이내
- 포인트 발표 즉시 대응
```

### 2. 학술적 검증 (Academic Validation)
```
Why It Matters:
- 직관 < 증명된 수학
- 백테스트 신뢰도 ↑
- 재현 가능성 ↑

Execution:
- Avellaneda-Stoikov (2008 논문)
- 30일 백테스트 통과 (+0.20%)
- 실전 검증 후 확장
```

### 3. 단순성 (Simplicity Over Complexity)
```
Why It Matters:
- 복잡함 = 버그 = 손실
- 단순함 = 안정성 = 신뢰
- 이해 가능 = 최적화 가능

Execution:
- 검증된 전략 1개 (Avellaneda MM)
- 명확한 파라미터 (γ, σ, k)
- 투명한 로직
```

### 4. 포트폴리오 접근 (Portfolio Approach)
```
Why It Matters:
- 단일 DEX 리스크 분산
- 다수 TGE 기회 확보
- 실패 내성 ↑

Execution:
- 2개 → 5개 → 20개 DEX
- 자본 분산 (30% Max per DEX)
- 지속적 확장
```

---

## 📚 References & Validation

### Academic Foundation
- **Paper**: "High-frequency trading in a limit order book"
- **Authors**: Marco Avellaneda, Sasha Stoikov (2008)
- **Link**: https://www.math.nyu.edu/~avellane/HighFrequencyTrading.pdf
- **Validation**: 백테스트 +0.20% (30일, 693 trades)

### Market Examples
- **dYdX**: 포인트 파밍 성공 사례 ($2-5/포인트)
- **Blur**: NFT 포인트 파밍 ($0.5-1/포인트)
- **Jito**: SOL MEV 포인트 파밍

### Internal Validation
- `docs/FINAL_STRATEGY_COMPARISON.md` - 5가지 전략 비교
- `docs/FEE_VERIFICATION_2025.md` - 수수료 구조 검증
- `PROJECT_STATUS.md` - 현재 진행 상황

---

## ✅ Approval & Consensus

**Strategic Direction**: APPROVED ✅
**Core Strategy (Avellaneda MM)**: VALIDATED ✅
**Risk Management**: ADEQUATE ✅
**Economic Model**: CONSERVATIVE ✅

**Next Step**: 구체적 실행 계획 (PLAN.md) 작성

---

**Document Status**: APPROVED FOR EXECUTION
**Owner**: Quantitative Trading Team
**Review Cycle**: Monthly or upon major DEX launch