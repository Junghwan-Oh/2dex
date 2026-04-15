# Ralphton Single-Shot Harness

## Purpose

이 문서는 짧은 시간 안에 agent-native 프로젝트를 끝까지 밀어붙이는 방법을 정리한 실전 메모다.

핵심 생각은 이것이다.

- 좋은 single-shot은 좋은 프롬프트보다 좋은 harness에서 나온다.
- 거대한 마법 프롬프트 하나로 끝내려 하지 않는다.
- 역할 분리, 파일 계약, 저장 규칙, 검증 루프를 먼저 만든다.
- 아주 짧은 루프로 vertical slice를 계속 완성한다.
- 문서, skill, hook, agent spec 자체를 제품 하네스의 일부로 본다.

이 문서는 특히 PolySona 같은 사례에서 읽히는 작업 흔적을 바탕으로 정리했다.

## What Single-Shot Really Means

겉으로는 "한 번에 나온 프로젝트"처럼 보여도 실제로는 보통 아래 패턴이다.

1. 문제 정의를 아주 빠르게 고정한다.
2. 상위 운영 계약을 먼저 쓴다.
3. 역할을 여러 agent/skill로 나눈다.
4. 출력물 저장 형식을 고정한다.
5. vertical slice 하나를 바로 runnable 하게 만든다.
6. `feat -> fix -> polish -> docs`를 매우 짧게 반복한다.

즉 single-shot은 보통 "한 번에 완성"이 아니라 "운영 루프를 너무 잘 설계해서 짧은 시간에 반복한 것"이다.

## Evidence Pattern From PolySona-Style Builds

다음 흔적이 있으면 대체로 잘 만든 harness-driven 프로젝트다.

- 상위 운영 문서가 있다.
  - `AGENTS.md`
  - `CLAUDE.md`
- 역할이 agent spec으로 분리돼 있다.
  - `profiler`
  - `trendsetter`
  - `content-writer`
  - `virtual-follower`
  - `admin`
- skill마다 입력과 출력 계약이 있다.
- 파일 저장 위치와 재검증 규칙이 있다.
- hook이 있다.
  - session start context preload
  - destructive write warning
  - slop detection
- 커밋이 큰 덩어리 한 방이 아니라 촘촘한 slice 단위로 쌓인다.

## Core Principles

### 1. Facts First

- 추측보다 확인을 우선한다.
- repo에서 읽을 수 있거나 API로 확인할 수 있으면 먼저 확인한다.
- 확실하지 않은 주장은 문서에 적지 않는다.

### 2. Output Contracts First

- "좋은 결과를 만들어"가 아니라
- "어디에 저장하고, 어떤 포맷으로 쓰고, 다시 읽어 확인해라"를 먼저 고정한다.

### 3. File-Backed State

- 세션 기억을 모델 컨텍스트에만 의존하지 않는다.
- 파일을 진짜 상태 저장소로 쓴다.
- Markdown, JSON, YAML 중 하나를 SSOT로 고정한다.

### 4. Roles Beat Giant Prompts

- 하나의 에이전트가 전부 잘하길 기대하지 않는다.
- 인터뷰, 생성, QA, 배포, 상태 확인을 분리한다.

### 5. Vertical Slice Over Big Plan

- 전체 시스템 완성보다
- "작동하는 한 줄"을 먼저 만든다.
- 예:
  - 인터뷰 1개
  - persona 1개 저장
  - QA 1개 실행
  - 대시보드 1개 표시

### 6. Verification Is Part of the Product

- 빌드가 되는지
- 파일이 실제 생성됐는지
- API가 응답하는지
- 동일 입력에 재현되는지

이것까지 포함해서 제품이다.

## Canonical Build Loop

1. One-line thesis를 쓴다.
2. 상위 운영 계약 문서를 쓴다.
3. 역할을 3~5개로 나눈다.
4. 역할별 skill을 만든다.
5. hook으로 guardrail을 둔다.
6. 저장 포맷을 고정한다.
7. vertical slice 하나를 runnable 하게 만든다.
8. QA/eval을 돌린다.
9. 작은 커밋으로 정리한다.
10. 다시 다음 slice로 간다.

## Harness Components

## 1. AGENTS.md

이 문서는 프로젝트의 운영 계약이다.

반드시 들어가야 할 것:

- 목표
- 역할
- source of truth 파일
- 검증 규칙
- stop condition
- anti-pattern

