#!/usr/bin/env python3
"""Check SOL market info on GRVT and Paradex."""

import os
import sys
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()


def check_grvt_sol():
    """Check GRVT SOL market info."""
    print("=" * 50)
    print("GRVT SOL Market Info")
    print("=" * 50)

    try:
        from pysdk.grvt_ccxt import GrvtCcxt
        from pysdk.grvt_ccxt_env import GrvtEnv

        params = {
            "trading_account_id": os.getenv("GRVT_TRADING_ACCOUNT_ID"),
            "private_key": os.getenv("GRVT_PRIVATE_KEY"),
            "api_key": os.getenv("GRVT_API_KEY"),
        }
        client = GrvtCcxt(env=GrvtEnv.PROD, parameters=params)

        markets = client.fetch_markets()
        for m in markets:
            if m.get("base") == "SOL" and m.get("kind") == "PERPETUAL":
                print(f"Contract: {m.get('instrument')}")
                print(f"Min Size: {m.get('min_size')} SOL")
                print(f"Size Increment: {m.get('size_increment')}")
                print(f"Tick Size: ${m.get('tick_size')}")

                # Calculate min notional with current price
                order_book = client.fetch_order_book(m.get("instrument"), limit=1)
                if order_book and order_book.get("asks"):
                    price = Decimal(order_book["asks"][0]["price"])
                    min_size = Decimal(m.get("min_size", "0"))
                    min_notional = price * min_size
                    print(f"Current Price: ${price}")
                    print(f"Min Notional: ~${min_notional:.2f}")
                break
        else:
            print("SOL market not found")

    except Exception as e:
        print(f"[ERROR] {e}")


def check_paradex_sol():
    """Check Paradex SOL market info."""
    print("\n" + "=" * 50)
    print("Paradex SOL Market Info")
    print("=" * 50)

    try:
        # Check if Paradex credentials are set
        if not os.getenv("PARADEX_L1_ADDRESS"):
            print("[SKIP] PARADEX_L1_ADDRESS not set in .env")
            print("Add the following to .env:")
            print("  PARADEX_L1_ADDRESS=0x<your EVM wallet>")
            print("  PARADEX_L2_PRIVATE_KEY=0x<Paradex private key>")
            print("  PARADEX_ENVIRONMENT=prod")
            return

        from paradex_py import Paradex
        from paradex_py.environment import PROD

        paradex = Paradex(env=PROD, logger=None)

        # Get SOL market info
        markets = paradex.api_client.fetch_markets({"market": "SOL-USD-PERP"})
        if markets and markets.get("results"):
            m = markets["results"][0]
            print(f"Contract: {m.get('symbol')}")
            print(f"Min Notional: ${m.get('min_notional')}")
            print(f"Order Size Increment: {m.get('order_size_increment')} SOL")
            print(f"Tick Size: ${m.get('price_tick_size')}")

            # Get current price
            summary = paradex.api_client.fetch_markets_summary(
                {"market": "SOL-USD-PERP"}
            )
            if summary and summary.get("results"):
                s = summary["results"][0]
                price = Decimal(s.get("mark_price", "0"))
                min_notional = Decimal(m.get("min_notional", "0"))
                min_size = min_notional / price if price > 0 else Decimal("0")
                print(f"Current Price: ${price}")
                print(f"Min Size (calculated): ~{min_size:.4f} SOL")
        else:
            print("SOL market not found")

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    check_grvt_sol()
    check_paradex_sol()
