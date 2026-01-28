# Logger API Fix - Complete Standardization

## Context

**Original Request:** Fix the AttributeError causing order submission failures in GRVT integration.

**Issue Identified:**
```
ERROR: AttributeError: 'TradingLogger' object has no attribute 'error'
File: grvt.py:266, in _ws_rpc_submit_order
```

**Root Cause Analysis:**
There are TWO different logger systems in this codebase:

1. **DN_alternate_backpack_grvt.py** - Uses Python's standard `logging` module
   - Line 195: `self.logger = logging.getLogger(f"dn_hedge_{self.ticker}")`
   - Standard Python logger HAS convenience methods: `info()`, `warning()`, `error()`, `debug()`
   - **Status:** All 200+ logger calls are VALID - NO CHANGES NEEDED

2. **grvt.py (ExchangeClient)** - Uses custom `TradingLogger` class
   - Custom logger with generic API: `log(message, level)`
   - **Status:** Partially fixed - some locations still use old convenience methods
   - **Must fix:** 11 remaining locations in grvt.py

**Current State:**
- grvt.py has been partially updated (main _ws_rpc_submit_order fixed)
- 11 locations in grvt.py still use `self.logger.info/warning/error/debug()`
- These 11 will cause AttributeError at runtime

## Work Objectives

**Core Objective:** Complete the logger API standardization in grvt.py by fixing all 11 remaining locations.

**Deliverables:**
- Update all 11 inconsistent logger calls in grvt.py to use `log(message, level)` API
- Verify no AttributeError exceptions occur

**Definition of Done:**
- All 11 locations in grvt.py updated to `self.logger.log(message, "LEVEL")`
- No AttributeError exceptions from TradingLogger
- Exchange client operates without logger errors

## Must Have / Must NOT Have

**Must Have:**
- Fix all 11 identified locations in grvt.py ONLY
- Use the generic `log(message, level)` API
- Preserve exact same log messages and context

**Must NOT Have:**
- Over-engineering or refactoring beyond the 11 fixes
- Changes to TradingLogger class
- Changes to DN_alternate_backpack_grvt.py (standard Python logger is fine)
- Changes to any other files
- Adding new convenience methods to TradingLogger

## Task Flow and Dependencies

**Sequential Tasks:**
1. Fix all 11 logger calls in grvt.py (lines: 488, 1260, 1265, 1314, 1339, 1352, 1371, 1383, 1400, 1415, 1421, 1430)
2. Verify syntax is correct
3. No dependencies - standalone fix

## Detailed TODOs

### Task 1: Fix Line 488 - Warning Log
**Location:** grvt.py:488
**Acceptance Criteria:** Logger call uses `log(message, "WARNING")` format

**Before:**
```python
self.logger.warning(
    f"GRVT: {method} failed: {data}"
)
```

**After:**
```python
self.logger.log(
    f"GRVT: {method} failed: {data}",
    "WARNING"
)
```

---

### Task 2: Fix Line 1260 - Info Log
**Location:** grvt.py:1260
**Acceptance Criteria:** Logger call uses `log(message, "INFO")` format

**Before:**
```python
self.logger.info(
    f"GRVT: Restoring session after authentication"
)
```

**After:**
```python
self.logger.log(
    f"GRVT: Restoring session after authentication",
    "INFO"
)
```

---

### Task 3: Fix Line 1265 - Warning Log
**Location:** grvt.py:1265
**Acceptance Criteria:** Logger call uses `log(message, "WARNING")` format

**Before:**
```python
self.logger.warning(
    f"GRVT: No active session to restore"
)
```

**After:**
```python
self.logger.log(
    f"GRVT: No active session to restore",
    "WARNING"
)
```

---

### Task 4: Fix Line 1314 - Info Log
**Location:** grvt.py:1314
**Acceptance Criteria:** Logger call uses `log(message, "INFO")` format

**Before:**
```python
self.logger.info(f"[ITERATIVE] SUCCESS: Filled {total_filled} ETH in {iteration} iterations")
```

**After:**
```python
self.logger.log(
    f"[ITERATIVE] SUCCESS: Filled {total_filled} ETH in {iteration} iterations",
    "INFO"
)
```

---

### Task 5: Fix Line 1339 - Warning Log
**Location:** grvt.py:1339
**Acceptance Criteria:** Logger call uses `log(message, "WARNING")` format

**Before:**
```python
self.logger.warning(f"[SMART_ROUTING] BBO re-fetch failed: {e}")
```

**After:**
```python
self.logger.log(
    f"[SMART_ROUTING] BBO re-fetch failed: {e}",
    "WARNING"
)
```

---

### Task 6: Fix Line 1352 - Info Log
**Location:** grvt.py:1352
**Acceptance Criteria:** Logger call uses `log(message, "INFO")` format

**Before:**
```python
self.logger.info(
    f"[SMART_ROUTING] Iteration {iteration}: "
    f"Remaining {remaining_qty} @ ${limit_price:.2f} "
    f"(placed {iteration} orders, filled {filled_qty} so far)"
)
```

