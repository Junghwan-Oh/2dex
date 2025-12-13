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
python hedge_mode.py --exchange backpack --ticker ETH --size 0.05 --iter 20
```

### 파라미터

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--exchange` | 거래소 선택 | (필수) | `backpack` |
| `--ticker` | 거래 심볼 | `BTC` | `ETH`, `SOL` |
| `--size` | 주문당 수량 | (필수) | `0.05` |
| `--iter` | 반복 횟수 | (필수) | `20` |
| `--fill-timeout` | 체결 대기 시간(초) | `5` | `10` |
| `--env-file` | 환경 파일 경로 | `.env` | `.env.prod` |

### 실행 예시

```bash
# ETH 테스트 (소액)
python hedge_mode.py --exchange backpack --ticker ETH --size 0.01 --iter 5

# BTC 본 실행
python hedge_mode.py --exchange backpack --ticker BTC --size 0.001 --iter 50

# SOL 실행 (커스텀 환경 파일)
python hedge_mode.py --exchange backpack --ticker SOL --size 1.0 --iter 100 --env-file .env.prod
```

## 파일 구조

```
hedge/
├── hedge_mode.py          # 메인 엔트리 포인트
├── hedge_mode_bp.py       # Backpack+Lighter HedgeBot 구현
├── hedge_mode_ext.py      # Extended+Lighter HedgeBot 구현
├── exchanges/
│   ├── backpack.py        # Backpack 거래소 클라이언트
│   └── lighter.py         # Lighter 거래소 클라이언트
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

## 라이센스

이 코드는 [perp-dex-toolkit](https://github.com/earthskyorg/perp-dex-toolkit)을 기반으로 합니다.

**중요**: perp-dex-toolkit은 **비상업용 라이센스**입니다.
- ✅ 개인 사용 가능
- ❌ 상업적 사용 금지
- ❌ 수정 배포 금지
