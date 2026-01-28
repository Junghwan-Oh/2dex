# Hummingbot Avellaneda 전략 통합 요약

## 📚 학습한 허밍봇 핵심 개념

### 1. Reservation Price (예약 가격)
**공식**: `r = mid_price - q * γ * σ² * (T-t)`

**변수**:
- `r`: Reservation price (예약 가격)
- `mid_price`: 현재 시장 중간 가격
- `q`: 인벤토리 (양수 = Long, 음수 = Short)
- `γ` (gamma): 위험 회피 계수 (0.1)
- `σ` (sigma): 변동성 (0.02)
- `T`: 거래일 종료 시간 (정규화: 1)
- `t`: 현재 시간 (0~1 사이 값)

**작동 원리**:
```
Long 포지션 (q > 0):
  → inventory_adjustment > 0
  → reservation_price < mid_price
  → 매도 주문이 상대적으로 유리한 가격에 배치
  → 자연스럽게 Long 청산 방향으로 유도

Short 포지션 (q < 0):
  → inventory_adjustment < 0
  → reservation_price > mid_price
  → 매수 주문이 상대적으로 유리한 가격에 배치
  → 자연스럽게 Short 청산 방향으로 유도

Neutral (q = 0):
  → reservation_price = mid_price
  → 양방향 주문 균형 유지
```

### 2. 허밍봇 아키텍처 패턴

**핵심 원칙**: "바퀴를 재발명하지 마라"
- **Core Strategy**: 순수 Avellaneda 로직 (거래소 독립적)
- **Connector**: 거래소별 API 연동 레이어

**우리 구현**:
```
├── Core Strategy (전략 로직)
│   ├── calculate_optimal_spread()  # Avellaneda 수식 구현
│   ├── calculate_volatility()      # 변동성 계산
│   └── Reservation price 계산      # 인벤토리 리밸런싱
│
└── ApeX Connector (거래소 연동)
    ├── ApexClient                   # REST API 래퍼
    ├── ApexWebSocketMonitor         # 실시간 가격 피드
    ├── HttpPrivateSign              # 주문 생성 API
    └── Price/Size 라운딩            # 거래소별 제약사항
```

## ✅ 구현 완료 사항

### Phase 1: WebSocket 실시간 피드 통합 ✓
- `ApexWebSocketMonitor` 통합으로 실시간 가격 업데이트
- REST API 대신 WebSocket으로 지연시간 최소화

### Phase 2: 실제 주문 API 연동 ✓
- `HttpPrivateSign.create_order_v3()` 메서드 사용
- `configs_v3()` + `get_account_v3()` 초기화 필수
- Price rounding: `tickSize = 0.1` (ETH-USDT)
- Size rounding: `stepSize = 0.01`

### Phase 3: Reservation Price 로직 적용 ✓
**수정 파일**: `apex/avellaneda_client.py`

**변경 1**: `calculate_optimal_spread()` 메서드 (Line 485-555)
```python
# BEFORE (잘못됨):
def calculate_optimal_spread(self, dynamic_kappa) -> Tuple[float, float]:
    inventory_penalty = gamma * σ² * time_remaining  # 계산만 하고 사용 안함
    return bid_spread, ask_spread

# AFTER (허밍봇 방식):
def calculate_optimal_spread(self, dynamic_kappa, mid_price) -> Tuple[float, float, float]:
    inventory_adjustment = inventory * gamma * σ² * time_remaining
    reservation_price = mid_price - inventory_adjustment
    return reservation_price, bid_spread, ask_spread
```

**변경 2**: `place_maker_orders()` 메서드 (Line 582-590)
```python
# BEFORE (잘못됨):
mid_price = self.current_price
bid_price = mid_price * (1 - bid_spread)
ask_price = mid_price * (1 + ask_spread)

# AFTER (허밍봇 방식):
reservation_price, bid_spread, ask_spread = self.calculate_optimal_spread(...)
bid_price = reservation_price * (1 - bid_spread)
ask_price = reservation_price * (1 + ask_spread)
```

## 🔄 자동 리밸런싱 메커니즘

### 기존 방식 (잘못됨)
```
Long 포지션 누적 → Inventory limit 초과 → 강제 청산 필요
```

### 허밍봇 방식 (자연스러운 리밸런싱)
```
Long 포지션 누적:
  → reservation_price ↓
  → Ask price ↓ (매도가 낮아짐)
  → Bid price ↓ (매수가 낮아짐)
  → 매도 체결 확률 ↑, 매수 체결 확률 ↓
  → 자연스럽게 Long → Neutral 방향으로 이동

Short 포지션 누적:
  → reservation_price ↑
  → Ask price ↑ (매도가 높아짐)
  → Bid price ↑ (매수가 높아짐)
  → 매수 체결 확률 ↑, 매도 체결 확률 ↓
  → 자연스럽게 Short → Neutral 방향으로 이동
```

## 📋 남은 구현 과제

### 1. Order Size Asymmetry (eta 파라미터)
**목적**: 리밸런싱 속도 조절

```python
# 허밍봇 구현 참고
if inventory > 0:  # Long → 매도 주문 크기 증가
    bid_size = base_size * (1 - eta)
    ask_size = base_size * (1 + eta)
elif inventory < 0:  # Short → 매수 주문 크기 증가
    bid_size = base_size * (1 + eta)
    ask_size = base_size * (1 - eta)
```

