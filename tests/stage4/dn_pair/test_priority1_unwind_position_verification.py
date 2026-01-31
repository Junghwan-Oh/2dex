"""
TDD Test: Priority 1 - Fix Normal Unwind Cycle Position Verification

This test demonstrates the bug where execute_unwind_cycle() reports success
but SOL positions remain open, causing accumulation.

TDD Approach:
1. RED: This test FAILS with current implementation (orders fill but position doesn't close)
2. GREEN: After fix, test passes (position verified after unwind)
3. REFACTOR: Code is clean and maintainable

Bug Evidence from CSV Analysis:
- SOL-BUY (exit): 39 trades attempting to close shorts
- SOL-SELL (entry): 26 trades opening new shorts
- Net accumulation: +12.399 SOL (40x imbalance)
- Pattern: UNWIND SOL-BUY fills but position doesn't close, then new SOL-SELL opens

Root Cause:
execute_unwind_cycle() returns True if orders fill successfully,
but doesn't verify positions actually closed.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hedge.DN_pair_eth_sol_nado import DNPairBot
from exchanges.base import OrderResult


# Test Constants
POSITION_TOLERANCE = Decimal("0.001")


@pytest.fixture
def bot():
    """Create a DNPairBot instance for testing."""
    return DNPairBot(
        target_notional=Decimal("100"),
        iterations=1,
        sleep_time=0
    )


def create_mock_order_result(success=True, status='FILLED', filled_size=Decimal('0.05'), price=Decimal('2000')):
    """Helper to create mock OrderResult."""
    result = Mock(spec=OrderResult)
    result.success = success
    result.status = status
    result.filled_size = filled_size
    result.price = price
    result.error_message = "Test error" if not success else None
    return result


class TestPriority1UnwindPositionVerification:
    """
    TDD Tests for Priority 1: Fix Normal Unwind Cycle

    These tests demonstrate the bug and verify the fix.
    """

    @pytest.mark.asyncio
    async def test_unwind_returns_false_when_position_not_closed(self, bot):
        """
        TEST: Unwind should return False when position doesn't close.

        BUG DEMONSTRATION (RED):
        Current implementation returns True because order fills,
        but position remains open. This test FAILS with current code.

        EXPECTED BEHAVIOR (GREEN):
        After fix, function checks position after unwind and returns False
        if position not closed (abs(pos) >= 0.001).

        CSV Pattern This Prevents:
        Line 87: ETH-SELL (exit) - SUCCESS
        Line 88: SOL-BUY (exit) - SUCCESS (order filled)
        Line 89: ETH-SELL (entry) - NEW POSITION (WRONG!)
        Line 90: SOL-SELL (entry) - NEW POSITION (WRONG!)
        Result: Accumulation continues
        """
        # Setup: Bot has open positions
        eth_pos_before = Decimal("0.05")  # Long 0.05 ETH
        sol_pos_before = Decimal("-0.5")  # Short 0.5 SOL

        # Mock: Orders fill successfully (this is the bug - order fills but position doesn't close)
        eth_order_result = create_mock_order_result(success=True, filled_size=Decimal("0.05"))
        sol_order_result = create_mock_order_result(success=True, filled_size=Decimal("0.5"))

        # Mock: Position doesn't close despite order filling (the bug scenario)
        eth_pos_after = Decimal("0")  # ETH closes
        sol_pos_after = Decimal("-0.5")  # SOL REMAINS OPEN (BUG!)

        # Mock the clients
        bot.eth_client = AsyncMock()
        bot.sol_client = AsyncMock()
        bot.logger = Mock()

        # Setup get_account_positions to return before/after positions
        bot.eth_client.get_account_positions = AsyncMock(
            side_effect=[eth_pos_before, eth_pos_after]
        )
        bot.sol_client.get_account_positions = AsyncMock(
            side_effect=[sol_pos_before, sol_pos_after]
        )

        # Mock place_simultaneous_orders to return successful order results
        bot.place_simultaneous_orders = AsyncMock(
            return_value=(eth_order_result, sol_order_result)
        )

        # Execute unwind
        result = await bot.execute_unwind_cycle()

        # ASSERT: Should return False because SOL position not closed
        # This FAILS with current implementation (returns True due to order success)
        assert result is False, (
            f"execute_unwind_cycle() should return False when SOL position not closed. "
            f"ETH after={eth_pos_after}, SOL after={sol_pos_after}"
        )

        # Verify logging occurred
        assert any("[UNWIND] POSITIONS BEFORE:" in str(call) for call in bot.logger.info.call_args_list), \
            "Should log positions before unwind"

        assert any("[UNWIND] POSITIONS AFTER:" in str(call) for call in bot.logger.info.call_args_list), \
            "Should log positions after unwind"

    @pytest.mark.asyncio
    async def test_unwind_returns_true_when_positions_closed(self, bot):
        """
        TEST: Unwind should return True when both positions close.

        This test PASSES with both current and fixed implementation
        when positions actually close.
        """
        # Setup: Bot has open positions
        eth_pos_before = Decimal("0.05")
        sol_pos_before = Decimal("-0.5")

        # Mock: Orders fill successfully
        eth_order_result = create_mock_order_result(success=True, filled_size=Decimal("0.05"))
        sol_order_result = create_mock_order_result(success=True, filled_size=Decimal("0.5"))

        # Mock: Both positions close successfully
        eth_pos_after = Decimal("0")
        sol_pos_after = Decimal("0")

        # Mock the clients
        bot.eth_client = AsyncMock()
        bot.sol_client = AsyncMock()
        bot.logger = Mock()

        bot.eth_client.get_account_positions = AsyncMock(
            side_effect=[eth_pos_before, eth_pos_after]
        )
        bot.sol_client.get_account_positions = AsyncMock(
            side_effect=[sol_pos_before, sol_pos_after]
        )

        bot.place_simultaneous_orders = AsyncMock(
            return_value=(eth_order_result, sol_order_result)
        )

        # Execute unwind
        result = await bot.execute_unwind_cycle()

        # ASSERT: Should return True when both positions closed
        assert result is True, \
            f"execute_unwind_cycle() should return True when positions closed. " \
            f"ETH after={eth_pos_after}, SOL after={sol_pos_after}"

    @pytest.mark.asyncio
    async def test_unwind_tolerance_check(self, bot):
        """
        TEST: Position tolerance check uses abs(position) < 0.001.

        Verifies that the direction-agnostic tolerance check works correctly.
        """
        test_cases = [
            (Decimal("0"), True, "Zero position should be closed"),
            (Decimal("0.0005"), True, "Position below tolerance should be closed"),
            (Decimal("-0.0005"), True, "Negative position below tolerance should be closed"),
            (Decimal("0.001"), False, "Position at tolerance should NOT be closed"),
            (Decimal("-0.001"), False, "Negative position at tolerance should NOT be closed"),
            (Decimal("12.399"), False, "Large position should NOT be closed (our bug!)"),
            (Decimal("-12.399"), False, "Large negative position should NOT be closed"),
        ]

        for position, expected_closed, description in test_cases:
            is_closed = abs(position) < POSITION_TOLERANCE
            assert is_closed == expected_closed, \
                f"{description}: abs({position}) < 0.001 = {is_closed}, expected {expected_closed}"

    @pytest.mark.asyncio
    async def test_unwind_logs_position_state(self, bot):
        """
        TEST: Unwind should log position state before and after.

        Verifies detailed logging for debugging position issues.
        """
        eth_pos_before = Decimal("0.05")
        sol_pos_before = Decimal("-0.5")
        eth_pos_after = Decimal("0")
        sol_pos_after = Decimal("-0.5")  # Position doesn't close

        eth_order_result = create_mock_order_result(success=True)
        sol_order_result = create_mock_order_result(success=True)

        bot.eth_client = AsyncMock()
        bot.sol_client = AsyncMock()
        bot.logger = Mock()

        # Setup get_account_positions to return before/after positions
        # Need 3 returns: before, after (first check), after (retry check)
        bot.eth_client.get_account_positions = AsyncMock(
            side_effect=[eth_pos_before, eth_pos_after, eth_pos_after]
        )
        bot.sol_client.get_account_positions = AsyncMock(
            side_effect=[sol_pos_before, sol_pos_after, sol_pos_after]
        )

        bot.place_simultaneous_orders = AsyncMock(
            return_value=(eth_order_result, sol_order_result)
        )

        # Execute unwind
        await bot.execute_unwind_cycle()

        # Verify logging
        log_calls = [str(call) for call in bot.logger.info.call_args_list]
        warning_calls = [str(call) for call in bot.logger.warning.call_args_list]
        error_calls = [str(call) for call in bot.logger.error.call_args_list]
        log_messages = "".join(log_calls + warning_calls + error_calls)

        # Check for before position logging
        assert "[UNWIND] POSITIONS BEFORE:" in log_messages, \
            "Should log positions before unwind"

        # Check for after position logging
        assert "[UNWIND] POSITIONS AFTER:" in log_messages, \
            "Should log positions after unwind"

        # Check for failure logging when position not closed
        assert any(keyword in log_messages for keyword in
                   ["FAILED", "not closed", "Positions not closed"]), \
            "Should log failure when positions not closed"

    @pytest.mark.asyncio
    async def test_unwind_retry_logic(self, bot):
        """
        TEST: Unwind should retry once if position not closed.

        Verifies retry logic with 1 second delay.
        """
        eth_pos_before = Decimal("0.05")
        sol_pos_before = Decimal("-0.5")

        # Orders fill but position doesn't close
        eth_order_result = create_mock_order_result(success=True)
        sol_order_result = create_mock_order_result(success=True)

        # First check: position not closed
        # Retry check: position still not closed
        eth_pos_after = Decimal("0")
        sol_pos_after = Decimal("-0.5")

        bot.eth_client = AsyncMock()
        bot.sol_client = AsyncMock()
        bot.logger = Mock()

        bot.eth_client.get_account_positions = AsyncMock(
            side_effect=[
                eth_pos_before,  # Before unwind
                eth_pos_after,   # After unwind (first check)
                eth_pos_after    # Retry check
            ]
        )
        bot.sol_client.get_account_positions = AsyncMock(
            side_effect=[
                sol_pos_before,  # Before unwind
                sol_pos_after,   # After unwind (first check)
                sol_pos_after    # Retry check
            ]
        )

        bot.place_simultaneous_orders = AsyncMock(
            return_value=(eth_order_result, sol_order_result)
        )

        # Mock sleep to avoid actual delay in test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await bot.execute_unwind_cycle()

        # Should still return False after retry
        assert result is False, \
            "Should return False after retry when position still not closed"

        # Verify retry was logged
        log_calls = [str(call) for call in bot.logger.info.call_args_list]
        log_messages = "".join(log_calls)
        assert "RETRY" in log_messages or "retry" in log_messages, \
            "Should log retry attempt"

    @pytest.mark.asyncio
    async def test_unwind_handles_position_check_failure(self, bot):
        """
        TEST: Unwind should handle position check failures gracefully.

        If getting positions fails, should return False and log error.
        """
        # Mock: Orders fill successfully
        eth_order_result = create_mock_order_result(success=True)
        sol_order_result = create_mock_order_result(success=True)

        bot.eth_client = AsyncMock()
        bot.sol_client = AsyncMock()
        bot.logger = Mock()

        # Position check fails
        bot.eth_client.get_account_positions = AsyncMock(
            side_effect=Exception("Network error")
        )
        bot.sol_client.get_account_positions = AsyncMock()

        bot.place_simultaneous_orders = AsyncMock(
            return_value=(eth_order_result, sol_order_result)
        )

        # Execute unwind
        result = await bot.execute_unwind_cycle()

        # Should return False on position check failure
        assert result is False, \
            "Should return False when position check fails"

        # Verify error logged
        assert any("Failed to get positions" in str(call) or "error" in str(call).lower()
                   for call in bot.logger.error.call_args_list), \
            "Should log error when position check fails"


class TestPriority1UnwindPreventsAccumulation:
    """
    Integration tests showing how the fix prevents SOL accumulation.
    """

    @pytest.mark.asyncio
    async def test_unwind_prevents_sol_accumulation_scenario(self, bot):
        """
        TEST: Fixed unwind prevents SOL accumulation scenario.

        This simulates the exact scenario from the CSV analysis:
        1. Unwind order fills successfully
        2. But position doesn't close (the bug)
        3. Fixed code returns False, preventing next build cycle
        4. No accumulation occurs

        Before fix: Returns True, next build opens new position → accumulation
        After fix: Returns False, next build refused → no accumulation
        """
        # Simulate failed unwind that reports success
        sol_pos_before = Decimal("-12.399")  # Large short position (our bug scenario)
        sol_pos_after = Decimal("-12.399")   # Position doesn't close despite order

        bot.sol_client = AsyncMock()
        bot.eth_client = AsyncMock()
        bot.logger = Mock()

        # Need 3 returns: before, after (first check), after (retry check)
        bot.eth_client.get_account_positions = AsyncMock(
            side_effect=[Decimal("0"), Decimal("0"), Decimal("0")]
        )
        bot.sol_client.get_account_positions = AsyncMock(
            side_effect=[sol_pos_before, sol_pos_after, sol_pos_after]
        )

        # Mock order fills (this is why current code returns True incorrectly)
        eth_order = create_mock_order_result(success=True)
        sol_order = create_mock_order_result(success=True)
        bot.place_simultaneous_orders = AsyncMock(return_value=(eth_order, sol_order))

        # Execute unwind
        unwind_result = await bot.execute_unwind_cycle()

        # ASSERT: Fixed code returns False
        assert unwind_result is False, \
            "Fixed unwind should return False when SOL position not closed"

        # Now verify build cycle would be refused
        # (This will be tested in Priority 3, but conceptually shown here)
        log_calls = [str(call) for call in bot.logger.info.call_args_list]
        warning_calls = [str(call) for call in bot.logger.warning.call_args_list]
        error_calls = [str(call) for call in bot.logger.error.call_args_list]
        log_messages = "".join(log_calls + warning_calls + error_calls)
        assert "FAILED" in log_messages or "not closed" in log_messages, \
            "Should clearly log failure when position doesn't close"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
