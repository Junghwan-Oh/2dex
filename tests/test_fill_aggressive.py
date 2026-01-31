#!/usr/bin/env python3
"""Test Fill message WITH aggressive order on MAINNET."""

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


async def test_fill_aggressive():
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
    print("Fill Test - Aggressive Order (MAINNET)")
    print("=" * 60)
    print(f'Owner: {client.owner}')

    # Subscribe to Fill stream FIRST
    print('\n[1] Subscribing to Fill stream...')
    fill_events = []

    async def on_fill(msg):
        fill_events.append(msg)
        print(f'    🎯 FILL RECEIVED: {msg}')

    await client._ws_client.subscribe('fill', 4, callback=on_fill, subaccount=subaccount_hex)
    print('    ✅ Subscribed')

    # Wait for subscription to activate
    print('\n[2] Waiting for subscription to activate...')
    await asyncio.sleep(3)

    # Get BBO and place aggressive order
    print('\n[3] Getting BBO and placing aggressive order...')
    bid, ask = await client.fetch_bbo_prices(4)
    print(f'    BBO: bid={bid}, ask={ask}')

    if ask and ask > 0:
        # Buy at ask (should fill immediately)
        print(f'    Placing buy order at ask ({ask})...')
        result = await client.place_ioc_order(4, Decimal('0.01'), 'buy')
        print(f'    Result: {result.status}')
        if result.success:
            print(f'    ✅ FILLED: {result.filled_size} @ ${result.price}')
            order_id = result.order_id
            print(f'    Order ID: {order_id[:20]}...')
        else:
            print(f'    ❌ Failed: {result.error_message}')
            order_id = None

    # Wait for fill message
    print('\n[4] Waiting for Fill WebSocket message (15 seconds)...')
    for i in range(15):
        await asyncio.sleep(1)
        if len(fill_events) > 0:
            print(f'    ✅ Fill message received after {i+1}s!')
            break
        else:
            print(f'    Waiting... {i+1}/15')

    # Results
    print(f'\n[5] Results:')
    print(f'    Fill events: {len(fill_events)}')
    if fill_events:
        print(f'    Fill event:')
        for key, value in fill_events[0].items():
            print(f'      {key}: {value}')

    # Close position if needed
    if result.success:
        print('\n[6] Closing position...')
        final_pos = await client.get_account_positions()
        if abs(final_pos) > Decimal('0.001'):
            close_result = await client.place_ioc_order(4, abs(final_pos), 'sell')
            if close_result.success:
                print(f'    ✅ Position closed: {close_result.filled_size} @ ${close_result.price}')

    await client.disconnect()

    print('\n' + '=' * 60)
    if len(fill_events) > 0:
        print('✅ SUCCESS: Fill messages working!')
        print('=' * 60)
        return True
    else:
        print('⚠️  No Fill messages received')
        print('=' * 60)
        return False


if __name__ == '__main__':
    result = asyncio.run(test_fill_aggressive())
    sys.exit(0 if result else 1)
