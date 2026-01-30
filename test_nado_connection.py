#!/usr/bin/env python3
"""
Test Nado API connection and functionality.
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

from exchanges.nado import NadoClient
from hedge.DN_pair_eth_sol_nado import Config


async def test_nado_connection():
    """Test Nado API connection."""
    print("=" * 60)
    print("Nado API Connection Test")
    print("=" * 60)

    # Check environment variables
    print("\n[1] Environment Variables Check:")
    private_key = os.getenv('NADO_PRIVATE_KEY')
    mode = os.getenv('NADO_MODE', 'MAINNET')
    print(f"  NADO_PRIVATE_KEY: {'✓ Set' if private_key else '✗ Missing'}")
    print(f"  NADO_MODE: {mode}")

    if not private_key:
        print("\n✗ ERROR: NADO_PRIVATE_KEY not set!")
        return False

    # Test ETH client
    print("\n[2] ETH Client Test:")
    eth_config = Config({
        'ticker': 'ETH',
        'contract_id': '2',
        'tick_size': Decimal('0.1'),
        'min_size': Decimal('0.01'),
    })

    try:
        eth_client = NadoClient(eth_config)
        await eth_client.connect()
        print("  ✓ ETH client connected")

        # Test BBO prices
        print("\n[3] ETH BBO Prices Test:")
        eth_bid, eth_ask = await eth_client.fetch_bbo_prices(eth_config.contract_id)
        print(f"  ETH Bid: ${eth_bid}")
        print(f"  ETH Ask: ${eth_ask}")

        if eth_bid > 0 and eth_ask > 0:
            print("  ✓ ETH prices are valid")
        else:
            print("  ✗ ETH prices are invalid (0)")

        # Test positions
        print("\n[4] ETH Position Test:")
        eth_position = await eth_client.get_account_positions()
        print(f"  ETH Position: {eth_position}")

        await eth_client.disconnect()

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test SOL client
    print("\n[5] SOL Client Test:")
    sol_config = Config({
        'ticker': 'SOL',
        'contract_id': '4',
        'tick_size': Decimal('0.001'),
        'min_size': Decimal('0.1'),
    })

    try:
        sol_client = NadoClient(sol_config)
        await sol_client.connect()
        print("  ✓ SOL client connected")

        # Test BBO prices
        print("\n[6] SOL BBO Prices Test:")
        sol_bid, sol_ask = await sol_client.fetch_bbo_prices(sol_config.contract_id)
        print(f"  SOL Bid: ${sol_bid}")
        print(f"  SOL Ask: ${sol_ask}")

        if sol_bid > 0 and sol_ask > 0:
            print("  ✓ SOL prices are valid")
        else:
            print("  ✗ SOL prices are invalid (0)")

        # Test positions
        print("\n[7] SOL Position Test:")
        sol_position = await sol_client.get_account_positions()
        print(f"  SOL Position: {sol_position}")

        await sol_client.disconnect()

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✓ Nado API connection test completed")
    print("=" * 60)
    return True


if __name__ == "__main__":
    result = asyncio.run(test_nado_connection())
    sys.exit(0 if result else 1)
