# Fix GRVT API Request Format Issues

## Context

### Original Request
Fix GRVT API request format issues causing 400 "Request could not be processed due to malformed syntax" errors.

### Problem Analysis
The GRVT API is rejecting requests due to incorrect payload format in the CCXT wrapper's `fetch_order_book` method:

**Current (Broken) Request:**
```json
{
  "instrument": "ETH-PERP",
  "aggregate": 1,
  "depth": 50
}
```

**Expected (Working) Request:**
```json
{
  "instrument": "ETH_USDT_Perp",
  "depth": 50
}
```

### Root Cause
The CCXT wrapper (`pysdk/grvt_ccxt.py` and `pysdk/grvt_ccxt_pro.py`) sends invalid parameters:
1. **Wrong symbol format**: Uses CCXT format `"ETH-PERP"` instead of GRVT format `"ETH_USDT_Perp"`
2. **Invalid parameter**: Sends `aggregate: 1` which GRVT API doesn't accept
3. **Missing symbol mapping**: No conversion between CCXT and GRVT instrument formats

### Affected Files
1. `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py` (line 654 - sync)
2. `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt_pro.py` (line 698 - async)
3. `f:/Dropbox/dexbot/perp-dex-tools-original/hedge/exchanges/grvt.py` (usage layer)

### Alternative Approach Considered
Use GRVT SDK native API directly in `grvt.py` instead of CCXT wrapper to bypass the issue entirely.

---

## Work Objectives

### Core Objective
Fix GRVT API request format issues to resolve 400 errors and restore order book functionality.

### Deliverables
1. Fixed payload format in CCXT wrapper files
2. Symbol format conversion (CCXT → GRVT format)
3. Remove invalid `aggregate` parameter
4. Verification testing with actual API calls
5. Rollback procedure if issues arise

### Definition of Done
- [ ] Order book requests return 200 status (not 400)
- [ ] Correct payload format verified via logs/API testing
- [ ] Both sync and async versions fixed
- [ ] No regression in existing functionality
- [ ] Documentation of changes

---

## Must Have / Must NOT Have

### Must Have
✅ Fix `fetch_order_book` payload format in both sync and async versions
✅ Remove `aggregate: 1` parameter from request
✅ Ensure symbol format matches GRVT expectations
✅ Preserve existing `depth` parameter handling
✅ Maintain backward compatibility with calling code

### Must NOT Have
❌ Breaking changes to public API surface
❌ Removal of `depth` parameter support
❌ Changes to WebSocket RPC methods (not affected)
❌ Modifications to authentication or other endpoints
❌ Regressions in order placement/cancellation

---

## Task Flow and Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Analysis & Planning (COMPLETE)                     │
│ - Understand CCXT wrapper structure                         │
│ - Map symbol format differences                             │
│ - Identify all affected call sites                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Fix Implementation (REQUIRED)                      │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Task 2.1: Fix sync version (grvt_ccxt.py)             │  │
│ │ - Remove 'aggregate' parameter                        │  │
│ │ - Ensure payload structure is correct                 │  │
│ └───────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Task 2.2: Fix async version (grvt_ccxt_pro.py)         │  │
│ │ - Mirror sync fixes                                   │  │
│ │ - Ensure consistency across implementations           │  │
│ └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Verification (REQUIRED)                            │
│ - Test order book retrieval with fixed code                │
│ - Verify API response status (expect 200, not 400)         │
│ - Check payload format in actual HTTP requests            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Regression Testing (REQUIRED)                      │
│ - Verify existing functionality still works                │
│ - Test order placement/cancellation                        │
│ - Check position queries                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed TODOs

### Task 1: Fix Sync Version in grvt_ccxt.py
**File:** `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py`
**Line:** 654

**Current Code:**
```python
payload = {"instrument": symbol, "aggregate": 1}
if limit:
    payload["depth"] = limit
```

**Required Change:**
```python
payload = {"instrument": symbol}
if limit:
    payload["depth"] = limit
```

**Acceptance Criteria:**
- [ ] `aggregate` parameter removed from payload
- [ ] `instrument` parameter preserved
- [ ] `depth` parameter conditional logic intact
- [ ] No other modifications to the method

---

### Task 2: Fix Async Version in grvt_ccxt_pro.py
**File:** `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt_pro.py`
**Line:** 698

**Current Code:**
```python
payload = {"instrument": symbol, "aggregate": 1}
if limit:
    payload["depth"] = limit
```

**Required Change:**
```python
payload = {"instrument": symbol}
if limit:
    payload["depth"] = limit
```

**Acceptance Criteria:**
- [ ] `aggregate` parameter removed from payload
- [ ] Changes mirror sync version exactly
- [ ] `depth` parameter logic preserved
- [ ] Async functionality unaffected

---

### Task 3: Verify Symbol Format Handling
**Investigation Required:** Determine if CCXT-to-GRVT symbol conversion is already handled

**Analysis:**
- Check if `symbol` parameter is already in GRVT format (`ETH_USDT_Perp`) when passed to `fetch_order_book`
- If not, identify where conversion should happen (wrapper or caller)
- Review `grvt.py` to see what symbol format is used

**Acceptance Criteria:**
- [ ] Document current symbol format at call site
- [ ] Confirm whether additional conversion needed
- [ ] If conversion needed, implement and test

---

### Task 4: Test Order Book Retrieval
**Verification:** Confirm API returns 200 status with fixed payload

