# EPIC: GRVT Production-Ready Hedge Bot

**Status**: Planning
**Created**: 2025-12-24
**Last Updated**: 2025-12-24

---

## Post-Mortem: 어제-오늘 삽질 교훈

### 🔴 치명적 실수들

1. **임포트 검증 생략**: 기본 기능 확인 없이 복잡한 헤지 플로우부터 시작
2. **Story 순서 오류**: API 연결 문제를 STORY-004에서 발견 (초기에 발견했어야 함)
3. **Over-Engineering**: GitHub 원본 단순 패턴 무시, Lighter 레거시 코드 오염
4. **DEX 특성 무시**: Initial margin, position size, leverage, WebSocket expire 미확인
5. **TDD 원칙 위반**: 테스트 작성 전 구현부터 시작

### ✅ 핵심 교훈

- **Simple is Best**: GitHub 원본처럼 .env 설정만으로 작동
- **Test First**: 임포트 → API → 복잡한 플로우 순서
- **DEX ≠ CEX**: Margin, leverage, position 관계 정확히 이해
- **레거시 차단**: Lighter 코드 완전 분리
- **무수정 유지**: 스토리 1-5는 원본 최대한 보존

---

## Epic 목표

**GRVT (DEX) + Backpack (CEX) 헤지봇을 GitHub 원본 기반으로 점진적으로 확장**

### 큰 그림 (Big Picture)

```
Phase 1: Foundation (STORY 1-2)
  ↓ 깃헙 원본 검증 완료

Phase 2: Core Hedge (STORY 3-5)
  ↓ 무수정 헤지봇 작동 + Progressive Sizing

Phase 3: Production Features (STORY 6-9)
  ↓ 기능 점진적 추가 (컨펌, 텔레그램, CSV, rebate)
```

### 성공 기준

1. ✅ **Simple Setup**: .env 설정만으로 즉시 실행
2. ✅ **원본 보존**: STORY 1-5는 깃헙 코드 최대한 유지
3. ✅ **TDD 준수**: RED → GREEN → REFACTOR 철저히 따름
4. ✅ **DEX 특성 이해**: Initial margin, position, leverage 완벽 검증
5. ✅ **점진적 확장**: 기본 작동 후 기능 하나씩 추가
6. ✅ **프로덕션 안정성**: 24시간 연속 실행 가능

---

## Story Breakdown

### Phase 1: Foundation (4.5시간)

#### STORY-001: GRVT DEX 기본 기능 완전 검증 ⭐

**우선순위**: P0 (절대적 기반)
**예상 시간**: 4시간
**의존성**: 없음

##### 목표

GRVT DEX의 모든 기본 기능을 단계별로 검증하여 안정적인 토대 확보

**⚠️ 중요**: Default ticker를 BTC → ETH로 변경 (절대 BTC 사용 금지)

##### Test Strategy (TDD)

- **Coverage Target**: 100% (모든 기본 기능)
  - **산출 근거**: 기반 기능이므로 모든 코드 경로 검증 필수
- **Test Types**:
  - Unit Tests: 개별 API 호출 (임포트, 초기화, 가격 조회 등)
  - Integration Tests: 실제 GRVT API 연동 (WebSocket, 주문 체결)
- **Test Framework**: pytest
- **Test Location**: `tests/test_001_grvt_foundation.py`
- **Test Fixtures**:
  - `@pytest.fixture` config 객체 (ticker='ETH', quantity=0.01)
  - `@pytest.fixture` grvt_client (재사용 가능한 클라이언트 인스턴스)

##### RED Phase: 실패하는 테스트 먼저 작성 (1시간)

1. [ ] `test_001_01_import_grvt_client()`: GrvtClient 임포트 테스트
   - **예상 실패 타입**: `ImportError: No module named 'pysdk'`
   - **성공 조건**: `from exchanges.grvt import GrvtClient` 5초 이내 완료
   - **왜 중요**: 어제-오늘 임포트 hang 문제 재발 방지

2. [ ] `test_001_02_initialize_grvt_client()`: GrvtClient 초기화 테스트
   - **예상 실패 타입**: `AttributeError: 'NoneType' object has no attribute 'grvt_env'`
   - **성공 조건**: `client = GrvtClient(config)` 정상 초기화

3. [ ] `test_001_03_get_contract_attributes()`: 계약 속성 조회 테스트 (Integration)
   - **예상 실패 타입**: `ConnectionError: GRVT API unreachable`
   - **성공 조건**: `contract_id`, `tick_size` 반환

4. [ ] `test_001_04_fetch_market_price()`: ETH 시장가 조회 테스트 (Integration)
   - **예상 실패 타입**: `ValueError: No price data for ETH/USDT`
   - **성공 조건**: ETH 현재가 반환 (예: 3500 USDT)

