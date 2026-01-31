#!/usr/bin/env python3
"""
Position Checker - Monitor ETH and SOL positions

Usage:
    python3 scripts/check_positions.py

Features:
- Shows current positions for ETH and SOL
- Compares against target max positions
- Warning at 1.2x target, Critical at 1.5x target
- Exit code 1 if positions exceed critical threshold
"""

import sys
import os
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from exchanges.nado import NadoClient
    from hedge.DN_pair_eth_sol_nado import DNPairBot, PriceMode
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)


async def check_positions():
    """Check current positions and display warnings."""
    import asyncio

    # Target max positions from config
    max_position_eth = Decimal("5")
    max_position_sol = Decimal("50")

    # Warning thresholds
    eth_warning = max_position_eth * Decimal("1.2")  # 6.0
    eth_critical = max_position_eth * Decimal("1.5")  # 7.5
    sol_warning = max_position_sol * Decimal("1.2")  # 60.0
    sol_critical = max_position_sol * Decimal("1.5")  # 75.0

    print("=" * 60)
    print("POSITION CHECKER")
    print("=" * 60)
    print(f"Target Max Positions: ETH={max_position_eth}, SOL={max_position_sol}")
    print(f"Warning Thresholds: ETH={eth_warning}, SOL={sol_warning}")
    print(f"Critical Thresholds: ETH={eth_critical}, SOL={sol_critical}")
    print("-" * 60)

    # Check if we can connect to exchange
    try:
        # Try to read from environment
        import os

        if not all(k in os.environ for k in ['NADO_PRIVATE_KEY', 'NADO_MODE', 'NADO_SUBACCOUNT_NAME']):
            print("\n[WARNING] NADO environment variables not set")
            print("Showing position check logic without live data...\n")

            # Simulate position check
            print("ETH Position: [Not available - check exchange directly]")
            print("SOL Position: [Not available - check exchange directly]")
            print("\nTo check live positions, ensure NADO credentials are set.")
            return 0

        # Create bot instance
        bot = DNPairBot(
            target_notional=Decimal("100"),
            max_position_eth=max_position_eth,
            max_position_sol=max_position_sol,
            order_mode=PriceMode.BBO
        )

        # Get positions
        eth_pos = await bot.eth_client.get_account_positions() if bot.eth_client else Decimal("0")
        sol_pos = await bot.sol_client.get_account_positions() if bot.sol_client else Decimal("0")

        # Display ETH position
        print(f"\nETH Position: ${eth_pos:.2f}")
        if abs(eth_pos) > eth_critical:
            print(f"  [CRITICAL] ETH position exceeds {eth_critical:.2f}")
        elif abs(eth_pos) > eth_warning:
            print(f"  [WARNING] ETH position exceeds {eth_warning:.2f}")
        elif abs(eth_pos) > max_position_eth:
            print(f"  [INFO] ETH position exceeds target {max_position_eth:.2f}")
        else:
            print(f"  [OK] ETH position within target")

        # Display SOL position
        print(f"\nSOL Position: ${sol_pos:.2f}")
        if abs(sol_pos) > sol_critical:
            print(f"  [CRITICAL] SOL position exceeds {sol_critical:.2f}")
        elif abs(sol_pos) > sol_warning:
            print(f"  [WARNING] SOL position exceeds {sol_warning:.2f}")
        elif abs(sol_pos) > max_position_sol:
            print(f"  [INFO] SOL position exceeds target {max_position_sol:.2f}")
        else:
            print(f"  [OK] SOL position within target")

        # Check ratio
        if eth_pos != Decimal("0"):
            ratio = abs(sol_pos / eth_pos)
            print(f"\nSOL/ETH Ratio: {ratio:.2f}x")
            if ratio > Decimal("40"):
                print(f"  [CRITICAL] Ratio exceeds 40x (SOL accumulation detected)")
            elif ratio > Decimal("10"):
                print(f"  [WARNING] Ratio exceeds 10x")
            else:
                print(f"  [OK] Ratio within normal range")

        # Exit with error if critical threshold exceeded
        if abs(eth_pos) > eth_critical or abs(sol_pos) > sol_critical:
            print("\n[CRITICAL] Position thresholds exceeded - manual intervention required")
            return 1

        print("\n[OK] All positions within acceptable thresholds")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Failed to check positions: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(check_positions()))
