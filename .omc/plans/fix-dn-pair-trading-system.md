# DN Pair Trading System Critical Fixes - Work Plan

## Context

### Original Request
DN pair trading bot has 5 critical issues preventing correct operation:
1. SOL orderbook data incorrect - fetch_bbo_prices returns 115.78 but actual orderbook shows bid at 115.56 (22 cents difference)
2. Hedging imbalance 4.5% - Target is 0.1%, but getting ETH $99, SOL $104
3. One-sided fills - Only ETH fills, SOL sell never fills
4. DN direction failure - Both legs end up long (not delta neutral)
5. Emergency unwind fails - Can't close positions when one leg fails

### Current State Analysis

**Orderbook Reality (from logs):**
```
Bids: [[115.56, 226.6], [115.55, 436.7], [115.54, 964.6]]
Asks: [[115.57, 165.8], [115.58, 706.6], [115.59, 400.7]]
```

**But code gets (from logs):**
```
[DEBUG] bid=115.78, ask=115.79  ← WRONG! Should be 115.56/115.57
```

### Root Causes Identified

#### Issue 1: BBO Data Incorrect
**Root Cause:** The BBO WebSocket handler may be returning stale data or there's a parsing issue with the x18 format conversion.

**Evidence:**
- `nado_bbo_handler.py:204-207` parses BBO data with `Decimal(message["bid_price"]) / Decimal(1e18)`
- `nado.py:176` uses WebSocket BBO first, then falls back to REST
- The 22-cent difference suggests data staleness or wrong field access

#### Issue 2: Hedging Imbalance 4.5%
**Root Cause:** SOL tick_size is 0.1, making precise 0.1% balance impossible with small notionals.

**Analysis:**
- At $115 price, 0.1 SOL = $11.50 notional
- With $100 target, quantities are ~0.87 SOL
- Rounding to 0.1 increments: 0.9 SOL = $103.50 vs 0.3 ETH @ $3300 = $99
- The 4.5% difference is due to tick_size constraints

#### Issue 3: One-Sided Fills
**Root Cause:** Aggressive pricing (crossing spread) combined with wide spreads causes only one leg to fill.

**Evidence:**
- `nado.py:500-503` uses aggressive IOC pricing (buy at ask, sell at bid)
- With 0.22 cent spread on SOL, orders may not match
- `place_simultaneous_orders` doesn't retry partial fills

#### Issue 4: DN Direction Failure
**Root Cause:** Emergency unwind logic doesn't track filled direction correctly.

**Evidence:**
- `handle_emergency_unwind` checks `filled_direction` but IOC orders may not set it
- Both legs ending long suggests the unwind leg isn't executing

#### Issue 5: Emergency Unwind Fails
**Root Cause:** Circular dependency - tries to close positions that were never opened.

**Evidence:**
- `emergency_unwind_eth` and `emergency_unwind_sol` check position after fill
- Position updates may be delayed by REST API polling

---

## Work Objectives

### Core Objective
Fix all 5 critical issues to make the DN pair trading bot operational with true delta-neutral behavior.

### Deliverables
1. BBO data accuracy: Bid/ask within 0.01% of actual orderbook
2. Hedging balance: Within 0.5% (SOL tick_size constraint)
3. Both legs fill: >90% fill rate for both ETH and SOL
4. Delta neutral: One long, one short always
5. Emergency unwind: Reliable position cleanup

### Definition of Done
- BBO prices verified against BookDepth data
- Notional imbalance <0.5% on 95%+ of cycles
- Fill rate >90% for both legs
- Position reconciliation confirms opposite directions
- Emergency unwind closes positions within 5 seconds

---

## Must Have / Must NOT Have

### Must Have
- Fix BBO data accuracy using BookDepth as verification
- Adjust SOL sizing to account for tick_size (0.1) constraints
- Implement retry logic for partial fills
- Fix emergency unwind to use filled order direction
- Add validation checks before placing orders