5. [ ] `test_001_05_calculate_initial_margin()`: Initial margin 계산 테스트
   - **예상 실패 타입**: `NotImplementedError: calculate_initial_margin() not implemented`
   - **성공 조건**: `initial_margin = position_value / leverage`
   - **검증 예시**: 0.01 ETH @ 3500 USDT, 10x leverage → $3.5 margin
   - **왜 중요**: DEX 특성 - margin 관리 필수

6. [ ] `test_001_06_verify_position_leverage_relationship()`: Position size와 leverage 관계 테스트
   - **예상 실패 타입**: `AssertionError: position_value != margin × leverage`
   - **성공 조건**: `position_value = margin × leverage` 검증
   - **왜 중요**: DEX 특성 - 잘못된 leverage는 청산 위험

7. [ ] `test_001_07_open_long_position()`: LONG 포지션 오픈 테스트 (Integration)
   - **예상 실패 타입**: `RuntimeError: Failed to place LONG order`
   - **성공 조건**: Order ID 반환, 포지션 확인

8. [ ] `test_001_08_open_short_position()`: SHORT 포지션 오픈 테스트 (Integration)
   - **예상 실패 타입**: `RuntimeError: Failed to place SHORT order`
   - **성공 조건**: Order ID 반환, 포지션 확인

9. [ ] `test_001_09_close_position()`: 포지션 닫기 테스트 (Integration)
   - **예상 실패 타입**: `RuntimeError: Failed to close position`
   - **성공 조건**: 포지션 0으로 확인

10. [ ] `test_001_10_cancel_order()`: 주문 취소 테스트 (Integration)
    - **예상 실패 타입**: `RuntimeError: Cancel order failed`
    - **성공 조건**: Order status = CANCELED

11. [ ] `test_001_11_websocket_connection()`: WebSocket 연결 테스트 (Integration)
    - **예상 실패 타입**: `TimeoutError: WebSocket connection timeout`
    - **성공 조건**: 3초 내 연결 완료

12. [ ] `test_001_12_websocket_expire_time()`: WebSocket expire 시간 테스트
    - **예상 실패 타입**: `AttributeError: 'ws_client' has no attribute 'expire_time'`
    - **성공 조건**: Expire 시간 확인, 재연결 필요 시점 알림
    - **왜 중요**: WebSocket 끊김 방지

13. [ ] 모든 테스트 실행 → **RED 확인** (12개 모두 실패해야 정상)

##### GREEN Phase: 최소 코드로 테스트 통과 (2시간)

14. [ ] pysdk 의존성 확인 (perp-dex-toolkit-ref 검증)
15. [ ] GrvtClient 임포트 수정 (필요 시만)
16. [ ] **Default ticker 변경**: BTC → ETH (hedge_mode_grvt.py:1305)
17. [ ] Initial margin 계산 헬퍼 함수 추가 (`helpers/dex_margin.py`)
18. [ ] Position-leverage 관계 검증 헬퍼 추가
19. [ ] WebSocket expire 시간 체크 로직 추가
20. [ ] 각 테스트 **하나씩** 통과시키기 (순차적으로)
21. [ ] 모든 테스트 GREEN 확인

##### REFACTOR Phase: 코드 품질 개선 (1시간)

22. [ ] 중복 코드 제거 (DRY 원칙)
23. [ ] 함수명 명확화 (camelCase)
24. [ ] 에러 핸들링 개선 (명확한 메시지)
25. [ ] 로깅 추가 (디버깅용, 최소한만)
26. [ ] 테스트 여전히 GREEN 확인

##### Quality Gate

**Build & Compilation**:
- [ ] 임포트 5초 이내 완료 (hang 없음)
- [ ] 문법 오류 없음

**TDD Compliance**:
- [ ] RED → GREEN → REFACTOR 순서 준수
- [ ] 12개 테스트 모두 PASS
- [ ] Coverage: 100% (기본 기능)

**Functionality**:
- [ ] ETH/USDT 계약 정보 조회 성공
- [ ] 시장가 조회 성공
- [ ] Initial margin 정확히 계산
- [ ] Position-leverage 관계 검증
- [ ] LONG/SHORT 포지션 오픈/닫기 성공
- [ ] 주문 취소 성공
- [ ] WebSocket 연결 성공
- [ ] WebSocket expire 시간 확인

**Performance**:
- [ ] 각 API 호출 5초 이내
- [ ] WebSocket 연결 3초 이내

**원본 보존**:
- [ ] 깃헙 원본 코드 구조 유지
- [ ] 수정은 helpers/ 폴더에만 추가

##### Deliverables

