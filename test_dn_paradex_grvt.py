#!/usr/bin/env python3
"""
Integration test for DN Hedge Bot (Paradex + GRVT)
Tests connection, market data, and optionally order placement.
"""

import asyncio
import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()


async def test_grvt():
    print("=" * 50)
    print("GRVT Connection Test")
    print("=" * 50)

    try:
        from pysdk.grvt_ccxt import GrvtCcxt
        from pysdk.grvt_ccxt_env import GrvtEnv

        params = {
            "trading_account_id": os.getenv("GRVT_TRADING_ACCOUNT_ID"),
            "private_key": os.getenv("GRVT_PRIVATE_KEY"),
            "api_key": os.getenv("GRVT_API_KEY"),
        }

        if not all(params.values()):
            print("[SKIP] GRVT credentials not configured")
            return False

        client = GrvtCcxt(env=GrvtEnv.PROD, parameters=params)

        markets = client.fetch_markets()
        sol_market = next(
            (
                m
                for m in markets
                if m.get("base") == "SOL" and m.get("kind") == "PERPETUAL"
            ),
            None,
        )

        if not sol_market:
            print("[ERROR] SOL market not found")
            return False

        contract = sol_market.get("instrument")
        min_size = sol_market.get("min_size")
        tick_size = sol_market.get("tick_size")

        print(f"[OK] Contract: {contract}")
        print(f"[OK] Min Size: {min_size} SOL")
        print(f"[OK] Tick Size: ${tick_size}")

        order_book = client.fetch_order_book(contract, limit=10)
        if order_book and order_book.get("bids") and order_book.get("asks"):
            bid = Decimal(order_book["bids"][0]["price"])
            ask = Decimal(order_book["asks"][0]["price"])
            print(f"[OK] BBO: Bid ${bid}, Ask ${ask}, Spread ${ask - bid}")

        positions = client.fetch_positions()
        sol_pos = next((p for p in positions if p.get("instrument") == contract), None)
        pos_size = sol_pos.get("size", "0") if sol_pos else "0"
        print(f"[OK] Position: {pos_size} SOL")

        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_paradex():
    print("\n" + "=" * 50)
    print("Paradex Connection Test")
    print("=" * 50)

    l1_addr = os.getenv("PARADEX_L1_ADDRESS")
    l2_key = os.getenv("PARADEX_L2_PRIVATE_KEY")

    if not l1_addr or not l2_key:
        print("[SKIP] Paradex credentials not configured")
        print("Required in .env:")
        print("  PARADEX_L1_ADDRESS=0x...")
        print("  PARADEX_L2_PRIVATE_KEY=0x...")
        print("  PARADEX_ENVIRONMENT=prod")
        return False

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from exchanges.paradex import ParadexClient

        class Config:
            def __init__(self):
                self.ticker = "SOL"
                self.contract_id = ""
                self.quantity = Decimal("0.1")
                self.tick_size = Decimal("0.001")
                self.close_order_side = "sell"
                self.direction = "buy"

        config = Config()
        client = ParadexClient(config)

        contract_id, tick_size = await client.get_contract_attributes()
        print(f"[OK] Contract: {contract_id}")
        print(f"[OK] Tick Size: ${tick_size}")

        bid, ask = await client.fetch_bbo_prices(contract_id)
        print(f"[OK] BBO: Bid ${bid}, Ask ${ask}, Spread ${ask - bid}")

        position = await client.get_account_positions()
        print(f"[OK] Position: {position} SOL")

        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_price_comparison():
    print("\n" + "=" * 50)
    print("Cross-Exchange Price Comparison")
    print("=" * 50)

    grvt_price = None
    paradex_price = None

    try:
        from pysdk.grvt_ccxt import GrvtCcxt
        from pysdk.grvt_ccxt_env import GrvtEnv

        params = {
            "trading_account_id": os.getenv("GRVT_TRADING_ACCOUNT_ID"),
            "private_key": os.getenv("GRVT_PRIVATE_KEY"),
            "api_key": os.getenv("GRVT_API_KEY"),
        }

        if all(params.values()):
            client = GrvtCcxt(env=GrvtEnv.PROD, parameters=params)
            ob = client.fetch_order_book("SOL_USDT_Perp", limit=10)
            if ob and ob.get("bids") and ob.get("asks"):
                grvt_bid = Decimal(ob["bids"][0]["price"])
                grvt_ask = Decimal(ob["asks"][0]["price"])
                grvt_price = (grvt_bid + grvt_ask) / 2
                print(
                    f"GRVT SOL: Bid ${grvt_bid}, Ask ${grvt_ask}, Mid ${grvt_price:.4f}"
                )
    except Exception as e:
        print(f"GRVT Error: {e}")

    try:
        if os.getenv("PARADEX_L1_ADDRESS"):
            from exchanges.paradex import ParadexClient

            class Config:
                def __init__(self):
                    self.ticker = "SOL"
                    self.contract_id = "SOL-USD-PERP"
                    self.quantity = Decimal("0.1")
                    self.tick_size = Decimal("0.001")
                    self.close_order_side = "sell"
                    self.direction = "buy"

            client = ParadexClient(Config())
            bid, ask = await client.fetch_bbo_prices("SOL-USD-PERP")
            paradex_price = (bid + ask) / 2
            print(f"Paradex SOL: Bid ${bid}, Ask ${ask}, Mid ${paradex_price:.4f}")
    except Exception as e:
        print(f"Paradex Error: {e}")

    if grvt_price and paradex_price:
        diff = abs(grvt_price - paradex_price)
        diff_pct = (diff / min(grvt_price, paradex_price)) * 100
        print(f"\nPrice Difference: ${diff:.4f} ({diff_pct:.4f}%)")

        if grvt_price > paradex_price:
            print("Arbitrage: Buy on Paradex, Sell on GRVT")
        else:
            print("Arbitrage: Buy on GRVT, Sell on Paradex")


async def main():
    print("DN Hedge Bot Integration Test")
    print("Paradex (PRIMARY) + GRVT (HEDGE)")
    print("=" * 50)

    grvt_ok = await test_grvt()
    paradex_ok = await test_paradex()

    if grvt_ok and paradex_ok:
        await test_price_comparison()

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"GRVT: {'PASS' if grvt_ok else 'FAIL/SKIP'}")
    print(f"Paradex: {'PASS' if paradex_ok else 'FAIL/SKIP'}")

    if grvt_ok and paradex_ok:
        print("\nReady to run DN Hedge Bot:")
        print(
            "  conda run -n quant python hedge_mode.py --exchange paradex --ticker SOL --size 0.1 --iter 10"
        )
    elif grvt_ok and not paradex_ok:
        print("\nParadex setup required. Add to .env:")
        print("  PARADEX_L1_ADDRESS=0x<wallet>")
        print("  PARADEX_L2_PRIVATE_KEY=0x<key>")
        print("  PARADEX_ENVIRONMENT=prod")


if __name__ == "__main__":
    asyncio.run(main())
