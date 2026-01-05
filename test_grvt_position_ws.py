#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from pysdk.grvt_ccxt_ws import GrvtCcxtWS
from pysdk.grvt_ccxt_env import GrvtEnv, GrvtWSEndpointType
from pysdk.grvt_ccxt_logging_selector import logger


async def main():
    params = {
        "api_key": os.getenv("GRVT_API_KEY"),
        "trading_account_id": os.getenv("GRVT_TRADING_ACCOUNT_ID"),
        "private_key": os.getenv("GRVT_PRIVATE_KEY"),
        "api_ws_version": "v1",
    }

    loop = asyncio.get_running_loop()
    ws = GrvtCcxtWS(env=GrvtEnv.PROD, loop=loop, logger=logger, parameters=params)

    await ws.initialize()
    print("WebSocket initialized")

    async def position_callback(message):
        print(f"[POSITION] {message}")

    async def order_callback(message):
        print(f"[ORDER] {message}")

    await ws.subscribe(
        stream="position",
        callback=position_callback,
        ws_end_point_type=GrvtWSEndpointType.TRADE_DATA_RPC_FULL,
        params={},
    )
    print("Subscribed to position stream")

    await ws.subscribe(
        stream="order",
        callback=order_callback,
        ws_end_point_type=GrvtWSEndpointType.TRADE_DATA_RPC_FULL,
        params={},
    )
    print("Subscribed to order stream")

    print("\nWaiting for messages (Ctrl+C to stop)...")
    print("Try placing/closing an order on GRVT to see position updates\n")

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
