# Nado DN Pair Trading Bot - 진행 상황 보고

**날짜**: 2026-01-30
**버전**: v0.5

---

## 완료된 작업

### ✅ P0: Critical Bug Fixes (완료)

#### 1. BookDepth 데이터 플로우 수정
**문제**: BookDepth handler가 999999 bps 반환 (데이터 미수신)

**원인 분석**:
1. `sortedcontainers` 모듈 미설치
2. product_id 매핑 오류 (ETH: 2→4, SOL: 누락)
3. TradingLogger를 handler에 전달 (내부 logger 필요)

**해결**:
```bash
pip3 install sortedcontainers
```

```python
# exchanges/nado.py
def _get_product_id_from_contract(self, contract_id: str) -> int:
    ticker_to_product_id = {
        'WBTC': 1,
        'ETH': 4,      # 수정: 2 → 4
        'SOL': 8,      # 추가
    }
    return ticker_to_product_id.get(ticker, 1)

# Handlers에 내부 logger 전달
self._bbo_handler = BBOHandler(..., logger=self.logger.logger)
self._bookdepth_handler = BookDepthHandler(..., logger=self.logger.logger)
```

**검증**:
```
Bids: 11 levels, Asks: 11 levels
Best bid: $2844.7, Best ask: $2844.8
Slippage: 0 bps (0.01 ETH)
```

#### 2. SOL 거래 검증
**결과**: 정상 체결 확인
```
SOL order: FILLED -0.8 @ $117.89
SOL close: FILLED 0.8 @ $118.03
```

#### 3. Isolated 마진 주문 적용
**변경**: 모든 주문을 `isolated=True`로 변경

```python
# 변경 전 (cross margin)
appendix=build_appendix(order_type=OrderType.IOC)

# 변경 후 (isolated margin)
appendix=build_appendix(order_type=OrderType.IOC, isolated=True)
```

**적용 위치**:
- `place_open_order()` - POST_ONLY (line 441)
- `place_ioc_order()` - IOC (line 513)
- `place_close_order()` - POST_ONLY (line 611)

---

### ✅ P1: V4 헬퍼 함수 포팅 (완료)

**참조**: `perp-dex-tools-original/hedge/exchanges/grvt.py`

#### 1. `calculate_timeout(quantity: Decimal) -> int`
```python
def calculate_timeout(self, quantity: Decimal) -> int:
    """주문 크기별 타임아웃"""
    quantity_float = float(quantity)
    if quantity_float <= 0.1:
        return 5    # 0.1 ETH → 5s
    elif quantity_float <= 0.5:
        return 10   # 0.5 ETH → 10s
    else:
        return 20   # 1.0+ ETH → 20s
```

#### 2. `extract_filled_quantity(order_result: dict) -> Decimal`
```python
def extract_filled_quantity(self, order_result: dict) -> Decimal:
    """다양한 포맷에서 체결 수량 추출 (x18 지원)"""
    # state/traded_size (x18 format)
    # list format [price, size]
    # dict format {size: ..., traded_size: ...}
    # metadata format (returns 0)
```

#### 3. `calculate_slippage_bps(...) -> Decimal`
```python
def calculate_slippage_bps(self, execution_price, reference_price) -> Decimal:
    """베이시스 포인트 슬리피지 계산"""
    return abs(execution_price - reference_price) / reference_price * 10000
```

**테스트**: 17/17 통과

---

### ✅ P1: 프로덕션 테스트 (완료)

#### $100 헷징 테스트 결과
```
ETH: 0.035 @ $2847.4 → 0.035 @ $2843.4
SOL: -0.8 @ $117.89 → 0.8 @ $118.03

Cycle time: ~3초
Fill rate: 100%
Position drift: <1%
```

---

### ⚠️ P2: WebSocket Fill 모니터링 (부분 완료)

#### 구현 완료
1. ✅ `FillHandler` 클래스 (`exchanges/nado_fill_handler.py`)
   - 실시간 체결 감지
   - 주문 추적 및 timeout 처리
   - Callback 지원

