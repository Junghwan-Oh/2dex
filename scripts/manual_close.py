#!/usr/bin/env python3
"""
Manual Position Close Utility

Usage:
    python3 scripts/manual_close.py [eth|sol|all]

Features:
- Manually close ETH/SOL positions
- Emergency utility for position cleanup
- Places IOC orders to close positions
- Logs all actions to CSV

WARNING: This places live orders on mainnet!
"""

import sys
import os
import asyncio
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from exchanges.nado import NadoClient
    from hedge.DN_pair_eth_sol_nado import DNPairBot, PriceMode
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)


async def close_position(position_type='all'):
    """
    Manually close position(s).

    Args:
        position_type: 'eth', 'sol', or 'all'
    """
    import os

    # Check environment
    if not all(k in os.environ for k in ['NADO_PRIVATE_KEY', 'NADO_MODE', 'NADO_SUBACCOUNT_NAME']):
        print("[ERROR] NADO environment variables not set")
        print("Required: NADO_PRIVATE_KEY, NADO_MODE, NADO_SUBACCOUNT_NAME")
        return 1

    # Check if mainnet
    mode = os.environ.get('NADO_MODE', 'TESTNET')
    if mode == 'MAINNET':
        print("=" * 60)
        print("WARNING: MAINNET MODE")
        print("=" * 60)
        print("This will place REAL orders on mainnet!")
        print(f"Position to close: {position_type.upper()}")

        confirmation = input("\nType 'CONFIRM' to proceed: ")
        if confirmation != 'CONFIRM':
            print("Aborted")
            return 1
    else:
        print(f"Mode: {mode} (Test)")

    print("-" * 60)

    try:
        # Create bot instance
        bot = DNPairBot(
            target_notional=Decimal("100"),
            max_position_eth=Decimal("5"),
            max_position_sol=Decimal("50"),
            order_mode=PriceMode.BBO
        )

        # Close positions
        if position_type in ['eth', 'all']:
            print("\nClosing ETH position...")
            await bot.emergency_unwind_eth()

        if position_type in ['sol', 'all']:
            print("\nClosing SOL position...")
            await bot.emergency_unwind_sol()

        # Verify positions closed
        print("\nVerifying positions...")
        if bot.eth_client:
            eth_pos = await bot.eth_client.get_account_positions()
            print(f"ETH Position: ${eth_pos:.2f}")
        else:
            eth_pos = Decimal("0")
            print("ETH Position: N/A")

        if bot.sol_client:
            sol_pos = await bot.sol_client.get_account_positions()
            print(f"SOL Position: ${sol_pos:.2f}")
        else:
            sol_pos = Decimal("0")
            print("SOL Position: N/A")

        # Check if positions closed
        if abs(eth_pos) < Decimal("0.001") and abs(sol_pos) < Decimal("0.001"):
            print("\n[SUCCESS] All positions closed")
            return 0
        else:
            print("\n[WARNING] Positions may not be fully closed")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Failed to close positions: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/manual_close.py [eth|sol|all]")
        print("\nExamples:")
        print("  python3 scripts/manual_close.py eth   # Close ETH position")
        print("  python3 scripts/manual_close.py sol   # Close SOL position")
        print("  python3 scripts/manual_close.py all   # Close both positions")
        return 1

    position_type = sys.argv[1].lower()

    if position_type not in ['eth', 'sol', 'all']:
        print(f"Invalid position type: {position_type}")
        print("Must be: eth, sol, or all")
        return 1

    return asyncio.run(close_position(position_type))


if __name__ == "__main__":
    sys.exit(main())
