# Multi-DEX Perpetual Futures Quant Trading System

20개 Perpetual DEX 대상 퀀트 트레이딩 시스템 - 실전 수익 + 포인트 파밍 최적화

---

## 📚 프로젝트 문서 구조

### 📋 전략 및 계획 문서

```
perpdex farm/
│
├── 📄 README.md                          # 이 파일 (프로젝트 전체 가이드)
│
├── common/docs/                          # 공통 문서
│   ├── PRD_MULTI_DEX_QUANT_SYSTEM.md    # 📊 제품 요구사항 정의서 (PRD)
│   └── IMPLEMENTATION_PLAN_COMMON.md    # 🔧 공통 인프라 실행계획
│
├── apex/docs/                            # ApeX 관련 문서
│   └── IMPLEMENTATION_PLAN.md           # ⚡ ApeX 실행계획 (2단계 전략)
│
└── paradex/docs/                         # Paradex 관련 문서
    └── IMPLEMENTATION_PLAN.md           # 🌊 Paradex 실행계획 (2단계 전략)
```

---

## 🎯 프로젝트 개요

### 목표
- **1차 목표**: 실전 트레이딩 수익 (월 10-20%)
- **2차 목표**: 포인트 파밍 최적화 (극초기 DEX 우선)

### 대상 DEX (20개)
- **Phase 1 (최우선)**: Apex, Paradex
- **Phase 2**: Lighter, Backpack, Aster
- **Phase 3**: 15개 추가 DEX (향후)

### 전략 유형
1. **고빈도 소액 거래**: 거래량 극대화 (100-150회/일)
2. **델타 뉴트럴**: Apex ↔ Paradex 펀딩비 차익 (일 3회)
3. **추세 추종**: Lighter, Hyperliquid 등 (Phase 2)

---

## 📖 문서 가이드

### 1️⃣ PRD (Product Requirements Document)
**파일**: `common/docs/PRD_MULTI_DEX_QUANT_SYSTEM.md`

**내용**:
- 비즈니스 목표 및 성공 지표
- DEX 선정 전략 (API 필수, 극초기 우선, 수수료 구조)
- 20개 DEX 로드맵 (6개월)
- Variational 제외 사례 연구 (API 없음)
- 전략 프레임워크 (수익형 vs 볼륨형 vs 펀딩비 차익)

**읽어야 할 사람**:
- 전략 기획자
- 비즈니스 의사결정자
- 투자자

---

### 2️⃣ 공통 인프라 실행계획
**파일**: `common/docs/IMPLEMENTATION_PLAN_COMMON.md`

**내용**:
- **공통 라이브러리**:
  - `BaseDexClient`: 모든 DEX 클라이언트 추상 클래스
  - `PositionCalculator`: 청산가, 손익, 증거금 계산
  - `RiskManager`: 드로우다운, 손실 제한, 노출 관리

- **전략 프레임워크**:
  - `HighFrequencyStrategy`: 고빈도 소액 거래
  - `DeltaNeutralStrategy`: 델타 뉴트럴 펀딩비 차익
  - `TrendFollowingStrategy`: 추세 추종 (Phase 2)

- **데이터 관리**: PostgreSQL (거래 내역), Redis (실시간 캐싱)
- **모니터링**: Grafana 대시보드, Telegram 알림
- **구현 우선순위**: 8주 Phase별 계획

**읽어야 할 사람**:
- 백엔드 개발자
- 시스템 아키텍트
- DevOps 엔지니어

---

### 3️⃣ ApeX 실행계획
**파일**: `apex/docs/IMPLEMENTATION_PLAN.md`

**내용**:
- **Strategy 1 - 고빈도 소액 거래**:
  - 펀딩비 시간 외 모든 시간 실행
  - 100-150회/일
  - 목표 수익: 왕복 0.05-0.1%
  - 예상 수익: 월 2.1% ($210 on $10K)

