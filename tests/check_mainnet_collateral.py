#!/usr/bin/env python3
"""Check mainnet collateral and isolated margin."""

import os
from dotenv import load_dotenv
from pathlib import Path
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams

load_dotenv(Path('.env'))
os.environ['NADO_MODE'] = 'MAINNET'

private_key = os.getenv('NADO_PRIVATE_KEY')
client = create_nado_client(mode=NadoClientMode.MAINNET, signer=private_key)

owner = client.context.signer.address
subaccount_hex = subaccount_to_hex(SubaccountParams(
    subaccount_owner=owner,
    subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default'),
))

account_data = client.context.engine_client.get_subaccount_info(subaccount_hex)

print('MAINNET Account Details:')
print(f'Owner: {owner}')
print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')

# Check spot balances (collateral)
if hasattr(account_data, 'spot_balances'):
    print('\nSpot Balances (Collateral):')
    for balance in account_data.spot_balances:
        balance_amount = getattr(balance, 'balance_amount', 0) or getattr(balance, 'amount', 0)
        if balance_amount != 0:
            product_id = getattr(balance, 'product_id', 'N/A')
            print(f'  Product {product_id}: {balance_amount}')

# Check perp positions
if hasattr(account_data, 'perp_balances'):
    print('\nPerp Positions:')
    for balance in account_data.perp_balances:
        position_size = getattr(balance, 'position_size', 0)
        if position_size != 0:
            product_id = getattr(balance, 'product_id', 'N/A')
            print(f'  Product {product_id}: {position_size}')

print('\nNote: Orders use isolated=True, which requires separate collateral')
print('Cross margin orders (isolated=False) may work with existing collateral')
