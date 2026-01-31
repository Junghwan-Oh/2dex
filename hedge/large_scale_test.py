#!/usr/bin/env python3
"""
Large-Scale DN Pair Trading Test

Tests $500 notional per side with 50+ iterations.
Collects metrics: slippage, fill rate, timing, PnL.

Usage:
    python large_scale_test.py --size 500 --iter 50
"""

import asyncio
import os
import sys
import signal
import logging
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import argparse
import csv
import pytz
from typing import List, Optional

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print("Warning: python-dotenv not installed")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force MAINNET mode
os.environ['NADO_MODE'] = 'MAINNET'

from hedge.DN_pair_eth_sol_nado import DNPairBot


class Config:
    """Simple config class that converts dict to object with attributes."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class LargeScaleTest:
    """Large-scale test runner with metrics collection."""

    def __init__(self, target_notional: Decimal, iterations: int):
        self.target_notional = target_notional
        self.iterations = iterations
        self.stop_requested = False
        self.cycle_results = []

        # Setup logging
        self.logger = logging.getLogger("LargeScaleTest")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(handler)

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals for graceful shutdown."""
        self.logger.warning(f"\n{'='*60}")
        self.logger.warning(f"Signal {signum} received, initiating graceful shutdown...")
        self.logger.warning(f"Completing current cycle, then stopping...")
        self.logger.warning(f"{'='*60}")
        self.stop_requested = True

    async def run_test(self):
        """Run the large-scale test."""
        self.logger.info(f"Starting Large-Scale DN Pair Test")
        self.logger.info(f"Target Notional: ${self.target_notional} per side")
        self.logger.info(f"Iterations: {self.iterations}")
        self.logger.info(f"Mode: MAINNET")

        # Create bot with proper parameters
        bot = DNPairBot(
            target_notional=self.target_notional,
            iterations=self.iterations,
            sleep_time=0,  # No delay between cycles for speed
        )

        try:
            # Initialize
            self.logger.info("\n[INIT] Initializing bot...")
            await bot.initialize_clients()

            # Check initial positions
            eth_pos = await bot.eth_client.get_account_positions()
            sol_pos = await bot.sol_client.get_account_positions()
            self.logger.info(f"Initial positions - ETH: {eth_pos}, SOL: {sol_pos}")

            # Close any existing positions
            if abs(eth_pos) > Decimal("0.001") or abs(sol_pos) > Decimal("0.001"):
                self.logger.warning("Existing positions detected, closing first...")
                await self._close_positions(bot, eth_pos, sol_pos)

            # Start timestamp
            start_time = datetime.now(pytz.utc)
            self.logger.info(f"Test started at: {start_time}")

            # Run test
            current_cycle = 0
            for i in range(self.iterations):
                if self.stop_requested:
                    self.logger.warning(f"\nStop requested, completing {current_cycle}/{self.iterations} cycles...")
                    break

                current_cycle = i + 1
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"CYCLE {current_cycle}/{self.iterations}")
                self.logger.info(f"{'='*60}")

                # Run one cycle (BUILD + UNWIND)
                cycle_result = await self._run_cycle(bot, current_cycle)

                if cycle_result:
                    self.cycle_results.append(cycle_result)

                    # Print summary every 10 cycles
                    if current_cycle % 10 == 0:
                        self._print_summary(current_cycle)

                # Small delay between cycles
                await asyncio.sleep(0.1)

            # Final position check
            self.logger.info(f"\n[FINAL] Checking final positions...")
            eth_pos = await bot.eth_client.get_account_positions()
            sol_pos = await bot.sol_client.get_account_positions()

            if abs(eth_pos) > Decimal("0.001") or abs(sol_pos) > Decimal("0.001"):
                self.logger.warning(f"Positions remain - ETH: {eth_pos}, SOL: {sol_pos}")
                self.logger.info("Closing final positions...")
                await self._close_positions(bot, eth_pos, sol_pos)

            # Final summary
            end_time = datetime.now(pytz.utc)
            duration = (end_time - start_time).total_seconds()

            self._print_final_summary(duration)

            # Export metrics
            bot.export_trade_metrics()

        finally:
            # Cleanup
            self.logger.info("\n[CLEANUP] Shutting down...")
            bot.shutdown()

    async def _run_cycle(self, bot: DNPairBot, cycle_num: int) -> Optional[dict]:
        """Run one DN pair cycle (BUILD + UNWIND)."""
        try:
            # Use alternating strategy: even cycles = buy_first, odd cycles = sell_first
            # But we only run buy_first (Long ETH / Short SOL) for this test
            self.logger.info("BUILD: Long ETH / Short SOL")

            # Use the bot's cycle execution method
            success = await bot.execute_buy_first_cycle()

            # Check result
            if success:
                self.logger.info(f"✅ Cycle {cycle_num} successful")
                return {"cycle": cycle_num, "status": "success"}
            else:
                self.logger.error(f"❌ Cycle {cycle_num} failed")
                return {"cycle": cycle_num, "status": "failed"}

        except Exception as e:
            self.logger.error(f"❌ Cycle {cycle_num} error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"cycle": cycle_num, "status": "error"}

    async def _close_positions(self, bot: DNPairBot, eth_pos: Decimal, sol_pos: Decimal):
        """Close all positions."""
        if abs(eth_pos) > Decimal("0.001"):
            self.logger.info(f"Closing ETH position: {eth_pos}")
            side = "sell" if eth_pos > 0 else "buy"
            result = await bot.eth_client.place_ioc_order(4, abs(eth_pos), side)
            if result.success:
                self.logger.info(f"✅ ETH closed: {result.filled_size} @ ${result.price}")
            else:
                self.logger.error(f"❌ ETH close failed: {result.error_message}")

        if abs(sol_pos) > Decimal("0.001"):
            self.logger.info(f"Closing SOL position: {sol_pos}")
            side = "buy" if sol_pos < 0 else "sell"
            result = await bot.sol_client.place_ioc_order(8, abs(sol_pos), side)
            if result.success:
                self.logger.info(f"✅ SOL closed: {result.filled_size} @ ${result.price}")
            else:
                self.logger.error(f"❌ SOL close failed: {result.error_message}")

    def _print_summary(self, current_cycle: int):
        """Print progress summary."""
        completed = len([r for r in self.cycle_results if r["status"] == "success"])
        success_rate = (completed / current_cycle) * 100

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"PROGRESS @ Cycle {current_cycle}/{self.iterations}")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Completed: {completed}/{current_cycle} ({success_rate:.1f}%)")
        self.logger.info(f"Failed: {current_cycle - completed}")

    def _print_final_summary(self, duration: float):
        """Print final test summary."""
        total = len(self.cycle_results)
        successful = len([r for r in self.cycle_results if r["status"] == "success"])
        failed = len([r for r in self.cycle_results if r["status"] == "failed"])
        errors = len([r for r in self.cycle_results if r["status"] == "error"])

        success_rate = (successful / total * 100) if total > 0 else 0

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"FINAL RESULTS")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total Cycles: {total}")
        self.logger.info(f"✅ Successful: {successful} ({success_rate:.1f}%)")
        self.logger.info(f"❌ Failed: {failed}")
        self.logger.info(f"⚠️  Errors: {errors}")
        self.logger.info(f"\nDuration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        self.logger.info(f"Avg time per cycle: {duration/total:.2f} seconds")
        self.logger.info(f"{'='*60}")


def parse_args():
    parser = argparse.ArgumentParser(description="Large-Scale DN Pair Test")
    parser.add_argument("--size", type=str, required=True, help="Target notional in USD (e.g., 500)")
    parser.add_argument("--iter", type=int, required=True, help="Number of iterations (e.g., 50)")
    return parser.parse_args()


async def main():
    args = parse_args()
    target_notional = Decimal(args.size)

    test = LargeScaleTest(target_notional, args.iter)
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
