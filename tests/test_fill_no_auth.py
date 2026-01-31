#!/usr/bin/env python3
"""Test Fill message WITHOUT authentication on MAINNET."""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))
os.environ['NADO_MODE'] = 'MAINNET'

from exchanges.nado import NadoClient
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def test_fill_no_auth():
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
    print("Fill Test - NO AUTHENTICATION (MAINNET)")
    print("=" * 60)
    print(f'Owner: {client.owner}')
    print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')

    # Subscribe to Fill (no auth, just subaccount)
    print('\n[1] Subscribing to Fill stream...')
    fill_events = []

    async def on_fill(msg):
        fill_events.append(msg)
        order_id = msg.get('order_id', 'N/A')[:10]
        qty = msg.get('filled_quantity', 'N/A')
        price = msg.get('price', 'N/A')
        print(f'    🎯 FILL: order={order_id}... qty={qty} price={price}')

    await client._ws_client.subscribe('fill', 4, callback=on_fill, subaccount=subaccount_hex)
    print('    ✅ Subscribed')

    # Wait
    await asyncio.sleep(2)

    # Place order
    print('\n[2] Placing IOC order for 0.01 ETH...')
    result = await client.place_ioc_order(4, Decimal('0.01'), 'buy')
    print(f'    Result: {result.status}')
    if result.success:
        print(f'    ✅ FILLED: {result.filled_size} @ ${result.price}')
        order_id = result.order_id
    else:
        print(f'    ❌ Failed: {result.error_message}')
        order_id = None

    # Wait for fill message
    print('\n[3] Waiting for Fill WebSocket message (10 seconds)...')
    for i in range(10):
        await asyncio.sleep(1)
        if len(fill_events) > 0:
            print(f'    ✅ Fill message received after {i+1}s!')
            break
        else:
            print(f'    Waiting... {i+1}/10')

    # Close position if filled
    if result.success:
        print('\n[4] Closing position...')
        close_result = await client.place_ioc_order(4, Decimal('0.01'), 'sell')
        if close_result.success:
            print(f'    ✅ Position closed: {close_result.filled_size} @ ${close_result.price}')

    # Results
    print(f'\n[5] Results:')
    print(f'    Fill events: {len(fill_events)}')

    await client.disconnect()

    print('\n' + '=' * 60)
    if len(fill_events) > 0:
        print('✅ SUCCESS: Fill messages WITHOUT authentication!')
    else:
        print('⚠️  No Fill messages received')
    print('=' * 60)

    # Final position check
    final_pos = await client.get_account_positions()
    print(f'\nFinal position: {final_pos}')

    return len(fill_events) > 0


if __name__ == '__main__':
    result = asyncio.run(test_fill_no_auth())
    sys.exit(0 if result else 1)
