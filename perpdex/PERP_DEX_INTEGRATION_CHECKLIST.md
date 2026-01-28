# Perpetual DEX 통합 최우선 체크리스트

**목적**: DEX API 통합 시 Lighter 같은 시행착오 방지
**기반**: Lighter DEX 10시간 삽질 경험
**작성일**: 2025-11-08

---

## 🚨 CRITICAL: 코드 작성 전 필수 확인 사항

**절대 규칙**: 이 체크리스트를 완료하기 전에는 코드를 한 줄도 작성하지 말 것

---

## Phase 0: API 접근 가능 여부 (30-60분)

### ✅ Checklist 0.1: Beta/Waitlist 프로그램 확인

**목적**: Lighter처럼 Private Beta 제한 조기 발견

```markdown
[ ] 공식 문서에서 "beta", "waitlist", "access" 키워드 검색
[ ] Discord/Telegram 커뮤니티 질문:
    "Is API access open to all users or restricted?"
[ ] Twitter에서 검색:
    "[DEX명] API beta"
    "[DEX명] API access"
[ ] GitHub Issues/Discussions에서 "API access" 검색
[ ] 공식 웹사이트 FAQ 확인
```

**결과 판정**:
```yaml
if "private beta" or "waitlist" or "application required":
  ⚠️ BLOCKER 발견
  Action:
    1. Beta 신청 즉시
    2. 대안 DEX 병렬 탐색
    3. 승인 대기 시간 예측
  Decision: 다른 DEX 우선 구현 or 승인 대기

else:
  ✅ 접근 가능
  Action: Phase 1으로 진행
```

---

### ✅ Checklist 0.2: 계정 타입/등급 요구사항

**목적**: Premium/Standard 같은 계정 등급과 API 관계 파악

```markdown
[ ] API 사용에 특정 계정 등급 필요한가?
    - Free tier: API 접근 가능?
    - Paid tier: API 접근 필요 조건?
[ ] 계정 등급별 API 제한사항
    - Rate limits
    - 사용 가능한 엔드포인트
    - 수수료 차이
[ ] 계정 업그레이드 시 API 자동 활성화?
    - 즉시? 대기 시간?
    - 추가 승인 필요?
```

**Lighter 경험**:
```
❌ 잘못된 가정: "Premium = API 접근"
✅ 실제: Premium ≠ API 접근 (별개)
```

**결과 판정**:
```yaml
if 명확한_요구사항_있음:
  ✅ 조건 충족 or 업그레이드 계획
  Action: Phase 1으로 진행

if 불명확:
  ⚠️ 커뮤니티에 재확인
  Action: 답변 받을 때까지 대기 or 대안 탐색
```

---

### ✅ Checklist 0.3: 공개 API 기능 범위

**목적**: 인증 없이 사용 가능한 기능 파악 (Fallback 전략)

```markdown
[ ] 공개 REST API 테스트 (인증 없이)
    [ ] 마켓 리스트 조회
    [ ] 현재 가격 조회
    [ ] 오더북 조회
    [ ] 최근 거래 내역
[ ] 공개 WebSocket 채널
    [ ] 가격 스트림
    [ ] 오더북 스트림
    [ ] 거래 스트림
[ ] 테스트 코드 작성 (5분)
```

**테스트 코드 예시**:
```python
# test_public_api.py
import requests

def testPublicAccess():
    """인증 없이 공개 API 테스트"""
    base = "https://api.[dex].com"

    # 마켓 리스트
    resp = requests.get(f"{base}/markets")
    print(f"Markets: {resp.status_code}")

    # 가격 조회
    resp = requests.get(f"{base}/markets/BTC-USD/ticker")
    print(f"Price: {resp.status_code}")

    # 오더북
    resp = requests.get(f"{base}/markets/BTC-USD/orderbook")
    print(f"Orderbook: {resp.status_code}")

testPublicAccess()
```

**결과 판정**:
```yaml
if 공개_API_충분:
  ✅ Paper trading 가능
  ✅ 가격 모니터링 가능
  Action: 공개 API로 부분 구현 후 인증 추가

if 공개_API_부족:
  ⚠️ 인증 필수
  Action: 인증 구현 우선
```

