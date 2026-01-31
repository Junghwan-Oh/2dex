#!/usr/bin/env python3
"""
Debug BookDepth Data Flow

This script tests and debugs the BookDepth WebSocket data flow.
It adds comprehensive logging to understand why slippage returns 999999 bps.
"""

import asyncio
import sys
import os
from decimal import Decimal
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print("Warning: python-dotenv not installed, skipping .env load")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Debug import
print("\n[DEBUG] Testing WebSocket imports...")
try:
    from exchanges.nado_websocket_client import NadoWebSocketClient
    print("    NadoWebSocketClient: OK")
except Exception as e:
    print(f"    NadoWebSocketClient: FAILED - {e}")

try:
    from exchanges.nado_bbo_handler import BBOHandler
    print("    BBOHandler: OK")
except Exception as e:
    print(f"    BBOHandler: FAILED - {e}")

try:
    from exchanges.nado_bookdepth_handler import BookDepthHandler
    print("    BookDepthHandler: OK")
except Exception as e:
    print(f"    BookDepthHandler: FAILED - {e}")

try:
    import websockets
    print("    websockets module: OK")
except ImportError as e:
    print(f"    websockets module: FAILED - {e}")

from exchanges.nado import NadoClient


class Config:
    """Simple config class that converts dict to object with attributes."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


async def debug_bookdepth():
    """Debug BookDepth data flow."""

    print("=" * 80)
    print("BookDepth Debug Test")
    print("=" * 80)

    # Create ETH client
    eth_config = Config({
        "ticker": "ETH",
        "quantity": Decimal("1"),
        "contract_id": 4,
        "tick_size": Decimal("0.001")
    })

    client = NadoClient(eth_config)

    # Connect (including WebSocket)
    print("\n[1] Connecting to Nado WebSocket...")
    print(f"    _use_websocket: {client._use_websocket}")

    # Directly call _connect_websocket to catch any exceptions
    try:
        await client._connect_websocket()
        print("    _connect_websocket() succeeded")
    except Exception as e:
        print(f"    _connect_websocket() failed: {e}")
        import traceback
        traceback.print_exc()

    print(f"    _ws_connected: {client._ws_connected}")
    print(f"    _ws_client: {client._ws_client}")
    print(f"    _bookdepth_handler: {client._bookdepth_handler}")
    print("    Connected!")

    # Get BookDepth handler
    print("\n[2] Getting BookDepth handler...")
    handler = client.get_bookdepth_handler()
    if handler is None:
        print("    ERROR: BookDepth handler is None!")
        print("    WebSocket may not be connected properly.")
        await client.disconnect()
        return

    print(f"    BookDepth handler: {handler}")
    print(f"    Product ID: {handler.product_id}")

    # Wait for data to arrive
    print("\n[3] Waiting for BookDepth data (5 seconds)...")
    for i in range(5):
        await asyncio.sleep(1)
        print(f"    Waited {i+1}s...")

    # Check order book state
    print("\n[4] Checking order book state...")
    print(f"    Bids count: {len(handler.bids)}")
    print(f"    Asks count: {len(handler.asks)}")

    best_bid, bid_qty = handler.get_best_bid()
    best_ask, ask_qty = handler.get_best_ask()

    print(f"    Best bid: {best_bid} (qty: {bid_qty})")
    print(f"    Best ask: {best_ask} (qty: {ask_qty})")

    # Test slippage estimation
    print("\n[5] Testing slippage estimation...")
    test_quantity = Decimal("0.01")  # 0.01 ETH

    buy_slippage = handler.estimate_slippage("buy", test_quantity)
    sell_slippage = handler.estimate_slippage("sell", test_quantity)

    print(f"    Buy {test_quantity} ETH slippage: {buy_slippage} bps")
    print(f"    Sell {test_quantity} ETH slippage: {sell_slippage} bps")

    if buy_slippage == 999999 or sell_slippage == 999999:
        print("    WARNING: Slippage is 999999 bps - insufficient liquidity or no data!")
    else:
        print("    OK: Slippage is within normal range")

    # Get order book summary
    print("\n[6] Order book summary...")
    summary = handler.get_order_book_summary(max_levels=3)
    print(f"    Product: {summary['product_id']}")
    print(f"    Best bid: {summary['best_bid']} ({summary['bid_qty']})")
    print(f"    Best ask: {summary['best_ask']} ({summary['ask_qty']})")
    print(f"    Spread: {summary['spread']}")
    print(f"    Total bid liquidity: {summary['total_bid_liquidity']}")
    print(f"    Total ask liquidity: {summary['total_ask_liquidity']}")

    print("\n    Bid levels:")
    for level in summary['bid_levels']:
        print(f"      Level {level['level']}: {level['price']} ({level['quantity']})")

    print("\n    Ask levels:")
    for level in summary['ask_levels']:
        print(f"      Level {level['level']}: {level['price']} ({level['quantity']})")

    # Check WebSocket subscriptions
    print("\n[7] Checking WebSocket subscriptions...")
    print(f"    Subscriptions: {client._ws_client._subscriptions}")

    # Disconnect
    print("\n[8] Disconnecting...")
    await client.disconnect()

    print("\n" + "=" * 80)
    print("Debug test completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_bookdepth())
