#!/usr/bin/env python3
"""Test Fill WebSocket message reception with real order."""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))

from exchanges.nado import NadoClient
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def test_fill():
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
    print("Fill Message Reception Test")
    print("=" * 60)
    print(f'Owner: {client.owner}')
    print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')

    # Subscribe to Fill stream
    print('\n[1] Subscribing to Fill stream...')
    fill_events = []

    async def on_fill(message):
        fill_events.append(message)
        order_id = message.get('order_id', 'N/A')[:10]
        qty = message.get('filled_quantity', 'N/A')
        price = message.get('price', 'N/A')
        print(f'    🎯 FILL: order_id={order_id}... qty={qty} price={price}')

    await client._ws_client.subscribe('fill', 4, callback=on_fill, subaccount=subaccount_hex)
    print('    ✅ Subscribed')

    # Wait for subscription to activate
    await asyncio.sleep(2)

    # Try to place a very small order
    print('\n[2] Placing tiny order for 0.001 ETH...')
    result = await client.place_ioc_order(4, Decimal('0.001'), 'buy')
    print(f'    Result: {result.status}')
    if result.success:
        print(f'    Filled: {result.filled_size} @ ${result.price}')
        order_id = result.order_id
    else:
        print(f'    Error: {result.error_message}')
        order_id = None

    # Wait for fill message
    print('\n[3] Waiting for Fill WebSocket message (5 seconds)...')
    for i in range(5):
        await asyncio.sleep(1)
        if len(fill_events) > 0:
            print(f'    ✅ Fill message received after {i+1}s!')
            break
        else:
            print(f'    Waiting... {i+1}/5')

    # Results
    print(f'\n[4] Results:')
    print(f'    Fill events received: {len(fill_events)}')

    # Show fill event details
    if fill_events:
        print(f'    Fill event details:')
        for key, value in fill_events[0].items():
            if key not in ['raw_message', 'timestamp']:
                print(f'      {key}: {value}')

    # Cleanup
    await client.disconnect()

    print('\n' + '=' * 60)
    if len(fill_events) > 0:
        print('✅ SUCCESS: Fill detection working!')
        print('=' * 60)
        return True
    else:
        print('⚠️  No Fill messages received')
        if not result.success:
            print('    Note: Order failed - account health issue')
            print('    To test Fill messages, you need to:')
            print('    1. Deposit collateral to your Nado testnet account')
            print('    2. Run this test again')
        print('=' * 60)
        return False


if __name__ == '__main__':
    result = asyncio.run(test_fill())
    sys.exit(0 if result else 1)
