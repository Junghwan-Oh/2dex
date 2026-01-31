# DN Pair Bot Liquidation Stabilization Plan

## Context

### Original Request
"DN Pair Bot 청산 로직 안정화 (Liquidation Stabilization)" - Stabilize the UNWIND (liquidation) logic for the DN Pair Bot to prevent position accumulation and manual intervention requirements.

### Background

**Critical Failure Scenario (Cycle 6 - 2026-01-31 01:27:46):**
- ETH buy IOC order: **FAILED to fill** (expired)
- SOL sell IOC order: **FILLED** (0.9 SOL @ $116.71)
- Emergency unwind triggered: "SOL filled but ETH failed, closing SOL position"
- **Bot stopped with SAFETY error**
- **User required manual intervention to close positions**

**Root Cause Analysis:**
1. **IOC orders have high failure rate** - No guaranteed fill mechanism
2. **Emergency unwind is NOT guaranteed** - Uses POST_ONLY orders which can fail
3. **No position verification** - Emergency unwind claims success but never verifies
4. **Missing MARKET order support** - NadoClient lacks `place_market_order()` method

### Interview Summary

**Safety Strategy:**
- Primary constraint: **Safety First** - Accept higher slippage/fees to guarantee position closure
- Verification approach: **Poll Until Closed** - Continuously poll position until abs(pos) < 0.001
- Circuit breaker: **Graceful Halt** - Allow 1 retry with MARKET orders before halting

### Research Findings

**Current Code Issues (from file analysis):**

1. **NadoClient Missing MARKET Orders** (`/Users/botfarmer/2dex/exchanges/nado.py`):
   - Line 477-587: `place_ioc_order()` exists but can fail
   - Line 636-709: `place_close_order()` uses POST_ONLY (not guaranteed to fill)
   - **NO `place_market_order()` method exists**

2. **Emergency Unwind Failures** (`/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`):
   - Line 382-396: `emergency_unwind_eth()` - No return value verification
   - Line 398-412: `emergency_unwind_sol()` - No position check after order
   - Line 357-380: `handle_emergency_unwind()` - No verification of close results

3. **Position Verification Gaps**:
   - Line 436-484: `execute_unwind_cycle()` - Only 3 retries × 2 seconds = 6 seconds max
   - Line 414-427: `execute_build_cycle()` - Only checks at START, not after emergency
   - Line 731-749: Startup check exists, but no verification after emergency unwind failure

4. **Test Coverage Exists** (`/Users/botfarmer/2dex/tests/stage4/dn_pair/test_priority1_unwind_position_verification.py`):
   - Line 70-127: Test demonstrating the bug
   - Line 136-178: Test for successful unwind
   - Line 256-304: Retry logic tests
   - **Tests already written but code needs fixing**

---

## Work Objectives

### Core Objective
**Implement guaranteed position closure for DN Pair Bot UNWIND cycles with 100% position verification to prevent accumulation.**

### Deliverables

1. **Market Order Implementation** (Priority 1)
   - New `place_market_order()` method in NadoClient
   - Aggressive pricing to guarantee fills
   - Comprehensive error handling

2. **Enhanced Emergency Unwind** (Priority 1)
   - Replace POST_ONLY with MARKET orders
   - Position verification with polling
   - Retry logic with escalation

3. **Robust Unwind Cycle** (Priority 2)
   - IOC → MARKET fallback mechanism
   - Increased retry count and timeout
   - Detailed logging at every step

4. **Comprehensive Testing** (Priority 2)
   - Unit tests for new MARKET order method
   - Integration tests for emergency unwind
   - End-to-end tests for failure scenarios

### Definition of Done

- [ ] All acceptance criteria met with 100% test coverage
- [ ] No emergency unwind can succeed without position verification
- [ ] All UNWIND failures trigger MARKET order retry
- [ ] Position accumulation is impossible (prevented by code)
- [ ] All existing tests pass
- [ ] New tests cover all failure scenarios
- [ ] Code review completed
- [ ] Documentation updated

---

## Must Have / Must NOT Have

### Must Have (Guardrails)

**Critical Safety Requirements:**
1. **Every position closure MUST be verified via API** - No log-based success claims
2. **Emergency unwind MUST use MARKET orders** - No POST_ONLY for emergency closure
3. **UNWIND failure MUST trigger MARKET retry** - No silent failures
4. **Position check MUST poll until closed OR timeout** - No single-check assumptions
5. **Startup MUST verify residual positions** - Prevent accumulation across restarts

**Code Quality Requirements:**
1. All new methods must have type hints
2. All new code must have docstrings
3. All failure modes must have tests
4. All critical operations must have detailed logging

### Must NOT Have

**Prohibited Actions:**
1. **MUST NOT use IOC for emergency unwind** - IOC can fail, use MARKET only
2. **MUST NOT assume order success = position closed** - Always verify via API
3. **MUST NOT silently catch exceptions in unwind** - All errors must be logged and surfaced
4. **MUST NOT use POST_ONLY for guaranteed closure** - POST_ONLY can expire unfilled
5. **MUST NOT allow BUILD with residual positions** - Check BEFORE every BUILD

**Anti-Patterns to Avoid:**
1. Using `try/except pass` in unwind logic (currently at lines 395-396, 410-411)
2. Returning `True` from unwind without position verification
3. Logging "position closing" without verification
4. Assuming `OrderResult.success == True` means position closed

---

## Task Flow and Dependencies

