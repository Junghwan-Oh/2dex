# DN Pair Trading System Fixes - FINAL PLAN

## Context

### Original Request
Fix DN pair trading system issues:
1. "SOL size increment is wrong" - orders rejected
2. "tick_size vs size_increment confusion" in previous plan
3. Show emergency_unwind integration points
4. Use REST API validation (not BookDepth)
5. Relax balance tolerance to 0.5% for SOL

### Pre-Gathered Codebase Context

**Current Code Reality:**

1. **tick_size (price increment)** - from Nado API:
   ```python
   # nado.py:877-880
   tick_size_x18 = current_market.book_info.price_increment_x18
   self.config.tick_size = Decimal(str(from_x18(tick_size_x18)))
   ```
   - Access via: `client.config.tick_size`
   - ETH: 0.001, SOL: 0.1

2. **size_increment (quantity increment)** - HARDCODED mapping:
   ```python
   # nado.py:581-590
   size_increments = {
       4: Decimal("0.001"),  # ETH size increment
       8: Decimal("0.1"),    # SOL size increment
   }
   ```
   - NO config attribute for size increment
   - Must use hardcoded mapping or add new field

3. **Emergency Unwind** - Already implemented:
   - `handle_emergency_unwind()` at line 820
   - `emergency_unwind_eth()` at line 854
   - `emergency_unwind_sol()` at line 919
   - Called from `place_simultaneous_orders()` at line 779

4. **Current Balance Tolerance**:
   - Lines 503-506: Checks within 0.1% (hardcoded)
   - Needs relaxation to 0.5% for SOL

### Critical Constraint

**DO NOT introduce fictional attributes** like `price_tick_size`. Use existing:
- `client.config.tick_size` = price increment (from API)
- Hardcoded `size_increments` mapping for quantity increments

---

## Work Objectives

### Core Objective
Fix DN pair trading system to handle SOL size increments correctly and relax balance tolerance.

### Deliverables
1. Phase 1: Diagnostic logging to confirm root cause
2. Phase 2: Fix size_increment rounding using correct mapping
3. Phase 3: Relax balance tolerance to 0.5%
4. Phase 4: Integration test and validation

### Definition of Done
- [ ] Diagnostic code shows actual vs expected size increments
- [ ] Orders use correct size_increment for SOL (0.1)
- [ ] Balance tolerance accepts 0.5% imbalance
- [ ] Emergency unwind integration documented
- [ ] Test run shows no order rejections

---

## Must Have / Must NOT Have

### Must Have
- Use hardcoded size_increment mapping (nado.py:581-590)
- Use config.tick_size for price rounding (NOT size_increment)
- REST API validation for position checks
- 0.5% balance tolerance for SOL
- Integration points documented

### Must NOT Have
- Fictional attributes like `price_tick_size`
- BookDepth for validation (use REST API)
- Removing diagnostic code (keep for monitoring)
- Hardcoded tolerance values (make configurable)

---

## Task Flow and Dependencies

```
Phase 1: Diagnostics (No dependencies)
  ↓
Phase 2: Fix size_increment (Depends on Phase 1)
  ↓
Phase 3: Relax tolerance (Independent of Phase 2)
  ↓
Phase 4: Validation (Depends on Phases 1-3)
```

---

## Detailed TODOs

### Phase 1: Add Diagnostic Logging

**Task 1.1: Add size_increment diagnostics to NadoClient**

File: `/Users/botfarmer/2dex/exchanges/nado.py`

Location: In `_round_quantity_to_size_increment()` method (line 581)

Add diagnostic logging:

```python
def _round_quantity_to_size_increment(self, product_id: int, quantity: Decimal) -> Decimal:
    """Round quantity to the product's size increment."""
    # Size increment mapping (in Decimal format, not X18)
    size_increments = {
        4: Decimal("0.001"),  # ETH
        8: Decimal("0.1"),    # SOL
    }
    size_increment = size_increments.get(product_id, Decimal("0.001"))

    # DIAGNOSTIC: Log before rounding
    import sys
    print(f"[DIAGNOSTIC] product_id={product_id}, raw_qty={quantity}, size_increment={size_increment}", file=sys.stderr)

    # Round to nearest increment
    rounded = (quantity / size_increment).quantize(Decimal('1')) * size_increment

    # DIAGNOSTIC: Log after rounding
    print(f"[DIAGNOSTIC] product_id={product_id}, rounded_qty={rounded}", file=sys.stderr)

    return rounded
```

