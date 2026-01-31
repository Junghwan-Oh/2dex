# Nado DN Pair - Practical Fixes Plan

**Created**: 2026-01-30
**Status**: ACTIVE
**Methodology**: Issue-Driven (based on actual test results)
**Estimated Duration**: 10-15 hours

---

## Executive Summary

Based on $100 notional testing (5/5 cycles = 100% success), we have working DN pair trading but need to fix:
1. **Hedging imbalance 4.9%** → Target: <0.1%
2. **Test coverage 28%** → Target: >85%
3. **Production reliability** → E2E testing

---

## Priority 1: Fix Hedging Imbalance (CRITICAL)

### Issue
```
For $100 notional:
ETH: 0.036 × $2757 = $99.25
SOL: 0.9 × $115.86 = $104.27
Imbalance: 5.06% (target: 0.1%)
```

### Root Cause
- ETH tick_size: 0.001
- SOL tick_size: 0.1
- Different rounding causes mismatched notionals

### Solution: Iterative Quantity Adjustment

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Algorithm**:
```python
def calculate_balanced_quantities(target_notional, eth_price, sol_price, eth_tick, sol_tick):
    """
    Find quantities that minimize notional difference.

    Returns: (eth_qty, sol_qty, actual_imbalance)
    """
    # Calculate initial quantities
    eth_qty = round(target_notional / eth_price / eth_tick) * eth_tick
    sol_qty = round(target_notional / sol_price / sol_tick) * sol_tick

    # Calculate notionals
    eth_notional = eth_qty * eth_price
    sol_notional = sol_qty * sol_price

    # If imbalance > 0.1%, adjust iteratively
    imbalance = abs(sol_notional - eth_notional) / eth_notional

    if imbalance > 0.001:  # 0.1%
        # Try adjusting SOL up/down by 1 tick
        sol_qty_up = sol_qty + sol_tick
        sol_qty_down = max(sol_tick, sol_qty - sol_tick)

        # Calculate imbalance for each option
        notional_up = abs(sol_qty_up * sol_price - eth_notional) / eth_notional
        notional_down = abs(sol_qty_down * sol_price - eth_notional) / eth_notional
        notional_current = imbalance

        # Choose best option
        if min(notional_up, notional_down, notional_current) == notional_up:
            sol_qty = sol_qty_up
            imbalance = notional_up
        elif min(notional_up, notional_down, notional_current) == notional_down:
            sol_qty = sol_qty_down
            imbalance = notional_down

    return eth_qty, sol_qty, imbalance
```

**Acceptance Criteria**:
- Hedging imbalance < 0.1% for $100 notional
- Hedging imbalance < 0.5% for $50 notional
- No degradation in fill rate

**Estimated Time**: 2 hours

---

## Priority 2: Improve Test Coverage (HIGH)

### Current State
```
Overall: 28%
exchanges.nado: 32%
hedge.DN_pair_eth_sol_nado: 27%
```

### Target State
```
Overall: >85%
exchanges.nado: >90%
hedge.DN_pair_eth_sol_nado: >85%
```

### Missing Test Coverage

**File**: `/Users/botfarmer/2dex/tests/coverage_gaps.py`

**1. Price Rounding Tests**
```python
def test_round_price_to_increment_eth():
    """Test ETH price rounding to 0.0001"""
    # Test cases: normal, edge, rounding

def test_round_price_to_increment_sol():
    """Test SOL price rounding to 0.01"""
```

**2. Quantity Calculation Tests**
```python
def test_calculate_order_sizes_basic():
    """Test basic size calculation"""

def test_calculate_order_sizes_tick_alignment():
    """Test tick size alignment"""

def test_calculate_balanced_quantities():
    """Test balanced quantity adjustment"""
```

**3. Order Result Handling Tests**
```python
def test_order_result_negative_filled_size():
    """Test that sell orders with negative filled_size are handled correctly"""

def test_order_result_zero_filled_size():
    """Test that unfilled orders return success=False"""
```

