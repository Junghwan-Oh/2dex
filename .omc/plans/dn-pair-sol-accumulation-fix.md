# DN Pair SOL Accumulation Fix Plan

**Plan ID**: dn-pair-sol-accumulation-fix
**Status**: READY (Final - Iteration 3/5)
**Priority**: CRITICAL
**Target File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Created**: 2026-01-30
**Revised**: 2026-01-30 (Final revision - addressed all critic feedback)

---

## Context

### Original Request
"hedge/DN_pair_eth_sol_nado.py 수정 계획 - 최신 분석 결과 반영 (정상 UNWIND 사이클 실패가 주원인, emergency_unwind_sol만 수정으로 해결 안됨, CSV 분석: SOL 39 BUY vs 26 SELL, 누적 12.399 SOL)"

### Critical Analysis Summary

**Root Cause Discovery**: Normal `execute_unwind_cycle()` is failing to close SOL positions, NOT just `emergency_unwind_sol()`.

**Evidence from CSV Analysis**:
- SOL-BUY (exit): 39 trades attempting to close shorts
- SOL-SELL (entry): 26 trades opening new shorts
- Net accumulation: +12.399 SOL (40x imbalance)
- Pattern: UNWIND SOL-BUY fills but position doesn't close, then new SOL-SELL opens

**CSV Pattern Example** (lines 87-124):
```
Line 87: ETH-SELL (exit) - SUCCESS
Line 88: SOL-BUY (exit) - SUCCESS (unwind attempt)
Line 89: ETH-SELL (entry) - NEW POSITION (WRONG!)
Line 90: SOL-SELL (entry) - NEW POSITION (WRONG!)
```

This proves UNWIND is not properly closing positions.

### Critic Feedback Resolution (All Issues Addressed)

**Iteration 2 Issues (All Resolved)**:
- Issue 1: Complete Before/After Code - Fixed
- Issue 2: Dual-Cycle Pattern - Fixed
- Issue 3: Position Direction Logic - Fixed
- Issue 4: Complete API Signatures - Fixed
- Issue 5: Exact Integration Points - Fixed
- Issue 6: Position State Documentation - Fixed

**Iteration 3 Issues (All Resolved)**:
- Issue 1: Misleading Line Numbers - Fixed (use relative insertion points)
- Issue 2: Duplicate Validation Logic - Fixed (keep internal, remove external)
- Issue 3: Missing Type Context - Fixed (document Decimal return type)
- Issue 4: API Call Consistency - Fixed (use positional arguments)

---

## Work Objectives

### Core Objective
Fix the SOL position accumulation bug by ensuring UNWIND cycles properly close SOL positions before BUILD cycles open new ones.

### Deliverables
1. Fixed `execute_unwind_cycle()` with position verification
2. Fixed `execute_build_cycle()` with internal pre-build validation
3. Fixed `execute_sell_first_cycle()` with position verification
4. Fixed `emergency_unwind_sol()` with logging and verification
5. Comprehensive logging for all position changes

### Definition of Done
- SOL positions verified to be 0 after unwind (tolerance: 0.001)
- BUILD cycles refuse to open if positions > 0.001 (internal validation)
- Emergency unwind attempts logged with success/failure
- CSV logging shows correct exit/entry patterns
- No accumulation of SOL positions across cycles

---

## Must Have / Must NOT Have

### Must Have
- Position verification after every unwind attempt
- Internal pre-build validation checking existing positions
- Logging of all position states before/after operations
- Retry logic for failed unwind attempts
- Direction-agnostic position checks using `abs(position) < 0.001`
- Positional arguments for API calls (matching current code style)

### Must NOT Have
- Silent exception swallowing in emergency_unwind_sol
- Opening new positions without checking existing state
- Assuming order success means position closed
- Removing CSV logging (enhance it instead)
- Changes to IOC order placement logic (it works)
- Direction-specific position checks (e.g., `position > 0` or `position < 0`)
- Duplicate validation logic (internal OR external, not both)
- External reconciliation function (removed - redundant with internal validation)
- Keyword arguments for API calls (use positional to match current style)

---

## Position State Documentation

### Tolerance Value Rationale

**Value**: 0.001
**Reasoning**:
- Decimal precision handling in floating-point arithmetic
- Accounts for minimal rounding errors from order calculations
- Small enough to detect real position issues
- Large enough to avoid false positives from precision noise

### Expected Position States by Cycle

