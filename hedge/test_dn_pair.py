#!/usr/bin/env python3
"""
Simple DN Pair Test: ETH Long / SOL Short on Nado

Usage:
    python test_dn_pair.py --size 100 --iter 1
"""

import asyncio
import os
import sys
import logging
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import argparse

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print("Warning: python-dotenv not installed, skipping .env load")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import NadoClient via exchanges module (symlinked)
from exchanges.nado import NadoClient


class Config:
    """Simple config class that converts dict to object with attributes."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class SimpleDNPairBot:
    def __init__(self, target_notional: Decimal, iterations: int):
        self.target_notional = target_notional
        self.iterations = iterations
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger("DNPairTest")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        return logger

    async def run(self):
        self.logger.info(f"Starting DN Pair Test: ${self.target_notional} notional each side")

        # Initialize clients
        eth_config = Config({"ticker": "ETH", "quantity": Decimal("1"), "contract_id": 4, "tick_size": Decimal("0.001")})
        sol_config = Config({"ticker": "SOL", "quantity": Decimal("1"), "contract_id": 8, "tick_size": Decimal("0.1")})

        self.eth_client = NadoClient(eth_config)
        self.sol_client = NadoClient(sol_config)

        # Connect (including WebSocket)
        await self.eth_client.connect()
        await self.sol_client.connect()

        self.logger.info("Connected to Nado (WebSocket enabled)")

        # Check initial positions
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()
        self.logger.info(f"Initial positions - ETH: {eth_pos}, SOL: {sol_pos}")

        if abs(eth_pos) > Decimal("0.001") or abs(sol_pos) > Decimal("0.001"):
            self.logger.warning("Existing positions detected, closing first...")
            await self.close_all_positions(eth_pos, sol_pos)

        # Run iterations
        for i in range(self.iterations):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Iteration {i+1}/{self.iterations}")
            self.logger.info(f"{'='*60}")

            # Open positions: Long ETH / Short SOL
            await self.open_positions()

            # Wait a bit
            await asyncio.sleep(2)

            # Close positions
            await self.close_positions()

        # Final check
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()
        self.logger.info(f"Final positions - ETH: {eth_pos}, SOL: {sol_pos}")

        # Disconnect
        await self.eth_client.disconnect()
        await self.sol_client.disconnect()
        self.logger.info("Test completed!")

    async def open_positions(self):
        """Open DN pair positions: Long ETH / Short SOL"""
        self.logger.info("Opening positions: Long ETH / Short SOL")

        # Get BBO prices
        self.logger.info("Fetching ETH prices...")
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(4)
        self.logger.info(f"ETH BBO: bid={eth_bid}, ask={eth_ask}")

        self.logger.info("Fetching SOL prices...")
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(8)
        self.logger.info(f"SOL BBO: bid={sol_bid}, ask={sol_ask}")

        if eth_bid <= 0 or eth_ask <= 0 or sol_bid <= 0 or sol_ask <= 0:
            self.logger.error("Invalid prices, cannot open positions")
            self.logger.error(f"Prices: ETH bid={eth_bid} ask={eth_ask}, SOL bid={sol_bid} ask={sol_ask}")
            return

        # Calculate quantities
        eth_price = eth_ask  # Buying ETH
        sol_price = sol_bid  # Selling SOL
        eth_qty = self.target_notional / eth_price
        sol_qty = self.target_notional / sol_price

        # Check slippage using BookDepth
        eth_slippage = await self.eth_client.estimate_slippage("buy", eth_qty)
        sol_slippage = await self.sol_client.estimate_slippage("sell", sol_qty)

        self.logger.info(f"ETH: Buy {eth_qty:.4f} @ ${eth_price:.2f} (slippage: {eth_slippage:.1f} bps)")
        self.logger.info(f"SOL: Sell {sol_qty:.4f} @ ${sol_price:.2f} (slippage: {sol_slippage:.1f} bps)")

        # Place IOC orders
        eth_result, sol_result = await asyncio.gather(
            self.eth_client.place_ioc_order(4, eth_qty, "buy"),
            self.sol_client.place_ioc_order(8, sol_qty, "sell"),
            return_exceptions=True
        )

        # Check results
        if isinstance(eth_result, Exception):
            self.logger.error(f"ETH order failed: {eth_result}")
        elif eth_result.success:
            self.logger.info(f"ETH order result: status={eth_result.status}, filled={eth_result.filled_size}, price=${eth_result.price}")
        else:
            self.logger.error(f"ETH order failed: {eth_result.error_message}")

        if isinstance(sol_result, Exception):
            self.logger.error(f"SOL order failed: {sol_result}")
        elif sol_result.success:
            self.logger.info(f"SOL order result: status={sol_result.status}, filled={sol_result.filled_size}, price=${sol_result.price}")
        else:
            self.logger.error(f"SOL order failed: {sol_result.error_message}")

    async def close_positions(self):
        """Close all positions using IOC orders"""
        self.logger.info("Closing positions...")

        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()
        self.logger.info(f"Current positions - ETH: {eth_pos}, SOL: {sol_pos}")

        # Close ETH position (if long, sell; if short, buy)
        if abs(eth_pos) > Decimal("0.001"):
            side = "sell" if eth_pos > 0 else "buy"
            self.logger.info(f"Closing ETH position: {eth_pos} ({side})")
            result = await self.eth_client.place_ioc_order(4, abs(eth_pos), side)
            if result.success:
                self.logger.info(f"ETH position closed: {result.filled_size} @ ${result.price}")
            else:
                self.logger.error(f"ETH close failed: {result.error_message}")

        # Close SOL position
        if abs(sol_pos) > Decimal("0.001"):
            side = "buy" if sol_pos < 0 else "sell"  # If short, buy to close; if long, sell to close
            self.logger.info(f"Closing SOL position: {sol_pos} ({side})")
            result = await self.sol_client.place_ioc_order(8, abs(sol_pos), side)
            if result.success:
                self.logger.info(f"SOL position closed: {result.filled_size} @ ${result.price}")
            else:
                self.logger.error(f"SOL close failed: {result.error_message}")

    async def close_all_positions(self, eth_pos, sol_pos):
        """Close any existing positions using IOC orders"""
        if abs(eth_pos) > Decimal("0.001"):
            side = "sell" if eth_pos > 0 else "buy"
            await self.eth_client.place_ioc_order(4, abs(eth_pos), side)
        if abs(sol_pos) > Decimal("0.001"):
            side = "buy" if sol_pos < 0 else "sell"
            await self.sol_client.place_ioc_order(8, abs(sol_pos), side)


def parse_args():
    parser = argparse.ArgumentParser(description="Simple DN Pair Test")
    parser.add_argument("--size", type=str, required=True, help="Target notional in USD (e.g., 100)")
    parser.add_argument("--iter", type=int, default=1, help="Number of iterations (default: 1)")
    return parser.parse_args()


async def main():
    args = parse_args()
    bot = SimpleDNPairBot(Decimal(args.size), args.iter)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
