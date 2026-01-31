#!/usr/bin/env python3
"""Check Nado account health and balance."""

import os
from pathlib import Path
from dotenv import load_dotenv
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams

load_dotenv(Path('.env'))
private_key = os.getenv('NADO_PRIVATE_KEY')

sdk_client = create_nado_client(mode=NadoClientMode.TESTNET, signer=private_key)

owner = sdk_client.context.signer.address
subaccount_hex = subaccount_to_hex(SubaccountParams(
    subaccount_owner=owner,
    subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default'),
))

account_data = sdk_client.context.engine_client.get_subaccount_info(subaccount_hex)

print('Account Health Summary:')
print(f'Owner: {owner}')
print(f'Subaccount: {subaccount_hex[:10]}...{subaccount_hex[-6:]}')

# Health info
if hasattr(account_data, 'healths'):
    print(f'Healths: {account_data.healths}')

# Perp balances (non-zero only)
if hasattr(account_data, 'perp_balances'):
    print(f'\nPerp Positions:')
    for balance in account_data.perp_balances:
        position_size = getattr(balance, 'position_size', 0)
        if position_size != 0:
            product_id = getattr(balance, 'product_id', 'N/A')
            print(f'  Product {product_id}: {position_size}')
        else:
            # Check if we have any balance at all
            product_id = getattr(balance, 'product_id', 'N/A')
            print(f'  Product {product_id}: No position')
