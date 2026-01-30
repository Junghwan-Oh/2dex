"""
Nado WebSocket Client Implementation

This module provides WebSocket client for Nado streams:
- Public: BBO, BookDepth, Trade (no authentication required)
- Private: Fill, PositionChange, OrderUpdate (EIP-712 authentication required)

Note: Nado SDK does not provide WebSocket client, so this is custom implementation.
"""

import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, Any, Optional, Callable, AsyncIterator, List, Tuple

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None

# EIP-712 signing support
try:
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    ETH_ACCOUNT_AVAILABLE = True
except ImportError:
    ETH_ACCOUNT_AVAILABLE = False
    Account = None
    encode_typed_data = None


class ConnectionState:
    """WebSocket connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class NadoWebSocketClient:
    """
    WebSocket client for Nado public streams.

    This client connects to Nado's WebSocket endpoint and subscribes to
    public streams (BBO, BookDepth, Trade) without requiring authentication.
    """

    # WebSocket endpoint
    # Mainnet: wss://gateway.prod.nado.xyz/v1/subscribe
    # Testnet: wss://gateway.test.nado.xyz/v1/subscribe
    WS_URL = "wss://gateway.prod.nado.xyz/v1/subscribe"

    # Ping interval (Nado requires ping every 30 seconds)
    PING_INTERVAL = 25  # Send ping every 25 seconds (5 second buffer)

    # Reconnection settings
    RECONNECT_DELAY_BASE = 1.0  # Initial delay in seconds
    RECONNECT_DELAY_MAX = 30.0  # Maximum delay
    RECONNECT_ATTEMPTS = 5  # Max reconnection attempts before giving up

    # EIP-712 Domain for StreamAuthentication (from Nado SDK)
    EIP712_DOMAIN = {
        "name": "Nado",
        "version": "0.0.1",
        "chainId": 542210,
        "verifyingContract": "0x3646be143c3873771dbeee0758af4a44b19ef5a3"
    }

    # EIP-712 Types for StreamAuthentication (from Nado SDK)
    # expiration is uint64 (integer), not string
    EIP712_TYPES = {
        "StreamAuthentication": [
            {"name": "sender", "type": "bytes32"},
            {"name": "expiration", "type": "uint64"},
        ]
    }

    # Private streams that require authentication
    PRIVATE_STREAMS = {"fill", "position_change", "order_update", "liquidation", "funding_payment", "funding_rate", "latest_candlestick"}

    def __init__(
        self,
        product_ids: Optional[List[int]] = None,
        auto_reconnect: bool = True,
        logger: Optional[logging.Logger] = None,
        private_key: Optional[str] = None,
        owner: Optional[str] = None,
        subaccount_name: str = "default"
    ):
        """
        Initialize Nado WebSocket client.

        Args:
            product_ids: List of product IDs to subscribe to (default: [4, 8] for ETH, SOL)
            auto_reconnect: Whether to automatically reconnect on disconnect
            logger: Optional logger instance
            private_key: Private key for EIP-712 authentication (required for private streams)
            owner: Wallet address (owner) for subaccount calculation
            subaccount_name: Subaccount name (default: "default")
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets library is required. Install with: pip install websockets")

        self.product_ids = product_ids or [4, 8]  # Default to ETH and SOL
        self.auto_reconnect = auto_reconnect

        # Setup logger
        self.logger = logger or logging.getLogger(__name__)

        # Authentication credentials
        self._private_key = private_key
        self._owner = owner
        self._subaccount_name = subaccount_name
        self._authenticated = False

        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self._ws = None
        self._stop_event = asyncio.Event()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

        # Subscriptions
        self._subscriptions: Dict[int, List[str]] = {}  # product_id -> list of stream types
        self._message_callbacks: Dict[str, List[Callable]] = {}  # stream_type -> list of callbacks

        # Message queue
        self._message_queue: asyncio.Queue = asyncio.Queue()

    @property
    def state(self) -> str:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._state == ConnectionState.CONNECTED and self._ws is not None

    async def connect(self) -> None:
        """
        Connect to Nado WebSocket server.

        Raises:
            ConnectionError: If connection fails
        """
        if self._state == ConnectionState.CONNECTED:
            self.logger.warning("Already connected")
            return

        self._state = ConnectionState.CONNECTING
        self.logger.info(f"Connecting to Nado WebSocket: {self.WS_URL}")

        try:
            self._ws = await websockets.connect(
                self.WS_URL,
                ping_interval=self.PING_INTERVAL,
                ping_timeout=10,
                close_timeout=10
            )

            self._state = ConnectionState.CONNECTED
            self.logger.info("Connected to Nado WebSocket")

            # Start message handler task
            asyncio.create_task(self._handle_messages())

            # Start ping task
            if self._ping_task is None or self._ping_task.done():
                self._ping_task = asyncio.create_task(self._ping_loop())

            # Resubscribe to all streams after reconnection
            if self._subscriptions:
                await self._resubscribe_all()

        except Exception as e:
            self._state = ConnectionState.FAILED
            self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"WebSocket connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Nado WebSocket server."""
        self._stop_event.set()

        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._state = ConnectionState.DISCONNECTED
        self.logger.info("Disconnected from Nado WebSocket")

    async def authenticate(self) -> None:
        """
        Authenticate WebSocket connection using EIP-712 signature.

        This is required for subscribing to private streams (fill, position_change, order_update).

        Raises:
            ValueError: If private_key or owner is not set
            ImportError: If eth-account is not available
        """
        if not ETH_ACCOUNT_AVAILABLE:
            raise ImportError("eth-account library is required for authentication. Install with: pip install eth-account")

        if not self._private_key:
            raise ValueError("private_key is required for authentication")
        if not self._owner:
            raise ValueError("owner is required for authentication")

        # Import nado_protocol utilities for subaccount conversion
        try:
            from nado_protocol.utils.bytes32 import subaccount_to_hex
            from nado_protocol.utils.subaccount import SubaccountParams
        except ImportError:
            raise ImportError("nado-protocol library is required for subaccount calculation")

        # Calculate subaccount bytes32
        subaccount_params = SubaccountParams(
            subaccount_owner=self._owner,
            subaccount_name=self._subaccount_name,
        )
        subaccount_hex = subaccount_to_hex(subaccount_params)

        # Calculate expiration (current time + 60 seconds, max 100s ahead)
        import time
        expiration = int(time.time() * 1000) + 60000  # 60 seconds from now

        # Create the message to sign (expiration as uint64 per Nado SDK)
        message_to_sign = {
            "sender": subaccount_hex,
            "expiration": expiration  # uint64 (integer) per Nado SDK
        }

        # Sign using EIP-712
        encoded_message = encode_typed_data(
            domain_data=self.EIP712_DOMAIN,
            message_types=self.EIP712_TYPES,
            message_data=message_to_sign
        )

        signed_message = Account.from_key(self._private_key).sign_message(encoded_message)

        # Build authentication message (expiration as integer per Nado SDK)
        auth_msg = {
            "method": "authenticate",
            "tx": {
                "sender": subaccount_hex,
                "expiration": expiration  # uint64 integer
            },
            "signature": signed_message.signature.hex(),
            "id": int(time.time() * 1000) % 1000000
        }

        # Send authentication message
        await self._ws.send(json.dumps(auth_msg))

        self._authenticated = True
        self.logger.info(f"WebSocket authenticated for subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}")

    async def subscribe(
        self,
        stream_type: str,
        product_id: int,
        callback: Optional[Callable[[Dict], None]] = None,
        subaccount: Optional[str] = None
    ) -> None:
        """
        Subscribe to a stream.

        Args:
            stream_type: Stream type ("best_bid_offer", "book_depth", "trade", "fill", "position_change")
            product_id: Product ID (4 for ETH, 8 for SOL)
            callback: Optional callback function for stream messages
            subaccount: Optional subaccount hex string (required for fill/position_change streams)

        Raises:
            ValueError: If stream_type is invalid
            ConnectionError: If not connected
        """
        # All stream types (public + private)
        valid_streams = ["best_bid_offer", "book_depth", "trade", "fill", "position_change", "order_update", "liquidation", "latest_candlestick", "funding_payment", "funding_rate"]

        if stream_type not in valid_streams:
            raise ValueError(f"Invalid stream_type: {stream_type}. Must be one of {valid_streams}")

        # Check subaccount requirement for private streams
        private_streams = ["fill", "position_change", "order_update"]
        if stream_type in private_streams and not subaccount:
            raise ValueError(f"subaccount parameter required for '{stream_type}' stream")

        if not self.is_connected:
            await self.connect()

        # Register callback
        if callback:
            if stream_type not in self._message_callbacks:
                self._message_callbacks[stream_type] = []
            self._message_callbacks[stream_type].append(callback)

        # Build subscription message
        stream_def = {
            "type": stream_type,
            "product_id": product_id
        }

        # Add subaccount for private streams
        if subaccount:
            stream_def["subaccount"] = subaccount

        subscribe_msg = {
            "method": "subscribe",
            "stream": stream_def,
            "id": int(time.time() * 1000) % 1000000
        }

        await self._ws.send(json.dumps(subscribe_msg))

        # Track subscription (with subaccount info if applicable)
        if product_id not in self._subscriptions:
            self._subscriptions[product_id] = []

        sub_info = {"type": stream_type}
        if subaccount:
            sub_info["subaccount"] = subaccount

        # Check if already subscribed
        already_subscribed = any(
            s.get("type") == stream_type and s.get("subaccount") == subaccount
            for s in self._subscriptions[product_id]
        )

        if not already_subscribed:
            self._subscriptions[product_id].append(sub_info)

        self.logger.info(f"Subscribed to {stream_type} for product_id={product_id}")

    async def unsubscribe(self, stream_type: str, product_id: int) -> None:
        """
        Unsubscribe from a stream.

        Args:
            stream_type: Stream type
            product_id: Product ID
        """
        unsubscribe_msg = {
            "method": "unsubscribe",
            "stream": {
                "type": stream_type,
                "product_id": product_id
            },
            "id": int(time.time() * 1000) % 1000000  # subscribe/unsubscribe use int id
        }

        await self._ws.send(json.dumps(unsubscribe_msg))

        # Remove from tracking
        if product_id in self._subscriptions and stream_type in self._subscriptions[product_id]:
            self._subscriptions[product_id].remove(stream_type)

        self.logger.info(f"Unsubscribed from {stream_type} for product_id={product_id}")

    async def _resubscribe_all(self) -> None:
        """Resubscribe to all previously subscribed streams."""
        for product_id, stream_types in self._subscriptions.items():
            for stream_type in stream_types:
                subscribe_msg = {
                    "method": "subscribe",
                    "stream": {
                        "type": stream_type,
                        "product_id": product_id
                    },
                    "id": int(time.time() * 1000) % 1000000  # subscribe/unsubscribe use int id
                }
                await self._ws.send(json.dumps(subscribe_msg))
                self.logger.info(f"Resubscribed to {stream_type} for product_id={product_id}")

    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
            self._state = ConnectionState.DISCONNECTED
            self._ws = None

            # Auto-reconnect if enabled
            if self.auto_reconnect and not self._stop_event.is_set():
                await self._reconnect()

    async def _process_message(self, data: Dict[str, Any]) -> None:
        """
        Process incoming WebSocket message.

        Args:
            data: Parsed JSON message
        """
        # Check if this is a response (has "id" field)
        if "id" in data:
            # This is a response to subscribe/unsubscribe/list
            if "error" in data and data["error"]:
                self.logger.error(f"WebSocket error response: {data['error']}")
            return

        # Check if this is a stream message (has "type" field)
        message_type = data.get("type")
        if message_type:
            # Add to message queue
            await self._message_queue.put(data)

            # Call registered callbacks
            if message_type in self._message_callbacks:
                for callback in self._message_callbacks[message_type]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        self.logger.error(f"Error in callback for {message_type}: {e}")

    async def _ping_loop(self) -> None:
        """Send periodic ping frames to keep connection alive."""
        while not self._stop_event.is_set() and self.is_connected:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if self._ws and not self._ws.closed:
                    # websockets library handles ping automatically
                    # But we can send a custom ping if needed
                    pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in ping loop: {e}")

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        delay = self.RECONNECT_DELAY_BASE
        attempt = 0

        while attempt < self.RECONNECT_ATTEMPTS and not self._stop_event.is_set():
            attempt += 1
            self.logger.info(f"Reconnection attempt {attempt}/{self.RECONNECT_ATTEMPTS}")

            try:
                await asyncio.sleep(delay)
                await self.connect()
                return  # Success

            except Exception as e:
                self.logger.warning(f"Reconnection attempt {attempt} failed: {e}")
                delay = min(delay * 2, self.RECONNECT_DELAY_MAX)

        self._state = ConnectionState.FAILED
        self.logger.error("Failed to reconnect after maximum attempts")

    async def messages(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Iterate over incoming messages.

        Yields:
            Parsed message dictionaries
        """
        while not self._stop_event.is_set():
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue

    def register_callback(self, stream_type: str, callback: Callable[[Dict], None]) -> None:
        """
        Register a callback for a specific stream type.

        Args:
            stream_type: Stream type ("best_bid_offer", "book_depth", "trade")
            callback: Callback function (can be sync or async)
        """
        if stream_type not in self._message_callbacks:
            self._message_callbacks[stream_type] = []
        self._message_callbacks[stream_type].append(callback)
