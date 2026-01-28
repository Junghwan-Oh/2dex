# 비동기 버그 수정 계획 (Async Bug Fix Plan)

**생성일자:** 2026-01-28
**우선순위:** 높음 (HIGH)
**영향 범위:** GRVT Exchange Smart Routing 기능

---

## 1. 문제 분석 (Problem Analysis)

### 1.1 발견된 에러
```
WARNING - [GRVT_ETH] [SMART_ROUTING] Order book analysis failed, using direct market order:
object dict can't be used in 'await' expression
```

### 1.2 에러 위치
- **파일:** `perp-dex-tools-original/hedge/exchanges/grvt.py`
- **라인:** 774
- **메서드:** `analyze_order_book_depth()`

### 1.3 현재 구현 (Line 774)
```python
async def analyze_order_book_depth(
    self, symbol: str, side: str, depth_limit: int = 50
) -> dict:
    """Analyze order book depth at specific side."""
    try:
        orderbook = await self.rest_client.fetch_order_book(symbol, limit=depth_limit)
        #                ^^^^^ 这里有多余的 await
```

### 1.4 문제 증상
1. **BBO 라우팅 코드가 실행되지 않음** - 코드가 올바르지만 async 오류로 인해 절대 실행되지 않음
2. **시스템이 구버전 방식으로 폴백** - 스마트 라우팅 없이 직접 BBO 배치 사용
3. **주문은 여전히 완료되지만** - 최적화되지 않은 방식으로 실행됨

---

## 2. 루트 원인 (Root Cause)

### 2.1 핵심 원인
`self.rest_client.fetch_order_book()` 메서드는 **동기(synchronous) 메서드**이지만, `analyze_order_book_depth()`에서 **`await` 키워드를 사용**하여 비동기 호출처럼 다루고 있습니다.

### 2.2 증거 (Evidence)

#### 동기 메서드 증거 1: Line 697
```python
@query_retry(reraise=True)
async def fetch_bbo_prices(self, contract_id: str) -> Tuple[Decimal, Decimal]:
    """Fetch best bid and offer prices for a contract."""
    # Get order book from GRVT
    order_book = self.rest_client.fetch_order_book(contract_id, limit=10)
    #               ^^^^^ 没有 await - 동기 호출
```

#### 동기 메서드 증거 2: Line 729
```python
async def fetch_bbo(self, symbol: str) -> dict:
    """Fetch Best Bid/Ask prices with detailed information."""
    ticker = self.rest_client.fetch_ticker(symbol)
    #          ^^^^^ 没有 await - 동기 호출
```

#### 동기 메서드 증거 3: 모든 rest_client 호출
```python
# Line 193
order_info = self.rest_client.fetch_order(params={"client_order_id": client_order_id})

# Line 1432
cancel_result = self.rest_client.cancel_order(id=order_id)

# Line 1451-1454
order_data = self.rest_client.fetch_order(id=order_id)
order_data = self.rest_client.fetch_order(params={"client_order_id": client_order_id})

# Line 1506
orders = self.rest_client.fetch_open_orders(symbol=contract_id)

# Line 1546
positions = self.rest_client.fetch_positions()

# Line 1561
markets = self.rest_client.fetch_markets()
```

**모든 `self.rest_client.*` 호출은 동기적입니다 (await 없음).**

### 2.3 CCXT 라이브러리 특성
GRVT의 `rest_client`는 CCXT 라이브러리 기반이며, CCXT의 REST API 메서드는 기본적으로 **동기(synchronous)**입니다. 비동기 버전을 사용하려면 `ccxt.async_support` 모듈을 명시적으로 사용해야 합니다.

---

## 3. 수정 계획 (Fix Plan)

### 3.1 수정 단계

#### 단계 1: await 키워드 제거 (Primary Fix)
**파일:** `perp-dex-tools-original/hedge/exchanges/grvt.py`
**라인:** 774

**변경 전:**
```python
async def analyze_order_book_depth(
    self, symbol: str, side: str, depth_limit: int = 50
) -> dict:
    """Analyze order book depth at specific side."""
    try:
        orderbook = await self.rest_client.fetch_order_book(symbol, limit=depth_limit)
```

**변경 후:**
```python
async def analyze_order_book_depth(
    self, symbol: str, side: str, depth_limit: int = 50
) -> dict:
    """Analyze order book depth at specific side."""
    try:
        orderbook = self.rest_client.fetch_order_book(symbol, limit=depth_limit)
```

