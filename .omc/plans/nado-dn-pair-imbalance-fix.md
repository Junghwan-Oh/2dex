# Nado DN Pair - Hedging Imbalance Complete Fix Plan

**Created**: 2026-01-30
**Status**: ACTIVE - ROOT CAUSE IDENTIFIED
**Methodology**: Root Cause Analysis → Fix → Verify
**Priority**: CRITICAL
**Estimated Duration**: 4-6 hours

---

## Executive Summary

### Critical Finding

The `calculate_balanced_quantities()` function **DOES work correctly** and achieves **0.06% imbalance**, but its results are **being IGNORED** in production.

### Evidence

| Metric | Function Result | Production Actual | Difference |
|--------|----------------|-------------------|------------|
| ETH Quantity | 0.042 | 0.036 | Function ignored |
| SOL Quantity | 1.0 | 0.9 | Function ignored |
| ETH Notional | $115.79 | $99.25 | +$16.54 |
| SOL Notional | $115.86 | $104.27 | +$11.59 |
| **Imbalance** | **0.06%** ✓ | **5.06%** ✗ | **84x worse** |

### Root Cause

The function call chain:
1. `execute_dn_pair_entry()` calls `calculate_balanced_order_sizes()`
2. `calculate_balanced_order_sizes()` calls `calculate_balanced_quantities()` ✓
3. **BUT**: The returned quantities may be overridden or not used properly

### Impact

- **Current**: 5.06% hedging imbalance (unacceptable for market making)
- **Target**: <0.1% imbalance (already achieved by function!)
- **Financial risk**: 5% notional mismatch on every trade

---

## Phase 1: Root Cause Verification (30 minutes)

### Task 1.1: Add Debug Logging

**Objective**: Verify that `calculate_balanced_quantities` is being called and what it returns.

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Location**: In `calculate_balanced_order_sizes()` method, right after line 619:

```python
# Use the new balanced quantities function
eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
    self.target_notional,
    eth_price,
    sol_price,
    eth_tick_size,
    sol_tick_size
)

# DEBUG: Log what the function returned
self.logger.debug(
    f"[DEBUG] calculate_balanced_quantities RETURNED: "
    f"eth_qty={eth_qty}, sol_qty={sol_qty}, imbalance={imbalance:.4f}"
)

# Log the achieved balance
eth_notional = eth_qty * eth_price
sol_notional = sol_qty * sol_price
self.logger.info(
    f"[BALANCE] Calculated quantities: "
    f"ETH {eth_qty} (${eth_notional:.2f}), "
    f"SOL {sol_qty} (${sol_notional:.2f}), "
    f"Imbalance: {imbalance * 100:.3f}%"
)
```

**Acceptance Criteria**:
- Debug log shows function returns ETH=0.042, SOL=1.0, imbalance=0.0006
- OR debug log shows function returns ETH=0.036, SOL=0.9 (indicating function bug)

---

### Task 1.2: Trace Call Chain

**Objective**: Identify where the function's return values are being overridden.

**Add logs at these locations**:

1. **After `calculate_balanced_order_sizes()` returns** (line 647):
```python
actual_notional = max(eth_notional, sol_notional)
self.logger.debug(f"[DEBUG] calculate_balanced_order_sizes RETURNING: eth_qty={eth_qty}, sol_qty={sol_qty}")
return eth_qty, sol_qty, actual_notional
```

2. **After assignment in `execute_dn_pair_entry()`** (after line 749):
```python
eth_qty, sol_qty, actual_notional = await self.calculate_balanced_order_sizes(
    eth_price, sol_price, eth_direction, sol_direction, max_slippage_bps=20
)

# DEBUG: Log what we received
self.logger.debug(f"[DEBUG] Received from calculate_balanced_order_sizes: eth_qty={eth_qty}, sol_qty={sol_qty}")
```

