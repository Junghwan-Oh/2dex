# Delta Neutral Hedge Bot - Epic & Story Breakdown

## Document Information

| Item | Value |
|------|-------|
| Project | Delta Neutral Hedge Bot (Backpack + GRVT) |
| Version | 2.0.0 |
| Status | Story Sharding Complete |
| Last Updated | 2025-12-23 |
| Related PRD | [docs/prd.md](./prd.md) |
| Related Architecture | [docs/architecture.md](./architecture.md) |

---

## Epic Overview

| Epic ID | Title | Priority | Status | Stories |
|---------|-------|----------|--------|---------|
| EPIC-001 | GRVT Exchange Client 완성 | P0 | 🔄 In Progress | 5 |
| EPIC-002 | Integration Testing | P1 | ⏳ Pending | 4 |
| EPIC-003 | Production Deployment | P1 | ⏳ Pending | 3 |

**Total Stories**: 12

---

## EPIC-001: GRVT Exchange Client 완성

### Epic Description
GRVT DEX와의 완전한 통합을 위한 Exchange Client 개발 및 검증

### Prerequisites
- [x] GRVT 계정 생성
- [x] API Key 발급
- [ ] **GRVT 계정에 마진 입금** (BLOCKER)

### Stories

---

#### STORY-001: GRVT 계정 마진 입금

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-001 |
| Epic | EPIC-001 |
| Priority | P0 (Blocker) |
| Status | ⏳ Pending (User Action Required) |
| Points | 1 |
| Type | Manual Task |

**As a** trader
**I want to** deposit margin into my GRVT account
**So that** I can place hedge orders on GRVT DEX

**Acceptance Criteria**:
- [ ] GRVT 계정에 최소 $1,000 USDT 입금
- [ ] 입금 확인 후 잔액 조회 성공
- [ ] "Insufficient margin" 오류 없이 테스트 주문 가능

**Technical Notes**:
- GRVT 입금 주소 확인 필요
- 입금 후 API로 잔액 조회 테스트
- 이전 오류: `InsufficientMarginToCreateOrder (code 2080)`

**Blocked By**: None
**Blocks**: STORY-002, STORY-003, STORY-004, STORY-005

---

#### STORY-002: GRVT REST API 주문 테스트

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-002 |
| Epic | EPIC-001 |
| Priority | P0 |
| Status | ⏳ Pending |
| Points | 3 |
| Type | Development |

**As a** developer
**I want to** verify GRVT REST API order placement works correctly
**So that** hedge orders can be placed reliably

**Acceptance Criteria**:
- [ ] `place_open_order()` 성공적으로 주문 생성
- [ ] `place_close_order()` 포지션 청산 성공
- [ ] `cancel_order()` 미체결 주문 취소 성공
- [ ] `get_account_positions()` 정확한 포지션 조회
- [ ] 모든 API 호출 로깅 확인

**Technical Tasks**:
1. 마진 입금 후 0.01 ETH 테스트 주문 생성
2. 주문 상태 확인 (open → filled)
3. 포지션 조회로 확인
4. 반대 방향 주문으로 포지션 청산
5. 로그 및 에러 핸들링 검증

**Blocked By**: STORY-001
**Blocks**: STORY-004

---

#### STORY-003: GRVT WebSocket 연결 검증

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-003 |
| Epic | EPIC-001 |
| Priority | P0 |
| Status | ⏳ Pending |
| Points | 3 |
| Type | Development |

**As a** developer
**I want to** verify GRVT WebSocket order updates work correctly
**So that** real-time order status can be tracked

**Acceptance Criteria**:
- [ ] WebSocket 연결 성공 및 인증 완료
- [ ] 주문 생성 시 WebSocket으로 업데이트 수신
- [ ] 주문 체결 시 실시간 알림 수신
- [ ] 연결 끊김 시 자동 재연결 동작
- [ ] Order update callback 정상 동작

**Technical Tasks**:
1. `GrvtCcxtWS` 연결 테스트
2. Order subscription 설정
3. Order update 이벤트 핸들러 검증
4. 재연결 로직 테스트
5. Heartbeat 및 ping/pong 확인

**Blocked By**: STORY-001
**Blocks**: STORY-004

---

#### STORY-004: Backpack + GRVT 헤지 플로우 테스트

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-004 |
| Epic | EPIC-001 |
| Priority | P0 |
| Status | ⏳ Pending |
| Points | 5 |
| Type | Development |

