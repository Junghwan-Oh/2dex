#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

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
        print("GRVT SOL Fee Structure:")
        print(f"  Maker Fee: {m.get('maker', 'N/A')}")
        print(f"  Taker Fee: {m.get('taker', 'N/A')}")
        print(f"  All fields: {list(m.keys())}")
        break