### Minimal AGENTS.md Skeleton

```md
# Project Name

## Goal
- 이 프로젝트가 해결하는 핵심 문제

## Roles
- researcher
- generator
- qa
- publisher

## Source Of Truth
- data/persona.md
- content/drafts/
- reports/qa/

## Execution Rules
- Read before write
- Save outputs to file
- Re-read saved outputs
- Do not claim success without verification

## Verification
- build passes
- file exists
- API responds
- smoke path works

## Stop Conditions
- runnable slice exists
- verification evidence collected
```

## 2. Skills

skill은 workflow command다.

좋은 skill은:

- 역할이 좁다
- 입력이 분명하다
- 출력 위치가 분명하다
- 저장 검증이 있다

### Minimal Skill Skeleton

```md
---
name: qa
description: Evaluate latest generated artifact
agent: qa-runner
---

# Protocol

- Read the latest draft from `content/drafts/`
- Evaluate it using the defined rubric
- Save the report to `content/qa/YYYY-MM-DD-slug.md`
- Re-read the saved file
- Return the confirmed saved path
- If save or re-read fails, report failure
```

## 3. Agent Specs

agent spec은 역할 prompt를 파일로 고정한 것이다.

반드시 들어가야 할 것:

- mission
- mandatory workflow
- non-responsibilities
- file contracts
- verification rule

### Minimal Agent Spec Skeleton

```md
---
name: content-writer
description: Generate drafts from persona + trend
tools:
  - Read
  - Write
---

# Role
- Generate exactly 3 variations
- Save before answering

# Workflow
1. Read persona source files
2. Generate drafts
3. Save to `content/drafts/`
4. Re-read saved file
5. Return confirmed path

# Non-Responsibilities
- Do not publish
- Do not invent source data
```

## 4. Hooks

hook은 품질과 일관성을 강제하는 가장 값싼 장치다.

추천 3종:

- SessionStart
- PreToolUse
- PostToolUse

### SessionStart Hook Purpose

- active context preload
- current persona or workspace summary 표시
- 핵심 rules reminder

### PreToolUse Hook Purpose

- write 전에 read 안 했으면 경고
- source-of-truth overwrite 위험 경고
- destructive command 경고

### PostToolUse Hook Purpose

- slop 표현 감지
- output contract 누락 감지
- 저장 실패 후 성공처럼 말하는 패턴 차단

### Minimal Hook Skeleton

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Load context / validate write / detect slop"
```

## 5. Data Contracts

데이터 구조를 빨리 고정할수록 single-shot 확률이 올라간다.

좋은 데이터 계약의 조건:

- 사람이 읽을 수 있다
- 모델이 다시 읽을 수 있다
- append-only가 가능하다
- 한 파일의 역할이 명확하다

추천 구조:

- `persona.md`
- `nuance.md`
- `accounts.md`
- `content/drafts/`
- `content/qa/`
- `content/published/`

## Single-Shot Project Layout Template

```text
project/
  AGENTS.md
  CLAUDE.md
  skills/
    interview/
      SKILL.md
    content/
      SKILL.md
    qa/
      SKILL.md
    publish/
      SKILL.md
  agents/
    profiler.md
    content-writer.md
    qa-runner.md
    publisher.md
  hooks/
    hooks.json
    session-start.sh
    pre-tool-use.sh
    post-tool-use.sh
  personas/
    default/
      persona.md
      nuance.md
      accounts.md
  content/
    drafts/
    qa/
    published/
  server/
  client/
