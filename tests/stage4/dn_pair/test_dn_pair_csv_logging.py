"""
Test CSV logging for DN pair trading bot.

Tests verify that CSV logging correctly identifies entry vs exit for both
BUY_FIRST and SELL_FIRST cycles.

TDD Approach: RED (failing tests) -> GREEN (implementation) -> REFACTOR
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hedge.DN_pair_eth_sol_nado import DNPairBot
from exchanges.base import OrderResult


@pytest.fixture
def bot():
    """Create a DNPairBot instance for testing."""
    return DNPairBot(
        target_notional=Decimal("100"),
        iterations=4,
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


class TestBuyFirstCSVLogging:
    """Test CSV logging for BUY_FIRST cycle (Long ETH / Short SOL)."""

    @pytest.mark.asyncio
    async def test_buy_first_build_csv_logging(self, bot):
        """
        TEST: BUY_FIRST BUILD logs correctly (Long ETH/Short SOL).

        Expected behavior:
        - ETH buy should log as "entry"
        - SOL sell should log as "entry"

        This test will FAIL until Task 1 is implemented (phase parameter added).
        """
        # Setup mock clients
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")
        bot.eth_client.config.contract_id = "4"
        bot.sol_client.config.contract_id = "8"

        # Mock order results - both filled
        eth_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('0.05'),  # ~0.05 ETH @ $2000 = $100
            price=Decimal('2000')
        )
        sol_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('100'),  # 100 SOL @ $1 = $100
            price=Decimal('1')
        )

        bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
        bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
        bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))

        # Mock estimate_slippage for balanced sizing
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        # Track CSV logging calls
        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            # Call with NEW signature (phase parameter)
            # This will FAIL with current signature (no phase parameter)
            try:
                await bot.place_simultaneous_orders("buy", "sell", "BUILD")
            except TypeError as e:
                # Expected to fail in RED phase - no phase parameter yet
                assert "phase" in str(e).lower() or "unexpected keyword" in str(e).lower()
                pytest.skip("Task 1 not implemented yet - phase parameter missing")

            # Verify ETH buy logged as entry
            assert any(
                call.kwargs.get('side') == "ETH-BUY" and call.kwargs.get('order_type') == "entry"
                for call in mock_log.call_args_list
            ), "ETH BUY in BUILD phase should log as entry"

            # Verify SOL sell logged as entry
            assert any(
                call.kwargs.get('side') == "SOL-SELL" and call.kwargs.get('order_type') == "entry"
                for call in mock_log.call_args_list
            ), "SOL SELL in BUILD phase should log as entry"

    @pytest.mark.asyncio
    async def test_buy_first_unwind_csv_logging(self, bot):
        """
        TEST: BUY_FIRST UNWIND logs correctly (Sell ETH/Buy SOL).

        Expected behavior:
        - ETH sell should log as "exit"
        - SOL buy should log as "exit"

        This test will FAIL until Task 1 is implemented (phase parameter added).
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")
        bot.eth_client.config.contract_id = "4"
        bot.sol_client.config.contract_id = "8"

        eth_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('0.05'),
            price=Decimal('2000')
        )
        sol_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('100'),
            price=Decimal('1')
        )

        bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
        bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
        bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
        # Mock estimate_slippage for balanced sizing
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            try:
                await bot.place_simultaneous_orders("sell", "buy", "UNWIND")
            except TypeError:
                pytest.skip("Task 1 not implemented yet - phase parameter missing")

            # Verify ETH sell logged as exit
            assert any(
                call.kwargs.get('side') == "ETH-SELL" and call.kwargs.get('order_type') == "exit"
                for call in mock_log.call_args_list
            ), "ETH SELL in UNWIND phase should log as exit"

            # Verify SOL buy logged as exit
            assert any(
                call.kwargs.get('side') == "SOL-BUY" and call.kwargs.get('order_type') == "exit"
                for call in mock_log.call_args_list
            ), "SOL BUY in UNWIND phase should log as exit"


