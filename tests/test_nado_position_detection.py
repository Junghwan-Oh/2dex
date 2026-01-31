"""
Integration tests for Nado position detection.

Tests verify that get_account_positions correctly detects positions
with proper subaccount resolution and returns accurate position sizes.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from nado_protocol.utils.math import from_x18
import sys
import os

# Add hedge directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hedge.exchanges.nado import NadoClient


class Config:
    """Config class that converts dict to object with attributes."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


@pytest.fixture
def nado_config_eth():
    """Create NadoClient config for ETH."""
    return Config({
        'ticker': 'ETH',
        'contract_id': '4',
        'tick_size': Decimal('0.0001'),
        'size_increment': Decimal('0.001'),
        'price_increment': Decimal('0.0001'),
    })


@pytest.fixture
def nado_config_sol():
    """Create NadoClient config for SOL."""
    return Config({
        'ticker': 'SOL',
        'contract_id': '8',
        'tick_size': Decimal('0.01'),
        'size_increment': Decimal('0.1'),
        'price_increment': Decimal('0.01'),
    })


@pytest.fixture
def mock_sdk_client():
    """Mock the Nado SDK client."""
    mock_client = Mock()
    mock_client.context = Mock()
    mock_client.context.engine_client = Mock()
    mock_client.context.indexer_client = Mock()
    mock_client.market = Mock()
    return mock_client


def create_mock_position(product_id, balance_amount):
    """Create a mock position object."""
    position = Mock()
    position.product_id = str(product_id)  # Convert to string to match config.contract_id
    position.balance.amount = balance_amount
    return position


def mock_subaccount_to_hex(*args):
    """Mock subaccount_to_hex for tests."""
    if len(args) == 1 and hasattr(args[0], 'subaccount_owner'):
        return f"0xsubaccount_{args[0].subaccount_owner}"
    elif len(args) == 2:
        return f"0xsubaccount_{args[0]}"
    return "0xmock_subaccount"


@pytest.mark.asyncio
async def test_get_account_positions_zero_position(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that get_account_positions returns 0 when no positions exist."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner123"

        # Mock empty position list
        mock_account_data = Mock()
        mock_account_data.perp_balances = []
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            position = await client.get_account_positions()

        # Assert: Position should be exactly 0
        assert position == Decimal('0'), f"Expected position 0, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_eth_long_position(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test detection of ETH long position (0.5 ETH)."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner456"

        # Mock ETH position: 0.5 ETH long
        mock_account_data = Mock()
        mock_position = create_mock_position(4, int(0.5 * 1e18))  # 0.5 ETH in x18
        mock_account_data.perp_balances = [mock_position]
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):
            with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):

                with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
                position = await client.get_account_positions()

        # Assert: Position should be 0.5 ETH (within tolerance)
        assert abs(position - Decimal('0.5')) < Decimal('0.001'), \
            f"Expected position 0.5, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_sol_short_position(nado_config_sol, mock_sdk_client, monkeypatch):
    """Test detection of SOL short position (-10 SOL)."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_sol)
        client.owner = "0xtestowner789"

        # Mock SOL position: -10 SOL short
        mock_account_data = Mock()
        mock_position = create_mock_position(8, int(-10 * 1e18))  # -10 SOL in x18
        mock_account_data.perp_balances = [mock_position]
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            position = await client.get_account_positions()

        # Assert: Position should be -10 SOL (within tolerance of 0.1)
        assert abs(position - Decimal('-10')) < Decimal('0.1'), \
            f"Expected position -10, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_filters_correct_product(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that get_account_positions filters by correct product_id."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner101"

        # Mock multiple positions: ETH (4) and SOL (8)
        mock_account_data = Mock()
        eth_position = create_mock_position(4, int(0.3 * 1e18))  # 0.3 ETH
        sol_position = create_mock_position(8, int(-5 * 1e18))  # -5 SOL
        mock_account_data.perp_balances = [eth_position, sol_position]
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            position = await client.get_account_positions()

        # Assert: Should return ETH position (0.3) since config is for ETH
        assert abs(position - Decimal('0.3')) < Decimal('0.001'), \
            f"Expected position 0.3 (ETH), got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_small_position(nado_config_sol, mock_sdk_client, monkeypatch):
    """Test detection of small SOL position (0.5 SOL)."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_sol)
        client.owner = "0xtestowner202"

        # Mock small SOL position: 0.5 SOL
        mock_account_data = Mock()
        mock_position = create_mock_position(8, int(0.5 * 1e18))
        mock_account_data.perp_balances = [mock_position]
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            position = await client.get_account_positions()

        # Assert: Position should be 0.5 SOL (within tolerance of 0.1)
        assert abs(position - Decimal('0.5')) < Decimal('0.1'), \
            f"Expected position 0.5, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_large_eth_position(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test detection of large ETH position (2.5 ETH)."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner303"

        # Mock large ETH position: 2.5 ETH
        mock_account_data = Mock()
        mock_position = create_mock_position(4, int(2.5 * 1e18))
        mock_account_data.perp_balances = [mock_position]
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            position = await client.get_account_positions()

        # Assert: Position should be 2.5 ETH (within tolerance of 0.001)
        assert abs(position - Decimal('2.5')) < Decimal('0.001'), \
            f"Expected position 2.5, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_error_handling(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that get_account_positions returns 0 on error."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner404"

        # Mock error response
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(side_effect=Exception("API Error"))

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            position = await client.get_account_positions()

        # Assert: Should return 0 on error
        assert position == Decimal('0'), f"Expected position 0 on error, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_subaccount_resolution(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that get_account_positions uses correct subaccount resolution."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "custom_subaccount")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner505"

        # Track subaccount_to_hex calls
        captured_subaccounts = []

        def mock_subaccount_to_hex(*args):
            # Handle both calling patterns
            if len(args) == 1 and hasattr(args[0], 'subaccount_owner'):
                # SubaccountParams object
                captured_subaccounts.append({
                    'owner': args[0].subaccount_owner,
                    'name': args[0].subaccount_name,
                })
                return "0xresolved_subaccount"
            elif len(args) == 2:
                # owner, name as separate args
                captured_subaccounts.append({
                    'owner': args[0],
                    'name': args[1],
                })
                return "0xresolved_subaccount"
            else:
                return "0xresolved_subaccount"

        # Mock position data
        mock_account_data = Mock()
        mock_position = create_mock_position(4, int(0.1 * 1e18))
        mock_account_data.perp_balances = [mock_position]
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):
            with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):

                with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
                position = await client.get_account_positions()

        # Assert: Subaccount should be resolved with correct owner and name
        assert len(captured_subaccounts) > 0, "subaccount_to_hex should have been called"
        assert captured_subaccounts[0]['owner'] == "0xtestowner505", \
            f"Expected owner 0xtestowner505, got {captured_subaccounts[0]['owner']}"
        assert captured_subaccounts[0]['name'] == "custom_subaccount", \
            f"Expected subaccount_name 'custom_subaccount', got {captured_subaccounts[0]['name']}"
        assert abs(position - Decimal('0.1')) < Decimal('0.001'), \
            f"Expected position 0.1, got {position}"


