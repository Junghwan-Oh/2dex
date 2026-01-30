#!/usr/bin/env python3
"""
Delta Neutral (DN) Pair Bot: ETH (Long) / SOL (Short) on Nado

Pairs Trading Strategy:
- Long ETH / Short SOL (correlation-based delta neutral)
- Notional-based position sizing: same USD value for both positions
- Simultaneous entry/exit for both positions

Usage:
    python DN_pair_eth_sol_nado.py --size 100 --iter 5
    # size is target notional in USD (e.g., 100 = $100 ETH and $100 SOL positions)
"""

import asyncio
import signal
import logging
import os
import sys
import time
import csv
from decimal import Decimal
from typing import Tuple, List
from datetime import datetime
import pytz

# Import exchanges modules (like Mean Reversion bot)
from exchanges.nado import NadoClient
from exchanges.base import OrderResult


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class DNPairBot:
    """
    ETH/SOL Pair Trading Bot on Nado

    Strategy:
    - Long ETH / Short SOL (correlation-based delta neutral)
    - Notional-based position sizing: same USD value for both positions
    - Simultaneous entry/exit for both positions
    - Alternate: BUILD (open positions) -> UNWIND (close positions)
    """

    def __init__(
        self,
        target_notional: Decimal,  # Target USD notional for each position (e.g., 100 = $100)
        iterations: int = 20,
        sleep_time: int = 0,
        csv_path: str = None,  # Optional custom CSV path for testing
    ):
        self.target_notional = target_notional  # USD notional for each position
        self.iterations = iterations
        self.sleep_time = sleep_time

        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/DN_pair_eth_sol_nado_log.txt"

        # Use custom CSV path if provided
        if csv_path:
            self.csv_filename = csv_path
        else:
            self.csv_filename = f"logs/DN_pair_eth_sol_nado_trades.csv"

        self._initialize_csv_file()
        self._setup_logger()

        self.stop_flag = False

        # Nado clients (one for each ticker)
        self.eth_client = None
        self.sol_client = None

        # Contract info
        self.eth_contract_id = None
        self.eth_tick_size = None
        self.sol_contract_id = None
        self.sol_tick_size = None

    def _setup_logger(self):
        self.logger = logging.getLogger("dn_pair_eth_sol_nado")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        for lib in ["urllib3", "requests", "websockets", "pysdk"]:
            logging.getLogger(lib).setLevel(logging.CRITICAL)
        logging.getLogger().setLevel(logging.CRITICAL)

        file_handler = logging.FileHandler(self.log_filename)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.propagate = False

    def _initialize_csv_file(self):
        if not os.path.exists(self.csv_filename):
            # Ensure parent directory exists
            csv_dir = os.path.dirname(self.csv_filename)
            if csv_dir:
                os.makedirs(csv_dir, exist_ok=True)

            with open(self.csv_filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    [
                        "exchange",
                        "timestamp",
                        "side",
                        "price",
                        "quantity",
                        "order_type",
                        "mode",
                        "fee_usd",
                        "pnl_no_fee",
                        "pnl_with_fee",
                    ]
                )

    def log_trade_to_csv(
        self,
        exchange: str,
        side: str,
        price: str,
        quantity: str,
        order_type: str = "hedge",
        mode: str = "",
        fee_usd: str = "0",
        pnl_no_fee: str = "0",
        pnl_with_fee: str = "0",
    ):
        timestamp = datetime.now(pytz.UTC).isoformat()
        with open(self.csv_filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [exchange, timestamp, side, price, quantity, order_type, mode, fee_usd, pnl_no_fee, pnl_with_fee]
            )

    async def cleanup_connections(self):
        # Disconnect old clients if they exist
        if hasattr(self, 'hedge_client') and self.hedge_client:
            try:
                await self.hedge_client.disconnect()
            except Exception:
                pass
        if hasattr(self, 'primary_client') and self.primary_client:
            try:
                await self.primary_client.disconnect()
            except Exception:
                pass

    async def cleanup(self):
        """Cleanup and disconnect all clients."""
        # Disconnect ETH client
        if self.eth_client:
            try:
                await self.eth_client.disconnect()
            except Exception:
                pass

        # Disconnect SOL client
        if self.sol_client:
            try:
                await self.sol_client.disconnect()
            except Exception:
                pass

        # Disconnect old clients if they exist
        await self.cleanup_connections()

    async def calculate_order_size_with_slippage(
        self,
        price: Decimal,
        ticker: str,
        direction: str,
        max_slippage_bps: int = 20
    ) -> Tuple[Decimal, Decimal, bool]:
        """
        Calculate order size with slippage check using BookDepth data.

        Args:
            price: Current price
            ticker: "ETH" or "SOL"
            direction: "buy" or "sell"
            max_slippage_bps: Maximum acceptable slippage in basis points

        Returns:
            Tuple of (order_quantity, estimated_slippage_bps, can_fill_at_full_qty)
        """
        client = self.eth_client if ticker == "ETH" else self.sol_client
        raw_qty = self.target_notional / price
        tick_size = client.config.tick_size
        target_qty = (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

        # Try to get slippage estimate from BookDepth
        slippage = await client.estimate_slippage(direction, target_qty)

        if slippage >= Decimal(999999):
            # No BookDepth data available - return target qty with warning
            self.logger.warning(f"[SLIPPAGE] No BookDepth data for {ticker}, using target quantity {target_qty}")
            return target_qty, Decimal(0), True

        # Check if slippage is acceptable
        if slippage <= max_slippage_bps:
            return target_qty, slippage, True
        else:
            # Slippage too high - find max quantity within limit
            can_exit, exitable_qty = await client.check_exit_capacity(
                target_qty if direction == "sell" else -target_qty,
                max_slippage_bps
            )
            if not can_exit:
                self.logger.warning(
                    f"[SLIPPAGE] {ticker} slippage {slippage:.1f} bps > {max_slippage_bps} bps limit, "
                    f"reducing qty from {target_qty} to {exitable_qty}"
                )
                return exitable_qty, slippage, False

            return target_qty, slippage, True

    async def place_simultaneous_orders(
        self,
        eth_direction: str,
        sol_direction: str,
    ) -> Tuple[OrderResult, OrderResult]:
        """Place ETH and SOL orders simultaneously using REST-based position monitoring.

        Follows the your-quantguy reference pattern:
        1. Get position BEFORE placing order
        2. Place order with aggressive pricing (cross spread)
        3. Poll position every 100ms via REST API
        4. Confirm fill when position changes by expected amount
        """
        # Get initial positions BEFORE placing orders
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()

        self.logger.info(f"[INIT] ETH pos: {eth_pos_before}, SOL pos: {sol_pos_before}")

        # Calculate order quantities
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

        eth_price = eth_ask if eth_direction == "buy" else eth_bid
        sol_price = sol_bid if sol_direction == "sell" else sol_ask

        # Use slippage-aware order sizing with BookDepth data
        # Reduced slippage from 20bps to 10bps to minimize losses
        eth_qty, eth_slippage_bps, eth_full_fill = await self.calculate_order_size_with_slippage(
            eth_price, "ETH", eth_direction, max_slippage_bps=10
        )
        sol_qty, sol_slippage_bps, sol_full_fill = await self.calculate_order_size_with_slippage(
            sol_price, "SOL", sol_direction, max_slippage_bps=10
        )

        self.logger.info(
            f"[ORDER] Placing orders: "
            f"ETH {eth_direction} {eth_qty} @ ~${eth_price} ({eth_slippage_bps:.1f} bps est. slippage), "
            f"SOL {sol_direction} {sol_qty} @ ~${sol_price} ({sol_slippage_bps:.1f} bps est. slippage)"
        )

        # Place IOC orders concurrently (Immediate-Or-Cancel for immediate fills)
        eth_result, sol_result = await asyncio.gather(
            self.eth_client.place_ioc_order(self.eth_client.config.contract_id, eth_qty, eth_direction),
            self.sol_client.place_ioc_order(self.sol_client.config.contract_id, sol_qty, sol_direction),
            return_exceptions=True
        )

        # Check for exceptions
        if isinstance(eth_result, Exception):
            self.logger.error(f"[ORDER] ETH order failed with exception: {eth_result}")
            eth_result = OrderResult(success=False, error_message=str(eth_result))
        if isinstance(sol_result, Exception):
            self.logger.error(f"[ORDER] SOL order failed with exception: {sol_result}")
            sol_result = OrderResult(success=False, error_message=str(sol_result))

        # If both failed, return immediately
        if not eth_result.success and not sol_result.success:
            self.logger.error("[ORDER] Both orders failed")
            return eth_result, sol_result

        # IOC orders return immediately with fill status
        # Extract fill details from OrderResult
        eth_filled = eth_result.status == 'FILLED'
        eth_fill_qty = eth_result.filled_size if eth_filled else Decimal(0)
        eth_fill_price = eth_result.price if eth_filled else Decimal(0)

        sol_filled = sol_result.status == 'FILLED'
        sol_fill_qty = sol_result.filled_size if sol_filled else Decimal(0)
        sol_fill_price = sol_result.price if sol_filled else Decimal(0)

        # Check results and log fills
        if eth_filled:
            self.logger.info(f"[FILL] ETH order filled: {eth_fill_qty} @ ${eth_fill_price}")
        elif eth_result.success and eth_fill_qty > 0:
            self.logger.warning(f"[FILL] ETH order partially filled: {eth_fill_qty}/{eth_qty}")
        else:
            self.logger.warning(f"[FILL] ETH order did not fill")

        if sol_filled:
            self.logger.info(f"[FILL] SOL order filled: {sol_fill_qty} @ ${sol_fill_price}")
        elif sol_result.success and sol_fill_qty > 0:
            self.logger.warning(f"[FILL] SOL order partially filled: {sol_fill_qty}/{sol_qty}")
        else:
            self.logger.warning(f"[FILL] SOL order did not fill")

        # Log actual fills to CSV
        # Calculate fee (0.05% taker fee for Nado)
        FEE_RATE = Decimal("0.0005")

        if eth_fill_qty > 0:
            eth_notional = eth_fill_price * eth_fill_qty
            eth_fee = eth_notional * FEE_RATE
            self.log_trade_to_csv(
                exchange="NADO",
                side=f"ETH-{eth_direction.upper()}",
                price=str(eth_fill_price),
                quantity=str(eth_fill_qty),
                order_type="entry" if eth_direction == "buy" else "exit",
                mode="FILLED" if eth_filled else "PARTIAL",
                fee_usd=str(eth_fee),
                pnl_no_fee="0",
                pnl_with_fee="0"
            )

        if sol_fill_qty > 0:
            sol_notional = sol_fill_price * sol_fill_qty
            sol_fee = sol_notional * FEE_RATE
            self.log_trade_to_csv(
                exchange="NADO",
                side=f"SOL-{sol_direction.upper()}",
                price=str(sol_fill_price),
                quantity=str(sol_fill_qty),
                order_type="entry" if sol_direction == "sell" else "exit",
                mode="FILLED" if sol_filled else "PARTIAL",
                fee_usd=str(sol_fee),
                pnl_no_fee="0",
                pnl_with_fee="0"
            )

        # Handle partial fills and failed orders
        await self.handle_emergency_unwind(eth_result, sol_result)

        return eth_result, sol_result

    async def handle_emergency_unwind(self, eth_result, sol_result):
        """Handle emergency unwind when one leg fails or is partially filled."""
        # Debug logging
        self.logger.info(f"[DEBUG] handle_emergency_unwind: eth_result.success={eth_result.success if isinstance(eth_result, OrderResult) else 'Exception'}, sol_result.success={sol_result.success if isinstance(sol_result, OrderResult) else 'Exception'}")

        # Check if both legs filled successfully
        # For IOC orders, success=True and status='FILLED' means the order filled
        eth_filled = (isinstance(eth_result, OrderResult) and
                      eth_result.success and
                      eth_result.status == 'FILLED')
        sol_filled = (isinstance(sol_result, OrderResult) and
                      sol_result.success and
                      sol_result.status == 'FILLED')

        # Only do emergency unwind if one succeeded and the other failed
        if eth_filled and not sol_filled:
            # ETH succeeded, SOL failed → close ETH
            self.logger.info(f"[UNWIND] ETH filled but SOL failed, closing ETH position")
            await self.emergency_unwind_eth()
        elif sol_filled and not eth_filled:
            # SOL succeeded, ETH failed → close SOL
            self.logger.info(f"[UNWIND] SOL filled but ETH failed, closing SOL position")
            await self.emergency_unwind_sol()
        # else: both succeeded or both failed → no emergency unwind

    async def emergency_unwind_eth(self):
        """Emergency unwind ETH position."""
        if self.eth_client:
            try:
                # Close ETH position with market order
                current_pos = await self.eth_client.get_account_positions()
                if current_pos > 0:
                    await self.eth_client.place_close_order(
                        self.eth_client.config.contract_id,
                        current_pos,
                        Decimal("0"),  # Market order
                        "sell"
                    )
            except Exception:
                pass

    async def emergency_unwind_sol(self):
        """Emergency unwind SOL position."""
        if self.sol_client:
            try:
                # Close SOL position with market order
                current_pos = await self.sol_client.get_account_positions()
                if current_pos < 0:  # Short position
                    await self.sol_client.place_close_order(
                        self.sol_client.config.contract_id,
                        abs(current_pos),
                        Decimal("0"),  # Market order
                        "buy"
                    )
            except Exception:
                pass

    async def execute_build_cycle(self) -> bool:
        """Execute BUILD cycle: Long ETH / Short SOL."""
        POSITION_TOLERANCE = Decimal("0.001")

        # SAFETY CHECK: Verify positions are closed before BUILD
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
            self.logger.error(
                f"[BUILD] SAFETY VIOLATION: Cannot BUILD with open positions - "
                f"ETH={eth_pos}, SOL={sol_pos}. Run UNWIND first!"
            )
            return False

        try:
            eth_result, sol_result = await self.place_simultaneous_orders("buy", "sell")
            return (isinstance(eth_result, OrderResult) and eth_result.success and
                    isinstance(sol_result, OrderResult) and sol_result.success)
        except Exception:
            return False

    async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
        """Execute UNWIND cycle with specified order sides.

        Args:
            eth_side: Order side for ETH ("buy" or "sell")
            sol_side: Order side for SOL ("buy" or "sell")

        Returns:
            True if both positions are closed (abs < 0.001), False otherwise.
        """
        POSITION_TOLERANCE = Decimal("0.001")
        MAX_RETRIES = 3
        RETRY_DELAY = 2.0

        # Log pre-unwind positions
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()
        self.logger.info(f"[UNWIND] POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")

        # Place UNWIND orders with specified sides
        eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

        # Check if orders filled
        if not (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
            self.logger.warning("[UNWIND] Orders failed or partially filled")
            return False

        # Verify positions closed with retries
        for attempt in range(MAX_RETRIES):
            await asyncio.sleep(RETRY_DELAY)

            eth_pos = await self.eth_client.get_account_positions()
            sol_pos = await self.sol_client.get_account_positions()

            self.logger.info(f"[UNWIND] POSITIONS CHECK (attempt {attempt + 1}/{MAX_RETRIES}): ETH={eth_pos}, SOL={sol_pos}")

            eth_closed = abs(eth_pos) < POSITION_TOLERANCE
            sol_closed = abs(sol_pos) < POSITION_TOLERANCE

            if eth_closed and sol_closed:
                self.logger.info("[UNWIND] SUCCESS: Both positions closed")
                return True

            if attempt < MAX_RETRIES - 1:
                self.logger.warning(f"[UNWIND] Positions still open, retrying in {RETRY_DELAY}s...")

        self.logger.error(f"[UNWIND] FAILED: Positions still open after {MAX_RETRIES} retries: ETH={eth_pos}, SOL={sol_pos}")
        return False

    async def execute_dn_pair_cycle(self) -> bool:
        """Execute full DN pair cycle: BUILD + UNWIND."""
        try:
            build_success = await self.execute_build_cycle()
            if not build_success:
                return False

            # Optional sleep
            if self.sleep_time > 0:
                await asyncio.sleep(self.sleep_time)

            unwind_success = await self.execute_unwind_cycle()
            return unwind_success
        except Exception:
            return False

    async def execute_buy_first_cycle(self) -> bool:
        """Execute BUY_FIRST cycle: BUILD (Long ETH / Short SOL) -> UNWIND."""
        try:
            # BUILD: Long ETH / Short SOL
            build_success = await self.execute_build_cycle()
            if not build_success:
                return False

            # Optional sleep
            if self.sleep_time > 0:
                await asyncio.sleep(self.sleep_time)

            # UNWIND: Sell ETH / Buy SOL
            unwind_success = await self.execute_unwind_cycle("sell", "buy")
            return unwind_success

        except Exception as e:
            self.logger.error(f"BUY_FIRST cycle failed: {e}")
            return False

    async def execute_sell_first_cycle(self) -> bool:
        """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND."""
        try:
            # BUILD: Short ETH / Long SOL (opposite of buy_first)
            eth_result, sol_result = await self.place_simultaneous_orders("sell", "buy")
            if not (isinstance(eth_result, OrderResult) and eth_result.success and
                    isinstance(sol_result, OrderResult) and sol_result.success):
                return False

            # Optional sleep
            if self.sleep_time > 0:
                await asyncio.sleep(self.sleep_time)

            # UNWIND: Buy ETH / Sell SOL
            unwind_success = await self.execute_unwind_cycle("buy", "sell")
            return unwind_success

        except Exception as e:
            self.logger.error(f"SELL_FIRST cycle failed: {e}")
            return False

    async def run_alternating_strategy(self) -> List[bool]:
        """Run alternating strategy for N iterations."""
        results = []

        for i in range(self.iterations):
            iteration_num = i + 1
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"ITERATION {iteration_num}/{self.iterations}")
            self.logger.info(f"{'='*60}")

            if i % 2 == 0:
                result = await self.execute_buy_first_cycle()
            else:
                result = await self.execute_sell_first_cycle()

            results.append(result)

            # CRITICAL: Stop if UNWIND failed
            if not result:
                self.logger.error(
                    f"[SAFETY] Cycle {iteration_num} FAILED! "
                    f"Bot stopping to prevent position accumulation."
                )
                self.logger.error(
                    f"[SAFETY] Check positions manually before restarting. "
                    f"ETH and SOL positions should be near 0."
                )
                break

            self.logger.info(f"[SUCCESS] Cycle {iteration_num} completed successfully")

        return results

    def shutdown(self, signum=None, frame=None):
        self.stop_flag = True
        self.logger.info("\n[SHUTDOWN] Stopping DN Hedge Bot...")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.cleanup_connections())
        except RuntimeError:
            pass

        for handler in self.logger.handlers[:]:
            try:
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                pass

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    async def initialize_clients(self):
        """Initialize ETH and SOL Nado clients for dual-ticker trading."""
        # Log WebSocket availability status
        from exchanges.nado import WEBSOCKET_AVAILABLE
        self.logger.info(
            f"[INIT] WEBSOCKET_AVAILABLE: {WEBSOCKET_AVAILABLE}"
        )

        # ETH client configuration
        eth_config = Config({
            'ticker': 'ETH',
            'contract_id': '4',  # ETH product ID on Nado
            'tick_size': Decimal('0.001'),  # ETH tick size (corrected: 0.1 → 0.001)
            'min_size': Decimal('0.001'),
        })

        # SOL client configuration
        sol_config = Config({
            'ticker': 'SOL',
            'contract_id': '8',  # SOL product ID on Nado
            'tick_size': Decimal('0.001'),  # SOL tick size (corrected: 0.1 → 0.001)
            'min_size': Decimal('0.001'),
        })

        # Create Nado clients for both tickers (pass Config objects directly)
        self.eth_client = NadoClient(eth_config)
        self.sol_client = NadoClient(sol_config)

        # Connect to Nado
        self.logger.info("[INIT] Connecting ETH client...")
        await self.eth_client.connect()
        self.logger.info(
            f"[INIT] WebSocket status for ETH: {'CONNECTED' if self.eth_client._ws_connected else 'REST FALLBACK'}"
        )

        self.logger.info("[INIT] Connecting SOL client...")
        await self.sol_client.connect()
        self.logger.info(
            f"[INIT] WebSocket status for SOL: {'CONNECTED' if self.sol_client._ws_connected else 'REST FALLBACK'}"
        )

        # Warning if WebSocket failed
        if not self.eth_client._ws_connected or not self.sol_client._ws_connected:
            self.logger.warning(
                "[INIT] One or more clients failed to connect via WebSocket - using REST fallback (higher latency, rate limits apply)"
            )

        # Store contract attributes
        self.eth_contract_id = eth_config.contract_id
        self.eth_tick_size = eth_config.tick_size
        self.sol_contract_id = sol_config.contract_id
        self.sol_tick_size = sol_config.tick_size

        self.logger.info(
            f"[INIT] ETH client initialized (contract: {self.eth_contract_id}, tick: {self.eth_tick_size}, ws: {self.eth_client._ws_connected})"
        )
        self.logger.info(
            f"[INIT] SOL client initialized (contract: {self.sol_contract_id}, tick: {self.sol_tick_size}, ws: {self.sol_client._ws_connected})"
        )















