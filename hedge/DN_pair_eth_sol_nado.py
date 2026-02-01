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
from typing import Tuple, List, Optional
from datetime import datetime
import pytz

# Import exchanges modules (like Mean Reversion bot)
from hedge.exchanges.nado import NadoClient
from hedge.exchanges.base import OrderResult
from hedge.rollback_monitor import RollbackMonitor


class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)

        # NEW: Feature flags for PNL optimization strategies
        self.enable_at_touch_pricing = getattr(self, 'enable_at_touch_pricing', False)
        self.enable_order_type_default = getattr(self, 'enable_order_type_default', False)
        self.enable_queue_filter = getattr(self, 'enable_queue_filter', False)
        self.enable_spread_filter = getattr(self, 'enable_spread_filter', False)
        self.enable_partial_fills = getattr(self, 'enable_partial_fills', False)
        self.enable_dynamic_timeout = getattr(self, 'enable_dynamic_timeout', False)

        # NEW: Configurable thresholds
        self.queue_threshold_ratio = getattr(self, 'queue_threshold_ratio', 0.5)
        self.spread_threshold_ticks = getattr(self, 'spread_threshold_ticks', 5)
        self.min_partial_fill_ratio = getattr(self, 'min_partial_fill_ratio', 0.5)


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
        use_post_only: bool = True,  # POST_ONLY mode (maker, 2 bps) vs IOC (taker, 5 bps)
        min_spread_bps: int = 0,  # Minimum spread in bps - sanity check only, profit comes from post-entry movements
        # Feature flags for PNL optimization
        enable_at_touch_pricing: bool = False,
        enable_order_type_default: bool = False,
        enable_queue_filter: bool = False,
        enable_spread_filter: bool = False,
        enable_partial_fills: bool = False,
        enable_dynamic_timeout: bool = False,
        # Configurable thresholds
        queue_threshold_ratio: float = 0.5,
        spread_threshold_ticks: int = 5,
        min_partial_fill_ratio: float = 0.5,
    ):
        self.target_notional = target_notional  # USD notional for each position
        self.iterations = iterations
        self.sleep_time = sleep_time
        self.min_spread_bps = min_spread_bps

        # PNL optimization feature flags
        self.enable_at_touch_pricing = enable_at_touch_pricing
        self.enable_order_type_default = enable_order_type_default
        self.enable_queue_filter = enable_queue_filter
        self.enable_spread_filter = enable_spread_filter
        self.enable_partial_fills = enable_partial_fills
        self.enable_dynamic_timeout = enable_dynamic_timeout

        # Configurable thresholds
        self.queue_threshold_ratio = queue_threshold_ratio
        self.spread_threshold_ticks = spread_threshold_ticks
        self.min_partial_fill_ratio = min_partial_fill_ratio

        # Determine order mode based on feature flags
        if self.enable_order_type_default:
            self.use_post_only = False  # Use OrderType.DEFAULT
            self.order_mode = "default"
        elif use_post_only is not None:
            self.use_post_only = use_post_only
            self.order_mode = "post_only" if self.use_post_only else "ioc"
        else:
            self.use_post_only = True  # Default behavior
            self.order_mode = "post_only"

        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/DN_pair_eth_sol_nado_log.txt"

        # Log order mode configuration
        import logging
        self._config_logger = logging.getLogger("dn_config")
        self._config_logger.info(f"[CONFIG] Order mode: {self.order_mode.upper()} (POST_ONLY={self.use_post_only})")
        self._config_logger.info(f"[CONFIG] Min spread filter: {self.min_spread_bps} bps")
        self._config_logger.info(f"[CONFIG] At-touch pricing: {self.enable_at_touch_pricing}")
        self._config_logger.info(f"[CONFIG] Order type DEFAULT: {self.enable_order_type_default}")
        self._config_logger.info(f"[CONFIG] Queue filter: {self.enable_queue_filter} (threshold: {self.queue_threshold_ratio})")
        self._config_logger.info(f"[CONFIG] Spread filter: {self.enable_spread_filter} (threshold: {self.spread_threshold_ticks} ticks)")
        self._config_logger.info(f"[CONFIG] Partial fills: {self.enable_partial_fills} (min ratio: {self.min_partial_fill_ratio})")
        self._config_logger.info(f"[CONFIG] Dynamic timeout: {self.enable_dynamic_timeout}")

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

        # PNL Tracking State (V5.3)
        from decimal import Decimal
        from datetime import datetime

        self.entry_prices = {
            "ETH": None,  # Decimal: Entry 진입 가격
            "SOL": None   # Decimal: Entry 진입 가격
        }
        self.entry_quantities = {
            "ETH": Decimal("0"),
            "SOL": Decimal("0")
        }
        self.entry_timestamps = {
            "ETH": None,
            "SOL": None
        }
        self.current_cycle_pnl = {
            "pnl_no_fee": Decimal("0"),
            "pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "entry_time": None,
            "exit_time": None
        }
        self.daily_pnl_summary = {
            "total_cycles": 0,
            "profitable_cycles": 0,
            "losing_cycles": 0,
            "total_pnl_no_fee": Decimal("0"),
            "total_pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "best_cycle_pnl": Decimal("0"),
            "worst_cycle_pnl": Decimal("0")
        }
        self.cycle_id = 0  # Unique cycle identifier

        # Rollback monitoring
        self.rollback_monitor = RollbackMonitor()
        self._had_safety_stop = False  # Track if current cycle had safety stop

        # Real-time PNL logging task
        self._realtime_pnl_task = None

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
                # V5.6 Enhanced CSV columns with WebSocket decision factors
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
                        "cycle_id",
                        "entry_timestamp",
                        "exit_timestamp",
                        "entry_price_eth",
                        "entry_price_sol",
                        "exit_price_eth",
                        "exit_price_sol",
                        "spread_bps_entry",
                        "spread_bps_exit",
                        "slippage_bps_entry",
                        "slippage_bps_exit",
                        "cycle_skipped",
                        "skip_reason",
                        # TASK 6: WebSocket decision factors
                        "eth_momentum_state",
                        "sol_momentum_state",
                        "spread_state_entry",
                        "spread_state_exit",
                        "entry_threshold_bps",
                        "exit_threshold_bps",
                        "exit_liquidity_available",
                        "exit_liquidity_usd",
                        "websocket_available"
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
        cycle_id: str = "",
        entry_timestamp: str = "",
        exit_timestamp: str = "",
        entry_price_eth: str = "",
        entry_price_sol: str = "",
        exit_price_eth: str = "",
        exit_price_sol: str = "",
        spread_bps_entry: str = "",
        spread_bps_exit: str = "",
        slippage_bps_entry: str = "",
        slippage_bps_exit: str = "",
        cycle_skipped: str = "false",
        skip_reason: str = "",
        # TASK 6: WebSocket decision factors
        eth_momentum_state: str = "",
        sol_momentum_state: str = "",
        spread_state_entry: str = "",
        spread_state_exit: str = "",
        entry_threshold_bps: str = "",
        exit_threshold_bps: str = "",
        exit_liquidity_available: str = "",
        exit_liquidity_usd: str = "",
        websocket_available: str = "",
    ):
        timestamp = datetime.now(pytz.UTC).isoformat()
        with open(self.csv_filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                exchange, timestamp, side, price, quantity, order_type, mode,
                fee_usd, pnl_no_fee, pnl_with_fee,
                cycle_id, entry_timestamp, exit_timestamp,
                entry_price_eth, entry_price_sol, exit_price_eth, exit_price_sol,
                spread_bps_entry, spread_bps_exit,
                slippage_bps_entry, slippage_bps_exit,
                cycle_skipped, skip_reason,
                # TASK 6: WebSocket decision factors
                eth_momentum_state, sol_momentum_state,
                spread_state_entry, spread_state_exit,
                entry_threshold_bps, exit_threshold_bps,
                exit_liquidity_available, exit_liquidity_usd,
                websocket_available
            ])

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

        Implements liquidity-based skip logic:
        - When slippage > 10 bps: return qty=0 (signal to skip trade)
        - When slippage <= 10 bps: return full target_qty
        - Maintains $100 fixed notional constraint (no size reduction)

        Args:
            price: Current price
            ticker: "ETH" or "SOL"
            direction: "buy" or "sell"
            max_slippage_bps: Maximum acceptable slippage in basis points

        Returns:
            Tuple of (order_quantity, estimated_slippage_bps, can_fill_at_full_qty)
            Note: qty=0 signals to skip the trade due to insufficient liquidity
        """
        # Define liquidity threshold for skipping trades (10 bps)
        LIQUIDITY_THRESHOLD_BPS = 10

        client = self.eth_client if ticker == "ETH" else self.sol_client
        raw_qty = self.target_notional / price
        tick_size = client.config.tick_size
        min_size = client.config.min_size

        # MINIMUM QUANTITY CHECK: Detect order too small for exchange before quantization
        if raw_qty < min_size:
            self.logger.warning(
                f"[SLIPPAGE] {ticker} order size {raw_qty:.6f} < minimum {min_size} - "
                f"CANNOT TRADE (notional=${self.target_notional}, price=${price:.2f})"
            )
            # Return zero quantity with error indicator (False = can't fill, 999999 = error code)
            return Decimal(0), Decimal(999999), False

        # Use raw_qty directly - no need to round quantity to price tick_size
        # (tick_size is for price rounding, not quantity rounding)
        target_qty = raw_qty

        # Try to get slippage estimate from BookDepth
        slippage = await client.estimate_slippage(direction, target_qty)

        if slippage >= Decimal(999999):
            # No BookDepth data available - return target qty with warning
            self.logger.warning(f"[SLIPPAGE] No BookDepth data for {ticker}, using target quantity {target_qty}")
            return target_qty, Decimal(0), True

        # LIQUIDITY-BASED SKIP LOGIC:
        # When slippage exceeds threshold, skip the trade entirely (return qty=0)
        if slippage > LIQUIDITY_THRESHOLD_BPS:
            self.logger.warning(
                f"[SLIPPAGE] {ticker} slippage {slippage:.1f} bps > {LIQUIDITY_THRESHOLD_BPS} bps threshold - "
                f"SKIPPING TRADE due to insufficient liquidity (target_qty={target_qty}, notional=${self.target_notional})"
            )
            return Decimal(0), slippage, False

        # Slippage within acceptable range - proceed with full target quantity
        if slippage <= max_slippage_bps:
            self.logger.info(
                f"[SLIPPAGE] {ticker} slippage {slippage:.1f} bps within threshold - "
                f"proceeding with full target_qty={target_qty} (notional=${self.target_notional})"
            )
            return target_qty, slippage, True

        # Edge case: slippage between threshold and max_slippage_bps
        # Still skip to maintain conservative approach
        self.logger.warning(
            f"[SLIPPAGE] {ticker} slippage {slippage:.1f} bps exceeds liquidity threshold - "
            f"SKIPPING TRADE (target_qty={target_qty}, notional=${self.target_notional})"
        )
        return Decimal(0), slippage, False

    async def place_simultaneous_orders(
        self,
        eth_direction: str,
        sol_direction: str,
        attempt_count: int = 0,
    ) -> Tuple[OrderResult, OrderResult]:
        """Place ETH and SOL orders simultaneously using REST-based position monitoring.

        Supports both IOC (Immediate-Or-Cancel) and POST_ONLY modes:
        - IOC: Aggressive, crosses spread, 5 bps taker fee, immediate fills
        - POST_ONLY: Passive, rests on book, 2 bps maker fee, may not fill

        Follows the your-quantguy reference pattern:
        1. Get position BEFORE placing order
        2. Place order with aggressive pricing (IOC) or passive pricing (POST_ONLY)
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

        # Calculate spread in ticks
        eth_spread = eth_ask - eth_bid
        eth_spread_ticks = eth_spread / self.eth_client.config.tick_size

        sol_spread = sol_ask - sol_bid
        sol_spread_ticks = sol_spread / self.sol_client.config.tick_size

        # Spread filter (only if enabled)
        if self.enable_spread_filter:
            if eth_spread_ticks > self.spread_threshold_ticks or sol_spread_ticks > self.spread_threshold_ticks:
                self.logger.warning(
                    f"[SPREAD FILTER] Skipping: ETH spread={eth_spread_ticks:.1f} ticks, "
                    f"SOL spread={sol_spread_ticks:.1f} ticks > {self.spread_threshold_ticks}"
                )
                return (OrderResult(success=False, error_message="Spread too wide"),
                        OrderResult(success=False, error_message="Spread too wide"))

        # Fee rate based on order mode: POST_ONLY = 2 bps (maker), IOC = 5 bps (taker)
        FEE_RATE = Decimal("0.0002") if self.use_post_only else Decimal("0.0005")
        fee_bps = float(FEE_RATE * 10000)
        self.logger.info(f"[ORDER] Mode: {self.order_mode.upper()}, Fee: {fee_bps:.0f} bps")

        # Queue filter (only if enabled)
        if self.enable_queue_filter:
            eth_can_trade, eth_queue_size, eth_queue_reason = await self.check_queue_size(
                self.eth_client, eth_direction, max_queue_ratio=self.queue_threshold_ratio
            )
            sol_can_trade, sol_queue_size, sol_queue_reason = await self.check_queue_size(
                self.sol_client, sol_direction, max_queue_ratio=self.queue_threshold_ratio
            )

            # Skip if either queue is too deep
            if not eth_can_trade or not sol_can_trade:
                skip_reasons = []
                if not eth_can_trade:
                    skip_reasons.append(f"ETH: {eth_queue_reason}")
                if not sol_can_trade:
                    skip_reasons.append(f"SOL: {sol_queue_reason}")
                self.logger.warning(
                    f"[QUEUE FILTER] Skipping trade: {', '.join(skip_reasons)}"
                )
                return (
                    OrderResult(success=False, error_message=f"Queue filter: {skip_reasons}"),
                    OrderResult(success=False, error_message=f"Queue filter: {skip_reasons}")
                )

        if self.use_post_only:
            # POST_ONLY: Place at touch price (limit order, passive)
            # For sell orders: use bid price; for buy orders: use ask price
            eth_price = eth_bid if eth_direction == "sell" else eth_ask
            sol_price = sol_bid if sol_direction == "sell" else sol_ask

            # Use BookDepth for sizing
            eth_qty, eth_slippage_bps, eth_full_fill = await self.calculate_order_size_with_slippage(
                eth_price, "ETH", eth_direction, max_slippage_bps=10
            )
            sol_qty, sol_slippage_bps, sol_full_fill = await self.calculate_order_size_with_slippage(
                sol_price, "SOL", sol_direction, max_slippage_bps=10
            )

            # LIQUIDITY-BASED SKIP LOGIC: Check if either leg signals to skip (qty=0)
            if eth_qty == 0 or sol_qty == 0:
                skip_reason = []
                if eth_qty == 0:
                    if eth_slippage_bps >= Decimal(999999):
                        skip_reason.append(f"ETH order size too small for exchange minimum")
                    else:
                        skip_reason.append(f"ETH slippage {eth_slippage_bps:.1f} bps > 10 bps threshold")
                if sol_qty == 0:
                    if sol_slippage_bps >= Decimal(999999):
                        skip_reason.append(f"SOL order size too small for exchange minimum")
                    else:
                        skip_reason.append(f"SOL slippage {sol_slippage_bps:.1f} bps > 10 bps threshold")
                self.logger.warning(
                    f"[ORDER] SKIPPING TRADE due to insufficient liquidity: {', '.join(skip_reason)}"
                )
                # Return failed results to signal skip
                return (
                    OrderResult(success=False, error_message=f"Skipped: {', '.join(skip_reason)}"),
                    OrderResult(success=False, error_message=f"Skipped: {', '.join(skip_reason)}")
                )

            self.logger.info(
                f"[ORDER] Placing POST_ONLY orders: "
                f"ETH {eth_direction} {eth_qty} @ ${eth_price}, "
                f"SOL {sol_direction} {sol_qty} @ ${sol_price}"
            )

            # Place POST_ONLY orders using place_open_order (which uses POST_ONLY appendix)
            # Note: place_open_order uses OrderType.POST_ONLY and isolated=True
            POST_ONLY_TIMEOUT = 5  # seconds

            eth_result, sol_result = await asyncio.gather(
                self.eth_client.place_open_order(
                    self.eth_client.config.contract_id,
                    eth_qty,
                    eth_direction,
                    eth_price
                ),
                self.sol_client.place_open_order(
                    self.sol_client.config.contract_id,
                    sol_qty,
                    sol_direction,
                    sol_price
                ),
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(eth_result, Exception):
                self.logger.error(f"[ORDER] ETH order failed: {eth_result}")
                eth_result = OrderResult(success=False, error_message=str(eth_result))
            if isinstance(sol_result, Exception):
                self.logger.error(f"[ORDER] SOL order failed: {sol_result}")
                sol_result = OrderResult(success=False, error_message=str(sol_result))

            # POST_ONLY: Poll and wait for actual fills (OPEN != filled)
            # Dynamic timeout (only if enabled)
            if self.enable_dynamic_timeout:
                spread_state = self.eth_client._bbo_handler.get_spread_state()
                POST_ONLY_TIMEOUT = self.eth_client.calculate_timeout(eth_qty, spread_state)
            else:
                POST_ONLY_TIMEOUT = 5.0  # Default timeout
            POLL_INTERVAL = 0.1
            eth_fill_event = asyncio.Event()
            sol_fill_event = asyncio.Event()

            async def poll_eth_fill():
                try:
                    for _ in range(int(POST_ONLY_TIMEOUT / POLL_INTERVAL)):
                        if eth_result.order_id:
                            order_info = await self.eth_client.get_order_info(eth_result.order_id)
                            if order_info:
                                filled_ratio = abs(order_info.filled_size) / eth_result.size
                                if order_info.remaining_size == 0 or filled_ratio >= self.min_partial_fill_ratio:
                                    eth_fill_event.set()
                                    return
                        await asyncio.sleep(POLL_INTERVAL)
                except Exception as e:
                    self.logger.warning(f"[ORDER] Error polling ETH fill: {e}")

            async def poll_sol_fill():
                try:
                    for _ in range(int(POST_ONLY_TIMEOUT / POLL_INTERVAL)):
                        if sol_result.order_id:
                            order_info = await self.sol_client.get_order_info(sol_result.order_id)
                            if order_info:
                                filled_ratio = abs(order_info.filled_size) / sol_result.size
                                if order_info.remaining_size == 0 or filled_ratio >= self.min_partial_fill_ratio:
                                    sol_fill_event.set()
                                    return
                        await asyncio.sleep(POLL_INTERVAL)
                except Exception as e:
                    self.logger.warning(f"[ORDER] Error polling SOL fill: {e}")

            poll_task = asyncio.gather(poll_eth_fill(), poll_sol_fill())

            try:
                await asyncio.wait_for(asyncio.gather(
                    eth_fill_event.wait(),
                    sol_fill_event.wait()
                ), timeout=POST_ONLY_TIMEOUT)
                self.logger.info("[ORDER] Both POST_ONLY orders filled successfully")
                poll_task.cancel()
            except asyncio.TimeoutError:
                self.logger.warning("[ORDER] POST_ONLY timeout, checking fill status...")
                eth_order_info = await self.eth_client.get_order_info(eth_result.order_id) if eth_result.order_id else None
                sol_order_info = await self.sol_client.get_order_info(sol_result.order_id) if sol_result.order_id else None
                eth_filled = eth_order_info and eth_order_info.remaining_size == 0
                sol_filled = sol_order_info and sol_order_info.remaining_size == 0
                if not (eth_filled and sol_filled):
                    # Cancel any open POST_ONLY orders
                    try:
                        if eth_result.status == 'OPEN' and eth_result.order_id:
                            await self.eth_client.cancel_order(eth_result.order_id)
                    except Exception as e:
                        self.logger.error(f"[CANCEL] Failed to cancel ETH order: {e}")

                    try:
                        if sol_result.status == 'OPEN' and sol_result.order_id:
                            await self.sol_client.cancel_order(sol_result.order_id)
                    except Exception as e:
                        self.logger.error(f"[CANCEL] Failed to cancel SOL order: {e}")

                    # Recursive fallback with attempt limit
                    if attempt_count < 2:
                        self.logger.warning(
                            f"[ORDER] POST_ONLY incomplete (attempt {attempt_count + 1}/2), "
                            f"falling back to IOC"
                        )
                        original_mode = self.use_post_only
                        self.use_post_only = False
                        try:
                            return await self.place_simultaneous_orders(
                                eth_direction, sol_direction, attempt_count + 1
                            )
                        finally:
                            self.use_post_only = original_mode
                    else:
                        self.logger.error("[ORDER] Max attempts exceeded, aborting cycle")
                        return (
                            OrderResult(success=False, error_message="POST_ONLY and IOC both failed"),
                            OrderResult(success=False, error_message="POST_ONLY and IOC both failed")
                        )

            # Store order results for further processing
            # Note: POST_ONLY orders may return with status='OPEN' instead of 'FILLED'
            # We need to handle this case appropriately

        else:
            # Original IOC logic (existing code)
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

            # LIQUIDITY-BASED SKIP LOGIC: Check if either leg signals to skip (qty=0)
            if eth_qty == 0 or sol_qty == 0:
                skip_reason = []
                if eth_qty == 0:
                    if eth_slippage_bps >= Decimal(999999):
                        skip_reason.append(f"ETH order size too small for exchange minimum")
                    else:
                        skip_reason.append(f"ETH slippage {eth_slippage_bps:.1f} bps > 10 bps threshold")
                if sol_qty == 0:
                    if sol_slippage_bps >= Decimal(999999):
                        skip_reason.append(f"SOL order size too small for exchange minimum")
                    else:
                        skip_reason.append(f"SOL slippage {sol_slippage_bps:.1f} bps > 10 bps threshold")
                self.logger.warning(
                    f"[ORDER] SKIPPING TRADE due to insufficient liquidity: {', '.join(skip_reason)}"
                )
                # Return failed results to signal skip
                return (
                    OrderResult(success=False, error_message=f"Skipped: {', '.join(skip_reason)}"),
                    OrderResult(success=False, error_message=f"Skipped: {', '.join(skip_reason)}")
                )

            self.logger.info(
                f"[ORDER] Placing IOC orders: "
                f"ETH {eth_direction} {eth_qty} @ ~${eth_price} ({eth_slippage_bps:.1f} bps est. slippage), "
                f"SOL {sol_direction} {sol_qty} @ ~${sol_price} ({sol_slippage_bps:.1f} bps est. slippage)"
            )

            # Place IOC orders concurrently (Immediate-Or-Cancel for immediate fills)
            eth_result, sol_result = await asyncio.gather(
                self.eth_client.place_ioc_order(self.eth_client.config.contract_id, eth_qty, eth_direction),
                self.sol_client.place_ioc_order(self.sol_client.config.contract_id, sol_qty, sol_direction),
                return_exceptions=True
            )

        # Check for exceptions (IOC mode only - POST_ONLY already handled above)
        if not self.use_post_only:
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

        # Extract fill details from OrderResult
        # Handle both IOC (immediate fill) and POST_ONLY (may return OPEN status)
        eth_filled = eth_result.status == 'FILLED' or (self.use_post_only and eth_result.status == 'OPEN')
        eth_fill_qty = eth_result.filled_size if eth_filled else (eth_result.size if eth_result.status == 'OPEN' else Decimal(0))
        eth_fill_price = eth_result.price if eth_filled else Decimal(0)

        sol_filled = sol_result.status == 'FILLED' or (self.use_post_only and sol_result.status == 'OPEN')
        sol_fill_qty = sol_result.filled_size if sol_filled else (sol_result.size if sol_result.status == 'OPEN' else Decimal(0))
        sol_fill_price = sol_result.price if sol_filled else Decimal(0)

        # Check results and log fills
        if eth_filled:
            self.logger.info(f"[FILL] ETH order {'filled' if not self.use_post_only else 'placed'}: {eth_fill_qty} @ ${eth_fill_price}")
        elif eth_result.success and eth_fill_qty > 0:
            self.logger.warning(f"[FILL] ETH order partially filled: {eth_fill_qty}/{eth_qty}")
        else:
            self.logger.warning(f"[FILL] ETH order did not fill")

        if sol_filled:
            self.logger.info(f"[FILL] SOL order {'filled' if not self.use_post_only else 'placed'}: {sol_fill_qty} @ ${sol_fill_price}")
        elif sol_result.success and sol_fill_qty > 0:
            self.logger.warning(f"[FILL] SOL order partially filled: {sol_fill_qty}/{sol_qty}")
        else:
            self.logger.warning(f"[FILL] SOL order did not fill")

        # Hybrid partial fill handling for IOC mode
        # Check if both orders had partial fills (not fully filled, but some quantity filled)
        if not self.use_post_only and eth_fill_qty > 0 and sol_fill_qty > 0:
            if (eth_fill_qty < eth_qty or sol_fill_qty < sol_qty):
                # At least one order was partially filled
                should_proceed, reason, retry_coro = self._handle_partial_fill(
                    eth_filled=eth_filled,
                    sol_filled=sol_filled,
                    eth_fill_qty=eth_fill_qty,
                    sol_fill_qty=sol_fill_qty,
                    eth_target_qty=eth_qty,
                    sol_target_qty=sol_qty,
                    eth_direction=eth_direction,
                    sol_direction=sol_direction
                )
                if not should_proceed:
                    # Partial fill rejected - trigger emergency unwind
                    self.logger.warning(f"[PARTIAL] {reason}")
                    await self.handle_emergency_unwind(eth_result, sol_result)
                    return eth_result, sol_result
                elif retry_coro is not None:
                    # Partial fill accepted - execute retry
                    self.logger.info(f"[PARTIAL] {reason}")
                    return await retry_coro
                else:
                    # Fill acceptable (>80%), proceed with normal flow
                    self.logger.info(f"[PARTIAL] {reason}")

        # Log actual fills to CSV
        # Fee rate based on order mode: POST_ONLY = 2 bps (maker), IOC = 5 bps (taker)
        # Re-calculate FEE_RATE here for CSV logging (was calculated above but in different scope)
        FEE_RATE = Decimal("0.0002") if self.use_post_only else Decimal("0.0005")

        # Store entry prices and quantities for PNL tracking
        if hasattr(self, '_is_entry_phase') and self._is_entry_phase:
            from datetime import datetime
            entry_timestamp = datetime.now(pytz.UTC).isoformat()

            if eth_fill_qty > 0:
                self.entry_prices["ETH"] = eth_fill_price
                self.entry_quantities["ETH"] = eth_fill_qty
                self.entry_timestamps["ETH"] = entry_timestamp

            if sol_fill_qty > 0:
                self.entry_prices["SOL"] = sol_fill_price
                self.entry_quantities["SOL"] = sol_fill_qty
                self.entry_timestamps["SOL"] = entry_timestamp

        if eth_fill_qty > 0:
            eth_notional = eth_fill_price * eth_fill_qty
            eth_fee = eth_notional * FEE_RATE

            # Track fees for PNL
            if hasattr(self, 'current_cycle_pnl'):
                self.current_cycle_pnl["total_fees"] += eth_fee

            # Determine if this is an exit order based on phase flags, not direction
            # SELL_FIRST cycle BUILD uses "sell" for ETH but it's still an entry, not exit
            is_exit_order = hasattr(self, '_is_exit_phase') and self._is_exit_phase

            # Prepare CSV parameters with new V5.3 fields
            csv_params = self._prepare_csv_params(
                exchange="NADO",
                side=f"ETH-{eth_direction.upper()}",
                price=str(eth_fill_price),
                quantity=str(eth_fill_qty),
                order_type="entry" if not is_exit_order else "exit",
                mode="FILLED" if eth_filled else "PARTIAL",
                fee_usd=str(eth_fee),
                is_exit=is_exit_order
            )
            try:
                self.log_trade_to_csv(**csv_params)
            except Exception as e:
                self.logger.error(f"[CSV] Error logging ETH trade: {e}")

        if sol_fill_qty > 0:
            sol_notional = sol_fill_price * sol_fill_qty
            sol_fee = sol_notional * FEE_RATE

            # Track fees for PNL
            if hasattr(self, 'current_cycle_pnl'):
                self.current_cycle_pnl["total_fees"] += sol_fee

            # Determine if this is an exit order based on phase flags, not direction
            # SELL_FIRST cycle BUILD uses "buy" for SOL but it's still an entry, not exit
            is_exit_order = hasattr(self, '_is_exit_phase') and self._is_exit_phase

            # Prepare CSV parameters with new V5.3 fields
            csv_params = self._prepare_csv_params(
                exchange="NADO",
                side=f"SOL-{sol_direction.upper()}",
                price=str(sol_fill_price),
                quantity=str(sol_fill_qty),
                order_type="entry" if not is_exit_order else "exit",
                mode="FILLED" if sol_filled else "PARTIAL",
                fee_usd=str(sol_fee),
                is_exit=is_exit_order
            )
            try:
                self.log_trade_to_csv(**csv_params)
            except Exception as e:
                self.logger.error(f"[CSV] Error logging SOL trade: {e}")

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
        """Emergency unwind ETH position (handles both long and short).

        Determines current position direction and closes with market order.
        Uses tolerance check (abs(pos) > 0.001) to handle Decimal precision.

        Called from handle_emergency_unwind() when ETH fills but SOL fails.
        """
        if self.eth_client:
            try:
                current_pos = await self.eth_client.get_account_positions()
                # NOTE: No None check needed - get_account_positions() always returns Decimal
                # See nado.py:1078 - method signature: async def get_account_positions(self) -> Decimal
                # Tolerance check: skip dust positions below 0.001
                # Pattern from test_dn_pair.py: handles Decimal precision issues
                if abs(current_pos) > Decimal("0.001"):
                    # Determine close side: long positions sell, short positions buy
                    close_side = "sell" if current_pos > 0 else "buy"
                    await self.eth_client.place_close_order(
                        self.eth_client.config.contract_id,
                        abs(current_pos),  # Always use positive quantity
                        Decimal("0"),  # Market order
                        close_side  # Dynamically determined side
                    )
            except Exception as e:
                self.logger.error(f"[UNWIND] Failed to close ETH position: {e}")

    async def emergency_unwind_sol(self):
        """Emergency unwind SOL position (handles both long and short).

        Determines current position direction and closes with market order.
        Uses tolerance check (abs(pos) > 0.001) to handle Decimal precision.

        Called from handle_emergency_unwind() when SOL fills but ETH fails.
        """
        if self.sol_client:
            try:
                current_pos = await self.sol_client.get_account_positions()
                # NOTE: No None check needed - get_account_positions() always returns Decimal
                # See nado.py:1078 - method signature: async def get_account_positions(self) -> Decimal
                # Tolerance check: skip dust positions below 0.001
                # Pattern from test_dn_pair.py: handles Decimal precision issues
                if abs(current_pos) > Decimal("0.001"):
                    # Determine close side: long positions sell, short positions buy
                    close_side = "sell" if current_pos > 0 else "buy"
                    await self.sol_client.place_close_order(
                        self.sol_client.config.contract_id,
                        abs(current_pos),  # Always use positive quantity
                        Decimal("0"),  # Market order
                        close_side  # Dynamically determined side
                    )
            except Exception as e:
                self.logger.error(f"[UNWIND] Failed to close SOL position: {e}")

    def _handle_partial_fill(
        self,
        eth_filled: bool,
        sol_filled: bool,
        eth_fill_qty: Decimal,
        sol_fill_qty: Decimal,
        eth_target_qty: Decimal,
        sol_target_qty: Decimal,
        eth_direction: str,
        sol_direction: str
    ) -> tuple[bool, str, Optional]:
        """
        Hybrid partial fill handling with complete retry logic.
        Returns: (should_proceed, reason, retry_coroutine)
        """
        eth_fill_ratio = float(eth_fill_qty / eth_target_qty) if eth_target_qty > 0 else 0
        sol_fill_ratio = float(sol_fill_qty / sol_target_qty) if sol_target_qty > 0 else 0
        avg_fill_ratio = (eth_fill_ratio + sol_fill_ratio) / 2

        # Check for dangerous imbalance
        imbalance = abs(eth_fill_ratio - sol_fill_ratio)
        if imbalance > 0.5:
            return False, f"Dangerous fill imbalance: ETH={eth_fill_ratio:.1%}, SOL={sol_fill_ratio:.1%}", None

        # Hybrid decision logic
        if avg_fill_ratio < 0.2:
            return False, f"Insufficient fill: {avg_fill_ratio:.1%} < 20%", None
        elif avg_fill_ratio < 0.8:
            # Retry remaining quantities
            retry_qty_eth = eth_target_qty - eth_fill_qty
            retry_qty_sol = sol_target_qty - sol_fill_qty
            self.logger.info(
                f"[PARTIAL] {avg_fill_ratio:.1%} filled, retrying remaining: "
                f"ETH={retry_qty_eth}, SOL={retry_qty_sol}"
            )
            async def retry_remaining():
                return await self.execute_entry(retry_qty_eth, retry_qty_sol)
            return True, "Partial fill accepted, retrying remaining", retry_remaining()
        else:
            # > 80% filled: accept and proceed
            return True, f"Fill acceptable: {avg_fill_ratio:.1%}", None

    def _prepare_csv_params(
        self,
        exchange: str,
        side: str,
        price: str,
        quantity: str,
        order_type: str,
        mode: str,
        fee_usd: str,
        is_exit: bool
    ) -> dict:
        """Prepare CSV logging parameters with V5.3 PNL tracking fields.

        Args:
            is_exit: True if this is an exit order (will calculate PNL)

        Returns:
            Dictionary with all CSV parameters including new V5.3 fields
        """
        from datetime import datetime
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE

        # Check if we're in exit phase
        in_exit_phase = hasattr(self, '_is_exit_phase') and self._is_exit_phase

        # TASK 6: Get WebSocket decision factors
        eth_momentum = getattr(self, '_eth_momentum_state', '')
        sol_momentum = getattr(self, '_sol_momentum_state', '')
        spread_state_entry = getattr(self, '_spread_state_entry', '')
        spread_state_exit = getattr(self, '_spread_state_exit', '')
        entry_threshold = getattr(self, '_entry_threshold_bps', '')
        exit_threshold = getattr(self, '_exit_threshold_bps', '')
        exit_liq_avail = getattr(self, '_exit_liquidity_available', '')
        exit_liq_usd = getattr(self, '_exit_liquidity_usd', '')

        params = {
            "exchange": exchange,
            "side": side,
            "price": price,
            "quantity": quantity,
            "order_type": order_type,
            "mode": mode,
            "fee_usd": fee_usd,
            "pnl_no_fee": "0",
            "pnl_with_fee": "0",
            "cycle_id": str(getattr(self, 'cycle_id', 0)),
            "entry_timestamp": "",
            "exit_timestamp": datetime.now(pytz.UTC).isoformat() if is_exit or in_exit_phase else "",
            "entry_price_eth": str(getattr(self, 'entry_prices', {}).get('ETH', '')) if hasattr(self, 'entry_prices') else "",
            "entry_price_sol": str(getattr(self, 'entry_prices', {}).get('SOL', '')) if hasattr(self, 'entry_prices') else "",
            "exit_price_eth": price if "ETH" in side and (is_exit or in_exit_phase) else "",
            "exit_price_sol": price if "SOL" in side and (is_exit or in_exit_phase) else "",
            "spread_bps_entry": str(getattr(self, '_entry_spread_info', {}).get('max_spread_bps', 0)),
            "spread_bps_exit": str(getattr(self, '_exit_spread_info', {}).get('max_spread_bps', 0)),
            "slippage_bps_entry": "",
            "slippage_bps_exit": "",
            "cycle_skipped": "false",
            "skip_reason": "",
            # TASK 6: WebSocket decision factors
            "eth_momentum_state": eth_momentum,
            "sol_momentum_state": sol_momentum,
            "spread_state_entry": spread_state_entry,
            "spread_state_exit": spread_state_exit,
            "entry_threshold_bps": entry_threshold,
            "exit_threshold_bps": exit_threshold,
            "exit_liquidity_available": exit_liq_avail,
            "exit_liquidity_usd": exit_liq_usd,
            "websocket_available": "true" if WEBSOCKET_AVAILABLE else "false"
        }

        # Calculate PNL if this is an exit order and we have complete data
        if (is_exit or in_exit_phase) and hasattr(self, '_exit_prices') and hasattr(self, 'entry_prices') and hasattr(self, 'current_cycle_pnl'):
            pnl_no_fee, pnl_with_fee, breakdown = self._calculate_current_pnl()
            params["pnl_no_fee"] = str(pnl_no_fee)
            params["pnl_with_fee"] = str(pnl_with_fee)
            # Note: eth_pnl and sol_pnl are in breakdown but not written to CSV

        # Set entry timestamp if available
        if hasattr(self, 'current_cycle_pnl') and self.current_cycle_pnl.get("entry_time"):
            entry_time = self.current_cycle_pnl["entry_time"]
            if isinstance(entry_time, datetime):
                params["entry_timestamp"] = entry_time.isoformat()

        return params

    def _check_spread_profitability(self, eth_bid: Decimal, eth_ask: Decimal,
                                    sol_bid: Decimal, sol_ask: Decimal) -> tuple[bool, dict]:
        """
        Check if spread is acceptable for entry.

        IMPORTANT: This is a sanity check, NOT a profitability filter.
        Verified from _calculate_current_pnl() (lines 1240-1289):
        - Profit = (exit_price - entry_price) * qty - fees
        - Profit comes from POST-ENTRY price movements, NOT entry spread
        - Exit thresholds (lines 1163-1167) enforce profitability

        Minimum spread prevents:
        - Data errors (0 or negative spreads from bad quotes)
        - Obviously poor entry conditions

        Returns:
            is_profitable: bool - True if spread >= minimum threshold
            info: dict with:
                - eth_spread_bps: ETH spread in bps
                - sol_spread_bps: SOL spread in bps
                - min_spread_bps: Minimum required spread (configurable, default 1)
                - max_spread_bps: Maximum of ETH/SOL spreads in bps
                - reason: Skip reason if not profitable
        """
        # Minimum spread is a sanity check, not a breakeven requirement
        # Verified from _calculate_current_pnl() (lines 1240-1289): profit comes from
        # (exit_price - entry_price) movements AFTER entry, NOT from entry spread
        #
        # Mode affects fees via FEE_RATE (line 390):
        # - POST_ONLY: 2 bps per leg = 8 bps total for 4 legs
        # - IOC: 5 bps per leg = 20 bps total for 4 legs
        #
        # But profitability is determined by exit conditions (lines 1163-1167), not entry spread
        MIN_SPREAD_BPS = self.min_spread_bps  # Configurable, default 1 bps

        # Calculate spreads in bps: (ask - bid) / mid_price * 10000
        eth_mid = (eth_bid + eth_ask) / 2
        eth_spread_bps = (eth_ask - eth_bid) / eth_mid * 10000 if eth_mid > 0 else 0

        sol_mid = (sol_bid + sol_ask) / 2
        sol_spread_bps = (sol_ask - sol_bid) / sol_mid * 10000 if sol_mid > 0 else 0

        # Check if either spread meets minimum threshold
        is_profitable = eth_spread_bps >= MIN_SPREAD_BPS or sol_spread_bps >= MIN_SPREAD_BPS

        # Calculate max spread for CSV logging
        max_spread_bps = max(eth_spread_bps, sol_spread_bps)

        info = {
            "eth_spread_bps": float(eth_spread_bps),
            "sol_spread_bps": float(sol_spread_bps),
            "min_spread_bps": MIN_SPREAD_BPS,
            "max_spread_bps": float(max_spread_bps),
            "reason": None if is_profitable else f"Spread below threshold: ETH={eth_spread_bps:.1f}bps, SOL={sol_spread_bps:.1f}bps < {MIN_SPREAD_BPS}bps"
        }

        return is_profitable, info

    async def _check_exit_liquidity(self, max_slippage_bps: int = 20) -> dict:
        """
        Check if there is sufficient liquidity to exit both positions.

        Args:
            max_slippage_bps: Maximum acceptable slippage in bps (default 20)

        Returns:
            dict with:
            - can_exit: bool - True if both positions can be exited
            - eth_can_exit: bool - True if ETH position can be exited
            - sol_can_exit: bool - True if SOL position can be exited
            - eth_exitable_qty: Decimal - Max exitable ETH quantity
            - sol_exitable_qty: Decimal - Max exitable SOL quantity
            - eth_liquidity_usd: Decimal - ETH liquidity available in USD
            - sol_liquidity_usd: Decimal - SOL liquidity available in USD
            - websocket_available: bool - Whether WebSocket data was used
        """
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE

        result = {
            "can_exit": True,
            "eth_can_exit": True,
            "sol_can_exit": True,
            "eth_exitable_qty": Decimal("0"),
            "sol_exitable_qty": Decimal("0"),
            "eth_liquidity_usd": Decimal("0"),
            "sol_liquidity_usd": Decimal("0"),
            "websocket_available": WEBSOCKET_AVAILABLE
        }

        # Get current positions
        eth_qty = self.entry_quantities.get("ETH", Decimal("0"))
        sol_qty = self.entry_quantities.get("SOL", Decimal("0"))

        if eth_qty == 0 and sol_qty == 0:
            return result  # No positions to exit

        # Check ETH liquidity (long position needs to sell)
        if eth_qty > 0:
            try:
                eth_handler = self.eth_client.get_bookdepth_handler()
                if eth_handler is not None:
                    # Use BookDepth for accurate liquidity check
                    can_exit, exitable_qty = eth_handler.estimate_exit_capacity(
                        eth_qty, max_slippage_bps
                    )
                    result["eth_can_exit"] = can_exit
                    result["eth_exitable_qty"] = exitable_qty

                    # Calculate liquidity available in USD
                    eth_price = self.entry_prices.get("ETH", Decimal("0"))
                    if eth_price > 0:
                        liq = await self.eth_client.get_available_liquidity("ask", max_depth=20)
                        result["eth_liquidity_usd"] = liq * eth_price
                else:
                    # WebSocket fallback - assume sufficient liquidity
                    result["eth_can_exit"] = True
                    result["eth_exitable_qty"] = eth_qty
                    self.logger.warning(
                        "[LIQUIDITY] ETH BookDepth unavailable, assuming sufficient liquidity"
                    )
            except Exception as e:
                self.logger.warning(f"[LIQUIDITY] Error checking ETH liquidity: {e}")
                result["eth_can_exit"] = True  # Conservative: allow exit

        # Check SOL liquidity (short position needs to buy)
        if sol_qty > 0:
            try:
                sol_handler = self.sol_client.get_bookdepth_handler()
                if sol_handler is not None:
                    # Use BookDepth for accurate liquidity check
                    can_exit, exitable_qty = sol_handler.estimate_exit_capacity(
                        sol_qty, max_slippage_bps
                    )
                    result["sol_can_exit"] = can_exit
                    result["sol_exitable_qty"] = exitable_qty

                    # Calculate liquidity available in USD
                    sol_price = self.entry_prices.get("SOL", Decimal("0"))
                    if sol_price > 0:
                        liq = await self.sol_client.get_available_liquidity("bid", max_depth=20)
                        result["sol_liquidity_usd"] = liq * sol_price
                else:
                    # WebSocket fallback - assume sufficient liquidity
                    result["sol_can_exit"] = True
                    result["sol_exitable_qty"] = sol_qty
                    self.logger.warning(
                        "[LIQUIDITY] SOL BookDepth unavailable, assuming sufficient liquidity"
                    )
            except Exception as e:
                self.logger.warning(f"[LIQUIDITY] Error checking SOL liquidity: {e}")
                result["sol_can_exit"] = True  # Conservative: allow exit

        # Overall exit decision
        result["can_exit"] = result["eth_can_exit"] and result["sol_can_exit"]

        # Log warnings if insufficient liquidity
        if not result["can_exit"]:
            if not result["eth_can_exit"]:
                self.logger.warning(
                    f"[LIQUIDITY] INSUFFICIENT ETH liquidity: "
                    f"need {eth_qty}, can exit {result['eth_exitable_qty']}"
                )
            if not result["sol_can_exit"]:
                self.logger.warning(
                    f"[LIQUIDITY] INSUFFICIENT SOL liquidity: "
                    f"need {sol_qty}, can exit {result['sol_exitable_qty']}"
                )

        return result

    def _check_momentum_filter(self, eth_direction: str, sol_direction: str) -> tuple[bool, str]:
        """Check momentum filter for entry conditions.

        For Long ETH/Short SOL: skip if ETH BEARISH OR SOL BULLISH
        For Short ETH/Long SOL: skip if ETH BULLISH OR SOL BEARISH

        Args:
            eth_direction: Order side for ETH ("buy" or "sell")
            sol_direction: Order side for SOL ("buy" or "sell")

        Returns:
            (should_enter, reason) where reason explains why skipped or "OK"
        """
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE

        # Get momentum from BBO handler with null checks
        eth_momentum = None
        sol_momentum = None

        try:
            if self.eth_client and self.eth_client.get_bbo_handler():
                eth_momentum = self.eth_client.get_bbo_handler().get_momentum()
        except Exception as e:
            self.logger.warning(f"[MOMENTUM] Error getting ETH momentum: {e}")

        try:
            if self.sol_client and self.sol_client.get_bbo_handler():
                sol_momentum = self.sol_client.get_bbo_handler().get_momentum()
        except Exception as e:
            self.logger.warning(f"[MOMENTUM] Error getting SOL momentum: {e}")

        # Log WebSocket fallback if momentum unavailable
        if eth_momentum is None or sol_momentum is None:
            if not WEBSOCKET_AVAILABLE:
                self.logger.warning(
                    f"[MOMENTUM] WebSocket unavailable - using REST fallback "
                    f"(ETH momentum: {eth_momentum}, SOL momentum: {sol_momentum})"
                )
            else:
                self.logger.warning(
                    f"[MOMENTUM] BBO data not yet available - skipping momentum check "
                    f"(ETH: {eth_momentum}, SOL: {sol_momentum})"
                )
            # Allow entry if momentum data unavailable (conservative approach)
            return True, "momentum_unavailable"

        # Apply momentum filter based on direction
        # Long ETH/Short SOL: want ETH BULLISH AND SOL not BULLISH
        if eth_direction == "buy" and sol_direction == "sell":
            if eth_momentum == "BEARISH":
                return False, f"ETH momentum BEARISH (want BULLISH for Long)"
            if sol_momentum == "BULLISH":
                return False, f"SOL momentum BULLISH (want not BULLISH for Short)"

        # Short ETH/Long SOL: want ETH BEARISH AND SOL not BEARISH
        elif eth_direction == "sell" and sol_direction == "buy":
            if eth_momentum == "BULLISH":
                return False, f"ETH momentum BULLISH (want BEARISH for Short)"
            if sol_momentum == "BEARISH":
                return False, f"SOL momentum BEARISH (want not BEARISH for Long)"

        self.logger.info(
            f"[MOMENTUM] Check passed: ETH={eth_momentum}, SOL={sol_momentum}"
        )
        return True, "OK"

    def _calculate_dynamic_exit_thresholds(self) -> dict:
        """Calculate dynamic exit thresholds based on BBO spread state.

        Uses BBO spread state (WIDENING/NARROWING/STABLE) to adjust:
        - WIDENING: profit_target 15->25 bps, stop_loss -30->-40 bps (wider exits)
        - NARROWING: profit_target 15->10 bps (quick exit)
        - STABLE: keep default (15/5/-30)

        Returns:
            dict with:
            - profit_target_bps: int - profit target in basis points
            - quick_exit_bps: int - small profit threshold in basis points
            - stop_loss_bps: int - maximum loss in basis points
            - websocket_available: bool - whether WebSocket is active
            - spread_state: str - current spread state (or None if unavailable)
        """
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE

        # Fee-aware profit targets (remaining fees only)
        # Entry fees ALREADY PAID: 10 bps (IOC) or 4 bps (POST_ONLY)
        # Exit fees REMAINING: 10 bps (IOC) or 4 bps (POST_ONLY)
        remaining_exit_fees_bps = 10 if not self.use_post_only else 4

        BASE_PROFIT = 15
        MIN_NET_PROFIT = 5

        profit_target = BASE_PROFIT + remaining_exit_fees_bps  # 25 for IOC, 19 for POST_ONLY
        quick_exit = MIN_NET_PROFIT + remaining_exit_fees_bps  # 15 for IOC, 9 for POST_ONLY
        stop_loss = 30  # Stop loss remains absolute

        self.logger.info(
            f"[EXIT] Fee-aware thresholds: profit_target={profit_target}bps, "
            f"quick_exit={quick_exit}bps (remaining_exit_fees={remaining_exit_fees_bps}bps)"
        )

        spread_state = None

        # Get spread state from ETH BBO handler (primary)
        try:
            if self.eth_client and self.eth_client.get_bbo_handler():
                spread_state = self.eth_client.get_bbo_handler().get_spread_state()
        except Exception as e:
            self.logger.warning(f"[EXIT] Error getting spread state: {e}")

        # Adjust thresholds based on spread state
        if spread_state == "WIDENING":
            # Widening spread: extend profit target, widen stop loss
            profit_target = 25
            stop_loss = 40
            self.logger.info(
                f"[EXIT] SPREAD WIDENING: extended thresholds "
                f"(profit: {profit_target}bps, stop: -{stop_loss}bps)"
            )
        elif spread_state == "NARROWING":
            # Narrowing spread: quick exit at lower profit target
            profit_target = 10
            self.logger.info(
                f"[EXIT] SPREAD NARROWING: quick exit "
                f"(profit: {profit_target}bps, stop: -{stop_loss}bps)"
            )
        else:
            # STABLE or None: use defaults
            if spread_state != "STABLE" and spread_state is not None:
                self.logger.warning(f"[EXIT] Unknown spread state: {spread_state}, using defaults")
            else:
                self.logger.info(
                    f"[EXIT] SPREAD {spread_state or 'STABLE'}: default thresholds "
                    f"(profit: {profit_target}bps, stop: -{stop_loss}bps)"
                )

        # Log WebSocket fallback if needed
        if not WEBSOCKET_AVAILABLE:
            self.logger.warning(
                f"[EXIT] WebSocket unavailable - using REST fallback with default thresholds"
            )

        return {
            "profit_target_bps": profit_target,
            "quick_exit_bps": quick_exit,
            "stop_loss_bps": stop_loss,
            "websocket_available": WEBSOCKET_AVAILABLE,
            "spread_state": spread_state
        }

    def _log_skipped_cycle(self, reason: str):
        """Log a skipped cycle to CSV."""
        csv_params = self._prepare_csv_params(
            exchange="NADO",
            side="SKIP",
            price="0",
            quantity="0",
            order_type="skip",
            mode="SKIPPED",
            fee_usd="0",
            is_exit=False
        )
        csv_params["cycle_skipped"] = "true"
        csv_params["skip_reason"] = reason
        self.log_trade_to_csv(**csv_params)

    def _calculate_current_pnl(self) -> tuple[Decimal, Decimal, dict]:
        """
        Calculate current cycle PNL with detailed breakdown.

        Returns:
            (pnl_no_fee, pnl_with_fee, breakdown_dict)
            breakdown_dict contains:
            - eth_pnl: ETH position PNL
            - sol_pnl: SOL position PNL
            - total_fees: All fees paid
            - funding_pnl: Funding PNL correction (V5.4)
            - eth_entry_price, eth_exit_price
            - sol_entry_price, sol_exit_price
            - eth_qty, sol_qty
        """
        try:
            eth_entry_price = self.entry_prices.get("ETH", Decimal("0")) or Decimal("0")
            sol_entry_price = self.entry_prices.get("SOL", Decimal("0")) or Decimal("0")
            eth_entry_qty = self.entry_quantities.get("ETH", Decimal("0"))
            sol_entry_qty = self.entry_quantities.get("SOL", Decimal("0"))

            # Validate we have entry data
            if eth_entry_price == 0 or sol_entry_price == 0:
                self.logger.warning("[PNL] Missing entry prices for PNL calculation")
                return Decimal("0"), Decimal("0"), {}

            # Get exit prices (stored during UNWIND)
            if not hasattr(self, '_exit_prices'):
                self.logger.warning("[PNL] No exit prices available yet")
                return Decimal("0"), Decimal("0"), {}

            eth_exit_price = self._exit_prices.get("ETH", eth_entry_price)
            sol_exit_price = self._exit_prices.get("SOL", sol_entry_price)

            # Calculate ETH PNL (Long: exit - entry)
            eth_pnl = (eth_exit_price - eth_entry_price) * eth_entry_qty

            # Calculate SOL PNL (Short: entry - exit)
            sol_pnl = (sol_entry_price - sol_exit_price) * sol_entry_qty

            # Total PNL without fees
            pnl_no_fee = eth_pnl + sol_pnl

            # Total fees paid
            total_fees = self.current_cycle_pnl.get("total_fees", Decimal("0"))

            # PNL with fees (before funding correction)
            pnl_with_fee = pnl_no_fee - total_fees

            # V5.4: Add funding PNL correction
            funding_pnl = Decimal("0")
            entry_time = self.current_cycle_pnl.get("entry_time")
            exit_time = self.current_cycle_pnl.get("exit_time")

            if entry_time and exit_time:
                # Calculate hold time in hours
                hold_seconds = (exit_time - entry_time).total_seconds()
                hold_hours = Decimal(str(hold_seconds / 3600))

                # Calculate funding PNL (synchronous version for compatibility)
                # Note: This is a simplified calculation; full async version requires call from unwind
                try:
                    eth_value = eth_entry_price * eth_entry_qty
                    sol_value = sol_entry_price * sol_entry_qty

                    # Use conservative funding rate estimate (1% annual)
                    # In production, this should use the actual async method
                    eth_funding_rate = Decimal("0.01")
                    sol_funding_rate = Decimal("0.01")

                    # CORRECTED FORMULA: / 3 for 8-hour funding interval
                    eth_hourly_funding = eth_value * eth_funding_rate / Decimal("365") / Decimal("3")
                    sol_hourly_funding = sol_value * sol_funding_rate / Decimal("365") / Decimal("3")

                    funding_pnl = (eth_hourly_funding + sol_hourly_funding) * hold_hours

                    self.logger.info(
                        f"[FUNDING] Estimated funding PNL: ${funding_pnl:.4f} for {hold_hours:.2f}h"
                    )
                except Exception as e:
                    self.logger.warning(f"[FUNDING] Error estimating funding PNL: {e}")

            # Final PNL with funding correction
            pnl_with_fee += funding_pnl

            # Store in current cycle state
            self.current_cycle_pnl["pnl_no_fee"] = pnl_no_fee
            self.current_cycle_pnl["pnl_with_fee"] = pnl_with_fee
            self.current_cycle_pnl["funding_pnl"] = funding_pnl

            breakdown = {
                "eth_pnl": float(eth_pnl),
                "sol_pnl": float(sol_pnl),
                "total_fees": float(total_fees),
                "funding_pnl": float(funding_pnl),
                "eth_entry_price": float(eth_entry_price),
                "eth_exit_price": float(eth_exit_price),
                "sol_entry_price": float(sol_entry_price),
                "sol_exit_price": float(sol_exit_price),
                "eth_qty": float(eth_entry_qty),
                "sol_qty": float(sol_entry_qty)
            }

            return pnl_no_fee, pnl_with_fee, breakdown

        except Exception as e:
            self.logger.error(f"[PNL] Error calculating PNL: {e}")
            return Decimal("0"), Decimal("0"), {}

    def _check_cumulative_pnl_health(self) -> tuple[bool, str]:
        """
        Check if cumulative PNL indicates strategy issues.

        Risk mitigation for relaxed entry filter:
        - If first 3 cycles unprofitable, may need to adjust min_spread_bps
        - Stop if cumulative loss exceeds threshold

        Returns:
            (is_healthy, message): tuple of health status and explanation
        """
        total_cycles = self.daily_pnl_summary.get("total_cycles", 0)
        total_pnl = self.daily_pnl_summary.get("total_pnl_with_fee", Decimal("0"))
        losing_cycles = self.daily_pnl_summary.get("losing_cycles", 0)

        # Risk threshold: $50 maximum cumulative loss
        MAX_CUMULATIVE_LOSS = Decimal("50")

        # Check cumulative loss
        if total_pnl < -MAX_CUMULATIVE_LOSS:
            return False, f"Cumulative loss ${-total_pnl:.2f} exceeds threshold ${MAX_CUMULATIVE_LOSS}"

        # Check if first 3 cycles are all unprofitable
        if 3 <= total_cycles <= 5 and losing_cycles == total_cycles:
            return False, f"First {total_cycles} cycles all unprofitable - consider increasing min_spread_bps to 2-3"

        # Check win rate after 10 cycles
        if total_cycles >= 10:
            win_rate = (total_cycles - losing_cycles) / total_cycles
            if win_rate < 0.3:
                return False, f"Win rate {win_rate*100:.0f}% below 30% after {total_cycles} cycles"

        return True, "Cumulative PNL within acceptable range"

    def _update_daily_pnl_summary(self):
        """Update daily PNL summary with completed cycle data."""
        try:
            if not hasattr(self, 'current_cycle_pnl'):
                return

            pnl_no_fee = self.current_cycle_pnl.get("pnl_no_fee", Decimal("0"))
            pnl_with_fee = self.current_cycle_pnl.get("pnl_with_fee", Decimal("0"))
            total_fees = self.current_cycle_pnl.get("total_fees", Decimal("0"))

            # Increment total cycles
            self.daily_pnl_summary["total_cycles"] += 1

            # Update best/worst cycle PNL
            if pnl_with_fee > self.daily_pnl_summary["best_cycle_pnl"]:
                self.daily_pnl_summary["best_cycle_pnl"] = pnl_with_fee
            if pnl_with_fee < self.daily_pnl_summary["worst_cycle_pnl"]:
                self.daily_pnl_summary["worst_cycle_pnl"] = pnl_with_fee

            # Count profitable vs losing cycles
            if pnl_with_fee > 0:
                self.daily_pnl_summary["profitable_cycles"] += 1
            elif pnl_with_fee < 0:
                self.daily_pnl_summary["losing_cycles"] += 1

            # Accumulate totals
            self.daily_pnl_summary["total_pnl_no_fee"] += pnl_no_fee
            self.daily_pnl_summary["total_pnl_with_fee"] += pnl_with_fee
            self.daily_pnl_summary["total_fees"] += total_fees

            # Log cycle summary
            self.logger.info(
                f"[CYCLE {self.cycle_id}] PNL Summary: "
                f"NoFee=${pnl_no_fee:.2f}, WithFee=${pnl_with_fee:.2f}, "
                f"Fees=${total_fees:.2f}"
            )

            # Record cycle results to rollback monitor
            # Calculate PNL in bps (basis points)
            # Position value = target_notional * 2 (ETH + SOL positions)
            position_value = float(self.target_notional * 2)
            if position_value > 0:
                pnl_bps = (float(pnl_with_fee) / position_value) * 10000
            else:
                pnl_bps = 0.0

            self.rollback_monitor.record_cycle(
                had_safety_stop=getattr(self, '_had_safety_stop', False),
                pnl_bps=pnl_bps
            )
            self.logger.info(
                f"[ROLLBACK] Cycle recorded: safety_stop={self._had_safety_stop}, "
                f"pnl_bps={pnl_bps:.2f}"
            )

            # Generate daily PNL report after each cycle
            self._generate_daily_pnl_report()

        except Exception as e:
            self.logger.error(f"[PNL] Error updating daily summary: {e}")

    def _log_final_cycle_pnl(self):
        """Log final cycle PNL after UNWIND completes."""
        if not hasattr(self, 'current_cycle_pnl'):
            return

        pnl_no_fee = self.current_cycle_pnl.get("pnl_no_fee", Decimal("0"))
        pnl_with_fee = self.current_cycle_pnl.get("pnl_with_fee", Decimal("0"))
        total_fees = self.current_cycle_pnl.get("total_fees", Decimal("0"))

        self.logger.info(
            f"[PNL] Cycle {self.cycle_id} Final: "
            f"NoFee=${pnl_no_fee:.2f}, WithFee=${pnl_with_fee:.2f}, Fees=${total_fees:.2f}"
        )

        # Log detailed breakdown if available
        if hasattr(self, '_pnl_breakdown') and self._pnl_breakdown:
            self.logger.info(
                f"[PNL] Breakdown: "
                f"ETH=${self._pnl_breakdown.get('eth_pnl', 0):.2f}, "
                f"SOL=${self._pnl_breakdown.get('sol_pnl', 0):.2f}"
            )

    async def _log_realtime_pnl(self):
        """
        Log unrealized PNL based on current market prices.
        Called periodically during position hold.
        """
        if not hasattr(self, 'entry_prices') or not self.entry_prices.get("ETH"):
            return  # No position open

        try:
            # Get current prices
            eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
            sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

            eth_entry_price = self.entry_prices.get("ETH", Decimal("0"))
            sol_entry_price = self.entry_prices.get("SOL", Decimal("0"))
            eth_qty = self.entry_quantities.get("ETH", Decimal("0"))
            sol_qty = self.entry_quantities.get("SOL", Decimal("0"))

            # Calculate unrealized PNL
            # ETH Long: would exit at bid
            eth_unrealized = (eth_bid - eth_entry_price) * eth_qty
            # SOL Short: would exit at ask
            sol_unrealized = (sol_entry_price - sol_ask) * sol_qty

            total_unrealized = eth_unrealized + sol_unrealized

            self.logger.info(
                f"[PNL] Real-time: ETH=${eth_unrealized:.2f}, SOL=${sol_unrealized:.2f}, "
                f"Total=${total_unrealized:.2f} (unrealized)"
            )

        except Exception as e:
            self.logger.error(f"[PNL] Error logging real-time PNL: {e}")

    def _generate_daily_pnl_report(self) -> dict:
        """
        Generate daily PNL report from accumulated statistics.

        Returns:
            dict with daily summary metrics
        """
        summary = self.daily_pnl_summary
        total_cycles = summary.get("total_cycles", 0)

        if total_cycles == 0:
            self.logger.info("[REPORT] No cycles completed today")
            return {}

        profitable_cycles = summary.get("profitable_cycles", 0)
        losing_cycles = summary.get("losing_cycles", 0)
        total_pnl = summary.get("total_pnl_with_fee", Decimal("0"))
        total_fees = summary.get("total_fees", Decimal("0"))
        best_pnl = summary.get("best_cycle_pnl", Decimal("0"))
        worst_pnl = summary.get("worst_cycle_pnl", Decimal("0"))

        # Calculate metrics
        win_rate = (profitable_cycles / total_cycles * 100) if total_cycles > 0 else 0
        avg_pnl = (total_pnl / total_cycles) if total_cycles > 0 else Decimal("0")

        report = {
            "total_cycles": total_cycles,
            "profitable_cycles": profitable_cycles,
            "losing_cycles": losing_cycles,
            "win_rate_pct": float(win_rate),
            "total_pnl_with_fee": float(total_pnl),
            "total_fees": float(total_fees),
            "avg_pnl_per_cycle": float(avg_pnl),
            "best_cycle_pnl": float(best_pnl),
            "worst_cycle_pnl": float(worst_pnl)
        }

        self.logger.info(
            f"[REPORT] ===== DAILY PNL SUMMARY =====\n"
            f"  Total Cycles: {total_cycles}\n"
            f"  Win Rate: {win_rate:.1f}% ({profitable_cycles}W / {losing_cycles}L)\n"
            f"  Total PNL: ${total_pnl:.2f}\n"
            f"  Total Fees: ${total_fees:.2f}\n"
            f"  Avg PNL/Cycle: ${avg_pnl:.2f}\n"
            f"  Best Cycle: ${best_pnl:.2f}\n"
            f"  Worst Cycle: ${worst_pnl:.2f}\n"
            f"================================"
        )

        return report

    def _initialize_spread_analysis_csv(self):
        """Initialize spread/slippage analysis CSV file."""
        filename = "logs/DN_pair_spread_slippage_analysis.csv"

        if not os.path.exists(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "cycle_id",
                    "timestamp",
                    "eth_spread_bps_entry",
                    "sol_spread_bps_entry",
                    "eth_spread_bps_exit",
                    "sol_spread_bps_exit",
                    "eth_slippage_bps_actual",
                    "sol_slippage_bps_actual",
                    "pnl_with_fee"
                ])

        return filename

    def _log_spread_analysis(self, spread_info_entry: dict, spread_info_exit: dict = None):
        """Log spread and slippage data to analysis CSV."""
        filename = self._initialize_spread_analysis_csv()

        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.cycle_id,
                datetime.now(pytz.UTC).isoformat(),
                spread_info_entry.get("eth_spread_bps", ""),
                spread_info_entry.get("sol_spread_bps", ""),
                spread_info_exit.get("eth_spread_bps", "") if spread_info_exit else "",
                spread_info_exit.get("sol_spread_bps", "") if spread_info_exit else "",
                "",  # Actual slippage (from OrderResult)
                "",  # Actual slippage (from OrderResult)
                float(self.current_cycle_pnl.get("pnl_with_fee", Decimal("0")))
            ])

    async def _wait_for_optimal_entry(self, timeout: int = 30, eth_direction: str = "buy", sol_direction: str = "sell") -> dict:
        """
        Wait for optimal entry timing based on BBO momentum and spread state.

        Uses dynamic thresholds based on market conditions:
        - FAVORABLE (ETH BULLISH + SOL BEARISH): enter at 18 bps
        - ADVERSE: wait for 30 bps
        - WebSocket fallback: default 25 bps

        Args:
            timeout: Maximum seconds to wait (default 30)
            eth_direction: Order side for ETH ("buy" or "sell")
            sol_direction: Order side for SOL ("buy" or "sell")

        Returns:
            dict with timing metrics including dynamic threshold used
        """
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE

        start_time = time.time()
        best_spread = None
        best_spread_time = None

        # Determine dynamic threshold based on momentum and spread state
        dynamic_threshold = 25  # Default fallback
        threshold_reason = "default"

        # Get momentum states
        eth_momentum = None
        sol_momentum = None
        spread_state = None

        try:
            if self.eth_client and self.eth_client.get_bbo_handler():
                eth_momentum = self.eth_client.get_bbo_handler().get_momentum()
                spread_state = self.eth_client.get_bbo_handler().get_spread_state()
        except Exception:
            pass

        try:
            if self.sol_client and self.sol_client.get_bbo_handler():
                sol_momentum = self.sol_client.get_bbo_handler().get_momentum()
        except Exception:
            pass

        # TASK 4: Calculate dynamic entry threshold
        if eth_momentum and sol_momentum:
            # Long ETH/Short SOL: favorable = ETH BULLISH + SOL BEARISH
            if eth_direction == "buy" and sol_direction == "sell":
                if eth_momentum == "BULLISH" and sol_momentum == "BEARISH":
                    # FAVORABLE: lower threshold to enter quickly
                    dynamic_threshold = 18
                    threshold_reason = "favorable_momentum"
                elif eth_momentum == "BEARISH" or sol_momentum == "BULLISH":
                    # ADVERSE: higher threshold to wait for better conditions
                    dynamic_threshold = 30
                    threshold_reason = "adverse_momentum"
                else:
                    # NEUTRAL: use default
                    dynamic_threshold = 25
                    threshold_reason = "neutral_momentum"

            # Short ETH/Long SOL: favorable = ETH BEARISH + SOL BULLISH
            elif eth_direction == "sell" and sol_direction == "buy":
                if eth_momentum == "BEARISH" and sol_momentum == "BULLISH":
                    dynamic_threshold = 18
                    threshold_reason = "favorable_momentum"
                elif eth_momentum == "BULLISH" or sol_momentum == "BEARISH":
                    dynamic_threshold = 30
                    threshold_reason = "adverse_momentum"
                else:
                    dynamic_threshold = 25
                    threshold_reason = "neutral_momentum"

        # Store for CSV logging (TASK 6)
        self._eth_momentum_state = eth_momentum or "unknown"
        self._sol_momentum_state = sol_momentum or "unknown"
        self._spread_state_entry = spread_state or "unknown"
        self._entry_threshold_bps = dynamic_threshold

        self.logger.info(
            f"[ENTRY] Dynamic threshold: {dynamic_threshold} bps "
            f"(reason={threshold_reason}, ETH={eth_momentum}, SOL={sol_momentum}, "
            f"spread={spread_state}, WS={'YES' if WEBSOCKET_AVAILABLE else 'NO'})"
        )

        self.logger.info(f"[ENTRY] Monitoring BBO for optimal entry (timeout={timeout}s)")

        while time.time() - start_time < timeout:
            eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
            sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

            is_profitable, spread_info = self._check_spread_profitability(eth_bid, eth_ask, sol_bid, sol_ask)

            if is_profitable:
                current_spread = max(spread_info["eth_spread_bps"], spread_info["sol_spread_bps"])

                if best_spread is None or current_spread > best_spread:
                    best_spread = current_spread
                    best_spread_time = time.time()

                # Enter immediately if spread meets dynamic threshold
                if current_spread >= dynamic_threshold:
                    self.logger.info(
                        f"[ENTRY] Optimal spread detected: {current_spread:.1f}bps "
                        f"(threshold={dynamic_threshold}bps)"
                    )
                    return {
                        "waited_seconds": time.time() - start_time,
                        "entry_spread_bps": current_spread,
                        "reason": "optimal_spread",
                        "threshold_bps": dynamic_threshold,
                        "threshold_reason": threshold_reason
                    }

            await asyncio.sleep(1)  # Check every second

        # Timeout: use best spread seen or current
        elapsed = time.time() - start_time
        entry_spread = best_spread or 20

        self.logger.info(
            f"[ENTRY] Timeout after {elapsed:.1f}s, entering with {entry_spread:.1f}bps spread "
            f"(threshold was {dynamic_threshold}bps)"
        )
        return {
            "waited_seconds": elapsed,
            "entry_spread_bps": entry_spread,
            "reason": "timeout",
            "threshold_bps": dynamic_threshold,
            "threshold_reason": threshold_reason
        }

    async def _check_exit_timing(self, max_loss_bps: int = None) -> tuple[bool, str]:
        """
        Check if current timing is good for exit using dynamic thresholds.

        Args:
            max_loss_bps: Optional override for maximum loss in bps (uses dynamic if None)

        Returns:
            (should_exit, reason)
        """
        if not hasattr(self, 'entry_prices') or not self.entry_prices.get("ETH"):
            return True, "no_position"

        # Get dynamic exit thresholds based on BBO spread state (V5.5)
        thresholds = self._calculate_dynamic_exit_thresholds()
        profit_target = thresholds["profit_target_bps"]
        quick_exit = thresholds["quick_exit_bps"]
        stop_loss = max_loss_bps if max_loss_bps is not None else thresholds["stop_loss_bps"]
        spread_state = thresholds["spread_state"]

        self.logger.info(
            f"[EXIT] Using dynamic thresholds: profit={profit_target}bps, "
            f"quick_exit={quick_exit}bps, stop_loss={stop_loss}bps "
            f"(spread_state={spread_state})"
        )

        # Calculate unrealized PNL
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

        eth_entry_price = self.entry_prices.get("ETH", Decimal("0"))
        sol_entry_price = self.entry_prices.get("SOL", Decimal("0"))
        eth_qty = self.entry_quantities.get("ETH", Decimal("0"))
        sol_qty = self.entry_quantities.get("SOL", Decimal("0"))

        eth_unrealized = (eth_bid - eth_entry_price) * eth_qty
        sol_unrealized = (sol_entry_price - sol_ask) * sol_qty
        total_unrealized = eth_unrealized + sol_unrealized

        # Calculate position value for PNL%
        position_value = (eth_entry_price * eth_qty) + (sol_entry_price * sol_qty)
        if position_value == 0:
            return True, "no_position"

        pnl_bps = (total_unrealized / position_value) * 10000

        # Stop loss: exit if losing more than stop_loss
        if pnl_bps < -stop_loss:
            return True, f"stop_loss_{pnl_bps:.1f}bps"

        # Profit target: exit if profitable enough (dynamic threshold)
        if pnl_bps > profit_target:
            return True, f"profit_target_{pnl_bps:.1f}bps"

        # Neutral: wait or exit
        if pnl_bps > quick_exit:  # Small profit, exit now (dynamic threshold)
            return True, f"small_profit_{pnl_bps:.1f}bps"

        # Small loss: wait for better
        return False, f"waiting_{pnl_bps:.1f}bps"

    async def _fetch_funding_rate_rest(self, contract_id: int, ticker: str) -> Decimal:
        """
        Fetch current funding rate via REST API.

        Args:
            contract_id: Contract ID for funding rate
            ticker: "ETH" or "SOL" to select appropriate client

        Returns:
            Funding rate as Decimal (e.g., 0.10 for 10% annual)

        Note: Uses conservative fallback (0.01 = 1%) if API unavailable
        """
        try:
            # Select appropriate client
            client = self.eth_client if ticker == "ETH" else self.sol_client

            # TODO: V5.4에서 WebSocket funding_rate handler 구현 예정
            # REST API endpoint to get current funding rate
            # Actual SDK method needs confirmation
            funding_data = client.client.market.get_funding_rate(product_id=int(contract_id))
            return Decimal(str(funding_data.rate))
        except Exception as e:
            self.logger.warning(f"[FUNDING] Could not fetch funding rate for {ticker}: {e}")
            # Conservative estimate: 1% annual rate
            return Decimal("0.01")

    async def _calculate_funding_pnl(self, hold_hours: Decimal) -> Decimal:
        """
        Calculate funding PNL correction for the cycle.

        Args:
            hold_hours: Time position was held (in hours)

        Returns:
            Funding PNL in USD (positive = received, negative = paid)

        Note: Uses CORRECTED formula with /3 for 8-hour funding interval
        """
        try:
            # Get position values
            eth_entry_price = self.entry_prices.get("ETH", Decimal("0"))
            sol_entry_price = self.entry_prices.get("SOL", Decimal("0"))
            eth_qty = self.entry_quantities.get("ETH", Decimal("0"))
            sol_qty = self.entry_quantities.get("SOL", Decimal("0"))

            eth_value = eth_entry_price * eth_qty
            sol_value = sol_entry_price * sol_qty

            # Fetch funding rates
            eth_contract_id = self.eth_client.config.contract_id
            sol_contract_id = self.sol_client.config.contract_id

            eth_funding_rate = await self._fetch_funding_rate_rest(eth_contract_id, "ETH")
            sol_funding_rate = await self._fetch_funding_rate_rest(sol_contract_id, "SOL")

            # CORRECTED FORMULA: / 3 for 8-hour funding interval
            # Position_Value * Annual_Rate / 365 / 3 (per 8-hour interval)
            eth_hourly_funding = eth_value * eth_funding_rate / Decimal("365") / Decimal("3")
            sol_hourly_funding = sol_value * sol_funding_rate / Decimal("365") / Decimal("3")

            # Total funding for hold time
            total_funding_pnl = (eth_hourly_funding + sol_hourly_funding) * hold_hours

            self.logger.info(
                f"[FUNDING] ETH: ${eth_hourly_funding:.4f}/h, SOL: ${sol_hourly_funding:.4f}/h, "
                f"Total: ${total_funding_pnl:.4f} for {hold_hours}h"
            )

            return total_funding_pnl

        except Exception as e:
            self.logger.error(f"[FUNDING] Error calculating funding PNL: {e}")
            return Decimal("0")

    async def check_queue_size(
        self,
        client,
        direction: str,
        max_queue_ratio: float = 0.5
    ) -> Tuple[bool, Decimal, str]:
        """
        Check if queue size at touch is acceptable.

        Args:
            client: NadoClient instance
            direction: "buy" or "sell"
            max_queue_ratio: Maximum queue size as ratio of average (default 0.5)

        Returns:
            Tuple of (can_trade, queue_size, reason)
        """
        handler = client.get_bookdepth_handler()
        if handler is None:
            return True, Decimal('0'), "No BookDepth data"

        # Get queue size at touch
        if direction == 'buy':
            best_price, queue_size = handler.get_best_ask()
            side = "ask"
        else:
            best_price, queue_size = handler.get_best_bid()
            side = "bid"

        if queue_size is None or queue_size == 0:
            return False, Decimal('0'), f"No {side} liquidity"

        # Calculate average queue size (top 5 levels)
        total_liquidity = handler.get_available_liquidity(side, max_depth=5)
        avg_queue_size = total_liquidity / 5 if total_liquidity > 0 else Decimal('0')

        # Check if current queue is too deep
        if avg_queue_size > 0:
            queue_ratio = queue_size / avg_queue_size
            if queue_ratio > max_queue_ratio:
                return False, queue_size, f"Queue too deep: {queue_size} ({queue_ratio:.1%} of avg)"

        return True, queue_size, "OK"

    async def execute_build_cycle(self, eth_direction: str = "buy", sol_direction: str = "sell") -> bool:
        """Execute BUILD cycle with specified directions.

        Args:
            eth_direction: Order side for ETH ("buy" or "sell")
            sol_direction: Order side for SOL ("buy" or "sell")

        Returns:
            True if both orders filled successfully, False otherwise.
        """
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

        # TASK 4: OPTIMAL ENTRY TIMING with dynamic thresholds (V5.6)
        entry_timing = await self._wait_for_optimal_entry(
            timeout=30,
            eth_direction=eth_direction,
            sol_direction=sol_direction
        )
        self.logger.info(
            f"[BUILD] Entry timing: waited {entry_timing['waited_seconds']:.1f}s, "
            f"spread={entry_timing['entry_spread_bps']:.1f}bps, "
            f"threshold={entry_timing.get('threshold_bps', 25)}bps, "
            f"reason={entry_timing['reason']}"
        )

        # SPREAD FILTER: Check if spread is profitable
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

        is_profitable, spread_info = self._check_spread_profitability(eth_bid, eth_ask, sol_bid, sol_ask)

        if not is_profitable:
            self.logger.warning(f"[BUILD] SPREAD FILTER SKIP: {spread_info['reason']}")
            # Log skipped cycle to CSV
            self._log_skipped_cycle(spread_info['reason'])
            return False

        self.logger.info(f"[BUILD] SPREAD CHECK PASS: ETH={spread_info['eth_spread_bps']:.1f}bps, SOL={spread_info['sol_spread_bps']:.1f}bps")

        # MOMENTUM FILTER: Check momentum alignment (V5.5)
        should_enter, momentum_reason = self._check_momentum_filter(eth_direction, sol_direction)

        if not should_enter:
            self.logger.warning(f"[BUILD] MOMENTUM FILTER SKIP: {momentum_reason}")
            # Log skipped cycle to CSV
            self._log_skipped_cycle(f"MOMENTUM: {momentum_reason}")
            return False

        self.logger.info(f"[BUILD] MOMENTUM CHECK PASS: {momentum_reason}")

        # Store entry spread info for later logging
        self._entry_spread_info = spread_info

        try:
            # Store entry phase flag for PNL tracking
            self._is_entry_phase = True
            eth_result, sol_result = await self.place_simultaneous_orders(eth_direction, sol_direction)
            self._is_entry_phase = False

            # Check if orders were skipped due to insufficient liquidity
            if (isinstance(eth_result, OrderResult) and not eth_result.success and
                eth_result.error_message and "Skipped:" in eth_result.error_message):
                self.logger.warning(f"[BUILD] LIQUIDITY SKIP: {eth_result.error_message}")
                # Log skipped cycle to CSV
                self._log_skipped_cycle(f"LIQUIDITY: {eth_result.error_message}")
                return False

            # Log spread analysis at entry if orders succeeded
            if (isinstance(eth_result, OrderResult) and eth_result.success and
                isinstance(sol_result, OrderResult) and sol_result.success):
                try:
                    self._log_spread_analysis(spread_info)
                except Exception as e:
                    self.logger.error(f"[CSV] Error logging spread analysis: {e}")

            # DEBUG: Log return values
            self.logger.info(f"[DEBUG] BUILD Return: isinstance(eth_result, OrderResult)={isinstance(eth_result, OrderResult)}, eth_result.success={eth_result.success if isinstance(eth_result, OrderResult) else 'N/A'}, isinstance(sol_result, OrderResult)={isinstance(sol_result, OrderResult)}, sol_result.success={sol_result.success if isinstance(sol_result, OrderResult) else 'N/A'}")

            return (isinstance(eth_result, OrderResult) and eth_result.success and
                    isinstance(sol_result, OrderResult) and sol_result.success)
        except Exception as e:
            self.logger.error(f"[BUILD] Exception during build cycle: {e}")
            import traceback
            self.logger.error(f"[BUILD] Traceback: {traceback.format_exc()}")
            self._is_entry_phase = False
            return False

    async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
        """Execute UNWIND cycle with specified order sides.

        Args:
            eth_side: Order side for ETH ("buy" or "sell")
            sol_side: Order side for SOL ("buy" or "sell")

        Returns:
            True if both positions are closed (abs < 0.001), False otherwise.
        """
        from datetime import datetime
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE
        POSITION_TOLERANCE = Decimal("0.001")
        MAX_RETRIES = 3
        RETRY_DELAY = 2.0

        # Log pre-unwind positions
        eth_pos_before = await self.eth_client.get_account_positions()
        sol_pos_before = await self.sol_client.get_account_positions()
        self.logger.info(f"[UNWIND] POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")

        # TASK 5: Pre-exit liquidity check using BookDepth (V5.6)
        liquidity_check = await self._check_exit_liquidity(max_slippage_bps=20)
        self.logger.info(
            f"[LIQUIDITY] Exit check: ETH={liquidity_check['eth_can_exit']} "
            f"(${liquidity_check['eth_liquidity_usd']:.2f}), "
            f"SOL={liquidity_check['sol_can_exit']} "
            f"(${liquidity_check['sol_liquidity_usd']:.2f})"
        )

        # Store for CSV logging (TASK 6)
        self._exit_liquidity_available = "true" if liquidity_check['can_exit'] else "false"
        self._exit_liquidity_usd = str(liquidity_check['eth_liquidity_usd'] + liquidity_check['sol_liquidity_usd'])

        # Log warning if insufficient liquidity
        if not liquidity_check['can_exit']:
            self.logger.warning(
                f"[LIQUIDITY] Insufficient liquidity for clean exit - "
                f"proceeding with caution (ETH: ${liquidity_check['eth_liquidity_usd']:.2f}, "
                f"SOL: ${liquidity_check['sol_liquidity_usd']:.2f})"
            )

        # V5.3: Check exit timing based on unrealized PNL
        should_exit, exit_reason = await self._check_exit_timing(max_loss_bps=30)
        self.logger.info(f"[EXIT] Timing check: should_exit={should_exit}, reason={exit_reason}")

        # Track if this cycle had a safety stop (for rollback monitoring)
        self._had_safety_stop = exit_reason.startswith("stop_loss_")

        # Get exit spread information for analysis
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)
        _, exit_spread_info = self._check_spread_profitability(eth_bid, eth_ask, sol_bid, sol_ask)
        self._exit_spread_info = exit_spread_info

        # TASK 6: Store exit spread state for CSV logging
        exit_spread_state = None
        try:
            if self.eth_client and self.eth_client.get_bbo_handler():
                exit_spread_state = self.eth_client.get_bbo_handler().get_spread_state()
        except Exception:
            pass
        self._spread_state_exit = exit_spread_state or "unknown"

        # Store exit threshold for CSV logging
        exit_thresholds = self._calculate_dynamic_exit_thresholds()
        self._exit_threshold_bps = exit_thresholds["profit_target_bps"]

        # Set exit phase flag for PNL tracking
        self._is_exit_phase = True

        # Place UNWIND orders with specified sides
        eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

        # Store exit prices from OrderResult
        if isinstance(eth_result, OrderResult) and eth_result.success:
            self._exit_prices = getattr(self, '_exit_prices', {})
            self._exit_prices["ETH"] = eth_result.price if eth_result.price else self.entry_prices.get("ETH", Decimal("0"))

        if isinstance(sol_result, OrderResult) and sol_result.success:
            self._exit_prices = getattr(self, '_exit_prices', {})
            self._exit_prices["SOL"] = sol_result.price if sol_result.price else self.entry_prices.get("SOL", Decimal("0"))

        self._is_exit_phase = False

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
                # Mark exit time and calculate final PNL
                self.current_cycle_pnl["exit_time"] = datetime.now(pytz.UTC)

                # Calculate and log final PNL (includes funding correction)
                pnl_no_fee, pnl_with_fee, breakdown = self._calculate_current_pnl()
                self._pnl_breakdown = breakdown  # Store for logging
                self._log_final_cycle_pnl()

                # Log final spread analysis with exit data
                entry_spread_info = getattr(self, '_entry_spread_info', {})
                exit_spread_info = getattr(self, '_exit_spread_info', {})
                self._log_spread_analysis(entry_spread_info, exit_spread_info)

                # Clear entry state for next cycle
                self.entry_prices = {"ETH": None, "SOL": None}
                self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
                self.entry_timestamps = {"ETH": None, "SOL": None}

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

            # Optional sleep with real-time PNL logging
            if self.sleep_time > 0:
                sleep_interval = 60  # Log every 60 seconds
                elapsed = 0
                while elapsed < self.sleep_time:
                    await asyncio.sleep(min(sleep_interval, self.sleep_time - elapsed))
                    await self._log_realtime_pnl()
                    elapsed += sleep_interval

            unwind_success = await self.execute_unwind_cycle()
            return unwind_success
        except Exception:
            return False

    async def execute_buy_first_cycle(self) -> bool:
        """Execute BUY_FIRST cycle: BUILD (Long ETH / Short SOL) -> UNWIND."""
        # Increment cycle_id for PNL tracking
        self.cycle_id += 1
        self.logger.info(f"[CYCLE {self.cycle_id}] Starting BUY_FIRST cycle")

        # Initialize cycle PNL state
        from datetime import datetime
        self.current_cycle_pnl = {
            "pnl_no_fee": Decimal("0"),
            "pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "entry_time": datetime.now(pytz.UTC),
            "exit_time": None
        }

        # Clear previous entry state
        self.entry_prices = {"ETH": None, "SOL": None}
        self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self.entry_timestamps = {"ETH": None, "SOL": None}

        try:
            # BUILD: Long ETH / Short SOL
            build_success = await self.execute_build_cycle("buy", "sell")
            if not build_success:
                return False

            # Optional sleep with real-time PNL logging
            if self.sleep_time > 0:
                sleep_interval = 60  # Log every 60 seconds
                elapsed = 0
                while elapsed < self.sleep_time:
                    await asyncio.sleep(min(sleep_interval, self.sleep_time - elapsed))
                    await self._log_realtime_pnl()
                    elapsed += sleep_interval

            # UNWIND: Sell ETH / Buy SOL
            unwind_success = await self.execute_unwind_cycle("sell", "buy")

            # Update daily summary after cycle completes
            if unwind_success:
                self._update_daily_pnl_summary()

            return unwind_success

        except Exception as e:
            self.logger.error(f"BUY_FIRST cycle failed: {e}")
            return False

    async def execute_sell_first_cycle(self) -> bool:
        """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND."""
        # Increment cycle_id for PNL tracking
        self.cycle_id += 1
        self.logger.info(f"[CYCLE {self.cycle_id}] Starting SELL_FIRST cycle")

        # Initialize cycle PNL state
        from datetime import datetime
        self.current_cycle_pnl = {
            "pnl_no_fee": Decimal("0"),
            "pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "entry_time": datetime.now(pytz.UTC),
            "exit_time": None
        }

        # Clear previous entry state
        self.entry_prices = {"ETH": None, "SOL": None}
        self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self.entry_timestamps = {"ETH": None, "SOL": None}

        try:
            # BUILD: Short ETH / Long SOL (opposite of buy_first)
            build_success = await self.execute_build_cycle("sell", "buy")
            if not build_success:
                return False

            # Optional sleep with real-time PNL logging
            if self.sleep_time > 0:
                sleep_interval = 60  # Log every 60 seconds
                elapsed = 0
                while elapsed < self.sleep_time:
                    await asyncio.sleep(min(sleep_interval, self.sleep_time - elapsed))
                    await self._log_realtime_pnl()
                    elapsed += sleep_interval

            # UNWIND: Buy ETH / Sell SOL
            unwind_success = await self.execute_unwind_cycle("buy", "sell")

            # Update daily summary after cycle completes
            if unwind_success:
                self._update_daily_pnl_summary()

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

            # Check rollback conditions after each successful cycle
            should_rollback, rollback_reason = self.rollback_monitor.should_rollback()
            if should_rollback:
                self.logger.error(f"[ROLLBACK] {rollback_reason}")
                self.logger.error(
                    f"[ROLLBACK] Bot stopping due to rollback conditions. "
                    f"Review strategy parameters before continuing."
                )
                break
            else:
                self.logger.info(f"[ROLLBACK] {rollback_reason}")

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
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE
        self.logger.info(
            f"[INIT] WEBSOCKET_AVAILABLE: {WEBSOCKET_AVAILABLE}"
        )

        # ETH client configuration
        eth_config = Config({
            'ticker': 'ETH',
            'contract_id': '4',  # ETH product ID on Nado
            'min_size': Decimal('0.001'),
            # Note: tick_size is fetched dynamically from SDK API in _round_price_to_increment()
        })

        # SOL client configuration
        sol_config = Config({
            'ticker': 'SOL',
            'contract_id': '8',  # SOL product ID on Nado
            'min_size': Decimal('0.001'),
            # Note: tick_size is fetched dynamically from SDK API in _round_price_to_increment()
        })

        # Create Nado clients for both tickers (pass Config objects directly)
        self.eth_client = NadoClient(eth_config)
        self.sol_client = NadoClient(sol_config)

        # Fetch contract attributes from SDK (populates client.config.tick_size)
        await self.eth_client.get_contract_attributes()
        await self.sol_client.get_contract_attributes()

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
        self.eth_tick_size = self.eth_client.config.tick_size
        self.sol_contract_id = sol_config.contract_id
        self.sol_tick_size = self.sol_client.config.tick_size

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
    parser.add_argument(
        "--use-ioc",
        action="store_true",
        help="Use IOC orders (taker, 5 bps fee) instead of POST_ONLY (maker, 2 bps fee, default)"
    )
    parser.add_argument(
        "--min-spread-bps",
        type=int,
        default=0,
        help="Minimum spread in bps - sanity check only, NOT breakeven. Profit comes from post-entry spread convergence and price movement. (default: 0)"
    )

    # Feature flags for PNL optimization
    parser.add_argument(
        '--enable-at-touch-pricing',
        action='store_true',
        help='Enable at-touch pricing (buy=bid, sell=ask) for maker execution'
    )
    parser.add_argument(
        '--enable-order-type-default',
        action='store_true',
        help='Use OrderType.DEFAULT instead of POST_ONLY for flexibility'
    )
    parser.add_argument(
        '--enable-queue-filter',
        action='store_true',
        help='Skip trading when queue size at touch is too deep'
    )
    parser.add_argument(
        '--enable-spread-filter',
        action='store_true',
        help='Skip trading when spread is too wide'
    )
    parser.add_argument(
        '--enable-partial-fills',
        action='store_true',
        help='Accept partial fills >= 50% of order size'
    )
    parser.add_argument(
        '--enable-dynamic-timeout',
        action='store_true',
        help='Adjust timeout based on market volatility'
    )

    # Configurable thresholds
    parser.add_argument(
        '--queue-threshold-ratio',
        type=float,
        default=0.5,
        help='Maximum queue size as ratio of average (default: 0.5)'
    )
    parser.add_argument(
        '--spread-threshold-ticks',
        type=int,
        default=5,
        help='Maximum spread in ticks before skipping (default: 5)'
    )
    parser.add_argument(
        '--min-partial-fill-ratio',
        type=float,
        default=0.5,
        help='Minimum partial fill ratio to accept (default: 0.5)'
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
        use_post_only=not getattr(args, 'use_ioc', False),  # POST_ONLY mode (default True)
        min_spread_bps=getattr(args, 'min_spread_bps', 0),  # Min spread sanity check - profit from post-entry movements (default 0 bps)
        # PNL optimization feature flags
        enable_at_touch_pricing=getattr(args, 'enable_at_touch_pricing', False),
        enable_order_type_default=getattr(args, 'enable_order_type_default', False),
        enable_queue_filter=getattr(args, 'enable_queue_filter', False),
        enable_spread_filter=getattr(args, 'enable_spread_filter', False),
        enable_partial_fills=getattr(args, 'enable_partial_fills', False),
        enable_dynamic_timeout=getattr(args, 'enable_dynamic_timeout', False),
        # Configurable thresholds
        queue_threshold_ratio=getattr(args, 'queue_threshold_ratio', 0.5),
        spread_threshold_ticks=getattr(args, 'spread_threshold_ticks', 5),
        min_partial_fill_ratio=getattr(args, 'min_partial_fill_ratio', 0.5),
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