### Must NOT Have
- Breaking changes to CSV format
- Changes to WebSocket subscriptions
- Switching to REST polling (keep WebSocket)
- Changing tick_size values (exchange constraint)

---

## Task Flow and Dependencies

```
Phase 1: Data Accuracy (Independent)
├── Fix BBO data fetching
└── Add BookDepth verification

Phase 2: Hedging Balance (Depends on Phase 1)
├── Adjust quantity calculation for SOL tick_size
└── Implement balanced sizing with tick awareness

Phase 3: Fill Rate (Depends on Phase 2)
├── Add retry logic for partial fills
└── Improve IOC pricing strategy

Phase 4: Delta Neutral (Depends on Phase 3)
├── Fix emergency unwind direction tracking
└── Add position validation

Phase 5: Testing (Depends on all phases)
└── Verification and validation
```

---

## Detailed TODOs

### Phase 1: Fix BBO Data Accuracy

#### Task 1.1: Add BBO Validation Against BookDepth
**File:** `exchanges/nado.py`

**Action:** In `fetch_bbo_prices`, add validation using BookDepth data.

**Implementation:**
```python
async def fetch_bbo_prices(self, contract_id: str) -> Tuple[Decimal, Decimal]:
    # Try WebSocket BBO first
    if self._ws_connected and self._bbo_handler:
        bid_price, ask_price = self._bbo_handler.get_prices()
        if bid_price is not None and bid_price > 0 and ask_price is not None and ask_price > 0:
            # VALIDATE against BookDepth
            if self._bookdepth_handler:
                book_bid, _ = self._bookdepth_handler.get_best_bid()
                book_ask, _ = self._bookdepth_handler.get_best_ask()
                if book_bid and book_ask:
                    # Check if BBO is stale (more than 0.1% difference)
                    if abs(bid_price - book_bid) / book_bid > Decimal('0.001'):
                        self.logger.warning(f"BBO stale: WS={bid_price}, Book={book_bid}, using BookDepth")
                        return book_bid, book_ask
            return bid_price, ask_price
    # Fallback to REST or BookDepth
    ...
```

**Acceptance Criteria:**
- BBO prices match BookDepth within 0.1%
- Warning logged when stale data detected
- Automatic fallback to BookDepth

#### Task 1.2: Add BBO Staleness Detection
**File:** `exchanges/nado_bbo_handler.py`

**Action:** Add timestamp check to detect stale BBO data.

**Implementation:**
```python
def get_prices(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    if self._latest_bbo is None:
        return None, None
    # Check staleness (older than 2 seconds)
    current_time = int(time.time() * 1000)
    if current_time - self._latest_bbo.timestamp > 2000:
        self.logger.warning(f"BBO data stale: {current_time - self._latest_bbo.timestamp}ms old")
        return None, None
    return self._latest_bbo.bid_price, self._latest_bbo.ask_price
```

**Acceptance Criteria:**
- Data older than 2 seconds rejected
- Warning logged with staleness duration
- Returns None to trigger fallback

---

### Phase 2: Fix Hedging Balance

#### Task 2.1: Adjust SOL Quantity Calculation
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Modify `calculate_balanced_order_sizes` to account for SOL tick_size.

**Root Cause:** SOL tick_size (0.1) is too large for precise balancing at $100 notional.

