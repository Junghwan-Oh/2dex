# 공통 인프라 실행계획 (Common Infrastructure Implementation Plan)

Multi-DEX 퀀트 트레이딩 시스템의 공통 인프라 및 재사용 가능한 컴포넌트 구현 계획

**Related Documents**:
- `DEX_BOT_DEVELOPMENT_CHECKLIST.md`: Operational requirements (version management, Telegram, GitHub)
- `DEX_INTEGRATION_FRAMEWORK.md`: 9-Stage integration process (Phase 0-8)

---

## 📋 목차

1. [개요](#개요)
2. [개발 프로세스 및 테스트 전략](#개발-프로세스-및-테스트-전략)
3. [Phase 0: API Connection Test](#phase-0-api-connection-test) ← NEW
4. [공통 라이브러리](#공통-라이브러리)
5. [전략 프레임워크](#전략-프레임워크)
6. [데이터 관리](#데이터-관리)
7. [모니터링 시스템](#모니터링-시스템)
8. [리스크 관리](#리스크-관리)
9. [백테스팅 프레임워크](#백테스팅-프레임워크)
10. [구현 우선순위](#구현-우선순위)

---

## 개요

### 목표
- **코드 재사용성 극대화**: 20개 DEX에서 공통으로 사용할 수 있는 기반 컴포넌트
- **일관된 전략 실행**: 모든 DEX에서 동일한 전략 로직 적용
- **통합 모니터링**: 단일 대시보드에서 모든 DEX 관리
- **중앙화된 리스크 관리**: DEX 간 총 리스크 추적 및 제어

### 아키텍처 원칙
```
common/
├── lib/                    # 공통 라이브러리
│   ├── base_dex_client.py        # DEX 클라이언트 추상 클래스
│   ├── position_calculator.py    # 포지션 계산 유틸리티
│   ├── risk_manager.py           # 리스크 관리 로직
│   └── order_executor.py         # 주문 실행 엔진
│
├── strategies/             # 전략 프레임워크
│   ├── base_strategy.py          # 전략 추상 클래스
│   ├── high_frequency.py         # 고빈도 전략
│   ├── delta_neutral.py          # 델타 뉴트럴 전략
│   └── trend_following.py        # 추세 추종 전략
│
├── database/               # 데이터 관리
│   ├── models.py                 # 데이터 모델 (SQLAlchemy)
│   ├── redis_client.py           # Redis 캐싱
│   └── postgres_client.py        # PostgreSQL 연결
│
├── monitoring/             # 모니터링
│   ├── metrics_collector.py      # 메트릭 수집
│   ├── alert_manager.py          # 알림 관리
│   └── grafana_exporter.py       # Grafana 연동
│
├── backtesting/            # 백테스팅
│   ├── backtest_engine.py        # 백테스팅 엔진
│   └── performance_analyzer.py   # 성능 분석
│
└── tests/                  # 테스트
    ├── unit/                        # 유닛 테스트
    │   ├── test_base_client.py
    │   ├── test_position_calculator.py
    │   ├── test_risk_manager.py
    │   └── test_strategies.py
    └── e2e/                         # E2E 테스트
        ├── test_high_frequency_flow.py
        └── test_delta_neutral_flow.py
```

---

## 개발 프로세스 및 테스트 전략

### 🔴 필수 개발 규칙 (모든 DEX 공통)

#### 1. 단계별 구현 필수
모든 DEX 및 전략 구현은 다음 단계를 **반드시** 거쳐야 합니다:

```
1. 설계 및 계획
   ├─ 기능 명세 작성
   ├─ 인터페이스 설계
   └─ 테스트 케이스 정의

2. 유닛 테스트 작성 (TDD)
   ├─ 테스트 먼저 작성
   ├─ 실패 확인
   └─ 구현 후 통과 확인

3. 구현
   ├─ 기능 구현
   └─ 코드 리뷰

4. Lint 검사
   ├─ flake8: 스타일 체크
   ├─ black: 코드 포맷팅
   ├─ mypy: 타입 체크
   └─ 모든 검사 통과 확인

5. E2E 테스트 작성
   ├─ 실제 환경 시나리오
   ├─ Testnet 검증
   └─ 통합 테스트

6. 검증 및 배포
   ├─ 전체 테스트 실행
   ├─ 커버리지 확인 (>80%)
   └─ Mainnet 소규모 테스트
```

#### 2. 테스트 커버리지 요구사항
- **유닛 테스트 커버리지**: 최소 80%
- **E2E 테스트**: 모든 주요 시나리오 커버
- **새 기능 추가 시**: 테스트 먼저 작성 (TDD)

#### 3. 테스트 자동화
```bash
# 전체 테스트 실행
pytest tests/

# 유닛 테스트만
pytest tests/unit/

# E2E 테스트만
pytest tests/e2e/

# 커버리지 포함
pytest --cov=common --cov=apex --cov=paradex tests/

# Lint 검사
flake8 common/ apex/ paradex/
black --check common/ apex/ paradex/
mypy common/ apex/ paradex/
```

---

## Phase 0: API Connection Test

**Purpose**: DEX별 첫 작업 - API 연결 검증 및 기본 기능 테스트

### ✅ Phase 0 체크리스트

#### 1. API 키 설정 및 연결 테스트
- [ ] **환경 변수 설정** (.env 파일)
  - API 키/시크릿 (또는 private key)
  - Account/Wallet 주소
  - Testnet/Mainnet 선택

- [ ] **기본 연결 테스트**
  - Public API 연결 (market data)
  - Private API 인증 (account info)
  - WebSocket 연결 (실시간 데이터)

#### 2. 핵심 기능 검증
- [ ] **Market Data 조회**
  - 티커 데이터 조회
  - K선 데이터 조회 (1m, 3m, 5m, 15m, 1h)
  - Order book 조회

- [ ] **Account 정보 조회**
  - 잔고 조회
  - 포지션 조회
  - 주문 내역 조회

- [ ] **주문 실행 테스트** (Testnet 또는 Paper Trading)
  - Market order (매수/매도)
  - Limit order (지정가)
  - 주문 취소
  - Position close

#### 3. WebSocket vs REST 결정
- [ ] **WebSocket 지원 확인**
  - 실시간 ticker stream
  - 실시간 depth/orderbook stream
  - 실시간 kline stream
  - Private stream (orders, positions)

- [ ] **REST 폴백 전략**
  - WebSocket 연결 실패 시 REST 사용
  - Health check 로직
  - Auto-reconnection 전략

**Apex 경험**:
- WebSocket: 실시간 가격 (100-200ms 레이턴시)
- REST: EMA 계산용 히스토리 데이터 (1Hz 폴링)
- Hybrid 아키텍처: 99.5% uptime, 5-8초 복구 시간

#### 4. 심볼 포맷 검증
- [ ] **REST API 심볼 포맷**
  - 예: `BTC-USDT`, `BTC/USDT`, `BTCUSDT`

- [ ] **WebSocket 심볼 포맷**
  - 예: `BTCUSDT` (하이픈 없음)
  - REST와 다를 수 있음 → 변환 로직 필요

**Apex 경험**:
- REST: `BTC-USDT`
- WebSocket: `BTCUSDT` (하이픈 제거 필요)

#### 5. Order Execution 검증
- [ ] **주문 파라미터 확인**
  - 최소 주문 수량 (minOrderSize)
  - 가격 단위 (tickSize)
  - Leverage 설정 방법
  - Position mode (one-way/hedge)

- [ ] **Paper Trading 모드**
  - 실제 주문 없이 시뮬레이션
  - 주문 응답 파싱
  - 에러 핸들링

#### 6. 타임프레임 지원 확인
- [ ] **지원 타임프레임 목록**
  - 1분(1m), 3분(3m), 5분(5m)
  - 15분(15m), 30분(30m), 1시간(1h)

- [ ] **K선 데이터 품질**
  - 데이터 누락 확인
  - 타임스탬프 정확도
  - OHLCV 완전성

**Apex 경험**:
- 1m, 3m, 5m, 15m, 30m, 1h 모두 지원
- Fast trading: 1m/3m (EMA 10/20, 10/30)
- Standard trading: 30m/1h (EMA 20/60, 30/80)

#### 7. Rate Limit 확인
- [ ] **REST API Rate Limit**
  - Public API: 초당 요청 수
  - Private API: 초당 요청 수
  - 초과 시 동작 확인

- [ ] **WebSocket 제한**
  - 동시 연결 수
  - Subscribe 채널 수

### 📚 참고 문서
- **상세 9단계 프로세스**: `DEX_INTEGRATION_FRAMEWORK.md` (Phase 0-8)
- **운영 체크리스트**: `DEX_BOT_DEVELOPMENT_CHECKLIST.md` (version, Telegram, GitHub)
- **Apex 구현 경험**: `apex/LESSONS_LEARNED_APEX_INTEGRATION.md`

---

### 유닛 테스트 전략

#### 테스트 구조
```
tests/unit/
├── common/
│   ├── test_base_dex_client.py      # BaseDexClient 테스트
│   ├── test_position_calculator.py  # 계산 로직 테스트
│   ├── test_risk_manager.py         # 리스크 관리 테스트
│   └── test_strategies.py           # 전략 로직 테스트
│
├── apex/
│   ├── test_apex_client.py          # ApexClient 테스트
│   └── test_apex_high_frequency.py  # Apex 고빈도 전략 테스트
│
└── paradex/
    ├── test_paradex_client.py
    └── test_paradex_high_frequency.py
```

#### 유닛 테스트 예시
```python
# tests/unit/common/test_position_calculator.py
import pytest
from common.lib.position_calculator import (
    calculateLiquidationPrice,
    calculateUnrealizedPnl
)

class TestPositionCalculator:
    """포지션 계산 유틸리티 테스트"""

    def test_liquidation_price_long(self):
        """LONG 포지션 청산가 계산"""
        liquidationPrice = calculateLiquidationPrice(
            entryPrice=50000.0,
            leverage=10.0,
            side='LONG',
            maintenanceMarginRate=0.005
        )

        # 예상: 50000 × (1 - 1/10 + 0.005) = 45,250
        assert abs(liquidationPrice - 45250.0) < 1.0

    def test_liquidation_price_short(self):
        """SHORT 포지션 청산가 계산"""
        liquidationPrice = calculateLiquidationPrice(
            entryPrice=50000.0,
            leverage=10.0,
            side='SHORT',
            maintenanceMarginRate=0.005
        )

        # 예상: 50000 × (1 + 1/10 - 0.005) = 54,750
        assert abs(liquidationPrice - 54750.0) < 1.0

    def test_unrealized_pnl_long_profit(self):
        """LONG 포지션 미실현 손익 (수익)"""
        pnl = calculateUnrealizedPnl(
            side='LONG',
            entryPrice=50000.0,
            markPrice=51000.0,
            size=0.1
        )

        # 예상: (51000 - 50000) × 0.1 = 100
        assert abs(pnl - 100.0) < 0.01

    def test_unrealized_pnl_long_loss(self):
        """LONG 포지션 미실현 손익 (손실)"""
        pnl = calculateUnrealizedPnl(
            side='LONG',
            entryPrice=50000.0,
            markPrice=49000.0,
            size=0.1
        )

        # 예상: (49000 - 50000) × 0.1 = -100
        assert abs(pnl - (-100.0)) < 0.01

    @pytest.mark.parametrize("entryPrice,leverage,expected", [
        (50000.0, 5.0, 40250.0),   # 5x leverage
        (50000.0, 10.0, 45250.0),  # 10x leverage
        (50000.0, 20.0, 47750.0),  # 20x leverage
    ])
    def test_liquidation_price_various_leverage(self, entryPrice, leverage, expected):
        """다양한 레버리지에서 청산가 계산"""
        liquidationPrice = calculateLiquidationPrice(
            entryPrice=entryPrice,
            leverage=leverage,
            side='LONG'
        )

        assert abs(liquidationPrice - expected) < 1.0
```

```python
# tests/unit/common/test_risk_manager.py
import pytest
from common.lib.risk_manager import RiskManager, RiskLimits

class TestRiskManager:
    """리스크 관리자 테스트"""

    def setup_method(self):
        """각 테스트 전 실행"""
        self.riskLimits = RiskLimits(
            maxPositionSizeUsd=10000.0,
            maxTotalExposureUsd=50000.0,
            maxDrawdownPercent=15.0,
            maxDailyLossUsd=500.0,
            maxDailyTradesPerDex=200
        )
        self.riskManager = RiskManager(self.riskLimits)
        self.riskManager.updateBalance(10000.0)

    def test_check_position_size_within_limit(self):
        """포지션 크기 제한 내"""
        result = self.riskManager.checkPositionSize('apex', 5000.0)
        assert result == True

    def test_check_position_size_exceeds_limit(self):
        """포지션 크기 제한 초과"""
        result = self.riskManager.checkPositionSize('apex', 15000.0)
        assert result == False

    def test_drawdown_calculation(self):
        """드로우다운 계산"""
        self.riskManager.updateBalance(10000.0)  # Peak
        self.riskManager.updateBalance(9000.0)   # Current

        drawdown = self.riskManager.getCurrentDrawdown()
        assert abs(drawdown - 10.0) < 0.01  # 10% drawdown

    def test_check_drawdown_limit_within(self):
        """드로우다운 제한 내"""
        self.riskManager.updateBalance(10000.0)
        self.riskManager.updateBalance(9000.0)  # 10% drawdown

        result = self.riskManager.checkDrawdownLimit()
        assert result == True

    def test_check_drawdown_limit_exceeded(self):
        """드로우다운 제한 초과"""
        self.riskManager.updateBalance(10000.0)
        self.riskManager.updateBalance(8000.0)  # 20% drawdown

        result = self.riskManager.checkDrawdownLimit()
        assert result == False

    def test_can_open_position_success(self):
        """포지션 진입 허용"""
        canOpen, reason = self.riskManager.canOpenPosition(
            dexName='apex',
            positionSizeUsd=5000.0
        )

        assert canOpen == True
        assert reason is None

    def test_can_open_position_drawdown_exceeded(self):
        """드로우다운 초과로 진입 거부"""
        self.riskManager.updateBalance(10000.0)
        self.riskManager.updateBalance(8000.0)  # 20% drawdown

        canOpen, reason = self.riskManager.canOpenPosition(
            dexName='apex',
            positionSizeUsd=5000.0
        )

        assert canOpen == False
        assert "drawdown" in reason.lower()

    def test_daily_trade_count_tracking(self):
        """일일 거래 횟수 추적"""
        # 200회 거래 기록
        for i in range(200):
            self.riskManager.recordTrade('apex', 10.0)

        # 201번째 거래 체크
        result = self.riskManager.checkDailyTradeLimit('apex')
        assert result == False
```

---

### E2E 테스트 전략

#### 테스트 구조
```
tests/e2e/
├── common/
│   └── fixtures.py                  # 공통 Fixture (Mock DEX 등)
│
├── apex/
│   ├── test_high_frequency_flow.py  # 고빈도 전략 E2E
│   ├── test_order_lifecycle.py      # 주문 생명주기
│   └── test_risk_integration.py     # 리스크 관리 통합
│
└── paradex/
    ├── test_high_frequency_flow.py
    └── test_maker_rebate_flow.py    # Maker Rebate 검증
```

#### E2E 테스트 예시
```python
# tests/e2e/apex/test_high_frequency_flow.py
import pytest
import time
from apex.lib.apex_client import ApexClient
from common.strategies.high_frequency import HighFrequencyStrategy
from common.lib.risk_manager import RiskManager, RiskLimits

@pytest.mark.e2e
class TestApexHighFrequencyE2E:
    """Apex 고빈도 전략 E2E 테스트"""

    def setup_method(self):
        """Testnet 환경 설정"""
        self.apexClient = ApexClient(environment='testnet')

        self.riskLimits = RiskLimits(
            maxPositionSizeUsd=1000.0,  # Testnet은 작은 금액
            maxDailyLossUsd=50.0
        )
        self.riskManager = RiskManager(self.riskLimits)

        config = {
            'symbol': 'BTC-USDT',
            'targetSpread': 0.001,
            'minProfitRate': 0.0005,
            'positionSize': 0.001
        }

        self.strategy = HighFrequencyStrategy(
            dexClient=self.apexClient,
            riskManager=self.riskManager,
            config=config
        )

    @pytest.mark.testnet
    def test_full_trade_lifecycle(self):
        """전체 거래 생명주기 (진입 → 체결 → 청산)"""
        # 1. 전략 초기화
        assert self.strategy.initialize() == True

        # 2. 계좌 잔고 확인
        account = self.apexClient.getAccount()
        initialBalance = float(account.get('equity', 0))
        assert initialBalance > 0

        self.riskManager.updateBalance(initialBalance)

        # 3. 현재가 조회
        ticker = self.apexClient.getTicker('BTC-USDT')
        currentPrice = float(ticker.get('price', 0))
        assert currentPrice > 0

        # 4. 시그널 생성
        marketData = {'ticker': ticker}
        orders = self.strategy.generateSignals(marketData)

        # Spread가 충분하면 주문 생성됨
        if len(orders) > 0:
            # 5. 주문 실행
            results = self.strategy.executeOrders(orders)
            assert len(results) > 0

            orderId = results[0].get('data', {}).get('orderId')
            assert orderId is not None

            # 6. 주문 체결 대기 (최대 60초)
            filled = False
            for _ in range(60):
                orderHistory = self.apexClient.getOrderHistory('BTC-USDT', limit=10)

                for order in orderHistory:
                    if order.get('orderId') == orderId and order.get('status') == 'FILLED':
                        filled = True
                        break

                if filled:
                    break

                time.sleep(1)

            # 7. 포지션 확인
            positions = self.apexClient.getPositions()
            activePosition = None
            for pos in positions:
                if float(pos.size) > 0:
                    activePosition = pos
                    break

            if activePosition:
                # 8. 포지션 청산
                closeOrder = self.apexClient.createOrder({
                    'symbol': 'BTC-USDT',
                    'side': 'SELL' if activePosition.side == 'LONG' else 'BUY',
                    'type': 'MARKET',
                    'size': str(abs(float(activePosition.size))),
                    'reduceOnly': True
                })

                assert closeOrder is not None

                # 9. 청산 확인
                time.sleep(5)
                positions = self.apexClient.getPositions()
                assert len([p for p in positions if float(p.size) > 0]) == 0

    @pytest.mark.testnet
    def test_risk_manager_integration(self):
        """리스크 관리자 통합 테스트"""
        # 1. 드로우다운 시뮬레이션
        self.riskManager.updateBalance(1000.0)  # Peak
        self.riskManager.updateBalance(800.0)   # 20% drawdown

        # 2. 포지션 진입 시도
        canOpen, reason = self.riskManager.canOpenPosition(
            dexName='apex',
            positionSizeUsd=100.0
        )

        # 3. 드로우다운 초과로 거부되어야 함
        assert canOpen == False
        assert "drawdown" in reason.lower()

    @pytest.mark.testnet
    def test_maker_fee_verification(self):
        """Maker 수수료 0% 검증"""
        # Limit 주문 (POST_ONLY) 생성
        ticker = self.apexClient.getTicker('BTC-USDT')
        currentPrice = float(ticker.get('price', 0))

        order = self.apexClient.createOrder({
            'symbol': 'BTC-USDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'size': '0.001',
            'price': str(currentPrice * 0.99),  # 현재가보다 1% 낮게
            'timeInForce': 'POST_ONLY'
        })

        orderId = order.get('data', {}).get('orderId')

        # 체결 대기 또는 취소
        time.sleep(10)

        # 체결 내역 조회
        fills = self.apexClient.getOrderHistory('BTC-USDT', limit=10)

        for fill in fills:
            if fill.get('orderId') == orderId and fill.get('status') == 'FILLED':
                feeRate = float(fill.get('feeRate', 1.0))

                # Maker 수수료 0% 확인
                assert abs(feeRate) < 0.0001  # 0%

                break

        # 미체결 주문 취소
        try:
            self.apexClient.cancelOrder(orderId)
        except:
            pass
```

---

### CI/CD 통합

#### GitHub Actions 워크플로우
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run unit tests
      run: |
        pytest tests/unit/ --cov=common --cov=apex --cov=paradex --cov-report=xml

    - name: Check coverage
      run: |
        coverage report --fail-under=80

  e2e-tests:
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest

    - name: Run E2E tests (Testnet)
      env:
        APEX_API_KEY: ${{ secrets.APEX_TESTNET_KEY }}
        APEX_API_SECRET: ${{ secrets.APEX_TESTNET_SECRET }}
        PARADEX_L1_PRIVATE_KEY: ${{ secrets.PARADEX_TESTNET_KEY }}
      run: |
        pytest tests/e2e/ -m testnet
```

---

### 테스트 실행 스크립트

#### 로컬 개발 환경
```bash
# scripts/run_tests.sh
#!/bin/bash

echo "=== Running Unit Tests ==="
pytest tests/unit/ -v

echo ""
echo "=== Running E2E Tests (Testnet) ==="
pytest tests/e2e/ -m testnet -v

echo ""
echo "=== Coverage Report ==="
pytest tests/unit/ --cov=common --cov=apex --cov=paradex --cov-report=html
echo "Coverage report: htmlcov/index.html"
```

---

## 공통 라이브러리

### 1. BaseDexClient (추상 클래스)

**파일**: `common/lib/base_dex_client.py`

**목적**: 모든 DEX 클라이언트가 구현해야 하는 인터페이스 정의

**핵심 메서드**:
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Order:
    """주문 데이터 클래스"""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    orderType: str  # 'LIMIT' or 'MARKET'
    size: str
    price: Optional[str] = None
    timeInForce: str = 'POST_ONLY'
    reduceOnly: bool = False

@dataclass
class Position:
    """포지션 데이터 클래스"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    size: float
    entryPrice: float
    markPrice: float
    unrealizedPnl: float
    leverage: float
    liquidationPrice: Optional[float] = None

class BaseDexClient(ABC):
    """DEX 클라이언트 추상 클래스"""

    def __init__(self, environment: str = 'testnet'):
        self.environment = environment
        self.isConnected = False

    @abstractmethod
    def connect(self) -> bool:
        """DEX 연결"""
        pass

    @abstractmethod
    def getTicker(self, symbol: str) -> Dict:
        """현재가 조회"""
        pass

    @abstractmethod
    def getFundingRate(self, symbol: str) -> Dict:
        """펀딩비 조회"""
        pass

    @abstractmethod
    def getAccount(self) -> Dict:
        """계좌 정보 조회"""
        pass

    @abstractmethod
    def getPositions(self) -> List[Position]:
        """포지션 조회"""
        pass

    @abstractmethod
    def createOrder(self, order: Order) -> Dict:
        """주문 생성"""
        pass

    @abstractmethod
    def cancelOrder(self, orderId: str) -> Dict:
        """주문 취소"""
        pass

    @abstractmethod
    def getOrderHistory(self, symbol: str, limit: int = 100) -> List[Dict]:
        """주문 내역 조회"""
        pass

    # 공통 유틸리티 메서드
    def formatPrice(self, price: float, symbol: str) -> str:
        """가격 포맷팅 (DEX별 소수점 자리수 다름)"""
        raise NotImplementedError

    def formatSize(self, size: float, symbol: str) -> str:
        """주문 크기 포맷팅"""
        raise NotImplementedError

    def validateOrder(self, order: Order) -> bool:
        """주문 유효성 검증"""
        raise NotImplementedError
```

**사용 예시** (Apex 클라이언트에서):
```python
from common.lib.base_dex_client import BaseDexClient, Order, Position

class ApexClient(BaseDexClient):
    """ApeX Omni 클라이언트 구현"""

    def __init__(self, environment='mainnet'):
        super().__init__(environment)
        self.httpClient = HttpPrivate_v3(...)

    def connect(self) -> bool:
        try:
            configs = self.httpClient.configs_v3()
            self.isConnected = True
            return True
        except Exception as e:
            return False

    def getTicker(self, symbol: str) -> Dict:
        return self.httpClient.ticker_v3(symbol)

    # ... 나머지 메서드 구현
```

---

### 2. PositionCalculator (계산 유틸리티)

**파일**: `common/lib/position_calculator.py`

**목적**: 포지션 관련 계산 함수 제공

**핵심 함수**:
```python
from typing import Optional

def calculateLiquidationPrice(
    entryPrice: float,
    leverage: float,
    side: str,  # 'LONG' or 'SHORT'
    maintenanceMarginRate: float = 0.005
) -> float:
    """
    청산가 계산

    Args:
        entryPrice: 진입가
        leverage: 레버리지
        side: 포지션 방향
        maintenanceMarginRate: 유지증거금률 (기본값 0.5%)

    Returns:
        청산가
    """
    if side == 'LONG':
        # LONG 청산가 = 진입가 × (1 - 1/레버리지 + 유지증거금률)
        liquidationPrice = entryPrice * (1 - 1/leverage + maintenanceMarginRate)
    else:  # SHORT
        # SHORT 청산가 = 진입가 × (1 + 1/레버리지 - 유지증거금률)
        liquidationPrice = entryPrice * (1 + 1/leverage - maintenanceMarginRate)

    return liquidationPrice


def calculateUnrealizedPnl(
    side: str,
    entryPrice: float,
    markPrice: float,
    size: float
) -> float:
    """
    미실현 손익 계산

    Args:
        side: 포지션 방향
        entryPrice: 진입가
        markPrice: 현재가
        size: 포지션 크기 (BTC)

    Returns:
        미실현 손익 (USD)
    """
    if side == 'LONG':
        pnl = (markPrice - entryPrice) * size
    else:  # SHORT
        pnl = (entryPrice - markPrice) * size

    return pnl


def calculateRequiredMargin(
    positionSize: float,
    entryPrice: float,
    leverage: float
) -> float:
    """
    필요 증거금 계산

    Args:
        positionSize: 포지션 크기 (BTC)
        entryPrice: 진입가
        leverage: 레버리지

    Returns:
        필요 증거금 (USD)
    """
    notionalValue = positionSize * entryPrice
    requiredMargin = notionalValue / leverage

    return requiredMargin


def calculatePositionSizeFromMargin(
    availableMargin: float,
    entryPrice: float,
    leverage: float,
    marginUsagePercent: float = 0.5
) -> float:
    """
    사용 가능한 증거금으로부터 포지션 크기 계산

    Args:
        availableMargin: 사용 가능한 증거금
        entryPrice: 진입가
        leverage: 레버리지
        marginUsagePercent: 증거금 사용 비율 (기본값 50%)

    Returns:
        포지션 크기 (BTC)
    """
    usableMargin = availableMargin * marginUsagePercent
    notionalValue = usableMargin * leverage
    positionSize = notionalValue / entryPrice

    return positionSize


def calculateBreakEvenPrice(
    entryPrice: float,
    side: str,
    makerFeeRate: float,
    takerFeeRate: float = 0.0
) -> float:
    """
    손익분기점 가격 계산

    Args:
        entryPrice: 진입가
        side: 포지션 방향
        makerFeeRate: Maker 수수료율 (음수면 Rebate)
        takerFeeRate: Taker 수수료율 (청산 시)

    Returns:
        손익분기점 가격
    """
    totalFeeRate = abs(makerFeeRate) + takerFeeRate

    if side == 'LONG':
        # LONG 손익분기 = 진입가 × (1 + 수수료)
        breakEvenPrice = entryPrice * (1 + totalFeeRate)
    else:  # SHORT
        # SHORT 손익분기 = 진입가 × (1 - 수수료)
        breakEvenPrice = entryPrice * (1 - totalFeeRate)

    return breakEvenPrice


def calculateFundingPayment(
    positionSize: float,
    markPrice: float,
    fundingRate: float
) -> float:
    """
    펀딩비 지급액 계산

    Args:
        positionSize: 포지션 크기 (BTC, LONG은 양수, SHORT는 음수)
        markPrice: 현재가
        fundingRate: 펀딩비율

    Returns:
        펀딩비 지급액 (양수: 수령, 음수: 지불)
    """
    notionalValue = abs(positionSize) * markPrice
    fundingPayment = -notionalValue * fundingRate

    # LONG일 때: 음의 펀딩비면 수령, 양의 펀딩비면 지불
    # SHORT일 때: 양의 펀딩비면 수령, 음의 펀딩비면 지불
    if positionSize < 0:  # SHORT
        fundingPayment = -fundingPayment

    return fundingPayment
```

**사용 예시**:
```python
from common.lib.position_calculator import (
    calculateLiquidationPrice,
    calculateUnrealizedPnl,
    calculatePositionSizeFromMargin
)

# 청산가 계산
liquidationPrice = calculateLiquidationPrice(
    entryPrice=50000.0,
    leverage=10.0,
    side='LONG'
)
# Result: $45,250 (50000 × (1 - 1/10 + 0.005))

# 미실현 손익 계산
unrealizedPnl = calculateUnrealizedPnl(
    side='LONG',
    entryPrice=50000.0,
    markPrice=51000.0,
    size=0.1
)
# Result: $100 ((51000 - 50000) × 0.1)

# 포지션 크기 계산
positionSize = calculatePositionSizeFromMargin(
    availableMargin=1000.0,
    entryPrice=50000.0,
    leverage=10.0,
    marginUsagePercent=0.5
)
# Result: 0.1 BTC ($500 × 10 / $50000)
```

---

### 3. RiskManager (리스크 관리)

**파일**: `common/lib/risk_manager.py`

**목적**: 중앙화된 리스크 관리 및 포지션 제한

**핵심 클래스**:
```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class RiskLimits:
    """리스크 제한 설정"""
    maxPositionSizeUsd: float = 10000.0  # DEX당 최대 포지션 크기
    maxTotalExposureUsd: float = 50000.0  # 전체 DEX 총 노출
    maxLeverage: float = 10.0
    maxDrawdownPercent: float = 15.0
    maxDailyLossUsd: float = 500.0
    maxDailyTradesPerDex: int = 200
    minAccountBalanceUsd: float = 1000.0

@dataclass
class PositionRisk:
    """포지션 리스크 정보"""
    dexName: str
    symbol: str
    side: str
    sizeUsd: float
    leverage: float
    unrealizedPnl: float
    liquidationPrice: float
    distanceToLiquidation: float  # %

class RiskManager:
    """통합 리스크 관리자"""

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.positions: Dict[str, List[PositionRisk]] = {}
        self.dailyPnl: Dict[str, float] = {}  # date -> pnl
        self.dailyTradeCount: Dict[str, Dict[str, int]] = {}  # date -> dex -> count
        self.peakBalance: float = 0.0
        self.currentBalance: float = 0.0

    def updateBalance(self, balance: float):
        """잔고 업데이트 및 피크 추적"""
        self.currentBalance = balance
        if balance > self.peakBalance:
            self.peakBalance = balance

    def getCurrentDrawdown(self) -> float:
        """현재 드로우다운 계산"""
        if self.peakBalance == 0:
            return 0.0

        drawdown = (self.peakBalance - self.currentBalance) / self.peakBalance * 100
        return drawdown

    def checkDrawdownLimit(self) -> bool:
        """드로우다운 제한 체크"""
        currentDrawdown = self.getCurrentDrawdown()

        if currentDrawdown >= self.limits.maxDrawdownPercent:
            return False  # 드로우다운 초과

        return True

    def checkDailyLossLimit(self) -> bool:
        """일일 손실 제한 체크"""
        today = datetime.now().date().isoformat()
        dailyPnl = self.dailyPnl.get(today, 0.0)

        if dailyPnl <= -self.limits.maxDailyLossUsd:
            return False  # 일일 손실 초과

        return True

    def checkDailyTradeLimit(self, dexName: str) -> bool:
        """DEX별 일일 거래 횟수 제한 체크"""
        today = datetime.now().date().isoformat()

        if today not in self.dailyTradeCount:
            self.dailyTradeCount[today] = {}

        tradeCount = self.dailyTradeCount[today].get(dexName, 0)

        if tradeCount >= self.limits.maxDailyTradesPerDex:
            return False  # 일일 거래 횟수 초과

        return True

    def checkPositionSize(self, dexName: str, newPositionSizeUsd: float) -> bool:
        """포지션 크기 제한 체크"""
        if newPositionSizeUsd > self.limits.maxPositionSizeUsd:
            return False

        return True

    def checkTotalExposure(self, newPositionSizeUsd: float) -> bool:
        """전체 노출 제한 체크"""
        totalExposure = sum(
            sum(pos.sizeUsd for pos in positions)
            for positions in self.positions.values()
        )

        if totalExposure + newPositionSizeUsd > self.limits.maxTotalExposureUsd:
            return False

        return True

    def canOpenPosition(
        self,
        dexName: str,
        positionSizeUsd: float
    ) -> tuple[bool, Optional[str]]:
        """
        포지션 진입 가능 여부 체크

        Returns:
            (허용 여부, 거부 사유)
        """
        # 1. 드로우다운 체크
        if not self.checkDrawdownLimit():
            return False, f"Max drawdown exceeded: {self.getCurrentDrawdown():.2f}%"

        # 2. 일일 손실 체크
        if not self.checkDailyLossLimit():
            today = datetime.now().date().isoformat()
            return False, f"Daily loss limit exceeded: ${self.dailyPnl[today]:.2f}"

        # 3. 일일 거래 횟수 체크
        if not self.checkDailyTradeLimit(dexName):
            return False, f"Daily trade limit exceeded for {dexName}"

        # 4. 포지션 크기 체크
        if not self.checkPositionSize(dexName, positionSizeUsd):
            return False, f"Position size exceeds limit: ${positionSizeUsd:.2f}"

        # 5. 전체 노출 체크
        if not self.checkTotalExposure(positionSizeUsd):
            return False, "Total exposure limit exceeded"

        # 6. 최소 잔고 체크
        if self.currentBalance < self.limits.minAccountBalanceUsd:
            return False, f"Account balance below minimum: ${self.currentBalance:.2f}"

        return True, None

    def recordTrade(self, dexName: str, pnl: float):
        """거래 기록"""
        today = datetime.now().date().isoformat()

        # 일일 손익 업데이트
        if today not in self.dailyPnl:
            self.dailyPnl[today] = 0.0
        self.dailyPnl[today] += pnl

        # 일일 거래 횟수 업데이트
        if today not in self.dailyTradeCount:
            self.dailyTradeCount[today] = {}
        if dexName not in self.dailyTradeCount[today]:
            self.dailyTradeCount[today][dexName] = 0
        self.dailyTradeCount[today][dexName] += 1

    def updatePositions(self, dexName: str, positions: List[PositionRisk]):
        """포지션 업데이트"""
        self.positions[dexName] = positions

    def getPositionSummary(self) -> Dict:
        """포지션 요약 정보"""
        totalExposure = sum(
            sum(pos.sizeUsd for pos in positions)
            for positions in self.positions.values()
        )

        totalUnrealizedPnl = sum(
            sum(pos.unrealizedPnl for pos in positions)
            for positions in self.positions.values()
        )

        return {
            'totalExposure': totalExposure,
            'totalUnrealizedPnl': totalUnrealizedPnl,
            'currentDrawdown': self.getCurrentDrawdown(),
            'currentBalance': self.currentBalance,
            'peakBalance': self.peakBalance,
            'positionCount': sum(len(positions) for positions in self.positions.values())
        }
```

**사용 예시**:
```python
from common.lib.risk_manager import RiskManager, RiskLimits, PositionRisk

# 리스크 관리자 초기화
riskLimits = RiskLimits(
    maxPositionSizeUsd=10000.0,
    maxTotalExposureUsd=50000.0,
    maxDrawdownPercent=15.0,
    maxDailyLossUsd=500.0
)
riskManager = RiskManager(riskLimits)
riskManager.updateBalance(10000.0)

# 포지션 진입 전 체크
canOpen, reason = riskManager.canOpenPosition(
    dexName='apex',
    positionSizeUsd=5000.0
)

if canOpen:
    # 포지션 진입
    executeOrder(...)

    # 거래 기록
    riskManager.recordTrade(dexName='apex', pnl=10.0)
else:
    print(f"Cannot open position: {reason}")

# 포지션 요약
summary = riskManager.getPositionSummary()
print(f"Total Exposure: ${summary['totalExposure']:.2f}")
print(f"Current Drawdown: {summary['currentDrawdown']:.2f}%")
```

---

### 4. VolumeTracker (거래량 모니터링)

**파일**: `common/lib/volume_tracker.py`

**목적**: DEX별 거래량 추적 및 목표 달성 모니터링
- **기본 목표**: 월 $1M (최소 목표)
- **확장 가능**: monthlyTargetUsd 파라미터로 $2M, $5M, $10M 등 조정 가능
- **DEX 규모 대응**: Top 50 진입 위해 목표 상향 조정 지원

**핵심 클래스**:
```python
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

@dataclass
class VolumeMetrics:
    """거래량 메트릭"""
    dexName: str
    symbol: str
    dailyVolumeUsd: float
    monthlyVolumeUsd: float
    tradeCount: int
    avgTradeSize: float
    targetProgress: float  # 월 $1M 대비 진행률 (%)

class VolumeTracker:
    """거래량 모니터링 시스템"""

    def __init__(self, monthlyTargetUsd: float = 1_000_000.0):
        """
        Args:
            monthlyTargetUsd: 월 목표 거래량 (기본값: $1M)
        """
        self.monthlyTargetUsd = monthlyTargetUsd

        # 거래 기록: {date: {dex: {symbol: [trades]}}}
        self.trades: Dict[str, Dict[str, Dict[str, List[Dict]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )

    def recordTrade(
        self,
        dexName: str,
        symbol: str,
        sizeUsd: float,
        timestamp: datetime = None
    ):
        """
        거래 기록

        Args:
            dexName: DEX 이름
            symbol: 거래 심볼
            sizeUsd: 거래 금액 (USD)
            timestamp: 거래 시각 (기본값: 현재)
        """
        if timestamp is None:
            timestamp = datetime.now()

        dateKey = timestamp.date().isoformat()

        trade = {
            'sizeUsd': sizeUsd,
            'timestamp': timestamp.isoformat()
        }

        self.trades[dateKey][dexName][symbol].append(trade)

    def getDailyVolume(self, dexName: str, date: str = None) -> float:
        """
        일일 거래량 조회

        Args:
            dexName: DEX 이름
            date: 날짜 (YYYY-MM-DD, 기본값: 오늘)

        Returns:
            일일 총 거래량 (USD)
        """
        if date is None:
            date = datetime.now().date().isoformat()

        if date not in self.trades or dexName not in self.trades[date]:
            return 0.0

        totalVolume = sum(
            sum(trade['sizeUsd'] for trade in trades)
            for trades in self.trades[date][dexName].values()
        )

        return totalVolume

    def getMonthlyVolume(
        self,
        dexName: str,
        yearMonth: str = None
    ) -> float:
        """
        월별 거래량 조회

        Args:
            dexName: DEX 이름
            yearMonth: 년-월 (YYYY-MM, 기본값: 이번 달)

        Returns:
            월 총 거래량 (USD)
        """
        if yearMonth is None:
            yearMonth = datetime.now().strftime('%Y-%m')

        totalVolume = 0.0

        for dateKey, dexData in self.trades.items():
            if dateKey.startswith(yearMonth) and dexName in dexData:
                for symbol, trades in dexData[dexName].items():
                    totalVolume += sum(trade['sizeUsd'] for trade in trades)

        return totalVolume

    def getMonthlyTradeCount(
        self,
        dexName: str,
        yearMonth: str = None
    ) -> int:
        """
        월별 거래 횟수 조회

        Args:
            dexName: DEX 이름
            yearMonth: 년-월 (YYYY-MM, 기본값: 이번 달)

        Returns:
            월 총 거래 횟수
        """
        if yearMonth is None:
            yearMonth = datetime.now().strftime('%Y-%m')

        totalCount = 0

        for dateKey, dexData in self.trades.items():
            if dateKey.startswith(yearMonth) and dexName in dexData:
                for symbol, trades in dexData[dexName].items():
                    totalCount += len(trades)

        return totalCount

    def getTargetProgress(
        self,
        dexName: str,
        yearMonth: str = None
    ) -> float:
        """
        월 목표 대비 진행률 계산

        Args:
            dexName: DEX 이름
            yearMonth: 년-월 (YYYY-MM, 기본값: 이번 달)

        Returns:
            진행률 (%)
        """
        monthlyVolume = self.getMonthlyVolume(dexName, yearMonth)
        progress = (monthlyVolume / self.monthlyTargetUsd) * 100

        return progress

    def getVolumeMetrics(
        self,
        dexName: str,
        symbol: str = 'ALL',
        yearMonth: str = None
    ) -> VolumeMetrics:
        """
        거래량 메트릭 조회

        Args:
            dexName: DEX 이름
            symbol: 거래 심볼 ('ALL'이면 전체)
            yearMonth: 년-월 (YYYY-MM, 기본값: 이번 달)

        Returns:
            VolumeMetrics 객체
        """
        if yearMonth is None:
            yearMonth = datetime.now().strftime('%Y-%m')

        # 일일 거래량
        today = datetime.now().date().isoformat()
        dailyVolume = self.getDailyVolume(dexName, today)

        # 월별 거래량
        monthlyVolume = self.getMonthlyVolume(dexName, yearMonth)

        # 월별 거래 횟수
        tradeCount = self.getMonthlyTradeCount(dexName, yearMonth)

        # 평균 거래 크기
        avgTradeSize = monthlyVolume / tradeCount if tradeCount > 0 else 0.0

        # 목표 진행률
        targetProgress = self.getTargetProgress(dexName, yearMonth)

        return VolumeMetrics(
            dexName=dexName,
            symbol=symbol,
            dailyVolumeUsd=dailyVolume,
            monthlyVolumeUsd=monthlyVolume,
            tradeCount=tradeCount,
            avgTradeSize=avgTradeSize,
            targetProgress=targetProgress
        )

    def getRemainingVolumeToTarget(
        self,
        dexName: str,
        yearMonth: str = None
    ) -> float:
        """
        목표 달성까지 필요한 거래량 계산

        Args:
            dexName: DEX 이름
            yearMonth: 년-월 (YYYY-MM, 기본값: 이번 달)

        Returns:
            필요 거래량 (USD)
        """
        monthlyVolume = self.getMonthlyVolume(dexName, yearMonth)
        remaining = max(0, self.monthlyTargetUsd - monthlyVolume)

        return remaining

    def getRecommendedDailyVolume(
        self,
        dexName: str,
        yearMonth: str = None
    ) -> float:
        """
        월 목표 달성을 위한 일일 권장 거래량 계산

        Args:
            dexName: DEX 이름
            yearMonth: 년-월 (YYYY-MM, 기본값: 이번 달)

        Returns:
            일일 권장 거래량 (USD)
        """
        if yearMonth is None:
            yearMonth = datetime.now().strftime('%Y-%m')

        # 남은 일수 계산
        now = datetime.now()
        lastDayOfMonth = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        remainingDays = (lastDayOfMonth.date() - now.date()).days + 1

        if remainingDays <= 0:
            return 0.0

        # 필요 거래량
        remaining = self.getRemainingVolumeToTarget(dexName, yearMonth)

        # 일일 권장 거래량
        recommendedDaily = remaining / remainingDays

        return recommendedDaily

    def getSummary(self, dexName: str = None) -> Dict:
        """
        전체 또는 DEX별 거래량 요약

        Args:
            dexName: DEX 이름 (None이면 전체)

        Returns:
            요약 정보 딕셔너리
        """
        yearMonth = datetime.now().strftime('%Y-%m')

        if dexName:
            # DEX별 요약
            metrics = self.getVolumeMetrics(dexName)
            remaining = self.getRemainingVolumeToTarget(dexName)
            recommended = self.getRecommendedDailyVolume(dexName)

            return {
                'dexName': dexName,
                'monthlyVolume': metrics.monthlyVolumeUsd,
                'targetProgress': metrics.targetProgress,
                'remainingVolume': remaining,
                'recommendedDailyVolume': recommended,
                'tradeCount': metrics.tradeCount,
                'avgTradeSize': metrics.avgTradeSize
            }
        else:
            # 전체 DEX 요약
            allDexNames = set()
            for dexData in self.trades.values():
                allDexNames.update(dexData.keys())

            summaries = {}
            for dex in allDexNames:
                summaries[dex] = self.getSummary(dex)

            return summaries
```

**사용 예시**:
```python
from common.lib.volume_tracker import VolumeTracker

# 기본 초기화 (월 $1M 목표)
volumeTracker = VolumeTracker(monthlyTargetUsd=1_000_000.0)

# 확장 목표 설정 예시 (Top 50 진입 위해)
volumeTrackerHigh = VolumeTracker(monthlyTargetUsd=5_000_000.0)  # $5M 목표

# 거래 기록
volumeTracker.recordTrade(
    dexName='apex',
    symbol='BTC-USDT',
    sizeUsd=1000.0
)

# 월별 거래량 조회
monthlyVolume = volumeTracker.getMonthlyVolume('apex')
print(f"Apex Monthly Volume: ${monthlyVolume:,.2f}")

# 목표 진행률 확인
progress = volumeTracker.getTargetProgress('apex')
print(f"Target Progress: {progress:.2f}%")

# 일일 권장 거래량
recommended = volumeTracker.getRecommendedDailyVolume('apex')
print(f"Recommended Daily Volume: ${recommended:,.2f}")

# 전체 요약
summary = volumeTracker.getSummary('apex')
print(f"""
Apex Summary:
  Monthly Volume: ${summary['monthlyVolume']:,.2f}
  Target Progress: {summary['targetProgress']:.2f}%
  Remaining: ${summary['remainingVolume']:,.2f}
  Recommended Daily: ${summary['recommendedDailyVolume']:,.2f}
  Trade Count: {summary['tradeCount']}
  Avg Trade Size: ${summary['avgTradeSize']:,.2f}
""")
```

**포인트 파밍 효율 계산**:
```python
# 포인트 파밍 효율 계산 예시
def calculatePointFarmingEfficiency(
    volumeTracker: VolumeTracker,
    dexName: str,
    estimatedPointsPerMillion: float,
    estimatedPointValue: float,
    tradingCost: float
) -> Dict:
    """
    포인트 파밍 효율 계산

    Args:
        volumeTracker: VolumeTracker 인스턴스
        dexName: DEX 이름
        estimatedPointsPerMillion: $1M당 예상 포인트
        estimatedPointValue: 포인트당 예상 가치 (USD)
        tradingCost: 월 거래 비용 (USD)

    Returns:
        효율 계산 결과
    """
    monthlyVolume = volumeTracker.getMonthlyVolume(dexName)

    # 예상 포인트 수
    estimatedPoints = (monthlyVolume / 1_000_000.0) * estimatedPointsPerMillion

    # 예상 포인트 가치
    estimatedValue = estimatedPoints * estimatedPointValue

    # 순이익 (포인트 가치 - 거래 비용)
    netProfit = estimatedValue - tradingCost

    # 효율 (순이익 / 거래 비용)
    efficiency = (netProfit / tradingCost * 100) if tradingCost > 0 else 0

    return {
        'monthlyVolume': monthlyVolume,
        'estimatedPoints': estimatedPoints,
        'estimatedValue': estimatedValue,
        'tradingCost': tradingCost,
        'netProfit': netProfit,
        'efficiency': efficiency  # %
    }

# 사용 예시: Apex 포인트 파밍 효율
apexEfficiency = calculatePointFarmingEfficiency(
    volumeTracker=volumeTracker,
    dexName='apex',
    estimatedPointsPerMillion=100.0,  # $1M당 100 포인트 (보수적)
    estimatedPointValue=1.0,           # 1 포인트 = $1 (보수적)
    tradingCost=100.0                  # 월 $100 비용
)

print(f"""
Apex Point Farming Efficiency:
  Monthly Volume: ${apexEfficiency['monthlyVolume']:,.2f}
  Estimated Points: {apexEfficiency['estimatedPoints']:,.0f}
  Estimated Value: ${apexEfficiency['estimatedValue']:,.2f}
  Trading Cost: ${apexEfficiency['tradingCost']:,.2f}
  Net Profit: ${apexEfficiency['netProfit']:,.2f}
  Efficiency: {apexEfficiency['efficiency']:.1f}%
""")
```

---

## 전략 프레임워크

### 1. BaseStrategy (전략 추상 클래스)

**파일**: `common/strategies/base_strategy.py`

**목적**: 모든 전략이 구현해야 하는 기본 인터페이스

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from common.lib.base_dex_client import BaseDexClient, Order
from common.lib.risk_manager import RiskManager

class BaseStrategy(ABC):
    """전략 추상 클래스"""

    def __init__(
        self,
        dexClient: BaseDexClient,
        riskManager: RiskManager,
        config: Dict
    ):
        self.dexClient = dexClient
        self.riskManager = riskManager
        self.config = config
        self.isActive = False

    @abstractmethod
    def initialize(self) -> bool:
        """전략 초기화"""
        pass

    @abstractmethod
    def generateSignals(self, marketData: Dict) -> List[Order]:
        """시그널 생성"""
        pass

    @abstractmethod
    def executeOrders(self, orders: List[Order]) -> List[Dict]:
        """주문 실행"""
        pass

    @abstractmethod
    def stop(self):
        """전략 중단"""
        pass

    def start(self):
        """전략 시작"""
        if not self.initialize():
            raise RuntimeError("Strategy initialization failed")

        self.isActive = True

    def pause(self):
        """전략 일시정지"""
        self.isActive = False

    def resume(self):
        """전략 재개"""
        self.isActive = True
```

---

### 2. HighFrequencyStrategy (고빈도 전략)

**파일**: `common/strategies/high_frequency.py`

**목적**: Apex, Paradex 등에서 사용하는 고빈도 소액 거래 전략

```python
from typing import Dict, List
import random
from common.strategies.base_strategy import BaseStrategy
from common.lib.base_dex_client import Order

class HighFrequencyStrategy(BaseStrategy):
    """고빈도 소액 거래 전략"""

    def initialize(self) -> bool:
        """전략 초기화"""
        # 설정 파라미터 로드
        self.symbol = self.config.get('symbol', 'BTC-USDT')
        self.targetSpread = self.config.get('targetSpread', 0.001)  # 0.1%
        self.minProfitRate = self.config.get('minProfitRate', 0.0005)  # 0.05%
        self.maxProfitRate = self.config.get('maxProfitRate', 0.001)  # 0.1%
        self.stopLossRate = self.config.get('stopLossRate', 0.0003)  # 0.03%
        self.positionSize = self.config.get('positionSize', 0.001)  # 0.001 BTC
        self.maxHoldingMinutes = self.config.get('maxHoldingMinutes', 30)

        # DEX 연결 확인
        if not self.dexClient.isConnected:
            return False

        return True

    def generateSignals(self, marketData: Dict) -> List[Order]:
        """시그널 생성"""
        orders = []

        # 현재가 조회
        ticker = marketData.get('ticker', {})
        currentPrice = float(ticker.get('price', 0))

        if currentPrice == 0:
            return orders

        # Spread 체크
        bid = float(ticker.get('bid', 0))
        ask = float(ticker.get('ask', 0))

        if bid == 0 or ask == 0:
            return orders

        spread = (ask - bid) / currentPrice

        # Spread가 목표 이상이면 주문 생성
        if spread >= self.targetSpread:
            # 목표 수익률 랜덤 설정 (human-like)
            targetProfitRate = random.uniform(self.minProfitRate, self.maxProfitRate)

            # BUY 시그널
            buyOrder = Order(
                symbol=self.symbol,
                side='BUY',
                orderType='LIMIT',
                size=str(self.positionSize),
                price=str(currentPrice * (1 - targetProfitRate)),
                timeInForce='POST_ONLY',
                reduceOnly=False
            )
            orders.append(buyOrder)

        return orders

    def executeOrders(self, orders: List[Order]) -> List[Dict]:
        """주문 실행"""
        results = []

        for order in orders:
            # 리스크 체크
            positionSizeUsd = float(order.size) * float(order.price or 0)
            canOpen, reason = self.riskManager.canOpenPosition(
                dexName=self.dexClient.__class__.__name__,
                positionSizeUsd=positionSizeUsd
            )

            if not canOpen:
                print(f"Order blocked by risk manager: {reason}")
                continue

            # 주문 실행
            try:
                result = self.dexClient.createOrder(order)
                results.append(result)

                # 거래 기록
                self.riskManager.recordTrade(
                    dexName=self.dexClient.__class__.__name__,
                    pnl=0.0  # 체결 시 업데이트
                )
            except Exception as e:
                print(f"Order execution failed: {e}")

        return results

    def stop(self):
        """전략 중단"""
        self.isActive = False
        # 모든 포지션 청산
        positions = self.dexClient.getPositions()
        for position in positions:
            # 청산 로직 (생략)
            pass
```

---

### 3. DeltaNeutralStrategy (델타 뉴트럴 전략)

**파일**: `common/strategies/delta_neutral.py`

**목적**: Apex ↔ Paradex 간 델타 뉴트럴 펀딩비 차익거래

```python
from typing import Dict, List, Tuple
import random
from datetime import datetime, timedelta
from common.strategies.base_strategy import BaseStrategy
from common.lib.base_dex_client import BaseDexClient, Order

class DeltaNeutralStrategy(BaseStrategy):
    """델타 뉴트럴 펀딩비 차익거래 전략"""

    def __init__(
        self,
        dexClient1: BaseDexClient,  # Apex
        dexClient2: BaseDexClient,  # Paradex
        riskManager,
        config: Dict
    ):
        super().__init__(dexClient1, riskManager, config)
        self.dexClient1 = dexClient1  # Apex
        self.dexClient2 = dexClient2  # Paradex

    def initialize(self) -> bool:
        """전략 초기화"""
        self.symbol = self.config.get('symbol', 'BTC-USDT')
        self.positionSize = self.config.get('positionSize', 0.01)  # 0.01 BTC

        # Human-like 타이밍 파라미터
        self.minEntryMinutesBefore = self.config.get('minEntryMinutesBefore', 15)
        self.maxEntryMinutesBefore = self.config.get('maxEntryMinutesBefore', 30)
        self.minHoldingMinutes = self.config.get('minHoldingMinutes', 3)
        self.maxHoldingMinutes = self.config.get('maxHoldingMinutes', 45)

        # 펀딩비 지급 시간 (UTC)
        self.fundingTimes = [0, 8, 16]  # 00:00, 08:00, 16:00 UTC

        return True

    def getNextFundingTime(self) -> datetime:
        """다음 펀딩비 지급 시각 계산"""
        now = datetime.utcnow()
        currentHour = now.hour

        # 다음 펀딩 시간 찾기
        for hour in self.fundingTimes:
            if currentHour < hour:
                nextFunding = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                return nextFunding

        # 오늘 남은 펀딩 시간 없으면 내일 첫 번째 시간
        nextFunding = (now + timedelta(days=1)).replace(
            hour=self.fundingTimes[0],
            minute=0,
            second=0,
            microsecond=0
        )
        return nextFunding

    def calculateEntryTime(self, fundingTime: datetime) -> datetime:
        """진입 시각 계산 (human-like randomization)"""
        entryMinutesBefore = random.randint(
            self.minEntryMinutesBefore,
            self.maxEntryMinutesBefore
        )
        entryTime = fundingTime - timedelta(minutes=entryMinutesBefore)
        return entryTime

    def calculateExitTime(self, entryTime: datetime, fundingTime: datetime) -> datetime:
        """청산 시각 계산 (human-like randomization)"""
        # 홀딩 시간 랜덤 생성
        holdingMinutes = random.randint(
            self.minHoldingMinutes,
            self.maxHoldingMinutes
        )

        exitTime = entryTime + timedelta(minutes=holdingMinutes)
        return exitTime

    def analyzeFundingOpportunity(self) -> Tuple[str, float]:
        """
        펀딩비 차익거래 기회 분석

        Returns:
            (전략, 펀딩비 차이)
            전략: 'APEX_LONG_PARADEX_SHORT' or 'APEX_SHORT_PARADEX_LONG'
        """
        # Apex 펀딩비 조회
        apexFunding = self.dexClient1.getFundingRate(self.symbol)
        apexFundingRate = float(apexFunding.get('fundingRate', 0))

        # Paradex 펀딩비 조회
        paradexFunding = self.dexClient2.getFundingRate(self.symbol)
        paradexFundingRate = float(paradexFunding.get('fundingRate', 0))

        # 펀딩비 차이 계산
        fundingDiff = apexFundingRate - paradexFundingRate

        # 전략 결정
        if fundingDiff > 0:
            # Apex 펀딩비가 더 높음 → Apex LONG, Paradex SHORT
            strategy = 'APEX_LONG_PARADEX_SHORT'
        else:
            # Paradex 펀딩비가 더 높음 → Apex SHORT, Paradex LONG
            strategy = 'APEX_SHORT_PARADEX_LONG'

        return strategy, abs(fundingDiff)

    def generateSignals(self, marketData: Dict) -> List[Tuple[Order, Order]]:
        """델타 뉴트럴 시그널 생성 (양쪽 DEX 동시)"""
        signals = []

        # 현재 시각
        now = datetime.utcnow()

        # 다음 펀딩 시간
        nextFunding = self.getNextFundingTime()

        # 진입 시각 계산
        entryTime = self.calculateEntryTime(nextFunding)

        # 진입 시각이 아니면 시그널 없음
        if now < entryTime:
            return signals

        # 펀딩비 차익거래 기회 분석
        strategy, fundingDiff = self.analyzeFundingOpportunity()

        # 최소 펀딩비 차이 체크 (0.01% 이상)
        if fundingDiff < 0.0001:
            return signals

        # 현재가 조회
        apexTicker = marketData.get('apex_ticker', {})
        paradexTicker = marketData.get('paradex_ticker', {})

        apexPrice = float(apexTicker.get('price', 0))
        paradexPrice = float(paradexTicker.get('price', 0))

        if apexPrice == 0 or paradexPrice == 0:
            return signals

        # 가격 분산 (human-like, ±0.01%)
        priceVariance1 = random.uniform(-0.0001, 0.0001)
        priceVariance2 = random.uniform(-0.0001, 0.0001)

        # 주문 생성
        if strategy == 'APEX_LONG_PARADEX_SHORT':
            # Apex LONG
            apexOrder = Order(
                symbol=self.symbol,
                side='BUY',
                orderType='LIMIT',
                size=str(self.positionSize),
                price=str(apexPrice * (1 + priceVariance1)),
                timeInForce='POST_ONLY',
                reduceOnly=False
            )

            # Paradex SHORT
            paradexOrder = Order(
                symbol=self.symbol,
                side='SELL',
                orderType='LIMIT',
                size=str(self.positionSize),
                price=str(paradexPrice * (1 + priceVariance2)),
                timeInForce='POST_ONLY',
                reduceOnly=False
            )
        else:
            # Apex SHORT
            apexOrder = Order(
                symbol=self.symbol,
                side='SELL',
                orderType='LIMIT',
                size=str(self.positionSize),
                price=str(apexPrice * (1 + priceVariance1)),
                timeInForce='POST_ONLY',
                reduceOnly=False
            )

            # Paradex LONG
            paradexOrder = Order(
                symbol=self.symbol,
                side='BUY',
                orderType='LIMIT',
                size=str(self.positionSize),
                price=str(paradexPrice * (1 + priceVariance2)),
                timeInForce='POST_ONLY',
                reduceOnly=False
            )

        signals.append((apexOrder, paradexOrder))
        return signals

    def executeOrders(self, orderPairs: List[Tuple[Order, Order]]) -> List[Dict]:
        """델타 뉴트럴 주문 실행 (양쪽 동시)"""
        results = []

        for apexOrder, paradexOrder in orderPairs:
            try:
                # Apex 주문 실행
                apexResult = self.dexClient1.createOrder(apexOrder)

                # Paradex 주문 실행
                paradexResult = self.dexClient2.createOrder(paradexOrder)

                results.append({
                    'apex': apexResult,
                    'paradex': paradexResult,
                    'strategy': 'delta_neutral',
                    'timestamp': datetime.utcnow().isoformat()
                })

                # 거래 기록
                self.riskManager.recordTrade(
                    dexName='delta_neutral',
                    pnl=0.0  # 청산 시 업데이트
                )

            except Exception as e:
                print(f"Delta neutral order execution failed: {e}")

                # 한쪽만 체결되면 위험 → 즉시 청산
                # (청산 로직 생략)

        return results

    def stop(self):
        """전략 중단"""
        self.isActive = False
        # 양쪽 DEX 모든 포지션 청산
        # (생략)
```

---

## 데이터 관리

### 데이터베이스 스키마

**파일**: `common/database/models.py`

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    """거래 내역"""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    dexName = Column(String(50), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    orderId = Column(String(100), nullable=False, unique=True)
    side = Column(String(10), nullable=False)  # 'BUY' or 'SELL'
    orderType = Column(String(20), nullable=False)  # 'LIMIT' or 'MARKET'
    size = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    feeRate = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    strategy = Column(String(50), nullable=False, index=True)
    createdAt = Column(DateTime, default=datetime.utcnow, index=True)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Position(Base):
    """포지션 스냅샷"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    dexName = Column(String(50), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    size = Column(Float, nullable=False)
    entryPrice = Column(Float, nullable=False)
    markPrice = Column(Float, nullable=False)
    unrealizedPnl = Column(Float, nullable=False)
    leverage = Column(Float, nullable=False)
    liquidationPrice = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class DailyPerformance(Base):
    """일일 성과"""
    __tablename__ = 'daily_performance'

    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD
    totalPnl = Column(Float, nullable=False)
    tradeCount = Column(Integer, nullable=False)
    winCount = Column(Integer, nullable=False)
    lossCount = Column(Integer, nullable=False)
    winRate = Column(Float, nullable=False)
    avgWin = Column(Float, nullable=False)
    avgLoss = Column(Float, nullable=False)
    maxDrawdown = Column(Float, nullable=False)
    sharpeRatio = Column(Float, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
```

---

## 모니터링 시스템

### Grafana 메트릭

**파일**: `common/monitoring/metrics_collector.py`

**주요 메트릭**:
```yaml
거래 메트릭:
  - total_trades_count: 총 거래 횟수
  - trades_per_dex: DEX별 거래 횟수
  - daily_trade_volume: 일일 거래량 (USD)

성과 메트릭:
  - total_pnl: 총 손익
  - daily_pnl: 일일 손익
  - unrealized_pnl: 미실현 손익
  - win_rate: 승률
  - sharpe_ratio: Sharpe Ratio

리스크 메트릭:
  - current_drawdown: 현재 드로우다운
  - max_drawdown: 최대 드로우다운
  - total_exposure: 총 노출
  - leverage_usage: 레버리지 사용률

포지션 메트릭:
  - active_positions_count: 활성 포지션 수
  - avg_position_size: 평균 포지션 크기
  - distance_to_liquidation: 청산가까지 거리 (%)
```

---

## 백테스팅 프레임워크

**파일**: `common/backtesting/backtest_engine.py`

**핵심 기능**:
- 과거 데이터 리플레이
- 전략 시뮬레이션
- 성과 분석 (Sharpe Ratio, MDD, Win Rate)
- 비용 정확한 반영 (Maker/Taker 수수료)

---

## 구현 우선순위

### Phase 1 (Week 1-2): 핵심 라이브러리
- [x] `BaseDexClient` 추상 클래스
- [x] `PositionCalculator` 계산 유틸리티
- [x] `RiskManager` 리스크 관리
- [ ] Lint 검사 통과 (flake8, black, mypy)

### Phase 2 (Week 3-4): 전략 프레임워크
- [ ] `BaseStrategy` 추상 클래스
- [ ] `HighFrequencyStrategy` 구현
- [ ] `DeltaNeutralStrategy` 구현
- [ ] Lint 검사 통과 (flake8, black, mypy)

### Phase 3 (Week 5-6): 데이터 및 모니터링
- [ ] PostgreSQL 스키마 생성
- [ ] Redis 캐싱 구현
- [ ] Grafana 대시보드 설정
- [ ] 알림 시스템 (Telegram/Slack)
- [ ] Lint 검사 통과 (flake8, black, mypy)

### Phase 4 (Week 7-8): 백테스팅 및 검증
- [ ] 백테스팅 엔진 구현
- [ ] 과거 데이터 수집
- [ ] 전략 검증 및 파라미터 최적화
- [ ] Lint 검사 통과 (flake8, black, mypy)

---

## 테스트 전략

### 유닛 테스트
```python
# common/tests/test_position_calculator.py
def test_calculate_liquidation_price_long():
    liquidationPrice = calculateLiquidationPrice(
        entryPrice=50000.0,
        leverage=10.0,
        side='LONG'
    )
    assert abs(liquidationPrice - 45250.0) < 1.0  # 50000 × (1 - 1/10 + 0.005)

def test_calculate_unrealized_pnl_long():
    pnl = calculateUnrealizedPnl(
        side='LONG',
        entryPrice=50000.0,
        markPrice=51000.0,
        size=0.1
    )
    assert abs(pnl - 100.0) < 0.01  # (51000 - 50000) × 0.1
```

### 통합 테스트
```python
# common/tests/test_strategies.py
def test_high_frequency_strategy():
    # Testnet에서 실제 전략 실행
    strategy = HighFrequencyStrategy(...)
    strategy.start()

    # 10분 실행
    time.sleep(600)

    # 결과 검증
    assert strategy.tradeCount >= 1
    assert strategy.totalPnl != 0
```

---

**Version**: 1.0
**Last Updated**: 2025-01-24
