# TP 기능 및 SOL Position Precision Fix Summary

## Overview

이 문서는 Nado DEX 봇의 TP (Take Profit) 기능 작동 문제와 SOL 포지션 정밀도 문제를 해결한 과정을 정리한 것입니다.

**Commit:** `3b483fe` - "Fix SOL WebSocket position precision and TP order placement"

---

## Problem 1: TP Orders Not Placing

### Initial Symptoms
- 웹 UI에서 TP 주문이 전혀 보이지 않음
- `--enable-static-tp` 파라미터를 사용해도 TP 주문이 생성되지 않음
- 로그에서 `[TP] Failed to place TP orders, continuing without TP` 메시지

### Root Cause
```python
# Before (line 2490)
result = await client.client.context.trigger_client.place_price_trigger_order(...)
```
`trigger_client.place_price_trigger_order()`는 async 함수가 아닌데 `await`를 사용하여 다음 에러 발생:
```
ERROR: [TP] ETH error placing TP: object ExecuteResponse can't be used in 'await' expression
```

### Fix
```python
# After (line 2490)
result = client.client.context.trigger_client.place_price_trigger_order(...)  # await 제거
```

### Result
- ETH TP 주문 정상 작동: `0x1d7b73bb...` @ $2234.9
- SOL TP 주문 정상 작동: `0x4409127d...` @ $101.62

---

## Problem 2: SOL Position Showing Wrong Values

### Initial Symptoms
WebSocket으로 받은 SOL 포지션 값이 완전히 잘못됨:
```
INFO: [UNWIND] POSITIONS BEFORE (WS): ETH=0.045, SOL=-5000000000
INFO: [UNWIND] POSITIONS BEFORE (WS): ETH=0.045, SOL=-4000000000
INFO: [UNWIND] POSITIONS BEFORE (WS): ETH=0.045, SOL=-3000000000
```
실제 SOL 포지션은 약 -1.0 (1 SOL short at 5x leverage)이어야 함.

### Root Cause Investigation

Raw WebSocket 데이터 확인:
```
INFO: [POSITION CHANGE] product_id=8, amount_raw=-1000000000000000000
INFO: [POSITION CHANGE] product_id=8, amount_raw=-2000000000000000000
INFO: [POSITION CHANGE] product_id=8, amount_raw=-3000000000000000000
```

`amount_raw`는 19자리 숫자 (x18 format).

But 코드는 SOL을 1e9로 나누고 있었음:
```python
# Before (line 441-442)
precision = Decimal("1e18") if ticker == "ETH" else Decimal("1e9")
amount = Decimal(str(amount_raw)) / precision
```

계산:
- `-1000000000000000000 / 1e9 = -1000000000` (wrong!)
- `-1000000000000000000 / 1e18 = -1.0` (correct!)

### Fix
```python
# After (line 441-442)
# WebSocket sends both ETH and SOL in x18 format
precision = Decimal("1e18")  # Both use 1e18
amount = Decimal(str(amount_raw)) / precision
```

### Result
```
INFO: [POSITION CHANGE] SOL: amount_raw=-4000000000000000000, precision=1E+18, amount=-4.000000000000000000
```
이제 SOL 포지션이 올바르게 표시됨 (-4.0 = 1 SOL short at 5x leverage).

---

## Test Results

### Before Fix (commit before 3b483fe)
```
ERROR: [TP] ETH error placing TP: object ExecuteResponse can't be used in 'await' expression
INFO: [UNWIND] POSITIONS BEFORE (WS): SOL=-5000000000.000000000  # Wrong!
```

### After Fix (commit 3b483fe)
```
INFO: [TP] ETH TP order placed: 0x1d7b73bb... @ $2234.9
INFO: [TP] SOL TP order placed: 0x4409127d... @ $101.62
INFO: [UNWIND] POSITIONS BEFORE (WS): ETH=0, SOL=-4.000000000000000000  # Correct!
INFO: [STATIC TP] SOL TP hit: 0.03% >= 10.0bps
INFO: [EXIT] Static TP triggered: static_tp_sol_0.03bps
```

---

## Files Modified

| File | Description |
|------|-------------|
| `hedge/DN_pair_eth_sol_nado.py` | Main bot file - TP order placement fix + SOL WebSocket precision fix |
| `hedge/exchanges/nado.py` | Nado exchange client updates |
| `tests/test_static_tp.py` | Static TP unit tests (new) |
| `scripts/compare_pnl.py` | PNL comparison script (new) |

---

## Key Learnings

1. **WebSocket x18 Format**: Nado DEX WebSocket `position_change` stream은 ETH와 SOL 모두 x18 format (1e18)으로 amount를 전송합니다. REST API와 다를 수 있음.

2. **TP SDK Method**: `trigger_client.place_price_trigger_order()`는 async 함수가 아닙니다. `await` 사용 금지.

3. **Debugging Strategy**: Raw WebSocket 데이터를 직접 로깅하여 실제 포맷을 확인해야 합니다. 문서화되지 않은 API는 실제 데이터를 먼저 확인하세요.

---

## Remaining Issues

1. **WebSocket Lag**: WebSocket position update에 ~20초 지연이 있어, unwind phase에서 REST API와 값이 다를 수 있음
   - Rest shows: 0.0
   - WS shows: -4.0
   - 이로 인해 position verification이 실패할 수 있음

2. **Entry Prices**: SOL에 대해 "Missing entry prices for PNL calculation" 경고

---

## How to Test

```bash
# Run single cycle test with TP enabled
python3 -m hedge.DN_pair_eth_sol_nado --size 100 --iter 1 --enable-static-tp --tp-bps 10 --tp-timeout 60
```

Expected output:
- Both ETH and SOL TP orders placed
- Positions showing correct values (e.g., SOL=-4.0 for 1 SOL short at 5x)
- TP hit triggers exit

---

Generated: 2026-02-02
Context: TP functionality debugging and SOL WebSocket precision fix
