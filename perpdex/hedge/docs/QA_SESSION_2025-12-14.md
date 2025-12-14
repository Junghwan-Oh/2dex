# Q&A Session - Delta Neutral Volume Farming Bot

> 날짜: 2025-12-14
> 주제: SPEC-001 완료 후 전략 상세 Q&A

---

## 질문 및 답변

### 1. EARS 형식이란?

**답변**: EARS (Easy Approach to Requirements Syntax)는 MoAI-ADK 프레임워크에서 SPEC 문서 작성 시 사용하는 요구사항 정의 표준입니다.

**구성요소**:
- **Ubiquitous (U)**: 시스템 전체에 적용되는 요구사항
- **Event-driven (E)**: 특정 이벤트 발생 시 동작
- **State-driven (S)**: 특정 상태에서의 동작
- **Unwanted (W)**: 금지사항 (해서는 안 되는 것)
- **Optional (O)**: 선택적 기능

---

### 2. REQ-U01에서 REQ의 의미

**답변**: REQ = Requirement (요구사항)

**명명 규칙**:
- `REQ-U01`: Ubiquitous 요구사항 1번
- `REQ-E01`: Event-driven 요구사항 1번
- `REQ-S01`: State-driven 요구사항 1번
- `REQ-W01`: Unwanted 요구사항 1번
- `REQ-O01`: Optional 요구사항 1번

---

### 3. 타입 검증을 하는 이유

**답변**: 런타임 에러 방지 및 잘못된 설정의 조기 발견

**예시**:
```yaml
# 잘못된 설정 (문자열)
position_diff_threshold: "0.2"  # ❌ 타입 에러

# 올바른 설정 (숫자)
position_diff_threshold: 0.2    # ✅ 정상
```

타입 검증 시 잘못된 타입은 무시하고 기본값 사용 + 경고 로그 출력.

---

### 4. API 키 저장 위치

**답변**: `.env` 파일에 저장

**내용**:
- `BACKPACK_PUBLIC_KEY`
- `BACKPACK_SECRET_KEY`
- `API_KEY_PRIVATE_KEY`
- `LIGHTER_ACCOUNT_INDEX`
- `LIGHTER_API_KEY_INDEX`

---

### 4-1. .env는 커밋되는가?

**답변**: ❌ 커밋되지 않음

`.gitignore` 파일에 포함되어 있음:
```
.env
.env.*
!.env.example
```

---

### 4-2. 만약 .env가 커밋된 경우 조치

**커밋된 경우**:
1. 즉시 API 키 재발급 (노출된 키는 무효화)
2. `git filter-branch` 또는 `BFG Repo-Cleaner`로 히스토리에서 제거
3. `.gitignore`에 추가 확인

**커밋되지 않은 경우**:
- 현재 상태 유지 (정상)
- `.env.example` 템플릿만 커밋 권장

---

### 5. hedge 폴더 내 py 파일 역할

| 파일 | 역할 |
|------|------|
| `hedge_mode.py` | 진입점, CLI 인자 파싱 |
| `hedge_mode_bp.py` | Backpack + Lighter 헷지 봇 (주력) |
| `hedge_mode_ext.py` | Extended + Lighter 헷지 봇 |
| `config_loader.py` | YAML 설정 파일 로더 |
| `exchanges/base.py` | 거래소 클라이언트 추상 베이스 |
| `exchanges/factory.py` | 거래소 인스턴스 팩토리 |
| `exchanges/backpack.py` | Backpack API 클라이언트 |
| `exchanges/bp_client.py` | Backpack HTTP/WebSocket |
| `exchanges/lighter.py` | Lighter API 클라이언트 |
| `exchanges/lighter_custom_websocket.py` | Lighter WebSocket |
| `exchanges/aster.py` | Aster DEX 클라이언트 |
| `exchanges/edgex.py` | EdgeX DEX 클라이언트 |
| `exchanges/extended.py` | Extended DEX 클라이언트 |
| `exchanges/grvt.py` | GRVT DEX 클라이언트 |
| `exchanges/paradex.py` | Paradex DEX 클라이언트 |