**As a** trader
**I want to** execute a complete hedge cycle (Backpack → GRVT)
**So that** I can validate the delta-neutral strategy works

**Acceptance Criteria**:
- [ ] Backpack에서 0.01 ETH post-only 주문 체결
- [ ] GRVT에서 반대 방향 0.01 ETH 헤지 주문 체결
- [ ] `verifyHedgeCompletion()` 포지션 일치 확인
- [ ] Telegram 알림 정상 전송
- [ ] bot_status.json 상태 업데이트

**Technical Tasks**:
1. `tradingLoop()` 1회 실행
2. Backpack post-only order 체결 확인
3. GRVT hedge order 체결 확인
4. 양쪽 포지션 REST API로 검증
5. 청산 테스트로 포지션 0으로 복귀

**Test Scenarios**:
- Happy path: 양쪽 모두 체결
- Partial fill: Backpack 체결, GRVT 부분 체결
- Timeout: GRVT 주문 타임아웃 시 Backpack 청산

**Blocked By**: STORY-002, STORY-003
**Blocks**: EPIC-002

---

#### STORY-005: Progressive Sizing 로직 검증

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-005 |
| Epic | EPIC-001 |
| Priority | P1 |
| Status | ⏳ Pending |
| Points | 2 |
| Type | Development |

**As a** trader
**I want to** gradually increase order sizes as validation progresses
**So that** I can minimize risk while building confidence

**Acceptance Criteria**:
- [ ] 초기 주문량 `initial_size`로 시작
- [ ] `validation_count` 도달 시 `increment`만큼 증가
- [ ] 최대 주문량 `max_size` 초과 방지
- [ ] `validationCount` 상태 지속성 확인

**Technical Tasks**:
1. config.yaml progressive_sizing 설정 확인
2. 주문량 증가 로직 단위 테스트
3. `validationCount` 상태 저장/복원 테스트
4. 최대값 경계 테스트

**Blocked By**: STORY-004
**Blocks**: None

---

## EPIC-002: Integration Testing

### Epic Description
Backpack + GRVT 통합 시스템의 안정성 및 신뢰성 검증

### Prerequisites
- [ ] EPIC-001 완료

### Stories

---

#### STORY-006: 연속 헤지 사이클 테스트 (10회)

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-006 |
| Epic | EPIC-002 |
| Priority | P0 |
| Status | ⏳ Pending |
| Points | 5 |
| Type | Testing |

**As a** trader
**I want to** run 10 consecutive hedge cycles successfully
**So that** I can validate system stability for Phase 1 deployment

**Acceptance Criteria**:
- [ ] 10회 연속 헤지 사이클 성공
- [ ] 각 사이클 후 포지션 밸런스 확인
- [ ] 오류 발생 시 자동 복구 동작
- [ ] 모든 거래 로그 기록
- [ ] Telegram 알림 정상 작동

**Success Metrics**:
- Success rate: ≥ 90% (9/10)
- Position mismatch: 0
- Error recovery: 100%

**Blocked By**: STORY-004
**Blocks**: STORY-007

---

#### STORY-007: 에러 복구 시나리오 테스트

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-007 |
| Epic | EPIC-002 |
| Priority | P1 |
| Status | ⏳ Pending |
| Points | 5 |
| Type | Testing |

**As a** developer
**I want to** validate error recovery mechanisms
**So that** the system can handle failures gracefully

**Acceptance Criteria**:
- [ ] WebSocket 연결 끊김 시 재연결 성공
- [ ] API 타임아웃 시 재시도 동작
- [ ] 헤지 실패 시 Backpack 포지션 청산
- [ ] Rate limit 시 적절한 백오프
- [ ] 모든 에러 Telegram 알림

**Test Scenarios**:
1. Network interruption simulation
2. API timeout handling
3. Partial fill recovery
4. Exchange maintenance mode handling
5. Insufficient margin during operation

**Blocked By**: STORY-006
**Blocks**: None

---

#### STORY-008: 성능 벤치마크

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-008 |
| Epic | EPIC-002 |
| Priority | P2 |
| Status | ⏳ Pending |
| Points | 3 |
| Type | Testing |

**As a** developer
**I want to** measure system performance metrics
**So that** I can optimize for production deployment

**Acceptance Criteria**:
- [ ] 주문 체결 평균 시간 측정
- [ ] WebSocket 메시지 지연 시간 측정
- [ ] REST API 응답 시간 측정
- [ ] 메모리 사용량 모니터링
- [ ] CPU 사용률 모니터링

