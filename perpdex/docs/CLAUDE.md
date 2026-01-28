# CLAUDE.md - AI 작업 규칙 (Rules)

**프로젝트**: Volume Farming Bot - Perpetual DEX Point Farming
**문서 버전**: 1.0
**작성일**: 2025-10-25

---

## 📖 이 문서의 목적

Claude Code가 이 프로젝트에서 작업할 때 따라야 할 규칙과 워크플로우. Ultra-Think 방법론의 3중 문서 체계 중 **Rules** 레이어.

**3중 문서 구조**:
- **TECHSPEC.md** (Why & What): 전략적 비전, 핵심 목적
- **PLAN.md** (How): 실행 계획서, 일일 작업 지시서
- **CLAUDE.md** (Rules): AI 작업 규칙, 워크플로우 (이 문서)

---

## 🚀 Pre-Work Rules (세션 시작 시 필수)

### Rule 1: 문서 읽기 순서 (MANDATORY)

**모든 작업 시작 전에 다음 순서로 읽기**:

```python
# 1. TECHSPEC.md 읽기 (프로젝트 핵심 목적 파악)
read("docs/TECHSPEC.md")

# 2. PLAN.md 읽기 (현재 세션 목표 확인)
read("docs/PLAN.md")
# Focus: "🎯 현재 세션 목표" 섹션

# 3. Session Notes 읽기 (이전 세션 컨텍스트)
read("docs/PLAN.md")
# Focus: "📝 Session Notes" 섹션
```

**Why**: 프로젝트의 진짜 목적을 이해하지 못하면 잘못된 방향으로 구현할 수 있음 (예: profit trading vs volume farming 혼동)

**Example**:
```
❌ WRONG (문서 안 읽고 시작):
- "TP/SL 수익률 극대화를 위해 10%로 설정하겠습니다"
  → Volume farming 목적과 상충 (거래 빈도 감소)

✅ RIGHT (TECHSPEC.md 읽고):
- "Volume farming이 목적이므로 TP/SL 0.2%로 좁게 설정 → 거래 빈도 증가"
  → 프로젝트 목적과 일치
```

---

### Rule 2: 컨텍스트 체크리스트

**매 세션 시작 시 확인**:

- [ ] TECHSPEC.md 읽음 → North Star 이해 (volume farming for points)
- [ ] PLAN.md 읽음 → 현재 Milestone/Phase 확인
- [ ] Session Notes 읽음 → Blockers, Lessons Learned 확인
- [ ] .env 파일 확인 → mainnet/testnet credentials 올바른지
- [ ] git status 확인 → 변경사항 없는 clean state인지

**Time**: ~3-5분 (절대 생략 금지)

---

## ⚡ Trigger Commands (사용자 명령어)

### Command: `go`

**의미**: PLAN.md의 "현재 세션 목표" 실행 시작

**Workflow**:
```python
# 1. Read current session goals
session_goals = read("docs/PLAN.md", section="현재 세션 목표")

# 2. Identify pending tasks (unchecked ☐)
pending_tasks = [task for task in session_goals if not task.completed]

# 3. Execute first pending task
execute(pending_tasks[0])

# 4. Update PLAN.md checkboxes as you complete
update_plan_md(task=pending_tasks[0], status="completed")
```

**Example**:
```
User: "go"

Claude:
1. Reading PLAN.md...
2. Current session goal: Task 1 - 잘못된 mainnet orders 수동 취소
3. Starting Task 1...
4. [Shows cancellation script]
5. ✅ Task 1 completed → Updating PLAN.md
```

---

### Command: `continue`

**의미**: 이전 세션에서 진행 중이던 작업 이어서 계속

**Workflow**:
```python
# 1. Read Session Notes - "진행 중인 작업"
in_progress = read("docs/PLAN.md", section="진행 중인 작업")

# 2. Resume from where it was left off
resume(in_progress)

# 3. Check for blockers
blockers = read("docs/PLAN.md", section="Blockers")
if blockers:
    alert_user(blockers)
```

---

### Command: `report`

**의미**: 현재 진행 상황 보고서 생성

**Workflow**:
```python
# Generate status report
report = {
    "milestone": current_milestone,
    "phase": current_phase,
    "completed_tasks": count_completed(),
    "pending_tasks": count_pending(),
    "blockers": list_blockers(),
    "next_actions": list_next_actions(),
}

# Display report
show_report(report)
```