---

### ✅ Checklist 0.4: 커뮤니티 사례 조사

**목적**: 다른 개발자의 성공/실패 사례 학습

```markdown
[ ] GitHub에서 "[DEX명] python" 검색
    - 성공한 봇 사례
    - 이슈에서 에러 패턴
[ ] Discord/Telegram에서 질문:
    "Has anyone successfully integrated the API for algo trading?"
[ ] Twitter 검색:
    "[DEX명] API integration"
    "[DEX명] trading bot"
[ ] Reddit/Medium 검색
```

**발견해야 할 정보**:
```yaml
성공_사례:
  - 어떤 SDK 사용?
  - 어떤 인증 방식?
  - 얼마나 걸렸나?

실패_사례:
  - 어떤 에러 발생?
  - 블로커는?
  - 해결했나?

경고_신호:
  - "waiting for API access"
  - "beta program full"
  - "API deprecated"
```

---

## Phase 1: 인증 메커니즘 (1-2시간)

### ✅ Checklist 1.1: 인증 방식 파악

```markdown
[ ] 인증 방식 확인
    [ ] API Key (Header)
    [ ] Ed25519 Signature (Lighter 방식)
    [ ] OAuth 2.0
    [ ] JWT Token
    [ ] Ethereum Wallet Signature
[ ] 키 생성 위치
    [ ] 웹 UI
    [ ] CLI 명령어
    [ ] 프로그래밍 방식
[ ] 키 타입
    [ ] Public + Private key pair
    [ ] Single API key
    [ ] API key + Secret
```

**Lighter 경험**:
```
✅ Ed25519 키 페어
✅ 80 hex characters (40 bytes)
✅ account_index + api_key_index 조합
❌ 하지만 Beta 제한으로 사용 불가
```

---

### ✅ Checklist 1.2: 키 등록 프로세스

```markdown
[ ] 키 생성 후 즉시 사용 가능?
    [ ] 동기화 시간 필요?
    [ ] 온체인 트랜잭션 필요?
[ ] 키 백엔드 등록 확인 방법
    [ ] 조회 API 있는가?
    [ ] 테스트 엔드포인트 있는가?
[ ] 키 활성화 조건
    [ ] 자동 활성화?
    [ ] 수동 승인 필요?
```

**테스트 코드**:
```python
def testKeyRegistration():
    """API 키가 백엔드에 등록되었는지 확인"""

    # 1. 키 생성
    apiKey = generate_api_key()

    # 2. 즉시 테스트 (실패 예상)
    result1 = test_authenticated_call(apiKey)
    print(f"Immediate: {result1}")

    # 3. 1분 대기 후 재시도
    time.sleep(60)
    result2 = test_authenticated_call(apiKey)
    print(f"After 1min: {result2}")

    # 4. 결과 판정
    if result2 == "success":
        print("✅ 자동 등록 (1분 동기화)")
    else:
        print("❌ 수동 승인 필요 or Beta 제한")
```

---

### ✅ Checklist 1.3: 에러 코드 사전 조사

```markdown
[ ] 공식 문서에서 에러 코드 리스트 찾기
[ ] 각 에러 코드의 의미와 해결 방법
[ ] 커뮤니티에서 자주 보고된 에러
```

**에러 매트릭스 작성**:
```markdown
| Error Code | Meaning | Likely Cause | Resolution |
|------------|---------|--------------|------------|
| 401 | Unauthorized | API key invalid | Check key format |
| 403 | Forbidden | No permission | Check account type |
| 21511 | (Lighter) | Beta restriction | Apply for beta |
```

**Lighter 경험**:
```
21511: "invalid tx type for account"
→ 5시간 동안 키 조합 시도
→ 실제 원인: Private Beta 제한
→ 문서에 없었던 정보
```

---

## Phase 2: SDK/라이브러리 검증 (30분)

### ✅ Checklist 2.1: 공식 SDK 존재 여부

