# 7-Day Harness Plan

## Purpose

이 문서는 현재 `dexbot` 환경에서 하네스 역량을 빠르게 끌어올리기 위한 7일 집중 플랜이다.

목표는 아래 세 가지를 동시에 진전시키는 것이다.

- 현재 하네스 문제 정리
- single-shot 방법론 공부와 체화
- 자기 암묵지 추출 기반의 `self-senpai` 방향 MVP 준비

이 문서는 "일주일 안에 싱글샷 달인 되기"가 아니라,
"일주일 안에 싱글샷 가능한 환경과 사고방식의 초석 만들기"를 목표로 한다.

## Week Goal

7일이 끝났을 때 아래 상태에 도달하는 것을 목표로 한다.

- clean lane에서 새 작업을 시작할 수 있다
- starter pack의 최소 골격이 존재한다
- 공통 verify 루프가 있다
- 자기 암묵지 입력 소스가 정리되어 있다
- `yourself-skill x colleague-skill` 하이브리드 관점의 tiny MVP 설계가 끝나 있다
- 최소 한 개 runnable reference 또는 실사용 가능한 skeleton이 있다

## Ground Rules

- dirty repo 위에서 직접 시작하지 않는다
- 문서만 쓰고 끝내지 않는다
- 매일 artifact를 하나 이상 남긴다
- 저장 후 readback 검증을 한다
- “좋은 아이디어”보다 “실행 가능한 구조”를 우선한다
- 하루 작업은 반드시 다음날 시작 조건을 개선해야 한다

## Day 1 — 현재 상태를 정직하게 고정

### 목표

지금 환경의 병목을 감정 없이 정리한다.

### 해야 할 일

- 현재 `dexbot` 루트의 오염 상태를 기록
- canonical orchestration surface가 무엇인지 정리
- 현재 존재하는 surface 목록 작성
  - `.claude`
  - `.omc`
  - `.opencode`
  - `.bmad-core`
  - `harness/`
- "single-shot이 안 되는 이유"를 항목형으로 정리
- 현재 이미 만든 하네스 문서 3개를 다시 읽고 겹침/부족분 표시

### 산출물

- `CURRENT_STATE.md`
- `SURFACE_MAP.md`

### 완료 기준

- 지금 왜 복잡한지 설명할 수 있다
- 앞으로 무엇을 버리고 무엇을 canonical로 쓸지 후보가 생긴다

## Day 2 — Clean Lane 확립

### 목표

새 작업을 오염 없이 시작하는 최소 습관을 만든다.

### 해야 할 일

- clean worktree 규칙 문서화
- 브랜치 네이밍 규칙 정리
- 하네스 작업 전용 lane 생성 규칙 정리
- "문서 lane", "실험 lane", "제품 lane" 구분
- 다음 프로젝트부터 그대로 쓸 시작 절차를 체크리스트로 작성

### 산출물

- `CLEAN_LANE_RULES.md`
- `START_CHECKLIST.md`

### 완료 기준

- 새 작업 시작 절차가 5분 안에 실행 가능하다
- dirty branch에서 일하는 습관을 의식적으로 차단할 수 있다

## Day 3 — Starter Pack 설계

### 목표

문서가 아니라 실제 starter pack 골격을 만든다.

### 해야 할 일

- starter pack 디렉터리 구조 설계
- 아래 파일 템플릿 작성
  - `AGENTS.md`
  - `skills/interview/SKILL.md`
  - `skills/generate/SKILL.md`
  - `skills/qa/SKILL.md`
  - `skills/publish/SKILL.md`
  - `hooks/session-start.sh`
  - `hooks/pre-tool-use.sh`
  - `hooks/post-tool-use.sh`
  - `VERIFY.md`
- 최소 data skeleton 생성
  - `personas/default/`
  - `content/drafts/`
  - `content/qa/`
  - `content/published/`

### 산출물

- `harness/starter/` 실제 파일 세트

### 완료 기준

- 새 프로젝트를 starter pack 복사로 시작할 수 있다
- 역할, 저장 위치, verify 흐름이 파일로 존재한다

## Day 4 — Single-Shot 공부를 구조로 흡수

### 목표

공식 문서를 읽는 것을 “메모”가 아니라 “하네스 개선”으로 연결한다.

### 읽을 것

- Anthropic memory
- Anthropic hooks
- Anthropic subagents
- OpenAI prompting
- OpenAI tools
- OpenAI evals

### 해야 할 일

- 각 문서에서 "내 환경에 바로 적용할 수 있는 것"만 추출
- 적용 후보를 아래 세 레이어로 나누기
  - immediate
  - next week
  - later