**After:**
```python
self.logger.log(
    f"[SMART_ROUTING] Iteration {iteration}: "
    f"Remaining {remaining_qty} @ ${limit_price:.2f} "
    f"(placed {iteration} orders, filled {filled_qty} so far)",
    "INFO"
)
```

---

### Task 7: Fix Line 1371 - Info Log
**Location:** grvt.py:1371
**Acceptance Criteria:** Logger call uses `log(message, "INFO")` format

**Before:**
```python
self.logger.info(
    f"[SMART_ROUTING] Fully filled in {iteration} iterations"
)
```

**After:**
```python
self.logger.log(
    f"[SMART_ROUTING] Fully filled in {iteration} iterations",
    "INFO"
)
```

---

### Task 8: Fix Line 1383 - Info Log
**Location:** grvt.py:1383
**Acceptance Criteria:** Logger call uses `log(message, "INFO")` format

**Before:**
```python
self.logger.info(
    f"[SMART_ROUTING] Iteration {iteration}: Placing chunk {chunk_i+1}/{num_chunks} of {chunk_qty:.4f}"
)
```

**After:**
```python
self.logger.log(
    f"[SMART_ROUTING] Iteration {iteration}: Placing chunk {chunk_i+1}/{num_chunks} of {chunk_qty:.4f}",
    "INFO"
)
```

---

### Task 9: Fix Line 1400 - Error Log
**Location:** grvt.py:1400
**Acceptance Criteria:** Logger call uses `log(message, "ERROR")` format

**Before:**
```python
self.logger.error(
    f"GRVT: REST API error: {e}",
    exc_info=e
)
```

**After:**
```python
self.logger.log(
    f"GRVT: REST API error: {e}",
    "ERROR"
)
```

**Note:** The `exc_info` parameter is not supported by the generic `log()` method, so it's omitted.

---

### Task 10: Fix Line 1415 - Debug Log
**Location:** grvt.py:1415
**Acceptance Criteria:** Logger call uses `log(message, "DEBUG")` format

**Before:**
```python
self.logger.debug(
    f"[SMART_ROUTING] Waiting {chunk_delay}s before next chunk..."
)
```

**After:**
```python
self.logger.log(
    f"[SMART_ROUTING] Waiting {chunk_delay}s before next chunk...",
    "DEBUG"
)
```

---

### Task 11: Fix Line 1421 - Info Log
**Location:** grvt.py:1421
**Acceptance Criteria:** Logger call uses `log(message, "INFO")` format

**Before:**
```python
self.logger.info(
    f"[SMART_ROUTING] Fully filled in {iteration} iterations, "
    f"final position: {final_pos} ETH (target: {target_qty})"
)
```

**After:**
```python
self.logger.log(
    f"[SMART_ROUTING] Fully filled in {iteration} iterations, "
    f"final position: {final_pos} ETH (target: {target_qty})",
    "INFO"
)
```

---

### Task 12: Fix Line 1430 - Error Log
**Location:** grvt.py:1430
**Acceptance Criteria:** Logger call uses `log(message, "ERROR")` format

**Before:**
```python
self.logger.error(
    f"GRVT: REST API unexpected error: {e}",
    exc_info=e
)
```

**After:**
```python
self.logger.log(
    f"GRVT: REST API unexpected error: {e}",
    "ERROR"
)
```

**Note:** The `exc_info` parameter is not supported by the generic `log()` method, so it's omitted.

---

## Commit Strategy

**Single Commit:**
```
fix(grvt): Complete logger API standardization to log(message, level)

- Update all 11 remaining inconsistent logger calls in grvt.py
- Replace info/warning/error/debug with log(message, "LEVEL")
- Resolves AttributeError during exchange operations
- Maintains same log messages and context

Files changed:
- perp-dex-tools-original/hedge/exchanges/grvt.py

Fixes: AttributeError: 'TradingLogger' object has no attribute 'error'

Complete breakdown:
- Line 488: warning → log(msg, "WARNING")
- Line 1260: info → log(msg, "INFO")
- Line 1265: warning → log(msg, "WARNING")
- Line 1314: info → log(msg, "INFO")
- Line 1339: warning → log(msg, "WARNING")
- Line 1352: info → log(msg, "INFO")
- Line 1371: info → log(msg, "INFO")
- Line 1383: info → log(msg, "INFO")
- Line 1400: error → log(msg, "ERROR")
- Line 1415: debug → log(msg, "DEBUG")
- Line 1421: info → log(msg, "INFO")
- Line 1430: error → log(msg, "ERROR")

Note: DN_alternate_backpack_grvt.py unchanged (uses standard Python logger)
```

## Success Criteria

- [ ] All 11 locations in grvt.py updated to `self.logger.log(message, "LEVEL")` format
- [ ] No AttributeError exceptions from TradingLogger in logs
- [ ] Exchange client operates without logger errors
- [ ] All log messages preserved with same context
- [ ] Only grvt.py modified (no other files changed)
- [ ] DN_alternate_backpack_grvt.py unchanged (uses valid standard Python logger)

## Estimated Time

**3 minutes** - Simple string replacements at 11 known locations

---

**PLAN_READY**
