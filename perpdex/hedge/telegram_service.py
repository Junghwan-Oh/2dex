#!/usr/bin/env python
"""
Telegram Bot Service for Hedge Bot
===================================
독립 실행 가능한 텔레그램 봇 서비스
- menu, help, balance, position, status: 항상 응답 가능
- stop, kill: 봇 실행 중일 때만 활성화
"""

import os
import sys
import json
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import certifi


class TelegramService:
    """독립 실행 가능한 텔레그램 봇 서비스"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chatId = os.getenv("TELEGRAM_CHAT_ID")
        self.baseUrl = "https://api.telegram.org/bot"
        self.apiUrl = f"{self.baseUrl}{self.token}"

        # Session with SSL
        self.session = requests.Session()
        self.session.verify = certifi.where()
        self.session.timeout = 10

        # Update tracking
        self.lastUpdateId = 0

        # Bot state tracking (via status file)
        self.statusFilePath = Path(__file__).parent / "bot_status.json"

        # Command definitions
        self.allCommands = ['menu', 'help', 'balance', 'position', 'stop', 'kill', 'status']
        self.alwaysActiveCommands = ['menu', 'help', 'balance', 'position', 'status']
        self.botActiveOnlyCommands = ['stop', 'kill']

        # Exchange clients (lazy init)
        self.backpackClient = None
        self.lighterBaseUrl = "https://mainnet.zklighter.elliot.ai"
        self.lighterAccountIndex = int(os.getenv('LIGHTER_ACCOUNT_INDEX', '0'))

        # Polling control
        self.running = False
        self.pollingInterval = 2  # seconds

        print("Telegram Service initialized")

    def sendMessage(self, text: str, parseMode: str = "HTML") -> Dict[str, Any]:
        """Send a text message to Telegram"""
        url = f"{self.apiUrl}/sendMessage"
        payload = {
            "chat_id": self.chatId,
            "text": text,
            "parse_mode": parseMode
        }
        try:
            response = self.session.post(url, json=payload)
            return response.json()
        except Exception as e:
            print(f"Send message error: {e}")
            return {"ok": False, "error": str(e)}

    def sendMenu(self, text: str = "Select a command:") -> Dict[str, Any]:
        """Send inline keyboard menu"""
        botStatus = self.getBotStatus()
        isRunning = botStatus.get("running", False)

        # Dynamic button text based on bot status
        stopText = "🛑 Stop" if isRunning else "⏹ Stop (inactive)"
        killText = "💀 Kill" if isRunning else "⏹ Kill (inactive)"

        inlineKeyboard = [
            [
                {"text": "💰 Balance", "callback_data": "balance"},
                {"text": "📊 Position", "callback_data": "position"}
            ],
            [
                {"text": stopText, "callback_data": "stop"},
                {"text": killText, "callback_data": "kill"}
            ],
            [
                {"text": "📈 Status", "callback_data": "status"}
            ]
        ]

        url = f"{self.apiUrl}/sendMessage"
        payload = {
            "chat_id": self.chatId,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": inlineKeyboard}
        }
        try:
            response = self.session.post(url, json=payload)
            return response.json()
        except Exception as e:
            print(f"Send menu error: {e}")
            return {"ok": False, "error": str(e)}

    def answerCallback(self, callbackQueryId: str, text: str = "") -> Dict[str, Any]:
        """Answer callback query"""
        url = f"{self.apiUrl}/answerCallbackQuery"
        payload = {
            "callback_query_id": callbackQueryId,
            "text": text
        }
        try:
            response = self.session.post(url, json=payload)
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def getUpdates(self, timeout: int = 30) -> list:
        """Get updates from Telegram (long polling)"""
        url = f"{self.apiUrl}/getUpdates"
        params = {"timeout": timeout}
        if self.lastUpdateId > 0:
            params["offset"] = self.lastUpdateId + 1

        try:
            response = self.session.get(url, params=params, timeout=timeout + 10)
            data = response.json()
            if data.get("ok", False):
                return data.get("result", [])
            return []
        except Exception as e:
            print(f"Get updates error: {e}")
            return []

    def getBotStatus(self) -> Dict[str, Any]:
        """Read bot status from status file"""
        try:
            if self.statusFilePath.exists():
                with open(self.statusFilePath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Read status error: {e}")
        return {"running": False, "ticker": None, "iteration": 0, "iterations": 0}

    def setBotStopFlag(self) -> bool:
        """Set stop flag in status file to signal bot to stop"""
        try:
            status = self.getBotStatus()
            status["stop_requested"] = True
            status["stop_time"] = datetime.now().isoformat()
            with open(self.statusFilePath, 'w') as f:
                json.dump(status, f, indent=2)
            return True
        except Exception as e:
            print(f"Set stop flag error: {e}")
            return False

    def initBackpackClient(self):
        """Initialize Backpack client for balance queries"""
        if self.backpackClient is None:
            try:
                from exchanges.backpack import BackpackClient
                from decimal import Decimal

                # Check required env vars
                publicKey = os.getenv("BACKPACK_PUBLIC_KEY")
                secretKey = os.getenv("BACKPACK_SECRET_KEY")

                if not publicKey or not secretKey:
                    print("Backpack keys not found in env")
                    return

                # Create Config class (same as hedge_mode_bp.py)
                class Config:
                    def __init__(self, config_dict):
                        for key, value in config_dict.items():
                            setattr(self, key, value)

                # Minimal config for balance/position queries
                configDict = {
                    'ticker': 'ETH',
                    'contract_id': '',
                    'quantity': Decimal('0.01'),
                    'tick_size': Decimal('0.01'),
                    'close_order_side': 'sell'
                }
                config = Config(configDict)

                self.backpackClient = BackpackClient(config)
                print("Backpack client initialized successfully")
            except Exception as e:
                print(f"Backpack client init error: {e}")
                import traceback
                traceback.print_exc()

    def getBalanceMessage(self) -> str:
        """
        Get formatted balance message
        Shows: Available Margin + Position Value = Total Equity
        """
        try:
            lines = ["<b>💰 Account Balances</b>", ""]

            # ========== Backpack Balance ==========
            lines.append("<b>📦 Backpack:</b>")
            self.initBackpackClient()
            if self.backpackClient:
                try:
                    # Use get_collateral() for accurate account equity info
                    collateral = self.backpackClient.account_client.get_collateral()
                    if collateral:
                        # netEquityAvailable: Available Equity (can trade with)
                        # netEquityLocked: Initial Margin (locked in positions)
                        # netEquity: Total Equity
                        availableEquity = float(collateral.get('netEquityAvailable', 0))
                        initialMargin = float(collateral.get('netEquityLocked', 0))
                        totalEquity = float(collateral.get('netEquity', 0))

                        lines.append(f"  Available: <code>{availableEquity:.2f}</code> USDC")
                        lines.append(f"  Initial Margin: <code>{initialMargin:.2f}</code> USDC")
                        lines.append(f"  Total: <code>{totalEquity:.2f}</code> USDC")
                    else:
                        lines.append("  No collateral data")
                except Exception as e:
                    lines.append(f"  Error: {str(e)[:50]}")
            else:
                lines.append("  Client not initialized")

            lines.append("")

            # ========== Lighter Balance ==========
            lines.append("<b>⚡ Lighter:</b>")
            try:
                url = f"{self.lighterBaseUrl}/api/v1/account?by=index&value={self.lighterAccountIndex}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get('accounts', [])
                    if accounts and len(accounts) > 0:
                        acc = accounts[0]
                        # collateral: Available to Trade (free margin)
                        # allocated_margin: Margin locked in positions
                        # total_asset_value: Total portfolio value
                        availableToTrade = float(acc.get('collateral', 0))
                        totalAssetValue = float(acc.get('total_asset_value', 0))

                        # Sum allocated_margin from all positions
                        allocatedMargin = 0.0
                        for pos in acc.get('positions', []):
                            allocatedMargin += float(pos.get('allocated_margin', 0))

                        lines.append(f"  Available: <code>{availableToTrade:.2f}</code> USDC")
                        lines.append(f"  Margin: <code>{allocatedMargin:.2f}</code> USDC")
                        lines.append(f"  Total: <code>{totalAssetValue:.2f}</code> USDC")
                    else:
                        lines.append("  No account data")
                else:
                    lines.append(f"  API Error: {response.status_code}")
            except Exception as e:
                lines.append(f"  Error: {str(e)[:50]}")

            return "\n".join(lines)
        except Exception as e:
            return f"<b>Balance Error:</b> {e}"

    def getPositionMessage(self) -> str:
        """
        Get formatted position message
        Shows ALL open positions (ETH, BTC, etc.) on both exchanges
        """
        try:
            lines = ["<b>📊 Open Positions</b>", ""]

            # ========== Backpack Positions ==========
            lines.append("<b>📦 Backpack:</b>")
            bpPositions = []
            self.initBackpackClient()
            if self.backpackClient:
                try:
                    positions = self.backpackClient.account_client.get_open_positions()
                    if positions:
                        for pos in positions:
                            symbol = pos.get('symbol', 'UNKNOWN')
                            # Use netQuantity (actual field name in API response)
                            netSize = float(pos.get('netQuantity', 0))
                            entryPrice = float(pos.get('entryPrice', 0))
                            breakEvenPrice = float(pos.get('breakEvenPrice', 0))
                            markPrice = float(pos.get('markPrice', 0))
                            # Total PnL = Realized (funding) + Unrealized (position)
                            unrealizedPnl = float(pos.get('pnlUnrealized', 0))
                            realizedPnl = float(pos.get('pnlRealized', 0))
                            totalPnl = realizedPnl + unrealizedPnl

                            if abs(netSize) > 0.00001:  # Filter out zero positions
                                ticker = symbol.replace('_USDC_PERP', '').replace('_PERP', '')
                                side = "LONG" if netSize > 0 else "SHORT"
                                sideEmoji = "🟢" if netSize > 0 else "🔴"
                                pnlSign = "+" if totalPnl >= 0 else ""

                                bpPositions.append({
                                    'ticker': ticker,
                                    'size': netSize,
                                    'side': side,
                                    'sideEmoji': sideEmoji,
                                    'entryPrice': entryPrice,
                                    'breakEvenPrice': breakEvenPrice,
                                    'markPrice': markPrice,
                                    'pnl': totalPnl,
                                    'pnlSign': pnlSign
                                })

                    if bpPositions:
                        for p in bpPositions:
                            lines.append(f"  {p['sideEmoji']} <b>{p['ticker']}</b>: {p['size']:+.4f} ({p['side']})")
                            lines.append(f"     Entry: ${p['entryPrice']:.2f} | B/E: ${p['breakEvenPrice']:.2f}")
                            lines.append(f"     Mark: ${p['markPrice']:.2f} | PnL: <code>{p['pnlSign']}${p['pnl']:.2f}</code>")
                    else:
                        lines.append("  No open positions")
                except Exception as e:
                    lines.append(f"  Error: {str(e)[:50]}")
            else:
                lines.append("  Client not initialized")

            lines.append("")

            # ========== Lighter Positions ==========
            lines.append("<b>⚡ Lighter:</b>")
            ltPositions = []
            try:
                # Use account endpoint which includes positions
                url = f"{self.lighterBaseUrl}/api/v1/account?by=index&value={self.lighterAccountIndex}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get('accounts', [])
                    if accounts and len(accounts) > 0:
                        positions = accounts[0].get('positions', [])

                        for pos in positions:
                            symbol = pos.get('symbol', 'UNKNOWN')
                            # sign: -1=short, 1=long
                            sign = pos.get('sign', 0)
                            size = float(pos.get('position', 0))
                            entryPrice = float(pos.get('avg_entry_price', 0))
                            unrealizedPnl = float(pos.get('unrealized_pnl', 0))

                            if abs(size) > 0.00001:
                                # Apply sign to size for display
                                signedSize = size * sign
                                side = "LONG" if sign > 0 else "SHORT"
                                sideEmoji = "🟢" if sign > 0 else "🔴"
                                pnlSign = "+" if unrealizedPnl >= 0 else ""

                                ltPositions.append({
                                    'ticker': symbol,
                                    'size': signedSize,
                                    'side': side,
                                    'sideEmoji': sideEmoji,
                                    'entryPrice': entryPrice,
                                    'pnl': unrealizedPnl,
                                    'pnlSign': pnlSign
                                })

                    if ltPositions:
                        for p in ltPositions:
                            lines.append(f"  {p['sideEmoji']} <b>{p['ticker']}</b>: {p['size']:+.4f} ({p['side']})")
                            if p['entryPrice'] > 0:
                                lines.append(f"     Entry: ${p['entryPrice']:.2f}")
                            if p['pnl'] != 0:
                                lines.append(f"     PnL: <code>{p['pnlSign']}${p['pnl']:.2f}</code>")
                    else:
                        lines.append("  No open positions")
                else:
                    lines.append(f"  API Error: {response.status_code}")
            except Exception as e:
                lines.append(f"  Error: {str(e)[:50]}")

            # ========== Net Position Summary (for hedge tracking) ==========
            lines.append("")
            lines.append("<b>🔄 Hedge Summary:</b>")

            # Calculate net positions by ticker
            allPositions = {}
            for p in bpPositions:
                ticker = p['ticker']
                if ticker not in allPositions:
                    allPositions[ticker] = {'bp': 0, 'lt': 0}
                allPositions[ticker]['bp'] = p['size']

            for p in ltPositions:
                ticker = p['ticker']
                if ticker not in allPositions:
                    allPositions[ticker] = {'bp': 0, 'lt': 0}
                allPositions[ticker]['lt'] = p['size']

            if allPositions:
                for ticker, sizes in allPositions.items():
                    bpSize = sizes['bp']
                    ltSize = sizes['lt']
                    netSize = bpSize + ltSize
                    statusEmoji = "✅" if abs(netSize) < 0.0001 else "⚠️"
                    lines.append(f"  <b>{ticker}</b>: BP {bpSize:+.4f} + LT {ltSize:+.4f} = Net {netSize:+.4f} {statusEmoji}")
            else:
                lines.append("  No positions to hedge")

            return "\n".join(lines)
        except Exception as e:
            return f"<b>Position Error:</b> {e}"

    def getStatusMessage(self) -> str:
        """Get bot status message (running state only)"""
        status = self.getBotStatus()
        running = status.get("running", False)
        ticker = status.get("ticker", "N/A")
        iteration = status.get("iteration", 0)
        iterations = status.get("iterations", 0)
        startTime = status.get("start_time", "N/A")
        orderSize = status.get("order_size", "N/A")

        statusEmoji = "🟢" if running else "🔴"
        statusText = "RUNNING" if running else "STOPPED"

        lines = [
            "<b>🤖 Hedge Bot Status</b>",
            "",
            f"<b>Status:</b> {statusEmoji} {statusText}",
        ]

        if running:
            lines.extend([
                f"<b>Ticker:</b> {ticker}",
                f"<b>Order Size:</b> {orderSize}",
                f"<b>Progress:</b> {iteration}/{iterations}",
                f"<b>Started:</b> {startTime[:19] if startTime != 'N/A' else 'N/A'}"
            ])
        else:
            lines.extend([
                "",
                "Bot is not running.",
                "Start with:",
                "<code>python hedge_mode_bp.py --ticker ETH --size 0.01 --iter 5</code>"
            ])

        return "\n".join(lines)

    def getHelpMessage(self) -> str:
        """Get help message"""
        return (
            "<b>📚 Hedge Bot Commands</b>\n"
            "\n"
            "<b>Always Available:</b>\n"
            "• <code>/menu</code> - Control panel\n"
            "• <code>/help</code> - This help\n"
            "• <code>balance</code> - Account balances (Margin + Position Value)\n"
            "• <code>position</code> - All open positions (ETH, BTC, etc.)\n"
            "• <code>status</code> - Bot running state\n"
            "\n"
            "<b>Bot Running Only:</b>\n"
            "• <code>stop</code> - Stop after current iteration\n"
            "• <code>kill</code> - Stop immediately\n"
            "\n"
            "💡 Use /menu for quick access"
        )

    async def handleCommand(self, command: str) -> None:
        """Handle incoming command"""
        command = command.lower().strip()
        print(f"[CMD] Processing: {command}")

        if command in ['menu', '/menu']:
            # Build menu text
            status = self.getBotStatus()
            running = status.get("running", False)
            ticker = status.get("ticker", "ETH")
            iteration = status.get("iteration", 0)
            iterations = status.get("iterations", 0)

            runningIcon = "🟢" if running else "🔴"
            menuText = (
                f"<b>🤖 Hedge Bot Control Panel</b>\n"
                f"Status: {runningIcon} {'Running' if running else 'Stopped'}\n"
            )
            if running:
                menuText += f"Ticker: <code>{ticker}</code>\n"
                menuText += f"Progress: {iteration}/{iterations}\n"
            menuText += "\nSelect a command:"
            self.sendMenu(menuText)

        elif command in ['help', '/help']:
            self.sendMessage(self.getHelpMessage())

        elif command in ['balance', '/balance']:
            self.sendMessage(self.getBalanceMessage())

        elif command in ['position', '/position']:
            self.sendMessage(self.getPositionMessage())

        elif command in ['status', '/status']:
            self.sendMessage(self.getStatusMessage())

        elif command in ['stop', '/stop', 'kill', '/kill']:
            status = self.getBotStatus()
            if status.get("running", False):
                if self.setBotStopFlag():
                    action = "stopping gracefully" if command in ['stop', '/stop'] else "killing"
                    self.sendMessage(f"<b>🛑 Bot {action}...</b>\nCommand received.")
                else:
                    self.sendMessage("<b>❌ Error:</b> Could not set stop flag")
            else:
                self.sendMessage(
                    "<b>⚠️ Bot is not running</b>\n"
                    "Start the bot first with:\n"
                    "<code>python hedge_mode_bp.py --ticker ETH --size 0.01 --iter 5</code>"
                )

    async def processUpdates(self) -> None:
        """Process incoming updates"""
        updates = self.getUpdates(timeout=30)

        for update in updates:
            updateId = update.get("update_id", 0)
            if updateId > self.lastUpdateId:
                self.lastUpdateId = updateId

            # Handle callback query (button clicks)
            callbackQuery = update.get("callback_query")
            if callbackQuery:
                callbackQueryId = callbackQuery.get("id")
                callbackData = callbackQuery.get("data", "")
                chatId = str(callbackQuery.get("message", {}).get("chat", {}).get("id", ""))

                if chatId == str(self.chatId):
                    self.answerCallback(callbackQueryId, f"Processing: {callbackData}")
                    await self.handleCommand(callbackData)
                continue

            # Handle text message
            message = update.get("message", {})
            chatId = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "").strip()

            if chatId == str(self.chatId) and text:
                await self.handleCommand(text)

    async def run(self):
        """Run the telegram service (blocking)"""
        print("Telegram Service starting...")
        print(f"Listening for commands from chat: {self.chatId}")

        # Clear pending updates
        updates = self.getUpdates(timeout=1)
        if updates:
            self.lastUpdateId = max(u.get("update_id", 0) for u in updates)
            print(f"Cleared {len(updates)} pending updates")

        self.running = True

        # Send startup notification
        self.sendMessage(
            "<b>🤖 Telegram Service Online</b>\n"
            "Commands: /menu, /help, /balance, /position, /status\n"
            "Send /menu to start!"
        )

        try:
            while self.running:
                try:
                    await self.processUpdates()
                except Exception as e:
                    print(f"Process updates error: {e}")
                    await asyncio.sleep(5)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False
            print("Telegram Service stopped")


def main():
    """Main entry point"""
    load_dotenv()

    # Check required env vars
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("Error: TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    if not os.getenv("TELEGRAM_CHAT_ID"):
        print("Error: TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    service = TelegramService()
    asyncio.run(service.run())


if __name__ == "__main__":
    main()
