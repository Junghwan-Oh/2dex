"""Close orphaned positions on the wrong subaccount."""
import os
import asyncio
from decimal import Decimal
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.subaccount import SubaccountParams
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.math import to_x18, from_x18
from nado_protocol.utils.expiration import get_expiration_timestamp
from nado_protocol.utils.nonce import gen_order_nonce
from nado_protocol.utils.order import build_appendix, OrderType

async def cleanup_orphaned_positions():
    """Close positions on the context.signer.address subaccount."""
    private_key = os.getenv('NADO_PRIVATE_KEY')
    mode = os.getenv('NADO_MODE', 'MAINNET').upper()
    subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')

    mode_map = {
        'MAINNET': NadoClientMode.MAINNET,
        'DEVNET': NadoClientMode.DEVNET,
    }
    client_mode = mode_map.get(mode, NadoClientMode.MAINNET)
    client = create_nado_client(client_mode, private_key)

    # Use the WRONG address (context.signer) to access orphaned positions
    orphaned_owner = client.context.signer.address
    print(f"Cleaning up positions on orphaned address: {orphaned_owner}")

    products = {
        4: ("ETH", "0.0001"),
        8: ("SOL", "0.01"),
    }

    for product_id, (ticker, price_increment) in products.items():
        # Get position
        orphaned_subaccount = subaccount_to_hex(orphaned_owner, subaccount_name)
        try:
            data = client.context.engine_client.get_subaccount_info(orphaned_subaccount)
            for pos in data.perp_balances:
                if pos.product_id == product_id:
                    size = Decimal(str(from_x18(pos.balance.amount)))
                    if size == 0:
                        continue

                    print(f"\nClosing orphaned {ticker} position: {size}")

                    # Determine close side
                    side = 'sell' if size > 0 else 'buy'
                    close_qty = abs(size)

                    # Get BBO
                    ticker_id = "ETH-PERP_USDT0" if product_id == 4 else "SOL-PERP_USDT0"
                    orderbook = client.context.engine_client.get_orderbook(ticker_id=ticker_id, depth=1)
                    if not orderbook or not orderbook.bids or not orderbook.asks:
                        print(f"  ERROR: Cannot get orderbook for {ticker}")
                        continue

                    best_bid = Decimal(str(orderbook.bids[0][0]))
                    best_ask = Decimal(str(orderbook.asks[0][0]))

                    # Taker pricing for limit order
                    close_price = best_bid if side == 'sell' else best_ask

                    # Build limit order to close (POST-only with timeout)
                    order = OrderParams(
                        sender=SubaccountParams(
                            subaccount_owner=orphaned_owner,
                            subaccount_name=subaccount_name,
                        ),
                        priceX18=to_x18(float(close_price)),
                        amount=to_x18(float(close_qty)) if side == 'buy' else -to_x18(float(close_qty)),
                        expiration=get_expiration_timestamp(60),
                        nonce=gen_order_nonce(),
                        appendix=build_appendix(
                            order_type=OrderType.LIMIT,
                            isolated=True,
                        )
                    )

                    # Place close order
                    result = client.market.place_order({"product_id": product_id, "order": order})
                    if result:
                        print(f"  SUCCESS: Closed {close_qty} @ ${close_price}")
                    else:
                        print(f"  ERROR: Order placement failed")
        except Exception as e:
            print(f"  ERROR: {e}")

if __name__ == "__main__":
    print("WARNING: This will close positions on the ORPHANED subaccount.")
    confirm = input("Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        asyncio.run(cleanup_orphaned_positions())
