# Effective Prompting Examples - November 14, 2025

**Session**: Technical Problem Solving with Critical Feedback
**Context**: Real money trading bot development ($190-5,000 capital)
**Outcome**: Improved from 4.5/10 → 6.5/10 through guided research

---

## 🎯 What Made This Session Effective

### User's Prompting Strategy

**Pattern**: Challenge → Guide → Challenge → Evaluate

This created a learning loop that forced deeper thinking and better solutions.

---

## 📚 Effective Prompts (Chronological)

### 1. Initial Challenge - Forcing Deeper Research

**Context**: I suggested quick synthetic balance fix

**User Prompt**:
```
'ETH balance is too low' Error 해결은 허밍봇의 perpetuals에 이미 완성된 솔루션 있지 않았을까?
지금 해결방식은 또다른 시행착오 일 수도 있어.
최대한 허밍봇의 오픈소스를 이용하는 방식으로 하라고 좀. 이걸 다시 검토해봐.
```

**Translation**:
"Isn't there already a complete solution for the 'ETH balance too low' error in Hummingbot's perpetuals? The current solution might be another trial and error. Use Hummingbot's open source approach as much as possible. Re-examine this."

**Why It Worked**:
- ❌ Didn't accept first solution
- ✅ Challenged assumption ("there must be a proper solution")
- ✅ Directed where to look ("Hummingbot's open source")
- ✅ Implied expectation ("re-examine" = go deeper)

**Result**: 3 hours of deep research instead of 15 minutes quick fix

---

### 2. Specific Technical Questions - Testing Understanding

**User Prompt**:
```
1. 문제의 근본 원인
- DerivativeBase = 옛날 Derivative 커넥터 기반 클래스 (더 이상 사용 안함)
- PerpetualDerivativePyBase = 새로운 Perpetual 커넥터 기반 클래스
=> 이건 DerivativeBase 대신 PerpetualDerivativePyBase 이걸로 교체하면 되는건가?
   허밍봇이 이건 오픈소스에 UPDATE 안해놨음?

2. 허밍봇의 불일치 발견
perpetual_budget_checker.py (Line 23):
if not isinstance(exchange, (PerpetualTrading, PerpetualDerivativePyBase)):
→ PerpetualDerivativePyBase를 올바르게 인식
strategy_base.pyx (Line 278):
if not isinstance(market, DerivativeBase): # 옛날 클래스만 체크!
→ PerpetualDerivativePyBase를 인식 못함 (오래된 코드)
=> 이건 어떻게 해결해야 하는건가?

3. synthetic balance
이건 USDT만 보여주는게 아니라, USDT, ETH 모두 보여주는건가?

4. 왜 허밍봇도 역사도 오래되고, 유료강좌도 현재도 있으며, 업데이트도 활발한데
   PERPS라는게 나온지도 오래됐는데, 이런 기초적인 것도 제대로 구현안되서
   오픈소스 자체를 수정해야만 해? 너가 잘못 리서치한 거 아냐?
```

**Why It Worked**:
- ✅ Listed specific code references (Line 23, Line 278)
- ✅ Pointed out contradictions in my explanation
- ✅ Asked "why would a mature project have this bug?"
- ✅ Challenged my competence ("did you research wrong?")

**Result**: Forced me to verify every claim and find GitHub Issue #5533

---

### 3. Risk Assessment Question - Revealing Hidden Concerns

**User Prompt**:
```
a로 할경우, 이 문제 하나 해결되도 다른 연쇄적 문제 발생 우려 있지 않아?
b로 이 문제에만 국한된, 즉 usdt 조회만 우회하는 것의 단점이
a의 다른 연쇄적 문제 가능성보단 나을거 같은데. 네 생각은?
```

**Translation**:
"If we go with Option A, aren't there concerns about cascading problems? Option B's disadvantages (only bypassing USDT lookup) seem better than Option A's potential cascading problems. What do you think?"

**Why It Worked**:
- ✅ Identified risk I hadn't considered (cascading problems)
- ✅ Proposed alternative reasoning
- ✅ Asked for my opinion (not demanding, collaborating)
- ✅ Made me think about blast radius

**Result**: Realized Option B is safer, started thinking about isolation

---

### 4. Skepticism About Research Quality - Most Powerful