**Output Example**:
```markdown
## 📊 Progress Report

**Milestone**: 1 - Single DEX Validation
**Phase**: 1.1 - Native TP/SL 안정화

**Progress**: 3/5 tasks completed (60%)

✅ Completed:
- Task 1: Mainnet orders 취소
- Task 2: ApexClient.get_positions() 구현
- Task 3: Entry Price Mismatch 해결

🔄 In Progress:
- Task 4: TP/SL Order Type 파라미터 추가

⏳ Pending:
- Task 5: Testnet 테스트

🚨 Blockers: None

⏭️ Next: Task 4 완료 후 → Task 5 testnet 검증
```

---

### Command: `checkpoint`

**의미**: 현재 상태를 PLAN.md Session Notes에 저장

**Workflow**:
```python
# Save current state to Session Notes
checkpoint = {
    "completed": list_completed_since_last_checkpoint(),
    "in_progress": list_current_tasks(),
    "blockers": list_new_blockers(),
    "lessons": list_lessons_learned(),
}

# Update PLAN.md
update_session_notes(checkpoint)
```

**When to use**: 30분마다 or risky operation 전

---

## 🧪 TDD Workflow (Test-Driven Development)

### Mandatory TDD for All Code

**NEVER write implementation before tests.**

**Workflow**:
```
1. Test (RED)
   ├─ Write failing test
   ├─ Run test → Verify failure
   └─ Commit: "test: Add test for X (failing)"

2. Code (GREEN)
   ├─ Write minimal implementation
   ├─ Run test → Verify pass
   └─ Commit: "feat: Implement X"

3. Iterate (REFACTOR)
   ├─ Improve code quality
   ├─ Run test → Still passing
   └─ Commit: "refactor: Improve X"
```

**Example - Task 2: ApexClient.get_positions()**:

```python
# Step 1: TEST (RED)
# File: tests/test_apex_client.py

def test_get_positions_returns_list():
    """Test get_positions() returns list of positions"""
    client = ApexClient(environment='testnet')
    positions = client.get_positions('BTC-USDT')

    assert isinstance(positions, list)
    # This will FAIL because method doesn't exist yet

# Run: pytest tests/test_apex_client.py::test_get_positions_returns_list
# Expected: ❌ FAIL (AttributeError: 'ApexClient' has no attribute 'get_positions')

# Commit:
git add tests/test_apex_client.py
git commit -m "test: Add test for get_positions() (failing)"


# Step 2: CODE (GREEN)
# File: apex/lib/apex_client.py

class ApexClient:
    def get_positions(self, symbol: str = None):
        """Get current positions"""
        account = self.private_client.get_account_v3()
        positions = account.get('data', {}).get('positions', [])

        if symbol:
            positions = [p for p in positions if p.get('symbol') == symbol]

        return positions

# Run: pytest tests/test_apex_client.py::test_get_positions_returns_list
# Expected: ✅ PASS

# Commit:
git add apex/lib/apex_client.py
git commit -m "feat: Implement ApexClient.get_positions()

- Returns list of current positions
- Optional symbol filter
- Test passing

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"


# Step 3: ITERATE (REFACTOR)
# Add error handling, improve docstring, etc.
```

---

### Test Coverage Requirements

**Minimum Coverage**:
- Unit tests: 80%+
- Integration tests: 60%+
- E2E tests: Critical paths only

**Test Files**:
```
tests/
├── unit/
│   ├── test_apex_client.py
│   ├── test_avellaneda.py
│   └── test_position_monitor.py
├── integration/
│   ├── test_native_tpsl.py
│   └── test_cross_exchange.py
└── e2e/
    ├── test_mainnet_flow.py
    └── test_24h_operation.py
```

---

## 📝 Commit Rules

### Rule 1: PLAN.md + Code 함께 커밋

**NEVER commit code without updating PLAN.md checkboxes.**

**Correct Workflow**:
```bash
# 1. Complete task
# 2. Update PLAN.md checkbox: ☐ → ✅
# 3. Commit BOTH files together

git add docs/PLAN.md apex/pilot_true_dynamic_tpsl.py
git commit -m "완료: Task 3 - MARKET entry Native TP/SL 구현

- pilot_true_dynamic_tpsl.py 생성 (MARKET entry)
- Entry uncertainty buffer 0.1% 추가
- PLAN.md Task 3 체크박스 완료 표시

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Why**: PLAN.md는 project의 single source of truth. 코드만 커밋하면 PLAN과 실제 진행 상황 불일치.

---

### Rule 2: Commit Message Format

**Template**:
```
완료: Task X - [작업 제목]

