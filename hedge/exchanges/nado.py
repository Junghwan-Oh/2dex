"""
Nado exchange client implementation.
"""

import os
import asyncio
import json
import traceback
import time
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.subaccount import SubaccountParams
from nado_protocol.engine_client.types import OrderParams
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.expiration import get_expiration_timestamp
from nado_protocol.utils.math import to_x18, from_x18
from nado_protocol.utils.nonce import gen_order_nonce
from nado_protocol.utils.order import build_appendix, OrderType
from nado_protocol.engine_client.types.execute import CancelOrdersParams

from .base import BaseExchangeClient, OrderResult, OrderInfo, query_retry
from helpers.logger import TradingLogger

# WebSocket imports (optional - only if available)
try:
    from .nado_websocket_client import NadoWebSocketClient
    from .nado_bbo_handler import BBOHandler
    from .nado_bookdepth_handler import BookDepthHandler
    WEBSOCKET_AVAILABLE = True
    import sys
    print("[NADO WEBSOCKET] Import successful - WEBSOCKET_AVAILABLE = True", file=sys.stderr)
except ImportError as e:
    WEBSOCKET_AVAILABLE = False
    NadoWebSocketClient = None
    BBOHandler = None
    BookDepthHandler = None
    # Log import error for debugging (only once at module load)
    import sys
    print(f"[NADO WEBSOCKET] Import failed: {e}", file=sys.stderr)
    print(f"[NADO WEBSOCKET] WEBSOCKET_AVAILABLE set to False - using REST fallback", file=sys.stderr)


