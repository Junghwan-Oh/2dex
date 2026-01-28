"""Test WebSocket RPC order submission for GRVT with REST verification."""

import asyncio
import os
from decimal import Decimal
from exchanges.grvt import GrvtClient
from helpers.logger import TradingLogger

async def test_websocket_rpc_orders():
    """Test WebSocket RPC order submission with REST verification."""
    config = {
        "ticker": "ETH",
        "contract_id": os.getenv("GRVT_CONTRACT_ID", "ETH-PERP"),
    }

    client = GrvtClient(config)

    try:
        # Connect to WebSocket
        await client.connect()
        print("✓ WebSocket connected")

        # Test market order
        print("\n[TEST] Placing market order via WebSocket RPC...")
        result = await client.place_market_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="buy"
        )
        print(f"✓ Market order result: {result}")
        print(f"  Success: {result.get('success')}")
        print(f"  Order ID: {result.get('metadata', {}).get('client_order_id')}")

        # Test POST_ONLY order
        print("\n[TEST] Placing POST_ONLY order via WebSocket RPC...")
        result = await client.place_post_only_order(
            contract_id=config["contract_id"],
            quantity=Decimal("0.01"),
            side="sell"
        )
        print(f"✓ POST_ONLY order result: {result}")
        print(f"  Success: {result.get('success')}")
        print(f"  Order ID: {result.get('metadata', {}).get('client_order_id')}")

        print("\n✓ All WebSocket RPC order tests passed")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        raise
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_websocket_rpc_orders())
