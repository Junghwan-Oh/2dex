"""
Integration tests for Nado close order functionality.

Tests verify that place_close_order:
1. Uses IOC order type (not POST_ONLY)
2. Calculates isolated margin correctly
3. Rounds quantities to size increments
4. Handles fill detection properly
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add hedge directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hedge.exchanges.nado import NadoClient
from hedge.exchanges.base import OrderResult


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


@pytest.mark.asyncio
async def test_place_close_order_uses_ioc_not_post_only(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that place_close_order uses IOC order type."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner123"

        # Capture order type from build_appendix call
        captured_order_types = []

        original_build_appendix = None
        try:
            from hedge.exchanges.nado import build_appendix
            original_build_appendix = build_appendix
        except ImportError:
            pass

        def mock_build_appendix(**kwargs):
            captured_order_types.append(kwargs.get('order_type'))
            # Return a mock appendix
            from nado_protocol.utils.order import OrderType
            return b'mock_appendix'

        # Mock place_order to return success
        def mock_place_order(params):
            result = Mock()
            result.data = Mock()
            result.data.digest = "close_order_123"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock get_order_info for filled order
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.build_appendix', side_effect=mock_build_appendix):
            result = await client.place_close_order(
                contract_id='4',
                quantity=Decimal('0.1'),
                price=Decimal('3000'),
                side='sell'
            )

        # Assert: Order type should be IOC
        from nado_protocol.utils.order import OrderType
        assert len(captured_order_types) > 0, "build_appendix should have been called"
        assert captured_order_types[0] == OrderType.IOC, \
            f"Expected OrderType.IOC, got {captured_order_types[0]}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_isolated_margin_calculation(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that isolated_margin is calculated correctly for 5x leverage."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner456"

        # Capture isolated_margin from build_appendix call
        captured_margins = []

        def mock_build_appendix(**kwargs):
            captured_margins.append(kwargs.get('isolated_margin'))
            return b'mock_appendix'

        # Mock place_order
        def mock_place_order(params):
            result = Mock()
            result.data = Mock()
            result.data.digest = "close_order_789"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock get_order_info
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        # Calculate expected margin
        quantity = Decimal('0.1')
        price = Decimal('3000')
        notional = quantity * price  # 300 USD
        leverage = 5.0
        expected_margin = int(notional / leverage * 10**6)  # x6 precision
        # 300 / 5 = 60, * 10^6 = 60,000,000

        with patch('hedge.exchanges.nado.build_appendix', side_effect=mock_build_appendix):
            result = await client.place_close_order(
                contract_id='4',
                quantity=quantity,
                price=price,
                side='sell'
            )

        # Assert: Isolated margin should be calculated correctly
        assert len(captured_margins) > 0, "build_appendix should have been called"
        assert captured_margins[0] == expected_margin, \
            f"Expected isolated_margin {expected_margin}, got {captured_margins[0]}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_isolated_margin_sol(nado_config_sol, mock_sdk_client, monkeypatch):
    """Test isolated_margin calculation for SOL position."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_sol)
        client.owner = "0xtestowner789"

        captured_margins = []

        def mock_build_appendix(**kwargs):
            captured_margins.append(kwargs.get('isolated_margin'))
            return b'mock_appendix'

        def mock_place_order(params):
            result = Mock()
            result.data = Mock()
            result.data.digest = "close_order_sol_123"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('150'), Decimal('151')))

        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('5')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        # Calculate expected margin for SOL
        quantity = Decimal('5')
        price = Decimal('150')
        notional = quantity * price  # 750 USD
        leverage = 5.0
        expected_margin = int(notional / leverage * 10**6)  # 150,000,000

        with patch('hedge.exchanges.nado.build_appendix', side_effect=mock_build_appendix):
            result = await client.place_close_order(
                contract_id='8',
                quantity=quantity,
                price=price,
                side='buy'
            )

        assert len(captured_margins) > 0
        assert captured_margins[0] == expected_margin, \
            f"Expected isolated_margin {expected_margin}, got {captured_margins[0]}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_rounds_quantity_to_size_increment(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that quantity is rounded to size increment before order placement."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner101"

        # Capture the amount sent to the order
        captured_amounts = []

        def mock_place_order(params):
            # Capture the amount (in x18 format)
            captured_amounts.append(params['order'].amount)
            result = Mock()
            result.data = Mock()
            result.data.digest = "close_order_rounded"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        # Use a quantity that needs rounding: 0.1005 -> 0.101
        # But for ETH size increment is 0.001, so 0.1005 rounds to 0.101
        input_quantity = Decimal('0.1005')
        expected_rounded = Decimal('0.101')  # Rounded to 0.001 increment

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='4',
                quantity=input_quantity,
                price=Decimal('3000'),
                side='sell'
            )

        # Verify the rounded quantity was used
        from nado_protocol.utils.math import from_x18
        assert len(captured_amounts) > 0
        actual_quantity = Decimal(str(from_x18(abs(captured_amounts[0]))))
        assert actual_quantity == expected_rounded, \
            f"Expected quantity {expected_rounded}, got {actual_quantity}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_sol_rounding(nado_config_sol, mock_sdk_client, monkeypatch):
    """Test quantity rounding for SOL (size increment 0.1)."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_sol)
        client.owner = "0xtestowner202"

        captured_amounts = []

        def mock_place_order(params):
            captured_amounts.append(params['order'].amount)
            result = Mock()
            result.data = Mock()
            result.data.digest = "close_order_sol_round"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('150'), Decimal('151')))

        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('5.5')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        # SOL size increment is 0.1
        # 5.45 -> 5.5 (rounds to nearest 0.1)
        input_quantity = Decimal('5.45')
        expected_rounded = Decimal('5.5')

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='8',
                quantity=input_quantity,
                price=Decimal('150'),
                side='buy'
            )

        from nado_protocol.utils.math import from_x18
        assert len(captured_amounts) > 0
        actual_quantity = Decimal(str(from_x18(abs(captured_amounts[0]))))
        assert actual_quantity == expected_rounded, \
            f"Expected quantity {expected_rounded}, got {actual_quantity}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_fill_detection_filled(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test fill detection when order is fully filled."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner303"

        def mock_place_order(params):
            result = Mock()
            result.data = Mock()
            result.data.digest = "filled_order_123"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock fully filled order
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='4',
                quantity=Decimal('0.1'),
                price=Decimal('3000'),
                side='sell'
            )

        # Assert: Order should be marked as FILLED
        assert result.success is True
        assert result.status == 'FILLED', f"Expected status 'FILLED', got {result.status}"
        assert result.filled_size == Decimal('0.1'), \
            f"Expected filled_size 0.1, got {result.filled_size}"


@pytest.mark.asyncio
async def test_place_close_order_fill_detection_partially_filled(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test fill detection when order is partially filled."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner404"

        def mock_place_order(params):
            result = Mock()
            result.data = Mock()
            result.data.digest = "partial_fill_order"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock partially filled order
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.05')
        mock_order_info.remaining_size = Decimal('0.05')
        client.get_order_info = Mock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='4',
                quantity=Decimal('0.1'),
                price=Decimal('3000'),
                side='sell'
            )

        # Assert: Order should be marked as PARTIALLY_FILLED
        assert result.success is True
        assert result.status == 'PARTIALLY_FILLED', f"Expected status 'PARTIALLY_FILLED', got {result.status}"
        assert result.filled_size == Decimal('0.05'), \
            f"Expected filled_size 0.05, got {result.filled_size}"


@pytest.mark.asyncio
async def test_place_close_order_fill_detection_expired(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test fill detection when IOC order expires with no fill."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner505"

        def mock_place_order(params):
            result = Mock()
            result.data = Mock()
            result.data.digest = "expired_order"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock unfilled order (IOC expired)
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0')
        mock_order_info.remaining_size = Decimal('0.1')
        client.get_order_info = Mock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='4',
                quantity=Decimal('0.1'),
                price=Decimal('3000'),
                side='sell'
            )

        # Assert: Order should be marked as EXPIRED and success=False
        assert result.success is False, "Expected success=False for expired IOC order"
        assert result.status == 'EXPIRED', f"Expected status 'EXPIRED', got {result.status}"


@pytest.mark.asyncio
async def test_place_close_order_buy_side_uses_ask_price(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that buy close orders use best ask price."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner606"

        captured_prices = []

        def mock_place_order(params):
            from nado_protocol.utils.math import from_x18
            price_x18 = params['order'].priceX18
            price_decimal = Decimal(str(from_x18(price_x18)))
            captured_prices.append(price_decimal)
            result = Mock()
            result.data = Mock()
            result.data.digest = "buy_close_order"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)

        # Set BBO: bid=2999, ask=3001
        best_ask = Decimal('3001')
        client.fetch_bbo_prices = Mock(return_value=(Decimal('2999'), best_ask))

        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='4',
                quantity=Decimal('0.1'),
                price=Decimal('3000'),
                side='buy'  # Buy to close short position
            )

        # Assert: Buy order should use best ask (3001)
        assert len(captured_prices) > 0
        assert captured_prices[0] == best_ask, \
            f"Expected price {best_ask} for buy order, got {captured_prices[0]}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_sell_side_uses_bid_price(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that sell close orders use best bid price."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner707"

        captured_prices = []

        def mock_place_order(params):
            from nado_protocol.utils.math import from_x18
            price_x18 = params['order'].priceX18
            price_decimal = Decimal(str(from_x18(price_x18)))
            captured_prices.append(price_decimal)
            result = Mock()
            result.data = Mock()
            result.data.digest = "sell_close_order"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)

        # Set BBO: bid=2999, ask=3001
        best_bid = Decimal('2999')
        client.fetch_bbo_prices = Mock(return_value=(best_bid, Decimal('3001')))

        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = Mock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.build_appendix', return_value=b'mock_appendix'):
            result = await client.place_close_order(
                contract_id='4',
                quantity=Decimal('0.1'),
                price=Decimal('3000'),
                side='sell'  # Sell to close long position
            )

        # Assert: Sell order should use best bid (2999)
        assert len(captured_prices) > 0
        assert captured_prices[0] == best_bid, \
            f"Expected price {best_bid} for sell order, got {captured_prices[0]}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_invalid_bbo_prices(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that invalid BBO prices are handled correctly."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner808"

        # Mock invalid BBO prices
        client.fetch_bbo_prices = Mock(return_value=(Decimal('0'), Decimal('0')))

        result = await client.place_close_order(
            contract_id='4',
            quantity=Decimal('0.1'),
            price=Decimal('3000'),
            side='sell'
        )

        # Assert: Should return error for invalid BBO
        assert result.success is False
        assert 'Invalid bid/ask prices' in result.error_message


@pytest.mark.asyncio
async def test_place_close_order_max_retries(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that place_close_order respects max retries."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner909"

        # Mock BBO prices
        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock place_order to fail (return None)
        attempt_count = [0]

        def mock_place_order_fail(params):
            attempt_count[0] += 1
            return None  # Simulate failure

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order_fail)

        result = await client.place_close_order(
            contract_id='4',
            quantity=Decimal('0.1'),
            price=Decimal('3000'),
            side='sell'
        )

        # Assert: Should have tried max_retries times and failed
        assert attempt_count[0] == 3, f"Expected 3 retry attempts, got {attempt_count[0]}"
        assert result.success is False
        assert 'Max retries exceeded' in result.error_message


@pytest.mark.asyncio
async def test_place_close_order_small_quantity_rounds_to_zero(nado_config_eth, mock_sdk_client, monkeypatch):
    """Test that very small quantities are rejected (rounds to 0)."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        client = NadoClient(nado_config_eth)
        client.owner = "0xtestowner1010"

        client.fetch_bbo_prices = Mock(return_value=(Decimal('3000'), Decimal('3001')))

        # Use quantity smaller than size increment (0.001)
        # 0.0005 rounds to 0.001, but 0.0001 might round to 0
        result = await client.place_close_order(
            contract_id='4',
            quantity=Decimal('0.0001'),  # Smaller than 0.001 increment
            price=Decimal('3000'),
            side='sell'
        )

        # Assert: Should fail due to quantity too small
        assert result.success is False
        assert 'too small' in result.error_message or 'rounds to 0' in result.error_message
