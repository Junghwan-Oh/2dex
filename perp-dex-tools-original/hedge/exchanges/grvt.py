"""
GRVT exchange client implementation.
"""

import os
import asyncio
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from pysdk.grvt_ccxt import GrvtCcxt
from pysdk.grvt_ccxt_ws import GrvtCcxtWS
from pysdk.grvt_ccxt_env import GrvtEnv, GrvtWSEndpointType

from .base import BaseExchangeClient, OrderResult, OrderInfo, query_retry
from helpers.logger import TradingLogger


def calculate_timeout(quantity: Decimal) -> int:
    """Calculate timeout based on order size with realistic microstructure awareness.

    Piecewise logic for predictable timeout values:
    - 0.1 ETH → 5s (quick fills at BBO)
    - 0.5 ETH → 10s (moderate spread)
    - 1.0 ETH → 20s (must look deeper)

    Args:
        quantity: Order quantity in ETH

    Returns:
        Timeout in seconds (5-20 second range)

    Example:
        >>> calculate_timeout(Decimal('0.1'))
        5
        >>> calculate_timeout(Decimal('0.5'))
        10
        >>> calculate_timeout(Decimal('1.0'))
        20
    """
    quantity_float = float(quantity)

    if quantity_float <= 0.1:
        return 5
    elif quantity_float <= 0.5:
        return 10
    else:
        return 20


def extract_filled_quantity(order_result: dict) -> Decimal:
    """Extract filled quantity from order result.

    Handles various order result formats:
    - dict with 'state/traded_size'
    - dict with 'size'
    - list/tuple format [price, size]
    - dict with 'metadata' (market orders return 0)

    Args:
        order_result: Order result from REST or WebSocket API

    Returns:
        Filled quantity as Decimal, or 0 if extraction fails
    """
    try:
        # Try direct key access first
        if 'state' in order_result and 'traded_size' in order_result['state']:
            return Decimal(order_result['state']['traded_size'])

        # Try metadata access (WebSocket format - market orders don't have metadata)
        if 'metadata' in order_result:
            return Decimal('0')

        # Try list format [price, size]
        if isinstance(order_result, (list, tuple)) and len(order_result) >= 2:
            return Decimal(order_result[1])

        # Try dict format {'price': ..., 'size': ...}
        if isinstance(order_result, dict):
            if 'size' in order_result:
                return Decimal(order_result['size'])
            if 'traded_size' in order_result:
                return Decimal(order_result['traded_size'])

        return Decimal('0')

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return Decimal('0')


def calculate_slippage_bps(execution_price: Decimal, reference_price: Decimal) -> Decimal:
    """Calculate slippage in basis points.

    Basis point (bps) = 0.01%, where 100 bps = 1%

    Args:
        execution_price: Actual execution price
        reference_price: Reference price (BBO midpoint or expected price)

    Returns:
        Slippage in basis points (1 bps = 0.01%)
    """
    if reference_price <= 0:
        return Decimal('0')

    slippage = abs(execution_price - reference_price) / reference_price * 10000
    return Decimal(str(slippage))


