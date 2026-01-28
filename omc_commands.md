# OMC (Oh-My-Claude-Code) 커맨드 참조

**마지막 업데이트**: 2026-01-28

## 개요

OMC는 Claude Code CLI의 멀티 에이전트 오케스트레이션 플랫폼입니다. 사용자가 간단한 요청만으로도 복잡한 작업을 완료할 수 있도록 지원합니다.

---

## 현재 프로젝트의 커스텀 스킬

### `feature-planner`

**사용법**: `/oh-my-claudecode:feature-planner`

**용도**: 기능을 단계별로 계획하고, 품질 게이트를 통해 검증하는 구조화된 계획 생성

**시작 키워드**:
- `plan`, `planning`, `phases`, `breakdown`, `strategy`, `roadmap`, `organize`, `structure`, `outline`

**주요 기능**:
- 3-7개의 단계(Phase)로 기능 분해
- TDD(테스트 주도 개발) 통합 - 테스트를 먼저 작성
- 각 Phase마다 1-4시간 제한
- 품질 게이트(빌드, 테스트, 코드 품질, 보안 등) 확인
- 롤백 전략 문서화
- 단계별 진행 추적 (마크다운 체크박스)

**Phase 구조**:
```
Phase Name: 명확한 결과물
Goal: 작동하는 기능 명시
Test Strategy: 테스트 유형, 커버리타 목표, 시나리오
Tasks (ordered by TDD workflow):
  1. RED Tasks: 실패하는 테스트 먼저 작성
  2. GREEN Tasks: 테스트 통과하는 최소 구현
  3. REFACTOR Tasks: 테스트 통과하며 코드 품질 개선
Quality Gate: TDD 준수 + 검증 기준
Dependencies: Phase 시작 전 필요한 것들
Coverage Target: 이 Phase의 커버리타 목표
```

---

## 모드 커맨드 (Parallel Execution)

### `/ultrawork` - 최대 병렬 실행

**사용법**: `/oh-my-claudecode:ultrawork`

**설명**: 여러 에이전트를 동시에 작업시켜 최대 성능을 발휘합니다.

**트리거 키워드**: `ulw`, `ultrawork`, `fast`, `parallel` (config 기본값에 따라)

**특징**:
- 여러 독립적인 작업을 병렬 처리
- 최대 5개의 백그라운드 작업 지원
- 자동 작업 분해 및 파일 소유권 할당

### `/ecomode` - 토큰 효율적 병렬

**사용법**: `/oh-my-claudecode:ecomode`

**설명**: 토큰 사용을 최적화하여 비용을 절감하는 병렬 모드입니다.

**트리거 키워드**: `eco`, `ecomode`, `efficient`, `save-tokens`, `budget`

**특징**:
- Haiku 모델 사용 (빠르고 저렴한)
- 세부 토큰 한도 설정 가능
- 큰 코드베이스 작업에 최적

---

## 스마트 파이프라인/워크플로우

### `/orchestrate` - 멀티 에이전트 오케스트레이션

**사용법**: `/oh-my-claudecode:orchestrate`

**설명**: 여러 전문 에이전트를 동시에 호출하여 작업 수행

### `/autopilot` - 자율 실행 (추천)

**사용법**: `/oh-my-claudecode:autopilot`

**설명**: **핵심 기능** - 사용자가 고수준 요청만 하면, 에이전트가 자동으로:
1. 계획 수립 및 요구사항 수집
2. 병렬 작업 분배
3. 지속적인 검증 및 수정
4. 작동하는 코드로 완료

**시작 키워드**: `autopilot`, `build me`, `I want a`

**특징**:
- 전체 자동화: 계획 → 분석 → 구현 → 테스트 → 검증
- 사용자 개입 없이 완료까지 진행
- 필요시 중단/수정 가능

### `/ultrapilot` - 병렬 자율 실행 (3-5x 빠름)

**사용법**: `/oh-my-claudecode:ultrapilot`

**설명**: 자율 실행 모드의 빠른 버전

