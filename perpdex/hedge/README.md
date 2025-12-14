# Delta Neutral Volume Farming Bot

Backpack + Lighter를 활용한 Delta Neutral 헷지 트레이딩 봇입니다.

## 목적

**Point Farming**을 위한 거래량 생성 봇입니다.
- 두 DEX에서 동시 LONG/SHORT 진입 → Hold → 동시 청산 → 무한 반복
- 펀딩비 차익은 부수적, **거래량 생성 및 포인트 파밍이 핵심 목적**

## 수수료 구조

| Exchange | Maker Fee | Taker Fee | Point System |
|----------|-----------|-----------|--------------|
| Backpack | -35% rebate | Standard | Trading volume points |
| Lighter  | 0%         | 0%        | $70k/point, 30-40% airdrop |

## 전략 흐름

```
[Iteration Loop]
│
├─ STEP 1: Backpack post-only BUY
│   └─ Price: market - spread/2
│   └─ Wait fill (timeout)
│
├─ STEP 2: Lighter market SELL (hedge)
│   └─ 동일량 즉시 실행 (delta-neutral)
│
├─ STEP 3: Backpack post-only SELL (close)
│   └─ Price: entry × (1 + take_profit%)
│
├─ STEP 4: Lighter market BUY (close hedge)
│   └─ 동일량 즉시 실행
│
└─ [Position Reconciliation]
    └─ |position_A + position_B| ≤ 0.2
```

## 설치

### 1. 의존성 설치

```bash
cd perpdex/hedge
pip install -r requirements.txt

# Lighter SDK 설치 (git에서 직접)
pip install git+https://github.com/elliottech/lighter-python.git@d0009799970aad54ebb940aa3dc90cbc00028c54
```

### 2. 환경 설정

```bash
# 설정 파일 복사
cp .env.backpack_lighter .env

# .env 파일 편집하여 API 키 입력
```

### 3. API 키 설정

#### Backpack
1. https://backpack.exchange 접속
2. Portfolio → Settings → API Keys
3. Trade 권한이 있는 API 키 생성
4. IP 화이트리스트 설정 권장

#### Lighter
1. https://app.lighter.xyz 접속
2. API 키 생성
3. Private key 내보내기

## 사용법

### 기본 실행

```bash
# CLI 파라미터로 직접 지정
python hedge_mode.py --exchange backpack --ticker ETH --size 0.05 --iter 20

# config.yaml 기본값 사용 (--size, --iter 생략 가능)
python hedge_mode.py --exchange backpack --ticker ETH
```

### 파라미터

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--exchange` | 거래소 선택 | (필수) | `backpack` |
| `--ticker` | 거래 심볼 | `BTC` | `ETH`, `SOL` |
| `--size` | 주문당 수량 | config.yaml | `0.05` |
| `--iter` | 반복 횟수 | config.yaml | `20` |
| `--fill-timeout` | 체결 대기 시간(초) | `5` | `10` |
| `--env-file` | 환경 파일 경로 | `.env` | `.env.prod` |
| `--config` | 설정 파일 경로 | `config.yaml` | `config.prod.yaml` |

### 실행 예시

```bash
# ETH 테스트 (소액, config.yaml 기본값 사용)
python hedge_mode.py --exchange backpack --ticker ETH

# ETH 커스텀 설정
python hedge_mode.py --exchange backpack --ticker ETH --size 0.05 --iter 20

# BTC 본 실행
python hedge_mode.py --exchange backpack --ticker BTC --size 0.001 --iter 50

# SOL 실행 (커스텀 환경 파일)
python hedge_mode.py --exchange backpack --ticker SOL --size 1.0 --iter 100 --env-file .env.prod
```

## 설정 파일 (config.yaml)

코드 수정 없이 전략 파라미터를 튜닝할 수 있습니다.

**우선순위**: CLI 인자 > config.yaml > 하드코딩 기본값

```yaml
trading:
  # 기본 주문 수량 (CLI --size 미지정 시 사용)
  default_size: 0.01           # 테스트: 0.01 (~$5)
  default_iterations: 10       # 기본 반복 횟수

  # 포지션 불균형 허용치
  position_diff_threshold: 0.2

  # 타임아웃 설정
  order_cancel_timeout: 10     # 미체결 주문 취소 (초)
  trading_loop_timeout: 180    # 루프 전체 타임아웃 (초)
  max_retries: 15              # API 재시도 횟수
  fill_check_interval: 10      # 체결 확인 간격 (초)