```

## Single-Shot Execution Protocol

## Phase 1. Freeze The Thesis

문장 하나로 끝내라.

예:

- "심층 인터뷰로 추출한 persona를 여러 AI agent surface에 이식한다"
- "트레이딩 전략 log를 agent가 읽고, 요약하고, 검증하고, 리포트한다"

이 문장이 흔들리면 single-shot이 안 된다.

## Phase 2. Freeze The Files

초기에 꼭 정할 것:

- 어디에 저장할지
- 무엇을 저장할지
- 누가 읽을지
- 누가 쓸지

## Phase 3. Split Roles

역할은 보통 3~5개가 적당하다.

- interview / profile
- generate
- qa
- publish
- status/export

## Phase 4. Build One Runnable Slice

가장 먼저 만들어야 할 건 전체 제품이 아니라 한 줄짜리 실사용 흐름이다.

예:

1. persona 파일 읽기
2. draft 생성
3. qa 저장
4. status page 노출

## Phase 5. Commit In Tiny Slices

좋은 single-shot commit rhythm:

- `feat(slice): ...`
- `fix(contract): ...`
- `fix(polish): ...`
- `docs(sync): ...`

한 커밋은 "사용자 입장에서 무엇이 하나 더 가능해졌는가" 기준으로 나눈다.

## Recommended Commit Rhythm

```text
feat(api): expose minimal endpoint
feat(page): render the endpoint
feat(save): persist output to file
fix(contract): align stored format
fix(polish): improve empty state / errors
docs(sync): update instructions
```

## Anti-Patterns

- giant prompt 하나에 모든 역할을 몰아넣기
- 저장 계약 없이 채팅 출력만 믿기
- build/test 없이 "대충 됐다" 하고 넘어가기
- deterministic mock인데 AI intelligence처럼 포장하기
- 대시보드만 먼저 만들고 core artifact가 없는 상태
- source-of-truth 파일을 append-only로 설계하지 않기
- repo에 남는 운영 계약 없이 감으로 반복하기

## How To Actually Get Good At This

실력은 프롬프트 암기에서 오지 않는다.

실제로 필요한 능력:

### 1. Problem Compression

큰 아이디어를 1문장으로 줄이는 능력.

### 2. Contract Design

입출력 파일, 저장 위치, 검증 단계를 빠르게 정하는 능력.

### 3. Role Decomposition

하나의 큰 태스크를 3~5개의 agent lane으로 나누는 능력.

### 4. Loop Discipline

2분~10분 단위 루프로 계속 `feat/fix/verify`를 돌리는 능력.

### 5. Honest Verification

"모형적으로 될 것 같다"가 아니라 실제로 build, run, readback, API response를 확인하는 습관.

## Recommended Reading Order

### Anthropic First For Harness Operations

하네스 운영 관점에서는 Anthropic 문서가 더 직접적이다.

1. Claude Code memory
   - https://docs.anthropic.com/en/docs/claude-code/memory
2. Claude Code hooks guide
   - https://docs.anthropic.com/en/docs/claude-code/hooks-guide
3. Claude Code hooks reference
   - https://docs.anthropic.com/en/docs/claude-code/hooks
4. Claude Code slash commands
   - https://docs.anthropic.com/en/docs/claude-code/slash-commands
5. Claude Code subagents
   - https://docs.anthropic.com/en/docs/claude-code/sub-agents
6. Prompt engineering overview
   - https://docs.anthropic.com/en/docs/prompt-engineering
7. Define your success criteria
   - https://docs.anthropic.com/en/docs/test-and-evaluate/define-success
8. Create strong empirical evaluations
   - https://docs.anthropic.com/en/docs/build-with-claude/develop-tests

### OpenAI For Agent Quality, Tools, And Evals

에이전트 품질, tool usage, eval workflow는 OpenAI 문서가 좋다.

1. Prompting guide
   - https://platform.openai.com/docs/guides/prompting
2. Responses API
   - https://platform.openai.com/docs/api-reference/responses
3. Tools guide
   - https://platform.openai.com/docs/guides/tools
4. Conversation state
   - https://platform.openai.com/docs/guides/conversation-state?api-mode=responses
5. Agents guide
   - https://platform.openai.com/docs/guides/agents
6. Agents SDK
   - https://platform.openai.com/docs/guides/agents-sdk/
7. Agent evals
   - https://platform.openai.com/docs/guides/agent-evals
8. Evaluation best practices
   - https://platform.openai.com/docs/guides/evaluation-best-practices
9. Working with evals
   - https://platform.openai.com/docs/guides/evals?api-mode=responses
10. Model optimization
   - https://platform.openai.com/docs/guides/fine-tuning
11. Model Spec
   - https://model-spec.openai.com/2025-10-27

## Practical Reading Strategy

문서를 읽는 순서는 이렇게 하는 게 좋다.

1. Anthropic memory
2. Anthropic hooks
3. Anthropic subagents
4. OpenAI prompting
5. OpenAI tools
6. OpenAI evals
7. OpenAI model spec

즉:

- 하네스는 Anthropic
- 품질과 eval은 OpenAI

## Minimal Ralphton Template Pack

### Template A. Project One-Liner

```md
Project thesis:
<who>를 위해 <artifact>를 <agent harness>로 생성/검증/운영한다.
```

### Template B. Success Criteria

```md
Success criteria:
- one runnable vertical slice exists
- one artifact is saved to disk
- one QA or eval pass exists
- one status surface exists
- same request can be reproduced
```

### Template C. Vertical Slice Checklist

```md
- thesis fixed
- source files fixed
- one skill created
- one agent created
- one hook created
- one output file saved
- one readback verified
- one build or API check passed
```

### Template D. Build Day Operating Notes

```md
Build-day rules:
- no giant redesign mid-flight
- no speculative abstractions
- every slice must end with verification
- if output is not saved, it does not exist
- if API does not respond, feature is not done
```

## Evidence That PolySona Was Built Harness-First

오늘 확인한 근거:

### 1. Top-Level Operating Contracts

- `AGENTS.md`
- `CLAUDE.md`

여기에 철학, context loading, source-of-truth, no-speculation 규칙이 박혀 있다.

### 2. Role Split

분리된 역할:

- `profiler`
- `trendsetter`
- `content-writer`
- `virtual-follower`
- `admin`

이건 giant prompt가 아니라 role-based harness 설계라는 신호다.

### 3. Skill Contracts

각 skill은 단순 명령 alias가 아니라 아래를 강제한다.

- 어떤 파일을 읽을지
- 어떤 artifact를 만들지
- 어디에 저장할지
- 저장 후 다시 읽어 검증할지

### 4. Hooks

실제 hook이 들어 있다.

- session start: active persona summary preload
- pre-tool-use: persona overwrite warning
- post-tool-use: AI slop detection

### 5. Codex Skill Sync Surface

`scripts/sync-codex-skills.mjs`가 있어서 `skills/`를 `.agents/skills/`에 미러링하도록 설계되어 있다.

이건 "프롬프트"가 아니라 "운영 표면"을 repo에 고정한 것이다.

### 6. Slide-Level Process Disclosure

발표 자료에 아예 다음이 적혀 있다.

- stack: oh-my-openagent, Codex, Claude Code
- process: `ralph-loop with ulw`

즉 운영 방식 자체를 제품 경쟁력의 일부로 보고 있다.

### 7. Commit Rhythm

커밋 패턴도 힌트다.

- `feat(api)`
- `feat(pages)`
- `feat(qa)`
- `fix(polish)`
- `docs(sync)`

이런 식의 짧은 slice 반복이 같은 날짜에 촘촘히 이어진다.

따라서 single-shot처럼 보여도 실제론 "짧은 반복 루프를 강하게 운영한 결과"일 가능성이 높다.

## What To Learn From That Pattern

배워야 할 건 "그때 무슨 마법 프롬프트를 쳤는가"보다 아래다.

### 1. Operating Contracts Before Code

코드보다 먼저 아래를 쓴다.

- 역할
- 저장 위치
- 출력 계약
- 검증 규칙

### 2. Roles Before Features

기능 목록보다 먼저 역할 분리를 고정한다.

- research
- generate
- qa
- publish
- export/status

### 3. Contracts Before UI

UI보다 먼저 아래가 있어야 한다.

- saved artifact
- deterministic file path
- readback verification

### 4. Verification Before Narrative

"AI product"라고 부르기 전에 실제로 확인한다.

- build pass
- server run
- API response
- readback
- reproducibility

## Practical Advice For Building Your Own Single-Shot Project

만약 비슷한 방식으로 프로젝트를 만들고 싶다면 아래 순서가 좋다.

1. 프로젝트 one-liner를 먼저 쓴다
2. `AGENTS.md`를 먼저 쓴다
3. 역할 3~5개를 나눈다
4. role별 skill 1개씩 만든다
5. source-of-truth 파일 포맷을 정한다
6. hook 2~3개를 붙인다
7. vertical slice 하나를 끝까지 연결한다
8. 실제로 돌려보고 증거를 남긴다
9. `feat -> fix -> polish -> docs` 리듬으로 커밋한다

## Minimal Build-Day Checklist

```md
- thesis fixed
- AGENTS written
- 3-5 roles defined
- 3-5 skills defined
- 2-3 hooks defined
- one source-of-truth format fixed
- one vertical slice runs
- one artifact saved and re-read
- one API or UI surface verified
- one eval or QA pass exists
- commit rhythm maintained
```
