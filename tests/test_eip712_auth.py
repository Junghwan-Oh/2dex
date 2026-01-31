#!/usr/bin/env python3
"""
EIP-712 WebSocket Authentication Test

Test the authentication flow for private streams (Fill, PositionChange, OrderUpdate).
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
        print(f"Loaded .env from {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print("Warning: python-dotenv not installed")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.nado_websocket_client import NadoWebSocketClient
from exchanges.nado import NadoClient
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def test_eip712_authentication():
    """Test EIP-712 authentication for private streams."""

    print("=" * 80)
    print("EIP-712 WebSocket Authentication Test")
    print("=" * 80)

    # Get credentials
    private_key = os.getenv('NADO_PRIVATE_KEY')
    if not private_key:
        print("ERROR: NADO_PRIVATE_KEY not set")
        return False

    # Create SDK client to get owner address
    from nado_protocol.client import create_nado_client, NadoClientMode
    sdk_client = create_nado_client(
        mode=NadoClientMode.TESTNET,
        signer=private_key
    )
    owner = sdk_client.context.signer.address
    subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')

    # Calculate subaccount
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=owner,
        subaccount_name=subaccount_name,
    ))

    print(f"\n[1] Credentials:")
    print(f"    Owner: {owner}")
    print(f"    Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}")

    # Create WebSocket client with credentials
    print(f"\n[2] Creating WebSocket client with credentials...")
    ws_client = NadoWebSocketClient(
        product_ids=[4],
        private_key=private_key,
        owner=owner,
        subaccount_name=subaccount_name
    )

    # Connect
    print(f"\n[3] Connecting to WebSocket...")
    await ws_client.connect()
    print(f"    ✅ Connected")

    # Subscribe to fill stream (requires authentication)
    print(f"\n[4] Subscribing to Fill stream (requires authentication)...")
    try:
        await ws_client.subscribe("fill", 4, subaccount=subaccount_hex)
        print(f"    ✅ Subscribed to Fill stream")
    except Exception as e:
        print(f"    ❌ Subscribe failed: {e}")
        await ws_client.disconnect()
        return False

    # Listen for messages
    print(f"\n[5] Listening for messages (10 seconds)...")
    message_count = 0
    auth_error_count = 0

    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < 10:
        try:
            message = await asyncio.wait_for(ws_client.messages().__anext__(), timeout=1.0)
            message_count += 1
            msg_type = message.get("type")

            if msg_type == "error":
                auth_error_count += 1
                print(f"    ❌ Error: {message}")
            elif msg_type == "fill":
                print(f"    🎯 FILL: {message}")
            elif msg_type in ["best_bid_offer", "book_depth"]:
                if message_count <= 3:
                    print(f"    📡 {msg_type}")
            else:
                print(f"    📨 {msg_type}: {str(message)[:100]}")

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"    Error receiving message: {e}")
            break

    print(f"\n[6] Results:")
    print(f"    Total messages: {message_count}")
    print(f"    Auth errors: {auth_error_count}")

    # Cleanup
    await ws_client.disconnect()

    print(f"\n" + "=" * 80)
    if auth_error_count == 0:
        print(f"✅ SUCCESS: Authentication working!")
    else:
        print(f"❌ FAILED: Authentication errors detected")
    print(f"=" * 80)

    return auth_error_count == 0


async def test_fill_with_real_order():
    """Test Fill detection by placing a real order."""

    print("\n" + "=" * 80)
    print("Fill Detection Test with Real Order")
    print("=" * 80)

    # Create Nado client
    config = type('Config', (), {
        "ticker": "ETH",
        "quantity": Decimal("1"),
        "contract_id": 4,
        "tick_size": Decimal("0.001")
    })()

    client = NadoClient(config)
    await client.connect()

    # Get subaccount
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=client.owner,
        subaccount_name=client.subaccount_name,
    ))

    # Subscribe to Fill stream
    print(f"\n[1] Subscribing to Fill stream...")
    fill_events = []

    async def on_fill(message):
        fill_events.append(message)
        print(f"    🎯 FILL: order_id={message.get('order_id', 'N/A')[:10]}... "
              f"qty={message.get('filled_quantity', 'N/A')} price={message.get('price', 'N/A')}")

    await client._ws_client.subscribe("fill", 4, callback=on_fill, subaccount=subaccount_hex)
    print(f"    ✅ Subscribed")

    # Wait a bit for subscription to activate
    await asyncio.sleep(2)

    # Place a small order
    print(f"\n[2] Placing small IOC order for 0.01 ETH...")
    result = await client.place_ioc_order(4, Decimal("0.01"), "buy")
    print(f"    Order result: {result.status}")
    if result.success:
        print(f"    Filled: {result.filled_size} @ ${result.price}")
        order_id = result.order_id
    else:
        print(f"    ❌ Order failed: {result.error_message}")
        order_id = None

    # Wait for fill message
    print(f"\n[3] Waiting for Fill WebSocket message (5 seconds)...")
    for i in range(5):
        await asyncio.sleep(1)
        if len(fill_events) > 0:
            print(f"    ✅ Fill message received after {i+1}s!")
            break
        else:
            print(f"    Waiting... {i+1}/5")

    # Results
    print(f"\n[4] Results:")
    print(f"    Fill events received: {len(fill_events)}")

    # Cleanup
    await client.disconnect()

    print(f"\n" + "=" * 80)
    if len(fill_events) > 0:
        print(f"✅ SUCCESS: Fill detection working!")
    else:
        print(f"⚠️  No Fill messages (order may not have filled)")
    print(f"=" * 80)

    return len(fill_events) > 0


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("EIP-712 Authentication Test Suite")
    print("=" * 80)

    # Test 1: Basic authentication
    result1 = asyncio.run(test_eip712_authentication())

    # Test 2: Fill detection with real order
    result2 = asyncio.run(test_fill_with_real_order())

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Authentication): {'PASS ✅' if result1 else 'FAIL ❌'}")
    print(f"Test 2 (Fill Detection): {'PASS ✅' if result2 else 'WARN ⚠️'}")
    print("=" * 80)
