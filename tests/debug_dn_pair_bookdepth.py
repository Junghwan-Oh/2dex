#!/usr/bin/env python3
"""
DN Pair Bot BookDepth Debug

BookDepth 데이터가 DN_pair_bot에서 수신되는지 확인
"""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    import os
    # Use absolute path
    env_path = "/Users/botfarmer/2dex/.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        print("Warning: .env file not found")
except ImportError:
    print("Warning: python-dotenv not installed")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hedge.DN_pair_eth_sol_nado import DNPairBot


async def debug_dn_pair_bookdepth():
    """DN Pair Bot에서 BookDepth 확인."""

    print("=" * 80)
    print("DN Pair Bot BookDepth Debug")
    print("=" * 80)

    # Create bot
    config_dict = {
        "target_notional": Decimal("100"),
        "iterations": 1,
        "sleep_time": 0,
        "eth_ticker": "ETH",
        "sol_ticker": "SOL",
        "eth_contract_id": "4",
        "sol_contract_id": "8",
        "eth_tick_size": Decimal("0.001"),
        "sol_tick_size": Decimal("0.1"),
        "mode": "ALTERNATING"
    }

    bot = DNPairBot(config_dict)

    # Initialize
    print("\n[1] Initializing bot...")
    await bot.initialize_clients()

    # Check WebSocket connection
    print("\n[2] Checking ETH client WebSocket...")
    print(f"    ETH client _ws_connected: {bot.eth_client._ws_connected}")
    print(f"    ETH client _ws_client: {bot.eth_client._ws_client}")

    if bot.eth_client._ws_connected and bot.eth_client._ws_client:
        print(f"    ETH subscriptions: {bot.eth_client._ws_client._subscriptions}")

        # Check BookDepth handler
        eth_handler = bot.eth_client.get_bookdepth_handler()
        if eth_handler:
            print(f"    ETH BookDepth handler: {eth_handler}")
            print(f"    ETH BookDepth product_id: {eth_handler.product_id}")

            # Wait for data
            print("\n[3] Waiting for ETH BookDepth data (5 seconds)...")
            for i in range(5):
                await asyncio.sleep(1)
                print(f"    Waited {i+1}s...")

            # Check order book
            print(f"\n[4] ETH Order Book State:")
            print(f"    Bids count: {len(eth_handler.bids)}")
            print(f"    Asks count: {len(eth_handler.asks)}")

            best_bid, bid_qty = eth_handler.get_best_bid()
            best_ask, ask_qty = eth_handler.get_best_ask()
            print(f"    Best bid: {best_bid} (qty: {bid_qty})")
            print(f"    Best ask: {best_ask} (qty: {ask_qty})")

            # Test slippage
            print(f"\n[5] Testing slippage estimation...")
            slippage = await bot.eth_client.estimate_slippage("buy", Decimal("0.01"))
            print(f"    Buy 0.01 ETH slippage: {slippage} bps")

            if slippage >= 999999:
                print(f"    ❌ BookDepth not working!")
            else:
                print(f"    ✅ BookDepth working!")
        else:
            print(f"    ❌ No BookDepth handler")
    else:
        print(f"    ❌ WebSocket not connected!")

    # Cleanup
    bot.shutdown()

    print("\n" + "=" * 80)
    print("Debug complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_dn_pair_bookdepth())
