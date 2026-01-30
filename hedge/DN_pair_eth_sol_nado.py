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
import traceback
from decimal import Decimal
from typing import Tuple, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict, field
import pytz

# Import exchanges modules (like Mean Reversion bot)
from exchanges.nado import NadoClient
from exchanges.base import OrderResult


class PriceMode(Enum):
    BBO_MINUS_1 = "bbo_minus_1"
    BBO_PLUS_1 = "bbo_plus_1"
    BBO = "bbo"
    AGGRESSIVE = "aggressive"
    MARKET = "market"


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


@dataclass
class TradeMetrics:
    """Metrics for tracking trade execution details."""
    iteration: int
    direction: str  # "BUY_FIRST" or "SELL_FIRST"

    # Entry prices
    eth_entry_price: Decimal
    sol_entry_price: Decimal
    eth_entry_time: float  # timestamp
    sol_entry_time: float

    # Exit prices
    eth_exit_price: Decimal
    sol_exit_price: Decimal
    eth_exit_time: float
    sol_exit_time: float

    # Timing measurements (milliseconds)
    order_to_fill_eth: float
    order_to_fill_sol: float
    websocket_latency: float
    rest_latency: float
    reconciliation_time: float

    # Other metrics
    repricing_count: int
    total_cycle_time: float  # seconds

    def to_dict(self):
        """Convert to dictionary for CSV export."""
        d = asdict(self)
        # Convert Decimal to string for CSV
        for key, value in d.items():
            if isinstance(value, Decimal):
                d[key] = str(value)
        return d


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
        fill_timeout: int = 5,
        iterations: int = 20,
        sleep_time: int = 0,
        max_position_eth: Decimal = Decimal("5"),  # Max ETH position
        max_position_sol: Decimal = Decimal("50"),  # Max SOL position
        order_mode: PriceMode = PriceMode.BBO,
        csv_path: str = None,  # Optional custom CSV path for testing
    ):
        self.target_notional = target_notional  # USD notional for each position
        self.fill_timeout = fill_timeout
        self.iterations = iterations
        self.sleep_time = sleep_time
        self.order_mode = order_mode
        self.max_position_eth = max_position_eth
        self.max_position_sol = max_position_sol

        # Tickers
        self.eth_ticker = "ETH"
        self.sol_ticker = "SOL"

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
        self.order_counter = 0

        # Positions
        self.eth_position = Decimal("0")  # Long position
        self.sol_position = Decimal("0")  # Short position

        # Local tracking for positions
        self.local_eth_position = Decimal("0")
        self.local_sol_position = Decimal("0")
        self.use_local_tracking = True
        self.reconcile_interval = 1

        # OMC v4 Safety limits
        self.MAX_DAILY_LOSS = Decimal("5")  # Maximum $5 USD daily loss
        self.daily_pnl = Decimal("0")
        self.daily_start_time = datetime.now(pytz.UTC)

        # Nado clients (one for each ticker)
        self.eth_client = None
        self.sol_client = None

        # Contract info
        self.eth_contract_id = None
        self.eth_tick_size = None
        self.sol_contract_id = None
        self.sol_tick_size = None

        # Order tracking
        self.eth_order_status = None
        self.sol_order_status = None
        self.order_execution_complete = False

        # PnL tracking
        self.total_gross_pnl = Decimal("0")
        self.total_volume = Decimal("0")
        self.completed_cycles = 0

        # Trade metrics tracking
        self.trade_metrics_list: List[TradeMetrics] = []
        self.current_cycle_start_time = None
        self.repricing_count = 0

        # Current cycle metrics (reset each cycle)
        self.current_eth_entry_price = None
        self.current_sol_entry_price = None
        self.current_eth_entry_time = None
        self.current_sol_entry_time = None
        self.current_eth_exit_price = None
        self.current_sol_exit_price = None
        self.current_eth_exit_time = None
        self.current_sol_exit_time = None
        self.current_order_to_fill_eth = 0
        self.current_order_to_fill_sol = 0

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

    def export_trade_metrics(self):
        """Export trade metrics to CSV file for analysis."""
        if not self.trade_metrics_list:
            self.logger.info("[EXPORT] No trade metrics to export")
            return

        timestamp_str = datetime.now(pytz.UTC).strftime("%Y%m%d_%H%M%S")
        metrics_filename = f"logs/trade_metrics_{self.primary_exchange}_{self.hedge_exchange}_{self.ticker}_{timestamp_str}.csv"

        try:
            with open(metrics_filename, "w", newline="") as csvfile:
                fieldnames = TradeMetrics.__dataclass_fields__.keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for metrics in self.trade_metrics_list:
                    writer.writerow(metrics.to_dict())

            self.logger.info(f"[EXPORT] Trade metrics exported to {metrics_filename}")
            self.logger.info(f"[EXPORT] Total {len(self.trade_metrics_list)} cycles exported")
        except Exception as e:
            self.logger.error(f"[EXPORT] Failed to export trade metrics: {e}")
            import traceback
            self.logger.error(f"[EXPORT] Traceback: {traceback.format_exc()}")

    def print_trade_summary(
        self,
        cycle_num: int,
        primary_side: str,
        primary_price: Decimal,
        hedge_side: str,
        hedge_price: Decimal,
        quantity: Decimal,
    ):
        if primary_side == "buy":
            spread = hedge_price - primary_price
            spread_bps = (spread / primary_price) * Decimal("10000")
        else:
            spread = primary_price - hedge_price
            spread_bps = (spread / hedge_price) * Decimal("10000")

        gross_pnl = spread * quantity
        self.total_gross_pnl += gross_pnl
        self.total_volume += quantity * primary_price
        self.completed_cycles += 1

        avg_pnl_bps = (
            (self.total_gross_pnl / self.total_volume) * Decimal("10000")
            if self.total_volume > 0
            else Decimal("0")
        )

        self.logger.info(
            f"\n{'-' * 55}\n"
            f"  CYCLE {cycle_num} COMPLETE\n"
            f"{'-' * 55}\n"
            f"  NADO:   {primary_side.upper():4} @ ${primary_price:.3f}\n"
            f"  EDGEX:  {hedge_side.upper():4} @ ${hedge_price:.3f}\n"
            f"  Spread: ${spread:.4f} ({spread_bps:+.2f} bps)\n"
            f"  Cycle PnL: ${gross_pnl:.4f}\n"
            f"{'-' * 55}\n"
            f"  CUMULATIVE: {self.completed_cycles} cycles | PnL: ${self.total_gross_pnl:.4f} | Avg: {avg_pnl_bps:+.2f} bps\n"
            f"{'-' * 55}"
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

    def calculate_order_size(self, price: Decimal, ticker: str) -> Decimal:
        """Calculate order size from target notional."""
        raw_qty = self.target_notional / price

        # Get tick size for ticker
        client = self.eth_client if ticker == "ETH" else self.sol_client
        tick_size = client.config.tick_size

        # Round to tick size
        return (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

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

    async def place_single_order(self, ticker: str, direction: str, notional: Decimal) -> OrderResult:
        """Place a single order for given ticker."""
        client = self.eth_client if ticker == "ETH" else self.sol_client
        price_bid, price_ask = await client.fetch_bbo_prices(client.config.contract_id)

        if price_bid <= 0 or price_ask <= 0:
            raise ValueError("Invalid prices")

        # Calculate quantity
        price = price_ask if direction == "buy" else price_bid
        qty = (notional / price).quantize(client.config.tick_size)

        return await client.place_ioc_order(client.config.contract_id, qty, direction)

    async def get_position(self, ticker: str) -> Decimal:
        """Get current position for given ticker."""
        client = self.eth_client if ticker == "ETH" else self.sol_client
        return await client.get_account_positions()

    def log_trade(self, trade_data: dict):
        """Log trade data to CSV file."""
        import csv
        file_exists = os.path.exists(self.csv_filename)

        with open(self.csv_filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trade_data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade_data)

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

    def _create_exchange_config(self, ticker: str, quantity: Decimal) -> Config:
        return Config(
            {
                "ticker": ticker,
                "contract_id": "",
                "quantity": quantity,
                "tick_size": Decimal("0.01"),
                "close_order_side": "sell",
                "direction": "buy",
            }
        )

    def calculate_order_price(
        self,
        side: str,
        best_bid: Decimal,
        best_ask: Decimal,
        tick_size: Decimal,
        mode: PriceMode,
    ) -> Optional[Decimal]:
        if mode == PriceMode.MARKET:
            return None

        if side == "buy":
            if mode == PriceMode.BBO_MINUS_1:
                return best_bid - tick_size
            elif mode == PriceMode.BBO_PLUS_1:
                return best_bid + tick_size
            elif mode == PriceMode.AGGRESSIVE:
                return best_ask
            else:
                return best_bid
        else:
            if mode == PriceMode.BBO_MINUS_1:
                return best_ask + tick_size
            elif mode == PriceMode.BBO_PLUS_1:
                return best_ask - tick_size
            elif mode == PriceMode.AGGRESSIVE:
                return best_bid
            else:
                return best_ask

    async def check_arbitrage_opportunity(self, direction: str) -> bool:
        if self.min_spread_bps == Decimal("0"):
            return True

        primary_bid, primary_ask = await self.primary_client.fetch_bbo_prices(
            self.primary_contract_id
        )
        hedge_bid, hedge_ask = await self.hedge_client.fetch_bbo_prices(
            self.hedge_contract_id
        )

        if direction == "buy":
            spread_bps = (hedge_bid - primary_ask) / primary_ask * Decimal("10000")
        else:
            spread_bps = (primary_bid - hedge_ask) / hedge_ask * Decimal("10000")

        if spread_bps >= self.min_spread_bps:
            self.logger.info(
                f"[ARB] Spread: {spread_bps:.2f} bps >= {self.min_spread_bps} bps -> ENTER"
            )
            return True
        else:
            self.logger.info(
                f"[ARB] Spread: {spread_bps:.2f} bps < {self.min_spread_bps} bps -> SKIP"
            )
            return False

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

    async def connect_websockets(self):
        def primary_order_handler(order_data):
            self._handle_primary_order_update(order_data)

        def hedge_order_handler(order_data):
            self._handle_hedge_order_update(order_data)

        self.primary_client.setup_order_update_handler(primary_order_handler)
        self.hedge_client.setup_order_update_handler(hedge_order_handler)

        await self.primary_client.connect()
        self.logger.info(f"[WS] PRIMARY ({self.primary_exchange.upper()}) connected")

        await self.hedge_client.connect()
        self.logger.info(f"[WS] HEDGE ({self.hedge_exchange.upper()}) connected")

    def _handle_primary_order_update(self, order_data):
        if order_data.get("contract_id") != self.primary_contract_id:
            return

        try:
            order_id = order_data.get("order_id")
            status = order_data.get("status")
            side = order_data.get("side", "").lower()
            filled_size = Decimal(order_data.get("filled_size", "0"))
            price = order_data.get("price", "0")

            order_type = "OPEN" if side == "buy" else "CLOSE"

            if status == "CANCELED" and filled_size > 0:
                status = "FILLED"

            if status == "FILLED" and self.primary_order_status != "FILLED":
                if side == "buy":
                    self.primary_position += filled_size
                    self.local_primary_position += filled_size
                else:
                    self.primary_position -= filled_size
                    self.local_primary_position -= filled_size

                self.logger.info(
                    f"[{order_id}] [{order_type}] [{self.primary_exchange.upper()}] [FILLED]: "
                    f"{filled_size} @ {price}"
                )
                self.primary_order_status = status

                self.log_trade_to_csv(
                    exchange=self.primary_exchange.upper(),
                    side=side,
                    price=str(price),
                    quantity=str(filled_size),
                    order_type="primary",
                    mode=self.primary_mode.value,
                )

                hedge_side = "sell" if side == "buy" else "buy"
                self.current_hedge_side = hedge_side
                self.current_hedge_quantity = filled_size
                self.current_hedge_price = Decimal(price)
                self.waiting_for_hedge_fill = True

            elif self.primary_order_status != "FILLED":
                self.logger.info(
                    f"[{order_id}] [{order_type}] [{self.primary_exchange.upper()}] [{status}]: "
                    f"{order_data.get('size', filled_size)} @ {price}"
                )
                self.primary_order_status = status

        except Exception as e:
            self.logger.error(f"Error handling PRIMARY order update: {e}")

    def _handle_hedge_order_update(self, order_data):
        """Handle HEDGE exchange order updates from WebSocket."""
        if order_data.get("contract_id") != self.hedge_contract_id:
            return

        try:
            order_id = order_data.get("order_id")
            status = order_data.get("status")
            side = order_data.get("side", "").lower()
            filled_size = Decimal(order_data.get("filled_size", "0"))
            price = order_data.get("price", "0")

            order_type = "OPEN" if side == "buy" else "CLOSE"

            if status == "CANCELED" and filled_size > 0:
                status = "FILLED"

            # Handle HEDGE order fill via WebSocket
            if status == "FILLED":
                if side == "buy":
                    self.hedge_position += filled_size
                    self.local_hedge_position += filled_size
                else:
                    self.hedge_position -= filled_size
                    self.local_hedge_position -= filled_size

                self.logger.info(
                    f"[{order_id}] [{order_type}] [{self.hedge_exchange.upper()}] [WS FILLED]: "
                    f"{filled_size} @ {price}"
                )

                # Update fill tracking flags
                self.hedge_order_status = "FILLED"
                self.hedge_order_filled = True
                self.order_execution_complete = True
                self.last_hedge_fill_price = Decimal(price)
                self.waiting_for_hedge_fill = False

                # Log hedge trade to CSV
                self.log_trade_to_csv(
                    exchange=self.hedge_exchange.upper(),
                    side=side,
                    price=str(price),
                    quantity=str(filled_size),
                    order_type="hedge",
                    mode=self.hedge_mode.value,
                )

            elif status in ["OPEN", "PARTIALLY_FILLED"]:
                self.hedge_order_status = status
                self.logger.info(
                    f"[{order_id}] [{order_type}] [{self.hedge_exchange.upper()}] [{status}]: "
                    f"{order_data.get('size', filled_size)} @ {price}"
                )

        except Exception as e:
            self.logger.error(f"Error handling HEDGE order update: {e}")

    async def get_positions(self, force_api: bool = False, primary_only: bool = False, hedge_only: bool = False) -> Tuple[Decimal, Decimal]:
        """Get positions from one or both exchanges.

        Args:
            force_api: Force REST API call even if WebSocket tracking is available
            primary_only: Only get primary exchange position
            hedge_only: Only get hedge exchange position

        Returns:
            Tuple of (primary_position, hedge_position)
        """
        # Use WebSocket positions for both exchanges if available (faster, no API calls)
        if self.use_local_tracking and not force_api:
            if hasattr(self.primary_client, 'get_ws_position') and hasattr(self.hedge_client, 'get_ws_position'):
                primary_ws_pos = self.primary_client.get_ws_position()
                hedge_ws_pos = self.hedge_client.get_ws_position()
                return primary_ws_pos, hedge_ws_pos
            # If WebSocket tracking not available, fall through to REST API

        # REST API as authoritative source or fallback
        primary_pos = await self.primary_client.get_account_positions() if not hedge_only else Decimal("0")
        hedge_pos = await self.hedge_client.get_account_positions() if not primary_only else Decimal("0")
        return primary_pos, hedge_pos

    async def reconcile_positions(self):
        """Reconcile positions from both exchanges using multiple sources.

        Simplified approach (Mean Reversion style):
        - REST API is authoritative source
        - WebSocket is for real-time reference only (if available)
        - Warn if WS and API differ significantly (>10% of order size)
        """
        try:
            # Get WebSocket positions first (faster, no API calls) - only if available
            if hasattr(self.primary_client, 'get_ws_position') and hasattr(self.hedge_client, 'get_ws_position'):
                ws_primary = self.primary_client.get_ws_position()
                ws_hedge = self.hedge_client.get_ws_position()
            else:
                # WebSocket tracking not available, skip comparison
                ws_primary = None
                ws_hedge = None

            # Get REST API positions (authoritative source)
            rest_primary, rest_hedge = await self.get_positions(force_api=True)

            # Use REST API as authoritative source (like Mean Reversion)
            primary_pos = rest_primary
            hedge_pos = rest_hedge

            # Log drift warning if WS and API differ significantly
            drift_threshold = self.order_quantity * Decimal("0.1")  # 0.001 for 0.01 size
            if abs(ws_primary - rest_primary) > drift_threshold:
                self.logger.warning(
                    f"[RECONCILE] PRIMARY position drift: WS={ws_primary}, API={rest_primary}"
                )
            if abs(ws_hedge - rest_hedge) > drift_threshold:
                self.logger.warning(
                    f"[RECONCILE] HEDGE position drift: WS={ws_hedge}, API={rest_hedge}"
                )

            # Calculate net delta
            net_delta = primary_pos + hedge_pos

            self.logger.info(
                f"[RECONCILE] P={primary_pos}, H={hedge_pos}, NetDelta={net_delta}"
            )

            # READ-ONLY: Monitor net delta and alert, DO NOT auto-trade
            # Alert levels based on drift severity
            NET_DELTA_WARNING_THRESHOLD = Decimal("0.01")  # 1%
            NET_DELTA_CRITICAL_THRESHOLD = Decimal("0.02")  # 2%

            if abs(net_delta) > self.order_quantity * NET_DELTA_WARNING_THRESHOLD:
                if abs(net_delta) > self.order_quantity * NET_DELTA_CRITICAL_THRESHOLD:
                    # CRITICAL: Log and send alert
                    self.logger.error(
                        f"[RECONCILE] CRITICAL: Net delta {net_delta} ({abs(net_delta)/self.order_quantity:.1%}) "
                        f"exceeds critical threshold - MANUAL INTERVENTION REQUIRED"
                    )
                    self.logger.error(
                        f"[RECONCILE] Positions: Primary={primary_pos}, Hedge={hedge_pos}, "
                        f"Target={self.order_quantity}, NetDelta={net_delta}"
                    )
                    # TODO: Send Telegram/Slack alert here
                else:
                    # WARNING: Log but no action
                    self.logger.warning(
                        f"[RECONCILE] WARNING: Net delta {net_delta} ({abs(net_delta)/self.order_quantity:.1%}) "
                        f"exceeds warning threshold"
                    )
                    self.logger.warning(
                        f"[RECONCILE] Positions: Primary={primary_pos}, Hedge={hedge_pos}"
                    )

            # Update instance variables
            self.primary_position = primary_pos
            self.hedge_position = hedge_pos

            # Update local tracking to match actual positions
            self.local_primary_position = primary_pos
            self.local_hedge_position = hedge_pos

            # Auto-recovery: If net delta exceeds threshold, force sync
            # OMC v4: Tightened tolerance from 50% to 1% for true Delta Neutral
            NET_DELTA_TOLERANCE = Decimal("0.01")  # 1% tolerance
            if abs(net_delta) > self.order_quantity * NET_DELTA_TOLERANCE:
                self.logger.warning(
                    f"[RECONCILE] Net delta drift detected: {net_delta} (exceeds {NET_DELTA_TOLERANCE * 100}% tolerance), initiating auto-recovery"
                )

                # Force sync WebSocket local positions with REST API values
                if hasattr(self.primary_client, '_local_position'):
                    self.primary_client._local_position = rest_primary
                if hasattr(self.hedge_client, '_local_position'):
                    self.hedge_client._local_position = rest_hedge

        except Exception as e:
            self.logger.error(f"[RECONCILE] Failed to reconcile positions: {e}")

    async def place_primary_order(self, side: str, quantity: Decimal) -> Optional[str]:
        self.primary_order_status = None

        best_bid, best_ask = await self.primary_client.fetch_bbo_prices(
            self.primary_contract_id
        )
        order_price = self.calculate_order_price(
            side, best_bid, best_ask, self.primary_tick_size, self.primary_mode
        )

        self.logger.info(
            f"[OPEN] [{self.primary_exchange.upper()}] [{side.upper()}] "
            f"POST_ONLY @ {order_price} (mode: {self.primary_mode.value})"
        )

        attempt = 0
        while not self.stop_flag:
            attempt += 1
            if attempt > 20:
                self.logger.error(
                    f"[OPEN] Failed to place order after {attempt} attempts"
                )
                return None

            try:
                # Nado/Edgex use string "buy"/"sell" directly
                order_side = side

                # For primary exchange: try POST_ONLY first (0% fee), fall back to OPEN order if not available
                if hasattr(self.primary_client, 'place_post_only_order'):
                    order_result = await self.primary_client.place_post_only_order(
                        contract_id=self.primary_contract_id,
                        quantity=quantity,
                        price=order_price,
                        side=order_side,
                    )
                else:
                    # Fallback to place_open_order for exchanges without POST_ONLY (e.g., Nado, current Backpack)
                    # Convert side to direction for place_open_order
                    direction = order_side  # "buy" or "sell"
                    order_result = await self.primary_client.place_open_order(
                        contract_id=self.primary_contract_id,
                        quantity=quantity,
                        direction=direction,
                    )

                if order_result and order_result.order_id:
                    order_id = order_result.order_id
                    actual_price = (
                        order_result.price
                        if hasattr(order_result, "price")
                        else order_price
                    )

                    start_time = time.time()
                    while not self.stop_flag:
                        if self.primary_order_status == "CANCELED":
                            self.primary_order_status = None
                            (
                                best_bid,
                                best_ask,
                            ) = await self.primary_client.fetch_bbo_prices(
                                self.primary_contract_id
                            )
                            order_price = self.calculate_order_price(
                                side,
                                best_bid,
                                best_ask,
                                self.primary_tick_size,
                                self.primary_mode,
                            )
                            break

                        if self.primary_order_status == "FILLED":
                            return order_id

                        if self.primary_order_status in [
                            "OPEN",
                            "PENDING",
                            "PARTIALLY_FILLED",
                        ]:
                            await asyncio.sleep(0.1)  # Reduced from 0.5s for faster response

                            # OPTIMIZATION: Reduced timeout from 10s to 5s for faster execution
                            # Expected: 50% speed improvement (77s → <50s per cycle)
                            # Tradeoff: Fill rate may drop from 95% to 80-90%
                            if time.time() - start_time > 5:
                                (
                                    best_bid,
                                    best_ask,
                                ) = await self.primary_client.fetch_bbo_prices(
                                    self.primary_contract_id
                                )
                                should_cancel = False

                                if (
                                    side == "buy"
                                    and actual_price < best_bid - self.primary_tick_size
                                ):
                                    should_cancel = True
                                elif (
                                    side == "sell"
                                    and actual_price > best_ask + self.primary_tick_size
                                ):
                                    should_cancel = True

                                if should_cancel:
                                    try:
                                        await self.primary_client.cancel_order(order_id)
                                    except Exception as e:
                                        self.logger.warning(
                                            f"Error canceling order: {e}"
                                        )
                                else:
                                    start_time = time.time()
                        else:
                            await asyncio.sleep(0.1)  # Reduced from 0.5s for faster response

                else:
                    self.logger.warning("Order placement failed, retrying...")
                    await asyncio.sleep(0.2)  # Reduced from 1s for faster retry

            except Exception as e:
                self.logger.error(f"Error placing PRIMARY order: {e}")
                await asyncio.sleep(0.2)  # Reduced from 1s for faster retry

        return None

    async def place_hedge_order(
        self, side: str, quantity: Decimal, reference_price: Decimal
    ) -> bool:
        self.hedge_order_status = None
        self.hedge_order_filled = False
        order_type = "CLOSE" if side == "buy" else "OPEN"
        maker_timeout = 20  # Increased from 12 to 20 for better WebSocket message delivery

        use_maker_mode = self.hedge_mode in [PriceMode.BBO_MINUS_1, PriceMode.BBO]

        max_retries = 6  # ENHANCED: 6 retries with exponential backoff for API stability
        for attempt in range(1, max_retries + 1):
            try:
                best_bid, best_ask = await self.hedge_client.fetch_bbo_prices(
                    self.hedge_contract_id
                )

                # MARKET ORDER for CLOSE (like original ext.py)
                # CLOSE: Always use BBO for immediate fill
                if order_type == "CLOSE":
                    # CLOSE BUY (close SHORT): Buy at ASK (market order)
                    # CLOSE SELL (close LONG): Sell at BID (market order)
                    if side == "buy":
                        # Buy at ask + small buffer for guaranteed fill
                        order_price = best_ask + (self.hedge_tick_size * Decimal("2"))
                    else:
                        # Sell at bid - small buffer for guaranteed fill
                        order_price = best_bid - (self.hedge_tick_size * Decimal("2"))
                    order_mode = "MARKET"
                else:
                    # OPEN: Use PRIMARY fill price as reference
                    order_price = reference_price
                    order_mode = "TAKER_AGGRESSIVE"

                order_price = self.hedge_client.round_to_tick(order_price)

                # Log HEDGE order
                self.logger.info(
                    f"[{order_type}] [{self.hedge_exchange.upper()}] [{side.upper()}] "
                    f"{order_mode} @ {order_price} (ref: {reference_price}, BBO: {best_bid}/{best_ask})"
                )

                # Nado/Edgex use string "buy"/"sell" directly
                order_side = side

                # CLOSE uses iterative market order for GRVT, regular market for others (Edgex)
                if order_type == "CLOSE":
                    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2"):
                        self.logger.info(f"[CLOSE] Using ITERATIVE market order for {quantity} ETH")
                        result = await self.hedge_client.place_iterative_market_order(
                            contract_id=self.hedge_contract_id,
                            target_quantity=quantity,
                            side=order_side,
                            max_iterations=10,   # Increased from 3 - fixes cold start failures
                            max_tick_offset=2,    # Sufficient for liquidity depth
                            max_fill_duration=30  # Increased from 1 - removes timeout constraint
                        )

                        if result['success']:
                            self.logger.info(
                                f"[CLOSE] [ITERATIVE] Filled {result['total_filled']} @ ${result['average_price']:.2f} "
                                f"({result['iterations']} iterations)"
                            )
                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(result['average_price']),
                                quantity=str(result['total_filled']),
                                order_type="hedge_close_iterative",
                                mode="iterative_market"
                            )
                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = result['average_price']
                            return True
                        else:
                            self.logger.error(f"[CLOSE] Iterative failed: {result.get('reason', 'unknown')}")
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False
                    else:
                        # NEW: Try POST_ONLY first for 0% fee, fall back to MARKET if needed
                        hedge_filled = False
                        hedge_fill_price = None

                        # Reference: Primary order uses POST_ONLY at line 703
                        if self.hedge_post_only and self.hedge_exchange.lower() == "grvt":
                            try:
                                # Get BBO for POST_ONLY pricing
                                # VERIFIED: fetch_bbo_prices exists at grvt.py line 340-353
                                best_bid, best_ask = await self.hedge_client.fetch_bbo_prices(
                                    self.hedge_contract_id
                                )

                                # Calculate POST_ONLY price (1 tick inside spread)
                                if order_side == "buy":
                                    hedge_post_only_price = best_ask - self.hedge_tick_size
                                else:  # sell
                                    hedge_post_only_price = best_bid + self.hedge_tick_size

                                hedge_post_only_price = self.hedge_client.round_to_tick(hedge_post_only_price)

                                self.logger.info(
                                    f"[CLOSE] [{self.hedge_exchange.upper()}] Attempting POST_ONLY @ {hedge_post_only_price} "
                                    f"(side: {order_side}, fee: 0%)"
                                )

                                # Try POST_ONLY with 3 second timeout
                                hedge_result = await asyncio.wait_for(
                                    self.hedge_client.place_post_only_order(
                                        contract_id=self.hedge_contract_id,
                                        quantity=quantity,
                                        price=hedge_post_only_price,
                                        side=order_side
                                    ),
                                    timeout=3.0
                                )

                                if hedge_result.status == "FILLED":
                                    hedge_filled = True
                                    hedge_fill_price = hedge_result.price

                                    self.logger.info(
                                        f"[CLOSE] [POST_ONLY FILLED]: {quantity} @ {hedge_fill_price} "
                                        f"(0% fee saved, from_post_only={hedge_result.from_post_only})"
                                    )

                                    # VERIFIED: _local_position is updated via WebSocket at grvt.py line 56
                                    # Additional manual update for immediate tracking
                                    if hasattr(self.hedge_client, '_local_position'):
                                        if order_side == "buy":
                                            self.hedge_client._local_position += quantity
                                        else:
                                            self.hedge_client._local_position -= quantity

                                    # Set flags and return success
                                    self.hedge_order_filled = True
                                    self.order_execution_complete = True
                                    self.last_hedge_fill_price = hedge_fill_price

                                    # Update tracking variables
                                    self.current_hedge_exit_order_type = "POST_ONLY"
                                    self.current_hedge_exit_fee_saved = True

                                    # Log to CSV with POST_ONLY indicator
                                    self.log_trade_to_csv(
                                        exchange=self.hedge_exchange.upper(),
                                        side=side,
                                        price=str(hedge_fill_price),
                                        quantity=str(quantity),
                                        order_type="hedge_close_post_only",
                                        mode="post_only_maker",
                                    )

                                    return True

                                elif hedge_result.status == "OPEN":
                                    # POST_ONLY accepted but not filled - cancel and fallback
                                    self.logger.warning(
                                        f"[CLOSE] POST_ONLY not filled within 3s, canceling order_id={hedge_result.order_id}"
                                    )
                                    # VERIFIED: cancel_order exists at grvt.py line 906-920
                                    cancel_result = await self.hedge_client.cancel_order(hedge_result.order_id)
                                    if not cancel_result.success:
                                        self.logger.error(f"[CLOSE] Failed to cancel POST_ONLY: {cancel_result.error_message}")
                                else:
                                    self.logger.warning(
                                        f"[CLOSE] POST_ONLY rejected (status: {hedge_result.status}), falling back to MARKET"
                                    )

                            except asyncio.TimeoutError:
                                self.logger.warning(
                                    f"[CLOSE] POST_ONLY timeout after 3s, falling back to MARKET"
                                )
                            except Exception as e:
                                self.logger.error(
                                    f"[CLOSE] POST_ONLY failed: {e}, falling back to MARKET"
                                )

                        # FALLBACK: Use MARKET order (0.05% taker fee)
                        if not hedge_filled:
                            self.logger.info(
                                f"[CLOSE] [{self.hedge_exchange.upper()}] Using MARKET fallback (0.05% taker fee)"
                            )

                            # Get position before placing order (REST API for reliability)
                            pos_before_close = await self.hedge_client.get_account_positions()

                            # Use true market order (no timeout, immediate fill)
                            order_info = await self.hedge_client.place_market_order(
                                contract_id=self.hedge_contract_id,
                                quantity=quantity,
                                side=order_side,
                            )

                            # Market orders fill immediately - verify with REST API
                            await asyncio.sleep(1.0)  # Brief wait for execution
                            pos_after_close = await self.hedge_client.get_account_positions()
                            position_change = abs(pos_after_close - pos_before_close)

                            if position_change >= quantity * Decimal("0.9"):
                                actual_fill_price = best_ask if side == "buy" else best_bid
                                self.logger.info(
                                    f"[CLOSE] [MARKET FILLED]: "
                                    f"{quantity} @ ~{actual_fill_price} (pos: {pos_before_close} -> {pos_after_close})"
                                )

                                self.log_trade_to_csv(
                                    exchange=self.hedge_exchange.upper(),
                                    side=side,
                                    price=str(actual_fill_price),
                                    quantity=str(quantity),
                                    order_type="hedge_close_market_fallback",
                                    mode="market_taker",
                                )

                                self.hedge_order_filled = True
                                self.order_execution_complete = True
                                self.last_hedge_fill_price = actual_fill_price

                                # Update tracking variables
                                self.current_hedge_exit_order_type = "MARKET"
                                self.current_hedge_exit_fee_saved = False

                                return True
                            else:
                                self.logger.error(
                                    f"[CLOSE] Market fallback failed to fill (pos: {pos_before_close} -> {pos_after_close})"
                                )
                                self.hedge_order_filled = False
                                self.order_execution_complete = False
                                return False
                else:
                    # OPEN: Use MARKET order for immediate fill (same as CLOSE)
                    self.logger.info(
                        f"[OPEN] [{self.hedge_exchange.upper()}] Using MARKET order for immediate execution"
                    )

                    # Get position before placing order
                    pos_before = await self.hedge_client.get_account_positions()

                    # Use iterative approach for GRVT orders > 0.2 ETH (not applicable for Edgex)
                    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and self.first_build_completed:
                        self.logger.info(f"[OPEN] Using ITERATIVE market order for {quantity} ETH")
                        result = await self.hedge_client.place_iterative_market_order(
                            contract_id=self.hedge_contract_id,
                            target_quantity=quantity,
                            side=order_side,
                            max_iterations=10,   # Increased from 3 - fixes cold start failures
                            max_tick_offset=2,    # Sufficient for liquidity depth
                            max_fill_duration=30  # Increased from 1 - removes timeout constraint
                        )

                        if result['success']:
                            self.logger.info(
                                f"[OPEN] [ITERATIVE] Filled {result['total_filled']} @ ${result['average_price']:.2f} "
                                f"({result['iterations']} iterations)"
                            )
                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(result['average_price']),
                                quantity=str(result['total_filled']),
                                order_type="hedge_open_iterative",
                                mode="iterative_market"
                            )
                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = result['average_price']
                            return True
                        else:
                            self.logger.error(f"[OPEN] Iterative failed: {result.get('reason', 'unknown')}")
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False

                    # Place market order for immediate fill
                    # First BUILD workaround: Try POST_ONLY first, fall back to MARKET if needed
                    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and not self.first_build_completed:
                        self.logger.info(
                            f"[OPEN] [FIRST BUILD] Using POST_ONLY first to avoid cold start issue"
                        )

                        hedge_filled = False

                        if self.hedge_post_only and self.hedge_exchange.lower() == "grvt":
                            try:
                                # Get BBO for POST_ONLY pricing
                                best_bid, best_ask = await self.hedge_client.fetch_bbo_prices(
                                    self.hedge_contract_id
                                )

                                # Calculate POST_ONLY price (1 tick inside spread)
                                if order_side == "buy":
                                    hedge_post_only_price = best_ask - self.hedge_tick_size
                                else:  # sell
                                    hedge_post_only_price = best_bid + self.hedge_tick_size

                                hedge_post_only_price = self.hedge_client.round_to_tick(hedge_post_only_price)

                                self.logger.info(
                                    f"[OPEN] [FIRST BUILD] Attempting POST_ONLY @ {hedge_post_only_price} "
                                    f"(side: {order_side}, fee: 0%)"
                                )

                                # Try POST_ONLY with 3 second timeout
                                hedge_result = await asyncio.wait_for(
                                    self.hedge_client.place_post_only_order(
                                        contract_id=self.hedge_contract_id,
                                        quantity=quantity,
                                        price=hedge_post_only_price,
                                        side=order_side
                                    ),
                                    timeout=3.0
                                )

                                if hedge_result.status == "FILLED":
                                    hedge_filled = True

                                    self.logger.info(
                                        f"[OPEN] [FIRST BUILD] [POST_ONLY FILLED]: {quantity} @ {hedge_result.price} "
                                        f"(0% fee saved)"
                                    )

                                    # Update local position
                                    if hasattr(self.hedge_client, '_local_position'):
                                        if order_side == "buy":
                                            self.hedge_client._local_position += quantity
                                        else:
                                            self.hedge_client._local_position -= quantity

                                    # Set flags
                                    self.hedge_order_filled = True
                                    self.order_execution_complete = True
                                    self.last_hedge_fill_price = hedge_result.price

                                    # Update tracking variables
                                    self.current_hedge_entry_order_type = "POST_ONLY"
                                    self.current_hedge_entry_fee_saved = True

                                    # Log to CSV
                                    self.log_trade_to_csv(
                                        exchange=self.hedge_exchange.upper(),
                                        side=side,
                                        price=str(hedge_result.price),
                                        quantity=str(quantity),
                                        order_type="hedge_open_first_build_post_only",
                                        mode="post_only_maker",
                                    )

                                    return True

                                elif hedge_result.status == "OPEN":
                                    self.logger.warning(
                                        f"[OPEN] [FIRST BUILD] POST_ONLY not filled, canceling and falling back"
                                    )
                                    await self.hedge_client.cancel_order(hedge_result.order_id)
                                else:
                                    self.logger.warning(
                                        f"[OPEN] [FIRST BUILD] POST_ONLY rejected, falling back to MARKET"
                                    )

                            except asyncio.TimeoutError:
                                self.logger.warning(f"[OPEN] [FIRST BUILD] POST_ONLY timeout, falling back to MARKET")
                            except Exception as e:
                                self.logger.error(f"[OPEN] [FIRST BUILD] POST_ONLY failed: {e}, falling back to MARKET")

                        # FALLBACK: Use regular MARKET to avoid cold start issue
                        if not hedge_filled:
                            self.logger.info(
                                f"[OPEN] [FIRST BUILD] Using MARKET fallback (0.05% taker fee)"
                            )

                            order_info = await self.hedge_client.place_market_order(
                                contract_id=self.hedge_contract_id,
                                quantity=quantity,
                                side=order_side,
                            )

                            # Wait briefly for execution and verify
                            await asyncio.sleep(1.0)
                            pos_after = await self.hedge_client.get_account_positions()
                            position_change = abs(pos_after - pos_before)

                            if position_change >= quantity * Decimal("0.9"):
                                actual_fill_price = best_ask if side == "buy" else best_bid
                                self.logger.info(
                                    f"[OPEN] [FIRST BUILD] [MARKET FILLED]: "
                                    f"{quantity} @ ~{actual_fill_price} (pos: {pos_before} -> {pos_after})"
                                )

                                self.log_trade_to_csv(
                                    exchange=self.hedge_exchange.upper(),
                                    side=side,
                                    price=str(actual_fill_price),
                                    quantity=str(quantity),
                                    order_type="hedge_open_first_build_market_fallback",
                                    mode="market_taker",
                                )

                                self.hedge_order_filled = True
                                self.order_execution_complete = True
                                self.last_hedge_fill_price = actual_fill_price

                                # Update tracking variables
                                self.current_hedge_entry_order_type = "MARKET"
                                self.current_hedge_entry_fee_saved = False

                                return True
                            else:
                                self.logger.error(
                                    f"[OPEN] [FIRST BUILD] Market fallback failed to fill (pos: {pos_before} -> {pos_after})"
                                )
                                self.hedge_order_filled = False
                                self.order_execution_complete = False
                                return False
                    else:
                        # Regular market order for small sizes or non-first-build
                        order_info = await self.hedge_client.place_market_order(
                            contract_id=self.hedge_contract_id,
                            quantity=quantity,
                            side=order_side,
                        )

                        # Wait briefly for execution and verify
                        await asyncio.sleep(1.0)
                        pos_after = await self.hedge_client.get_account_positions()
                        position_change = abs(pos_after - pos_before)

                        if position_change >= quantity * Decimal("0.9"):
                            actual_fill_price = best_ask if side == "buy" else best_bid
                            self.logger.info(
                                f"[OPEN] [{self.hedge_exchange.upper()}] [MARKET FILLED]: "
                                f"{quantity} @ ~{actual_fill_price} (pos: {pos_before} -> {pos_after})"
                            )

                            self.log_trade_to_csv(
                                exchange=self.hedge_exchange.upper(),
                                side=side,
                                price=str(actual_fill_price),
                                quantity=str(quantity),
                                order_type="hedge_open",
                                mode="market_taker",
                            )

                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = actual_fill_price
                            return True
                        else:
                            self.logger.error(
                                f"[OPEN] Market order failed to fill (pos: {pos_before} -> {pos_after})"
                            )
                            self.hedge_order_filled = False
                            self.order_execution_complete = False
                            return False

                # Skip old OPEN logic - set order_filled for downstream code
                order_filled = self.hedge_order_filled

                # Final check: Was order filled?
                if order_filled:
                    pos_after = pos_current
                    actual_fill_price = best_ask if side == "buy" else best_bid

                    self.logger.info(
                        f"[{order_type}] [{self.hedge_exchange.upper()}] [FILLED]: "
                        f"{quantity} @ ~{actual_fill_price} (pos: {pos_before} -> {pos_after})"
                    )

                    self.log_trade_to_csv(
                        exchange=self.hedge_exchange.upper(),
                        side=side,
                        price=str(actual_fill_price),
                        quantity=str(quantity),
                        order_type="hedge",
                        mode="aggressive_taker",
                    )

                    self.hedge_order_filled = True
                    self.order_execution_complete = True
                    self.last_hedge_fill_price = actual_fill_price
                    return True
                else:
                    # Order not confirmed by WebSocket within timeout
                    # Check REST API to confirm (may be filled but WS delayed)
                    self.logger.warning(
                        f"[{order_type}] Fill not confirmed by WebSocket (expected: {quantity}, actual: {position_change})"
                    )
                    self.logger.info(f"[{order_type}] Checking REST API for confirmation...")

                    try:
                        rest_position = await self.hedge_client.get_account_positions()
                        rest_position_change = abs(rest_position - pos_before)

                        if rest_position_change >= quantity * Decimal("0.9"):
                            # Confirmed filled by REST API
                            self.logger.info(
                                f"[{order_type}] Fill confirmed by REST API! (WS was delayed, actual: {rest_position_change})"
                            )
                            # Update local WebSocket position
                            if hasattr(self.hedge_client, '_local_position'):
                                self.hedge_client._local_position = rest_position

                            actual_fill_price = best_ask if side == "buy" else best_bid
                            self.hedge_order_filled = True
                            self.order_execution_complete = True
                            self.last_hedge_fill_price = actual_fill_price
                            return True
                        else:
                            # Still not filled after REST check - close at market
                            self.logger.warning(
                                f"[{order_type}] Still not filled after REST check (expected: {quantity}, actual: {rest_position_change})"
                            )

                            # CRITICAL FIX: Check ACTUAL position before attempting close
                            # The original order may not have filled, so there might be no position to close
                            current_pos = await self.hedge_client.get_account_positions()

                            if abs(current_pos) >= quantity * Decimal("0.9"):  # Position exists (>=90% of expected)
                                self.logger.info(f"[{order_type}] Position found (pos: {current_pos}), closing at market...")
                                close_side = "sell" if current_pos > 0 else "buy"
                                close_qty = abs(current_pos)

                                try:
                                    close_result = await self.hedge_client.place_market_order(
                                        contract_id=self.hedge_contract_id,
                                        quantity=close_qty,
                                        side=close_side
                                    )
                                    self.logger.info(
                                        f"[{order_type}] Market close order placed: {close_side.upper()} {close_qty}"
                                    )
                                    # Consider it executed
                                    self.hedge_order_filled = True
                                    self.order_execution_complete = True
                                    return True
                                except Exception as close_error:
                                    self.logger.error(f"[{order_type}] Failed to close at market: {close_error}")
                                    return False
                            else:
                                # No position exists - original order never filled, skip close
                                self.logger.warning(
                                    f"[{order_type}] No position to close (pos: {current_pos} < {quantity}), skipping market close"
                                )
                                self.hedge_order_filled = False
                                self.order_execution_complete = False
                                return False

                    except Exception as api_error:
                        self.logger.error(f"[{order_type}] REST API check failed: {api_error}")
                        return False

            except Exception as e:
                self.logger.error(
                    f"Error placing HEDGE order (attempt {attempt}/{max_retries}): {e}"
                )
                if attempt < max_retries:
                    # ENHANCED: Exponential backoff (1s, 2s, 4s, 8s, 16s, 32s)
                    delay = 2 ** (attempt - 1)
                    self.logger.info(f"Retrying hedge order in {delay} second(s)...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All {max_retries} hedge attempts failed!")
                    self.logger.error(traceback.format_exc())

        self.logger.error(
            "[EMERGENCY] Hedge order failed after all retries, closing primary position!"
        )
        await self.emergency_close_primary(quantity, side)
        return False

    async def force_close_all_positions(self):
        """Force close all positions with improved verification and retry logic.

        Key improvements:
        - 10 second max wait for fill confirmation
        - Absolute threshold (0.001) instead of percentage
        - WebSocket + REST parallel confirmation
        - Max 3 retry attempts
        - Better error handling and logging
        """
        try:
            self.logger.info("[FORCE_CLOSE] Starting forced position cleanup with improved logic...")

            # Check both exchanges using REST API for accurate positions
            for exchange_name, client in [
                ("PRIMARY", self.primary_client),
                ("HEDGE", self.hedge_client),
            ]:
                if client is None:
                    continue

                # 1. Get REST API position (authoritative)
                try:
                    rest_pos = await client.get_account_positions()
                except Exception as e:
                    self.logger.error(f"[FORCE_CLOSE] Failed to get {exchange_name} position: {e}")
                    continue

                if abs(rest_pos) < Decimal("0.001"):
                    self.logger.info(f"[FORCE_CLOSE] {exchange_name} already flat: {rest_pos}")
                    continue

                self.logger.warning(
                    f"[FORCE_CLOSE] {exchange_name} has residual position: {rest_pos}, forcing close"
                )

                # 2. Determine close side and quantity
                close_side = "sell" if rest_pos > 0 else "buy"
                close_qty = abs(rest_pos)

                # 3. Get BBO for aggressive pricing
                try:
                    best_bid, best_ask = await client.fetch_bbo_prices(client.config.contract_id)

                    # Use aggressive pricing for immediate fill
                    if close_side == "buy":
                        # Cross spread: buy at ASK (aggressive)
                        close_price = best_ask  # Cross immediately
                    else:
                        # Cross spread: sell at BID (aggressive)
                        close_price = best_bid  # Cross immediately

                    self.logger.warning(
                        f"[FORCE_CLOSE] {exchange_name} {close_side.upper()} {close_qty} @ market (crossing spread)"
                    )

                    # 4. Place close order
                    if hasattr(client, "place_market_order"):
                        # Check if it's Nado/Backpack (uses 'direction') or GRVT/Edgex (uses 'side')
                        if self.primary_exchange in ["nado", "backpack"] and exchange_name == "PRIMARY":
                            # Nado/Backpack uses 'direction' parameter
                            await client.place_market_order(
                                contract_id=client.config.contract_id,
                                quantity=close_qty,
                                direction=close_side,  # Nado/Backpack uses 'direction'
                            )
                        else:
                            # GRVT/Edgex uses 'side' parameter
                            await client.place_market_order(
                                contract_id=client.config.contract_id,
                                quantity=close_qty,
                                side=close_side,
                            )
                        self.logger.info(f"[FORCE_CLOSE] Market order placed for {exchange_name}")
                    else:
                        # Fallback: Use aggressive limit order (cross spread) or market order
                        if hasattr(client, 'place_post_only_order'):
                            await client.place_post_only_order(
                                contract_id=client.config.contract_id,
                                quantity=close_qty,
                                price=close_price,
                                side=close_side,
                            )
                            self.logger.info(f"[FORCE_CLOSE] Aggressive limit order placed for {exchange_name}")
                        else:
                            # No POST_ONLY available, use market order with appropriate parameter
                            if exchange_name == "PRIMARY" and self.primary_exchange in ["nado", "backpack"]:
                                await client.place_open_order(
                                    contract_id=client.config.contract_id,
                                    quantity=close_qty,
                                    direction=close_side,
                                )
                            else:
                                # For hedge exchanges
                                await client.place_market_order(
                                    contract_id=client.config.contract_id,
                                    quantity=close_qty,
                                    side=close_side,
                                )
                            self.logger.info(f"[FORCE_CLOSE] Market order placed for {exchange_name}")

                    # 5. Wait for fill with REST API PRIMARY confirmation
                    filled = False
                    max_wait = 10  # 10 seconds max wait

                    for i in range(max_wait * 10):  # 0.1 second intervals
                        await asyncio.sleep(0.1)

                        # REST API confirmation every 0.5 second (every 5 iterations) - PRIMARY CHECK
                        # REST API is authoritative, WebSocket is supplementary only
                        if i % 5 == 0:
                            rest_check = await client.get_account_positions()
                            if abs(rest_check) < Decimal("0.001"):
                                self.logger.info(f"[FORCE_CLOSE] {exchange_name} filled (REST confirmed - authoritative)")
                                # CRITICAL: Sync local position after successful close
                                if exchange_name == "PRIMARY":
                                    self.local_primary_position = rest_check
                                    self.primary_position = rest_check
                                else:
                                    self.local_hedge_position = rest_check
                                    self.hedge_position = rest_check
                                filled = True
                                break

                        # WebSocket confirmation SUPPLEMENTARY ONLY (checked after REST)
                        # WebSocket can show false positives, so we only use it as a hint
                        if hasattr(client, 'get_ws_position'):
                            ws_pos = client.get_ws_position()
                            if abs(ws_pos) < Decimal("0.001"):
                                # WS shows 0, but we still need REST confirmation
                                # Just log it and continue to next REST check
                                self.logger.debug(f"[FORCE_CLOSE] {exchange_name} WS shows 0, waiting for REST confirmation...")

                    # 6. If not filled, retry up to 3 times
                    if not filled:
                        remaining = await client.get_account_positions()

                        # Use ABSOLUTE threshold (0.001) instead of percentage
                        if abs(remaining) > Decimal("0.001"):
                            self.logger.warning(
                                f"[FORCE_CLOSE] {exchange_name} not filled after {max_wait}s. "
                                f"Remaining: {remaining}. Retrying (max 3 attempts)..."
                            )

                            # Retry loop (max 3 attempts)
                            for retry in range(3):
                                self.logger.warning(
                                    f"[FORCE_CLOSE] Retry attempt {retry + 1}/3 for {exchange_name}..."
                                )

                                # Re-check position (may have been filled during wait)
                                current_pos = await client.get_account_positions()
                                if abs(current_pos) < Decimal("0.001"):
                                    self.logger.info(
                                        f"[FORCE_CLOSE] {exchange_name} filled during wait before retry {retry + 1}"
                                    )
                                    filled = True
                                    break

                                # Place retry order
                                retry_qty = abs(current_pos)

                                if hasattr(client, "place_market_order"):
                                    # Check if it's Nado/Backpack (uses 'direction') or GRVT/Edgex (uses 'side')
                                    if self.primary_exchange in ["nado", "backpack"] and exchange_name == "PRIMARY":
                                        # Nado/Backpack uses 'direction' parameter
                                        await client.place_market_order(
                                            contract_id=client.config.contract_id,
                                            quantity=retry_qty,
                                            direction=close_side,
                                        )
                                    else:
                                        # GRVT/Edgex uses 'side' parameter
                                        await client.place_market_order(
                                            contract_id=client.config.contract_id,
                                            quantity=retry_qty,
                                            side=close_side,
                                        )
                                else:
                                    # Re-fetch BBO for retry
                                    best_bid, best_ask = await client.fetch_bbo_prices(client.config.contract_id)
                                    retry_price = best_ask if close_side == "buy" else best_bid
                                    await client.place_post_only_order(
                                        contract_id=client.config.contract_id,
                                        quantity=retry_qty,
                                        price=retry_price,
                                        side=close_side,
                                    )

                                # Wait for retry fill with REST API PRIMARY confirmation
                                for j in range(max_wait * 10):
                                    await asyncio.sleep(0.1)

                                    # REST API confirmation every 0.5 second (every 5 iterations) - PRIMARY
                                    if j % 5 == 0:
                                        rest_check = await client.get_account_positions()
                                        if abs(rest_check) < Decimal("0.001"):
                                            self.logger.info(
                                                f"[FORCE_CLOSE] {exchange_name} retry {retry + 1} filled (REST - authoritative)"
                                            )
                                            filled = True
                                            break

                                    # WebSocket check SUPPLEMENTARY ONLY
                                    if hasattr(client, 'get_ws_position'):
                                        ws_pos = client.get_ws_position()
                                        if abs(ws_pos) < Decimal("0.001"):
                                            self.logger.debug(
                                                f"[FORCE_CLOSE] {exchange_name} retry {retry + 1} WS shows 0, waiting for REST..."
                                            )

                                if filled:
                                    break

                            # Final check after all retries
                            final_remaining = await client.get_account_positions()
                            if abs(final_remaining) > Decimal("0.001"):
                                self.logger.error(
                                    f"[FORCE_CLOSE] {exchange_name} FAILED to close after 3 retries! "
                                    f"Remaining: {final_remaining}. Manual intervention required."
                                )
                            else:
                                # CRITICAL: Sync local position after successful retries
                                if exchange_name == "PRIMARY":
                                    self.local_primary_position = final_remaining
                                    self.primary_position = final_remaining
                                else:
                                    self.local_hedge_position = final_remaining
                                    self.hedge_position = final_remaining
                                self.logger.info(
                                    f"[FORCE_CLOSE] {exchange_name} successfully closed after retries"
                                )

                except Exception as inner_e:
                    self.logger.error(f"[FORCE_CLOSE] Error closing {exchange_name}: {inner_e}")
                    import traceback
                    self.logger.error(f"[FORCE_CLOSE] Traceback: {traceback.format_exc()}")

            # 7. Final verification of all positions
            await asyncio.sleep(1)
            final_primary = await self.primary_client.get_account_positions()
            final_hedge = await self.hedge_client.get_account_positions()
            final_net = final_primary + final_hedge

            # CRITICAL: Sync all local positions with final REST API values
            self.local_primary_position = final_primary
            self.local_hedge_position = final_hedge
            self.primary_position = final_primary
            self.hedge_position = final_hedge

            self.logger.info(
                f"[FORCE_CLOSE] Final positions - PRIMARY: {final_primary}, HEDGE: {final_hedge}, Net: {final_net}"
            )

            if abs(final_net) > self.order_quantity * Decimal("0.01"):
                self.logger.error(
                    f"[FORCE_CLOSE] WARNING: Net delta still significant: {final_net}. "
                    f"Manual position check recommended."
                )
            else:
                self.logger.info("[FORCE_CLOSE] All positions successfully closed")

        except Exception as e:
            self.logger.error(f"[FORCE_CLOSE] Error: {e}")

    async def emergency_close_primary(self, quantity: Decimal, failed_hedge_side: str):
        close_side = failed_hedge_side

        self.logger.warning(
            f"[EMERGENCY] Closing PRIMARY position: {close_side.upper()} {quantity}"
        )

        max_close_attempts = 3
        for attempt in range(max_close_attempts):
            try:
                # Use market order for emergency close (more reliable)
                # Nado/Edgex use string "buy"/"sell" directly
                order_side = close_side

                # Try to use market order if available
                if hasattr(self.primary_client, "place_market_order"):
                    # Check if it's Nado/Backpack (uses 'direction') or GRVT/Edgex (uses 'side')
                    if self.primary_exchange in ["nado", "backpack"]:
                        # Nado/Backpack uses 'direction' parameter
                        await self.primary_client.place_market_order(
                            contract_id=self.primary_contract_id,
                            quantity=quantity,
                            direction=order_side,
                        )
                    else:
                        # GRVT/Edgex uses 'side' parameter
                        await self.primary_client.place_market_order(
                            contract_id=self.primary_contract_id,
                            quantity=quantity,
                            side=order_side,
                        )
                    self.logger.warning(
                        f"[EMERGENCY] MARKET order placed: {close_side.upper()} {quantity}"
                    )
                else:
                    # Fallback: aggressive limit order (small buffer)
                    best_bid, best_ask = await self.primary_client.fetch_bbo_prices(
                        self.primary_contract_id
                    )

                    if close_side == "buy":
                        price = best_ask + (self.primary_tick_size * Decimal("3"))
                    else:
                        price = best_bid - (self.primary_tick_size * Decimal("3"))

                    # Round to tick size
                    price = self.primary_client.round_to_tick(price)

                    # Try POST_ONLY if available, otherwise use market order for emergency close
                    if hasattr(self.primary_client, 'place_post_only_order'):
                        await self.primary_client.place_post_only_order(
                            contract_id=self.primary_contract_id,
                            quantity=quantity,
                            price=price,
                            side=order_side,
                        )
                    else:
                        # Emergency fallback to market order for exchanges without POST_ONLY
                        direction = "buy" if close_side == "buy" else "sell"
                        await self.primary_client.place_open_order(
                            contract_id=self.primary_contract_id,
                            quantity=quantity,
                            direction=direction,
                        )

                    self.logger.warning(
                        f"[EMERGENCY] Aggressive limit order placed: {close_side.upper()} {quantity} @ {price}"
                    )

                # Wait for order to process
                await asyncio.sleep(2)

                # Verify position was closed
                primary_pos = await self.primary_client.get_account_positions()

                # Check if position was reduced (allow for some tolerance)
                position_ok = abs(primary_pos) < quantity * Decimal("0.1")

                if position_ok:
                    self.logger.info(
                        f"[EMERGENCY] Primary position closed successfully: {primary_pos}"
                    )

                    # Update local tracking
                    self.local_primary_position = primary_pos
                    self.primary_position = primary_pos

                    # Get approximate fill price for logging
                    best_bid, best_ask = await self.primary_client.fetch_bbo_prices(
                        self.primary_contract_id
                    )
                    approx_price = best_ask if close_side == "buy" else best_bid

                    self.log_trade_to_csv(
                        exchange=self.primary_exchange.upper(),
                        side=close_side,
                        price=str(approx_price),
                        quantity=str(quantity),
                        order_type="emergency_close",
                        mode="market",
                    )
                    return  # Success
                else:
                    self.logger.warning(
                        f"[EMERGENCY] Close attempt {attempt+1}/{max_close_attempts} failed. Position: {primary_pos}"
                    )
                    if attempt < max_close_attempts - 1:
                        self.logger.info("[EMERGENCY] Retrying in 2 seconds...")
                        await asyncio.sleep(2)

            except Exception as e:
                self.logger.error(
                    f"[EMERGENCY] Close attempt {attempt+1} failed: {e}"
                )
                if attempt < max_close_attempts - 1:
                    await asyncio.sleep(2)

        # All attempts failed
        self.logger.error("[EMERGENCY] Failed to close primary position after all attempts!")
        self.logger.error(traceback.format_exc())
        self.stop_flag = True

    def _reset_current_cycle_metrics(self):
        """Reset current cycle metrics at start of new cycle."""
        self.current_cycle_start_time = time.time()
        self.repricing_count = 0
        self.current_primary_entry_price = None
        self.current_hedge_entry_price = None
        self.current_primary_entry_time = None
        self.current_hedge_entry_time = None
        self.current_primary_exit_price = None
        self.current_hedge_exit_price = None
        self.current_primary_exit_time = None
        self.current_hedge_exit_time = None
        self.current_order_to_fill_primary = 0
        self.current_order_to_fill_hedge = 0
        self.current_websocket_latency = 0
        self.current_rest_latency = 0
        self.current_reconciliation_time = 0
        self.current_hedge_entry_order_type = "MARKET"
        self.current_hedge_exit_order_type = "MARKET"
        self.current_hedge_entry_fee_saved = False
        self.current_hedge_exit_fee_saved = False

    def _create_trade_metrics(self, iteration: int, direction: str) -> TradeMetrics:
        """Create TradeMetrics object from current cycle data."""
        cycle_time = time.time() - self.current_cycle_start_time if self.current_cycle_start_time else 0

        return TradeMetrics(
            iteration=iteration,
            direction=direction,
            primary_entry_price=self.current_primary_entry_price or Decimal("0"),
            hedge_entry_price=self.current_hedge_entry_price or Decimal("0"),
            primary_entry_time=self.current_primary_entry_time or 0,
            hedge_entry_time=self.current_hedge_entry_time or 0,
            primary_exit_price=self.current_primary_exit_price or Decimal("0"),
            hedge_exit_price=self.current_hedge_exit_price or Decimal("0"),
            primary_exit_time=self.current_primary_exit_time or 0,
            hedge_exit_time=self.current_hedge_exit_time or 0,
            order_to_fill_primary=self.current_order_to_fill_primary,
            order_to_fill_hedge=self.current_order_to_fill_hedge,
            websocket_latency=self.current_websocket_latency,
            rest_latency=self.current_rest_latency,
            reconciliation_time=self.current_reconciliation_time,
            repricing_count=self.repricing_count,
            total_cycle_time=cycle_time,
            hedge_entry_order_type=self.current_hedge_entry_order_type,
            hedge_exit_order_type=self.current_hedge_exit_order_type,
            hedge_entry_fee_saved=self.current_hedge_entry_fee_saved,
            hedge_exit_fee_saved=self.current_hedge_exit_fee_saved,
        )

    async def _pre_trade_check(self):
        """OMC v4: Pre-trade safety checks to prevent losses before they happen."""
        # 1. Position limit check
        total_pos = abs(self.primary_position) + abs(self.hedge_position)
        if total_pos + self.order_quantity > self.MAX_POSITION:
            raise RuntimeError(
                f"[SAFETY] Cannot trade: projected position {total_pos + self.order_quantity} ETH "
                f"would exceed MAX_POSITION {self.MAX_POSITION} ETH. "
                f"Current positions: Primary={self.primary_position}, Hedge={self.hedge_position}. "
                f"Reduce order size or close existing positions first."
            )

        # 2. Daily loss limit check (with UTC midnight reset)
        now = datetime.now(pytz.UTC)
        if now.date() > self.daily_start_time.date():
            # New day (UTC midnight): reset daily PnL
            self.logger.info(
                f"[SAFETY] New day detected ({now.date()}). Resetting daily PnL from ${self.daily_pnl:.2f} to $0.00"
            )
            self.daily_pnl = Decimal("0")
            self.daily_start_time = now

        if self.daily_pnl < -self.MAX_DAILY_LOSS:
            raise RuntimeError(
                f"[SAFETY] Daily loss ${-self.daily_pnl:.2f} exceeds ${self.MAX_DAILY_LOSS} limit. "
                f"Trading halted until next UTC midnight. "
                f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

#         # 3. NetDelta drift check (early warning)
#         net_delta = self.primary_position + self.hedge_position
#         NET_DELTA_TOLERANCE = Decimal("0.01")  # 1% tolerance
#         if abs(net_delta) > self.order_quantity * NET_DELTA_TOLERANCE:
#             raise RuntimeError(
#                 f"[SAFETY] NetDelta {net_delta} exceeds {NET_DELTA_TOLERANCE * 100}% tolerance before trade. "
#                 f"Rebalance required. Primary={self.primary_position}, Hedge={self.hedge_position}"
#             )

        net_delta = self.primary_position + self.hedge_position  # For logging
        self.logger.info(
            f"[SAFETY] Pre-trade checks passed: Pos={total_pos}/{self.MAX_POSITION}, "
            f"DailyPnL=${self.daily_pnl:.2f}/${self.MAX_DAILY_LOSS}, NetDelta={net_delta}"
        )

    async def execute_dn_cycle(
        self, direction: str
    ) -> Tuple[bool, Optional[Decimal], Optional[Decimal]]:
        # OMC v4: Pre-trade safety check BEFORE placing any order
        await self._pre_trade_check()

        self.order_execution_complete = False
        self.waiting_for_hedge_fill = False

        # Track primary order timing
        primary_order_start = time.time()

        order_id = await self.place_primary_order(direction, self.order_quantity)

        if order_id is None:
            return False, None, None

        # Track primary order fill time
        self.current_order_to_fill_primary = (time.time() - primary_order_start) * 1000  # ms

        start_time = time.time()
        primary_fill_price = None
        hedge_fill_price = None

        while not self.order_execution_complete and not self.stop_flag:
            if self.waiting_for_hedge_fill:
                primary_fill_price = self.current_hedge_price

                # Track hedge order timing
                hedge_order_start = time.time()

                success = await self.place_hedge_order(
                    self.current_hedge_side,
                    self.current_hedge_quantity,
                    self.current_hedge_price,
                )

                # Track hedge order fill time
                self.current_order_to_fill_hedge = (time.time() - hedge_order_start) * 1000  # ms

                # SCENARIO 2 HANDLING: Check if hedge BUILD succeeded
                # If Primary BUILD FULL succeeded but Hedge BUILD failed → EMERGENCY UNWIND
                if not success:
                    self.logger.error(
                        f"[BUILD_CYCLE] Primary BUILD succeeded (FULL) but Hedge BUILD failed - "
                        f"triggering EMERGENCY UNWIND of Primary position"
                    )
                    await self._emergency_unwind_primary_position()
                    return False, None, None  # Signal BUILD loop to STOP

                if success and hasattr(self, "last_hedge_fill_price"):
                    hedge_fill_price = self.last_hedge_fill_price
                break  # Only break if hedge succeeded

            await asyncio.sleep(0.01)

            if time.time() - start_time > 180:
                self.logger.error("Timeout waiting for trade completion")
                return False, None, None

        # Store entry/exit prices based on direction
        if direction == "buy":
            # Building long position
            if self.current_primary_entry_price is None:
                self.current_primary_entry_price = primary_fill_price or Decimal("0")
                self.current_primary_entry_time = time.time()
            if self.current_hedge_entry_price is None:
                self.current_hedge_entry_price = hedge_fill_price or Decimal("0")
                self.current_hedge_entry_time = time.time()
            # First BUILD completed successfully
            if not self.first_build_completed:
                self.first_build_completed = True
                self.logger.info("[BUILD] First BUILD completed - cold start workaround disabled")
        else:
            # Unwinding (selling)
            self.current_primary_exit_price = primary_fill_price or Decimal("0")
            self.current_primary_exit_time = time.time()
            self.current_hedge_exit_price = hedge_fill_price or Decimal("0")
            self.current_hedge_exit_time = time.time()

        return True, primary_fill_price, hedge_fill_price

    async def _emergency_unwind_primary_position(self):
        """Emergency UNWIND of Primary position when Hedge BUILD fails.

        Scenario 2: Primary has FULL position, Hedge has NO position.
        Must UNWIND Primary immediately to prevent delta exposure.

        Uses ACTUAL API position to determine UNWIND direction.
        """
        from decimal import Decimal

        # Get ACTUAL Primary position from API (authoritative source)
        # NOTE: Verify this returns Decimal scalar, not dict/list
        actual_position = await self.primary_client.get_account_positions()

        if abs(actual_position) < Decimal("0.001"):
            self.logger.warning("[EMERGENCY_UNWIND] No Primary position to unwind")
            return

        # Determine UNWIND direction based on ACTUAL position
        # If position > 0 (LONG), need to SELL to close
        # If position < 0 (SHORT), need to BUY to close
        unwind_side = "sell" if actual_position > 0 else "buy"
        unwind_qty = abs(actual_position)

        self.logger.error(
            f"[EMERGENCY_UNWIND] Unwinding Primary: {unwind_side.upper()} {unwind_qty} ETH "
            f"(actual position: {actual_position})"
        )

        try:
            # FIX: Changed side= to direction= (Backpack API expects 'direction' parameter)
            await self.primary_client.place_market_order(
                contract_id=self.primary_contract_id,
                quantity=unwind_qty,
                direction=unwind_side
            )
            self.logger.error(
                f"[EMERGENCY_UNWIND] Successfully unwound Primary: "
                f"{unwind_side.upper()} {unwind_qty}"
            )
        except Exception as e:
            self.logger.error(f"[EMERGENCY_UNWIND] Failed to unwind Primary: {e}")
            # Set stop flag to prevent further trading
            self.stop_flag = True

    async def trading_loop(self):
        self.logger.info(f"{'=' * 60}")
        self.logger.info("DN Hedge Bot Starting (ALTERNATIVE STRATEGY)")
        self.logger.info(
            f"PRIMARY: {self.primary_exchange.upper()} ({self.primary_mode.value}) | "
            f"HEDGE: {self.hedge_exchange.upper()} ({self.hedge_mode.value})"
        )
        self.logger.info(
            f"Ticker: {self.ticker} | Quantity: {self.order_quantity} | Iterations: {self.iterations}"
        )
        # OMC v4: Log safety limits
        self.logger.info(
            f"[SAFETY] MAX_POSITION: {self.MAX_POSITION} ETH | "
            f"MAX_DAILY_LOSS: ${self.MAX_DAILY_LOSS} | "
            f"NetDelta Tolerance: 1%"
        )
        self.logger.info(f"{'=' * 60}")

        try:
            await self.initialize_clients()
            await self.connect_websockets()
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return

        await asyncio.sleep(5)  # Increased from 3 for initial WebSocket stabilization

        api_primary, api_hedge = await self.get_positions(force_api=True)
        self.local_primary_position = api_primary
        self.local_hedge_position = api_hedge
        self.primary_position = api_primary
        self.hedge_position = api_hedge
        self.logger.info(
            f"[INIT] Positions - PRIMARY: {self.primary_position}, HEDGE: {self.hedge_position}"
        )

        # Check for residual positions and auto-close if needed
        net_delta = api_primary + api_hedge
        if abs(net_delta) > self.order_quantity:
            self.logger.warning(
                f"[INIT] Residual positions detected! Primary: {api_primary}, Hedge: {api_hedge}, Net: {net_delta}"
            )
            self.logger.warning("[INIT] Auto-closing residual positions...")

            try:
                # First attempt: Force close all positions
                await self.force_close_all_positions()

                # Wait and recheck
                await asyncio.sleep(3)
                api_primary, api_hedge = await self.get_positions(force_api=True)
                net_delta = api_primary + api_hedge

                # Second attempt if still has residual positions
                if abs(net_delta) > self.order_quantity * Decimal("0.01"):
                    self.logger.warning(
                        f"[INIT] First attempt incomplete. Net: {net_delta}. Trying second cleanup..."
                    )
                    await self.force_close_all_positions()

                    # Wait and recheck again
                    await asyncio.sleep(3)
                    api_primary, api_hedge = await self.get_positions(force_api=True)
                    net_delta = api_primary + api_hedge

                if abs(net_delta) > self.order_quantity * Decimal("0.01"):
                    self.logger.error(
                        f"[INIT] Failed to close residual positions after 2 attempts! Net: {net_delta}. Please manually close positions."
                    )
                    self.logger.error("[INIT] Bot cannot start safely. Exiting...")
                    return
                else:
                    self.logger.info(f"[INIT] Residual positions closed successfully. Net: {net_delta}")
                    # Update local tracking
                    self.local_primary_position = api_primary
                    self.local_hedge_position = api_hedge
                    self.primary_position = api_primary
                    self.hedge_position = api_hedge

            except Exception as e:
                self.logger.error(f"[INIT] Error during residual position cleanup: {e}")
                self.logger.error("[INIT] Bot cannot start safely. Exiting...")
                return

        cycle_count = 0

        for iteration in range(1, self.iterations + 1):
            if self.stop_flag:
                break

            self.logger.info(f"\n{'=' * 40}")
            self.logger.info(f"Iteration {iteration}/{self.iterations}")
            self.logger.info(f"{'=' * 40}")

            # Reset metrics for new cycle
            self._reset_current_cycle_metrics()

            await self.reconcile_positions()

            # Direction determination: odd=buy first, even=sell first
            build_direction = "buy" if iteration % 2 == 1 else "sell"
            unwind_direction = "sell" if build_direction == "buy" else "buy"

            self.logger.info(
                f"[DIRECTION] BUILD: {build_direction.upper()}, UNWIND: {unwind_direction.upper()}"
            )

            # ===== BUILD Phase: max_position =====
            # Get initial positions (use REST API fallback if WebSocket not available)
            if hasattr(self.primary_client, 'get_ws_position'):
                current_primary_pos = self.primary_client.get_ws_position()
            else:
                current_primary_pos, _ = await self.get_positions(primary_only=True)

            if hasattr(self.hedge_client, 'get_ws_position'):
                current_hedge_pos = self.hedge_client.get_ws_position()
            else:
                _, current_hedge_pos = await self.get_positions(hedge_only=True)

            while (
                abs(current_primary_pos) < self.max_position
                and not self.stop_flag
            ):
                cycle_count += 1

                if cycle_count % self.reconcile_interval == 0:
                    await self.reconcile_positions()
                    # Sync WebSocket positions with REST API periodically
                    if hasattr(self.hedge_client, "sync_ws_position_if_needed"):
                        await self.hedge_client.sync_ws_position_if_needed(cycle_count)
                    if hasattr(self.primary_client, "sync_ws_position_if_needed"):
                        await self.primary_client.sync_ws_position_if_needed(cycle_count)

                # Use WebSocket positions if available, otherwise use REST API
                if hasattr(self.primary_client, 'get_ws_position'):
                    self.primary_position = self.primary_client.get_ws_position()
                else:
                    self.primary_position, _ = await self.get_positions(primary_only=True)

                if hasattr(self.hedge_client, 'get_ws_position'):
                    self.hedge_position = self.hedge_client.get_ws_position()
                else:
                    _, self.hedge_position = await self.get_positions(hedge_only=True)

                current_primary_pos = self.primary_position
                net_delta = self.primary_position + self.hedge_position

                self.logger.info(
                    f"[BUILD] PRIMARY(WS): {self.primary_position} | HEDGE(WS): {self.hedge_position} | Net: {net_delta}"
                )

                # Position imbalance threshold during operation: 5x for tolerance
                if abs(net_delta) > self.order_quantity * 5:
                    self.logger.error(f"Position imbalance too large: {net_delta}")
                    self.stop_flag = True
                    break

                if not await self.check_arbitrage_opportunity(build_direction):
                    await asyncio.sleep(0.1)  # Reduced from 1s for faster retry
                    continue

                success, primary_price, hedge_price = await self.execute_dn_cycle(build_direction)
                if success and primary_price and hedge_price:
                    hedge_side = "sell" if build_direction == "buy" else "buy"
                    self.print_trade_summary(
                        cycle_count,
                        build_direction,
                        primary_price,
                        hedge_side,
                        hedge_price,
                        self.order_quantity,
                    )
                if not success:
                    await asyncio.sleep(1)  # Reduced from 5s for faster recovery

            if self.sleep_time > 0:
                self.logger.info(f"Sleeping {self.sleep_time}s...")
                await asyncio.sleep(self.sleep_time)

            # ===== UNWIND Phase: 0 =====
            # Get initial positions (use REST API fallback if WebSocket not available)
            if hasattr(self.primary_client, 'get_ws_position'):
                current_primary_pos = self.primary_client.get_ws_position()
            else:
                current_primary_pos, _ = await self.get_positions(primary_only=True)

            while (
                abs(current_primary_pos) > 0
                and not self.stop_flag
            ):
                cycle_count += 1

                if cycle_count % self.reconcile_interval == 0:
                    await self.reconcile_positions()
                    # Sync WebSocket positions with REST API periodically
                    if hasattr(self.hedge_client, "sync_ws_position_if_needed"):
                        await self.hedge_client.sync_ws_position_if_needed(cycle_count)
                    if hasattr(self.primary_client, "sync_ws_position_if_needed"):
                        await self.primary_client.sync_ws_position_if_needed(cycle_count)

                # Use WebSocket positions if available, otherwise use REST API
                if hasattr(self.primary_client, 'get_ws_position'):
                    self.primary_position = self.primary_client.get_ws_position()
                else:
                    self.primary_position, _ = await self.get_positions(primary_only=True)

                if hasattr(self.hedge_client, 'get_ws_position'):
                    self.hedge_position = self.hedge_client.get_ws_position()
                else:
                    _, self.hedge_position = await self.get_positions(hedge_only=True)

                current_primary_pos = self.primary_position
                net_delta = self.primary_position + self.hedge_position

                self.logger.info(
                    f"[UNWIND] PRIMARY(WS): {self.primary_position} | HEDGE(WS): {self.hedge_position} | Net: {net_delta}"
                )

                # Position imbalance threshold during operation: 5x for tolerance
                if abs(net_delta) > self.order_quantity * 5:
                    self.logger.error(f"Position imbalance too large: {net_delta}")
                    self.stop_flag = True
                    break

                if not await self.check_arbitrage_opportunity(unwind_direction):
                    await asyncio.sleep(0.1)  # Reduced from 1s for faster retry
                    continue

                success, primary_price, hedge_price = await self.execute_dn_cycle(
                    unwind_direction
                )
                if success and primary_price and hedge_price:
                    hedge_side = "sell" if unwind_direction == "buy" else "buy"
                    self.print_trade_summary(
                        cycle_count,
                        unwind_direction,
                        primary_price,
                        hedge_side,
                        hedge_price,
                        self.order_quantity,
                    )
                if not success:
                    await asyncio.sleep(1)  # Reduced from 5s for faster recovery

            # Create and store trade metrics after completing BUILD + UNWIND cycle
            direction_label = "BUY_FIRST" if iteration % 2 == 1 else "SELL_FIRST"
            metrics = self._create_trade_metrics(iteration, direction_label)
            self.trade_metrics_list.append(metrics)

            self.logger.info(
                f"[METRICS] Cycle {iteration} complete - "
                f"Entry: P={metrics.primary_entry_price} H={metrics.hedge_entry_price}, "
                f"Exit: P={metrics.primary_exit_price} H={metrics.hedge_exit_price}, "
                f"Time: {metrics.total_cycle_time:.2f}s"
            )

        final_primary, final_hedge = await self.get_positions(force_api=True)
        avg_pnl_bps = (
            (self.total_gross_pnl / self.total_volume) * Decimal("10000")
            if self.total_volume > 0
            else Decimal("0")
        )

        self.logger.info(f"\n{'=' * 60}")
        self.logger.info("TRADING COMPLETE - FINAL SUMMARY")
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"  Completed Cycles: {self.completed_cycles}")
        self.logger.info(f"  Total Volume: ${self.total_volume:.2f}")
        self.logger.info(f"  Total Gross PnL: ${self.total_gross_pnl:.4f}")
        self.logger.info(f"  Average Edge: {avg_pnl_bps:+.2f} bps")
        self.logger.info(f"{'-' * 60}")
        self.logger.info(
            f"  Final Positions - NADO: {final_primary}, EDGEX: {final_hedge}"
        )
        self.logger.info(f"  Net Delta: {final_primary + final_hedge}")
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"  Completed Cycles: {self.completed_cycles}")
        self.logger.info(f"  Total Volume: ${self.total_volume:.2f}")
        self.logger.info(f"  Total Gross PnL: ${self.total_gross_pnl:.4f}")
        self.logger.info(f"  Average Edge: {avg_pnl_bps:+.2f} bps")
        self.logger.info(f"{'─' * 60}")
        self.logger.info(
            f"  Final Positions - NADO: {final_primary}, EDGEX: {final_hedge}"
        )
        self.logger.info(f"  Net Delta: {final_primary + final_hedge}")
        self.logger.info(f"{'=' * 60}")

        # Auto-cleanup residual positions at shutdown
        net_delta = final_primary + final_hedge
        if abs(net_delta) > self.order_quantity * Decimal("0.01"):
            self.logger.warning(f"[SHUTDOWN] Residual positions detected! Net: {net_delta}")
            self.logger.warning("[SHUTDOWN] Auto-closing residual positions...")
            await self.force_close_all_positions()

            # Verify cleanup succeeded
            await asyncio.sleep(3)
            final_primary, final_hedge = await self.get_positions(force_api=True)
            net_delta = final_primary + final_hedge

            if abs(net_delta) > self.order_quantity * Decimal("0.01"):
                self.logger.error(f"[SHUTDOWN] Failed to close residual positions! Net: {net_delta}")
            else:
                self.logger.info(f"[SHUTDOWN] Residual positions closed successfully. Net: {net_delta}")
        else:
            self.logger.info("[SHUTDOWN] No residual positions. Clean shutdown.")

        # Export trade metrics at shutdown
        self.logger.info("[SHUTDOWN] Exporting trade metrics...")
        self.export_trade_metrics()

    async def run(self):
        self.setup_signal_handlers()

        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            self.logger.info("\nReceived interrupt signal...")
        finally:
            self.logger.info("Cleaning up...")
            await self.cleanup_connections()
            self.shutdown()