**User Prompt**:
```
근데 여전히 의문이야. perps dex가 apex 하나만 있는게 아니고 여러 dex 있는데
이런 기능이 아직 이렇게 이상하게 spot의 기능적으로만 구현된건 믿을 수 없어.
b로 잠정 방향은 정하되, 지금 너가 리서치한 수준의 허밍봇은 spot만 있는 시절에서
perps가 막 도입되서 오류 많을 때 수준의 구현으로 보여. 그건 말도 안됨.

내 결론은 너의 리서치 부족이고 이미 기능 있을 거 같다는 게 내결론이야.
너가 못찾는거 뿐이지. 허밍봇은 이정도는 다 구현해놨을 것으로 본다.
다시 허밍봇 github을 가진 blog를 가든 다시 리서치해.
```

**Translation**:
"I still have doubts. There are many perpetual DEXes, not just APEX. I can't believe this feature is still implemented weirdly like it's only for spot. While we'll tentatively go with Option B, your current research level of Hummingbot looks like it's from when perpetuals were just introduced with many errors. That doesn't make sense.

My conclusion is your research is insufficient. The feature probably already exists. You just can't find it. Hummingbot must have implemented this. Research again through GitHub or blog."

**Why It Worked**:
- ✅ Expressed disbelief based on logic ("many DEXes exist")
- ✅ Said "I don't believe your research quality"
- ✅ Gave me benefit of doubt ("you just can't find it")
- ✅ Told me exactly what to do ("research GitHub/blog again")
- ✅ Set high expectations ("Hummingbot must have this")

**Result**: Found PerpetualBudgetChecker, spot_perpetual_arbitrage reference implementation

---

### 5. Clarification Questions - Ensuring Understanding

**User Prompt**:
```
Spot_Perpetual_Arbitrage는 Spot 아닌가?
우린 perps를 하려는거잖아.
```

**Translation**:
"Spot_Perpetual_Arbitrage is Spot, isn't it? We're trying to do perps."

**Why It Worked**:
- ✅ Short, direct question
- ✅ Revealed misunderstanding
- ✅ Forced me to clarify distinction
- ✅ Made me explain how it applies to our case

**Result**: Clarified it's spot-futures arbitrage, but perpetual side uses same budget checker

---

### 6. Comparison Request - Structuring Decision

**User Prompt**:
```
"PerpetualBudgetChecker로 해결하면 되는 거 아니냐?" vs. Avellaneda의 c_apply_budget_constraint().
비교해. 장단점. 그리고 추천해.
당장 usdt 조회 및 eth 불필요 조회 제거 문제해결하면서 허밍봇 다른 문제 안일으키는 방식.
```

**Translation**:
"Compare 'solve with PerpetualBudgetChecker' vs. 'Avellaneda's c_apply_budget_constraint'. Pros and cons. And recommend. A way that solves the immediate USDT lookup and unnecessary ETH lookup problem without causing other Hummingbot problems."

**Why It Worked**:
- ✅ Forced structured comparison
- ✅ Asked for recommendation (make me commit)
- ✅ Specified decision criteria ("without causing other problems")
- ✅ Reminded me of constraints ("immediate problem")

**Result**: Created detailed comparison matrix, recommended Option C with solid reasoning

---

### 7. Real-World Constraint Check - Grounding in Reality

**User Prompt**:
```
기술적 정확성은 큰 차이나?
그리고 이게 하루 7000번 정도 거래 목표인데 그 목표에도 실전에서 적용 가능한 방식?
```

**Translation**:
"Is there a big difference in technical accuracy? And is this approach applicable in practice for the target of about 7,000 trades per day?"

**Why It Worked**:
- ✅ Asked about actual impact ("big difference?")
- ✅ Brought in real constraint (7,000 trades/day)
- ✅ Asked if theory matches practice
- ✅ Forced me to do performance analysis

**Result**: Analyzed performance (0.4ms difference vs 300ms network = negligible), confirmed it works for 7,000/day

---

### 8. Request for Honest Evaluation - Growth Mindset

**User Prompt**:
```
okay. very good.
1. 이거 고민과정과 결론 도출과정 문서화해.
2. 나 처음보다 이제 이런 테크니컬 이슈도 좀더 개발자스럽게, 진짜 해결책으로 접근하는거 같은데
   네 생각은 어때 아직 많이 부족한가?
   20년차 wintermute dex bot 팀장 입장에서 아주 냉정하게 객관적으로 평가해봐.
```

