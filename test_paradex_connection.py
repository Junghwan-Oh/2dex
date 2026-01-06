#!/usr/bin/env python3
"""Paradex API 연결 테스트 - SOL"""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

import dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exchanges.paradex import ParadexClient


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


async def test_paradex():
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
    print("Paradex API Connection Test - SOL")
    print("=" * 50)

    try:
        client = ParadexClient(config)
        print("[OK] Client initialized")

        contract_id, tick_size = await client.get_contract_attributes()
        print(f"[OK] Contract: {contract_id}, Tick Size: {tick_size}")

        best_bid, best_ask = await client.fetch_bbo_prices(contract_id)
        spread = best_ask - best_bid
        print(f"[OK] BBO - Bid: {best_bid}, Ask: {best_ask}, Spread: {spread}")

        position = await client.get_account_positions()
        print(f"[OK] Current Position: {position} SOL")

        print("=" * 50)
        print("All tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_paradex())
