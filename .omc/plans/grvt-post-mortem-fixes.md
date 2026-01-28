# GRVT POST_ONLY Timeout Fallback Fixes

**Plan Version**: 2.0 (Critic-Approved)
**Date**: 2026-01-27
**Status**: READY FOR IMPLEMENTATION

---

## Context

### Original Request
1. ✅ Test results already documented in plan-v4
2. Check DN file's iterative order condition (quantity > 0.2)
3. Verify grvt_websocket_rpc is working
4. Fix POST_ONLY Timeout Fallback problem

### Interview Summary
User reported POST_ONLY orders timing out after 3 seconds and falling back to MARKET orders, incurring 0.05% taker fees unnecessarily.

---

## Research Findings

### Actual Test Log Evidence

**Log File**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\logs\DN_alternate_backpack_grvt_ETH_log.txt`

**Issue 1: POST_ONLY Timeout (2026-01-27)**
- **Lines**: 37140-37173 (CLOSE operations), 35866-36462 (OPEN operations)
- **Pattern**: POST_ONLY orders timing out after 3 seconds, falling back to MARKET
- **Example** (line 37141):
  ```
  2026-01-27 17:45:40,632 - WARNING - [CLOSE] POST_ONLY timeout after 3s, falling back to MARKET
  ```
- **Root Cause**: DN file wraps `place_post_only_order()` with 3-second timeout at lines 912 and 1110
- **Impact**: POST_ONLY orders don't have enough time to fill, forcing unnecessary MARKET fallback

**Issue 2: TradingLogger Bug (2026-01-25) - ALREADY FIXED**
- **Lines**: 18481-19120
- **Pattern**: `'TradingLogger' object has no attribute 'info'` errors
- **Example** (lines 18480-18481):
  ```
  2026-01-25 19:38:07,406 - INFO - [OPEN] Using ITERATIVE market order for 0.5000 ETH
  2026-01-25 19:38:07,407 - ERROR - Error placing HEDGE order (attempt 1/4): 'TradingLogger' object has no attribute 'info'
  ```
- **Root Cause**: Old code called `self.logger.info()` before TradingLogger had `info()` method
- **Status**: ✅ **FIXED** - See `GRVT_FIX_SUMMARY.md` lines 168-189

**Issue 3: Iterative Order Already Working**
- **Lines**: 18480, 18485, 18490 show iterative order IS being triggered for 0.5 ETH
- **Code**: DN file lines 851, 1046 correctly check `quantity > Decimal("0.2")`
- **Status**: ✅ **WORKING** - No changes needed

---

## Root Cause Analysis

### Primary Issue: POST_ONLY Timeout Too Short

**Current Flow**:
```
DN File (line 912, 1110):
  asyncio.wait_for(place_post_only_order(), timeout=3.0)

↓

grvt.py::place_post_only_order() (line 866):
  1. Calls _ws_rpc_submit_order() (internal 10s timeout)
  2. Polls order status for up to 10 seconds (line 896)
  3. Returns OrderResult when filled or OPEN

↓

If DN timeout (3s) triggers before fill:
  → Raises asyncio.TimeoutError
  → Falls back to MARKET order
  → Incurs 0.05% taker fee
```

**Problem**: 3-second timeout is too short for POST_ONLY orders that need to wait in the order book.

**Evidence from logs**:
- POST_ONLY orders consistently timeout at 3 seconds
- MARKET fallback orders also timeout (not filling within timeout)
- This indicates the 3s limit is the bottleneck, not GRVT's API

---

## Work Objectives

### Core Objective
Increase POST_ONLY timeout to allow orders sufficient time to fill at the best price, reducing unnecessary MARKET fallbacks.

### Deliverables
1. ✅ Verify TradingLogger fix (already complete)
2. ✅ Verify iterative market order logic (already working)
3. Modify POST_ONLY timeout values in DN file
4. Test with increased timeout to confirm improvement

### Definition of Done
- [ ] POST_ONLY timeout increased from 3s to 10s in DN file
- [ ] All changes tested with live run
- [ ] Log analysis shows reduced POST_ONLY timeout frequency
- [ ] No regression in order success rate

---

## Must Have / Must NOT Have

### Must Have
- Increase timeout at DN file lines 912 and 1110 from 3.0 to 10.0 seconds
- Maintain backward compatibility with existing error handling
- Test changes with small quantities first

### Must NOT Have
- NO changes to `grvt.py::place_post_only_order()` (already has 10s internal timeout)
- NO changes to TradingLogger (already fixed)
- NO changes to iterative order logic (already working)
- NO dynamic timeout calculation (over-engineering)

---

## Task Flow and Dependencies

```
┌─────────────────────────────────────────────────────────┐
│ Task 1: Update CLOSE operation timeout (line 912)        │
│ File: DN_alternate_backpack_grvt.py                     │
│ Change: timeout=3.0 → timeout=10.0                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Task 2: Update OPEN operation timeout (line 1110)       │
│ File: DN_alternate_backpack_grvt.py                     │
│ Change: timeout=3.0 → timeout=10.0                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Task 3: Test with small quantity (0.05 ETH, 10 cycles)  │
│ Verify: POST_ONLY orders have time to fill              │
│ Verify: Reduced MARKET fallback frequency               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Task 4: Analyze logs for improvement metrics            │
│ Compare: POST_ONLY timeout frequency before/after       │
│ Measure: Fee savings from reduced MARKET fallbacks      │
└─────────────────────────────────────────────────────────┘
```

---

## Detailed TODOs

### Task 1: Update CLOSE Operation POST_ONLY Timeout

**File**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\DN_alternate_backpack_grvt.py`

