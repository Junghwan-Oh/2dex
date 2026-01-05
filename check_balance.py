#!/usr/bin/env python3
import asyncio
import os
import sys

sys.path.append(".")
from dotenv import load_dotenv

load_dotenv()

from exchanges.paradex import ParadexClient
from exchanges.grvt import GrvtClient


class Config:
    def __init__(self):
        self.ticker = "SOL"
        self.contract_id = ""
        self.quantity = 0.1
        self.tick_size = 0.01
        self.close_order_side = "sell"
        self.direction = "buy"


async def main():
    from paradex_py import Paradex
    from paradex_py.environment import PROD
    from starknet_py.common import int_from_hex

    l1_address = os.getenv("PARADEX_L1_ADDRESS")
    l2_private_key_hex = os.getenv("PARADEX_L2_PRIVATE_KEY")
    l2_private_key = int_from_hex(l2_private_key_hex)

    paradex = Paradex(
        env=PROD,
        l1_address=l1_address,
        l2_private_key=l2_private_key,
    )

    print("=== Paradex Account ===")

    positions = paradex.api_client.fetch_positions()
    for pos in positions.get("results", []):
        if pos.get("size") != "0":
            print(f"  {pos.get('market')}: {pos.get('size')} ({pos.get('side')})")

    balances = paradex.api_client.fetch_balances()
    for bal in balances.get("results", []):
        print(f"  {bal.get('token')}: {bal.get('size')}")

    print("\n=== GRVT Account ===")
    config = Config()
    grvt = GrvtClient(config)

    positions = grvt.rest_client.fetch_positions()
    print("GRVT Positions:")
    for pos in positions:
        if float(pos.get("contracts", 0)) != 0:
            print(
                f"  {pos.get('symbol')}: {pos.get('contracts')} @ {pos.get('entryPrice')}"
            )

    balance = grvt.rest_client.fetch_balance()
    print(f"GRVT Balance: {balance}")


asyncio.run(main())
