#!/usr/bin/env python3
"""Close any open positions."""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['NADO_MODE'] = 'MAINNET'

from exchanges.nado import NadoClient


async def close_position():
    load_dotenv(Path('.env'))

    # Close SOL position
    sol_config = type('Config', (), {
        'ticker': 'SOL',
        'quantity': Decimal('1'),
        'contract_id': 8,
        'tick_size': Decimal('0.1')
    })()
    sol_client = NadoClient(sol_config)
    await sol_client.connect()

    sol_pos = await sol_client.get_account_positions()
    print(f'Current SOL position: {sol_pos}')

    if abs(sol_pos) > Decimal('0.001'):
        print(f'Closing SOL position: {sol_pos}')
        side = 'buy' if sol_pos < 0 else 'sell'
        result = await sol_client.place_limit_order_with_timeout(
            contract_id=8,
            quantity=abs(sol_pos),
            direction=side,
            price=None,
            timeout_seconds=60,
            max_retries=3
        )
        if result.success:
            print(f'Successfully closed: {result.filled_size} @ ${result.price}')
        else:
            print(f'Failed to close: {result.error_message}')

    # Also check ETH
    eth_config = type('Config', (), {
        'ticker': 'ETH',
        'quantity': Decimal('1'),
        'contract_id': 4,
        'tick_size': Decimal('0.001')
    })()
    eth_client = NadoClient(eth_config)
    await eth_client.connect()

    eth_pos = await eth_client.get_account_positions()
    print(f'Current ETH position: {eth_pos}')

    if abs(eth_pos) > Decimal('0.001'):
        print(f'Closing ETH position: {eth_pos}')
        side = 'sell' if eth_pos > 0 else 'buy'
        result = await eth_client.place_limit_order_with_timeout(
            contract_id=4,
            quantity=abs(eth_pos),
            direction=side,
            price=None,
            timeout_seconds=60,
            max_retries=3
        )
        if result.success:
            print(f'Successfully closed: {result.filled_size} @ ${result.price}')
        else:
            print(f'Failed to close: {result.error_message}')

    await sol_client.disconnect()
    await eth_client.disconnect()
    print('Done.')


if __name__ == '__main__':
    asyncio.run(close_position())