**Implementation:**
```python
async def calculate_balanced_order_sizes(
    self,
    eth_price: Decimal,
    sol_price: Decimal,
    eth_direction: str,
    sol_direction: str,
    max_slippage_bps: int = 20
) -> Tuple[Decimal, Decimal, Decimal]:
    # ... existing code ...

    # NEW: Adjust for SOL tick_size constraint
    # Calculate target notional based on SOL's tick granularity
    sol_tick_value = sol_price * sol_tick_size  # ~$11.50 at $115 price

    # Find nearest achievable balance
    # At $100 target with $11.50 granularity, best we can do is:
    # - 8 ticks = $92 notional (0.8 SOL)
    # - 9 ticks = $103.50 notional (0.9 SOL)
    # Choose closest to target with tolerance

    target_ticks = round(self.target_notional / sol_tick_value)
    adjusted_notional = target_ticks * sol_tick_value

    # Recalculate both quantities based on adjusted notional
    eth_qty = (adjusted_notional / eth_price / eth_tick_size).quantize(Decimal('1')) * eth_tick_size
    sol_qty = (adjusted_notional / sol_price / sol_tick_size).quantize(Decimal('1')) * sol_tick_size

    # Verify balance
    eth_notional = eth_qty * eth_price
    sol_notional = sol_qty * sol_price
    imbalance_pct = abs(eth_notional - sol_notional) / ((eth_notional + sol_notional) / 2) * 100

    self.logger.info(f"[BALANCE] Adjusted for SOL tick_size: "
                    f"Target=${adjusted_notional:.2f}, "
                    f"ETH=${eth_notional:.2f}, SOL=${sol_notional:.2f}, "
                    f"Imbalance={imbalance_pct:.2f}%")

    return eth_qty, sol_qty, adjusted_notional
```

**Acceptance Criteria:**
- Notional imbalance <0.5% (within SOL tick constraint)
- Adjusted target logged for visibility
- Both quantities rounded to tick sizes

#### Task 2.2: Relax Balance Target
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Update balance tolerance from 0.1% to 0.5% for SOL.

**Implementation:**
```python
# In calculate_balanced_order_sizes, line 512
# OLD: if notional_diff_pct <= 0.1:  # 0.1% tolerance
# NEW:
if notional_diff_pct <= 0.5:  # 0.5% tolerance (SOL tick_size constraint)
```

**Acceptance Criteria:**
- 0.5% tolerance documented in code
- Matches achievable precision with SOL tick_size

---

### Phase 3: Fix Fill Rate

#### Task 3.1: Add IOC Order Retry Logic
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Implement retry for partially filled IOC orders.

**Root Cause:** Wide spreads cause IOC orders to not fill; no retry exists.

**Implementation:**
```python
async def place_ioc_order_with_retry(
    self,
    client: NadoClient,
    contract_id: str,
    quantity: Decimal,
    direction: str,
    max_retries: int = 3
) -> OrderResult:
    """Place IOC order with retry on partial fill."""
    total_filled = Decimal(0)
    best_fill_price = Decimal(0)

    for attempt in range(max_retries):
        remaining_qty = quantity - total_filled

        if remaining_qty <= client.config.min_size:
            break  # Too small to retry

        # Get fresh BBO prices
        bid, ask = await client.fetch_bbo_prices(contract_id)

        # Adjust pricing: more aggressive on retries
        if direction == "buy":
            # Attempt 1: ask, Attempt 2+: ask + 1 tick
            order_price = ask if attempt == 0 else ask + client.config.tick_size
        else:
            # Attempt 1: bid, Attempt 2+: bid - 1 tick
            order_price = bid if attempt == 0 else bid - client.config.tick_size

        result = await client.place_ioc_order(contract_id, remaining_qty, direction)

        if result.success and result.filled_size > 0:
            total_filled += result.filled_size
            if result.price > 0:
                best_fill_price = result.price
            self.logger.info(f"[RETRY] Attempt {attempt+1}: Filled {result.filled_size}/{remaining_qty}")

            if total_filled >= quantity * Decimal('0.95'):  # 95% fill threshold
                break
        else:
            self.logger.warning(f"[RETRY] Attempt {attempt+1}: Failed - {result.error_message}")
            await asyncio.sleep(0.1)  # Brief wait before retry

    # Return aggregated result
    return OrderResult(
        success=total_filled > 0,
        filled_size=total_filled,
        price=best_fill_price,
        status='FILLED' if total_filled >= quantity * Decimal('0.95') else 'PARTIALLY_FILLED'
    )
```

**Acceptance Criteria:**
- Up to 3 retry attempts for partial fills
- More aggressive pricing on retries
- Aggregates fills across attempts
- 95% fill threshold for success

