#!/usr/bin/env python3
"""
Test script for Nado fill monitoring implementation.

This script tests the new wait_for_fill() functionality to ensure:
1. Orders are placed and return immediately with order_id
2. wait_for_fill() correctly waits for order completion
3. Actual fill prices are logged, not initial order prices
"""

import asyncio
import os
from decimal import Decimal
from exchanges.nado import NadoClient
from exchanges.base import Config

async def test_wait_for_fill():
    """Test the wait_for_fill functionality."""

    # Create Nado client config
    config = Config({
        "ticker": "ETH",
        "contract_id": "",
        "quantity": Decimal("0.01"),
        "tick_size": Decimal("0.01"),
        "close_order_side": "sell",
        "direction": "buy",
    })

    # Initialize Nado client
    client = NadoClient(config)

    try:
        # Connect to Nado
        await client.connect()
        print("✅ Connected to Nado")

        # Get contract attributes
        contract_id, tick_size = await client.get_contract_attributes()
        print(f"✅ Contract ID: {contract_id}, Tick size: {tick_size}")

        # Place a small test order
        print("\n📝 Placing test order...")
        result = await client.place_open_order(
            contract_id,
            Decimal("0.01"),
            "buy"
        )

        if not result.success:
            print(f"❌ Failed to place order: {result.error_message}")
            return

        print(f"✅ Order placed successfully")
        print(f"   Order ID: {result.order_id}")
        print(f"   Status: {result.status}")
        print(f"   Price: ${result.price}")

        # Wait for fill
        print(f"\n⏳ Waiting for order to fill (timeout: 10s)...")
        try:
            fill_info = await client.wait_for_fill(result.order_id, timeout=10)

            print(f"\n📊 Fill Result:")
            print(f"   Status: {fill_info.status}")
            print(f"   Filled Size: {fill_info.filled_size}")
            print(f"   Fill Price: ${fill_info.price}")
            print(f"   Remaining: {fill_info.remaining_size}")

            if fill_info.status == 'FILLED':
                print(f"\n✅ Order successfully filled!")
            elif fill_info.status == 'CANCELLED':
                print(f"\n⚠️ Order was cancelled (likely timed out)")
            else:
                print(f"\n⚠️ Order status: {fill_info.status}")

        except Exception as e:
            print(f"\n❌ Error waiting for fill: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.disconnect()
        print("\n✅ Disconnected from Nado")

if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv('NADO_PRIVATE_KEY'):
        print("❌ NADO_PRIVATE_KEY environment variable not set")
        print("Please set it with: export NADO_PRIVATE_KEY=your_key")
        exit(1)

    asyncio.run(test_wait_for_fill())