**Target Metrics**:
- Order placement: < 500ms
- WebSocket latency: < 100ms
- REST API: < 200ms
- Memory: < 256MB

**Blocked By**: STORY-006
**Blocks**: None

---

#### STORY-009: 50회 연속 헤지 테스트 (Phase 2 Validation)

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-009 |
| Epic | EPIC-002 |
| Priority | P1 |
| Status | ⏳ Pending |
| Points | 8 |
| Type | Testing |

**As a** trader
**I want to** run 50 consecutive hedge cycles
**So that** I can validate readiness for $5,000 deployment

**Acceptance Criteria**:
- [ ] 50회 연속 헤지 성공 (>95% success rate)
- [ ] 총 손실 < 0.1%
- [ ] 포지션 불일치 0건
- [ ] 시스템 다운타임 0

**Success Criteria for Phase 2**:
- 50 consecutive hedges
- Loss < 0.1% of capital
- Zero position mismatches

**Blocked By**: STORY-007
**Blocks**: EPIC-003

---

## EPIC-003: Production Deployment

### Epic Description
프로덕션 환경 배포 및 자동화 운영 설정

### Prerequisites
- [ ] EPIC-002 완료
- [ ] Phase 2 검증 통과

### Stories

---

#### STORY-010: 프로덕션 설정 및 보안 강화

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-010 |
| Epic | EPIC-003 |
| Priority | P0 |
| Status | ⏳ Pending |
| Points | 3 |
| Type | DevOps |

**As a** operator
**I want to** configure production settings securely
**So that** the system is safe for real capital deployment

**Acceptance Criteria**:
- [ ] API 키 환경 변수 또는 시크릿 매니저 사용
- [ ] config.yaml 프로덕션 값 설정
- [ ] 로그 로테이션 설정
- [ ] Telegram 알림 프로덕션 채널 설정
- [ ] IP 화이트리스팅 (지원 시)

**Technical Tasks**:
1. 환경 변수 기반 설정 검증
2. config.yaml.production 템플릿 생성
3. 로그 보관 정책 설정 (30일)
4. 보안 체크리스트 검토

**Blocked By**: STORY-009
**Blocks**: STORY-011

---

#### STORY-011: 자동 시작/재시작 스크립트

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-011 |
| Epic | EPIC-003 |
| Priority | P1 |
| Status | ⏳ Pending |
| Points | 3 |
| Type | DevOps |

**As a** operator
**I want to** have automated start/restart capabilities
**So that** the system can recover from crashes automatically

**Acceptance Criteria**:
- [ ] 시작 스크립트 (start_bot.bat/sh) 생성
- [ ] 프로세스 모니터링 및 자동 재시작
- [ ] 크래시 시 Telegram 알림
- [ ] 상태 파일 기반 재개 로직
- [ ] 안전한 종료 핸들러

**Technical Tasks**:
1. Windows batch 스크립트 작성
2. 프로세스 감시 로직 구현
3. Graceful shutdown 핸들러
4. 상태 복원 로직 검증

**Blocked By**: STORY-010
**Blocks**: STORY-012

---

#### STORY-012: 모니터링 대시보드 설정

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-012 |
| Epic | EPIC-003 |
| Priority | P2 |
| Status | ⏳ Pending |
| Points | 5 |
| Type | DevOps |

**As a** operator
**I want to** monitor system health and trading performance
**So that** I can detect and respond to issues quickly

**Acceptance Criteria**:
- [ ] 실시간 포지션 모니터링
- [ ] P&L 추적
- [ ] 거래 이력 조회
- [ ] 알림 히스토리
- [ ] 시스템 상태 지표

**Options**:
1. Telegram bot commands (/status, /pnl, /history)
2. Simple web dashboard (Flask/FastAPI)
3. Log-based monitoring (ELK stack)

**Blocked By**: STORY-011
**Blocks**: None

---

## Story Dependency Graph

```
STORY-001 (마진 입금) [BLOCKER]
    │
    ├──► STORY-002 (REST API 테스트)
    │         │
    │         └──► STORY-004 (헤지 플로우 테스트)
    │                   │
    │                   ├──► STORY-005 (Progressive Sizing)
    │                   │
    │                   └──► STORY-006 (10회 연속 테스트)
    │                             │
    │                             └──► STORY-007 (에러 복구)
    │                             │         │
    │                             │         └──► STORY-009 (50회 테스트)
    │                             │                   │
    │                             │                   └──► STORY-010 (프로덕션 설정)
    │                             │                             │
    │                             │                             └──► STORY-011 (자동화)
    │                             │                                       │
    │                             │                                       └──► STORY-012 (모니터링)
    │                             │
    │                             └──► STORY-008 (성능 벤치마크)
    │
    └──► STORY-003 (WebSocket 테스트)
              │
              └──► STORY-004 (헤지 플로우 테스트)
```

