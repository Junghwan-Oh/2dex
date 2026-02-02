"""
TP Order Placement Testing (TDD - RED PHASE)

Tests for _place_tp_orders() method in DN_pair_eth_sol_nado.py

This file contains FAILING tests that should initially fail.
They will pass after proper implementation of the TP order functionality.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from decimal import Decimal
import sys
import os

# Add project to path
sys.path.insert(0, '/Users/botfarmer/2dex')

from hedge.DN_pair_eth_sol_nado import DNPairBot
from nado_protocol.engine_client.types.execute import ResponseStatus


class TestTPOrders:
    """Test TP order placement functionality."""

    @pytest.fixture
    async def bot(self):
        """Create a bot instance for testing."""
        # Mock environment variables
        with patch.dict('os.environ', {
            'NADO_PRIVATE_KEY': '0x' + '1' * 64,
            'NADO_MODE': 'MAINNET',
            'NADO_SUBACCOUNT_NAME': 'test'
        }):
            # Create bot with minimal config
            bot = DNPairBot(
                target_notional=Decimal('100'),
                csv_path='/tmp/test_trades.csv'
            )

            # Initialize state
            bot._tp_order_ids = {}
            bot.entry_prices = {}
            bot.entry_quantities = {}
            bot.entry_directions = {}

            return bot

    @pytest.mark.asyncio
    async def test_place_tp_orders_places_both_orders(self, bot):
        """
        RED PHASE: Test that _place_tp_orders() places both ETH and SOL TP orders.

        This test will FAIL initially because:
        1. The bot may not have clients initialized
        2. The mock setup may not match actual implementation
        3. The _place_tp_orders method may have dependencies not yet mocked
        """
        # Setup entry data
        bot.entry_prices = {"ETH": Decimal("2000"), "SOL": Decimal("100")}
        bot.entry_quantities = {"ETH": Decimal("0.05"), "SOL": Decimal("1.0")}
        bot.entry_directions = {"ETH": "buy", "SOL": "sell"}

        # Create mock clients
        mock_eth_client = Mock()
        mock_sol_client = Mock()

        # Configure mock eth_client
        mock_eth_client.config = Mock()
        mock_eth_client.config.contract_id = 4
        mock_eth_client.owner = "test_owner"
        mock_eth_client.subaccount_name = "test_subaccount"
        mock_eth_client._round_price_to_increment = Mock(return_value=Decimal("2000.02"))

        # Configure mock sol_client
        mock_sol_client.config = Mock()
        mock_sol_client.config.contract_id = 5
        mock_sol_client.owner = "test_owner"
        mock_sol_client.subaccount_name = "test_subaccount"
        mock_sol_client._round_price_to_increment = Mock(return_value=Decimal("99.98"))

        # Mock the context and trigger_client for both
        mock_eth_context = Mock()
        mock_eth_trigger = AsyncMock()
        mock_eth_context.trigger_client = mock_eth_trigger
        mock_eth_client.client.context = mock_eth_context

        mock_sol_context = Mock()
        mock_sol_trigger = AsyncMock()
        mock_sol_context.trigger_client = mock_sol_trigger
        mock_sol_client.client.context = mock_sol_context

        # Configure mock to return success
        mock_result = MagicMock()
        mock_result.status = ResponseStatus.SUCCESS
        mock_result.data = MagicMock()
        mock_result.data.digest = "test_order_id"

        mock_eth_trigger.place_price_trigger_order = AsyncMock(return_value=mock_result)
        mock_sol_trigger.place_price_trigger_order = AsyncMock(return_value=mock_result)

        # Assign clients to bot
        bot.eth_client = mock_eth_client
        bot.sol_client = mock_sol_client

        # Call the method
        result = await bot._place_tp_orders()

        # Assertions
        assert result is True, "Should return True on success"
        assert "ETH" in bot._tp_order_ids, "Should store ETH TP order ID"
        assert "SOL" in bot._tp_order_ids, "Should store SOL TP order ID"

        # Verify place_price_trigger_order was called twice
        assert mock_eth_trigger.place_price_trigger_order.call_count == 1, \
            f"ETH trigger_client.place_price_trigger_order should be called once, got {mock_eth_trigger.place_price_trigger_order.call_count}"
        assert mock_sol_trigger.place_price_trigger_order.call_count == 1, \
            f"SOL trigger_client.place_price_trigger_order should be called once, got {mock_sol_trigger.place_price_trigger_order.call_count}"

    @pytest.mark.asyncio
    async def test_tp_order_parameters_for_long_position(self, bot):
        """
        RED PHASE: Test TP orders use correct parameters for long positions.

        For a long position (buy):
        - trigger_type should be "last_price_above" (trigger when price rises)
        - reduce_only should be True
        - amount should be negative (selling to close)
        """
        # Setup entry data for long position
        bot.entry_prices = {"ETH": Decimal("2000")}
        bot.entry_quantities = {"ETH": Decimal("0.05")}
        bot.entry_directions = {"ETH": "buy"}

        # Create mock client
        mock_client = Mock()
        mock_client.config = Mock()
        mock_client.config.contract_id = 4
        mock_client.owner = "test_owner"
        mock_client.subaccount_name = "test_subaccount"
        mock_client._round_price_to_increment = Mock(return_value=Decimal("2000.02"))

        # Mock the context and trigger_client
        mock_context = Mock()
        mock_trigger = AsyncMock()
        mock_context.trigger_client = mock_trigger
        mock_client.client.context = mock_context

        # Configure mock to capture calls
        mock_result = MagicMock()
        mock_result.status = ResponseStatus.SUCCESS
        mock_result.data = MagicMock()
        mock_result.data.digest = "test_order_id"
        mock_trigger.place_price_trigger_order = AsyncMock(return_value=mock_result)

        # Assign client to bot
        bot.eth_client = mock_client
        bot.sol_client = None  # Only test ETH

        # Call the method
        await bot._place_tp_orders()

        # Get ETH call
        assert mock_trigger.place_price_trigger_order.call_count == 1, \
            "place_price_trigger_order should be called once"

        call_kwargs = mock_trigger.place_price_trigger_order.call_args.kwargs

        # Verify parameters for long position
        assert call_kwargs.get('product_id') == 4, \
            f"ETH product_id should be 4, got {call_kwargs.get('product_id')}"
        assert call_kwargs.get('reduce_only') is True, \
            f"Should be reduce_only=True, got {call_kwargs.get('reduce_only')}"
        assert call_kwargs.get('trigger_type') == "last_price_above", \
            f"ETH long should use last_price_above, got {call_kwargs.get('trigger_type')}"

        # Verify amount is negative (selling to close long)
        amount = call_kwargs.get('amount_x18')
        assert amount is not None, "amount_x18 should be provided"
        assert str(amount).startswith('-'), \
            f"Long position TP amount should be negative (selling to close), got {amount}"

    @pytest.mark.asyncio
    async def test_tp_order_parameters_for_short_position(self, bot):
        """
        RED PHASE: Test TP orders use correct parameters for short positions.

        For a short position (sell):
        - trigger_type should be "last_price_below" (trigger when price falls)
        - reduce_only should be True
        - amount should be positive (buying to close)
        """
        # Setup entry data for short position
        bot.entry_prices = {"SOL": Decimal("100")}
        bot.entry_quantities = {"SOL": Decimal("1.0")}
        bot.entry_directions = {"SOL": "sell"}

        # Create mock client
        mock_client = Mock()
        mock_client.config = Mock()
        mock_client.config.contract_id = 5
        mock_client.owner = "test_owner"
        mock_client.subaccount_name = "test_subaccount"
        mock_client._round_price_to_increment = Mock(return_value=Decimal("99.98"))

        # Mock the context and trigger_client
        mock_context = Mock()
        mock_trigger = AsyncMock()
        mock_context.trigger_client = mock_trigger
        mock_client.client.context = mock_context

        # Configure mock to capture calls
        mock_result = MagicMock()
        mock_result.status = ResponseStatus.SUCCESS
        mock_result.data = MagicMock()
        mock_result.data.digest = "test_order_id"
        mock_trigger.place_price_trigger_order = AsyncMock(return_value=mock_result)

        # Assign client to bot
        bot.eth_client = None  # Only test SOL
        bot.sol_client = mock_client

        # Call the method
        await bot._place_tp_orders()

        # Get SOL call
        assert mock_trigger.place_price_trigger_order.call_count == 1, \
            "place_price_trigger_order should be called once"

        call_kwargs = mock_trigger.place_price_trigger_order.call_args.kwargs

        # Verify parameters for short position
        assert call_kwargs.get('product_id') == 5, \
            f"SOL product_id should be 5, got {call_kwargs.get('product_id')}"
        assert call_kwargs.get('reduce_only') is True, \
            f"Should be reduce_only=True, got {call_kwargs.get('reduce_only')}"
        assert call_kwargs.get('trigger_type') == "last_price_below", \
            f"SOL short should use last_price_below, got {call_kwargs.get('trigger_type')}"

        # Verify amount is positive (buying to close short)
        amount = call_kwargs.get('amount_x18')
        assert amount is not None, "amount_x18 should be provided"
        # Note: to_x18 wraps in str(), so we need to check if the numeric value is positive
        # The amount should NOT start with '-' for short position closing
        assert not str(amount).startswith('-'), \
            f"Short position TP amount should be positive (buying to close), got {amount}"

    @pytest.mark.asyncio
    async def test_tp_order_returns_false_on_failure(self, bot):
        """
        RED PHASE: Test that _place_tp_orders returns False when order placement fails.

        This verifies error handling when the trigger_client returns a failure status.
        """
        # Setup entry data
        bot.entry_prices = {"ETH": Decimal("2000")}
        bot.entry_quantities = {"ETH": Decimal("0.05")}
        bot.entry_directions = {"ETH": "buy"}

        # Create mock client
        mock_client = Mock()
        mock_client.config = Mock()
        mock_client.config.contract_id = 4
        mock_client.owner = "test_owner"
        mock_client.subaccount_name = "test_subaccount"
        mock_client._round_price_to_increment = Mock(return_value=Decimal("2000.02"))

        # Mock the context and trigger_client
        mock_context = Mock()
        mock_trigger = AsyncMock()
        mock_context.trigger_client = mock_trigger
        mock_client.client.context = mock_context

        # Configure mock to return FAILURE
        mock_result = MagicMock()
        mock_result.status = ResponseStatus.FAILURE
        mock_result.error = "Insufficient margin"
        mock_trigger.place_price_trigger_order = AsyncMock(return_value=mock_result)

        # Assign client to bot
        bot.eth_client = mock_client
        bot.sol_client = None

        # Call the method
        result = await bot._place_tp_orders()

        # Assertions
        assert result is False, \
            f"Should return False on order placement failure, got {result}"

    @pytest.mark.asyncio
    async def test_tp_order_skips_missing_entry_data(self, bot):
        """
        RED PHASE: Test that _place_tp_orders skips tickers with missing entry data.

        This verifies graceful handling when entry_prices, entry_quantities,
        or entry_directions are missing for a ticker.
        """
        # Setup partial entry data (only ETH, no SOL)
        bot.entry_prices = {"ETH": Decimal("2000")}
        bot.entry_quantities = {"ETH": Decimal("0.05")}
        bot.entry_directions = {"ETH": "buy"}
        # SOL data is missing

        # Create mock clients
        mock_eth_client = Mock()
        mock_eth_client.config = Mock()
        mock_eth_client.config.contract_id = 4
        mock_eth_client.owner = "test_owner"
        mock_eth_client.subaccount_name = "test_subaccount"
        mock_eth_client._round_price_to_increment = Mock(return_value=Decimal("2000.02"))

        mock_context = Mock()
        mock_trigger = AsyncMock()
        mock_context.trigger_client = mock_trigger
        mock_eth_client.client.context = mock_context

        mock_result = MagicMock()
        mock_result.status = ResponseStatus.SUCCESS
        mock_result.data = MagicMock()
        mock_result.data.digest = "test_order_id"
        mock_trigger.place_price_trigger_order = AsyncMock(return_value=mock_result)

        bot.eth_client = mock_eth_client
        bot.sol_client = None  # No SOL client

        # Call the method
        result = await bot._place_tp_orders()

        # Assertions
        assert result is True, "Should succeed with partial data"
        assert "ETH" in bot._tp_order_ids, "Should store ETH TP order ID"
        assert "SOL" not in bot._tp_order_ids, "Should NOT store SOL TP order ID (no data)"

        # Verify only ETH was called
        assert mock_trigger.place_price_trigger_order.call_count == 1, \
            f"Should only call once for ETH, got {mock_trigger.place_price_trigger_order.call_count}"
