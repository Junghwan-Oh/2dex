#!/usr/bin/env python3.11
"""
Quick script to close residual position on Backpack
"""
import asyncio
import os
import sys
from decimal import Decimal

# Load environment variables
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

sys.path.insert(0, 'pysdk')

from exchanges.backpack import BackpackClient
from pysdk.grvt_ccxt_pro import GrvtCcxtPro

async def main():
    # Initialize Backpack client
    bp_config = {
        "ticker": "ETH",
        "contract_id": "ETH_USDC_PERP",
        "quantity": Decimal("0.2"),
        "tick_size": Decimal("0.01"),
        "close_order_side": "sell",
        "direction": "buy",
    }

    bp_client = BackpackClient(bp_config)

    try:
        await bp_client.initialize()

        # Get current position
        pos = await bp_client.get_account_positions()
        print(f"Current Backpack position: {pos} ETH")

        if abs(pos) > 0:
            print(f"Closing {pos} ETH...")
            side = "sell" if pos > 0 else "buy"
            quantity = abs(pos)

            result = await bp_client.place_market_order(
                contract_id="ETH_USDC_PERP",
                quantity=str(quantity),
                side=side
            )
            print(f"Order placed: {result}")

            # Wait for execution
            await asyncio.sleep(2)

            # Verify position is closed
            pos_after = await bp_client.get_account_positions()
            print(f"Position after close: {pos_after} ETH")
        else:
            print("No position to close")

    finally:
        await bp_client.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
