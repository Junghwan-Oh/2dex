# 2DEX Hedge Mode 종합 계획서 v3.0

**문서 목적**: Position Imbalance 버그 수정 Post-Mortem + 매매 분석 + 안정화 계획
**최종 업데이트**: 2026-01-03
**Bot 목적**: Perp DEX Point Farming DN (Delta-Neutral) Bot

---

## 1. Bot 목적 및 수익 구조

### 1.1 핵심 목적
**거래량(Volume)을 최대한 무손실로 최대한 많이 만들어서 2개 DEX의 Point를 farming**

### 1.2 수익 구조
```
실제 수익 = GRVT maker rebate + DEX Points (volume 비례) - Spread Cost
```

| 수익 항목 | 설명 | 비고 |
|----------|------|------|
| GRVT Maker Rebate | POST_ONLY 주문 체결 시 리베이트 | 확정 수익 |
| DEX Points | 거래량 비례 포인트 적립 | 잠재 수익 (에어드롭 등) |
| Spread Cost | GRVT fill price vs Backpack fill price 차이 | 비용 |

### 1.3 무손실 조건
```
Maker Rebate >= Spread Cost
```
→ 이 조건 충족 시, Volume 생성이 순수익으로 전환

---

## 2. Post-Mortem: Position Imbalance 버그 (2026-01-03)

### 2.1 발생한 문제
- **증상**: GRVT에서 0.08 ETH filled, Backpack hedge 실패 → 0.08 ETH 노출
- **에러**: `Invalid market symbol (occurred while parsing "OrderExecutePayload")`

### 2.2 근본 원인: 심볼 환각

| 구분 | 잘못된 값 (환각) | 올바른 값 (API 조회) |
|------|-----------------|---------------------|
| Backpack contract_id | `ETH-PERP` | `ETH_USDC_PERP` |
| 원인 | 하드코딩된 `TICKER_CONTRACT_MAP` | `get_contract_attributes()` 동적 조회 |

### 2.3 수정 내용

**삭제된 코드**:
- `TICKER_CONTRACT_MAP` (하드코딩 심볼 매핑)
- `TICK_SIZE_MAP` (하드코딩 tick size)
- `get_contract_id()` 함수
- `get_tick_size()` 함수

**적용된 패턴**:
```python
# 동적 contract_id 조회
self.primaryContractId, self.primaryTickSize = await self.primaryClient.get_contract_attributes()
self.hedgeContractId, self.hedgeTickSize = await self.hedgeClient.get_contract_attributes()
```

### 2.4 수정 결과

| 테스트 | Position Imbalance | 상태 |
|-------|-------------------|------|
| Fix 이전 (0.08 ETH) | **0.08 ETH** | 위험 노출 |
| Fix 이후 (모든 size) | **0** | 해결됨 |

**Git Commit**: `d4c2942`

### 2.5 교훈

1. **기존 패턴 확인 필수**: 9개 거래소 모두 `get_contract_attributes()` 구현됨
2. **하드코딩 금지**: 동적 API 조회 패턴 사용
3. **최소 구현**: 새로운 매핑 만들지 말고 기존 메서드 호출

---

## 3. 매매 분석 (2026-01-03 테스트 데이터)

### 3.1 데이터 소스
- **CSV**: `logs/2dex_grvt_backpack_ETH_trades.csv` (146 rows)
- **Log**: `logs/2dex_grvt_backpack_ETH_log.txt`

### 3.2 Volume 성과 (핵심 지표)

| 지표 | 값 | 설명 |
|-----|---|------|
| 총 거래량 | **1.06 ETH** | 10 paired trades |
| 최대 단일 거래 | 0.32 ETH | size=0.32 테스트 성공 |
| 평균 거래 크기 | 0.106 ETH | - |
| 성공 거래 수 | 10회 | GRVT+Backpack 양쪽 체결 |

### 3.3 Fill Rate 분석

| 지표 | 값 | 문제점 |
|-----|---|--------|
| 시도 횟수 | ~60 cycles | 여러 테스트 세션 합계 |
| 성공 횟수 | 10회 | - |
| 성공률 | **~16.7%** | 5초 timeout 내 미체결 |

**주요 실패 원인**:
1. GRVT maker order가 5초 timeout 내 체결되지 않음
2. GRVT rate limit (429 오류)
3. 시장 변동성 낮은 시간대

### 3.4 Spread 분석

**방향별 Spread**:

| 방향 | GRVT Side | Backpack Side | 평균 Spread | 해석 |
|------|-----------|---------------|-------------|------|
| BUY | Buy (maker) | Sell (taker) | **-$4.22** | Cost 발생 |
| SELL | Sell (maker) | Buy (taker) | **+$2.17** | Favorable |

**Per-Trade Spread 상세**:

| Trade # | GRVT Side | GRVT Price | BP Price | Spread | Size |
|---------|-----------|------------|----------|--------|------|
| 1 | BUY | $3,072.80 | $3,068.53 | -$4.27 | 0.01 |
| 2 | BUY | $3,409.86 | $3,405.63 | -$4.23 | 0.01 |
| 3 | BUY | $3,411.17 | $3,406.87 | -$4.30 | 0.01 |
| 4 | BUY | $3,412.93 | $3,408.78 | -$4.15 | 0.01 |
| 5 | BUY | $3,413.35 | $3,409.19 | -$4.16 | 0.01 |
| 6 | SELL | $3,095.71 | $3,093.56 | +$2.15 | 0.16 |
| 7 | SELL | $3,087.82 | $3,085.59 | +$2.23 | 0.32 |
| 8 | SELL | $3,086.58 | $3,084.42 | +$2.16 | 0.16 |
| 9 | SELL | $3,085.82 | $3,083.59 | +$2.23 | 0.16 |
| 10 | SELL | $3,086.17 | $3,083.95 | +$2.22 | 0.16 |

### 3.5 Latency 분석

| 지표 | 값 |
|-----|---|
| 평균 Latency | ~65ms |
| 최소 Latency | ~61ms |
| 최대 Latency | ~70ms |

**Latency 정의**: GRVT fill timestamp → Backpack fill timestamp

### 3.6 Position Imbalance 이력

| 시점 | Imbalance | 원인 |
|------|-----------|------|
| Bug 발생 시 | 0.08 ETH | Backpack hedge 실패 (심볼 환각) |
| Fix 이후 | **0** | 동적 조회로 해결 |

### 3.7 분석 요약

**Point Farming 관점 평가**:

| 항목 | 현재 상태 | 목표 | Gap |
|------|----------|------|-----|
| Position Imbalance | 0 | 0 | 해결됨 |
| Fill Rate | 16.7% | 50%+ | 개선 필요 |
| Volume/Session | 1.06 ETH | 최대화 | Fill Rate 의존 |
| Spread Cost | -$4.22 ~ +$2.17 | 최소화 | 방향별 차이 |

---

## 4. 안정화 계획 (Next Steps)

### 4.1 우선순위

| 순위 | Task | 목적 | 상태 |
|------|------|------|------|
| 1 | Position Imbalance = 0 유지 | 안정성 | 완료 |
| 2 | Fill Rate 개선 | Volume 최대화 | 진행 예정 |
| 3 | Spread Cost 관리 | 무손실 운영 | 모니터링 |
| 4 | Rebate Rate 확인 | 수익성 검증 | 후순위 |

### 4.2 Fill Rate 개선 방안

**Option A: fillTimeout 증가**
```bash
# 현재
--fill-timeout 5

# 변경안
--fill-timeout 10  # 또는 15
```

**Option B: BBO 추적 전략 개선**
- 현재: 단순 BBO at order time
- 개선안: BBO 변화 추적 후 적응형 주문

**Option C: Rate Limit 대응**
- GRVT 429 오류 발생 시 exponential backoff
- 요청 간격 조절

### 4.3 테스트 계획

| Phase | Size | Iterations | 목적 |
|-------|------|------------|------|
| 1 | 0.01 ETH | 20 | fillTimeout 변경 효과 검증 |
| 2 | 0.16 ETH | 20 | 중형 size 안정성 |
| 3 | 0.32 ETH | 20 | 대형 size 안정성 |
| 4 | 0.5 ETH | 10 | 최대 size 테스트 |

### 4.4 모니터링 지표

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| Fill Rate | 성공 cycles / 총 cycles | 50%+ |
| Position Imbalance | 매 세션 종료 시 확인 | 0 |
| Avg Spread | CSV 분석 | 최소화 |
| Total Volume | CSV 합계 | 최대화 |

---

## 5. 코드 참조

### 5.1 핵심 파일

| 파일 | 역할 |
|------|------|
| `hedge/hedge_mode_2dex.py` | 2DEX Hedge Bot 메인 로직 |
| `hedge_mode.py` | Entry point (--primary, --hedge 지원) |
| `exchanges/factory.py` | Exchange client factory |
| `exchanges/backpack.py:578` | `get_contract_attributes()` |
| `exchanges/grvt.py:529` | `get_contract_attributes()` |

### 5.2 실행 명령어

```bash
# 기본 테스트
python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.01 --iter 10

# fillTimeout 증가 테스트
python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.16 --iter 20 --fill-timeout 10

# 대형 size 테스트
python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.32 --iter 10
```

---

## 6. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-01-02 | 초기 계획 수립 |
| v2.0 | 2026-01-03 | Post-Mortem 추가 (Position Imbalance 버그) |
| v3.0 | 2026-01-03 | 매매 분석 통합 + 안정화 계획 |

---

## 7. 결론

### 7.1 완료된 작업
- Position Imbalance 버그 수정 (심볼 환각 → 동적 조회)
- 매매 데이터 분석 (1.06 ETH volume, 10 successful trades)

### 7.2 진행 중인 작업
- Fill Rate 개선 (16.7% → 50%+ 목표)
- 안정적 장기 운영 테스트

### 7.3 후순위 작업
- GRVT maker rebate rate 확인
- Spread 최적화 전략

**핵심 원칙**: "일단 DN bot이 안정적으로 돌아가는게 급선무다"
