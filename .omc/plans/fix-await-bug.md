# Work Plan: Fix async/await Bug in analyze_order_book_depth

**Plan ID:** fix-await-bug
**Created:** 2026-01-28
**Status:** Draft

---

## Context

### Original Request
Fix async/await bug in `analyze_order_book_depth` function causing KeyError: 'asks'

### Problem Analysis
- **Error:** `KeyError: 'asks'` - order book data not being retrieved properly
- **Root Cause:** `await` keyword incorrectly removed at line 783 in `grvt.py`
- **Function Signature:** `async def analyze_order_book_depth(...) -> dict:`
- **Technical Detail:** The CCXT wrapper's `fetch_order_book()` is synchronous but internally calls async POST requests. Without `await`, the async POST doesn't execute properly

### Impact
- Order book analysis failing
- Prevents proper price discovery and liquidity analysis
- Blocks hedge strategy execution

---

## Work Objectives

### Core Objective
Restore proper async/await handling in `analyze_order_book_depth` function to fix order book retrieval

### Deliverables
1. Restore `await` keyword at line 783 in `grvt.py`
2. Add `await` keyword at line 1253 where `analyze_order_book_depth()` is called
3. Verify fix with test execution

### Definition of Done
- [ ] Line 783: `order_book = await self.exchange.fetch_order_book(symbol)` has `await` keyword
- [ ] Line 1253: Call site includes `await` keyword
- [ ] Test executes without KeyError: 'asks'
- [ ] Order book data properly retrieved and analyzed

---

## Must Have / Must NOT Have

### Must Have
- Restore `await` at line 783 for `self.exchange.fetch_order_book(symbol)`
- Add `await` at line 1253 for `analyze_order_book_depth()` call
- Fix must maintain async function signature
- No other changes to function logic

### Must NOT Have
- Do NOT change function signature
- Do NOT refactor related code (out of scope)
- Do NOT add new features
- Do NOT modify other functions

---

## Task Flow and Dependencies

```
Task 1: Read grvt.py to understand current state
  ↓
Task 2: Restore await keyword at line 783
  ↓
Task 3: Add await keyword at line 1253
  ↓
Task 4: Verify fix with quick syntax check
  ↓
Task 5: Commit changes
```

**Dependencies:** Each task depends on the previous task completing successfully

---

## Detailed TODOs

### Task 1: Read Current State
**File:** `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\exchanges\grvt.py`

**Action:** Read file to verify current state at lines 783 and 1253

**Acceptance Criteria:**
- File read successfully
- Current code at target lines documented

---

### Task 2: Restore await Keyword at Line 783
**File:** `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\exchanges\grvt.py`

**Current Code (line ~783):**
```python
order_book = self.exchange.fetch_order_book(symbol)
```

**Target Code:**
```python
order_book = await self.exchange.fetch_order_book(symbol)
```

**Action:** Use Edit tool to add `await` keyword

**Acceptance Criteria:**
- `await` keyword present at line 783
- No other changes to the line
- Edit verified via Read tool

---

### Task 3: Add await Keyword at Line 1253
**File:** `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\exchanges\grvt.py`

**Current Code (line ~1253):**
```python
depth_analysis = self.analyze_order_book_depth(...)
```

**Target Code:**
```python
depth_analysis = await self.analyze_order_book_depth(...)
```

**Action:** Use Edit tool to add `await` keyword

**Acceptance Criteria:**
- `await` keyword present at line 1253
- No other changes to the line
- Edit verified via Read tool

---

### Task 4: Syntax Verification
**Action:** Run Python syntax check on modified file

**Command:**
```bash
python -m py_compile "f:\Dropbox\dexbot\perp-dex-tools-original\hedge\exchanges\grvt.py"
```

**Acceptance Criteria:**
- No syntax errors reported
- File compiles successfully

---

### Task 5: Commit Changes
**Action:** Create git commit with descriptive message

**Commit Message:**
```
fix(grvt): Restore missing await keywords in analyze_order_book_depth

- Add await at line 783 for fetch_order_book() call
- Add await at line 1253 for analyze_order_book_depth() call
- Fixes KeyError: 'asks' caused by incomplete async execution

The CCXT wrapper's fetch_order_book() is synchronous but internally
calls async POST requests. Without await, the async POST doesn't
execute properly, causing empty order book data.

Related: Order book analysis failing with KeyError
```

**Acceptance Criteria:**
- Git commit created successfully
- Commit message follows conventional commit format
- Changes staged and committed

---

## Success Criteria

### Functional
- [ ] No `KeyError: 'asks'` when calling `analyze_order_book_depth()`
- [ ] Order book data properly retrieved with 'asks' and 'bids' keys
- [ ] Async execution works correctly

### Code Quality
- [ ] Python syntax is valid
- [ ] No unintended changes to other code
- [ ] Maintains existing function signatures

### Git
- [ ] Atomic commit with focused changes
- [ ] Descriptive commit message
- [ ] Clean git status after commit

---

## Notes

### Technical Context
The bug occurred because the CCXT wrapper pattern used in this codebase has synchronous function signatures that internally call async operations. The `await` keyword is required to ensure the internal async POST requests complete before returning data.

### Testing Recommendation
After applying this fix, run a quick test to verify order book retrieval:
```python
# Test that order book has 'asks' and 'bids'
depth = await exchange.analyze_order_book_depth("BTC-USD")
assert 'asks' in depth
assert 'bids' in depth
```

---

## Handoff

**To implement this plan, run:**
```
/oh-my-claudecode:start-work fix-await-bug
```

This will spawn executor agents to complete each task in sequence.