2. ✅ `PositionChangeHandler` 클래스 (`exchanges/nado_position_handler.py`)
   - 실시간 포지션 업데이트
   - 포지션 변화 기록
   - Callback 지원

3. ✅ WebSocket client subaccount 파라미터
   ```python
   await ws_client.subscribe("fill", product_id=4, subaccount=subaccount_hex)
   ```

4. ✅ 단위 테스트: 12/12 통과

#### ✅ EIP-712 인증 구현 (완료)

**구현 내용**:
```python
# exchanges/nado_websocket_client.py
async def authenticate(self) -> None:
    """EIP-712 StreamAuthentication signing"""
    # Calculate subaccount bytes32
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=self._owner,
        subaccount_name=self._subaccount_name,
    ))

    # Calculate expiration (60 seconds from now)
    expiration = int(time.time() * 1000) + 60000

    # Create message to sign
    message = {
        "sender": subaccount_hex,
        "expiration": expiration
    }

    # Sign using EIP-712
    encoded_message = encode_typed_data(
        domain_data=self.EIP712_DOMAIN,
        message_types=self.EIP712_TYPES,
        message_data=message
    )

    signed_message = Account.from_key(self._private_key).sign_message(encoded_message)

    # Send authentication message
    auth_msg = {
        "method": "authenticate",
        "tx": message,
        "signature": signed_message.signature.hex(),
        "id": str(int(time.time() * 1000) % 1000000)
    }

    await self._ws.send(json.dumps(auth_msg))
```

**EIP-712 Domain**:
```python
EIP712_DOMAIN = {
    "name": "StreamAuthentication",
    "version": "1",
    "chainId": 542210,
    "verifyingContract": "0x3646be143c3873771dbeee0758af4a44b19ef5a3"
}
```

**테스트 결과**:
```
tests/test_eip712_auth.py 실행 결과:
Test 1 (Authentication): PASS ✅
- Fill stream subscription 성공
- 인증 오류 없음
```

**수정된 파일**:
- `exchanges/nado_websocket_client.py`: EIP-712 인증 구현
- `exchanges/nado.py`: WebSocket 클라이언트에 자격 증명 전달
- `tests/test_eip712_auth.py`: 인증 테스트 (신규)

---

## 파일 구조

```
exchanges/
├── nado.py                          # Nado 클라이언트 (isolated 적용 완료)
├── nado_websocket_client.py          # WebSocket (subaccount 지원 완료)
├── nado_bbo_handler.py              # BBO handler
├── nado_bookdepth_handler.py         # BookDepth handler
├── nado_fill_handler.py              # Fill handler (신규)
└── nado_position_handler.py          # PositionChange handler (신규)

hedge/
└── test_dn_pair.py                   # $100 헷징 테스트

tests/
├── test_v4_helpers.py                # V4 헬퍼 테스트 (17/17 통과)
├── test_fill_handler.py              # Fill handler 테스트 (12/12 통과)
├── test_fill_integration.py          # Fill 통합 테스트
├── test_fill_real_order.py           # 실제 주문 Fill 테스트
└── debug_websocket_messages.py      # WebSocket 메시지 디버그
```

---

## 다음 단계 (옵션)

### 옵션 1: 메인 DN 전략에 BookDepth 통합
**목표**: Slippage를 고려한 정확한 주문 실행

**작업**:
- `hedge/DN_pair_eth_sol_nado.py`에 BookDepth slippage estimation 통합
- 주문 전 용량 확인
- Slippage 과다 시 주문 크기 조정

**예상 시간**: 2-3시간

---

### 옵션 2: 대규모 테스트
**목표**: 프로덕션 배포 전 안정성 확보

**작업**:
- $500-$1000 규모 테스트
- 50회 이상 반복
- 메트릭 수집

**예상 시간**: 3-4시간

---

### 옵션 3: WebSocket Fill 모니터링 완료
**목표**: 실시간 체결 감지로 rate limit 해결

**추가 작업**:
- EIP-712 StreamAuthentication 구현
- WebSocket 인증 로직
- 통합 테스트

**예상 시간**: 2-3시간

---

## 기술 스택

