"""
Temporary script to place Paradex SHORT order
"""
import sys
import os
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

# Set environment variables BEFORE importing ParadexClient
os.environ['PARADEX_L1_ADDRESS'] = '0x0BA21b57e01A574DE6bc09faA66877756a547897'
os.environ['PARADEX_L1_PRIVATE_KEY'] = '0x25ba735e47010ecec6c260a37ed036c68b978edc9a389b44352fd32697d7cdd'

from paradex_client import ParadexClient

def main():
    print("=" * 60)
    print("Paradex Mainnet - BTC SHORT Order")
    print("=" * 60)

    # Initialize client
    print("\n[1] Initializing Paradex Client...")
    client = ParadexClient(environment='mainnet')
    print(f"   [OK] {client}")

    # Check current BTC price
    print("\n[2] Checking BTC-USD-PERP price...")
    ticker = client.get_ticker('BTC-USD-PERP')
    last_price = float(ticker.get('last_price', 0))
    mark_price = float(ticker.get('mark_price', 0))
    print(f"   Last Price: ${last_price:,.2f}")
    print(f"   Mark Price: ${mark_price:,.2f}")

    # Place SHORT order
    print("\n[3] Placing SHORT Order...")
    print(f"   Market: BTC-USD-PERP")
    print(f"   Side: SELL")
    print(f"   Price: $90,400")
    print(f"   Size: 100")

    order = client.create_order(
        market='BTC-USD-PERP',
        side='SELL',
        order_type='LIMIT',
        size='100',
        price='90400',
        post_only=True,
        reduce_only=False
    )

    if order:
        print("\n" + "=" * 60)
        print("[ORDER SUCCESS]")
        print("=" * 60)
        print(f"  Order ID: {order.get('id', 'N/A')}")
        print(f"  Status: {order.get('status', 'N/A')}")
        print(f"  Market: {order.get('market', 'N/A')}")
        print(f"  Side: {order.get('side', 'N/A')}")
        print(f"  Size: {order.get('size', 'N/A')}")
        print(f"  Price: ${order.get('price', 'N/A')}")
    else:
        print("\n[ORDER FAILED]")

if __name__ == "__main__":
    main()
