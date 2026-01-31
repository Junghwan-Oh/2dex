"""
Unit tests for Nado address consistency.

Tests verify that all NadoClient methods use self.owner consistently
for subaccount resolution instead of using self.client.context.signer.address.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock, AsyncMock
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
def nado_config():
    """Create NadoClient config for testing."""
    return Config({
        'ticker': 'ETH',
        'contract_id': '4',
        'tick_size': Decimal('0.0001'),
        'size_increment': Decimal('0.001'),
        'price_increment': Decimal('0.0001'),
    })


@pytest.fixture
def mock_sdk_client():
    """Mock the Nado SDK client."""
    mock_client = Mock()
    mock_client.context = Mock()
    mock_client.context.engine_client = Mock()
    mock_client.context.indexer_client = Mock()
    mock_client.market = Mock()

    # Mock signer.address - this should NOT be used for order operations
    mock_client.context.engine_client.signer.address = "0xwrongaddress123"

    return mock_client


@pytest.mark.asyncio
async def test_place_ioc_order_uses_owner_not_signer_address(nado_config, mock_sdk_client, monkeypatch):
    """Test that place_ioc_order uses self.owner, not self.client.context.signer.address."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    # Patch create_nado_client to return our mock
    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create client
        client = NadoClient(nado_config)

        # Set owner to a different address than signer.address
        # This simulates the bug where owner differs from signer.address
        expected_owner = "0xexpectedowner456"
        client.owner = expected_owner

        # Mock the place_order method to capture the SubaccountParams
        captured_params = {}

        def mock_place_order(params):
            captured_params['sender'] = params['order'].sender.subaccount_owner
            # Return a successful result
            result = Mock()
            result.data = Mock()
            result.data.digest = "test_order_123"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)

        # Mock fetch_bbo_prices as async
        client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock get_order_info
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = AsyncMock(return_value=mock_order_info)

        # Call place_ioc_order
        result = await client.place_ioc_order(
            contract_id='4',
            quantity=Decimal('0.1'),
            direction='buy'
        )

        # Assert that the correct owner address was used
        assert captured_params['sender'] == expected_owner, \
            f"Expected owner {expected_owner} to be used, but got {captured_params['sender']}"
        assert result.success is True


