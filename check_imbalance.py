#!/usr/bin/env python3
"""Check position imbalance calculation."""

import asyncio
from decimal import Decimal
from dotenv import load_dotenv
import os

load_dotenv('.env')
os.environ['NADO_MODE'] = 'MAINNET'

import sys
sys.path.insert(0, '.')

from hedge.DN_pair_eth_sol_nado import DNPairBot

async def test():
    bot = DNPairBot(
        target_notional=Decimal('100'),
        iterations=1,
        sleep_time=0
    )

    # Test the balanced calculation directly
    eth_price = Decimal('2757')
    sol_price = Decimal('115.86')
    eth_tick = Decimal('0.001')
    sol_tick = Decimal('0.1')

    print('Testing calculate_balanced_quantities:')
    eth_qty, sol_qty, imbalance = bot.calculate_balanced_quantities(
        Decimal('100'), eth_price, sol_price, eth_tick, sol_tick
    )

    eth_notional = eth_qty * eth_price
    sol_notional = sol_qty * sol_price

    print(f'ETH: {eth_qty} × ${eth_price} = ${eth_notional:.2f}')
    print(f'SOL: {sol_qty} × ${sol_price} = ${sol_notional:.2f}')
    print(f'Imbalance: {imbalance * 100:.4f}%')
    if eth_notional > 0:
        print(f'Ratio: {sol_notional/eth_notional:.2f}x')

    # Check what the old calculation would give
    print('\n--- Old Calculation (for comparison) ---')
    old_eth_qty = (Decimal('100') / eth_price).quantize(eth_tick)
    old_sol_qty = (Decimal('100') / sol_price).quantize(sol_tick)
    old_eth_notional = old_eth_qty * eth_price
    old_sol_notional = old_sol_qty * sol_price
    old_imbalance = abs(old_sol_notional - old_eth_notional) / old_eth_notional

    print(f'ETH: {old_eth_qty} × ${eth_price} = ${old_eth_notional:.2f}')
    print(f'SOL: {old_sol_qty} × ${sol_price} = ${old_sol_notional:.2f}')
    print(f'Imbalance: {old_imbalance * 100:.4f}%')

asyncio.run(test())