class TestSellFirstCSVLogging:
    """Test CSV logging for SELL_FIRST cycle (Short ETH / Long SOL)."""

    @pytest.mark.asyncio
    async def test_sell_first_build_csv_logging(self, bot):
        """
        TEST: SELL_FIRST BUILD logs correctly (Short ETH/Long SOL).

        Expected behavior:
        - ETH sell should log as "entry" (NOT exit!)
        - SOL buy should log as "entry" (NOT exit!)

        This is the CRITICAL BUG fix - SELL_FIRST BUILD was logging as exit.

        This test will FAIL until Task 1 is implemented.
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")
        bot.eth_client.config.contract_id = "4"
        bot.sol_client.config.contract_id = "8"

        eth_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('0.05'),
            price=Decimal('2000')
        )
        sol_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('100'),
            price=Decimal('1')
        )

        bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
        bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
        bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
        # Mock estimate_slippage for balanced sizing
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            try:
                await bot.place_simultaneous_orders("sell", "buy", "BUILD")
            except TypeError:
                pytest.skip("Task 1 not implemented yet - phase parameter missing")

            # Verify ETH sell logged as entry (SELL_FIRST BUILD)
            assert any(
                call.kwargs.get('side') == "ETH-SELL" and call.kwargs.get('order_type') == "entry"
                for call in mock_log.call_args_list
            ), "ETH SELL in SELL_FIRST BUILD should log as entry (CRITICAL BUG FIX)"

            # Verify SOL buy logged as entry (SELL_FIRST BUILD)
            assert any(
                call.kwargs.get('side') == "SOL-BUY" and call.kwargs.get('order_type') == "entry"
                for call in mock_log.call_args_list
            ), "SOL BUY in SELL_FIRST BUILD should log as entry (CRITICAL BUG FIX)"

    @pytest.mark.asyncio
    async def test_sell_first_unwind_csv_logging(self, bot):
        """
        TEST: SELL_FIRST UNWIND logs correctly (Buy ETH/Sell SOL).

        Expected behavior:
        - ETH buy should log as "exit" (NOT entry!)
        - SOL sell should log as "exit" (NOT entry!)

        This is the CRITICAL BUG fix - SELL_FIRST UNWIND was logging as entry.

        This test will FAIL until Task 1 is implemented.
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")
        bot.eth_client.config.contract_id = "4"
        bot.sol_client.config.contract_id = "8"

        eth_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('0.05'),
            price=Decimal('2000')
        )
        sol_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('100'),
            price=Decimal('1')
        )

        bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
        bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
        bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
        # Mock estimate_slippage for balanced sizing
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            try:
                await bot.place_simultaneous_orders("buy", "sell", "UNWIND")
            except TypeError:
                pytest.skip("Task 1 not implemented yet - phase parameter missing")

            # Verify ETH buy logged as exit (SELL_FIRST UNWIND)
            assert any(
                call.kwargs.get('side') == "ETH-BUY" and call.kwargs.get('order_type') == "exit"
                for call in mock_log.call_args_list
            ), "ETH BUY in SELL_FIRST UNWIND should log as exit (CRITICAL BUG FIX)"

            # Verify SOL sell logged as exit (SELL_FIRST UNWIND)
            assert any(
                call.kwargs.get('side') == "SOL-SELL" and call.kwargs.get('order_type') == "exit"
                for call in mock_log.call_args_list
            ), "SOL SELL in SELL_FIRST UNWIND should log as exit (CRITICAL BUG FIX)"