@pytest.mark.asyncio
async def test_place_close_order_uses_owner_not_signer_address(nado_config, mock_sdk_client, monkeypatch):
    """Test that place_close_order uses self.owner, not self.client.context.signer.address."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    # Patch create_nado_client to return our mock
    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create client
        client = NadoClient(nado_config)

        # Set owner to a different address than signer.address
        expected_owner = "0xexpectedowner789"
        client.owner = expected_owner

        # Mock the place_order method to capture the SubaccountParams
        captured_params = {}

        def mock_place_order(params):
            captured_params['sender'] = params['order'].sender.subaccount_owner
            result = Mock()
            result.data = Mock()
            result.data.digest = "test_close_order_123"
            return result

        mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order)

        # Mock fetch_bbo_prices as async
        client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('3000'), Decimal('3001')))

        # Mock get_order_info
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0.1')
        mock_order_info.remaining_size = Decimal('0')
        client.get_order_info = AsyncMock(return_value=mock_order_info)

        # Call place_close_order
        result = await client.place_close_order(
            contract_id='4',
            quantity=Decimal('0.1'),
            price=Decimal('3000'),
            side='sell'
        )

        # Assert that the correct owner address was used
        assert captured_params['sender'] == expected_owner, \
            f"Expected owner {expected_owner} to be used, but got {captured_params['sender']}"
        assert result.success is True


@pytest.mark.asyncio
async def test_get_account_positions_uses_owner_not_signer_address(nado_config, mock_sdk_client, monkeypatch):
    """Test that get_account_positions uses self.owner, not self.client.context.signer.address."""
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    # Patch create_nado_client to return our mock
    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create client
        client = NadoClient(nado_config)

        # Set owner to a specific address
        expected_owner = "0xexpectedowner101"
        client.owner = expected_owner

        # Mock subaccount_to_hex to capture the SubaccountParams or owner/name args
        captured_subaccount = []

        def mock_subaccount_to_hex(*args):
            # Handle both calling patterns:
            # 1. subaccount_to_hex(SubaccountParams(...)) - single arg
            # 2. subaccount_to_hex(owner, name) - two args
            if len(args) == 1 and hasattr(args[0], 'subaccount_owner'):
                # SubaccountParams object
                captured_subaccount.append(args[0].subaccount_owner)
                return f"0xsubaccount_{args[0].subaccount_owner}"
            elif len(args) == 2:
                # owner, name as separate args
                captured_subaccount.append(args[0])
                return f"0xsubaccount_{args[0]}"
            else:
                # Fallback
                return "0xmock_subaccount"

        # Mock get_subaccount_info to return position data
        mock_account_data = Mock()
        mock_position = Mock()
        mock_position.product_id = '4'  # String to match config.contract_id
        mock_position.balance.amount = int(0.1 * 1e18)  # 0.1 ETH in x18
        mock_account_data.perp_balances = [mock_position]

        mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):
            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
                # Call get_account_positions
                position = await client.get_account_positions()

        # Assert that the correct owner address was used
        assert len(captured_subaccount) > 0, "subaccount_to_hex should have been called"
        assert captured_subaccount[0] == expected_owner, \
            f"Expected owner {expected_owner} to be used, but got {captured_subaccount[0]}"

        # Verify position value
        assert position == Decimal('0.1'), f"Expected position 0.1, got {position}"


@pytest.mark.asyncio
async def test_cancel_order_uses_owner_not_signer_address(nado_config, mock_sdk_client, monkeypatch):
    """Test that cancel_order uses self.owner, not self.client.context.signer.address."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    # Patch create_nado_client to return our mock
    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create client
        client = NadoClient(nado_config)

        # Set owner to a specific address
        expected_owner = "0xexpectedowner202"
        client.owner = expected_owner

        # Mock subaccount_to_hex to return valid hex
        def mock_subaccount_to_hex(*args):
            if len(args) == 1 and hasattr(args[0], 'subaccount_owner'):
                return f"0xsubaccount_{args[0].subaccount_owner}"
            elif len(args) == 2:
                return f"0xsubaccount_{args[0]}"
            return "0xmock_subaccount"

        # Mock cancel_orders to capture the sender
        captured_sender = []

        def mock_cancel_orders(params):
            captured_sender.append(params.sender)
            result = Mock()
            result.data = Mock()
            return result  # Return truthy result

        mock_sdk_client.market.cancel_orders = Mock(side_effect=mock_cancel_orders)

        # Mock get_order_info
        mock_order_info = Mock()
        mock_order_info.filled_size = Decimal('0')
        mock_order_info.price = Decimal('3000')
        client.get_order_info = AsyncMock(return_value=mock_order_info)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):
            # Call cancel_order with valid hex order_id
            result = await client.cancel_order("0x" + "a" * 64)

        # Assert that the correct owner address was used
        # The captured_sender should contain the subaccount hex with expected_owner
        assert len(captured_sender) > 0, "cancel_orders should have been called"
        assert expected_owner in captured_sender[0], \
            f"Expected owner {expected_owner} to be in sender, but got {captured_sender[0]}"
        assert result.success is True


@pytest.mark.asyncio
async def test_get_active_orders_uses_owner_not_signer_address(nado_config, mock_sdk_client, monkeypatch):
    """Test that get_active_orders uses self.owner, not self.client.context.signer.address."""
    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    # Patch create_nado_client to return our mock
    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create client
        client = NadoClient(nado_config)

        # Set owner to a specific address
        expected_owner = "0xexpectedowner303"
        client.owner = expected_owner

        # Mock subaccount_to_hex to return valid hex
        def mock_subaccount_to_hex(*args):
            if len(args) == 1 and hasattr(args[0], 'subaccount_owner'):
                return f"0xsubaccount_{args[0].subaccount_owner}"
            elif len(args) == 2:
                return f"0xsubaccount_{args[0]}"
            return "0xmock_subaccount"

        # Mock get_subaccount_open_orders to capture the sender
        captured_sender = []

        def mock_get_subaccount_open_orders(product_id, sender):
            captured_sender.append(sender)
            result = Mock()
            result.orders = []
            return result

        mock_sdk_client.market.get_subaccount_open_orders = Mock(side_effect=mock_get_subaccount_open_orders)

        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):
            # Call get_active_orders
            orders = await client.get_active_orders('4')

        # Assert that the correct owner address was used
        assert len(captured_sender) > 0, "get_subaccount_open_orders should have been called"
        assert expected_owner in captured_sender[0], \
            f"Expected owner {expected_owner} to be in sender, but got {captured_sender[0]}"
        assert orders == []