- **거래소**: Nado testnet (`wss://gateway.test.nado.xyz/v1/subscribe`)
- **Product IDs**: ETH=4, SOL=8
- **주문 타입**: IOC (Immediate-Or-Cancel), POST_ONLY
- **마진 모드**: Isolated (cross에서 변경)
- **WebSocket**: Public streams (BBO, BookDepth, Trade)
- **인증**: EIP-712 (private streams용)

---

## 참고 자료

- [Nado Docs - Streams](https://docs.nado.xyz/developer-resources/api/subscriptions/streams)
- [Nado Docs - Authentication](https://docs.nado.xyz/developer-resources/api/subscriptions/authentication)
- V4 reference: `perp-dex-tools-original/hedge/exchanges/grvt.py`

---

---

### ✅ P1: BookDepth DN 전략 통합 검증 (완료)

**발견**: `hedge/DN_pair_eth_sol_nado.py`에 이미 BookDepth 통합 구현됨

```python
async def calculate_order_size_with_slippage(
    self,
    price: Decimal,
    ticker: str,
    direction: str,
    max_slippage_bps: int = 20
) -> Tuple[Decimal, Decimal, bool]:
    """BookDepth 데이터로 슬리피지 체크 후 주문 수량 계산"""
    client = self.eth_client if ticker == "ETH" else self.sol_client
    raw_qty = self.target_notional / price
    tick_size = client.config.tick_size
    target_qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

    # BookDepth에서 슬리피지 추정
    slippage = await client.estimate_slippage(direction, target_qty)

    if slippage >= Decimal(999999):
        # BookDepth 데이터 없음
        self.logger.warning(f"[SLIPPAGE] No BookDepth data for {ticker}, using target quantity {target_qty}")
        return target_qty, Decimal(0), True

    # 슬리피지 허용 범위 체크
    if slippage <= max_slippage_bps:
        return target_qty, slippage, True
    else:
        # 슬리피지 과다 시 수량 조정
        can_exit, exitable_qty = await client.check_exit_capacity(
            target_qty if direction == "sell" else -target_qty,
            max_slippage_bps
        )
        if not can_exit:
            self.logger.warning(
                f"[SLIPPAGE] {ticker} slippage {slippage:.1f} bps > {max_slippage_bps} bps limit, "
                f"reducing qty from {target_qty} to {exitable_qty}"
            )
            return exitable_qty, slippage, False
```

**최종 검증 결과 (2026-01-30 04:00 UTC)**:
```
DN Pair Bot BookDepth 통합 테스트:
- ETH Order Book: 1 bids, 2 asks
- Best bid: $2791.6 (qty: 1.64)
- Best ask: $2822 (qty: 0.482)
- Buy 0.01 ETH slippage: 0 bps
- ✅ BookDepth working!

참고: Nado testnet 유동성이 낮아 오더북이 천천히 구축됨
(BookDepth 메시지는 수신 중이지만 대부분 삭제 메시지 qty=0)
```

**수정된 파일**:
- `hedge/test_dn_pair.py`: ETH tick_size 0.1 → 0.001 정정

---

## 다음 단계 (옵션)

### 옵션 1: Fill 메시지 수신 검증 (새로 추가)
**목표**: 실제 주문 체결 시 Fill WebSocket 메시지 수신 확인

**작업**:
- 계정 health 문제 해결 (충분한 담보금 입금)
- 실제 주문 실행 후 Fill 메시지 수신 확인
- PositionChange 메시지 수신 확인

**예상 시간**: 1-2시간

---

### 옵션 2: 대규모 테스트
**목표**: 프로덕션 배포 전 안정성 확보

**작업**:
- $500-$1000 규모 테스트
- 50회 이상 반복
- 메트릭 수집

**예상 시간**: 3-4시간

---

### 옵션 3: 프로덕션 배포
**목표**: Nado 메인넷 배포

**작업**:
- 환경 변수 설정 (NADO_MODE=MAINNET)
- 메인넷 endpoint 변경
- 프로덕션 모니터링 설정

**예상 시간**: 2-3시간
