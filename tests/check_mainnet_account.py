#!/usr/bin/env python3
"""Check mainnet account balance."""

import os
from dotenv import load_dotenv
from pathlib import Path
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams

load_dotenv(Path('.env'))
print(f'Current NADO_MODE: {os.getenv("NADO_MODE", "TESTNET")}')

private_key = os.getenv('NADO_PRIVATE_KEY')

# Check mainnet
client = create_nado_client(mode=NadoClientMode.MAINNET, signer=private_key)

owner = client.context.signer.address
subaccount_hex = subaccount_to_hex(SubaccountParams(
    subaccount_owner=owner,
    subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default'),
))

account_data = client.context.engine_client.get_subaccount_info(subaccount_hex)

print(f'\nMAINNET Account:')
print(f'Owner: {owner}')
print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')

if hasattr(account_data, 'healths') and account_data.healths:
    print(f'\nHealth:')
    for i, health in enumerate(account_data.healths):
        print(f'  Health {i}: assets={health.assets}, liabilities={health.liabilities}, health={health.health}')

if hasattr(account_data, 'perp_balances'):
    print(f'\nMAINNET Positions:')
    for balance in account_data.perp_balances:
        position_size = getattr(balance, 'position_size', 0)
        if position_size != 0:
            product_id = getattr(balance, 'product_id', 'N/A')
            print(f'  Product {product_id}: {position_size}')
