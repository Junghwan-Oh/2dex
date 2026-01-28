# DN Bot Timeout Optimization + Post-Mortem Report

**Date**: 2026-01-26
**Status**: RALPLAN COMPREHENSIVE PLAN (REVISED)
**Working Commit**: 0b17cea (BUILD/UNWIND comprehensive fix + GRVT cold start solution)

---

## Part 1: POST-MORTEM - Agent Failure Analysis

### What Happened

**Timeline of Events**:
1. **Working State**: Commit 0b17cea was functioning correctly
   - BUILD/UNWIND logic working
   - GRVT cold start workaround in place
   - Emergency unwind implemented
   - Test passed: ETH 0.5, 1 iteration

2. **User Requests**: Two optimization tasks
   - Task 1: "Remove Primary 10s timeout - speed up execution"
   - Task 2: "Change GRVT to LIMIT orders for maker fees"

3. **Agent Delegation**: Executor-low agents were delegated to implement

4. **CRITICAL FAILURE**: Agents introduced **broken buy/sell logic** in GRVT LIMIT order code

**Evidence of Failure**:
```python
# BROKEN CODE introduced by agent (lines 806-813 in multiple .tmp files):
if side == "buy":
    order_price = best_ask + self.hedge_tick_size
    post_only_side = "sell"  # WRONG! Should be "buy"
else:
    order_price = best_bid - self.hedge_tick_size
    post_only_side = "buy"   # WRONG! Should be "sell"
```

**Impact**:
- If bot wants to BUY hedge → places SELL order → OPPOSITE DIRECTION
- If bot wants to SELL hedge → places BUY order → OPPOSITE DIRECTION
- **Doubles position instead of hedging**
- **Complete loss of delta neutrality**

---

### Root Cause Analysis

#### 1. Agent Prompt Interpretation Failure

**What the Agent Was Asked**:
```
"Change GRVT to LIMIT orders for maker fees"
```

**What the Agent Likely Misunderstood**:
The agent saw "POST_ONLY LIMIT orders for maker fees" and **incorrectly assumed** that POST_ONLY orders must be placed on the **opposite side** of the order book.

**The Flawed Logic Chain**:
1. POST_ONLY means "don't cross the spread"
2. To avoid crossing, agent thought "post on opposite side"
3. Agent flipped `post_only_side` variable
4. **Result**: Buy orders became sell orders, sell orders became buy orders

**Why This Happened**:
- **Lack of trading domain knowledge**: Agent didn't understand that POST_ONLY orders are still placed in the **intended direction**, just at conservative prices
- **Missing context**: Agent wasn't told this is a HEDGING bot where direction is critical
- **No verification step**: Agent didn't validate the logic against working code

#### 2. Misunderstanding POST_ONLY Mechanics

**Correct POST_ONLY Behavior**:
```python
# CORRECT: Place BUY order on BID side (conservative price)
if side == "buy":
    order_price = best_bid - tick_size  # BELOW best bid (conservative)
    post_only_side = "buy"              # Still a BUY order
```

**Agent's Incorrect Interpretation**:
```python
# WRONG: Place BUY order on ASK side (crosses spread)
if side == "buy":
    order_price = best_ask + tick_size  # ABOVE best ask (aggressive)
    post_only_side = "sell"             # Flipped to SELL
```

**The Agent's Error**:
- Thought "POST_ONLY on opposite side" meant "flip the direction"
- Actually means "place on same side, but at passive price"

---

### Why the Agent Flipped buy/sell

**Hypothesis 1: Ambiguous Variable Name**
```python
post_only_side = "sell"  # Agent thought this meant "side of order book"
                           # Not "direction of trade"
```

**Hypothesis 2: Confusion with "Opposite Side" Terminology**
- In order book terminology: "opposite side" = bid vs ask
- In trading terminology: "opposite side" = buy vs sell
- Agent mixed these concepts

**Hypothesis 3: No Understanding of Hedge Logic**
- Agent didn't realize this is a delta-neutral strategy
- Didn't understand that flipping direction breaks the hedge
- **Never asked**: "Will this change the hedge direction?"

---

### Prevention Strategies

#### Strategy 1: Add Pre-Flight Validation Check

**Add to `place_hedge_order()` method**:
```python
# CRITICAL: Validate order direction before placement
if self.hedge_exchange.lower() == "grvt" and "post_only" in str(order_type).lower():
    # Verify hedge direction matches intended direction
    # Use internal position tracking, not API call
    intended_hedge_side = "sell" if self.primary_position > 0 else "buy"
    actual_hedge_side = side

    if intended_hedge_side != actual_hedge_side:
        self.logger.error(
            f"[CRITICAL] Hedge direction MISMATCH! "
            f"Primary={self.primary_position}, intended={intended_hedge_side}, actual={actual_hedge_side}"
        )
        raise Exception("HEDGE_DIRECTION_ERROR: Agent may have flipped buy/sell")
```

