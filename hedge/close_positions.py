#!/usr/bin/env python3
"""
Emergency script to close open DN Pair positions.
"""

import asyncio
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

# Add hedge to path
sys.path.insert(0, 'hedge')

from exchanges.nado import NadoClient


class SimpleConfig:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)


async def close_positions():
    """Close open ETH and SOL positions."""
    load_dotenv()

    # Initialize ETH client
    eth_config = SimpleConfig({
        'ticker': 'ETH',
        'contract_id': '4',
        'tick_size': Decimal('0.001'),
    })

    # Initialize SOL client
    sol_config = SimpleConfig({
        'ticker': 'SOL',
        'contract_id': '8',
        'tick_size': Decimal('0.001'),
    })

    eth_client = NadoClient(eth_config)
    sol_client = NadoClient(sol_config)

    await eth_client.connect()
    await sol_client.connect()

    # Get current positions
    eth_pos = await eth_client.get_account_positions()
    sol_pos = await sol_client.get_account_positions()

    print(f"Current positions:")
    print(f"  ETH: {eth_pos}")
    print(f"  SOL: {sol_pos}")

    # Close ETH position (if SHORT)
    if eth_pos < -0.001:
        eth_close_qty = abs(eth_pos)
        print(f"\nClosing ETH SHORT {eth_pos}...")

        result = await eth_client.place_market_order(
            contract_id='4',
            quantity=eth_close_qty,
            side='buy'
        )
        print(f"ETH close result: {result}")

    # Close SOL position (if LONG)
    elif sol_pos > 0.001:
        sol_close_qty = sol_pos
        print(f"\nClosing SOL LONG {sol_pos}...")

        result = await sol_client.place_market_order(
            contract_id='8',
            quantity=sol_close_qty,
            side='sell'
        )
        print(f"SOL close result: {result}")

    # Verify positions are closed
    eth_pos_after = await eth_client.get_account_positions()
    sol_pos_after = await sol_client.get_account_positions()

    print(f"\nPositions after close:")
    print(f"  ETH: {eth_pos_after}")
    print(f"  SOL: {sol_pos_after}")

    await eth_client.disconnect()
    await sol_client.disconnect()

    if abs(eth_pos_after) < 0.001 and abs(sol_pos_after) < 0.001:
        print("\n✅ Positions closed successfully!")
    else:
        print("\n❌ Positions not fully closed!")


if __name__ == "__main__":
    asyncio.run(close_positions())
