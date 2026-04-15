# Single-Shot Readiness Todo

## Purpose

이 문서는 현재 `dexbot` 환경에서 single-shot 방식으로 프로젝트를 밀 수 있을 정도의 하네스 성숙도를 만들기 위한 우선순위 문서다.

이 문서는 방법론 설명이 아니라 실행용 todo 문서다.

## Current Diagnosis

현재 상태에서 바로 single-shot을 기대하기 어려운 이유는 아래와 같다.

- 루트 작업트리가 과도하게 오염되어 있다.
- 루트 수준의 `AGENTS.md`가 없다.
- `harness/`에는 방법론 문서만 있고 starter pack이 없다.
- `.claude`, `.omc`, `.opencode`, `.bmad-core` 등 orchestration surface가 공존하지만 canonical flow가 없다.
- 루트 공통 verify entrypoint가 없다.

즉 지금은 "잘 만드는 프롬프트"보다 먼저 "작업 환경을 오염 없이 시작하는 구조"가 필요한 상태다.

## Urgent + Important Top 3

### 1. Clean Lane 분리

가장 먼저 해야 할 일은 깨끗한 실행 lane을 만드는 것이다.

해야 할 것:

- `clean worktree` 기반으로 시작
- harness 전용 브랜치 규칙 만들기
- 실험용 lane과 제품 lane 분리
- 하네스용 starter 디렉터리 고정

완료 기준:

- 새 작업을 항상 오염 없는 worktree에서 시작할 수 있다
- "방법론 문서"와 "실제 제품 코드"가 섞이지 않는다

### 2. Canonical Starter Pack 만들기

문서만 있으면 안 된다. 복붙 가능한 실제 starter pack이 필요하다.

최소 구성:

- `AGENTS.md`
- `skills/`
- `hooks/`
- `personas/default/`
- `content/{drafts,qa,published}/`
- `VERIFY.md`

완료 기준:

- 새 프로젝트를 시작할 때 starter pack을 그대로 복사해 시작할 수 있다
- 역할, 저장 위치, 검증 루프가 기본으로 깔린다

### 3. 공통 Verification Path 만들기

single-shot은 빠른 생성이 아니라 빠른 검증이 핵심이다.

최소 verify path:

- artifact 생성
- readback
- smoke run
- API or UI 확인
- eval or QA 1회

완료 기준:

- 모든 새 프로젝트가 같은 verify flow를 따른다
- "만들었다"와 "증명했다"가 분리되지 않는다

## Mid-Term Top 10

아래 10개를 위에서부터 순서대로 처리하는 것이 좋다.

### 1. Create clean harness lane

- `harness/starter/` 또는 별도 clean worktree 규칙 만들기
- dirty repo 위에서 직접 시작하지 않기

### 2. Add root harness contract

- 루트 수준 `AGENTS.md` 또는 동등한 운영 계약 추가
- source-of-truth, read-before-write, verify-first 원칙 고정

### 3. Build starter pack files

- 실제 starter pack 디렉터리 생성
- 템플릿이 아니라 실행 가능한 파일 묶음으로 만들기

### 4. Normalize file contracts

- persona/data/content/report 경로 표준화
- append-only와 canonical owner 문서 원칙 적용

### 5. Normalize role split

- 최소 역할 세트 고정
  - research/interview
  - generate
  - qa
  - publish
  - status/export

### 6. Add hook guardrails

- SessionStart
- PreToolUse
- PostToolUse

목표:

- context preload
- overwrite warning
- slop warning

### 7. Add one universal verify entrypoint

- `VERIFY.md`만으로는 부족할 수 있다
- 가능하면 `make verify`, `just verify`, `bun run verify`, `python -m ...` 중 하나로 통일

목표:

- build
- smoke
- artifact check
- readback

### 8. Add one small runnable reference project

starter pack이 실제로 유효한지 보이려면 tiny reference가 필요하다.

예:

- persona -> draft -> qa -> status page

목표:

- 새 하네스가 종이 설계가 아니라 실제 runnable slice임을 증명

### 9. Define commit rhythm and branch hygiene

- `feat(slice)`
- `fix(contract)`
- `fix(polish)`
- `docs(sync)`

목표:

- single-shot처럼 보여도 내부적으로는 짧은 루프를 유지
- dirty branch로 오래 끌지 않기

### 10. Add eval discipline

최소 eval 기준:

- 같은 입력에서 같은 결과가 나오는지
- 저장된 artifact가 다시 읽히는지
- QA가 실제 판단인지 mock인지 분리되는지

목표:

- 데모와 진짜 runtime을 혼동하지 않기

## To-Do Path To Single-Shot

single-shot readiness까지의 실행 순서는 아래가 권장된다.

### Phase 1. Stabilize the environment

1. clean lane 만들기
2. root harness contract 만들기
3. starter pack 만들기

### Phase 2. Stabilize execution

4. file contracts 표준화
5. role split 고정
6. hooks 추가
7. universal verify entrypoint 추가

### Phase 3. Prove the harness

8. tiny runnable reference 만들기
9. commit rhythm 고정
10. eval discipline 추가

## Single-Shot Readiness Criteria

아래 조건이 충족되면 single-shot 방식으로 밀 수 있는 최소 준비가 된 것이다.

- 새 프로젝트를 clean lane에서 시작할 수 있다
- starter pack을 복사해 바로 시작할 수 있다
- 역할, 저장 위치, 검증 흐름이 이미 정의돼 있다
- 최소 한 개 reference project가 실제로 돌아간다
- verify path가 공통 명령으로 실행된다
- 산출물 생성과 검증이 분리되지 않는다

## Weekly Review Checklist

매주 아래 질문으로 점검한다.

- 새 프로젝트를 시작할 때 매번 구조를 다시 고민하는가?
- source-of-truth 파일이 흔들리는가?
- dirty branch 위에서 그냥 작업하는가?
- verify가 사람 머릿속에만 있고 명령으로 고정되지 않았는가?
- hooks가 없어서 같은 실수를 반복하는가?
- starter pack이 실제로 복사 가능한가?

질문 중 2개 이상이 `yes`면 아직 single-shot readiness가 부족한 상태다.