**Benefit**: Catches direction errors BEFORE order placement

#### Strategy 2: Add Unit Tests for Hedge Direction

**Create `tests/test_hedge_direction.py`** (NOTE: tests/ directory must be created first):
```python
def test_hedge_buy_direction():
    """Verify BUY hedge places BUY order, not SELL"""
    bot = DNHedgeBot(...)  # CORRECTED: Use actual class name
    bot.primary_position = Decimal("1.0")  # LONG position
    bot.hedge_position = Decimal("0.0")    # No hedge

    # Should place SELL to hedge LONG position
    result = bot.place_hedge_order(side="sell", quantity=Decimal("1.0"))
    assert result == True
    assert bot.hedge_position < 0  # SHORT hedge created

def test_hedge_sell_direction():
    """Verify SELL hedge places SELL order, not BUY"""
    bot = DNHedgeBot(...)  # CORRECTED: Use actual class name
    bot.primary_position = Decimal("-1.0")  # SHORT position
    bot.hedge_position = Decimal("0.0")     # No hedge

    # Should place BUY to hedge SHORT position
    result = bot.place_hedge_order(side="buy", quantity=Decimal("1.0"))
    assert result == True
    assert bot.hedge_position > 0  # LONG hedge created
```

**Benefit**: Automated detection of direction flips

#### Strategy 3: Add Agent Prompt Guardrails

**When delegating to executor agents, always include**:
```python
AGENT_PROMPT_TEMPLATE = """
CRITICAL CONSTRAINTS:
- This is a DELTA-NEUTRAL HEDGING bot
- Direction is CRITICAL: Buy hedge ≠ Buy order
- NEVER flip buy/sell direction without EXPLICIT user request
- If you change order logic, you MUST explain impact on hedge direction

TASK: {task_description}

CONTEXT:
- Primary position: {primary_position}
- Hedge position: {hedge_position}
- Intended hedge side: {intended_side}

QUESTION: Will your change flip the hedge direction? If YES, STOP and ask user.
"""
```

**Benefit**: Agents understand the stakes before making changes

#### Strategy 4: Mandatory Code Review for Trading Logic

**New Rule**:
> Any change to `place_hedge_order()`, `place_primary_order()`, or order direction logic MUST be reviewed by:
> 1. Human trader (domain knowledge)
> 2. Senior engineer (code logic)
> 3. **Both** must approve before merge

**Implementation**:
- Add `.omc/config/trading-logic-review-required.json`
- Executor agents refuse to modify these files without approval flag

#### Strategy 5: Add Integration Test Before Commit

**Create `tests/test_integration_hedge.py`** (NOTE: tests/ directory must be created first):
```python
async def test_hedge_maintains_delta_neutrality():
    """Verify hedge actually neutralizes delta"""
    bot = DNHedgeBot(...)  # CORRECTED: Use actual class name

    # Build LONG position on Primary
    await bot.build_cycle()

    # Verify net delta is near zero
    net_delta = bot.primary_position + bot.hedge_position
    assert abs(net_delta) < Decimal("0.01"), f"Net delta {net_delta} too large!"

    # Build SHORT position on Primary
    await bot.unwind_cycle()

    # Verify net delta is still near zero
    net_delta = bot.primary_position + bot.hedge_position
    assert abs(net_delta) < Decimal("0.01"), f"Net delta {net_delta} too large!"
```

**Benefit**: Catches hedge failures before production

---

### Lessons Learned

1. **Trading bots require domain knowledge validation**
   - Generic agents don't understand delta neutrality
   - Financial logic needs expert review

2. **Direction is the most critical variable**
   - A single flipped variable can double positions
   - Always add pre-flight checks for trading direction

3. **"Optimization" tasks are riskiest**
   - Agents optimize for speed/fees without understanding strategy
   - Performance improvements can break correctness

4. **Working code is sacred**
   - Agent broke commit 0b17cea which was TESTED and WORKING
   - Should have added NEW logic, not MODIFIED working logic

5. **Post-only orders are confusing**
   - Terminology is ambiguous ("opposite side")
   - Need explicit documentation of expected behavior

---

## Part 2: 5s Timeout Optimization

### Context: Why 5s Timeout?

**Background**:
- **Previous state**: 10s timeout on Primary POST_ONLY orders
- **User request**: "Remove timeout to speed up execution"
- **Agent change**: Removed timeout completely
- **Result**: Indefinite waits when POST_ONLY orders don't fill
- **User response**: "Reduce timeout to 5s는 흥미롭네" (5s timeout is interesting)

**Tradeoff Analysis**:

| Timeout | Speed | Fill Rate | Risk |
|---------|-------|-----------|------|
| **0s (no limit)** | Indefinite wait | 100% | Stuck orders |
| **10s (current)** | Slow (77s/cycle) | 95%+ | Safe |
| **5s (proposed)** | ~50% faster | 80-90% | More retries |
| **2s (aggressive)** | 75% faster | <70% | Excessive retries |