| Cycle Type | Before Build | After Build | Before Unwind | After Unwind | Verification |
|------------|--------------|-------------|---------------|--------------|--------------|
| BUY_FIRST | ETH=0, SOL=0 | ETH>0, SOL<0 | ETH>0, SOL<0 | ETH=0, SOL=0 | abs(pos) < 0.001 |
| SELL_FIRST | ETH=0, SOL=0 | ETH<0, SOL>0 | ETH<0, SOL>0 | ETH=0, SOL=0 | abs(pos) < 0.001 |
| DN_PAIR | ETH=0, SOL=0 | ETH>0, SOL<0 | ETH>0, SOL<0 | ETH=0, SOL=0 | abs(pos) < 0.001 |

**Key**: All position checks use `abs(position) < 0.001` regardless of direction.

### Position Verification Logic

```python
# Direction-agnostic check - works for both long and short positions
POSITION_TOLERANCE = Decimal("0.001")

def is_position_closed(position: Decimal) -> bool:
    """Check if position is effectively closed."""
    return abs(position) < POSITION_TOLERANCE

# Examples:
# is_position_closed(Decimal("0.0005"))  → True
# is_position_closed(Decimal("-0.0005")) → True
# is_position_closed(Decimal("0.001"))   → False
# is_position_closed(Decimal("-0.001"))  → False
# is_position_closed(Decimal("12.399"))  → False (our bug!)
```

### Type Information

**get_account_positions() Return Type**: `Decimal`
- Verified from source: `async def get_account_positions(self) -> Decimal:`
- Location: `exchanges/base.py` and implemented in `exchanges/nado.py`
- Returns signed Decimal value (positive for long, negative for short)

---

## Task Flow and Dependencies

```
Priority 1 (CRITICAL): Fix Normal Unwind Cycle
├── Add position verification after unwind
├── Add retry logic if position not closed
└── Add detailed logging of position state

Priority 2 (HIGH): Fix SELL_FIRST Cycle Position Verification
├── Add unwind position verification to execute_sell_first_cycle
├── Use direction-agnostic abs(position) < 0.001 check
└── Add logging of position state

Priority 3 (HIGH): Add Pre-Build Position Validation (Internal Only)
├── Check positions inside execute_build_cycle before opening new ones
├── Refuse to build if abs(position) > 0.001
├── Log position state before build
└── NO external reconciliation function (avoid duplication)

Priority 4 (HIGH): Fix emergency_unwind_sol Silent Failures
├── Add logging of unwind attempts
├── Add position verification after unwind
└── Add retry logic with exponential backoff
```

---

## Detailed TODOs

### Priority 1: Fix Normal Unwind Cycle (CRITICAL)

**Location**: `execute_unwind_cycle()` function (search for exact function definition)

**BEFORE (Current Code)**:
```python
async def execute_unwind_cycle(self) -> bool:
    """Execute UNWIND cycle: Sell ETH / Buy SOL."""
    try:
        eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")
        return (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success)
    except Exception:
        return False
```

**AFTER (Refactored Code)**:
```python
async def execute_unwind_cycle(self) -> bool:
    """Execute UNWIND cycle: Sell ETH / Buy SOL.

    Returns:
        True if both positions are closed (abs < 0.001), False otherwise.
    """
    POSITION_TOLERANCE = Decimal("0.001")

    # Get positions BEFORE unwind
    try:
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()
        self.logger.info(f"[UNWIND] POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")
    except Exception as e:
        self.logger.error(f"[UNWIND] Failed to get positions before: {e}")
        return False

    # Place unwind orders: Sell ETH (exit long), Buy SOL (exit short)
    try:
        eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")

        # Check if orders filled successfully
        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.warning("[UNWIND] Orders failed or partially filled")
            return False

    except Exception as e:
        self.logger.error(f"[UNWIND] Order placement failed: {e}")
        return False

    # CRITICAL: Verify positions actually closed
    await asyncio.sleep(0.5)  # Brief pause for exchange to process

    try:
        eth_pos_after = await self.eth_client.get_account_positions()
        sol_pos_after = await self.sol_client.get_account_positions()
        self.logger.info(f"[UNWIND] POSITIONS AFTER: ETH={eth_pos_after}, SOL={sol_pos_after}")

        # Check if positions are closed using direction-agnostic tolerance
        eth_closed = abs(eth_pos_after) < POSITION_TOLERANCE
        sol_closed = abs(sol_pos_after) < POSITION_TOLERANCE

        if eth_closed and sol_closed:
            self.logger.info("[UNWIND] SUCCESS: Both positions closed")
            return True
        else:
            # Retry once if positions not closed
            self.logger.warning(f"[UNWIND] Positions not closed: ETH={eth_pos_after}, SOL={sol_pos_after}")
            await asyncio.sleep(1.0)

            eth_pos_retry = await self.eth_client.get_account_positions()
            sol_pos_retry = await self.sol_client.get_account_positions()
            self.logger.info(f"[UNWIND] POSITIONS RETRY: ETH={eth_pos_retry}, SOL={sol_pos_retry}")

            eth_closed = abs(eth_pos_retry) < POSITION_TOLERANCE
            sol_closed = abs(sol_pos_retry) < POSITION_TOLERANCE

            if eth_closed and sol_closed:
                self.logger.info("[UNWIND] SUCCESS: Positions closed after retry")
                return True
            else:
                self.logger.error(f"[UNWIND] FAILED: Positions still open after retry: ETH={eth_pos_retry}, SOL={sol_pos_retry}")
                return False

    except Exception as e:
        self.logger.error(f"[UNWIND] Position verification failed: {e}")
        return False
```