monitoring:
  # 펀딩비 모니터링
  funding_fee_logging: true
  funding_fee_log_interval: 5  # N회 반복마다 로깅
  funding_fee_warning_threshold: -10.0  # 경고 임계값 (USD)

pricing:
  # 가격 조정 (post-only maker)
  buy_price_multiplier: 0.998  # 시장가 × 0.998 (-0.2%)
  sell_price_multiplier: 1.002 # 진입가 × 1.002 (+0.2%)
```

## 펀딩비 모니터링

봇은 자동으로 펀딩비를 모니터링하고 로깅합니다:

- **주기적 로깅**: `funding_fee_log_interval` 마다 누적 펀딩비 표시
- **경고 알림**: 누적 펀딩비가 `funding_fee_warning_threshold` 초과 시 경고
- **로그 예시**:
  ```
  [INFO] Funding status: Total=-$5.23 from 12 payments (last 10 shown)
  [WARNING] Cumulative funding fee (-$12.50) exceeds warning threshold (-$10.00)!
  ```

## 파일 구조

```
hedge/
├── hedge_mode.py          # 메인 엔트리 포인트
├── hedge_mode_bp.py       # Backpack+Lighter HedgeBot 구현
├── hedge_mode_ext.py      # Extended+Lighter HedgeBot 구현
├── config_loader.py       # YAML 설정 로더
├── config.yaml            # 전략 파라미터 설정
├── exchanges/
│   ├── backpack.py        # Backpack 거래소 클라이언트
│   ├── bp_client.py       # Backpack HTTP/WebSocket
│   ├── lighter.py         # Lighter 거래소 클라이언트
│   └── lighter_custom_websocket.py  # Lighter WebSocket
├── tests/
│   └── test_config_loader.py  # 설정 로더 단위 테스트
├── docs/
│   ├── PARAMETERS_ANALYSIS.md  # 파라미터 분석 문서
│   └── QA_SESSION_2025-12-14.md  # Q&A 세션 기록
├── .env.example           # 전체 환경 설정 예시
├── .env.backpack_lighter  # Backpack+Lighter 전용 설정
├── requirements.txt       # Python 의존성
└── README.md              # 이 문서
```

## 주의사항

### Backpack Wash Trading 필터
- 최소 **10분** 이상 포지션 유지 권장
- 너무 빠른 진입/청산은 wash trading으로 간주될 수 있음

### 포지션 관리
- 봇은 자동으로 포지션 불균형을 모니터링
- `|backpack_position + lighter_position| > 0.2` 시 경고
- 수동 리밸런싱이 필요할 수 있음

### 리스크
- 네트워크 지연으로 인한 일시적 포지션 불균형
- 거래소 API 장애 시 한쪽만 체결될 가능성
- 슬리피지로 인한 소액 손실 가능

## 예상 수익성

**$100k 거래량 기준**:
- Backpack rebate: +$350 (35%)
- Lighter fee: $0
- Spread cost: -$50 (예상)
- **순수익: +$300**

**포인트 획득**:
- Lighter: ~1.4 points ($70k/point)
- Backpack: Trading volume points

## 구현 현황

### 완료 (Completed)
- [x] config.yaml 설정 파일 지원 (SPEC-001)
- [x] default_size, default_iterations 파라미터
- [x] 펀딩비 모니터링 및 로깅

### 권장 (Medium Priority)
- [ ] 잔고 모니터링

### 잠재 기능 (보류)
- [ ] holding_time 파라미터 (거래량 감소 우려로 보류)
- [ ] 자동 리밸런싱
- [ ] 다른 DEX 페어 확장

## 라이센스

이 코드는 [perp-dex-toolkit](https://github.com/earthskyorg/perp-dex-toolkit)을 기반으로 합니다.

**중요**: perp-dex-toolkit은 **비상업용 라이센스**입니다.
- ✅ 개인 사용 가능
- ❌ 상업적 사용 금지
- ❌ 수정 배포 금지
