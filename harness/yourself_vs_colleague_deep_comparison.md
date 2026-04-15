# yourself-skill vs colleague-skill Deep Comparison

기준 repo:

- `colleague-skill`: https://github.com/titanwings/colleague-skill
- `yourself-skill`: https://github.com/notdog1998/yourself-skill

## 한 줄 결론 먼저

- **업무 암묵지 추출 능력**은 `colleague-skill`이 더 강합니다.
- **개인 정체성/기억/자기모델 추출 능력**은 `yourself-skill`이 더 맞습니다.
- **네가 자기 데이터로 “미래의 나”를 만드는 목적**이라면, 가장 강한 조합은 사실 `yourself-skill`의 타깃 + `colleague-skill`의 구조입니다.

## 1. 암묵지를 “무엇으로 보느냐”에서 이미 둘이 다릅니다

`colleague-skill`은 암묵지를 주로 **업무 수행 방식**으로 봅니다.

- 어떤 시스템을 맡았는지
- 어떤 기준으로 CR 하는지
- 어떤 포맷을 강제하는지
- 어떤 흐름으로 문제를 푸는지
- 어떤 조직/직급/회사 문화에서 반응하는지

이걸 README와 `SKILL.md`에서 아예 `Work Skill + Persona` 이중 구조로 분리합니다.

Source:

- README: https://github.com/titanwings/colleague-skill/blob/main/README.md
- SKILL: https://github.com/titanwings/colleague-skill/blob/main/SKILL.md

`yourself-skill`은 암묵지를 **자기 기억 + 자기 성향**으로 봅니다.

- 내가 어떤 경험을 중요하게 기억하는지
- 어떤 말투로 반응하는지
- 어떤 감정 패턴이 있는지
- 어떤 가치관과 생활 습관을 가지는지
- 내가 나를 어떻게 해석하는지

즉 “일 잘하는 나”보다 “살아온 나/생각하는 나”를 먼저 복원합니다.

Source:

- README: https://github.com/notdog1998/yourself-skill/blob/main/README.md
- SKILL: https://github.com/notdog1998/yourself-skill/blob/main/SKILL.md

이 차이가 굉장히 큽니다.

`colleague-skill`은 **행동 가능한 업무 암묵지**, `yourself-skill`은 **자기모델 암묵지** 쪽입니다.

## 2. 업무 노하우 추출 능력은 `colleague-skill`이 더 세다

이건 거의 분명합니다.

이유:

- 입력 소스가 enterprise/work trace에 최적화되어 있습니다.
  - Feishu
  - DingTalk
  - Slack
  - email
  - docs
  - spreadsheets
  - screenshots
- 추출 라인이 처음부터 `work_analyzer -> work_builder`로 분리돼 있습니다.
- 생성 결과도 `work.md`와 `persona.md`로 나뉩니다.
- README가 역할/직급/회사문화 태그까지 적극적으로 받습니다.
- `SKILL.md`도 backend/frontend/ML/product/design에 따라 분석 포커스를 다르게 두게 설계돼 있습니다.

즉 이건 “그 사람이 어떤 인간인가?”보다
**“그 사람이 어떻게 일하는가?”를 복원하는 데 훨씬 잘 맞는 설계**입니다.

반면 `yourself-skill`은 업무 흔적도 먹일 수는 있지만, 기본 framing이 work twin이 아니라 self twin입니다.
그래서 업무 노하우, 리뷰 습관, 운영 체크리스트, 코딩 결정 패턴만 뽑아내는 능력은 구조상 `colleague-skill`보다 약합니다.

여기서 중요한 건 단순히 입력 소스가 많다는 게 아닙니다.
`colleague-skill`은 아예 **업무 노하우 추출을 위한 분업 구조**가 더 선명합니다.

- intake에서 동료의 회사/레벨/직무/성향을 먼저 잡습니다.
- source import 단계에서 enterprise trace를 우선 수집합니다.
- 그다음 분석이 `Work Skill`과 `Persona`로 갈라집니다.
- 최종적으로는 `Receive task -> Persona decides attitude -> Work Skill executes -> Output in their voice` 구조를 취합니다.