class GrvtClient(BaseExchangeClient):
    """GRVT exchange client implementation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize GRVT client."""
        super().__init__(config)

        # GRVT credentials from environment
        self.trading_account_id = os.getenv("GRVT_TRADING_ACCOUNT_ID")
        self.private_key = os.getenv("GRVT_PRIVATE_KEY")
        self.api_key = os.getenv("GRVT_API_KEY")
        self.environment = os.getenv("GRVT_ENVIRONMENT", "prod")

        if not self.trading_account_id or not self.private_key or not self.api_key:
            raise ValueError(
                "GRVT_TRADING_ACCOUNT_ID, GRVT_PRIVATE_KEY, and GRVT_API_KEY must be set in environment variables"
            )

        # Convert environment string to proper enum
        env_map = {
            "prod": GrvtEnv.PROD,
            "testnet": GrvtEnv.TESTNET,
            "staging": GrvtEnv.STAGING,
            "dev": GrvtEnv.DEV,
        }
        self.env = env_map.get(self.environment.lower(), GrvtEnv.PROD)

        # Initialize logger
        self.logger = TradingLogger(
            exchange="grvt", ticker=self.config.ticker, log_to_console=True
        )

        # Initialize GRVT clients
        self._initialize_grvt_clients()

        self._order_update_handler = None
        self._ws_client = None
        self._order_update_callback = None
        self._local_position = Decimal("0")  # Local position tracking via WebSocket
        self._last_sync_time = 0  # Last REST API position sync time
        self._sync_interval = 1  # Sync with REST API every cycle (reduced from 3 for better accuracy)

    def _initialize_grvt_clients(self) -> None:
        """Initialize the GRVT REST and WebSocket clients."""
        try:
            # Parameters for GRVT SDK
            parameters = {
                "trading_account_id": self.trading_account_id,
                "private_key": self.private_key,
                "api_key": self.api_key,
            }

            # Initialize REST client
            self.rest_client = GrvtCcxt(env=self.env, parameters=parameters)

        except Exception as e:
            raise ValueError(f"Failed to initialize GRVT client: {e}")

    async def _verify_order_status(
        self,
        symbol: str,
        client_order_id: str,
        timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """Verify order status via REST API.

        After sending RPC request, use REST API to verify order execution.

        Args:
            symbol: Trading pair
            client_order_id: Client order ID from RPC payload
            timeout: Seconds to wait for order to fill (default: 10s)

        Returns:
            Order status dict or None if timeout/failed
        """
        if not self.rest_client:
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Query order status via REST API using correct client_order_id
                order_info = self.rest_client.fetch_order(params={"client_order_id": client_order_id})

                if order_info:
                    status = order_info.get('state', {}).get('status', 'UNKNOWN')
                    self.logger.log(
                        f"[ORDER_VERIFICATION] Order {client_order_id} status: {status}",
                        "DEBUG"
                    )

                    if status in ["FILLED", "CANCELLED", "REJECTED"]:
                        return order_info
                    elif status in ["OPEN", "PENDING"]:
                        await asyncio.sleep(0.1)  # Check every 100ms
                        continue
                    else:
                        return order_info  # UNKNOWN status

            except Exception as e:
                self.logger.log(f"[ORDER_VERIFICATION] Error: {e}", "WARNING")
                await asyncio.sleep(0.1)

        # Timeout
        self.logger.log(
            f"[ORDER_VERIFICATION] Order {client_order_id} timeout after {timeout}s",
            "WARNING"
        )
        return None

    async def _ws_rpc_submit_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: Decimal,
        price: Optional[Decimal] = None,
        params: Dict[str, Any] = None,
        verify_with_rest: bool = True
    ) -> Dict[str, Any]:
        """Submit order via WebSocket RPC with REST verification.

        Uses RPC for order submission and REST API for verification.

        Args:
            symbol: Trading pair
            order_type: 'market' or 'limit'
            side: 'buy' or 'sell'
            amount: Order quantity
            price: Limit price (required for limit orders)
            params: Additional order parameters (can include client_order_id)
            verify_with_rest: Whether to verify order status via REST (default: True)

        Returns:
            Standard order result dict with keys:
            - 'success': bool
            - 'order_id': str or None (client order ID)
            - 'status': str or None
            - 'error': str or None
        """
        if not self._ws_client:
            self.logger.log("[WS_RPC] WebSocket client not available, using REST fallback", "WARNING")
            return self.rest_client.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )

        # Map order types
        grpc_order_type = "limit" if order_type == "limit" else "market"
        grpc_side = "buy" if side == "buy" else "sell"

        # Prepare parameters
        rpc_params = params.copy() if params else {}

        try:
            # Send RPC request with 10-second timeout
            self.logger.log(
                f"[WS_RPC] Submitting {order_type.upper()} order via WebSocket: {side} {amount} @ {price}",
                "INFO"
            )

            # For market orders, use rpc_create_order with order_type="market"
            # For limit orders, use rpc_create_limit_order (which internally passes "limit")
            if order_type == "market":
                result = await asyncio.wait_for(
                    self._ws_client.rpc_create_order(
                        symbol=symbol,
                        order_type="market",
                        side=grpc_side,
                        amount=float(amount),
                        price=None,  # Market orders don't need price
                        params=rpc_params
                    ),
                    timeout=10.0
                )
            else:
                # Limit order - use rpc_create_limit_order
                result = await asyncio.wait_for(
                    self._ws_client.rpc_create_limit_order(
                        symbol=symbol,
                        side=grpc_side,
                        amount=float(amount),
                        price=float(price),
                        params=rpc_params
                    ),
                    timeout=10.0
                )

            # CORRECT: Extract client_order_id from payload structure
            # Payload format: {'params': {'order': {'metadata': {'client_order_id': '123'}}}}
            client_order_id = str(result.get('params', {}).get('order', {}).get('metadata', {}).get('client_order_id', ''))

            self.logger.log(
                f"[WS_RPC] RPC request sent with client_order_id: {client_order_id}",
                "INFO"
            )

            # Verify order status via REST API (if enabled)
            if verify_with_rest:
                self.logger.log(
                    f"[WS_RPC] Verifying order status via REST API...",
                    "DEBUG"
                )

                order_info = await self._verify_order_status(
                    symbol=symbol,
                    client_order_id=client_order_id,
                    timeout=10.0
                )

                if not order_info:
                    self.logger.log(
                        f"[WS_RPC] Order verification failed (timeout or error)",
                        "WARNING"
                    )
                    # Fall back to REST submission
                    if order_type == "market":
                        return self.rest_client.create_order(
                            symbol=symbol,
                            order_type="market",
                            side=side,
                            amount=amount
                        )
                    else:
                        return self.rest_client.create_limit_order(
                            symbol=symbol,
                            side=side,
                            amount=amount,
                            price=price,
                            params=params or {}
                        )

                # Get status from REST API response
                status = order_info.get('state', {}).get('status', 'OPEN')

                self.logger.log(
                    f"[WS_RPC] Order verification: {status}",
                    "INFO"
                )

                return {
                    'success': True,
                    'metadata': {'client_order_id': client_order_id},
                    'state': {'status': status},
                    'raw_rpc_response': result,
                    'raw_rest_response': order_info
                }

            # No verification - return immediately
            return {
                'success': True,
                'metadata': {'client_order_id': client_order_id},
                'state': {'status': 'PENDING'},
                'raw_rpc_response': result
            }

        except asyncio.TimeoutError:
            self.logger.log(
                f"[WS_RPC] WebSocket order timeout after 10s, falling back to REST",
                "WARNING"
            )
            # Fall back to REST
            if order_type == "market":
                return self.rest_client.create_order(
                    symbol=symbol,
                    order_type="market",
                    side=side,
                    amount=amount
                )
            else:
                return self.rest_client.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price,
                    params=params or {}
                )

        except Exception as e:
            self.logger.log(
                f"[WS_RPC] WebSocket RPC failed: {e}, falling back to REST",
                "ERROR"
            )
            # Fall back to REST
            if order_type == "market":
                return self.rest_client.create_order(
                    symbol=symbol,
                    order_type="market",
                    side=side,
                    amount=amount
                )
            else:
                return self.rest_client.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price,
                    params=params or {}
                )

    def _validate_config(self) -> None:
        """Validate GRVT configuration."""
        required_env_vars = [
            "GRVT_TRADING_ACCOUNT_ID",
            "GRVT_PRIVATE_KEY",
            "GRVT_API_KEY",
        ]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

    async def connect(self) -> None:
        """Connect to GRVT WebSocket."""
        try:
            # Initialize WebSocket client - match the working test implementation
            loop = asyncio.get_running_loop()

            # Import logger from pysdk like in the test file
            from pysdk.grvt_ccxt_logging_selector import logger

            # Parameters for GRVT SDK - match test file structure
            parameters = {
                "api_key": self.api_key,
                "trading_account_id": self.trading_account_id,
                "api_ws_version": "v1",
                "private_key": self.private_key,
            }

            self._ws_client = GrvtCcxtWS(
                env=self.env,
                loop=loop,
                logger=logger,  # Add logger parameter like in test file
                parameters=parameters,
            )

            # Initialize and connect
            await self._ws_client.initialize()
            await asyncio.sleep(2)  # Wait for connection to establish

            # If an order update callback was set before connect, subscribe now
            if self._order_update_callback is not None:
                asyncio.create_task(
                    self._subscribe_to_orders(self._order_update_callback)
                )
                self.logger.log(
                    f"Deferred subscription started for {self.config.contract_id}",
                    "INFO",
                )

        except Exception as e:
            self.logger.log(f"Error connecting to GRVT WebSocket: {e}", "ERROR")
            raise

    async def disconnect(self) -> None:
        """Disconnect from GRVT."""
        try:
            if self._ws_client:
                await self._ws_client.__aexit__()
        except Exception as e:
            self.logger.log(f"Error during GRVT disconnect: {e}", "ERROR")

    def trigger_websocket_reconnect(self) -> None:
        """Trigger SDK's built-in reconnect mechanism.

        The SDK's connect_all_channels() loop checks force_reconnect_flag
        every 5 seconds and will reconnect when this flag is set.
        """
        if self._ws_client and hasattr(self._ws_client, 'force_reconnect_flag'):
            self._ws_client.force_reconnect_flag = True
            self.logger.log(
                "[WS_RECONNECT] Triggered SDK reconnect (will execute within 5s)",
                "INFO"
            )
        else:
            self.logger.warning(
                "[WS_RECONNECT] Cannot trigger reconnect: _ws_client or force_reconnect_flag not available"
            )

    def get_ws_position(self) -> Decimal:
        """Get position from local WebSocket tracking.

        Improved: Periodically sync with REST API to ensure accuracy.
        Returns the locally tracked position, synced with REST API periodically.
        """
        # Note: This is a synchronous method, so we can't do async operations here.
        # The actual sync should be done from the main trading loop.
        return self._local_position

    async def sync_ws_position_if_needed(self, cycle_count: int) -> None:
        """Sync WebSocket position with REST API if needed.

        Args:
            cycle_count: Current cycle count for determining sync interval
        """
        # Sync every N cycles to ensure position accuracy
        if cycle_count > 0 and cycle_count % self._sync_interval == 0:
            try:
                rest_position = await self.get_account_positions()
                position_diff = abs(self._local_position - rest_position)

                if position_diff > Decimal("0.001"):  # More than 0.001 difference
                    self.logger.log(
                        f"[WS_SYNC] Syncing position: WS={self._local_position}, REST={rest_position}, diff={position_diff}",
                        "WARNING",
                    )
                    self._local_position = rest_position
            except Exception as e:
                self.logger.log(
                    f"[WS_SYNC] Failed to sync position: {e}",
                    "ERROR",
                )

    def get_exchange_name(self) -> str:
        """Get the exchange name."""
        return "grvt"

    def setup_order_update_handler(self, handler) -> None:
        """Setup order update handler for WebSocket."""
        self._order_update_handler = handler

        async def order_update_callback(message: Dict[str, Any]):
            """Handle order updates from WebSocket - match working test implementation."""
            # Log raw message for debugging
            self.logger.log(f"Received WebSocket message: {message}", "INFO")
            self.logger.log(
                "**************************************************", "INFO"
            )
            try:
                # Parse the message structure - match the working test implementation exactly
                if "feed" in message:
                    data = message.get("feed", {})
                    leg = data.get("legs", [])[0] if data.get("legs") else None

                    if isinstance(data, dict) and leg:
                        contract_id = leg.get("instrument", "")
                        if contract_id != self.config.contract_id:
                            self.logger.log(f"Skipping - contract mismatch: {contract_id} != {self.config.contract_id}", "INFO")
                            return

                        order_state = data.get("state", {})
                        # Extract order data using the exact structure from test
                        order_id = data.get("order_id", "")
                        status = order_state.get("status", "")
                        side = "buy" if leg.get("is_buying_asset") else "sell"
                        size = leg.get("size", "0")
                        price = leg.get("limit_price", "0")
                        filled_size = (
                            order_state.get("traded_size")[0]
                            if order_state.get("traded_size")
                            else "0"
                        )

                        self.logger.log(f"Processing order update: {order_id} status={status} side={side} filled={filled_size}", "INFO")

                        if Decimal(price) == 0:
                            price = data.get("state", {}).get("avg_fill_price", ["0"])[
                                0
                            ]

                        if order_id and status:
                            # Determine order type based on side
                            if side == self.config.close_order_side:
                                order_type = "CLOSE"
                            else:
                                order_type = "OPEN"

                            # Map GRVT status to our status
                            status_map = {
                                "OPEN": "OPEN",
                                "FILLED": "FILLED",
                                "CANCELLED": "CANCELED",
                                "REJECTED": "CANCELED",
                            }
                            mapped_status = status_map.get(status, status)

                            # Handle partially filled orders
                            if status == "OPEN" and Decimal(filled_size) > 0:
                                mapped_status = "PARTIALLY_FILLED"

                            if mapped_status in [
                                "OPEN",
                                "PARTIALLY_FILLED",
                                "FILLED",
                                "CANCELED",
                            ]:
                                # DISABLED: WebSocket position updates to avoid conflicts with REST API
                                # REST API is now the authoritative source (Mean Reversion style)
                                # Position updates are done in place_market_order() and sync_ws_position_if_needed()

                                # if mapped_status == "FILLED":
                                #     fill_qty = (
                                #         Decimal(filled_size)
                                #         if filled_size
                                #         else Decimal(size)
                                #     )
                                #     if side == "buy":
                                #         self._local_position += fill_qty
                                #     else:
                                #         self._local_position -= fill_qty
                                #     self.logger.log(
                                #         f"[WS_POSITION] Updated position: {self._local_position} (+{fill_qty} for {side})",
                                #         "INFO",
                                #     )

                                if self._order_update_handler:
                                    self._order_update_handler(
                                        {
                                            "order_id": order_id,
                                            "side": side,
                                            "order_type": order_type,
                                            "status": mapped_status,
                                            "size": size,
                                            "price": price,
                                            "contract_id": contract_id,
                                            "filled_size": filled_size,
                                        }
                                    )
                            else:
                                self.logger.log(
                                    f"Ignoring order update with status: {mapped_status}",
                                    "DEBUG",
                                )
                        else:
                            self.logger.log(
                                f"Order update missing order_id or status: {data}",
                                "DEBUG",
                            )
                    else:
                        self.logger.log(
                            f"Order update data is not dict or missing legs: {data}",
                            "DEBUG",
                        )
                else:
                    # Handle other message types (position, fill, etc.)
                    method = message.get("method", "unknown")
                    self.logger.log(f"Received non-order message: {method}", "DEBUG")

            except Exception as e:
                self.logger.log(f"Error handling order update: {e}", "ERROR")
                self.logger.log(f"Message that caused error: {message}", "ERROR")

        # Store callback for use after connect
        self._order_update_callback = order_update_callback

        # Subscribe immediately if WebSocket is already initialized; otherwise defer to connect()
        if self._ws_client:
            try:
                asyncio.create_task(
                    self._subscribe_to_orders(self._order_update_callback)
                )
                self.logger.log(
                    f"Successfully initiated subscription to order updates for {self.config.contract_id}",
                    "INFO",
                )
            except Exception as e:
                self.logger.log(f"Error subscribing to order updates: {e}", "ERROR")
                raise
        else:
            self.logger.log(
                "WebSocket not ready yet; will subscribe after connect()", "INFO"
            )

    async def _subscribe_to_orders(self, callback):
        """Subscribe to order updates asynchronously."""
        try:
            await self._ws_client.subscribe(
                stream="order",
                callback=callback,
                ws_end_point_type=GrvtWSEndpointType.TRADE_DATA_RPC_FULL,
                params={"instrument": self.config.contract_id},
            )
            await asyncio.sleep(0)  # Small delay like in test file
            self.logger.log(
                f"Successfully subscribed to order updates for {self.config.contract_id}",
                "INFO",
            )
        except Exception as e:
            self.logger.log(f"Error in subscription task: {e}", "ERROR")

    @query_retry(reraise=True)
    async def fetch_bbo_prices(self, contract_id: str) -> Tuple[Decimal, Decimal]:
        """Fetch best bid and offer prices for a contract."""
        # Get order book from GRVT
        order_book = self.rest_client.fetch_order_book(contract_id, limit=10)

        if not order_book or "bids" not in order_book or "asks" not in order_book:
            raise ValueError(f"Unable to get order book: {order_book}")

        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])

        best_bid = Decimal(bids[0]["price"]) if bids and len(bids) > 0 else Decimal(0)
        best_ask = Decimal(asks[0]["price"]) if asks and len(asks) > 0 else Decimal(0)

        return best_bid, best_ask

    async def fetch_bbo(self, symbol: str) -> dict:
        """Fetch Best Bid/Ask prices with detailed information.

        Returns dict format with all BBO details for smart routing.
        This is a NEW method - existing fetch_bbo_prices() still returns Tuple[Decimal, Decimal].

        Args:
            symbol: Trading pair (uses existing contract_id format)

        Returns:
            {
                'best_bid_price': Decimal,
                'best_bid_size': Decimal,
                'best_ask_price': Decimal,
                'best_ask_size': Decimal,
                'spread': Decimal,
                'mid_price': Decimal
            }
        """
        ticker = await self.rest_client.fetch_ticker(symbol)

        # Verify required keys exist
        required_keys = ['best_bid_price', 'best_bid_size', 'best_ask_price', 'best_ask_size']
        for key in required_keys:
            if key not in ticker:
                raise ValueError(f"fetch_ticker() returned unexpected structure: {ticker}")

        best_bid = Decimal(ticker['best_bid_price'])
        best_bid_size = Decimal(ticker['best_bid_size'])
        best_ask = Decimal(ticker['best_ask_price'])
        best_ask_size = Decimal(ticker['best_ask_size'])

        return {
            'best_bid_price': best_bid,
            'best_bid_size': best_bid_size,
            'best_ask_price': best_ask,
            'best_ask_size': best_ask_size,
            'spread': best_ask - best_bid,
            'mid_price': (best_bid + best_ask) / 2
        }

    async def analyze_order_book_depth(
        self, symbol: str, side: str, depth_limit: int = 50
    ) -> dict:
        """Analyze order book depth at specific side.

        Args:
            symbol: Trading pair (uses existing contract_id format)
            side: 'buy' (check asks) or 'sell' (check bids)
            depth_limit: Number of levels (10, 50, 100, 500)

        Returns:
            {
                'top_price': Decimal,
                'top_size': Decimal,
                'cumulative_size': Decimal,
                'price_levels': [
                    {'price': Decimal, 'size': Decimal, 'cumulative': Decimal, 'position': int},
                    ...
                ]
            }

        Note: GRVT returns order book as dict with 'price', 'size', 'num_orders' keys
        """
        orderbook = await self.rest_client.fetch_order_book(symbol, limit=depth_limit)

        # GRVT format: {'bids': [{'price': '...', 'size': '...', ...}], 'asks': [...]}
        if side == 'buy':
            levels = orderbook['asks']
        else:
            levels = orderbook['bids']

        if not levels:
            raise ValueError(f"No {side} order book data available")

        price_levels = []
        cumulative = Decimal('0')

        for i, level in enumerate(levels):
            # GRVT uses dict format: {'price': str, 'size': str, 'num_orders': int}
            if isinstance(level, dict):
                price = Decimal(level['price'])
                size = Decimal(level['size'])
            else:
                raise ValueError(f"Unexpected order book format: {type(level)}")

            cumulative += size
            price_levels.append({
                'price': price,
                'size': size,
                'cumulative': cumulative,
                'position': i + 1
            })

        top = price_levels[0]

        return {
            'top_price': top['price'],
            'top_size': top['size'],
            'cumulative_size': top['cumulative'],
            'price_levels': price_levels,
            'total_levels_analyzed': len(price_levels)
        }

    async def find_hedge_price_with_liquidity(
        self, symbol: str, side: str, target_quantity: Decimal, max_slippage_bps: int = 5, depth_limit: int = 50
    ) -> tuple:
        """Find optimal price for hedge order with sufficient liquidity.

        Walks the order book to find price where cumulative size >= target.

        Args:
            symbol: Trading pair (uses existing contract_id format)
            side: 'buy' (look at asks) or 'sell' (look at bids)
            target_quantity: Size needed
            max_slippage_bps: Maximum acceptable slippage (default: 5)
            depth_limit: Order book levels to analyze

        Returns:
            (optimal_price, slippage_bps, levels_used)

        Raises:
            ValueError: If insufficient liquidity at max slippage
        """
        analysis = await self.analyze_order_book_depth(symbol, side, depth_limit)

        top_price = analysis['top_price']
        cumulative = analysis['top_size']
        price_levels = analysis['price_levels']

        # If top of book has enough liquidity, use it
        if cumulative >= target_quantity:
            return top_price, Decimal('0'), 1

        # Walk the order book
        worst_price = top_price
        for level in price_levels:
            worst_price = level['price']
            cumulative = level['cumulative']
            if cumulative >= target_quantity:
                break

        # Calculate slippage
        slippage = abs(worst_price - top_price) / top_price * 10000  # Basis points

        # Check against max slippage
        if slippage > max_slippage_bps:
            available = cumulative
            raise ValueError(
                f"Insufficient liquidity: need {target_quantity}, "
                f"available {available} at {max_slippage_bps} bps slippage, "
                f"worst price: {worst_price:.2f}, slippage: {slippage:.2f} bps"
            )

        return worst_price, slippage, analysis['total_levels_analyzed']

    async def place_post_only_order(
        self, contract_id: str, quantity: Decimal, price: Decimal, side: str
    ) -> OrderResult:
        """Place a post only order with GRVT using official SDK.

        v5: Use WebSocket RPC for order submission with REST fallback.
        """

        # Place the order using WebSocket RPC with REST verification
        order_result = await self._ws_rpc_submit_order(
            symbol=contract_id,
            order_type='limit',
            side=side,
            amount=quantity,
            price=price,
            params={
                "post_only": True,
                "order_duration_secs": 30 * 86400 - 1,
            },
            verify_with_rest=True
        )

        client_order_id = order_result.get("metadata").get("client_order_id")
        order_status = order_result.get("state").get("status")
        order_status_start_time = time.time()
        order_info = await self.get_order_info(client_order_id=client_order_id)
        if order_info is not None:
            order_status = order_info.status

        while (
            order_status in ["PENDING"] and time.time() - order_status_start_time < 10
        ):
            # Check order status after a short delay
            await asyncio.sleep(0.05)
            order_info = await self.get_order_info(client_order_id=client_order_id)
            if order_info is not None:
                order_status = order_info.status

        if order_status == "PENDING":
            raise Exception("GRVT Server Error: Order not processed after 10 seconds")
        else:
            # Track that this came from POST_ONLY for metrics
            order_info.from_post_only = True
            return order_info

    async def place_market_order(
        self, contract_id: str, quantity: Decimal, side: str
    ) -> OrderResult:
        """Place a market order with GRVT using official SDK.

        Improved: Wait for fill confirmation and return OrderResult.
        OMC v4: Enforce GRVT liquidity limit of 0.2 ETH based on testing.
        v5: Add REST client recovery on empty response.
        """
        # NOTE: Hard 0.2 ETH limit removed - using iterative market order approach instead
        # The place_iterative_market_order method handles large orders by:
        # 1. Consuming available liquidity at current price
        # 2. Retrying at 1-tick worse prices until filled
        # 3. This achieves higher fill rates for orders >0.2 ETH

        # Get current BBO for price reference
        best_bid, best_ask = await self.fetch_bbo_prices(contract_id)
        expected_price = best_ask if side == "buy" else best_bid

        # Place the order using WebSocket RPC method with REST verification
        order_result = await self._ws_rpc_submit_order(
            symbol=contract_id,
            order_type='market',
            side=side,
            amount=quantity,
            verify_with_rest=True
        )

        # Extract order info
        metadata = order_result.get("metadata", {})
        client_order_id = metadata.get("client_order_id")
        state = order_result.get("state", {})
        order_status = state.get("status", "UNKNOWN")

        self.logger.log(
            f"[MARKET] Order placed: {side.upper()} {quantity} @ ~{expected_price} (status: {order_status})",
            "INFO",
        )

        # Wait for fill confirmation
        start_time = time.time()
        timeout = 30  # 30 seconds timeout for market order

        while order_status in ["PENDING", "OPEN"] and time.time() - start_time < timeout:
            await asyncio.sleep(0.1)
            order_info = await self.get_order_info(client_order_id=client_order_id)
            if order_info:
                order_status = order_info.status
                if order_info.status == "FILLED":
                    # CRITICAL FIX: Update local position AFTER confirming with REST API
                    # This ensures _local_position matches the actual exchange position
                    try:
                        # Get actual position from REST API (authoritative source)
                        actual_position = await self.get_account_positions()
                        self._local_position = actual_position
                        self.logger.log(
                            f"[MARKET] Filled: {side.upper()} {quantity} @ {order_info.price} (pos: {self._local_position}, synced with REST API)",
                            "INFO",
                        )
                    except Exception as sync_error:
                        # Fallback to local calculation if REST API fails
                        if side == "buy":
                            self._local_position += quantity
                        else:
                            self._local_position -= quantity
                        self.logger.log(
                            f"[MARKET] Filled: {side.upper()} {quantity} @ {order_info.price} (pos: {self._local_position}, local calculation)",
                            "WARNING",
                        )
                    return OrderResult(
                        success=True,
                        order_id=order_info.order_id,
                        side=side,
                        size=quantity,
                        price=order_info.price,
                        status=order_info.status,
                        from_post_only=False  # MARKET orders always False
                    )

        # Check final status
        if order_status in ["FILLED", "PARTIALLY_FILLED"]:
            return OrderResult(
                success=True,
                order_id=client_order_id,
                side=side,
                size=quantity,
                price=expected_price,
                status=order_status,
                from_post_only=False  # MARKET orders always False
            )
        else:
            raise Exception(f"[MARKET] Order not filled within timeout. Final status: {order_status}")

    async def get_order_price(self, direction: str) -> Decimal:
        """Get the price of an order with GRVT using official SDK."""
        best_bid, best_ask = await self.fetch_bbo_prices(self.config.contract_id)
        if best_bid <= 0 or best_ask <= 0:
            raise ValueError("Invalid bid/ask prices")

        if direction == "buy":
            return best_ask - self.config.tick_size
        elif direction == "sell":
            return best_bid + self.config.tick_size
        else:
            raise ValueError("Invalid direction")

    async def place_open_order(
        self, contract_id: str, quantity: Decimal, direction: str
    ) -> OrderResult:
        """Place an open order with GRVT.

        Improved: Use aggressive limit orders for immediate fills.
        - Places orders at BBO for instant execution
        - Falls back to POST_ONLY if aggressive orders fail
        """
        attempt = 0
        while attempt < 15:
            attempt += 1
            if attempt % 5 == 0:
                self.logger.log(f"[OPEN] Attempt {attempt} to place order", "INFO")
                active_orders = await self.get_active_orders(contract_id)
                active_open_orders = 0
                for order in active_orders:
                    if order.side == self.config.direction:
                        active_open_orders += 1
                if active_open_orders > 1:
                    self.logger.log(
                        f"[OPEN] ERROR: Active open orders abnormal: {active_open_orders}",
                        "ERROR",
                    )
                    raise Exception(
                        f"[OPEN] ERROR: Active open orders abnormal: {active_open_orders}"
                    )

            # Get current market prices
            best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

            if best_bid <= 0 or best_ask <= 0:
                return OrderResult(
                    success=False, error_message="Invalid bid/ask prices"
                )

            # Determine order side and price (AGGRESSIVE for immediate fill)
            if direction == "buy":
                # Place at ASK to ensure immediate fill (cross the spread)
                order_price = best_ask
            elif direction == "sell":
                # Place at BID to ensure immediate fill (cross the spread)
                order_price = best_bid
            else:
                raise Exception(f"[OPEN] Invalid direction: {direction}")

            # Try aggressive limit order first (cross spread)
            try:
                self.logger.log(
                    f"[OPEN] Attempting aggressive order at {order_price} (BBO: {best_bid}/{best_ask})",
                    "INFO",
                )

                order_info = await self.place_post_only_order(
                    contract_id, quantity, order_price, direction
                )

                order_status = order_info.status
                order_id = order_info.order_id

                # If order was filled, we're done
                if order_status == "FILLED":
                    self.logger.log(
                        f"[OPEN] Aggressive order filled immediately at {order_price}",
                        "INFO",
                    )
                    return OrderResult(
                        success=True,
                        order_id=order_id,
                        side=direction,
                        size=quantity,
                        price=order_price,
                        status=order_status,
                    )
                # If order was accepted but not yet filled, wait a bit
                elif order_status == "OPEN":
                    # Wait up to 3 seconds for fill
                    await asyncio.sleep(3)
                    order_info = await self.get_order_info(order_id=order_id)
                    if order_info and order_info.status == "FILLED":
                        return OrderResult(
                            success=True,
                            order_id=order_id,
                            side=direction,
                            size=quantity,
                            price=order_price,
                            status="FILLED",
                        )
                    # Cancel and retry
                    await self.cancel_order(order_id)

            except Exception as e:
                self.logger.log(f"[OPEN] Error placing aggressive order: {e}", "ERROR")

            # Fallback: Try in-spread aggressive maker order
            try:
                if direction == "buy":
                    # Place 1 tick below best ask (aggressive bid in spread)
                    order_price = best_ask - self.config.tick_size
                elif direction == "sell":
                    # Place 1 tick above best bid (aggressive ask in spread)
                    order_price = best_bid + self.config.tick_size
                else:
                    raise Exception(f"[OPEN] Invalid direction: {direction}")

                self.logger.log(
                    f"[OPEN] Fallback: In-spread order at {order_price}",
                    "INFO",
                )

                order_info = await self.place_post_only_order(
                    contract_id, quantity, order_price, direction
                )
            except Exception as e:
                self.logger.log(f"[OPEN] Error placing fallback order: {e}", "ERROR")
                continue

            order_status = order_info.status
            order_id = order_info.order_id

            if order_status == "REJECTED":
                continue
            if order_status in ["OPEN", "FILLED"]:
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    side=direction,
                    size=quantity,
                    price=order_price,
                    status=order_status,
                )
            elif order_status == "PENDING":
                raise Exception("[OPEN] Order not processed after 10 seconds")
            else:
                raise Exception(f"[OPEN] Unexpected order status: {order_status}")

    async def place_close_order(
        self, contract_id: str, quantity: Decimal, price: Decimal, side: str
    ) -> OrderResult:
        """Place a close order with GRVT."""
        # Get current market prices
        attempt = 0
        active_close_orders = await self._get_active_close_orders(contract_id)
        while True:
            attempt += 1
            if attempt % 5 == 0:
                self.logger.log(f"[CLOSE] Attempt {attempt} to place order", "INFO")
                current_close_orders = await self._get_active_close_orders(contract_id)

                if current_close_orders - active_close_orders > 1:
                    self.logger.log(
                        f"[CLOSE] ERROR: Active close orders abnormal: "
                        f"{active_close_orders}, {current_close_orders}",
                        "ERROR",
                    )
                    raise Exception(
                        f"[CLOSE] ERROR: Active close orders abnormal: "
                        f"{active_close_orders}, {current_close_orders}"
                    )
                else:
                    active_close_orders = current_close_orders

            # Adjust price to ensure maker order
            best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

            if side == "sell" and price <= best_bid:
                adjusted_price = best_bid + self.config.tick_size
            elif side == "buy" and price >= best_ask:
                adjusted_price = best_ask - self.config.tick_size
            else:
                adjusted_price = price

            adjusted_price = self.round_to_tick(adjusted_price)
            try:
                order_info = await self.place_post_only_order(
                    contract_id, quantity, adjusted_price, side
                )
            except Exception as e:
                self.logger.log(f"[CLOSE] Error placing order: {e}", "ERROR")
                continue

            order_status = order_info.status
            order_id = order_info.order_id

            if order_status == "REJECTED":
                continue
            if order_status in ["OPEN", "FILLED"]:
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    side=side,
                    size=quantity,
                    price=adjusted_price,
                    status=order_status,
                )
            elif order_status == "PENDING":
                raise Exception("[CLOSE] Order not processed after 10 seconds")
            else:
                raise Exception(f"[CLOSE] Unexpected order status: {order_status}")


    async def place_iterative_market_order(
        self,
        contract_id: str,
        target_quantity: Decimal,
        side: str,
        max_iterations: int = 20,
        max_slippage_bps: int = 5,
        tick_size: int = 10,
    ) -> dict:
        """Place iterative market orders with smart liquidity routing.

        Strategy:
        1. Fetch BBO at start
        2. Place first chunk at BBO-1tick
        3. Re-fetch BBO at each iteration for fresh data
        4. Use cumulative depth to determine chunk sizes
        5. Monitor slippage and stop when filled or max iterations

        Args:
            contract_id: Trading pair (used as-is, no format conversion)
            target_quantity: Total quantity to fill
            side: 'buy' or 'sell'
            max_iterations: Maximum iterations (default: 20)
            max_slippage_bps: Maximum acceptable slippage (default: 5 bps)
            tick_size: GRVT tick size in cents (default: 10 for ETH = $0.10)

        Returns:
            Standard order result dict
        """
        remaining = target_quantity
        tick_offset = 0
        total_slippage_bps = Decimal('0')

        # Initial BBO analysis
        try:
            bbo = await self.fetch_bbo(contract_id)

            if side == 'buy':
                start_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
            else:
                start_price = bbo['best_bid_price'] + (Decimal(tick_size) * Decimal(tick_offset))

            self.logger.info(
                f"[SMART_ROUTING] Starting with {side} order at {start_price:.2f}, "
                f"target: {target_quantity}, BBO spread: {bbo['spread']:.2f}"
            )
        except Exception as e:
            self.logger.warning(
                f"[SMART_ROUTING] BBO fetch failed, using direct market order: {e}"
            )
            # Use old method as fallback
            import time
            start_time = time.time()
            total_filled = Decimal('0')
            iteration = 0

            while total_filled < target_quantity:
                iteration += 1
                if iteration > max_iterations:
                    break

                remaining = target_quantity - total_filled
                best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

                tick_size = Decimal("0.01")
                if side == "buy":
                    base_price = best_ask
                else:
                    base_price = best_bid

                adjusted_price = base_price + (tick_offset * tick_size) if side == "buy" else base_price - (tick_offset * tick_size)

                order_result = await self._ws_rpc_submit_order(
                    symbol=contract_id,
                    order_type='market',
                    side=side,
                    amount=remaining,
                    price=adjusted_price,
                    verify_with_rest=True
                )

                if not order_result:
                    tick_offset += 1
                    continue

                metadata = order_result.get("metadata", {})
                client_order_id = metadata.get("client_order_id")

                await asyncio.sleep(0.5)
                order_info = await self.get_order_info(client_order_id=client_order_id)

                if order_info and order_info.status == "FILLED":
                    filled_quantity = order_info.filled_size
                    total_filled += filled_quantity

                    if total_filled >= target_quantity:
                        self.logger.info(f"[ITERATIVE] SUCCESS: Filled {total_filled} ETH in {iteration} iterations")
                        return {
                            'total_filled': total_filled,
                            'total_fees': Decimal('0'),
                            'average_price': order_info.avg_fill_price if order_info.avg_fill_price else Decimal('0'),
                            'iterations': iteration,
                            'success': True
                        }

                    tick_offset += 1

            return {
                'total_filled': total_filled,
                'total_fees': Decimal('0'),
                'average_price': Decimal('0'),
                'iterations': iteration,
                'success': False,
                'reason': 'Max iterations exceeded (fallback)'
            }

        for iteration in range(1, max_iterations + 1):
            # Re-fetch BBO for fresh market data
            try:
                bbo = await self.fetch_bbo(contract_id)
            except Exception as e:
                self.logger.warning(f"[SMART_ROUTING] BBO re-fetch failed: {e}")

            # Calculate current price with tick offset
            if side == 'buy':
                current_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
            else:
                current_price = bbo['best_bid_price'] + (Decimal(tick_size) * Decimal(tick_offset))

            # Get current level size from BBO
            current_level_size = bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']

            # If current level has enough liquidity, use it directly
            if current_level_size >= remaining:
                self.logger.info(
                    f"[SMART_ROUTING] Iteration {iteration}: Placing {remaining} at "
                    f"{current_price:.2f} (BBO level {tick_offset})"
                )

                order_result = await self._ws_rpc_submit_order(
                    symbol=contract_id,
                    order_type='market',
                    side=side,
                    amount=remaining,
                    price=current_price,
                    verify_with_rest=True
                )

                if order_result.get('success'):
                    filled = extract_filled_quantity(order_result)
                    remaining -= filled

                    if remaining <= Decimal('0'):
                        self.logger.info(
                            f"[SMART_ROUTING] ✅ Fully filled in {iteration} iterations"
                        )
                        return order_result

                # If failed, increment tick offset and continue
                tick_offset += 1
                continue

            # Otherwise, use incremental chunking based on current level size
            chunk_size = current_level_size

            self.logger.info(
                f"[SMART_ROUTING] Iteration {iteration}: Placing chunk {chunk_size} at "
                f"{current_price:.2f} (BBO level {tick_offset}), remaining: {remaining}"
            )

            order_result = await self._ws_rpc_submit_order(
                symbol=contract_id,
                order_type='market',
                side=side,
                amount=chunk_size,
                price=current_price,
                verify_with_rest=True
            )

            if not order_result.get('success'):
                tick_offset += 1
                if tick_offset > max_iterations:
                    self.logger.error(
                        f"[SMART_ROUTING] ❌ Failed after {iteration} iterations"
                    )
                    return order_result
                continue

            # Extract filled quantity
            filled = extract_filled_quantity(order_result)
            remaining -= filled

            # Calculate slippage
            if iteration == 1:
                reference_price = bbo['best_ask_price'] if side == 'buy' else bbo['best_bid_price']
                total_slippage_bps = calculate_slippage_bps(current_price, reference_price)

            self.logger.debug(
                f"[SMART_ROUTING] Filled {filled}, remaining: {remaining}, "
                f"price: {current_price:.2f}, slippage: {total_slippage_bps:.2f} bps"
            )

            if remaining <= Decimal('0'):
                self.logger.info(
                    f"[SMART_ROUTING] ✅ Fully filled in {iteration} iterations, "
                    f"total slippage: {total_slippage_bps:.2f} bps"
                )
                return order_result

            # Increment tick offset and continue
            tick_offset += 1

        self.logger.error(
            f"[SMART_ROUTING] ❌ Failed to fill {target_quantity} after {max_iterations} iterations"
        )
        return {'success': False, 'error': 'Max iterations reached'}

    async def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel an order with GRVT."""
        try:
            # Cancel the order using GRVT SDK
            cancel_result = self.rest_client.cancel_order(id=order_id)

            if cancel_result:
                return OrderResult(success=True)
            else:
                return OrderResult(
                    success=False, error_message="Failed to cancel order"
                )

        except Exception as e:
            return OrderResult(success=False, error_message=str(e))

    @query_retry(reraise=True)
    async def get_order_info(
        self, order_id: str = None, client_order_id: str = None
    ) -> Optional[OrderInfo]:
        """Get order information from GRVT."""
        # Get order information using GRVT SDK
        if order_id is not None:
            order_data = self.rest_client.fetch_order(id=order_id)
        elif client_order_id is not None:
            order_data = self.rest_client.fetch_order(
                params={"client_order_id": client_order_id}
            )
        else:
            raise ValueError("Either order_id or client_order_id must be provided")

        if not order_data or "result" not in order_data:
            raise ValueError(f"Unable to get order info: {order_id}")

        order = order_data["result"]
        legs = order.get("legs", [])
        if not legs:
            raise ValueError(f"Unable to get order info: {order_id}")

        leg = legs[0]  # Get first leg
        state = order.get("state", {})

        return OrderInfo(
            order_id=order.get("order_id", ""),
            side=leg.get("is_buying_asset", False) and "buy" or "sell",
            size=Decimal(leg.get("size", 0)),
            price=Decimal(leg.get("limit_price", 0)),
            status=state.get("status", ""),
            filled_size=(
                Decimal(state.get("traded_size", ["0"])[0])
                if isinstance(state.get("traded_size"), list)
                else Decimal(0)
            ),
            remaining_size=(
                Decimal(state.get("book_size", ["0"])[0])
                if isinstance(state.get("book_size"), list)
                else Decimal(0)
            ),
            avg_fill_price=(
                Decimal(state.get("avg_fill_price", ["0"])[0])
                if isinstance(state.get("avg_fill_price"), list)
                else Decimal(0)
            ),
        )

    async def _get_active_close_orders(self, contract_id: str) -> int:
        """Get active close orders for a contract using official SDK."""
        active_orders = await self.get_active_orders(contract_id)
        active_close_orders = 0
        for order in active_orders:
            if order.side == self.config.close_order_side:
                active_close_orders += 1
        return active_close_orders

    @query_retry(reraise=True)
    async def get_active_orders(self, contract_id: str) -> List[OrderInfo]:
        """Get active orders for a contract."""
        # Get active orders using GRVT SDK
        orders = self.rest_client.fetch_open_orders(symbol=contract_id)

        if not orders:
            return []

        order_list = []
        for order in orders:
            legs = order.get("legs", [])
            if not legs:
                continue

            leg = legs[0]  # Get first leg
            state = order.get("state", {})

            order_list.append(
                OrderInfo(
                    order_id=order.get("order_id", ""),
                    side=leg.get("is_buying_asset", False) and "buy" or "sell",
                    size=Decimal(leg.get("size", 0)),
                    price=Decimal(leg.get("limit_price", 0)),
                    status=state.get("status", ""),
                    filled_size=(
                        Decimal(state.get("traded_size", ["0"])[0])
                        if isinstance(state.get("traded_size"), list)
                        else Decimal(0)
                    ),
                    remaining_size=(
                        Decimal(state.get("book_size", ["0"])[0])
                        if isinstance(state.get("book_size"), list)
                        else Decimal(0)
                    ),
                )
            )

        return order_list

    @query_retry(reraise=True)
    async def get_account_positions(self) -> Decimal:
        """Get account positions."""
        # Get positions using GRVT SDK
        positions = self.rest_client.fetch_positions()

        for position in positions:
            if position.get("instrument") == self.config.contract_id:
                return Decimal(position.get("size", 0))

        return Decimal(0)

    async def get_contract_attributes(self) -> Tuple[str, Decimal]:
        """Get contract ID and tick size for a ticker."""
        ticker = self.config.ticker
        if not ticker:
            raise ValueError("Ticker is empty")

        # Get markets from GRVT
        markets = self.rest_client.fetch_markets()

        for market in markets:
            if (
                market.get("base") == ticker
                and market.get("quote") == "USDT"
                and market.get("kind") == "PERPETUAL"
            ):
                self.config.contract_id = market.get("instrument", "")
                self.config.tick_size = Decimal(market.get("tick_size", 0))

                # Validate minimum quantity
                min_size = Decimal(market.get("min_size", 0))
                if self.config.quantity < min_size:
                    raise ValueError(
                        f"Order quantity is less than min quantity: {self.config.quantity} < {min_size}"
                    )

                return self.config.contract_id, self.config.tick_size

        raise ValueError(f"Contract not found for ticker: {ticker}")