#### Task 3.2: Use Retry in Simultaneous Orders
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Replace direct `place_ioc_order` calls with retry version.

**Implementation:**
```python
# In place_simultaneous_orders, line 711-715
# OLD:
eth_result, sol_result = await asyncio.gather(
    self.eth_client.place_ioc_order(self.eth_client.config.contract_id, eth_qty, eth_direction),
    self.sol_client.place_ioc_order(self.sol_client.config.contract_id, sol_qty, sol_direction),
    return_exceptions=True
)

# NEW:
eth_result, sol_result = await asyncio.gather(
    self.place_ioc_order_with_retry(self.eth_client, self.eth_client.config.contract_id, eth_qty, eth_direction),
    self.place_ioc_order_with_retry(self.sol_client, self.sol_client.config.contract_id, sol_qty, sol_direction),
    return_exceptions=True
)
```

**Acceptance Criteria:**
- Both legs use retry logic
- Fill rate >90% achieved
- No breaking changes to OrderResult format

---

### Phase 4: Fix Delta Neutral Direction

#### Task 4.1: Track Fill Direction Correctly
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Ensure `handle_emergency_unwind` receives correct direction.

**Root Cause:** IOC orders may not set `filled_direction` correctly.

**Implementation:**
```python
async def handle_emergency_unwind(
    self,
    eth_result: OrderResult,
    sol_result: OrderResult,
    eth_direction: str,  # Always provide these
    sol_direction: str
):
    """Handle emergency unwind when one leg fails."""
    # Debug logging
    self.logger.info(f"[UNWIND] eth_success={eth_result.success}, sol_success={sol_result.success}")
    self.logger.info(f"[UNWIND] eth_direction={eth_direction}, sol_direction={sol_direction}")

    # Check fill status using OrderResult fields (not relying on external tracking)
    eth_filled = (eth_result.success and
                  eth_result.status == 'FILLED' and
                  eth_result.filled_size > 0)
    sol_filled = (sol_result.success and
                  sol_result.status == 'FILLED' and
                  sol_result.filled_size > 0)

    # Emergency unwind if only one leg filled
    if eth_filled and not sol_filled:
        self.logger.info(f"[UNWIND] ETH filled ({eth_result.filled_size}) but SOL failed, closing ETH")
        await self.emergency_unwind_eth(eth_direction, eth_result.filled_size)
    elif sol_filled and not eth_filled:
        self.logger.info(f"[UNWIND] SOL filled ({sol_result.filled_size}) but ETH failed, closing SOL")
        await self.emergency_unwind_sol(sol_direction, sol_result.filled_size)
    else:
        self.logger.info(f"[UNWIND] Both filled or both failed, no emergency unwind needed")
```

**Acceptance Criteria:**
- Direction passed explicitly (not inferred)
- Fill status checked from OrderResult
- Both legs ending in opposite directions

#### Task 4.2: Add Position Validation
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Verify delta-neutral state after orders.

**Implementation:**
```python
async def validate_dn_state(self, expected_eth_direction: str, expected_sol_direction: str) -> bool:
    """Validate that positions are delta-neutral."""
    eth_pos = await self.eth_client.get_account_positions()
    sol_pos = await self.sol_client.get_account_positions()

    # Expected: ETH long if buy, SOL short if sell
    expected_eth_positive = (expected_eth_direction == "buy")
    expected_sol_positive = (expected_sol_direction == "buy")

    eth_correct = (eth_pos > 0) == expected_eth_positive
    sol_correct = (sol_pos > 0) == expected_sol_positive

    if not eth_correct or not sol_correct:
        self.logger.error(f"[DN VALIDATION] FAILED: "
                         f"ETH pos={eth_pos} (expected {'positive' if expected_eth_positive else 'negative'}), "
                         f"SOL pos={sol_pos} (expected {'positive' if expected_sol_positive else 'negative'})")
        return False

    self.logger.info(f"[DN VALIDATION] PASSED: ETH={eth_pos}, SOL={sol_pos}")
    return True
```