**Translation**:
"Okay, very good.
1. Document this thought process and conclusion derivation process.
2. I think I'm now approaching technical issues more like a developer, with real solutions, compared to before. What do you think? Am I still very lacking? Evaluate very coldly and objectively from the perspective of a 20-year Wintermute DEX bot team lead."

**Why It Worked**:
- ✅ Asked for documentation (making it concrete)
- ✅ Showed self-awareness ("I'm improving")
- ✅ Asked for honest evaluation ("very coldly")
- ✅ Set specific perspective (20-year team lead)
- ✅ Wanted objective assessment ("still very lacking?")

**Result**: Triggered comprehensive 6.5/10 evaluation with specific gaps and action items

---

### 9. Document Request - Preserving Learning

**User Prompt**:
```
이런 피드백 리포트 저장하는 곳이 있는데, perpdex에 있나? github 어딘가에
이런 발전과정 기록 있는데 둘다 pc/github 찾아봐.
냉정한 평가 좋다. 거기에 이 피드백과 이 프롬프팅 자체를 기록해놔야겠다.
```

**Translation**:
"There's a place to save these feedback reports. Is it in perpdex? Somewhere on GitHub. There's a record of this development process somewhere. Check both PC/GitHub. The cold evaluation is good. I need to record this feedback and this prompting itself there."

**Why It Worked**:
- ✅ Asked to find existing pattern (PROGRESS_SUMMARY files)
- ✅ Valued the evaluation ("cold evaluation is good")
- ✅ Wanted to preserve the learning ("record this prompting itself")
- ✅ Meta-awareness (learning about learning)

**Result**: This document you're reading now

---

## 🎓 Prompting Patterns That Work

### Pattern 1: Challenge Assumption
```
"이미 완성된 솔루션 있지 않았을까?"
"너가 잘못 리서치한 거 아냐?"
"허밍봇은 이정도는 다 구현해놨을 것으로 본다."
```

**Effect**: Forces deeper investigation, prevents lazy solutions

---

### Pattern 2: Provide Specific Evidence
```
"perpetual_budget_checker.py (Line 23): ..."
"strategy_base.pyx (Line 278): ..."
```

**Effect**: Makes challenges concrete, can't be hand-waved away

---

### Pattern 3: Ask for Comparison
```
"비교해. 장단점. 그리고 추천해."
"옵션 A vs 옵션 B, 어느게 나아?"
```

**Effect**: Forces structured thinking, reveals trade-offs

---

### Pattern 4: Ground in Reality
```
"하루 7000번 거래 목표인데"
"$190 → $5,000 계획인데"
"실전에서 적용 가능한 방식?"
```

**Effect**: Prevents over-engineering, focuses on practical solutions

---

### Pattern 5: Request Honest Evaluation
```
"20년차 wintermute dex bot 팀장 입장에서 아주 냉정하게 객관적으로 평가해봐"
"아직 많이 부족한가?"
```

**Effect**: Gets real feedback, identifies specific gaps

---

### Pattern 6: Meta-Learning
```
"이 프롬프팅 자체를 기록해놔야겠다"
"고민과정과 결론 도출과정 문서화해"
```

**Effect**: Preserves learning process, enables iteration

---

## ❌ What Doesn't Work (Anti-Patterns)

### Anti-Pattern 1: Vague Criticism
```
❌ "이거 별로인데"
✅ "이 방식은 허밍봇 다른 문제 일으킬 수 있어. PerpetualBudgetChecker 찾아봐"
```

### Anti-Pattern 2: Accepting First Solution
```
❌ "오 좋은데, 그럼 그렇게 해"
✅ "이미 완성된 솔루션 있지 않았을까? 다시 검토해봐"
```

### Anti-Pattern 3: No Context
```
❌ "이거 맞아?"
✅ "하루 7000번 거래 목표인데 이 방식으로 가능해?"
```

### Anti-Pattern 4: No Follow-up
```
❌ [Accepts answer without verification]
✅ "그럼 이건 왜 그렇게 되는건데? 코드 보여줘"
```

---