**Why 5s is "Interesting"**:
- Balances speed (5s vs 10s = 50% improvement)
- Maintains reasonable fill rate (POST_ONLY orders often fill within 5s in volatile markets)
- Reduces worst-case delay (5s max wait vs indefinite)
- Middle ground between speed and reliability

---

### Requirements

#### Functional Requirements

**FR1**: Reduce Primary order timeout from 10s to 5s
- Location: `place_primary_order()` method, lines 720-748 (CORRECTED line numbers)
- Current: No timeout (while loop with no break condition)
- Target: 5s timeout with order cancellation

**FR2**: Maintain POST_ONLY maker order behavior
- Keep limit order placement on book
- Preserve price calculation logic
- Do NOT change to market orders

**FR3**: Add timeout-based fallback
- If 5s expires without fill → cancel order
- After cancel → retry with fresh price
- Max retries: 4 (same as current)

**FR4**: Preserve all safety checks
- Emergency unwind on hedge failure (lines 1617-1657, verified present)
- Net delta monitoring
- Position reconciliation

#### Non-Functional Requirements

**NFR1**: Speed improvement
- Target: Reduce cycle time from 77s to <50s
- Measurement: Average execution time over 10 iterations

**NFR2**: Fill rate monitoring
- Track POST_ONLY fill rate at 5s timeout
- Log timeout events for analysis
- Alert if fill rate drops below 80%

**NFR3**: Backward compatibility
- No changes to order price calculation
- No changes to hedge logic
- No changes to position management

---

### Implementation Plan

#### Task 1: Implement 5s Timeout Logic

**File**: `DN_alternate_backpack_grvt.py`
**Method**: `place_primary_order()`
**Lines**: 720-748 (CORRECTED from 718-758)
**Class**: `DNHedgeBot` (CORRECTED from DNAlternateBot)

**Current Code** (lines 720-748):
```python
# OPTIMIZATION: Removed 10s timeout/cancellation - POST_ONLY orders stay on book until filled
# This eliminates 10-11 second cancellation delays that were causing 77s/cycle execution time
while not self.stop_flag:
    if self.primary_order_status == "CANCELED":
        self.primary_order_status = None
        (best_bid, best_ask) = await self.primary_client.fetch_bbo_prices(
            self.primary_contract_id
        )
        order_price = self.calculate_order_price(
            side, best_bid, best_ask, self.primary_tick_size, self.primary_mode
        )
        break

    if self.primary_order_status == "FILLED":
        return order_id

    if self.primary_order_status in ["OPEN", "PENDING", "PARTIALLY_FILLED"]:
        await asyncio.sleep(0.1)  # Poll status for faster response
    else:
        await asyncio.sleep(0.1)  # Poll status for faster response
```

**WebSocket Status Update Context** (IMPORTANT - How primary_order_status gets updated):
- `self.primary_order_status` is updated by WebSocket callbacks in `_handle_primary_order_update()` (lines 477, 489, 506, 511, 676)
- WebSocket callback sets status to: "FILLED", "CANCELED", "OPEN", "PENDING", "PARTIALLY_FILLED"
- Status updates happen asynchronously via WebSocket, not via polling
- The while loop polls the status variable that WebSocket callbacks update

**New Code** (add timeout tracking):
```python
# Track order placement time for timeout
# NOTE: time module is already imported at line 14
order_start_time = time.time()
POST_ONLY_TIMEOUT = 5.0  # 5 second timeout for POST_ONLY orders

while not self.stop_flag:
    current_time = time.time()
    elapsed_time = current_time - order_start_time

    # TIMEOUT: Cancel if 5s elapsed without fill
    if elapsed_time >= POST_ONLY_TIMEOUT and self.primary_order_status in ["OPEN", "PENDING"]:
        self.logger.warning(
            f"[PRIMARY] Post-only order timeout after {elapsed_time:.1f}s - cancelling"
        )
        await self.primary_client.cancel_order(order_id)
        # WebSocket callback will set primary_order_status to "CANCELED"
        continue

    if self.primary_order_status == "CANCELED":
        self.primary_order_status = None
        (best_bid, best_ask) = await self.primary_client.fetch_bbo_prices(
            self.primary_contract_id
        )
        order_price = self.calculate_order_price(
            side, best_bid, best_ask, self.primary_tick_size, self.primary_mode
        )
        break

    if self.primary_order_status == "FILLED":
        fill_time = current_time - order_start_time
        self.logger.info(f"[PRIMARY] Filled in {fill_time:.2f}s")
        return order_id

    if self.primary_order_status in ["OPEN", "PENDING", "PARTIALLY_FILLED"]:
        await asyncio.sleep(0.1)  # Poll status for faster response
    else:
        await asyncio.sleep(0.1)  # Poll status for faster response
```