- [ ] `tests/test_001_grvt_foundation.py` (12개 테스트 PASS)
- [ ] `helpers/dex_margin.py` (margin 계산 헬퍼, 새 파일)
- [ ] Initial margin 계산 문서 (주석으로)
- [ ] WebSocket expire 시간 문서

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **테스트 실패**: `git checkout HEAD -- helpers/`, helpers/ 폴더 변경사항 롤백
2. **임포트 실패**: perp-dex-toolkit-ref 디렉토리 삭제 후 재클론
3. **API 연동 실패**: .env 파일 백업본으로 복원, API 키 재확인
4. **WebSocket 실패**: GRVT 원본 WebSocket 예제 코드로 복원
5. **긴급 상황**: `git reset --hard <commit>` (Phase 0 직후 커밋으로)

---

#### STORY-002: Backpack CEX 기본 검증 (간단 체크만)

**우선순위**: P0
**예상 시간**: 30분
**의존성**: 없음 (STORY-001과 병렬 진행 가능)

##### 목표

Backpack API 정상 작동 확인 (이전 봇에서 검증됨, 최소 테스트만)

##### Test Strategy

- **Coverage Target**: 기본 기능만 (이미 검증된 코드)
  - **산출 근거**: 이전 봇에서 작동 확인, 최소 검증만 필요
- **Test Types**: Integration Tests (실제 Backpack API)
- **Test Location**: `tests/test_002_backpack_basic.py`

##### RED Phase (10분)

1. [ ] `test_002_01_import_and_init()`: 임포트 및 초기화 테스트
   - **예상 실패 타입**: `ImportError: No module named 'exchanges.backpack'`
2. [ ] `test_002_02_place_single_order()`: Post-only 주문 1회 테스트 (Integration)
   - **예상 실패 타입**: `RuntimeError: Order placement failed`
3. [ ] RED 확인

##### GREEN Phase (15분)

4. [ ] 테스트 통과 확인 (원본 코드로 이미 작동할 것)

##### REFACTOR Phase (5분)

5. [ ] 필요 시 코드 정리

##### Quality Gate

- [ ] TDD 준수
- [ ] 2개 테스트 PASS
- [ ] 원본 코드 수정 없음

##### Deliverables

- [ ] `tests/test_002_backpack_basic.py` (2개 테스트 PASS)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **임포트 실패**: Backpack 클라이언트 원본 확인
2. **API 연동 실패**: .env 파일의 Backpack API 키 재확인
3. **긴급 상황**: 이전 작동하던 hedge_mode_bp.py로 복원

---

### Phase 2: Core Hedge (8시간)

#### STORY-003: 단순 헤지 사이클 (원본 기반)

**우선순위**: P1
**예상 시간**: 3시간
**의존성**: STORY-001 ✅, STORY-002 ✅

##### 목표

깃헙 원본 코드 기반 단순 헤지 사이클 1회 실행

**⚠️ 중요 수정사항**:
1. **maxRetries=3 유지** (원본 보존 원칙, 재시도 로직 중요)
2. **헤지 순서 변경**: GRVT 먼저 → Backpack 나중 (백팩 앱 알림이 헤징 완료 신호)

##### Test Strategy

- **Coverage Target**: 90% (핵심 헤지 로직)
  - **산출 근거**: 핵심 플로우 + 에러 핸들링, 엣지 케이스는 제외
- **Test Types**:
  - Unit Tests: 넷 익스포저 계산 로직
  - Integration Tests: 실제 GRVT + Backpack 헤지 사이클
- **Test Location**: `tests/test_003_simple_hedge.py`
- **Test Fixtures**:
  - `@pytest.fixture` test_config (ticker='ETH', quantity=0.01, iterations=1)

##### RED Phase (1시간)

1. [ ] `test_003_single_hedge_cycle()`: 완전한 헤지 사이클 테스트 (Integration)
   - **순서**: GRVT SHORT 0.01 ETH → Backpack BUY 0.01 ETH
   - 넷 익스포저 ≈ 0 검증
   - **예상 실패 타입**: `NotImplementedError: hedge_mode_clean.py not created`

##### GREEN Phase (1.5시간)

2. [ ] `hedge_mode_clean.py` 생성 (깃헙 원본 hedge_mode_grvt.py 기반)
   - HedgeBotClean 클래스 (hedge_mode_grvt.py 복사)
   - **maxRetries=3 유지** (lines 570-593 그대로 유지)
   - **헤지 순서 변경** (lines 1179-1204):
     * 기존: Backpack 먼저 (BUY) → GRVT 나중 (SHORT)
     * 변경: GRVT 먼저 (SHORT) → Backpack 나중 (BUY)
   - 넷 익스포저 계산
3. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

4. [ ] 중복 코드 제거
5. [ ] 로깅 추가 (최소한만)
6. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] 1회 헤지 사이클 성공
- [ ] 넷 익스포저 < 0.001 ETH
- [ ] 원본 코드 구조 유지
- [ ] Coverage: 90%

##### Deliverables

