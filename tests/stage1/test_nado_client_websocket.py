"""
Test Nado Client with WebSocket Integration

Tests for NadoClient with WebSocket BBO support.
"""

import pytest
import asyncio
import sys
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch, Mock

# Add to path
sys.path.insert(0, '/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges')

# We need to mock websockets but preserve it for web3's use
# Mock the WebSocket client classes directly
import nado_websocket_client
import nado_bbo_handler
import nado_bookdepth_handler


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

    @pytest.mark.asyncio
    async def test_get_bookdepth_handler(mock_config, mock_env):
        """Test getting BookDepth handler."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # Mock BookDepth handler
            mock_bookdepth_handler = MagicMock()
            client._bookdepth_handler = mock_bookdepth_handler
            client._ws_connected = True

            # Get handler
            handler = client.get_bookdepth_handler()
            assert handler == mock_bookdepth_handler

            # When not connected, should return None
            client._ws_connected = False
            handler = client.get_bookdepth_handler()
            assert handler is None

    @pytest.mark.asyncio
    async def test_estimate_slippage(mock_config, mock_env):
        """Test slippage estimation."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # Mock BookDepth handler
            mock_bookdepth_handler = MagicMock()
            mock_bookdepth_handler.estimate_slippage.return_value = Decimal("5.5")
            client._bookdepth_handler = mock_bookdepth_handler
            client._ws_connected = True

            # Estimate slippage
            slippage = await client.estimate_slippage("buy", Decimal("1.0"))
            assert slippage == Decimal("5.5")
            mock_bookdepth_handler.estimate_slippage.assert_called_once_with("buy", Decimal("1.0"))

    @pytest.mark.asyncio
    async def test_estimate_slippage_no_websocket(mock_config, mock_env):
        """Test slippage estimation when WebSocket not connected."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)
            client._ws_connected = False

            # Should return high slippage to indicate unavailable
            slippage = await client.estimate_slippage("buy", Decimal("1.0"))
            assert slippage == Decimal(999999)

    @pytest.mark.asyncio
    async def test_check_exit_capacity(mock_config, mock_env):
        """Test checking exit capacity."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # Mock BookDepth handler
            mock_bookdepth_handler = MagicMock()
            mock_bookdepth_handler.estimate_exit_capacity.return_value = (True, Decimal("1.0"))
            client._bookdepth_handler = mock_bookdepth_handler
            client._ws_connected = True

            # Check exit capacity
            can_exit, qty = await client.check_exit_capacity(Decimal("1.0"), max_slippage_bps=20)
            assert can_exit == True
            assert qty == Decimal("1.0")
            mock_bookdepth_handler.estimate_exit_capacity.assert_called_once_with(Decimal("1.0"), 20)

    @pytest.mark.asyncio
    async def test_get_available_liquidity(mock_config, mock_env):
        """Test getting available liquidity."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            client = nado.NadoClient(mock_config)

            # Mock BookDepth handler
            mock_bookdepth_handler = MagicMock()
            mock_bookdepth_handler.get_available_liquidity.return_value = Decimal("100.5")
            client._bookdepth_handler = mock_bookdepth_handler
            client._ws_connected = True

            # Get liquidity
            liquidity = await client.get_available_liquidity("ask", max_depth=20)
            assert liquidity == Decimal("100.5")
            mock_bookdepth_handler.get_available_liquidity.assert_called_once_with("ask", 20)

    @pytest.mark.asyncio
    async def test_connect_websocket_with_bookdepth(mock_config, mock_env):
        """Test that WebSocket connection initializes BookDepth handler."""
        with patch('nado.WEBSOCKET_AVAILABLE', True):
            # Mock WebSocket client
            mock_ws_client = MagicMock()
            mock_ws_client.connect = AsyncMock()
            mock_bbo_handler = MagicMock()
            mock_bbo_handler.start = AsyncMock()
            mock_bookdepth_handler = MagicMock()
            mock_bookdepth_handler.start = AsyncMock()

            with patch('nado.NadoWebSocketClient', return_value=mock_ws_client):
                with patch('nado.BBOHandler', return_value=mock_bbo_handler):
                    with patch('nado.BookDepthHandler', return_value=mock_bookdepth_handler):
                        client = nado.NadoClient(mock_config)

                        await client.connect()

                        # Verify both handlers were initialized and started
                        assert client._bbo_handler is not None
                        assert client._bookdepth_handler is not None
                        mock_bbo_handler.start.assert_called_once()
                        mock_bookdepth_handler.start.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
