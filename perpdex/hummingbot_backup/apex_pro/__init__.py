"""
Apex Pro Exchange Connector for Hummingbot

This connector integrates the Apex Pro decentralized exchange with Hummingbot's
trading framework, enabling strategies like Avellaneda market making with native
TP/SL support.

Features:
- WebSocket real-time orderbook and trade feeds
- Native Take Profit / Stop Loss order support
- Maker-only order placement (POST_ONLY)
- ZK-rollup based settlement (Layer 2)
- Reuses proven apex trading bot logic

Architecture:
- Thin wrapper pattern: delegates to AvellanedaApexClient
- Runtime sys.path injection for apex imports
- Async/sync bridge for Hummingbot compatibility
"""

from hummingbot.connector.exchange.apex_pro.apex_pro_exchange import (
    ApexProExchange,
)

__all__ = [
    "ApexProExchange",
]


# Apex Pro connector metadata
CONNECTOR_NAME = "apex_pro"
CONNECTOR_DISPLAY_NAME = "Apex Pro"
CONNECTOR_TYPE = "exchange"
CONNECTOR_CATEGORY = "derivative"

# Exchange information
EXCHANGE_URL = "https://app.apex.exchange/"
EXCHANGE_DOCS_URL = "https://docs.apex.exchange/"
EXCHANGE_API_DOCS_URL = "https://api-docs.apex.exchange/"

# Supported features
SUPPORTED_FEATURES = [
    "LIMIT_ORDERS",
    "MARKET_ORDERS",
    "POST_ONLY_ORDERS",
    "NATIVE_TPSL",
    "WEBSOCKET_FEEDS",
    "MAKER_REBATES",
]