- [ ] `hedge_mode_clean.py` (깃헙 원본 기반, maxRetries=3 유지, 헤지 순서 변경)
- [ ] `tests/test_003_simple_hedge.py` (PASS)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **헤지 순서 실패**: lines 1179-1204 원본(Backpack 먼저)으로 복원
2. **넷 익스포저 불일치**: 포지션 수동 정리 후 재시작
3. **maxRetries 버그**: hedge_mode_grvt.py lines 570-593 원본 재복사
4. **긴급 상황**: `git checkout HEAD -- hedge_mode_clean.py`

---

#### STORY-004: 재시도 로직 테스트 및 검증

**우선순위**: P1
**예상 시간**: 2시간
**의존성**: STORY-003 ✅

##### 목표

기존 maxRetries=3 로직 철저히 테스트 (무한 루프 방지 확인)

**⚠️ 중요**: maxRetries 로직은 STORY-003에서 이미 hedge_mode_grvt.py에서 복사됨

##### Test Strategy

- **Coverage Target**: 95% (재시도 로직 + 무한 루프 방지)
  - **산출 근거**: 재시도 경로 전체 + 엣지 케이스 (3회 실패, 로깅)
- **Test Types**:
  - Unit Tests: 재시도 카운터, 로깅 검증
  - Integration Tests: 실제 2-DEX 헤징 여부 검증 (GRVT + Backpack)
- **Test Location**: `tests/test_004_retry_logic.py`
- **Mocking Strategy**:
  - Backpack API 타임아웃 시뮬레이션 (unittest.mock 사용)
  - 로깅 출력 캡처 (pytest caplog)

**Integration Test 의미 명확화**:
- **핵심**: 실제 2개 DEX 헤징 여부 검증 (mock 아님)
- **1차 방법 (임시)**: Backpack 앱 알림 모니터링
  - Backpack 2번째 포지션 오픈 알림 → 헷징 ON
  - Backpack 포지션 close 알림 → 헷징 OFF
- **2차 방법 (정식)**: 사이즈업 이후 Story에서 헷징 ON/OFF 테스트 + 텔레그램 알림 기능 구현
- **Mock 용도**: 타임아웃 시뮬레이션 전용 (Integration 테스트 의미와 별개)

##### RED Phase (30분)

1. [ ] `test_004_01_backpack_retry_limit()`: Backpack 재시도 제한 테스트 (Integration with mock)
   - 3회 재시도 후 Exception 발생 확인
   - **예상 실패 타입**: `AssertionError: Expected 3 retries, got unlimited`
2. [ ] `test_004_02_retry_logging()`: 재시도 로그 검증 (Unit)
   - `[RETRY]` 로그 출력 확인
   - **예상 실패 타입**: `AssertionError: '[RETRY]' not found in caplog`
3. [ ] `test_004_03_no_infinite_loop()`: 무한 루프 절대 발생 안 함 확인 (Integration with mock)
   - **예상 실패 타입**: `TimeoutError: Test exceeded 30 seconds (infinite loop detected)`
4. [ ] RED 확인

##### GREEN Phase (1시간)

5. [ ] 기존 maxRetries=3 로직 검증 (hedge_mode_clean.py lines 570-593)
   - 재시도 카운터 정상 작동 확인
   - `[RETRY]` 로그 출력 확인
   - Exception 정상 발생 확인
6. [ ] 필요 시 최소 수정 (버그 발견 시만)
7. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

8. [ ] 코드 정리 (over-engineering 체크)
9. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] 3회 재시도 후 Exception 정상 발생
- [ ] 무한 루프 절대 발생 안 함 (철저히 테스트)
- [ ] 기존 로직 검증 완료 (수정 최소화)
- [ ] Coverage: 95%

##### Deliverables

- [ ] `tests/test_004_retry_logic.py` (PASS, 무한 루프 방지 검증)
- [ ] 테스트 결과 문서 (재시도 로직 정상 작동 확인)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **재시도 로직 버그**: hedge_mode_grvt.py lines 570-593 원본으로 재복사
2. **무한 루프 발생**: 프로세스 강제 종료, maxRetries 파라미터 확인
3. **테스트 실패**: mock 설정 검증, 실제 API와 비교
4. **긴급 상황**: STORY-003 완료 시점 커밋으로 복원

---

#### STORY-005: Progressive Sizing 통합

**우선순위**: P1
**예상 시간**: 3시간
**의존성**: STORY-004 ✅

##### 목표

점진적 포지션 크기 증가 시스템 (깃헙 원본에 이미 있는 기능 활용)

##### Test Strategy

- **Coverage Target**: 90% (sizing 알고리즘 + 경계 조건)
  - **산출 근거**: 증가/감소 로직 + 최대값 제한, 비정상 상황 제외
- **Test Types**:
  - Unit Tests: Size 계산 로직, 증가/감소 알고리즘
  - Integration Tests: 실제 헤지 사이클에서 size 적용