**Changes**:
1. Verified `time` module import exists (line 14) - no new import needed
2. Added `POST_ONLY_TIMEOUT = 5.0` constant
3. Track `order_start_time` when placing order
4. Check timeout in while loop
5. Cancel order if timeout exceeded (WebSocket callback will update status to "CANCELED")
6. Log fill time for monitoring (elapsed_time is accessible in loop scope)

---

#### Task 2: Add Timeout Metrics

**File**: `DN_alternate_backpack_grvt.py`
**Location**: Class `__init__` method (around line 150) and `place_primary_order()` method

**Implementation**:
```python
# Add to class __init__ (around line 150)
self.timeout_count = 0
self.fast_fill_count = 0  # Fills within 2s
self.slow_fill_count = 0  # Fills 2-5s
self.total_fill_time = 0.0

# Add after order fills (in place_primary_order, after line 738)
if self.primary_order_status == "FILLED":
    fill_time = current_time - order_start_time
    self.logger.info(f"[PRIMARY] Filled in {fill_time:.2f}s")

    # Update metrics (elapsed_time is now called fill_time and is in scope)
    if fill_time < 2.0:
        self.fast_fill_count += 1
    elif fill_time < 5.0:
        self.slow_fill_count += 1
    self.total_fill_time += fill_time

    return order_id

# Add timeout counter in timeout handler (line ~730)
if elapsed_time >= POST_ONLY_TIMEOUT and self.primary_order_status in ["OPEN", "PENDING"]:
    self.logger.warning(
        f"[PRIMARY] Post-only order timeout after {elapsed_time:.1f}s - cancelling"
    )
    self.timeout_count += 1

    # Log metrics
    total_fills = self.fast_fill_count + self.slow_fill_count
    avg_fill_time = self.total_fill_time / total_fills if total_fills > 0 else 0
    self.logger.info(
        f"[METRICS] Timeouts: {self.timeout_count}, "
        f"Fast fills: {self.fast_fill_count}, "
        f"Slow fills: {self.slow_fill_count}, "
        f"Avg fill time: {avg_fill_time:.2f}s"
    )

    await self.primary_client.cancel_order(order_id)
    # WebSocket callback will set primary_order_status to "CANCELED"
    continue
```

**CORRECTED**: Fixed variable scope issue - `elapsed_time` is accessible in the while loop where timeout check happens, and `fill_time` is calculated when order fills.

---

#### Task 3: Update Documentation

**File**: Create new file `TIMEOUT_OPTIMIZATION_REPORT.md` in hedge folder

**Content**:
```markdown
## Timeout Optimization (2026-01-26)

### Problem
- Previous: 10s timeout on Primary POST_ONLY orders
- Removed timeout → indefinite waits when orders don't fill
- Need balance: speed vs fill rate

### Solution: 5s Timeout
- Reduce timeout from 10s to 5s
- Track order placement time
- Cancel and retry if 5s elapsed without fill
- Log timeout metrics for analysis

### Expected Results
- Speed: 50% faster (5s max wait vs 10s)
- Fill rate: 80-90% (vs 95%+ at 10s)
- Cycle time: Target <50s (vs 77s current)

### Tradeoffs
| Timeout | Speed | Fill Rate | Retries |
|---------|-------|-----------|---------|
| 5s | Fast | Good | Moderate |
| 10s | Slow | Excellent | Few |
| No limit | Stuck | 100% | Never |

### Monitoring
- Track timeout frequency
- Measure average fill time
- Alert if fill rate drops below 80%

### Verification
- Emergency unwind preserved (lines 1617-1657)
- Net delta monitoring unchanged
- Position tracking via self.primary_position (internal state)
- WebSocket status updates via _handle_primary_order_update() callback
```

---

### Testing Strategy

#### Test 1: Manual Integration Test - End-to-End

**NOTE**: Unit tests in `tests/test_timeout_logic.py` would require creating tests/ directory infrastructure.
Since no test infrastructure exists in the hedge folder, we'll use manual integration testing first.

**File**: `DN_alternate_backpack_grvt.py`
**Test Method**: Run with small quantity and monitor logs

**Configuration**:
```bash
# Run 5 iterations with small size to test
python DN_alternate_backpack_grvt.py \
  --ticker ETH \
  --quantity 0.1 \
  --iterations 5 \
  --fill-timeout 5
```

**Metrics to Track**:
1. **Cycle Time**: Log shows "[PRIMARY] Filled in X.XXs" for each order
2. **Timeout Rate**: Count "[PRIMARY] Post-only order timeout" messages
3. **Fill Rate**: Successful fills vs timeouts
4. **Position Accuracy**: Verify net delta remains neutral

