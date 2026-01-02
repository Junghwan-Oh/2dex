"""
2DEX Hedge Mode - Dynamic Dual Exchange Hedge Bot

This module implements a hedge trading bot that works with any two exchanges dynamically.
PRIMARY exchange places maker orders (POST_ONLY for rebates), HEDGE exchange places taker orders.

Usage:
    python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.01 --iter 10
"""

import asyncio
import logging
import os
import signal
import sys
import csv
from decimal import Decimal
from datetime import datetime
from typing import Optional

import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.factory import ExchangeFactory
from exchanges.base import BaseExchangeClient, OrderResult, OrderInfo


class Config:
    """Simple config class to wrap dictionary for exchange clients."""
    def __init__(self, configDict: dict):
        for key, value in configDict.items():
            setattr(self, key, value)


# NOTE: Contract IDs and tick sizes are dynamically fetched via get_contract_attributes()
# Each exchange client implements this method to query the API for correct values.
# See: exchanges/backpack.py:578, exchanges/grvt.py:529


class HedgeBot2DEX:
    """Trading bot that places maker orders on PRIMARY and hedges with taker orders on HEDGE."""

    def __init__(
        self,
        primaryExchange: str,
        hedgeExchange: str,
        ticker: str,
        orderQuantity: Decimal,
        fillTimeout: int = 5,
        iterations: int = 20,
        sleepTime: int = 0,
        maxPosition: Decimal = Decimal('0')
    ):
        self.primaryExchangeName = primaryExchange.lower()
        self.hedgeExchangeName = hedgeExchange.lower()
        self.ticker = ticker.upper()
        self.orderQuantity = orderQuantity
        self.fillTimeout = fillTimeout
        self.iterations = iterations
        self.sleepTime = sleepTime
        self.maxPosition = maxPosition if maxPosition > 0 else orderQuantity

        # Initialize logging
        os.makedirs("logs", exist_ok=True)
        self.logFilename = f"logs/2dex_{primaryExchange}_{hedgeExchange}_{ticker}_log.txt"
        self.csvFilename = f"logs/2dex_{primaryExchange}_{hedgeExchange}_{ticker}_trades.csv"
        self._initializeCsvFile()

        # Setup logger
        self.logger = logging.getLogger(f"hedge_2dex_{primaryExchange}_{hedgeExchange}_{ticker}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # Disable verbose logging from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)

        # File handler
        fileHandler = logging.FileHandler(self.logFilename)
        fileHandler.setLevel(logging.INFO)
        fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fileHandler)

        # Console handler
        consoleHandler = logging.StreamHandler(sys.stdout)
        consoleHandler.setLevel(logging.INFO)
        consoleHandler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
        self.logger.addHandler(consoleHandler)

        self.logger.propagate = False

        # State management
        self.stopFlag = False
        self.orderCounter = 0
        self.positionImbalance = Decimal('0')

        # Exchange clients (initialized later)
        self.primaryClient: Optional[BaseExchangeClient] = None
        self.hedgeClient: Optional[BaseExchangeClient] = None

        # Contract IDs
        self.primaryContractId = None
        self.hedgeContractId = None

        # Tick sizes
        self.primaryTickSize = None
        self.hedgeTickSize = None

        # Fill rate tracking
        self.fillRateStats = {
            'attempts': 0,
            'filled': 0,
            'timeout': 0,
            'cancelled': 0,
            'total_volume': Decimal('0')
        }

        # Rate limit backoff (for GRVT 429 errors)
        self.rateLimitBackoff = 1  # seconds
        self.maxBackoff = 60  # max 60 seconds

    def _initializeCsvFile(self):
        """Initialize CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csvFilename):
            with open(self.csvFilename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['exchange', 'role', 'timestamp', 'side', 'price', 'quantity', 'status'])

    def logTradeToCsv(self, exchange: str, role: str, side: str, price: str, quantity: str, status: str):
        """Log trade details to CSV file."""
        timestamp = datetime.now(pytz.UTC).isoformat()
        with open(self.csvFilename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([exchange, role, timestamp, side, price, quantity, status])

    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown handler."""
        self.stopFlag = True
        self.logger.info("\n[STOP] Stopping 2DEX hedge bot...")

    async def initializeClients(self) -> bool:
        """Initialize PRIMARY and HEDGE exchange clients using ExchangeFactory.

        Uses get_contract_attributes() to dynamically fetch contract_id and tick_size.
        """
        self.logger.info(f"[INIT] Initializing clients: PRIMARY={self.primaryExchangeName}, HEDGE={self.hedgeExchangeName}")

        # Create configs with ticker and quantity (required by get_contract_attributes)
        # Also include contract_id and tick_size with defaults (required by some exchanges' connect())
        # These will be properly set after get_contract_attributes() is called
        primaryConfig = Config({
            'ticker': self.ticker,
            'quantity': self.orderQuantity,
            'contract_id': '',  # Placeholder, will be set by get_contract_attributes()
            'tick_size': Decimal('0.01'),  # Default, will be updated
        })
        hedgeConfig = Config({
            'ticker': self.ticker,
            'quantity': self.orderQuantity,
            'contract_id': '',  # Placeholder, will be set by get_contract_attributes()
            'tick_size': Decimal('0.01'),  # Default, will be updated
        })

        try:
            # Create and connect PRIMARY client
            self.logger.info(f"[CONN] Creating PRIMARY client: {self.primaryExchangeName}")
            self.primaryClient = ExchangeFactory.create_exchange(self.primaryExchangeName, primaryConfig)
            await self.primaryClient.connect()

            # Dynamically fetch contract_id and tick_size from API
            self.primaryContractId, self.primaryTickSize = await self.primaryClient.get_contract_attributes()
            self.logger.info(f"[OK] PRIMARY ({self.primaryExchangeName}) connected: contract={self.primaryContractId}, tick={self.primaryTickSize}")

            # Create and connect HEDGE client
            self.logger.info(f"[CONN] Creating HEDGE client: {self.hedgeExchangeName}")
            self.hedgeClient = ExchangeFactory.create_exchange(self.hedgeExchangeName, hedgeConfig)
            await self.hedgeClient.connect()

            # Dynamically fetch contract_id and tick_size from API
            self.hedgeContractId, self.hedgeTickSize = await self.hedgeClient.get_contract_attributes()
            self.logger.info(f"[OK] HEDGE ({self.hedgeExchangeName}) connected: contract={self.hedgeContractId}, tick={self.hedgeTickSize}")

            return True

        except Exception as e:
            self.logger.error(f"[ERROR] Failed to initialize clients: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # Clean up any partially initialized clients
            if self.primaryClient:
                try:
                    await self.primaryClient.disconnect()
                except Exception:
                    pass
            if self.hedgeClient:
                try:
                    await self.hedgeClient.disconnect()
                except Exception:
                    pass
            return False

    async def executeHedgeCycle(self, direction: str) -> bool:
        """Execute a single hedge cycle.

        Args:
            direction: 'buy' or 'sell' for PRIMARY side

        Returns:
            True if cycle completed successfully
        """
        self.orderCounter += 1
        self.fillRateStats['attempts'] += 1
        oppositeDirection = 'sell' if direction == 'buy' else 'buy'

        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"[CYCLE {self.orderCounter}] PRIMARY {direction.upper()} -> HEDGE {oppositeDirection.upper()}")

        try:
            # Apply rate limit backoff if needed
            if self.rateLimitBackoff > 1:
                self.logger.info(f"[BACKOFF] Waiting {self.rateLimitBackoff}s due to rate limit...")
                await asyncio.sleep(self.rateLimitBackoff)
            # Step 1: Get BBO from PRIMARY
            self.logger.info(f"[BBO] Fetching from PRIMARY ({self.primaryExchangeName})...")
            bboPrices = await self.primaryClient.fetch_bbo_prices(self.primaryContractId)
            if not bboPrices:
                self.logger.warning("[WARN] Failed to get BBO prices from PRIMARY")
                return False

            bestBid, bestAsk = bboPrices
            self.logger.info(f"[BBO] PRIMARY: Bid={bestBid}, Ask={bestAsk}")

            # Determine maker price (post-only)
            if direction == 'buy':
                makerPrice = bestBid  # Buy at bid (maker)
            else:
                makerPrice = bestAsk  # Sell at ask (maker)

            # Step 2: Place POST_ONLY maker order on PRIMARY
            self.logger.info(f"[ORDER] Placing {direction.upper()} maker on PRIMARY @ {makerPrice}")
            primaryResult = await self.primaryClient.place_open_order(
                self.primaryContractId,
                self.orderQuantity,
                direction
            )

            if not primaryResult.success:
                self.logger.warning(f"[WARN] PRIMARY order failed: {primaryResult.error_message}")

                # Check for rate limit (429 error)
                if '429' in str(primaryResult.error_message) or 'rate limit' in str(primaryResult.error_message).lower():
                    self.rateLimitBackoff = min(self.rateLimitBackoff * 2, self.maxBackoff)
                    self.logger.warning(f"[RATE_LIMIT] Detected, increasing backoff to {self.rateLimitBackoff}s")

                return False

            self.logger.info(f"[OK] PRIMARY order placed: ID={primaryResult.order_id}")
            self.logTradeToCsv(
                self.primaryExchangeName, 'PRIMARY', direction,
                str(makerPrice), str(self.orderQuantity), 'placed'
            )

            # Step 3: Wait for fill with timeout
            fillStartTime = asyncio.get_event_loop().time()
            filledSize = Decimal('0')
            orderFilled = False

            while asyncio.get_event_loop().time() - fillStartTime < self.fillTimeout:
                if self.stopFlag:
                    # Cancel pending order on shutdown
                    await self.primaryClient.cancel_order(primaryResult.order_id)
                    return False

                orderInfo = await self.primaryClient.get_order_info(primaryResult.order_id)
                if orderInfo:
                    if orderInfo.status in ['filled', 'FILLED', 'Filled']:
                        filledSize = orderInfo.filled_size if orderInfo.filled_size else self.orderQuantity
                        orderFilled = True
                        self.logger.info(f"[FILLED] PRIMARY order FILLED: {filledSize}")
                        break
                    elif orderInfo.status in ['partially_filled', 'PARTIALLY_FILLED', 'PartiallyFilled']:
                        filledSize = orderInfo.filled_size if orderInfo.filled_size else Decimal('0')
                        if filledSize > 0:
                            orderFilled = True
                            self.logger.info(f"[PARTIAL] PRIMARY order PARTIAL: {filledSize}/{self.orderQuantity}")
                            break
                    elif orderInfo.status in ['cancelled', 'CANCELLED', 'Cancelled', 'rejected', 'REJECTED']:
                        self.logger.info(f"[CANCEL] PRIMARY order cancelled/rejected")
                        return False

                await asyncio.sleep(0.1)

            # Step 4: Handle fill status
            if not orderFilled or filledSize <= 0:
                self.logger.info(f"[TIMEOUT] PRIMARY order not filled within {self.fillTimeout}s, cancelling...")
                await self.primaryClient.cancel_order(primaryResult.order_id)
                self.fillRateStats['timeout'] += 1
                self.logTradeToCsv(
                    self.primaryExchangeName, 'PRIMARY', direction,
                    str(makerPrice), str(self.orderQuantity), 'cancelled'
                )
                return False

            # Update fill rate stats
            self.fillRateStats['filled'] += 1
            self.fillRateStats['total_volume'] += filledSize

            # Reset rate limit backoff on successful fill
            if self.rateLimitBackoff > 1:
                self.rateLimitBackoff = max(1, self.rateLimitBackoff / 2)
                self.logger.info(f"[BACKOFF] Successful fill, reducing backoff to {self.rateLimitBackoff}s")

            self.logTradeToCsv(
                self.primaryExchangeName, 'PRIMARY', direction,
                str(makerPrice), str(filledSize), 'filled'
            )

            # Step 5: Place market order on HEDGE for filled amount
            self.logger.info(f"[HEDGE] Placing {oppositeDirection.upper()} market order on HEDGE for {filledSize}")
            hedgeResult = await self.hedgeClient.place_market_order(
                self.hedgeContractId,
                filledSize,
                oppositeDirection
            )

            if not hedgeResult.success:
                self.logger.error(f"[FAIL] HEDGE order FAILED: {hedgeResult.error_message}")
                self.logger.error(f"[IMBALANCE] POSITION IMBALANCE: {filledSize} {direction} on PRIMARY not hedged!")
                self.positionImbalance += filledSize if direction == 'buy' else -filledSize
                self.logTradeToCsv(
                    self.hedgeExchangeName, 'HEDGE', oppositeDirection,
                    'N/A', str(filledSize), 'FAILED'
                )
                return False

            hedgePrice = hedgeResult.price if hedgeResult.price else 'market'
            self.logger.info(f"[OK] HEDGE order FILLED @ {hedgePrice}")
            self.logTradeToCsv(
                self.hedgeExchangeName, 'HEDGE', oppositeDirection,
                str(hedgePrice), str(filledSize), 'filled'
            )

            self.logger.info(f"[DONE] Cycle {self.orderCounter} COMPLETE")
            return True

        except Exception as e:
            self.logger.error(f"[ERROR] Cycle error: {e}")
            return False

    async def tradingLoop(self):
        """Main trading loop."""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"[START] Starting 2DEX Trading Loop")
        self.logger.info(f"   PRIMARY: {self.primaryExchangeName} (maker, POST_ONLY)")
        self.logger.info(f"   HEDGE: {self.hedgeExchangeName} (taker, market)")
        self.logger.info(f"   Ticker: {self.ticker}")
        self.logger.info(f"   Quantity: {self.orderQuantity}")
        self.logger.info(f"   Iterations: {self.iterations}")
        self.logger.info(f"   Fill Timeout: {self.fillTimeout}s")
        self.logger.info(f"{'='*60}\n")

        # Initialize clients
        if not await self.initializeClients():
            self.logger.error("[ERROR] Failed to initialize exchange clients. Aborting.")
            return

        try:
            direction = 'buy'  # Start with buy
            successCount = 0
            failCount = 0

            for i in range(self.iterations):
                if self.stopFlag:
                    self.logger.info("[STOP] Stop flag detected, exiting loop")
                    break

                success = await self.executeHedgeCycle(direction)
                if success:
                    successCount += 1
                else:
                    failCount += 1

                # Alternate direction
                direction = 'sell' if direction == 'buy' else 'buy'

                # Sleep between cycles
                if self.sleepTime > 0 and i < self.iterations - 1:
                    self.logger.info(f"[SLEEP] Sleeping {self.sleepTime}s...")
                    await asyncio.sleep(self.sleepTime)

            # Summary
            fillRate = (self.fillRateStats['filled'] / self.fillRateStats['attempts'] * 100) if self.fillRateStats['attempts'] > 0 else 0

            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"[SUMMARY] SESSION SUMMARY")
            self.logger.info(f"   Total Cycles: {self.orderCounter}")
            self.logger.info(f"   Successful: {successCount}")
            self.logger.info(f"   Failed: {failCount}")
            self.logger.info(f"   Position Imbalance: {self.positionImbalance}")
            self.logger.info(f"\n[FILL RATE STATS]")
            self.logger.info(f"   Fill Rate: {fillRate:.1f}% ({self.fillRateStats['filled']}/{self.fillRateStats['attempts']})")
            self.logger.info(f"   Filled: {self.fillRateStats['filled']} orders")
            self.logger.info(f"   Timeout: {self.fillRateStats['timeout']} orders")
            self.logger.info(f"   Total Volume: {self.fillRateStats['total_volume']} {self.ticker}")
            self.logger.info(f"{'='*60}\n")

        except Exception as e:
            self.logger.error(f"[ERROR] Trading loop error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("[CLEANUP] Cleaning up...")

        if self.primaryClient:
            try:
                await self.primaryClient.disconnect()
                self.logger.info(f"[DISCONN] PRIMARY ({self.primaryExchangeName}) disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting PRIMARY: {e}")

        if self.hedgeClient:
            try:
                await self.hedgeClient.disconnect()
                self.logger.info(f"[DISCONN] HEDGE ({self.hedgeExchangeName}) disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting HEDGE: {e}")

        # Close logging handlers
        for handler in self.logger.handlers[:]:
            try:
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                pass

    async def run(self):
        """Main entry point."""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.logger.info(f"[BOT] 2DEX Hedge Bot Starting...")
        self.logger.info(f"   PRIMARY: {self.primaryExchangeName}")
        self.logger.info(f"   HEDGE: {self.hedgeExchangeName}")

        try:
            await self.tradingLoop()
        except KeyboardInterrupt:
            self.logger.info("\n[INT] Interrupted by user")
        except Exception as e:
            self.logger.error(f"[FATAL] Fatal error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            self.logger.info("[END] 2DEX Hedge Bot Stopped")
