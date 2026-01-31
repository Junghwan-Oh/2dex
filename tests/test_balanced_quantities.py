"""
Test calculate_balanced_quantities function for fixing hedging imbalance.

TDD Approach: RED (failing tests) -> GREEN (implementation) -> REFACTOR

This test file implements Priority 1 from the Nado DN Pair Practical Fixes Plan:
- Fix Hedging Imbalance (CRITICAL)
- Reduce 4.9% imbalance to <0.1%

Algorithm to Test:
    def calculate_balanced_quantities(target_notional, eth_price, sol_price, eth_tick, sol_tick):
        Find quantities that minimize notional difference.
        Returns: (eth_qty, sol_qty, actual_imbalance)

Test Cases:
1. Test $100 notional with current prices (ETH $2757, SOL $115.86)
2. Test $50 notional (smaller size)
3. Test $200 notional (larger size)
4. Verify imbalance < 0.1% for $100
5. Verify imbalance < 0.5% for $50
6. Edge cases: zero notional, negative prices, extreme prices
"""

import pytest
from decimal import Decimal
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to import the function - it doesn't exist yet, so tests will fail
try:
    from hedge.DN_pair_eth_sol_nado import calculate_balanced_quantities
    FUNCTION_EXISTS = True
except ImportError:
    FUNCTION_EXISTS = False