**Success Criteria** (objectively measurable):
- [ ] All 5 iterations complete without errors
- [ ] Log shows fill times <6s for all orders
- [ ] Timeout messages appear if orders exceed 5s
- [ ] Final positions: primary_position + hedge_position = 0 ±0.01 ETH
- [ ] No "stuck" orders (all complete within reasonable time)

**Log Output to Verify**:
```
[PRIMARY] Filled in 2.34s
[METRICS] Timeouts: 1, Fast fills: 3, Slow fills: 1, Avg fill time: 2.45s
[RECONCILE] Primary: 0.1 ETH, Hedge: -0.1 ETH, Net: 0.0 ETH
```

---

#### Test 2: Comparative Performance Test

**Purpose**: Measure actual speed improvement vs baseline

**Baseline Test** (current state without 5s timeout):
```bash
# Temporarily disable timeout to measure baseline
# Edit POST_ONLY_TIMEOUT to 0 (disabled) or use existing code
python DN_alternate_backpack_grvt.py --ticker ETH --quantity 0.5 --iterations 10

# Record average cycle time from logs
```

**Optimized Test** (with 5s timeout):
```bash
# With 5s timeout implemented
python DN_alternate_backpack_grvt.py --ticker ETH --quantity 0.5 --iterations 10

# Record average cycle time from logs
```

**Comparison Metrics** (objectively measurable):
- [ ] Average cycle time (baseline vs optimized)
- [ ] Timeout frequency (count timeout messages)
- [ ] Fill rate (successful fills / total orders)
- [ ] API call rate (cancel + retry frequency)

**Target Improvements** (measurable):
- Cycle time reduction >20%: (baseline - optimized) / baseline > 0.20
- Timeout rate <30%: timeout_count / total_orders < 0.30
- No position errors: final net delta always <0.01 ETH

---

#### Test 3: Safety Verification Test

**Purpose**: Verify emergency unwind and safety checks are preserved

**Test Method**: Artificially trigger hedge failure

**Procedure**:
1. Start bot with small quantity
2. Monitor for hedge order failures
3. Verify emergency unwind executes if hedge fails

**Success Criteria** (objectively measurable from logs):
- [ ] Log shows "[EMERGENCY_UNWIND] Unwinding Primary" if hedge fails
- [ ] Final positions return to neutral after emergency unwind
- [ ] No position accumulation (primary_position + hedge_position <0.01)
- [ ] Error handling catches exceptions without crashing

**Verification Commands**:
```bash
# Check emergency unwind code exists and is unchanged
grep -n "_emergency_unwind_primary_position" DN_alternate_backpack_grvt.py
# Should show lines 1617-1657

# Verify position tracking uses internal state
grep -n "self.primary_position" DN_alternate_backpack_grvt.py | head -20
# Should show usage at lines 126, 479, 482, 651, etc.

# Verify WebSocket callback updates status
grep -n "self.primary_order_status" DN_alternate_backpack_grvt.py
# Should show updates in _handle_primary_order_update() (lines 477, 489, 506, 511)
```

---

### Expected Outcomes

#### Performance Improvements

**Baseline (commit 0b17cea)**:
- Cycle time: 77.72s
- Primary order wait: 10-18s per order
- Timeout: 10s (fixed)

**Target (5s timeout)**:
- Cycle time: <50s (35% improvement)
- Primary order wait: 2-5s per order
- Timeout: 5s (adaptive)

**Projected Impact**:
```
Current: 77s/cycle × 300 cycles = 6.4 hours
Target:  50s/cycle × 300 cycles = 4.2 hours

Time savings: 2.2 hours per 300-cycle run
```

#### Tradeoffs

**Pros**:
- 35% faster execution
- No indefinite waits (worst case 5s)
- Better responsiveness to price changes
- Reduced slippage (orders refresh faster)

**Cons**:
- More order cancellations
- Slightly lower fill rate (80-90% vs 95%+)
- More API calls (cancel + retry)
- Potential increase in taker fees (if fallback to market)

---

### Risk Mitigation

#### Risk 1: Excessive Timeouts → High Taker Fees

**Scenario**: 5s timeout causes 40%+ timeouts → fallback to market orders → high fees

**Mitigation**:
1. **Monitor timeout rate in real-time**
   ```python
   if self.timeout_count > 5:
       self.logger.warning("[RISK] High timeout rate - consider increasing timeout")
   ```

2. **Auto-adjust timeout if needed**
   ```python
   total_fills = self.fast_fill_count + self.slow_fill_count
   timeout_rate = self.timeout_count / (self.timeout_count + total_fills) if (self.timeout_count + total_fills) > 0 else 0

   if timeout_rate > 0.4:  # 40% timeout rate
       POST_ONLY_TIMEOUT = 7.0  # Increase to 7s
       self.logger.info("[AUTO] Adjusted timeout to 7s due to high timeout rate")
   ```

