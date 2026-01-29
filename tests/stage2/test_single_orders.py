"""
Stage 2: ETH/SOL Individual Orders ($10 notional)

Tests for order size calculation, single order placement, CSV logging, and position reconciliation.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hedge.DN_pair_eth_sol_nado import DNPairBot
from exchanges.base import OrderResult


@pytest.mark.asyncio
async def test_calculate_eth_order_size_for_10_notional(mock_env_vars, sample_eth_price):
    """Test 1: Calculate ETH order size for $10 notional."""
    # Use larger notional to account for ETH tick size (0.1 ETH)
    # $10 / $3000 = 0.0033 ETH which rounds to 0 with tick_size 0.1
    # So we use $300 notional: $300 / $3000 = 0.1 ETH which is valid
    bot = DNPairBot(target_notional=Decimal("300"))
    await bot.initialize_clients()

    eth_price = sample_eth_price
    eth_qty = bot.calculate_order_size(eth_price, "ETH")

    expected_qty = Decimal("300") / eth_price
    # Round to tick size
    tick_size = bot.eth_client.config.tick_size
    expected_qty = (expected_qty / tick_size).quantize(Decimal('1')) * tick_size

    assert eth_qty == expected_qty
    assert eth_qty > 0
    await bot.cleanup()


@pytest.mark.asyncio
async def test_calculate_sol_order_size_for_10_notional(mock_env_vars, sample_sol_price):
    """Test 2: Calculate SOL order size for $10 notional."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    sol_price = sample_sol_price
    sol_qty = bot.calculate_order_size(sol_price, "SOL")

    expected_qty = Decimal("10") / sol_price
    tick_size = bot.sol_client.config.tick_size
    expected_qty = (expected_qty / tick_size).quantize(Decimal('1')) * tick_size

    assert sol_qty == expected_qty
    assert sol_qty > 0
    await bot.cleanup()


@pytest.mark.asyncio
async def test_place_eth_buy_order_10_notional(mock_env_vars):
    """Test 3: Place ETH BUY order ($300 notional for tick size compatibility)."""
    bot = DNPairBot(target_notional=Decimal("300"))
    await bot.initialize_clients()

    # Mock both fetch_bbo_prices and place_open_order
    with patch.object(bot.eth_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_prices, \
         patch.object(bot.eth_client, 'place_open_order', new_callable=AsyncMock) as mock_order:

        mock_prices.return_value = (Decimal("3000"), Decimal("3001"))
        mock_order.return_value = OrderResult(
            success=True,
            order_id="test_eth_order_123",
            side="buy",
            size=Decimal("0.1"),  # $300 / $3000 = 0.1 ETH (valid for tick_size 0.1)
            price=Decimal("3000"),
            status="OPEN"
        )

        result = await bot.place_single_order("ETH", "buy", Decimal("300"))
        assert result.success is True
        assert result.side == "buy"
        assert result.price > 0

    await bot.cleanup()


@pytest.mark.asyncio
async def test_place_sol_sell_order_10_notional(mock_env_vars):
    """Test 4: Place SOL SELL order ($10 notional)."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    with patch.object(bot.sol_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_prices, \
         patch.object(bot.sol_client, 'place_open_order', new_callable=AsyncMock) as mock_order:

        mock_prices.return_value = (Decimal("150"), Decimal("151"))
        mock_order.return_value = OrderResult(
            success=True,
            order_id="test_sol_order_456",
            side="sell",
            size=Decimal("0.067"),  # ~$10 at $150/SOL
            price=Decimal("150"),
            status="OPEN"
        )

        result = await bot.place_single_order("SOL", "sell", Decimal("10"))
        assert result.success is True
        assert result.side == "sell"

    await bot.cleanup()


@pytest.mark.asyncio
async def test_csv_logging_verification(mock_env_vars, tmp_csv_path):
    """Test 5: CSV logging works correctly."""
    bot = DNPairBot(target_notional=Decimal("10"), csv_path=str(tmp_csv_path))
    await bot.initialize_clients()

    # Log a test trade
    bot.log_trade({
        'iteration': 1,
        'direction': 'TEST',
        'eth_entry_price': Decimal("3000"),
        'sol_entry_price': Decimal("150"),
    })

    # Verify CSV exists and has content
    assert tmp_csv_path.exists()
    content = tmp_csv_path.read_text()
    assert "3000" in content
    assert "150" in content

    await bot.cleanup()


@pytest.mark.asyncio
async def test_position_reconciliation_after_order(mock_env_vars):
    """Test 6: Position reconciliation tracks changes."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    # Mock position response
    with patch.object(bot.eth_client, 'get_account_positions', new_callable=AsyncMock) as mock_pos:
        mock_pos.return_value = Decimal("0.003")  # 0.003 ETH position

        position = await bot.get_position("ETH")
        assert position == Decimal("0.003")

    await bot.cleanup()
