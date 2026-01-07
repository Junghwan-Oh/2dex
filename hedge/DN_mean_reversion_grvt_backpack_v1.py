#!/usr/bin/env python3
"""
Delta Neutral (DN) Hedge Mode: GRVT + Backpack

Usage:
    python hedge_mode_paradex_grvt.py --ticker SOL --size 1 --iter 10
    python hedge_mode_paradex_grvt.py --ticker SOL --size 1 --iter 10 --primary-mode bbo_minus_1 --hedge-mode market
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
from typing import Tuple, Optional
from datetime import datetime
from enum import Enum
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.backpack import BackpackClient
from exchanges.grvt import GrvtClient


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


class DNHedgeBot:
    def __init__(
        self,
        ticker: str,
        order_quantity: Decimal,
        fill_timeout: int = 5,
        iterations: int = 20,
        sleep_time: int = 0,
        max_position: Decimal = Decimal("0"),
        primary_exchange: str = "grvt",
        hedge_exchange: str = "backpack",
        primary_mode: PriceMode = PriceMode.BBO_MINUS_1,
        hedge_mode: PriceMode = PriceMode.MARKET,
        min_spread_bps: Decimal = Decimal("0"),
    ):
        self.ticker = ticker
        self.order_quantity = order_quantity
        self.fill_timeout = fill_timeout
        self.iterations = iterations
        self.sleep_time = sleep_time
        self.primary_exchange = primary_exchange.lower()
        self.hedge_exchange = hedge_exchange.lower()
        self.primary_mode = primary_mode
        self.hedge_mode = hedge_mode
        self.min_spread_bps = min_spread_bps
        self.strategy = "mean_reversion"  # Fixed strategy for this file

        self.max_position = (
            order_quantity if max_position == Decimal("0") else max_position
        )

        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/dn_mean_reversion_grvt_backpack_{self.primary_exchange}_{self.hedge_exchange}_{ticker}_log.txt"
        self.csv_filename = f"logs/dn_mean_reversion_grvt_backpack_{self.primary_exchange}_{self.hedge_exchange}_{ticker}_trades.csv"

        self._initialize_csv_file()
        self._setup_logger()

        self.stop_flag = False
        self.order_counter = 0

        self.primary_position = Decimal("0")
        self.hedge_position = Decimal("0")

        # Local position tracking (like original hedge_mode_grvt.py)
        self.local_primary_position = Decimal("0")
        self.local_hedge_position = Decimal("0")

        # Position change tracking for fill confirmation
        self.last_primary_fill_size = Decimal("0")
        self.last_hedge_fill_size = Decimal("0")
        self.last_primary_fill_side = None
        self.last_hedge_fill_side = None

        self.use_local_tracking = True
        self.reconcile_interval = 1  # Reconcile every cycle for tighter drift control

        self.primary_client = None
        self.hedge_client = None

        self.primary_contract_id = None
        self.primary_tick_size = None
        self.hedge_contract_id = None
        self.hedge_tick_size = None

        self.primary_order_status = None
        self.hedge_order_filled = False
        self.order_execution_complete = False
        self.waiting_for_hedge_fill = False

        self.current_hedge_side = None
        self.current_hedge_quantity = None
        self.current_hedge_price = None

        self.total_gross_pnl = Decimal("0")
        self.total_volume = Decimal("0")
        self.completed_cycles = 0

    def _setup_logger(self):
        self.logger = logging.getLogger(f"dn_hedge_{self.ticker}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        for lib in ["urllib3", "requests", "websockets", "pysdk", "paradex_py"]:
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
    ):
        timestamp = datetime.now(pytz.UTC).isoformat()
        with open(self.csv_filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [exchange, timestamp, side, price, quantity, order_type, mode]
            )

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
            f"  PARADEX: {primary_side.upper():4} @ ${primary_price:.3f}\n"
            f"  GRVT:    {hedge_side.upper():4} @ ${hedge_price:.3f}\n"
            f"  Spread: ${spread:.4f} ({spread_bps:+.2f} bps)\n"
            f"  Cycle PnL: ${gross_pnl:.4f}\n"
            f"{'-' * 55}\n"
            f"  CUMULATIVE: {self.completed_cycles} cycles | PnL: ${self.total_gross_pnl:.4f} | Avg: {avg_pnl_bps:+.2f} bps\n"
            f"{'-' * 55}"
        )

    async def cleanup_connections(self):
        if self.hedge_client:
            try:
                await self.hedge_client.disconnect()
            except Exception:
                pass
        if self.primary_client:
            try:
                await self.primary_client.disconnect()
            except Exception:
                pass

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

    async def should_enter_trade(self) -> Optional[str]:
        """
        Mean Reversion: Compare mid prices and decide direction

        - GRVT (primary) > Paradex (hedge) → GRVT SHORT (sell)
        - GRVT (primary) < Paradex (hedge) → GRVT LONG (buy)

        Returns:
            "sell": GRVT에서 SHORT 진입
            "buy": GRVT에서 LONG 진입
            None: 스프레드 부족으로 진입 안함
        """
        # BBO 가격 가져오기
        primary_bid, primary_ask = await self.primary_client.fetch_bbo_prices(
            self.primary_contract_id
        )
        hedge_bid, hedge_ask = await self.hedge_client.fetch_bbo_prices(
            self.hedge_contract_id
        )

        # Mid price 계산
        primary_mid = (primary_bid + primary_ask) / 2  # GRVT mid
        hedge_mid = (hedge_bid + hedge_ask) / 2  # Paradex mid

        # 가격 비교 (핵심!)
        if primary_mid > hedge_mid:
            # GRVT가 높음 → Mean Reversion: GRVT에서 SHORT
            spread = primary_mid - hedge_mid
            spread_bps = (spread / hedge_mid) * Decimal("10000")
            direction = "sell"  # GRVT에서 SELL
        elif primary_mid < hedge_mid:
            # GRVT가 낮음 → Mean Reversion: GRVT에서 LONG
            spread = hedge_mid - primary_mid
            spread_bps = (spread / primary_mid) * Decimal("10000")
            direction = "buy"  # GRVT에서 BUY
        else:
            self.logger.debug(f"[ARB] Mid prices equal, no spread")
            return None

        # 스프레드 임계값 체크
        min_spread = self.min_spread_bps if self.min_spread_bps > 0 else Decimal("-100")

        if spread_bps >= min_spread:
            self.logger.info(
                f"[ARB] GRVT mid: {primary_mid:.4f}, Paradex mid: {hedge_mid:.4f}, "
                f"Spread: {spread_bps:.2f} bps -> {direction.upper()}"
            )
            return direction
        else:
            self.logger.debug(
                f"[ARB] Spread: {spread_bps:.2f} bps < {min_spread} bps -> SKIP"
            )
            return None

    async def initialize_clients(self):
        config = self._create_exchange_config(self.ticker, self.order_quantity)

        if self.primary_exchange == "paradex":
            self.primary_client = BackpackClient(config)
        elif self.primary_exchange == "grvt":
            self.primary_client = GrvtClient(config)
        else:
            raise ValueError(f"Unsupported primary exchange: {self.primary_exchange}")
        self.logger.info(
            f"[INIT] PRIMARY: {self.primary_exchange.upper()} (mode: {self.primary_mode.value})"
        )

        hedge_config = self._create_exchange_config(self.ticker, self.order_quantity)
        if self.hedge_exchange == "grvt":
            self.hedge_client = GrvtClient(hedge_config)
        elif self.hedge_exchange == "paradex":
            self.hedge_client = BackpackClient(hedge_config)
        else:
            raise ValueError(f"Unsupported hedge exchange: {self.hedge_exchange}")
        self.logger.info(
            f"[INIT] HEDGE: {self.hedge_exchange.upper()} (mode: {self.hedge_mode.value})"
        )

        (
            self.primary_contract_id,
            self.primary_tick_size,
        ) = await self.primary_client.get_contract_attributes()
        (
            self.hedge_contract_id,
            self.hedge_tick_size,
        ) = await self.hedge_client.get_contract_attributes()

        self.logger.info(
            f"[INIT] PRIMARY contract: {self.primary_contract_id}, tick: {self.primary_tick_size}"
        )
        self.logger.info(
            f"[INIT] HEDGE contract: {self.hedge_contract_id}, tick: {self.hedge_tick_size}"
        )

    async def connect_websockets(self):
        def primary_order_handler(order_data):
            self._handle_primary_order_update(order_data)

        self.primary_client.setup_order_update_handler(primary_order_handler)
        await self.primary_client.connect()
        self.logger.info(f"[WS] PRIMARY ({self.primary_exchange.upper()}) connected")

        # Connect to hedge exchange with retries and longer timeout
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(
                    f"[WS] Connecting to HEDGE (attempt {attempt}/{max_retries})..."
                )
                # Increased timeout from 60s to 120s to allow for slower Paradex WebSocket connection
                await asyncio.wait_for(self.hedge_client.connect(), timeout=120.0)
                self.logger.info(
                    f"[WS] HEDGE ({self.hedge_exchange.upper()}) connected"
                )
                break
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"[WS] HEDGE connection timeout (attempt {attempt}/{max_retries})"
                )
                if attempt < max_retries:
                    self.logger.info("[WS] Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    self.logger.error("[WS] HEDGE connection failed after all retries")
                    raise
            except Exception as e:
                self.logger.warning(
                    f"[WS] HEDGE connection error: {e} (attempt {attempt}/{max_retries})"
                )
                if attempt < max_retries:
                    self.logger.info("[WS] Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    self.logger.error("[WS] HEDGE connection failed after all retries")
                    raise

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

    async def get_positions(self, force_api: bool = False) -> Tuple[Decimal, Decimal]:
        if self.use_local_tracking and not force_api:
            # PRIMARY: Use WebSocket (GRVT WebSocket is reliable)
            primary_pos = self.primary_client.get_ws_position()

            # HEDGE: ALWAYS use REST API for Paradex (WebSocket unreliable)
            if self.hedge_exchange == "paradex":
                hedge_pos = await self.hedge_client.get_account_positions()
            else:
                hedge_pos = self.hedge_client.get_ws_position()
        else:
            # Force REST API positions (slower but authoritative)
            primary_pos = await self.primary_client.get_account_positions()
            hedge_pos = await self.hedge_client.get_account_positions()

        return primary_pos, hedge_pos

    async def reconcile_positions(self):
        """Reconcile positions from both exchanges using multiple sources."""
        try:
            # Get WebSocket positions first (faster, no API calls)
            ws_primary = self.primary_client.get_ws_position()
            ws_hedge = self.hedge_client.get_ws_position()

            # Also get REST API positions for confirmation
            api_primary, api_hedge = await self.get_positions(force_api=True)

            # Use the larger absolute position (most reliable source)
            primary_pos = (
                ws_primary if abs(ws_primary) >= abs(api_primary) else api_primary
            )
            hedge_pos = ws_hedge if abs(ws_hedge) >= abs(api_hedge) else api_hedge

            # Update instance variables
            self.primary_position = primary_pos
            self.hedge_position = hedge_pos

            # Update local tracking to match actual positions
            self.local_primary_position = primary_pos
            self.local_hedge_position = hedge_pos

            # Calculate net delta
            net_delta = primary_pos + hedge_pos

            self.logger.info(
                f"[RECONCILE] PRIMARY: {primary_pos} (WS:{ws_primary}, API:{api_primary}) | "
                f"HEDGE: {hedge_pos} (WS:{ws_hedge}, API:{api_hedge}) | Net: {net_delta}"
            )

            # Check for position imbalance (like original hedge_mode_grvt.py)
            if abs(net_delta) > self.order_quantity * Decimal("2"):
                self.logger.error(
                    f"[RECONCILE] CRITICAL: Position imbalance too large! "
                    f"Primary: {primary_pos}, Hedge: {hedge_pos}, Net: {net_delta}"
                )
                self.logger.error("[RECONCILE] Stopping bot to prevent further losses")
                self.logger.error("[RECONCILE] Attempting to close all positions...")
                await self.force_close_all_positions()
                self.stop_flag = True

        except Exception as e:
            self.logger.error(f"Error reconciling positions: {e}")
            self.logger.error(traceback.format_exc())

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
                # Convert side based on exchange type
                if self.primary_exchange == "paradex":
                    from paradex_py.common.order import OrderSide

                    order_side = OrderSide.Buy if side == "buy" else OrderSide.Sell
                else:
                    order_side = side  # GRVT expects lowercase string

                order_result = await self.primary_client.place_post_only_order(
                    contract_id=self.primary_contract_id,
                    quantity=quantity,
                    price=order_price,
                    side=order_side,
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
                            await asyncio.sleep(0.5)

                            if time.time() - start_time > 10:
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
                            await asyncio.sleep(0.5)

                else:
                    self.logger.warning("Order placement failed, retrying...")
                    await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error placing PRIMARY order: {e}")
                await asyncio.sleep(1)

        return None

    async def place_hedge_order(
        self, side: str, quantity: Decimal, reference_price: Decimal
    ) -> bool:
        self.hedge_order_filled = False
        order_type = "CLOSE" if side == "buy" else "OPEN"
        maker_timeout = 15  # Reduced from 30s for faster position resolution

        use_maker_mode = self.hedge_mode in [PriceMode.BBO_MINUS_1, PriceMode.BBO]

        max_retries = 4  # Increased retries for better reliability
        for attempt in range(1, max_retries + 1):
            try:
                best_bid, best_ask = await self.hedge_client.fetch_bbo_prices(
                    self.hedge_contract_id
                )

                # CLOSE operations: use AGGRESSIVE mode for immediate fill
                is_close = side == "buy"  # CLOSE = BUY on hedge (closing SHORT)

                if is_close:
                    # AGGRESSIVE: use best ask/bid for immediate fill
                    if side == "buy":
                        order_price = best_ask  # BUY at best ask -> immediate fill
                    else:
                        order_price = best_bid  # SELL at best bid -> immediate fill
                    order_mode = "AGGRESSIVE"
                elif use_maker_mode and attempt <= 1:
                    # OPEN with maker mode
                    if side == "buy":
                        order_price = best_bid - self.hedge_tick_size
                    else:
                        order_price = best_ask + self.hedge_tick_size
                    order_mode = "MAKER"
                else:
                    # OPEN with taker fallback - reprice if needed
                    if side == "buy":
                        order_price = best_ask + (self.hedge_tick_size * Decimal("2"))
                    else:
                        order_price = best_bid - (self.hedge_tick_size * Decimal("2"))
                    order_mode = "TAKER_FALLBACK"

                order_price = self.hedge_client.round_to_tick(order_price)

                self.logger.info(
                    f"[{order_type}] [{self.hedge_exchange.upper()}] [{side.upper()}] "
                    f"{order_mode} @ {order_price} (BBO: {best_bid}/{best_ask}, attempt {attempt}/{max_retries})"
                )

                if self.hedge_exchange == "paradex":
                    from paradex_py.common.order import OrderSide

                    order_side = OrderSide.Buy if side == "buy" else OrderSide.Sell
                else:
                    order_side = side

                pos_before = self.hedge_client.get_ws_position()

                if order_mode == "TAKER_FALLBACK" and hasattr(
                    self.hedge_client, "place_aggressive_limit_order"
                ):
                    await self.hedge_client.place_aggressive_limit_order(
                        contract_id=self.hedge_contract_id,
                        quantity=quantity,
                        price=order_price,
                        side=order_side,
                    )
                    # Wait for fill confirmation with REST API fallback
                    start_wait = time.time()
                    while (
                        time.time() - start_wait < 5
                    ):  # Wait up to 5 seconds for aggressive orders
                        await asyncio.sleep(0.1)

                        # Check both WebSocket and REST API positions
                        pos_ws = self.hedge_client.get_ws_position()
                        pos_api = pos_ws
                        try:
                            pos_api = await self.hedge_client.get_account_positions()
                        except Exception:
                            pass

                        pos_change = max(
                            abs(pos_ws - pos_before), abs(pos_api - pos_before)
                        )
                        if pos_change >= quantity * Decimal("0.99"):
                            break
                else:
                    await self.hedge_client.place_post_only_order(
                        contract_id=self.hedge_contract_id,
                        quantity=quantity,
                        price=order_price,
                        side=order_side,
                    )

                    start_wait = time.time()
                    while time.time() - start_wait < maker_timeout:
                        await asyncio.sleep(1)
                        pos_current = self.hedge_client.get_ws_position()
                        # Fallback to REST API if WebSocket position is 0 but we expect a fill
                        if pos_current == pos_before:
                            try:
                                pos_current = (
                                    await self.hedge_client.get_account_positions()
                                )
                            except Exception:
                                pass
                        if abs(pos_current - pos_before) >= quantity * Decimal("0.99"):
                            break

                        # For CLOSE operations, don't reprice - just retry at current BBO
                        if not is_close:
                            new_bid, new_ask = await self.hedge_client.fetch_bbo_prices(
                                self.hedge_contract_id
                            )
                            # Check if order price is still within spread (not crossed)
                            if (
                                side == "buy"
                                and order_price > new_ask + self.hedge_tick_size
                            ):
                                self.logger.info(
                                    f"[{order_type}] BUY price {order_price} > ask {new_ask}, repricing..."
                                )
                                break
                            elif (
                                side == "sell"
                                and order_price < new_bid - self.hedge_tick_size
                            ):
                                self.logger.info(
                                    f"[{order_type}] SELL price {order_price} < bid {new_bid}, repricing..."
                                )
                                break

                # Check position change - prefer REST API for definitive answer
                pos_after_ws = self.hedge_client.get_ws_position()
                pos_change_ws = abs(pos_after_ws - pos_before)

                # For CLOSE operations, be more aggressive with REST API checks
                if is_close:
                    # Check REST API immediately for CLOSE operations
                    try:
                        pos_after_api = await self.hedge_client.get_account_positions()
                        pos_change_api = abs(pos_after_api - pos_before)

                        self.logger.info(
                            f"[{order_type}] REST API position check: {pos_before} -> {pos_after_api} (change: {pos_change_api})"
                        )

                        if pos_change_api >= quantity * Decimal("0.99"):
                            actual_fill_price = best_ask if side == "buy" else best_bid
                            self.logger.info(
                                f"[{order_type}] [{self.hedge_exchange.upper()}] [FILLED via REST]: "
                                f"{quantity} @ ~{actual_fill_price} (API: {pos_before} -> {pos_after_api})"
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
                    except Exception as e:
                        self.logger.warning(
                            f"[{order_type}] REST API check failed: {e}, falling back to WS"
                        )

                # Also check REST API for confirmation
                pos_after_api = pos_after_ws
                try:
                    pos_after_api = await self.hedge_client.get_account_positions()
                except Exception:
                    pass
                pos_change_api = abs(pos_after_api - pos_before)

                # Use the larger change for confirmation
                position_change = max(pos_change_ws, pos_change_api)

                if position_change >= quantity * Decimal("0.99"):
                    actual_fill_price = best_ask if side == "buy" else best_bid

                    self.logger.info(
                        f"[{order_type}] [{self.hedge_exchange.upper()}] [FILLED]: "
                        f"{quantity} @ ~{actual_fill_price} (WS: {pos_before} -> {pos_after_ws}, API: {pos_before} -> {pos_after_api})"
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
                    self.logger.warning(
                        f"[{order_type}] Hedge fill not confirmed! "
                        f"Expected: +/-{quantity}, WS change: {pos_change_ws:+0.04f}, API change: {pos_change_api:+0.04f}"
                    )

            except Exception as e:
                self.logger.error(
                    f"Error placing HEDGE order (attempt {attempt}/{max_retries}): {e}"
                )
                if attempt < max_retries:
                    self.logger.info(f"Retrying hedge order in 1 second...")
                    await asyncio.sleep(1)
                else:
                    self.logger.error(f"All {max_retries} hedge attempts failed!")
                    self.logger.error(traceback.format_exc())

        self.logger.error(
            "[EMERGENCY] Hedge order failed after all retries, closing primary position!"
        )
        await self.emergency_close_primary(quantity, side)
        return False

    async def force_close_all_positions(self):
        """Force close all positions (like original ext.py STEP 3)."""
        try:
            # Check both exchanges
            for exchange_name, client in [
                ("PRIMARY", self.primary_client),
                ("HEDGE", self.hedge_client),
            ]:
                if client is None:
                    continue

                # Get current position
                ws_pos = client.get_ws_position()
                if ws_pos == 0:
                    continue

                self.logger.warning(
                    f"[FORCE_CLOSE] {exchange_name} has residual position: {ws_pos}, forcing close"
                )

                # Determine close side
                if ws_pos > 0:
                    close_side = "sell"
                else:
                    close_side = "buy"

                close_qty = abs(ws_pos)

                # Determine contract_id for this client
                if exchange_name == "PRIMARY":
                    contract_id = self.primary_contract_id
                else:  # HEDGE
                    contract_id = self.hedge_contract_id

                # Get BBO and place market order
                best_bid, best_ask = await client.fetch_bbo_prices(contract_id)

                if close_side == "buy":
                    close_price = best_ask + (client.tick_size * Decimal("2"))
                else:
                    close_price = best_bid - (client.tick_size * Decimal("2"))

                close_price = client.round_to_tick(close_price)

                self.logger.warning(
                    f"[FORCE_CLOSE] {exchange_name} {close_side.upper()} {close_qty} @ {close_price}"
                )

                # Place aggressive close order
                if hasattr(client, "place_aggressive_limit_order"):
                    await client.place_aggressive_limit_order(
                        contract_id=contract_id,
                        quantity=close_qty,
                        price=close_price,
                        side=close_side,
                    )
                else:
                    await client.place_post_only_order(
                        contract_id=contract_id,
                        quantity=close_qty,
                        price=close_price,
                        side=close_side,
                    )

                # Wait for fill
                await asyncio.sleep(2)

                new_pos = client.get_ws_position()
                self.logger.warning(
                    f"[FORCE_CLOSE] {exchange_name} position after close: {new_pos}"
                )

        except Exception as e:
            self.logger.error(f"[FORCE_CLOSE] Error: {e}")

    async def emergency_close_primary(self, quantity: Decimal, failed_hedge_side: str):
        close_side = failed_hedge_side

        self.logger.warning(
            f"[EMERGENCY] Closing PRIMARY position: {close_side.upper()} {quantity}"
        )

        try:
            # For emergency close, use market order to guarantee execution
            # (POST_ONLY might fail if price crosses spread)
            if self.primary_exchange == "grvt":
                # GRVT: use market order
                await self.primary_client.place_market_order(
                    contract_id=self.primary_contract_id,
                    quantity=quantity,
                    side=close_side,
                )
                price = "MARKET"  # For logging
            else:
                # Paradex: use aggressive limit order
                best_bid, best_ask = await self.primary_client.fetch_bbo_prices(
                    self.primary_contract_id
                )
                if close_side == "buy":
                    price = best_ask * Decimal("1.005")
                else:
                    price = best_bid * Decimal("0.995")

                from paradex_py.common.order import OrderSide

                order_side = OrderSide.Buy if close_side == "buy" else OrderSide.Sell
                await self.primary_client.place_post_only_order(
                    contract_id=self.primary_contract_id,
                    quantity=quantity,
                    price=price,
                    side=order_side,
                )

            # Update local position tracking
            if close_side == "buy":
                self.local_primary_position -= quantity
            else:
                self.local_primary_position += quantity

            # Wait for fill confirmation
            start_wait = time.time()
            filled = False

            while time.time() - start_wait < 10 and not filled:
                await asyncio.sleep(0.5)

                # Check via REST API (more reliable)
                try:
                    pos_current = await self.primary_client.get_account_positions()
                    pos_change = abs(pos_current - pos_before)
                    if pos_change >= quantity * Decimal("0.99"):
                        filled = True
                        self.logger.warning(
                            f"[EMERGENCY] PRIMARY position closed: {pos_before} -> {pos_current}"
                        )
                except Exception as e:
                    self.logger.debug(f"[EMERGENCY] Position check failed: {e}")

            if not filled:
                self.logger.error(f"[EMERGENCY] PRIMARY position close NOT confirmed!")

            self.logger.warning(
                f"[EMERGENCY] Close order placed: {close_side.upper()} {quantity} @ {price}"
            )

            self.log_trade_to_csv(
                exchange=self.primary_exchange.upper(),
                side=close_side,
                price=str(price),
                quantity=str(quantity),
                order_type="emergency_close",
                mode="aggressive",
            )

        except Exception as e:
            self.logger.error(f"[EMERGENCY] Failed to close primary position: {e}")
            self.logger.error(traceback.format_exc())
            self.stop_flag = True

    async def execute_dn_cycle(
        self, direction: str
    ) -> Tuple[bool, Optional[Decimal], Optional[Decimal]]:
        self.order_execution_complete = False
        self.waiting_for_hedge_fill = False

        order_id = await self.place_primary_order(direction, self.order_quantity)

        if order_id is None:
            return False, None, None

        start_time = time.time()
        primary_fill_price = None
        hedge_fill_price = None

        while not self.order_execution_complete and not self.stop_flag:
            if self.waiting_for_hedge_fill:
                primary_fill_price = self.current_hedge_price
                success = await self.place_hedge_order(
                    self.current_hedge_side,
                    self.current_hedge_quantity,
                    self.current_hedge_price,
                )
                if success and hasattr(self, "last_hedge_fill_price"):
                    hedge_fill_price = self.last_hedge_fill_price
                break

            await asyncio.sleep(0.01)

            if time.time() - start_time > 180:
                self.logger.error("Timeout waiting for trade completion")
                return False, None, None

        return True, primary_fill_price, hedge_fill_price

    async def trading_loop(self):
        self.logger.info(f"{'=' * 60}")
        # Flush log handlers to ensure output
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass
        self.logger.info("DN Hedge Bot Starting (MEAN REVERSION STRATEGY)")
        self.logger.info(
            f"PRIMARY: {self.primary_exchange.upper()} ({self.primary_mode.value}) | "
            f"HEDGE: {self.hedge_exchange.upper()} ({self.hedge_mode.value})"
        )
        self.logger.info(
            f"Ticker: {self.ticker} | Quantity: {self.order_quantity} | Iterations: {self.iterations}"
        )
        self.logger.info(f"{'=' * 60}")
        # Flush log handlers to ensure output
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass

        try:
            await self.initialize_clients()
            await self.connect_websockets()
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return

        self.logger.info("[INIT] Waiting for connections to stabilize...")
        await asyncio.sleep(3)
        self.logger.info("[INIT] Fetching initial positions...")

        try:
            api_primary, api_hedge = await asyncio.wait_for(
                self.get_positions(force_api=True), timeout=30.0
            )
            self.logger.info(
                f"[INIT] Positions fetched: PRIMARY={api_primary}, HEDGE={api_hedge}"
            )
        except asyncio.TimeoutError:
            self.logger.error("[INIT] Timeout fetching positions, using WS positions")
            api_primary, api_hedge = await self.get_positions(force_api=False)
        except Exception as e:
            self.logger.error(
                f"[INIT] Error fetching positions: {e}, using WS positions"
            )
            api_primary, api_hedge = await self.get_positions(force_api=False)
        self.local_primary_position = api_primary
        self.local_hedge_position = api_hedge
        self.primary_position = api_primary
        self.hedge_position = api_hedge
        self.logger.info(
            f"[INIT] Positions - PRIMARY: {self.primary_position}, HEDGE: {self.hedge_position}"
        )

        cycle_count = 0

        for iteration in range(1, self.iterations + 1):
            if self.stop_flag:
                break

            self.logger.info(f"\n{'=' * 40}")
            self.logger.info(f"Iteration {iteration}/{self.iterations}")
            self.logger.info(f"{'=' * 40}")

            await self.reconcile_positions()

            while (
                self.primary_client.get_ws_position() < self.max_position
                and not self.stop_flag
            ):
                cycle_count += 1

                if cycle_count % self.reconcile_interval == 0:
                    await self.reconcile_positions()

                # Use WebSocket positions for both exchanges (real-time tracking)
                self.primary_position = self.primary_client.get_ws_position()
                self.hedge_position = self.hedge_client.get_ws_position()
                net_delta = self.primary_position + self.hedge_position

                # Check position imbalance (like original hedge_mode_grvt.py)
                net_delta = self.local_primary_position + self.local_hedge_position
                if abs(net_delta) > self.order_quantity * Decimal("2"):
                    self.logger.error(
                        f"[BUILD] CRITICAL: Position imbalance too large! "
                        f"Primary: {self.local_primary_position}, Hedge: {self.local_hedge_position}, Net: {net_delta}"
                    )
                    self.logger.error("[BUILD] Stopping bot to prevent further losses")
                    self.logger.error("[BUILD] Attempting to close all positions...")
                    await self.force_close_all_positions()
                    self.stop_flag = True
                    break

                self.logger.info(
                    f"[BUILD] PRIMARY(WS): {self.primary_position} | HEDGE(WS): {self.hedge_position} | "
                    f"Local: {self.local_primary_position}/{self.local_hedge_position} | Net: {net_delta}"
                )

                # Tighter position imbalance threshold: 2x instead of 5x
                if abs(net_delta) > self.order_quantity * 2:
                    self.logger.error(f"Position imbalance too large: {net_delta}")
                    self.logger.error("[BUILD] Attempting to close all positions...")
                    await self.force_close_all_positions()
                    self.stop_flag = True
                    break

                # Mean Reversion: 가격 비교 후 방향 결정
                direction = await self.should_enter_trade()
                if direction is None:
                    await asyncio.sleep(1)
                    continue

                success, primary_price, hedge_price = await self.execute_dn_cycle(
                    direction
                )
                if success and primary_price and hedge_price:
                    self.print_trade_summary(
                        cycle_count,
                        "sell",
                        primary_price,
                        "buy",
                        hedge_price,
                        self.order_quantity,
                    )
                if not success:
                    await asyncio.sleep(5)

            if self.sleep_time > 0:
                self.logger.info(f"Sleeping {self.sleep_time}s...")
                await asyncio.sleep(self.sleep_time)

            while (
                self.primary_client.get_ws_position() > -self.max_position
                and not self.stop_flag
            ):
                cycle_count += 1

                if cycle_count % self.reconcile_interval == 0:
                    await self.reconcile_positions()

                # Use WebSocket positions for both exchanges (real-time tracking)
                self.primary_position = self.primary_client.get_ws_position()
                self.hedge_position = self.hedge_client.get_ws_position()
                net_delta = self.primary_position + self.hedge_position

                self.logger.info(
                    f"[UNWIND] PRIMARY(WS): {self.primary_position} | HEDGE(WS): {self.hedge_position} | Net: {net_delta}"
                )

                # Tighter position imbalance threshold: 2x instead of 5x
                if abs(net_delta) > self.order_quantity * 2:
                    self.logger.error(f"Position imbalance too large: {net_delta}")
                    self.logger.error("[UNWIND] Attempting to close all positions...")
                    await self.force_close_all_positions()
                    self.stop_flag = True
                    break

                remaining_qty = self.order_quantity
                if (
                    iteration == self.iterations
                    and abs(self.local_primary_position) <= self.order_quantity
                ):
                    remaining_qty = abs(self.local_primary_position)
                    if remaining_qty == 0:
                        break

                # Mean Reversion UNWIND: 기존 포지션 청산 (역방향)
                direction = "buy" if self.primary_position > 0 else "sell"
                if not await self.should_enter_trade():
                    await asyncio.sleep(1)
                    continue

                success, primary_price, hedge_price = await self.execute_dn_cycle(
                    direction
                )
                if success and primary_price and hedge_price:
                    self.print_trade_summary(
                        cycle_count,
                        "buy",
                        primary_price,
                        "sell",
                        hedge_price,
                        self.order_quantity,
                    )
                if not success:
                    await asyncio.sleep(5)

        final_primary, final_hedge = await self.get_positions(force_api=True)
        avg_pnl_bps = (
            (self.total_gross_pnl / self.total_volume) * Decimal("10000")
            if self.total_volume > 0
            else Decimal("0")
        )

        self.logger.info(f"\n{'=' * 60}")
        self.logger.info("TRADING COMPLETE - FINAL SUMMARY")
        self.logger.info(f"{'=' * 60}")
        # Flush log handlers to ensure output
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass
        self.logger.info(f"  Completed Cycles: {self.completed_cycles}")
        self.logger.info(f"  Total Volume: ${self.total_volume:.2f}")
        self.logger.info(f"  Total Gross PnL: ${self.total_gross_pnl:.4f}")
        self.logger.info(f"  Average Edge: {avg_pnl_bps:+.2f} bps")
        self.logger.info(f"{'-' * 60}")
        self.logger.info(
            f"  Final Positions - PARADEX: {final_primary}, GRVT: {final_hedge}"
        )
        self.logger.info(f"  Net Delta: {final_primary + final_hedge}")
        self.logger.info(f"{'=' * 60}")
        # Flush log handlers to ensure output
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass
        self.logger.info(f"  Completed Cycles: {self.completed_cycles}")
        self.logger.info(f"  Total Volume: ${self.total_volume:.2f}")
        self.logger.info(f"  Total Gross PnL: ${self.total_gross_pnl:.4f}")
        self.logger.info(f"  Average Edge: {avg_pnl_bps:+.2f} bps")
        self.logger.info(f"{'─' * 60}")
        self.logger.info(
            f"  Final Positions - PARADEX: {final_primary}, GRVT: {final_hedge}"
        )
        self.logger.info(f"  Net Delta: {final_primary + final_hedge}")
        self.logger.info(f"{'=' * 60}")
        # Flush log handlers to ensure output
        for handler in self.logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass

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
        description="Delta Neutral Hedge Bot: Paradex + GRVT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test 1: PRIMARY=BBO-1tick, HEDGE=market (default)
    python hedge_mode_paradex_grvt.py --ticker SOL --size 1 --iter 10

    # Test 2: PRIMARY=BBO, HEDGE=market
    python hedge_mode_paradex_grvt.py --ticker SOL --size 1 --iter 10 --primary-mode bbo

    # Test 3: PRIMARY=BBO-1tick, HEDGE=BBO-1tick
    python hedge_mode_paradex_grvt.py --ticker SOL --size 1 --iter 10 --hedge-mode bbo_minus_1

    # Test 4: PRIMARY=BBO, HEDGE=BBO
    python hedge_mode_paradex_grvt.py --ticker SOL --size 1 --iter 10 --primary-mode bbo --hedge-mode bbo
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
        default="grvt",
        choices=["paradex", "grvt"],
        help="Primary exchange for POST_ONLY orders (default: grvt)",
    )
    parser.add_argument(
        "--hedge",
        type=str,
        default="paradex",
        choices=["paradex", "grvt"],
        help="Hedge exchange for market orders (default: paradex)",
    )
    parser.add_argument(
        "--primary-mode",
        type=str,
        default="bbo_minus_1",
        choices=["bbo_minus_1", "bbo"],
        help="Primary order price mode (default: bbo_minus_1)",
    )
    parser.add_argument(
        "--hedge-mode",
        type=str,
        default="market",
        choices=["market", "bbo_minus_1", "bbo_plus_1", "bbo", "aggressive"],
        help="Hedge order price mode (default: market). aggressive: BUY@ask, SELL@bid for instant fill",
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

    bot = DNHedgeBot(
        ticker=args.ticker.upper(),
        order_quantity=Decimal(args.size),
        fill_timeout=args.fill_timeout,
        iterations=args.iter,
        sleep_time=args.sleep,
        max_position=Decimal(args.max_position),
        primary_exchange=args.primary,
        hedge_exchange=args.hedge,
        primary_mode=primary_mode,
        hedge_mode=hedge_mode,
        min_spread_bps=Decimal(args.min_spread),
    )

    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