- **Strategy 2 - 델타 뉴트럴**:
  - 일 3회 (00:00, 08:00, 16:00 UTC)
  - Paradex와 연결 (Apex LONG ↔ Paradex SHORT)
  - Human-like 랜덤화 (3-45분 홀딩)
  - 예상 수익: 월 1.8% ($180 on $10K)

- **총 예상 수익**: 월 10-15% ($390 on $10K)

**읽어야 할 사람**:
- ApeX API 개발자
- 트레이딩 봇 운영자

---

### 4️⃣ Paradex 실행계획
**파일**: `paradex/docs/IMPLEMENTATION_PLAN.md`

**내용**:
- **Strategy 1 - 고빈도 with Maker Rebate**:
  - **Maker Rebate -0.005%** (핵심 강점!)
  - 100-150회/일
  - 리베이트만으로 월 $30 보장
  - 예상 수익: 월 18% ($180 on $1K)

- **Strategy 2 - 델타 뉴트럴**:
  - Apex와 동일 (역방향)
  - 리베이트 추가 수익
  - 예상 수익: 월 1.8% + 리베이트

- **총 예상 수익**: 월 12-18%

**읽어야 할 사람**:
- Paradex API 개발자
- Maker Rebate 최적화 담당자

---

## 🚀 빠른 시작

### Phase 1 우선순위 (Apex + Paradex)

#### 1. 환경 설정
```bash
# ApeX 환경 설정
cd apex
cp .env.example .env
# .env 파일에 API 키 입력

# Paradex 환경 설정
cd ../paradex
cp .env.example .env
# .env 파일에 L1 Address, Private Key 입력
```

#### 2. 의존성 설치
```bash
# ApeX
cd apex
pip install -r requirements.txt

# Paradex
cd ../paradex
pip install -r requirements.txt
```

#### 3. Testnet 테스트
```bash
# Paradex Testnet 연결 테스트
cd paradex
python examples/01_connect_testnet.py

# Maker Rebate 검증
python examples/02_testnet_order.py

# 펀딩비 모니터링
python examples/03_funding_monitor.py
```

#### 4. 공통 라이브러리 구현 (우선)
```bash
cd ../common

# 1. BaseDexClient 추상 클래스 구현
# 2. PositionCalculator 유틸리티 구현
# 3. RiskManager 클래스 구현
```

#### 5. 전략 구현
```bash
# High-frequency strategy
common/strategies/high_frequency.py

# Delta neutral strategy
common/strategies/delta_neutral.py
```

---

## 📊 전략 예상 수익률 요약

| DEX | Strategy 1 (고빈도) | Strategy 2 (델타뉴트럴) | 총 월 수익률 |
|-----|---------------------|-------------------------|--------------|
| **ApeX** | 2.1% ($210) | 1.8% ($180) | **10-15%** |
| **Paradex** | 18% ($180)* | 1.8% + 리베이트 | **12-18%** |

*Maker Rebate -0.005% 효과 포함

### 델타 뉴트럴 복합 수익
```
Position: $10,000 × 2 (Apex + Paradex)

일일 (3회):
  - Funding 차익: $1 × 3 = $3
  - Maker Rebate: $1 × 3 = $3
  - 총: $6/일

월 수익: $180 (1.8%)
```

---

## 🛠️ 기술 스택

### Backend
- **Python 3.10+**
- **PostgreSQL**: 거래 내역 저장
- **Redis**: 실시간 데이터 캐싱

### DEX APIs
- **ApeX Omni**: `apexomni` Python SDK
- **Paradex**: `paradex-py` Python SDK

### Monitoring
- **Grafana**: 대시보드
- **Prometheus**: 메트릭 수집
- **Telegram Bot**: 실시간 알림

### Infrastructure
- **Docker**: 컨테이너화
- **systemd**: 서비스 관리 (리눅스)

---

## ⚠️ 리스크 관리

### 자동 제한
- **최대 드로우다운**: 15%
- **일일 손실 제한**: $500
- **DEX별 일일 거래**: 200회
- **총 노출 제한**: $50,000