@pytest.mark.asyncio
async def test_get_account_positions_concurrent_calls(nado_config_eth, nado_config_sol, mock_sdk_client, monkeypatch):
    """Test concurrent position queries for ETH and SOL."""
    import asyncio
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create both clients
        eth_client = NadoClient(nado_config_eth)
        eth_client.owner = "0xtestowner606"

        sol_client = NadoClient(nado_config_sol)
        sol_client.owner = "0xtestowner606"  # Same owner, different contract

        # Mock ETH position
        def mock_get_subaccount_info_eth(subaccount_hex):
            mock_data = Mock()
            mock_position = create_mock_position(4, int(0.2 * 1e18))
            mock_data.perp_balances = [mock_position]
            return mock_data

        # Mock SOL position
        def mock_get_subaccount_info_sol(subaccount_hex):
            mock_data = Mock()
            mock_position = create_mock_position(8, int(-3 * 1e18))
            mock_data.perp_balances = [mock_position]
            return mock_data

        # Set up different mocks for each client
        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(
            side_effect=lambda x: mock_get_subaccount_info_eth(x) if '4' in str(eth_client.config.contract_id) else mock_get_subaccount_info_sol(x)
        )

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
            # Call both concurrently
            results = await asyncio.gather(
                eth_client.get_account_positions(),
                sol_client.get_account_positions()
            )

        eth_position, sol_position = results

        # Assert both positions are correct
        assert abs(eth_position - Decimal('0.2')) < Decimal('0.001'), \
            f"Expected ETH position 0.2, got {eth_position}"
        assert abs(sol_position - Decimal('-3')) < Decimal('0.1'), \
            f"Expected SOL position -3, got {sol_position}"


@pytest.mark.asyncio
async def test_get_account_positions_precision_tolerance(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test position detection with various precision levels."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner707"

        # Test various position sizes with tolerance 0.001 ETH
        test_cases = [
            (Decimal('0.001'), int(0.001 * 1e18), Decimal('0.001')),  # Minimum detectable
            (Decimal('0.010'), int(0.010 * 1e18), Decimal('0.010')),  # 0.01 ETH
            (Decimal('0.100'), int(0.100 * 1e18), Decimal('0.100')),  # 0.1 ETH
            (Decimal('1.000'), int(1.000 * 1e18), Decimal('1.000')),  # 1 ETH
        ]

        for expected_pos, x18_amount, expected_decimal in test_cases:
            mock_account_data = Mock()
            mock_position = create_mock_position(4, x18_amount)
            mock_account_data.perp_balances = [mock_position]
            mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

            with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):


                with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
                position = await client.get_account_positions()

            # Assert within tolerance of 0.001 ETH
            assert abs(position - expected_decimal) <= Decimal('0.001'), \
                f"For expected {expected_decimal}, got {position}, diff = {abs(position - expected_decimal)}"