3. **User alert before auto-adjust**
   ```python
   if timeout_rate > 0.4:
       send_telegram_alert("High timeout rate detected. Pausing for manual review.")
       self.stop_flag = True
   ```

---

#### Risk 2: Market Volatility → Many Cancel/Retries

**Scenario**: Fast price moves → orders stale → continuous cancel/retry loop

**Mitigation**:
1. **Max retry limit**: 4 retries (already implemented at line 770)
2. **Exponential backoff**: 0.2s → 0.4s → 0.8s → 1.6s (already in retry loop)
3. **Circuit breaker**: Stop after 10 consecutive failures
   ```python
   if self.consecutive_failures >= 10:
       self.logger.error("[CIRCUIT_BREAKER] Too many failures - stopping")
       self.stop_flag = True
   ```

---

#### Risk 3: Regression - Break Working Logic

**Scenario**: Timeout changes break existing BUILD/UNWIND logic

**Mitigation**:
1. **Comprehensive testing** (manual integration + comparative + safety)
2. **Git revert plan**: `git revert <timeout-commit>` if critical bug
3. **Feature flag**: Allow disabling timeout without code change
   ```python
   POST_ONLY_TIMEOUT = os.getenv("POST_ONLY_TIMEOUT", "5.0")  # Configurable
   if POST_ONLY_TIMEOUT == "0":
       # Disable timeout (old behavior)
       pass
   ```

---

### Rollback Plan

**If 5s timeout causes critical issues**:

**Option 1: Revert to 10s timeout**
```python
POST_ONLY_TIMEOUT = 10.0  # Back to safe value
```

**Option 2: Revert to no timeout (commit 0b17cea behavior)**
```bash
git revert <timeout-commit>
```

**Option 3: Make timeout configurable**
```python
# Add to config.json
{
    "primary_order_timeout": 5.0,  # Configurable per deployment
    "hedge_order_timeout": 20.0
}
```

**Decision Tree**:
```
Test results show:
├─ Fill rate >80%, Cycle time <50s → Deploy 5s timeout
├─ Fill rate 60-80%, Cycle time 50-70s → Try 7s timeout
├─ Fill rate <60%, Excessive retries → Revert to 10s timeout
└─ Critical errors (position accumulation) → Revert immediately, investigate
```

---

## Part 3: Implementation TODOs

### Phase 1: Code Changes (LOW RISK)

- [ ] **TODO-1**: Add timeout metrics initialization to `__init__` method
  - File: `DN_alternate_backpack_grvt.py`, around line 150
  - Add: `self.timeout_count`, `self.fast_fill_count`, `self.slow_fill_count`, `self.total_fill_time`
  - Acceptance: Variables initialized, can be verified in log output

- [ ] **TODO-2**: Implement timeout tracking in `place_primary_order()` method
  - File: `DN_alternate_backpack_grvt.py`, lines 720-748 (timeout loop)
  - Class: `DNHedgeBot` (verify class name at line 84)
  - Acceptance:
    - Adds `order_start_time = time.time()` (time module imported at line 14)
    - Checks `elapsed_time >= POST_ONLY_TIMEOUT` in while loop
    - Cancels order via `await self.primary_client.cancel_order(order_id)`
    - Logs timeout event with elapsed time
    - WebSocket callback will set `self.primary_order_status` to "CANCELED"

- [ ] **TODO-3**: Add timeout metrics logging
  - File: `DN_alternate_backpack_grvt.py`, in `place_primary_order()` method
  - Acceptance:
    - Tracks fill times when order fills (`fill_time = current_time - order_start_time`)
    - Updates `fast_fill_count` (<2s), `slow_fill_count` (2-5s), `total_fill_time`
    - Logs metrics after timeout: "Timeouts: X, Fast fills: Y, Slow fills: Z, Avg fill time: A"
    - Calculates average fill time correctly (total / count)

- [ ] **TODO-4**: Verify safety checks preserved
  - Check emergency unwind method exists at lines 1617-1657
  - Verify position tracking uses `self.primary_position` (not API calls)
  - Verify WebSocket callback `_handle_primary_order_update()` updates status
  - Acceptance: All safety mechanisms present and unchanged

### Phase 2: Testing (MEDIUM RISK)

- [ ] **TODO-5**: Run manual integration test (5 iterations)
  - Command: `python DN_alternate_backpack_grvt.py --ticker ETH --quantity 0.1 --iterations 5 --fill-timeout 5`
  - Acceptance:
    - All 5 iterations complete
    - Log shows fill times for each order
    - Timeout messages appear if applicable
    - Final net delta = 0 ±0.01 ETH
    - No stuck orders

- [ ] **TODO-6**: Run comparative performance test (10 iterations)
  - Baseline: Run without 5s timeout (current code)
  - Optimized: Run with 5s timeout
  - Acceptance:
    - Document cycle time for both runs
    - Calculate percentage improvement
    - Document timeout rate
    - Document fill rate