```markdown
[ ] Python SDK 공식 지원?
    [ ] PyPI에 있는가?
    [ ] GitHub repo 공식인가?
    [ ] 마지막 업데이트 언제?
[ ] SDK 성숙도
    [ ] Star 수
    [ ] 이슈/PR 활동
    [ ] 최근 커밋
[ ] SDK vs REST API 직접 호출
    [ ] SDK 사용 권장?
    [ ] REST API 더 간단?
```

**Lighter 경험**:
```
❌ PyPI 버전: SignerClient 없음
✅ GitHub 버전: SignerClient 있음
→ pip install git+https://github.com/...
→ 버전 불일치 주의
```

---

### ✅ Checklist 2.2: 예제 코드 작동 확인

```markdown
[ ] 공식 문서 예제 코드 복사
[ ] 그대로 실행 (수정 없이)
[ ] 작동하는가?
    [ ] YES: SDK 신뢰 가능
    [ ] NO: 문서 오래됨 or 제한 있음
[ ] 최소 예제 작성 (10분)
```

**최소 예제**:
```python
# minimal_test.py
"""가장 간단한 인증 테스트"""

# 1. SDK import
from [dex] import Client

# 2. 클라이언트 생성
client = Client(api_key="test_key")

# 3. 가장 간단한 API 호출
try:
    result = client.get_account()
    print(f"✅ SUCCESS: {result}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    # 에러 분석
    if "401" in str(e):
        print("→ 인증 실패")
    elif "403" in str(e):
        print("→ 권한 없음")
    elif "beta" in str(e).lower():
        print("→ Beta 제한!")
```

---

## Phase 3: 아키텍처 설계 (1시간)

### ✅ Checklist 3.1: Layered Architecture

```markdown
[ ] Layer 1: Data Access (공개 API)
    [ ] 가격 조회 ✅
    [ ] 오더북 조회 ✅
    [ ] 마켓 데이터 ✅
    → 즉시 구현 가능

[ ] Layer 2: Trading Execution (인증 필요)
    [ ] 주문 생성
    [ ] 주문 취소
    [ ] 포지션 관리
    → 인증 성공 후 구현

[ ] Layer 3: Account Management
    [ ] 잔고 조회
    [ ] 거래 내역
    [ ] 수수료 조회
```

**설계 원칙**:
```yaml
원칙_1: 독립적 레이어
  - Layer 1 실패해도 Layer 2 영향 없음
  - 공개 API로 먼저 검증

원칙_2: Fallback 전략
  - Layer 2 실패 시 Paper trading
  - Layer 3 실패 시 로컬 계산

원칙_3: 점진적 구현
  - Layer 1 완성 (1시간)
  - Layer 1 테스트 (30분)
  - Layer 2 시도 (블로커 발견 가능)
```

---

### ✅ Checklist 3.2: 멀티 DEX 대응 설계

```markdown
[ ] 추상화 레이어 설계
    [ ] Interface 정의
    [ ] DEX별 Adapter 패턴
[ ] 공통 로직 vs DEX 특화 로직 분리
[ ] 90% 코드 재사용 가능하게 설계
```

**인터페이스 예시**:
```python
# dex_interface.py
from abc import ABC, abstractmethod

class PerpDEXInterface(ABC):
    """모든 Perp DEX가 구현해야 할 인터페이스"""

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """현재 가격 조회 (공개 API)"""
        pass

    @abstractmethod
    def create_order(self, order: Order) -> str:
        """주문 생성 (인증 필요)"""
        pass

    @abstractmethod
    def get_balance(self) -> dict:
        """잔고 조회 (인증 필요)"""
        pass

# lighter_adapter.py
class LighterAdapter(PerpDEXInterface):
    """Lighter DEX 구현"""

    def get_price(self, symbol: str) -> float:
        # Lighter 특화 구현
        pass

# hyperliquid_adapter.py
class HyperliquidAdapter(PerpDEXInterface):
    """Hyperliquid DEX 구현"""

    def get_price(self, symbol: str) -> float:
        # Hyperliquid 특화 구현
        pass
```

---

## Phase 4: 리스크 완화 전략 (30분)

### ✅ Checklist 4.1: 블로커 시나리오 대비

