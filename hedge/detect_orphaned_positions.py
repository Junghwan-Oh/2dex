"""Detect positions on both possible subaccount addresses."""
import os
import asyncio
from decimal import Decimal
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.engine_client.types import OrderParams
from nado_protocol.utils.subaccount import SubaccountParams
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.math import from_x18

async def detect_orphaned_positions():
    """Check both addresses for positions."""
    private_key = os.getenv('NADO_PRIVATE_KEY')
    mode = os.getenv('NADO_MODE', 'MAINNET').upper()
    subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')

    mode_map = {
        'MAINNET': NadoClientMode.MAINNET,
        'DEVNET': NadoClientMode.DEVNET,
    }
    client_mode = mode_map.get(mode, NadoClientMode.MAINNET)
    client = create_nado_client(client_mode, private_key)

    # Get both addresses
    engine_client_address = client.context.engine_client.signer.address
    context_address = client.context.signer.address

    print(f"Engine Client Address (used for orders): {engine_client_address}")
    print(f"Context Signer Address (buggy, used for position checks): {context_address}")
    print(f"Addresses match: {engine_client_address == context_address}")
    print()

    # Check both addresses for positions
    products = [4, 8]  # ETH, SOL

    for product_id in products:
        ticker = "ETH" if product_id == 4 else "SOL"

        # Check engine_client address (correct)
        engine_subaccount = subaccount_to_hex(engine_client_address, subaccount_name)
        try:
            engine_data = client.context.engine_client.get_subaccount_info(engine_subaccount)
            for pos in engine_data.perp_balances:
                if pos.product_id == product_id:
                    size = Decimal(str(from_x18(pos.balance.amount)))
                    if size != 0:
                        print(f"[ENGINE_CLIENT] {ticker}: {size} (CORRECT address)")
        except Exception as e:
            print(f"[ENGINE_CLIENT] {ticker}: Error - {e}")

        # Check context address (buggy, may have orphaned positions)
        context_subaccount = subaccount_to_hex(context_address, subaccount_name)
        try:
            context_data = client.context.engine_client.get_subaccount_info(context_subaccount)
            for pos in context_data.perp_balances:
                if pos.product_id == product_id:
                    size = Decimal(str(from_x18(pos.balance.amount)))
                    if size != 0:
                        print(f"[CONTEXT_SIGNER] {ticker}: {size} (ORPHANED on wrong address)")
        except Exception as e:
            print(f"[CONTEXT_SIGNER] {ticker}: Error - {e}")

if __name__ == "__main__":
    asyncio.run(detect_orphaned_positions())