---

## Implementation Priority

### 🔴 Immediate (Blocked by User Action)
1. **STORY-001**: GRVT 계정 마진 입금

### 🟡 After Margin Deposit
2. **STORY-002**: GRVT REST API 주문 테스트
3. **STORY-003**: GRVT WebSocket 연결 검증
4. **STORY-004**: Backpack + GRVT 헤지 플로우 테스트

### 🟢 Validation Phase
5. **STORY-005**: Progressive Sizing 로직 검증
6. **STORY-006**: 연속 헤지 사이클 테스트 (10회)
7. **STORY-007**: 에러 복구 시나리오 테스트
8. **STORY-008**: 성능 벤치마크
9. **STORY-009**: 50회 연속 헤지 테스트

### 🔵 Production Deployment
10. **STORY-010**: 프로덕션 설정 및 보안 강화
11. **STORY-011**: 자동 시작/재시작 스크립트
12. **STORY-012**: 모니터링 대시보드 설정

---

## Live Trading Validation Stories (STORY-V Series)

EPIC-001 완료 후 라이브 트레이딩 검증 과정에서 발생한 추가 스토리들입니다.

---

#### STORY-V1: Consecutive Success Tracking

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-V1 |
| Epic | EPIC-001 |
| Priority | P0 |
| Status | ✅ Completed |
| Points | 2 |
| Type | Development |
| Completed | 2025-12-23 |

**As a** trader
**I want to** track consecutive successful hedge cycles
**So that** I can safely scale up position sizes based on proven reliability

**Acceptance Criteria**:
- [x] Consecutive success counter implementation
- [x] State persistence across bot restarts
- [x] Reset on failure logic

**Related Documentation**: [STORY-V1_COMPLETION_REPORT.md](./STORY-V1_COMPLETION_REPORT.md)

---

#### STORY-V2: Dynamic Sizing with Phase Advancement

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-V2 |
| Epic | EPIC-001 |
| Priority | P0 |
| Status | ✅ Completed |
| Points | 3 |
| Type | Development |
| Completed | 2025-12-24 |

**As a** trader
**I want to** automatically increase order sizes after consecutive successes
**So that** I can progressively scale from $10 to $500 positions

**Acceptance Criteria**:
- [x] Dynamic order size calculation (target_value / current_price)
- [x] Phase advancement after 3 consecutive successes
- [x] Phase downgrade after 2 consecutive failures
- [x] 6 phases: $10, $20, $50, $100, $200, $500

**Related Documentation**: [STORY-V2_COMPLETION_REPORT.md](./STORY-V2_COMPLETION_REPORT.md)

---

#### STORY-V3: Live Trading Validation ($10 → $500)

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-V3 |
| Epic | EPIC-001 |
| Priority | P0 |
| Status | 🔄 In Progress |
| Points | 8 |
| Type | Validation |
| Started | 2025-12-24 |

**As a** trader
**I want to** validate progressive sizing in live trading
**So that** I can confirm the system works with real money

**Acceptance Criteria**:
- [x] Phase 1 ($10): 3 consecutive successes
- [ ] Phase 2 ($20): 3 consecutive successes
- [ ] Phase 3 ($50): 3 consecutive successes
- [ ] Phase 4 ($100): 3 consecutive successes
- [ ] Phase 5 ($200): 3 consecutive successes
- [ ] Phase 6 ($500): Continuous operation

**Current Status**:
- Phase 1 완료 (3회 성공)
- ~~Rate Limit Error 1006 발생으로 Phase 2 진입 차단~~ → 오진단
- 실제 원인: 이전 세션의 미체결 주문 4개가 남아있었음
- STORY-V4 롤백됨, 봇 시작 시 미체결 주문 취소 로직 필요

**Related Documentation**: [STORY-V3_LIVE_TRADING_GUIDE.md](./STORY-V3_LIVE_TRADING_GUIDE.md)

---

