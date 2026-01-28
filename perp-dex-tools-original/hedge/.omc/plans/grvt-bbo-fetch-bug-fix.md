# GRVT BBO Fetch Bug Fix Plan

**Created**: 2026-01-28  
**Status**: Critical Issue - V4 Core Feature Not Working  
**Iteration**: 1/5

---

## Critical Issue Summary

### Problem Statement

V4 BBO routing's core functionality is **completely non-functional**. All orders are falling back to direct market orders instead of using BBO-1tick smart routing.

**Error Message**:
```
[SMART_ROUTING] BBO fetch failed, using direct market order: object dict can't be used in 'await' expression
```

**Impact**:
- V4 BBO routing **NOT WORKING** - entire purpose of V4 is defeated
- Expected spread: ~0.5 bps → Actual spread: 2-3 cents
- Timeout issues **NOT SOLVED** - orders use simple market order
- Trading costs **HIGHER** - simple market order vs BBO-1tick

### Root Cause Analysis

**Location**: [DN_alternate_backpack_grvt.py:922-925](perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py#L922-L925)

```python
# CURRENT CODE (BROKEN):
result = await self.hedge_client.place_iterative_market_order(
    contract_id=self.hedge_contract_id,
    target_quantity=quantity,
    side=order_side,
    max_iterations=10,
    tick_size=10  # INT: 10 cents = $0.10 - FIXED V4 SIGNATURE
)

# Line 923: This is causing the error
if result.get('success', True):  # FIXED: Use .get() for safety
    filled = extract_filled_quantity(result)
    avg_price = result.get('average_price', None) or result.get('traded_size', result.get('size', {}))
```

**The Bug**: The error happens when `result.get('average_price', ...)` tries to access dict as if it were awaitable.

**Wait - that's not the real error.** Let me check the grvt.py code.

---

## Root Cause: Async/Await Mixing in DN File

### Problem Location

**File**: [DN_alternate_backpack_grvt.py:921-939](perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py#L921-L939)

```python
if order_type == "CLOSE":
    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2"):
        self.logger.info(f"[CLOSE] Using ITERATIVE market order for {quantity} ETH")
        result = await self.hedge_client.place_iterative_market_order(
            contract_id=self.hedge_contract_id,
            target_quantity=quantity,
            side=order_side,
            max_iterations=10,
            tick_size=10
        )

        if result.get('success', True):  # Line 923
            filled = extract_filled_quantity(result)
            avg_price = result.get('average_price', None) or result.get('traded_size', result.get('size', {}))

            self.logger.info(
                f"[CLOSE] [GRVT] [ITERATIVE_FILL]: "
                f"{filled} @ ~{avg_price}"
            )
```

### Actual Error Source

Looking at the log output:
```
[SMART_ROUTING] BBO fetch failed, using direct market order: object dict can't be used in 'await' expression
```

This error is **NOT coming from DN file** - it's coming from **grvt.py's place_iterative_market_order() method**.

**Let me check grvt.py:1200+ where place_iterative_market_order is defined:**

The error must be in how the BBO data is being used in the iterative order loop.

---

## Investigation: BBO Fetch Error Source

### Error Location: grvt.py Lines 1218-1433 (place_iterative_market_order)

The error message indicates an async/await issue when trying to fetch BBO data.

**Likely Problem**: Line ~1220-1250 where BBO is fetched:

```python
# CURRENT CODE (suspected):
for iteration in range(1, max_iterations + 1):
    try:
        bbo = await self.fetch_bbo_prices(contract_id)  # Line ~1037 (relative to method)
    except Exception as e:
        self.logger.warning(f"[SMART_ROUTING] BBO re-fetch failed: {e}")
    
    # ... rest of the loop
```

The error "object dict can't be used in 'await' expression" suggests:
- Either `fetch_bbo_prices` is returning a dict instead of being awaited
- Or `bbo` is being treated as a dict when it should be awaited
- Or the result is being awaited somewhere incorrectly

---

## Bug Fix Plan

### Phase 1: Investigate grvt.py BBO Fetch Issue

**Task 1.1: Read place_iterative_market_order in grvt.py**
- Read lines 1218-1433 from grvt.py
- Identify exact line where BBO fetch happens
- Find the async/await bug

**Task 1.2: Read fetch_bbo_prices in grvt.py**
- Read lines 602-650 from grvt.py
- Verify it's async and returns a dict
- Check if there's any synchronous code being called incorrectly

**Acceptance Criteria**:
- BBO fetch error source identified
- Exact line number and code pattern found
- Root cause explanation documented

---

### Phase 2: Fix the Async/Await Bug

**Approach**: Based on investigation, apply the appropriate fix

**Potential Fixes**:
1. If `fetch_bbo_prices` returns a dict but should be awaited: Add `await` before the call
2. If `bbo` is being treated as a dict incorrectly: Fix the variable usage
3. If REST client method needs to be awaited: Ensure proper async/await pattern

**Example Fix Pattern**:
```python
# BEFORE (broken):
bbo = self.rest_client.fetch_ticker(contract_id)  # Missing await

# AFTER (fixed):
bbo = await self.rest_client.fetch_ticker(contract_id)  # Add await
```

**Acceptance Criteria**:
- Async/await pattern corrected
- No syntax errors
- Code compiles

---

### Phase 3: Test BBO Routing

**Task 3.1: Run test with BBO routing**
```bash
cd perp-dex-tools-original/hedge
python DN_alternate_backpack_grvt.py --ticker ETH --size 0.5 --iter 5
```

**Task 3.2: Verify BBO routing is working**
- Check for `[SMART_ROUTING] Starting with` log message
- Check for BBO spread display
- Check for iterative order placement at BBO-1tick
- Verify no "BBO fetch failed" error

**Task 3.3: Measure actual spread**
- Compare actual spread vs expected ~0.5 bps
- Verify if timeout issues are resolved

**Acceptance Criteria**:
- No "BBO fetch failed" error
- BBO routing logs appear
- Spread is significantly lower than before (approaching 0.5 bps target)

---

### Phase 4: Verify Safety Features Still Work

**Task 4.1: Confirm all safety features are preserved**
- MAX_POSITION check works
- MAX_DAILY_LOSS check works
- Pre-trade check logs appear
- Emergency unwind still triggers

**Task 4.2: Run additional test**
```bash
python DN_alternate_backpack_grvt.py --ticker ETH --size 0.5 --iter 3
```

**Acceptance Criteria**:
- All safety features still functional
- No regressions from original implementation

---

## Definition of Done

- [ ] Async/await bug in grvt.py BBO fetch identified and fixed
- [ ] BBO routing working (no "BBO fetch failed" error)
- [ ] Spread reduced to target range (~0.5 bps)
- [ ] All safety features preserved
- [ ] Test passes with V4 BBO routing enabled
- [ ] Original V3 params (max_tick_offset, max_fill_duration) removed
- [ ] Verification tests pass

---

## Critical Lessons

### What Went Wrong

1. **QA Failure**: BBO fetch error is obvious in test logs. QA should have flagged this as CRITICAL.
2. **RALPLAN Failure**: Plan didn't include proper async/await verification steps.
3. **Architect Failure**: Should have caught this during code review of place_iterative_market_order.
4. **Testing Gap**: Test only verified that orders "complete" not that "BBO routing works".

### How to Fix the Process

1. **BBO Routing Verification**: Test MUST verify:
   - No "BBO fetch failed" errors
   - BBO spread logs appear
   - Spread is within target range
2. **Async/Await Testing**: Add specific tests for async operations
3. **Root Cause Validation**: Before claiming "fix complete", verify the exact bug is fixed
4. **Regression Prevention**: Every fix must include:
   - What was broken
   - Why it was broken
   - How it's now fixed
   - Evidence it's working

---

## Root Cause Summary

**Bug**: Async/await mixing in grvt.py's place_iterative_market_order() method when fetching BBO data.

**Location**: [grvt.py:~1037 (relative to method)](perp-dex-tools-original/hedge/exchanges/grvt.py#L1037)

**Fix**: Add missing `await` keyword before BBO fetch call.

**Impact**: V4 BBO routing completely non-functional. All orders fall back to simple market order.

**Fix Verification**: 
1. Run test and verify no "BBO fetch failed" error
2. Check logs for BBO spread information
3. Confirm spread is ~0.5 bps (was 2-3 cents)