```
Phase 1: Critical Safety Infrastructure (Foundation)
├── Task 1.1: Implement place_market_order() in NadoClient
│   └── Blocks: All emergency unwind improvements
├── Task 1.2: Add verify_position_closed() utility
│   └── Blocks: Position verification in unwind
└── Task 1.3: Enhance logging for position state
    └── Blocks: Debugging and monitoring

Phase 2: Emergency Unwind Stabilization (Critical Fixes)
├── Task 2.1: Refactor emergency_unwind_eth() with MARKET + verification
│   ├── Depends on: Task 1.1, Task 1.2
│   └── Blocks: Task 2.3
├── Task 2.2: Refactor emergency_unwind_sol() with MARKET + verification
│   ├── Depends on: Task 1.1, Task 1.2
│   └── Blocks: Task 2.3
└── Task 2.3: Update handle_emergency_unwind() with result verification
    └── Depends on: Task 2.1, Task 2.2

Phase 3: Unwind Cycle Robustness (Production Readiness)
├── Task 3.1: Implement IOC → MARKET fallback in execute_unwind_cycle()
│   ├── Depends on: Task 1.1, Task 2.3
│   └── Blocks: Task 3.3
├── Task 3.2: Increase retry count (3→5) and timeout (2s→5s)
│   ├── Depends on: Task 1.2
│   └── Blocks: Task 3.3
└── Task 3.3: Add graceful retry with MARKET before halt
    └── Depends on: Task 3.1, Task 3.2

Phase 4: Testing & Validation (Quality Assurance)
├── Task 4.1: Unit tests for place_market_order()
│   ├── Depends on: Task 1.1
│   └── Parallel with: Task 4.2
├── Task 4.2: Unit tests for verify_position_closed()
│   ├── Depends on: Task 1.2
│   └── Parallel with: Task 4.1
├── Task 4.3: Integration tests for emergency unwind
│   ├── Depends on: Task 2.3
│   └── Parallel with: Task 4.4
├── Task 4.4: End-to-end tests for failure scenarios
│   ├── Depends on: Task 3.3
│   └── Parallel with: Task 4.3
└── Task 4.5: Run existing test suite and fix failures
    └── Depends on: All previous tasks

Phase 5: Documentation & Handoff (Completion)
├── Task 5.1: Update code documentation
├── Task 5.2: Create runbook for emergency procedures
└── Task 5.3: Final review and sign-off
```

---

## Detailed TODOs with Acceptance Criteria

### Phase 1: Critical Safety Infrastructure

#### Task 1.1: Implement `place_market_order()` in NadoClient
**File:** `/Users/botfarmer/2dex/exchanges/nado.py`

**Implementation:**
```python
async def place_market_order(
    self,
    contract_id: str,
    quantity: Decimal,
    side: str,
    max_slippage_bps: int = 50  # Allow 0.5% slippage for guaranteed fill
) -> OrderResult:
    """
    Place a MARKET order with aggressive pricing for guaranteed execution.

    Uses LIMIT order with aggressive pricing (deeply cross spread) instead of
    IOC to ensure execution while maintaining some price control.

    Args:
        contract_id: Contract ID to trade
        quantity: Order quantity (positive for both buy/sell)
        side: 'buy' or 'sell'
        max_slippage_bps: Maximum acceptable slippage in basis points

    Returns:
        OrderResult with execution details
    """
```

**Acceptance Criteria:**
- [ ] Method places LIMIT order at aggressive price (buy: ask + 5 ticks, sell: bid - 5 ticks)
- [ ] Method uses `OrderType.LIMIT` (NOT IOC or POST_ONLY)
- [ ] Method includes `max_slippage_bps` parameter (default 50 bps = 0.5%)
- [ ] Method returns `OrderResult` with all fields populated
- [ ] Method has 5 retries with exponential backoff (0.1s, 0.2s, 0.4s, 0.8s, 1.6s)
- [ ] Method logs pricing details: "MARKET {side} {qty} @ {price} (aggressive)"
- [ ] Error handling: Returns `OrderResult(success=False)` if all retries fail
- [ ] Type hints on all parameters and return value
- [ ] Docstring with usage examples

**Testing:**
- Unit test: Successful market buy order fills
- Unit test: Successful market sell order fills
- Unit test: Retry logic on network errors
- Unit test: Error handling when exchange unavailable

---

#### Task 1.2: Add `verify_position_closed()` utility to DNPairBot
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
async def verify_position_closed(
    self,
    ticker: str,
    timeout_seconds: int = 30,
    poll_interval: float = 0.5
) -> Tuple[bool, Decimal, int]:
    """
    Verify position is closed by polling until timeout.

    Args:
        ticker: 'ETH' or 'SOL'
        timeout_seconds: Maximum seconds to poll (default 30)
        poll_interval: Seconds between polls (default 0.5)

    Returns:
        Tuple of (is_closed, final_position, poll_count)
    """
```

**Acceptance Criteria:**
- [ ] Method polls position every `poll_interval` seconds
- [ ] Method stops when `abs(position) < 0.001` (POSITION_TOLERANCE)
- [ ] Method stops after `timeout_seconds` (prevents infinite loops)
- [ ] Returns `(True, final_pos, poll_count)` when position closed
- [ ] Returns `(False, final_pos, poll_count)` when timeout
- [ ] Logs every poll: "[VERIFY] {ticker} position: {pos} (attempt {n})"
- [ ] Uses correct client: `self.eth_client` or `self.sol_client`
- [ ] Type hints on all parameters and return value
- [ ] Docstring with usage examples

**Testing:**
- Unit test: Position closes immediately (poll_count = 1)
- Unit test: Position closes after 3 seconds (poll_count = 6)
- Unit test: Position never closes (timeout after 30s)
- Unit test: Network errors during polling

---

#### Task 1.3: Enhance logging for position state
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
- Add logging macro for position state changes
- Log position before EVERY order (BUILD, UNWIND, emergency)
- Log position after EVERY order with verification
- Log position state during polling

**Acceptance Criteria:**
- [ ] Every order placement logs: "[ORDER] {ticker} position BEFORE: {pos}"
- [ ] Every order result logs: "[ORDER] {ticker} position AFTER: {pos}"
- [ ] Emergency unwind logs: "[EMERGENCY] Attempting to close {ticker} position {pos}"
- [ ] Emergency unwind verifies: "[EMERGENCY] {ticker} position AFTER close: {pos}, verified={result}"
- [ ] All position logs include ticker name (ETH/SOL)
- [ ] All position logs use consistent format for grepping
- [ ] No "position closing" logs without verification

---

### Phase 2: Emergency Unwind Stabilization

#### Task 2.1: Refactor `emergency_unwind_eth()` with MARKET + verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 382-396

**Current Implementation (PROBLEMATIC):**
```python
async def emergency_unwind_eth(self):
    if self.eth_client:
        try:
            current_pos = await self.eth_client.get_account_positions()
            if current_pos > 0:
                await self.eth_client.place_close_order(
                    self.eth_client.config.contract_id,
                    current_pos,
                    Decimal("0"),  # Assumes market order, but uses POST_ONLY
                    "sell"
                )
        except Exception:
            pass  # Silent failure - CRITICAL BUG