- **Test Location**: `tests/test_005_progressive_sizing.py`
- **Test Fixtures**:
  - `@pytest.fixture` sizing_config (initial=0.01, max=0.1, factor=1.5)

##### RED Phase (1시간)

1. [ ] `test_005_01_initial_size()`: 초기 사이즈 0.01 ETH (Unit)
   - **예상 실패 타입**: `AssertionError: Expected 0.01, got None`
2. [ ] `test_005_02_size_increase()`: 성공 후 증가 (Unit)
   - **예상 실패 타입**: `NotImplementedError: increase_size() not implemented`
3. [ ] `test_005_03_size_decrease()`: 실패 후 감소 (Unit)
   - **예상 실패 타입**: `NotImplementedError: decrease_size() not implemented`
4. [ ] `test_005_04_max_size_cap()`: 최대 크기 제한 (Unit)
   - **예상 실패 타입**: `AssertionError: Size exceeded max limit`
5. [ ] RED 확인

##### GREEN Phase (1.5시간)

6. [ ] `helpers/progressive_sizing.py` 확인 (원본에 이미 있으면 활용)
7. [ ] `hedge_mode_clean.py`에 통합
8. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

9. [ ] 코드 정리
10. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] 초기 0.01 ETH → 성공 후 증가
- [ ] 최대 크기 제한 작동
- [ ] 원본 로직 활용
- [ ] Coverage: 90%

##### Deliverables

- [ ] `helpers/progressive_sizing.py` (원본 활용 또는 최소 수정)
- [ ] `hedge_mode_clean.py` (sizing 통합)
- [ ] `tests/test_005_progressive_sizing.py` (PASS)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **Sizing 로직 버그**: helpers/progressive_sizing.py 삭제, 고정 size 사용
2. **최대값 초과**: config.yaml에서 max_size 조정
3. **증가/감소 오류**: sizing 로직 비활성화, 0.01 ETH 고정
4. **긴급 상황**: STORY-004 완료 시점 커밋으로 복원

---

### Phase 3: Production Features (8시간)

#### STORY-006: 헷징 ON/OFF 컨펌 로직

**우선순위**: P2
**예상 시간**: 2시간
**의존성**: STORY-005 ✅

##### 목표

봇 시작 전 사용자 컨펌 받기 (실수로 실행 방지)

##### Test Strategy

- **Coverage Target**: 100% (컨펌 로직)
- **Test Location**: `tests/test_006_confirm_logic.py`

##### RED Phase (30분)

1. [ ] `test_006_01_require_confirmation()`: 컨펌 없으면 시작 안 됨
2. [ ] `test_006_02_yes_starts_bot()`: 'yes' 입력 시 시작
3. [ ] `test_006_03_no_exits()`: 'no' 입력 시 종료
4. [ ] RED 확인

##### GREEN Phase (1시간)

5. [ ] `hedge_mode_production.py` 생성 (hedge_mode_clean.py 기반)
6. [ ] 시작 시 컨펌 프롬프트 추가
   ```python
   confirm = input("Start hedging? (yes/no): ")
   if confirm.lower() != 'yes':
       logger.info("Hedging cancelled by user")
       sys.exit(0)
   ```
7. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

8. [ ] 코드 정리
9. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] 컨펌 없으면 절대 시작 안 됨
- [ ] 사용자 입력 검증
- [ ] Coverage: 100%

##### Deliverables

- [ ] `hedge_mode_production.py` (컨펌 로직 추가)
- [ ] `tests/test_006_confirm_logic.py` (PASS)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **컨펌 로직 버그**: hedge_mode_clean.py로 복원 (컨펌 없이 실행)
2. **입력 검증 오류**: 컨펌 로직 비활성화, 자동 시작 모드
3. **긴급 상황**: STORY-005 완료 시점 커밋으로 복원

---

#### STORY-007: 텔레그램 알람 추가

**우선순위**: P2
**예상 시간**: 2시간
**의존성**: STORY-006 ✅

##### 목표

주요 이벤트를 텔레그램으로 알림 (시작, 주문, 에러)

##### Test Strategy

- **Coverage Target**: 90%
- **Test Location**: `tests/test_007_telegram.py`

##### RED Phase (30분)

1. [ ] `test_007_01_send_start_message()`: 시작 알림
2. [ ] `test_007_02_send_order_message()`: 주문 알림
3. [ ] `test_007_03_send_error_message()`: 에러 알림
4. [ ] RED 확인

##### GREEN Phase (1시간)

5. [ ] `helpers/telegram_bot.py` 확인 (원본에 이미 있으면 활용)
6. [ ] `hedge_mode_production.py`에 통합
   - 시작 시 알림
   - 주문 체결 시 알림
   - 에러 발생 시 알림
7. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

8. [ ] 중복 제거
9. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] 텔레그램 봇 토큰 .env 설정
- [ ] 주요 이벤트 알림 확인
- [ ] Coverage: 90%

