# Fix CCXT Wrapper Order Book API Bug

## Context

**Original Request:** Fix CCXT wrapper order book API bug causing 400 error

**Problem Summary:**
- API returns 400 "Request could not be processed due to malformed syntax"
- CCXT wrapper sends: `{"instrument": "ETH-PERP", "aggregate": 1, "depth": 50}`
- GRVT API expects: `{"instrument": "ETH_USDT_Perp", "depth": 50}` (no aggregate parameter)

**Root Cause:** Line 654 in `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py` includes an unwanted `aggregate: 1` parameter that the GRVT API does not support.

## Work Objectives

### Core Objective
Fix the CCXT wrapper's `fetch_order_book` method to send only the parameters expected by the GRVT API.

### Deliverables
1. Modified `grvt_ccxt.py` with `aggregate` parameter removed from order book request
2. Verification that order book fetch works correctly

### Definition of Done
- Line 654 no longer includes `aggregate: 1`
- Only `instrument` and `depth` parameters are sent
- Order book fetch returns valid data without 400 error

## Must Have / Must NOT Have

**Must Have:**
- Remove `aggregate: 1` from line 654
- Keep `instrument` parameter
- Keep `depth` parameter
- Test order book fetch after fix

**Must NOT Have:**
- No async/await changes (method is synchronous)
- No changes to other parts of the CCXT wrapper
- No breaking changes to the method signature

## Task Flow and Dependencies

```
┌─────────────────────────────────────┐
│ 1. Read grvt_ccxt.py file           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Locate line 654                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Remove aggregate parameter       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Test order book fetch            │
└─────────────────────────────────────┘
```

## Detailed TODOs

### Task 1: Read the CCXT wrapper file
**File:** `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py`

**Acceptance Criteria:**
- File is successfully read
- Line 654 is visible and contains the `aggregate: 1` parameter

### Task 2: Edit line 654 to remove aggregate parameter
**File:** `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py`
**Line:** 654

**Current code (expected):**
```python
params = {"instrument": instrument, "aggregate": 1, "depth": depth}
```

**Change to:**
```python
params = {"instrument": instrument, "depth": depth}
```

**Acceptance Criteria:**
- `aggregate: 1` is removed
- Only `instrument` and `depth` remain
- No other changes to the line or surrounding code

### Task 3: Verify the fix
Create a simple test to verify order book fetch works:

**Test steps:**
1. Import the CCXT wrapper
2. Initialize GRVT exchange instance
3. Call `fetch_order_book('ETH_USDT_Perp', limit=50)`
4. Verify response is valid (not 400 error)
5. Verify order book contains bids and asks arrays

**Acceptance Criteria:**
- Order book fetch executes without error
- Response contains valid order book data
- No 400 status code returned

## Commit Strategy

**Commit message:**
```
fix(grvt): Remove unsupported aggregate parameter from order book API

The GRVT API does not support the 'aggregate' parameter in order book
requests. Removing it to fix 400 Bad Request errors.

Fixes: CCXT wrapper order book API bug
```

**Atomic commit:** Single file change in `grvt_ccxt.py`

## Success Criteria

1. **Functional:** Order book fetch returns valid data without 400 error
2. **API Compatibility:** Request matches GRVT API specification
3. **No Regressions:** Method signature unchanged, existing code continues to work
4. **Test Evidence:** Order book fetch verified working after fix

## Implementation Notes

- The method is synchronous (no async/await needed)
- Only modify the parameters object, not the method logic
- The instrument name format conversion (ETH-PERP → ETH_USDT_Perp) may be handled elsewhere in the wrapper
- This is a site-packages file modification - consider documenting for future dependency updates

## Files Modified

- `C:/Users/crypto quant/anaconda3/Lib/site-packages/pysdk/grvt_ccxt.py` (line 654)

## Related Files

None - this is an isolated fix to the CCXT wrapper.

---

**Plan created:** 2026-01-28
**Estimated complexity:** LOW (single line change + verification)
**Estimated time:** 15-30 minutes