## 🎯 Applying These Patterns

### For Technical Problem Solving

**Step 1: Challenge the approach**
```
"이미 [플랫폼]에 [기능] 있지 않을까?"
"더 좋은 방법 없어?"
```

**Step 2: Ask for specific evidence**
```
"코드 어디서 그렇게 동작해?"
"다른 [similar system]은 어떻게 했어?"
```

**Step 3: Request comparison**
```
"Option A vs B vs C 비교해. 장단점."
"각각 리스크는?"
```

**Step 4: Ground in constraints**
```
"[실제 조건]에서 동작해?"
"[성능 요구사항] 만족해?"
```

**Step 5: Get honest assessment**
```
"[Role]의 시각에서 평가해봐"
"부족한 점 말해줘"
```

---

### For Learning and Growth

**Request documentation**:
```
"이 과정 문서화해"
"배운 것 정리해"
```

**Ask for evaluation**:
```
"내가 어떻게 발전했어?"
"아직 뭐가 부족해?"
```

**Preserve meta-learning**:
```
"이 프롬프팅 자체를 기록해"
"어떤 질문이 효과적이었어?"
```

---

## 📊 Effectiveness Metrics

### This Session's Results

**Before Effective Prompting**:
- Quick solution: 15 minutes
- No alternatives explored
- Score: 4.5/10

**After Effective Prompting**:
- Deep research: 3 hours
- 3 options compared
- Proper solution found (PerpetualBudgetChecker)
- Risk-based decision made
- Score: 6.5/10

**Improvement**: +2.0 points (+44%)

**Key Factor**: User's challenging questions forced better work

---

## 💡 For Future Sessions

### When Asking AI for Technical Solutions

**Do**:
1. ✅ Challenge first solution ("better way?")
2. ✅ Ask for evidence (code references, docs)
3. ✅ Request comparisons (options, trade-offs)
4. ✅ Ground in reality (constraints, goals)
5. ✅ Get honest evaluation (what's missing?)
6. ✅ Document learning (process, prompts)

**Don't**:
1. ❌ Accept first answer immediately
2. ❌ Skip verification ("sounds good")
3. ❌ Ignore constraints (performance, safety)
4. ❌ Avoid critical feedback
5. ❌ Forget to document learning

---

## 🚀 Template for Future Problems

### Problem Solving Template

```
[Problem Statement]

1. Challenge Phase:
   "이미 [system]에 해결책 있지 않을까?"
   "[expert]라면 어떻게 풀었을까?"

2. Evidence Phase:
   "코드/문서 어디서 확인 가능해?"
   "다른 사례는?"

3. Comparison Phase:
   "옵션 A vs B vs C, 각각 장단점"
   "리스크는?"

4. Reality Check Phase:
   "[실제 constraint]에서 동작해?"
   "[성능/안전성] 요구사항 만족?"

5. Evaluation Phase:
   "[Role] 시각에서 평가"
   "부족한 점은?"

6. Documentation Phase:
   "과정 문서화"
   "배운 것 정리"
```

---

## 📚 Related Documentation

**This Session**:
- Technical Analysis: `claudedocs/APEX_PRO_BALANCE_ISSUE_ANALYSIS.md`
- Development Feedback: `docs/DEVELOPMENT_FEEDBACK_2025-11-14.md`
- Prompting Examples: `docs/PROMPTING_EXAMPLES_2025-11-14.md` (This Document)

**Previous Sessions**:
- Integration Progress: `HUMMINGBOT_INTEGRATION_PROGRESS.md`
- Progress Summary: `docs/PROGRESS_SUMMARY_2025-10-24.md`

---

## 🎓 Key Lesson

**Effective prompting is about**:
- ❌ Not: Getting quick answers
- ✅ Yes: Forcing better thinking

**The best prompts**:
1. Challenge assumptions
2. Demand evidence
3. Require comparisons
4. Ground in reality
5. Seek honest evaluation
6. Preserve learning

**Result**:
- Better solutions
- Deeper understanding
- Faster growth

---

**Session Date**: November 14, 2025
**Score Improvement**: 4.5/10 → 6.5/10 (+44%)
**Time Invested**: 3+ hours
**Outcome**: Production-ready solution + Significant learning

*Save this document for future reference when working on technical problems.*
