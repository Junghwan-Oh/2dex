"""
Stage 3: DN Hedge Test ($100 notional, 1 cycle)

Tests for simultaneous order placement, partial fill handling, and position delta checking.
"""

import pytest
import asyncio
import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hedge.DN_pair_eth_sol_nado import DNPairBot
from exchanges.base import OrderResult, OrderInfo


@pytest.mark.asyncio
async def test_simultaneous_order_placement(mock_env_vars):
    """Test 1: Simultaneous ETH Long + SOL Short order placement."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock fetch_bbo_prices and place_open_order for both clients
    with patch.object(bot.eth_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_eth_prices, \
         patch.object(bot.sol_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_sol_prices, \
         patch.object(bot.eth_client, 'place_open_order', new_callable=AsyncMock) as mock_eth, \
         patch.object(bot.sol_client, 'place_open_order', new_callable=AsyncMock) as mock_sol:

        mock_eth_prices.return_value = (Decimal("3000"), Decimal("3001"))
        mock_sol_prices.return_value = (Decimal("150"), Decimal("151"))
        mock_eth.return_value = OrderResult(
            success=True, order_id="eth_123", side="buy",
            size=Decimal("0.1"), price=Decimal("3000"), status="OPEN"
        )
        mock_sol.return_value = OrderResult(
            success=True, order_id="sol_456", side="sell",
            size=Decimal("0.667"), price=Decimal("150"), status="OPEN"
        )

        start_time = time.time()
        eth_result, sol_result = await bot.place_simultaneous_orders(
            eth_direction="buy",
            sol_direction="sell",
        )
        elapsed = time.time() - start_time

        # Quantified: Both orders must succeed
        assert eth_result.success is True
        assert sol_result.success is True

        # Quantified: Orders placed within 1 second
        assert elapsed < 1.0, f"Orders took {elapsed:.2f}s, expected <1s"

    await bot.cleanup()


@pytest.mark.asyncio
async def test_partial_fill_handling(mock_env_vars):
    """Test 2: Partial fill on one leg triggers emergency unwind."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock ETH fills, SOL fails
    with patch.object(bot.eth_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_eth_prices, \
         patch.object(bot.sol_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_sol_prices, \
         patch.object(bot.eth_client, 'place_open_order', new_callable=AsyncMock) as mock_eth, \
         patch.object(bot.sol_client, 'place_open_order', new_callable=AsyncMock) as mock_sol, \
         patch.object(bot, 'emergency_unwind_eth', new_callable=AsyncMock) as mock_unwind:

        mock_eth_prices.return_value = (Decimal("3000"), Decimal("3001"))
        mock_sol_prices.return_value = (Decimal("150"), Decimal("151"))
        mock_eth.return_value = OrderResult(
            success=True, order_id="eth_123", side="buy",
            size=Decimal("0.1"), price=Decimal("3000"), status="OPEN"
        )
        mock_sol.return_value = OrderResult(
            success=False, error_message="Liquidity insufficient"
        )

        await bot.place_simultaneous_orders(eth_direction="buy", sol_direction="sell")

        # Verify emergency unwind was called
        mock_unwind.assert_called_once()

    await bot.cleanup()


@pytest.mark.asyncio
async def test_position_delta_check(mock_env_vars):
    """Test 3: Net delta is approximately neutral after BUILD+UNWIND."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock full cycle: BUILD (Long ETH / Short SOL) -> UNWIND
    with patch.object(bot, 'execute_build_cycle', new_callable=AsyncMock) as mock_build, \
         patch.object(bot, 'execute_unwind_cycle', new_callable=AsyncMock) as mock_unwind, \
         patch.object(bot.eth_client, 'get_account_positions', new_callable=AsyncMock) as mock_eth_pos, \
         patch.object(bot.sol_client, 'get_account_positions', new_callable=AsyncMock) as mock_sol_pos:

        mock_build.return_value = True
        mock_unwind.return_value = True
        mock_eth_pos.return_value = Decimal("0")
        mock_sol_pos.return_value = Decimal("0")

        # Execute cycle
        success = await bot.execute_dn_pair_cycle()

        assert success is True

        # Verify positions are flat
        eth_pos = await bot.eth_client.get_account_positions()
        sol_pos = await bot.sol_client.get_account_positions()

        # Quantified: Net delta within 1% tolerance
        assert abs(eth_pos) < Decimal("0.01"), f"ETH position not flat: {eth_pos}"
        assert abs(sol_pos) < Decimal("0.1"), f"SOL position not flat: {sol_pos}"

    await bot.cleanup()