**Changes Made**:
1. Added position logging BEFORE unwind
2. Added position verification AFTER unwind
3. Use `abs(position) < 0.001` for direction-agnostic check
4. Added retry logic with 1 second delay
5. Added detailed logging at each step
6. Returns False if position verification fails (even if orders filled)

**Acceptance Criteria**:
- SOL position verified to be `abs(position) < 0.001` after unwind
- Returns False if position verification fails
- Logs show position state before and after unwind
- No more false positive success returns

---

### Priority 2: Fix SELL_FIRST Cycle Position Verification (HIGH)

**Location**: `execute_sell_first_cycle()` function (search for exact function definition)

**BEFORE (Current Code)**:
```python
async def execute_sell_first_cycle(self) -> bool:
    """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND."""
    try:
        # BUILD: Short ETH / Long SOL (opposite of buy_first)
        eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")
        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            return False

        # Optional sleep
        if self.sleep_time > 0:
            await asyncio.sleep(self.sleep_time)

        # UNWIND: Buy ETH / Sell SOL
        eth_result, sol_result = await self.place_simultaneous_orders("buy", "sell")
        return (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success)

    except Exception as e:
        self.logger.error(f"SELL_FIRST cycle failed: {e}")
        return False
```

**AFTER (Refactored Code)**:
```python
async def execute_sell_first_cycle(self) -> bool:
    """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND.

    This cycle:
    1. BUILD: Short ETH (negative position), Long SOL (positive position)
    2. UNWIND: Buy ETH (close short), Sell SOL (close long)

    Returns:
        True if both cycles complete and positions return to zero.
    """
    POSITION_TOLERANCE = Decimal("0.001")

    try:
        # BUILD: Short ETH / Long SOL (opposite of buy_first)
        eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")
        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.warning("[SELL_FIRST] BUILD phase failed")
            return False

        self.logger.info("[SELL_FIRST] BUILD phase completed")

        # Optional sleep
        if self.sleep_time > 0:
            await asyncio.sleep(self.sleep_time)

        # UNWIND: Buy ETH (close short), Sell SOL (close long)
        # Get positions before unwind
        try:
            eth_pos_before = await self.eth_client.get_account_positions()
            sol_pos_before = await self.sol_client.get_account_positions()
            self.logger.info(f"[SELL_FIRST] UNWIND POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")
        except Exception as e:
            self.logger.error(f"[SELL_FIRST] Failed to get positions: {e}")
            return False

        # Place unwind orders
        eth_result, sol_result = await self.place_simultaneous_orders("buy", "sell")

        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.warning("[SELL_FIRST] UNWIND orders failed")
            return False

        # CRITICAL: Verify positions actually closed
        await asyncio.sleep(0.5)  # Brief pause for exchange to process

        try:
            eth_pos_after = await self.eth_client.get_account_positions()
            sol_pos_after = await self.sol_client.get_account_positions()
            self.logger.info(f"[SELL_FIRST] UNWIND POSITIONS AFTER: ETH={eth_pos_after}, SOL={sol_pos_after}")

            # Direction-agnostic check using abs()
            eth_closed = abs(eth_pos_after) < POSITION_TOLERANCE
            sol_closed = abs(sol_pos_after) < POSITION_TOLERANCE

            if eth_closed and sol_closed:
                self.logger.info("[SELL_FIRST] SUCCESS: Both positions closed")
                return True
            else:
                self.logger.error(f"[SELL_FIRST] FAILED: Positions not closed: ETH={eth_pos_after}, SOL={sol_pos_after}")
                return False

        except Exception as e:
            self.logger.error(f"[SELL_FIRST] Position verification failed: {e}")
            return False

    except Exception as e:
        self.logger.error(f"SELL_FIRST cycle failed: {e}")
        return False
```

