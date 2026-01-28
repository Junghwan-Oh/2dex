"""
Utility functions for Apex Pro Exchange Connector

Symbol format conversion, decimal precision helpers, and trading pair validation.
"""

from decimal import Decimal
from typing import Optional

import hummingbot.connector.exchange.apex_pro.apex_pro_constants as CONSTANTS


def convert_to_exchange_trading_pair(hbTradingPair: str) -> str:
    """
    Convert Hummingbot trading pair format to Apex exchange format.

    Args:
        hbTradingPair: Trading pair in Hummingbot format (e.g., "BTC-USDT")

    Returns:
        Trading pair in Apex format (e.g., "BTCUSDT")

    Example:
        >>> convertToExchangeTradingPair("BTC-USDT")
        "BTCUSDT"
    """
    if hbTradingPair in CONSTANTS.SYMBOL_MAPPING:
        return CONSTANTS.SYMBOL_MAPPING[hbTradingPair]

    # Fallback: remove hyphen
    return hbTradingPair.replace("-", "")


def convert_from_exchange_trading_pair(exchangeTradingPair: str) -> str:
    """
    Convert Apex exchange trading pair format to Hummingbot format.

    Args:
        exchangeTradingPair: Trading pair in Apex format (e.g., "BTCUSDT")

    Returns:
        Trading pair in Hummingbot format (e.g., "BTC-USDT")

    Example:
        >>> convertFromExchangeTradingPair("BTCUSDT")
        "BTC-USDT"
    """
    if exchangeTradingPair in CONSTANTS.REVERSE_SYMBOL_MAPPING:
        return CONSTANTS.REVERSE_SYMBOL_MAPPING[exchangeTradingPair]

    # Fallback: add hyphen before USDT
    if "USDT" in exchangeTradingPair:
        baseCurrency = exchangeTradingPair.replace("USDT", "")
        return f"{baseCurrency}-USDT"

    return exchangeTradingPair


def round_price(price: Decimal, tickSize: Decimal = Decimal(str(CONSTANTS.DEFAULT_TICK_SIZE))) -> Decimal:
    """
    Round price to the nearest tick size.

    Args:
        price: Price to round
        tickSize: Minimum price increment

    Returns:
        Rounded price

    Example:
        >>> roundPrice(Decimal("100.456"), Decimal("0.1"))
        Decimal("100.5")
    """
    if tickSize == 0:
        return price

    return (price // tickSize) * tickSize


def round_quantity(quantity: Decimal, stepSize: Decimal = Decimal(str(CONSTANTS.DEFAULT_STEP_SIZE))) -> Decimal:
    """
    Round quantity to the nearest step size.

    Args:
        quantity: Quantity to round
        stepSize: Minimum quantity increment

    Returns:
        Rounded quantity

    Example:
        >>> roundQuantity(Decimal("0.1234"), Decimal("0.001"))
        Decimal("0.123")
    """
    if stepSize == 0:
        return quantity

    return (quantity // stepSize) * stepSize


def validateTradingPair(tradingPair: str) -> bool:
    """
    Validate if a trading pair is supported.

    Args:
        tradingPair: Trading pair in Hummingbot format (e.g., "BTC-USDT")

    Returns:
        True if supported, False otherwise
    """
    return tradingPair in CONSTANTS.SYMBOL_MAPPING or "-" in tradingPair


def get_domain(network: str = "mainnet") -> str:
    """
    Get domain configuration based on network.

    Args:
        network: "mainnet" or "testnet"

    Returns:
        Domain identifier
    """
    if network.lower() == "testnet":
        return "apex_pro_test"
    return "apex_pro_main"


def get_rest_api_url(network: str = "mainnet") -> str:
    """
    Get REST API URL based on network.

    Args:
        network: "mainnet" or "testnet"

    Returns:
        REST API base URL
    """
    if network.lower() == "testnet":
        return CONSTANTS.APEX_OMNI_HTTP_TEST
    return CONSTANTS.APEX_OMNI_HTTP_MAIN


def get_ws_url(network: str = "mainnet", private: bool = False) -> str:
    """
    Get WebSocket URL based on network and channel type.

    Args:
        network: "mainnet" or "testnet"
        private: True for private channel, False for public

    Returns:
        WebSocket URL
    """
    if network.lower() == "testnet":
        return CONSTANTS.APEX_OMNI_WS_PRIVATE_TEST if private else CONSTANTS.APEX_OMNI_WS_TEST
    return CONSTANTS.APEX_OMNI_WS_PRIVATE_MAIN if private else CONSTANTS.APEX_OMNI_WS_MAIN


def get_network_id(network: str = "mainnet") -> int:
    """
    Get blockchain network ID.

    Args:
        network: "mainnet" or "testnet"

    Returns:
        Network ID (chain ID)
    """
    if network.lower() == "testnet":
        return CONSTANTS.NETWORKID_OMNI_TEST_BNB
    return CONSTANTS.NETWORKID_OMNI_MAIN_ARB


def rest_url(pathUrl: str, domain: str = "apex_pro_main") -> str:
    """
    Creates a full URL for provided REST endpoint.

    Args:
        pathUrl: REST endpoint path
        domain: Apex domain ("apex_pro_main" or "apex_pro_test")

    Returns:
        Full URL to the endpoint
    """
    import hummingbot.connector.exchange.apex_pro.apex_pro_constants as CONSTANTS
    
    baseUrl = CONSTANTS.APEX_OMNI_HTTP_MAIN if "main" in domain else CONSTANTS.APEX_OMNI_HTTP_TEST
    return baseUrl + pathUrl


def public_rest_url(path_url: str, domain: str = "apex_pro_main") -> str:
    """
    Alias for rest_url for compatibility with ExchangePyBase.

    Args:
        path_url: REST endpoint path
        domain: Apex domain ("apex_pro_main" or "apex_pro_test")

    Returns:
        Full URL to the endpoint
    """
    return rest_url(path_url, domain)

def private_rest_url(path_url: str, domain: str = "apex_pro_main") -> str:
    """
    Alias for rest_url for private API endpoints (same as public).

    Args:
        path_url: REST endpoint path
        domain: Apex domain ("apex_pro_main" or "apex_pro_test")

    Returns:
        Full URL to the endpoint
    """
    return rest_url(path_url, domain)


def build_api_factory(
    throttler=None,
    timeSynchronizer=None,
    domain: str = "apex_pro_main",
    auth=None,
):
    """
    Build WebAssistantsFactory for Apex Pro API requests.

    Args:
        throttler: AsyncThrottler instance for rate limiting
        timeSynchronizer: TimeSynchronizer instance for time sync
        domain: Apex domain identifier
        auth: Authentication instance (ApexProAuth)

    Returns:
        WebAssistantsFactory instance
    """
    from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
    from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
    from hummingbot.core.utils.tracking_nonce import get_tracking_nonce
    import hummingbot.connector.exchange.apex_pro.apex_pro_constants as CONSTANTS
    
    throttler = throttler or AsyncThrottler(CONSTANTS.RATE_LIMITS)
    
    apiFactory = WebAssistantsFactory(
        throttler=throttler,
        auth=auth,
    )
    
    return apiFactory
