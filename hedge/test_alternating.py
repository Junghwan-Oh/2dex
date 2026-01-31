#!/usr/bin/env python3
"""Test alternating DN pair strategy."""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))
os.environ['NADO_MODE'] = 'MAINNET'

from hedge.DN_pair_eth_sol_nado import DNPairBot


async def test_alternating():
    """Test alternating strategy with 5 cycles."""
    print("=" * 60)
    print("Alternating DN Pair Test (5 cycles)")
    print("=" * 60)

    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=5,
        sleep_time=1
    )

    await bot.initialize_clients()

    # Wait for BookDepth data to be ready
    print("\nWaiting for BookDepth data...")
    if not await bot.wait_for_bookdepth_ready(timeout_seconds=10):
        print("ERROR: BookDepth data not ready after timeout")
        bot.shutdown()
        return

    # Check initial positions
    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()
    print(f"Initial positions - ETH: {eth_pos}, SOL: {sol_pos}")

    # Run alternating strategy
    print("\nRunning alternating strategy...")
    results = await bot.run_alternating_strategy()

    # Check final positions
    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()
    print(f"\nFinal positions - ETH: {eth_pos}, SOL: {sol_pos}")

    # Print results
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    successful = sum(results)
    print(f"Successful: {successful}/5 ({successful/5*100:.1f}%)")
    print(f"Failed: {5 - successful}")
    print(f"{'='*60}")

    # Close positions if needed
    if abs(eth_pos) > Decimal("0.001") or abs(sol_pos) > Decimal("0.001"):
        print("\nClosing positions...")
        await bot.force_close_all_positions()

    bot.shutdown()

    # Print CSV records
    print("\nTrade records from CSV:")
    print("-" * 60)
    with open("logs/DN_pair_eth_sol_nado_trades.csv", "r") as f:
        for line in f.readlines()[-10:]:
            print(line.strip())


if __name__ == '__main__':
    import sys
    asyncio.run(test_alternating())