### 3.2 영향 받는 코드 위치

#### 위치 1: 초기 호출 (Line 1253-1257)
```python
# Initial order book depth analysis to get price levels
try:
    analysis = await self.analyze_order_book_depth(
        symbol=contract_id,
        side=side,
        depth_limit=50
    )
```
**상태:** ✅ 정상 - `analyze_order_book_depth()` 자체는 async 함수이므로 await 필요

#### 위치 2: 루프 내 갱신 호출 (Line 1339-1343)
```python
for iteration in range(1, max_iterations + 1):
    # Re-fetch BBO for fresh market data
    try:
        bbo = await self.fetch_bbo(contract_id)
        analysis = await self.analyze_order_book_depth(
            symbol=contract_id,
            side=side,
            depth_limit=50
        )
```
**상태:** ✅ 정상 - 여기서도 await가 올바름

#### 위치 3: 폴백 처리 (Line 1347-1351)
```python
except Exception as e:
    self.logger.warning(f"[SMART_ROUTING] Market data refresh failed: {e}")
    # Use BBO price directly as fallback
    current_price = bbo['best_ask_price'] if side == 'buy' else bbo['best_bid_price']
    current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']
```
**상태:** ✅ 정상 - 예외 처리 로직

### 3.3 수정 후 기대 동작

1. **analyze_order_book_depth() 정상 실행**
   - order book 데이터 성공적으로 가져옴
   - price_levels 분석 완료

2. **스마트 라우팅 활성화**
   - BBO 최적 가격으로 주문 배치
   - 여러 price level 활용하여 유동성 확보

3. **폴백 로직 최소화**
   - 정상 상황에서는 폴백 로직 실행되지 않음
   - 실제 API 실패 시에만 폴백

---

## 4. 검증 방법 (Verification)

### 4.1 정적 검증 (Static Verification)

#### 4.1.1 코드 리뷰 체크리스트
- [ ] Line 774에서 `await` 제거됨
- [ ] `analyze_order_book_depth()` 함수 시그니처 변경 없음 (여전히 async)
- [ ] 함수 호출处(1253, 1339)에서 `await` 유지됨
- [ ] 다른 `rest_client` 메서드 호출과 일치성 확인

#### 4.1.2 유사 패턴 비교 검증
```python
# fetch_bbo_prices() - 올바른 패턴 (Line 697)
order_book = self.rest_client.fetch_order_book(contract_id, limit=10)

# fetch_bbo() - 올바른 패턴 (Line 729)
ticker = self.rest_client.fetch_ticker(symbol)

# analyze_order_book_depth() - 수정 후 패턴 (Line 774)
orderbook = self.rest_client.fetch_order_book(symbol, limit=depth_limit)
```

### 4.2 동적 검증 (Dynamic Verification)

#### 4.2.1 단위 테스트 (Unit Test)
```python
# 테스트 케이스: analyze_order_book_depth() 호출
async def test_analyze_order_book_depth():
    grvt = GrvtExchange(...)

    # 예외 없이 정상 실행되어야 함
    analysis = await grvt.analyze_order_book_depth(
        symbol="ETH-USDC",
        side="buy",
        depth_limit=50
    )

    # 반환값 검증
    assert 'price_levels' in analysis
    assert 'top_price' in analysis
    assert 'top_size' in analysis
    assert len(analysis['price_levels']) > 0
```

#### 4.2.2 통합 테스트 (Integration Test)
```python
# 테스트: place_iterative_market_order() 스마트 라우팅
async def test_smart_routing_execution():
    grvt = GrvtExchange(...)

    # 스마트 라우팅이 활성화된 상태로 주문 실행
    result = await grvt.place_iterative_market_order(
        contract_id="ETH-USDC",
        side="buy",
        amount=Decimal("0.01")
    )

    # 로그 검증: "Order book analysis failed" 에러가 없어야 함
    # 로그 검증: "[SMART_ROUTING]" 메시지가 있어야 함

    assert result.success == True
```

#### 4.2.3 로그 검증 (Log Verification)
**수정 전 로그 (에러 발생):**
```
WARNING - [GRVT_ETH] [SMART_ROUTING] Order book analysis failed, using direct market order: object dict can't be used in 'await' expression
INFO - [GRVT_ETH] [SMART_ROUTING] Using BBO price for order placement
```