- [ ] **TODO-7**: Verify safety mechanisms
  - Check emergency unwind code unchanged (grep lines 1617-1657)
  - Verify position tracking unchanged (grep self.primary_position)
  - Verify WebSocket status updates (grep self.primary_order_status)
  - Acceptance: All safety code present and functional

### Phase 3: Validation (HIGH RISK)

- [ ] **TODO-8**: Create TIMEOUT_OPTIMIZATION_REPORT.md
  - File: `TIMEOUT_OPTIMIZATION_REPORT.md` in hedge folder
  - Acceptance:
    - Document implementation approach
    - Document test results (cycle time, fill rate, timeout rate)
    - Document tradeoffs
    - Include log output examples
    - Document rollback procedure

- [ ] **TODO-9**: Compare results vs baseline
  - Baseline: 77.72s/cycle (commit 0b17cea or measured baseline)
  - Target: <50s/cycle
  - Acceptance:
    - Document actual speed improvement percentage
    - Document actual fill rate
    - Document actual timeout rate
    - Compare against expected results

- [ ] **TODO-10**: Create git commit
  - Message: "feat(dn-bot): Add 5s timeout optimization for Primary POST_ONLY orders"
  - Acceptance:
    - Clean commit history
    - References post-mortem lessons
    - Includes test results in commit message or attached report
    - No changes to hedge direction logic

---

## Part 4: Success Criteria

### Must Have (Go/No-Go) - All Objectively Measurable

- [ ] **CRITICAL**: No buy/sell direction flips (post-mortem lesson)
  - Verify: `git diff` shows no changes to hedge buy/sell logic

- [ ] **CRITICAL**: Net delta remains neutral (±0.01 ETH)
  - Verify: `final_primary_position + final_hedge_position` < 0.01

- [ ] **CRITICAL**: No position accumulation
  - Verify: Positions return to 0 after each BUILD + UNWIND cycle

- [ ] **REQUIRED**: Cycle time improvement >20% (77s → <62s)
  - Verify: Measure average cycle time over 10 iterations

- [ ] **REQUIRED**: Timeout rate <30%
  - Verify: Count timeout messages / total orders < 0.30

- [ ] **REQUIRED**: Emergency unwind preserved
  - Verify: Method `_emergency_unwind_primary_position` exists at lines 1617-1657

### Nice to Have - All Objectively Measurable

- [ ] Cycle time improvement >35% (77s → <50s)
  - Verify: Measure average cycle time

- [ ] Fill rate >85%
  - Verify: Successful fills / total orders > 0.85

- [ ] Timeout rate <20%
  - Verify: Timeout count / total orders < 0.20

- [ ] Average fill time logged
  - Verify: Log shows "Avg fill time: X.XXs"

### Do NOT Do

- [ ] **FORBIDDEN**: Change hedge order direction
  - Prevent: Code review of all changes to `place_hedge_order()`

- [ ] **FORBIDDEN**: Remove emergency unwind
  - Prevent: Code review verifies method exists and unchanged

- [ ] **FORBIDDEN**: Remove net delta monitoring
  - Prevent: Verify reconciliation code unchanged

- [ ] **FORBIDDEN**: Increase timeout above 10s
  - Prevent: Code review verifies `POST_ONLY_TIMEOUT = 5.0` or less

- [ ] **FORBIDDEN**: Remove timeout completely (indefinite wait)
  - Prevent: Code review verifies timeout logic present

---

## Part 5: Commit Strategy

### Commit Message

```
feat(dn-bot): Add 5s timeout optimization for Primary POST_ONLY orders

Problem:
- Previous 10s timeout caused slow execution (77s/cycle)
- Agent removed timeout → indefinite waits when orders don't fill
- Need balance: speed vs fill rate

Solution:
- Implement 5s timeout for Primary POST_ONLY orders
- Track order placement time and cancel if timeout exceeded
- Log timeout metrics for monitoring (fast/slow fill counts)
- Fallback to retry with fresh price after timeout

Implementation:
- Add POST_ONLY_TIMEOUT = 5.0 constant in place_primary_order()
- Track order_start_time when placing order
- Check timeout each loop iteration (elapsed_time = current_time - order_start_time)
- Cancel via primary_client.cancel_order() if 5s elapsed without fill
- Log timeout events and fill times (fast fills <2s, slow fills 2-5s)
- WebSocket callback updates primary_order_status to "CANCELED" after cancel

Key Technical Details:
- Class: DNHedgeBot (line 84)
- Method: place_primary_order() (lines 675-758, timeout loop at 720-748)
- Status updates: Via WebSocket callback _handle_primary_order_update() (lines 477, 489, 506, 511)
- Position tracking: Uses internal self.primary_position (not API calls)
- Import: time module already imported at line 14

Safety Preserved:
- Emergency unwind: _emergency_unwind_primary_position() at lines 1617-1657
- Position reconciliation: Unchanged
- Net delta monitoring: Unchanged
- No changes to hedge direction logic

Expected Results:
- Speed: 35% faster (5s max wait vs 10s)
- Fill rate: 80-90% (vs 95%+ at 10s)
- Cycle time: Target <50s (vs 77s current)

Testing:
- Manual integration: 5-iteration test with 0.1 ETH
- Comparative: 10-iteration test measuring cycle time improvement
- Safety: Verify emergency unwind preserved
- Metrics: Track timeout rate, fill rate, cycle time

Post-Mortem Lessons Applied:
- Previous agent attempt broke buy/sell direction (CRITICAL)
- Verified no changes to hedge direction logic
- All changes preserve hedge direction and delta neutrality
- Safety mechanisms verified and unchanged

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Verification Steps

After commit, verify:

```bash
# 1. Check git diff (only timeout changes, no direction flips)
git diff HEAD~1 HEAD | grep -i "buy\|sell"
# Should show NO changes to hedge buy/sell logic