**시작 키워드**: `ultrapilot`, `parallel build`, `swarm build`

**특징**:
- 3-5개의 병렬 워커
- 파일 소유권 코디네이터
- 충돌 감지 및 해결

### `/swarm` - N개 에이전트 동시 작업

**사용법**: `/oh-my-claudecode:swarm N:executor "task"`

**예시**: `/oh-my-claudecode:swarm 5:executor "fix all TypeScript errors"`

**설명**: N개의 에이전트가 공유 작업 리스트에서 순차적으로 작업 수행

**특징**:
- 공유 작업 리스트 (pending/claimed/done 상태)
- 각 작업 5분 타임아웃, 자동 해제
- 청크별 집계 결과

**특징**:
- 에이전트 수: N (1-5개)
- 타임아웃: 5분/작업
- 자동 해제: 타임아웃 시

### `/pipeline` - 순차적 에이전트 체인

**사용법**: `/oh-my-claudecode:pipeline`

**내장 프리셋**:

| 프리셋 | 단계 |
|--------|------|
| `review` | explore → architect → critic → executor |
| `implement` | planner → executor → tdd-guide |
| `debug` | explore → architect → build-fixer |
| `research` | parallel(researcher, explore) → architect → writer |
| `refactor` | explore → architect-medium → executor-high → qa-tester |
| `security` | explore → security-reviewer → executor → security-reviewer-low |

**커스텀 파이프라인**: `/pipeline explore:haiku -> architect:opus -> executor:sonnet`

---

## 계획/설계

### `/plan` - 계획 세션 (인터뷰)

**사용법**: `/oh-my-claudecode:plan`

**설명**: 넓은/모호한 요청을 위해 사용자와 인터뷰하여 계획을 수립합니다.

**특징**:
- 사용자 선호 질문 (AskUserQuestion UI)
- 타입: Requirement, Scope, Constraint, Risk Tolerance

### `/ralplan` - 반복적 계획 (합의)

**사용법**: `/oh-my-claudecode:ralplan`

**설명**: Planner, Architect, Critic 세 에이전트가 합의를 이루는 반복적 계획

**트리거 키워드**: `ralplan`

**특징**:
- 합의 도달까지 반복
- 전문가 의견 충돌 해결

### `/review` - 계획 검토

**사용법**: `/oh-my-claudecode:review`

**설명**: Critic 에이전트가 계획을 검토합니다.

---

## 기타 고급 기능

### `/ralph` - 지속적 실행

**사용법**: `/oh-my-claudecode:ralph`

**설명**: **중요** - "don't stop", "must complete" 키워드와 함께 사용하여 작업이 완료될 때까지 계속 실행

**트리거 키워드**: `don't stop`, `must complete`

**특징**:
- 작업 완료 전 중단하지 않음
- 자동 재시도 및 롤백
- 완료까지 지속적인 검증

### `/ultraqa` - QA 사이클링

**사용법**: `/oh-my-claudecode:ultraqa`

**설명**: 테스트 → 검증 → 수정 → 반복의 QA 사이클을 자동화

**특징**:
- 테스트 작성
- 실패 시 수정
- 검증 실행
- 재시도直到成功
- 완료 보고

### `/cancel` - 통합 취소

**사용법**: `/oh-my-claudecode:cancel`

**설명**: 현재 활성화된 모드를 자동 감지하여 취소

**옵션**:
- 기본: 현재 모드 취소
- `--force` 또는 `--all`: 모든 OMC 상태 초기화

**시작 키워드**: `stop`, `cancel`, `abort`

### `/learner` - 스킬 추출

**사용법**: `/oh-my-claudecode:learner`

**설명**: 현재 세션에서 학습된 패턴을 재사용 가능한 스킬로 추출

---

## 전문가 에이전트

### `/analyze` - 깊은 분석/조사

**사용법**: `/oh-my-claudecode:analyze`

**설명**: 복잡한 버그 분석, 아키텍처 조사

**톤**: Opus

### `/deepsearch` - 코드베이스 탐색

**사용법**: `/oh-my-claudecode:deepsearch`

