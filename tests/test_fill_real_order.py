#!/usr/bin/env python3
"""
WebSocket Fill Detection Test - 주문 동시에 실행하며 Fill 수신 확인
"""

import asyncio
import os
import sys
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

from exchanges.nado import NadoClient
from exchanges.nado_fill_handler import FillHandler
from exchanges.nado_position_handler import PositionChangeHandler
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


async def test_fill_detection():
    """주문을 넣고 Fill WebSocket 메시지 수신 확인."""

    print("=" * 80)
    print("WebSocket Fill Detection Test with Real Order")
    print("=" * 80)

    # ETH client
    eth_config = Config({
        "ticker": "ETH",
        "quantity": Decimal("1"),
        "contract_id": 4,
        "tick_size": Decimal("0.001")
    })

    client = NadoClient(eth_config)
    await client.connect()

    # Subaccount
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=client.owner,
        subaccount_name=client.subaccount_name,
    ))

    # Create handlers
    fill_handler = FillHandler(
        product_id=4,
        subaccount=subaccount_hex,
        ws_client=client._ws_client,
        logger=client.logger.logger
    )

    position_handler = PositionChangeHandler(
        product_id=4,
        subaccount=subaccount_hex,
        ws_client=client._ws_client,
        logger=client.logger.logger
    )

    # Subscribe
    print("\n[1] Subscribing to Fill/PositionChange streams...")
    await fill_handler.start()
    await position_handler.start()
    print("    ✅ Subscribed")

    # Setup callbacks
    fill_events = []
    position_events = []

    def on_fill(fill_info):
        fill_events.append(fill_info)
        print(f"\n    🎯 FILL RECEIVED: {fill_info['order_id'][:10]}...")
        print(f"       Quantity: {fill_info['filled_quantity']}")
        print(f"       Price: ${fill_info['price']}")

    def on_position(old_pos, new_pos):
        position_events.append((old_pos, new_pos))
        print(f"\n    📊 POSITION CHANGE: {old_pos} → {new_pos}")

    fill_handler.register_callback(on_fill)
    position_handler.register_callback(on_position)

    # Wait a bit for subscription to activate
    print("\n[2] Waiting for subscriptions to activate...")
    await asyncio.sleep(2)

    # Place an order
    print("\n[3] Placing IOC buy order for 0.01 ETH...")
    result = await client.place_ioc_order(4, Decimal("0.01"), "buy")
    print(f"    Order result: {result.status}")
    if result.success:
        print(f"    Filled: {result.filled_size} @ ${result.price}")
        order_id = result.order_id
        print(f"    Order ID: {order_id[:20]}...")
    else:
        print(f"    ❌ Order failed: {result.error_message}")
        order_id = None

    # Wait for fill message
    print("\n[4] Waiting for Fill WebSocket message (5 seconds)...")
    for i in range(5):
        await asyncio.sleep(1)
        if len(fill_events) > 0:
            print(f"    ✅ Fill message received after {i+1}s!")
            break
        else:
            print(f"    Waiting... {i+1}/5")

    # Check results
    print("\n[5] Results:")
    print(f"    Fill events: {len(fill_events)}")
    print(f"    Position events: {len(position_events)}")
    print(f"    Current position: {position_handler.get_current_position()}")

    if order_id and len(fill_events) > 0:
        print(f"\n    ✅ SUCCESS: Fill detected via WebSocket!")
        print(f"    Expected order: {order_id[:10]}...")
        print(f"    Received fill: {fill_events[0]['order_id'][:10]}...")

        # Check if it's the same order
        if fill_events[0]['order_id'].startswith(order_id[:10]):
            print(f"    ✅ Order ID matches!")
        else:
            print(f"    ⚠️  Different order (might be previous fill)")
    elif order_id:
        print(f"\n    ⚠️  Order filled but WebSocket message not received")
        print(f"    This could mean:")
        print(f"    - WebSocket subscription not working")
        print(f"    - Nado testnet not sending Fill messages")
        print(f"    - Message format different than expected")

    # Cleanup
    await client.disconnect()

    print("\n" + "=" * 80)
    return {
        "fill_events": len(fill_events),
        "position_events": len(position_events),
        "order_placed": order_id is not None,
        "success": len(fill_events) > 0
    }


if __name__ == "__main__":
    result = asyncio.run(test_fill_detection())
    print(f"\nFinal Result: {result}")
