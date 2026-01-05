#!/usr/bin/env python3
import asyncio
import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()


async def close_all_positions():
    print("=" * 50)
    print("Closing all positions")
    print("=" * 50)

    from pysdk.grvt_ccxt import GrvtCcxt
    from pysdk.grvt_ccxt_env import GrvtEnv

    grvt_params = {
        "trading_account_id": os.getenv("GRVT_TRADING_ACCOUNT_ID"),
        "private_key": os.getenv("GRVT_PRIVATE_KEY"),
        "api_key": os.getenv("GRVT_API_KEY"),
    }
    grvt = GrvtCcxt(env=GrvtEnv.PROD, parameters=grvt_params)

    positions = grvt.fetch_positions()
    for pos in positions:
        if pos.get("instrument") == "SOL_USDT_Perp":
            size = Decimal(pos.get("size", "0"))
            if size != 0:
                side = "buy" if size < 0 else "sell"
                qty = abs(size)
                print(f"[GRVT] Closing {qty} SOL ({side})")
                grvt.create_order(
                    symbol="SOL_USDT_Perp", order_type="market", side=side, amount=qty
                )
                print(f"[GRVT] Closed")

    from exchanges.paradex import ParadexClient

    class Config:
        def __init__(self):
            self.ticker = "SOL"
            self.contract_id = "SOL-USD-PERP"
            self.quantity = Decimal("0.1")
            self.tick_size = Decimal("0.001")
            self.close_order_side = "sell"
            self.direction = "buy"

    paradex = ParadexClient(Config())
    await paradex.get_contract_attributes()
    try:
        pos = await paradex.get_account_positions()
    except Exception as e:
        print(f"[Paradex] Error getting position: {e}")
        pos = Decimal("0")

    if pos != 0:
        side = "buy" if pos < 0 else "sell"
        qty = abs(pos)
        print(f"[Paradex] Closing {qty} SOL ({side})")

        bid, ask = await paradex.fetch_bbo_prices("SOL-USD-PERP")
        price = ask if side == "buy" else bid

        from paradex_py.common.order import Order, OrderSide, OrderType

        order_side = OrderSide.Buy if side == "buy" else OrderSide.Sell

        order = Order(
            market="SOL-USD-PERP",
            order_type=OrderType.Market,
            order_side=order_side,
            size=qty,
        )
        paradex.paradex.api_client.submit_order(order)
        print(f"[Paradex] Closed")

    print("\nFinal check...")
    await asyncio.sleep(2)

    positions = grvt.fetch_positions()
    grvt_pos = 0
    for pos in positions:
        if pos.get("instrument") == "SOL_USDT_Perp":
            grvt_pos = Decimal(pos.get("size", "0"))

    paradex_pos = await paradex.get_account_positions()

    print(f"[GRVT] Position: {grvt_pos}")
    print(f"[Paradex] Position: {paradex_pos}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(close_all_positions())