### 모니터링 지표
- Sharpe Ratio (목표: >2.0)
- Win Rate (목표: >60%)
- 청산가까지 거리 (최소: 20%)

---

## 📈 로드맵

### Month 1-2 (현재)
- [x] PRD 작성 완료
- [x] Apex 실행계획 완료
- [x] Paradex 실행계획 완료
- [x] 공통 인프라 계획 완료
- [ ] 공통 라이브러리 구현 (Week 1-2)
- [ ] Testnet 검증
- [ ] Mainnet 소규모 테스트 ($1K)

### Month 3-4
- [ ] Apex + Paradex 프로덕션 ($10K)
- [ ] Lighter, Backpack, Aster 추가
- [ ] 백테스팅 프레임워크 구축

### Month 5-6
- [ ] 15개 추가 DEX 통합
- [ ] 자동 포트폴리오 리밸런싱
- [ ] 고급 전략 개발

---

## 📞 문의 및 기여

### 문서 업데이트
- PRD 수정: `common/docs/PRD_MULTI_DEX_QUANT_SYSTEM.md` 편집
- 실행계획 수정: 각 DEX의 `docs/IMPLEMENTATION_PLAN.md` 편집

### 개발 진행 상황
- 구현 우선순위: `common/docs/IMPLEMENTATION_PLAN_COMMON.md` 참조
- 8주 Phase별 체크리스트 확인

---

## 📂 폴더 구조 (전체)

```
perpdex farm/
│
├── README.md                             # 프로젝트 종합 가이드
│
├── common/                               # 공통 컴포넌트
│   ├── docs/
│   │   ├── PRD_MULTI_DEX_QUANT_SYSTEM.md
│   │   └── IMPLEMENTATION_PLAN_COMMON.md
│   ├── lib/                             # 공통 라이브러리
│   │   ├── base_dex_client.py          # DEX 클라이언트 추상 클래스
│   │   ├── position_calculator.py      # 계산 유틸리티
│   │   └── risk_manager.py             # 리스크 관리
│   ├── strategies/                      # 전략 프레임워크
│   │   ├── base_strategy.py
│   │   ├── high_frequency.py
│   │   └── delta_neutral.py
│   ├── database/                        # 데이터베이스
│   │   └── models.py
│   └── monitoring/                      # 모니터링
│       └── metrics_collector.py
│
├── apex/                                 # ApeX Omni
│   ├── docs/
│   │   └── IMPLEMENTATION_PLAN.md
│   ├── lib/
│   │   └── apex_client.py              # ApeX 클라이언트 (BaseDexClient 상속)
│   ├── examples/                        # 예제 코드
│   └── strategies/                      # ApeX 전용 전략
│
├── paradex/                              # Paradex
│   ├── docs/
│   │   └── IMPLEMENTATION_PLAN.md
│   ├── lib/
│   │   └── paradex_client.py           # Paradex 클라이언트
│   ├── examples/
│   │   ├── 01_connect_testnet.py
│   │   ├── 02_testnet_order.py
│   │   └── 03_funding_monitor.py
│   └── README.md                        # Paradex 사용 가이드
│
└── lighter/                              # Lighter (Phase 2, 향후)
    └── docs/
        └── IMPLEMENTATION_PLAN.md       # (작성 예정)
```

---

**Version**: 1.0
**Last Updated**: 2025-01-24
**Status**: Phase 1 계획 완료, 구현 시작 대기

---

## 🔗 관련 링크

### ApeX
- API 문서: https://api-docs.omni.apex.exchange/
- Python SDK: `apexomni`

### Paradex
- API 문서: https://docs.paradex.trade/api/
- Python SDK: https://github.com/tradeparadex/paradex-py
- Testnet: https://testnet.paradex.trade
- Mainnet: https://www.paradex.trade

### 펀딩비 스케줄
- **공통**: 00:00, 08:00, 16:00 UTC (하루 3회)
- KST: 09:00, 17:00, 익일 01:00