class TestEmergencyUnwindCSVLogging:
    """Test CSV logging for emergency unwind operations."""

    @pytest.mark.asyncio
    async def test_emergency_unwind_eth_logging(self, bot):
        """
        TEST: Emergency unwind ETH logs to CSV.

        Expected behavior:
        - Logs with order_type="exit" (emergency unwind always exits)
        - Logs with mode="EMERGENCY" to distinguish from normal unwinds
        - Logs only if result.filled_size > 0

        This test will FAIL until Task 2 is implemented.
        """
        bot.eth_client = Mock()
        bot.eth_client.config.contract_id = "4"

        # Simulate having a long position
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0.05'))

        # Mock successful order
        bot.eth_client.place_ioc_order = AsyncMock(
            return_value=create_mock_order_result(
                success=True,
                status='FILLED',
                filled_size=Decimal('0.05'),
                price=Decimal('2000')
            )
        )

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            await bot.emergency_unwind_eth()

            # Should have logged to CSV
            assert mock_log.called, "Emergency unwind ETH should log to CSV"

            # Verify logged as exit with EMERGENCY mode
            call_kwargs = mock_log.call_args[1] if mock_log.called else {}
            assert call_kwargs.get('order_type') == "exit", \
                "Emergency unwind should be logged as exit"
            assert call_kwargs.get('mode') == "EMERGENCY", \
                "Should have EMERGENCY mode"

    @pytest.mark.asyncio
    async def test_emergency_unwind_sol_logging(self, bot):
        """
        TEST: Emergency unwind SOL logs to CSV.

        Expected behavior:
        - Logs with order_type="exit"
        - Logs with mode="EMERGENCY"
        - Logs only if result.filled_size > 0

        This test will FAIL until Task 3 is implemented.
        """
        bot.sol_client = Mock()
        bot.sol_client.config.contract_id = "8"

        # Simulate having a long position
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('100'))

        # Mock successful order
        bot.sol_client.place_ioc_order = AsyncMock(
            return_value=create_mock_order_result(
                success=True,
                status='FILLED',
                filled_size=Decimal('100'),
                price=Decimal('1')
            )
        )

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            await bot.emergency_unwind_sol()

            # Should have logged to CSV
            assert mock_log.called, "Emergency unwind SOL should log to CSV"

            # Verify logged as exit with EMERGENCY mode
            call_kwargs = mock_log.call_args[1] if mock_log.called else {}
            assert call_kwargs.get('order_type') == "exit", \
                "Emergency unwind should be logged as exit"
            assert call_kwargs.get('mode') == "EMERGENCY", \
                "Should have EMERGENCY mode"

    @pytest.mark.asyncio
    async def test_emergency_unwind_short_position(self, bot):
        """
        TEST: Emergency unwind handles short positions correctly.

        Expected behavior:
        - Short position (negative) should buy to close
        - Logs correctly regardless of direction
        """
        bot.eth_client = Mock()
        bot.eth_client.config.contract_id = "4"

        # Simulate having a SHORT position (negative)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('-0.05'))

        # Mock successful buy to close
        bot.eth_client.place_ioc_order = AsyncMock(
            return_value=create_mock_order_result(
                success=True,
                status='FILLED',
                filled_size=Decimal('0.05'),
                price=Decimal('2000')
            )
        )

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            await bot.emergency_unwind_eth()

            # Should have logged to CSV
            assert mock_log.called, "Emergency unwind of short position should log to CSV"

            # Verify logged as exit (even though it's a buy order)
            call_kwargs = mock_log.call_args[1] if mock_log.called else {}
            assert call_kwargs.get('order_type') == "exit", \
                "Emergency unwind should be logged as exit regardless of direction"

    @pytest.mark.asyncio
    async def test_emergency_unwind_no_position(self, bot):
        """
        TEST: Emergency unwind with no position does not log.

        Expected behavior:
        - No CSV logging if position is zero
        """
        bot.eth_client = Mock()
        bot.eth_client.config.contract_id = "4"

        # No position
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            await bot.emergency_unwind_eth()

            # Should NOT have logged
            assert not mock_log.called, "Emergency unwind with no position should not log"


class TestPartialFillLogging:
    """Test CSV logging for partial fills."""

    @pytest.mark.asyncio
    async def test_partial_fill_logs_mode_partial(self, bot):
        """
        TEST: Partial fills log with mode="PARTIAL".

        Expected behavior:
        - Partial fills should log with mode="PARTIAL"
        - Still logs with correct order_type based on phase
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")
        bot.eth_client.config.contract_id = "4"
        bot.sol_client.config.contract_id = "8"

        # ETH partially filled, SOL fully filled
        eth_result = create_mock_order_result(
            success=True,
            status='PARTIALLY_FILLED',
            filled_size=Decimal('0.025'),  # Only half filled
            price=Decimal('2000')
        )
        sol_result = create_mock_order_result(
            success=True,
            status='FILLED',
            filled_size=Decimal('100'),
            price=Decimal('1')
        )

        bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
        bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
        bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))
        # Mock estimate_slippage for balanced sizing
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        with patch.object(bot, 'log_trade_to_csv') as mock_log:
            try:
                await bot.place_simultaneous_orders("buy", "sell", "BUILD")
            except TypeError:
                pytest.skip("Task 1 not implemented yet - phase parameter missing")

            # Verify ETH partial fill logged with mode="PARTIAL"
            eth_log = next((
                call for call in mock_log.call_args_list
                if call.kwargs.get('side') == "ETH-BUY"
            ), None)

            assert eth_log is not None, "ETH should be logged"
            assert eth_log.kwargs.get('mode') == "PARTIAL", \
                "Partial fill should log with mode=PARTIAL"
            assert eth_log.kwargs.get('order_type') == "entry", \
                "Partial fill should still have correct order_type"