#### STORY-V4: ~~WebSocket-Only Rate Limit Fix~~ → 오진단으로 롤백됨

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-V4 |
| Epic | EPIC-001 |
| Priority | P0 (Blocker for V3 Scale-Up) |
| Status | ❌ ROLLED BACK (오진단) |
| Points | 3 |
| Type | Development |
| Created | 2025-12-25 |
| Rolled Back | 2025-12-25 |

**As a** trader
**I want to** track order status via WebSocket only
**So that** I can avoid GRVT rate limit errors during progressive sizing scale-up

**Problem Statement (오진단)**:
~~STORY-V3 Phase 1 완료 후 Phase 2 진입 시 GRVT Rate Limit Error 1006 발생.~~
~~REST polling이 10초당 600+ API 호출 → GRVT 한도 (60/분) 10배 초과.~~

**실제 원인**:
```
[ERROR] Error placing GRVT order: [OPEN] ERROR: Active open orders abnormal: 4
```
- 이전 세션에서 4개의 미체결 주문이 남아있었음
- 이 주문들이 새 세션 중 체결되면서 헷지 불균형 발생
- Rate Limit과 무관한 문제였음

**Solution (롤백됨)**:
~~- `_pendingOrders` 딕셔너리로 주문 추적~~
~~- `asyncio.Event()` 기반 동기화~~
~~- `place_post_only_order()` REST 폴링 완전 제거~~
~~- WebSocket 핸들러에서 이벤트 시그널링~~

**실제 필요한 해결책**:
- 봇 시작 시 미체결 주문 전체 취소 (단 몇 줄)

**Acceptance Criteria**:
- [ ] ~~`_pendingOrders` 딕셔너리 추가~~ → 롤백됨
- [ ] ~~`place_post_only_order()` REST 폴링 제거~~ → 롤백됨
- [ ] ~~WebSocket 이벤트 기반 주문 상태 대기~~ → 롤백됨
- [ ] ~~TDD 테스트 10개 통과~~ → 불필요
- [ ] ~~라이브 연결 테스트 성공~~ → 불필요

**POST-MORTEM**: [POST_MORTEM_V4_MISDIAGNOSIS.md](./POST_MORTEM_V4_MISDIAGNOSIS.md)

**교훈**:
1. 로그를 꼼꼼히 읽고 실제 에러 메시지 확인
2. 키워드("Rate Limit")에 즉시 반응하지 않기
3. 가설 검증 후 구현
4. 최소 개입 원칙 (Over-Engineering 금지)

---

#### STORY-V5: Clean Start - 미체결 주문 정리 로직

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-V5 |
| Epic | EPIC-001 |
| Priority | P0 (Blocker for V3 Phase 2+) |
| Status | ✅ Completed |
| Points | 1 |
| Type | Development |
| Created | 2025-12-25 |
| Completed | 2025-12-25 |

**As a** trader
**I want to** automatically cancel all pending orders when bot starts
**So that** I can avoid hedge imbalance from stale orders in previous sessions

**Problem Statement**:
- STORY-V4 오진단 분석에서 발견된 실제 원인
- 이전 세션의 미체결 주문이 새 세션에서 예기치 않게 체결됨
- 헷지 불균형 발생 → Rate Limit 에러로 오인

**Root Cause Analysis**:
```
2025-12-25 13:04:19,957 - ERROR - [ERROR] Error placing GRVT order:
[OPEN] ERROR: Active open orders abnormal: 4
```

**Solution** (최소 개입 원칙):
- `trading_loop()` 초기화 직후 미체결 주문 전체 취소
- GRVT + Backpack 모두 적용
- 10줄 이내의 간단한 코드

**Implementation**:
```python
async def ensure_clean_start(self):
    """Cancel all open orders before starting trading loop."""
    # GRVT
    grvt_orders = await self.grvt_client.get_active_orders(self.grvt_contract)
    for order in grvt_orders:
        await self.grvt_client.cancel_order(order.order_id)

    # Backpack
    bp_orders = await self.backpack_client.get_active_orders(self.backpack_contract_id)
    for order in bp_orders:
        await self.backpack_client.cancel_order(order.order_id)
```

**Acceptance Criteria**:
- [x] `ensure_clean_start()` 함수 구현
- [x] GRVT 미체결 주문 취소
- [x] Backpack 미체결 주문 취소
- [x] 라이브 테스트 성공 (봇 정상 실행 확인)

**Related Documentation**:
- [POST_MORTEM_V4_MISDIAGNOSIS.md](./POST_MORTEM_V4_MISDIAGNOSIS.md)
- Wintermute Tech Lead Analysis (2025-12-25)

