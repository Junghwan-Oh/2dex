"""
Test Nado WebSocket Client

Tests for WebSocket client, BBO handler, and BookDepth handler.
"""

import pytest
import asyncio
import sys
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Add exchanges directory to path
sys.path.insert(0, '/Users/botfarmer/2dex/perpdex/strategies/2dex/exchanges')

# Mock websockets library before importing our modules
ws_mock = MagicMock()
ws_mock.connect = AsyncMock()
ws_mock.exceptions = MagicMock()
ws_mock.exceptions.ConnectionClosed = Exception
sys.modules['websockets'] = ws_mock

import nado_websocket_client
import nado_bbo_handler
import nado_bookdepth_handler

NadoWebSocketClient = nado_websocket_client.NadoWebSocketClient
ConnectionState = nado_websocket_client.ConnectionState
BBOHandler = nado_bbo_handler.BBOHandler
BBOData = nado_bbo_handler.BBOData
SpreadMonitor = nado_bbo_handler.SpreadMonitor
MomentumDetector = nado_bbo_handler.MomentumDetector
BookDepthHandler = nado_bookdepth_handler.BookDepthHandler


@pytest.fixture
def mock_ws():
    """Mock WebSocket connection."""
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.closed = False
    return ws


@pytest.fixture
def mock_websocket_client(mock_ws):
    """Mock WebSocket client."""
    with patch('perpdex.strategies.2dex.exchanges.nado_websocket_client.websockets.connect') as mock_connect:
        mock_connect.return_value = mock_ws
        client = NadoWebSocketClient(product_ids=[4])
        yield client, mock_ws