```

**New Implementation:**
```python
async def emergency_unwind_eth(self) -> bool:
    """
    Emergency unwind ETH position using MARKET order with verification.

    Returns:
        True if position closed successfully, False otherwise
    """
    if not self.eth_client:
        self.logger.error("[EMERGENCY] ETH client not available")
        return False

    try:
        # Get current position
        current_pos = await self.eth_client.get_account_positions()
        self.logger.info(f"[EMERGENCY] ETH position BEFORE close: {current_pos}")

        if abs(current_pos) < Decimal("0.001"):
            self.logger.info("[EMERGENCY] ETH position already closed")
            return True

        # Close with MARKET order (guaranteed execution)
        close_qty = abs(current_pos)
        side = "sell" if current_pos > 0 else "buy"

        result = await self.eth_client.place_market_order(
            self.eth_client.config.contract_id,
            close_qty,
            side
        )

        if not result.success:
            self.logger.error(f"[EMERGENCY] ETH MARKET order failed: {result.error_message}")
            return False

        # Verify position closed
        is_closed, final_pos, poll_count = await self.verify_position_closed("ETH")

        self.logger.info(
            f"[EMERGENCY] ETH position AFTER close: {final_pos}, "
            f"verified={is_closed}, polls={poll_count}"
        )

        if not is_closed:
            self.logger.error(
                f"[EMERGENCY] ETH position NOT CLOSED after MARKET order: {final_pos}"
            )
            return False

        return True

    except Exception as e:
        self.logger.error(f"[EMERGENCY] ETH unwind failed with exception: {e}")
        return False
```

**Acceptance Criteria:**
- [ ] Method returns `bool` (success/failure) - **CRITICAL CHANGE**
- [ ] Uses `place_market_order()` instead of `place_close_order()`
- [ ] Logs position BEFORE closing
- [ ] Logs position AFTER closing with verification result
- [ ] Calls `verify_position_closed("ETH")` with 30s timeout
- [ ] Returns `False` if position not closed after MARKET order
- [ ] Returns `False` on any exception (no silent failures)
- [ ] Returns `True` only if position verified closed
- [ ] Side detection: "sell" if current_pos > 0, "buy" if current_pos < 0
- [ ] Type hints on return value
- [ ] Docstring explaining verification logic

**Testing:**
- Unit test: Successful ETH close with MARKET order
- Unit test: Position verification fails (returns False)
- Unit test: MARKET order fails (returns False)
- Unit test: Network exception during close (returns False, no crash)

---

#### Task 2.2: Refactor `emergency_unwind_sol()` with MARKET + verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 398-412

**Current Implementation (PROBLEMATIC):** Same pattern as ETH - silent failures

**New Implementation:** Identical structure to Task 2.1 but for SOL

**Acceptance Criteria:**
- [ ] Method returns `bool` (success/failure) - **CRITICAL CHANGE**
- [ ] Uses `place_market_order()` instead of `place_close_order()`
- [ ] Logs position BEFORE closing
- [ ] Logs position AFTER closing with verification result
- [ ] Calls `verify_position_closed("SOL")` with 30s timeout
- [ ] Returns `False` if position not closed after MARKET order
- [ ] Returns `False` on any exception (no silent failures)
- [ ] Returns `True` only if position verified closed
- [ ] Side detection: "sell" if current_pos > 0, "buy" if current_pos < 0
- [ ] Type hints on return value
- [ ] Docstring explaining verification logic

**Testing:**
- Unit test: Successful SOL close with MARKET order
- Unit test: Position verification fails (returns False)
- Unit test: MARKET order fails (returns False)
- Unit test: Network exception during close (returns False, no crash)

---

#### Task 2.3: Update `handle_emergency_unwind()` with result verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 357-380

**Current Implementation:**
```python
async def handle_emergency_unwind(self, eth_result, sol_result):
    # Check if one succeeded and other failed
    if eth_filled and not sol_filled:
        await self.emergency_unwind_sol()  # No return value check
    elif sol_filled and not eth_filled:
        await self.emergency_unwind_eth()  # No return value check
```

**New Implementation:**
```python
async def handle_emergency_unwind(self, eth_result: OrderResult, sol_result: OrderResult) -> bool:
    """
    Handle emergency unwind when one leg fails.

    Returns:
        True if emergency unwind succeeded, False otherwise
    """
    # Check fill status
    eth_filled = (isinstance(eth_result, OrderResult) and
                  eth_result.success and
                  eth_result.status == 'FILLED')
    sol_filled = (isinstance(sol_result, OrderResult) and
                  sol_result.success and
                  sol_result.status == 'FILLED')

    # Scenario 1: ETH filled, SOL failed → Close ETH
    if eth_filled and not sol_filled:
        self.logger.warning("[UNWIND] ETH filled but SOL failed, closing ETH position")
        success = await self.emergency_unwind_eth()
        if not success:
            self.logger.error("[UNWIND] Emergency ETH close FAILED - position may be open")
            return False
        self.logger.info("[UNWIND] Emergency ETH close succeeded")
        return False  # Unwind failed overall (SOL not filled)

    # Scenario 2: SOL filled, ETH failed → Close SOL
    elif sol_filled and not eth_filled:
        self.logger.warning("[UNWIND] SOL filled but ETH failed, closing SOL position")
        success = await self.emergency_unwind_sol()
        if not success:
            self.logger.error("[UNWIND] Emergency SOL close FAILED - position may be open")
            return False
        self.logger.info("[UNWIND] Emergency SOL close succeeded")
        return False  # Unwind failed overall (ETH not filled)

    # Scenario 3: Both failed or both filled → No emergency unwind needed
    return True