---

## Updated Dependency Graph

```
STORY-001 (마진 입금) [COMPLETED]
    │
    ├──► STORY-002 (REST API 테스트) [COMPLETED]
    │         │
    │         └──► STORY-004 (헤지 플로우 테스트) [COMPLETED]
    │                   │
    │                   └──► STORY-V1 (Consecutive Tracking) ✅
    │                             │
    │                             └──► STORY-V2 (Dynamic Sizing) ✅
    │                                       │
    │                                       └──► STORY-V3 (Live Trading) 🔄
    │                                                 │
    │                                                 ├──► Phase 1: $30 ✅
    │                                                 ├──► STORY-V4 (Rate Limit Fix) ❌ 롤백
    │                                                 ├──► STORY-V5 (Clean Start) ✅
    │                                                 └──► Phase 2-6: $60-$1500 ⏳
    │
    └──► STORY-003 (WebSocket 테스트) [COMPLETED]
```

---

## Summary

| Metric | Value |
|--------|-------|
| Total Epics | 3 |
| Total Stories | 12 (base) + 5 (V-series) = 17 |
| Total Story Points | 46 + 17 = 63 |
| Blockers | 0 |
| Completed Stories | 4 (V1, V2, V3-Phase1, V5) |
| Rolled Back | 1 (V4 - 오진단) |
| In Progress | 1 (STORY-V3 Phase 2+) |

**Critical Path**: ~~STORY-001~~ → ~~STORY-002/003~~ → ~~STORY-004~~ → ~~V1~~ → ~~V2~~ → V3 (Phase 2+) → STORY-006 → STORY-009

**Current Focus**:
1. ~~봇 시작 시 미체결 주문 취소 로직 추가~~ ✅ STORY-V5 완료
2. STORY-V3 Phase 2+ 라이브 트레이딩 재개

**Next Action**:
1. `python hedge_mode_bp.py --ticker ETH --iter 10` 실행
2. Phase 2 ($60) 진입 확인

---

*Document updated: 2025-12-25*
*Last Change: STORY-V5 완료 - ensure_clean_start() 구현 및 검증*

---

#### STORY-V6: Entry Price & Order Type Validation

| Attribute | Value |
|-----------|-------|
| Story ID | STORY-V6 |
| Epic | EPIC-001 |
| Priority | P0 (V3 Phase 2 진입 전 검증) |
| Status | ✅ Completed |
| Points | 2 |
| Type | Validation |
| Created | 2025-12-26 |

**As a** trader
**I want to** validate entry prices and order types on both exchanges
**So that** I can ensure delta-neutral positions without unfavorable fills on both sides

**Problem Statement**:
- 유저 보고: 양쪽(GRVT, Backpack) 모두 불리한 가격으로 체결됨
- 코드 불일치: place_backpack_post_only_order() 함수명 vs 로그 "TAKER order" 출력
- 양쪽 모두 불리 → 헷지임에도 양쪽 손실 가능성

**Expected Behavior**:
| Exchange | Order Type | Price | 기대 |
|----------|------------|-------|------|
| GRVT | IOC TAKER | Hit bid/ask | 불리 (정상) |
| Backpack | Post-Only MAKER | Provide liquidity | 유리 (필수) |

**Investigation Tasks**:
1. Backpack 주문 로직 분석 - 실제 MAKER인지 TAKER인지 확인
2. 로그 메시지 정합성 수정
3. 체결 가격 로그 분석 (bid/ask 대비)
4. 필요시 주문 로직 수정

**Acceptance Criteria**:
- [x] Backpack 주문이 실제 Post-Only MAKER인지 확인 ✅ `'postOnly': True` 확인
- [x] 로그 메시지와 실제 주문 타입 일치 ✅ "MAKER order (post_only)" 출력
- [x] Entry Price 로그에 bid/ask 대비 표시 ✅ `bid=2937, ask=2937.01` 로그 확인
- [x] GRVT: 불리 (정상), Backpack: 유리 또는 동일 확인 ✅ 체결가 2937 < ask 2937.01

**Verification Results** (2025-12-26):
- BUY @ 2937.00 (bid=2937, ask=2937.01) - 유리한 가격으로 체결됨
- `post_only=True` API 응답 확인
- MAKER 로그 메시지 정상 출력

**Blocked By**: STORY-V5 ✅
**Blocks**: STORY-V3 Phase 2+ (UNBLOCKED)