**Changes Made**:
1. Added position logging before unwind
2. Added position verification after unwind
3. Use `abs(position) < 0.001` for direction-agnostic check
4. Added detailed logging at each phase
5. Returns False if position verification fails

**Acceptance Criteria**:
- Both ETH and SOL positions verified to be `abs(position) < 0.001` after unwind
- Returns False if position verification fails
- Logs show position state for BUILD and UNWIND phases

---

### Priority 3: Add Pre-Build Position Validation (HIGH)

**Location**: `execute_build_cycle()` function (search for exact function definition)

**BEFORE (Current Code)**:
```python
async def execute_build_cycle(self) -> bool:
    """Execute BUILD cycle: Long ETH / Short SOL."""
    try:
        eth_result, sol_result = await self.place_simultaneous_orders("buy", "sell")
        return (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success)
    except Exception:
        return False
```

**AFTER (Refactored Code)**:
```python
async def execute_build_cycle(self) -> bool:
    """Execute BUILD cycle: Long ETH / Short SOL.

    CRITICAL: Refuses to open new positions if existing positions detected.
    This prevents accumulation from failed unwinds.

    NOTE: Internal validation only - NO external reconciliation function needed.
    This single layer of validation is sufficient to prevent accumulation.

    Returns:
        True if positions opened successfully, False if refused or failed.
    """
    POSITION_TOLERANCE = Decimal("0.001")

    # Check existing positions BEFORE building
    try:
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()
        self.logger.info(f"[BUILD] POSITIONS CHECK: ETH={eth_pos_before}, SOL={sol_pos_before}")

        # Refuse to build if positions already exist (direction-agnostic)
        if abs(eth_pos_before) > POSITION_TOLERANCE or abs(sol_pos_before) > POSITION_TOLERANCE:
            self.logger.error(
                f"[BUILD] REFUSED: Existing positions detected - "
                f"ETH={eth_pos_before}, SOL={sol_pos_before}. "
                f"Manual intervention required."
            )
            return False

    except Exception as e:
        self.logger.error(f"[BUILD] Position check failed: {e}")
        return False

    # Positions are clean, proceed to build
    try:
        eth_result, sol_result = await self.place_simultaneous_orders("buy", "sell")

        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.warning("[BUILD] Order placement failed")
            return False

        self.logger.info("[BUILD] SUCCESS: Positions opened")
        return True

    except Exception as e:
        self.logger.error(f"[BUILD] Exception during order placement: {e}")
        return False
```

**Changes Made**:
1. Added position check before opening new ones
2. Use `abs(position) > 0.001` for direction-agnostic check
3. Refuse to build if positions exist
4. Log refusal with clear message
5. Added detailed logging throughout
6. NO external reconciliation (avoid duplication)

**Acceptance Criteria**:
- Returns False if `abs(eth_pos_before) > 0.001` before build
- Returns False if `abs(sol_pos_before) > 0.001` before build
- Logs show refusal reason when positions exist
- Prevents accumulation of duplicate positions
- NO duplicate validation logic

---

### Priority 4: Fix emergency_unwind_sol Silent Failures (HIGH)

**Location**: `emergency_unwind_sol()` function (search for exact function definition)

**BEFORE (Current Code)**:
```python
async def emergency_unwind_sol(self):
    """Emergency unwind SOL position."""
    if self.sol_client:
        try:
            # Close SOL position with market order
            current_pos = await self.sol_client.get_account_positions()
            if current_pos < 0:  # Short position
                await self.sol_client.place_close_order(
                    self.sol_client.config.contract_id,
                    abs(current_pos),
                    Decimal("0"),  # Market order
                    "buy"
                )
        except Exception:
            pass
```