이 설계가 중요한 이유는, 많은 “사람 복제” 프로젝트가 결국 말투 imitation에 멈추는데,
`colleague-skill`은 처음부터 **태도와 업무 능력을 분리했다가 다시 합성**합니다.

즉 “그 사람처럼 말하는가?”가 아니라
**“그 사람이 어떤 근거와 습관으로 일을 처리하는가?”**를 중심에 놓습니다.

이게 업무 암묵지 추출기라는 평가의 핵심 근거입니다.

## 3. 자기 자신의 깊은 패턴 복원은 `yourself-skill`이 더 자연스럽다

여기서는 반대로 `yourself-skill`이 더 좋습니다.

이유:

- 입력으로
  - chat history
  - diaries
  - notes
  - photos
  - self-description
  를 전면에 둡니다.
- 출력도 `Self Memory + Persona` 구조입니다.
- README 예시도 단순 업무 답변이 아니라
  - 나의 감정
  - 나의 미루는 습관
  - 나의 기억
  - 나의 가치판단
  을 반영하는 식입니다.

즉 “미래의 나가 다시 돌아왔을 때 내가 어떤 사람인지 복구”하는 목적에는 `yourself-skill`이 더 맞습니다.
이건 네가 말한 `future-me recovery`, `self-senpai`, `personal tacit knowledge OS`와 더 가깝습니다.

여기서도 핵심은 입력 종류 자체보다 **해석의 중심축**입니다.

`yourself-skill`은 원자료를 다음 질문으로 읽습니다.

- 나는 무엇을 반복해서 말하는가
- 나는 어떤 기억을 중심으로 자신을 설명하는가
- 나는 압박을 받으면 어떤 정서 패턴을 보이는가
- 나는 나 자신을 어떤 narrative로 이해하는가

즉 이 프로젝트는 “직장인 twin”보다는
**자기 narrative와 자기 반응 구조를 보존하는 자기 복원 장치**에 더 가깝습니다.

이 차이 때문에 `yourself-skill`은 단순 자동화보다 아래 용도에 특히 강합니다.

- 미래의 나 onboarding
- 자기 회고
- 자기 말투 유지형 writing assistant
- personal memory prompt layer
- 자기판단 보정 장치

## 4. 자동 수집과 실전 파이프라인은 `colleague-skill`이 더 성숙해 보인다

공식 repo 기준으로 `colleague-skill`은 더 operational합니다.

보이는 것들:

- Claude Code / OpenClaw 설치 surface
- auto collectors
- browser/MCP/API 경로
- version backup / rollback
- generated skill directory
- update / correction / merge 루프

`yourself-skill`도 같은 패턴을 거의 계승하고 있고, `version_manager.py`도 실제로 있습니다.
하지만 현재로선 `colleague-skill`이 더 넓은 ingestion과 더 강한 “현업 투입” 감각을 갖고 있습니다.

그래서 **제품 하네스 성숙도**는:

- `colleague-skill`이 한 단계 위
- `yourself-skill`은 그 구조를 self-use에 맞게 안쪽으로 접은 버전

이라고 보는 게 맞습니다.

이 차이는 실제 파일 구조와 실행 경로에도 드러납니다.

`colleague-skill` 쪽:

- 생성 위치: `./colleagues/{slug}/`
- 핵심 파일:
  - `work.md`
  - `persona.md`
  - `meta.json`
  - `SKILL.md`
- 호출 surface:
  - `/{slug}`
  - `/{slug}-work`
  - `/{slug}-persona`
- 운영 기능:
  - append files
  - conversation correction
  - version archive
  - rollback

`yourself-skill` 쪽:

- 생성 위치: `./.claude/skills/{slug}/`
- 핵심 파일:
  - `self.md`
  - `persona.md`
  - `meta.json`
  - `SKILL.md`
- 호출 surface:
  - `/{slug}`
  - `/{slug}-self`
  - `/{slug}-persona`