**Line**: 912

**Current Code**:
```python
# Try POST_ONLY with 3 second timeout
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(
        contract_id=self.hedge_contract_id,
        quantity=quantity,
        price=hedge_post_only_price,
        side=order_side
    ),
    timeout=3.0
)
```

**Required Change**:
```python
# Try POST_ONLY with 10 second timeout
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(
        contract_id=self.hedge_contract_id,
        quantity=quantity,
        price=hedge_post_only_price,
        side=order_side
    ),
    timeout=10.0
)
```

**Acceptance Criteria**:
- [ ] Line 912 changed from `timeout=3.0` to `timeout=10.0`
- [ ] Comment updated from "3 second" to "10 second"

---

### Task 2: Update OPEN Operation POST_ONLY Timeout

**File**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\DN_alternate_backpack_grvt.py`

**Line**: 1110

**Current Code**:
```python
# Try POST_ONLY with 3 second timeout
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(
        contract_id=self.hedge_contract_id,
        quantity=quantity,
        price=hedge_post_only_price,
        side=order_side
    ),
    timeout=3.0
)
```

**Required Change**:
```python
# Try POST_ONLY with 10 second timeout
hedge_result = await asyncio.wait_for(
    self.hedge_client.place_post_only_order(
        contract_id=self.hedge_contract_id,
        quantity=quantity,
        price=hedge_post_only_price,
        side=order_side
    ),
    timeout=10.0
)
```

**Acceptance Criteria**:
- [ ] Line 1110 changed from `timeout=3.0` to `timeout=10.0`
- [ ] Comment updated from "3 second" to "10 second"

---

### Task 3: Verify TradingLogger Fix (Already Complete)

**Evidence**:
- File: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\helpers\logger.py`
- Lines 114-128: TradingLogger has `error()`, `warning()`, `info()`, `debug()` methods
- All methods call `self.log(message, level)` correctly

**Status**: ✅ **NO ACTION NEEDED**

**Acceptance Criteria**:
- [ ] Confirmed TradingLogger has all required methods
- [ ] Confirmed `grvt.py` uses correct logger calls

---

### Task 4: Verify Iterative Order Logic (Already Working)

**Evidence**:
- DN file lines 851, 1046: Check `quantity > Decimal("0.2")`
- Log lines 18480, 18485, 18490: Show "Using ITERATIVE market order for 0.5000 ETH"
- Logic is correctly triggering iterative orders for quantities > 0.2 ETH

**Status**: ✅ **NO ACTION NEEDED**

**Acceptance Criteria**:
- [ ] Confirmed iterative order condition is correct
- [ ] Confirmed logs show iterative orders being used

---

### Task 5: Test POST_ONLY Timeout Fix

**Test Configuration**:
- Quantity: 0.05 ETH (small size to avoid immediate fills)
- Cycles: 10
- Expected: POST_ONLY orders have more time to fill

**Commands**:
```bash
cd f:\Dropbox\dexbot\perp-dex-tools-original\hedge
python DN_alternate_backpack_grvt.py --iterations 10 --quantity 0.05
```

**Verification Steps**:
1. Run test with updated timeout values
2. Monitor log file: `logs/DN_alternate_backpack_grvt_ETH_log.txt`
3. Count POST_ONLY timeout occurrences
4. Compare with baseline (pre-fix logs)

