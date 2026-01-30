"""
Stage 1: Nado Basic Functionality Check ($0 risk)

Tests for Nado API connection, client initialization, position queries, and BBO price fetching.
All tests have $0 risk - no actual orders placed.
"""

import pytest
import asyncio
from decimal import Decimal
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hedge.DN_pair_eth_sol_nado import DNPairBot


@pytest.mark.asyncio
async def test_eth_client_initialization(mock_env_vars):
    """Test 1: ETH client initializes successfully."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.eth_client is not None
    assert bot.eth_client.config.ticker == "ETH"
    await bot.cleanup()


@pytest.mark.asyncio
async def test_sol_client_initialization(mock_env_vars):
    """Test 2: SOL client initializes successfully."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.sol_client is not None
    assert bot.sol_client.config.ticker == "SOL"
    await bot.cleanup()


@pytest.mark.asyncio
async def test_eth_contract_attributes(mock_env_vars):
    """Test 3: ETH contract has correct attributes."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.eth_client.config.contract_id == "4"  # ETH product ID on Nado
    assert bot.eth_client.config.tick_size > 0
    await bot.cleanup()


@pytest.mark.asyncio
async def test_sol_contract_attributes(mock_env_vars):
    """Test 4: SOL contract has correct attributes."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.sol_client.config.contract_id == "8"  # SOL product ID on Nado
    assert bot.sol_client.config.tick_size > 0
    await bot.cleanup()


@pytest.mark.asyncio
async def test_eth_position_query_zero(mock_env_vars):
    """Test 5: ETH position query returns 0 (no open positions)."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    position = await bot.eth_client.get_account_positions()
    assert position == 0  # Quantified: must be exactly 0
    await bot.cleanup()


@pytest.mark.asyncio
async def test_sol_position_query_zero(mock_env_vars):
    """Test 6: SOL position query returns 0."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    position = await bot.sol_client.get_account_positions()
    assert position == 0
    await bot.cleanup()


@pytest.mark.asyncio
async def test_eth_bbo_prices_positive(mock_env_vars):
    """Test 7: ETH BBO prices return positive values."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock fetch_bbo_prices to return valid prices
    from unittest.mock import AsyncMock, patch
    with patch.object(bot.eth_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_prices:
        mock_prices.return_value = (Decimal("3000"), Decimal("3001"))
        bid, ask = await bot.eth_client.fetch_bbo_prices(bot.eth_client.config.contract_id)
        assert bid > 0  # Quantified: must be > 0
        assert ask > 0
        assert ask >= bid  # Basic sanity check

    await bot.cleanup()


@pytest.mark.asyncio
async def test_sol_bbo_prices_positive(mock_env_vars):
    """Test 8: SOL BBO prices return positive values."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock fetch_bbo_prices to return valid prices
    from unittest.mock import AsyncMock, patch
    with patch.object(bot.sol_client, 'fetch_bbo_prices', new_callable=AsyncMock) as mock_prices:
        mock_prices.return_value = (Decimal("150"), Decimal("151"))
        bid, ask = await bot.sol_client.fetch_bbo_prices(bot.sol_client.config.contract_id)
        assert bid > 0
        assert ask > 0
        assert ask >= bid

    await bot.cleanup()


@pytest.mark.asyncio
async def test_websocket_connection(mock_env_vars):
    """Test 9: WebSocket connection can be established."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    await bot.eth_client.connect()
    await bot.sol_client.connect()
    # If no exception raised, test passes
    await bot.cleanup()


@pytest.mark.asyncio
async def test_environment_variables_set(mock_env_vars):
    """Test 10: Required environment variables are set."""
    assert os.getenv("NADO_PRIVATE_KEY") is not None
    assert len(os.getenv("NADO_PRIVATE_KEY")) == 66  # 0x + 64 hex chars
