#!/usr/bin/env python3
"""GRVT WebSocket 연결 테스트 - SOL"""

import asyncio
import os
import sys
from decimal import Decimal

import dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exchanges.grvt import GrvtClient


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


async def test_grvt_websocket():
    dotenv.load_dotenv()

    config = Config(
        {
            "ticker": "SOL",
            "contract_id": "",
            "quantity": Decimal("0.1"),
            "tick_size": Decimal("0.01"),
            "close_order_side": "sell",
            "direction": "buy",
        }
    )

    print("=" * 50)
    print("GRVT WebSocket Connection Test - SOL")
    print("=" * 50)

    order_updates = []

    def order_handler(data):
        order_updates.append(data)
        print(f"[WS] Order update received: {data.get('status', 'unknown')}")

    try:
        client = GrvtClient(config)
        print("[OK] Client initialized")

        contract_id, tick_size = await client.get_contract_attributes()
        print(f"[OK] Contract: {contract_id}")

        client.setup_order_update_handler(order_handler)
        print("[OK] Order handler set up")

        await client.connect()
        print("[OK] WebSocket connected")

        print("[INFO] Waiting 5 seconds for connection stability...")
        await asyncio.sleep(5)

        await client.disconnect()
        print("[OK] WebSocket disconnected")

        print("=" * 50)
        print("WebSocket test passed!")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_grvt_websocket())