```

**Acceptance Criteria:**
- [ ] Method returns `bool` indicating emergency unwind success
- [ ] Checks return value from `emergency_unwind_eth()` - **CRITICAL**
- [ ] Checks return value from `emergency_unwind_sol()` - **CRITICAL**
- [ ] Logs "[UNWIND] Emergency ETH/SOL close FAILED" if verification fails
- [ ] Returns `False` if emergency unwind fails
- [ ] Returns `False` if one leg filled (unwind incomplete)
- [ ] Returns `True` only if both filled or both failed
- [ ] Type hints on parameters and return value
- [ ] Docstring explaining scenarios

**Testing:**
- Unit test: ETH filled, SOL failed → ETH close succeeds
- Unit test: ETH filled, SOL failed → ETH close fails (returns False)
- Unit test: SOL filled, ETH failed → SOL close succeeds
- Unit test: SOL filled, ETH failed → SOL close fails (returns False)
- Unit test: Both filled → No emergency unwind
- Unit test: Both failed → No emergency unwind

---

### Phase 3: Unwind Cycle Robustness

#### Task 3.1: Implement IOC → MARKET fallback in `execute_unwind_cycle()`
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 436-484

**Current Implementation (IOC only):**
```python
async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
    # Place IOC orders
    eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

    # Check if orders filled
    if not (eth_result.success and sol_result.success):
        return False  # No retry, no fallback

    # Verify positions closed with retries
    for attempt in range(MAX_RETRIES):
        # ... polling logic ...
```

**New Implementation (IOC with MARKET fallback):**
```python
async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
    """
    Execute UNWIND cycle with IOC → MARKET fallback.

    Strategy:
    1. Try IOC orders first (fast, low fees)
    2. If IOC fails, fallback to MARKET orders (guaranteed fill)
    3. Verify positions closed with polling
    4. Retry if verification fails

    Returns:
        True if both positions verified closed, False otherwise
    """
    POSITION_TOLERANCE = Decimal("0.001")
    MAX_RETRIES = 5  # Increased from 3
    RETRY_DELAY = 5.0  # Increased from 2.0

    # Log pre-unwind positions
    eth_pos_before = await self.eth_client.get_account_positions()
    sol_pos_before = await self.sol_client.get_account_positions()
    self.logger.info(f"[UNWIND] POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")

    # Attempt 1: IOC orders (fast, low fees)
    self.logger.info(f"[UNWIND] Attempt 1: IOC orders")
    eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

    # Check if IOC succeeded
    ioc_success = (
        isinstance(eth_result, OrderResult) and eth_result.success and eth_result.status == 'FILLED' and
        isinstance(sol_result, OrderResult) and sol_result.success and sol_result.status == 'FILLED'
    )

    if not ioc_success:
        # IOC failed - fallback to MARKET orders
        self.logger.warning(
            f"[UNWIND] IOC orders failed (ETH: {eth_result.status}, SOL: {sol_result.status})"
        )
        self.logger.info("[UNWIND] Fallback: MARKET orders for guaranteed execution")

        # Place MARKET orders for both legs
        eth_result = await self.eth_client.place_market_order(
            self.eth_client.config.contract_id,
            abs(eth_pos_before),
            eth_side
        )
        sol_result = await self.sol_client.place_market_order(
            self.sol_client.config.contract_id,
            abs(sol_pos_before),
            sol_side
        )

        if not eth_result.success or not sol_result.success:
            self.logger.error("[UNWIND] MARKET orders failed - cannot close positions")
            return False

    # Verify positions closed with retries
    for attempt in range(MAX_RETRIES):
        await asyncio.sleep(RETRY_DELAY)

        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        self.logger.info(f"[UNWIND] POSITIONS CHECK (attempt {attempt + 1}/{MAX_RETRIES}): ETH={eth_pos}, SOL={sol_pos}")

        eth_closed = abs(eth_pos) < POSITION_TOLERANCE
        sol_closed = abs(sol_pos) < POSITION_TOLERANCE

        if eth_closed and sol_closed:
            self.logger.info("[UNWIND] SUCCESS: Both positions verified closed")
            return True

        if attempt < MAX_RETRIES - 1:
            self.logger.warning(f"[UNWIND] Positions still open, retrying in {RETRY_DELAY}s...")

    self.logger.error(f"[UNWIND] FAILED: Positions still open after {MAX_RETRIES} retries: ETH={eth_pos}, SOL={sol_pos}")
    return False
```

**Acceptance Criteria:**
- [ ] First attempts IOC orders (existing behavior)
- [ ] If IOC fails (not FILLED), logs fallback reason
- [ ] Fallback uses `place_market_order()` for BOTH legs
- [ ] MARKET orders use absolute position size from BEFORE unwind
- [ ] Logs "FALLBACK: MARKET orders" when IOC fails
- [ ] Returns `False` if MARKET orders fail
- [ ] Increases MAX_RETRIES from 3 to 5
- [ ] Increases RETRY_DELAY from 2.0 to 5.0 seconds
- [ ] Verification polls up to 5 times × 5 seconds = 25 seconds max
- [ ] Logs "SUCCESS: Both positions verified closed" only when verified
- [ ] Type hints on all parameters and return value
- [ ] Docstring explaining IOC → MARKET fallback

**Testing:**
- Unit test: IOC succeeds → No fallback
- Unit test: IOC fails ETH → MARKET fallback for both
- Unit test: IOC fails SOL → MARKET fallback for both
- Unit test: IOC fails both → MARKET fallback for both
- Unit test: MARKET fallback succeeds
- Unit test: MARKET fallback fails (returns False)
- Integration test: Full cycle with IOC failure

---

#### Task 3.2: Increase retry count and timeout in position verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Changes:**
- `MAX_RETRIES`: 3 → 5 (line 447)
- `RETRY_DELAY`: 2.0 → 5.0 seconds (line 448)
- `verify_position_closed()`: Default timeout 30 seconds, poll interval 0.5s

**Acceptance Criteria:**
- [ ] MAX_RETRIES = 5 in `execute_unwind_cycle()`
- [ ] RETRY_DELAY = 5.0 in `execute_unwind_cycle()`
- [ ] `verify_position_closed()` defaults: timeout=30s, interval=0.5s
- [ ] Total verification time: 5 retries × 5 seconds = 25 seconds max
- [ ] Allow sufficient time for exchange API delays

---

#### Task 3.3: Add graceful retry with MARKET before halt
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 543-574

**Current Implementation:**
```python
async def run_alternating_strategy(self) -> List[bool]:
    for i in range(self.iterations):
        result = await self.execute_buy_first_cycle() or self.execute_sell_first_cycle()

        # CRITICAL: Stop if UNWIND failed
        if not result:
            self.logger.error(f"[SAFETY] Cycle {iteration_num} FAILED! Bot stopping...")
            break  # Immediate halt - too conservative