**Acceptance Criteria**:
- [ ] Test runs successfully for 10 cycles
- [ ] POST_ONLY timeout frequency reduced by > 50%
- [ ] No increase in overall error rate
- [ ] Fee savings observed from reduced MARKET fallbacks

---

### Task 6: Analyze Results and Document

**Analysis Commands**:
```bash
# Count POST_ONLY timeouts in pre-fix log (2026-01-27)
grep "POST_ONLY timeout" logs/DN_alternate_backpack_grvt_ETH_log.txt | wc -l

# Count POST_ONLY timeouts in post-fix log
grep "POST_ONLY timeout" logs/DN_alternate_backpack_grvt_ETH_log.txt | tail -100 | grep "POST_ONLY timeout" | wc -l

# Measure fee savings
grep "POST_ONLY FILLED" logs/DN_alternate_backpack_grvt_ETH_log.txt | wc -l
```

**Documentation**:
- Update `GRVT_FIX_SUMMARY.md` with POST_ONLY timeout fix details
- Include before/after metrics
- Document fee savings

**Acceptance Criteria**:
- [ ] POST_ONLY timeout frequency reduced
- [ ] Metrics documented in summary
- [ ] Fee savings quantified

---

## Commit Strategy

### Commit 1: Increase POST_ONLY Timeout
```
feat(grvt): Increase POST_ONLY timeout from 3s to 10s

- Update timeout at line 912 (CLOSE operation)
- Update timeout at line 1110 (OPEN operation)
- Allows POST_ONLY orders sufficient time to fill
- Reduces unnecessary MARKET fallbacks and taker fees

Resolves: POST_ONLY timeout fallback issue
File: perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py
```

### Commit 2: Test Results Documentation
```
docs(grvt): Document POST_ONLY timeout fix test results

- Added before/after timeout frequency metrics
- Documented fee savings from reduced MARKET fallbacks
- Updated GRVT_FIX_SUMMARY.md with timeout fix details

File: perp-dex-tools-original/hedge/GRVT_FIX_SUMMARY.md
```

---

## Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **POST_ONLY Timeout Rate** | < 20% of orders | Log analysis: `grep "POST_ONLY timeout" log \| wc -l` |
| **POST_ONLY Fill Rate** | > 60% of POST_ONLY attempts | Log analysis: `grep "POST_ONLY FILLED" log \| wc -l` |
| **Fee Savings** | > 0.02% average | Compare taker fee vs maker fee per cycle |
| **Error Rate** | < 1% of orders | Log analysis: `grep "ERROR" log \| wc -l` |
| **Order Success Rate** | > 99% | Log analysis: `grep "FILLED" log \| wc -l` / total orders |

---

## Implementation Notes

### Why 10 Seconds?

1. **grvt.py internal timeout**: `place_post_only_order()` has 10-second internal timeout (line 896)
2. **GRVT API behavior**: Orders can take 5-10 seconds to fill depending on market conditions
3. **Balance**: 10s allows sufficient fill time without excessive waiting
4. **Backward compatibility**: Matches grvt.py's existing timeout structure

### No Changes Needed To

- **TradingLogger**: Already has `error()`, `warning()`, `info()`, `debug()` methods (logger.py lines 114-128)
- **Iterative order logic**: Already checks `quantity > 0.2` correctly (DN file lines 851, 1046)
- **grvt.py**: `place_post_only_order()` already has proper 10s timeout (line 896)

### Risk Mitigation

- Test with small quantity (0.05 ETH) before full-scale deployment
- Monitor logs for increased timeout frequency
- Revert to 3s if 10s causes other issues (unlikely)

---

## References

- **Test Logs**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\logs\DN_alternate_backpack_grvt_ETH_log.txt`
- **POST_ONLY timeout evidence**: Lines 37140-37173 (2026-01-27)
- **Logger bug evidence**: Lines 18481-19120 (2026-01-25) - ALREADY FIXED
- **GRVT Fix Summary**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\GRVT_FIX_SUMMARY.md`
- **DN File**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\DN_alternate_backpack_grvt.py`
- **GRVT Exchange**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\exchanges\grvt.py`
- **TradingLogger**: `f:\Dropbox\dexbot\perp-dex-tools-original\hedge\helpers\logger.py`

---

**End of Plan v2.0 - Critic-Approved**