3. **Before placing orders** (before actual order placement calls):
```python
# DEBUG: Log what quantities will be used for orders
self.logger.info(f"[ORDER] About to place orders: ETH qty={eth_qty}, SOL qty={sol_qty}")
```

**Acceptance Criteria**:
- Logs show exact quantities at each step
- Identify where quantities change from 0.042/1.0 to 0.036/0.9

---

## Phase 2: Fix Implementation (1-2 hours)

### Scenario A: Function Not Being Called

**If logs show `calculate_balanced_order_sizes` is never called**:

**Root Cause**: Code path uses old `calculate_order_size_with_slippage()` method.

**Fix**: Ensure `calculate_balanced_order_sizes()` is the ONLY method used for quantity calculation.

**Location**: Search for all calls to `calculate_order_size_with_slippage()` and replace with `calculate_balanced_order_sizes()`.

**Files to check**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

---

### Scenario B: Function Returns Wrong Values

**If logs show function returns ETH=0.036, SOL=0.9**:

**Root Cause**: Function implementation has bug in optimization logic.

**Fix**: Review the 20% deviation constraint (line 506):

```python
# Current: Skip if notionals are too far from target (more than 20% deviation)
eth_deviation = abs(test_eth_notional - target_notional) / target_notional
sol_deviation = abs(test_sol_notional - target_notional) / target_notional
if eth_deviation > Decimal("0.2") or sol_deviation > Decimal("0.2"):
    continue
```

**Issue**: The optimal quantities (ETH=0.042, SOL=1.0) have notionals of $115.79 and $115.86, which are 15.79% and 15.86% away from $100 target. This should NOT trigger the 20% skip.

**Verification**: Test if the deviation check is incorrectly filtering out the optimal solution.

---

### Scenario C: Return Values Ignored

**If logs show function returns correct values but they're overridden**:

**Root Cause**: Return values from `calculate_balanced_order_sizes()` are being ignored or reassigned.

**Fix**: Find and remove any code that reassigns `eth_qty` or `sol_qty` after the function call.

**Likely locations**:
- Slippage estimation code (lines 761-766)
- Any additional quantity calculation after line 749
- Order preparation logic

**Search pattern**:
```python
# Find any lines that look like:
eth_qty = ...  # After line 749
sol_qty = ...  # After line 749
```

---

## Phase 3: Verification (1 hour)

### Task 3.1: Unit Test with Real Prices

**File**: `/Users/botfarmer/2dex/tests/test_real_world_imbalance.py`

**Create new test**:

```python
import pytest
from decimal import Decimal
from hedge.DN_pair_eth_sol_nado import calculate_balanced_quantities

def test_production_prices_achieves_target():
    """
    Test with actual production prices from 2026-01-30.

    This test verifies that the function achieves <0.1% imbalance
    with real-world prices that previously caused 5.06% imbalance.
    """
    target = Decimal('100')
    eth_price = Decimal('2756.9')
    sol_price = Decimal('115.86')
    eth_tick = Decimal('0.001')
    sol_tick = Decimal('0.1')

    eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
        target, eth_price, sol_price, eth_tick, sol_tick
    )

    # Verify imbalance target achieved
    assert imbalance < Decimal('0.001'), \
        f"Imbalance {imbalance:.4f} exceeds 0.1% target"

    # Verify quantities are different from production (which had 5.06%)
    assert eth_qty != Decimal('0.036') or sol_qty != Decimal('0.9'), \
        "Function should return different quantities than production bug"

    # Calculate actual notionals
    eth_notional = eth_qty * eth_price
    sol_notional = sol_qty * sol_price

    # Verify notionals are close to target (within 20%)
    assert abs(eth_notional - target) / target < Decimal('0.2'), \
        f"ETH notional ${eth_notional:.2f} deviates too much from ${target}"
    assert abs(sol_notional - target) / target < Decimal('0.2'), \
        f"SOL notional ${sol_notional:.2f} deviates too much from ${target}"

    print(f"\n[TEST] Production prices test:")
    print(f"  ETH: {eth_qty} × ${eth_price} = ${eth_notional:.2f}")
    print(f"  SOL: {sol_qty} × ${sol_price} = ${sol_notional:.2f}")
    print(f"  Imbalance: {imbalance:.4f} ({imbalance * 100:.2f}%)")
```