- theoretical note가 아니라 concrete patch idea로 바꾸기

### 산출물

- `OFFICIAL_DOCS_NOTES.md`
- `APPLICABLE_PATTERNS.md`

### 완료 기준

- 읽은 문서가 starter pack 개선 항목으로 변환되어 있다
- “좋은 문서를 읽었다”가 아니라 “하네스가 바뀔 예정” 상태가 된다

## Day 5 — 자기 암묵지 입력 소스 맵 만들기

### 목표

`yourself-skill`과 `colleague-skill`을 참고해,
내 환경에서 자기 암묵지를 어디서 뽑을지 정한다.

### 분류 기준

- Work trace
- Memory trace
- Persona trace

### 후보 소스

- git history
- commit messages
- PR/issue-like 문서
- `.omx` plans/logs/state
- `.claude`
- `.opencode`
- README/docs
- task notes
- shell history
- tmp 문서들
- evaluations

### 해야 할 일

- 소스를 `Work / Memory / Persona`로 재분류
- 고가치 소스만 먼저 추리기
- low-noise / high-signal 소스를 우선순위화
- future-me recovery에 가장 도움이 되는 source 10개 선정

### 산출물

- `SELF_SIGNAL_MAP.md`
- `SOURCE_PRIORITY.md`

### 완료 기준

- “무엇을 먹여야 내 암묵지가 살아나는지”가 명확해진다
- 단순 수집이 아니라 해석 목적별 소스 구분이 끝난다

## Day 6 — `self-senpai` tiny MVP 설계

### 목표

지금까지 정리한 것을 바탕으로 작고 명확한 self-use MVP를 정의한다.

### MVP 질문

- 입력은 무엇인가?
- 출력은 무엇인가?
- verify는 무엇인가?
- 한 번 돌렸을 때 실제로 뭐가 편해지는가?

### 추천 MVP 형태

- 입력:
  - git history 일부
  - 최근 plans
  - 핵심 docs
  - shell/work notes 일부
- 출력:
  - `START_HERE.md`
  - `RUNBOOK.md`
  - `COMMON_FAILURES.md`
  - `NEXT_ACTIONS.md`
- 선택적 출력:
  - `AGENTS.generated.md`
  - `SELF_MEMORY.md`

### 해야 할 일

- MVP 범위 고정
- 제외 범위도 명시
- tiny flow 1개 정의
  - ingest
  - structure
  - save
  - readback
  - use

### 산출물

- `SELF_SENPAI_MVP.md`

### 완료 기준

- MVP가 과장 없이 1~2개의 flow로 설명된다
- 지금 바로 만들 수 있는 수준으로 작아졌다

## Day 7 — Runnable reference 만들기

### 목표

문서만이 아니라 실제로 돌아가는 reference 하나를 만든다.

### 형태

너무 크게 잡지 말고 아래 중 하나만 해도 된다.

- CLI 스크립트
- 단일 Python parser
- 단일 markdown generator
- tiny dashboard status page

### 최소 요구

- 입력 파일 읽기
- 구조화
- output 파일 저장
- readback
- smoke verification

### 산출물

- `reference/` 또는 `starter/examples/`
- 실제 실행 커맨드
- 결과 artifact 1세트

### 완료 기준

- starter pack이 종이 설계가 아니라 실제 runnable slice라는 증거가 생긴다
- “single-shot readiness”가 말이 아니라 구조로 보인다

## Daily Success Condition

매일 아래 중 최소 3개를 만족시킨다.

- 새 파일 1개 이상 생성
- 기존 하네스 문서 1개 이상 개선
- 실제 실행 또는 검증 1회 이상
- 다음날 작업 속도를 높여주는 artifact 생성
- canonical rule 1개 이상 고정

## End-Of-Week Review

7일 뒤 아래 질문에 답한다.

- 이제 새 프로젝트를 clean lane에서 시작할 수 있는가?
- starter pack이 실제 파일로 존재하는가?
- verify 루프가 문서가 아니라 명령 수준으로 존재하는가?
- 자기 암묵지 입력 소스가 정리되었는가?
- tiny MVP가 runnable 한가?
- future-me recovery가 개념이 아니라 artifact로 보이는가?

## Realistic Expectation

1주일 뒤 기대치는 아래가 맞다.

- single-shot 달인: 아니다
- single-shot 가능한 환경의 초석: 가능하다
- 하네스 체계화: 충분히 가능하다
- 자기 암묵지 기반 tiny MVP: 충분히 가능하다

즉 1주일은 “실력이 완성되는 시간”이 아니라
“실력이 빠르게 붙을 수 있는 구조를 만드는 시간”으로 보는 게 정확하다.
