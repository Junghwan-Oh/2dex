# Phase 2E: 양방향 Passive Maker + TP 청산 전략 구현 계획

## Git 브랜치
- **브랜치명**: `feature/phase2e-passive-maker-tp`
- **베이스**: `feature/phase2d-momentum-strategy` (현재 브랜치)
- **커밋 순서**: 계획 → Phase A → Phase B → Phase C

## 사용자 설정
- **HEDGE 전략**: Passive Maker (마켓 → 리밋)
- **체결 타임아웃**: 60초

## 목표
1. 진입가 로직 변경 (Aggressive → Passive Maker) - PRIMARY & HEDGE 양방향
2. TP(Take Profit) 청산 로직 구현
3. 동적 손절 타임아웃 실험

---

## Phase A: 양방향 Passive Maker 진입가 로직

### 현재 로직
```
PRIMARY: Aggressive Maker (ask-1틱 / bid+1틱)
HEDGE:   Market Order (즉시 체결, 스프레드 비용)
```

### 변경 로직
```
PRIMARY: Passive Maker (bid-1틱 / ask+1틱)
HEDGE:   Passive Maker (bid-1틱 / ask+1틱)
타임아웃: 60초
```

### 수정 파일 및 라인

**1. GRVT Exchange**
- 파일: `f:/Dropbox/dexbot/perpdex/2dex/exchanges/grvt.py`
- `place_open_order()` (Lines 342-345):
  - BUY: `best_ask - tick` → `best_bid - tick`
  - SELL: `best_bid + tick` → `best_ask + tick`
- `place_close_order()` (Lines 398-400):
  - 동일하게 변경

**2. Backpack Exchange**
- 파일: `f:/Dropbox/dexbot/perpdex/2dex/exchanges/backpack.py`
- `place_open_order()` (Lines 339-343):
  - BUY: `best_ask - tick` → `best_bid - tick`
  - SELL: `best_bid + tick` → `best_ask + tick`
- `place_close_order()` (Lines 446-451):
  - 동일하게 변경

**3. hedge_mode_2dex.py - HEDGE를 Maker로 변경**
- 파일: `f:/Dropbox/dexbot/perpdex/2dex/hedge/hedge_mode_2dex.py`
- HEDGE 마켓 오더 → 리밋 오더 (Passive Maker)
- 순차 체결: PRIMARY 체결 후 → HEDGE 리밋 주문
- 타임아웃: 60초

### 테스트
- 10회 사이클 실행
- 체결율 확인 (양방향 Passive Maker는 체결 지연 가능)
- 진입가 비교 (이전 대비 개선 확인)

---

## Phase B: TP(Take Profit) 청산 로직 구현

### 목표
- 진입 시 TP 청산 주문을 함께 설정
- TP 가격 = 진입가 * (1 + 0.0005) = 진입가 + 0.05%

### 수정 파일

**1. hedge_mode_2dex.py**
- 파일: `f:/Dropbox/dexbot/perpdex/2dex/hedge/hedge_mode_2dex.py`

**Open Cycle 수정 (Lines 301-532)**:
- PRIMARY 진입 체결 후 (Line ~415):
  - TP 가격 계산: `tp_price = entry_price * 1.0005`
  - TP 청산 주문 즉시 배치 (POST_ONLY)

**Close Cycle 수정 (Lines 534-768)**:
- 기존 즉시 청산 로직 제거
- TP 주문 체결 대기 로직으로 변경

### TP 계산 로직
```
BUY 진입 → SELL 청산:
  tp_price = entry_price * 1.0005 (0.05% 높게)

SELL 진입 → BUY 청산:
  tp_price = entry_price * 0.9995 (0.05% 낮게)
```

---

## Phase C: 동적 손절 타임아웃 실험

### 목표
- TP 미체결 시 타임아웃 후 시장가 청산
- 5가지 타임아웃 값 테스트: 5초, 10초, 15초, 30초, 60초
- 각 50회씩 테스트

### 수정 사항
- config에 `tp_timeout` 파라미터 추가
- TP 대기 중 타임아웃 도달 시:
  - TP 주문 취소
  - 시장가 청산 실행

### 테스트 계획
| 실험 | 타임아웃 | 반복 | 예상 시간 |
|------|----------|------|-----------|
| C1 | 5초 | 50회 | ~30분 |
| C2 | 10초 | 50회 | ~45분 |
| C3 | 15초 | 50회 | ~60분 |
| C4 | 30초 | 50회 | ~90분 |
| C5 | 60초 | 50회 | ~120분 |

---

## 구현 순서

### Step 1: Phase A 구현
1. grvt.py 진입가 로직 수정
2. backpack.py 진입가 로직 수정
3. 10회 테스트 실행
4. 결과 분석 (체결율, 진입가 개선)

### Step 2: Phase B 구현
1. hedge_mode_2dex.py에 TP 로직 추가
2. Open Cycle에서 TP 주문 배치
3. Close Cycle을 TP 대기 로직으로 변경
4. 10회 테스트 실행

### Step 3: Phase C 실험
1. tp_timeout 파라미터 추가
2. 5초 타임아웃 50회 테스트
3. 10초 타임아웃 50회 테스트
4. ... (순차 진행)
5. 결과 비교 분석

---

## 핵심 수정 파일 목록

| 파일 | 수정 내용 |
|------|-----------|
| `exchanges/grvt.py` | 진입가 로직 (Passive Maker) |
| `exchanges/backpack.py` | 진입가 로직 (Passive Maker) |
| `hedge/hedge_mode_2dex.py` | TP 청산 로직, 타임아웃 손절 |

---

## 예상 리스크

1. **체결율 저하**: Passive Maker는 체결이 느릴 수 있음
   - 대응: cancel-and-replace 로직 유지

2. **TP 미체결**: 가격이 TP까지 도달 안 할 수 있음
   - 대응: 동적 손절 타임아웃으로 해결

3. **양방향 미체결**: PRIMARY/HEDGE 둘 다 체결 지연
   - 대응: Phase A 테스트에서 체결율 확인 후 진행 결정
