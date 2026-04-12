# 1DEX Mainnet Screening Handoff

작성일: 2026-04-12

## 목적

이 문서는 `2dex` 팀이 current `1DEX` 레인을 이어받을 때
무엇을 historical reference 로 보고, current head 가 어디까지 왔는지
짧게 잡기 위한 handoff note 다.

## Historical commit screening result

current mainnet 에서 아래 후보들을 같은 방식으로 다시 봤다.

- startup truth
- `100 USD / 1-cycle BUILD probe`
- post-check flatness

screened commits:

- `7e11a6f`
- `c4f7c75`
- `0c93e82`
- `3b483fe`
- `9c3be2b`
- `4ff3ae2`
- `43b36fb`
- `93bdfce`

### winner

- `c4f7c75`

이유:

- startup truth sane
- BUILD order placement reached
- `POST_ONLY -> IOC fallback` 경로로 current mainnet `1-cycle completion` reached
- post-check flat `ETH=0.0`, `SOL=0.0`

주의:

- 이건 `historical first anchor`지 direct production baseline 은 아니다
- `UNWIND POSITIONS BEFORE: ETH=0.0, SOL=0.0` 같이 close-state truth 는 여전히 수상하다

### explicit rejects

- `3b483fe`
  - current mainnet startup WS truth mismatch
  - same account probe 에서 `SOL=-12.9` bogus position
- `43b36fb`
  - startup truth sane
  - but current market 에서 `ENTRY_TIMEOUT_BELOW_THRESHOLD`
- `7e11a6f`
  - current env import surface mismatch

### middle candidates

- `4ff3ae2`
  - build-friendly
  - but `no-fill + flat -> retry re-entry`
- `9c3be2b`
  - build-friendly
  - but `no-fill + flat -> retry re-entry`
- `0c93e82`
  - build-friendly
  - but no-fill 후 바로 bot stop

## Current head result

current head 는 `c4f7c75`보다 startup / WS truth 쪽이 더 낫다.

kept:

- `WS warmup + REST 1회 seed`
- `fill` 기반 position truth
- `position_change.amount` 는 diagnostic-only

최근 실전에서 추가로 고친 것:

- `no-fill + flat` -> `clean skip`
- `one-leg fill -> emergency unwind -> actual flat` -> `unwind_recovered_flat`
- `unwind_recovered_flat` 이후 BUILD retry 재진입 금지
- `WS unhealthy + REST flat` 이면 stale WS cache 를 REST 값으로 sync

이 결과 current mainnet `3-cycle` 은 끝까지 갔다.

하지만 패턴은 아래였다.

- cycle 1: one-leg -> unwind recovered flat
- cycle 2: one-leg -> unwind recovered flat
- cycle 3: one-leg -> unwind recovered flat

즉:

- infra survival / flat recovery 는 좋아졌다
- build quality / paired fill viability 는 아직 낮다

## What to keep

1. historical reference
   - `c4f7c75`
2. current infra baseline
   - current head
3. reading rule
   - `c4f7c75`에서 build completion 흐름을 읽고
   - current head 에 startup / truth / recovery improvements 를 유지한 채 흡수

## Next priority

다음 우선순위는 하나다.

- `paired fill viability`

구체적으로:

1. one-leg 발생 자체를 줄이는 build-side 개선
2. `POST_ONLY -> IOC fallback` 같은 `c4f7c75` build completion 흐름을 current head 에서 재해석
3. 3-cycle 이후에는 `healthy paired fill` 비율을 올리는 쪽으로 이동

## One sentence summary

`c4f7c75`는 historical first anchor, current head 는 infra baseline, 다음 과제는 entry quality 다.