```

**New Implementation (Graceful Halt):**
```python
async def run_alternating_strategy(self) -> List[bool]:
    """Run alternating strategy for N iterations with graceful recovery."""
    results = []
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 2  # Allow 1 retry before permanent halt

    for i in range(self.iterations):
        iteration_num = i + 1
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ITERATION {iteration_num}/{self.iterations}")
        self.logger.info(f"{'='*60}")

        # Execute cycle
        if i % 2 == 0:
            result = await self.execute_buy_first_cycle()
        else:
            result = await self.execute_sell_first_cycle()

        # Check for failure
        if not result:
            consecutive_failures += 1
            self.logger.error(f"[SAFETY] Cycle {iteration_num} FAILED!")

            # Graceful retry attempt
            if consecutive_failures < MAX_CONSECUTIVE_FAILURES:
                self.logger.warning(
                    f"[RECOVERY] Attempting emergency MARKET unwind before halt..."
                )

                # Force close both positions with MARKET orders
                recovery_success = await self.emergency_recovery_unwind()

                if recovery_success:
                    self.logger.info("[RECOVERY] Emergency MARKET unwind succeeded - resuming")
                    consecutive_failures = 0  # Reset counter
                    results.append(True)
                    continue
                else:
                    self.logger.error("[RECOVERY] Emergency MARKET unwind FAILED - halting")
            else:
                self.logger.error(
                    f"[SAFETY] {MAX_CONSECUTIVE_FAILURES} consecutive failures! "
                    f"Bot halting to prevent accumulation."
                )

            self.logger.error(
                f"[SAFETY] Check positions manually before restarting. "
                f"ETH and SOL positions should be near 0."
            )
            break
        else:
            consecutive_failures = 0  # Reset on success
            results.append(True)
            self.logger.info(f"[SUCCESS] Cycle {iteration_num} completed successfully")

    return results


async def emergency_recovery_unwind(self) -> bool:
    """
    Emergency recovery: Force close both positions with MARKET orders.

    Returns:
        True if both positions verified closed, False otherwise
    """
    self.logger.info("[RECOVERY] Starting emergency MARKET unwind for both positions")

    # Close both positions with MARKET orders
    eth_success = await self.emergency_unwind_eth()
    sol_success = await self.emergency_unwind_sol()

    if eth_success and sol_success:
        self.logger.info("[RECOVERY] Both positions closed successfully")
        return True
    else:
        self.logger.error(
            f"[RECOVERY] Emergency unwind incomplete: "
            f"ETH={'closed' if eth_success else 'OPEN'}, "
            f"SOL={'closed' if sol_success else 'OPEN'}"
        )
        return False
```

**Acceptance Criteria:**
- [ ] Tracks `consecutive_failures` counter
- [ ] Allows 1 retry before permanent halt (`MAX_CONSECUTIVE_FAILURES = 2`)
- [ ] First failure triggers `emergency_recovery_unwind()`
- [ ] `emergency_recovery_unwind()` closes BOTH positions with MARKET
- [ ] Verifies BOTH positions closed before returning True
- [ ] If recovery succeeds, resets counter and continues trading
- [ ] If recovery fails, halts with SAFETY error
- [ ] Logs "[RECOVERY] Attempting emergency MARKET unwind"
- [ ] Logs "[RECOVERY] Emergency MARKET unwind succeeded/FAILED"
- [ ] Type hints on all new methods
- [ ] Docstrings explaining recovery logic

**Testing:**
- Unit test: Single failure → Recovery succeeds → Resumes trading
- Unit test: Single failure → Recovery fails → Halts
- Unit test: Two consecutive failures → Halts without second recovery
- Unit test: Recovery after IOC failure
- Unit test: Recovery after network error
- Integration test: Full strategy with transient failure

---

### Phase 4: Testing & Validation

#### Task 4.1: Unit tests for `place_market_order()`
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_market_order.py` (new file)

**Test Cases:**
```python
class TestPlaceMarketOrder:
    """Unit tests for place_market_order() in NadoClient."""

    async def test_market_buy_order_fills(self):
        """Test MARKET buy order fills successfully."""
        # Setup mock client with BBO: bid=2700, ask=2701
        # Expect order at ask+5ticks = 2701.0005 (aggressive)
        # Verify order placed and filled

    async def test_market_sell_order_fills(self):
        """Test MARKET sell order fills successfully."""
        # Setup mock client with BBO: bid=2700, ask=2701
        # Expect order at bid-5ticks = 2699.9995 (aggressive)
        # Verify order placed and filled

    async def test_market_order_retry_on_network_error(self):
        """Test MARKET order retries on network errors."""
        # Mock first 2 calls to fail, 3rd to succeed
        # Verify retry attempts with exponential backoff
        # Verify success after retries

    async def test_market_order_returns_failure_on_max_retries(self):
        """Test MARKET order fails after max retries."""
        # Mock all calls to fail
        # Verify returns OrderResult(success=False)
        # Verify error message populated

    async def test_market_order_respects_max_slippage(self):
        """Test MARKET order respects max_slippage_bps parameter."""
        # Test with max_slippage_bps=10 (0.1%)
        # Test with max_slippage_bps=100 (1%)
        # Verify pricing within slippage limit
```

**Acceptance Criteria:**
- [ ] All tests pass with mocked NadoClient
- [ ] Test coverage > 90% for `place_market_order()`
- [ ] Edge cases covered: network errors, retries, slippage
- [ ] Assertions verify OrderResult fields populated correctly

