# Perpetual Futures 기본 기능 테스트 계획 (템플릿)

Perpetual Futures 거래 기능을 체계적으로 테스트하기 위한 계획서 템플릿입니다.

> **사용 방법**: 이 템플릿을 각 DEX 폴더로 복사하고, `{DEX_SPECIFIC}` placeholder와 API 예시를 해당 DEX에 맞게 수정하세요.

## 📋 목차
- [테스트 목표](#테스트-목표)
- [테스트 환경](#테스트-환경)
- [테스트 시나리오](#테스트-시나리오)
- [리스크 관리](#리스크-관리)
- [구현 계획](#구현-계획)

---

## 테스트 목표

### 1차 목표: 기본 거래 플로우 검증

- [ ] 계좌 조회 및 포지션 모니터링
- [ ] **포지션 오픈** (신규 주문 생성)
- [ ] **Take-Profit 주문 자동 설정** (오픈과 동시에)
- [ ] **포지션 클로징** (Take-Profit 체결 or 수동 클로징)
- [ ] **수수료 및 손익 분석**

### 2차 목표: 자동화 준비

- [ ] 주문 생성 → 체결 → 보고 자동화
- [ ] WebSocket 실시간 모니터링
- [ ] 에러 처리 및 재시도 로직

---

## 테스트 환경

### 권장 설정

| 항목 | 값 | 이유 |
|------|-----|------|
| **환경** | Testnet → Mainnet | 안전한 테스트 후 실전 |
| **초기 자금** | 최소 ${DEX_SPECIFIC} USDT | 수수료 감안 |
| **포지션 크기** | {DEX_SPECIFIC} BTC (최소) | 리스크 최소화 |
| **레버리지** | 1x ~ {DEX_SPECIFIC}x | 낮은 레버리지로 안전성 확보 |
| **테스트 심볼** | BTC-USDT | 유동성 최고 |

### 수수료 구조

> **중요**: 각 DEX마다 수수료 구조가 다릅니다. 아래는 예시이며, 공식 문서에서 확인하세요.

| 주문 타입 | 수수료율 | 비고 |
|-----------|---------|------|
| **Limit (Maker)** | {DEX_SPECIFIC}% | POST_ONLY 사용 |
| **Market (Taker)** | {DEX_SPECIFIC}% | 즉시 체결 |
| **Target** | {DEX_SPECIFIC}% 수익 | 수수료 제외 순이익 목표 |

**손익 분기점:**
- Maker 주문: {MAKER_FEE}% (진입) + {MAKER_FEE}% (청산) = **{TOTAL_MAKER_FEE}%**
- Taker 주문: {TAKER_FEE}% (진입) + {TAKER_FEE}% (청산) = **{TOTAL_TAKER_FEE}%**

---

## 테스트 시나리오

### 시나리오 1: LONG 포지션 (기본 테스트)

#### 1단계: 포지션 오픈

**목표:**
- BTC-USDT LONG 포지션 {SIZE} BTC 진입
- Limit 주문으로 Maker 수수료 적용

**실행:**
```python
# {DEX_NAME} SDK 사용 예시
import time
# from {dex_sdk} import {Client}  # 각 DEX SDK import

# 현재가 조회
# ticker = client.get_ticker('BTC-USDT')
# current_price = float(ticker['lastPrice'])

# 진입가 설정 (현재가보다 0.05% 낮게 설정하여 Maker 주문)
# entry_price = current_price * 0.9995

# LONG 포지션 오픈
# open_order = client.create_order(
#     symbol="BTC-USDT",
#     side="BUY",
#     type="LIMIT",
#     size="{SIZE}",  # 예: 0.001 BTC
#     price=str(entry_price),
#     time_in_force="POST_ONLY"  # Maker 전용 (DEX마다 다를 수 있음)
# )

print(f"[OPEN] LONG 포지션 진입 주문")
print(f"  Size: {SIZE} BTC")
print(f"  Entry Price: ${entry_price:,.2f}")
print(f"  Expected Fee: {entry_price * SIZE * MAKER_FEE_RATE:.6f} USDT")
```

**보고 항목:**
- ✅ 주문 ID
- ✅ 진입가
- ✅ 주문 상태 (PENDING → FILLED)
- ✅ 실제 체결가
- ✅ 수수료

#### 2단계: Take-Profit 주문 자동 설정

**목표:**
- 진입과 동시에 {TP_PERCENTAGE}% 수익 시 자동 청산 주문
- LONG 포지션이므로 진입가 대비 {TP_PERCENTAGE}% 상승가에 SELL 주문

**실행:**
```python
# Take-Profit 가격 계산
# tp_price = entry_price * (1 + TP_PERCENTAGE)  # 예: 1.001 for 0.1%

# Take-Profit 주문 생성
# tp_order = client.create_order(
#     symbol="BTC-USDT",
#     side="SELL",  # LONG 포지션 청산
#     type="LIMIT",
#     size="{SIZE}",  # 전체 포지션 청산
#     price=str(tp_price),
#     time_in_force="POST_ONLY",  # Maker 수수료 적용
#     reduce_only=True  # 포지션 청산 전용 (신규 진입 방지)
# )

print(f"[TP] Take-Profit 주문 설정")
print(f"  TP Price: ${tp_price:,.2f} (+{TP_PERCENTAGE*100:.1f}%)")
print(f"  Expected Profit: ${(tp_price - entry_price) * SIZE:.6f} USDT")
print(f"  Expected Fee: ${tp_price * SIZE * MAKER_FEE_RATE:.6f} USDT")
print(f"  Net Profit: ${net_profit:.6f} USDT")
```

**보고 항목:**
- ✅ Take-Profit 가격
- ✅ 예상 수익 (수수료 제외)
- ✅ 예상 순이익 (수수료 포함)
- ✅ 주문 ID

#### 3단계: 포지션 모니터링

**목표:**
- 실시간 포지션 및 주문 상태 확인
- Take-Profit 체결 대기

**실행:**
```python
import time

def monitor_position():
    """포지션 및 주문 상태 모니터링"""
    while True:
        # 현재 포지션 조회
        # positions = client.get_active_positions()
        # if not positions:
        #     print("[INFO] 포지션 청산 완료!")
        #     break

        # position = positions[0]
        # size = float(position.get('size', '0'))
        # entry_price = float(position.get('entryPrice', '0'))

        # 현재가 조회
        # ticker = client.get_ticker('BTC-USDT')
        # current_price = float(ticker['markPrice'])

        # 미실현 손익 계산
        # unrealized_pnl = (current_price - entry_price) * size

        # 미체결 주문 확인
        # open_orders = client.get_open_orders()

        print(f"\n[MONITOR] {time.strftime('%H:%M:%S')}")
        print(f"  Position: {size} BTC @ ${entry_price:,.2f}")
        print(f"  Current Price: ${current_price:,.2f}")
        print(f"  Unrealized PnL: ${unrealized_pnl:+.6f} USDT")

        time.sleep(10)  # 10초마다 체크

# monitor_position()
```

**보고 항목:**
- ✅ 현재가
- ✅ 미실현 손익
- ✅ Take-Profit 주문 상태

#### 4단계: 포지션 클로징 (자동 or 수동)

**자동 청산 (Take-Profit 체결):**
```python
# Take-Profit 체결 확인
# fills = client.get_fills(limit=10)
# for fill in fills:
#     if fill.get('order_id') == tp_order_id:
#         print(f"\n[FILLED] Take-Profit 체결!")
#         print(f"  Fill Price: ${float(fill['price']):,.2f}")
#         print(f"  Fill Size: {fill['size']} BTC")
#         print(f"  Fee: ${float(fill['fee']):.6f} USDT")
```

**수동 청산 (긴급 상황):**
```python
# 현재 포지션 조회
# positions = client.get_active_positions()
# if positions:
#     position = positions[0]
#     size = position['size']

    # 현재가로 즉시 청산 (Market 주문)
    # close_order = client.create_order(
    #     symbol="BTC-USDT",
    #     side="SELL",  # LONG 포지션 청산
    #     type="MARKET",
    #     size=size,
    #     reduce_only=True
    # )

    print(f"[CLOSE] 긴급 수동 청산 완료")
    print(f"  Size: {size} BTC")
    print(f"  Type: MARKET (Taker Fee {TAKER_FEE}%)")
```

**보고 항목:**
- ✅ 청산 방식 (자동 TP / 수동 Market)
- ✅ 청산가
- ✅ 실현 손익
- ✅ 총 수수료
- ✅ 순이익

---

### 시나리오 2: SHORT 포지션

#### 1단계: 포지션 오픈

**목표:**
- BTC-USDT SHORT 포지션 진입
- SHORT 포지션이므로 가격 하락 시 수익

**실행:**
```python
# SHORT 포지션 진입 (SELL 주문)
# short_order = client.create_order(
#     symbol="BTC-USDT",
#     side="SELL",  # SHORT 진입
#     type="LIMIT",
#     size="{SIZE}",
#     price=str(entry_price),
#     time_in_force="POST_ONLY"
# )
```

#### 2단계: Take-Profit 주문 설정

**목표:**
- SHORT 포지션이므로 {TP_PERCENTAGE}% 하락 시 청산
- TP Price = Entry Price × (1 - TP_PERCENTAGE)

**실행:**
```python
# Take-Profit 가격 계산 (하락)
# tp_price = entry_price * (1 - TP_PERCENTAGE)

# Take-Profit 주문 생성
# tp_order = client.create_order(
#     symbol="BTC-USDT",
#     side="BUY",  # SHORT 포지션 청산 (BUY로 포지션 닫기)
#     type="LIMIT",
#     size=str(size),
#     price=str(tp_price),
#     time_in_force="POST_ONLY",
#     reduce_only=True
# )

print(f"[TP] SHORT 포지션 Take-Profit 주문 설정")
print(f"  Entry Price: ${entry_price:,.2f}")
print(f"  TP Price: ${tp_price:,.2f} (-{TP_PERCENTAGE*100:.1f}%)")
print(f"  Expected Profit: ${(entry_price - tp_price) * size:.6f} USDT")
```

---

## 리스크 관리

### 필수 체크리스트

- [ ] **API Key 확보**: 주문 생성에 필수 (각 DEX별 키 발급 방법 확인)
- [ ] **초기 자금 충분**: 최소 ${DEX_SPECIFIC} USDT 권장
- [ ] **테스트넷 먼저**: Mainnet 전에 Testnet 검증 (지원 시)
- [ ] **최소 포지션**: {MIN_SIZE} BTC로 시작
- [ ] **손절가 설정**: Take-Profit과 별도로 Stop-Loss 고려
- [ ] **모니터링 도구**: WebSocket 또는 주기적 폴링

### 비상 대응

| 상황 | 대응 방법 |
|------|-----------|
| **급격한 가격 변동** | Market 주문으로 즉시 청산 |
| **API 장애** | 웹사이트에서 수동 청산 |
| **Take-Profit 미체결** | 수동으로 시장가 청산 |
| **잔액 부족** | 포지션 크기 축소 |

---

## 구현 계획

### Phase 1: 기본 기능 구현 (1-2일)

- [ ] `examples/03_automated_trading.py` 작성
- [ ] 포지션 오픈 함수
- [ ] Take-Profit 자동 설정 함수
- [ ] 모니터링 함수
- [ ] 보고 함수

### Phase 2: 테스트 실행 (1일)

- [ ] Testnet에서 전체 플로우 테스트 (지원 시)
- [ ] 수수료 및 손익 검증
- [ ] 에러 케이스 확인

### Phase 3: Mainnet 배포 (신중하게)

- [ ] 최소 금액으로 실전 테스트
- [ ] 결과 분석 및 문서화
- [ ] 자동화 스크립트 개선

---

## DEX별 구현 체크리스트

각 DEX에서 이 템플릿을 복사하여 다음을 확인하세요:

- [ ] SDK/API 클라이언트 Import 경로 수정
- [ ] 수수료 구조 (Maker/Taker) 확인 및 업데이트
- [ ] 주문 타입 파라미터 확인 (time_in_force, reduce_only 등)
- [ ] 최소 주문 크기 확인
- [ ] Mark Price vs Last Price 사용 확인
- [ ] Testnet 지원 여부 확인
- [ ] 공식 문서 링크 추가

---

**Template Version:** 1.0
**Last Updated:** 2025-01-23