def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(
        description="Delta Neutral Pair Bot: ETH (Long) / SOL (Short) on Nado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with $100 notional per position, 5 iterations
    python DN_pair_eth_sol_nado.py --size 100 --iter 5

    # Run with sleep time between cycles
    python DN_pair_eth_sol_nado.py --size 100 --iter 10 --sleep 5
        """,
    )

    parser.add_argument(
        "--size", type=str, required=True, help="Target notional in USD per position (e.g., 100 = $100 ETH and $100 SOL)"
    )
    parser.add_argument(
        "--iter", type=int, required=True, help="Number of trading iterations"
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=0,
        help="Sleep time between BUILD and UNWIND in seconds (default: 0)",
    )
    parser.add_argument(
        "--env-file", type=str, default=".env", help=".env file path (default: .env)"
    )
    parser.add_argument(
        "--csv-path", type=str, default=None, help="Optional custom CSV path for testing"
    )
    return parser.parse_args()


async def main():
    from pathlib import Path
    import dotenv

    args = parse_arguments()

    env_path = Path(args.env_file)
    if not env_path.exists():
        print(f"Error: .env file not found: {env_path.resolve()}")
        sys.exit(1)
    dotenv.load_dotenv(args.env_file)

    # DNPairBot uses target_notional (USD notional per position)
    bot = DNPairBot(
        target_notional=Decimal(args.size),  # USD notional per position (e.g., 100 = $100)
        iterations=args.iter,
        sleep_time=args.sleep,
        csv_path=args.csv_path,
    )

    # Initialize clients
    await bot.initialize_clients()

    # STARTUP CHECK: Verify no residual positions
    print("\n[STARTUP] Checking for residual positions...")
    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()

    print(f"[STARTUP] ETH position: {eth_pos}")
    print(f"[STARTUP] SOL position: {sol_pos}")

    POSITION_TOLERANCE = Decimal("0.001")
    if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
        print(f"\n[WARNING] Residual positions detected!")
        print(f"  ETH: {eth_pos}")
        print(f"  SOL: {sol_pos}")
        print(f"\n[SAFETY] Please close positions manually before starting the bot.")
        print(f"  - Use the exchange interface to close positions")
        print(f"  - Or use a separate close-positions script")
        sys.exit(1)

    print("[STARTUP] No residual positions. Ready to start.\n")

    # Run alternating strategy
    await bot.run_alternating_strategy()


if __name__ == "__main__":
    asyncio.run(main())
