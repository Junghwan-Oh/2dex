#!/usr/bin/env python3
"""Log ALL WebSocket messages during order execution."""

import asyncio
import os
import sys
import json
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
from exchanges.nado import NadoClient


async def log_all_messages():
    private_key = os.getenv('NADO_PRIVATE_KEY')
    sdk_client = create_nado_client(mode=NadoClientMode.MAINNET, signer=private_key)

    owner = sdk_client.context.signer.address
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=owner,
        subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default'),
    ))

    print("=" * 60)
    print("ALL WebSocket Messages Logger")
    print("=" * 60)

    # Create WebSocket client
    ws_client = NadoWebSocketClient(
        product_ids=[4],
        private_key=private_key,
        owner=owner,
        subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default')
    )

    # Monkey-patch to log ALL messages
    original_process = ws_client._process_message
    all_messages = []

    async def logged_process(data):
        all_messages.append(data)
        msg_type = data.get('type', 'response')
        print(f'  [MSG] type={msg_type}')

        if msg_type in ['fill', 'position_change', 'order_update']:
            print(f'    📨 PRIVATE STREAM: {json.dumps(data, indent=12)[:300]}...')
        elif msg_type == 'response':
            if 'error' in data:
                print(f'    ❌ ERROR: {data.get("error", "Unknown error")}')
            else:
                print(f'    ✅ Response: {data}')
        elif msg_type in ['book_depth', 'best_bid_offer']:
            # Only print first 3
            count = sum(1 for m in all_messages if m.get('type') == msg_type)
            if count <= 3:
                print(f'    📡 {msg_type}')

        await original_process(data)

    ws_client._process_message = logged_process

    await ws_client.connect()
    print('✅ Connected')

    # Subscribe
    print('\n[1] Subscribing to Fill stream...')
    await ws_client.subscribe('fill', 4, subaccount=subaccount_hex)
    print('    ✅ Subscribed')

    # Wait
    await asyncio.sleep(2)

    # Place order using REST client
    print('\n[2] Placing order via REST...')
    config = type('Config', (), {
        'ticker': 'ETH',
        'quantity': Decimal('1'),
        'contract_id': 4,
        'tick_size': Decimal('0.001')
    })()

    client = NadoClient(config)
    await client.connect()

    # Get BBO and place aggressive order
    bid, ask = await client.fetch_bbo_prices(4)
    print(f'    BBO: bid={bid}, ask={ask}')

    if ask and ask > 0:
        print(f'    Placing aggressive buy order...')
        result = await client.place_ioc_order(4, Decimal('0.01'), 'buy')
        print(f'    Result: {result.status}')
        if result.success:
            print(f'    ✅ FILLED: {result.filled_size} @ ${result.price}')
            order_id = result.order_id
            print(f'    Order ID: {order_id[:20]}...')

            # Close position
            print(f'    Closing position...')
            close_result = await client.place_ioc_order(4, Decimal('0.01'), 'sell')
            if close_result.success:
                print(f'    ✅ Closed: {close_result.filled_size} @ ${close_result.price}')

    # Listen for more messages
    print('\n[3] Listening for 10 more seconds...')
    for i in range(10):
        await asyncio.sleep(1)
        count = len([m for m in all_messages if m.get('type') in ['fill', 'position_change']])
        print(f'    {i+1}/10 - Fill/Position messages: {count}')

    # Summary
    print(f'\n[4] Summary:')
    print(f'    Total messages: {len(all_messages)}')

    msg_counts = {}
    for msg in all_messages:
        msg_type = msg.get('type', 'unknown')
        msg_counts[msg_type] = msg_counts.get(msg_type, 0) + 1

    for msg_type, count in sorted(msg_counts.items()):
        print(f'    {msg_type}: {count}')

    print(f'\n[5] All Fill/PositionChange/OrderUpdate messages:')
    for msg in all_messages:
        if msg.get('type') in ['fill', 'position_change', 'order_update']:
            print(f'\n    {json.dumps(msg, indent=8)[:400]}...')

    await ws_client.disconnect()
    await client.disconnect()

    print('\n' + '=' * 60)


if __name__ == '__main__':
    asyncio.run(log_all_messages())