class TestNadoWebSocketClient:
    """Test NadoWebSocketClient class."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_websocket_client):
        """Test successful WebSocket connection."""
        client, mock_ws = mock_websocket_client

        await client.connect()

        assert client.state == ConnectionState.CONNECTED
        assert client.is_connected

    @pytest.mark.asyncio
    async def test_subscribe_bbo(self, mock_websocket_client):
        """Test subscribing to BBO stream."""
        client, mock_ws = mock_websocket_client

        await client.connect()
        await client.subscribe("best_bid_offer", 4)

        # Verify subscription message was sent
        mock_ws.send.assert_called_once()
        sent_message = mock_ws.send.call_args[0][0]
        import json
        data = json.loads(sent_message)

        assert data["method"] == "subscribe"
        assert data["stream"]["type"] == "best_bid_offer"
        assert data["stream"]["product_id"] == 4

    @pytest.mark.asyncio
    async def test_subscribe_invalid_stream_type(self, mock_websocket_client):
        """Test subscribing with invalid stream type raises ValueError."""
        client, _ = mock_websocket_client

        await client.connect()

        with pytest.raises(ValueError, match="Invalid stream_type"):
            await client.subscribe("invalid_stream", 4)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, mock_websocket_client):
        """Test unsubscribing from a stream."""
        client, mock_ws = mock_websocket_client

        await client.connect()
        await client.subscribe("best_bid_offer", 4)
        await client.unsubscribe("best_bid_offer", 4)

        # Verify unsubscribe message was sent
        assert mock_ws.send.call_count == 2  # subscribe + unsubscribe


class TestBBOHandler:
    """Test BBOHandler class."""

    @pytest.mark.asyncio
    async def test_process_bbo_message(self, mock_websocket_client):
        """Test processing BBO message."""
        client, _ = mock_websocket_client
        handler = BBOHandler(4, client)

        message = {
            "type": "best_bid_offer",
            "timestamp": "1769702385345466465",
            "product_id": 4,
            "bid_price": "2821900000000000000000",
            "bid_qty": "417000000000000000",
            "ask_price": "2822000000000000000000",
            "ask_qty": "1334000000000000000"
        }

        await handler._on_bbo_message(message)

        bbo = handler.get_latest_bbo()
        assert bbo is not None
        assert bbo.bid_price == Decimal("2821.9")
        assert bbo.ask_price == Decimal("2822.0")
        assert bbo.spread == Decimal("0.1")

    @pytest.mark.asyncio
    async def test_get_prices(self, mock_websocket_client):
        """Test getting current prices."""
        client, _ = mock_websocket_client
        handler = BBOHandler(4, client)

        message = {
            "type": "best_bid_offer",
            "product_id": 4,
            "bid_price": "3000000000000000000000",  # 3000
            "bid_qty": "1000000000000000000",
            "ask_price": "3001000000000000000000",  # 3001
            "ask_qty": "1000000000000000000"
        }

        await handler._on_bbo_message(message)

        bid, ask = handler.get_prices()
        assert bid == Decimal("3000")
        assert ask == Decimal("3001")

    @pytest.mark.asyncio
    async def test_get_fair_value(self, mock_websocket_client):
        """Test getting fair value (mid price)."""
        client, _ = mock_websocket_client
        handler = BBOHandler(4, client)

        message = {
            "type": "best_bid_offer",
            "product_id": 4,
            "bid_price": "3000000000000000000000",  # 3000
            "bid_qty": "1000000000000000000",
            "ask_price": "3002000000000000000000",  # 3002
            "ask_qty": "1000000000000000000"
        }

        await handler._on_bbo_message(message)

        fair_value = handler.get_fair_value()
        assert fair_value == Decimal("3001")  # Mid of 3000 and 3002

    @pytest.mark.asyncio
    async def test_get_spread_bps(self, mock_websocket_client):
        """Test getting spread in basis points."""
        client, _ = mock_websocket_client
        handler = BBOHandler(4, client)

        message = {
            "type": "best_bid_offer",
            "product_id": 4,
            "bid_price": "3000000000000000000000",  # 3000
            "bid_qty": "1000000000000000000",
            "ask_price": "3001000000000000000000",  # 3001
            "ask_qty": "1000000000000000000"
        }

        await handler._on_bbo_message(message)

        bbo = handler.get_latest_bbo()
        spread_bps = bbo.spread_bps
        # spread = 1, mid = 3000.5, bps = (1 / 3000.5) * 10000 ≈ 3.33
        assert spread_bps > Decimal("3")
        assert spread_bps < Decimal("4")


class TestSpreadMonitor:
    """Test SpreadMonitor class."""

    def test_spread_monitor_stable(self):
        """Test spread monitor with stable spread."""
        monitor = SpreadMonitor(window_size=10)

        # Create stable BBO data
        for i in range(10):
            bbo = BBOData(
                product_id=4,
                bid_price=Decimal("3000"),
                bid_qty=Decimal("1"),
                ask_price=Decimal("3001"),
                ask_qty=Decimal("1"),
                timestamp=i * 1000
            )
            state = monitor.on_bbo(bbo)

        assert state == "STABLE"

    def test_spread_monitor_widening(self):
        """Test spread monitor detecting widening spread."""
        monitor = SpreadMonitor(window_size=10)

        # Create stable spreads, then widening
        for i in range(8):
            bbo = BBOData(
                product_id=4,
                bid_price=Decimal("3000"),
                bid_qty=Decimal("1"),
                ask_price=Decimal("3001"),
                ask_qty=Decimal("1"),
                timestamp=i * 1000
            )
            monitor.on_bbo(bbo)

        # Now send widening spread
        bbo = BBOData(
            product_id=4,
            bid_price=Decimal("3000"),
            bid_qty=Decimal("1"),
            ask_price=Decimal("3010"),  # Much wider
            ask_qty=Decimal("1"),
            timestamp=8000
        )

        state = monitor.on_bbo(bbo)
        assert state == "WIDENING"


class TestMomentumDetector:
    """Test MomentumDetector class."""

    def test_momentum_detector_bullish(self):
        """Test momentum detector detecting bullish trend."""
        detector = MomentumDetector(window_size=10)

        # Create rising prices
        for i in range(10):
            bbo = BBOData(
                product_id=4,
                bid_price=Decimal("3000") + Decimal(i),
                bid_qty=Decimal("1"),
                ask_price=Decimal("3001") + Decimal(i),
                ask_qty=Decimal("1"),
                timestamp=i * 1000
            )
            detector.on_bbo(bbo)

        momentum = detector.on_bbo(bbo)
        assert momentum == "BULLISH"

    def test_momentum_detector_bearish(self):
        """Test momentum detector detecting bearish trend."""
        detector = MomentumDetector(window_size=10)

        # Create falling prices
        for i in range(10):
            bbo = BBOData(
                product_id=4,
                bid_price=Decimal("3010") - Decimal(i),
                bid_qty=Decimal("1"),
                ask_price=Decimal("3011") - Decimal(i),
                ask_qty=Decimal("1"),
                timestamp=i * 1000
            )
            detector.on_bbo(bbo)

        momentum = detector.on_bbo(bbo)
        assert momentum == "BEARISH"


class TestBookDepthHandler:
    """Test BookDepthHandler class."""

    @pytest.mark.asyncio
    async def test_process_bookdepth_add_levels(self, mock_websocket_client):
        """Test processing BookDepth message adding levels."""
        client, _ = mock_websocket_client
        handler = BookDepthHandler(4, client)

        message = {
            "type": "book_depth",
            "product_id": 4,
            "bids": [
                ["3000000000000000000000", "1000000000000000000"],  # 3000 x 1
                ["2999000000000000000000", "2000000000000000000"],  # 2999 x 2
            ],
            "asks": [
                ["3001000000000000000000", "1000000000000000000"],  # 3001 x 1
                ["3002000000000000000000", "2000000000000000000"],  # 3002 x 2
            ]
        }

        await handler._on_bookdepth_message(message)

        # Check best bid
        best_bid_price, best_bid_qty = handler.get_best_bid()
        assert best_bid_price == Decimal("3000")
        assert best_bid_qty == Decimal("1")

        # Check best ask
        best_ask_price, best_ask_qty = handler.get_best_ask()
        assert best_ask_price == Decimal("3001")
        assert best_ask_qty == Decimal("1")

    @pytest.mark.asyncio
    async def test_process_bookdepth_incremental_delete(self, mock_websocket_client):
        """Test processing BookDepth message with delete (qty=0)."""
        client, _ = mock_websocket_client
        handler = BookDepthHandler(4, client)

        # Add levels
        message = {
            "type": "book_depth",
            "product_id": 4,
            "bids": [
                ["3000000000000000000000", "1000000000000000000"],
                ["2999000000000000000000", "2000000000000000000"],
            ],
            "asks": []
        }

        await handler._on_bookdepth_message(message)

        assert len(handler.bids) == 2

        # Delete one level
        message = {
            "type": "book_depth",
            "product_id": 4,
            "bids": [
                ["2999000000000000000000", "0"],  # Delete this level
            ],
            "asks": []
        }

        await handler._on_bookdepth_message(message)

        assert len(handler.bids) == 1
        assert Decimal("2999") not in handler.bids

    @pytest.mark.asyncio
    async def test_estimate_slippage(self, mock_websocket_client):
        """Test slippage estimation."""
        client, _ = mock_websocket_client
        handler = BookDepthHandler(4, client)

        # Create order book with depth
        message = {
            "type": "book_depth",
            "product_id": 4,
            "bids": [],
            "asks": [
                ["3000000000000000000000", "1000000000000000000"],  # 3000 x 1
                ["3001000000000000000000", "2000000000000000000"],  # 3001 x 2
                ["3002000000000000000000", "3000000000000000000"],  # 3002 x 3
            ]
        }

        await handler._on_bookdepth_message(message)

        # Buying 1 ETH should have minimal slippage
        slippage = handler.estimate_slippage("buy", Decimal("1"))
        assert slippage < Decimal("1")  # < 1 bps

        # Buying 4 ETH should have more slippage (goes 3 levels deep)
        slippage = handler.estimate_slippage("buy", Decimal("4"))
        assert slippage > Decimal("5")  # More slippage

    @pytest.mark.asyncio
    async def test_estimate_exit_capacity(self, mock_websocket_client):
        """Test estimating exit capacity."""
        client, _ = mock_websocket_client
        handler = BookDepthHandler(4, client)

        # Create order book
        message = {
            "type": "book_depth",
            "product_id": 4,
            "bids": [
                ["3000000000000000000000", "500000000000000000"],  # 3000 x 0.5
                ["2999000000000000000000", "1000000000000000000"],  # 2999 x 1
            ],
            "asks": []
        }

        await handler._on_bookdepth_message(message)

        # Selling 0.5 ETH should work (within slippage limit)
        can_exit, qty = handler.estimate_exit_capacity(
            Decimal("0.5"),  # 0.5 ETH position
            max_slippage_bps=20
        )
        assert can_exit
        assert qty == Decimal("0.5")

        # Selling 2 ETH should not work (insufficient liquidity)
        can_exit, qty = handler.estimate_exit_capacity(
            Decimal("2"),  # 2 ETH position
            max_slippage_bps=20
        )
        assert not can_exit
        assert qty < Decimal("2")
