"""
Apex Pro Exchange Connector for Hummingbot

Thin adapter layer between Hummingbot trading framework and Apex Pro API.
Follows standard Hummingbot connector pattern with Apex-specific ZK-rollup authentication.
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import AddedToCostTradeFee, TokenAmount, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

import hummingbot.connector.exchange.apex_pro.apex_pro_constants as CONSTANTS
import hummingbot.connector.exchange.apex_pro.apex_pro_utils as utils
from hummingbot.connector.exchange.apex_pro.apex_client import ApexClient

from hummingbot.connector.exchange.apex_pro.apex_pro_auth import ApexProAuth
from hummingbot.connector.exchange.apex_pro.apex_pro_api_order_book_data_source import ApexProAPIOrderBookDataSource


class ApexProExchange(ExchangePyBase):
    """
    Apex Pro exchange connector for Hummingbot.

    Provides REST API integration for order placement and account management.
    WebSocket orderbook feeds handled by ApexProAPIOrderBookDataSource.
    Uses ZK-rollup Layer 2 authentication unique to Apex Pro.
    """

    web_utils = utils

    def __init__(
        self,
        apex_pro_api_key: str,
        apex_pro_api_secret: str,
        apex_pro_api_passphrase: str,
        apex_pro_zk_seeds: str,
        apex_pro_zk_l2_key: str,
        apex_pro_network: str = "mainnet",
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
    ):
        """
        Initialize Apex Pro exchange connector.

        Args:
            apex_pro_api_key: API key from Apex Pro
            apex_pro_api_secret: API secret from Apex Pro
            apex_pro_api_passphrase: API passphrase
            apex_pro_zk_seeds: ZK-rollup seed phrase
            apex_pro_zk_l2_key: Layer 2 private key
            apex_pro_network: "mainnet" or "testnet"
            trading_pairs: List of trading pairs to trade
            trading_required: Whether trading is required
        """
        self._apiKey = apex_pro_api_key
        self._apiSecret = apex_pro_api_secret
        self._apiPassphrase = apex_pro_api_passphrase
        self._zkSeeds = apex_pro_zk_seeds
        self._zkL2Key = apex_pro_zk_l2_key
        self._network = apex_pro_network.lower()
        self._domain = utils.get_domain(self._network)
        self._tradingRequired = trading_required
        self._tradingPairs = trading_pairs or CONSTANTS.DEFAULT_TRADING_PAIRS

        # Network configuration
        self._networkId = utils.get_network_id(self._network)
        self._restApiUrl = utils.get_rest_api_url(self._network)

        super().__init__()
        # Initialize ApexClient for API calls
        self._apex_client = ApexClient(
            environment=self._network,
            api_key=self._apiKey,
            api_secret=self._apiSecret,
            api_passphrase=self._apiPassphrase,
            zk_seeds=self._zkSeeds,
            zk_l2_key=self._zkL2Key
        )

    # ========================================
    # Properties (7 standard + 4 custom)
    # ========================================

    @property
    def authenticator(self):
        """Get authenticator instance with ZK-rollup credentials."""
        return ApexProAuth(
            api_key=self._apiKey,
            api_secret=self._apiSecret,
            api_passphrase=self._apiPassphrase,
            zk_seeds=self._zkSeeds,
            zk_l2_key=self._zkL2Key,
            network_id=self._networkId,
        )

    @property
    def name(self) -> str:
        """Get connector name."""
        return f"apex_pro_{self._network}"

    @property
    def rate_limits_rules(self):
        """Get rate limits configuration."""
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self):
        """Get domain identifier."""
        return self._domain

    @property
    def client_order_id_max_length(self):
        """Get maximum order ID length."""
        return CONSTANTS.MAX_ORDER_ID_LEN

    @property
    def client_order_id_prefix(self):
        """Get order ID prefix."""
        return CONSTANTS.HBOT_ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self):
        """Get trading rules API path."""
        return CONSTANTS.EXCHANGE_INFO_PATH_URL

    @property
    def trading_pairs_request_path(self):
        """Get trading pairs API path."""
        return CONSTANTS.EXCHANGE_INFO_PATH_URL

    @property
    def check_network_request_path(self):
        """Get network check API path."""
        return CONSTANTS.SERVER_TIME_PATH_URL

    @property
    def trading_pairs(self):
        """Get trading pairs list."""
        return self._tradingPairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        """Check if cancel requests are synchronous."""
        return True

    @property
    def is_trading_required(self) -> bool:
        """Check if trading is required."""
        return self._tradingRequired

    # ========================================
    # Supported Order Types
    # ========================================

    def supported_order_types(self) -> List[OrderType]:
        """Get supported order types."""
        return [OrderType.LIMIT, OrderType.LIMIT_MAKER]

    # ========================================
    # Exception Handlers (3 methods)
    # ========================================

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception) -> bool:
        """Check if exception is related to time synchronization."""
        errorDescription = str(request_exception)
        return "timestamp" in errorDescription.lower() or "time" in errorDescription.lower()

    def _is_order_not_found_during_status_update_error(self, statusUpdateException: Exception) -> bool:
        """Check if order not found during status update."""
        return "not found" in str(statusUpdateException).lower()

    def _is_order_not_found_during_cancelation_error(self, cancelationException: Exception) -> bool:
        """Check if order not found during cancellation."""
        return "not found" in str(cancelationException).lower()

    # ========================================
    # Helper Methods (3 methods)
    # ========================================

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        """Create web assistants factory for HTTP requests."""
        return utils.build_api_factory(
            throttler=self._throttler,
            timeSynchronizer=self._time_synchronizer,
            domain=self._domain,
            auth=self._auth
        )

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        """Create order book data source for WebSocket feeds."""
        return ApexProAPIOrderBookDataSource(
            trading_pairs=self.trading_pairs,
            connector=self,
            domain=self.domain,
            api_factory=self._web_assistants_factory,
            throttler=self._throttler,
            timeSynchronizer=self._time_synchronizer,
        )

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        """Create user stream data source (not implemented for Apex)."""
        # Apex Pro uses public WebSocket for orderbook only
        # User updates handled via REST API polling
        return None

    # ========================================
    # Core Order Management (5 methods)
    # ========================================

    async def _place_order(
        self,
        orderId: str,
        tradingPair: str,
        amount: Decimal,
        tradeType: TradeType,
        orderType: OrderType,
        price: Decimal,
        **kwargs,
    ) -> Tuple[str, float]:
        """
        Place an order on Apex Pro exchange using ApexClient (ZK-signature).

        Args:
            orderId: Client order ID
            tradingPair: Trading pair (e.g., "BTC-USDT")
            amount: Order amount
            tradeType: BUY or SELL
            orderType: LIMIT or LIMIT_MAKER
            price: Order price

        Returns:
            Tuple of (exchange_order_id, timestamp)
        """
        # For ZK-signature orders, Apex Pro expects symbol with hyphen (ETH-USDT)
        # NOT the exchange symbol without hyphen (ETHUSDT)
        # The create_order_v3 method looks for 'symbol' field which has hyphens
        sideStr = CONSTANTS.SIDE_BUY if tradeType == TradeType.BUY else CONSTANTS.SIDE_SELL

        # ApexClient.create_order is synchronous (apexomni SDK doesn't use asyncio)
        response = self._apex_client.create_order(
            symbol=tradingPair,  # Use Hummingbot format (ETH-USDT) directly
            side=sideStr,
            order_type="LIMIT_MAKER" if orderType == OrderType.LIMIT_MAKER else "LIMIT",
            size=f"{amount:f}",
            price=f"{price:f}",
            client_id=orderId
        )

        if not response or 'data' not in response:
            error_msg = response.get("msg") if response else "No response"
            raise ValueError(f"Order placement failed: {error_msg}")

        # apexomni SDK returns {'data': {...}, 'timeCost': ...} directly (no 'code' wrapper)
        orderResult = response.get("data", {})
        exchangeOrderId = str(orderResult["id"])
        transactTime = float(orderResult.get("createdAt", 0)) / 1000  # Convert ms to seconds

        return (exchangeOrderId, transactTime)

    async def _place_cancel(self, orderId: str, trackedOrder: InFlightOrder):
        """
        Cancel an order on Apex Pro exchange using ApexClient.

        Args:
            orderId: Order ID (not used for Apex)
            trackedOrder: Tracked order to cancel

        Returns:
            True if successful
        """
        exchangeOrderId = trackedOrder.exchange_order_id

        # ApexClient.cancel_order is synchronous (apexomni SDK doesn't use asyncio)
        response = self._apex_client.cancel_order(order_id=exchangeOrderId)

        # apexomni SDK returns {'data': {...}, ...} directly (no 'code' wrapper)
        if not response or 'data' not in response:
            error_msg = response.get("msg") if response else "No response"
            raise ValueError(f"Order cancellation failed: {error_msg}")

        return True

    async def _format_trading_rules(self, exchangeInfoDict: Dict[str, Any]) -> List[TradingRule]:
        """
        Parse trading rules from exchange info response.

        Args:
            exchangeInfoDict: Exchange info dictionary from API

        Returns:
            List of TradingRule objects
        """
        tradingPairRules = exchangeInfoDict.get("data", {}).get("perpetualContract", [])
        retval = []

        for rule in tradingPairRules:
            try:
                tradingPair = await self.trading_pair_associated_to_exchange_symbol(symbol=rule["crossSymbolName"])

                retval.append(
                    TradingRule(
                        trading_pair=tradingPair,
                        minOrderSize=Decimal(str(rule.get("minOrderSize", CONSTANTS.MIN_ORDER_SIZE))),
                        maxOrderSize=Decimal(str(rule.get("maxOrderSize", "1000000"))),
                        minPriceIncrement=Decimal(str(rule.get("tickSize", CONSTANTS.DEFAULT_TICK_SIZE))),
                        minBaseAmountIncrement=Decimal(str(rule.get("stepSize", CONSTANTS.DEFAULT_STEP_SIZE))),
                    )
                )
            except Exception:
                self.logger().exception(f"Error parsing trading pair rule {rule.get('symbol')}. Skipping.")

        return retval

    async def _update_balances(self):
        """Update account balances from exchange using ApexClient."""
        # Use ApexClient for balance retrieval
        balance_response = self._apex_client.get_account_balance()
        
        if not balance_response or 'data' not in balance_response:
            raise ValueError(f"Balance update failed: Invalid response")
        
        balance_data = balance_response['data']
        
        # Update USDT balance
        self._account_balances["USDT"] = Decimal(str(balance_data.get("totalEquityValue", "0")))
        self._account_available_balances["USDT"] = Decimal(str(balance_data.get("availableBalance", "0")))

    async def _request_exchange_info(self) -> Dict[str, Any]:
        """
        Request exchange info using ApexClient.

        Returns:
            Exchange info dictionary with trading rules
        """
        # Use ApexClient to get market configs
        configs = self._apex_client.get_market_configs()

        if not configs or 'data' not in configs:
            return {"code": "1", "data": {"perpetualContract": []}}

        # Extract perpetualContract from data.contractConfig.perpetualContract
        perpetual_contract = configs.get("data", {}).get("contractConfig", {}).get("perpetualContract", [])

        # Restructure to match expected format for _format_trading_rules
        return {
            "code": "0",
            "data": {
                "perpetualContract": perpetual_contract
            }
        }

    async def get_last_traded_prices(self, tradingPairs: List[str]) -> Dict[str, float]:
        """
        Get last traded prices for multiple trading pairs using ApexClient.

        Args:
            tradingPairs: List of trading pairs in Hummingbot format (e.g., ["BTC-USDT"])

        Returns:
            Dictionary mapping trading pairs to their last traded prices
        """
        result = {}

        for trading_pair in tradingPairs:
            try:
                # Convert to exchange symbol format (BTC-USDT → BTCUSDT)
                exchange_symbol = await self.exchange_symbol_associated_to_pair(tradingPair=trading_pair)

                # Get ticker data from ApexClient
                ticker = self._apex_client.get_ticker(exchange_symbol)

                if ticker and 'lastPrice' in ticker:
                    result[trading_pair] = float(ticker['lastPrice'])
                else:
                    self.logger().warning(f"No ticker data for {trading_pair}")

            except Exception as e:
                self.logger().error(f"Error fetching price for {trading_pair}: {e}")

        return result

    async def _update_trading_fees(self):
        """Update trading fees from exchange via REST API."""
        # Apex Pro uses flat fee structure: 0.02% maker, 0.05% taker
        # For all trading pairs
        for tradingPair in self._tradingPairs:
            self._tradingFees[tradingPair] = {
                "makerFeeRate": CONSTANTS.DEFAULT_MAKER_FEE,
                "takerFeeRate": CONSTANTS.DEFAULT_TAKER_FEE,
            }

    # ========================================
    # API Request Methods
    # ========================================

    async def _apiRequest(
        self,
        path_url: str,
        method: RESTMethod = RESTMethod.GET,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        is_auth_required: bool = False,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute API request with retry logic.

        Args:
            path_url: API endpoint path
            method: HTTP method (GET/POST/DELETE)
            params: Query parameters
            data: Request body data
            is_auth_required: Whether authentication is required
            headers: Additional headers

        Returns:
            API response dictionary
        """
        last_exception = None
        rest_assistant = await self._web_assistants_factory.get_rest_assistant()
        url = utils.rest_url(path_url, domain=self.domain)

        for _ in range(CONSTANTS.API_REQUEST_RETRY):
            try:
                request_result = await rest_assistant.execute_request(
                    url=url,
                    params=params,
                    data=data,
                    method=method,
                    is_auth_required=is_auth_required,
                    headers=headers,
                    throttler_limit_id=path_url,
                )
                return request_result
            except IOError as request_exception:
                last_exception = request_exception
                if self._is_request_exception_related_to_time_synchronizer(request_exception=request_exception):
                    self._time_synchronizer.clear_time_offset_ms_samples()
                    await self._update_time_synchronizer()
                else:
                    raise

        # Failed even after retries
        raise last_exception

    async def _apiGet(self, path_url: str, params: Optional[Dict[str, Any]] = None, is_auth_required: bool = False, **kwargs) -> Dict[str, Any]:
        """Execute GET request."""
        return await self._apiRequest(path_url=path_url, method=RESTMethod.GET, params=params, is_auth_required=is_auth_required, **kwargs)

    async def _apiPost(self, path_url: str, data: Optional[Dict[str, Any]] = None, is_auth_required: bool = False, **kwargs) -> Dict[str, Any]:
        """Execute POST request."""
        return await self._apiRequest(path_url=path_url, method=RESTMethod.POST, data=data, is_auth_required=is_auth_required, **kwargs)

    # ========================================
    # Additional Required Methods
    # ========================================

    def _get_fee(
        self,
        baseCurrency: str,
        quoteCurrency: str,
        orderType: OrderType,
        orderSide: TradeType,
        amount: Decimal,
        price: Decimal = Decimal("NaN"),
        isMaker: Optional[bool] = None
    ) -> TradeFeeBase:
        """
        Calculate trading fee for an order.

        Args:
            baseCurrency: Base currency
            quoteCurrency: Quote currency
            orderType: Order type
            orderSide: Trade side (BUY/SELL)
            amount: Order amount
            price: Order price
            isMaker: Whether order is maker

        Returns:
            TradeFeeBase with fee information
        """
        isMaker = orderType is OrderType.LIMIT_MAKER
        tradingPair = combine_to_hb_trading_pair(base=baseCurrency, quote=quoteCurrency)

        if tradingPair in self._tradingFees:
            feesData = self._tradingFees[tradingPair]
            feeValue = Decimal(feesData["makerFeeRate"]) if isMaker else Decimal(feesData["takerFeeRate"])
            fee = AddedToCostTradeFee(percent=feeValue)
        else:
            fee = build_trade_fee(
                self.name,
                isMaker,
                base_currency=baseCurrency,
                quote_currency=quoteCurrency,
                order_type=orderType,
                order_side=orderSide,
                amount=amount,
                price=price,
            )
        return fee

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        """
        Get all trade updates for an order.

        Args:
            order: InFlightOrder to get trades for

        Returns:
            List of TradeUpdate objects
        """
        tradeUpdates = []
        # Apex Pro: Query trades via REST API if needed
        # For MVP, return empty list (trades tracked via user stream)
        return tradeUpdates

    async def _request_order_status(self, trackedOrder: InFlightOrder) -> OrderUpdate:
        """
        Request order status from exchange.

        Args:
            trackedOrder: Order to check status

        Returns:
            OrderUpdate with current status
        """
        exchangeOrderId = trackedOrder.exchange_order_id
        clientOrderId = trackedOrder.client_order_id
        tradingPair = trackedOrder.trading_pair

        apiParams = {
            "orderId": exchangeOrderId,
        }

        updatedOrderData = await self._apiGet(
            path_url=CONSTANTS.OPEN_ORDERS_PATH_URL,
            params=apiParams,
            is_auth_required=True
        )

        if updatedOrderData.get("code") != "0":
            raise ValueError(f"Failed to get order status: {updatedOrderData.get('msg')}")

        orderData = updatedOrderData.get("data", {})
        orderStatus = orderData.get("status", "UNKNOWN")

        # Map Apex status to Hummingbot status
        statusMapping = {
            "PENDING": "PENDING",
            "OPEN": "OPEN",
            "FILLED": "FILLED",
            "PARTIALLY_FILLED": "PARTIALLY_FILLED",
            "CANCELED": "CANCELED",
            "REJECTED": "REJECTED",
        }

        newState = statusMapping.get(orderStatus, "UNKNOWN")

        orderUpdate = OrderUpdate(
            clientOrderId=clientOrderId,
            exchangeOrderId=exchangeOrderId,
            trading_pair=tradingPair,
            updateTimestamp=float(orderData.get("updatedAt", 0)) / 1000,
            newState=newState,
        )

        return orderUpdate

    async def _user_stream_event_listener(self):
        """
        Listen to user stream events (orders, trades, balances).

        For MVP: Poll REST API instead of WebSocket.
        Future enhancement: Implement private WebSocket subscription.
        """
        while True:
            try:
                await asyncio.sleep(5.0)  # Poll every 5 seconds

                # Update balances
                try:
                    await self._updateBalances()
                except Exception as e:
                    self.logger().error(f"Error updating balances: {e}")

                # Poll order statuses
                for clientOrderId, order in self._orderTracker.allUpdatableOrders.items():
                    try:
                        orderUpdate = await self._request_order_status(order)
                        self._orderTracker.processOrderUpdate(orderUpdate=orderUpdate)
                    except Exception as e:
                        self.logger().error(f"Error updating order {clientOrderId}: {e}")

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Error in user stream listener: {e}", exc_info=True)
                await asyncio.sleep(5.0)

    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]):
        """
        Initialize trading pair symbol mapping from exchange info.

        Args:
            exchange_info: Exchange info response from API
        """
        from bidict import bidict

        mapping = bidict()
        
        # First, add all symbols from CONSTANTS.SYMBOL_MAPPING
        for hb_pair, exchange_symbol in CONSTANTS.SYMBOL_MAPPING.items():
            mapping[exchange_symbol] = hb_pair
        
        # Then, add any additional symbols from exchange info
        symbolsList = exchange_info.get("data", {}).get("perpetualContract", [])

        for symbolData in symbolsList:
            # Apex Pro uses "crossSymbolName" (e.g., "ETHUSDT")
            exchangeSymbol = symbolData.get("crossSymbolName")

            if exchangeSymbol and exchangeSymbol not in mapping:
                # Convert exchange symbol to Hummingbot format
                # ETHUSDT → ETH-USDT, BTCUSDT → BTC-USDT
                if exchangeSymbol.endswith("USDT"):
                    baseCurrency = exchangeSymbol.replace("USDT", "")
                    hbTradingPair = f"{baseCurrency}-USDT"
                    mapping[exchangeSymbol] = hbTradingPair

        self._set_trading_pair_symbol_map(mapping)