##### Deliverables

- [ ] `helpers/telegram_bot.py` (원본 활용 또는 최소 수정)
- [ ] `hedge_mode_production.py` (텔레그램 통합)
- [ ] `tests/test_007_telegram.py` (PASS)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **텔레그램 API 오류**: helpers/telegram_bot.py 비활성화, 로깅만 사용
2. **봇 토큰 오류**: .env 파일의 TELEGRAM_BOT_TOKEN 재확인
3. **메시지 전송 실패**: 텔레그램 기능 비활성화, 기본 로깅으로 복원
4. **긴급 상황**: STORY-006 완료 시점 커밋으로 복원

---

#### STORY-008: 매매내역 CSV 로깅

**우선순위**: P2
**예상 시간**: 2시간
**의존성**: STORY-007 ✅

##### 목표

모든 주문/포지션을 CSV 파일로 기록 (분석용)

##### Test Strategy

- **Coverage Target**: 100%
- **Test Location**: `tests/test_008_csv_logging.py`

##### RED Phase (30분)

1. [ ] `test_008_01_create_csv_file()`: CSV 파일 생성
2. [ ] `test_008_02_log_backpack_order()`: Backpack 주문 기록
3. [ ] `test_008_03_log_grvt_position()`: GRVT 포지션 기록
4. [ ] `test_008_04_csv_format_valid()`: CSV 포맷 검증
5. [ ] RED 확인

##### GREEN Phase (1시간)

6. [ ] CSV 로거 추가 (`helpers/csv_logger.py`)
   - 헤더: timestamp, exchange, side, quantity, price, order_id, status
7. [ ] `hedge_mode_production.py`에 통합
8. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

9. [ ] 코드 정리
10. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] CSV 파일 정상 생성
- [ ] 모든 주문 기록됨
- [ ] 포맷 검증 (pandas로 읽기 가능)
- [ ] Coverage: 100%

##### Deliverables

- [ ] `helpers/csv_logger.py` (새 파일)
- [ ] `hedge_mode_production.py` (CSV 로깅 통합)
- [ ] `tests/test_008_csv_logging.py` (PASS)
- [ ] 샘플 CSV 파일

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **CSV 생성 실패**: `git checkout HEAD -- helpers/csv_logger.py`, 파일 재생성
2. **파일 쓰기 오류**: `trades/` 디렉토리 권한 확인 (chmod 755), 디스크 공간 확인
3. **포맷 오류**: 샘플 CSV 파일 삭제 후 재생성, pandas 검증 재실행
4. **통합 오류**: `git checkout HEAD -- hedge_mode_production.py`, CSV 로깅 제거
5. **긴급 상황**: `git reset --hard <commit>` (STORY-007 완료 직후 커밋으로)

---

#### STORY-009: GRVT Rebate 확인 및 텔레그램 알람

**우선순위**: P3
**예상 시간**: 2시간
**의존성**: STORY-008 ✅

##### 목표

GRVT rebate 정보 조회하여 텔레그램으로 알림

##### Test Strategy

- **Coverage Target**: 90%
- **Test Location**: `tests/test_009_rebate.py`

##### RED Phase (30분)

1. [ ] `test_009_01_get_rebate_info()`: Rebate 정보 조회
2. [ ] `test_009_02_calculate_total_rebate()`: 누적 rebate 계산
3. [ ] `test_009_03_send_rebate_alert()`: 텔레그램 알림
4. [ ] RED 확인

##### GREEN Phase (1시간)

5. [ ] GRVT API rebate 엔드포인트 확인
6. [ ] `exchanges/grvt.py`에 rebate 조회 메서드 추가
7. [ ] `hedge_mode_production.py`에 통합
   - 매 사이클 후 rebate 조회
   - 무조건 텔레그램 알림 (금액 무관, 얼마나 되는지 궁금하므로)
8. [ ] 테스트 통과 확인

##### REFACTOR Phase (30분)

9. [ ] 코드 정리
10. [ ] 테스트 GREEN 확인

##### Quality Gate

- [ ] TDD 준수
- [ ] Rebate 정보 정확히 조회
- [ ] 텔레그램 알림 전송
- [ ] Coverage: 90%

##### Deliverables

- [ ] `exchanges/grvt.py` (rebate 메서드 추가)
- [ ] `hedge_mode_production.py` (rebate 알림 통합)
- [ ] `tests/test_009_rebate.py` (PASS)

##### Rollback Strategy

**실패 시나리오별 복구 절차**:
1. **Rebate 조회 실패**: GRVT API 문서 재확인, 엔드포인트 URL 검증
2. **계산 오류**: `git checkout HEAD -- exchanges/grvt.py`, rebate 로직 재구현
3. **텔레그램 전송 실패**: .env 파일 TELEGRAM_TOKEN 확인, 봇 권한 재설정
4. **통합 오류**: `git checkout HEAD -- hedge_mode_production.py`, rebate 기능 제거
5. **긴급 상황**: `git reset --hard <commit>` (STORY-008 완료 직후 커밋으로)

