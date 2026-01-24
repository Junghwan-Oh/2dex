# Paradex → Backpack-GRVT 이식 계획

## 배경

**19일 사건**: Paradex에서 모든 open orders가 일방적으로 취소됨. Paradex 인도 서버 문제로 인한 것으로, 사용자 코드 문제가 아님. Paradex에서 완전히 탈출하여 안정적인 거래소 조합으로 이식.

---

## 1. 목표

**기존**: `DN_alternate_grvt_paradex.py` (Paradex-GRVT Alternate 전략)
**신규**: `DN_alternate_backpack_grvt.py` (Backpack-GRVT Alternate 전략)

**핵심**: Paradex만 Backpack으로 교체, GRVT은 Hedge 위치 유지

---

## 2. 거래소 변경

| 역할 | 소스 (기존) | 타겟 (신규) | 변경 |
|------|-------------|-------------|------|
| **Primary** | Paradex (Maker) | **Backpack (Maker)** | Paradex → Backpack |
| **Hedge** | GRVT (Taker) | **GRVT (Taker)** | 그대로 유지 ✅ |

**이유**: GRVT을 Hedge로 유지하면 위치 바꾸는 에러를 피할 수 있음

---

## 3. 핵심 변경사항

### 3.1 Import 변경

```python
# 소스 (DN_alternate_grvt_paradex.py)
from exchanges.paradex import ParadexClient
from exchanges.grvt import GrvtClient

# 타겟 (DN_alternate_backpack_grvt.py)
from exchanges.backpack import BackpackClient  # Paradex → Backpack
from exchanges.grvt import GrvtClient           # GRVT는 그대로
```

### 3.2 클라이언트 인스턴스화

```python
# 소스
self.primary_client = ParadexClient(config)
self.hedge_client = GrvtClient(config)

# 타겟
self.primary_client = BackpackClient(config)  # Paradex → Backpack
self.hedge_client = GrvtClient(config)         # GRVT는 그대로 ✅
```

### 3.3 설정 변경

```python
# 소스
self.primary_exchange = "paradex"
self.hedge_exchange = "grvt"

# 타겟
self.primary_exchange = "backpack"  # Paradex → Backpack
# self.hedge_exchange = "grvt"      # GRVT는 그대로 ✅
```

---

## 4. 유지할 좋은 기능

파일 복사 시 DN_alternate_grvt_paradex.py의 모든 최적화와 기능이 자동으로 유지됨:

| 기능 | 설명 |
|------|------|
| TradeMetrics dataclass | 거래 실행 세부사항 추적 |
| Repricing 횟수 추적 | TradeMetrics에 포함 |
| Repricing 한도 5회 | 3회 → 5회 개선 |
| Maker timeout 8s | 20s → 8s 개선 |
| Reconcile 강화 | 모든 불일치 감지 |
| Auto-recovery 0.01 | 2.0x → 0.01 개선 |
| 중복 루프 삭제 | Lines 861-927 제거 |

---

## 5. 예상 소요 시간

| 작업 | 예상 시간 |
|------|----------|
| 파일 복사 및 Import 변경 | 10분 |
| 클라이언트 설정 변경 (Primary만) | 20분 |
| Backpack Maker 메서드 확인 | 30분 |
| 테스트 및 수정 | 1-2시간 |
| **총계** | **2-3시간** |

---

## 6. 포지션 구조

```
Build Phase (Long-first):
├── Backpack (Maker):  Long position  →  +0.01
└── GRVT (Taker):      Short position  →  -0.01
   Net Delta: 0

Unwind Phase:
├── Backpack 청산:  Long 0.01 → 0
└── GRVT 청산:      Short 0.01 → 0
   Net Delta: 0

Next Build Phase (Short-first):
├── Backpack (Maker):  Short position  →  -0.01
└── GRVT (Taker):      Long position  →  +0.01
   Net Delta: 0
```

---

## 7. 참고 파일

- **소스**: `DN_alternate_grvt_paradex.py` (Alternate 전략, 복사 기반)
- **참조**: `DN_mean_reversion_grvt_backpack_v1.py` (Backpack-GRVT 백엔드 확인용)

---

**작성일**: 2026-01-23
**파일명**: `DN_alternate_backpack_grvt.py`