**Acceptance Criteria**:
- Test passes
- Imbalance < 0.1%
- Quantities differ from production bug values

---

### Task 3.2: Integration Test

**File**: `/Users/botfarmer/2dex/hedge/test_imbalance_fix.py`

**Create integration test**:

```python
#!/usr/bin/env python3
"""Test imbalance fix with real mainnet data."""

import asyncio
import os
from decimal import Decimal
from dotenv import load_dotenv

os.environ['NADO_MODE'] = 'MAINNET'
load_dotenv()

from hedge.DN_pair_eth_sol_nado import DNPairBot

async def test_imbalance_fix():
    """Verify that balanced quantities are actually used in trading."""
    print("=" * 60)
    print("Testing Imbalance Fix")
    print("=" * 60)

    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
        sleep_time=1
    )

    await bot.initialize_clients()

    # Wait for BookDepth
    if not await bot.wait_for_bookdepth_ready(timeout_seconds=10):
        print("ERROR: BookDepth not ready")
        bot.shutdown()
        return

    # Execute one DN pair cycle
    print("\nExecuting DN pair entry...")
    result = await bot.execute_dn_pair_entry(
        eth_direction="buy",
        sol_direction="sell"
    )

    # Check the results
    if result[0].success and result[1].success:
        print("✓ Orders placed successfully")

        # Read back the trade data from CSV
        import csv
        from pathlib import Path

        csv_path = Path("logs/DN_pair_eth_sol_nado_trades.csv")
        if csv_path.exists():
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Get the last two trades (ETH and SOL)
            if len(rows) >= 2:
                eth_trade = rows[-2]
                sol_trade = rows[-1]

                eth_qty = Decimal(eth_trade['quantity'])
                sol_qty = Decimal(sol_trade['quantity'])
                eth_price = Decimal(eth_trade['price'])
                sol_price = Decimal(sol_trade['price'])

                eth_notional = eth_qty * eth_price
                sol_notional = sol_qty * sol_price
                imbalance = abs(sol_notional - eth_notional) / eth_notional

                print(f"\nActual Trade Results:")
                print(f"  ETH: {eth_qty} × ${eth_price} = ${eth_notional:.2f}")
                print(f"  SOL: {sol_qty} × ${sol_price} = ${sol_notional:.2f}")
                print(f"  Imbalance: {imbalance:.4f} ({imbalance * 100:.2f}%)")

                if imbalance < Decimal('0.001'):
                    print("\n✓ SUCCESS: Imbalance < 0.1%")
                else:
                    print(f"\n✗ FAIL: Imbalance {imbalance * 100:.2f}% exceeds 0.1% target")

                # Close positions
                await bot.force_close_all_positions()

    bot.shutdown()

if __name__ == '__main__':
    asyncio.run(test_imbalance_fix())
```

**Acceptance Criteria**:
- Test runs successfully
- Actual trades show <0.1% imbalance
- CSV logs confirm correct quantities used

---

## Phase 4: Production Validation (1 hour)

### Task 4.1: Deploy to Mainnet

**Steps**:
1. Backup current version: `cp hedge/DN_pair_eth_sol_nado.py hedge/DN_pair_eth_sol_nado.py.backup`
2. Deploy fix
3. Monitor logs for `[DEBUG]` messages
4. Execute 5 test cycles
5. Verify CSV trade data

**Acceptance Criteria**:
- All 5 cycles successful
- All cycles show <0.1% imbalance in CSV
- No regression in fill rate

---

### Task 4.2: Monitor and Verify

**Metrics to track**:

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Hedging Imbalance | 5.06% | ? | <0.1% |
| Fill Rate | 100% | ? | ≥95% |
| Cycle Success Rate | 100% | ? | ≥95% |