**AFTER (Refactored Code)**:
```python
async def emergency_unwind_sol(self) -> bool:
    """Emergency unwind SOL position with logging and verification.

    Called when one leg fills and the other fails during simultaneous orders.
    This is NOT the main cause of accumulation (that's execute_unwind_cycle),
    but it should not fail silently.

    Returns:
        True if position closed successfully, False otherwise.
    """
    POSITION_TOLERANCE = Decimal("0.001")

    if not self.sol_client:
        self.logger.warning("[EMERGENCY_UNWIND_SOL] No SOL client available")
        return False

    for attempt in range(3):  # Max 3 attempts with exponential backoff
        try:
            current_pos = await self.sol_client.get_account_positions()
            self.logger.info(
                f"[EMERGENCY_UNWIND_SOL] Attempt {attempt + 1}/3: "
                f"current_pos={current_pos}"
            )

            # Direction-agnostic check - close any non-zero position
            if abs(current_pos) < POSITION_TOLERANCE:
                self.logger.info("[EMERGENCY_UNWIND_SOL] Position already closed")
                return True

            # Determine close side based on position direction
            if current_pos > 0:
                close_side = "sell"  # Close long position
                close_qty = current_pos
            else:
                close_side = "buy"   # Close short position
                close_qty = abs(current_pos)

            self.logger.info(
                f"[EMERGENCY_UNWIND_SOL] Closing position: "
                f"side={close_side}, qty={close_qty}"
            )

            # Place market close order - POSITIONAL ARGUMENTS (matching current code style)
            await self.sol_client.place_close_order(
                self.sol_client.config.contract_id,
                close_qty,
                Decimal("0"),  # Market order
                close_side
            )

            # Wait for order to process
            await asyncio.sleep(0.5)

            # Verify position closed
            new_pos = await self.sol_client.get_account_positions()
            self.logger.info(f"[EMERGENCY_UNWIND_SOL] After close: position={new_pos}")

            if abs(new_pos) < POSITION_TOLERANCE:
                self.logger.info("[EMERGENCY_UNWIND_SOL] SUCCESS: Position closed")
                return True
            else:
                self.logger.warning(
                    f"[EMERGENCY_UNWIND_SOL] FAILED: Position still open: {new_pos}"
                )

        except Exception as e:
            self.logger.error(
                f"[EMERGENCY_UNWIND_SOL] Exception on attempt {attempt + 1}: {e}"
            )

        # Exponential backoff before retry
        if attempt < 2:
            backoff_time = 2 ** attempt  # 1s, 2s, 4s
            self.logger.info(f"[EMERGENCY_UNWIND_SOL] Retrying in {backoff_time}s...")
            await asyncio.sleep(backoff_time)

    self.logger.error("[EMERGENCY_UNWIND_SOL] FAILED: All attempts exhausted")
    return False
```

**Changes Made**:
1. Added return type `bool`
2. Added logging for every attempt
3. Use `abs(position) < 0.001` for direction-agnostic checks
4. Added position verification after close
5. Added retry logic with exponential backoff (1s, 2s, 4s)
6. Positional arguments for `place_close_order()` (matches current code style)
7. No more silent exception swallowing

**Acceptance Criteria**:
- Logs show every unwind attempt with position values
- Logs show success/failure with position values
- Retries up to 3 times with exponential backoff
- Returns True only if `abs(position) < 0.001` after unwind
- No more silent failures
- Positional arguments match current code style

---

## Implementation Notes

### Relative Insertion Points

**Important**: After adding these changes, line numbers will shift. Use these relative insertion points:

1. **execute_unwind_cycle()**: Search for function definition, replace entire function body
2. **execute_sell_first_cycle()**: Search for function definition, replace entire function body
3. **execute_build_cycle()**: Search for function definition, replace entire function body
4. **emergency_unwind_sol()**: Search for function definition, replace entire function body

### Type Context

**get_account_positions() Return Type**: `Decimal`
- Verified from source code at `exchanges/base.py` line 117
- Implemented in `exchanges/nado.py` line 866
- Returns signed Decimal (positive = long, negative = short)
- Safe to use with `abs()` for direction-agnostic checks

### API Call Style

**place_close_order()**: Use positional arguments (matching current code style)
```python
# Current code style (positional):
await client.place_close_order(
    client.config.contract_id,
    quantity,
    Decimal("0"),
    "buy"
)

# NOT keyword arguments (don't use):
await client.place_close_order(
    contract_id=client.config.contract_id,
    quantity=quantity,
    price=Decimal("0"),
    side="buy"
)
```

