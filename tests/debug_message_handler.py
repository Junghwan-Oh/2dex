#!/usr/bin/env python3
"""Debug WebSocket message handler - check if messages are arriving."""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))
os.environ['NADO_MODE'] = 'MAINNET'

from exchanges.nado_websocket_client import NadoWebSocketClient
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def debug_handler():
    private_key = os.getenv('NADO_PRIVATE_KEY')
    sdk_client = create_nado_client(mode=NadoClientMode.MAINNET, signer=private_key)

    owner = sdk_client.context.signer.address
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=owner,
        subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default'),
    ))

    print("=" * 60)
    print("Debug Message Handler - MAINNET")
    print("=" * 60)

    # Create WebSocket client
    ws_client = NadoWebSocketClient(
        product_ids=[4],
        private_key=private_key,
        owner=owner,
        subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default')
    )

    # Monkey-patch _process_message to log ALL messages
    original_process = ws_client._process_message
    message_count = {'total': 0, 'by_type': {}}

    async def logged_process(data):
        message_count['total'] += 1
        msg_type = data.get('type', 'unknown')
        message_count['by_type'][msg_type] = message_count['by_type'].get(msg_type, 0) + 1

        print(f'  [MSG #{message_count["total"]}] type={msg_type}')

        if message_count['total'] <= 5:
            print(f'    Data: {str(data)[:200]}...')

        await original_process(data)

    ws_client._process_message = logged_process

    await ws_client.connect()
    print('✅ Connected')

    # Subscribe
    print('\n[1] Subscribing to streams...')
    await ws_client.subscribe('book_depth', 4)
    await ws_client.subscribe('fill', 4, subaccount=subaccount_hex)
    print('    ✅ Subscribed')

    # Wait
    print('\n[2] Waiting for messages (5 seconds)...')
    await asyncio.sleep(5)

    # Check queue
    print('\n[3] Message queue size:', ws_client._message_queue.qsize())

    await ws_client.disconnect()

    print('\n' + '=' * 60)
    print(f'Results:')
    print(f'  Total messages processed: {message_count["total"]}')
    print(f'  By type: {message_count["by_type"]}')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(debug_handler())
