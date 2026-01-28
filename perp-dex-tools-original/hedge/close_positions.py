"""Quick script to close all positions on both exchanges."""
import asyncio
import sys
from decimal import Decimal

async def close_positions():
    # Import after adding path
    sys.path.insert(0, 'F:/Dropbox/dexbot/perp-dex-tools-original/hedge')

    from exchanges.grvt import GrvtClient
    from exchanges.backpack import BackpackClient

    ticker = 'ETH'

    print("Checking and closing positions...")

    # Close Backpack position
    print("\n1. Checking Backpack...")
    bp = BackpackClient(ticker)
    try:
        await bp.connect()
        bp_pos = await bp.get_account_positions()
        print(f"   Backpack position: {bp_pos}")

        if bp_pos != Decimal("0"):
            print(f"   Closing {bp_pos} ETH on Backpack...")
            if bp_pos > 0:
                await bp.place_market_order("ETH_USDC_PERP", "sell", abs(bp_pos))
            else:
                await bp.place_market_order("ETH_USDC_PERP", "buy", abs(bp_pos))
            print("   Backpack position closed")
        else:
            print("   No Backpack position to close")
    finally:
        await bp.disconnect()

    # Close GRVT position
    print("\n2. Checking GRVT...")
    grvt = GrvtClient(ticker)
    try:
        await grvt.connect()
        grvt_pos = await grvt.get_account_positions()
        print(f"   GRVT position: {grvt_pos}")

        if grvt_pos != Decimal("0"):
            print(f"   Closing {grvt_pos} ETH on GRVT...")
            if grvt_pos > 0:
                await grvt.place_market_order("ETH_USDT_Perp", "sell", abs(grvt_pos))
            else:
                await grvt.place_market_order("ETH_USDT_Perp", "buy", abs(grvt_pos))
            print("   GRVT position closed")
        else:
            print("   No GRVT position to close")
    finally:
        await grvt.disconnect()

    print("\n✓ All positions closed")

if __name__ == "__main__":
    asyncio.run(close_positions())