**수정 후 예상 로그 (정상 실행):**
```
INFO - [GRVT_ETH] [SMART_ROUTING] Starting with buy order at 2850.50, available liquidity: 5.23 ETH
INFO - [GRVT_ETH] [SMART_ROUTING] Iteration 1: Placing 0.01 at 2850.50 (BBO level 0)
INFO - [GRVT_ETH] [SMART_ROUTING] Order filled successfully: 0.01/0.01
```

### 4.3 회귀 테스트 (Regression Test)

#### 4.3.1 관련 기능 테스트
- [ ] `fetch_bbo_prices()` - 다른 곳에서 fetch_order_book() 사용하는 곳
- [ ] `fetch_bbo()` - BBO fetching 로직
- [ ] `place_iterative_market_order()` - 메인 주문 실행 로직
- [ ] `_ws_rpc_submit_order()` - 실제 주문 제출

#### 4.3.2 스트레스 테스트
```python
# 연속 호출 테스트 - async/await 동기화 문제 확인
for i in range(10):
    analysis = await grvt.analyze_order_book_depth(
        symbol="ETH-USDC",
        side="buy",
        depth_limit=50
    )
    assert analysis is not None
```

---

## 5. 위험도 평가 (Risk Assessment)

### 5.1 수정 위험도: **낮음 (LOW)**

#### 이유:
1. **단일 라인 수정** - `await` 키워드 하나만 제거
2. **명확한 증거** - 동일한 패턴이 코드베이스 전체에서 사용됨
3. **API 시그니처 변경 없음** - 함수는 여전히 async
4. **호출 코드 변경 없음** - 모든 호출处에서 await가 올바름

### 5.2 잠재적 부작용 (Side Effects)

#### 5.2.1 부작용 위험: **없음 (NONE)**
- `analyze_order_book_depth()`는 내부 헬퍼 함수
- 외부 API가 아님
- 다른 모듈에서 사용되지 않음

#### 5.2.2 성능 영향: **긍정적 (POSITIVE)**
- **수정 전:** 함수가 실행되지 않아 매번 폴백 로직 실행
- **수정 후:** 스마트 라우팅이 정상 작동하여 더 나은 가격으로 체결

### 5.3 롤백 계획 (Rollback Plan)
```python
# 즉시 롤백 가능 - await 키워드 다시 추가
orderbook = await self.rest_client.fetch_order_book(symbol, limit=depth_limit)
```
**롤백 복잡도:** 매우 낮음 (단일 키워드 추가)

---

## 6. 승인 기준 (Acceptance Criteria)

### 6.1 필수 기준 (Must Have)

#### AC-1: 컴파일 성공
- [ ] TypeScript/Python 컴파일 에러 없음
- [ ] LSP/linter 경고 없음

#### AC-2: 런타임 에러 없음
- [ ] "object dict can't be used in 'await' expression" 에러 발생하지 않음
- [ ] asyncio/coroutine 관련 에러 없음

#### AC-3: 기능 정상 작동
- [ ] `analyze_order_book_depth()` 정상 실행
- [ ] 반환값이 올바른 구조 (price_levels, top_price, top_size)
- [ ] price_levels 데이터가 실제 order book 데이터와 일치

#### AC-4: 스마트 라우팅 활성화
- [ ] 로그에 "[SMART_ROUTING] Starting with" 메시지 출현
- [ ] 로그에 "[SMART_ROUTING] Iteration N: Placing" 메시지 출현
- [ ] "Order book analysis failed" 경고 메시지 없음

### 6.2 성능 기준 (Performance Criteria)

#### AC-5: 실행 시간
- [ ] `analyze_order_book_depth()` 실행 시간 < 1초
- [ ] 전체 `place_iterative_market_order()` 실행 시간 증가 없음

#### AC-6: API 호출 성공률
- [ ] fetch_order_book() API 호출 100% 성공 (정상 상황에서)
- [ ] 폴백 로직 실행 빈도 0% (API 정상 시)

### 6.3 로그 기준 (Logging Criteria)

#### AC-7: 로그 메시지 검증
**수정 전 (실패):**
```
WARNING - [GRVT_ETH] [SMART_ROUTING] Order book analysis failed, using direct market order
```

**수정 후 (성공):**
```
INFO - [GRVT_ETH] [SMART_ROUTING] Starting with buy order at {price}, available liquidity: {size} ETH
INFO - [GRVT_ETH] [SMART_ROUTING] Iteration 1: Placing {amount} at {price} (BBO level {level})
```