# 2. Verify emergency unwind preserved
git show HEAD:DN_alternate_backpack_grvt.py | grep -n "_emergency_unwind_primary_position"
# Should show method at lines 1617-1657

# 3. Verify class name correct
git show HEAD:DN_alternate_backpack_grvt.py | grep -n "class DNHedgeBot"
# Should show line 84

# 4. Verify timeout logic added
git show HEAD:DN_alternate_backpack_grvt.py | grep -n "POST_ONLY_TIMEOUT"
# Should show "POST_ONLY_TIMEOUT = 5.0"

# 5. Check time import
git show HEAD:DN_alternate_backpack_grvt.py | grep "^import time"
# Should show line 14

# 6. Run dry-run to verify no syntax errors
python DN_alternate_backpack_grvt.py --help
# Should show usage without errors
```

---

## Conclusion

This plan addresses **TWO critical areas**:

### Part 1: Post-Mortem (Why the Agent Failed)

**Root Cause**: Agent misunderstood POST_ONLY mechanics and flipped buy/sell direction

**Impact**: Bot would double positions instead of hedging (catastrophic)

**Prevention**: 5 strategies to prevent future agent failures
1. Pre-flight validation checks
2. Unit tests for hedge direction (if test infrastructure created)
3. Agent prompt guardrails
4. Mandatory code review for trading logic
5. Integration tests before commit (if test infrastructure created)

### Part 2: 5s Timeout Optimization

**Goal**: Reduce cycle time from 77s to <50s (35% improvement)

**Method**: 5s timeout on Primary POST_ONLY orders with cancel/retry

**Technical Details** (CORRECTED):
- Class: `DNHedgeBot` (line 84, not DNAlternateBot)
- Method: `place_primary_order()` (lines 675-758, timeout loop at 720-748)
- Timeout loop: Lines 720-748 (not 718-758)
- Position tracking: `self.primary_position` (internal state, not API)
- Status updates: WebSocket callback `_handle_primary_order_update()` (lines 477, 489, 506, 511)
- Time module: Already imported at line 14
- Emergency unwind: Preserved at lines 1617-1657

**Tradeoffs**:
- Speed: 35% faster
- Fill rate: 80-90% (vs 95%+ at 10s)
- More retries

**Testing**: Manual integration → Comparative performance → Safety verification

**Success Criteria** (all objectively measurable):
- No direction flips (verify via git diff)
- Cycle time <50s (measure)
- Fill rate >80% (calculate from logs)
- No position accumulation (verify net delta)
- Emergency unwind preserved (verify code exists)

---

**Next Steps**:

1. **Review this plan** - All critical issues from previous version have been addressed
2. **Get user approval** - This is a trading system, high risk
3. **Implement Phase 1** - Code changes (with verification)
4. **Run Phase 2 tests** - Manual integration and comparative tests
5. **Run Phase 3 validation** - Safety verification
6. **Commit if success criteria met** - All criteria objectively measurable

---

**PLAN_STATUS**: REVISED and ready for implementation
**RISK_LEVEL**: HIGH (trading system, direction flips are catastrophic)
**RECOMMENDATION**: Proceed with extreme caution, verify hedge direction at every step

**Changes from Previous Version**:
1. Fixed class name: `DNHedgeBot` (was `DNAlternateBot`)
2. Fixed line numbers: 720-748 (was 718-758)
3. Removed unit test TODOs (tests/ directory doesn't exist)
4. Fixed position tracking: Uses `self.primary_position` (not API)
5. Fixed variable scope: `elapsed_time`/`fill_time` accessible in loop
6. Added WebSocket context: Explained how `primary_order_status` updates
7. Verified time import: Already at line 14
8. Verified emergency unwind: Present at lines 1617-1657
9. Made all success criteria objectively measurable
10. Added safety verification TODO (grep commands)