**설명**: 파일/패턴 검색, 코드베이스 구조 이해

**톤**: Haiku (빠름) 또는 Sonnet

### `/research` - 문서/API 조사

**사용법**: `/oh-my-claudecode:research`

**설명**: 외부 문서, API 문서 조사

**에이전트**: Scientist (Sonnet)

### `/security-review` - 보안 검토

**사용법**: `/oh-my-claudecode:security-review`

**설명**: OWASP Top 10 취약점, 보안 패턴 검토

**에이전트**: Security Reviewer (Opus)

### `/code-review` - 코드 품질 검토

**사용법**: `/oh-my-claudecode:code-review`

**설명**: 코드 품질, 보안, 유지보수성 검토

**에이전트**: Code Reviewer (Opus)

### `/tdd` - TDD 워크플로우 강제

**사용법**: `/oh-my-claudecode:tdd`

**설명**: 테스트를 먼저 작성하도록 강제하는 TDD 워크플로우

**목표**: 80%+ 테스트 커버리지

### `/git-master` - Git 전문가

**사용법**: `/oh-my-claudecode:git-master`

**설명**: 커밋, 리베이스, 히스토리 관리 전문가

**특징**:
- 원자적 커밋
- 리베이스 히스토리 관리
- 스타일 감지

---

## 유틸리티

### `/doctor` - OMC 진단

**사용법**: `/oh-my-claudecode:doctor`

**설명**: OMC 설치 문제 진단 및 수정

### `/help` - 사용 가이드

**사용법**: `/oh-my-claudecode:help`

**설명**: OMC 사용법 가이드

### `/mcp-setup` - MCP 서버 설정

**사용법**: `/oh-my-claudecode:mcp-setup`

**설명**: MCP 서버를 사용하여 에이전트 기능 확장

### `/hud` - HUD 상태줄 설정

**사용법**: `/oh-my-claudecode:hud`

**설명**: HUD 상태줄 레이아웃/프리셋/요소 설정

### `/note` - 메모 저장

**사용법**: `/oh-my-claudecode:note`

**설명**: notepad.md에 메모 저장 (복원성 지원)

### `/omc-setup` - 초기 설정

**사용법**: `/oh-my-claudecode:omc-setup`

**설명**: OMC 한 번 설정 (자동화)

---

## 에이전트 라우팅 가이드

| 작업 유형 | 에이전트 | 모델 | 설명 |
|----------|----------|------|------|
| 단순 코드 조회 | `explore` | haiku | "이것은 어떤 값을 반환하는가?" |
| 파일/패턴 검색 | `explore` / `explore-medium` | haiku/sonnet | "find definition of X" |
| 복잡한 아키텍처 탐색 | `explore-high` | opus | 코드베이스 구조 이해 |
| 단일 코드 변경 | `executor-low` | haiku | 한 줄 수정 |
| 기능 구현 | `executor` | sonnet | "Add error handling" |
| 복잡한 리팩토링 | `executor-high` | opus | 아키텍처 변경 |
| 단순 디버깅 | `architect-low` | haiku | 간단한 버그 |
| 복잡한 디버깅 | `architect` | opus | 경쟁 상태, 복잡한 논리 |
| UI/컴포넌트 | `designer` | sonnet | "Add validation" |
| 복잡한 UI 시스템 | `designer-high` | opus | 디자인 시스템 |
| 문서/주석 작성 | `writer` | haiku | "Write README" |
| 문서/API 조사 | `researcher` | sonnet | "Research API" |
| 이미지/다이어그램 분석 | `vision` | sonnet | "Analyze diagram" |
| 전략적 계획 | `planner` | opus | "Plan new API" |
| 계획 검토 | `critic` | opus | "Review plan" |
| 사전 계획 분석 | `analyst` | opus | "Analyze requirements" |
| CLI 상호작용 테스트 | `qa-tester` | sonnet | "Test CLI" |
| 보안 검토 | `security-reviewer` | opus | "Review security" |
| 단순 보안 스캔 | `security-reviewer-low` | haiku | "Quick security check" |
| 빌드 에러 수정 | `build-fixer` | sonnet | "Fix build errors" |
| 단순 빌드 수정 | `build-fixer-low` | haiku | "Trivial type errors" |
| TDD 워크플로우 | `tdd-guide` | sonnet | "Test-first development" |
| 단순 테스트 제안 | `tdd-guide-low` | haiku | "Quick test ideas" |
| 코드 검토 | `code-reviewer` | opus | "Review code" |
| 빠른 코드 검사 | `code-reviewer-low` | haiku | "Quick code check" |
| 데이터 분석/통계 | `scientist` | sonnet | "Analyze data" |
| 단순 데이터 검사 | `scientist-low` | haiku | "Quick data inspection" |
| 복잡한 ML/가설 | `scientist-high` | opus | "ML hypothesis testing" |