**현재 상태**: 모든 주문 동일 크기 사용
**우선순위**: 중간 (reservation price가 더 중요)

### 2. Closing Time Mechanism
**목적**: 거래일 종료 시 강제 청산

```python
# T-t가 0에 가까워질수록
# reservation_price → mid_price로 수렴
# 인벤토리 효과 감소
```

**현재 상태**: `time_remaining` 계산은 있으나 closing logic 없음
**우선순위**: 낮음 (24시간 운영이므로 closing이 명확하지 않음)

### 3. 동적 파라미터 최적화
**Order Book Analyzer 활용**:
- `alpha`: 주문 도착률
- `kappa`: 시장 유동성
- `sigma`: 실시간 변동성

**현재 상태**: 계산은 되지만 활용도 낮음
**우선순위**: 낮음 (정적 파라미터로도 충분히 작동)

## 🧪 테스트 계획

### 테스트 1: Neutral 인벤토리에서 Reservation Price 확인
```bash
# 포지션 정리 후 (inventory ≈ 0)
python apex/deploy_testnet.py \
  --mode static \
  --environment mainnet \
  --symbol ETH-USDT \
  --duration 180 \
  --dry-run \
  --yes
```

**예상 로그**:
```
[Reservation Price] mid=$3,590.00, inventory=0.0000 → adjustment=+0.000% → r=$3,590.00
[DRY-RUN] Would place BID at $3,589.28 (spread: 0.020%), size: 0.0050 BTC
[DRY-RUN] Would place ASK at $3,590.72 (spread: 0.020%), size: 0.0050 BTC
```

### 테스트 2: Long 포지션에서 자동 리밸런싱
```bash
# Long 포지션 0.01 BTC 보유 시
python apex/deploy_testnet.py --mode static --yes
```

**예상 로그**:
```
[Reservation Price] mid=$3,590.00, inventory=0.0100 → adjustment=-0.150% → r=$3,584.61
[INFO] BID placed at $3,583.89 (낮아진 가격 - 체결 어려움)
[INFO] ASK placed at $3,585.33 (낮아진 가격 - 체결 쉬움)
→ 매도 주문이 더 쉽게 체결되어 Long → Neutral로 이동
```

### 테스트 3: 실제 거래 실행 (신중하게)
```bash
# 매우 짧은 시간으로 실전 테스트
python apex/deploy_testnet.py \
  --mode static \
  --environment mainnet \
  --symbol ETH-USDT \
  --duration 300 \
  --position-limit 0.005 \  # 작은 크기로 시작
  --yes
```

## 🎓 핵심 교훈

### 1. "바퀴를 재발명하지 마라"
- 허밍봇은 이미 검증된 구현을 제공
- 핵심 로직을 복사하고 connector만 교체
- 불필요한 리팩토링으로 시간 낭비 금지

### 2. Reservation Price의 중요성
- 단순히 spread 조정만으로는 리밸런싱 불가능
- 주문 가격 자체를 인벤토리에 따라 조정해야 함
- Mid price 대신 reservation price 기준으로 주문 생성

### 3. 작은 변경으로 큰 효과
- 단 2개 메서드 수정으로 자동 리밸런싱 구현
- Line 485-555: `calculate_optimal_spread()` 반환값 추가
- Line 582-590: `place_maker_orders()` 가격 계산 수정

## 📂 관련 파일

### 핵심 파일
- `apex/avellaneda_client.py`: 전략 로직 (주요 수정 파일)
- `apex/lib/apex_client.py`: ApeX API 래퍼
- `apex/common/monitoring/websocket_monitor.py`: 실시간 가격 피드
- `apex/deploy_testnet.py`: 배포 스크립트

### 로그 파일
- `logs/phase3_reservation_price_test.log`: Reservation price 테스트 로그

### 문서
- `claudedocs/hummingbot_integration_summary.md`: 이 문서
- 허밍봇 공식 소스: https://github.com/hummingbot/hummingbot/blob/master/hummingbot/strategy/avellaneda_market_making/avellaneda_market_making.pyx

## 🔗 참고 자료

### 허밍봇 공식 문서
- Architecture: https://hummingbot.org/developers/architecture/
- Avellaneda Strategy: https://hummingbot.org/strategies/avellaneda-market-making/
- Technical Deep Dive: https://hummingbot.org/blog/technical-deep-dive-into-the-avellaneda--stoikov-strategy/

### 학술 논문
- Avellaneda & Stoikov (2008): "High-frequency Trading in a Limit Order Book"

## 🚀 다음 세션 시작 시

1. **포지션 확인**: 현재 인벤토리 상태 체크
2. **Neutral 테스트**: 인벤토리 0 근처에서 reservation price 로그 확인
3. **실전 배포**: 작은 크기로 실제 거래 시작 (position_limit=0.005)
4. **모니터링**: 자동 리밸런싱이 제대로 작동하는지 관찰

---

**작성 일시**: 2025-11-11 21:11
**버전**: Phase 3 완료 (Reservation Price 구현)
**다음 목표**: Order Size Asymmetry (eta parameter) 구현 고려
