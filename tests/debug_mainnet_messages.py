#!/usr/bin/env python3
"""Debug ALL WebSocket messages on MAINNET to see Fill messages."""

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

from exchanges.nado import NadoClient
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def debug_messages():
    config = type('Config', (), {
        'ticker': 'ETH',
        'quantity': Decimal('1'),
        'contract_id': 4,
        'tick_size': Decimal('0.001')
    })()

    client = NadoClient(config)
    await client.connect()

    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=client.owner,
        subaccount_name=client.subaccount_name,
    ))

    print("=" * 60)
    print("WebSocket Message Debug - MAINNET")
    print("=" * 60)
    print(f'Owner: {client.owner}')

    # Subscribe to Fill stream
    print('\n[1] Subscribing to all streams...')
    await client._ws_client.subscribe('fill', 4, subaccount=subaccount_hex)
    await client._ws_client.subscribe('position_change', 4, subaccount=subaccount_hex)
    await client._ws_client.subscribe('order_update', 4, subaccount=subaccount_hex)
    await client._ws_client.subscribe('book_depth', 4)
    print('    ✅ Subscribed')

    # Listen to ALL messages
    print('\n[2] Listening to ALL WebSocket messages...')
    all_messages = []

    async def log_all():
        async for message in client._ws_client.messages():
            msg_type = message.get('type', 'unknown')
            all_messages.append({'type': msg_type, 'data': message})

            # Print all messages
            if msg_type in ['fill', 'position_change', 'order_update']:
                print(f'\n    📨 {msg_type.upper()}:')
                print(f'    {json.dumps(message, indent=12)[:500]}...')
            elif msg_type in ['best_bid_offer', 'book_depth']:
                # Only print first 3
                count = sum(1 for m in all_messages if m['type'] == msg_type)
                if count <= 3:
                    print(f'    📡 {msg_type}')
            else:
                print(f'    ❓ {msg_type}: {str(message)[:100]}')

    logger_task = asyncio.create_task(log_all())

    # Wait for subscriptions
    await asyncio.sleep(2)

    # Place order
    print('\n[3] Placing IOC order for 0.01 ETH...')
    result = await client.place_ioc_order(4, Decimal('0.01'), 'buy')
    print(f'    Result: {result.status}')
    if result.success:
        print(f'    ✅ FILLED: {result.filled_size} @ ${result.price}')
        order_id = result.order_id
        print(f'    Order ID: {order_id[:20]}...')

    # Listen for 10 seconds
    print('\n[4] Listening for 10 seconds...')
    await asyncio.sleep(10)

    # Cancel logger
    logger_task.cancel()
    try:
        await logger_task
    except asyncio.CancelledError:
        pass

    # Summary
    print('\n[5] Message Summary:')
    msg_counts = {}
    for msg in all_messages:
        msg_type = msg['type']
        msg_counts[msg_type] = msg_counts.get(msg_type, 0) + 1

    for msg_type, count in sorted(msg_counts.items()):
        print(f'    {msg_type}: {count} messages')

    # Show fill/position/order_update messages
    print('\n[6] All Fill/PositionChange/OrderUpdate messages:')
    for msg in all_messages:
        if msg['type'] in ['fill', 'position_change', 'order_update']:
            print(f'\n    {msg["type"]}:')
            print(f'    {json.dumps(msg["data"], indent=8)[:600]}...')

    await client.disconnect()

    print('\n' + '=' * 60)
    if any(m['type'] == 'fill' for m in all_messages):
        print('✅ Fill messages received!')
    else:
        print('⚠️  No Fill messages received')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(debug_messages())
