#!/usr/bin/env python3
"""Test Fill WebSocket message reception on MAINNET."""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))

# Force MAINNET mode
os.environ['NADO_MODE'] = 'MAINNET'

from exchanges.nado import NadoClient
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def test_fill_mainnet():
    # Create client
    config = type('Config', (), {
        'ticker': 'ETH',
        'quantity': Decimal('1'),
        'contract_id': 4,
        'tick_size': Decimal('0.001')
    })()

    client = NadoClient(config)
    await client.connect()

    # Get subaccount
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=client.owner,
        subaccount_name=client.subaccount_name,
    ))

    print("=" * 60)
    print("Fill Message Reception Test - MAINNET")
    print("=" * 60)
    print(f'Owner: {client.owner}')
    print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')
    print(f'Mode: MAINNET')

    # Subscribe to Fill stream
    print('\n[1] Subscribing to Fill stream...')
    fill_events = []

    async def on_fill(message):
        fill_events.append(message)
        order_id = message.get('order_id', 'N/A')[:10]
        qty = message.get('filled_quantity', 'N/A')
        price = message.get('price', 'N/A')
        print(f'    🎯 FILL RECEIVED: order={order_id}... qty={qty} price={price}')

    await client._ws_client.subscribe('fill', 4, callback=on_fill, subaccount=subaccount_hex)
    print('    ✅ Subscribed to Fill stream')

    # Also subscribe to PositionChange
    print('\n[2] Subscribing to PositionChange stream...')
    position_events = []

    async def on_position(message):
        position_events.append(message)
        print(f'    📊 POSITION CHANGE: {message}')

    await client._ws_client.subscribe('position_change', 4, callback=on_position, subaccount=subaccount_hex)
    print('    ✅ Subscribed to PositionChange stream')

    # Wait for subscriptions to activate
    print('\n[3] Waiting for subscriptions to activate...')
    await asyncio.sleep(3)

    # Place a small order
    print('\n[4] Placing IOC order for 0.01 ETH (MAINNET)...')
    result = await client.place_ioc_order(4, Decimal('0.01'), 'buy')
    print(f'    Result: {result.status}')
    if result.success:
        print(f'    ✅ FILLED: {result.filled_size} @ ${result.price}')
        order_id = result.order_id
    else:
        print(f'    ❌ Failed: {result.error_message}')
        order_id = None

    # Wait for fill message
    print('\n[5] Waiting for Fill/PositionChange WebSocket messages (10 seconds)...')
    for i in range(10):
        await asyncio.sleep(1)
        if len(fill_events) > 0 or len(position_events) > 0:
            print(f'    ✅ Messages received after {i+1}s!')
            break
        else:
            print(f'    Waiting... {i+1}/10')

    # Results
    print(f'\n[6] Results:')
    print(f'    Fill events: {len(fill_events)}')
    print(f'    Position events: {len(position_events)}')

    # Show fill event details
    if fill_events:
        print(f'\n    Fill event details:')
        for key, value in fill_events[0].items():
            if key not in ['raw_message', 'timestamp']:
                print(f'      {key}: {value}')

    # Cleanup
    await client.disconnect()

    print('\n' + '=' * 60)
    if len(fill_events) > 0:
        print('✅ SUCCESS: Fill detection working on MAINNET!')
        print('=' * 60)
        return True
    else:
        print('⚠️  No Fill messages received on MAINNET')
        if order_id:
            print(f'    Order {order_id[:10]}... was filled but no WebSocket message')
        print('=' * 60)
        return False


if __name__ == '__main__':
    result = asyncio.run(test_fill_mainnet())
    sys.exit(0 if result else 1)
