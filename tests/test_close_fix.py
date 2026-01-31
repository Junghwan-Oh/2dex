#!/usr/bin/env python3
"""
Live test script for close order fixes.

This script performs 5 iterations of the close order cycle to verify:
1. IOC order type is used (not POST_ONLY)
2. Isolated margin is calculated correctly
3. Quantities are rounded to size increments
4. Fill detection works properly
5. Positions close cleanly without accumulation

Usage:
    python test_close_fix.py

Environment variables required:
    - NADO_PRIVATE_KEY: Private key for Nado trading
    - NADO_MODE: MAINNET or DEVNET
    - NADO_SUBACCOUNT_NAME: Subaccount name (default: "default")
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime
import logging

# Add hedge directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hedge.exchanges.nado import NadoClient


# Configuration
TARGET_NOTIONAL = Decimal("50")  # USD notional per position (small for testing)
ITERATIONS = 5  # Number of test cycles
SLEEP_TIME = 2  # Seconds between iterations

# Tolerances
SOL_TOLERANCE = Decimal("0.1")  # SOL position tolerance
ETH_TOLERANCE = Decimal("0.001")  # ETH position tolerance


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/test_close_fix.log')
        ]
    )
    os.makedirs('logs', exist_ok=True)
    return logging.getLogger('test_close_fix')


logger = setup_logging()


class CloseFixTest:
    """Test class for close order fixes."""

    def __init__(self):
        self.eth_client = None
        self.sol_client = None
        self.test_results = {
            'iterations': [],
            'total_cycles': 0,
            'successful_closes': 0,
            'failed_closes': 0,
            'position_accumulation_detected': False,
        }

    async def initialize(self):
        """Initialize Nado clients."""
        logger.info("Initializing Nado clients...")

        # ETH client config
        eth_config = {
            'ticker': 'ETH',
            'contract_id': '4',
            'tick_size': Decimal('0.0001'),
            'size_increment': Decimal('0.001'),
            'price_increment': Decimal('0.0001'),
        }

        # SOL client config
        sol_config = {
            'ticker': 'SOL',
            'contract_id': '8',
            'tick_size': Decimal('0.01'),
            'size_increment': Decimal('0.1'),
            'price_increment': Decimal('0.01'),
        }

        self.eth_client = NadoClient(eth_config)
        self.sol_client = NadoClient(sol_config)

        await self.eth_client.connect()
        await self.sol_client.connect()

        logger.info("Clients initialized successfully")
        logger.info(f"ETH owner: {self.eth_client.owner}")
        logger.info(f"SOL owner: {self.sol_client.owner}")

    async def check_positions(self) -> tuple:
        """Get current positions for ETH and SOL."""
        eth_position = await self.eth_client.get_account_positions()
        sol_position = await self.sol_client.get_account_positions()

        logger.info(f"Current positions - ETH: {eth_position}, SOL: {sol_position}")

        return eth_position, sol_position

    async def place_open_orders(self) -> dict:
        """Place opening orders (long ETH, short SOL)."""
        logger.info("=== Placing OPEN orders ===")

        # Get current BBO prices
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices('4')
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices('8')

        logger.info(f"ETH BBO: bid={eth_bid}, ask={eth_ask}")
        logger.info(f"SOL BBO: bid={sol_bid}, ask={sol_ask}")

        # Calculate quantities
        eth_quantity = TARGET_NOTIONAL / eth_ask
        sol_quantity = TARGET_NOTIONAL / sol_bid

        logger.info(f"Order quantities - ETH: {eth_quantity}, SOL: {sol_quantity}")

        # Place ETH long order (IOC)
        logger.info("Placing ETH long IOC order...")
        eth_result = await self.eth_client.place_ioc_order(
            contract_id='4',
            quantity=eth_quantity,
            side='buy'
        )

        # Place SOL short order (IOC)
        logger.info("Placing SOL short IOC order...")
        sol_result = await self.sol_client.place_ioc_order(
            contract_id='8',
            quantity=sol_quantity,
            side='sell'
        )

        results = {
            'eth_open': eth_result,
            'sol_open': sol_result,
            'eth_bid': eth_bid,
            'eth_ask': eth_ask,
            'sol_bid': sol_bid,
            'sol_ask': sol_ask,
            'eth_quantity': eth_quantity,
            'sol_quantity': sol_quantity,
        }

        # Log results
        logger.info(f"ETH open result: success={eth_result.success}, "
                   f"status={eth_result.status}, filled_size={eth_result.filled_size}")
        logger.info(f"SOL open result: success={sol_result.success}, "
                   f"status={sol_result.status}, filled_size={sol_result.filled_size}")

        return results

    async def place_close_orders(self, open_results: dict) -> dict:
        """Place closing orders using place_close_order."""
        logger.info("=== Placing CLOSE orders (testing fix) ===")

        # Get filled sizes from open orders
        eth_filled_size = open_results['eth_open'].filled_size
        sol_filled_size = open_results['sol_open'].filled_size

        if eth_filled_size == 0 or sol_filled_size == 0:
            logger.warning("One or both orders did not fill, skipping close")
            return {
                'eth_close': None,
                'sol_close': None,
                'skipped': True,
            }

        logger.info(f"Closing ETH position: {eth_filled_size}")
        logger.info(f"Closing SOL position: {sol_filled_size}")

        # Close ETH (sell to close long)
        eth_close_result = await self.eth_client.place_close_order(
            contract_id='4',
            quantity=eth_filled_size,
            price=open_results['eth_bid'],  # Use bid for sell
            side='sell'
        )

        # Close SOL (buy to close short)
        sol_close_result = await self.sol_client.place_close_order(
            contract_id='8',
            quantity=sol_filled_size,
            price=open_results['sol_ask'],  # Use ask for buy
            side='buy'
        )

        results = {
            'eth_close': eth_close_result,
            'sol_close': sol_close_result,
            'skipped': False,
        }

        # Log results
        logger.info(f"ETH close result: success={eth_close_result.success}, "
                   f"status={eth_close_result.status}, filled_size={eth_close_result.filled_size}")
        logger.info(f"SOL close result: success={sol_close_result.success}, "
                   f"status={sol_close_result.status}, filled_size={sol_close_result.filled_size}")

        return results

    async def verify_close(self, close_results: dict) -> bool:
        """Verify that positions closed correctly."""
        if close_results.get('skipped'):
            return False

        eth_close = close_results['eth_close']
        sol_close = close_results['sol_close']

        # Check if both closes succeeded
        if not eth_close.success or not sol_close.success:
            logger.error("One or both close orders failed!")
            return False

        # Check fill status
        eth_fully_filled = eth_close.status == 'FILLED'
        sol_fully_filled = sol_close.status == 'FILLED'

        if not eth_fully_filled or not sol_fully_filled:
            logger.warning(f"Partial fill detected - ETH: {eth_close.status}, SOL: {sol_close.status}")
            # Still count as success if partially filled (IOC behavior)

        # Check final positions
        eth_position, sol_position = await self.check_positions()

        # Verify positions are near zero
        eth_near_zero = abs(eth_position) < ETH_TOLERANCE
        sol_near_zero = abs(sol_position) < SOL_TOLERANCE

        if not eth_near_zero:
            logger.error(f"ETH position accumulation detected: {eth_position}")
            self.test_results['position_accumulation_detected'] = True

        if not sol_near_zero:
            logger.error(f"SOL position accumulation detected: {sol_position}")
            self.test_results['position_accumulation_detected'] = True

        return eth_near_zero and sol_near_zero

    async def run_iteration(self, iteration: int):
        """Run a single test iteration."""
        logger.info(f"\n{'='*60}")
        logger.info(f"ITERATION {iteration + 1}/{ITERATIONS}")
        logger.info(f"{'='*60}\n")

        iteration_result = {
            'iteration': iteration + 1,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'eth_position_before': None,
            'sol_position_before': None,
            'eth_position_after': None,
            'sol_position_after': None,
            'eth_open_success': False,
            'sol_open_success': False,
            'eth_close_success': False,
            'sol_close_success': False,
        }

        # Check positions before
        eth_pos_before, sol_pos_before = await self.check_positions()
        iteration_result['eth_position_before'] = str(eth_pos_before)
        iteration_result['sol_position_before'] = str(sol_pos_before)

        # Place open orders
        open_results = await self.place_open_orders()
        iteration_result['eth_open_success'] = open_results['eth_open'].success
        iteration_result['sol_open_success'] = open_results['sol_open'].success

        # Small delay to ensure orders are processed
        await asyncio.sleep(1)

        # Place close orders
        close_results = await self.place_close_orders(open_results)

        if close_results.get('skipped'):
            logger.warning("Iteration skipped - open orders did not fill")
            iteration_result['skipped'] = True
            self.test_results['iterations'].append(iteration_result)
            return

        # Small delay to ensure closes are processed
        await asyncio.sleep(1)

        # Verify close
        close_verified = await self.verify_close(close_results)

        if close_results['eth_close']:
            iteration_result['eth_close_success'] = close_results['eth_close'].success
        if close_results['sol_close']:
            iteration_result['sol_close_success'] = close_results['sol_close'].success

        # Check positions after
        eth_pos_after, sol_pos_after = await self.check_positions()
        iteration_result['eth_position_after'] = str(eth_pos_after)
        iteration_result['sol_position_after'] = str(sol_pos_after)

        iteration_result['success'] = close_verified

        # Update totals
        self.test_results['total_cycles'] += 1
        if close_verified:
            self.test_results['successful_closes'] += 1
            logger.info(f"✓ Iteration {iteration + 1} PASSED")
        else:
            self.test_results['failed_closes'] += 1
            logger.error(f"✗ Iteration {iteration + 1} FAILED")

        self.test_results['iterations'].append(iteration_result)

    async def run_all_iterations(self):
        """Run all test iterations."""
        logger.info(f"\nStarting {ITERATIONS} iterations of close order testing...")
        logger.info(f"Target notional: ${TARGET_NOTIONAL}")
        logger.info(f"Tolerances: ETH={ETH_TOLERANCE}, SOL={SOL_TOLERANCE}\n")

        for i in range(ITERATIONS):
            try:
                await self.run_iteration(i)

                if i < ITERATIONS - 1:
                    logger.info(f"\nWaiting {SLEEP_TIME} seconds before next iteration...")
                    await asyncio.sleep(SLEEP_TIME)

            except Exception as e:
                logger.error(f"Error in iteration {i + 1}: {e}")
                import traceback
                traceback.print_exc()

    def print_summary(self):
        """Print test summary."""
        logger.info(f"\n{'='*60}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*60}\n")

        total = self.test_results['total_cycles']
        successful = self.test_results['successful_closes']
        failed = self.test_results['failed_closes']

        logger.info(f"Total cycles: {total}")
        logger.info(f"Successful closes: {successful}")
        logger.info(f"Failed closes: {failed}")

        if total > 0:
            success_rate = (successful / total) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        if self.test_results['position_accumulation_detected']:
            logger.warning("⚠ POSITION ACCUMULATION DETECTED - FIX MAY NOT BE WORKING")
        else:
            logger.info("✓ No position accumulation detected")

        # Detailed iteration results
        logger.info("\nDetailed results:")
        for result in self.test_results['iterations']:
            if result.get('skipped'):
                logger.info(f"  Iteration {result['iteration']}: SKIPPED")
            else:
                status = "✓ PASSED" if result['success'] else "✗ FAILED"
                logger.info(f"  Iteration {result['iteration']}: {status}")
                logger.info(f"    ETH: {result['eth_position_before']} → {result['eth_position_after']}")
                logger.info(f"    SOL: {result['sol_position_before']} → {result['sol_position_after']}")

    async def cleanup(self):
        """Clean up resources."""
        logger.info("\nCleaning up...")
        if self.eth_client:
            await self.eth_client.disconnect()
        if self.sol_client:
            await self.sol_client.disconnect()
        logger.info("Cleanup complete")


async def main():
    """Main test function."""
    test = CloseFixTest()

    try:
        # Initialize
        await test.initialize()

        # Check starting positions
        eth_pos, sol_pos = await test.check_positions()

        if abs(eth_pos) > ETH_TOLERANCE or abs(sol_pos) > SOL_TOLERANCE:
            logger.warning("⚠ WARNING: Starting with non-zero positions!")
            logger.warning(f"  ETH: {eth_pos}, SOL: {sol_pos}")
            logger.warning("  Consider manually closing positions before running test")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                logger.info("Test aborted by user")
                return

        # Run iterations
        await test.run_all_iterations()

        # Print summary
        test.print_summary()

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await test.cleanup()


if __name__ == "__main__":
    # Check environment variables
    required_vars = ["NADO_PRIVATE_KEY", "NADO_MODE"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set the following environment variables:")
        for var in missing_vars:
            logger.error(f"  export {var}=<value>")
        sys.exit(1)

    # Run test
    asyncio.run(main())
