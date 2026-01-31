#!/usr/bin/env python3
"""Check and close MAINNET positions."""

import os
import sys
import asyncio
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))
os.environ['NADO_MODE'] = 'MAINNET'

from exchanges.nado import NadoClient


async def check_and_close():
    # Create ETH client
    config = type('Config', (), {
        'ticker': 'ETH',
        'quantity': Decimal('1'),
        'contract_id': 4,
        'tick_size': Decimal('0.001')
    })()

    client = NadoClient(config)
    await client.connect()

    # Check positions
    print('=' * 60)
    print('MAINNET Position Check')
    print('=' * 60)

    eth_pos = await client.get_account_positions()
    print(f'ETH Position: {eth_pos}')

    if abs(eth_pos) > Decimal('0.001'):
        print(f'\n⚠️  OPEN POSITION DETECTED: {eth_pos} ETH')
        print(f'Closing position...')

        # Close position
        side = 'sell' if eth_pos > 0 else 'buy'
        result = await client.place_ioc_order(4, abs(eth_pos), side)

        if result.success:
            print(f'✅ Position closed: {result.filled_size} @ ${result.price}')
        else:
            print(f'❌ Close failed: {result.error_message}')
    else:
        print('\n✅ No open positions')

    # Final check
    eth_pos_final = await client.get_account_positions()
    print(f'\nFinal ETH Position: {eth_pos_final}')

    await client.disconnect()

    print('=' * 60)
    if abs(eth_pos_final) < Decimal('0.001'):
        print('✅ ALL POSITIONS CLOSED')
    else:
        print(f'⚠️  POSITION REMAINS: {eth_pos_final}')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(check_and_close())