---

#### Task 4.2: Unit tests for `verify_position_closed()`
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_verify_position.py` (new file)

**Test Cases:**
```python
class TestVerifyPositionClosed:
    """Unit tests for verify_position_closed() in DNPairBot."""

    async def test_position_closes_immediately(self):
        """Test position closes immediately (poll_count = 1)."""
        # Mock: First poll returns 0.0
        # Expect: (True, 0.0, 1)

    async def test_position_closes_after_3_seconds(self):
        """Test position closes after 3 seconds (poll_count = 6)."""
        # Mock: First 5 polls return 0.5, 6th poll returns 0.0
        # Expect: (True, 0.0, 6)

    async def test_position_never_closes_timeout(self):
        """Test position timeout after 30 seconds."""
        # Mock: All polls return 0.5 (never closes)
        # Expect: (False, 0.5, 60)  # 60 polls = 30s / 0.5s interval
        # Verify timeout not exceeded

    async def test_position_below_tolerance(self):
        """Test position below tolerance is considered closed."""
        # Mock: Poll returns 0.0005 (< 0.001)
        # Expect: (True, 0.0005, 1)

    async def test_network_errors_during_polling(self):
        """Test network errors during position polling."""
        # Mock: First 2 polls raise Exception, 3rd succeeds
        # Verify: Exception handled, polling continues
        # Expect: (True, 0.0, 3)
```

**Acceptance Criteria:**
- [ ] All tests pass with mocked ETH/SOL clients
- [ ] Test coverage > 95% for `verify_position_closed()`
- [ ] Edge cases covered: timeout, tolerance, network errors
- [ ] Assertions verify return tuple (is_closed, final_pos, poll_count)

---

#### Task 4.3: Integration tests for emergency unwind
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_emergency_unwind.py` (new file)

**Test Cases:**
```python
class TestEmergencyUnwind:
    """Integration tests for emergency unwind logic."""

    async def test_emergency_unwind_eth_succeeds(self):
        """Test emergency_unwind_eth() succeeds with MARKET order."""
        # Setup: ETH position = 0.05
        # Mock: place_market_order() succeeds
        # Mock: verify_position_closed() returns (True, 0.0, 3)
        # Expect: returns True
        # Verify: logs include "verified=True"

    async def test_emergency_unwind_eth_fails_verification(self):
        """Test emergency_unwind_eth() fails when position not closed."""
        # Setup: ETH position = 0.05
        # Mock: place_market_order() succeeds
        # Mock: verify_position_closed() returns (False, 0.03, 60) # timeout
        # Expect: returns False
        # Verify: logs include "NOT CLOSED after MARKET order"

    async def test_emergency_unwind_sol_succeeds(self):
        """Test emergency_unwind_sol() succeeds with MARKET order."""
        # Setup: SOL position = -0.5
        # Mock: place_market_order() succeeds
        # Mock: verify_position_closed() returns (True, 0.0, 2)
        # Expect: returns True

    async def test_emergency_unwind_with_exception(self):
        """Test emergency_unwind handles exceptions gracefully."""
        # Mock: place_market_order() raises Exception
        # Expect: returns False (no crash)
        # Verify: logs include "exception"
```

**Acceptance Criteria:**
- [ ] All tests pass with integration mocks
- [ ] Test coverage = 100% for emergency unwind methods
- [ ] Exception handling verified
- [ ] Verification logic tested

---

#### Task 4.4: End-to-end tests for failure scenarios
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_failure_scenarios.py` (new file)

**Test Cases:**
```python
class TestFailureScenarios:
    """End-to-end tests for UNWIND failure scenarios."""

    async def test_ioc_fails_market_fallback_succeeds(self):
        """Test IOC failure → MARKET fallback → Success."""
        # Setup: Open positions ETH=0.05, SOL=-0.5
        # Mock: IOC orders fail (not FILLED)
        # Mock: MARKET orders succeed
        # Mock: Positions verify closed
        # Run: execute_unwind_cycle()
        # Expect: returns True
        # Verify: logs include "FALLBACK: MARKET orders"

    async def test_ioc_fails_market_fallback_fails(self):
        """Test IOC failure → MARKET fallback → Failure."""
        # Setup: Open positions ETH=0.05, SOL=-0.5
        # Mock: IOC orders fail
        # Mock: MARKET orders fail
        # Run: execute_unwind_cycle()
        # Expect: returns False
        # Verify: logs include "MARKET orders failed"

    async def test_cycle_6_scenario_reproduction(self):
        """Test reproduce Cycle 6 failure scenario."""
        # Setup: Recreate exact Cycle 6 conditions
        # Mock: ETH IOC fails, SOL IOC fills
        # Mock: Emergency SOL unwind succeeds with MARKET
        # Run: execute_unwind_cycle()
        # Expect: Returns False (SOL closed, ETH not filled)
        # Verify: No position accumulation

    async def test_graceful_recovery_after_failure(self):
        """Test graceful recovery with MARKET retry."""
        # Setup: run_alternating_strategy() with 3 iterations
        # Mock: Cycle 2 fails, recovery succeeds
        # Mock: Cycle 3 succeeds
        # Run: strategy
        # Expect: results = [True, True, True] (recovery succeeded)
        # Verify: logs include "RECOVERY" and "resuming"

    async def test_permanent_halt_after_recovery_failure(self):
        """Test permanent halt when recovery fails."""
        # Setup: run_alternating_strategy() with 3 iterations
        # Mock: Cycle 2 fails, recovery fails
        # Run: strategy
        # Expect: Halts after Cycle 2
        # Verify: logs include "consecutive failures" and "halting"
