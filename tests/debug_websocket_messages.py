#!/usr/bin/env python3
"""
Debug WebSocket Messages - 모든 수신 메시지 로깅
"""

import asyncio
import os
import sys
import json
from decimal import Decimal
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    print("Warning: python-dotenv not installed")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.nado_websocket_client import NadoWebSocketClient
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams
from nado_protocol.client import create_nado_client, NadoClientMode


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


async def debug_websocket():
    """모든 WebSocket 메시지를 캡처해서 로깅."""

    print("=" * 80)
    print("WebSocket Message Debug")
    print("=" * 80)

    # Create Nado client to get credentials
    private_key = os.getenv('NADO_PRIVATE_KEY')
    mode = os.getenv('NADO_MODE', 'TESTNET').upper()

    # Create Nado SDK client
    sdk_client = create_nado_client(
        mode=NadoClientMode.TESTNET,
        signer=private_key
    )

    # Get subaccount
    owner = sdk_client.context.signer.address
    subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=owner,
        subaccount_name=subaccount_name,
    ))

    print(f"\n[1] Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}")

    # Create WebSocket client
    ws_client = NadoWebSocketClient(product_ids=[4])
    await ws_client.connect()
    print("    ✅ Connected")

    # Message counter
    message_counts = {
        "best_bid_offer": 0,
        "book_depth": 0,
        "fill": 0,
        "position_change": 0,
        "order_update": 0,
        "other": 0
    }

    # Log all messages
    all_messages = []

    async def log_all_messages():
        """Log all incoming messages."""
        print("\n[2] Listening to all WebSocket messages...")

        async for message in ws_client.messages():
            msg_type = message.get("type", "unknown")
            message_counts[msg_type] = message_counts.get(msg_type, 0) + 1

            # Store message
            all_messages.append({
                "type": msg_type,
                "data": message
            })

            # Print based on type
            if msg_type in ["fill", "position_change", "order_update"]:
                print(f"\n    📨 {msg_type.upper()}: {json.dumps(message, indent=12)[:200]}...")
            elif msg_type == "best_bid_offer":
                message_counts["best_bid_offer"] += 1
                if message_counts["best_bid_offer"] <= 3:  # Print first 3
                    print(f"    BBO: bid={message.get('bid_price')}, ask={message.get('ask_price')}")
            elif msg_type == "book_depth":
                message_counts["book_depth"] += 1
                if message_counts["book_depth"] <= 3:  # Print first 3
                    bids = len(message.get("bids", []))
                    asks = len(message.get("asks", []))
                    print(f"    BookDepth: {bids} bids, {asks} asks")

    # Subscribe to all streams
    print("\n[3] Subscribing to all streams...")

    # Public streams
    await ws_client.subscribe("best_bid_offer", 4)
    print("    ✅ best_bid_offer")

    await ws_client.subscribe("book_depth", 4)
    print("    ✅ book_depth")

    # Private streams
    await ws_client.subscribe("fill", 4, subaccount=subaccount_hex)
    print("    ✅ fill (subaccount: {subaccount_hex[:10]}...)")

    await ws_client.subscribe("position_change", 4, subaccount=subaccount_hex)
    print("    ✅ position_change")

    await ws_client.subscribe("order_update", 4, subaccount=subaccount_hex)
    print("    ✅ order_update")

    # Start message logger in background
    logger_task = asyncio.create_task(log_all_messages())

    # Wait and place order
    print("\n[4] Waiting 2 seconds for streams to activate...")
    await asyncio.sleep(2)

    print("\n[5] Placing test order via REST...")
    try:
        from exchanges.nado import NadoClient
        config = Config({
            "ticker": "ETH",
            "quantity": Decimal("1"),
            "contract_id": 4,
            "tick_size": Decimal("0.001")
        })
        client = NadoClient(config)
        result = await client.place_ioc_order(4, Decimal("0.01"), "buy")
        print(f"    Order: {result.status}")
        if result.success:
            print(f"    Filled: {result.filled_size} @ ${result.price}")
    except Exception as e:
        print(f"    Error: {e}")

    # Listen for more messages
    print("\n[6] Listening for 10 more seconds...")
    await asyncio.sleep(10)

    # Cancel logger
    logger_task.cancel()
    try:
        await logger_task
    except asyncio.CancelledError:
        pass

    # Summary
    print("\n[7] Message Summary:")
    for msg_type, count in message_counts.items():
        if count > 0:
            print(f"    {msg_type}: {count} messages")

    print(f"\n[8] All fill/position/order_update messages:")
    for msg in all_messages:
        if msg["type"] in ["fill", "position_change", "order_update"]:
            print(f"\n    {msg['type']}:")
            print(f"    {json.dumps(msg['data'], indent=8)[:300]}...")

    # Cleanup
    await ws_client.disconnect()

    print("\n" + "=" * 80)
    print("Debug complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_websocket())