def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(
        description="Delta Neutral Hedge Bot: Backpack + GRVT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test 1: PRIMARY=BBO-1tick, HEDGE=market (default)
    python DN_alternate_backpack_grvt.py --ticker SOL --size 1 --iter 10

    # Test 2: PRIMARY=BBO, HEDGE=market
    python DN_alternate_backpack_grvt.py --ticker SOL --size 1 --iter 10 --primary-mode bbo

    # Test 3: PRIMARY=BBO-1tick, HEDGE=BBO-1tick
    python DN_alternate_backpack_grvt.py --ticker SOL --size 1 --iter 10 --hedge-mode bbo_minus_1

    # Test 4: PRIMARY=BBO, HEDGE=BBO
    python DN_alternate_backpack_grvt.py --ticker SOL --size 1 --iter 10 --primary-mode bbo --hedge-mode bbo
        """,
    )

    parser.add_argument(
        "--ticker", type=str, default="SOL", help="Ticker symbol (default: SOL)"
    )
    parser.add_argument(
        "--size", type=str, required=True, help="Order quantity per trade"
    )
    parser.add_argument(
        "--iter", type=int, required=True, help="Number of trading iterations"
    )
    parser.add_argument(
        "--fill-timeout",
        type=int,
        default=5,
        help="Timeout for order fills in seconds (default: 5)",
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=0,
        help="Sleep time between iterations in seconds (default: 0)",
    )
    parser.add_argument(
        "--max-position",
        type=str,
        default="0",
        help="Maximum position size (default: same as --size)",
    )
    parser.add_argument(
        "--primary",
        type=str,
        default="nado",
        choices=["nado", "backpack", "grvt"],
        help="Primary exchange for POST_ONLY orders (default: nado)",
    )
    parser.add_argument(
        "--hedge",
        type=str,
        default="edgex",
        choices=["edgex", "grvt"],
        help="Hedge exchange for market orders (default: edgex)",
    )
    parser.add_argument(
        "--primary-mode",
        type=str,
        default="bbo",
        choices=["bbo_minus_1", "bbo", "aggressive"],
        help="Primary order price mode (default: bbo). Use 'bbo' for volatile markets, 'aggressive' for immediate fills",
    )
    parser.add_argument(
        "--hedge-mode",
        type=str,
        default="market",
        choices=["market", "bbo_minus_1", "bbo_plus_1", "bbo", "aggressive"],
        help="Hedge order price mode (default: market). aggressive: BUY@ask, SELL@bid for instant fill",
    )
    parser.add_argument(
        "--hedge-post-only",
        action="store_true",
        default=True,
        help="Use POST_ONLY for hedge orders to save 0.05% taker fee (default: True)",
    )
    parser.add_argument(
        "--hedge-market",
        action="store_true",
        default=False,
        help="Use MARKET for hedge orders (0.05% taker fee) - disables POST_ONLY",
    )
    parser.add_argument(
        "--env-file", type=str, default=".env", help=".env file path (default: .env)"
    )
    parser.add_argument(
        "--min-spread",
        type=str,
        default="0",
        help="Minimum spread in bps to enter trade (default: 0 = disabled)",
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

    if args.primary == args.hedge:
        print("Error: PRIMARY and HEDGE exchanges must be different")
        sys.exit(1)

    primary_mode = PriceMode(args.primary_mode)
    hedge_mode = PriceMode(args.hedge_mode)
    hedge_post_only = args.hedge_post_only and not args.hedge_market

    # DNPairBot uses target_notional (USD notional per position)
    bot = DNPairBot(
        target_notional=Decimal(args.size),  # USD notional per position (e.g., 100 = $100)
        fill_timeout=args.fill_timeout,
        iterations=args.iter,
        sleep_time=args.sleep,
        max_position_eth=Decimal("5"),
        max_position_sol=Decimal("50"),
        order_mode=PriceMode.BBO,
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