```

**Acceptance Criteria:**
- [ ] All tests pass with full integration mocks
- [ ] Cycle 6 scenario reproducible and fixable
- [ ] Recovery logic tested end-to-end
- [ ] Permanent halt logic verified

---

#### Task 4.5: Run existing test suite and fix failures
**Files:** All existing tests

**Actions:**
1. Run existing test suite: `pytest tests/stage4/dn_pair/ -v`
2. Fix any breaking changes from refactoring
3. Ensure all existing tests still pass
4. Update tests if needed (e.g., return value changes)

**Acceptance Criteria:**
- [ ] All existing tests pass
- [ ] `test_priority1_unwind_position_verification.py` passes
- [ ] No regressions introduced
- [ ] Test coverage maintained or increased

---

### Phase 5: Documentation & Handoff

#### Task 5.1: Update code documentation
**Files:** All modified files

**Actions:**
- Update docstrings for modified methods
- Add usage examples for new methods
- Document emergency unwind flow in comments
- Update type hints for all modified signatures

**Acceptance Criteria:**
- [ ] All new methods have comprehensive docstrings
- [ ] All modified methods have updated docstrings
- [ ] Type hints present on all public methods
- [ ] Complex logic has inline comments

---

#### Task 5.2: Create runbook for emergency procedures
**File:** `/Users/botfarmer/2dex/docs/dn-pair-emergency-runbook.md` (new file)

**Content:**
```markdown
# DN Pair Bot Emergency Runbook

## Automatic Recovery Procedures

### IOC Order Failure
**Trigger:** IOC order expires without fill
**Automatic Action:**
1. Bot detects IOC failure (OrderResult.status != 'FILLED')
2. Logs: "[UNWIND] IOC orders failed - Fallback: MARKET orders"
3. Places MARKET orders for both legs
4. Verifies positions closed with polling (30s timeout)
5. Resumes trading if successful, halts if failed

**Manual Intervention Required:** No (automatic)

### Emergency Unwind Triggered
**Trigger:** One leg fills, other fails
**Automatic Action:**
1. Bot detects asymmetric fill (e.g., ETH filled, SOL failed)
2. Logs: "[UNWIND] SOL filled but ETH failed, closing SOL position"
3. Closes filled leg with MARKET order
4. Verifies position closed with polling
5. Returns False (cycle failed)

**Manual Intervention Required:** No (automatic)

### Graceful Recovery Attempt
**Trigger:** First cycle failure
**Automatic Action:**
1. Bot logs: "[RECOVERY] Attempting emergency MARKET unwind"
2. Closes BOTH positions with MARKET orders
3. Verifies BOTH positions closed
4. Resumes trading if successful
5. Halts if recovery fails

**Manual Intervention Required:** No (automatic)

## Manual Recovery Procedures

### Bot Halted with Open Positions
**Trigger:** Automatic recovery failed
**Symptoms:**
- Log: "[SAFETY] Cycle N FAILED! Bot stopping..."
- Log: "[SAFETY] Check positions manually before restarting"

**Manual Steps:**
1. Check positions on exchange UI
2. If positions exist, run manual close script:
   ```bash
   cd /Users/botfarmer/2dex/hedge
   python close_positions.py
   ```
3. Verify positions closed (output should show "✅ Positions closed successfully!")
4. Do NOT restart bot until positions = 0

### Persistent Position Accumulation
**Trigger:** Multiple cycles with partial closes
**Symptoms:**
- Log shows "Position BEFORE" increasing each cycle
- Exchange UI shows large positions (>10x notional)

**Manual Steps:**
1. **STOP THE BOT IMMEDIATELY**
2. Check all positions on exchange UI
3. Calculate total exposure (sum of all positions)
4. Close all positions manually via exchange UI
5. Review logs for root cause (likely IOC failures)
6. Consider switching to MARKET-only mode if IOC unreliable
7. Do NOT restart until root cause identified and fixed

## Monitoring and Alerts

### Key Log Patterns to Monitor
- `[UNWIND] IOC orders failed` - IOC failure rate
- `[RECOVERY] Attempting emergency MARKET unwind` - Recovery attempts
- `[UNWIND] FAILED: Positions still open` - Verification failures
- `[SAFETY] Cycle N FAILED` - Cycle failures

### Healthy Operation Indicators
- Most cycles: `[SUCCESS] Cycle N completed successfully`
- Few IOC fallbacks: <10% of cycles
- Zero emergency unwinds: Should never happen in healthy operation
- Zero recovery attempts: Should never happen in healthy operation

### Degraded Operation Indicators
- Frequent IOC fallbacks: >20% of cycles
- Emergency unwinds occurring: Indicates asymmetric fills
- Recovery attempts: Indicates IOC + MARKET failures

## Configuration Tuning

### Conservative Mode (Highest Safety)
```python
# In DN_pair_eth_sol_nado.py
MAX_RETRIES = 10  # More retries
RETRY_DELAY = 10.0  # Longer delay
MAX_CONSECUTIVE_FAILURES = 1  # Halt immediately
```

### Balanced Mode (Default)
```python
MAX_RETRIES = 5
RETRY_DELAY = 5.0
MAX_CONSECUTIVE_FAILURES = 2  # Allow 1 recovery
```

### Aggressive Mode (Lowest Safety, Not Recommended)
```python
MAX_RETRIES = 3
RETRY_DELAY = 2.0
MAX_CONSECUTIVE_FAILURES = 3  # Allow 2 recoveries
```

## Contact and Escalation
- Developer: [Your contact]
- On-call: [On-call procedure]
- Emergency: [Emergency shutdown procedure]
```

**Acceptance Criteria:**
- [ ] Runbook covers all emergency scenarios
- [ ] Manual procedures are clear and step-by-step
- [ ] Automatic procedures documented with log examples
- [ ] Monitoring guidelines included
- [ ] Configuration tuning options documented

---

#### Task 5.3: Final review and sign-off
**Actions:**
- Review all code changes
- Review all test results
- Review documentation
- Sign-off on deployment readiness

**Acceptance Criteria:**
- [ ] All tasks completed
- [ ] All tests pass (unit + integration + e2e)
- [ ] Code review approved
- [ ] Documentation complete
- [ ] Ready for deployment

---

## Commit Strategy

### Commit 1: Phase 1 - Critical Infrastructure
```
feat(nado): Implement MARKET order support for guaranteed position closure

- Add place_market_order() method to NadoClient
- Implement aggressive pricing for guaranteed fills
- Add verify_position_closed() utility with polling
- Enhance position logging throughout bot lifecycle