### Validation Strategy

**Single-Layer Validation**: Keep internal validation in `execute_build_cycle()`
- Pros: Simpler, no duplication, easier to maintain
- Cons: None significant for this use case
- Decision: Use internal validation only, NO external reconciliation function

**Rationale**:
- External reconciliation would duplicate the same checks
- Internal validation is sufficient to prevent accumulation
- Simpler code with single responsibility
- Easier to debug and maintain

---

## Commit Strategy

### Commit 1: Fix Normal Unwind Cycle (execute_unwind_cycle)
- **File**: `hedge/DN_pair_eth_sol_nado.py`
- **Function**: `execute_unwind_cycle()` (search for definition)
- **Changes**:
  - Add position logging BEFORE unwind
  - Add position verification AFTER unwind
  - Add retry logic with 1 second delay
  - Use `abs(position) < 0.001` for direction-agnostic check
  - Add detailed logging at each step
- **Message**: "Fix: Add position verification to execute_unwind_cycle() to prevent SOL accumulation"

### Commit 2: Fix SELL_FIRST Cycle Position Verification
- **File**: `hedge/DN_pair_eth_sol_nado.py`
- **Function**: `execute_sell_first_cycle()` (search for definition)
- **Changes**:
  - Add position logging before unwind
  - Add position verification after unwind
  - Use `abs(position) < 0.001` for direction-agnostic check
  - Add detailed logging at each phase
- **Message**: "Fix: Add position verification to execute_sell_first_cycle() UNWIND phase"

### Commit 3: Add Pre-Build Position Validation (Internal Only)
- **File**: `hedge/DN_pair_eth_sol_nado.py`
- **Function**: `execute_build_cycle()` (search for definition)
- **Changes**:
  - Add position check before build
  - Refuse to build if `abs(position) > 0.001`
  - Add detailed logging throughout
  - NO external reconciliation function (avoid duplication)
- **Message**: "Fix: Add pre-build validation to execute_build_cycle() to prevent duplicate positions"

### Commit 4: Fix emergency_unwind_sol Silent Failures
- **File**: `hedge/DN_pair_eth_sol_nado.py`
- **Function**: `emergency_unwind_sol()` (search for definition)
- **Changes**:
  - Add return type `bool`
  - Add logging for every attempt
  - Add position verification after close
  - Add retry logic with exponential backoff
  - Positional arguments for place_close_order()
- **Message**: "Fix: Add logging and verification to emergency_unwind_sol() to prevent silent failures"

---

## Success Criteria

### Functional Requirements
- SOL positions verified to be `abs(position) < 0.001` after unwind
- BUILD cycles refuse to open if `abs(position) > 0.001` (internal validation)
- Emergency unwind attempts logged with success/failure
- No external reconciliation function (single-layer validation)
- CSV logging shows correct exit/entry patterns

### Testing Requirements
- Run bot for 10 iterations
- Verify CSV shows equal SELL (entry) and BUY (exit) counts for SOL
- Verify no accumulation of SOL positions
- Check logs show position verification at each step

### Log Output Verification
- Every unwind cycle logs: `[UNWIND] POSITIONS BEFORE: ETH=X, SOL=Y`
- Every unwind cycle logs: `[UNWIND] POSITIONS AFTER: ETH=X, SOL=Y`
- Every build cycle logs: `[BUILD] POSITIONS CHECK: ETH=X, SOL=Y`
- Emergency unwind logs: `[EMERGENCY_UNWIND_SOL] Attempt N/3: current_pos=X`

### CSV Pattern Verification
**Before Fix** (wrong):
```
Line 87: ETH-SELL (exit) - SUCCESS
Line 88: SOL-BUY (exit) - SUCCESS (order filled)
Line 89: ETH-SELL (entry) - NEW POSITION (WRONG!)
Line 90: SOL-SELL (entry) - NEW POSITION (WRONG!)
Result: Accumulation continues
```