```markdown
[ ] 시나리오 1: Beta 제한 발견
    [ ] Plan A: Beta 신청 (1-7일 대기)
    [ ] Plan B: 대안 DEX 병렬 구현
    [ ] Plan C: 공개 API로 Paper trading

[ ] 시나리오 2: 인증 실패
    [ ] 에러 코드 분석
    [ ] 커뮤니티 질문
    [ ] 다른 인증 방식 시도
    [ ] 대안 DEX 고려

[ ] 시나리오 3: API 불안정
    [ ] Rate limit 대응
    [ ] Retry 로직
    [ ] Circuit breaker
    [ ] Fallback data source
```

---

### ✅ Checklist 4.2: 멀티 트랙 전략

```markdown
[ ] Track 1: Primary DEX
    [ ] 첫 선택 DEX 구현
    [ ] 블로커 발견 시 즉시 중단

[ ] Track 2: Backup DEX
    [ ] 대안 DEX 리서치 완료
    [ ] Interface 동일하게 설계
    [ ] Primary 실패 시 즉시 전환

[ ] Track 3: Paper Trading
    [ ] 공개 API로 가격 수집
    [ ] 시뮬레이션 로직
    [ ] 전략 검증용
```

**의사결정 매트릭스**:
```yaml
if Primary_성공:
  → Full implementation

if Primary_블로커_발견:
  → Backup으로 전환 (2-3시간)
  → Primary는 백그라운드 (Beta 신청)

if Primary_실패 and Backup_실패:
  → Paper trading으로 전략 검증
  → 새로운 DEX 조사
```

---

## Phase 5: 실행 (조건부)

### ✅ Checklist 5.1: 실행 전 최종 확인

```markdown
[ ] Phase 0 완료?
    [ ] Beta 제한 없음 확인
    [ ] 계정 타입 요구사항 충족
    [ ] 공개 API 테스트 완료
    [ ] 커뮤니티 사례 조사 완료

[ ] Phase 1 완료?
    [ ] 인증 방식 이해
    [ ] 키 등록 프로세스 확인
    [ ] 에러 코드 매트릭스 작성

[ ] Phase 2 완료?
    [ ] SDK 검증 완료
    [ ] 예제 코드 작동 확인

[ ] Phase 3 완료?
    [ ] Layered architecture 설계
    [ ] 멀티 DEX 인터페이스 설계

[ ] Phase 4 완료?
    [ ] 블로커 시나리오 대비
    [ ] 멀티 트랙 전략 수립
```

**최종 Go/No-Go 판정**:
```yaml
if 모든_체크리스트_통과:
  ✅ GO: 구현 시작
  예상 시간: 3-5시간
  성공 확률: 80%+

if 일부_실패:
  ⚠️ CAUTION: 대안 준비 후 시작
  예상 시간: 5-8시간
  성공 확률: 50-60%

if Beta_제한_발견:
  🚨 NO-GO: 대안 DEX 우선
  현재 DEX: Beta 신청 백그라운드
```

---

## 체크리스트 사용 예시

### Case Study 1: Hyperliquid 통합

**Phase 0 체크리스트** (30분):
```markdown
✅ Beta 프로그램: 없음 (공개 API)
✅ 계정 타입: 모든 계정 API 사용 가능
✅ 공개 API: 가격, 오더북, 거래 내역 모두 가능
✅ 커뮤니티: 많은 성공 사례

판정: ✅ GO - 즉시 구현 시작
```

**예상 결과**:
- Phase 0: 30분 (리서치)
- Phase 1: 1시간 (인증 구현)
- Phase 2: 30분 (SDK 테스트)
- Phase 3: 1시간 (아키텍처)
- Phase 5: 2시간 (구현)
- **Total: 5시간 → 작동하는 시스템** ✅

---

### Case Study 2: Lighter 통합 (실제 경험)

**Phase 0 체크리스트** (했다면):
```markdown
❌ Beta 프로그램: Private Beta (UI 메시지)
⚠️ 계정 타입: Premium ≠ API 접근
✅ 공개 API: 가격, 오더북 가능
⚠️ 커뮤니티: Beta 신청 사례 발견

판정: 🚨 BLOCKER - 대안 준비
```

