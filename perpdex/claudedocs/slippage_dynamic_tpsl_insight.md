# Slippage와 동적 TP/SL 전략 인사이트

## 날짜: 2025-01-XX

## 발견한 문제

### ApeX Pro 신생 DEX의 슬리피지 현실
- **실제 사례**: Order ID `769561569622229354`
  - Limit Price: 110,512.1 USDT
  - Entry Price: 110,559.6 USDT
  - **슬리피지**: +47.5 포인트 (0.043%)

### 기존 전략의 문제점

**정적 TP/SL 방식 (Limit Price 기준)**:
```python
# ❌ 문제: Limit price 기준으로 미리 TP/SL 설정
limit_price = 110,512.1
tp = limit_price * 1.001  # 110,622.6
sl = limit_price * 0.999  # 110,401.6

# 실제 체결: 110,559.6 (슬리피지 +47.5)
# → TP까지 거리: 110,622.6 - 110,559.6 = 63 포인트
# → 목표 0.1% (110.5 포인트)가 아니라 0.057%만 남음!
# → 실제 손익비가 왜곡됨
```

**고빈도 전략에 치명적인 이유**:
1. TP 목표가 0.1% → 실제로는 0.057%로 축소
2. 슬리피지가 불리한 방향이면 손실 확대
3. 정확한 손익 관리 불가능
4. 승률과 손익비 예측 불가능

---

## 핵심 인사이트: 웹소켓 활용 동적 TP/SL

### 전략 개요
슬리피지는 양방향으로 발생할 수 있다:
- **유리한 슬리피지**: Entry price가 limit보다 좋게 체결 → 보너스
- **불리한 슬리피지**: Entry price가 limit보다 나쁘게 체결 → 손실

**핵심 아이디어**:
- Limit price 기준이 아닌 **실제 Entry Price 기준**으로 TP/SL 설정
- 웹소켓으로 체결가를 실시간 캐치하여 즉시 TP/SL 재계산

### 구현 방식

```python
# ✅ 해결책: 실제 Entry Price 기준 동적 TP/SL

# 1단계: Limit order만 제출 (TP/SL 없이)
submit_limit_order(side='BUY', size=0.001, price=110,512.1)

# 2단계: 웹소켓으로 체결 실시간 캐치
@websocket.on('position_update')
def on_fill(data):
    entry_price = data['entry_price']  # 110,559.6

    # 3단계: 실제 entry price 기준으로 TP/SL 계산
    tp_price = entry_price * (1 + 0.001)  # 110,670.2 (정확한 +0.1%)
    sl_price = entry_price * (1 - 0.001)  # 110,449.0 (정확한 -0.1%)

    # 4단계: TP/SL 주문 즉시 제출 (수 밀리초 내)
    submit_conditional_orders(tp=tp_price, sl=sl_price)
```

---

## 전략의 장점

### 1. 정확한 손익 관리
- 슬리피지 방향과 무관하게 **항상 정확한 TP/SL 비율** 유지
- 목표 0.1% → 실제로도 정확히 0.1%

### 2. 유리한 슬리피지 활용
- 슬리피지가 유리한 방향이면 그만큼 추가 이익
- 불리한 슬리피지도 TP/SL로 정확히 헷지

### 3. 웹소켓 실시간성 완전 활용
- 체결 즉시 (수 밀리초 내) TP/SL 설정
- ApeX Pro 웹소켓 API의 낮은 레이턴시 활용

### 4. 고빈도 전략 가능
- 정확한 손익률 보장으로 작은 TP/SL (0.05~0.1%)도 실용적
- 슬리피지가 큰 신생 DEX에서도 고빈도 전략 유지 가능

---

## 기술적 구현 요구사항

### WebSocket 이벤트 처리
```python
async def wait_for_position_fill(self, order_id: str, timeout: float = 10.0):
    """포지션 체결 대기"""
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < timeout:
        # WebSocket에서 position update 이벤트 확인
        if order_id in self.filled_orders:
            return self.filled_orders[order_id]
        await asyncio.sleep(0.01)  # 10ms 폴링

    raise TimeoutError(f"Position fill timeout for order {order_id}")
```

### 동적 TP/SL 설정
```python
async def submit_dynamic_tp_sl(self, entry_price: float, tp_pct: float, sl_pct: float):
    """실제 체결가 기준 TP/SL 계산 및 제출"""
    tp_price = entry_price * (1 + tp_pct)
    sl_price = entry_price * (1 - sl_pct)

    # Conditional order 제출 (TP/SL)
    await self.client.create_conditional_order(
        symbol=self.symbol,
        trigger_price_type='MARK',  # Mark price 기준
        # ... TP/SL 주문 파라미터
    )
```

---

## 성능 지표 예측

### 기존 정적 방식 vs 동적 방식

| 항목 | 정적 TP/SL | 동적 TP/SL |
|------|-----------|-----------|
| 실제 TP 비율 | 0.057% ~ 0.143% (변동) | 항상 정확히 0.1% |
| 손익비 안정성 | 불안정 | 안정 |
| 슬리피지 활용 | 불가능 | 가능 |
| 고빈도 적합성 | 낮음 | 높음 |
| 구현 복잡도 | 낮음 | 중간 |
| 레이턴시 증가 | 0ms | ~10-50ms (체결 대기) |

### 예상 성능
- **정확한 리스크 관리**: 슬리피지가 ±0.05%여도 TP/SL은 정확히 0.1% 유지
- **레이턴시**: 체결 확인 후 TP/SL 설정까지 10-50ms 추가
- **고빈도 가능성**: 0.05~0.1% TP/SL로도 정확한 손익비 유지

---

## 적용 범위

### 적합한 경우
- 신생 DEX처럼 슬리피지가 큰 거래소
- 고빈도 전략 (작은 TP/SL 사용)
- 정확한 손익비가 중요한 전략
- WebSocket 인프라가 안정적인 경우

### 부적합한 경우
- 슬리피지가 매우 작은 거래소 (<0.01%)
- WebSocket 불안정한 거래소
- 단순한 저빈도 전략

---

## 다음 단계

1. **구현**: `pilot_directional_ws.py`에 동적 TP/SL 로직 추가
2. **테스트**: 메인넷에서 실제 슬리피지 측정 및 성능 검증
3. **최적화**: TP/SL 설정 레이턴시 최소화 (목표: <20ms)
4. **모니터링**: 슬리피지 통계 수집 및 전략 조정

---

## 결론

웹소켓의 실시간성을 활용한 동적 TP/SL 전략은:
- 슬리피지가 큰 신생 DEX에서도 고빈도 전략을 가능하게 함
- 정확한 손익 관리로 전략 안정성 향상
- 기술적 복잡도는 중간 수준이지만 성능 향상 효과는 큼

**핵심 원칙**: "Limit price가 아닌 Entry price 기준으로 생각하라"
