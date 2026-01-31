#!/usr/bin/env python3
"""
WebSocket Fill Integration Test - 실제 연결 테스트

This test verifies that Fill and PositionChange handlers work with real Nado WebSocket.
"""

import asyncio
import os
import sys
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
        sys.exit(1)
except ImportError:
    print("Warning: python-dotenv not installed")
    sys.exit(1)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.nado import NadoClient
from exchanges.nado_fill_handler import FillHandler
from exchanges.nado_position_handler import PositionChangeHandler


class Config:
    """Simple config class that converts dict to object with attributes."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


async def test_fill_integration():
    """Test Fill and PositionChange handlers with real WebSocket."""

    print("=" * 80)
    print("WebSocket Fill/Position Integration Test")
    print("=" * 80)

    # Create ETH client
    eth_config = Config({
        "ticker": "ETH",
        "quantity": Decimal("1"),
        "contract_id": 4,
        "tick_size": Decimal("0.001")
    })

    client = NadoClient(eth_config)

    # Connect WebSocket
    print("\n[1] Connecting to Nado WebSocket...")
    await client.connect()
    print("    Connected!")

    # Get subaccount hex
    print(f"\n[2] Getting subaccount info...")
    from nado_protocol.utils.bytes32 import subaccount_to_hex
    from nado_protocol.utils.subaccount import SubaccountParams

    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=client.owner,
        subaccount_name=client.subaccount_name,
    ))
    print(f"    Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}")

    # Create Fill handler
    print(f"\n[3] Creating Fill handler...")
    fill_handler = FillHandler(
        product_id=4,
        subaccount=subaccount_hex,
        ws_client=client._ws_client,
        logger=client.logger.logger
    )
    print("    Fill handler created")

    # Create PositionChange handler
    print(f"\n[4] Creating PositionChange handler...")
    position_handler = PositionChangeHandler(
        product_id=4,
        subaccount=subaccount_hex,
        ws_client=client._ws_client,
        logger=client.logger.logger
    )
    print("    PositionChange handler created")

    # Subscribe to streams
    print(f"\n[5] Subscribing to Fill stream...")
    await fill_handler.start()
    print("    Subscribed to Fill stream")

    print(f"\n[6] Subscribing to PositionChange stream...")
    await position_handler.start()
    print("    Subscribed to PositionChange stream")

    # Check subscriptions
    print(f"\n[7] Checking active subscriptions...")
    print(f"    Subscriptions: {client._ws_client._subscriptions}")

    # Wait for messages
    print(f"\n[8] Waiting for messages (10 seconds)...")
    print("    (Place an order on Nado testnet to generate fill messages)")

    fill_received = []
    position_received = []

    def on_fill(fill_info):
        fill_received.append(fill_info)
        print(f"    [FILL] Order {fill_info['order_id'][:10]}... filled: {fill_info['filled_quantity']} @ ${fill_info['price']}")

    def on_position(old_pos, new_pos):
        position_received.append((old_pos, new_pos))
        print(f"    [POSITION] {old_pos} → {new_pos}")

    fill_handler.register_callback(on_fill)
    position_handler.register_callback(on_position)

    await asyncio.sleep(10)

    # Summary
    print(f"\n[9] Summary:")
    print(f"    Fill messages received: {len(fill_received)}")
    print(f"    Position messages received: {len(position_received)}")
    print(f"    Current position: {position_handler.get_current_position()}")

    # Disconnect
    print(f"\n[10] Disconnecting...")
    await client.disconnect()

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

    # Return results
    return {
        "fill_count": len(fill_received),
        "position_count": len(position_received),
        "current_position": str(position_handler.get_current_position())
    }


if __name__ == "__main__":
    result = asyncio.run(test_fill_integration())
    print(f"\nResult: {result}")