**실제 vs 체크리스트 적용 시**:
```yaml
실제_경험:
  - Phase 0 체크리스트: 생략
  - 바로 구현 시작
  - 5시간 후 Beta 발견
  - 10시간 → 실패

체크리스트_적용_시:
  - Phase 0: 30분 → Beta 발견
  - Phase 0: 30분 → Hyperliquid 리서치
  - Phase 1-5: 4시간 → Hyperliquid 구현
  - Total: 5시간 → 작동하는 시스템 ✅
```

---

## 시간 절약 효과 분석

### Without Checklist (Lighter 경험)
```
Hour 0-3: 의미 있는 학습 (SDK, 인증)
Hour 3-5: 유의미한 실험 (키 조합)
Hour 5-8: 무의미한 반복 (같은 에러)
Hour 8-10: 문서화

Total: 10시간
Result: 실패 (Private Beta 제한)
Success Rate: 0%
```

### With Checklist
```
Hour 0-0.5: Phase 0 체크리스트
  → Beta 제한 발견
  → Hyperliquid 대안 선택

Hour 0.5-1.5: Phase 1-2 (Hyperliquid)
  → 인증 구현
  → SDK 검증

Hour 1.5-2.5: Phase 3 (아키텍처)
  → Layered design
  → 멀티 DEX 인터페이스

Hour 2.5-5: Phase 5 (구현)
  → 작동하는 시스템

Total: 5시간
Result: 작동하는 시스템 ✅
Success Rate: 100%
```

**시간 절약**: 5시간 (50%)
**성공 확률**: 0% → 100%

---

## 체크리스트 업데이트 전략

### 새로운 DEX 경험 시 추가

```markdown
## DEX 경험 로그

### [DEX명] 통합 (날짜)

**Phase 0 결과**:
- Beta 제한: [Yes/No]
- 특이사항: [...]

**Phase 1 결과**:
- 인증 방식: [...]
- 에러 코드: [...]

**예상 시간 vs 실제**:
- 예상: X시간
- 실제: Y시간
- 차이 원인: [...]

**체크리스트 개선사항**:
- [ ] 추가할 항목: [...]
- [ ] 수정할 항목: [...]
```

---

## Quick Reference Card

```
┌──────────────────────────────────────────────┐
│  PERP DEX 통합 체크리스트 Quick Reference     │
├──────────────────────────────────────────────┤
│                                               │
│  🚨 코드 작성 전 필수 확인:                   │
│                                               │
│  ☐ Beta/Waitlist 프로그램 확인 (30분)         │
│  ☐ 계정 타입 요구사항 (15분)                  │
│  ☐ 공개 API 테스트 (15분)                     │
│  ☐ 커뮤니티 사례 조사 (30분)                  │
│                                               │
│  ⚠️ BLOCKER 발견 시:                          │
│                                               │
│  1. Beta 신청 (백그라운드)                    │
│  2. 대안 DEX 즉시 탐색                        │
│  3. 공개 API로 Paper trading                  │
│                                               │
│  ✅ 체크리스트 완료 후 구현 시작              │
│                                               │
│  예상 시간: 5-6시간                           │
│  성공 확률: 80%+                              │
│                                               │
└──────────────────────────────────────────────┘
```

---

## 최종 권장사항

### 모든 Perp DEX 통합 시

**1. Phase 0는 생략 금지** (30-60분 투자):
```
"바로 구현하고 싶어!" → ❌ 금지
"Phase 0 체크리스트부터!" → ✅ 필수
```

**2. 블로커 발견 = 즉시 대안**:
```
"이 DEX만 고집" → ❌ 시간 낭비
"대안 준비, 멀티 트랙" → ✅ 리스크 관리
```

**3. 문서 우선**:
```
"일단 코딩" → ❌ Lighter 반복
"PRD/Tech Spec 먼저" → ✅ BMAD 방식
```

**4. 커뮤니티 활용**:
```
"혼자 해결" → ❌ 10시간 삽질
"Discord에 먼저 질문" → ✅ 30분 해결
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-08
**Based On**: Lighter DEX 10-hour failure experience
**Success Rate**: 0% → 80%+ (with checklist)
**Time Saving**: 5 hours (50%)