class NadoClient(BaseExchangeClient):
    """Nado exchange client implementation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Nado client."""
        super().__init__(config)

        # Nado credentials from environment
        self.private_key = os.getenv('NADO_PRIVATE_KEY')
        self.mode = os.getenv('NADO_MODE', 'MAINNET').upper()
        self.subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')
        self.symbol = self.config.ticker + '-PERP'
        
        if not self.private_key:
            raise ValueError("NADO_PRIVATE_KEY must be set in environment variables")

        # Map mode string to NadoClientMode enum
        mode_map = {
            'MAINNET': NadoClientMode.MAINNET,
            'DEVNET': NadoClientMode.DEVNET,
        }
        client_mode = mode_map.get(self.mode, NadoClientMode.MAINNET)

        # Initialize Nado client using official SDK
        self.client = create_nado_client(client_mode, self.private_key)
        self.owner = self.client.context.engine_client.signer.address

        # Initialize logger
        self.logger = TradingLogger(exchange="nado", ticker=self.config.ticker, log_to_console=False)

        # WebSocket components (if available)
        self._ws_client: Optional[NadoWebSocketClient] = None
        self._bbo_handler: Optional[BBOHandler] = None
        self._bookdepth_handler: Optional['BookDepthHandler'] = None
        self._ws_connected = False
        self._use_websocket = WEBSOCKET_AVAILABLE

        # Legacy placeholder variables
        self._order_update_handler = None
        self._ws_task: Optional[asyncio.Task] = None
        self._ws_stop = asyncio.Event()

    async def verify_leverage(self) -> dict:
        """Verify current leverage settings using MarginManager.

        Returns:
            dict: {
                "account_leverage": Decimal,
                "eth_leverage": Optional[Decimal],
                "sol_leverage": Optional[Decimal],
                "margin_mode": str
            }
        """
        try:
            from nado_protocol.utils.margin_manager import MarginManager

            # Create margin manager from client
            margin_manager = MarginManager.from_client(self.client)

            # Get account-level summary
            account_summary = margin_manager.calculate_account_summary()

            # Get isolated position metrics
            isolated_positions = margin_manager.calculate_isolated_position_metrics(
                self.client.context.subaccount
            )

            # Extract leverage for our positions
            eth_leverage = None
            sol_leverage = None

            for pos in isolated_positions.isolated_positions:
                if pos.ticker == "ETH":
                    eth_leverage = pos.leverage
                elif pos.ticker == "SOL":
                    sol_leverage = pos.leverage

            result = {
                "account_leverage": account_summary.account_leverage,
                "eth_leverage": eth_leverage,
                "sol_leverage": sol_leverage,
                "margin_mode": "isolated" if eth_leverage or sol_leverage else "cross"
            }

            self.logger.log(
                f"Leverage verification - Account: {result['account_leverage']:.2f}x, "
                f"ETH: {eth_leverage if eth_leverage else 'N/A'}x, "
                f"SOL: {sol_leverage if sol_leverage else 'N/A'}x",
                "INFO"
            )

            return result

        except Exception as e:
            self.logger.log(f"Error verifying leverage: {e}", "ERROR")
            return {
                "account_leverage": Decimal("0"),
                "eth_leverage": None,
                "sol_leverage": None,
                "margin_mode": "unknown"
            }

    def _validate_config(self) -> None:
        """Validate Nado configuration."""
        required_env_vars = ['NADO_PRIVATE_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

    async def connect(self) -> None:
        """Connect to Nado (setup WebSocket for BBO if available)."""
        # Log WebSocket availability at start
        self.logger.log(f"WEBSOCKET_AVAILABLE: {WEBSOCKET_AVAILABLE}", "INFO")

        try:
            # Try to connect to WebSocket for real-time BBO data
            if self._use_websocket and WEBSOCKET_AVAILABLE:
                self.logger.log(f"Attempting WebSocket connection for {self.config.ticker}...", "INFO")
                await self._connect_websocket()
            else:
                if not WEBSOCKET_AVAILABLE:
                    self.logger.log("WebSocket modules not available, using REST-only mode", "WARN")
                else:
                    self.logger.log("WebSocket disabled by configuration, using REST-only mode", "WARN")
        except Exception as e:
            self.logger.log(f"WebSocket connection failed: {e}, using REST fallback", "WARN")
            self._use_websocket = False

        # Log final connection status
        if self._ws_connected:
            self.logger.log(f"WebSocket connected for {self.config.ticker}", "INFO")
        else:
            self.logger.log(f"Connected to Nado (REST-only mode for {self.config.ticker})", "INFO")

    async def _connect_websocket(self) -> None:
        """Connect to WebSocket for real-time BBO data."""
        if not WEBSOCKET_AVAILABLE:
            raise ImportError("WebSocket modules not available")

        # Get product ID for this ticker
        product_id = self._get_product_id_from_contract(self.config.ticker)
        self.logger.log(f"WebSocket: Creating client for {self.config.ticker} (product_id={product_id})", "INFO")

        # Create WebSocket client (with credentials for private stream authentication)
        self._ws_client = NadoWebSocketClient(
            product_ids=[product_id],
            auto_reconnect=True,
            private_key=self.private_key,
            owner=self.owner,
            subaccount_name=self.subaccount_name
        )

        # Create BBO handler (pass internal logger, not TradingLogger wrapper)
        self._bbo_handler = BBOHandler(
            product_id=product_id,
            ws_client=self._ws_client,
            logger=self.logger.logger  # Use internal logger
        )

        # Create BookDepth handler for slippage estimation
        self._bookdepth_handler = BookDepthHandler(
            product_id=product_id,
            ws_client=self._ws_client,
            logger=self.logger.logger  # Use internal logger
        )

        # Connect and subscribe
        self.logger.log(f"WebSocket: Connecting to server for {self.config.ticker}...", "INFO")
        await self._ws_client.connect()

        self.logger.log(f"WebSocket: Starting BBO handler for {self.config.ticker}...", "INFO")
        await self._bbo_handler.start()

        self.logger.log(f"WebSocket: Starting BookDepth handler for {self.config.ticker}...", "INFO")
        await self._bookdepth_handler.start()

        self._ws_connected = True
        self.logger.log(f"WebSocket connected for {self.config.ticker} (product_id={product_id})", "INFO")

    async def disconnect(self) -> None:
        """Disconnect from Nado."""
        # Disconnect WebSocket if connected
        if self._ws_connected and self._ws_client:
            try:
                await self._ws_client.disconnect()
                self._ws_connected = False
                self.logger.log("WebSocket disconnected", "INFO")
            except Exception as e:
                self.logger.log(f"Error during WebSocket disconnect: {e}", "ERROR")

        # Legacy cleanup
        try:
            self._ws_stop.set()
            if self._ws_task and not self._ws_task.done():
                await self._ws_task
        except Exception as e:
            self.logger.log(f"Error during Nado disconnect: {e}", "ERROR")

    def get_exchange_name(self) -> str:
        """Get the exchange name."""
        return "nado"

    def setup_order_update_handler(self, handler) -> None:
        """Setup order update handler for WebSocket."""
        self._order_update_handler = handler
        # Nado SDK may provide WebSocket callbacks, but for now we'll use polling
        # This can be enhanced if Nado SDK provides WebSocket support

    @query_retry(default_return=(0, 0))
    async def fetch_bbo_prices(self, contract_id: str) -> Tuple[Decimal, Decimal]:
        """
        Fetch best bid/offer prices from Nado.

        Uses WebSocket BBO if available, otherwise falls back to REST API.
        """
        # Try WebSocket first (real-time, no rate limit)
        if self._ws_connected and self._bbo_handler:
            bid_price, ask_price = self._bbo_handler.get_prices()
            if bid_price is not None and bid_price > 0 and ask_price is not None and ask_price > 0:
                # Got valid data from WebSocket
                return bid_price, ask_price

        # Fallback to REST API
        try:
            # Convert contract_id (product_id number) to ticker_id string
            ticker_id = self._get_ticker_id(int(contract_id))
            # Get order book depth
            order_book = self.client.context.engine_client.get_orderbook(ticker_id=ticker_id, depth=1)

            if not order_book:
                return Decimal(0), Decimal(0)

            # Extract best bid and ask
            bids = order_book.bids
            asks = order_book.asks

            if not bids or not asks:
                return Decimal(0), Decimal(0)

            # Best bid is highest price (first in sorted list)
            best_bid = Decimal(str(bids[0][0]))
            # Best ask is lowest price (first in sorted list)
            best_ask = Decimal(str(asks[0][0]))

            return best_bid, best_ask

        except Exception as e:
            self.logger.log(f"Error fetching BBO prices: {e}", "ERROR")
            return Decimal(0), Decimal(0)

    def get_bookdepth_handler(self) -> Optional['BookDepthHandler']:
        """Get the BookDepth handler for this client (if WebSocket is connected)."""
        return self._bookdepth_handler if self._ws_connected else None

    def get_bbo_handler(self) -> Optional['BBOHandler']:
        """Get the BBO handler for this client (if WebSocket is connected).

        Returns:
            BBOHandler instance if WebSocket is connected, None otherwise
        """
        return self._bbo_handler if self._ws_connected else None

    async def estimate_slippage(
        self,
        side: str,
        quantity: Decimal
    ) -> Decimal:
        """
        Estimate slippage for a given order quantity using BookDepth data.

        Args:
            side: "buy" or "sell"
            quantity: Order quantity

        Returns:
            Slippage in basis points, or 999999 if insufficient liquidity
        """
        handler = self.get_bookdepth_handler()
        if handler is None:
            # No WebSocket data - return high slippage to indicate unavailable
            return Decimal(999999)

        return handler.estimate_slippage(side, quantity)

    async def check_exit_capacity(
        self,
        position: Decimal,
        max_slippage_bps: int = 20
    ) -> Tuple[bool, Decimal]:
        """
        Check if we can exit a position without excessive slippage.

        Args:
            position: Current position (positive = long, negative = short)
            max_slippage_bps: Maximum acceptable slippage in bps

        Returns:
            Tuple of (can_exit, exitable_quantity)
        """
        handler = self.get_bookdepth_handler()
        if handler is None:
            # No WebSocket data - conservative assumption
            return False, Decimal(0)

        return handler.estimate_exit_capacity(position, max_slippage_bps)

    async def get_available_liquidity(
        self,
        side: str,
        max_depth: int = 20
    ) -> Decimal:
        """
        Get total available liquidity up to specified depth.

        Args:
            side: "bid" or "ask"
            max_depth: Maximum depth levels to consider

        Returns:
            Total liquidity quantity
        """
        handler = self.get_bookdepth_handler()
        if handler is None:
            return Decimal(0)

        return handler.get_available_liquidity(side, max_depth)

    def _get_product_id_from_contract(self, contract_id: str) -> int:
        """Convert contract_id (ticker) to product_id."""
        # Try to parse as int first
        try:
            return int(contract_id)
        except ValueError:
            # If it's a ticker like "BTC", we need to look it up
            # Nado testnet product IDs
            ticker_to_product_id = {
                'WBTC': 1,
                'ETH': 4,
                'SOL': 8,
            }
            ticker = contract_id.upper()
            return ticker_to_product_id.get(ticker, 1)  # Default to WBTC

    def _get_ticker_id(self, product_id: int) -> str:
        """Get ticker_id string from product_id."""
        ticker_id_map = {
            1: "WBTC_USDT0",
            2: "BTC-PERP_USDT0",
            3: "WETH_USDT0",
            4: "ETH-PERP_USDT0",
            5: "USDC_USDT0",
            8: "SOL-PERP_USDT0",
            10: "XRP-PERP_USDT0",
        }
        return ticker_id_map.get(product_id, f"PERP_{product_id}")

    def calculate_timeout(self, quantity: Decimal) -> int:
        """Calculate timeout based on order size with realistic microstructure awareness.

        Piecewise logic for predictable timeout values:
        - 0.1 ETH → 5s (quick fills at BBO)
        - 0.5 ETH → 10s (moderate spread)
        - 1.0 ETH → 20s (must look deeper)

        Args:
            quantity: Order quantity in tokens

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

    def extract_filled_quantity(self, order_result: dict) -> Decimal:
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
            # Try direct key access first (Nado REST API returns x18 format)
            if 'state' in order_result and 'traded_size' in order_result['state']:
                traded_size = order_result['state']['traded_size']
                # Check if it's in x18 format (large number)
                traded_size_decimal = Decimal(traded_size)
                if traded_size_decimal > Decimal('1000000'):  # Likely x18 format
                    return traded_size_decimal / Decimal(1e18)
                return traded_size_decimal

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

        except (KeyError, IndexError, TypeError, ValueError, InvalidOperation) as e:
            return Decimal('0')

    def calculate_slippage_bps(self, execution_price: Decimal, reference_price: Decimal) -> Decimal:
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

    async def get_order_price(self, direction: str) -> Decimal:
        """Get the price of an order with Nado."""
        best_bid, best_ask = await self.fetch_bbo_prices(self.symbol + '_USDT0')
        if best_bid <= 0 or best_ask <= 0:
            self.logger.log("Invalid bid/ask prices", "ERROR")
            raise ValueError("Invalid bid/ask prices")

        if direction == 'buy':
            # For buy orders, place slightly below best ask to ensure execution
            order_price = best_ask - self.config.tick_size
        else:
            # For sell orders, place slightly above best bid to ensure execution
            order_price = best_bid + self.config.tick_size
        return self.round_to_tick(order_price)

    async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
        """Place an open order with Nado using official SDK."""
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

                if best_bid <= 0 or best_ask <= 0:
                    return OrderResult(success=False, error_message='Invalid bid/ask prices')

                # Determine order price
                if direction == 'buy':
                    order_price = best_ask - self.config.tick_size
                else:
                    order_price = best_bid + self.config.tick_size

                # Build order parameters
                order = OrderParams(
                    sender=SubaccountParams(
                        subaccount_owner=self.owner,
                        subaccount_name=self.subaccount_name,
                    ),
                    priceX18=to_x18(float(str(order_price))),
                    amount=to_x18(float(str(quantity))) if direction == 'buy' else -to_x18(float(str(quantity))),
                    expiration=get_expiration_timestamp(60*60*24*30),
                    nonce=gen_order_nonce(),
                    appendix=build_appendix(
                        order_type=OrderType.POST_ONLY,
                        isolated=True
                    )
                )

                # Place the order
                result = self.client.market.place_order({"product_id": int(contract_id), "order": order})

                if not result:
                    return OrderResult(success=False, error_message='Failed to place order')

                # Extract order ID from response
                order_id = result.data.digest

                # Order successfully placed
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    side=direction,
                    size=quantity,
                    price=order_price,
                    status='OPEN'
                )

            except Exception as e:
                self.logger.log(f"Error placing open order: {e}", "ERROR")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(0.1)
                    continue
                else:
                    return OrderResult(success=False, error_message=str(e))

        return OrderResult(success=False, error_message='Max retries exceeded')

    async def place_ioc_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
        """Place an IOC (Immediate-Or-Cancel) order for immediate execution.

        IOC orders are either filled immediately (or partially) and any remaining
        quantity is cancelled. This is useful for entering/exit positions quickly.
        """
        # DEBUG: Log entry to stderr
        import sys
        print(f"[DEBUG] place_ioc_order: contract={contract_id}, direction={direction}, qty={quantity}", file=sys.stderr)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

                if best_bid <= 0 or best_ask <= 0:
                    return OrderResult(success=False, error_message='Invalid bid/ask prices')

                # Use taker pricing for IOC: price at the touch to cross the spread
                # For IOC orders to fill immediately, they must match with standing orders
                product_id_int = int(contract_id)

                if direction == 'buy':
                    # Buy at best ask to match with standing sell orders
                    order_price = self._round_price_to_increment(product_id_int, best_ask)
                else:
                    # Sell at best bid to match with standing buy orders
                    # No need to go below - matching at the bid should work as a taker
                    order_price = self._round_price_to_increment(product_id_int, best_bid)

                # Round quantity to size increment (tick size for quantity) FIRST
                rounded_quantity = self._round_quantity_to_size_increment(product_id_int, quantity)
                if rounded_quantity == 0:
                    return OrderResult(success=False, error_message=f'Quantity {quantity} too small (rounds to 0)')

                # DEBUG: Log pricing details for all IOC orders
                import sys
                print(f"[DEBUG IOC {direction.upper()}] contract={contract_id}, bid={best_bid}, ask={best_ask}, order_price={order_price} (taker), rounded_qty={rounded_quantity}", file=sys.stderr)

                # Calculate isolated margin for 5x leverage (margin = notional / leverage)
                # SDK requires x6 precision (6 decimal places) for isolated_margin parameter
                notional_value = float(str(rounded_quantity)) * float(str(order_price))
                leverage = 5.0
                isolated_margin = int(notional_value / leverage * 10**6)  # x6 precision: 100.00 -> 100000000

                # DEBUG: Log isolated margin details
                import sys
                print(f"[DEBUG ISOLATED] notional={notional_value:.2f}, leverage={leverage}x, margin={notional_value/leverage:.2f}, isolated_margin_x6={isolated_margin}", file=sys.stderr)
                order = OrderParams(
                    sender=SubaccountParams(
                        subaccount_owner=self.owner,
                        subaccount_name=self.subaccount_name,
                    ),
                    priceX18=to_x18(float(str(order_price))),
                    amount=to_x18(float(str(rounded_quantity))) if direction == 'buy' else -to_x18(float(str(rounded_quantity))),
                    expiration=get_expiration_timestamp(60),  # Short expiration for IOC
                    nonce=gen_order_nonce(),
                    appendix=build_appendix(
                        order_type=OrderType.IOC,
                        isolated=True,
                        isolated_margin=isolated_margin  # CRITICAL: Must pass x6-precision margin
                    )
                )

                # Place the order
                result = self.client.market.place_order({"product_id": int(contract_id), "order": order})
                print(f"[DEBUG PLACE_ORDER] Result type: {type(result)}, value: {result}", file=sys.stderr)

                if not result:
                    print(f"[DEBUG PLACE_ORDER] Order placement returned falsy result", file=sys.stderr)
                    return OrderResult(success=False, error_message='Failed to place order', status='EXPIRED')

                order_id = result.data.digest

                # Immediately check order status to see if it filled
                await asyncio.sleep(0.1)  # Brief wait for execution
                order_info = await self.get_order_info(order_id)

                if order_info is None:
                    return OrderResult(
                        success=False,
                        error_message='Could not get order info',
                        status='UNKNOWN'
                    )

                # Determine filled status
                filled_size = order_info.filled_size
                remaining_size = order_info.remaining_size

                # DEBUG: Log order info for troubleshooting
                import sys
                print(f"[DEBUG ORDER INFO] contract={contract_id}, direction={direction}, filled_size={filled_size}, remaining_size={remaining_size}, order_price={order_info.price}", file=sys.stderr)

                if remaining_size == 0:
                    status = 'FILLED'
                elif filled_size > 0:
                    status = 'PARTIALLY_FILLED'
                else:
                    status = 'EXPIRED'

                # Success only if there was actual fill (filled_size != 0)
                # Note: filled_size is negative for sell orders, positive for buy orders
                actual_fill = filled_size != 0
                return OrderResult(
                    success=actual_fill,
                    order_id=order_id,
                    side=direction,
                    size=rounded_quantity,
                    filled_size=abs(filled_size) if filled_size != 0 else Decimal('0'),  # Store as positive
                    price=order_info.price,
                    status=status
                )

            except Exception as e:
                import traceback
                self.logger.log(f"Error placing IOC order: {e}", "ERROR")
                print(f"[DEBUG EXCEPTION] {type(e).__name__}: {e}", file=sys.stderr)
                print(f"[DEBUG TRACEBACK]\n{traceback.format_exc()}", file=sys.stderr)
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(0.05)
                    continue
                else:
                    return OrderResult(success=False, error_message=str(e))

        return OrderResult(success=False, error_message='Max retries exceeded for IOC order')

    def _round_quantity_to_size_increment(self, product_id: int, quantity: Decimal) -> Decimal:
        """Round quantity to the product's size increment.

        Uses ROUND_HALF_UP to match standard trading behavior where
        values exactly halfway between increments round up.

        Args:
            product_id: Product ID (4=ETH, 8=SOL)
            quantity: Quantity to round

        Returns:
            Rounded quantity aligned to size increment
        """
        # Size increment mapping (in Decimal format, not X18)
        size_increments = {
            4: Decimal("0.001"),  # ETH
            8: Decimal("0.1"),    # SOL
        }
        size_increment = size_increments.get(product_id, Decimal("0.001"))
        # Round to nearest increment using ROUND_HALF_UP
        from decimal import ROUND_HALF_UP
        return (quantity / size_increment).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * size_increment

    def _round_price_to_increment(self, product_id: int, price: Decimal) -> Decimal:
        """Round price to the product's price increment.

        Uses ROUND_HALF_UP to match standard trading behavior where
        values exactly halfway between increments round up.

        Args:
            product_id: Product ID (4=ETH, 8=SOL)
            price: Price to round

        Returns:
            Rounded price aligned to price increment
        """
        # Price increment mapping (in Decimal format, not X18)
        # ETH: 0.0001, SOL: 0.01
        price_increments = {
            4: Decimal("0.0001"),  # ETH
            8: Decimal("0.01"),     # SOL
        }
        price_increment = price_increments.get(product_id, Decimal("0.0001"))
        # Round to nearest increment using ROUND_HALF_UP
        from decimal import ROUND_HALF_UP
        return (price / price_increment).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * price_increment

    async def place_close_order(self, contract_id: str, quantity: Decimal, price: Decimal, side: str) -> OrderResult:
        """Place a close order with Nado using official SDK."""
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

                if best_bid <= 0 or best_ask <= 0:
                    return OrderResult(success=False, error_message='Invalid bid/ask prices')

                # Adjust order price based on market conditions
                adjusted_price = price
                if side.lower() == 'sell':
                    # For sell orders, ensure price is above best bid to be a maker order
                    if price <= best_bid:
                        adjusted_price = best_bid + self.config.tick_size
                elif side.lower() == 'buy':
                    # For buy orders, ensure price is below best ask to be a maker order
                    if price >= best_ask:
                        adjusted_price = best_ask - self.config.tick_size

                # Build order parameters
                order = OrderParams(
                    sender=SubaccountParams(
                        subaccount_owner=self.owner,
                        subaccount_name=self.subaccount_name,
                    ),
                    priceX18=to_x18(float(adjusted_price)),
                    amount=to_x18(float(quantity)) if side.lower() == 'buy' else -to_x18(float(quantity)),
                    expiration=get_expiration_timestamp(3600),  # 1 hour expiration
                    nonce=gen_order_nonce(),
                    appendix=build_appendix(
                        order_type=OrderType.POST_ONLY,
                        isolated=True
                    )
                )

                # Place the order
                result = self.client.market.place_order({"product_id": int(contract_id), "order": order})

                if not result:
                    return OrderResult(success=False, error_message='Failed to place order')

                # Extract order ID from response
                order_id = result.data.digest
                if not order_id:
                    await asyncio.sleep(0.1)
                    return OrderResult(
                        success=True,
                        side=side,
                        size=quantity,
                        price=adjusted_price,
                        status='OPEN'
                    )

                # Order successfully placed
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    side=side,
                    size=quantity,
                    price=adjusted_price,
                    status='OPEN'
                )

            except Exception as e:
                self.logger.log(f"Error placing close order: {e}", "ERROR")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(0.1)
                    continue
                else:
                    return OrderResult(success=False, error_message=str(e))

        return OrderResult(success=False, error_message='Max retries exceeded for close order')

    async def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel an order with Nado using official SDK."""
        try:
            sender = subaccount_to_hex(SubaccountParams(
                    subaccount_owner=self.owner,
                    subaccount_name=self.subaccount_name,
                ))
            # Cancel order using Nado SDK
            result = self.client.market.cancel_orders(
                CancelOrdersParams(productIds=[self.config.contract_id], digests=[order_id], sender=sender)
            )

            if not result:
                return OrderResult(success=False, error_message='Failed to cancel order')

            order_info = await self.get_order_info(order_id)

            filled_size = order_info.filled_size if order_info is not None else Decimal(0)
            price = order_info.price if order_info is not None else Decimal(0)

            return OrderResult(success=True, filled_size=filled_size, price=price)

        except Exception as e:
            self.logger.log(f"Error canceling order: {e}", "ERROR")
            return OrderResult(success=False, error_message=str(e))

    @query_retry()
    async def get_order_info(self, order_id: str) -> Optional[OrderInfo]:
        """Get order information from Nado using official SDK."""
        try:
            # Get order info from Nado SDK
            # Note: Adjust method name if SDK uses different API
            order = self.client.context.engine_client.get_order(product_id=self.config.contract_id, digest=order_id)
            price_x18 = getattr(order, 'price_x18', None)
            amount_x18 = getattr(order, 'amount', None)
            unfilled_x18 = getattr(order, 'unfilled_amount', None)
            order_id = str(getattr(order, 'digest', None))

            size = Decimal(str(from_x18(amount_x18))) if amount_x18 else Decimal(0)
            remaining_size = Decimal(str(from_x18(unfilled_x18))) if unfilled_x18 else Decimal(0)
            filled_size = size - remaining_size

            side = 'buy' if size > 0 else 'sell'

            return OrderInfo(
                order_id=order_id,
                side=side,
                size=size,
                price=Decimal(str(from_x18(price_x18))),
                status='OPEN',
                filled_size=filled_size,
                remaining_size=remaining_size
            )

        except Exception as e:
            attempt = 0
            while attempt < 4:
                attempt += 1
                self.logger.log(f"Attempt {attempt} to get archived order info", "INFO")
                try:
                    order_result = self.client.context.indexer_client.get_historical_orders_by_digest([order_id])
                    if order_result.orders != []:
                        order = order_result.orders[0]
                        # Parse order data
                        price_x18 = getattr(order, 'price_x18', None)
                        amount_x18 = getattr(order, 'amount', None)
                        filled_x18 = getattr(order, 'base_filled', None)
                        order_id = str(getattr(order, 'digest', None))

                        if order.base_filled == order.amount:
                            status = 'FILLED'
                        else:
                            status = 'CANCELLED'

                        size = Decimal(str(from_x18(amount_x18))) if amount_x18 else Decimal(0)
                        filled_size = Decimal(str(from_x18(filled_x18))) if filled_x18 else Decimal(0)
                        remaining_size = size - filled_size

                        side = 'buy' if size > 0 else 'sell'

                        return OrderInfo(
                            order_id=order_id,
                            side=side,
                            size=size,
                            price=Decimal(str(from_x18(price_x18))),
                            status=status,
                            filled_size=filled_size,
                            remaining_size=remaining_size
                        )
                except Exception as e:
                    self.logger.log(f"Error getting order info after retry: {e}", "ERROR")

                await asyncio.sleep(0.5)

            return OrderInfo(
                order_id=order_id,
                side='',
                size=Decimal(0),
                price=Decimal(0),
                status='CANCELLED',
                filled_size=Decimal(0),
                remaining_size=Decimal(0)
            )

    @query_retry(default_return=[])
    async def get_active_orders(self, contract_id: str) -> List[OrderInfo]:
        """Get active orders for a contract using official SDK."""
        try:            
            # Get subaccount open orders from Nado SDK
            sender = subaccount_to_hex(SubaccountParams(
                    subaccount_owner=self.owner,
                    subaccount_name=self.subaccount_name,
                ))

            orders_data = self.client.market.get_subaccount_open_orders(
                product_id=contract_id,
                sender=sender)

            if not orders_data:
                return []

            orders = []
            # Handle both list and object with orders attribute
            order_list = orders_data if isinstance(orders_data, list) else getattr(orders_data, 'orders', [])

            for order in order_list:
                price_x18 = getattr(order, 'price_x18', None)
                amount_x18 = getattr(order, 'amount', None)
                unfilled_x18 = getattr(order, 'unfilled_amount', None)
                order_id = str(getattr(order, 'digest', None))

                size = Decimal(str(from_x18(amount_x18))) if amount_x18 else Decimal(0)
                remaining_size = Decimal(str(from_x18(unfilled_x18))) if unfilled_x18 else Decimal(0)
                filled_size = size - remaining_size

                side = 'buy' if size > 0 else 'sell'

                orders.append(OrderInfo(
                    order_id=str(order_id),
                    side=side,
                    size=size,
                    price=Decimal(str(from_x18(price_x18))) if price_x18 else Decimal(0),
                    status='OPEN',
                    filled_size=filled_size,
                    remaining_size=remaining_size
                ))

            return orders

        except Exception as e:
            self.logger.log(f"Error getting active orders: {e}", "ERROR")
            self.logger.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return []

    @query_retry(default_return=0)
    async def get_account_positions(self) -> Decimal:
        """Get account positions using official SDK."""
        try:
            # Get subaccount identifier
            resolved_subaccount = subaccount_to_hex(self.client.context.signer.address, self.subaccount_name)
            
            # Get isolated positions from Nado SDK (requires subaccount parameter)
            account_data = self.client.context.engine_client.get_subaccount_info(resolved_subaccount)
            position_data = account_data.perp_balances

            # Find position for current contract
            product_id = self.config.contract_id
            
            for position in position_data:
                if position.product_id == product_id:
                    position_size = position.balance.amount
                    return Decimal(str(from_x18(position_size)))

            return Decimal(0)

        except Exception as e:
            self.logger.log(f"Error getting account positions: {e}", "ERROR")
            self.logger.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return Decimal(0)

    async def get_contract_attributes(self) -> Tuple[str, Decimal]:
        """Get contract ID and tick size for a ticker."""
        ticker = self.config.ticker
        if len(ticker) == 0:
            self.logger.log("Ticker is empty", "ERROR")
            raise ValueError("Ticker is empty")

        try:
            # Get markets/products from Nado SDK
            symbols = self.client.market.get_all_product_symbols()
            product_id = None
            for symbol in symbols:
                symbol_str = symbol.symbol if hasattr(symbol, 'symbol') else str(symbol)
                if symbol_str == f"{ticker.upper()}-PERP":
                    product_id = symbol.product_id if hasattr(symbol, 'product_id') else symbol
                    self.config.contract_id = product_id
                    break
            all_markets = self.client.market.get_all_engine_markets()
            markets = all_markets.perp_products
            current_market = None
            for market in markets:
                if market.product_id == product_id:
                    current_market = market
                    break

            if current_market is None:
                self.logger.log(f"Failed to get market for ticker {ticker}", "ERROR")
                raise ValueError(f"Failed to get market for ticker {ticker}")

            # Get tick size and min quantity
            tick_size_x18 = current_market.book_info.price_increment_x18
            min_quantity_x18 = current_market.book_info.size_increment

            self.config.tick_size = Decimal(str(from_x18(tick_size_x18)))

            min_quantity = Decimal(str(from_x18(min_quantity_x18)))

            if self.config.quantity < min_quantity:
                self.logger.log(f"Order quantity is less than min quantity: {self.config.quantity} < {min_quantity}", "ERROR")
                raise ValueError(f"Order quantity is less than min quantity: {self.config.quantity} < {min_quantity}")

            return self.config.contract_id, self.config.tick_size

        except Exception as e:
            self.logger.log(f"Error getting contract attributes: {e}", "ERROR")
            self.logger.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            raise