- 운영 기능:
  - append memory
  - self-correction
  - version archive
  - rollback

즉 `yourself-skill`도 가벼운 장난 repo는 아닙니다.
하지만 operational 관점에서는 `colleague-skill`이 더 먼저 “현업 trace ingestion -> skillization”을 뚜렷하게 만들었고,
`yourself-skill`은 그 골격을 자기 자신 쪽으로 inward turn시킨 것입니다.

다시 말해:

- `colleague-skill`은 **조직 지식 복원용 파이프라인**
- `yourself-skill`은 **개인 지식 복원용 파이프라인**

입니다.

## 5. 실용성 전범위로 보면 둘의 쓰임새가 다릅니다

`colleague-skill`이 더 잘하는 일:

- 코드 리뷰 스타일 복원
- 운영/인수인계 노하우 복원
- 팀의 암묵 규칙 복원
- 특정 역할자의 의사결정 방식 재현
- “이 사람이면 이 상황에서 어떻게 할까?”에 답하는 것

`yourself-skill`이 더 잘하는 일:

- 미래의 나 onboarding
- 자기 생각/기억/감정 패턴 복구
- 자기 톤으로 글쓰기/대화하기
- 자기 의사결정 성향 되짚기
- 개인 자동화 에이전트의 persona layer 만들기

즉:

- **업무 실행성** 중심이면 `colleague-skill`
- **자기 복원성** 중심이면 `yourself-skill`

이걸 더 세게 말하면 아래처럼 나뉩니다.

`colleague-skill`의 실용성은
**“지금 당장 팀의 손실을 막는 것”**에 있습니다.

- 사람 빠진 뒤 빈자리 메우기
- 리뷰/운영/의사결정 스타일 복원
- 인수인계 문서가 짧을 때 gap 메우기
- 신규 담당자에게 “이 사람이라면 어떻게 했을까”를 주는 것

`yourself-skill`의 실용성은
**“지금 당장 미래의 나를 덜 불편하게 만드는 것”**에 있습니다.

- 며칠 후 다시 돌아온 나 복구
- 프로젝트 톤과 판단 일관성 유지
- 개인 runbook 자동화
- self-onboarding
- 기억을 prompt layer로 끌어올리기

그래서 전범위 실용성이라는 관점에서는:

- 팀 협업, 오프보딩, 조직 지식: `colleague-skill`
- 개인 생산성, 자기복원, personal automation: `yourself-skill`

## 6. 네 목적에 딱 맞춰 말하면

네가 원하는 건 단순히 “내 말투 흉내”가 아니라

- 내 작업 흔적
- 내 노하우
- 내 암묵적 판단 기준
- 미래의 나를 위한 복구성

이죠.

그 기준이면 `yourself-skill`이 방향은 더 맞습니다.
그런데 **실제 추출 성능과 운영 구조는 `colleague-skill` 쪽이 더 강합니다.**

그래서 가장 날카로운 결론은 이겁니다:

네가 진짜 만들고 싶은 건
**`yourself-skill`의 목적을 가진 `colleague-skill`형 하네스**입니다.

즉:

- 대상은 `나`
- 하지만 구조는
  - Work layer
  - Memory layer
  - Persona layer
  - Update / correction
  - Version rollback
- Multi-source ingestion

으로 가져가는 게 맞습니다.

여기서 특히 중요한 건,
네 목적은 “나처럼 말하는 에이전트” 하나가 아니라
**“미래의 나도 바로 복구되고, 내 판단 기준도 다시 불러오고, 내 작업방식도 재가동되는 시스템”**이라는 점입니다.

그 기준이면 `yourself-skill`만 쓰면 자기 narrative 쪽은 좋지만 업무 spine이 약하고,
`colleague-skill`만 쓰면 업무 spine은 강하지만 자기복원감이 떨어집니다.

그래서 네 목적을 제대로 만족시키는 설계는 단순 선택이 아니라 조합입니다.

- `yourself-skill`이 주는 것:
  - self-targeting
  - 자기 기억 복원
  - 자기 서사/감정 패턴 복원