class TestCalculateBalancedQuantities:
    """Test the calculate_balanced_quantities function."""

    def test_100_notional_real_prices(self):
        """
        TEST: $100 notional with real-world prices (ETH $2757, SOL $115.86).

        This is the PRIMARY test case from the plan:
        - ETH: 0.036 × $2757 = $99.25
        - SOL: 0.9 × $115.86 = $104.27
        - Current imbalance: 5.06%
        - Target: < 0.1%

        Expected behavior:
        - Returns tick-aligned quantities
        - Achieves < 0.1% imbalance
        - Returns actual imbalance percentage

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        # Real-world prices from the plan
        target_notional = Decimal("100")
        eth_price = Decimal("2757")
        sol_price = Decimal("115.86")
        eth_tick = Decimal("0.001")
        sol_tick = Decimal("0.1")

        # Call the function
        eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
            target_notional, eth_price, sol_price, eth_tick, sol_tick
        )

        # Calculate actual notionals
        eth_notional = eth_qty * eth_price
        sol_notional = sol_qty * sol_price

        # Verify quantities are tick-aligned
        eth_ticks = eth_qty / eth_tick
        sol_ticks = sol_qty / sol_tick
        assert eth_ticks == int(eth_ticks), f"ETH qty {eth_qty} not tick-aligned to {eth_tick}"
        assert sol_ticks == int(sol_ticks), f"SOL qty {sol_qty} not tick-aligned to {sol_tick}"

        # Verify non-zero quantities
        assert eth_qty > 0, "ETH quantity must be > 0"
        assert sol_qty > 0, "SOL quantity must be > 0"

        # PRIMARY ASSERTION: Imbalance < 0.1%
        assert imbalance < 0.001, f"Imbalance {imbalance:.4f} (0.1%) exceeds target"

        # Verify actual notionals are close to target
        assert eth_notional > 0, "ETH notional must be > 0"
        assert sol_notional > 0, "SOL notional must be > 0"

        # Log results for verification
        print(f"\n[TEST] $100 Notional Results:")
        print(f"  ETH: {eth_qty} × ${eth_price} = ${eth_notional:.2f}")
        print(f"  SOL: {sol_qty} × ${sol_price} = ${sol_notional:.2f}")
        print(f"  Imbalance: {imbalance:.4f} ({imbalance * 100:.2f}%)")

    def test_50_notional_smaller_size(self):
        """
        TEST: $50 notional (smaller size).

        For smaller notionals, the tick size constraint may prevent
        achieving < 0.1% imbalance, so we accept < 0.5%.

        Expected behavior:
        - Returns tick-aligned quantities
        - Achieves < 0.5% imbalance (relaxed for small sizes)
        - Quantities are reasonable for $50 notional

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        target_notional = Decimal("50")
        eth_price = Decimal("2757")
        sol_price = Decimal("115.86")
        eth_tick = Decimal("0.001")
        sol_tick = Decimal("0.1")

        eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
            target_notional, eth_price, sol_price, eth_tick, sol_tick
        )

        # Verify quantities are tick-aligned
        eth_ticks = eth_qty / eth_tick
        sol_ticks = sol_qty / sol_tick
        assert eth_ticks == int(eth_ticks), f"ETH qty {eth_qty} not tick-aligned to {eth_tick}"
        assert sol_ticks == int(sol_ticks), f"SOL qty {sol_qty} not tick-aligned to {sol_tick}"

        # Verify non-zero quantities
        assert eth_qty > 0, "ETH quantity must be > 0"
        assert sol_qty > 0, "SOL quantity must be > 0"

        # RELAXED ASSERTION for small sizes: < 0.5%
        assert imbalance < 0.005, f"Imbalance {imbalance:.4f} (0.5%) exceeds target for $50"

        print(f"\n[TEST] $50 Notional Results:")
        print(f"  ETH: {eth_qty} × ${eth_price} = ${eth_qty * eth_price:.2f}")
        print(f"  SOL: {sol_qty} × ${sol_price} = ${sol_qty * sol_price:.2f}")
        print(f"  Imbalance: {imbalance:.4f} ({imbalance * 100:.2f}%)")

    def test_200_notional_larger_size(self):
        """
        TEST: $200 notional (larger size).

        For larger notionals, we should be able to achieve better balance
        due to more granular tick adjustment options.

        Expected behavior:
        - Returns tick-aligned quantities
        - Achieves < 0.1% imbalance
        - Quantities are approximately double the $100 case

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        target_notional = Decimal("200")
        eth_price = Decimal("2757")
        sol_price = Decimal("115.86")
        eth_tick = Decimal("0.001")
        sol_tick = Decimal("0.1")

        eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
            target_notional, eth_price, sol_price, eth_tick, sol_tick
        )

        # Verify quantities are tick-aligned
        eth_ticks = eth_qty / eth_tick
        sol_ticks = sol_qty / sol_tick
        assert eth_ticks == int(eth_ticks), f"ETH qty {eth_qty} not tick-aligned to {eth_tick}"
        assert sol_ticks == int(sol_ticks), f"SOL qty {sol_qty} not tick-aligned to {sol_tick}"

        # Verify non-zero quantities
        assert eth_qty > 0, "ETH quantity must be > 0"
        assert sol_qty > 0, "SOL quantity must be > 0"

        # ASSERTION: < 0.1% for larger sizes
        assert imbalance < 0.001, f"Imbalance {imbalance:.4f} (0.1%) exceeds target for $200"

        print(f"\n[TEST] $200 Notional Results:")
        print(f"  ETH: {eth_qty} × ${eth_price} = ${eth_qty * eth_price:.2f}")
        print(f"  SOL: {sol_qty} × ${sol_price} = ${sol_qty * sol_price:.2f}")
        print(f"  Imbalance: {imbalance:.4f} ({imbalance * 100:.2f}%)")

    def test_different_price_combinations(self):
        """
        TEST: Various price combinations to ensure robustness.

        Tests different price scenarios:
        - ETH much higher than SOL
        - ETH and SOL close in price
        - Extreme price ratios

        Expected behavior:
        - Algorithm works with any price combination
        - Always returns tick-aligned quantities
        - Maintains reasonable balance

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        test_cases = [
            # (target_notional, eth_price, sol_price, description)
            (Decimal("100"), Decimal("3000"), Decimal("100"), "ETH 30x SOL"),
            (Decimal("100"), Decimal("2000"), Decimal("80"), "ETH 25x SOL"),
            (Decimal("100"), Decimal("150"), Decimal("100"), "ETH 1.5x SOL"),
        ]

        for target, eth_p, sol_p, desc in test_cases:
            eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
                target, eth_p, sol_p, Decimal("0.001"), Decimal("0.1")
            )

            # Verify tick alignment
            eth_ticks = eth_qty / Decimal("0.001")
            sol_ticks = sol_qty / Decimal("0.1")
            assert eth_ticks == int(eth_ticks), f"[{desc}] ETH qty not tick-aligned"
            assert sol_ticks == int(sol_ticks), f"[{desc}] SOL qty not tick-aligned"

            # Verify non-zero
            assert eth_qty > 0, f"[{desc}] ETH qty must be > 0"
            assert sol_qty > 0, f"[{desc}] SOL qty must be > 0"

            # Verify reasonable balance (< 1% for extreme cases)
            assert imbalance < 0.01, f"[{desc}] Imbalance {imbalance:.4f} too high"

            print(f"\n[TEST] {desc}:")
            print(f"  ETH: {eth_qty} × ${eth_p} = ${eth_qty * eth_p:.2f}")
            print(f"  SOL: {sol_qty} × ${sol_p} = ${sol_qty * sol_p:.2f}")
            print(f"  Imbalance: {imbalance:.4f} ({imbalance * 100:.2f}%)")

    def test_edge_case_zero_notional(self):
        """
        TEST: Edge case - zero notional.

        Expected behavior:
        - Returns zero quantities
        - Returns zero imbalance
        - Handles gracefully without error

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        eth_qty, sol_qty, imbalance = calculate_balanced_quantities(
            Decimal("0"), Decimal("2757"), Decimal("115.86"),
            Decimal("0.001"), Decimal("0.1")
        )

        # Should return zero quantities for zero notional
        assert eth_qty == 0, "ETH qty should be 0 for zero notional"
        assert sol_qty == 0, "SOL qty should be 0 for zero notional"
        assert imbalance == 0, "Imbalance should be 0 for zero notional"

    def test_edge_case_negative_prices(self):
        """
        TEST: Edge case - negative prices (invalid input).

        Expected behavior:
        - Function should handle negative prices gracefully
        - Either raise ValueError or return zero quantities
        - Should not crash

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        # Test with negative price - should handle gracefully
        with pytest.raises((ValueError, AssertionError)):
            calculate_balanced_quantities(
                Decimal("100"), Decimal("-2757"), Decimal("115.86"),
                Decimal("0.001"), Decimal("0.1")
            )

    def test_imbalance_calculation_accuracy(self):
        """
        TEST: Verify imbalance calculation is accurate.

        The imbalance should be calculated as:
        imbalance = abs(sol_notional - eth_notional) / eth_notional

        Expected behavior:
        - Returned imbalance matches calculated imbalance
        - Calculation is accurate to 6 decimal places

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        target_notional = Decimal("100")
        eth_price = Decimal("2757")
        sol_price = Decimal("115.86")

        eth_qty, sol_qty, returned_imbalance = calculate_balanced_quantities(
            target_notional, eth_price, sol_price,
            Decimal("0.001"), Decimal("0.1")
        )

        # Calculate expected imbalance
        eth_notional = eth_qty * eth_price
        sol_notional = sol_qty * sol_price
        expected_imbalance = abs(sol_notional - eth_notional) / eth_notional

        # Verify returned imbalance matches calculation
        assert abs(returned_imbalance - expected_imbalance) < Decimal("0.000001"), \
            f"Returned imbalance {returned_imbalance} doesn't match calculated {expected_imbalance}"

    def test_iterative_adjustment_improves_balance(self):
        """
        TEST: Verify iterative adjustment actually improves balance.

        The algorithm should:
        1. Calculate initial quantities
        2. Check if imbalance > 0.1%
        3. Try adjusting SOL up/down by 1 tick
        4. Choose the option with minimum imbalance

        Expected behavior:
        - After adjustment, imbalance is <= initial imbalance
        - Algorithm doesn't make balance worse

        This test will FAIL until calculate_balanced_quantities is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        # Use prices that will trigger adjustment
        target_notional = Decimal("100")
        eth_price = Decimal("2757")  # Creates imbalance with SOL
        sol_price = Decimal("115.86")

        eth_qty, sol_qty, final_imbalance = calculate_balanced_quantities(
            target_notional, eth_price, sol_price,
            Decimal("0.001"), Decimal("0.1")
        )

        # Calculate initial quantities (without adjustment)
        initial_eth_qty = (target_notional / eth_price / Decimal("0.001")).quantize(Decimal('1')) * Decimal("0.001")
        initial_sol_qty = (target_notional / sol_price / Decimal("0.1")).quantize(Decimal('1')) * Decimal("0.1")

        initial_eth_notional = initial_eth_qty * eth_price
        initial_sol_notional = initial_sol_qty * sol_price
        initial_imbalance = abs(initial_sol_notional - initial_eth_notional) / initial_eth_notional

        # Final imbalance should be <= initial imbalance
        assert final_imbalance <= initial_imbalance, \
            f"Final imbalance {final_imbalance:.4f} is worse than initial {initial_imbalance:.4f}"

        print(f"\n[TEST] Iterative Adjustment:")
        print(f"  Initial imbalance: {initial_imbalance:.4f} ({initial_imbalance * 100:.2f}%)")
        print(f"  Final imbalance: {final_imbalance:.4f} ({final_imbalance * 100:.2f}%)")
        print(f"  Improvement: {((initial_imbalance - final_imbalance) / initial_imbalance * 100):.1f}%")