---

### 6. position_diff_threshold 설명

**정의**: 두 거래소 간 포지션 불균형 허용 한계

**계산**: `|Backpack_position + Lighter_position|`

**예시**:
- Backpack LONG +0.1 ETH, Lighter SHORT -0.1 ETH → 차이 = 0 (완벽 헷지)
- Backpack LONG +0.15 ETH, Lighter SHORT -0.1 ETH → 차이 = 0.05

**기본값**: 0.2

**초과 시**: 경고 로그 출력, 수동 리밸런싱 권장

---

### 7. 시드머니 불균형 문제 (한쪽에 손실 누적)

**현재 상태**: 수동 조정 필요

DN 전략 특성상 한쪽 거래소에 손실이 누적될 수 있음:
- Backpack: 수익 누적 → 마진 여유
- Lighter: 손실 누적 → 마진 부족 가능

**권장 조치**:
1. 주기적으로 양쪽 잔고 확인
2. 불균형 심화 시 수동으로 자금 이동
3. 향후 자동 리밸런싱 기능 구현 가능 (잠재 기능)

---

### 8. WebSocket vs REST 거래

**현재 구현**:
- **WebSocket**: 시세 데이터 실시간 수신, 주문 상태 모니터링
- **REST API**: 주문 생성/취소/조회

`lighter_custom_websocket.py`가 WebSocket 연결 관리

---

### 9. 구현 필요 기능 전체 리스트

**완료**:
- [x] config.yaml 설정 파일 지원 (SPEC-001)

**필수 (High Priority)**:
- [ ] 주문 금액 설정 파일화 (default_size)
- [ ] 펀딩비 모니터링 로깅

**권장 (Medium Priority)**:
- [ ] 잔고 모니터링

**잠재 기능 (보류)**:
- [ ] holding_time 파라미터 (거래량 감소 우려로 보류)
- [ ] 자동 리밸런싱
- [ ] 다른 DEX 페어 확장

---

### 10. 주문 금액 설정

**요구사항**:
- 테스트용: 최소액 ($5, size: 0.01)
- 예시 금액: $100 (size: 0.05)
- config.yaml에서 쉽게 조정 가능하게

**구현 계획**:
- config.yaml에 `default_size` 파라미터 추가
- CLI `--size`가 있으면 CLI 우선

---

### 11. DEX 페어 확장 순서

**1단계**: Backpack + Lighter 안정화 (현재)
**2단계**: 메인넷 테스트 및 모니터링
**3단계**: 다른 DEX 페어 확장 (향후)
- Paradex + Lighter
- GRVT + Lighter

---

### 12. holding_time 재검토 보류

**사용자 결정**: holding_time 구현 보류

**이유**:
- 10분 홀딩은 거래 횟수/거래량에 급격한 감소 초래
- 현재 로직(10초 미체결 취소 후 재주문)으로 충분
- 포인트 파밍 목적상 거래량 최대화가 중요

**조치**: 잠재 구현 선택사항 리스트에만 추가

---

## 파라미터 수정 방법

`perpdex/hedge/config.yaml` 파일 수정:

```yaml
trading:
  position_diff_threshold: 0.2    # 포지션 불균형 허용치
  order_cancel_timeout: 10        # 미체결 주문 취소 (초)
  trading_loop_timeout: 180       # 루프 전체 타임아웃 (초)
  max_retries: 15                 # API 재시도 횟수
  fill_check_interval: 10         # 체결 확인 간격 (초)

pricing:
  buy_price_multiplier: 0.998     # 매수가 = 시장가 × 0.998
  sell_price_multiplier: 1.002    # 매도가 = 진입가 × 1.002
```

**우선순위**: CLI 인자 > config.yaml > 하드코딩 기본값