- [변경사항 1]
- [변경사항 2]
- PLAN.md Task X 체크박스 완료 표시

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Examples**:
```
✅ GOOD:
완료: Task 2 - ApexClient.get_positions() 구현

- apex/lib/apex_client.py에 get_positions() 메서드 추가
- Symbol 필터 기능 구현
- tests/test_apex_client.py 테스트 추가 (passing)
- PLAN.md Task 2 체크박스 완료

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>

❌ BAD:
"fixed stuff"
"update"
"wip"
```

---

### Rule 3: Session End Commit

**세션 종료 시 필수 커밋**:

```bash
# Update Session Notes
# Commit everything

git add docs/PLAN.md [other_modified_files]
git commit -m "체크포인트: Phase 1.1 진행 상황 저장

완료:
- Task 1: Mainnet orders 취소
- Task 2: ApexClient.get_positions() 구현

진행 중:
- Task 3: MARKET entry 구현

다음 세션:
- Task 3 완료 후 testnet 테스트

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 🎯 프로젝트별 특수 규칙

### Rule A: Volume Farming 우선순위

**이 프로젝트는 Volume Farming이 목적 (Profit Trading 아님)**

**Implications**:
- 거래 빈도 > 수익률
- 손실 방지 (≥0%) > 수익 극대화
- Point farming 추적 필수
- TP/SL은 좁게 (0.2%) → 빠른 회전

**Forbidden Actions**:
- ❌ TP/SL 넓게 설정 (5-10%) → 거래 빈도 감소
- ❌ Taker orders 사용 → Fee 증가
- ❌ High-risk strategies (arbitrage, leverage >10x)

---

### Rule B: Native TP/SL 필수

**이 프로젝트는 Apex Native TP/SL 사용 필수**

**Reasons**:
- Phase 7.1-7.27에서 15-20시간 낭비 (별도 TP/SL orders, WebSocket OCO 등)
- Native가 가장 빠르고 안정적 (OCO built-in)

**Forbidden Approaches**:
- ❌ 별도 TP/SL orders 생성
- ❌ WebSocket OCO 직접 구현
- ❌ REST polling for TP/SL

**Correct**:
- ✅ `isOpenTpslOrder=True` with `tpTriggerPrice`, `slTriggerPrice`
- ✅ MARKET entry (LIMIT entry는 Entry Price Mismatch 위험)
- ✅ LIMIT TP/SL orders (not MARKET)
- ✅ GTT TimeInForce (not IOC)

---

### Rule C: Mainnet 신중히

**Mainnet 작업 전 필수 체크리스트**:

- [ ] Testnet에서 10회 이상 성공
- [ ] Entry Price Mismatch 해결 확인
- [ ] TP/SL direction validation 통과
- [ ] Position size ≤ 0.001 BTC (≈$10)
- [ ] 사용자에게 명시적 확인 받음 (`--yes` flag)

**Forbidden**:
- ❌ Testnet 테스트 없이 mainnet 배포
- ❌ 큰 포지션 크기로 실험 (>0.01 BTC)
- ❌ 사용자 확인 없이 자동 mainnet 실행

---

### Rule D: 변수명 카멜 케이스

**모든 Python 변수는 snake_case, JavaScript는 camelCase**

**Python Example**:
```python
# ✅ CORRECT
entry_price = 110000
take_profit_pct = 0.002
current_inventory = 0.005

# ❌ WRONG
entryPrice = 110000  # JavaScript style in Python
TakeProfitPct = 0.002  # PascalCase
currentinventory = 0.005  # no separator
```

**JavaScript Example**:
```javascript
// ✅ CORRECT
const entryPrice = 110000;
const takeProfitPct = 0.002;

// ❌ WRONG
const entry_price = 110000;  // Python style in JS
const EntryPrice = 110000;   // PascalCase
```

---

## 🔄 Auto-Update Workflow

### PLAN.md 자동 업데이트 규칙

**When**: 작업 완료 시마다

**What to update**:
1. **Checkboxes**: ☐ → ✅
2. **Session Notes - 완료된 작업**: 새 항목 추가
3. **Session Notes - 진행 중인 작업**: 완료된 것 제거
4. **Session Notes - 다음 세션 우선순위**: 업데이트
5. **Session Notes - Lessons Learned**: 새로운 교훈 추가

**Example**:
```markdown
# Before
### ✅ 완료된 작업
-

