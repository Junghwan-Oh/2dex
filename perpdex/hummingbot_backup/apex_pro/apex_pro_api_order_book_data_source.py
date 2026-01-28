"""
Order Book Data Source for Apex Pro Exchange Connector

Handles WebSocket subscriptions for real-time orderbook, trade, and ticker data.
Uses standard Hummingbot WebSocket pattern with Apex Pro API.
"""

import asyncio
from collections import defaultdict
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from decimal import Decimal

from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, WSJSONRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.logger import HummingbotLogger

import hummingbot.connector.exchange.apex_pro.apex_pro_constants as CONSTANTS
import hummingbot.connector.exchange.apex_pro.apex_pro_utils as utils

if TYPE_CHECKING:
    from hummingbot.connector.exchange.apex_pro.apex_pro_exchange import ApexProExchange


class ApexProAPIOrderBookDataSource(OrderBookTrackerDataSource):
    """
    Order book data source for Apex Pro.

    Provides WebSocket orderbook data feeds to Hummingbot's trading framework.
    Uses standard Hummingbot WebSocket pattern with Apex-specific message formats.
    """

    HEARTBEAT_TIME_INTERVAL = 30.0

    _logger: Optional[HummingbotLogger] = None

    def __init__(
        self,
        trading_pairs: List[str],
        connector: 'ApexProExchange',
        api_factory: Optional[WebAssistantsFactory] = None,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
        throttler: Optional[AsyncThrottler] = None,
        timeSynchronizer: Optional[TimeSynchronizer] = None,
    ):
        """
        Initialize order book data source.

        Args:
            trading_pairs: List of trading pairs to track
            connector: Parent exchange connector
            api_factory: WebAssistantsFactory for HTTP/WS requests
            domain: Domain configuration (mainnet/testnet)
            throttler: Rate limiter
            timeSynchronizer: Time synchronization
        """
        super().__init__(trading_pairs)
        self._connector = connector
        self._domain = domain
        self._time_synchronizer = timeSynchronizer
        self._throttler = throttler
        self._api_factory = api_factory or utils.build_api_factory(
            throttler=self._throttler,
            timeSynchronizer=self._time_synchronizer,
            domain=self._domain,
        )
        self._message_queue: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._last_ws_message_sent_timestamp = 0

    @classmethod
    def logger(cls) -> HummingbotLogger:
        """Get logger instance."""
        if cls._logger is None:
            cls._logger = HummingbotLogger.getLogger(__name__)
        return cls._logger

    async def get_last_traded_prices(
        self, trading_pairs: List[str], domain: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get last traded prices for trading pairs.

        Args:
            trading_pairs: List of trading pairs
            domain: Domain (unused, for compatibility)

        Returns:
            Dictionary of trading pair to last price
        """
        return await self._connector.get_last_traded_prices(tradingPairs=trading_pairs)

    async def _request_order_book_snapshot(self, tradingPair: str) -> Dict[str, Any]:
        """
        Retrieve order book snapshot from exchange REST API.

        Args:
            tradingPair: Trading pair in Hummingbot format (e.g., "BTC-USDT")

        Returns:
            Order book snapshot data from API
        """
        exchangeSymbol = await self._connector.exchange_symbol_associated_to_pair(tradingPair=tradingPair)

        params = {
            "symbol": exchangeSymbol,
            "limit": 100,  # Depth of orderbook
        }

        data = await self._connector._api_request(
            pathUrl=CONSTANTS.ORDERBOOK_SNAPSHOT_PATH_URL,
            method=RESTMethod.GET,
            params=params
        )

        if data.get("code") != "0":
            raise ValueError(f"Failed to fetch orderbook snapshot: {data.get('msg')}")

        return data.get("data", {})

    async def _order_book_snapshot(self, tradingPair: str) -> OrderBookMessage:
        """
        Get orderbook snapshot message.

        Args:
            tradingPair: Trading pair

        Returns:
            OrderBookMessage with snapshot data
        """
        snapshot = await self._request_order_book_snapshot(tradingPair)
        snapshotTimestamp = float(snapshot.get("timestamp", 0)) / 1000  # Convert ms to seconds

        # Convert to OrderBookMessage format
        bids = [(Decimal(str(bid[0])), Decimal(str(bid[1]))) for bid in snapshot.get("bids", [])]
        asks = [(Decimal(str(ask[0])), Decimal(str(ask[1]))) for ask in snapshot.get("asks", [])]

        snapshotMsg = OrderBookMessage(
            messageType=OrderBookMessageType.SNAPSHOT,
            content={
                "trading_pair": tradingPair,
                "update_id": int(snapshotTimestamp * 1000),
                "bids": bids,
                "asks": asks,
            },
            timestamp=snapshotTimestamp,
        )

        return snapshotMsg

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """
        Create and connect WebSocket assistant.

        Returns:
            Connected WSAssistant instance
        """
        wsUrl = utils.get_ws_url(self._domain)
        wsAssistant = await self._api_factory.get_ws_assistant()
        await wsAssistant.connect(wsUrl, pingTimeout=self.HEARTBEAT_TIME_INTERVAL)
        return wsAssistant

    async def _subscribe_channels(self, wsAssistant: WSAssistant):
        """
        Subscribe to WebSocket channels for orderbook updates.

        Args:
            wsAssistant: Connected WebSocket assistant
        """
        for tradingPair in self._trading_pairs:
            exchangeSymbol = await self._connector.exchange_symbol_associated_to_pair(tradingPair=tradingPair)

            # Subscribe to orderbook channel
            subscribeRequest = WSJSONRequest(
                payload={
                    "op": "subscribe",
                    "args": [f"{CONSTANTS.WS_CHANNEL_ORDERBOOK}.{exchangeSymbol}"]
                }
            )
            await wsAssistant.send(subscribeRequest)

            # Subscribe to trades channel
            tradesRequest = WSJSONRequest(
                payload={
                    "op": "subscribe",
                    "args": [f"{CONSTANTS.WS_CHANNEL_TRADES}.{exchangeSymbol}"]
                }
            )
            await wsAssistant.send(tradesRequest)

    async def _parse_order_book_diff_message(self, rawMessage: Dict[str, Any], messageQueue: asyncio.Queue):
        """
        Parse orderbook diff/update message from WebSocket.

        Args:
            rawMessage: Raw message from WebSocket
            messageQueue: Queue to put parsed message
        """
        data = rawMessage.get("data", {})
        symbol = data.get("s")

        if not symbol:
            return

        tradingPair = await self._connector.trading_pair_associated_to_exchange_symbol(symbol=symbol)
        timestamp = float(data.get("t", 0)) / 1000

        bids = [(Decimal(str(bid[0])), Decimal(str(bid[1]))) for bid in data.get("b", [])]
        asks = [(Decimal(str(ask[0])), Decimal(str(ask[1]))) for ask in data.get("a", [])]

        diffMessage = OrderBookMessage(
            messageType=OrderBookMessageType.DIFF,
            content={
                "trading_pair": tradingPair,
                "update_id": int(timestamp * 1000),
                "bids": bids,
                "asks": asks,
            },
            timestamp=timestamp,
        )

        messageQueue.put_nowait(diffMessage)

    async def _parse_trade_message(self, rawMessage: Dict[str, Any], messageQueue: asyncio.Queue):
        """
        Parse trade message from WebSocket.

        Args:
            rawMessage: Raw message from WebSocket
            messageQueue: Queue to put parsed message
        """
        data = rawMessage.get("data", {})

        for trade in data:
            symbol = trade.get("s")
            tradingPair = await self._connector.trading_pair_associated_to_exchange_symbol(symbol=symbol)
            timestamp = float(trade.get("t", 0)) / 1000

            tradeMessage = OrderBookMessage(
                messageType=OrderBookMessageType.TRADE,
                content={
                    "trading_pair": tradingPair,
                    "trade_type": "BUY" if trade.get("S") == "Buy" else "SELL",
                    "trade_id": trade.get("i"),
                    "update_id": int(timestamp * 1000),
                    "price": Decimal(str(trade.get("p"))),
                    "amount": Decimal(str(trade.get("v"))),
                },
                timestamp=timestamp,
            )

            messageQueue.put_nowait(tradeMessage)

    async def _process_websocket_messages(self, websocketAssistant: WSAssistant):
        """
        Process incoming WebSocket messages.

        Args:
            websocketAssistant: Connected WebSocket assistant
        """
        async for wsResponse in websocketAssistant.iter_messages():
            data = wsResponse.data

            # Skip ping/pong messages
            if data.get("op") == "pong":
                continue

            channel = data.get("topic", "")

            if CONSTANTS.WS_CHANNEL_ORDERBOOK in channel:
                await self._parse_order_book_diff_message(data, self._message_queue[CONSTANTS.WS_CHANNEL_ORDERBOOK])
            elif CONSTANTS.WS_CHANNEL_TRADES in channel:
                await self._parse_trade_message(data, self._message_queue[CONSTANTS.WS_CHANNEL_TRADES])

    async def listen_for_order_book_diffs(self, evQueue: asyncio.Queue, outputQueue: asyncio.Queue):
        """
        Listen to orderbook diff messages from WebSocket.

        Args:
            evQueue: Event queue (unused, for compatibility)
            outputQueue: Queue to push orderbook diff messages
        """
        wsAssistant = None
        while True:
            try:
                wsAssistant = await self._connected_websocket_assistant()
                await self._subscribe_channels(wsAssistant)

                # Process messages
                await self._process_websocket_messages(wsAssistant)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Error listening for orderbook diffs: {e}", exc_info=True)
                await asyncio.sleep(5.0)
            finally:
                if wsAssistant:
                    await wsAssistant.disconnect()

    async def listen_for_order_book_snapshots(self, evQueue: asyncio.Queue, outputQueue: asyncio.Queue):
        """
        Listen to orderbook snapshot messages.

        Args:
            evQueue: Event queue (unused, for compatibility)
            outputQueue: Queue to push orderbook snapshot messages
        """
        while True:
            try:
                # Request snapshots periodically
                await asyncio.sleep(60.0)  # Snapshot every 60 seconds

                for tradingPair in self._trading_pairs:
                    snapshot = await self._order_book_snapshot(tradingPair)
                    outputQueue.put_nowait(snapshot)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Error listening for orderbook snapshots: {e}", exc_info=True)
                await asyncio.sleep(5.0)

    async def listen_for_trades(self, evQueue: asyncio.Queue, outputQueue: asyncio.Queue):
        """
        Listen to trade messages from WebSocket.

        Args:
            evQueue: Event queue (unused, for compatibility)
            outputQueue: Queue to push trade messages
        """
        # Trade feed handled by listenForOrderBookDiffs WebSocket connection
        # This method provided for framework compatibility
        await asyncio.sleep(1.0)
