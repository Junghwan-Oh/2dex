"""
Test hedging balance calculation with BookDepth.

Tests verify that balanced order sizing ensures equal notionals between
ETH and SOL legs within 0.1% tolerance.

TDD Approach: RED (failing tests) -> GREEN (implementation) -> REFACTOR
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hedge.DN_pair_eth_sol_nado import DNPairBot


@pytest.fixture
def bot():
    """Create a DNPairBot instance for testing."""
    return DNPairBot(
        target_notional=Decimal("100"),
        iterations=1
    )


class TestBalancedOrderSizes:
    """Test calculate_balanced_order_sizes method."""

    @pytest.mark.asyncio
    async def test_balanced_order_sizes_basic(self, bot):
        """
        TEST: Balanced order sizing ensures equal notionals.

        Expected behavior:
        - Returns quantities that achieve < 0.1% notional imbalance
        - Quantities are tick-aligned
        - Actual notional is returned

        This test will FAIL until Task 4 is implemented.
        """
        # Setup mock clients with BookDepth
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        # Mock slippage estimates (NadoClient.estimate_slippage proxies to BookDepthHandler)
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))  # 5 bps
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))  # 5 bps

        eth_price = Decimal('2000')  # ETH $2000
        sol_price = Decimal('100')   # SOL $100

        # Check if method exists
        if not hasattr(bot, 'calculate_balanced_order_sizes'):
            pytest.skip("Task 4 not implemented yet - calculate_balanced_order_sizes method missing")

        eth_qty, sol_qty, actual_notional = await bot.calculate_balanced_order_sizes(
            eth_price, sol_price, "buy", "sell", max_slippage_bps=20
        )

        # Calculate actual notionals
        eth_notional = eth_qty * eth_price
        sol_notional = sol_qty * sol_price

        # Verify balance < 0.1%
        imbalance_pct = abs(eth_notional - sol_notional) / ((eth_notional + sol_notional) / 2) * 100
        assert imbalance_pct < 0.1, f"Hedging imbalance {imbalance_pct:.2f}% exceeds 0.1%"

        # Verify quantities are tick-aligned
        assert eth_qty % bot.eth_client.config.tick_size == 0, "ETH qty should align to tick size"
        assert sol_qty % bot.sol_client.config.tick_size == 0, "SOL qty should align to tick size"

        # Verify non-zero quantities
        assert eth_qty > 0, "ETH quantity should be > 0"
        assert sol_qty > 0, "SOL quantity should be > 0"

    @pytest.mark.asyncio
    async def test_balanced_order_sizes_slippage_limit(self, bot):
        """
        TEST: Returns zero quantities when slippage exceeds limits.

        Expected behavior:
        - If cannot fill within slippage limits, returns (0, 0, 0)
        - Prevents executing orders that violate slippage limits

        This test will FAIL until Task 4 is implemented.
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        # Mock high slippage (exceeds 20 bps limit)
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("50"))  # 50 bps
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("50"))  # 50 bps

        if not hasattr(bot, 'calculate_balanced_order_sizes'):
            pytest.skip("Task 4 not implemented yet")

        eth_price = Decimal('2000')
        sol_price = Decimal('100')

        eth_qty, sol_qty, actual_notional = await bot.calculate_balanced_order_sizes(
            eth_price, sol_price, "buy", "sell", max_slippage_bps=20
        )

        # Should return zero quantities when slippage too high
        assert eth_qty == 0, "Should return 0 ETH qty when slippage exceeds limit"
        assert sol_qty == 0, "Should return 0 SOL qty when slippage exceeds limit"
        assert actual_notional == 0, "Should return 0 notional when slippage exceeds limit"

    @pytest.mark.asyncio
    async def test_balanced_order_sizes_different_slippage(self, bot):
        """
        TEST: Handles asymmetric slippage between legs.

        Expected behavior:
        - Reduces quantity to accommodate leg with higher slippage
        - Maintains balance within 0.1%
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        # ETH has higher slippage than SOL
        async def eth_slippage_mock(side, qty):
            # Slippage increases with quantity
            return Decimal(str(float(qty) * 10))  # 10 bps per 1 ETH

        async def sol_slippage_mock(side, qty):
            # SOL has lower slippage
            return Decimal("5")  # Constant 5 bps

        bot.eth_client.estimate_slippage = AsyncMock(side_effect=eth_slippage_mock)
        bot.sol_client.estimate_slippage = AsyncMock(side_effect=sol_slippage_mock)

        if not hasattr(bot, 'calculate_balanced_order_sizes'):
            pytest.skip("Task 4 not implemented yet")

        eth_price = Decimal('2000')
        sol_price = Decimal('100')

        eth_qty, sol_qty, actual_notional = await bot.calculate_balanced_order_sizes(
            eth_price, sol_price, "buy", "sell", max_slippage_bps=20
        )

        # Verify balance < 0.1%
        eth_notional = eth_qty * eth_price
        sol_notional = sol_qty * sol_price
        imbalance_pct = abs(eth_notional - sol_notional) / ((eth_notional + sol_notional) / 2) * 100
        assert imbalance_pct < 0.1, f"Hedging imbalance {imbalance_pct:.2f}% exceeds 0.1%"

        # Verify final quantities meet slippage limits
        final_eth_slippage = await bot.eth_client.estimate_slippage("buy", eth_qty)
        final_sol_slippage = await bot.sol_client.estimate_slippage("sell", sol_qty)
        assert final_eth_slippage <= 20, f"Final ETH slippage {final_eth_slippage} bps exceeds limit"
        assert final_sol_slippage <= 20, f"Final SOL slippage {final_sol_slippage} bps exceeds limit"

    @pytest.mark.asyncio
    async def test_balanced_order_sizes_tick_alignment(self, bot):
        """
        TEST: Quantities are properly aligned to tick sizes.

        Expected behavior:
        - ETH quantity is multiple of 0.001
        - SOL quantity is multiple of 0.1
        """
        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.sol_client.config.tick_size = Decimal("0.1")

        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))

        if not hasattr(bot, 'calculate_balanced_order_sizes'):
            pytest.skip("Task 4 not implemented yet")

        # Use prices that don't divide evenly by tick sizes
        eth_price = Decimal('1987.65')  # Odd price
        sol_price = Decimal('103.47')   # Odd price

        eth_qty, sol_qty, actual_notional = await bot.calculate_balanced_order_sizes(
            eth_price, sol_price, "buy", "sell", max_slippage_bps=20
        )

        # Verify tick alignment
        eth_qty_aligned = (eth_qty / bot.eth_client.config.tick_size) % 1 == 0
        sol_qty_aligned = (sol_qty / bot.sol_client.config.tick_size) % 1 == 0

        assert eth_qty_aligned, f"ETH qty {eth_qty} not aligned to tick size {bot.eth_client.config.tick_size}"
        assert sol_qty_aligned, f"SOL qty {sol_qty} not aligned to tick size {bot.sol_client.config.tick_size}"


class TestBookDepthVerification:
    """Test BookDepth connection verification."""

    @pytest.mark.asyncio
    async def test_verify_bookdepth_connection(self, bot):
        """
        TEST: Verify BookDepth WebSocket is connected.

        Expected behavior:
        - Returns True when BookDepth handlers exist and have data
        - Returns False when handlers missing or no data

        This test will FAIL until Task 4 is implemented.
        """
        if not hasattr(bot, 'verify_bookdepth_connection'):
            pytest.skip("Task 4 not implemented yet - verify_bookdepth_connection method missing")

        # Setup mock clients
        bot.eth_client = Mock()
        bot.sol_client = Mock()

        # Mock BookDepth handlers
        eth_handler = Mock()
        sol_handler = Mock()

        # Mock get_best_bid and get_best_ask to return tuples (price, quantity)
        eth_handler.get_best_bid = Mock(return_value=(Decimal('1999'), Decimal('10')))
        eth_handler.get_best_ask = Mock(return_value=(Decimal('2001'), Decimal('10')))
        sol_handler.get_best_bid = Mock(return_value=(Decimal('99'), Decimal('1000')))
        sol_handler.get_best_ask = Mock(return_value=(Decimal('101'), Decimal('1000')))

        bot.eth_client.get_bookdepth_handler = Mock(return_value=eth_handler)
        bot.sol_client.get_bookdepth_handler = Mock(return_value=sol_handler)

        # Should return True when connected
        is_connected = await bot.verify_bookdepth_connection()
        assert is_connected is True, "Should return True when BookDepth connected"

        # Test missing handlers
        bot.eth_client.get_bookdepth_handler = Mock(return_value=None)
        is_connected = await bot.verify_bookdepth_connection()
        assert is_connected is False, "Should return False when handlers missing"

        # Test no data
        bot.eth_client.get_bookdepth_handler = Mock(return_value=eth_handler)
        eth_handler.get_best_bid = Mock(return_value=(None, None))
        is_connected = await bot.verify_bookdepth_connection()
        assert is_connected is False, "Should return False when no book data"


class TestIntegration:
    """Integration tests for hedging balance in place_simultaneous_orders."""

    @pytest.mark.asyncio
    async def test_place_simultaneous_orders_uses_balanced_sizing(self, bot):
        """
        TEST: place_simultaneous_orders uses balanced sizing.

        Expected behavior:
        - Calls calculate_balanced_order_sizes if available
        - Logs actual notionals for both legs
        """
        from exchanges.base import OrderResult

        bot.eth_client = Mock()
        bot.sol_client = Mock()
        bot.eth_client.config.tick_size = Decimal("0.001")
        bot.eth_client.config.contract_id = "4"
        bot.sol_client.config.tick_size = Decimal("0.1")
        bot.sol_client.config.contract_id = "8"

        # Mock slippage
        bot.eth_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))
        bot.sol_client.estimate_slippage = AsyncMock(return_value=Decimal("5"))

        # Mock order results
        eth_result = Mock(spec=OrderResult)
        eth_result.success = True
        eth_result.status = 'FILLED'
        eth_result.filled_size = Decimal('0.05')
        eth_result.price = Decimal('2000')

        sol_result = Mock(spec=OrderResult)
        sol_result.success = True
        sol_result.status = 'FILLED'
        sol_result.filled_size = Decimal('100')
        sol_result.price = Decimal('1')

        bot.eth_client.place_ioc_order = AsyncMock(return_value=eth_result)
        bot.sol_client.place_ioc_order = AsyncMock(return_value=sol_result)
        bot.eth_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.sol_client.get_account_positions = AsyncMock(return_value=Decimal('0'))
        bot.eth_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('1999'), Decimal('2001')))
        bot.sol_client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('0.99'), Decimal('1.01')))

        # If balanced sizing exists, it should be called
        if hasattr(bot, 'calculate_balanced_order_sizes'):
            with patch.object(bot, 'calculate_balanced_order_sizes',
                            return_value=(Decimal('0.05'), Decimal('100'), Decimal('100'))) as mock_calc:
                with patch.object(bot, 'log_trade_to_csv'):
                    await bot.place_simultaneous_orders("buy", "sell", "BUILD")
                    # Should have called calculate_balanced_order_sizes
                    assert mock_calc.called, "Should use balanced order sizing"
        else:
            pytest.skip("Task 4 not implemented yet")