@pytest.mark.asyncio
async def test_all_methods_consistent_owner_address(nado_config, mock_sdk_client, monkeypatch):
    """
    Integration test: Verify all order-related methods use consistent owner address.

    This test ensures that:
    1. place_ioc_order uses self.owner
    2. place_close_order uses self.owner
    3. get_account_positions uses self.owner
    4. cancel_order uses self.owner
    5. get_active_orders uses self.owner
    """
    from nado_protocol.utils.math import from_x18

    # Set up environment
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

    # Patch create_nado_client to return our mock
    with patch('hedge.exchanges.nado.create_nado_client', return_value=mock_sdk_client):
        # Create client
        client = NadoClient(nado_config)

        # All methods should use this owner address
        expected_owner = "0xconsistent_owner_404"
        client.owner = expected_owner

        # Track which methods used the correct owner
        methods_checked = {}

        # Create a shared subaccount_to_hex mock for all tests
        captured_subaccount_calls = []

        def mock_subaccount_to_hex(*args):
            # Handle both calling patterns
            if len(args) == 1 and hasattr(args[0], 'subaccount_owner'):
                # SubaccountParams object
                captured_subaccount_calls.append(args[0].subaccount_owner)
                return f"0xsubaccount_{args[0].subaccount_owner}"
            elif len(args) == 2:
                # owner, name as separate args
                captured_subaccount_calls.append(args[0])
                return f"0xsubaccount_{args[0]}"
            else:
                return "0xmock_subaccount"

        # Patch subaccount_to_hex for the entire test
        with patch('hedge.exchanges.nado.subaccount_to_hex', side_effect=mock_subaccount_to_hex):
            with patch('hedge.exchanges.nado.from_x18', side_effect=from_x18):
                # 1. Test place_ioc_order
                captured_ioc = []

                def mock_place_order_ioc(params):
                    captured_ioc.append(params['order'].sender.subaccount_owner)
                    result = Mock()
                    result.data = Mock()
                    result.data.digest = "ioc_order_123"
                    return result

                mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order_ioc)
                client.fetch_bbo_prices = AsyncMock(return_value=(Decimal('3000'), Decimal('3001')))

                mock_order_info_ioc = Mock()
                mock_order_info_ioc.filled_size = Decimal('0.05')
                mock_order_info_ioc.remaining_size = Decimal('0')
                client.get_order_info = AsyncMock(return_value=mock_order_info_ioc)

                await client.place_ioc_order('4', Decimal('0.05'), 'buy')
                methods_checked['place_ioc_order'] = captured_ioc[0] == expected_owner

                # 2. Test place_close_order
                captured_close = []

                def mock_place_order_close(params):
                    captured_close.append(params['order'].sender.subaccount_owner)
                    result = Mock()
                    result.data = Mock()
                    result.data.digest = "close_order_123"
                    return result

                mock_sdk_client.market.place_order = Mock(side_effect=mock_place_order_close)

                await client.place_close_order('4', Decimal('0.05'), Decimal('3000'), 'sell')
                methods_checked['place_close_order'] = captured_close[0] == expected_owner

                # 3. Test get_account_positions
                # Clear the shared captured list for this test
                captured_positions_count_before = len(captured_subaccount_calls)

                mock_account_data = Mock()
                mock_account_data.perp_balances = []
                mock_sdk_client.context.engine_client.get_subaccount_info = Mock(return_value=mock_account_data)

                await client.get_account_positions()

                # Check that subaccount_to_hex was called with expected_owner
                methods_checked['get_account_positions'] = (
                    len(captured_subaccount_calls) > captured_positions_count_before and
                    captured_subaccount_calls[captured_positions_count_before] == expected_owner
                )

                # 4. Test cancel_order
                captured_cancel = []

                def mock_cancel_orders(params):
                    captured_cancel.append(params.sender)
                    result = Mock()
                    return result

                mock_sdk_client.market.cancel_orders = Mock(side_effect=mock_cancel_orders)

                mock_order_info_cancel = Mock()
                mock_order_info_cancel.filled_size = Decimal('0')
                mock_order_info_cancel.price = Decimal('3000')
                client.get_order_info = AsyncMock(return_value=mock_order_info_cancel)

                await client.cancel_order("0x" + "a" * 64)  # Use valid hex order_id
                methods_checked['cancel_order'] = expected_owner in captured_cancel[0]

                # 5. Test get_active_orders
                captured_active = []

                def mock_get_subaccount_open_orders(product_id, sender):
                    captured_active.append(sender)
                    result = Mock()
                    result.orders = []
                    return result

                mock_sdk_client.market.get_subaccount_open_orders = Mock(side_effect=mock_get_subaccount_open_orders)

                await client.get_active_orders('4')
                methods_checked['get_active_orders'] = expected_owner in captured_active[0]

                # Assert all methods used the correct owner
                for method_name, used_correct_owner in methods_checked.items():
                    assert used_correct_owner, \
                        f"Method {method_name} did not use the expected owner address {expected_owner}"

                # All methods should pass
                assert all(methods_checked.values()), \
                    f"Not all methods used consistent owner: {methods_checked}"
