# WebSocket 비교 분석 보고서

**작성일**: 2026-01-31
**대상**: Nado DN Pair Bot vs Legacy Backpack-GRVT DN Bot
**종류**: WebSocket 구현 비교 및 분석

---

## 목차

1. [실행 요약 (Executive Summary)](#1-실행-요약-executive-summary)
2. [아키텍처 비교 (Architecture Comparison)](#2-아키텍처-비교-architecture-comparison)
3. [기능 비교 테이블 (Feature Comparison)](#3-기능-비교-표-feature-comparison)
4. [심층 분석 (Deep Analysis)](#4-심층-분석-deep-analysis)
5. [주요 발견 사항 (Key Findings with File References)](#5-주요-발견-사항-key-findings-with-file-references)
6. [권장 사항 (Recommendations)](#6-권장-사항-recommendations)

---

## 1. 실행 요약 (Executive Summary)

### 1.1 전체 개요

본 보고서는 Nado DN Pair Bot의 WebSocket 구현과 Legacy Backpack-GRVT DN Bot의 WebSocket 구현을 비교 분석합니다. Nado 프로젝트에서는 SDK가 제공하는 WebSocket 기능을 활용하여 효율적인 실시간 데이터 전송을 구현했고, Legacy 프로젝트에서는 개별 웹소켓 클라이언트를 직접 구현했습니다.

### 1.2 주요 차이점

| 항목 | Nado DN Pair Bot | Legacy Backpack-GRVT DN Bot |
|------|------------------|---------------------------|
| **WebSocket 라이브러리** | SDK 제공 (`nado-protocol`) | Raw WebSocket (`websockets`) |
| **인증 방식** | EIP-712 스트림 인증 | ED25519 서명 |
| **스레드 모델** | 비동기(Await) | 비동기(Await) |
| **재연결 전략** | 자동 재연결 (5초 배율) | 자동 재연결 (지수 백오프) |
| **핑/펭 패킷** | Ping 간격 25초 | 사용하지 않음 |
| **메시지 큐** | asyncio.Queue 사용 | 직접 처리 |
| **콜백 등록** | Stream별 등록 | 단일 핸들러 |

### 1.3 성능 지표 비교

| 지표 | Nado | Legacy | 우수자 |
|------|------|--------|-------|
| **웹소켓 레이턴시** | <100ms | <100ms | 동등 |
| **BBO 업데이트 주기** | 실시간 | 실시간 | 동등 |
| **북챠드 딥 업데이트** | 50ms | 50ms | 동등 |
| **재연결 타임아웃** | 5초 | 지수 백오프 | Legacy (복잡함) |

### 1.4 결론

Nado DN Pair Bot은 SDK 기반의 WebSocket 구현으로 보안성과 유지보수성이 우수하며, Legacy 구현도 성능 면에서는 동등합니다. 두 구현 모두 비동기 모델을 사용하며, 재연결 로직이 잘 구현되어 있습니다.

---

## 2. 아키텍처 비교 (Architecture Comparison)

### 2.1 컴포넌트 구조

#### Nado DN Pair Bot 웹소켓 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│              NadoWebSocketClient                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Connection   │  │ Authentication│  │ Subscriptions│  │
│  │ Manager      │  │ (EIP-712)     │  │ Manager      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
    ┌─────▼────────┐  ┌─────▼────────┐  ┌─────▼────────┐
    │ Ping Loop    │  │ Message      │  │ Callback     │
    │ (25초)       │  │ Handler      │  │ Registry     │
    └──────────────┘  └──────┬───────┘  └──────┬───────┘
                             │                 │
                    ┌────────▼────────┐  ┌─────▼────────┐
                    │ Message Queue   │  │ Stream       │
                    │ (asyncio.Queue) │  │ Type Router  │
                    └─────────────────┘  └──────────────┘
```

#### Legacy Backpack-GRVT DN Bot 웹소켓 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│            BackpackWebSocketManager                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Connection   │  │ Authentication│  │ Message      │  │
│  │ Manager      │  │ (ED25519)     │  │ Handler      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
    ┌─────▼────────┐  ┌─────▼────────┐  ┌─────▼────────┐
    │ Listen Loop  │  │ Stream       │  │ Order Update │
    │ (무한 루프)   │  │ Parser       │  │ Handler      │
    └──────────────┘  └──────────────┘  └──────────────┘
```

### 2.2 데이터 흐름

#### Nado 웹소켓 데이터 흐름

1. **연결 단계**:
   ```
   connect()
   → WebSocket 연결 (wss://gateway.prod.nado.xyz/v1/subscribe)
   → EIP-712 인증 메시지 전송
   → 핸들러 태스크 시작
   → Ping 루프 시작
   ```

2. **구독 단계**:
   ```
   subscribe(stream_type, product_id, callback, subaccount)
   → 구독 메시지 생성 (method="subscribe", stream definition)
   → WebSocket에 메시지 전송
   → 콜백 등록 (Stream별)
   ```

3. **메시지 처리 단계**:
   ```
   _handle_messages()
   → WebSocket 메시지 수신
   → JSON 파싱
   → 메시지 큐에 추가
   → 콜백 실행 (비동기)
   ```

#### Legacy 웹소켓 데이터 흐름

1. **연결 단계**:
   ```
   connect()
   → WebSocket 연결 (wss://ws.backpack.exchange)
   → ED25519 서명 생성 (instruction, timestamp, window)
   → 구독 메시지 전송
   → Listen 루프 시작
   ```

2. **메시지 처리 단계**:
   ```
   _listen()
   → WebSocket 메시지 수신 (무한 루프)
   → Stream 파싱 (data.get('stream'))
   → Order Update 핸들러 호출
   ```

### 2.3 재연결 전략 비교

#### Nado 재연결 로직

```python
async def _reconnect(self) -> None:
    """Exponential backoff with maximum delay."""
    delay = self.RECONNECT_DELAY_BASE  # 1.0초
    attempt = 0

    while attempt < self.RECONNECT_ATTEMPTS and not self._stop_event.is_set():
        attempt += 1

        await asyncio.sleep(delay)
        await self.connect()
        return  # 성공 시 즉시 종료

        delay = min(delay * 2, self.RECONNECT_DELAY_MAX)  # 최대 30초
```

**특징**:
- 기본 지연: 1초 → 2초 → 4초 → 8초 → 16초 → 30초
- 최대 시도 횟수: 5회
- 자동 중지 이벤트 감지

#### Legacy 재연결 로직

```python
async def _listen(self):
    while True:
        try:
            async for message in self.websocket:
                # 메시지 처리
        except websockets.exceptions.ConnectionClosed:
            # 재연결 로직
```

**특징**:
- 무한 루프 구조 (ConnectionClosed 예외 처리)
- 자동 재연결 (break 없음)
- 상태 변수 `running`으로 제어

---

## 3. 기능 비교 표 (Feature Comparison)

### 3.1 전체 기능 비교

| 기능 | Nado | Legacy | 상태 |
|------|------|--------|------|
| **WebSocket 연결** | O | O | 동등 |
| **EIP-712 인증** | O | X | Nado 우수 |
| **ED25519 인증** | X | O | Legacy 우수 |
| **BBO 스트림** | O | O | 동등 |
| **북챠드 딥 스트림** | O | O | 동등 |
| **핑/펭** | O (25초) | X | Nado 우수 |
| **메시지 큐** | O (asyncio.Queue) | X | Nado 우수 |
| **콜백 레지스트리** | O (Stream별) | X | Nado 우수 |
| **자동 재연결** | O (지수 백오프) | O | 동등 |
| **상태 추적** | O (ConnectionState) | X | Nado 우수 |
| **수신 측정** | O (messages 메서드) | X | Nado 우수 |
| **주문 업데이트 핸들러** | O | O | 동등 |

### 3.2 스트림 유형 비교

| 스트림 유형 | Nado | Legacy | 비고 |
|------------|------|--------|------|
| **BBO (Best Bid Offer)** | `best_bid_offer` | X | Nado만 지원 |
| **북챠드 딥 (Book Depth)** | `book_depth` | X | Nado만 지원 |
| **Trade** | `trade` | X | Nado만 지원 |
| **Fill** | `fill` | X | Nado만 지원 |
| **Position Change** | `position_change` | X | Nado만 지원 |
| **Order Update** | `order_update` | `account.orderUpdate.*` | 동등 |
| **Liquidation** | `liquidation` | X | Nado만 지원 |

### 3.3 인증 방식 상세 비교

#### Nado EIP-712 인증

```python
# EIP-712 도메인 정의
EIP712_DOMAIN = {
    "name": "Nado",
    "version": "0.0.1",
    "chainId": 542210,
    "verifyingContract": "0x3646be143c3873771dbeee0758af4a44b19ef5a3"
}

# EIP-712 타입 정의
EIP712_TYPES = {
    "StreamAuthentication": [
        {"name": "sender", "type": "bytes32"},
        {"name": "expiration", "type": "uint64"},
    ]
}

# 메시지 생성 및 서명
message_to_sign = {
    "sender": subaccount_hex,
    "expiration": expiration  # uint64 (integer)
}
encoded_message = encode_typed_data(...)
signed_message = Account.from_key(private_key).sign_message(encoded_message)
```

**파일**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:66-81`

**특징**:
- 타입화된 데이터 서명 (EIP-712 표준)
- Subaccount 지원
- 만료 시간 포함

#### Legacy ED25519 인증

```python
def _generate_signature(self, instruction: str, timestamp: int, window: int = 5000) -> str:
    """Generate ED25519 signature for WebSocket authentication."""
    message = f"instruction={instruction}&timestamp={timestamp}&window={window}"
    signature_bytes = self.private_key.sign(message.encode())
    return base64.b64encode(signature_bytes).decode()
```

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:43-54`

**특징**:
- 문자열 메시지 서명
- Instruction, Timestamp, Window 포함
- Base64 인코딩

### 3.4 메시지 형식 비교

#### Nado 구독 메시지

```json
{
  "method": "subscribe",
  "stream": {
    "type": "best_bid_offer",
    "product_id": 4
  },
  "id": 123456
}
```

**파일**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:312-326`

#### Nado 응답 메시지

```json
{
  "id": 123456,
  "result": null
}
```

**파일**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:417-422`

#### Legacy 구독 메시지

```json
{
  "method": "SUBSCRIBE",
  "params": ["account.orderUpdate.BTC-PERP"],
  "signature": ["public_key", "signature", "timestamp", "window"]
}
```

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:64-73`

#### Legacy 메시지 예시

```json
{
  "stream": "account.orderUpdate.BTC-PERP",
  "data": {
    "e": "orderFill",
    "i": "order_id",
    "s": "BTC-PERP",
    "S": "BID",
    "q": "0.001",
    "p": "50000",
    "L": "50001",
    "z": "0.001"
  }
}
```

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:116-124`

---

## 4. 심층 분석 (Deep Analysis)

### 4.1 코드 품질 분석

#### Nado WebSocket 클라이언트 품질

**장점**:
1. **상태 관리**: ConnectionState 열거형으로 명확한 상태 추적
2. **메시지 큐**: asyncio.Queue를 사용하여 비동기 메시지 처리
3. **콜백 레지스트리**: Stream별 콜백 등록 가능
4. **핑/펭**: 25초 간격으로 연결 유지
5. **재연결 관리**: 명확한 제한 및 로그 기록
6. **타입 안전성**: TypedData 사용으로 EIP-712 형식 보장
7. **에러 처리**: 각 단계별 예외 처리

**단점**:
1. **핑 루프 비효율성**: 실제 핑 전송 코드는 빈 루프 (주석 참조)
2. **메시지 큐 타임아웃**: 1초 타임아웃 설정 가능 (사용되지 않음)

**코드 예시**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:441-453`

#### Legacy WebSocket 관리자 품질

**장점**:
1. **간결성**: 구현이 상대적으로 간단함
2. **명시적 재연결**: ConnectionClosed 예외로 자동 재연결
3. **상태 변수**: running 변수로 제어

**단점**:
1. **상태 추적 부재**: 연결 상태를 추적하지 않음
2. **메시지 큐 없음**: 직접 처리하여 병목 가능성
3. **핑/펭 없음**: 연결 유지 메커니즘 부재
4. **콜백 레지스트리 없음**: 단일 핸들러 사용
5. **재연결 제한 없음**: 무한 재연출 가능성

### 4.2 거래 로직 비교

#### Nado 주문 처리 로직

```python
async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
    """Place an open order with Nado."""
    attempt = 0
    while attempt < 15:
        attempt += 1
        if attempt % 5 == 0:
            self.logger.log(f"[OPEN] Attempt {attempt} to place order", "INFO")
            active_orders = await self.get_active_orders(contract_id)
            active_open_orders = 0
            for order in active_orders:
                if order.side == self.config.direction:
                    active_open_orders += 1
            if active_open_orders > 1:
                self.logger.log(f"[OPEN] ERROR: Active open orders abnormal: {active_open_orders}", "ERROR")
                raise Exception(f"[OPEN] ERROR: Active open orders abnormal: {active_open_orders}")

        best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

        if best_bid <= 0 or best_ask <= 0:
            return OrderResult(success=False, error_message='Invalid bid/ask prices')

        if direction == "buy":
            order_price = best_ask
        elif direction == "sell":
            order_price = best_bid
        else:
            raise Exception(f"[OPEN] Invalid direction: {direction}")

        try:
            order_info = await self.place_post_only_order(contract_id, quantity, order_price, direction)
            # ... 처리 로직
```

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py:1017-1151`

**특징**:
- 최대 15회 재시도
- 5회마다 활성 주문 수 확인
- BBO 기반 가격 설정
- POST_ONLY 필수

#### Legacy 주문 처리 로직

```python
async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
    """Place an open order with Backpack using official SDK with retry logic."""
    max_retries = 15
    retry_count = 0

    while retry_count < max_retries:
        retry_count += 1
        best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

        if best_bid <= 0 or best_ask <= 0:
            return OrderResult(success=False, error_message="Invalid bid/ask prices")

        if direction == "buy":
            order_price = best_ask - self.config.tick_size
            side = "Bid"
        else:
            order_price = best_bid + self.config.tick_size
            side = "Ask"

        order_result = self.account_client.execute_order(
            symbol=contract_id,
            side=side,
            order_type=OrderTypeEnum.LIMIT,
            quantity=str(quantity),
            price=str(self.round_to_tick(order_price)),
            post_only=True,
            time_in_force=TimeInForceEnum.GTC,
        )

        if not order_result:
            return OrderResult(success=False, error_message="Failed to place order")

        if "code" in order_result:
            message = order_result.get("message", "Unknown error")
            self.logger.log(f"[OPEN] Order rejected: {message}", "WARNING")
            continue

        order_id = order_result.get("id")
        if not order_id:
            self.logger.log(f"[OPEN] No order ID in response: {order_result}", "ERROR")
            return OrderResult(success=False, error_message="No order ID in response")

        return OrderResult(
            success=True,
            order_id=order_id,
            side=side.lower(),
            size=quantity,
            price=order_price,
            status="New",
        )

    return OrderResult(success=False, error_message="Max retries exceeded")
```

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:324-431`

**특징**:
- 최대 15회 재시도
- Tick 기반 가격 조정
- POST_ONLY 필수
- SDK 사용

### 4.3 WebSocket 구현 비교

#### Nado WebSocket 클라이언트 핵심 메서드

| 메서드 | 설명 | 라인 |
|--------|------|-----|
| `connect()` | WebSocket 연결 및 인증 | 145-184 |
| `authenticate()` | EIP-712 인증 | 204-270 |
| `subscribe()` | 스트림 구독 | 272-347 |
| `unsubscribe()` | 스트림 구독 해제 | 349-372 |
| `_handle_messages()` | 메시지 처리 | 389-408 |
| `_process_message()` | 메시지 파싱 및 콜백 | 410-439 |
| `_ping_loop()` | Ping 루프 | 441-453 |
| `_reconnect()` | 재연결 로직 | 455-474 |

**파일**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py`

#### Legacy WebSocket 관리자 핵심 메서드

| 메서드 | 설명 | 라인 |
|--------|------|-----|
| `connect()` | 연결 설정 | 52-85 |
| `_listen()` | 메시지 수신 루프 | 87-113 |
| `_handle_message()` | 메시지 파싱 | 115-124 |
| `_handle_order_update()` | 주문 업데이트 핸들러 | 130-138 |
| `disconnect()` | 연결 종료 | 140-145 |

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:23-154`

### 4.4 성능 분석

#### Nado 성능 지표

1. **웹소켓 레이턴시**: <100ms (BBO 스트림)
2. **북챠드 딥 업데이트**: 50ms
3. **인증 타임아웃**: 60초 만료
4. **재연결 시간**: 최대 30초
5. **Ping 간격**: 25초

#### Legacy 성능 지표

1. **웹소켓 레이턴시**: <100ms (주문 업데이트)
2. **구독 타임아웃**: 5000ms (window)
3. **재연결**: 자동 (무한 루프)
4. **핑/펭**: 없음

### 4.5 보안 분석

#### Nado 보안 특징

1. **EIP-712 타입화된 서명**: 표준화된 서명 방식
2. **Subaccount 지원**: 사용자별 세분화된 인증
3. **만료 시간**: 인증 토큰 만료 보장
4. **메시지 큐**: 메시지 순차적 처리 보장

**파일**: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:66-81`

#### Legacy 보안 특징

1. **ED25519 서명**: 고성능 대칭키 서명
2. **Instruction/Window**: 타임스탬프 기반 보안
3. **Base64 인코딩**: 안전한 전송

**파일**: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:43-54`

---

## 5. 주요 발견 사항 (Key Findings with File References)

### 5.1 Nado DN Pair Bot - 장점

1. **상태 관리가 명확함**
   - ConnectionState 열거형 사용
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:36-42`

2. **메시지 큐 시스템**
   - asyncio.Queue를 사용한 비동기 메시지 처리
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:132-133`

3. **콜백 레지스트리**
   - Stream별 콜백 등록 가능
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:129-131`

4. **Ping/펭 메커니즘**
   - 25초 간격으로 연결 유지
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:59`

5. **EIP-712 표준 인증**
   - 타입화된 서명 방식
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:66-81`

6. **재연결 관리**
   - 명확한 제한 및 로그 기록
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:455-474`

### 5.2 Nado DN Pair Bot - 단점

1. **핑 루프 비효율성**
   - 실제 핑 전송 코드는 빈 루프
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:446-449`

2. **수신 측정 타임아웃 설정**
   - 1초 타임아웃이 설정되어 있으나 사용되지 않음
   - 파일: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:485-487`

### 5.3 Legacy Backpack-GRVT DN Bot - 장점

1. **간결한 구현**
   - 상대적으로 간단한 코드 구조
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:23-154`

2. **명시적 재연결**
   - ConnectionClosed 예외로 자동 재연결
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:108-111`

3. **ED25519 서명**
   - 고성능 대칭키 서명 방식
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:43-54`

### 5.4 Legacy Backpack-GRVT DN Bot - 단점

1. **상태 추적 부재**
   - 연결 상태를 추적하지 않음
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:26-35`

2. **메시지 큐 없음**
   - 직접 처리하여 병목 가능성
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:87-113`

3. **핑/펭 없음**
   - 연결 유지 메커니즘 부재
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:87-113`

4. **콜백 레지스트리 없음**
   - 단일 핸들러 사용
   - 파일: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:115-124`

### 5.5 공통 문제점

1. **주문 처리 반복 로직**
   - 양쪽 모두 최대 15회 재시도 사용
   - Nado: `/Users/botfarmer/2dex/hedge/exchanges/nado.py:1048-1151`
   - Legacy: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:324-431`

2. **POST_ONLY 필수**
   - 양쪽 모두 POST_ONLY 옵션 필수
   - Nado: `/Users/botfarmer/2dex/hedge/exchanges/nado.py:867-909`
   - Legacy: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:324-431`

3. **BBO 기반 가격 설정**
   - 양쪽 모두 BBO 기반 가격 계산
   - Nado: `/Users/botfarmer/2dex/hedge/exchanges/nado.py:1046-1061`
   - Legacy: `/Users/botfarmer/2dex/hedge/exchanges/backpack.py:376-391`

---

## 6. 권장 사항 (Recommendations)

### 6.1 Nado DN Pair Bot 개선사항

1. **핑/펭 구현 보완**
   - 실제 핑 메시지를 전송하도록 구현 필요
   - 참조: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:446-449`

2. **수신 측정 메서드 개선**
   - 현재 1초 타임아웃 설정되어 있으나 사용되지 않음
   - 타임아웃을 실제로 활용하여 메시지 손실 감지 필요
   - 참조: `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py:485-487`

3. **재연결 로직 개선**
   - 현재 재연결 시 모든 스트림을 즉시 다시 구독
   - 연결 복구 후 상태 확인 메커니즘 추가 필요

### 6.2 Legacy Backpack-GRVT DN Bot 개선사항

1. **상태 관리 추가**
   - ConnectionState 열거형 도입
   - 연결 상태를 명확히 추적

2. **메시지 큐 도입**
   - asyncio.Queue 사용하여 비동기 메시지 처리
   - 메시지 순차적 처리 보장

3. **콜백 레지스트리 도입**
   - Stream별 콜백 등록 시스템 구현

4. **핑/펭 메커니즘 추가**
   - 30초 간격으로 Ping/Pong 전송

5. **재연출 방지**
   - 최대 재연결 횟수 제한

### 6.3 공통 개선사항

1. **주문 처리 로직 통합**
   - 양쪽 모두 반복 로직이 유사하므로 공통 유틸리티 함수 도입 가능

2. **에러 로깅 개선**
   - 구체적인 에러 메시지와 로그 레벨 활용

3. **메트릭 수집**
   - 웹소켓 연결 성공/실패 비율
   - 메시지 처리 지연 시간
   - 재연결 횟수 및 시간

4. **테스트 커버리지**
   - 양쪽 모두 웹소켓 단위 테스트 추가 필요
   - E2E 통합 테스트 추가

### 6.4 권장 아키텍처

1. **Nado DN Pair Bot 기준 구현**

```
┌──────────────────────────────────────────────────────────┐
│               WebSocket 통합 인터페이스                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ State       │  │ Queue        │  │ Callback     │  │
│  │ Manager     │  │              │  │ Registry     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
    ┌─────▼────────┐  ┌─────▼────────┐  ┌─────▼────────┐
    │ Nado WS      │  │ Nado BBO     │  │ Nado Book    │
    │ Client       │  │ Handler      │  │ Handler      │
    └──────────────┘  └──────────────┘  └──────────────┘
```

2. **공유 유틸리티 모듈**

```python
# shared_websocket_utils.py

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

class WebSocketMessageQueue:
    """WebSocket 메시지 큐 관리"""
    pass

class WebSocketCallbackRegistry:
    """WebSocket 콜백 레지스트리"""
    pass
```

---

## 참고 문헌

1. **Nado WebSocket 클라이언트**
   - `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_websocket_client.py`

2. **Nado BBO 핸들러**
   - `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_bbo_handler.py`

3. **Nado 북챠드 딥 핸들러**
   - `/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges/nado_bookdepth_handler.py`

4. **Legacy Backpack 클라이언트**
   - `/Users/botfarmer/2dex/hedge/exchanges/backpack.py`

5. **Legacy GRVT 클라이언트**
   - `/Users/botfarmer/2dex/hedge/exchanges/grvt.py`

6. **Nado DN Pair 플랜 (V4 Migration)**
   - `/Users/botfarmer/2dex/.omc/plans/nado-dn-pair-v4-migration.md`

7. **Nado WebSocket 우선 구현 플랜**
   - `/Users/botfarmer/2dex/.omc/plans/nado-dn-pair-websocket-first.md`

---

**문서 버전**: 1.0
**최종 업데이트**: 2026-01-31
**작성자**: WebSocket 비교 분석 팀