---

## 실행 타임라인

### Day 1: Foundation (4.5시간)
- [ ] **Phase 0**: Clean Slate (30분) - Python 프로세스 종료, 백업, 재클론
- [ ] STORY-001: GRVT DEX 기본 검증 (4시간)
- [ ] STORY-002: Backpack 기본 검증 (30분)

### Day 2: Core Hedge (8시간)
- [ ] STORY-003: 단순 헤지 사이클 (3시간)
- [ ] STORY-004: 재시도 로직 (2시간)
- [ ] STORY-005: Progressive Sizing (3시간)

### Day 3: Production Features (8시간)
- [ ] STORY-006: 헷징 컨펌 (2시간)
- [ ] STORY-007: 텔레그램 알람 (2시간)
- [ ] STORY-008: 매매내역 CSV (2시간)
- [ ] STORY-009: GRVT Rebate 알람 (2시간)

**총 예상 시간**: 20.5시간

---

## 로깅 시스템 (2가지)

### 1. 일반 로그 파일 (디버깅용)

**목적**: 봇 실행 과정 추적
**파일**: `logs/hedge_bot_YYYYMMDD.log`
**포맷**: `timestamp - level - message`
**로테이션**: 일별

**예시**:
```
2025-12-24 10:00:00 - INFO - [START] Hedge bot starting
2025-12-24 10:00:05 - INFO - [OPEN] [Backpack] [BUY] Placing order
2025-12-24 10:00:10 - INFO - [FILL] [Backpack] Order filled
2025-12-24 10:00:15 - ERROR - [ERROR] GRVT connection timeout
```

### 2. 매매내역 CSV (분석용)

**목적**: 주문/포지션 이력 분석
**파일**: `logs/trades_YYYYMMDD.csv`
**포맷**: CSV (pandas 호환)

**컬럼**:
```
timestamp, exchange, side, quantity, price, order_id, status, net_exposure
```

**예시**:
```csv
2025-12-24 10:00:10,Backpack,BUY,0.01,3500,abc123,FILLED,0.01
2025-12-24 10:00:20,GRVT,SHORT,0.01,3500,xyz789,FILLED,0.0
```

---

## Over-Engineering 방지 체크리스트

### ❌ 절대 하지 말 것

- [ ] STORY 1-5에서 깃헙 원본 구조 변경
- [ ] 불필요한 추상화 레이어 추가
- [ ] 복잡한 디자인 패턴 적용
- [ ] 사용하지 않는 기능 미리 구현
- [ ] 테스트 없이 코드 작성
- [ ] Lighter 레거시 코드 참조

### ✅ 반드시 할 것

- [ ] GitHub 원본 코드 구조 그대로 따르기
- [ ] .env 설정만으로 실행 가능
- [ ] TDD 철저히 준수 (RED → GREEN → REFACTOR)
- [ ] 필요한 기능만 최소로 구현
- [ ] 각 Story 완료 후 Quality Gate 통과
- [ ] 단순함 유지 (KISS 원칙)
- [ ] STORY 1-5는 수정 최소화 (helpers/만 추가)

---

## Risk Mitigation

### Risk 1: pysdk 여전히 누락
- **확률**: Medium
- **영향**: High
- **완화책**: STORY-001 첫 테스트에서 즉시 발견

### Risk 2: 깃헙 원본 코드 불완전
- **확률**: Low
- **영향**: Medium
- **완화책**: Phase 0에서 재클론, STORY-001에서 검증

### Risk 3: Initial margin 계산 복잡
- **확률**: Medium
- **영향**: Medium
- **완화책**: helpers/dex_margin.py에 격리

### Risk 4: 텔레그램/CSV 기능 복잡도
- **확률**: Low
- **영향**: Low
- **완화책**: 원본 helpers/ 최대한 활용

---

## Clean Code 원칙 (SKILL.md 기반)

### 함수 설계
1. **단일 책임**: 각 함수는 한 가지만
2. **명확한 이름**: 함수/변수명으로 의도 전달 (camelCase)
3. **짧은 함수**: 20줄 이내
4. **중복 제거**: DRY 원칙

### 테스트 패턴
1. **AAA Pattern**: Arrange - Act - Assert
2. **Mocking**: 외부 의존성 격리
3. **Coverage**: 각 Story별 target 달성

### 코드 품질
1. **주석 최소화**: 코드 자체가 설명
2. **에러 명확히**: 무엇이 잘못됐는지 명확한 메시지
3. **로깅 적절히**: 디버깅 가능하되 과하지 않게

---

## Post-Sizing Stories (사이즈업 이후 구현)