### 🔄 진행 중인 작업
- Task 2: ApexClient.get_positions() 구현

# After (Task 2 완료 시)
### ✅ 완료된 작업
- Task 2: ApexClient.get_positions() 구현 (2025-10-25)
  - apex/lib/apex_client.py에 메서드 추가
  - tests/test_apex_client.py 테스트 통과

### 🔄 진행 중인 작업
- Task 3: MARKET entry Native TP/SL 구현
```

---

## 🚨 Error Handling & Recovery

### Principle: Never Skip Investigation

**When error occurs**:
1. ❌ NEVER skip tests or validation to "make it work"
2. ❌ NEVER comment out failing code
3. ❌ NEVER workaround without understanding root cause

**Correct Approach**:
```
1. Read error message carefully
2. Investigate root cause (use --ultrathink if needed)
3. Document findings in NATIVE_TPSL_CRITICAL_ISSUES.md or similar
4. Fix properly (not workaround)
5. Add to "Lessons Learned" in PLAN.md
```

**Example - Entry Price Mismatch**:
```
❌ WRONG Response:
"Entry price mismatch 발생 → TP/SL 비활성화하겠습니다"

✅ RIGHT Response:
1. Entry Price Mismatch 분석
2. NATIVE_TPSL_CRITICAL_ISSUES.md 작성 (원인, 4가지 해결책)
3. Solution 1 선택 (MARKET entry)
4. PLAN.md에 Task 3 추가
5. Lessons Learned 업데이트: "LIMIT entry는 Native TP/SL과 위험"
```

---

## 📊 Quality Gates

### Before Mainnet Deployment

**Mandatory Checks**:
- [ ] All unit tests passing (80%+ coverage)
- [ ] All integration tests passing
- [ ] Testnet validation (10+ successful cycles)
- [ ] Entry Price Mismatch resolved
- [ ] TP/SL direction validation passed
- [ ] PLAN.md checkboxes all completed for current phase
- [ ] User explicit approval (`--yes` flag)

**If ANY check fails**: ❌ BLOCK mainnet deployment

---

## 🔧 Debugging Guidelines

### When Stuck (>30 min on same issue)

**Escalation Process**:
```
1. Review TECHSPEC.md → Am I solving the right problem?
2. Review PLAN.md → Is this the right approach?
3. Check Session Notes - Lessons Learned → Has this been solved before?
4. Use --ultrathink for systematic analysis
5. Document blocker in PLAN.md Session Notes
6. Ask user for guidance if truly blocked
```

**Forbidden**:
- ❌ Continuing to bang head against wall for >1 hour
- ❌ Implementing without understanding
- ❌ Guessing and hoping it works

---

## 📚 Documentation Standards

### Code Comments

**When to comment**:
- Complex algorithms (e.g., Avellaneda spread calculation)
- Non-obvious business logic (e.g., "Why 0.1% buffer?")
- Workarounds (explain why workaround needed)

**When NOT to comment**:
- Obvious code (`x = x + 1  # increment x`)
- Duplicate information from docstrings

**Example**:
```python
# ✅ GOOD COMMENT
def calculate_spread(self, mid_price, volatility, inventory):
    """Calculate optimal bid/ask spread"""

    # Avellaneda-Stoikov formula (2008)
    # Base spread accounts for volatility risk
    base_spread = self.gamma * (volatility ** 2) * self.tau + \
                  (2 / self.gamma) * np.log(1 + self.gamma / self.k)

    # Inventory skew: penalize excess inventory to encourage rebalancing
    # q > 0 (LONG inventory) → wider bid, tighter ask → encourage sells
    # q < 0 (SHORT inventory) → tighter bid, wider ask → encourage buys
    inventory_skew = (q / 2) * self.gamma * volatility * np.sqrt(self.tau)

    return base_spread, inventory_skew


# ❌ BAD COMMENT
def get_price(self):
    # Get the current price
    price = self.client.get_current_price()
    # Return the price
    return price  # return
```

---

### Docstring Standards

**Format**: Google Style