**Test Steps:**
1. Create test script to call `fetch_order_book` with typical parameters
2. Verify HTTP status code is 200 (not 400)
3. Check response contains valid order book data
4. Log actual payload sent to API for verification

**Acceptance Criteria:**
- [ ] No 400 errors returned
- [ ] Order book data structure is valid
- [ ] Bids and asks arrays present
- [ ] Price/size data accessible

---

### Task 5: Regression Test Existing Functionality
**Safety Check:** Ensure no breaking changes to other operations

**Test Areas:**
- Order placement (market/limit)
- Order cancellation
- Position queries
- Order status queries

**Acceptance Criteria:**
- [ ] All existing operations still functional
- [ ] No new errors introduced
- [ ] Performance not degraded

---

## Commit Strategy

### Recommended Approach
Given this is a critical bug fix with minimal code change:

**Option A: Single Atomic Commit** (Preferred)
```
fix(grvt): Remove invalid 'aggregate' parameter from order book requests

- Remove 'aggregate: 1' from fetch_order_book payload in grvt_ccxt.py
- Remove 'aggregate: 1' from fetch_order_book payload in grvt_ccxt_pro.py
- Fixes 400 "malformed syntax" errors from GRVT API
- Preserves 'depth' parameter functionality

Resolves: GRVT API request format issues
```

**Option B: Two-Phase Commit** (If symbol conversion also needed)
```
Commit 1: fix(grvt): Remove aggregate parameter from order book requests
Commit 2: fix(grvt): Add CCXT-to-GRVT symbol format conversion
```

### Commit Message Guidelines
- Use conventional commit format
- Reference issue/ticket if applicable
- Include file paths changed
- Note API behavior change (400 → 200)

---

## Success Criteria

### Functional Success
1. ✅ Order book requests return HTTP 200 status
2. ✅ No "malformed syntax" errors in logs
3. ✅ Valid order book data returned for all test symbols
4. ✅ Both sync and async versions working correctly

### Technical Success
1. ✅ Payload matches GRVT API specification exactly
2. ✅ No regressions in other API operations
3. ✅ Code changes are minimal and focused
4. ✅ Both wrapper versions (sync/async) consistent

### Verification Success
1. ✅ Manual testing confirms fix
2. ✅ Automated tests (if existing) still pass
3. ✅ Log analysis shows correct payload format
4. ✅ Error rates reduced to zero for order book queries

---

## Risk Assessment

### Low Risk
- ✅ Minimal code change (remove 1 parameter)
- ✅ Well-isolated (only affects order book retrieval)
- ✅ Easy to rollback if issues arise
- ✅ No database/schema changes

### Mitigation Strategies
1. **Backup original files** before modification
2. **Test in dev environment** first (if available)
3. **Rollback plan**: Revert single commit if issues detected
4. **Monitoring**: Check logs for 24 hours after deployment

---

## Alternative Solutions (Considered but Not Recommended)

### Alternative 1: Bypass CCXT Wrapper
**Approach:** Use GRVT SDK native API directly in `grvt.py`

**Pros:**
- Full control over request format
- Potentially better performance

**Cons:**
- Larger code changes required
- Loses CCXT standardization benefits
- Higher risk of introducing bugs
- More maintenance overhead

**Decision:** Not recommended unless CCXT wrapper fix fails

### Alternative 2: Hotfix in Caller Code
**Approach:** Override `fetch_order_book` in `grvt.py` with custom implementation

**Pros:**
- Faster to implement
- No modification to installed package

**Cons:**
- Code duplication
- Maintenance burden
- Doesn't fix root cause
- Other code using CCXT wrapper still broken

**Decision:** Not recommended - fix should be in wrapper

---

## Implementation Notes

### Symbol Format Considerations
The current fix focuses on removing the `aggregate` parameter. However, symbol format may still be an issue:

**CCXT Format:** `ETH/USDT:USDT` or `ETH-PERP`
**GRVT Format:** `ETH_USDT_Perp`

If symbol format issues persist after removing `aggregate`, additional conversion will be needed in the wrapper or at call sites.

### Testing Environment
- The fix should be tested against GRVT's testnet first if available
- Verify with real API calls, not just code inspection
- Check both sync and async code paths

---

## References

### GRVT API Documentation
- Endpoint: `GET_ORDER_BOOK`
- Expected parameters:
  - `instrument`: string (e.g., "ETH_USDT_Perp")
  - `depth`: integer (10, 50, 100, 500)
- Invalid parameters:
  - `aggregate`: NOT supported

### Related Files
- CCXT sync wrapper: `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py`
- CCXT async wrapper: `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt_pro.py`
- Usage layer: `f:/Dropbox/dexbot/perp-dex-tools-original/hedge/exchanges/grvt.py`

---

## Post-Implementation

### Monitoring Checklist
- [ ] Monitor logs for 400 errors (should be zero)
- [ ] Check order book refresh rates
- [ ] Verify trading bot functionality unaffected
- [ ] Review API error rates in first 24 hours

### Documentation Updates
- Update any internal docs referencing old payload format
- Note the GRVT-specific parameter requirements
- Document symbol format if conversion implemented

---

**Plan Status:** ✅ READY FOR EXECUTION

**Estimated Completion Time:** 30-60 minutes
**Complexity:** LOW
**Risk Level:** LOW