---

## 대화 전략

### BROAD REQUEST 감지 및 처리

**정의**: BROAD REQUEST = 다음 중 하나 이상
- 모호한 동사: "improve", "enhance", "fix" (대상 없음)
- 특정 파일/함수 언급 없음
- 3개 이상 관련 없는 영역에 영향
- 문장으로만 구성되고 명확한 결과물 없음

**처리 프로세스**:
1. `explore` 에이전트로 코드베이스 이해
2. 필요시 `architect`에 자문
3. THEN `plan` 스킬에 맥락 전달
4. Plan 스킬이 사용자에게만 선호 질문

### AskUserQuestion 사용 (Planning 모드)

Planning/Interview 모드에서는 선호 질문에 `AskUserQuestion` 도구 사용:

```markdown
**Question types**: Preference, Requirement, Scope, Constraint, Risk tolerance
```

---

## 검증-전-완료 프로토콜

**중요 규칙**: 완료 주장 전 반드시 검증 증거 있어야 함

| 주장 | 필요 증거 |
|------|----------|
| "Fixed" | 테스트 통과 증명 |
| "Implemented" | lsp_diagnostics 정리 + 빌드 통과 |
| "Refactored" | 모든 테스트 여전히 통과 |
| "Debugged" | 파일:행에서 루트 원인 파악 |

**심각한 신호 (중지 및 검증)**:
- "should", "probably", "seems to" 사용
- 검증 전 만족 표현
- 검증 없이 완료 주장

**증거 유형**:
| 주장 | 필요 증거 |
|------|----------|
| "Fixed" | 작동하는 테스트 결과 |
| "Implemented" | lsp_diagnostics 정리 + 빌드 통과 |
| "Refactored" | 모든 테스트 여전히 통과 |
| "Debugged" | 루트 원인 파일:행 파악 |

---

## 병렬화 규칙

- **2+ 독립 작업** (>30초 작업) → 병렬 실행
- **순차 의존** → 순서대로 실행
- **빠른 작업** (<10초) → 직접 실행 (read, status check)

---

## 백그라운드 실행

**백그라운드** (`run_in_background: true`):
- npm install, pip install
- npm run build, make, tsc
- npm test, pytest, cargo test

**포그라운드** (실행 직렬):
- git status, ls, pwd
- File reads/edits
- Quick commands

**최대 동시 백그라운드**: 5개

---

## Notepad Wisdom System (v3.1+)

Plan-scoped 지혜 캡처: learnings, decisions, issues, problems

**위치**: `.omc/notepads/{plan-name}/`

| 파일 | 용도 |
|------|------|
| `learnings.md` | 기술적 발견 및 패턴 |
| `decisions.md` | 아키텍처 및 설계 결정 |
| `issues.md` | 알려진 이슈 및 워크라운드 |
| `problems.md` | 차단 요소 및 도전 과제 |

---

## 경로 기반 쓰기 규칙

**허용 경로 (직접 쓰기 가능)**:
| 경로 | 사용 |
|------|------|
| `~/.claude/**` | 시스템 설정 |
| `.omc/**` | OMC 상태 및 설정 |
| `.claude/**` | 로컬 클라우드 설정 |
| `CLAUDE.md` | 사용자 지침 |
| `AGENTS.md` | AI 문서화 |