**Example**:
```python
def execute_with_native_tpsl(
    self,
    side: str,
    size: float,
    tp_pct: float,
    sl_pct: float
) -> Dict:
    """
    Execute MARKET entry with Native TP/SL

    Uses Apex Pro Native TP/SL (isOpenTpslOrder=True) with MARKET entry
    to avoid Entry Price Mismatch issues.

    Args:
        side: 'LONG' or 'SHORT'
        size: Position size in BTC (e.g., 0.001)
        tp_pct: Take profit percentage (e.g., 0.002 = 0.2%)
        sl_pct: Stop loss percentage (e.g., 0.002 = 0.2%)

    Returns:
        Order response dict from Apex API

    Raises:
        ValueError: If side not 'LONG' or 'SHORT'
        APIError: If order placement fails

    Example:
        >>> client = DynamicTPSL(environment='testnet')
        >>> order = client.execute_with_native_tpsl(
        ...     side='SHORT',
        ...     size=0.001,
        ...     tp_pct=0.002,
        ...     sl_pct=0.002
        ... )
        >>> print(order['orderId'])
        '123456789'
    """
```

---

## 🎓 Learning & Improvement

### Lessons Learned Repository

**After every mistake or discovery**:

1. Document in PLAN.md Session Notes - Lessons Learned
2. If major issue → Create separate .md file (e.g., NATIVE_TPSL_CRITICAL_ISSUES.md)
3. Update CLAUDE.md Rules if applicable

**Example**:
```markdown
### 💡 Lessons Learned

2025-10-25:
- Native TP/SL은 entry order와 동시 제출 → Entry price uncertainty 반드시 고려
- LIMIT entry는 위험 → MARKET entry 더 안전
- TP/SL Order Type/TimeInForce 파라미터 명시 필수 (LIMIT, GTT)
- 15시간 낭비한 WebSocket OCO는 불필요 → Native 기능 먼저 확인할 것
```

---

## 🔐 Security Rules

### API Keys & Credentials

**NEVER**:
- ❌ Hardcode API keys in source code
- ❌ Commit .env files to git
- ❌ Log API keys or secrets
- ❌ Share mainnet credentials

**ALWAYS**:
- ✅ Use environment variables (.env)
- ✅ Add .env to .gitignore
- ✅ Separate testnet and mainnet credentials
- ✅ Rotate keys after exposure

---

### Mainnet Safety

**Before mainnet execution**:
- [ ] Double-check environment variable (`APEX_API_KEY` → mainnet or testnet?)
- [ ] Verify position size (≤ 0.001 BTC initially)
- [ ] Confirm with user explicitly
- [ ] Enable dry-run mode first if available

---

## 📞 Support & References

### When Uncertain

**Decision Tree**:
```
Is this about project purpose/strategy?
├─ YES → Read TECHSPEC.md
└─ NO
    ├─ Is this about current task?
    │   └─ Read PLAN.md current session goals
    └─ Is this about implementation details?
        ├─ Apex API → https://api-docs.pro.apex.exchange
        ├─ Paradex API → https://docs.paradex.trade
        └─ Avellaneda MM → Read original paper (2008)
```

### External Resources

- **Apex Pro API Docs**: https://api-docs.pro.apex.exchange
- **Paradex API Docs**: https://docs.paradex.trade
- **Avellaneda & Stoikov Paper**: High-frequency Trading in a Limit Order Book (2008)
- **Kelly Criterion**: Wikipedia article on optimal position sizing

---

## 📋 Quick Reference Checklist

### Every Session Start
- [ ] Read TECHSPEC.md (understand Why & What)
- [ ] Read PLAN.md current session goals
- [ ] Read Session Notes (context from last session)
- [ ] Check git status (clean state)
- [ ] Verify environment (.env correct)

### Every Task
- [ ] Write test first (TDD)
- [ ] Implement
- [ ] Test passes
- [ ] Update PLAN.md checkbox
- [ ] Commit PLAN.md + code together

### Every Session End
- [ ] Update Session Notes (completed, in-progress, next)
- [ ] Commit checkpoint
- [ ] Review Lessons Learned
- [ ] Leave clear notes for next session

### Before Mainnet
- [ ] Testnet validation (10+ cycles)
- [ ] All quality gates passed
- [ ] User explicit approval
- [ ] Small position size (≤0.001 BTC)

---

## 🔄 Version History

**v1.0** (2025-10-25):
- Initial CLAUDE.md creation
- Ultra-Think 방법론 적용
- TDD workflow 정의
- 프로젝트별 특수 규칙 추가

---

**Last Updated**: 2025-10-25
**Next Review**: Milestone 1 완료 시 or 규칙 위반 발견 시