### STORY-010: Security 강화 (PID Lock)

**우선순위**: P2 (Post-sizing)
**예상 시간**: 2시간
**의존성**: STORY-009 ✅

##### 목표

OS 레벨 PID 잠금으로 중복 봇 실행 방지 (fcntl.flock 사용)

##### 구현 내용

1. **PID Lock 파일 생성**: `hedge_bot.lock` (fcntl.flock 사용)
2. **중복 실행 감지**: 이미 실행 중인 봇 발견 시 즉시 종료
3. **정상 종료 시 Lock 해제**: 프로세스 종료 시 자동 정리
4. **비정상 종료 대응**: OS가 자동으로 Lock 해제 (fcntl.flock 장점)

##### 롤백 전략

PID Lock 실패 시 기존 동작 유지 (로그 경고만)

---

### STORY-011: WebSocket 안정성 (Auto-Reconnection)

**우선순위**: P2 (Post-sizing)
**예상 시간**: 3시간
**의존성**: STORY-001 ✅

##### 목표

WebSocket Expire 시간 감지 및 자동 재연결

##### 구현 내용

1. **Expire Time 모니터링**: 현재 STORY-001에 있는 expire 체크 활용
2. **Auto-Reconnect 로직**:
   - Expire 5분 전 자동 재연결 시도
   - 재연결 실패 시 3회 재시도 (지수 백오프)
3. **재연결 알림**: 텔레그램으로 재연결 상태 알림
4. **Connection Pool**: 연결 풀 관리로 안정성 향상

##### 롤백 전략

재연결 실패 시 기존 수동 재시작 방식 유지

---

### STORY-012: Circuit Breaker Pattern

**우선순위**: P2 (Post-sizing)
**예상 시간**: 2.5시간
**의존성**: STORY-003 ✅

##### 목표

API 장애 시 연쇄 실패 방지 (3회 실패 = 30초 대기)

##### 구현 내용

1. **실패 카운터**: API 호출 실패 횟수 추적
2. **Circuit Open**: 3회 연속 실패 시 Circuit OPEN 상태
3. **대기 시간**: 30초 대기 후 Half-Open 상태로 전환
4. **복구 감지**: 성공 시 Circuit CLOSED로 복원
5. **텔레그램 알림**: Circuit OPEN/CLOSED 상태 알림

##### 롤백 전략

Circuit Breaker 비활성화 옵션 (config.yaml: circuit_breaker: false)

---

### STORY-013: 포지션 동기화 모니터링

**우선순위**: P2 (Post-sizing)
**예상 시간**: 3시간
**의존성**: STORY-007 ✅

##### 목표

GRVT/Backpack 포지션 불일치 감지 및 긴급 알림

##### 구현 내용

1. **주기적 동기화 체크**: 매 헤지 사이클 후 포지션 비교
2. **불일치 감지**:
   - GRVT SHORT ≠ Backpack LONG (절대값 비교, 0.001 ETH 허용 오차)
   - 한쪽만 포지션 있는 경우
3. **긴급 알림**: 텔레그램으로 즉시 알림 (포지션 상세 정보 포함)
4. **자동 복구**: 불일치 발견 시 헤지 사이클 일시 중지 (수동 개입 대기)

##### 롤백 전략

동기화 체크 비활성화 옵션 (config.yaml: sync_check: false)

---

## CRITICAL INSTRUCTIONS (SKILL.md 준수)

### TDD Workflow (절대 준수)
1. ✅ **RED**: 테스트 먼저 작성 → 실패 확인
2. 🧪 **GREEN**: 최소 코드로 테스트 통과
3. ⚡ **REFACTOR**: 코드 품질 개선 (테스트 유지)

### Quality Gate (각 Story마다)
- [ ] Build & Compilation: 에러 없음
- [ ] TDD Compliance: RED → GREEN → REFACTOR 준수
- [ ] Testing: 모든 테스트 PASS, Coverage 달성
- [ ] Code Quality: Linting, formatting 통과
- [ ] Functionality: 수동 테스트 확인
- [ ] 원본 보존 (STORY 1-5): 수정 최소화

### Phase 완료 체크 (SKILL.md Template)
1. ✅ 체크박스 업데이트
2. 🧪 Quality Gate 검증
3. ⚠️ 모든 항목 PASS 확인
4. 📅 문서 날짜 업데이트
5. 📝 Notes 섹션에 교훈 기록
6. ➡️ 다음 Phase 시작

⛔ **절대 금지**:
- 테스트 없이 구현
- Over-engineering
- Lighter 레거시 코드 사용
- Quality Gate 스킵
- STORY 1-5에서 원본 대폭 수정

---

**Document Status**: Ready for Execution
**Next Action**: Phase 0 Clean Slate → STORY-001 시작
**Framework Compliance**: ✅ SKILL.md TDD, Phase Structure, Quality Gates 완전 준수