**경고 경로 (위임 권장)**:
| 확장자 | 유형 |
|--------|------|
| `.ts`, `.tsx`, `.js`, `.jsx` | JavaScript/TypeScript |
| `.py` | Python |
| `.go`, `.rs`, `.java` | 컴파일된 언어 |
| `.c`, `.cpp`, `.h` | C/C++ |
| `.svelte`, `.vue` | 프론트엔드 프레임워크 |

---

## 에이전트 선택 가이드

| 작업 유형 | Best Agent | Model | 사용 시점 |
|----------|------------|-------|----------|
| 빠른 코드 조회 | `explore` | haiku | "이것은 어떤 값을 반환하는가?" |
| 파일/패턴 검색 | `explore` / `explore-medium` | haiku/sonnet | "find definition of X" |
| 복잡한 아키텍처 탐색 | `explore-high` | opus | 코드베이스 구조 이해 |
| 단일 코드 변경 | `executor-low` | haiku | 한 줄 수정 |
| 기능 구현 | `executor` | sonnet | "Add error handling" |
| 복잡한 리팩토링 | `executor-high` | opus | 아키텍처 변경 |
| 단순 디버깅 | `architect-low` | haiku | 간단한 버그 |
| 복잡한 디버깅 | `architect` | opus | 경쟁 상태, 복잡한 논리 |
| UI/컴포넌트 | `designer` | sonnet | "Add validation" |
| 복잡한 UI 시스템 | `designer-high` | opus | 디자인 시스템 |
| 문서/주석 작성 | `writer` | haiku | "Write README" |
| 문서/API 조사 | `researcher` | sonnet | "Research API" |
| 이미지/다이어그램 분석 | `vision` | sonnet | "Analyze diagram" |
| 전략적 계획 | `planner` | opus | "Plan new API" |
| 계획 검토 | `critic` | opus | "Review plan" |
| 사전 계획 분석 | `analyst` | opus | "Analyze requirements" |
| CLI 상호작용 테스트 | `qa-tester` | sonnet | "Test CLI" |
| 보안 검토 | `security-reviewer` | opus | "Review security" |
| 단순 보안 스캔 | `security-reviewer-low` | haiku | "Quick security check" |
| 빌드 에러 수정 | `build-fixer` | sonnet | "Fix build errors" |
| 단순 빌드 수정 | `build-fixer-low` | haiku | "Trivial type errors" |
| TDD 워크플로우 | `tdd-guide` | sonnet | "Test-first development" |
| 단순 테스트 제안 | `tdd-guide-low` | haiku | "Quick test ideas" |
| 코드 검토 | `code-reviewer` | opus | "Review code" |
| 빠른 코드 검사 | `code-reviewer-low` | haiku | "Quick code check" |
| 데이터 분석/통계 | `scientist` | sonnet | "Analyze data" |
| 단순 데이터 검사 | `scientist-low` | haiku | "Quick data inspection" |
| 복잡한 ML/가설 | `scientist-high` | opus | "ML hypothesis testing" |

---

## 사용 예시

```bash
# 커스텀 커맨드 - 기능 계획 생성
"feature-planner: Add dark mode toggle"

# 병렬 최대 성능 모드
"ulw: fix all TypeScript errors"

# 토큰 절약 모드
"eco: optimize codebase"

# 자율 실행 (완전 자동화)
"autopilot: build me a REST API for managing tasks"

# 지속적 실행 (완료될 때까지 계속)
"ralph: refactor the entire authentication system"

# QA 사이클링 (테스트/수정/검증 반복)
"ultraqa: test the trading bot"

# 계획 검토
"review plan"

# TDD 워크플로우 (테스트 우선)
"tdd: implement user auth"
```

---

## 참고 자료

- [MIGRATION.md](./MIGRATION.md) - 마이그레이션 가이드
- [Global CLAUDE.md](../CLAUDE.md) - 전역 사용자 지침