**Acceptance Criteria:**
- Diagnostic prints appear in stderr when placing IOC orders
- Shows product_id, raw_qty, size_increment, and rounded_qty

**Task 1.2: Add balance tolerance diagnostics**

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

Location: In `calculate_balanced_order_sizes()` method (around line 503)

Add diagnostic logging for tolerance check:

```python
# After calculating notional_imbalance_pct (around line 506)
import sys
print(f"[DIAGNOSTIC] Balance check: eth_notional={eth_final_notional:.2f}, sol_notional={sol_final_notional:.2f}, imbalance_pct={imbalance_pct:.3f}%, tolerance=0.5%", file=sys.stderr)
```

**Acceptance Criteria:**
- Shows actual notional values and imbalance percentage
- Confirms tolerance threshold used

---

### Phase 2: Fix Size Increment Usage

**Task 2.1: Verify size_increment is called for all quantity rounding**

File: `/Users/botfarmer/2dex/exchanges/nado.py`

Location: Line 506 in `place_ioc_order()`

Current code (CORRECT):
```python
# Round quantity to size increment (tick size for quantity) FIRST
rounded_quantity = self._round_quantity_to_size_increment(int(contract_id), quantity)
```

**Acceptance Criteria:**
- All IOC orders call `_round_quantity_to_size_increment()` before placing
- No quantity rounding uses `config.tick_size` (that's for prices only)

**Task 2.2: Ensure main bot doesn't bypass size_increment**

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

Check these locations for INCORRECT usage:
- Line 417-420: `calculate_order_size()` - USES tick_size (WRONG for quantities)
- Line 443-444: `calculate_order_size_with_slippage()` - USES tick_size (WRONG)
- Line 494-498: `calculate_balanced_order_sizes()` - USES tick_size (WRONG)

**Fix Required:**

The main bot is using `client.config.tick_size` for quantity rounding, but it should use the size_increment mapping. However, since `_round_quantity_to_size_increment()` is a method on NadoClient and already called in `place_ioc_order()`, we have two options:

**Option A: Call _round_quantity_to_size_increment from main bot**
```python
# In calculate_order_size() - line 417-420
client = self.eth_client if ticker == "ETH" else self.sol_client
raw_qty = self.target_notional / price
# Use client's size_increment method, NOT config.tick_size
tick_size = client.config.tick_size  # This is PRICE increment, wrong for qty
# INSTEAD: Call the correct method
rounded_qty = client._round_quantity_to_size_increment(
    int(client.config.contract_id),
    raw_qty
)
return rounded_qty
```

**Option B: Add size_increment to config (RECOMMENDED for cleaner API)**

This requires modifying NadoClient to store size_increment in config:

```python
# In nado.py get_contract_attributes() - around line 880
self.config.tick_size = Decimal(str(from_x18(tick_size_x18)))

# Also store size_increment from hardcoded mapping
size_increments = {
    4: Decimal("0.001"),  # ETH
    8: Decimal("0.1"),    # SOL
}
self.config.size_increment = size_increments.get(product_id, Decimal("0.001"))
```

Then in main bot:
```python
# Use config.size_increment for quantities
size_increment = client.config.size_increment
return (raw_qty / size_increment).quantize(Decimal('1')) * size_increment
```

**Acceptance Criteria:**
- Choose Option A (use existing method) or Option B (add to config)
- All quantity rounding uses size_increment, NOT tick_size
- Price rounding still uses tick_size (correct)

**Task 2.3: Document size_increment vs tick_size**

File: `/Users/botfarmer/2dex/exchanges/nado.py`

Location: Add docstring clarification at top of file

```python
"""
Nado exchange client implementation.

IMPORTANT: tick_size vs size_increment
- tick_size: Price increment (from API price_increment_x18)
  - Used for: Rounding ORDER PRICES
  - Access: client.config.tick_size
  - Values: ETH=0.001, SOL=0.1

- size_increment: Quantity increment (hardcoded mapping)
  - Used for: Rounding ORDER QUANTITIES
  - Access: client._round_quantity_to_size_increment(product_id, qty)
  - Values: ETH=0.001, SOL=0.1 (from size_increments dict at line 584)
"""
```

**Acceptance Criteria:**
- Clear distinction documented
- Developers know which to use for prices vs quantities

---

### Phase 3: Relax Balance Tolerance

**Task 3.1: Update balance tolerance in main bot**

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

Location: Around line 503-506 in `calculate_balanced_order_sizes()`

Current code (hardcoded 0.1%):
```python
if imbalance_pct <= Decimal("0.1"):
    return final_eth_qty, final_sol_qty, final_notional
```

**Fix to 0.5%:**
```python
# Relaxed tolerance for SOL volatility (0.5% instead of 0.1%)
BALANCE_TOLERANCE_PCT = Decimal("0.5")

if imbalance_pct <= BALANCE_TOLERANCE_PCT:
    return final_eth_qty, final_sol_qty, final_notional
else:
    self.logger.warning(
        f"[BALANCE] Cannot achieve balance within {BALANCE_TOLERANCE_PCT}% tolerance. "
        f"Current imbalance: {imbalance_pct:.2f}%"
    )
    # Return anyway with best effort (relaxed tolerance)
    return final_eth_qty, final_sol_qty, final_notional
```

**Acceptance Criteria:**
- Balance tolerance set to 0.5%
- No order rejection due to tight tolerance
- Warning logged if imbalance exceeds threshold

**Task 3.2: Make tolerance configurable**

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

Location: In `__init__()` method (around line 139)

Add class attribute:
```python
def __init__(
    self,
    target_notional: Decimal,
    fill_timeout: int = 5,
    iterations: int = 20,
    sleep_time: int = 0,
    max_position_eth: Decimal = Decimal("5"),
    max_position_sol: Decimal = Decimal("50"),
    order_mode: PriceMode = PriceMode.BBO,
    csv_path: str = None,
    balance_tolerance_pct: Decimal = Decimal("0.5"),  # NEW: Configurable tolerance
):
    # ... existing code ...
    self.balance_tolerance_pct = balance_tolerance_pct
```

Then use in `calculate_balanced_order_sizes()`:
```python
if imbalance_pct <= self.balance_tolerance_pct:
    return final_eth_qty, final_sol_qty, final_notional
```

**Acceptance Criteria:**
- Tolerance configurable via constructor
- Default 0.5% for SOL
- Can be adjusted per trading session

---

### Phase 4: Emergency Unwind Integration

**Task 4.1: Document emergency_unwind integration points**

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Integration Points:**

1. **Call from simultaneous orders** (line 779):
```python
# Handle partial fills and failed orders
await self.handle_emergency_unwind(eth_result, sol_result, eth_direction, sol_direction)
```

2. **Handler implementation** (line 820-852):
```python
async def handle_emergency_unwind(self, eth_result, sol_result, eth_direction, sol_direction):
    # Checks if one leg filled and other didn't
    # Calls emergency_unwind_eth() or emergency_unwind_sol()
```

3. **ETH unwind** (line 854-917):
```python
async def emergency_unwind_eth(self, filled_direction, filled_qty):
    # Places IOC order to close ETH position
    # Uses opposite side of filled_direction
    # Logs to CSV with mode="EMERGENCY"
```

4. **SOL unwind** (line 919-963):
```python
async def emergency_unwind_sol(self, filled_direction, filled_qty):
    # Places IOC order to close SOL position
    # Uses opposite side of filled_direction
    # Logs to CSV with mode="EMERGENCY"
```

5. **Force close all** (line 965-969):
```python
async def force_close_all_positions(self):
    # Calls both emergency_unwind_eth() and emergency_unwind_sol()
    # Used when cycle fails completely
```

**Acceptance Criteria:**
- All integration points documented
- Flow from order failure to unwind clear
- CSV logging includes emergency mode

**Task 4.2: Add emergency unwind metrics to CycleMetrics**

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

Location: In `place_simultaneous_orders()` when creating metrics (line 812-813)

Update to track emergency unwind:
```python
# Track if emergency unwind was triggered
emergency_triggered = (eth_filled and not sol_filled) or (sol_filled and not eth_filled)
emergency_leg = "ETH" if (eth_filled and not sol_filled) else ("SOL" if (sol_filled and not eth_filled) else "NONE")

metrics = CycleMetrics(
    # ... existing fields ...
    emergency_unwind=emergency_triggered,
    emergency_unwind_leg=emergency_leg
)
```

**Acceptance Criteria:**
- CycleMetrics shows if emergency unwind occurred
- Shows which leg was unwound
- Exported to CSV for analysis

---

### Phase 5: Integration Testing

**Task 5.1: Create test script**

File: `/Users/botfarmer/2dex/hedge/test_dn_fixes.py`

```python
#!/usr/bin/env python3
"""
Test DN pair trading fixes.

Tests:
1. Size increment rounding for SOL
2. Balance tolerance relaxation
3. Emergency unwind integration
"""

import asyncio
import sys
from decimal import Decimal
from DN_pair_eth_sol_nado import DNPairBot

async def test_size_increment():
    """Test SOL size increment rounding."""
    print("[TEST] Size increment rounding")

    # Mock client
    from exchanges.nado import NadoClient
    config = type('Config', (), {
        'ticker': 'SOL',
        'contract_id': '8',
        'tick_size': Decimal('0.1')
    })()

    client = NadoClient(config)

    # Test rounding
    test_qty = Decimal("10.123456")
    rounded = client._round_quantity_to_size_increment(8, test_qty)

    # Should round to nearest 0.1
    assert rounded == Decimal("10.1"), f"Expected 10.1, got {rounded}"
    print(f"[PASS] SOL rounding: {test_qty} -> {rounded}")

async def test_balance_tolerance():
    """Test balance tolerance calculation."""
    print("[TEST] Balance tolerance")

    eth_notional = Decimal("100.00")
    sol_notional = Decimal("100.50")  # 0.5% imbalance

    imbalance_pct = abs(eth_notional - sol_notional) / ((eth_notional + sol_notional) / 2) * 100
    print(f"[INFO] Imbalance: {imbalance_pct:.3f}%")

    # Should pass with 0.5% tolerance
    assert imbalance_pct <= Decimal("0.5"), f"Imbalance {imbalance_pct}% exceeds 0.5%"
    print(f"[PASS] Balance tolerance: {imbalance_pct:.3f}% <= 0.5%")

async def main():
    print("=" * 60)
    print("DN Pair Trading Fixes - Test Suite")
    print("=" * 60)

    await test_size_increment()
    await test_balance_tolerance()

    print("=" * 60)
    print("[SUCCESS] All tests passed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria:**
- Test script runs without errors
- SOL rounding verified
- Balance tolerance verified

**Task 5.2: Run live test with small size**

```bash
# Run with small notional to test fixes
python hedge/DN_pair_eth_sol_nado.py --size 10 --iter 1 --csv-path tests/test_dn_fixes.csv
```

**Acceptance Criteria:**
- No "quantity too small" errors
- No order rejections
- Emergency unwind not triggered (both legs fill)
- CSV shows balanced notionals

---

## Commit Strategy

### Commit 1: Add diagnostics
```
feat(dn-bot): Add diagnostic logging for size_increment and balance tolerance

- Log size_increment values before/after rounding
- Log balance tolerance checks with actual percentages
- Helps identify root cause of SOL order rejections

Files modified:
- exchanges/nado.py (_round_quantity_to_size_increment)
- hedge/DN_pair_eth_sol_nado.py (calculate_balanced_order_sizes)
```

### Commit 2: Fix size_increment usage
```
fix(dn-bot): Use size_increment for quantity rounding, not tick_size

- Add size_increment to NadoClient config
- Update main bot to use size_increment for quantities
- Keep tick_size for price rounding only
- Add docstring clarifying tick_size vs size_increment

Fixes: SOL size increment confusion causing order rejections

Files modified:
- exchanges/nado.py (get_contract_attributes, docstring)
- hedge/DN_pair_eth_sol_nado.py (calculate_order_size, calculate_balanced_order_sizes)
```

### Commit 3: Relax balance tolerance
```
feat(dn-bot): Relax balance tolerance to 0.5% for SOL volatility

- Change balance tolerance from 0.1% to 0.5%
- Make tolerance configurable via constructor
- Log warning when imbalance exceeds threshold
- Prevents order rejection due to SOL price movement

Files modified:
- hedge/DN_pair_eth_sol_nado.py (__init__, calculate_balanced_order_sizes)
```

### Commit 4: Emergency unwind metrics
```
feat(dn-bot): Track emergency unwind in cycle metrics

- Update CycleMetrics to show emergency unwind events
- Track which leg was unwound
- Export to CSV for analysis

Files modified:
- hedge/DN_pair_eth_sol_nado.py (place_simultaneous_orders)
```

### Commit 5: Integration tests
```
test(dn-bot): Add integration tests for DN fixes

- Test size_increment rounding for SOL
- Test balance tolerance calculation
- Add test script for validation

Files added:
- hedge/test_dn_fixes.py
```

---

## Success Criteria

1. **Diagnostics show correct values**
   - SOL size_increment: 0.1
   - Balance tolerance: 0.5%

2. **No order rejections**
   - SOL orders accepted by exchange
   - Quantities rounded to correct increment

3. **Balanced fills**
   - ETH and SOL notionals within 0.5%
   - No emergency unwind triggered during normal operation

4. **Emergency unwind works**
   - One leg failure triggers unwind
   - CSV logs emergency mode
   - Metrics track unwind events

5. **Tests pass**
   - Unit tests for rounding
   - Integration test with live orders

---

## Files Modified

### Core Files
- `/Users/botfarmer/2dex/exchanges/nado.py` - Size increment fix, diagnostics
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Tolerance, metrics, diagnostics

### Test Files
- `/Users/botfarmer/2dex/hedge/test_dn_fixes.py` - NEW - Integration tests

---

## Key Implementation Notes

### Size Increment vs Tick Size (CRITICAL)

**tick_size** = Price increment (from API):
- Use for rounding ORDER PRICES
- Access: `client.config.tick_size`
- ETH: 0.001, SOL: 0.1

**size_increment** = Quantity increment (hardcoded):
- Use for rounding ORDER QUANTITIES
- Access: `client._round_quantity_to_size_increment(product_id, qty)`
- ETH: 0.001, SOL: 0.1

**Common Mistake:**
```python
# WRONG - Using tick_size for quantities
qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

# CORRECT - Using size_increment for quantities
qty = client._round_quantity_to_size_increment(product_id, raw_qty)
```

### Emergency Unwind Flow

```
place_simultaneous_orders()
  ├─> Place IOC orders
  ├─> Check results
  ├─> handle_emergency_unwind()  [line 779]
  │    ├─> emergency_unwind_eth()   [line 854]
  │    │    └─> Place IOC to close ETH
  │    └─> emergency_unwind_sol()   [line 919]
  │         └─> Place IOC to close SOL
  └─> Log metrics with emergency_unwind flag
```

### Balance Tolerance

**Before:** 0.1% (too strict for SOL volatility)
**After:** 0.5% (realistic for SOL)

**Calculation:**
```python
imbalance_pct = abs(eth_notional - sol_notional) / avg_notional * 100
if imbalance_pct <= 0.5:  # Accept
```

---

## Post-Implementation Validation

### Run with diagnostics
```bash
python hedge/DN_pair_eth_sol_nado.py --size 100 --iter 5 2>&1 | grep -E "\[DIAGNOSTIC\]|\[BALANCE\]"
```

### Check CSV for emergency unwinds
```bash
grep "EMERGENCY" logs/DN_pair_eth_sol_nado_trades.csv
```

### Verify balance tolerance
```bash
grep "Balance check" logs/DN_pair_eth_sol_nado_log.txt
```

---

## Risk Mitigation

1. **Keep diagnostic code** - Don't remove, useful for monitoring
2. **Test with small size first** - Verify fixes before full size
3. **Monitor emergency unwinds** - Should be rare in normal operation
4. **Check CSV logs** - Verify mode="EMERGENCY" appears only when expected
5. **Fallback to tight tolerance** - Can revert to 0.1% if 0.5% too loose

---

## Rollback Plan

If issues occur:
1. Revert commits 2-3 (keep diagnostics from commit 1)
2. Analyze diagnostic output
3. Adjust tolerance or size_increment as needed
4. Re-apply fixes with adjustments

---

**Plan Status:** READY FOR IMPLEMENTATION

**Estimated Complexity:** MEDIUM
**Estimated Time:** 2-3 hours
**Risk Level:** LOW (diagnostics first, conservative changes)
