import asyncio
import json
import signal
import logging
import os
import sys
import time
import requests
import argparse
import traceback
import csv
from decimal import Decimal
from typing import Tuple, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.backpack import BackpackClient
from exchanges.grvt import GrvtClient
from config_loader import ConfigLoader
from helpers.telegram_bot import TelegramBot
from helpers.progressive_sizing import ProgressiveSizingManager
from helpers.rebate_tracker import RebateTracker
import websockets
from datetime import datetime
import pytz

class Config:
    """Simple config class to wrap dictionary for Backpack client."""
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)


class HedgeBot:
    """Trading bot that places post-only orders on Backpack and hedges with market orders on GRVT."""

    def __init__(self, ticker: str, order_quantity: Decimal, fill_timeout: int = 5, iterations: int = 20, config_path: str = "config.yaml"):
        self.ticker = ticker
        self.order_quantity = order_quantity
        self.fill_timeout = fill_timeout
        self.grvt_order_filled = False
        self.iterations = iterations
        self.backpack_position = Decimal('0')
        self.grvt_position = Decimal('0')
        self.current_order = {}

        # Load configuration from config.yaml
        self.config = ConfigLoader(config_path)

        # Initialize logging to file
        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/backpack_{ticker}_hedge_mode_log.txt"
        self.csv_filename = f"logs/backpack_{ticker}_hedge_mode_trades.csv"
        self.original_stdout = sys.stdout

        # Initialize CSV file with headers if it doesn't exist
        self._initialize_csv_file()

        # Setup logger
        self.logger = logging.getLogger(f"hedge_bot_{ticker}")
        self.logger.setLevel(logging.INFO)

        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Disable verbose logging from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)

        # Create file handler (UTF-8 encoding for emoji/unicode support)
        file_handler = logging.FileHandler(self.log_filename, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # Create console handler (UTF-8 stream for emoji/unicode support)
        import io
        if hasattr(sys.stdout, 'buffer'):
            console_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        else:
            console_stream = sys.stdout
        console_handler = logging.StreamHandler(console_stream)
        console_handler.setLevel(logging.INFO)

        # Create different formatters for file and console
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Prevent propagation to root logger to avoid duplicate messages
        self.logger.propagate = False

        # State management
        self.stop_flag = False
        self.order_counter = 0

        # Backpack state
        self.backpack_client = None
        self.backpack_contract_id = None
        self.backpack_tick_size = None
        self.backpack_order_status = None

        # Backpack order book state for websocket-based BBO
        self.backpack_order_book = {'bids': {}, 'asks': {}}
        self.backpack_best_bid = None
        self.backpack_best_ask = None
        self.backpack_order_book_ready = False

        # GRVT order book state
        self.grvt_client = None
        self.grvt_order_book = {"bids": {}, "asks": {}}
        self.grvt_best_bid = None
        self.grvt_best_ask = None
        self.grvt_order_book_ready = False
        self.grvt_order_book_offset = 0
        self.grvt_order_book_sequence_gap = False
        self.grvt_snapshot_loaded = False
        self.grvt_order_book_lock = asyncio.Lock()

        # GRVT WebSocket state
        self.grvt_ws_task = None
        self.grvt_order_result = None

        # GRVT order management
        self.grvt_order_status = None
        self.grvt_order_price = None
        self.grvt_order_side = None
        self.grvt_order_size = None
        self.grvt_order_start_time = None

        # Strategy state
        self.waiting_for_grvt_fill = False
        self.wait_start_time = None

        # Order execution tracking
        self.order_execution_complete = False

        # Current order details for immediate execution
        self.current_grvt_side = None
        self.current_grvt_quantity = None
        self.current_grvt_price = None
        self.grvt_order_info = None

        # GRVT API configuration
        self.grvt_trading_account_id = os.getenv('GRVT_TRADING_ACCOUNT_ID')
        self.grvt_private_key = os.getenv('GRVT_PRIVATE_KEY')
        self.grvt_api_key = os.getenv('GRVT_API_KEY')
        self.grvt_environment = os.getenv('GRVT_ENVIRONMENT', 'prod')
        self.grvt_contract = f"{ticker}_USDT_Perp"  # GRVT contract ID

        # Backpack configuration
        self.backpack_public_key = os.getenv('BACKPACK_PUBLIC_KEY')
        self.backpack_secret_key = os.getenv('BACKPACK_SECRET_KEY')

        # Telegram notification configuration
        self.telegram_bot = None
        telegramToken = os.getenv('TELEGRAM_BOT_TOKEN')
        telegramChatId = os.getenv('TELEGRAM_CHAT_ID')
        if telegramToken and telegramChatId:
            try:
                self.telegram_bot = TelegramBot(telegramToken, telegramChatId)
                self.logger.info("Telegram bot initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Telegram bot: {e}")

        # Telegram command polling configuration
        self.telegramPollingInterval = 5  # seconds
        self.telegramPollingTask = None

        # Status file for inter-process communication with TelegramService
        from pathlib import Path
        self.statusFilePath = Path(__file__).parent / "bot_status.json"

        # Initialize Progressive Sizing Manager
        self.progressiveSizing = ProgressiveSizingManager(
            config=self.config.config,
            ticker=ticker,
            logger=self.logger
        )
        self.logger.info(f"Progressive Sizing: {'ENABLED' if self.progressiveSizing.enabled else 'DISABLED'}")

        # Initialize GRVT Rebate Tracker (STORY-004)
        rebate_config = {
            'rebate_tracking': {
                'enabled': self.config.get('grvt_rebate_tracking', 'enabled', True),
                'milestones': self.config.get('grvt_rebate_tracking', 'milestone_alerts', [1, 5, 10, 25, 50, 100]),
                'telegram_notifications': True,
                'csv_logging': self.config.get('grvt_rebate_tracking', 'log_to_csv', True)
            }
        }
        self.rebateTracker = RebateTracker(
            config=rebate_config,
            ticker=ticker,
            logger=self.logger
        )
        self.logger.info(f"GRVT Rebate Tracking: {'ENABLED' if self.rebateTracker.enabled else 'DISABLED'}")

    def updateStatusFile(self, running: bool = True):
        """Update status file for TelegramService inter-process communication."""
        try:
            status = {
                "running": running,
                "ticker": self.ticker,
                "order_size": str(self.order_quantity),
                "iteration": self.order_counter,
                "iterations": self.iterations,
                "start_time": datetime.now().isoformat(),
                "stop_requested": False
            }
            with open(self.statusFilePath, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to update status file: {e}")

    def checkStopFlag(self) -> bool:
        """Check if TelegramService has requested a stop."""
        try:
            if self.statusFilePath.exists():
                with open(self.statusFilePath, 'r') as f:
                    status = json.load(f)
                    if status.get("stop_requested", False):
                        self.logger.info("🛑 Stop requested via Telegram")
                        return True
        except Exception as e:
            self.logger.warning(f"Failed to check stop flag: {e}")
        return False

    def clearStatusFile(self):
        """Clear the status file when bot stops."""
        try:
            status = {
                "running": False,
                "ticker": self.ticker,
                "order_size": str(self.order_quantity),
                "iteration": self.order_counter,
                "iterations": self.iterations,
                "stop_time": datetime.now().isoformat(),
                "stop_requested": False
            }
            with open(self.statusFilePath, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to clear status file: {e}")

    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown handler."""
        self.stop_flag = True
        self.logger.info("\n🛑 Stopping...")

        # Update status file to indicate bot is stopped
        self.clearStatusFile()

        # Close WebSocket connections
        if self.backpack_client:
            try:
                # Note: disconnect() is async, but shutdown() is sync
                # We'll let the cleanup happen naturally
                self.logger.info("🔌 Backpack WebSocket will be disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting Backpack WebSocket: {e}")

        # Cancel GRVT WebSocket task
        if self.grvt_ws_task and not self.grvt_ws_task.done():
            try:
                self.grvt_ws_task.cancel()
                self.logger.info("🔌 GRVT WebSocket task cancelled")
            except Exception as e:
                self.logger.error(f"Error cancelling GRVT WebSocket task: {e}")

        # Stop Telegram polling task
        self.stopTelegramPolling()

        # Close Telegram bot connection
        if self.telegram_bot:
            try:
                self.telegram_bot.close()
                self.logger.info("Telegram bot connection closed")
            except Exception as e:
                self.logger.error(f"Error closing Telegram bot: {e}")

        # Close logging handlers properly
        for handler in self.logger.handlers[:]:
            try:
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                pass

    def send_telegram_alert(self, message: str, parseMode: str = "HTML"):
        """Send alert message to Telegram."""
        if self.telegram_bot:
            try:
                self.telegram_bot.send_text(message, parseMode)
            except Exception as e:
                self.logger.warning(f"Failed to send Telegram alert: {e}")

    async def telegramCommandPolling(self):
        """Background task to poll for Telegram commands."""
        self.logger.info("Telegram command polling started")
        while not self.stop_flag:
            try:
                if self.telegram_bot:
                    command = self.telegram_bot.processUpdates()
                    if command:
                        await self.handleTelegramCommand(command)
            except Exception as e:
                self.logger.warning(f"Telegram polling error: {e}")
            await asyncio.sleep(self.telegramPollingInterval)

    async def handleTelegramCommand(self, command: str):
        """Handle Telegram command from user."""
        self.logger.info(f"Processing Telegram command: {command}")

        if command == "menu":
            # Send inline keyboard menu
            bpPos = float(self.backpack_position)
            grvtPos = float(self.grvt_position)
            menuText = (
                f"<b>🤖 Hedge Bot Control Panel</b>\n"
                f"Ticker: <code>{self.ticker}</code>\n"
                "---\n"
                f"📈 Backpack: {bpPos:+.4f}\n"
                f"📉 GRVT: {grvtPos:+.4f}\n"
                f"🔄 Progress: {self.order_counter}/{self.iterations}\n"
                "---\n"
                "Select a command:"
            )
            self.telegram_bot.sendMenu(menuText)

        elif command == "balance":
            # Get and send balance information
            balanceMsg = await self.getBalanceMessage()
            self.send_telegram_alert(balanceMsg)

        elif command == "position":
            # Send current position information
            positionMsg = self.getPositionMessage()
            self.send_telegram_alert(positionMsg)

        elif command in ["stop", "kill"]:
            # Stop the bot
            self.logger.info(f"Received {command} command from Telegram")
            bpPos = float(self.backpack_position)
            grvtPos = float(self.grvt_position)
            stopMsg = (
                f"<b>🛑 Bot Stopping...</b>\n"
                f"Received <code>{command}</code> command.\n"
                f"Ticker: <code>{self.ticker}</code>\n"
                "---\n"
                f"📊 Final Positions:\n"
                f"  Backpack: {bpPos:+.4f}\n"
                f"  GRVT: {grvtPos:+.4f}\n"
                f"🔄 Completed: {self.order_counter}/{self.iterations} iterations"
            )
            self.send_telegram_alert(stopMsg)
            self.stop_flag = True

    async def getBalanceMessage(self) -> str:
        """Get formatted balance message for Telegram."""
        try:
            # Get Backpack balance using the correct method
            backpackBalance = "N/A"
            if self.backpack_client:
                try:
                    balances = self.backpack_client.account_client.get_balances()
                    if balances:
                        for balance in balances:
                            if balance.get('symbol') == 'USDC':
                                available = float(balance.get('available', 0))
                                locked = float(balance.get('locked', 0))
                                total = available + locked
                                backpackBalance = f"Available: {available:.2f} USDC\nLocked: {locked:.2f} USDC\nTotal: {total:.2f} USDC"
                                break
                        else:
                            backpackBalance = "USDC not found"
                    else:
                        backpackBalance = "No balance data"
                except Exception as e:
                    backpackBalance = f"Error: {e}"

            # Get GRVT balance
            grvtBalance = "N/A"
            try:
                if self.grvt_client:
                    balance = self.grvt_client.fetch_balance()
                    if balance and 'USDT' in balance:
                        usdtBalance = balance['USDT']
                        free = float(usdtBalance.get('free', 0))
                        total = float(usdtBalance.get('total', 0))
                        grvtBalance = f"Free: {free:.2f} USDT\nTotal: {total:.2f} USDT"
                    else:
                        grvtBalance = "USDT balance not found"
                else:
                    grvtBalance = "Client not initialized"
            except Exception as e:
                grvtBalance = f"Error: {e}"

            return (
                "<b>Account Balances</b>\n"
                "---\n"
                f"<b>Backpack:</b>\n{backpackBalance}\n\n"
                f"<b>GRVT:</b>\n{grvtBalance}"
            )
        except Exception as e:
            return f"<b>Balance Error:</b> {e}"

    def getPositionMessage(self) -> str:
        """Get formatted position message for Telegram."""
        netPosition = self.backpack_position + self.grvt_position
        imbalance = abs(netPosition)
        statusEmoji = "✅" if imbalance < Decimal('0.0001') else "⚠️"
        status = "Balanced" if imbalance < Decimal('0.0001') else f"Imbalanced ({imbalance:.4f})"

        # Format positions with proper decimal places
        bpPos = float(self.backpack_position)
        grvtPos = float(self.grvt_position)
        netPos = float(netPosition)

        return (
            f"<b>📊 Current Positions</b>\n"
            f"Ticker: <code>{self.ticker}</code>\n"
            "---\n"
            f"<b>Backpack:</b> {bpPos:+.4f} {self.ticker}\n"
            f"<b>GRVT:</b> {grvtPos:+.4f} {self.ticker}\n"
            f"<b>Net:</b> {netPos:+.4f} {self.ticker}\n"
            f"<b>Status:</b> {statusEmoji} {status}\n"
            "---\n"
            f"<b>Progress:</b> {self.order_counter}/{self.iterations} iterations"
        )

    def startTelegramPolling(self):
        """Start the Telegram command polling background task."""
        if self.telegram_bot:
            self.telegramPollingTask = asyncio.create_task(self.telegramCommandPolling())
            self.logger.info("Telegram polling task created")

    def stopTelegramPolling(self):
        """Stop the Telegram command polling background task."""
        if self.telegramPollingTask and not self.telegramPollingTask.done():
            self.telegramPollingTask.cancel()
            self.logger.info("Telegram polling task cancelled")

    def _initialize_csv_file(self):
        """Initialize CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['exchange', 'timestamp', 'side', 'price', 'quantity',
                                 'ps_phase', 'ps_target_usd', 'ps_successes', 'ps_failures',
                                 'rebate_cumulative', 'rebate_last_milestone', 'rebate_next_milestone'])

    def log_trade_to_csv(self, exchange: str, side: str, price: str, quantity: str):
        """Log trade details to CSV file."""
        timestamp = datetime.now(pytz.UTC).isoformat()

        # Get progressive sizing data
        ps_data = self.progressiveSizing.get_csv_log_data()

        # Get rebate tracking data (STORY-004)
        rebate_data = self.rebateTracker.get_csv_log_data()

        with open(self.csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                exchange,
                timestamp,
                side,
                price,
                quantity,
                ps_data['current_phase'],
                ps_data['phase_target_usd'],
                ps_data['consecutive_successes'],
                ps_data['consecutive_failures'],
                rebate_data['cumulative_rebate'],
                rebate_data['last_milestone_hit'],
                rebate_data['next_milestone']
            ])

        self.logger.info(f"📊 Trade logged to CSV: {exchange} {side} {quantity} @ {price} (PS Phase {ps_data['current_phase']}, Rebate: ${rebate_data['cumulative_rebate']})")

    def handle_grvt_order_result(self, order_data):
        """Handle GRVT order result from WebSocket."""
        try:
            # GRVT order structure: size (positive=long, negative=short)
            filled_size = Decimal(str(order_data.get('size', 0)))
            avg_filled_price = Decimal(str(order_data.get('average_entry_price', 0)))

            # Determine side and update position
            if filled_size < 0:
                order_data["side"] = "SHORT"
                order_type = "OPEN"
                self.grvt_position += filled_size  # filled_size is already negative
            else:
                order_data["side"] = "LONG"
                order_type = "CLOSE"
                self.grvt_position += filled_size

            client_order_id = order_data.get("client_order_id", "N/A")

            self.logger.info(f"[{client_order_id}] [{order_type}] [GRVT] [FILLED]: "
                             f"{abs(filled_size)} @ {avg_filled_price}")

            # Log GRVT trade to CSV
            self.log_trade_to_csv(
                exchange='GRVT',
                side=order_data['side'],
                price=str(avg_filled_price),
                quantity=str(abs(filled_size))
            )

            # STORY-004: Calculate and record GRVT maker rebate
            rebate_rate = Decimal(str(self.config.get('grvt_rebate_tracking', 'rebate_rate', 0.0002)))
            trade_volume = abs(filled_size) * avg_filled_price  # Trade volume in USD
            rebate_amount = trade_volume * rebate_rate  # Rebate in USD

            self.logger.info(f"💰 GRVT Rebate: ${rebate_amount:.4f} (Volume: ${trade_volume:.2f}, Rate: {rebate_rate*100}%)")

            # Record rebate and check for milestone
            milestone_hit, milestone_msg = self.rebateTracker.record_rebate(rebate_amount)

            # Send telegram alert for GRVT trade
            tradeMsg = (
                f"<b>📊 GRVT Trade Filled</b>\n"
                f"Ticker: {self.ticker}\n"
                f"Side: {order_data['side']}\n"
                f"Size: {abs(filled_size)}\n"
                f"Price: ${avg_filled_price:.2f}\n"
                f"Position: {self.grvt_position}\n"
                f"Rebate: ${rebate_amount:.4f}"
            )
            self.send_telegram_alert(tradeMsg)

            # Send milestone notification if triggered
            if milestone_hit and milestone_msg:
                self.logger.info(f"🎉 Rebate Milestone: {milestone_msg}")
                self.send_telegram_alert(milestone_msg)

            # Mark execution as complete
            self.grvt_order_filled = True  # Mark order as filled
            self.order_execution_complete = True

            # STORY-003: Hedge confirmation after GRVT fill
            asyncio.create_task(self._check_hedge_confirmation_after_fill(avg_filled_price))

        except Exception as e:
            self.logger.error(f"Error handling GRVT order result: {e}")

    async def reset_grvt_order_book(self):
        """Reset GRVT order book state."""
        async with self.grvt_order_book_lock:
            self.grvt_order_book["bids"].clear()
            self.grvt_order_book["asks"].clear()
            self.grvt_best_bid = None
            self.grvt_best_ask = None

    def update_grvt_order_book(self, side: str, levels: list):
        """Update GRVT order book with new levels."""
        for level in levels:
            # GRVT order book format: {"price": ..., "size": ...}
            if isinstance(level, dict):
                price = Decimal(str(level.get("price", 0)))
                size = Decimal(str(level.get("size", 0)))
            else:
                self.logger.warning(f"⚠️ Unexpected level format: {level}")
                continue

            if size > 0:
                self.grvt_order_book[side][price] = size
            else:
                # Remove zero size orders
                self.grvt_order_book[side].pop(price, None)

    def validate_order_book_integrity(self) -> bool:
        """Validate order book integrity."""
        # Check for negative prices or sizes
        for side in ["bids", "asks"]:
            for price, size in self.grvt_order_book[side].items():
                if price <= 0 or size <= 0:
                    self.logger.error(f"❌ Invalid order book data: {side} price={price}, size={size}")
                    return False
        return True

    def get_grvt_best_levels(self) -> Tuple[Tuple[Decimal, Decimal], Tuple[Decimal, Decimal]]:
        """Get best bid and ask levels from GRVT order book."""
        best_bid = None
        best_ask = None

        if self.grvt_order_book["bids"]:
            best_bid_price = max(self.grvt_order_book["bids"].keys())
            best_bid_size = self.grvt_order_book["bids"][best_bid_price]
            best_bid = (best_bid_price, best_bid_size)

        if self.grvt_order_book["asks"]:
            best_ask_price = min(self.grvt_order_book["asks"].keys())
            best_ask_size = self.grvt_order_book["asks"][best_ask_price]
            best_ask = (best_ask_price, best_ask_size)

        return best_bid, best_ask

    def get_grvt_mid_price(self) -> Decimal:
        """Get mid price from GRVT order book."""
        best_bid, best_ask = self.get_grvt_best_levels()

        if best_bid is None or best_ask is None:
            raise Exception("Cannot calculate mid price - missing order book data")

        mid_price = (best_bid[0] + best_ask[0]) / Decimal('2')
        return mid_price

    def get_grvt_order_price(self, is_ask: bool) -> Decimal:
        """Get order price from GRVT order book."""
        best_bid, best_ask = self.get_grvt_best_levels()

        if best_bid is None or best_ask is None:
            raise Exception("Cannot calculate order price - missing order book data")

        if is_ask:
            order_price = best_bid[0] + Decimal('0.1')
        else:
            order_price = best_ask[0] - Decimal('0.1')

        return order_price

    def calculate_adjusted_price(self, original_price: Decimal, side: str, adjustment_percent: Decimal) -> Decimal:
        """Calculate adjusted price for order modification."""
        adjustment = original_price * adjustment_percent

        if side.lower() == 'buy':
            # For buy orders, increase price to improve fill probability
            return original_price + adjustment
        else:
            # For sell orders, decrease price to improve fill probability
            return original_price - adjustment

    async def handle_grvt_ws(self):
        """Handle GRVT connection and order book polling via REST API."""
        self.logger.info("[GRVT] REST API polling starting...")

        if self.grvt_client is None:
            self.logger.error("[GRVT] Client not initialized")
            return

        try:
            # Fetch initial order book via REST API
            self.logger.info(f"[GRVT] Fetching order book for {self.grvt_contract}...")
            best_bid, best_ask = await self.grvt_client.fetch_bbo_prices(self.grvt_contract)

            if best_bid > 0 and best_ask > 0:
                # Populate order book with best levels
                self.grvt_order_book["bids"][best_bid] = Decimal('1')  # Placeholder size
                self.grvt_order_book["asks"][best_ask] = Decimal('1')  # Placeholder size
                self.grvt_best_bid = best_bid
                self.grvt_best_ask = best_ask
                self.grvt_order_book_ready = True
                self.logger.info(f"[GRVT] Order book ready - Bid: {best_bid}, Ask: {best_ask}")
            else:
                self.logger.warning(f"[GRVT] Order book empty - Bid: {best_bid}, Ask: {best_ask}")

            # Connect to GRVT WebSocket for order updates
            await self.grvt_client.connect()
            self.logger.info("[GRVT] WebSocket connected")

            # Setup order update handler
            async def order_update_handler(order_data):
                """Handle order updates from GRVT WebSocket."""
                try:
                    await self.handle_grvt_order_result(order_data)
                except Exception as e:
                    self.logger.error(f"Error handling GRVT order update: {e}")

            self.grvt_client.setup_order_update_handler(order_update_handler)
            self.logger.info("[OK] GRVT WebSocket order update handler set up")

        except Exception as e:
            self.logger.error(f"[GRVT] Could not setup connection: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def initialize_grvt_client(self):
        """Initialize the GRVT client with WebSocket support."""
        if self.grvt_client is None:
            # Create config for GrvtClient
            grvt_config = Config({
                'ticker': self.ticker,
                'contract_id': self.grvt_contract,  # e.g., "ETH_USDT_Perp"
                'environment': os.getenv('GRVT_ENVIRONMENT', 'prod')
            })

            # Initialize GrvtClient (includes WebSocket support)
            self.grvt_client = GrvtClient(grvt_config)
            self.logger.info("✅ GRVT client initialized successfully (WebSocket enabled)")
        return self.grvt_client

    def get_backpack_funding_payments(self, limit: int = 10) -> dict:
        """
        Get recent funding payments from Backpack.

        Args:
            limit: Number of recent funding payments to retrieve

        Returns:
            dict with funding payments summary:
            - total: cumulative funding fee (positive = received, negative = paid)
            - count: number of payments
            - payments: list of recent payments
        """
        try:
            if not self.backpack_client:
                return {"total": 0, "count": 0, "payments": [], "error": "Client not initialized"}

            # Use the account client's get_funding_payments method
            symbol = f"{self.ticker}_USDC_PERP"
            fundingPayments = self.backpack_client.account_client.get_funding_payments(
                symbol=symbol,
                limit=limit
            )

            if not fundingPayments:
                return {"total": 0, "count": 0, "payments": []}

            # Calculate cumulative funding fee
            total = Decimal('0')
            payments = []
            for payment in fundingPayments:
                amount = Decimal(str(payment.get('paymentAmount', '0')))
                total += amount
                payments.append({
                    "symbol": payment.get('symbol'),
                    "amount": float(amount),
                    "timestamp": payment.get('timestamp')
                })

            return {
                "total": float(total),
                "count": len(payments),
                "payments": payments
            }

        except Exception as e:
            self.logger.warning(f"⚠️ Failed to get Backpack funding payments: {e}")
            return {"total": 0, "count": 0, "payments": [], "error": str(e)}

    def log_funding_status(self, iteration: int):
        """
        Log funding fee status at specified intervals.

        Args:
            iteration: Current trading loop iteration number
        """
        fundingFeeLogging = self.config.get("monitoring", "funding_fee_logging")
        if not fundingFeeLogging:
            return

        fundingFeeLogInterval = self.config.get("monitoring", "funding_fee_log_interval")
        if iteration % fundingFeeLogInterval != 0:
            return

        # Get Backpack funding payments
        backpackFunding = self.get_backpack_funding_payments(limit=20)

        # Log funding summary
        self.logger.info("=" * 50)
        self.logger.info("📊 FUNDING FEE STATUS")
        self.logger.info("=" * 50)
        self.logger.info(f"💰 Backpack Cumulative Funding: ${backpackFunding['total']:.4f}")
        self.logger.info(f"📝 Recent Payments Count: {backpackFunding['count']}")

        # Check warning threshold
        fundingFeeWarningThreshold = self.config.get("monitoring", "funding_fee_warning_threshold")
        if backpackFunding['total'] < fundingFeeWarningThreshold:
            self.logger.warning(
                f"⚠️ FUNDING WARNING: Cumulative funding fee (${backpackFunding['total']:.2f}) "
                f"exceeds threshold (${fundingFeeWarningThreshold:.2f})"
            )
            self.logger.warning("⚠️ Consider checking position direction or rebalancing")

        # Log recent payments details (last 3)
        if backpackFunding['payments']:
            self.logger.info("📋 Recent Funding Payments (Backpack):")
            for payment in backpackFunding['payments'][:3]:
                direction = "received" if payment['amount'] > 0 else "paid"
                self.logger.info(f"   • ${abs(payment['amount']):.6f} ({direction})")

        self.logger.info("=" * 50)

    def get_backpack_balance(self) -> dict:
        """
        Get USDC balance from Backpack.

        Returns:
            dict with balance info:
            - available: available USDC balance
            - total: total USDC balance (including in orders)
            - error: error message if failed
        """
        try:
            if not self.backpack_client:
                return {"available": 0, "total": 0, "error": "Client not initialized"}

            balances = self.backpack_client.account_client.get_balances()

            if not balances:
                return {"available": 0, "total": 0, "error": "No balance data"}

            # Find USDC balance
            for balance in balances:
                if balance.get('symbol') == 'USDC':
                    available = float(balance.get('available', 0))
                    locked = float(balance.get('locked', 0))
                    return {
                        "available": available,
                        "total": available + locked,
                        "locked": locked
                    }

            return {"available": 0, "total": 0, "error": "USDC not found"}

        except Exception as e:
            self.logger.warning(f"⚠️ Failed to get Backpack balance: {e}")
            return {"available": 0, "total": 0, "error": str(e)}

    def get_grvt_balance(self) -> dict:
        """
        Get collateral balance from GRVT.

        Returns:
            dict with balance info:
            - total_collateral: total USDT balance
            - free_collateral: available (free) USDT
            - error: error message if failed
        """
        try:
            if not self.grvt_client:
                return {"total_collateral": 0, "free_collateral": 0, "error": "Client not initialized"}

            # Get balance from GRVT
            balance = self.grvt_client.fetch_balance()

            if balance and 'USDT' in balance:
                usdtBalance = balance['USDT']
                freeCollateral = float(usdtBalance.get('free', 0))
                totalCollateral = float(usdtBalance.get('total', 0))
                return {
                    "total_collateral": totalCollateral,
                    "free_collateral": freeCollateral
                }

            return {"total_collateral": 0, "free_collateral": 0, "error": "No USDT balance"}

        except Exception as e:
            self.logger.warning(f"⚠️ Failed to get GRVT balance: {e}")
            return {"total_collateral": 0, "free_collateral": 0, "error": str(e)}

    def log_balance_status(self, iteration: int):
        """
        Log balance status at specified intervals.

        Args:
            iteration: Current trading loop iteration number
        """
        balanceLogging = self.config.get("monitoring", "balance_logging")
        if not balanceLogging:
            return

        balanceLogInterval = self.config.get("monitoring", "balance_log_interval")
        if iteration % balanceLogInterval != 0:
            return

        # Get balances from both exchanges
        backpackBalance = self.get_backpack_balance()
        grvtBalance = self.get_grvt_balance()

        # Log balance summary
        self.logger.info("=" * 50)
        self.logger.info("💰 BALANCE STATUS")
        self.logger.info("=" * 50)
        self.logger.info(f"📊 Backpack USDC: ${backpackBalance.get('available', 0):.2f} available "
                        f"(${backpackBalance.get('total', 0):.2f} total)")
        self.logger.info(f"📊 GRVT USDT: ${grvtBalance.get('free_collateral', 0):.2f} free "
                        f"(${grvtBalance.get('total_collateral', 0):.2f} total)")

        # Calculate and check imbalance
        backpackTotal = backpackBalance.get('total', 0)
        grvtTotal = grvtBalance.get('total_collateral', 0)
        combinedTotal = backpackTotal + grvtTotal

        if combinedTotal > 0:
            backpackRatio = backpackTotal / combinedTotal
            grvtRatio = grvtTotal / combinedTotal

            self.logger.info(f"📈 Balance Ratio: Backpack {backpackRatio*100:.1f}% | GRVT {grvtRatio*100:.1f}%")

            # Check warning threshold
            balanceWarningThreshold = self.config.get("monitoring", "balance_warning_threshold")
            imbalance = abs(backpackRatio - 0.5)  # Deviation from 50/50

            if imbalance > balanceWarningThreshold / 2:  # /2 because we measure from 50%
                self.logger.warning(
                    f"⚠️ BALANCE WARNING: Significant imbalance detected! "
                    f"(Backpack: {backpackRatio*100:.1f}%, GRVT: {grvtRatio*100:.1f}%)"
                )
                self.logger.warning("⚠️ Consider transferring funds to rebalance")

        self.logger.info("=" * 50)

    def initialize_backpack_client(self):
        """Initialize the Backpack client."""
        if not self.backpack_public_key or not self.backpack_secret_key:
            raise ValueError("BACKPACK_PUBLIC_KEY and BACKPACK_SECRET_KEY must be set in environment variables")

        # Create config for Backpack client
        config_dict = {
            'ticker': self.ticker,
            'contract_id': '',  # Will be set when we get contract info
            'quantity': self.order_quantity,
            'tick_size': Decimal('0.01'),  # Will be updated when we get contract info
            'close_order_side': 'sell'  # Default, will be updated based on strategy
        }

        # Wrap in Config class for Backpack client
        config = Config(config_dict)

        # Initialize Backpack client
        self.backpack_client = BackpackClient(config)
        self.backpack_client.logger = self.logger  # Set logger for Backpack client

        self.logger.info("✅ Backpack client initialized successfully")
        return self.backpack_client

    # GRVT uses simple string contract symbols, no market config lookup needed
    # Contract symbol is directly set as "ETH_USDT_Perp" in __init__

    async def get_backpack_contract_info(self) -> Tuple[str, Decimal]:
        """Get Backpack contract ID and tick size."""
        if not self.backpack_client:
            raise Exception("Backpack client not initialized")

        contract_id, tick_size = await self.backpack_client.get_contract_attributes()

        if self.order_quantity < self.backpack_client.config.quantity:
            raise ValueError(
                f"Order quantity is less than min quantity: {self.order_quantity} < {self.backpack_client.config.quantity}")

        return contract_id, tick_size

    async def get_current_price(self) -> Optional[Decimal]:
        """Get current mid price for progressive sizing calculations."""
        try:
            bid, ask = await self.fetch_backpack_bbo_prices()
            mid_price = (bid + ask) / Decimal('2')
            return mid_price
        except Exception as e:
            self.logger.error(f"Failed to get current price: {e}")
            return None

    async def fetch_backpack_bbo_prices(self) -> Tuple[Decimal, Decimal]:
        """Fetch best bid/ask prices from Backpack using websocket data."""
        # Use WebSocket data if available
        if self.backpack_order_book_ready and self.backpack_best_bid and self.backpack_best_ask:
            if self.backpack_best_bid > 0 and self.backpack_best_ask > 0 and self.backpack_best_bid < self.backpack_best_ask:
                return self.backpack_best_bid, self.backpack_best_ask

        # Fallback to REST API if websocket data is not available
        self.logger.warning("WebSocket BBO data not available, falling back to REST API")
        if not self.backpack_client:
            raise Exception("Backpack client not initialized")

        best_bid, best_ask = await self.backpack_client.fetch_bbo_prices(self.backpack_contract_id)

        return best_bid, best_ask

    def round_to_tick(self, price: Decimal) -> Decimal:
        """Round price to tick size."""
        if self.backpack_tick_size is None:
            return price
        return (price / self.backpack_tick_size).quantize(Decimal('1')) * self.backpack_tick_size

    async def place_bbo_order(self, side: str, quantity: Decimal):
        # Get best bid/ask prices
        best_bid, best_ask = await self.fetch_backpack_bbo_prices()

        # Place the order using Backpack client
        order_result = await self.backpack_client.place_open_order(
            contract_id=self.backpack_contract_id,
            quantity=quantity,
            direction=side.lower()
        )

        if order_result.success:
            return order_result.order_id
        else:
            raise Exception(f"Failed to place order: {order_result.error_message}")

    async def place_backpack_post_only_order(self, side: str, quantity: Decimal, max_retries: int = 3):
        """Place a post-only order on Backpack with retry limit."""
        if not self.backpack_client:
            raise Exception("Backpack client not initialized")

        self.backpack_order_status = None
        retry_count = 0
        self.logger.info(f"[OPEN] [Backpack] [{side}] Placing Backpack MAKER order (post_only)")
        try:
            order_id = await self.place_bbo_order(side, quantity)
            self.logger.info(f"[OPEN] [Backpack] Order placed successfully: {order_id}")
        except Exception as e:
            self.logger.error(f"[OPEN] [Backpack] Order placement failed: {e}")
            import traceback
            self.logger.error(f"[OPEN] [Backpack] Traceback: {traceback.format_exc()}")
            raise

        start_time = time.time()
        while not self.stop_flag:
            if self.backpack_order_status == 'CANCELED':
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.warning(f"[WARN] Max retries ({max_retries}) reached for Backpack order")
                    raise Exception(f"Backpack order failed after {max_retries} retries")

                self.logger.info(f"[RETRY] Backpack order retry {retry_count}/{max_retries}")
                self.backpack_order_status = 'NEW'
                order_id = await self.place_bbo_order(side, quantity)
                start_time = time.time()
                await asyncio.sleep(0.5)
            elif self.backpack_order_status in ['NEW', 'OPEN', 'PENDING', 'CANCELING', 'PARTIALLY_FILLED']:
                await asyncio.sleep(0.5)
                orderCancelTimeout = self.config.get("trading", "order_cancel_timeout")
                if time.time() - start_time > orderCancelTimeout:
                    try:
                        # Cancel the order using Backpack client
                        cancel_result = await self.backpack_client.cancel_order(order_id)
                        if not cancel_result.success:
                            self.logger.error(f"❌ Error canceling Backpack order: {cancel_result.error_message}")
                    except Exception as e:
                        self.logger.error(f"❌ Error canceling Backpack order: {e}")
            elif self.backpack_order_status == 'FILLED':
                break
            else:
                if self.backpack_order_status is not None:
                    self.logger.error(f"❌ Unknown Backpack order status: {self.backpack_order_status}")
                    break
                else:
                    await asyncio.sleep(0.5)

    def handle_backpack_order_book_update(self, message):
        """Handle Backpack order book updates from WebSocket."""
        try:
            if isinstance(message, str):
                message = json.loads(message)

            self.logger.debug(f"Received Backpack depth message: {message}")

            # Check if this is a depth update message
            if message.get("stream") and "depth" in message.get("stream", ""):
                data = message.get("data", {})

                if data:
                    # Update bids - format is [["price", "size"], ...]
                    # Backpack API uses 'b' for bids
                    bids = data.get('b', [])
                    for bid in bids:
                        price = Decimal(bid[0])
                        size = Decimal(bid[1])
                        if size > 0:
                            self.backpack_order_book['bids'][price] = size
                        else:
                            # Remove zero size orders
                            self.backpack_order_book['bids'].pop(price, None)

                    # Update asks - format is [["price", "size"], ...]
                    # Backpack API uses 'a' for asks
                    asks = data.get('a', [])
                    for ask in asks:
                        price = Decimal(ask[0])
                        size = Decimal(ask[1])
                        if size > 0:
                            self.backpack_order_book['asks'][price] = size
                        else:
                            # Remove zero size orders
                            self.backpack_order_book['asks'].pop(price, None)

                    # Update best bid and ask
                    if self.backpack_order_book['bids']:
                        self.backpack_best_bid = max(self.backpack_order_book['bids'].keys())
                    if self.backpack_order_book['asks']:
                        self.backpack_best_ask = min(self.backpack_order_book['asks'].keys())

                    if not self.backpack_order_book_ready:
                        self.backpack_order_book_ready = True
                        self.logger.info(f"📊 Backpack order book ready - Best bid: {self.backpack_best_bid}, "
                                         f"Best ask: {self.backpack_best_ask}")
                    else:
                        self.logger.debug(f"📊 Order book updated - Best bid: {self.backpack_best_bid}, "
                                          f"Best ask: {self.backpack_best_ask}")

        except Exception as e:
            self.logger.error(f"Error handling Backpack order book update: {e}")
            self.logger.error(f"Message content: {message}")

    def handle_backpack_order_update(self, order_data):
        """Handle Backpack order updates from WebSocket."""
        side = order_data.get('side', '').lower()
        filled_size = Decimal(order_data.get('filled_size', '0'))
        price = Decimal(order_data.get('price', '0'))

        if side == 'buy':
            grvt_side = 'sell'
        else:
            grvt_side = 'buy'

        # Store order details for immediate execution
        self.current_grvt_side = grvt_side
        self.current_grvt_quantity = filled_size
        self.current_grvt_price = price

        self.grvt_order_info = {
            'grvt_side': grvt_side,
            'quantity': filled_size,
            'price': price
        }

        self.waiting_for_grvt_fill = True


    async def place_grvt_market_order(self, grvt_side: str, quantity: Decimal, price: Decimal):
        if not self.grvt_client:
            self.initialize_grvt_client()

        best_bid, best_ask = self.get_grvt_best_levels()

        # If order book not ready, fetch fresh prices via REST API
        if best_bid is None or best_ask is None:
            self.logger.info(f"[GRVT] Order book not ready, fetching fresh prices via REST API...")
            try:
                bid_price, ask_price = await self.grvt_client.fetch_bbo_prices(self.grvt_contract)
                if bid_price > 0 and ask_price > 0:
                    best_bid = (bid_price, Decimal('1'))
                    best_ask = (ask_price, Decimal('1'))
                    # Update local order book
                    self.grvt_order_book["bids"][bid_price] = Decimal('1')
                    self.grvt_order_book["asks"][ask_price] = Decimal('1')
                    self.grvt_order_book_ready = True
                    self.logger.info(f"[GRVT] Fresh prices - Bid: {bid_price}, Ask: {ask_price}")
                else:
                    self.logger.error(f"[GRVT] REST API returned invalid prices - Bid: {bid_price}, Ask: {ask_price}")
                    raise Exception("GRVT REST API returned invalid prices")
            except Exception as e:
                self.logger.error(f"[GRVT] Failed to fetch prices via REST API: {e}")
                raise Exception(f"GRVT order book not ready and REST API failed: {e}")

        # Determine order parameters (get multipliers from config)
        sellPriceMultiplier = Decimal(str(self.config.get("pricing", "sell_price_multiplier")))
        buyPriceMultiplier = Decimal(str(self.config.get("pricing", "buy_price_multiplier")))

        if grvt_side.lower() == 'buy':
            order_type = "CLOSE"
            price = best_ask[0] * sellPriceMultiplier
        else:
            order_type = "OPEN"
            price = best_bid[0] * buyPriceMultiplier


        # Reset order state
        self.grvt_order_filled = False
        self.grvt_order_price = price
        self.grvt_order_side = grvt_side
        self.grvt_order_size = quantity

        try:
            # GRVT uses place_post_only_order with IOC for TAKER execution
            # use_ioc=True for immediate fill (TAKER role in hedge)
            orderResult = await self.grvt_client.place_post_only_order(
                contract_id=self.grvt_contract,  # "ETH_USDT_Perp"
                quantity=quantity,
                price=price,
                side=grvt_side,  # 'buy' or 'sell'
                use_ioc=True  # TAKER: Immediate Or Cancel
            )

            # Extract client_order_id for monitoring
            clientOrderId = None
            if orderResult:
                # OrderInfo object has order_id attribute
                if hasattr(orderResult, 'order_id'):
                    clientOrderId = orderResult.order_id
                elif hasattr(orderResult, 'client_order_id'):
                    clientOrderId = orderResult.client_order_id

            self.logger.info(f"[{clientOrderId}] [{order_type}] [GRVT] [PLACED]: {quantity} @ {price}")

            # Check order status from result
            if orderResult and hasattr(orderResult, 'status'):
                if orderResult.status == 'FILLED':
                    self.logger.info(f"[{clientOrderId}] [{order_type}] [GRVT] [FILLED]: {quantity} @ {price}")
                    # Trigger GRVT order result handling (synchronous method)
                    # Convert side to size sign: sell -> negative, buy -> positive
                    signed_size = -quantity if grvt_side.lower() == 'sell' else quantity
                    self.handle_grvt_order_result({
                        'client_order_id': clientOrderId,
                        'status': 'FILLED',
                        'size': str(signed_size),  # Signed size (negative for SHORT/sell)
                        'average_entry_price': str(price)
                    })
                elif orderResult.status == 'CANCELLED':
                    self.logger.warning(f"[{clientOrderId}] [{order_type}] [GRVT] [CANCELLED]: IOC order not filled")
                else:
                    self.logger.info(f"[{clientOrderId}] [{order_type}] [GRVT] [{orderResult.status}]")
                    await self.monitor_grvt_order(clientOrderId)

            return orderResult
        except Exception as e:
            self.logger.error(f"[ERROR] Error placing GRVT order: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    async def monitor_grvt_order(self, client_order_id: str):
        """Monitor GRVT order and adjust price if needed."""

        start_time = time.time()
        while not self.grvt_order_filled and not self.stop_flag:
            # Check for timeout (30 seconds total)
            if time.time() - start_time > 30:
                elapsed = time.time() - start_time
                self.logger.error("="*60)
                self.logger.error(f"❌ CRITICAL: GRVT order TIMEOUT after {elapsed:.1f}s")
                self.logger.error(f"❌ Order: {self.grvt_order_side} {self.grvt_order_size} @ {self.grvt_order_price}")
                self.logger.error("❌ STOPPING BOT - Manual intervention required")
                self.logger.error("="*60)

                # Send critical Telegram alert
                self.send_telegram_alert(
                    f"<b>🚨 GRVT ORDER TIMEOUT</b>\n\n"
                    f"Ticker: {self.ticker}\n"
                    f"Order: {self.grvt_order_side} {self.grvt_order_size} @ {self.grvt_order_price}\n"
                    f"Timeout: {elapsed:.1f}s\n\n"
                    f"<b>Action:</b> Bot stopped\n"
                    f"<b>Next Step:</b> Manual verification required\n"
                    f"1. Check GRVT API status\n"
                    f"2. Verify actual positions on both exchanges\n"
                    f"3. Resume bot only after confirming hedge balance"
                )

                # STOP BOT IMMEDIATELY (NO FALLBACK)
                self.stop_flag = True
                break

            await asyncio.sleep(0.1)  # Check every 100ms

    # GRVT order modification not needed - uses post-only orders with immediate fill or cancel

    async def setup_backpack_websocket(self):
        """Setup Backpack websocket for order updates and order book data."""
        if not self.backpack_client:
            raise Exception("Backpack client not initialized")

        def order_update_handler(order_data):
            """Handle order updates from Backpack WebSocket."""
            if order_data.get('contract_id') != self.backpack_contract_id:
                return
            try:
                order_id = order_data.get('order_id')
                status = order_data.get('status')
                side = order_data.get('side', '').lower()
                filled_size = Decimal(order_data.get('filled_size', '0'))
                size = Decimal(order_data.get('size', '0'))
                price = order_data.get('price', '0')

                if side == 'buy':
                    order_type = "OPEN"
                else:
                    order_type = "CLOSE"
                
                if status == 'CANCELED' and filled_size > 0:
                    status = 'FILLED'

                # Handle the order update
                if status == 'FILLED' and self.backpack_order_status != 'FILLED':
                    if side == 'buy':
                        self.backpack_position += filled_size
                    else:
                        self.backpack_position -= filled_size
                    self.logger.info(f"[{order_id}] [{order_type}] [Backpack] [{status}]: {filled_size} @ {price}")
                    self.backpack_order_status = status

                    # Log Backpack trade to CSV
                    self.log_trade_to_csv(
                        exchange='Backpack',
                        side=side,
                        price=str(price),
                        quantity=str(filled_size)
                    )

                    # Send telegram alert for Backpack trade
                    tradeMsg = (
                        f"<b>📊 Backpack Trade Filled</b>\n"
                        f"Ticker: {self.ticker}\n"
                        f"Side: {side.upper()}\n"
                        f"Size: {filled_size}\n"
                        f"Price: ${price}\n"
                        f"Position: {self.backpack_position}"
                    )
                    self.send_telegram_alert(tradeMsg)

                    self.handle_backpack_order_update({
                        'order_id': order_id,
                        'side': side,
                        'status': status,
                        'size': size,
                        'price': price,
                        'contract_id': self.backpack_contract_id,
                        'filled_size': filled_size
                    })
                elif self.backpack_order_status != 'FILLED':
                    if status == 'OPEN':
                        self.logger.info(f"[{order_id}] [{order_type}] [Backpack] [{status}]: {size} @ {price}")
                    else:
                        self.logger.info(f"[{order_id}] [{order_type}] [Backpack] [{status}]: {filled_size} @ {price}")
                    self.backpack_order_status = status

            except Exception as e:
                self.logger.error(f"Error handling Backpack order update: {e}")

        try:
            # Setup order update handler
            self.backpack_client.setup_order_update_handler(order_update_handler)
            self.logger.info("✅ Backpack WebSocket order update handler set up")

            # Connect to Backpack WebSocket
            await self.backpack_client.connect()
            self.logger.info("✅ Backpack WebSocket connection established")

            # Setup separate WebSocket connection for depth updates
            await self.setup_backpack_depth_websocket()

        except Exception as e:
            self.logger.error(f"Could not setup Backpack WebSocket handlers: {e}")

    async def setup_backpack_depth_websocket(self):
        """Setup separate WebSocket connection for Backpack depth updates."""
        try:
            import websockets

            async def handle_depth_websocket():
                """Handle depth WebSocket connection."""
                url = "wss://ws.backpack.exchange"

                while not self.stop_flag:
                    try:
                        async with websockets.connect(url) as ws:
                            # Subscribe to depth updates
                            subscribe_message = {
                                "method": "SUBSCRIBE",
                                "params": [f"depth.{self.backpack_contract_id}"]
                            }
                            await ws.send(json.dumps(subscribe_message))
                            self.logger.info(f"✅ Subscribed to depth updates for {self.backpack_contract_id}")

                            # Listen for messages
                            async for message in ws:
                                if self.stop_flag:
                                    break

                                try:
                                    # Handle ping frames
                                    if isinstance(message, bytes) and message == b'\x09':
                                        await ws.pong()
                                        continue

                                    data = json.loads(message)

                                    # Handle depth updates
                                    if data.get('stream') and 'depth' in data.get('stream', ''):
                                        self.handle_backpack_order_book_update(data)

                                except json.JSONDecodeError as e:
                                    self.logger.warning(f"Failed to parse depth WebSocket message: {e}")
                                except Exception as e:
                                    self.logger.error(f"Error handling depth WebSocket message: {e}")

                    except websockets.exceptions.ConnectionClosed:
                        self.logger.warning("Depth WebSocket connection closed, reconnecting...")
                    except Exception as e:
                        self.logger.error(f"Depth WebSocket error: {e}")

                    # Wait before reconnecting
                    if not self.stop_flag:
                        await asyncio.sleep(2)

            # Start depth WebSocket in background
            asyncio.create_task(handle_depth_websocket())
            self.logger.info("✅ Backpack depth WebSocket task started")

        except Exception as e:
            self.logger.error(f"Could not setup Backpack depth WebSocket: {e}")

# DELETED: Duplicate trading_loop() method (replaced with the correct one below at line 1565)

    async def _fetch_grvt_position_rest(self) -> Decimal:
        """
        Fetch actual GRVT position via REST API.

        Returns:
            Decimal: Net position in ETH (positive = long, negative = short)
        """
        try:
            if not self.grvt_client:
                raise Exception("GRVT client not initialized")

            # Fetch positions from GRVT using rest_client
            positions = self.grvt_client.rest_client.fetch_positions()

            net_position = Decimal('0')

            if positions:
                for position in positions:
                    if position.get('instrument') == self.grvt_contract:
                        # GRVT position structure: size (positive=long, negative=short)
                        size = Decimal(str(position.get('size', '0')))
                        net_position = size
                        self.logger.debug(f"Found {self.grvt_contract} position: {size}")
                        break

            return net_position

        except Exception as e:
            self.logger.error(f"❌ Error fetching GRVT position via REST: {e}")
            raise

    async def _fetch_backpack_position_rest(self) -> Decimal:
        """
        Fetch actual Backpack position via REST API.

        Returns:
            Decimal: Net position in ETH (positive = long, negative = short)
        """
        try:
            if not self.backpack_client:
                raise Exception("Backpack client not initialized")

            # Use Backpack client's account_client to get positions
            positions = self.backpack_client.account_client.get_open_positions()

            self.logger.debug(f"Backpack positions response: {positions}")

            # Find ETH_USDC_PERP position
            symbol = f"{self.ticker}_USDC_PERP"
            net_position = Decimal('0')

            if isinstance(positions, list):
                for position in positions:
                    if position.get('symbol') == symbol:
                        # Backpack returns netQuantity as the position
                        net_position = Decimal(str(position.get('netQuantity', '0')))
                        self.logger.debug(f"Found {symbol} position: {net_position}")
                        break

            return net_position

        except Exception as e:
            self.logger.error(f"❌ Error fetching Backpack position via REST: {e}")
            raise

    async def verify_hedge_completion(self) -> bool:
        """
        Verify that hedge is actually balanced by fetching real positions from both exchanges.

        Returns:
            bool: True if hedge is confirmed successful, False otherwise
        """
        try:
            self.logger.info("🔍 [HEDGE VERIFICATION] Starting verification...")

            # Get tolerance and threshold from config
            tolerance = Decimal(str(self.config.get("hedge_verification", "position_tolerance", 0.001)))
            threshold = Decimal(str(self.config.get("trading", "position_diff_threshold", 0.2)))

            # Fetch actual positions from both exchanges
            self.logger.info("🔍 [HEDGE VERIFICATION] Fetching GRVT position via REST...")
            actual_grvt = await self._fetch_grvt_position_rest()

            self.logger.info("🔍 [HEDGE VERIFICATION] Fetching Backpack position via REST...")
            actual_backpack = await self._fetch_backpack_position_rest()

            # Log actual vs tracked positions
            self.logger.info("="*60)
            self.logger.info("📊 [HEDGE VERIFICATION] Position Comparison:")
            self.logger.info(f"   GRVT     - Actual: {actual_grvt:>10} | Tracked: {self.grvt_position:>10}")
            self.logger.info(f"   Backpack - Actual: {actual_backpack:>10} | Tracked: {self.backpack_position:>10}")

            # Check for discrepancies
            grvt_diff = abs(actual_grvt - self.grvt_position)
            backpack_diff = abs(actual_backpack - self.backpack_position)

            if grvt_diff > tolerance:
                self.logger.warning(f"⚠️ [HEDGE VERIFICATION] GRVT position mismatch: {grvt_diff} (tolerance: {tolerance})")
                self.logger.warning(f"⚠️ [HEDGE VERIFICATION] Updating tracked GRVT position: {self.grvt_position} → {actual_grvt}")
                self.grvt_position = actual_grvt

            if backpack_diff > tolerance:
                self.logger.warning(f"⚠️ [HEDGE VERIFICATION] Backpack position mismatch: {backpack_diff} (tolerance: {tolerance})")
                self.logger.warning(f"⚠️ [HEDGE VERIFICATION] Updating tracked Backpack position: {self.backpack_position} → {actual_backpack}")
                self.backpack_position = actual_backpack

            # Calculate net position
            net_position = actual_grvt + actual_backpack
            self.logger.info(f"📊 [HEDGE VERIFICATION] Net Position: {net_position} (threshold: {threshold})")

            # Verify hedge balance
            if abs(net_position) > threshold:
                self.logger.error(f"❌ [HEDGE VERIFICATION] FAILED - Net position {net_position} exceeds threshold {threshold}")
                self.logger.error(f"❌ [HEDGE VERIFICATION] GRVT: {actual_grvt} | Backpack: {actual_backpack}")
                self.logger.info("="*60)
                return False

            self.logger.info(f"✅ [HEDGE VERIFICATION] PASSED - Hedge is balanced")
            self.logger.info("="*60)
            return True

        except Exception as e:
            self.logger.error(f"❌ [HEDGE VERIFICATION] Exception during verification: {e}")
            self.logger.error("❌ [HEDGE VERIFICATION] FAILED - Unable to verify hedge")
            return False

    async def _check_hedge_confirmation_after_fill(self, fill_price: Decimal):
        """
        STORY-003: Check hedge confirmation after GRVT fill if position value exceeds threshold.

        Args:
            fill_price: The price at which the GRVT order was filled
        """
        try:
            # Get hedge confirmation config
            hc_config = self.config.config.get('hedge_confirmation', {})
            if not hc_config.get('enabled', False):
                return  # Hedge confirmation disabled

            activation_threshold = Decimal(str(hc_config.get('activation_threshold_usd', 50.0)))

            # Calculate current position value
            position_value = abs(self.grvt_position) * fill_price

            if position_value >= activation_threshold:
                self.logger.info(f"🔍 [HEDGE CONFIRMATION] Position value ${position_value:.2f} >= ${activation_threshold}")
                self.logger.info(f"🔍 [HEDGE CONFIRMATION] Triggering post-fill verification...")

                hedge_ok = await self.verify_hedge_completion()

                if not hedge_ok and hc_config.get('stop_on_critical', True):
                    self.logger.error("❌ [HEDGE CONFIRMATION] CRITICAL - Stopping bot due to hedge imbalance")
                    self.stop_flag = True

                    # Send Telegram alert
                    alertMsg = (
                        f"<b>🚨 HEDGE CONFIRMATION FAILED</b>\n"
                        f"Ticker: {self.ticker}\n"
                        f"Position Value: ${position_value:.2f}\n"
                        f"Action: Bot stopped for safety"
                    )
                    self.send_telegram_alert(alertMsg)

        except Exception as e:
            self.logger.error(f"Error in hedge confirmation check: {e}")

    async def ensure_clean_start(self):
        """Cancel all open orders before starting trading loop (STORY-V5).

        This prevents Rate Limit Error 1006 caused by stale orders from previous sessions.
        """
        self.logger.info("🧹 [CLEAN START] Checking for stale orders...")
        cancelledCount = 0

        try:
            # GRVT orders
            grvtOrders = await self.grvt_client.get_active_orders(self.grvt_contract)
            if grvtOrders:
                self.logger.warning(f"⚠️ Found {len(grvtOrders)} stale GRVT orders, cancelling...")
                for order in grvtOrders:
                    await self.grvt_client.cancel_order(order.order_id)
                    cancelledCount += 1
                    self.logger.info(f"  ❌ Cancelled GRVT order: {order.order_id}")
        except Exception as e:
            self.logger.error(f"Error cancelling GRVT orders: {e}")

        try:
            # Backpack orders
            bpOrders = await self.backpack_client.get_active_orders(self.backpack_contract_id)
            if bpOrders:
                self.logger.warning(f"⚠️ Found {len(bpOrders)} stale Backpack orders, cancelling...")
                for order in bpOrders:
                    await self.backpack_client.cancel_order(order.order_id)
                    cancelledCount += 1
                    self.logger.info(f"  ❌ Cancelled Backpack order: {order.order_id}")
        except Exception as e:
            self.logger.error(f"Error cancelling Backpack orders: {e}")

        if cancelledCount > 0:
            self.logger.info(f"✅ [CLEAN START] Cancelled {cancelledCount} stale orders")
        else:
            self.logger.info("✅ [CLEAN START] No stale orders found")

    async def trading_loop(self):
        """Main trading loop for hedge bot."""
        self.logger.info(f"🚀 Starting hedge bot for {self.ticker}")

        # ============================================================
        # INITIALIZATION
        # ============================================================
        # Initialize clients
        try:
            self.initialize_grvt_client()
            self.initialize_backpack_client()

            # Get contract info
            self.backpack_contract_id, self.backpack_tick_size = await self.get_backpack_contract_info()
            # GRVT contract symbol already set in __init__ as "ETH_USDT_Perp"

            self.logger.info(f"Contract info loaded - Backpack: {self.backpack_contract_id}, "
                             f"GRVT: {self.grvt_contract}")

            # STORY-V5: Clean Start - Cancel stale orders before trading
            await self.ensure_clean_start()

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize: {e}")
            return

        # Setup Backpack websocket
        try:
            await self.setup_backpack_websocket()
            self.logger.info("✅ Backpack WebSocket connection established")

            # Wait for initial order book data with timeout
            self.logger.info("⏳ Waiting for initial order book data...")
            timeout = 10  # seconds
            start_time = time.time()
            while not self.backpack_order_book_ready and not self.stop_flag:
                if time.time() - start_time > timeout:
                    self.logger.warning(f"⚠️ Timeout waiting for WebSocket order book data after {timeout}s")
                    break
                await asyncio.sleep(0.5)

            if self.backpack_order_book_ready:
                self.logger.info("✅ WebSocket order book data received")
            else:
                self.logger.warning("⚠️ WebSocket order book not ready, will use REST API fallback")

        except Exception as e:
            self.logger.error(f"❌ Failed to setup Backpack websocket: {e}")
            return

        # Setup GRVT REST API polling (replaces WebSocket)
        try:
            self.grvt_ws_task = asyncio.create_task(self.handle_grvt_ws())
            self.logger.info("✅ GRVT order book polling task started")

            # Wait for initial GRVT order book data with timeout
            self.logger.info("⏳ Waiting for initial GRVT order book data...")
            timeout = 10  # seconds
            start_time = time.time()
            while not self.grvt_order_book_ready and not self.stop_flag:
                if time.time() - start_time > timeout:
                    self.logger.warning(f"⚠️ Timeout waiting for GRVT order book data after {timeout}s")
                    break
                await asyncio.sleep(0.5)

            if self.grvt_order_book_ready:
                self.logger.info("✅ GRVT order book data received")
            else:
                self.logger.warning("⚠️ GRVT order book not ready")

        except Exception as e:
            self.logger.error(f"❌ Failed to setup GRVT polling: {e}")
            return

        await asyncio.sleep(5)

        # ============================================================
        # TRADING LOOP
        # ============================================================
        # Send Telegram notification for bot start
        startMsg = (
            f"<b>Hedge Bot Started</b>\n"
            f"Ticker: {self.ticker}\n"
            f"Size: {self.order_quantity}\n"
            f"Iterations: {self.iterations}"
        )
        self.send_telegram_alert(startMsg)

        iterations = 0
        while iterations < self.iterations and not self.stop_flag:
            # Check for stop request from TelegramService
            if self.checkStopFlag():
                self.stop_flag = True
                self.send_telegram_alert(f"<b>🛑 Hedge Bot Stopping</b>\nTicker: {self.ticker}\nReason: Telegram stop command")
                break

            iterations += 1
            self.order_counter = iterations  # Update for status file

            # Update status file with current progress
            self.updateStatusFile(running=True)

            self.logger.info("-----------------------------------------------")
            self.logger.info(f"🔄 Trading loop iteration {iterations}")
            self.logger.info("-----------------------------------------------")

            # Log funding fee status at configured intervals
            self.log_funding_status(iterations)

            # Log balance status at configured intervals
            self.log_balance_status(iterations)

            # Send periodic Telegram status update every 10 iterations
            if iterations % 10 == 0:
                statusMsg = (
                    f"<b>Hedge Bot Status</b>\n"
                    f"Ticker: {self.ticker}\n"
                    f"Progress: {iterations}/{self.iterations}\n"
                    f"Position:\n"
                    f"  Backpack: {self.backpack_position}\n"
                    f"  GRVT: {self.grvt_position}"
                )
                self.send_telegram_alert(statusMsg)

            # ============================================================
            # HEDGE VERIFICATION GATE (매 반복 시작 전)
            # ============================================================
            self.logger.info("="*60)
            self.logger.info(f"🔍 [PRE-ITERATION CHECK] Iteration {iterations}")
            self.logger.info("="*60)

            # Log locally tracked positions
            self.logger.info(f"📊 Tracked - Backpack: {self.backpack_position} | GRVT: {self.grvt_position}")

            # Verify hedge via REST API before proceeding
            self.logger.info("🔍 Verifying hedge balance via REST API...")
            hedge_verified = await self.verify_hedge_completion()

            if not hedge_verified:
                self.logger.error("❌ HEDGE VERIFICATION FAILED - STOPPING BOT")
                self.send_telegram_alert(
                    f"<b>🚨 HEDGE VERIFICATION FAILED</b>\n"
                    f"Ticker: {self.ticker}\n"
                    f"Iteration: {iterations}\n"
                    f"Tracked - BP: {self.backpack_position}, GRVT: {self.grvt_position}\n"
                    f"Action: Bot stopped for safety"
                )
                self.stop_flag = True
                break

            self.logger.info("✅ Hedge verified - safe to proceed with new orders")
            self.logger.info("="*60)

            self.order_execution_complete = False
            self.waiting_for_grvt_fill = False
            try:
                # Get current order size from progressive sizing
                current_price = await self.get_current_price()
                if current_price:
                    dynamic_size = self.progressiveSizing.get_current_size(current_price)
                else:
                    dynamic_size = self.order_quantity  # Fallback to fixed size
                    self.logger.warning("Could not get price, using fixed order size")

                self.logger.info(f"📊 Order size: {dynamic_size} {self.ticker} (${dynamic_size * current_price if current_price else 'N/A'})")

                # Determine side based on some logic (for now, alternate)
                side = 'buy'
                await self.place_backpack_post_only_order(side, dynamic_size)
            except Exception as e:
                self.logger.error(f"⚠️ Error in trading loop: {e}")
                self.logger.error(f"⚠️ Full traceback: {traceback.format_exc()}")
                break

            start_time = time.time()
            while not self.order_execution_complete and not self.stop_flag:
                # Check if Backpack order filled and we need to place GRVT order
                if self.waiting_for_grvt_fill:
                    await self.place_grvt_market_order(
                        self.current_grvt_side,
                        self.current_grvt_quantity,
                        self.current_grvt_price
                    )
                    break

                await asyncio.sleep(0.01)
                if time.time() - start_time > 180:
                    self.logger.error("❌ Timeout waiting for trade completion")
                    break

            if self.stop_flag:
                break

            # Close position
            self.logger.info(f"[STEP 2] Backpack position: {self.backpack_position} | GRVT position: {self.grvt_position}")
            self.order_execution_complete = False
            self.waiting_for_grvt_fill = False
            try:
                # Use same dynamic size for sell order
                side = 'sell'
                await self.place_backpack_post_only_order(side, dynamic_size)
            except Exception as e:
                self.logger.error(f"⚠️ Error in trading loop: {e}")
                self.logger.error(f"⚠️ Full traceback: {traceback.format_exc()}")
                break

            while not self.order_execution_complete and not self.stop_flag:
                # Check if Backpack order filled and we need to place GRVT order
                if self.waiting_for_grvt_fill:
                    await self.place_grvt_market_order(
                        self.current_grvt_side,
                        self.current_grvt_quantity,
                        self.current_grvt_price
                    )
                    break

                await asyncio.sleep(0.01)
                if time.time() - start_time > 180:
                    self.logger.error("❌ Timeout waiting for trade completion")
                    break

            # Close remaining position
            self.logger.info(f"[STEP 3] Backpack position: {self.backpack_position} | GRVT position: {self.grvt_position}")
            self.order_execution_complete = False
            self.waiting_for_grvt_fill = False
            if self.backpack_position == 0:
                continue
            elif self.backpack_position > 0:
                side = 'sell'
            else:
                side = 'buy'

            try:
                # Determine side based on some logic (for now, alternate)
                await self.place_backpack_post_only_order(side, abs(self.backpack_position))
            except Exception as e:
                self.logger.error(f"⚠️ Error in trading loop: {e}")
                self.logger.error(f"⚠️ Full traceback: {traceback.format_exc()}")
                break

            # Wait for order to be filled via WebSocket
            while not self.order_execution_complete and not self.stop_flag:
                # Check if Backpack order filled and we need to place GRVT order
                if self.waiting_for_grvt_fill:
                    await self.place_grvt_market_order(
                        self.current_grvt_side,
                        self.current_grvt_quantity,
                        self.current_grvt_price
                    )
                    break

                await asyncio.sleep(0.01)
                if time.time() - start_time > 180:
                    self.logger.error("❌ Timeout waiting for trade completion")
                    # Record failure for timeout
                    downgraded, failure_msg = self.progressiveSizing.record_failure()
                    if failure_msg:
                        self.logger.warning(f"Progressive Sizing: {failure_msg}")
                        self.send_telegram_alert(f"<b>Progressive Sizing Update</b>\n{failure_msg}")
                    break

            # Record success if iteration completed without errors
            if self.order_execution_complete and not self.stop_flag:
                advanced, success_msg = self.progressiveSizing.record_success()
                if success_msg:
                    self.logger.info(f"Progressive Sizing: {success_msg}")
                    self.send_telegram_alert(f"<b>Progressive Sizing Update</b>\n{success_msg}")

                # Log current progressive sizing status
                ps_status = self.progressiveSizing.get_status_summary()
                self.logger.info(f"\n{ps_status}")

    async def run(self):
        """Run the hedge bot."""
        self.setup_signal_handlers()

        # Update status file to indicate bot is running
        self.updateStatusFile(running=True)

        # Start Telegram command polling in background
        self.startTelegramPolling()

        try:
            await self.trading_loop()
            # Send completion notification
            bpPos = float(self.backpack_position)
            grvtPos = float(self.grvt_position)
            netPos = bpPos + grvtPos
            statusEmoji = "✅" if abs(netPos) < 0.0001 else "⚠️"
            completionMsg = (
                f"<b>✅ Hedge Bot Completed</b>\n"
                f"Ticker: <code>{self.ticker}</code>\n"
                "---\n"
                f"<b>📊 Final Positions:</b>\n"
                f"  Backpack: {bpPos:+.4f} {self.ticker}\n"
                f"  GRVT: {grvtPos:+.4f} {self.ticker}\n"
                f"  Net: {netPos:+.4f} {statusEmoji}\n"
                "---\n"
                f"🔄 Iterations: {self.order_counter}/{self.iterations}"
            )
            self.send_telegram_alert(completionMsg)
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Received interrupt signal...")
            self.send_telegram_alert(f"<b>Hedge Bot Stopped</b>\nTicker: {self.ticker}\nReason: User interrupt")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.send_telegram_alert(f"<b>Hedge Bot Error</b>\nTicker: {self.ticker}\nError: {str(e)[:200]}")
        finally:
            self.logger.info("🔄 Cleaning up...")
            self.shutdown()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Trading bot for Backpack and GRVT')
    parser.add_argument('--exchange', type=str,
                        help='Exchange')
    parser.add_argument('--ticker', type=str, default='BTC',
                        help='Ticker symbol (default: BTC)')
    parser.add_argument('--size', type=str,
                        help='Number of tokens to buy/sell per order')
    parser.add_argument('--iter', type=int,
                        help='Number of iterations to run')
    parser.add_argument('--fill-timeout', type=int, default=5,
                        help='Timeout in seconds for maker order fills (default: 5)')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Path to configuration file (default: config.yaml)')

    return parser.parse_args()


def main():
    """Main entry point for the hedge bot."""
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    args = parse_arguments()

    # Load config to get default values
    config = ConfigLoader(args.config)

    # Get values from args or config (args take precedence)
    orderSize = Decimal(args.size) if args.size else Decimal(str(config.get("trading", "default_size")))
    iterations = args.iter if args.iter else config.get("trading", "default_iterations")

    # Create and run the bot
    bot = HedgeBot(
        ticker=args.ticker,
        order_quantity=orderSize,
        fill_timeout=args.fill_timeout,
        iterations=iterations,
        config_path=args.config
    )

    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