class TestFunctionSignature:
    """Test that the function has the correct signature."""

    def test_function_exists(self):
        """
        TEST: Verify calculate_balanced_quantities function exists.

        This is the FIRST test that will fail in RED phase.

        Expected behavior:
        - Function exists in hedge.DN_pair_eth_sol_nado module
        - Function accepts 5 parameters
        - Function returns tuple of (Decimal, Decimal, Decimal)

        This test will FAIL until the function is implemented.
        """
        assert FUNCTION_EXISTS, "calculate_balanced_quantities function not found - IMPLEMENT FIRST"

        # Check function signature
        import inspect
        sig = inspect.signature(calculate_balanced_quantities)
        params = list(sig.parameters.keys())

        expected_params = ['target_notional', 'eth_price', 'sol_price', 'eth_tick', 'sol_tick']
        assert params == expected_params, \
            f"Function signature incorrect. Expected {expected_params}, got {params}"

    def test_function_returns_tuple(self):
        """
        TEST: Verify function returns correct tuple structure.

        Expected behavior:
        - Returns tuple of (eth_qty, sol_qty, imbalance)
        - All values are Decimal type
        - First two are quantities, third is ratio

        This test will FAIL until the function is implemented.
        """
        if not FUNCTION_EXISTS:
            pytest.skip("calculate_balanced_quantities function not implemented yet - RED phase")

        result = calculate_balanced_quantities(
            Decimal("100"), Decimal("2757"), Decimal("115.86"),
            Decimal("0.001"), Decimal("0.1")
        )

        assert isinstance(result, tuple), "Function must return a tuple"
        assert len(result) == 3, "Function must return exactly 3 values"

        eth_qty, sol_qty, imbalance = result

        assert isinstance(eth_qty, Decimal), "eth_qty must be Decimal"
        assert isinstance(sol_qty, Decimal), "sol_qty must be Decimal"
        assert isinstance(imbalance, Decimal), "imbalance must be Decimal"


# Run tests with verbose output
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
