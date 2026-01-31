#!/usr/bin/env python3
"""Test EIP-712 authentication and subscription only."""

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


async def test_auth():
    private_key = os.getenv('NADO_PRIVATE_KEY')
    sdk_client = create_nado_client(mode=NadoClientMode.MAINNET, signer=private_key)

    owner = sdk_client.context.signer.address
    subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')

    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=owner,
        subaccount_name=subaccount_name,
    ))

    print("=" * 60)
    print("EIP-712 Authentication Test - MAINNET")
    print("=" * 60)
    print(f'Owner: {owner}')
    print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')

    # Create WebSocket client
    ws_client = NadoWebSocketClient(
        product_ids=[4],
        private_key=private_key,
        owner=owner,
        subaccount_name=subaccount_name
    )

    await ws_client.connect()
    print('✅ Connected to MAINNET WebSocket')

    # Subscribe to public stream (should work without auth)
    print('\n[1] Subscribing to public stream (book_depth)...')
    await ws_client.subscribe('book_depth', 4)
    print('    ✅ Subscribed')

    # Wait for public messages
    print('\n[2] Waiting for public messages (3 seconds)...')
    public_count = 0
    for _ in range(30):
        try:
            msg = await asyncio.wait_for(ws_client.messages().__anext__(), timeout=0.1)
            if msg.get('type') == 'book_depth':
                public_count += 1
                if public_count <= 3:
                    print(f'    📡 book_depth: {len(msg.get("bids", []))} bids, {len(msg.get("asks", []))} asks')
        except asyncio.TimeoutError:
            continue

    print(f'    Public messages received: {public_count}')

    # Subscribe to private stream (requires auth)
    print('\n[3] Subscribing to private stream (fill)...')
    fill_events = []

    async def on_fill(msg):
        fill_events.append(msg)
        print(f'    🎯 FILL: {msg}')

    try:
        await ws_client.subscribe('fill', 4, callback=on_fill, subaccount=subaccount_hex)
        print('    ✅ Subscribed to fill stream')
    except Exception as e:
        print(f'    ❌ Subscribe failed: {e}')
        await ws_client.disconnect()
        return False

    # Wait for private messages
    print('\n[4] Waiting for private messages (5 seconds)...')
    for i in range(5):
        await asyncio.sleep(1)
        print(f'    Waiting... {i+1}/5 (fill events: {len(fill_events)})')

    await ws_client.disconnect()

    print('\n' + '=' * 60)
    print(f'Results:')
    print(f'  Public messages: {public_count}')
    print(f'  Fill events: {len(fill_events)}')
    print('=' * 60)

    return public_count > 0


if __name__ == '__main__':
    result = asyncio.run(test_auth())
    sys.exit(0 if result else 1)
