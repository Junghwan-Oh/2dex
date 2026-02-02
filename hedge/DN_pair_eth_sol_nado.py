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
        # Static TP parameters (Phase 2)
        enable_static_tp: bool = False,
        tp_bps: float = 10.0,
        tp_timeout: int = 60,
        enable_tp_orders: bool = True,  # Set to False to disable TP
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

        # Static TP parameters (Phase 2)
        self.enable_static_tp = enable_static_tp
        self.tp_bps = tp_bps
        self.tp_timeout = tp_timeout
        self.enable_tp_orders = enable_tp_orders  # Set to False to disable TP

        # CRITICAL: Initialize to prevent AttributeError in Phase 2
        self._tp_hit_position = None  # Track which position hit TP
        self._tp_hit_pnl_pct = None   # Track PNL % when TP hit

        # Order mode: Always use DEFAULT (true limit order) now
        # Feature flags have been removed in favor of single unified path
        self.order_mode = "default"

        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/DN_pair_eth_sol_nado_log.txt"

        # Log order mode configuration
        import logging
        self._config_logger = logging.getLogger("dn_config")
        self._config_logger.info(f"[CONFIG] Order mode: {self.order_mode.upper()}")
        self._config_logger.info(f"[CONFIG] Min spread filter: {self.min_spread_bps} bps")
        self._config_logger.info(f"[CONFIG] At-touch pricing: {self.enable_at_touch_pricing}")
        self._config_logger.info(f"[CONFIG] Order type DEFAULT: {self.enable_order_type_default}")
        self._config_logger.info(f"[CONFIG] Queue filter: {self.enable_queue_filter} (threshold: {self.queue_threshold_ratio})")
        self._config_logger.info(f"[CONFIG] Spread filter: {self.enable_spread_filter} (threshold: {self.spread_threshold_ticks} ticks)")
        self._config_logger.info(f"[CONFIG] Partial fills: {self.enable_partial_fills} (min ratio: {self.min_partial_fill_ratio})")
        self._config_logger.info(f"[CONFIG] Dynamic timeout: {self.enable_dynamic_timeout}")
        self._config_logger.info(f"[CONFIG] Static TP: {self.enable_static_tp} (threshold: {self.tp_bps} bps, timeout: {self.tp_timeout}s)")

        # Use custom CSV path if provided
        if csv_path:
            self.csv_filename = csv_path
        else:
            self.csv_filename = f"logs/DN_pair_eth_sol_nado_trades.csv"

        # Position CSV file for tracking WebSocket position updates
        self.position_csv_filename = csv_path.replace("_trades.csv", "_positions.csv") if csv_path and "_trades.csv" in csv_path else f"logs/DN_pair_eth_sol_nado_positions.csv"

        self._initialize_csv_file()
        self._initialize_position_csv_file()
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
        # Track actual order directions (buy/sell) for TP calculation
        self.entry_directions = {
            "ETH": None,  # "buy" (long) or "sell" (short)
            "SOL": None
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

        # WebSocket position tracking for startup residual detection
        self._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self._ws_initial_sync_complete = False  # Track if WebSocket has received initial position data
        self._startup_data_source = None  # Track which data source was used for startup check

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

    def _initialize_position_csv_file(self):
        """Initialize position CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.position_csv_filename):
            csv_dir = os.path.dirname(self.position_csv_filename)
            if csv_dir and not os.path.exists(csv_dir):
                os.makedirs(csv_dir, exist_ok=True)

            with open(self.position_csv_filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "exchange",
                    "timestamp",
                    "ticker",
                    "old_position",
                    "new_position",
                    "position_change",
                    "cycle_id",
                    "source",
                    "price"
                ])

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

    def log_position_update(
        self,
        ticker: str,
        old_position: Decimal,
        new_position: Decimal,
        cycle_id: str = "",
        source: str = "websocket",
        price: Decimal = None
    ):
        """Log position update to CSV for tracking."""
        from decimal import Decimal

        position_change = float(new_position - old_position)
        timestamp = datetime.now(pytz.UTC).isoformat()

        with open(self.position_csv_filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "NADO",
                timestamp,
                ticker,
                str(old_position),
                str(new_position),
                str(position_change),
                cycle_id,
                source,
                str(price) if price else ""
            ])

        self.logger.debug(f"[POSITION CSV] {ticker}: {old_position} -> {new_position} ({source})")

    def _on_eth_position_update(self, old_pos: Decimal, new_pos: Decimal) -> None:
        """Callback for ETH position updates from WebSocket."""
        try:
            self.log_position_update(
                ticker="ETH",
                old_position=old_pos,
                new_position=new_pos,
                cycle_id=str(self.iteration) if hasattr(self, 'iteration') else "",
                source="websocket"
            )
        except Exception as e:
            self.logger.error(f"[POSITION] Error logging ETH update: {e}")

    def _on_sol_position_update(self, old_pos: Decimal, new_pos: Decimal) -> None:
        """Callback for SOL position updates from WebSocket."""
        try:
            self.log_position_update(
                ticker="SOL",
                old_position=old_pos,
                new_position=new_pos,
                cycle_id=str(self.iteration) if hasattr(self, 'iteration') else "",
                source="websocket"
            )
        except Exception as e:
            self.logger.error(f"[POSITION] Error logging SOL update: {e}")

    def _on_position_change(self, data: dict) -> None:
        """WebSocket callback for position changes.

        This callback receives real-time position updates from Nado's WebSocket
        position_change stream, enabling early detection of position imbalances.
        """
        from decimal import Decimal

        # Debug: Log full message to understand the actual format
        product_id = data.get("product_id")
        amount_raw = data.get("amount", "0")
        self.logger.info(f"[POSITION CHANGE] product_id={product_id}, amount_raw={amount_raw}, type={type(amount_raw)}")

        try:
            # Determine which ticker this update is for
            if product_id == self.eth_client.config.contract_id:
                ticker = "ETH"
            elif product_id == self.sol_client.config.contract_id:
                ticker = "SOL"
            else:
                self.logger.warning(f"[POSITION CHANGE] Unknown product_id: {product_id}")
                return

            # Extract position data (actual format from Nado WebSocket)
            # The amount field is in x18 format for both ETH and SOL
            # Both use 1e18 (18 decimal places)
            precision = Decimal("1e18")
            amount = Decimal(str(amount_raw)) / precision if amount_raw else Decimal("0")
            self.logger.info(f"[POSITION CHANGE] {ticker}: amount_raw={amount_raw}, precision={precision}, amount={amount}")
            v_quote_amount = data.get("v_quote_amount", "0")  # USD value
            reason = data.get("reason", "")

            # Store in memory for real-time monitoring
            if not hasattr(self, '_ws_positions'):
                self._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}

            # For position_change events, the amount field contains the absolute position
            # Calculate change from previous tracked value
            old_pos = self._ws_positions.get(ticker, Decimal("0"))
            new_pos = amount

            # Update the tracked position
            self._ws_positions[ticker] = new_pos

            # Mark sync as complete when we receive position data for both tickers
            if not self._ws_initial_sync_complete:
                # Check if we have received data for both tickers
                has_eth = "ETH" in self._ws_positions
                has_sol = "SOL" in self._ws_positions
                if has_eth and has_sol:
                    self._ws_initial_sync_complete = True
                    self.logger.info("[POSITION SYNC] Initial WebSocket position sync complete")

            # For position_change events, calculate the delta
            position_change = float(new_pos - old_pos) if old_pos > 0 else float(new_pos)

            # Log to CSV
            self.log_position_update(
                ticker=ticker,
                old_position=old_pos,
                new_position=new_pos,
                cycle_id=str(self.iteration) if hasattr(self, 'iteration') else "",
                source="websocket_position_change",
                price=None  # Price not provided in position_change message
            )

            self.logger.debug(
                f"[POSITION CHANGE] {ticker}: amount={amount}, v_quote=${v_quote_amount}, reason={reason}"
            )

        except Exception as e:
            self.logger.error(f"[POSITION CHANGE] Error processing update: {e}")

    async def _wait_for_ws_position_sync(self, timeout: float = 5.0) -> bool:
        """
        Wait for WebSocket to receive initial position_change events.

        Args:
            timeout: Maximum time to wait in seconds (default 5.0)

        Returns:
            True when sync complete, False on timeout
        """
        if not self.eth_client._ws_connected or not self.sol_client._ws_connected:
            self.logger.warning("[WS SYNC] WebSocket not connected, skipping sync wait")
            return False

        start_time = time.time()
        self.logger.info(f"[WS SYNC] Waiting for initial position sync (timeout: {timeout}s)...")

        while not self._ws_initial_sync_complete:
            if time.time() - start_time > timeout:
                self.logger.warning(f"[WS SYNC] Timeout waiting for position sync after {timeout}s")
                return False
            await asyncio.sleep(0.1)

        self.logger.info("[WS SYNC] Position sync complete")
        return True

    async def _get_startup_positions(self) -> Tuple[Decimal, Decimal]:
        """
        Get positions at startup with WebSocket priority.

        Priority:
        1. WebSocket positions (_ws_positions) if available (sync complete or manually set)
        2. REST API fallback

        Returns:
            Tuple of (eth_pos, sol_pos)
            Data source is tracked in self._startup_data_source
        """
        # Try WebSocket positions first
        # Use WebSocket positions if:
        # 1. Initial sync is complete (WebSocket is connected and received data), OR
        # 2. _ws_positions has been manually set with non-default values (for testing)
        use_websocket = False
        if hasattr(self, '_ws_positions') and self._ws_positions:
            if self._ws_initial_sync_complete:
                # WebSocket sync completed - use these positions
                use_websocket = True
            else:
                # Check if positions have been manually set (not the default zero initialization)
                # This allows tests to simulate WebSocket positions
                eth_val = self._ws_positions.get("ETH", Decimal("0"))
                sol_val = self._ws_positions.get("SOL", Decimal("0"))
                # If either position is non-zero, assume it was manually set for testing
                if eth_val != Decimal("0") or sol_val != Decimal("0"):
                    use_websocket = True

        if use_websocket:
            eth_pos = self._ws_positions.get("ETH", Decimal("0"))
            sol_pos = self._ws_positions.get("SOL", Decimal("0"))
            self._startup_data_source = "websocket"
            self.logger.info("[STARTUP] Using WebSocket positions for startup check")
            self.logger.info(f"[STARTUP] ETH (WS): {eth_pos}, SOL (WS): {sol_pos}")
            return eth_pos, sol_pos

        # Fall back to REST API
        self._startup_data_source = "rest_api"
        self.logger.info("[STARTUP] WebSocket not ready, using REST API for startup check")
        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()
        self.logger.info(f"[STARTUP] ETH (REST): {eth_pos}, SOL (REST): {sol_pos}")
        return eth_pos, sol_pos

    async def _check_residual_positions_at_startup(self) -> bool:
        """
        Complete startup position check with WebSocket priority.

        Uses WebSocket positions if available, falls back to REST API.
        Logs which data source was used.

        Returns:
            True if no residuals (clean start), exits if residuals found

        Raises:
            SystemExit: If residual positions detected (exit code 1)
        """
        POSITION_TOLERANCE = Decimal("0.001")

        # Get positions using WebSocket priority
        eth_pos, sol_pos = await self._get_startup_positions()

        # Check for residual positions
        if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
            data_source = self._startup_data_source or "unknown"
            print(f"\n[WARNING] Residual positions detected (source: {data_source})!")
            print(f"  ETH: {eth_pos}")
            print(f"  SOL: {sol_pos}")
            print(f"\n[SAFETY] Please close positions manually before starting the bot.")
            print(f"  - Use the exchange interface to close positions")
            print(f"  - Or use a separate close-positions script")
            sys.exit(1)

        print("[STARTUP] No residual positions. Ready to start.\n")
        return True

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

    async def _poll_limit_order_fill(
        self,
        client: 'NadoClient',
        order_result: OrderResult,
        original_qty: Decimal,
        timeout: int
    ) -> OrderResult:
        """Poll limit order until filled or timeout.

        Args:
            client: NadoClient instance
            order_result: Initial order result with status='OPEN'
            original_qty: Original order quantity
            timeout: Maximum seconds to wait

        Returns:
            Updated OrderResult with fill status
        """
        import time
        POLL_INTERVAL = 0.1
        start_time = time.time()
        order_id = order_result.order_id

        while time.time() - start_time < timeout:
            try:
                order_info = await client.get_order_info(order_id)
                if order_info:
                    filled_size = abs(order_info.filled_size)
                    remaining_size = order_info.remaining_size

                    if remaining_size == 0:
                        # Fully filled
                        return OrderResult(
                            success=True,
                            order_id=order_id,
                            filled_size=original_qty,
                            status='FILLED',
                            price=order_info.price,
                            side=order_result.side
                        )
                    elif filled_size > 0:
                        filled_ratio = filled_size / original_qty
                        if filled_ratio >= self.min_partial_fill_ratio:
                            # Partially filled, accept it and cancel remainder
                            self.logger.info(
                                f"Partial fill accepted: {filled_size}/{original_qty} ({filled_ratio:.1%})"
                            )
                            await client.cancel_order(order_id)
                            return OrderResult(
                                success=True,
                                order_id=order_id,
                                filled_size=filled_size,
                                status='PARTIALLY_FILLED',
                                price=order_info.price,
                                side=order_result.side
                            )
            except Exception as e:
                self.logger.warning(f"Error polling order {order_id}: {e}")

            await asyncio.sleep(POLL_INTERVAL)

        # Timeout - cancel and return failure (SIMPLE: no retry)
        self.logger.warning(f"Limit order timeout after {timeout}s, cancelling")
        try:
            await client.cancel_order(order_id)
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")

        return OrderResult(
            success=False,
            error_message=f'Limit order timeout after {timeout}s'
        )

    async def place_simultaneous_orders(
        self,
        eth_direction: str,
        sol_direction: str,
    ) -> Tuple[OrderResult, OrderResult]:
        """Place ETH and SOL orders simultaneously using OrderType.DEFAULT.

        Single unified path - no use_post_only branching, no IOC fallback.
        Orders rest on book at maker prices (BUY=bid, SELL=ask).
        """
        # Get initial positions BEFORE placing orders
        # NOTE: WebSocket positions are real-time; REST API has ~20s lag
        eth_pos_before = self._ws_positions.get("ETH", Decimal("0"))
        sol_pos_before = self._ws_positions.get("SOL", Decimal("0"))

        self.logger.info(f"[INIT] ETH pos: {eth_pos_before} (WS), SOL pos: {sol_pos_before} (WS)")

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

        # Fee rate based on order mode: DEFAULT = 2 bps (maker)
        FEE_RATE = Decimal("0.0002") if self.order_mode == "default" else Decimal("0.0005")
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

        # CORE FIX: Maker pricing (BUY at bid, SELL at ask)
        eth_price = eth_bid if eth_direction == "buy" else eth_ask
        sol_price = sol_bid if sol_direction == "buy" else sol_ask

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
            return (
                OrderResult(success=False, error_message=f"Skipped: {', '.join(skip_reason)}"),
                OrderResult(success=False, error_message=f"Skipped: {', '.join(skip_reason)}")
            )

        self.logger.info(
            f"[ORDER] Placing DEFAULT limit orders: "
            f"ETH {eth_direction} {eth_qty} @ ${eth_price}, "
            f"SOL {sol_direction} {sol_qty} @ ${sol_price}"
        )

        # Calculate dynamic timeout (FIXED: use get_bbo_handler())
        spread_state = None
        if self.enable_dynamic_timeout:
            if self.eth_client.get_bbo_handler():
                spread_state = self.eth_client.get_bbo_handler().get_spread_state()

        # For limit orders (maker), use longer timeout since they rest on the book
        # Base timeout * 3 to give counterparties time to take our orders
        eth_timeout = self.eth_client.calculate_timeout(eth_qty, spread_state) * 3
        sol_timeout = self.sol_client.calculate_timeout(sol_qty, spread_state) * 3

        # Cap at 30 seconds maximum for limit orders
        eth_timeout = min(eth_timeout, 30)
        sol_timeout = min(sol_timeout, 30)

        # Place limit orders (returns OPEN status immediately)
        eth_result, sol_result = await asyncio.gather(
            self.eth_client.place_limit_order(
                self.eth_client.config.contract_id,
                eth_qty,
                eth_direction,
                eth_price
            ),
            self.sol_client.place_limit_order(
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

        # If both failed, return immediately
        if not eth_result.success and not sol_result.success:
            self.logger.error(f"[ORDER] Both orders failed - ETH: {eth_result.error_message}, SOL: {sol_result.error_message}")
            return eth_result, sol_result

        # Poll for fills (if OPEN status)
        if eth_result.status == 'OPEN' or sol_result.status == 'OPEN':
            eth_result = await self._poll_limit_order_fill(
                self.eth_client, eth_result, eth_qty, eth_timeout
            )
            sol_result = await self._poll_limit_order_fill(
                self.sol_client, sol_result, sol_qty, sol_timeout
            )

        # Extract fill details from OrderResult
        eth_filled = eth_result.status in ('FILLED', 'PARTIALLY_FILLED')
        eth_fill_qty = eth_result.filled_size if eth_filled else Decimal(0)
        eth_fill_price = eth_result.price if eth_filled else Decimal(0)

        sol_filled = sol_result.status in ('FILLED', 'PARTIALLY_FILLED')
        sol_fill_qty = sol_result.filled_size if sol_filled else Decimal(0)
        sol_fill_price = sol_result.price if sol_filled else Decimal(0)

        # Check results and log fills
        if eth_filled:
            fill_type = "fully" if eth_result.status == 'FILLED' else "partially"
            self.logger.info(f"[FILL] ETH order {fill_type} filled: {eth_fill_qty} @ ${eth_fill_price}")
        elif not eth_result.success:
            self.logger.error(f"[FILL] ETH order failed: {eth_result.error_message}")

        if sol_filled:
            fill_type = "fully" if sol_result.status == 'FILLED' else "partially"
            self.logger.info(f"[FILL] SOL order {fill_type} filled: {sol_fill_qty} @ ${sol_fill_price}")
        elif not sol_result.success:
            self.logger.error(f"[FILL] SOL order failed: {sol_result.error_message}")

        # Partial fill handling
        if eth_fill_qty > 0 and sol_fill_qty > 0:
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
        # Fee rate based on order mode: DEFAULT = 2 bps (maker)
        FEE_RATE = Decimal("0.0002") if self.order_mode == "default" else Decimal("0.0005")

        # Store entry prices and quantities for PNL tracking
        if hasattr(self, '_is_entry_phase') and self._is_entry_phase:
            from datetime import datetime
            entry_timestamp = datetime.now(pytz.UTC).isoformat()

            if eth_fill_qty > 0:
                # CRITICAL: Ensure entry price is valid, fetch from market if missing
                if not eth_fill_price or eth_fill_price == 0:
                    eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
                    eth_fill_price = eth_ask if eth_direction == "buy" else eth_bid
                    self.logger.warning(f"[BUILD] ETH fill price missing, using market price: ${eth_fill_price}")
                self.entry_prices["ETH"] = eth_fill_price
                self.entry_quantities["ETH"] += eth_fill_qty
                self.entry_timestamps["ETH"] = entry_timestamp

            if sol_fill_qty > 0:
                # CRITICAL: Ensure entry price is valid, fetch from market if missing
                if not sol_fill_price or sol_fill_price == 0:
                    sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)
                    sol_fill_price = sol_ask if sol_direction == "buy" else sol_bid
                    self.logger.warning(f"[BUILD] SOL fill price missing, using market price: ${sol_fill_price}")
                self.entry_prices["SOL"] = sol_fill_price
                self.entry_quantities["SOL"] += sol_fill_qty
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

        # Handle partial fills and failed orders - ONLY trigger if there's an actual issue
        eth_filled = (isinstance(eth_result, OrderResult) and self._is_fill_complete(eth_result))
        sol_filled = (isinstance(sol_result, OrderResult) and self._is_fill_complete(sol_result))

        # Only trigger emergency unwind if one leg failed
        if not eth_filled or not sol_filled:
            # One or both orders failed - trigger emergency unwind
            self.logger.warning(f"[BUILD] Triggering emergency unwind - ETH filled={eth_filled}, SOL filled={sol_filled}")
            await self.handle_emergency_unwind(eth_result, sol_result)
        elif eth_filled and sol_filled:
            # Both filled successfully - proceed to UNWIND phase, do NOT close positions!
            self.logger.info(f"[BUILD] Both orders filled successfully - proceeding to UNWIND phase")
            # No emergency unwind needed - positions are established correctly
        else:
            # Both failed (shouldn't happen but handle safely)
            self.logger.error(f"[BUILD] Both orders failed - checking for residual positions")
            await self.handle_emergency_unwind(eth_result, sol_result)

        return eth_result, sol_result

    async def handle_emergency_unwind(self, eth_result, sol_result):
        """Handle emergency unwind when one leg fails or is partially filled.

        CRITICAL: ALWAYS close BOTH positions on emergency unwind to prevent
        position accumulation bugs. This is called when:
        - One leg fills and the other fails
        - Positions become imbalanced
        - Retry limit is exceeded
        """
        # Debug logging
        self.logger.info(f"[DEBUG] handle_emergency_unwind: eth_result.success={eth_result.success if isinstance(eth_result, OrderResult) else 'Exception'}, sol_result.success={sol_result.success if isinstance(sol_result, OrderResult) else 'Exception'}")

        # CRITICAL FIX: Always close BOTH positions on emergency unwind
        # This prevents position accumulation when one leg fails

        # Check if both legs filled successfully
        eth_filled = (isinstance(eth_result, OrderResult) and
                      self._is_fill_complete(eth_result))
        sol_filled = (isinstance(sol_result, OrderResult) and
                      self._is_fill_complete(sol_result))

        # Log the situation
        if eth_filled and not sol_filled:
            self.logger.warning(f"[UNWIND] ETH filled but SOL failed - closing BOTH positions")
        elif sol_filled and not eth_filled:
            self.logger.warning(f"[UNWIND] SOL filled but ETH failed - closing BOTH positions")
        elif eth_filled and sol_filled:
            self.logger.info(f"[UNWIND] Both filled but imbalanced - closing BOTH positions")
        else:
            self.logger.info(f"[UNWIND] Both failed - checking for residual positions")

        # ALWAYS close both positions
        await self._force_close_position("ETH")
        await self._force_close_position("SOL")

    async def _force_close_position(self, ticker: str) -> bool:
        """Force close position with retry, handling settlement lag.

        This method is used during emergency unwind to ensure positions are
        fully closed even when settlement delays cause position checks to
        be temporarily inaccurate.

        Args:
            ticker: Either "ETH" or "SOL"

        Returns:
            True if position confirmed closed, False otherwise
        """
        from decimal import Decimal
        POSITION_TOLERANCE = Decimal("0.001")

        client = self.eth_client if ticker == "ETH" else self.sol_client

        if not client:
            self.logger.warning(f"[FORCE] No client for {ticker}, skipping")
            return False

        contract_id = client.config.contract_id

        for attempt in range(5):
            try:
                # Wait for settlement to process
                await asyncio.sleep(2)

                current_pos = await client.get_account_positions()

                if abs(current_pos) < POSITION_TOLERANCE:
                    self.logger.info(f"[FORCE] {ticker} position confirmed closed (pos={current_pos})")
                    return True

                # Determine close side and quantity
                close_side = "sell" if current_pos > 0 else "buy"
                close_qty = abs(current_pos)

                # Get current prices
                bid, ask = await client.fetch_bbo_prices(contract_id)
                close_price = bid if close_side == "sell" else ask

                self.logger.info(
                    f"[FORCE] Closing {ticker} {close_side} {close_qty} @ {close_price} "
                    f"(attempt {attempt+1}/5, current_pos={current_pos})"
                )

                result = await client.place_limit_order_with_timeout(
                    contract_id=contract_id,
                    quantity=close_qty,
                    direction=close_side,
                    price=close_price,
                    timeout_seconds=15,
                    max_retries=1
                )

                if result.success:
                    filled_size = self._get_filled_size(result)
                    if self._is_fill_complete(result):
                        self.logger.info(f"[FORCE] {ticker} closed successfully: {filled_size} filled")
                        # Final verification
                        await asyncio.sleep(1)
                        final_pos = await client.get_account_positions()
                        if abs(final_pos) < POSITION_TOLERANCE:
                            return True
                        else:
                            self.logger.warning(f"[FORCE] {ticker} still has position after close: {final_pos}")
                    else:
                        self.logger.warning(f"[FORCE] {ticker} partial fill: {filled_size}")
                else:
                    self.logger.warning(f"[FORCE] {ticker} close attempt failed: {result.error_message}")

            except Exception as e:
                self.logger.error(f"[FORCE] {ticker} close attempt {attempt+1} error: {e}")

        self.logger.error(f"[FORCE] Failed to close {ticker} after 5 attempts")
        return False

    async def _verify_and_force_close_all_positions(self) -> None:
        """Verify and force close all positions to prevent accumulation.

        This is called in exception handlers to ensure no residual positions
        remain after errors or unexpected failures.
        """
        from decimal import Decimal
        POSITION_TOLERANCE = Decimal("0.001")

        try:
            # NOTE: WebSocket positions are real-time; REST API has ~20s lag
            eth_pos = self._ws_positions.get("ETH", Decimal("0"))
            sol_pos = self._ws_positions.get("SOL", Decimal("0"))

            self.logger.warning(f"[CLEANUP] Checking positions (WS): ETH={eth_pos}, SOL={sol_pos}")

            if abs(eth_pos) > POSITION_TOLERANCE:
                self.logger.warning(f"[CLEANUP] Force closing ETH position: {eth_pos}")
                await self._force_close_position("ETH")

            if abs(sol_pos) > POSITION_TOLERANCE:
                self.logger.warning(f"[CLEANUP] Force closing SOL position: {sol_pos}")
                await self._force_close_position("SOL")

        except Exception as e:
            self.logger.error(f"[CLEANUP] Error during position cleanup: {e}")

    async def _verify_positions_before_build(self) -> bool:
        """Verify positions using REST API before starting BUILD cycle.

        This is a safety check to prevent position accumulation by verifying
        that positions are actually closed using REST API before starting a new cycle.

        Returns:
            True if positions are closed (or successfully closed), False otherwise.
        """
        from decimal import Decimal
        POSITION_TOLERANCE = Decimal("0.001")

        try:
            eth_rest = await self.eth_client.get_account_positions()
            sol_rest = await self.sol_client.get_account_positions()

            self.logger.info(f"[SAFETY] REST API positions: ETH={eth_rest}, SOL={sol_rest}")

            if abs(eth_rest) > POSITION_TOLERANCE or abs(sol_rest) > POSITION_TOLERANCE:
                self.logger.error(
                    f"[SAFETY] Positions not closed before BUILD: "
                    f"ETH={eth_rest}, SOL={sol_rest}. Attempting to close..."
                )

                if abs(eth_rest) > POSITION_TOLERANCE:
                    await self._force_close_position("ETH")
                if abs(sol_rest) > POSITION_TOLERANCE:
                    await self._force_close_position("SOL")

                eth_rest = await self.eth_client.get_account_positions()
                sol_rest = await self.sol_client.get_account_positions()

                if abs(eth_rest) > POSITION_TOLERANCE or abs(sol_rest) > POSITION_TOLERANCE:
                    self.logger.error(
                        f"[SAFETY] Failed to close positions before BUILD: "
                        f"ETH={eth_rest}, SOL={sol_rest}. ABORTING."
                    )
                    return False

                self.logger.info("[SAFETY] Positions successfully closed before BUILD")

            self._ws_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
            self.logger.info("[CYCLE START] WebSocket positions reset after REST verification")

            return True

        except Exception as e:
            self.logger.error(f"[SAFETY] Error during position verification: {e}")
            return False

    async def emergency_unwind_eth(self):
        """Emergency unwind ETH position (handles both long and short).

        Determines current position direction and closes with limit order.
        Uses at-touch pricing with automatic price improvement (2, 4, 6 bps).

        Called from handle_emergency_unwind() when ETH fills but SOL fails.
        """
        if self.eth_client:
            max_retries = 3
            max_timeout_seconds = 60

            for attempt in range(max_retries):
                try:
                    current_pos = await self.eth_client.get_account_positions()
                    if abs(current_pos) < Decimal("0.001"):
                        self.logger.info(f"[UNWIND] ETH position cleared (pos={current_pos})")
                        return

                    # Determine close side: long positions sell, short positions buy
                    close_side = "sell" if current_pos > 0 else "buy"

                    # Use limit order with timeout and price improvement
                    result = await self.eth_client.place_limit_order_with_timeout(
                        contract_id=self.eth_client.config.contract_id,
                        quantity=abs(current_pos),
                        direction=close_side,
                        price=None,  # Let method determine at-touch price
                        timeout_seconds=max_timeout_seconds,
                        max_retries=1  # Single attempt per outer loop iteration
                    )

                    if result.success and result.status in ('FILLED', 'PARTIALLY_FILLED'):
                        self.logger.info(f"[UNWIND] ETH emergency close attempt {attempt+1}: {result.filled_size} filled")
                        # Check if remaining position needs another iteration
                        remaining = await self.eth_client.get_account_positions()
                        if abs(remaining) < Decimal("0.001"):
                            self.logger.info(f"[UNWIND] ETH position fully closed")
                            return
                        # Continue to next attempt with remaining quantity
                    else:
                        self.logger.warning(f"[UNWIND] ETH emergency close attempt {attempt+1} failed: {result.error_message}")

                except Exception as e:
                    self.logger.error(f"[UNWIND] ETH emergency close attempt {attempt+1} error: {e}")

            self.logger.error(f"[UNWIND] Failed to fully close ETH position after {max_retries} attempts ({max_retries * max_timeout_seconds}s total)")

    async def emergency_unwind_sol(self):
        """Emergency unwind SOL position (handles both long and short).

        Determines current position direction and closes with Limit Order.
        Max 3 retries, 60 seconds per retry (180 seconds total).

        Called from handle_emergency_unwind() when SOL fills but ETH fails.
        """
        if self.sol_client:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    current_pos = await self.sol_client.get_account_positions()
                    if abs(current_pos) < Decimal("0.001"):
                        self.logger.info(f"[UNWIND] SOL position cleared (pos={current_pos})")
                        return

                    # Determine close side: long positions sell, short positions buy
                    close_side = "sell" if current_pos > 0 else "buy"

                    # Use Limit Order with timeout (NO IOC)
                    result = await self.sol_client.place_limit_order_with_timeout(
                        contract_id=self.sol_client.config.contract_id,
                        quantity=abs(current_pos),
                        direction=close_side,
                        price=None,
                        timeout_seconds=60,
                        max_retries=3
                    )

                    if result.success and result.status in ('FILLED', 'PARTIALLY_FILLED'):
                        self.logger.info(f"[UNWIND] SOL emergency close successful: {result.filled_size} filled")
                        # Check if remaining position needs another iteration
                        remaining = await self.sol_client.get_account_positions()
                        if abs(remaining) < Decimal("0.001"):
                            return
                    else:
                        self.logger.warning(f"[UNWIND] SOL emergency close attempt {attempt+1} failed: {result.error_message}")

                except Exception as e:
                    self.logger.error(f"[UNWIND] SOL emergency close attempt {attempt+1} error: {e}")

                await asyncio.sleep(0.1)

            self.logger.error(f"[UNWIND] Failed to close SOL position after {max_retries} attempts")

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
                        if liq is not None:
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
                        if liq is not None:
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
        # Entry fees ALREADY PAID: 10 bps (IOC) or 4 bps (DEFAULT)
        # Exit fees REMAINING: 10 bps (IOC) or 4 bps (DEFAULT)
        remaining_exit_fees_bps = 4 if self.order_mode == "default" else 10

        BASE_PROFIT = 15
        MIN_NET_PROFIT = 5

        profit_target = BASE_PROFIT + remaining_exit_fees_bps  # 19 for DEFAULT, 25 for IOC
        quick_exit = MIN_NET_PROFIT + remaining_exit_fees_bps  # 9 for DEFAULT, 15 for IOC
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

            eth_entry_price = self.entry_prices.get("ETH") or Decimal("0")
            sol_entry_price = self.entry_prices.get("SOL") or Decimal("0")
            eth_qty = self.entry_quantities.get("ETH") or Decimal("0")
            sol_qty = self.entry_quantities.get("SOL") or Decimal("0")

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

        eth_entry_price = self.entry_prices.get("ETH") or Decimal("0")
        sol_entry_price = self.entry_prices.get("SOL") or Decimal("0")
        eth_qty = self.entry_quantities.get("ETH") or Decimal("0")
        sol_qty = self.entry_quantities.get("SOL") or Decimal("0")

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

    async def _monitor_static_individual_tp(
        self,
        tp_threshold_bps: float = 10.0,
        timeout_seconds: int = 600  # Increased to 10 minutes for better TP hit chance
    ) -> tuple[bool, str]:
        """
        Monitor individual positions and exit when TP hit.

        Static TP: Set at entry, check until hit or timeout.

        Args:
            tp_threshold_bps: TP threshold in basis points (default: 10bps = 0.1%)
            timeout_seconds: Max wait time before fallback (default: 60s)

        Returns:
            (should_exit, reason)
            - should_exit=True when TP hit or timeout
            - reason indicates which position hit TP or "timeout"

        Instance Variables Used:
            - self.entry_prices: Dict with "ETH" and "SOL" entry prices
            - self.entry_quantities: Dict with "ETH" and "SOL" quantities
            - self._tp_hit_position: Set to "ETH" or "SOL" when TP hit
            - self._tp_hit_pnl_pct: Set to PNL % when TP hit
            - self.eth_client: NadoClient for ETH
            - self.sol_client: NadoClient for SOL
        """
        from decimal import Decimal
        import asyncio

        tp_threshold = Decimal(str(tp_threshold_bps / 10000))  # 0.02% for quicker exits
        POSITION_TOLERANCE = Decimal("0.001")

        start_time = time.time()
        check_interval = 1.0

        self.logger.info(
            f"[STATIC TP] Monitoring: TP={tp_threshold_bps}bps, "
            f"timeout={timeout_seconds}s"
        )

        # BLOCKING BEHAVIOR: This loop blocks until TP hit or timeout
        while time.time() - start_time < timeout_seconds:
            eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(
                self.eth_client.config.contract_id
            )
            sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(
                self.sol_client.config.contract_id
            )

            eth_entry_price = self.entry_prices.get("ETH") or Decimal("0")
            sol_entry_price = self.entry_prices.get("SOL") or Decimal("0")
            eth_qty = self.entry_quantities.get("ETH") or Decimal("0")
            sol_qty = self.entry_quantities.get("SOL") or Decimal("0")

            # Allow individual position monitoring - check each separately
            eth_available = eth_entry_price > 0 and eth_qty > 0
            sol_available = sol_entry_price > 0 and sol_qty > 0

            if not eth_available and not sol_available:
                self.logger.warning("[STATIC TP] No entry data available for either position")
                return False, "no_entry_data"

            # CRITICAL: Use tracked entry_directions, not derive from quantity sign
            # entry_quantities stores absolute values (always positive)
            eth_entry_direction = self.entry_directions.get("ETH", "buy")
            sol_entry_direction = self.entry_directions.get("SOL", "buy")
            eth_direction = "long" if eth_entry_direction == "buy" else "short"
            sol_direction = "long" if sol_entry_direction == "buy" else "short"

            eth_pnl_pct = Decimal("0")
            sol_pnl_pct = Decimal("0")

            if eth_available:
                if eth_direction == "long":
                    eth_pnl_pct = (eth_bid - eth_entry_price) / eth_entry_price
                else:
                    eth_pnl_pct = (eth_entry_price - eth_ask) / eth_entry_price

            if sol_available:
                if sol_direction == "long":
                    sol_pnl_pct = (sol_bid - sol_entry_price) / sol_entry_price
                else:
                    sol_pnl_pct = (sol_entry_price - sol_ask) / sol_entry_price

            self.logger.info(
                f"[STATIC TP] ETH: {eth_pnl_pct*100:.2f}% ({eth_direction}, {'active' if eth_available else 'inactive'}), "
                f"SOL: {sol_pnl_pct*100:.2f}% ({sol_direction}, {'active' if sol_available else 'inactive'}), target: +{tp_threshold_bps}bps"
            )

            if eth_available and eth_pnl_pct >= tp_threshold:
                self.logger.info(
                    f"[STATIC TP] ETH TP hit: {eth_pnl_pct*100:.2f}% >= {tp_threshold_bps}bps"
                )
                self._tp_hit_position = "ETH"
                self._tp_hit_pnl_pct = float(eth_pnl_pct) * 100
                return True, f"static_tp_eth_{eth_pnl_pct*100:.2f}bps"

            if sol_available and sol_pnl_pct >= tp_threshold:
                self.logger.info(
                    f"[STATIC TP] SOL TP hit: {sol_pnl_pct*100:.2f}% >= {tp_threshold_bps}bps"
                )
                self._tp_hit_position = "SOL"
                self._tp_hit_pnl_pct = float(sol_pnl_pct) * 100
                return True, f"static_tp_sol_{sol_pnl_pct*100:.2f}bps"

            await asyncio.sleep(check_interval)

        self.logger.info(
            f"[STATIC TP] Timeout after {timeout_seconds}s, "
            f"falling back to spread exit"
        )
        return False, "static_tp_timeout"

    async def _place_tp_orders(self) -> bool:
        """
        Place TP orders for both positions using trigger_client.

        TP orders are self-executing limit orders that fire when
        the trigger price is hit.

        Returns:
            True if both TP orders placed successfully
        """
        from decimal import Decimal
        from nado_protocol.utils.math import to_x18
        from nado_protocol.utils.subaccount import SubaccountParams
        from nado_protocol.engine_client.types.execute import ResponseStatus

        TP_THRESHOLD_BPS = 2  # 2bps = 0.02% for quicker exits
        tp_threshold = Decimal(str(TP_THRESHOLD_BPS / 10000))  # 0.02%

        self._tp_order_ids = {}  # Store for tracking

        for ticker in ["ETH", "SOL"]:
            client = self.eth_client if ticker == "ETH" else self.sol_client

            entry_price = self.entry_prices.get(ticker)
            entry_qty = self.entry_quantities.get(ticker, Decimal("0"))
            entry_direction = self.entry_directions.get(ticker, "buy")

            if not entry_price or entry_qty == 0:
                self.logger.warning(f"[TP] {ticker} skipping - no entry data")
                continue

            # Calculate TP trigger price
            if entry_direction == "buy":
                # Long position: TP above entry
                tp_trigger_price = entry_price * (Decimal("1") + tp_threshold)
                tp_amount = str(-to_x18(float(str(entry_qty))))  # Sell to close
            else:
                # Short position: TP below entry
                tp_trigger_price = entry_price * (Decimal("1") - tp_threshold)
                tp_amount = str(to_x18(float(str(entry_qty))))  # Buy to close

            # Round to tick size
            product_id = int(client.config.contract_id)
            tp_trigger_price_rounded = client._round_price_to_increment(
                product_id, tp_trigger_price
            )

            # Build sender params
            sender = SubaccountParams(
                subaccount_owner=client.owner,
                subaccount_name=client.subaccount_name,
            )

            try:
                # Long positions trigger when price rises, short when price falls
                trigger_type = "last_price_above" if entry_direction == "buy" else "last_price_below"

                result = client.client.context.trigger_client.place_price_trigger_order(
                    product_id=product_id,
                    price_x18=str(to_x18(float(str(tp_trigger_price_rounded)))),
                    amount_x18=tp_amount,
                    trigger_price_x18=str(to_x18(float(str(tp_trigger_price_rounded)))),
                    trigger_type=trigger_type,
                    sender=sender,
                    reduce_only=True,
                )

                if result and result.status == ResponseStatus.SUCCESS:
                    order_id = result.data.digest
                    self._tp_order_ids[ticker] = order_id
                    self.logger.info(
                        f"[TP] {ticker} TP order placed: {order_id} @ ${tp_trigger_price_rounded}"
                    )
                else:
                    error = result.error if result else "Unknown error"
                    self.logger.error(f"[TP] {ticker} failed to place TP: {error}")
                    return False

            except Exception as e:
                self.logger.error(f"[TP] {ticker} error placing TP: {e}")
                return False

        return True

    async def _maybe_place_tp_orders(self) -> None:
        """
        Place TP orders if configured.

        This is a conditional wrapper that checks if TP is enabled
        before placing orders. Makes it easy to disable TP if needed.
        """
        if not getattr(self, 'enable_tp_orders', True):
            self.logger.info("[TP] TP orders disabled, skipping")
            return

        success = await self._place_tp_orders()
        if success:
            self.logger.info(f"[TP] TP orders placed: {self._tp_order_ids}")
        else:
            self.logger.warning("[TP] Failed to place TP orders, continuing without TP")

    async def _verify_position_closed(self, ticker: str, max_wait_seconds: int = 10) -> bool:
        """Verify position is actually closed via both REST and WebSocket."""
        from decimal import Decimal
        import asyncio

        POSITION_TOLERANCE = Decimal("0.001")
        start_time = time.time()

        self.logger.info(f"[VERIFY] Starting position verification for {ticker}")

        while time.time() - start_time < max_wait_seconds:
            # Check REST API
            client = self.eth_client if ticker == "ETH" else self.sol_client
            rest_pos = await client.get_account_positions()

            # Check WebSocket (if available)
            ws_pos = self._ws_positions.get(ticker, Decimal("0")) if hasattr(self, '_ws_positions') else rest_pos

            self.logger.info(f"[VERIFY] {ticker} - REST={rest_pos}, WS={ws_pos}")

            if abs(rest_pos) < POSITION_TOLERANCE and abs(ws_pos) < POSITION_TOLERANCE:
                self.logger.info(f"[VERIFY] {ticker} confirmed closed")
                return True

            await asyncio.sleep(1)

        # CRITICAL: Position not closed after timeout
        self.logger.critical(f"[VERIFY] CRITICAL: {ticker} NOT CLOSED after {max_wait_seconds}s - REST={rest_pos}, WS={ws_pos}")
        return False

    async def _close_individual_position(self, ticker: str) -> bool:
        """
        Close individual position (ETH or SOL).

        Args:
            ticker: "ETH" or "SOL"

        Returns:
            True if position closed successfully (full or partial)
            False if order failed completely

        "Hedge break" definition: Period when one position is closed but the other
        remains open, exposing the bot to directional risk.

        Partial Fill Handling:
            - If order partially filled, accept partial fill and update entry_quantities
            - If order fails completely, return False to trigger emergency handling

        CRITICAL: Uses entry_quantities instead of get_account_positions() to avoid
        settlement delay issues where positions show 0.0 for 20+ seconds after fills.
        """
        from decimal import Decimal

        POSITION_TOLERANCE = Decimal("0.001")
        client = self.eth_client if ticker == "ETH" else self.sol_client
        contract_id = client.config.contract_id

        # CRITICAL: Use entry_quantities which we know are filled, not position checks which lag
        entry_qty = self.entry_quantities.get(ticker, Decimal("0"))
        entry_price = self.entry_prices.get(ticker)

        if entry_qty == Decimal("0") or abs(entry_qty) < POSITION_TOLERANCE:
            self.logger.info(f"[CLOSE] {ticker} no entry quantity to close (entry_qty={entry_qty})")
            return True

        if entry_price is None or entry_price == Decimal("0"):
            self.logger.warning(f"[CLOSE] {ticker} no entry price, cannot close (entry_price={entry_price})")
            return False

        # Determine close side from entry_direction (NOT from entry_qty sign)
        # entry_directions stores actual order direction: "buy" = long, "sell" = short
        # To close: opposite of entry direction
        entry_direction = self.entry_directions.get(ticker, "buy")
        close_side = "sell" if entry_direction == "buy" else "buy"
        close_qty = abs(entry_qty)

        bid, ask = await client.fetch_bbo_prices(contract_id)
        close_price = bid if close_side == "sell" else ask

        self.logger.info(
            f"[CLOSE] {ticker} {close_side} {close_qty} @ ${close_price} "
            f"(entry_qty={entry_qty}, entry_price=${entry_price})"
        )

        # Optional: Log position check for debugging (may show 0.0 due to lag)
        pos_check = await client.get_account_positions()
        self.logger.debug(f"[CLOSE] Position check (may lag): {ticker}={pos_check}")

        result = await client.place_limit_order_with_timeout(
            contract_id=contract_id,
            quantity=close_qty,
            direction=close_side,
            price=close_price,
            timeout_seconds=60
        )

        filled_size = self._get_filled_size(result)

        # Store exit price for PNL calculation
        if not hasattr(self, '_exit_prices'):
            self._exit_prices = {}
        if not hasattr(self, '_exit_quantities'):
            self._exit_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}

        if result.success and self._is_fill_complete(result):
            exit_price = result.price if result.price else entry_price
            self._exit_prices[ticker] = exit_price
            self._exit_quantities[ticker] += filled_size
            # DO NOT clear entry_quantities yet - verify position closed first
            # REMOVED: self.entry_quantities[ticker] = Decimal("0")

            # VERIFY position is actually closed before clearing state
            self.logger.info(f"[CLOSE] {ticker} order filled, verifying position closed...")
            verified = await self._verify_position_closed(ticker, max_wait_seconds=5)

            if verified:
                self.entry_quantities[ticker] = Decimal("0")
                self.logger.info(f"[CLOSE] {ticker} fully closed and verified: {filled_size}, exit_price={exit_price}")
                return True
            else:
                self.logger.critical(f"[CLOSE] CRITICAL: {ticker} order filled but position STILL OPEN! Attempting market order fallback...")

                # Market order fallback
                try:
                    close_side = "sell" if entry_qty > 0 else "buy"
                    market_result = await client.place_ioc_order(
                        contract_id=contract_id,
                        quantity=abs(entry_qty),
                        direction=close_side
                    )

                    # Re-verify
                    verified = await self._verify_position_closed(ticker, max_wait_seconds=5)
                    if verified:
                        self.entry_quantities[ticker] = Decimal("0")
                        self.logger.warning(f"[CLOSE] {ticker} closed via MARKET order fallback")
                        return True
                except Exception as e:
                    self.logger.critical(f"[CLOSE] FAILED to close {ticker} with market order: {e}")

                return False
        elif result.success and filled_size > POSITION_TOLERANCE:
            exit_price = result.price if result.price else entry_price
            self._exit_prices[ticker] = exit_price
            self._exit_quantities[ticker] += filled_size
            # Update entry quantity for remaining position
            self.entry_quantities[ticker] = entry_qty - filled_size
            self.logger.warning(
                f"[CLOSE] {ticker} partially closed: {filled_size}/{close_qty} "
                f"({float(filled_size/close_qty*100):.1f}%), remaining={entry_qty - filled_size}"
            )
            return True
        else:
            self.logger.error(
                f"[CLOSE] {ticker} failed: success={result.success}, "
                f"status={result.status if hasattr(result, 'status') else 'N/A'}, "
                f"error={result.error_message if hasattr(result, 'error_message') else 'N/A'}"
            )
            # RETRY: On timeout, try market order immediately
            if hasattr(result, 'status') and result.status == 'TIMEOUT':
                self.logger.warning(f"[CLOSE] {ticker} timeout - attempting immediate market order")
                try:
                    close_side = "sell" if entry_qty > 0 else "buy"
                    market_result = await client.place_ioc_order(
                        contract_id=contract_id,
                        quantity=abs(entry_qty),
                        direction=close_side
                    )
                    if market_result.success:
                        filled_size = self._get_filled_size(market_result)
                        self._exit_prices[ticker] = market_result.price if market_result.price else entry_price
                        self._exit_quantities[ticker] += filled_size
                        self.entry_quantities[ticker] = Decimal("0")
                        self.logger.info(f"[CLOSE] {ticker} closed via MARKET order after timeout: {filled_size}")
                        return True
                    else:
                        self.logger.critical(f"[CLOSE] {ticker} MARKET order also failed after timeout!")
                except Exception as e:
                    self.logger.critical(f"[CLOSE] {ticker} MARKET order exception after timeout: {e}")
            return False

    async def _check_and_close_remaining_position(self, closed_position: str) -> bool:
        """
        Check and close remaining position after individual TP close.

        Args:
            closed_position: "ETH" or "SOL" that was already closed

        Returns:
            True if all positions closed, False if error occurred
        """
        from decimal import Decimal

        POSITION_TOLERANCE = Decimal("0.001")

        remaining_ticker = "SOL" if closed_position == "ETH" else "ETH"
        remaining_client = self.eth_client if remaining_ticker == "ETH" else self.sol_client

        # Use WebSocket positions if available (more accurate, no settlement lag)
        if hasattr(self, '_ws_positions') and remaining_ticker in self._ws_positions:
            ws_pos = self._ws_positions[remaining_ticker]
            # Also check REST as backup
            rest_pos = await remaining_client.get_account_positions()
            self.logger.info(f"[CLOSE] {remaining_ticker} position check - WS={ws_pos}, REST={rest_pos}")

            # Use WebSocket position (more accurate)
            remaining_pos = ws_pos
        else:
            # Fallback to REST only
            remaining_pos = await remaining_client.get_account_positions()
            self.logger.info(f"[CLOSE] {remaining_ticker} position check (REST only) - {remaining_pos}")

        if abs(remaining_pos) < POSITION_TOLERANCE:
            self.logger.info(f"[CLOSE] No remaining {remaining_ticker} position")
            return True

        self.logger.info(
            f"[CLOSE] Remaining position: {remaining_ticker}={remaining_pos}"
        )

        should_exit, exit_reason = await self._check_exit_timing(max_loss_bps=30)

        if should_exit:
            self.logger.info(
                f"[CLOSE] Closing {remaining_ticker}: {exit_reason}"
            )
            return await self._close_individual_position(remaining_ticker)
        else:
            self.logger.warning(
                f"[CLOSE] Spread condition not met for {remaining_ticker}, "
                f"closing anyway to minimize hedge break time"
            )
            return await self._close_individual_position(remaining_ticker)

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
            eth_entry_price = self.entry_prices.get("ETH") or Decimal("0")
            sol_entry_price = self.entry_prices.get("SOL") or Decimal("0")
            eth_qty = self.entry_quantities.get("ETH") or Decimal("0")
            sol_qty = self.entry_quantities.get("SOL") or Decimal("0")

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

    def _get_filled_size(self, result) -> Decimal:
        """Extract filled_size from OrderResult with null-safety."""
        if result is None:
            return Decimal("0")
        if not hasattr(result, 'filled_size'):
            return Decimal("0")
        if result.filled_size is None:
            return Decimal("0")
        return result.filled_size

    def _is_fill_complete(self, result, expected_quantity: Decimal = None) -> bool:
        """Check if order is completely filled."""
        if result is None or not hasattr(result, 'success'):
            return False
        if not result.success:
            return False

        # Check status field - FILLED means complete
        if hasattr(result, 'status') and result.status == 'FILLED':
            return True

        filled = self._get_filled_size(result)

        # If expected_quantity provided, check if we filled >= 99% of it
        if expected_quantity is not None and expected_quantity > 0:
            fill_ratio = filled / expected_quantity
            self.logger.debug(f"[FILL] fill_ratio={fill_ratio:.2%}, filled={filled}, expected={expected_quantity}")
            return fill_ratio >= Decimal("0.99")

        return filled > Decimal("0.001")  # Legacy behavior when no expected quantity

    def _calculate_remaining_quantities(
        self,
        target_notional: Decimal,
        eth_price: Decimal,
        sol_price: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate remaining quantities based on filled amounts and current prices.
        Uses remaining notional (USD) to handle price changes between retries.
        """
        eth_filled_notional = Decimal("0")
        sol_filled_notional = Decimal("0")

        if self.entry_quantities.get("ETH", Decimal("0")) > Decimal("0"):
            eth_fill_price = self.entry_prices.get("ETH") or eth_price
            eth_filled_notional = self.entry_quantities["ETH"] * eth_fill_price

        if self.entry_quantities.get("SOL", Decimal("0")) > Decimal("0"):
            sol_fill_price = self.entry_prices.get("SOL") or sol_price
            sol_filled_notional = self.entry_quantities["SOL"] * sol_fill_price

        eth_remaining_notional = target_notional - eth_filled_notional
        sol_remaining_notional = target_notional - sol_filled_notional

        eth_remaining_qty = eth_remaining_notional / eth_price if eth_price > 0 else Decimal("0")
        sol_remaining_qty = sol_remaining_notional / sol_price if sol_price > 0 else Decimal("0")

        eth_remaining_qty = max(eth_remaining_qty, Decimal("0"))
        sol_remaining_qty = max(sol_remaining_qty, Decimal("0"))

        return eth_remaining_qty, sol_remaining_qty

    async def _retry_side_order(
        self,
        client,
        ticker: str,
        direction: str,
        quantity: Decimal,
        price: Decimal,
        bypass_queue_filter: bool = False
    ):
        """
        Retry a single side order with optional filter bypass.
        """
        contract_id = client.config.contract_id

        if bypass_queue_filter:
            self.logger.warning(
                f"[RETRY] Bypassing queue filter for {ticker} - "
                f"placing order at current market price"
            )
            result = await client.place_limit_order_with_timeout(
                contract_id=contract_id,
                quantity=quantity,
                price=price,
                direction=direction,
                timeout_seconds=30
            )
            return result
        else:
            # Use standard place_limit_order_with_timeout
            result = await client.place_limit_order_with_timeout(
                contract_id=contract_id,
                quantity=quantity,
                price=price,
                direction=direction
            )
            return result

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
        # NOTE: WebSocket positions are real-time; REST API has ~20s lag
        eth_pos = self._ws_positions.get("ETH", Decimal("0"))
        sol_pos = self._ws_positions.get("SOL", Decimal("0"))

        if abs(eth_pos) > POSITION_TOLERANCE or abs(sol_pos) > POSITION_TOLERANCE:
            self.logger.error(
                f"[BUILD] SAFETY VIOLATION: Cannot BUILD with open positions - "
                f"ETH={eth_pos} (WS), SOL={sol_pos} (WS). Run UNWIND first!"
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

        MAX_RETRIES = 3
        RETRY_DELAY = 2.0
        POSITION_TOLERANCE = Decimal("0.001")

        try:
            # Store entry phase flag for PNL tracking
            self._is_entry_phase = True

            # Reset entry quantities and prices for retry tracking
            self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
            self.entry_prices = {"ETH": None, "SOL": None}
            self.entry_directions = {"ETH": eth_direction, "SOL": sol_direction}

            eth_result, sol_result = await self.place_simultaneous_orders(eth_direction, sol_direction)

            # Extract initial fills
            eth_filled_size = self._get_filled_size(eth_result)
            sol_filled_size = self._get_filled_size(sol_result)

            self.logger.info(
                f"[BUILD] Initial fills: ETH={eth_filled_size}, SOL={sol_filled_size}"
            )

            # Check for filter SKIP (both failed with filter error)
            both_failed_filter = (
                isinstance(eth_result, OrderResult) and not eth_result.success and
                isinstance(sol_result, OrderResult) and not sol_result.success and
                eth_result.error_message and "Queue filter" in eth_result.error_message
            )
            if both_failed_filter:
                self.logger.warning(f"[BUILD] FILTER SKIP: {eth_result.error_message}")
                self._log_skipped_cycle(f"FILTER: {eth_result.error_message}")
                self._is_entry_phase = False
                return False

            # Check if both filled
            if self._is_fill_complete(eth_result) and self._is_fill_complete(sol_result):
                self.logger.info(f"[BUILD] Both orders filled successfully on first attempt")
                self._is_entry_phase = False
                await self._maybe_place_tp_orders()

                # Log spread analysis at entry if orders succeeded
                try:
                    self._log_spread_analysis(spread_info)
                except Exception as e:
                    self.logger.error(f"[CSV] Error logging spread analysis: {e}")

                return True

            # Retry loop for position imbalance
            latest_eth_result = eth_result
            latest_sol_result = sol_result

            # Track cumulative fills from OrderResult (not position checks which lag)
            cumulative_eth_filled = self._get_filled_size(eth_result)
            cumulative_sol_filled = self._get_filled_size(sol_result)
            self.logger.info(
                f"[BUILD] Initial cumulative fills: ETH={cumulative_eth_filled}, SOL={cumulative_sol_filled}"
            )

            for attempt in range(MAX_RETRIES):
                self.logger.warning(
                    f"[BUILD] Position imbalance detected (attempt {attempt + 1}/{MAX_RETRIES})"
                )

                await asyncio.sleep(RETRY_DELAY)

                # Fetch current prices
                eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
                sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

                # Calculate target quantities from notional
                eth_price = eth_bid if eth_direction == "buy" else eth_ask
                sol_price = sol_bid if sol_direction == "buy" else sol_ask
                target_eth_qty = self.target_notional / eth_price
                target_sol_qty = self.target_notional / sol_price

                # Calculate remaining based on cumulative fills (not positions)
                eth_remaining_qty = max(target_eth_qty - cumulative_eth_filled, Decimal("0"))
                sol_remaining_qty = max(target_sol_qty - cumulative_sol_filled, Decimal("0"))

                self.logger.info(
                    f"[BUILD] Cumulative fills: ETH={cumulative_eth_filled}/{target_eth_qty}, "
                    f"SOL={cumulative_sol_filled}/{target_sol_qty}"
                )
                self.logger.info(
                    f"[BUILD] Remaining quantities: ETH={eth_remaining_qty}, SOL={sol_remaining_qty}"
                )

                # Check positions for logging only (may show 0.0 before settlement)
                eth_pos = await self.eth_client.get_account_positions()
                sol_pos = await self.sol_client.get_account_positions()
                self.logger.info(f"[BUILD] Current positions (may lag): ETH={eth_pos}, SOL={sol_pos}")

                # Retry missing sides with filter bypass on 3rd attempt
                bypass_filter = (attempt >= 2)
                retry_results = []

                if eth_remaining_qty > Decimal("0.001"):
                    self.logger.info(
                        f"[BUILD] Retrying ETH {eth_direction} {eth_remaining_qty} @ ${eth_price}"
                    )
                    retry_result = await self._retry_side_order(
                        self.eth_client, "ETH", eth_direction, eth_remaining_qty, eth_price, bypass_filter
                    )
                    retry_results.append(("ETH", retry_result))
                    latest_eth_result = retry_result

                if sol_remaining_qty > Decimal("0.001"):
                    self.logger.info(
                        f"[BUILD] Retrying SOL {sol_direction} {sol_remaining_qty} @ ${sol_price}"
                    )
                    retry_result = await self._retry_side_order(
                        self.sol_client, "SOL", sol_direction, sol_remaining_qty, sol_price, bypass_filter
                    )
                    retry_results.append(("SOL", retry_result))
                    latest_sol_result = retry_result

                # Update entry quantities and cumulative fills from retry results
                for ticker, result in retry_results:
                    filled_size = self._get_filled_size(result)
                    if filled_size > Decimal("0.001"):
                        # Update cumulative fills for remaining quantity calculation
                        if ticker == "ETH":
                            cumulative_eth_filled += filled_size
                        elif ticker == "SOL":
                            cumulative_sol_filled += filled_size

                        # Update entry quantities and prices
                        if hasattr(result, 'price') and result.price:
                            self.entry_quantities[ticker] += filled_size
                            # Always update entry_prices on successful fills (use latest price)
                            # This ensures entry_prices is set even during retries with different prices
                            if result.price > 0:
                                self.entry_prices[ticker] = result.price
                            self.logger.info(
                                f"[BUILD] {ticker} retry filled: {filled_size} @ ${result.price}, "
                                f"cumulative: {cumulative_eth_filled if ticker == 'ETH' else cumulative_sol_filled}"
                            )

                # Check if all target quantities are now filled based on cumulative fills
                if cumulative_eth_filled >= target_eth_qty * Decimal("0.99") and cumulative_sol_filled >= target_sol_qty * Decimal("0.99"):
                    self.logger.info(
                        f"[BUILD] All target quantities filled: ETH={cumulative_eth_filled}/{target_eth_qty}, "
                        f"SOL={cumulative_sol_filled}/{target_sol_qty}. Waiting for positions to settle..."
                    )
                    # CRITICAL: Trust cumulative fills, not position checks which lag
                    # Position checks can show 0.0 for 20+ seconds after fills
                    if cumulative_eth_filled >= target_eth_qty * Decimal("0.99") and cumulative_sol_filled >= target_sol_qty * Decimal("0.99"):
                        self.logger.info(
                            f"[BUILD] Both positions filled (cumulative): ETH={cumulative_eth_filled}/{target_eth_qty}, "
                            f"SOL={cumulative_sol_filled}/{target_sol_qty}"
                        )

                        # Optional: Log position check for debugging (may show 0.0 due to lag)
                        eth_pos_check = await self.eth_client.get_account_positions()
                        sol_pos_check = await self.sol_client.get_account_positions()
                        self.logger.debug(f"[BUILD] Position check (may lag): ETH={eth_pos_check}, SOL={sol_pos_check}")

                        self._is_entry_phase = False
                        await self._maybe_place_tp_orders()

                        # Log spread analysis at entry if orders succeeded
                        try:
                            self._log_spread_analysis(spread_info)
                        except Exception as e:
                            self.logger.error(f"[CSV] Error logging spread analysis: {e}")

                        return True

            # After all retries, verify final state
            eth_pos = await self.eth_client.get_account_positions()
            sol_pos = await self.sol_client.get_account_positions()

            # CRITICAL FIX: Check if positions are imbalanced (one significantly larger than other)
            # This detects both "double entry" bugs and single-leg failures
            eth_significant = abs(eth_pos) > Decimal("0.01")
            sol_significant = abs(sol_pos) > Decimal("0.01")

            # If both have positions (double entry) OR one is significantly larger
            if (eth_significant and sol_significant) or (eth_significant != sol_significant):
                # Check for imbalance ratio (more than 10% difference)
                if eth_significant and sol_significant:
                    ratio = abs(eth_pos) / max(abs(sol_pos), Decimal("0.0001"))
                    if Decimal("0.9") <= ratio <= Decimal("1.1"):
                        # Positions are balanced, this is OK
                        self.logger.info(f"[BUILD] Both positions established and balanced")
                        self._is_entry_phase = False
                        await self._maybe_place_tp_orders()
                        return True

                # Positions are imbalanced or single-leg only - trigger emergency unwind
                self.logger.error(
                    f"[BUILD] FAILED: Positions still imbalanced after {MAX_RETRIES} retries: "
                    f"ETH={eth_pos}, SOL={sol_pos}"
                )
                # Trigger emergency unwind with latest results
                await self.handle_emergency_unwind(latest_eth_result, latest_sol_result)
                self._is_entry_phase = False
                return False

            self.logger.info(f"[BUILD] Both positions established")
            self._is_entry_phase = False
            await self._maybe_place_tp_orders()

            # Log spread analysis at entry if orders succeeded
            try:
                self._log_spread_analysis(spread_info)
            except Exception as e:
                self.logger.error(f"[CSV] Error logging spread analysis: {e}")

            return True
        except Exception as e:
            self.logger.error(f"[BUILD] Exception during build cycle: {e}")
            import traceback
            self.logger.error(f"[BUILD] Traceback: {traceback.format_exc()}")
            self._is_entry_phase = False

            # CRITICAL: Force close any open positions to prevent accumulation
            await self._verify_and_force_close_all_positions()
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
        # NOTE: WebSocket positions are real-time; REST API has ~20s lag
        eth_pos_before = self._ws_positions.get("ETH", Decimal("0"))
        sol_pos_before = self._ws_positions.get("SOL", Decimal("0"))
        self.logger.info(f"[UNWIND] POSITIONS BEFORE (WS): ETH={eth_pos_before}, SOL={sol_pos_before}")

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

        # Initialize exit tracking (separate from entry tracking)
        if not hasattr(self, '_exit_quantities'):
            self._exit_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        if not hasattr(self, '_exit_prices'):
            self._exit_prices = {"ETH": None, "SOL": None}

        # STATIC TP CHECK (if enabled) - Runs FIRST
        if self.enable_static_tp:
            self.logger.info("[UNWIND] Checking static TP conditions...")
            should_exit_tp, tp_reason = await self._monitor_static_individual_tp(
                tp_threshold_bps=self.tp_bps,
                timeout_seconds=self.tp_timeout
            )

            if should_exit_tp:
                self.logger.info(f"[EXIT] Static TP triggered: {tp_reason}")

                # SEQUENTIAL EXECUTION: Close TP-hit position first
                if hasattr(self, '_tp_hit_position') and self._tp_hit_position:
                    position_to_close = self._tp_hit_position
                    self.logger.info(f"[EXIT] Closing {position_to_close} (TP hit: {self._tp_hit_pnl_pct:.2f}bps)")

                    # Step 1: Close individual position that hit TP
                    close_success = await self._close_individual_position(position_to_close)

                    if not close_success:
                        self.logger.error(f"[EXIT] Failed to close {position_to_close}")
                        return False

                    # Step 2: Check and close remaining position
                    remaining_pos_check = await self._check_and_close_remaining_position(
                        closed_position=position_to_close
                    )

                    return remaining_pos_check

        # FALLBACK: Spread-based exit check (original logic)
        self.logger.info("[UNWIND] Checking spread-based exit conditions...")

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

        # Check if orders filled and add retry logic for partial fills
        MAX_ORDER_RETRIES = 3
        ORDER_RETRY_DELAY = 2.0

        # Check initial fill status using _is_fill_complete()
        eth_filled = (isinstance(eth_result, OrderResult) and
                      self._is_fill_complete(eth_result))
        sol_filled = (isinstance(sol_result, OrderResult) and
                      self._is_fill_complete(sol_result))

        if eth_filled and sol_filled:
            self.logger.info("[UNWIND] Both orders filled successfully")
        else:
            # One or both legs didn't fill - retry individual legs
            self.logger.warning(f"[UNWIND] Initial fill incomplete: ETH={eth_filled}, SOL={sol_filled}")

            latest_eth_result = eth_result
            latest_sol_result = sol_result

            # Get entry quantities to determine target close amounts
            eth_entry_qty = self.entry_quantities.get("ETH", Decimal("0"))
            sol_entry_qty = self.entry_quantities.get("SOL", Decimal("0"))

            # Track cumulative filled amounts from OrderResult (not position checks which lag)
            cumulative_eth_filled = self._get_filled_size(eth_result)
            cumulative_sol_filled = self._get_filled_size(sol_result)

            self.logger.info(
                f"[UNWIND] Initial cumulative fills: ETH={cumulative_eth_filled}/{eth_entry_qty}, "
                f"SOL={cumulative_sol_filled}/{sol_entry_qty}"
            )

            for attempt in range(MAX_ORDER_RETRIES):
                await asyncio.sleep(ORDER_RETRY_DELAY)

                # Get current prices
                eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
                sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

                # Calculate remaining based on cumulative fills (not positions which lag)
                # We need to close the full entry quantity
                eth_remaining_qty = max(eth_entry_qty - cumulative_eth_filled, Decimal("0"))
                sol_remaining_qty = max(sol_entry_qty - cumulative_sol_filled, Decimal("0"))

                # Determine which side needs retry based on cumulative fills
                retry_eth = cumulative_eth_filled < eth_entry_qty * Decimal("0.99")
                retry_sol = cumulative_sol_filled < sol_entry_qty * Decimal("0.99")

                self.logger.info(
                    f"[UNWIND] Cumulative fills: ETH={cumulative_eth_filled}/{eth_entry_qty}, "
                    f"SOL={cumulative_sol_filled}/{sol_entry_qty}"
                )
                self.logger.info(
                    f"[UNWIND] Remaining: ETH={eth_remaining_qty}, SOL={sol_remaining_qty}, "
                    f"retry_eth={retry_eth}, retry_sol={retry_sol}"
                )

                # Log positions for reference (may lag actual fills)
                eth_pos = await self.eth_client.get_account_positions()
                sol_pos = await self.sol_client.get_account_positions()
                self.logger.info(f"[UNWIND] Current positions (may lag): ETH={eth_pos}, SOL={sol_pos}")

                if not retry_eth and not retry_sol:
                    self.logger.info("[UNWIND] Both positions now closed, no retry needed")
                    break

                # Bypass queue filter on 3rd attempt
                bypass_queue_filter = (attempt >= 2)

                if retry_eth:
                    self.logger.info(f"[UNWIND] Retrying ETH: side={eth_side}, qty={eth_remaining_qty}")
                    eth_result = await self._retry_side_order(
                        self.eth_client, "ETH", eth_side, eth_remaining_qty,
                        eth_bid if eth_side == "buy" else eth_ask,
                        bypass_queue_filter
                    )
                    latest_eth_result = eth_result

                    # Track cumulative fills and exit quantities
                    filled_size = self._get_filled_size(eth_result)
                    if filled_size > POSITION_TOLERANCE:
                        cumulative_eth_filled += filled_size
                        self._exit_quantities["ETH"] += filled_size
                        # Always update exit_prices on successful fills (use latest price)
                        if eth_result.price and eth_result.price > 0:
                            self._exit_prices["ETH"] = eth_result.price
                        self.logger.info(
                            f"[UNWIND] ETH retry filled: {filled_size} @ {eth_result.price}, "
                            f"cumulative: {cumulative_eth_filled}/{eth_entry_qty}"
                        )

                if retry_sol:
                    self.logger.info(f"[UNWIND] Retrying SOL: side={sol_side}, qty={sol_remaining_qty}")
                    sol_result = await self._retry_side_order(
                        self.sol_client, "SOL", sol_side, sol_remaining_qty,
                        sol_bid if sol_side == "buy" else sol_ask,
                        bypass_queue_filter
                    )
                    latest_sol_result = sol_result

                    # Track cumulative fills and exit quantities
                    filled_size = self._get_filled_size(sol_result)
                    if filled_size > POSITION_TOLERANCE:
                        cumulative_sol_filled += filled_size
                        self._exit_quantities["SOL"] += filled_size
                        # Always update exit_prices on successful fills (use latest price)
                        if sol_result.price and sol_result.price > 0:
                            self._exit_prices["SOL"] = sol_result.price
                        self.logger.info(
                            f"[UNWIND] SOL retry filled: {filled_size} @ {sol_result.price}, "
                            f"cumulative: {cumulative_sol_filled}/{sol_entry_qty}"
                        )

                # Check if retry succeeded based on cumulative fills (99% of entry quantity)
                if (cumulative_eth_filled >= eth_entry_qty * Decimal("0.99") and
                    cumulative_sol_filled >= sol_entry_qty * Decimal("0.99")):
                    self.logger.info(
                        f"[UNWIND] Retry successful: ETH={cumulative_eth_filled}/{eth_entry_qty}, "
                        f"SOL={cumulative_sol_filled}/{sol_entry_qty}"
                    )
                    break

            # After order retry, check for emergency unwind condition
            # Use cumulative fills for accurate determination (not just latest result)
            eth_final_filled = cumulative_eth_filled >= eth_entry_qty * Decimal("0.99")
            sol_final_filled = cumulative_sol_filled >= sol_entry_qty * Decimal("0.99")

            if eth_final_filled and not sol_final_filled:
                self.logger.warning("[UNWIND] ETH filled but SOL failed after retries")
                await self.handle_emergency_unwind(latest_eth_result, latest_sol_result)
                return False
            elif sol_final_filled and not eth_final_filled:
                self.logger.warning("[UNWIND] SOL filled but ETH failed after retries")
                await self.handle_emergency_unwind(latest_eth_result, latest_sol_result)
                return False
            elif not eth_final_filled and not sol_final_filled:
                self.logger.error("[UNWIND] Both legs failed after retries")
                return False

        # Verify positions closed with retries
        for attempt in range(MAX_RETRIES):
            await asyncio.sleep(RETRY_DELAY)

            # NOTE: WebSocket positions are real-time; REST API has ~20s lag
            # Use WS for initial check, REST as backup/verification
            eth_pos_ws = self._ws_positions.get("ETH", Decimal("0"))
            sol_pos_ws = self._ws_positions.get("SOL", Decimal("0"))
            eth_pos_rest = await self.eth_client.get_account_positions()
            sol_pos_rest = await self.sol_client.get_account_positions()

            self.logger.info(
                f"[UNWIND] POSITIONS CHECK (attempt {attempt + 1}/{MAX_RETRIES}): "
                f"ETH WS={eth_pos_ws} REST={eth_pos_rest}, "
                f"SOL WS={sol_pos_ws} REST={sol_pos_rest}"
            )

            # Use WebSocket positions for real-time verification
            eth_pos = eth_pos_ws
            sol_pos = sol_pos_ws

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

                    # Check for position imbalance using WebSocket data
                    if hasattr(self, '_ws_positions'):
                        eth_pos = abs(self._ws_positions.get("ETH", Decimal("0")))
                        sol_pos = abs(self._ws_positions.get("SOL", Decimal("0")))
                        if sol_pos > 0:
                            ratio = float(eth_pos / sol_pos)
                            if ratio > 1.5 or ratio < 0.67:  # More than 50% imbalance
                                self.logger.warning(
                                    f"[POSITION IMBALANCE] ETH={eth_pos}, SOL={sol_pos}, ratio={ratio:.2f}"
                                )

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

        # Verify positions are closed before starting new cycle
        positions_verified = await self._verify_positions_before_build()
        if not positions_verified:
            self.logger.error("[CYCLE START] Positions not verified. Aborting cycle.")
            return False

        # Clear previous entry state
        self.entry_prices = {"ETH": None, "SOL": None}
        self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self.entry_directions = {"ETH": None, "SOL": None}  # CRITICAL: Reset entry directions to prevent stale data
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

                    # Check for position imbalance using WebSocket data
                    if hasattr(self, '_ws_positions'):
                        eth_pos = abs(self._ws_positions.get("ETH", Decimal("0")))
                        sol_pos = abs(self._ws_positions.get("SOL", Decimal("0")))
                        if sol_pos > 0:
                            ratio = float(eth_pos / sol_pos)
                            if ratio > 1.5 or ratio < 0.67:  # More than 50% imbalance
                                self.logger.warning(
                                    f"[POSITION IMBALANCE] ETH={eth_pos}, SOL={sol_pos}, ratio={ratio:.2f}"
                                )

                    elapsed += sleep_interval

            # UNWIND: Sell ETH / Buy SOL
            unwind_success = await self.execute_unwind_cycle("sell", "buy")

            # Update daily summary after cycle completes
            if unwind_success:
                self._update_daily_pnl_summary()

            return unwind_success

        except Exception as e:
            self.logger.error(f"BUY_FIRST cycle failed: {e}")
            # CRITICAL: Force close any open positions to prevent accumulation
            await self._verify_and_force_close_all_positions()
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

        # Verify positions are closed before starting new cycle
        positions_verified = await self._verify_positions_before_build()
        if not positions_verified:
            self.logger.error("[CYCLE START] Positions not verified. Aborting cycle.")
            return False

        # Clear previous entry state
        self.entry_prices = {"ETH": None, "SOL": None}
        self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
        self.entry_directions = {"ETH": None, "SOL": None}  # CRITICAL: Reset entry directions to prevent stale data
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

                    # Check for position imbalance using WebSocket data
                    if hasattr(self, '_ws_positions'):
                        eth_pos = abs(self._ws_positions.get("ETH", Decimal("0")))
                        sol_pos = abs(self._ws_positions.get("SOL", Decimal("0")))
                        if sol_pos > 0:
                            ratio = float(eth_pos / sol_pos)
                            if ratio > 1.5 or ratio < 0.67:  # More than 50% imbalance
                                self.logger.warning(
                                    f"[POSITION IMBALANCE] ETH={eth_pos}, SOL={sol_pos}, ratio={ratio:.2f}"
                                )

                    elapsed += sleep_interval

            # UNWIND: Buy ETH / Sell SOL
            unwind_success = await self.execute_unwind_cycle("buy", "sell")

            # Update daily summary after cycle completes
            if unwind_success:
                self._update_daily_pnl_summary()

            return unwind_success

        except Exception as e:
            self.logger.error(f"SELL_FIRST cycle failed: {e}")
            # CRITICAL: Force close any open positions to prevent accumulation
            await self._verify_and_force_close_all_positions()
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

        # Subscribe to position changes for real-time monitoring
        from hedge.exchanges.nado import WEBSOCKET_AVAILABLE

        if WEBSOCKET_AVAILABLE:
            # Subscribe to ETH position changes
            if self.eth_client._ws_client:
                try:
                    await self.eth_client._ws_client.subscribe(
                        stream_type="position_change",
                        product_id=self.eth_client.config.contract_id,
                        subaccount=self.eth_client.subaccount_hex,
                        callback=self._on_position_change
                    )
                    self.logger.info("[INIT] Subscribed to ETH position_change stream")
                except Exception as e:
                    self.logger.warning(f"[INIT] Failed to subscribe to ETH position_change: {e}")

            # Subscribe to SOL position changes
            if self.sol_client._ws_client:
                try:
                    await self.sol_client._ws_client.subscribe(
                        stream_type="position_change",
                        product_id=self.sol_client.config.contract_id,
                        subaccount=self.sol_client.subaccount_hex,
                        callback=self._on_position_change
                    )
                    self.logger.info("[INIT] Subscribed to SOL position_change stream")
                except Exception as e:
                    self.logger.warning(f"[INIT] Failed to subscribe to SOL position_change: {e}")
        else:
            self.logger.info("[INIT] WebSocket not available - position_change streaming disabled")















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
        help='Accept partial fills >= 50%% of order size'
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

    # Static TP parameters (Phase 2)
    parser.add_argument(
        '--enable-static-tp',
        action='store_true',
        help='Enable static individual TP per position (default: disabled)'
    )
    parser.add_argument(
        '--tp-bps',
        type=float,
        default=10.0,
        help='TP threshold in bps per position (default: 10.0)'
    )
    parser.add_argument(
        '--tp-timeout',
        type=int,
        default=60,
        help='Max wait time for TP hit before fallback in seconds (default: 60)'
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
        # Static TP parameters (Phase 2)
        enable_static_tp=getattr(args, 'enable_static_tp', False),
        tp_bps=getattr(args, 'tp_bps', 10.0),
        tp_timeout=getattr(args, 'tp_timeout', 60),
    )

    # Initialize clients
    await bot.initialize_clients()

    # STARTUP CHECK: Verify no residual positions
    # Use WebSocket positions for real-time detection (REST API has 20+ second lag)
    print("\n[STARTUP] Checking for residual positions...")

    # Wait for WebSocket to receive initial position sync
    await bot._wait_for_ws_position_sync(timeout=5.0)

    # Check for residual positions using WebSocket priority
    await bot._check_residual_positions_at_startup()

    # Run alternating strategy
    await bot.run_alternating_strategy()


if __name__ == "__main__":
    asyncio.run(main())
