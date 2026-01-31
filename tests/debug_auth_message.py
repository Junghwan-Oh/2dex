#!/usr/bin/env python3
"""Debug authentication message format."""

import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(Path('.env'))
os.environ['NADO_MODE'] = 'MAINNET'

from exchanges.nado_websocket_client import NadoWebSocketClient
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.subaccount import SubaccountParams


async def debug_auth():
    private_key = os.getenv('NADO_PRIVATE_KEY')
    sdk_client = create_nado_client(mode=NadoClientMode.MAINNET, signer=private_key)

    owner = sdk_client.context.signer.address

    print("=" * 60)
    print("Debug Authentication Message")
    print("=" * 60)

    ws_client = NadoWebSocketClient(
        product_ids=[4],
        private_key=private_key,
        owner=owner,
        subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default')
    )

    # Monkey-patch to log the auth message
    original_auth = ws_client.authenticate

    async def logged_auth():
        print('\n[Calling authenticate...]')

        # Build the auth message manually to see what we're sending
        from nado_protocol.utils.bytes32 import subaccount_to_hex
        from nado_protocol.utils.subaccount import SubaccountParams
        from eth_account.messages import encode_typed_data
        from eth_account import Account
        import time

        subaccount_hex = subaccount_to_hex(SubaccountParams(
            subaccount_owner=ws_client._owner,
            subaccount_name=ws_client._subaccount_name,
        ))

        expiration = int(time.time() * 1000) + 60000

        # Message to sign (integer expiration)
        message_to_sign = {
            'sender': subaccount_hex,
            'expiration': expiration
        }

        # Sign
        encoded = encode_typed_data(
            domain_data=ws_client.EIP712_DOMAIN,
            message_types=ws_client.EIP712_TYPES,
            message_data=message_to_sign
        )

        signed = Account.from_key(ws_client._private_key).sign_message(encoded)

        # API message (string expiration)
        auth_msg = {
            'method': 'authenticate',
            'tx': {
                'sender': subaccount_hex,
                'expiration': str(expiration)
            },
            'signature': signed.signature.hex(),
            'id': str(int(time.time() * 1000) % 1000000)
        }

        print('\nAuth Message:')
        print(json.dumps(auth_msg, indent=2))

        # Send it
        await ws_client._ws.send(json.dumps(auth_msg))

        # Now call original to set authenticated flag
        ws_client._authenticated = True

    ws_client.authenticate = logged_auth

    await ws_client.connect()
    print('✅ Connected')

    # Get subaccount
    subaccount_hex = subaccount_to_hex(SubaccountParams(
        subaccount_owner=owner,
        subaccount_name=os.getenv('NADO_SUBACCOUNT_NAME', 'default'),
    ))

    # Subscribe to fill (which triggers auth)
    print('\n[Subscribing to fill...]')
    await ws_client.subscribe('fill', 4, subaccount=subaccount_hex)

    # Wait for messages
    print('\n[Waiting for messages (5 seconds)...]')
    for i in range(5):
        await asyncio.sleep(1)
        print(f'  {i+1}/5')

    await ws_client.disconnect()

    print('\n' + '=' * 60)


if __name__ == '__main__':
    asyncio.run(debug_auth())
