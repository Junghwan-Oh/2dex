"""
Constants for Apex Pro Exchange Connector

API endpoints, WebSocket URLs, and configuration constants for Apex Pro integration.
"""

from typing import Dict
from hummingbot.core.api_throttler.data_types import RateLimit

# Exchange name
EXCHANGE_NAME = "apex_pro"

# API Domains
DEFAULT_DOMAIN = "apex_pro_main"

# REST API Endpoints
APEX_OMNI_HTTP_MAIN = "https://omni.apex.exchange"
APEX_OMNI_HTTP_TEST = "https://qa.omni.apex.exchange"

# WebSocket Endpoints
APEX_OMNI_WS_MAIN = "wss://quote.omni.apex.exchange/realtime_public"
APEX_OMNI_WS_TEST = "wss://quote.qa.omni.apex.exchange/realtime_public"

# WebSocket Private Endpoints
APEX_OMNI_WS_PRIVATE_MAIN = "wss://quote.omni.apex.exchange/realtime_private"
APEX_OMNI_WS_PRIVATE_TEST = "wss://quote.qa.omni.apex.exchange/realtime_private"

# Network IDs
NETWORKID_OMNI_MAIN_ARB = 42161  # Arbitrum mainnet
NETWORKID_OMNI_TEST_BNB = 97     # BSC testnet

# API Endpoints Paths
SERVER_TIME_PATH_URL = "/api/v1/time"
EXCHANGE_INFO_PATH_URL = "/api/v3/symbols"
ACCOUNT_INFO_PATH_URL = "/api/v3/account"
BALANCES_PATH_URL = "/api/v3/account"
ORDER_PATH_URL = "/api/v3/createOrder"
CANCEL_ORDER_PATH_URL = "/api/v3/deleteOrder"
OPEN_ORDERS_PATH_URL = "/api/v3/openOrders"
ORDER_HISTORY_PATH_URL = "/api/v3/historyOrders"
TRADES_PATH_URL = "/api/v3/trades"

# Order Book Depth Endpoint
ORDERBOOK_SNAPSHOT_PATH_URL = "/api/v1/depth"

# WebSocket Public Channels
WS_CHANNEL_ORDERBOOK = "orderbook"
WS_CHANNEL_TRADES = "trade"
WS_CHANNEL_TICKER = "ticker"
WS_CHANNEL_KLINE = "kline"

# WebSocket Private Channels
WS_CHANNEL_ORDERS = "orders"
WS_CHANNEL_POSITIONS = "positions"
WS_CHANNEL_ACCOUNT = "account"

# Rate Limits (requests per minute)
RATE_LIMITS = [
    # Public endpoints
    RateLimit(limit_id=SERVER_TIME_PATH_URL, limit=600, time_interval=60),
    RateLimit(limit_id=EXCHANGE_INFO_PATH_URL, limit=600, time_interval=60),
    RateLimit(limit_id=ORDERBOOK_SNAPSHOT_PATH_URL, limit=600, time_interval=60),
    # Private endpoints
    RateLimit(limit_id=ACCOUNT_INFO_PATH_URL, limit=300, time_interval=60),
    RateLimit(limit_id=BALANCES_PATH_URL, limit=300, time_interval=60),
    RateLimit(limit_id=OPEN_ORDERS_PATH_URL, limit=300, time_interval=60),
    RateLimit(limit_id=ORDER_HISTORY_PATH_URL, limit=300, time_interval=60),
    RateLimit(limit_id=TRADES_PATH_URL, limit=300, time_interval=60),
    # Order placement
    RateLimit(limit_id=ORDER_PATH_URL, limit=100, time_interval=60),
    RateLimit(limit_id=CANCEL_ORDER_PATH_URL, limit=100, time_interval=60),
]

# Trading Constants
MIN_ORDER_SIZE = 0.001  # Minimum order size in base currency
MAX_ORDER_ID_LEN = 64   # Maximum length for client order IDs
HBOT_ORDER_ID_PREFIX = "HBOT-"

# Order Types
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT_MAKER = "POST_ONLY"

# Order Sides
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"

# Time In Force
TIME_IN_FORCE_GTC = "GOOD_TIL_CANCEL"
TIME_IN_FORCE_IOC = "IMMEDIATE_OR_CANCEL"
TIME_IN_FORCE_FOK = "FILL_OR_KILL"
TIME_IN_FORCE_POST_ONLY = "POST_ONLY"

# Trade Category (Apex uses "PERPETUAL" for all perpetual contracts)
TRADE_CATEGORY = "PERPETUAL"

# Default Trading Pairs
DEFAULT_TRADING_PAIRS = [
    "BTC-USDT",
    "ETH-USDT",
    "SOL-USDT",
    "ARB-USDT",
]

# Symbol Format Mapping (Hummingbot ↔ Apex)
SYMBOL_MAPPING: Dict[str, str] = {
    "BTC-USDT": "BTCUSDT",
    "ETH-USDT": "ETHUSDT",
    "SOL-USDT": "SOLUSDT",
    "ARB-USDT": "ARBUSDT",
    "MATIC-USDT": "MATICUSDT",
    "OP-USDT": "OPUSDT",
}

# Reverse mapping (Apex → Hummingbot)
REVERSE_SYMBOL_MAPPING = {v: k for k, v in SYMBOL_MAPPING.items()}

# Tick Sizes and Step Sizes (default values, fetched from API in production)
DEFAULT_TICK_SIZE = 0.1  # Price precision
DEFAULT_STEP_SIZE = 0.001  # Quantity precision

# Fee Structure (maker/taker)
DEFAULT_MAKER_FEE = 0.0002  # 0.02% maker fee
DEFAULT_TAKER_FEE = 0.0005  # 0.05% taker fee

# Timeout Settings
API_CALL_TIMEOUT = 10  # seconds
WS_HEARTBEAT_TIME_INTERVAL = 30  # seconds

# Order Status Mapping (Apex → Hummingbot)
ORDER_STATUS = {
    "PENDING": "PENDING",
    "OPEN": "OPEN",
    "FILLED": "FILLED",
    "PARTIALLY_FILLED": "PARTIALLY_FILLED",
    "CANCELED": "CANCELED",
    "REJECTED": "REJECTED",
    "EXPIRED": "EXPIRED",
}

# Aliases for consistent naming (referenced in apex_pro_exchange.py)
ORDER_PLACE_PATH_URL = ORDER_PATH_URL
ORDER_CANCEL_PATH_URL = CANCEL_ORDER_PATH_URL
BALANCE_PATH_URL = BALANCES_PATH_URL

# API Request Configuration
API_REQUEST_RETRY = 3  # Number of retries for failed API requests
