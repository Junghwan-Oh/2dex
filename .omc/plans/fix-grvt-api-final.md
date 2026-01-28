# Work Plan: Fix GRVT API Request Format Issues

**Status:** PENDING
**Created:** 2026-01-28
**Intent:** Fix

---

## Context

### Original Request
Fix GRVT API request format issues causing 400 errors when fetching order books.

### Problem Analysis
The API returns 400 "Request could not be processed due to malformed syntax" due to two identified issues:

1. **Symbol Format Mismatch:**
   - Test code uses: `ETH-PERP`
   - API expects: `ETH_USDT_Perp` (underscore not hyphen)

2. **Invalid Parameter:**
   - CCXT wrapper sends: `aggregate: 1`
   - API does NOT support this parameter

### Expected Format (from GRVT SDK)
```python
{
    "instrument": "ETH_USDT_Perp",  # perpetual format
    "depth": 10,                     # int (10, 50, 100, 500)
    # NO "aggregate" parameter
}
```

---

## Work Objectives

### Core Objective
Fix the GRVT CCXT wrapper request payload to match the API specification, eliminating 400 errors.

### Deliverables
1. Backup of both target files
2. Fixed `grvt_ccxt.py` (synchronous) - remove `aggregate` parameter
3. Fixed `grvt_ccxt_pro.py` (asynchronous) - remove `aggregate` parameter
4. Verification logging to show actual payloads sent
5. Successful test run (ETH 0.5, 10 iterations)

### Definition of Done
- [ ] Both files backed up
- [ ] `aggregate: 1` removed from payload initialization in both files
- [ ] Payload logging added to verify correct format
- [ ] Test run completes without 400 errors
- [ ] Order book fetch succeeds

---

## Must Have / Must NOT Have

### Must Have
- Remove `aggregate` parameter from payload
- Keep `instrument` parameter
- Keep `depth` parameter
- Add payload logging for verification
- Backup files before modification

### Must NOT Have
- NO breaking changes to other parameters
- NO changes to error handling logic
- NO modifications to symbol format conversion (handled elsewhere)

---

## Task Flow and Dependencies

```
Task 1: Backup Files (INDEPENDENT)
   ↓
Task 2: Fix Synchronous Wrapper (INDEPENDENT)
Task 3: Fix Asynchronous Wrapper (INDEPENDENT)
   ↓ (both must complete)
Task 4: Add Verification Logging (DEPENDS on 2, 3)
   ↓
Task 5: Test Verification (DEPENDS on 4)
```

---

## Detailed TODOs

### Task 1: Backup Target Files
**Priority:** HIGH
**Complexity:** LOW

**Acceptance Criteria:**
- [ ] `grvt_ccxt.py` backed up to `grvt_ccxt.py.backup_before_fix`
- [ ] `grvt_ccxt_pro.py` backed up to `grvt_ccxt_pro.py.backup_before_fix`
- [ ] Backup files verified to exist

**Steps:**
1. Navigate to `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/`
2. Copy `grvt_ccxt.py` to `grvt_ccxt.py.backup_before_fix`
3. Copy `grvt_ccxt_pro.py` to `grvt_ccxt_pro.py.backup_before_fix`
4. Verify backups exist

---

### Task 2: Fix Synchronous Wrapper (grvt_ccxt.py)
**Priority:** HIGH
**Complexity:** LOW
**File:** `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py`
**Line:** 654

**Acceptance Criteria:**
- [ ] `aggregate: 1` removed from payload initialization
- [ ] `instrument` parameter preserved
- [ ] `depth` parameter preserved
- [ ] Code syntax valid (no Python errors)

**Current Code (around line 654):**
```python
payload = {
    'instrument': instrument,
    'depth': depth,
    'aggregate': 1,  # <-- REMOVE THIS LINE
}
```

**Target Code:**
```python
payload = {
    'instrument': instrument,
    'depth': depth,
}
```

**Steps:**
1. Read file at line 654 to confirm exact structure
2. Remove `aggregate: 1` line from payload initialization
3. Preserve correct indentation and structure

---