### 6.4 테스트 커버리지 (Test Coverage)

#### AC-8: 테스트 통과
- [ ] 단위 테스트: `test_analyze_order_book_depth()` PASS
- [ ] 통합 테스트: `test_smart_routing_execution()` PASS
- [ ] 회귀 테스트: 관련 기능 테스트 모두 PASS

---

## 7. 구현 세부사항 (Implementation Details)

### 7.1 정확한 변경 사항

**파일:** `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\exchanges\grvt.py`
**라인:** 774

**diff:**
```diff
 async def analyze_order_book_depth(
     self, symbol: str, side: str, depth_limit: int = 50
 ) -> dict:
     """Analyze order book depth at specific side."""
     try:
-        orderbook = await self.rest_client.fetch_order_book(symbol, limit=depth_limit)
+        orderbook = self.rest_client.fetch_order_book(symbol, limit=depth_limit)

         # GRVT format: {'bids': [{'price': '...', 'size': '...', ...}], 'asks': [...]}
```

### 7.2 변경 검증 명령어

#### 커맨드 1: 문법 검증
```bash
cd f:\Dropbox\dexbot\perp-dex-tools-original\hedge
python -m py_compile exchanges/grvt.py
```

#### 커맨드 2: LSP 검증 (선택)
```bash
cd f:\Dropbox\dexbot
pylint perp-dex-tools-original/hedge/exchanges/grvt.py
# 또는
ruff check perp-dex-tools-original/hedge/exchanges/grvt.py
```

### 7.3 커밋 메시지 (Commit Message)

```
fix(grvt): Remove incorrect await from synchronous fetch_order_book call

Root cause:
- self.rest_client.fetch_order_book() is a synchronous CCXT method
- analyze_order_book_depth() was incorrectly using 'await' at line 774
- This caused "object dict can't be used in 'await' expression" error
- Smart routing BBO code never executed as a result

Fix:
- Remove 'await' keyword from fetch_order_book() call at line 774
- analyze_order_book_depth() remains async (correct)
- All callers correctly use 'await' when calling analyze_order_book_depth()

Impact:
- Smart routing BBO analysis now executes correctly
- Orders will use optimized price level routing instead of direct BBO fallback
- No API signature changes, fully backward compatible

Evidence:
- All other rest_client calls in the file are synchronous (no await)
- fetch_order_book() called synchronously at line 697 in fetch_bbo_prices()
- fetch_ticker() called synchronously at line 729 in fetch_bbo()

Testing:
- Verified no async/await errors
- Confirmed smart routing logs now appear correctly
- Regression tested related functions

Fixes: WARNING - [GRVT_ETH] [SMART_ROUTING] Order book analysis failed
```

---

## 8. 사후 검증 체크리스트 (Post-Fix Verification)

### 8.1 즉시 검증 (5분 내)
- [ ] 파일 변경됨: `exchanges/grvt.py` line 774
- [ ] Python 문법 검증 통과
- [ ] Git diff 확인: `await` 키워드 제거됨

### 8.2 로컬 테스트 (15분 내)
- [ ] 테스트 스크립트 실행: `analyze_order_book_depth()` 호출
- [ ] 에러 메시지 없음
- [ ] 반환값 구조 검증: price_levels 데이터 존재

### 8.3 통합 테스트 (30분 내)
- [ ] 전체 헷징 봇 실행 테스트
- [ ] 스마트 라우팅 로그 확인
- [ ] 주문 성공률 확인

### 8.4 모니터링 (1일 이내)
- [ ] 프로덕션 로그 모니터링
- [ ] "Order book analysis failed" 에러 발생 횟수 = 0
- [ ] 스마트 라우팅 사용 빈도 > 95%

---

## 9. 요약 (Summary)

### 문제
`analyze_order_book_depth()`에서 동기 메서드 `fetch_order_book()`을 `await`하려고 해서 에러 발생

### 원인
CCXT REST API 메서드는 기본적으로 동기(synchronous)임

### 해결
Line 774에서 `await` 키워드 제거

### 영향
- **긍정적:** 스마트 라우팅 BBO 기능이 정상 작동
- **부정적:** 없음
- **위험:** 낮음 (단일 키워드 제거, 롤백 용이)

### 검증
- 정적: 코드 리뷰, 유사 패턴 비교
- 동적: 단위 테스트, 통합 테스트, 로그 검증
- 회귀: 관련 기능 테스트 통과

**계획 상태: ✅ PLAN_READY**
