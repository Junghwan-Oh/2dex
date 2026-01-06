"""
2DEX Hedge Mode - Dynamic Dual Exchange Hedge Bot

This module implements a hedge trading bot that works with any two exchanges dynamically.
PRIMARY exchange places maker orders (POST_ONLY for rebates), HEDGE exchange places taker orders.

Usage:
    python hedge_mode.py --primary grvt --hedge backpack --ticker ETH --size 0.01 --iter 10
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
import csv
from decimal import Decimal
from datetime import datetime
from typing import Optional

import pytz
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        fillTimeout: int = 5,  # Restored from original template default (hedge_mode_ext.py)
        iterations: int = 20,
        sleepTime: int = 0,
        maxPosition: Decimal = Decimal('0'),
        useTaker: bool = False  # Strategy B: Use taker (market) orders for PRIMARY
    ):
        self.primaryExchangeName = primaryExchange.lower()
        self.hedgeExchangeName = hedgeExchange.lower()
        self.ticker = ticker.upper()
        self.orderQuantity = orderQuantity
        self.fillTimeout = fillTimeout
        self.iterations = iterations
        self.sleepTime = sleepTime
        self.maxPosition = maxPosition if maxPosition > 0 else orderQuantity
        self.useTaker = useTaker  # Store taker strategy flag

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

        # WebSocket order update tracking
        self.orderFilledEvent = asyncio.Event()
        self.lastOrderUpdate = None

        # Position tracking for open/close logic
        self.currentPosition = Decimal('0')  # Net position (+ for long, - for short)
        self.positionOpen = False  # Whether we have an open position

        # Take Profit order tracking (Phase B)
        self.tpOrderId = None  # TP order ID on PRIMARY
        self.tpPrice = Decimal('0')  # TP price
        self.tpDirection = None  # TP direction ('sell' for BUY entry, 'buy' for SELL entry)
        self.entryPrice = Decimal('0')  # Entry price for TP calculation
        self.openDirection = None  # Original open direction for close cycle
        self.currentOrderId = None  # Track current order ID for WebSocket updates

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

    async def get_bbo(self, client, contractId: str) -> tuple:
        """Helper function to get BBO with WebSocket fallback support.
        
        Args:
            client: Exchange client instance (PRIMARY or HEDGE)
            contractId: Contract ID to fetch BBO for
            
        Returns:
            Tuple of (best_bid, best_ask) as Decimal values
            
        Implementation:
            - First checks if client has WebSocket BBO cache (extended_best_bid/ask)
            - If WebSocket BBO available and valid, returns cached values
            - Otherwise falls back to REST API fetch_bbo_prices()
        """
        # Task 2: Check WebSocket BBO cache first
        if hasattr(client, 'extended_best_bid') and client.extended_best_bid is not None:
            # WebSocket BBO available
            return (client.extended_best_bid, client.extended_best_ask)
        else:
            # Task 1: Fallback to REST API
            return await client.fetch_bbo_prices(contractId)

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
            'close_order_side': 'sell',  # Default, will be updated based on strategy
        })
        hedgeConfig = Config({
            'ticker': self.ticker,
            'quantity': self.orderQuantity,
            'contract_id': '',  # Placeholder, will be set by get_contract_attributes()
            'tick_size': Decimal('0.01'),  # Default, will be updated
            'close_order_side': 'sell',  # Default, will be updated based on strategy
        })

        # Define local WebSocket order update handler (following template pattern)
        # NOT async, NOT a class method - this is critical for callback to work
        def order_update_handler(order_data):
            """Handle order updates from WebSocket.

            This is a local function (not async, not class method) following the template pattern
            used in hedge_mode_bp.py, hedge_mode_grvt.py, etc.
            """
            try:
                print(f"[DEBUG] order_update_handler CALLED! Data: {order_data}")  # Debug print
                order_id = order_data.get('order_id')
                status = order_data.get('status')
                filled_size = order_data.get('filled_size', '0')

                # DIAGNOSTIC Step 0.1: Verify Event Detection
                print(f"[DEBUG] Handler called for order {order_id}, status={status}")
                print(f"[DEBUG] orderFilledEvent before set: {self.orderFilledEvent.is_set()}")
                print(f"[DEBUG] Current order ID: {getattr(self, 'currentOrderId', 'NOT SET')}")

                # DIAGNOSTIC Step 0.2: Verify Order ID Matching
                if hasattr(self, 'currentOrderId') and order_id != self.currentOrderId:
                    print(f"[WARNING] Received update for different order! Expected {self.currentOrderId}, got {order_id}")
                    self.logger.warning(f"[WebSocket] Ignoring update for order {order_id} (expecting {self.currentOrderId})")
                    return  # Ignore updates for other orders

                self.logger.info(f"[WebSocket] Order {order_id}: {status}, filled={filled_size}")
                self.lastOrderUpdate = order_data

                if status in ['FILLED', 'PARTIALLY_FILLED']:
                    self.orderFilledEvent.set()
                    # DIAGNOSTIC Step 0.1 continued: Verify set() was called
                    print(f"[DEBUG] orderFilledEvent.set() CALLED!")
                    print(f"[DEBUG] orderFilledEvent after set: {self.orderFilledEvent.is_set()}")
            except Exception as e:
                self.logger.error(f"Error handling order update: {e}")
                import traceback
                print(f"[DEBUG] Handler error traceback: {traceback.format_exc()}")

        try:
            # Create PRIMARY client
            self.logger.info(f"[CONN] Creating PRIMARY client: {self.primaryExchangeName}")
            self.primaryClient = ExchangeFactory.create_exchange(self.primaryExchangeName, primaryConfig)

            # Get contract_id FIRST (following template: hedge_mode_bp.py line 1047)
            self.primaryContractId, self.primaryTickSize = await self.primaryClient.get_contract_attributes()
            self.logger.info(f"[OK] PRIMARY ({self.primaryExchangeName}) contract info: contract={self.primaryContractId}, tick={self.primaryTickSize}")

            # Update config with real contract_id (critical for WebSocket subscription)
            self.primaryClient.config.contract_id = self.primaryContractId

            # Setup WebSocket order update handler AFTER contract_id is set
            if hasattr(self.primaryClient, 'setup_order_update_handler'):
                self.primaryClient.setup_order_update_handler(order_update_handler)
                self.logger.info(f"[{self.primaryExchangeName}] WebSocket order handler registered")

            # Connect to PRIMARY client (WebSocket subscription will use real contract_id)
            await self.primaryClient.connect()
            self.logger.info(f"[OK] PRIMARY ({self.primaryExchangeName}) connected")

            # Create HEDGE client
            self.logger.info(f"[CONN] Creating HEDGE client: {self.hedgeExchangeName}")
            self.hedgeClient = ExchangeFactory.create_exchange(self.hedgeExchangeName, hedgeConfig)

            # Get contract_id FIRST (following template: hedge_mode_bp.py line 1047)
            self.hedgeContractId, self.hedgeTickSize = await self.hedgeClient.get_contract_attributes()
            self.logger.info(f"[OK] HEDGE ({self.hedgeExchangeName}) contract info: contract={self.hedgeContractId}, tick={self.hedgeTickSize}")

            # Update config with real contract_id (critical for WebSocket subscription)
            self.hedgeClient.config.contract_id = self.hedgeContractId

            # Setup WebSocket order update handler AFTER contract_id is set
            if hasattr(self.hedgeClient, 'setup_order_update_handler'):
                self.hedgeClient.setup_order_update_handler(order_update_handler)
                self.logger.info(f"[{self.hedgeExchangeName}] WebSocket order handler registered")

            # Connect to HEDGE client (WebSocket subscription will use real contract_id)
            await self.hedgeClient.connect()
            self.logger.info(f"[OK] HEDGE ({self.hedgeExchangeName}) connected")

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

    async def executeOpenCycle(self, direction: str) -> bool:
        """Execute open position cycle.

        Args:
            direction: 'buy' or 'sell' for PRIMARY side

        Returns:
            True if cycle completed successfully
        """
        self.orderCounter += 1
        self.fillRateStats['attempts'] += 1
        oppositeDirection = 'sell' if direction == 'buy' else 'buy'

        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"[OPEN CYCLE {self.orderCounter}] PRIMARY {direction.upper()} -> HEDGE {oppositeDirection.upper()}")

        try:
            # Step 1: Get BBO from PRIMARY
            self.logger.info(f"[BBO] Fetching from PRIMARY ({self.primaryExchangeName})...")
            bboPrices = await self.primaryClient.fetch_bbo_prices(self.primaryContractId)
            if not bboPrices:
                self.logger.warning("[WARN] Failed to get BBO prices from PRIMARY")
                return False

            bestBid, bestAsk = bboPrices
            self.logger.info(f"[BBO] PRIMARY: Bid={bestBid}, Ask={bestAsk}")

            # Step 2-3: Place order on PRIMARY (Maker or Taker based on strategy)
            filledSize = Decimal('0')
            orderFilled = False
            executionPrice = None

            if self.useTaker:
                # Strategy B: Taker (Market Order) - Immediate fill
                self.logger.info(f"[ORDER] Placing {direction.upper()} TAKER (market) on PRIMARY")
                primaryResult = await self.primaryClient.place_market_order(
                    self.primaryContractId,
                    self.orderQuantity,
                    direction
                )

                if not primaryResult.success:
                    self.logger.warning(f"[WARN] PRIMARY taker order failed: {primaryResult.error_message}")
                    return False

                # Market orders fill immediately
                orderFilled = True
                filledSize = self.orderQuantity
                executionPrice = primaryResult.price if primaryResult.price else 'market'
                self.logger.info(f"[OK] PRIMARY taker order FILLED immediately @ {executionPrice}")
                self.logTradeToCsv(
                    self.primaryExchangeName, 'PRIMARY_TAKER', direction,
                    str(executionPrice), str(filledSize), 'filled'
                )

            else:
                # Strategy A: Maker (POST_ONLY Order) - Wait for fill
                # NOTE: Actual price is determined by API (aggressive maker: ask-tick for BUY, bid+tick for SELL)
                self.logger.info(f"[ORDER] Placing {direction.upper()} MAKER (post-only) on PRIMARY")
                primaryResult = await self.primaryClient.place_open_order(
                    self.primaryContractId,
                    self.orderQuantity,
                    direction
                )

                if not primaryResult.success:
                    self.logger.warning(f"[WARN] PRIMARY maker order failed: {primaryResult.error_message}")
                    return False

                # Store order info (price is determined by API: ask-tick for BUY, bid+tick for SELL)
                self.currentOrderId = primaryResult.order_id
                makerPrice = primaryResult.price  # Get actual price from API
                self.logger.info(f"[OK] PRIMARY maker order placed: ID={primaryResult.order_id} @ {makerPrice}")
                self.logTradeToCsv(
                    self.primaryExchangeName, 'PRIMARY_MAKER', direction,
                    str(makerPrice), str(self.orderQuantity), 'placed'
                )

                # Active monitoring with cancel-and-replace (restored from original template)
                self.orderFilledEvent.clear()
                self.lastOrderUpdate = None
                startTime = time.time()
                lastCancelTime = 0

                while not self.stopFlag:
                    # Check if order filled via WebSocket
                    if self.lastOrderUpdate:
                        status = self.lastOrderUpdate.get('status', '')
                        if status in ['FILLED', 'filled', 'Filled']:
                            filledSize = Decimal(self.lastOrderUpdate.get('filled_size', '0'))
                            orderFilled = True
                            self.logger.info(f"[WebSocket] Fill detected: {filledSize} {self.ticker}")
                            break  # Exit loop, order filled
                        elif status in ['PARTIALLY_FILLED', 'partially_filled', 'PartiallyFilled']:
                            filledSize = Decimal(self.lastOrderUpdate.get('filled_size', '0'))
                            if filledSize > 0:
                                orderFilled = True
                                self.logger.info(f"[WebSocket] Partial fill: {filledSize}/{self.orderQuantity}")
                                break
                        elif status in ['CANCELED', 'CANCELLED', 'cancelled']:
                            # Order was cancelled, place new order and continue
                            self.logger.info(f"[ACTIVE] Order cancelled, placing new order at current BBO")
                            bboPrices = await self.get_bbo(self.primaryClient, self.primaryContractId)
                            bestBid, bestAsk = bboPrices
                            makerPrice = bestBid if direction == 'buy' else bestAsk

                            primaryResult = await self.primaryClient.place_open_order(
                                self.primaryContractId, self.orderQuantity, direction
                            )
                            self.currentOrderId = primaryResult.order_id
                            startTime = time.time()
                            lastCancelTime = 0
                            self.orderFilledEvent.clear()
                            self.lastOrderUpdate = None
                            continue
                        elif status in ['REJECTED', 'rejected']:
                            self.logger.info(f"[WebSocket] Order rejected")
                            return False
                        elif status in ['NEW', 'OPEN', 'PENDING', 'CANCELING', 'new', 'open', 'pending']:
                            # Normal waiting states - continue monitoring
                            pass  # No action, staleness check will handle if needed
                        else:
                            # Truly unknown status - log warning and continue waiting
                            self.logger.warning(f"[WebSocket] Unknown order status: {status}")
                            # Continue monitoring (no action taken)

                    # Active BBO monitoring for cancel-and-replace decision
                    currentTime = time.time()
                    elapsed = currentTime - startTime

                    # Timeout check (original template: 180s per order)
                    if elapsed > 180:
                        self.logger.error("[TIMEOUT] PRIMARY order timeout after 180s, cancelling...")
                        await self.primaryClient.cancel_order(primaryResult.order_id)
                        self.fillRateStats['timeout'] += 1
                        self.logTradeToCsv(
                            self.primaryExchangeName, 'PRIMARY_MAKER', direction,
                            str(makerPrice), str(self.orderQuantity), 'timeout'
                        )
                        return False

                    if elapsed > 10:  # After 10 seconds, check if order price is stale
                        # Fetch current BBO to check if our order is still competitive
                        bboPrices = await self.get_bbo(self.primaryClient, self.primaryContractId)
                        bestBid, bestAsk = bboPrices

                        shouldCancel = False
                        if direction == 'buy':
                            if makerPrice < bestBid:  # Our buy order is below best bid
                                shouldCancel = True
                        else:
                            if makerPrice > bestAsk:  # Our sell order is above best ask
                                shouldCancel = True

                        if shouldCancel and (currentTime - lastCancelTime > 5):  # Rate limiting: 5s between cancels
                            self.logger.info(f"[ACTIVE] Cancelling order due to stale price: {makerPrice} vs BBO {bestBid}/{bestAsk}")
                            await self.primaryClient.cancel_order(primaryResult.order_id)
                            lastCancelTime = currentTime
                            # Cancellation will trigger new order placement in next iteration

                    # Active monitoring with 180s timeout (original template pattern)
                    await asyncio.sleep(0.5)  # Check every 0.5s

                # Handle fill status for maker orders
                if not orderFilled or filledSize <= 0:
                    self.logger.info(f"[TIMEOUT] PRIMARY maker order not filled within {self.fillTimeout}s, cancelling...")
                    await self.primaryClient.cancel_order(primaryResult.order_id)
                    self.fillRateStats['timeout'] += 1
                    self.logTradeToCsv(
                        self.primaryExchangeName, 'PRIMARY_MAKER', direction,
                        str(makerPrice), str(self.orderQuantity), 'cancelled'
                    )
                    return False

                executionPrice = makerPrice

            # Step 4: Validate fill (common for both strategies)
            if not orderFilled or filledSize <= 0:
                self.logger.error(f"[ERROR] PRIMARY order validation failed: orderFilled={orderFilled}, filledSize={filledSize}")
                return False

            # Update fill rate stats
            self.fillRateStats['filled'] += 1
            self.fillRateStats['total_volume'] += filledSize

            # Log fill (only if not already logged in taker branch above)
            if not self.useTaker:
                self.logTradeToCsv(
                    self.primaryExchangeName, 'PRIMARY_MAKER', direction,
                    str(executionPrice), str(filledSize), 'filled'
                )

            # Step 5: Place PASSIVE MAKER limit order on HEDGE for filled amount
            self.logger.info(f"[HEDGE] Placing {oppositeDirection.upper()} PASSIVE MAKER on HEDGE for {filledSize}")
            hedgeResult = await self.hedgeClient.place_open_order(
                self.hedgeContractId,
                filledSize,
                oppositeDirection
            )

            if not hedgeResult.success:
                self.logger.error(f"[FAIL] HEDGE passive maker order FAILED: {hedgeResult.error_message}")
                self.logger.error(f"[IMBALANCE] POSITION IMBALANCE: {filledSize} {direction} on PRIMARY not hedged!")
                self.positionImbalance += filledSize if direction == 'buy' else -filledSize
                self.logTradeToCsv(
                    self.hedgeExchangeName, 'HEDGE', oppositeDirection,
                    'N/A', str(filledSize), 'FAILED'
                )
                return False

            hedgeOrderId = hedgeResult.order_id
            hedgeMakerPrice = hedgeResult.price
            self.logger.info(f"[HEDGE] Passive maker order placed: ID={hedgeOrderId} @ {hedgeMakerPrice}")
            self.logTradeToCsv(
                self.hedgeExchangeName, 'HEDGE', oppositeDirection,
                str(hedgeMakerPrice), str(filledSize), 'placed'
            )

            # Wait for HEDGE order fill with 60s timeout
            hedgeStartTime = time.time()
            hedgeFilled = False
            hedgeFilledSize = Decimal('0')

            while not self.stopFlag:
                elapsed = time.time() - hedgeStartTime
                
                # 60 second timeout
                if elapsed > 60:
                    self.logger.error("[TIMEOUT] HEDGE passive maker order timeout after 60s, checking status...")
                    cancel_result = await self.hedgeClient.cancel_order(hedgeOrderId)
                    # If filled_size >= target, order was already filled (cancel_order returns filled qty on error)
                    if cancel_result.filled_size and cancel_result.filled_size >= filledSize:
                        self.logger.info(f"[HEDGE] Order was already FILLED (filled_size={cancel_result.filled_size})")
                        hedgeFilled = True
                        hedgeFilledSize = cancel_result.filled_size
                        break
                    else:
                        self.fillRateStats['timeout'] += 1
                        self.logTradeToCsv(
                            self.hedgeExchangeName, 'HEDGE', oppositeDirection,
                            str(hedgeMakerPrice), str(filledSize), 'timeout'
                        )
                        # Position imbalance - PRIMARY filled but HEDGE not
                        self.positionImbalance += filledSize if direction == 'buy' else -filledSize
                        return False
                
                # Check order status (polling)
                try:
                    orderInfo = await self.hedgeClient.get_order_info(hedgeOrderId)
                    self.logger.debug(f"[HEDGE] get_order_info result: {orderInfo}")
                    if orderInfo is None:
                        # Order not in open orders = already filled (get_open_order returns None for filled)
                        self.logger.info(f"[HEDGE] Order {hedgeOrderId} not in open orders - assuming FILLED")
                        hedgeFilled = True
                        hedgeFilledSize = filledSize
                        break
                    else:
                        status = orderInfo.status.upper() if orderInfo.status else ''
                        if status in ['FILLED', 'COMPLETE']:
                            hedgeFilled = True
                            hedgeFilledSize = orderInfo.filled_size if orderInfo.filled_size else filledSize
                            break
                        elif status in ['PARTIALLY_FILLED']:
                            if orderInfo.filled_size >= filledSize:
                                hedgeFilled = True
                                hedgeFilledSize = orderInfo.filled_size
                                break
                        elif status in ['CANCELED', 'CANCELLED', 'REJECTED', 'EXPIRED']:
                            self.logger.error(f"[HEDGE] Order was {status}")
                            self.positionImbalance += filledSize if direction == 'buy' else -filledSize
                            return False
                except Exception as e:
                    self.logger.warning(f"[HEDGE] Order status check error: {e}")
                
                await asyncio.sleep(0.5)

            if not hedgeFilled:
                self.logger.error("[ERROR] HEDGE order not filled")
                self.positionImbalance += filledSize if direction == 'buy' else -filledSize
                return False

            hedgePrice = hedgeMakerPrice
            self.logger.info(f"[OK] HEDGE order FILLED @ {hedgePrice}")
            self.logTradeToCsv(
                self.hedgeExchangeName, 'HEDGE', oppositeDirection,
                str(hedgePrice), str(hedgeFilledSize), 'filled'
            )

            # Step 6: Place Take Profit order on PRIMARY
            self.openDirection = direction  # Store for close cycle
            self.entryPrice = executionPrice
            self.tpDirection = 'sell' if direction == 'buy' else 'buy'
            
            # Calculate TP price: entry +/- 0.05%
            if direction == 'buy':
                self.tpPrice = self.entryPrice * Decimal('1.0005')  # 0.05% higher
            else:
                self.tpPrice = self.entryPrice * Decimal('0.9995')  # 0.05% lower
            self.tpPrice = self.primaryClient.round_to_tick(self.tpPrice)
            
            self.logger.info(f"[TP] Placing {self.tpDirection.upper()} TP order on PRIMARY @ {self.tpPrice}")
            try:
                tpResult = await self.primaryClient.place_post_only_order(
                    self.primaryContractId,
                    filledSize,
                    self.tpPrice,
                    self.tpDirection
                )
                if tpResult and tpResult.order_id:
                    self.tpOrderId = tpResult.order_id
                    self.logger.info(f"[TP] TP order placed: ID={self.tpOrderId} @ {self.tpPrice}")
                    self.logTradeToCsv(
                        self.primaryExchangeName, 'TP', self.tpDirection,
                        str(self.tpPrice), str(filledSize), 'placed'
                    )
                else:
                    self.logger.warning(f"[TP] Failed to place TP order: No order ID returned")
                    self.tpOrderId = None
            except Exception as e:
                self.logger.warning(f"[TP] Failed to place TP order: {e}")
                self.tpOrderId = None

            # Step 7: Update position tracking (OPEN position)
            if direction == 'buy':
                self.currentPosition += filledSize  # Long position
            else:
                self.currentPosition -= filledSize  # Short position

            self.positionOpen = True
            self.logger.info(f"[POSITION] OPEN complete: currentPosition={self.currentPosition}")

            self.logger.info(f"[DONE] Open cycle {self.orderCounter} COMPLETE")
            return True

        except Exception as e:
            self.logger.error(f"[ERROR] Open cycle error: {e}")
            return False

    async def executeCloseCycle(self, direction: str) -> bool:
        """Execute close position cycle - Wait for TP order to fill.

        Args:
            direction: Original open direction ('buy' or 'sell') - will close in opposite direction

        Returns:
            True if cycle completed successfully
        """
        self.orderCounter += 1
        self.fillRateStats['attempts'] += 1
        oppositeDirection = 'sell' if direction == 'buy' else 'buy'

        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"[CLOSE CYCLE {self.orderCounter}] Waiting for TP on PRIMARY -> HEDGE {direction.upper()}")

        try:
            # Validation: Check if we have a position to close
            if abs(self.currentPosition) < Decimal('0.001'):
                self.logger.error(f"[CLOSE] ERROR: No position to close! currentPosition={self.currentPosition}")
                return False

            closeSize = abs(self.currentPosition)
            filledSize = Decimal('0')
            orderFilled = False
            executionPrice = None

            # Phase B: Wait for TP order to fill on PRIMARY
            if self.tpOrderId:
                self.logger.info(f"[TP] Waiting for TP order {self.tpOrderId} @ {self.tpPrice} to fill...")
                self.currentOrderId = self.tpOrderId  # Track for WebSocket updates
                self.orderFilledEvent.clear()
                self.lastOrderUpdate = None
                startTime = time.time()

                while not self.stopFlag:
                    # Check if order filled via WebSocket
                    if self.lastOrderUpdate:
                        status = self.lastOrderUpdate.get('status', '')
                        if status in ['FILLED', 'filled', 'Filled']:
                            filledSize = Decimal(self.lastOrderUpdate.get('filled_size', '0'))
                            orderFilled = True
                            executionPrice = self.tpPrice
                            self.logger.info(f"[TP] TP order FILLED @ {self.tpPrice}: {filledSize} {self.ticker}")
                            self.logTradeToCsv(
                                self.primaryExchangeName, 'TP', self.tpDirection,
                                str(self.tpPrice), str(filledSize), 'filled'
                            )
                            break
                        elif status in ['PARTIALLY_FILLED', 'partially_filled', 'PartiallyFilled']:
                            filledSize = Decimal(self.lastOrderUpdate.get('filled_size', '0'))
                            if filledSize >= closeSize:
                                orderFilled = True
                                executionPrice = self.tpPrice
                                self.logger.info(f"[TP] TP order partially filled: {filledSize}/{closeSize}")
                                break
                        elif status in ['CANCELED', 'CANCELLED', 'cancelled', 'REJECTED', 'rejected']:
                            self.logger.warning(f"[TP] TP order was {status}")
                            break
                        elif status in ['NEW', 'OPEN', 'PENDING', 'new', 'open', 'pending']:
                            pass  # Normal waiting state
                        else:
                            self.logger.debug(f"[TP] Unknown TP order status: {status}")

                    # Timeout check - 60 seconds (Phase C will make this configurable)
                    currentTime = time.time()
                    elapsed = currentTime - startTime

                    if elapsed > 60:
                        self.logger.warning(f"[TP] TP order timeout after 60s, cancelling and executing market close...")
                        await self.primaryClient.cancel_order(self.tpOrderId)
                        self.tpOrderId = None
                        break

                    await asyncio.sleep(0.5)

                # If TP not filled, fall back to market close
                if not orderFilled:
                    self.logger.info(f"[FALLBACK] Executing market close on PRIMARY")
                    primaryResult = await self.primaryClient.place_market_order(
                        self.primaryContractId,
                        closeSize,
                        oppositeDirection
                    )

                    if not primaryResult.success:
                        self.logger.error(f"[FAIL] Market close failed: {primaryResult.error_message}")
                        return False

                    orderFilled = True
                    filledSize = closeSize
                    executionPrice = primaryResult.price if primaryResult.price else 'market'
                    self.logger.info(f"[OK] PRIMARY market close FILLED @ {executionPrice}")
                    self.logTradeToCsv(
                        self.primaryExchangeName, 'PRIMARY_MARKET', oppositeDirection,
                        str(executionPrice), str(filledSize), 'filled_close'
                    )
            else:
                # No TP order - shouldn't happen in Phase B, but fall back to market close
                self.logger.warning("[WARN] No TP order found, executing market close")
                primaryResult = await self.primaryClient.place_market_order(
                    self.primaryContractId,
                    closeSize,
                    oppositeDirection
                )

                if not primaryResult.success:
                    self.logger.error(f"[FAIL] Market close failed: {primaryResult.error_message}")
                    return False

                orderFilled = True
                filledSize = closeSize
                executionPrice = primaryResult.price if primaryResult.price else 'market'
                self.logger.info(f"[OK] PRIMARY market close FILLED @ {executionPrice}")
                self.logTradeToCsv(
                    self.primaryExchangeName, 'PRIMARY_MARKET', oppositeDirection,
                    str(executionPrice), str(filledSize), 'filled_close'
                )

            # Clear TP state
            self.tpOrderId = None
            self.tpPrice = Decimal('0')
            self.tpDirection = None

            # Step 4: Validate fill (common for both strategies)
            if not orderFilled or filledSize <= 0:
                self.logger.error(f"[ERROR] PRIMARY close order validation failed: orderFilled={orderFilled}, filledSize={filledSize}")
                return False

            # Update fill rate stats
            self.fillRateStats['filled'] += 1
            self.fillRateStats['total_volume'] += filledSize

            # Step 5: Place PASSIVE MAKER limit order on HEDGE for filled amount (SAME direction as original open)
            self.logger.info(f"[HEDGE] Placing {direction.upper()} PASSIVE MAKER CLOSE on HEDGE for {filledSize}")
            hedgeResult = await self.hedgeClient.place_open_order(
                self.hedgeContractId,
                filledSize,
                direction  # Same direction as original open
            )

            if not hedgeResult.success:
                self.logger.error(f"[FAIL] HEDGE close passive maker order FAILED: {hedgeResult.error_message}")
                self.logger.error(f"[IMBALANCE] POSITION IMBALANCE: {filledSize} close on PRIMARY not hedged!")
                self.positionImbalance += filledSize if oppositeDirection == 'buy' else -filledSize
                self.logTradeToCsv(
                    self.hedgeExchangeName, 'HEDGE', direction,
                    'N/A', str(filledSize), 'FAILED'
                )
                return False

            hedgeOrderId = hedgeResult.order_id
            hedgeMakerPrice = hedgeResult.price
            self.logger.info(f"[HEDGE] Passive maker close order placed: ID={hedgeOrderId} @ {hedgeMakerPrice}")
            self.logTradeToCsv(
                self.hedgeExchangeName, 'HEDGE', direction,
                str(hedgeMakerPrice), str(filledSize), 'placed_close'
            )

            # Wait for HEDGE order fill with 60s timeout
            hedgeStartTime = time.time()
            hedgeFilled = False
            hedgeFilledSize = Decimal('0')

            while not self.stopFlag:
                elapsed = time.time() - hedgeStartTime
                
                # 60 second timeout
                if elapsed > 60:
                    self.logger.error("[TIMEOUT] HEDGE close passive maker order timeout after 60s, checking status...")
                    cancel_result = await self.hedgeClient.cancel_order(hedgeOrderId)
                    # If filled_size >= target, order was already filled (cancel_order returns filled qty on error)
                    if cancel_result.filled_size and cancel_result.filled_size >= filledSize:
                        self.logger.info(f"[HEDGE] Close order was already FILLED (filled_size={cancel_result.filled_size})")
                        hedgeFilled = True
                        hedgeFilledSize = cancel_result.filled_size
                        break
                    else:
                        self.fillRateStats['timeout'] += 1
                        self.logTradeToCsv(
                            self.hedgeExchangeName, 'HEDGE', direction,
                            str(hedgeMakerPrice), str(filledSize), 'timeout_close'
                        )
                        # Position imbalance - PRIMARY closed but HEDGE not
                        self.positionImbalance += filledSize if oppositeDirection == 'buy' else -filledSize
                        return False
                
                # Check order status (polling)
                try:
                    orderInfo = await self.hedgeClient.get_order_info(hedgeOrderId)
                    self.logger.debug(f"[HEDGE] Close get_order_info result: {orderInfo}")
                    if orderInfo is None:
                        # Order not in open orders = already filled (get_open_order returns None for filled)
                        self.logger.info(f"[HEDGE] Close order {hedgeOrderId} not in open orders - assuming FILLED")
                        hedgeFilled = True
                        hedgeFilledSize = filledSize
                        break
                    else:
                        status = orderInfo.status.upper() if orderInfo.status else ''
                        if status in ['FILLED', 'COMPLETE']:
                            hedgeFilled = True
                            hedgeFilledSize = orderInfo.filled_size if orderInfo.filled_size else filledSize
                            break
                        elif status in ['PARTIALLY_FILLED']:
                            if orderInfo.filled_size >= filledSize:
                                hedgeFilled = True
                                hedgeFilledSize = orderInfo.filled_size
                                break
                        elif status in ['CANCELED', 'CANCELLED', 'REJECTED', 'EXPIRED']:
                            self.logger.error(f"[HEDGE] Close order was {status}")
                            self.positionImbalance += filledSize if oppositeDirection == 'buy' else -filledSize
                            return False
                except Exception as e:
                    self.logger.warning(f"[HEDGE] Close order status check error: {e}")
                
                await asyncio.sleep(0.5)

            if not hedgeFilled:
                self.logger.error("[ERROR] HEDGE close order not filled")
                self.positionImbalance += filledSize if oppositeDirection == 'buy' else -filledSize
                return False

            hedgePrice = hedgeMakerPrice
            self.logger.info(f"[OK] HEDGE close order FILLED @ {hedgePrice}")
            self.logTradeToCsv(
                self.hedgeExchangeName, 'HEDGE', direction,
                str(hedgePrice), str(hedgeFilledSize), 'filled_close'
            )

            # Step 6: Update position tracking (CLOSE position - reset to 0)
            self.currentPosition = Decimal('0')
            self.positionOpen = False
            self.logger.info(f"[POSITION] CLOSE complete: currentPosition={self.currentPosition}")

            self.logger.info(f"[DONE] Close cycle {self.orderCounter} COMPLETE")
            return True

        except Exception as e:
            self.logger.error(f"[ERROR] Close cycle error: {e}")
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
            # Step 1: Get BBO from PRIMARY
            self.logger.info(f"[BBO] Fetching from PRIMARY ({self.primaryExchangeName})...")
            bboPrices = await self.primaryClient.fetch_bbo_prices(self.primaryContractId)
            if not bboPrices:
                self.logger.warning("[WARN] Failed to get BBO prices from PRIMARY")
                return False

            bestBid, bestAsk = bboPrices
            self.logger.info(f"[BBO] PRIMARY: Bid={bestBid}, Ask={bestAsk}")

            # Step 2: Place POST_ONLY maker order on PRIMARY
            # NOTE: Actual price is determined by API (aggressive maker: ask-tick for BUY, bid+tick for SELL)
            self.logger.info(f"[ORDER] Placing {direction.upper()} maker on PRIMARY")
            primaryResult = await self.primaryClient.place_open_order(
                self.primaryContractId,
                self.orderQuantity,
                direction
            )

            if not primaryResult.success:
                self.logger.warning(f"[WARN] PRIMARY order failed: {primaryResult.error_message}")
                return False

            # DIAGNOSTIC Step 0.2: Store order info (price is determined by API)
            self.currentOrderId = primaryResult.order_id
            makerPrice = primaryResult.price  # Get actual price from API
            print(f"[DEBUG] Stored currentOrderId: {self.currentOrderId}, price: {makerPrice}")

            self.logger.info(f"[OK] PRIMARY order placed: ID={primaryResult.order_id} @ {makerPrice}")
            self.logTradeToCsv(
                self.primaryExchangeName, 'PRIMARY', direction,
                str(makerPrice), str(self.orderQuantity), 'placed'
            )

            # Step 3: Wait for fill with timeout (WebSocket event-driven)
            self.orderFilledEvent.clear()
            self.lastOrderUpdate = None
            filledSize = Decimal('0')
            orderFilled = False

            # DIAGNOSTIC Step 0.4: Log event state before wait
            print(f"[DEBUG] BEFORE wait: orderFilledEvent.is_set() = {self.orderFilledEvent.is_set()}")
            print(f"[DEBUG] Waiting for order {self.currentOrderId} fill (timeout={self.fillTimeout}s)...")

            try:
                # Phase 1.5 Step 1 Alternative: Simple wait with 15s timeout (isolated test)
                await asyncio.wait_for(
                    self.orderFilledEvent.wait(),
                    timeout=self.fillTimeout
                )

                # DIAGNOSTIC Step 0.4: Log event state after successful wait
                print(f"[DEBUG] AFTER wait: orderFilledEvent.is_set() = {self.orderFilledEvent.is_set()}")
                print(f"[DEBUG] Event detected! Proceeding with fill processing...")

                if self.lastOrderUpdate:
                    status = self.lastOrderUpdate.get('status', '')
                    filledSize = Decimal(self.lastOrderUpdate.get('filled_size', '0'))

                    if status in ['FILLED', 'filled', 'Filled']:
                        orderFilled = True
                        self.logger.info(f"[WebSocket] Fill detected: {filledSize} {self.ticker}")
                    elif status in ['PARTIALLY_FILLED', 'partially_filled', 'PartiallyFilled']:
                        if filledSize > 0:
                            orderFilled = True
                            self.logger.info(f"[WebSocket] Partial fill: {filledSize}/{self.orderQuantity}")
                    elif status in ['CANCELLED', 'cancelled', 'Cancelled', 'REJECTED', 'rejected']:
                        self.logger.info(f"[WebSocket] Order cancelled/rejected")
                        return False
                    else:
                        filledSize = Decimal('0')
                        orderFilled = False
                        self.logger.warning(f"[WebSocket] Event triggered but unexpected status: {status}")
                else:
                    filledSize = Decimal('0')
                    orderFilled = False
                    self.logger.warning("[WebSocket] Event triggered but no order update")

            except asyncio.TimeoutError:
                orderFilled = False
                filledSize = Decimal('0')
                # DIAGNOSTIC Step 0.4: Log event state on timeout
                print(f"[DEBUG] TIMEOUT! orderFilledEvent.is_set() = {self.orderFilledEvent.is_set()}")
                print(f"[DEBUG] lastOrderUpdate = {self.lastOrderUpdate}")
                self.logger.error(f"[TIMEOUT] Event never set! Final state: is_set={self.orderFilledEvent.is_set()}")
                self.logger.info(f"[WebSocket] Order {primaryResult.order_id} not filled within {self.fillTimeout}s")

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

                # Alternate between OPEN and CLOSE cycles based on position state
                if self.positionOpen:
                    # Close existing position
                    self.logger.info(f"[CYCLE {i+1}] Position is OPEN, executing CLOSE cycle")
                    success = await self.executeCloseCycle(direction)
                    if success:
                        successCount += 1
                        # Phase 2A: Alternate direction after each close
                        direction = 'sell' if direction == 'buy' else 'buy'
                    else:
                        failCount += 1
                        # Keep same direction to retry close on next iteration
                else:
                    # Open new position
                    # ============================================================
                    # Phase 2A: Simple Alternating Direction
                    # No spread prediction - just alternate BUY → SELL → BUY → SELL
                    # ============================================================
                    self.logger.info(f"[PHASE 2A ALTERNATING] Direction: {direction.upper()}")

                    self.logger.info(f"[CYCLE {i+1}] Position is CLOSED, executing OPEN cycle with {direction.upper()}")
                    success = await self.executeOpenCycle(direction)
                    if success:
                        successCount += 1
                        # Keep same direction for close
                    else:
                        failCount += 1
                        # Keep same direction to retry open on next iteration

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

            # Position consistency validation
            self.logger.info(f"\n[POSITION TRACKING]")
            self.logger.info(f"   Current Position: {self.currentPosition} {self.ticker}")
            self.logger.info(f"   Position Open: {self.positionOpen}")

            if abs(self.currentPosition) > Decimal('0.001'):
                self.logger.error(f"[WARNING] Unclosed position detected! currentPosition={self.currentPosition}")
                self.logger.error(f"[WARNING] This indicates incomplete Open/Close cycle.")
            elif self.currentPosition == Decimal('0'):
                self.logger.info(f"[OK] Position fully closed (currentPosition=0)")

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

    async def adjustPriceIfNeeded(self, orderId: str, direction: str, originalPrice: Decimal, tickSize: Decimal, elapsed: float) -> bool:
        """Adjust order price to be more aggressive if not filled within threshold.

        Args:
            orderId: Order ID to modify
            direction: 'buy' or 'sell'
            originalPrice: Original order price
            tickSize: Minimum price increment
            elapsed: Time elapsed since order placement (seconds)

        Returns:
            True if order was modified successfully, False otherwise
        """
        if elapsed < 1.5:
            return False  # Too early to adjust

        # Calculate new aggressive price (1 tick beyond original)
        if direction == 'buy':
            newPrice = originalPrice + tickSize  # More aggressive for buy
        else:
            newPrice = originalPrice - tickSize  # More aggressive for sell

        try:
            self.logger.info(f"[PRICE ADJUST] {direction.upper()} {originalPrice} → {newPrice} after {elapsed:.1f}s")
            await self.primaryClient.modify_order(orderId, newPrice, self.orderQuantity)
            return True
        except Exception as e:
            self.logger.warning(f"[PRICE ADJUST] Failed to modify order: {e}")
            return False

    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("[CLEANUP] Cleaning up...")

        # Auto-close any unclosed position before disconnection (DN logic: one side profit + one side loss = net zero)
        if abs(self.currentPosition) > 0:
            self.logger.warning(f"[AUTO-CLOSE] Unclosed position detected: {self.currentPosition}, forcing cleanup close...")

            try:
                # Determine close direction (opposite of current position)
                closeDirection = 'sell' if self.currentPosition > 0 else 'buy'
                closeSize = abs(self.currentPosition)

                self.logger.info(f"[AUTO-CLOSE] Closing position: direction={closeDirection}, size={closeSize}")

                # Close on PRIMARY (market taker for immediate execution)
                if self.primaryClient:
                    primaryResult = await self.primaryClient.place_market_order(
                        self.primaryContractId,
                        closeSize,
                        closeDirection
                    )
                    if primaryResult.success:
                        primaryPrice = primaryResult.price if primaryResult.price else 'market'
                        self.logger.info(f"[AUTO-CLOSE] PRIMARY close filled @ {primaryPrice}")
                        self.logTradeToCsv(
                            self.primaryExchangeName, 'PRIMARY_TAKER', closeDirection,
                            str(primaryPrice), str(closeSize), 'auto_close'
                        )
                    else:
                        self.logger.error(f"[AUTO-CLOSE] PRIMARY close FAILED: {primaryResult.error_message}")

                # Close on HEDGE (market order, same direction as open)
                hedgeDirection = 'sell' if closeDirection == 'buy' else 'buy'
                if self.hedgeClient:
                    hedgeResult = await self.hedgeClient.place_market_order(
                        self.hedgeContractId,
                        closeSize,
                        hedgeDirection
                    )
                    if hedgeResult.success:
                        hedgePrice = hedgeResult.price if hedgeResult.price else 'market'
                        self.logger.info(f"[AUTO-CLOSE] HEDGE close filled @ {hedgePrice}")
                        self.logTradeToCsv(
                            self.hedgeExchangeName, 'HEDGE', hedgeDirection,
                            str(hedgePrice), str(closeSize), 'auto_close'
                        )
                    else:
                        self.logger.error(f"[AUTO-CLOSE] HEDGE close FAILED: {hedgeResult.error_message}")

                # Update position tracking
                self.currentPosition = Decimal('0')
                self.positionOpen = False
                self.logger.info(f"[AUTO-CLOSE] Position cleanup complete: currentPosition={self.currentPosition}")

            except Exception as e:
                self.logger.error(f"[AUTO-CLOSE] Error during position cleanup: {e}")
                self.logger.error(f"[MANUAL] Manual intervention required: unclosed position={self.currentPosition}")

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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='2DEX Hedge Mode - Dynamic Dual Exchange Hedge Bot')
    parser.add_argument('--primary', type=str, required=True,
                        help='PRIMARY exchange (e.g., grvt, backpack, apex)')
    parser.add_argument('--hedge', type=str, required=True,
                        help='HEDGE exchange (e.g., grvt, backpack, apex)')
    parser.add_argument('--ticker', type=str, default='ETH',
                        help='Ticker symbol (default: ETH)')
    parser.add_argument('--size', type=str, required=True,
                        help='Order quantity (e.g., 0.01)')
    parser.add_argument('--iter', type=int, required=True,
                        help='Number of iterations to run')
    parser.add_argument('--fill-timeout', type=int, default=5,
                        help='Timeout in seconds for maker order fills (default: 5s, restored from original template)')
    parser.add_argument('--sleep', type=int, default=0,
                        help='Sleep time in seconds between cycles (default: 0)')
    parser.add_argument('--use-taker', action='store_true',
                        help='Use taker (market) orders for PRIMARY instead of maker (post-only) orders - Strategy B test')

    return parser.parse_args()


async def main():
    """Main entry point for the bot."""
    args = parse_arguments()

    # Create bot instance
    bot = HedgeBot2DEX(
        primaryExchange=args.primary,
        hedgeExchange=args.hedge,
        ticker=args.ticker,
        orderQuantity=Decimal(args.size),
        fillTimeout=args.fill_timeout,
        iterations=args.iter,
        sleepTime=args.sleep,
        useTaker=args.use_taker  # Strategy B: Taker mode
    )

    # Run the bot
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