- `colleague-skill`이 주는 것:
  - operational pipeline
  - 업무 암묵지 추출 구조
  - work/persona 분업 설계
  - update/correction/versioning spine

이 둘을 합쳐야 비로소 네가 말한
`future-me recovery harness`
`self-senpai`
`personal tacit knowledge OS`
에 가까워집니다.

## 최종 판단

- `colleague-skill`은 “업무 암묵지 추출기”로 더 강하다
- `yourself-skill`은 “자기 복원기”로 더 적합하다
- 네 실사용 MVP는 `yourself-skill` 단독보다
  **`self-colleague-skill` 혹은 `self-senpai` 형태의 하이브리드**가 가장 유망하다

## 추가 근거

`colleague-skill`은 README만 있는 repo가 아니라, 실제 installable skill entrypoint와 versioned rollback pipeline이 있습니다.

- `SKILL.md`는 실제 Claude Code skill frontmatter를 가집니다.
  - https://raw.githubusercontent.com/titanwings/colleague-skill/main/SKILL.md
- repo 구조도 `prompts/`, `tools/`, `colleagues/`, `docs/PRD.md`, `requirements.txt`를 갖춘 실제 skill pipeline입니다.
  - https://github.com/titanwings/colleague-skill/blob/main/README.md
- `version_manager.py`는 backup, rollback, cleanup, list를 지원하고, 최대 10개 버전을 관리합니다.
  - https://raw.githubusercontent.com/titanwings/colleague-skill/main/tools/version_manager.py

`yourself-skill`도 self-use 방향으로 이 구조를 상당 부분 계승합니다.

- `SKILL.md`는 `create-yourself` skill로 정의되어 있고, `Read, Write, Edit, Bash`를 허용합니다.
  - https://raw.githubusercontent.com/notdog1998/yourself-skill/main/SKILL.md
- 생성 위치도 Claude Code 기준 `./.claude/skills/{slug}/`로 명확히 고정합니다.
- `version_manager.py`도 실제로 backup / rollback / list를 지원합니다.
  - https://raw.githubusercontent.com/notdog1998/yourself-skill/main/tools/version_manager.py

즉 둘 다 실체가 있지만, 방향성이 다릅니다.

- `colleague-skill`: 업무 역할자 복원
- `yourself-skill`: 자기 자신 복원

네 목적이 “내 작업 지식 + 내 판단 + 미래의 나 복구”라면,
결국 가장 강한 설계는 아래입니다.

- `colleague-skill`의 operational spine
- `yourself-skill`의 self-targeting
- 여기에 네 환경의 `future-me recovery harness`를 얹는 방식

추가로, `yourself-skill`은 단순히 “나를 흉내내는 챗봇”으로 끝내지 않고,
생성 결과를 Claude Code skill 디렉터리인 `./.claude/skills/{slug}/`에 직접 심는다는 점도 중요합니다.

이 말은 곧:

- 결과물이 그냥 분석 리포트가 아니라
- **바로 호출 가능한 agent surface**라는 뜻입니다.

반면 `colleague-skill`은 generated skill을 `./colleagues/{slug}/`에 두고,
이후 `/{slug}`, `/{slug}-work`, `/{slug}-persona`로 나누어 호출하는 흐름을 전제로 합니다.

즉 둘 다 “문서 생성기”가 아니라
**실행 가능한 skill artifact 생성기**라는 공통점이 있습니다.

이 공통점 때문에, 네가 이걸 참고해 만들 때도
최종 산출물은 메모나 리포트가 아니라
바로 호출 가능한 `self-senpai skill`이 되어야 합니다.

## 최종 요약

짧게 말하면:

- `colleague-skill`은 **일을 잘하는 사람의 업무 암묵지**를 뽑아내는 데 더 좋다
- `yourself-skill`은 **나라는 사람의 기억/성향/표현 패턴**을 복원하는 데 더 좋다
- 네가 원하는 건 둘 중 하나가 아니라, **둘의 장점을 합친 self-use 하이브리드**다