### Task 3: Fix Asynchronous Wrapper (grvt_ccxt_pro.py)
**Priority:** HIGH
**Complexity:** LOW
**File:** `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt_pro.py`
**Line:** 698

**Acceptance Criteria:**
- [ ] `aggregate: 1` removed from payload initialization
- [ ] `instrument` parameter preserved
- [ ] `depth` parameter preserved
- [ ] Code syntax valid (no Python errors)

**Current Code (around line 698):**
```python
payload = {
    'instrument': instrument,
    'depth': depth,
    'aggregate': 1,  # <-- REMOVE THIS LINE
}
```

**Target Code:**
```python
payload = {
    'instrument': instrument,
    'depth': depth,
}
```

**Steps:**
1. Read file at line 698 to confirm exact structure
2. Remove `aggregate: 1` line from payload initialization
3. Preserve correct indentation and structure

---

### Task 4: Add Verification Logging
**Priority:** MEDIUM
**Complexity:** LOW
**Files:** Both `grvt_ccxt.py` and `grvt_ccxt_pro.py`

**Acceptance Criteria:**
- [ ] Logging added to show actual payload before request
- [ ] Log format: `GRVT API Request Payload: {json.dumps(payload)}`
- [ ] Logging placed after payload construction, before request

**Steps:**
1. Import logging module (if not already imported)
2. Add log statement after payload construction in both files
3. Example: `logger.info(f"GRVT API Request Payload: {payload}")`

---

### Task 5: Verification Test
**Priority:** HIGH
**Complexity:** MEDIUM

**Acceptance Criteria:**
- [ ] Test script runs without 400 errors
- [ ] Order book fetch succeeds
- [ ] Payload logs show correct format (no `aggregate` parameter)
- [ ] 10 iterations complete successfully

**Test Parameters:**
- Symbol: ETH
- Size: 0.5
- Iterations: 10

**Steps:**
1. Run test script with ETH 0.5, 10 iterations
2. Monitor output for 400 errors
3. Verify payload logs show correct format
4. Confirm order book data is received

---

## Commit Strategy

**Atomic commits:**

1. `backup: backup GRVT CCXT wrappers before fix`
   - Both backup files

2. `fix(grvt): remove invalid aggregate parameter from order book request`
   - Both wrapper files with `aggregate` removed

3. `feat(grvt): add payload logging for API verification`
   - Logging additions

4. `test: verify GRVT API fix - ETH 0.5 10 iterations`
   - Test results and confirmation

---

## Success Criteria

### Functional Success
- [ ] No 400 errors when fetching order books
- [ ] Order book data returned successfully
- [ ] Test completes 10 iterations without failure

### Technical Success
- [ ] Payload format matches API specification
- [ ] No regressions in other CCXT methods
- [ ] Logging provides visibility into requests

### Verification Success
- [ ] Payload logs show correct format
- [ ] Backup files allow rollback if needed
- [ ] Code syntax is valid (no import/runtime errors)

---

## Risk Assessment

**Low Risk:**
- Changes are minimal (single line removal)
- Files are backed up
- Changes are isolated to order book fetch

**Mitigation:**
- Backups allow instant rollback
- Test with small size (0.5 ETH) first
- Verify both sync and async versions

---

## Notes

### Symbol Format Handling
The symbol format conversion (`ETH-PERP` → `ETH_USDT_Perp`) is handled elsewhere in the codebase and is NOT part of this fix.

### API Specification Reference
Expected format confirmed from GRVT SDK types:
- `instrument`: string (perpetual format)
- `depth`: int (10, 50, 100, 500)
- NO additional parameters

### Test Environment
- Python environment: `C:/Users/crypto quant/anaconda3`
- Package location: `Lib/site-packages/pysdk/`

---

## Rollback Plan

If issues occur after deployment:

1. Restore backup files:
   ```bash
   cp grvt_ccxt.py.backup_before_fix grvt_ccxt.py
   cp grvt_ccxt_pro.py.backup_before_fix grvt_ccxt_pro.py
   ```

2. Verify rollback with test run

3. Report issues for further investigation

---

**End of Work Plan**