**4. Integration Tests**
```python
def test_full_cycle_build_unwind():
    """Test complete BUILD → UNWIND cycle"""

def test_alternating_strategy_dn_direction():
    """Verify DN direction alternates correctly"""

def test_emergency_unwind_partial_fill():
    """Test emergency unwind when only one leg fills"""
```

**Acceptance Criteria**:
- All new tests pass
- Coverage increases to >85%
- No regression in functionality

**Estimated Time**: 4 hours

---

## Priority 3: Production Reliability (MEDIUM)

### Issue: Manual Testing Required

**Current**: Test requires manual execution
`python3 hedge/test_alternating.py`

**Solution**: Automated E2E Tests

**File**: `/Users/botfarmer/2dex/tests/test_e2e_automated.py`

```python
import pytest
from hedge.DN_pair_eth_sol_nado import DNPairBot

@pytest.mark.e2e
@pytest.mark.parametrize("notional,iterations", [
    (Decimal("50"), 3),
    (Decimal("100"), 5),
    (Decimal("200"), 3),
])
async def test_automated_dn_pair_cycles(notional, iterations):
    """Automated E2E test with multiple configurations"""
    bot = DNPairBot(
        target_notional=notional,
        iterations=iterations,
        sleep_time=0
    )

    await bot.initialize_clients()
    ready = await bot.wait_for_bookdepth_ready(timeout_seconds=10)
    assert ready, "BookDepth not ready"

    results = await bot.run_alternating_strategy()

    # Verify all cycles succeeded
    success_rate = sum(results) / len(results)
    assert success_rate >= 0.8, f"Success rate {success_rate} < 80%"

    # Verify positions are closed
    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()
    assert abs(eth_pos) < 0.001, f"ETH position not closed: {eth_pos}"
    assert abs(sol_pos) < 0.001, f"SOL position not closed: {sol_pos}"

    bot.shutdown()
```

**Acceptance Criteria**:
- E2E tests can run via `pytest`
- Tests cover multiple notionals ($50, $100, $200)
- Tests verify position cleanup
- CI/CD integration ready

**Estimated Time**: 2 hours

---

## Priority 4: Documentation & Monitoring (LOW)

### Trade Metrics Dashboard

**File**: `/Users/botfarmer/2dex/hedge/metrics_dashboard.py`

```python
def generate_trade_summary():
    """Generate summary from CSV trades"""
    # Read trades CSV
    # Calculate:
    #   - Success rate
    #   - Average cycle time
    #   - Hedging imbalance (avg, max)
    #   - PnL per cycle
    #   - Fill rate
```

**Acceptance Criteria**:
- Dashboard readable after each test
- Metrics export to JSON for monitoring
- Historical tracking capability

**Estimated Time**: 1 hour

---

## Implementation Order

### Week 1: Critical Fixes
1. **Day 1**: Priority 1 - Fix hedging imbalance (2h)
2. **Day 2**: Priority 2a - Add critical tests (2h)
3. **Day 3**: Priority 2b - Integration tests (2h)
4. **Day 4**: Priority 3 - E2E automation (2h)
5. **Day 5**: Buffer for fixes/review (4h)

### Total Estimated Time: 12-15 hours

---

## Success Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Hedging Imbalance | 4.9% | <0.1% | Automated test |
| Test Coverage | 28% | >85% | pytest --cov |
| Fill Rate | 100% | ≥95% | E2E test |
| Cycle Success Rate | 100% | ≥95% | E2E test |
| Automation | Manual | Automated | pytest runs |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tick size constraint | High | Accept 0.1% minimum for small notionals |
| Test flakiness | Medium | Use mainnet, handle latency |
| Regression | Medium | Run full test suite after changes |

---

## Notes

- This plan focuses on **practical fixes** vs. theoretical migration
- TDD methodology applies to all new code
- All tests must pass before considering a task complete
- Real mainnet testing required (no testnet available)

**Last Updated**: 2026-01-30
**Status**: READY FOR IMPLEMENTATION