Closes: Task 1.1, Task 1.2, Task 1.3
Risk: Critical - Foundation for all subsequent fixes
Test: Unit tests for new methods
```

### Commit 2: Phase 2 - Emergency Unwind Fixes
```
fix(dn-pair): Stabilize emergency unwind with MARKET orders and verification

- Refactor emergency_unwind_eth() to return bool and verify closure
- Refactor emergency_unwind_sol() to return bool and verify closure
- Update handle_emergency_unwind() to check return values
- Fix silent exception handling (no more try/except pass)

Critical fix: Emergency unwind now GUARANTEED to close positions or report failure
Previous behavior: Logged "closing position" but never verified

Closes: Task 2.1, Task 2.2, Task 2.3
Risk: Critical - Fixes root cause of position accumulation
Test: Integration tests for emergency unwind
```

### Commit 3: Phase 3 - Unwind Cycle Robustness
```
feat(dn-pair): Add IOC → MARKET fallback and graceful recovery

- Implement IOC → MARKET fallback in execute_unwind_cycle()
- Increase retry count (3→5) and timeout (2s→5s)
- Add graceful recovery with MARKET retry before halt
- Implement emergency_recovery_unwind() for forced closure

Benefits:
- IOC orders still fast when they work (low fees)
- Automatic MARKET fallback when IOC fails (guaranteed close)
- Graceful recovery before permanent halt (reduces manual intervention)

Closes: Task 3.1, Task 3.2, Task 3.3
Risk: High - Changes core unwind logic
Test: End-to-end tests for failure scenarios
```

### Commit 4: Phase 4 - Comprehensive Testing
```
test(dn-pair): Add comprehensive test coverage for liquidation stabilization

- Unit tests for place_market_order() (4 test cases)
- Unit tests for verify_position_closed() (5 test cases)
- Integration tests for emergency unwind (4 test cases)
- End-to-end tests for failure scenarios (5 test cases)
- Fix any failures in existing test suite

Coverage: 100% of emergency unwind paths, 95%+ of new code
Closes: Task 4.1, Task 4.2, Task 4.3, Task 4.4, Task 4.5
Risk: Low - Test-only changes
Test: All tests pass
```

### Commit 5: Phase 5 - Documentation
```
docs(dn-pair): Add emergency runbook and update code documentation

- Create comprehensive emergency runbook
- Update docstrings for all modified methods
- Add usage examples for new methods
- Document emergency unwind flow in comments

Closes: Task 5.1, Task 5.2, Task 5.3
Risk: Low - Documentation only
Test: N/A
```

---

## Success Criteria

### Functional Requirements
- [ ] **100% of emergency unwinds verify position closure** - No more "assumed" closures
- [ ] **100% of UNWIND failures trigger MARKET retry** - No silent failures
- [ ] **0% position accumulation possible** - Code prevents accumulation at every level
- [ ] **99%+ of UNWIND cycles succeed on first attempt** - IOC → MARKET fallback effective

### Quality Requirements
- [ ] **Test coverage > 90%** for all new code
- [ ] **All existing tests pass** - No regressions
- [ ] **Type hints on all public methods** - Maintainability
- [ ] **Comprehensive logging** - All critical operations logged

### Safety Requirements
- [ ] **Emergency unwind cannot succeed without verification** - Enforced by return type
- [ ] **No silent exception handling** - All errors logged and surfaced
- [ ] **Position accumulation impossible** - Multiple safeguards prevent
- [ ] **Manual intervention still works** - close_positions.py script maintained

### Performance Requirements
- [ ] **Normal UNWIND (IOC success): < 2 seconds** - No performance regression
- [ ] **IOC → MARKET fallback: < 10 seconds** - Acceptable for safety
- [ ] **Emergency unwind: < 35 seconds** - 30s verification timeout + 5s execution
- [ ] **Graceful recovery: < 40 seconds** - Both positions closed + verification

### Operational Requirements
- [ ] **Deployment requires zero config changes** - Drop-in replacement
- [ ] **Backward compatible with existing scripts** - No breaking changes
- [ ] **Emergency runbook available** - Ops team trained on procedures
- [ ] **Monitoring alerts defined** - Log patterns for alerting

---

## Risk Mitigation

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| MARKET order slippage | Limit to 50 bps (0.5%) | Add max slippage config |
| Exchange API delays | 30s verification timeout | Increase to 60s if needed |
| Network errors | 5 retries with exponential backoff | Circuit breaker to halt |
| Position check failures | Poll until timeout, then halt | Manual close script |
| Test flakiness | Mock all external dependencies | Run tests multiple times |
| Deployment issues | Feature flag for MARKET mode | Rollback to IOC-only |

---

## Rollback Plan

If critical issues discovered after deployment:

1. **Immediate Rollback:** Revert to commit before Phase 3 (keep Phase 1-2 for safety)
2. **Partial Rollback:** Disable IOC → MARKET fallback (keep emergency unwind fixes)
3. **Configuration Rollback:** Set `MAX_CONSECUTIVE_FAILURES = 1` (halt immediately)
4. **Manual Override:** Use `close_positions.py` script for all closures

**Rollback Command:**
```bash
cd /Users/botfarmer/2dex
git revert <commit-hash>
# Or use feature flag:
export DN_PAIR_USE_MARKET_FALLBACK=false
```

---

## Notes

- This plan prioritizes **safety over cost** - MARKET orders may have higher slippage than IOC, but guaranteed closure is worth the cost
- The existing test at `tests/stage4/dn_pair/test_priority1_unwind_position_verification.py` already demonstrates the bug - this plan fixes it
- Emergency unwind is the **last line of defense** - it must never fail silently
- IOC orders are still used for **normal operation** - MARKET is only for fallbacks and emergencies
- The `place_market_order()` implementation should be reviewed by a Nado exchange expert to ensure aggressive pricing is correct

---

**Plan Version:** 1.0
**Created:** 2026-01-31
**Priority:** CRITICAL - Position accumulation is causing financial losses
**Estimated Effort:** 8-12 hours (split across phases)
**Dependencies:** Nado exchange API access for testing MARKET orders