**Verification commands**:

```bash
# Check latest trades
tail -20 logs/DN_pair_eth_sol_nado_trades.csv

# Calculate imbalance
python3 << 'EOF'
import csv
from decimal import Decimal

with open('logs/DN_pair_eth_sol_nado_trades.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Analyze last 10 trades (5 pairs)
for i in range(len(rows) - 10, len(rows), 2):
    if i + 1 < len(rows):
        eth_row = rows[i]
        sol_row = rows[i + 1]

        if 'ETH' in eth_row['side'] and 'SOL' in sol_row['side']:
            eth_qty = Decimal(eth_row['quantity'])
            sol_qty = Decimal(sol_row['quantity'])
            eth_price = Decimal(eth_row['price'])
            sol_price = Decimal(sol_row['price'])

            eth_notional = eth_qty * eth_price
            sol_notional = sol_qty * sol_price
            imbalance = abs(sol_notional - eth_notional) / eth_notional

            print(f"Trade {i}: Imbalance = {imbalance * 100:.2f}%")
EOF
```

**Acceptance Criteria**:
- All trades show <0.1% imbalance
- No errors or warnings in logs
- System stable for 1 hour

---

## Phase 5: Rollback Plan (if needed)

### If Fix Causes Issues

**Symptoms that require rollback**:
- Fill rate drops below 90%
- Orders start failing
- Slippage exceeds limits
- System instability

**Rollback steps**:

```bash
# Stop the bot
# pkill -f DN_pair_eth_sol_nado

# Restore backup
cp hedge/DN_pair_eth_sol_nado.py.backup hedge/DN_pair_eth_sol_nado.py

# Restart
python3 hedge/DN_pair_eth_sol_nado.py
```

**Alternative fix if rollback needed**:
- Accept 5% imbalance temporarily
- Investigate why optimal quantities cause issues
- Possibly adjust slippage limits
- Re-test with smaller deviations

---

## Success Criteria

### Must Have (Blocking)

- [ ] `calculate_balanced_quantities` returns ETH=0.042, SOL=1.0 (or similar optimal values)
- [ ] Production code uses these quantities (not ETH=0.036, SOL=0.9)
- [ ] Unit test with production prices passes (imbalance <0.1%)
- [ ] Integration test shows actual trades with <0.1% imbalance
- [ ] CSV trade data confirms <0.1% imbalance in production
- [ ] Fill rate remains ≥95%

### Nice to Have

- [ ] Additional test coverage for edge cases
- [ ] Performance metrics dashboard
- [ ] Automated regression tests

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Optimal quantities exceed slippage limits | Medium | Medium | Adjust slippage tolerance or accept slightly higher imbalance |
| Fill rate decreases | Low | High | Monitor closely, rollback if needed |
| Bug in fix causes orders to fail | Low | High | Comprehensive testing before deployment |
| Deviation constraint too restrictive | Medium | Low | Relax to 25% if needed |

---

## Notes

### About the "40x Difference"

The user's request mentions "40x 차이" (40x difference), but actual analysis shows:
- **Notional imbalance: 5.06%** (not 4000%)
- **Quantity ratio: 25x** (0.9 SOL / 0.036 ETH = 25x)

The "40x" might refer to:
1. A mischaracterization of the 5.06% imbalance
2. The quantity ratio (25x, rounded up)
3. A different metric not yet identified

Regardless, the fix addresses the core issue: **achieving <0.1% notional imbalance**.

### Why This Matters

Market making requires precise hedging:
- 5% imbalance = $5 loss on every $100 trade
- Over 100 trades = $500 avoidable loss
- With optimal quantities = $6 loss total (0.06%)
- **Savings: $494 per 100 trades**

---

**Last Updated**: 2026-01-30
**Status**: READY FOR IMPLEMENTATION
**Next Step**: Execute Phase 1 (Root Cause Verification)