**After Fix** (correct):
```
Line 87: ETH-SELL (exit) - SUCCESS
Line 88: SOL-BUY (exit) - SUCCESS (order filled)
Line 89: [UNWIND] POSITIONS AFTER: ETH=0, SOL=12.399 (WRONG!)
Line 90: [UNWIND] FAILED: Positions not closed, retrying...
Line 91: [UNWIND] POSITIONS RETRY: ETH=0, SOL=12.399 (STILL WRONG!)
Line 92: [UNWIND] FAILED: Positions still open after retry
Line 93: [BUILD] POSITIONS CHECK: ETH=0, SOL=12.399
Line 94: [BUILD] REFUSED: Existing positions detected
Result: No accumulation (build refused)
```

---

## Important Notes

### Critical Constraints
1. **DO NOT fix only emergency_unwind_sol()** - This alone will NOT solve the problem
2. **Must address normal unwind cycle failure** - This is the primary root cause
3. **Must add internal position validation** - Prevents accumulation
4. **Must keep CSV logging** - Enhance it, don't remove it
5. **Use direction-agnostic checks** - Always use `abs(position) < 0.001`
6. **NO external reconciliation** - Single-layer validation is sufficient
7. **Use positional arguments** - Match current code style for API calls

### Root Cause Summary
The CSV analysis proves that `execute_unwind_cycle()` reports success but SOL positions remain open. The IOC order fills (SOL-BUY), but the position doesn't close. Then the next cycle opens a new position without checking, causing accumulation.

### Why emergency_unwind_sol Alone Won't Fix It
The emergency unwind is only called when ONE leg fills and the OTHER fails. But in our case, BOTH legs report success (orders fill), yet the SOL position remains open. So emergency_unwind_sol is never called.

The fix MUST be in the normal unwind cycle: verify positions after unwind, not just check if orders filled.

### Tolerance Value Explanation
**Value**: 0.001
**Rationale**:
- Decimal precision in floating-point arithmetic
- Minimal rounding errors from order calculations
- Small enough to detect real issues
- Large enough to avoid false positives

### Direction-Agnostic Position Checks
All position verification uses `abs(position) < 0.001` instead of direction-specific checks. This works for both long and short positions and simplifies the logic.

### Single-Layer Validation Strategy
**Decision**: Internal validation in `execute_build_cycle()` only
**Rationale**:
- External reconciliation would duplicate the same checks
- Internal validation is sufficient to prevent accumulation
- Simpler code with single responsibility
- Easier to debug and maintain
- No race conditions between validation layers

---

## References

### File Information
- **Path**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
- **Lines**: 2843 total
- **Key Functions** (search for definitions):
  - `emergency_unwind_sol()`: around line 589
  - `execute_build_cycle()`: around line 605
  - `execute_unwind_cycle()`: around line 614
  - `execute_dn_pair_cycle()`: around line 623
  - `execute_buy_first_cycle()`: around line 639
  - `execute_sell_first_cycle()`: around line 659
  - `place_simultaneous_orders()`: around line 437

### Type Information
**get_account_positions() Return Type**: `Decimal`
- Source: `exchanges/base.py` line 117
- Implementation: `exchanges/nado.py` line 866
- Returns: Signed Decimal (positive = long, negative = short)

### API Signature Reference
**place_close_order()**: Positional arguments (matching current code style)
```python
# Current code style (positional) - USE THIS
await client.place_close_order(
    client.config.contract_id,  # Contract ID
    quantity,                   # Quantity to close (Decimal)
    Decimal("0"),               # Price (0 = market)
    "buy"                       # Side ("buy" or "sell")
)
```

### Related Analysis
- CSV Analysis: SOL 39 BUY vs 26 SELL, net +12.399 SOL accumulation
- Pattern: UNWIND fills but position remains open
- Evidence: Lines 87-124 show failed unwind followed by new positions
- Root Cause: Order success != Position closed

---

## Revision History

**Iteration 1 (Initial)**:
- Basic plan with snippets
- Missing complete code examples
- Incomplete API signatures
- No dual-cycle pattern handling

**Iteration 2**:
- Complete before/after code for all functions
- Full API signatures with all parameters
- Added `execute_sell_first_cycle()` position verification
- Direction-agnostic position checks using `abs(position) < 0.001`
- Exact integration points with line numbers
- Position state documentation table
- Tolerance value rationale
- Reconciliation behavior on failure specified

**Iteration 3 (Final)**:
- Fixed misleading line numbers (use relative insertion points)
- Removed duplicate validation logic (internal only, no external reconciliation)
- Added type context (get_account_positions returns Decimal)
- Standardized API calls to positional arguments (match current code style)
- Clarified single-layer validation strategy
- Documented relative insertion points for implementation