**Acceptance Criteria:**
- Validation called after each cycle
- Error logged if positions wrong
- Returns boolean for health check

---

### Phase 5: Fix Emergency Unwind

#### Task 5.1: Simplify Emergency Unwind
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Remove position checks; use filled order data directly.

**Root Cause:** Position checks are slow and may be delayed.

**Implementation:**
```python
async def emergency_unwind_eth(self, filled_direction: str, filled_qty: Decimal):
    """Emergency unwind ETH using filled order data."""
    if not filled_direction or filled_qty <= 0:
        self.logger.error("[EMERGENCY] Invalid params: direction={}, qty={}".format(
            filled_direction, filled_qty))
        return

    # Opposite direction to close
    close_side = "sell" if filled_direction == "buy" else "buy"

    self.logger.info(f"[EMERGENCY] Closing ETH: {filled_qty} ({close_side})")

    result = await self.eth_client.place_ioc_order(
        self.eth_client.config.contract_id,
        filled_qty,
        close_side
    )

    if result.success and result.filled_size > 0:
        self.logger.info(f"[EMERGENCY] ETH closed: {result.filled_size} @ ${result.price}")
        self.log_trade_to_csv(
            exchange="NADO",
            side=f"ETH-{close_side.upper()}",
            price=str(result.price),
            quantity=str(result.filled_size),
            order_type="exit",
            mode="EMERGENCY"
        )
    else:
        self.logger.error(f"[EMERGENCY] ETH close failed: {result.error_message}")
        # Fallback: try with more aggressive pricing
        await self._emergency_unwind_fallback(self.eth_client, filled_qty, close_side)
```

**Acceptance Criteria:**
- No position checks (uses order data)
- Immediate execution
- Fallback for aggressive pricing

#### Task 5.2: Add Fallback Unwind
**File:** `hedge/DN_pair_eth_sol_nado.py`

**Action:** Implement aggressive fallback if first unwind fails.

**Implementation:**
```python
async def _emergency_unwind_fallback(
    self,
    client: NadoClient,
    quantity: Decimal,
    side: str
):
    """Fallback with aggressive pricing."""
    bid, ask = await client.fetch_bbo_prices(client.config.contract_id)

    # Cross the spread aggressively
    if side == "buy":
        order_price = ask + (client.config.tick_size * Decimal('2'))
    else:
        order_price = bid - (client.config.tick_size * Decimal('2'))

    self.logger.info(f"[EMERGENCY] FALLBACK: {side} {quantity} @ {order_price}")

    result = await client.place_ioc_order(
        client.config.contract_id,
        quantity,
        side
    )

    if result.success:
        self.logger.info(f"[EMERGENCY] FALLBACK succeeded: {result.filled_size} @ ${result.price}")
    else:
        self.logger.error(f"[EMERGENCY] FALLBACK failed: {result.error_message}")
```

**Acceptance Criteria:**
- Cross spread by 2 ticks
- Logged as FALLBACK
- Last resort before manual intervention

---

## Verification Approach

### Unit Verification
1. **BBO Accuracy:** Log BBO vs BookDepth differences
2. **Balance Calculation:** Verify notional imbalance <0.5%
3. **Fill Rate:** Track fill percentages per leg
4. **Direction:** Log position signs after each cycle
5. **Unwind:** Time emergency unwind execution

### Integration Testing
1. Run 5 test cycles with logging enabled
2. Verify CSV output format unchanged
3. Check all 5 issues resolved:
   - BBO within 0.1% of BookDepth
   - Notional imbalance <0.5%
   - Fill rate >90% both legs
   - Opposite direction positions
   - Emergency unwind <5s

### Success Metrics
- BBO accuracy: >99% within 0.1%
- Hedging balance: >95% cycles within 0.5%
- Fill rate: >90% for both legs
- Delta neutral: 100% cycles opposite directions
- Emergency unwind: >95% success rate

---

## Rollback Plan

If fixes introduce new issues:

1. **BBO Fix:** Remove BookDepth validation, use REST only
2. **Balance Fix:** Revert to original calculation (accept 4.5% imbalance)
3. **Fill Rate:** Remove retry logic (accept one-sided fills)
4. **Direction Fix:** Revert to old direction tracking
5. **Unwind Fix:** Restore position-based unwinding

**Rollback Command:** `git revert <commit-hash>`

**Data Recovery:** CSV logs remain readable; no breaking changes

---

## Implementation Order

### Priority 1 (Data Accuracy - Days 1-2)
1. Task 1.1: Add BBO validation
2. Task 1.2: Add staleness detection

### Priority 2 (Balance - Days 3-4)
3. Task 2.1: Adjust SOL calculation
4. Task 2.2: Relax tolerance

### Priority 3 (Fill Rate - Days 5-6)
5. Task 3.1: Add retry logic
6. Task 3.2: Use retry in orders

### Priority 4 (Direction - Days 7-8)
7. Task 4.1: Track direction correctly
8. Task 4.2: Add validation

### Priority 5 (Unwind - Days 9-10)
9. Task 5.1: Simplify unwind
10. Task 5.2: Add fallback

### Testing (Days 11-12)
11. Verification and validation
12. Documentation

---

## Files Modified

### Core Changes
- `hedge/DN_pair_eth_sol_nado.py` (5 tasks)
- `exchanges/nado.py` (2 tasks)
- `exchanges/nado_bbo_handler.py` (1 task)

### No Changes Required
- `exchanges/nado_bookdepth_handler.py` (used as-is)
- `exchanges/nado_websocket_client.py` (used as-is)
- CSV format (unchanged)

---

## Notes

### SOL Tick Size Constraint
The SOL tick_size of 0.1 is an exchange constraint that cannot be changed. At $115 price:
- 0.1 SOL = $11.50 notional
- Minimum balance precision = $11.50 / $100 = 11.5%
- With adjusted sizing, best achievable = ~0.5% imbalance

### IOC Order Behavior
IOC (Immediate-Or-Cancel) orders either:
- Fill completely (status='FILLED')
- Fill partially (status='PARTIALLY_FILLED')
- Don't fill (status='EXPIRED')

The retry logic handles all three cases.

### Emergency Unwind Timing
Emergency unwind must execute within 5 seconds to prevent:
- Price moves against filled leg
- Accumulation of unwanted positions
- Margin requirements breach

The simplified approach using filled order data ensures speed.

---

## Commit Strategy

### Feature Branches
1. `fix/bbo-accuracy` (Tasks 1.1-1.2)
2. `fix/hedging-balance` (Tasks 2.1-2.2)
3. `fix/fill-rate` (Tasks 3.1-3.2)
4. `fix/delta-neutral` (Tasks 4.1-4.2)
5. `fix/emergency-unwind` (Tasks 5.1-5.2)

### Commit Messages
```
fix(bbo): Add BookDepth validation for BBO accuracy

- Validate WebSocket BBO against BookDepth
- Reject stale data (>2 seconds old)
- Fallback to REST if validation fails

Fixes issue #1: SOL orderbook data incorrect

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

### Merge Strategy
- Merge each feature branch after testing
- Run full integration test after all merges
- Tag release as `v1.1.0-dn-fixes`

---

## Success Criteria

### Phase Completion
- [ ] BBO data accurate within 0.1%
- [ ] Notional imbalance <0.5%
- [ ] Fill rate >90% both legs
- [ ] Delta neutral confirmed
- [ ] Emergency unwind <5s

### System Health
- [ ] No error logs during 10-cycle test
- [ ] CSV format backward compatible
- [ ] WebSocket stable (no disconnects)
- [ ] Memory usage stable
- [ ] Position reconciliation matches

### Business Metrics
- [ ] Cycle success rate >95%
- [ ] Average cycle time <30s
- [ ] PnL within expected range
- [ ] No position accumulation
- [ ] Emergency unwinds <5% of cycles
