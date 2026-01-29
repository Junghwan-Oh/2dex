#!/usr/bin/env python3
"""
DN Pair Bot: Alternating Strategy Execution
Alternating BUY_FIRST / SELL_FIRST cycles with $100 notional
"""
import asyncio
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Load environment variables
load_dotenv()

from hedge.DN_pair_eth_sol_nado import DNPairBot


async def run_alternating_strategy():
    """Run alternating strategy for 5 iterations."""
    print("=" * 70)
    print("DN Pair Bot: Alternating Strategy Execution")
    print("=" * 70)
    print(f"Target Notional: $300 (minimum for ETH tick_size 0.1)")
    print(f"Iterations: 5")
    print(f"Strategy: Alternating BUY_FIRST / SELL_FIRST")
    print("=" * 70)

    # Initialize bot
    bot = DNPairBot(
        target_notional=Decimal("300"),  # $300 notional (minimum for ETH)
        iterations=5,
        fill_timeout=10,  # 10 second timeout for fills
        sleep_time=1,  # 1 second sleep between BUILD and UNWIND
    )

    try:
        await bot.initialize_clients()
        print("\n✓ Clients initialized")

        # Check current prices
        eth_bid, eth_ask = await bot.eth_client.fetch_bbo_prices(bot.eth_client.config.contract_id)
        sol_bid, sol_ask = await bot.sol_client.fetch_bbo_prices(bot.sol_client.config.contract_id)

        print(f"\nCurrent Market Prices:")
        print(f"  ETH: ${eth_bid} / ${eth_ask}")
        print(f"  SOL: ${sol_bid} / ${sol_ask}")

        # Calculate order sizes
        eth_qty = bot.calculate_order_size(eth_ask, 'ETH')
        sol_qty = bot.calculate_order_size(sol_ask, 'SOL')

        print(f"\nOrder Sizes per Leg:")
        print(f"  ETH: {eth_qty} (~${float(eth_qty * eth_ask):.2f})")
        print(f"  SOL: {sol_qty} (~${float(sol_qty * sol_ask):.2f})")

        # Check current positions
        eth_pos = await bot.eth_client.get_account_positions()
        sol_pos = await bot.sol_client.get_account_positions()

        print(f"\nCurrent Positions:")
        print(f"  ETH: {eth_pos}")
        print(f"  SOL: {sol_pos}")

        print("\n" + "=" * 70)
        print("Starting Alternating Strategy...")
        print("=" * 70)

        # Run alternating strategy
        results = await bot.run_alternating_strategy()

        print("\n" + "=" * 70)
        print("Execution Results")
        print("=" * 70)

        for i, result in enumerate(results, 1):
            status = "✓ PASS" if result else "✗ FAIL"
            cycle_type = "BUY_FIRST" if i % 2 == 1 else "SELL_FIRST"
            print(f"  Iteration {i} ({cycle_type}): {status}")

        # Summary
        success_count = sum(1 for r in results if r)
        print(f"\nSummary: {success_count}/{len(results)} cycles successful")

        # Final positions
        eth_pos_final = await bot.eth_client.get_account_positions()
        sol_pos_final = await bot.sol_client.get_account_positions()

        print(f"\nFinal Positions:")
        print(f"  ETH: {eth_pos_final}")
        print(f"  SOL: {sol_pos_final}")

        # Check if positions are flat
        if abs(eth_pos_final) < Decimal("0.01") and abs(sol_pos_final) < Decimal("0.1"):
            print("\n✓ Positions are FLAT - Delta Neutral achieved")
        else:
            print(f"\n⚠ Position drift detected - ETH: {eth_pos_final}, SOL: {sol_pos_final}")

        print("\n" + "=" * 70)
        print("Alternating Strategy Execution Complete")
        print("=" * 70)

        return all(results)

    except Exception as e:
        print(f"\n✗ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await bot.cleanup()
        print("\n✓ Clients disconnected")


if __name__ == "__main__":
    result = asyncio.run(run_alternating_strategy())
    sys.exit(0 if result else 1)
