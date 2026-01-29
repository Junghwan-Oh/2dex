"""
Test Nado Client with WebSocket Integration

Tests for NadoClient with WebSocket BBO support.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch

# Mock imports
ws_mock = MagicMock()
ws_mock.connect = AsyncMock()
import sys
sys.modules['websockets'] = ws_mock
sys.modules['websockets'].exceptions = MagicMock()
sys.modules['websockets'].exceptions.ConnectionClosed = Exception

# Add to path
sys.path.insert(0, '/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges')

import nado


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock()
    config.ticker = "ETH"
    config.tick_size = Decimal("0.1")
    return config


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    import os
    os.environ['NADO_PRIVATE_KEY'] = '0x' + '0' * 63 + '1'  # Valid private key format


class TestNadoClientWebSocket:
    """Test NadoClient with WebSocket integration."""

    @pytest.mark.asyncio
    async def test_init_with_websocket_available(mock_config, mock_env):
        """Test initialization when WebSocket is available."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            assert client._use_websocket == True
            assert client._ws_client is None  # Not connected yet
            assert client._bbo_handler is None

    @pytest.mark.asyncio
    async def test_connect_websocket(mock_config, mock_env):
        """Test connecting to WebSocket."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            # Mock WebSocket client
            mock_ws_client = MagicMock()
            mock_ws_client.connect = AsyncMock()
            mock_bbo_handler = MagicMock()

            with patch('nado.NadoWebSocketClient', return_value=mock_ws_client):
                with patch('nado.BBOHandler', return_value=mock_bbo_handler):
                    client = nado.NadoClient(mock_config)

                    await client.connect()

                    # Verify WebSocket was initialized
                    assert client._ws_client is not None

    @pytest.mark.asyncio
    async def test_fetch_bbo_from_websocket(mock_config, mock_env):
        """Test fetching BBO from WebSocket when connected."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # Mock BBO handler with prices
            mock_bbo_handler = MagicMock()
            mock_bbo_handler.get_prices.return_value = (Decimal("3000"), Decimal("3001"))
            client._bbo_handler = mock_bbo_handler
            client._ws_connected = True

            # Fetch BBO
            bid, ask = await client.fetch_bbo_prices("ETH")

            # Verify WebSocket data was used
            assert bid == Decimal("3000")
            assert ask == Decimal("3001")
            mock_bbo_handler.get_prices.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_bbo_fallback_to_rest(mock_config, mock_env):
        """Test REST fallback when WebSocket not available."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # WebSocket not connected
            client._ws_connected = False

            # Mock REST API response
            mock_orderbook = MagicMock()
            mock_orderbook.bids = [[Decimal("3000"), Decimal("1.0")]]
            mock_orderbook.asks = [[Decimal("3001"), Decimal("1.0")]]

            with patch.object(client.client.context.engine_client, 'get_orderbook', return_value=mock_orderbook):
                bid, ask = await client.fetch_bbo_prices("ETH")

                # Verify REST was called
                assert bid == Decimal("3000")
                assert ask == Decimal("3001")

    @pytest.mark.asyncio
    async def test_disconnect_websocket(mock_config, mock_env):
        """Test disconnecting WebSocket."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # Mock WebSocket client
            mock_ws_client = MagicMock()
            mock_ws_client.disconnect = AsyncMock()
            client._ws_client = mock_ws_client
            client._ws_connected = True

            await client.disconnect()

            # Verify disconnect was called
            mock_ws_client.disconnect.assert_called_once()
            assert client._ws_connected == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
