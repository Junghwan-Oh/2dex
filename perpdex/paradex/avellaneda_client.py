"""
Avellaneda Market Making Client for Paradex

Optimized for maker rebates (-0.005% fee) and cross-DEX coordination
with Apex Pro for volume farming strategy.

Based on backtest showing +0.20% return with proper fee modeling.
"""

import os
import json
import time
import asyncio
import websocket
import threading
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue
import numpy as np
from dotenv import load_dotenv

# Use existing ParadexClient as base
from paradex.lib.paradex_client import ParadexClient


@dataclass
class ParadexOrderBookSnapshot:
    """Paradex order book snapshot"""
    timestamp: float
    bids: List[Tuple[float, float]]  # [(price, size), ...]
    asks: List[Tuple[float, float]]
    symbol: str

    @property
    def best_bid(self) -> Tuple[float, float]:
        """Get best bid price and size"""
        return self.bids[0] if self.bids else (0, 0)

    @property
    def best_ask(self) -> Tuple[float, float]:
        """Get best ask price and size"""
        return self.asks[0] if self.asks else (0, 0)

    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        if self.bids and self.asks:
            return (self.bids[0][0] + self.asks[0][0]) / 2
        return 0


@dataclass
class ParadexPosition:
    """Paradex position tracking"""
    market: str
    side: str  # 'LONG' or 'SHORT'
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    funding_accumulated: float = 0.0

    @property
    def notional_value(self) -> float:
        """Position notional value"""
        return self.size * self.mark_price

    @property
    def is_profitable(self) -> bool:
        """Check if position is profitable"""
        return self.unrealized_pnl > 0


@dataclass
class AvellanedaParadexParams:
    """Paradex-specific Avellaneda parameters"""
    gamma: float = 0.1  # Risk aversion
    sigma: float = 0.02  # Volatility estimate
    k: float = 1.5  # Liquidity parameter
    eta: float = 1.0  # Order arrival intensity
    T: int = 86400  # Trading day length
    position_limit: float = 1000.0  # Max position
    min_spread: float = 0.0001  # Min spread (0.01%)
    max_spread: float = 0.005  # Max spread (0.5%)
    # Paradex specific
    rebate_optimization: bool = True  # Optimize for rebates
    maker_rebate: float = -0.00005  # -0.005% rebate
    taker_fee: float = 0.0003  # 0.03% fee (NEVER USE)


class AvellanedaParadexClient:
    """
    Paradex client optimized for Avellaneda MM with rebate focus

    Key Features:
    - ALWAYS use post_only orders for maker rebate
    - WebSocket real-time feeds
    - Cross-DEX coordination with Apex
    - Inventory risk management
    - Funding rate optimization
    """

    def __init__(
        self,
        environment: str = 'testnet',
        market: str = 'BTC-USD-PERP',
        params: Optional[AvellanedaParadexParams] = None,
        l1_address: Optional[str] = None,
        l1_private_key: Optional[str] = None
    ):
        """
        Initialize Paradex Avellaneda client

        Args:
            environment: 'testnet' or 'mainnet'
            market: Trading market (default BTC-USD-PERP)
            params: Avellaneda parameters
            l1_address: Ethereum L1 address
            l1_private_key: Ethereum L1 private key
        """
        # Base client for REST API
        self.client = ParadexClient(
            environment=environment,
            l1_address=l1_address,
            l1_private_key=l1_private_key
        )

        self.environment = environment
        self.market = market
        self.params = params or AvellanedaParadexParams()

        # WebSocket management
        self.ws = None
        self.ws_thread = None
        self.ws_connected = False
        self.ws_url = self._get_ws_url()

        # Market data
        self.order_book = None
        self.last_price = 0.0
        self.mark_price = 0.0
        self.index_price = 0.0
        self.price_history = []
        self.funding_rate = 0.0

        # Position tracking
        self.current_position = None
        self.inventory_balance = 0.0

        # Order management (maker only)
        self.open_orders = {}
        self.filled_orders = []
        self.total_rebates = 0.0

        # Timing
        self.day_start_time = time.time()
        self.last_order_time = 0
        self.last_funding_time = 0

        # Callbacks
        self.on_price_update = None
        self.on_order_filled = None
        self.on_rebate_earned = None

    def _get_ws_url(self) -> str:
        """Get WebSocket URL for environment"""
        if self.environment == 'testnet':
            return 'wss://ws.testnet.paradex.trade/v1'
        else:
            return 'wss://ws.paradex.trade/v1'

    # ========== WebSocket Management ==========

    def connect_websocket(self):
        """Connect to Paradex WebSocket"""
        def on_message(ws, message):
            self._handle_ws_message(json.loads(message))

        def on_error(ws, error):
            print(f"[PARADEX WS ERROR] {error}")
            self.ws_connected = False

        def on_close(ws, close_status_code, close_msg):
            print(f"[PARADEX WS CLOSED] Code: {close_status_code}")
            self.ws_connected = False

        def on_open(ws):
            print("[PARADEX WS CONNECTED] Subscribing to channels...")
            self.ws_connected = True
            # Subscribe to market data
            self._subscribe_market_data()
            # Subscribe to order updates
            self._subscribe_orders()
            # Subscribe to funding rates
            self._subscribe_funding()

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        # Run in separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

        # Wait for connection
        for i in range(10):
            if self.ws_connected:
                print("[PARADEX] WebSocket connected successfully")
                return True
            time.sleep(0.5)

        print("[PARADEX] WebSocket connection timeout")
        return False

    def _subscribe_market_data(self):
        """Subscribe to order book and trades"""
        # Order book subscription
        sub_msg = {
            "type": "subscribe",
            "channel": "orderbook",
            "market": self.market,
            "depth": 10
        }
        self.ws.send(json.dumps(sub_msg))

        # Trades subscription
        sub_msg = {
            "type": "subscribe",
            "channel": "trades",
            "market": self.market
        }
        self.ws.send(json.dumps(sub_msg))

    def _subscribe_orders(self):
        """Subscribe to order updates (requires auth)"""
        # This requires authentication with signature
        # Implementation depends on Paradex WebSocket auth flow
        pass

    def _subscribe_funding(self):
        """Subscribe to funding rate updates"""
        sub_msg = {
            "type": "subscribe",
            "channel": "funding",
            "market": self.market
        }
        self.ws.send(json.dumps(sub_msg))

    def _handle_ws_message(self, message: Dict):
        """Handle incoming WebSocket messages"""
        msg_type = message.get('type')
        channel = message.get('channel')

        if channel == 'orderbook':
            self._update_orderbook(message.get('data'))
        elif channel == 'trades':
            self._update_price(message.get('data'))
        elif channel == 'funding':
            self._update_funding(message.get('data'))
        elif channel == 'orders':
            self._handle_order_update(message.get('data'))

    def _update_orderbook(self, data: Dict):
        """Update order book from WebSocket"""
        if not data:
            return

        self.order_book = ParadexOrderBookSnapshot(
            timestamp=time.time(),
            bids=[(float(b['price']), float(b['size'])) for b in data.get('bids', [])],
            asks=[(float(a['price']), float(a['size'])) for a in data.get('asks', [])],
            symbol=self.market
        )

    def _update_price(self, data: Dict):
        """Update prices from trade data"""
        if not data:
            return

        self.last_price = float(data.get('price', 0))
        self.mark_price = float(data.get('mark_price', self.last_price))
        self.index_price = float(data.get('index_price', self.last_price))

        self.price_history.append({
            'price': self.last_price,
            'timestamp': time.time()
        })

        # Keep last 1000 prices
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-1000:]

        if self.on_price_update:
            self.on_price_update(self.last_price)

    def _update_funding(self, data: Dict):
        """Update funding rate"""
        if not data:
            return

        self.funding_rate = float(data.get('funding_rate', 0))
        self.last_funding_time = time.time()

    def _handle_order_update(self, data: Dict):
        """Handle order fills and rebates"""
        if not data:
            return

        order_id = data.get('order_id')
        status = data.get('status')

        if status == 'FILLED':
            # Calculate rebate earned
            size = float(data.get('size', 0))
            price = float(data.get('price', 0))
            is_maker = data.get('is_maker', True)

            if is_maker:
                # Earned rebate!
                rebate = size * price * abs(self.params.maker_rebate)
                self.total_rebates += rebate

                print(f"[REBATE] Earned ${rebate:.4f} on order {order_id}")

                if self.on_rebate_earned:
                    self.on_rebate_earned(rebate)

            # Track filled order
            self.filled_orders.append(data)

            if self.on_order_filled:
                self.on_order_filled(data)

    # ========== Avellaneda MM Logic ==========

    def calculate_volatility(self, lookback: int = 100) -> float:
        """
        Calculate realized volatility

        Args:
            lookback: Number of periods

        Returns:
            Volatility estimate
        """
        if len(self.price_history) < lookback + 1:
            return self.params.sigma

        prices = [p['price'] for p in self.price_history[-lookback:]]
        returns = np.diff(np.log(prices))

        if len(returns) == 0:
            return self.params.sigma

        # Annualized volatility
        std = np.std(returns)
        periods_per_day = 1440
        annualized_vol = std * np.sqrt(periods_per_day * 365)

        return 0.7 * annualized_vol + 0.3 * self.params.sigma

    def calculate_optimal_spread_with_rebate(self) -> Tuple[float, float]:
        """
        Calculate spreads optimized for Paradex rebates

        Key: Tighter spreads on Paradex to capture more rebates

        Returns:
            (bid_spread, ask_spread) as percentages
        """
        # Time remaining
        elapsed_time = time.time() - self.day_start_time
        time_remaining = max(0, 1 - (elapsed_time / self.params.T))

        # Volatility
        volatility = self.calculate_volatility()

        # Base Avellaneda spread
        base_spread = (
            self.params.gamma * volatility * volatility * time_remaining +
            (2 / self.params.gamma) * np.log(1 + self.params.gamma / self.params.k)
        )

        # REBATE OPTIMIZATION: Tighter spreads for more fills
        if self.params.rebate_optimization:
            # Reduce spread to increase fill probability
            rebate_adjustment = 0.7  # 30% tighter spreads
            base_spread *= rebate_adjustment

        # Inventory skew
        position_skew = abs(self.inventory_balance) / self.params.position_limit if self.params.position_limit > 0 else 0

        if self.inventory_balance > 0:  # Long
            bid_spread = base_spread * (1 + position_skew)
            ask_spread = base_spread * (1 - position_skew * 0.5)
        elif self.inventory_balance < 0:  # Short
            bid_spread = base_spread * (1 - position_skew * 0.5)
            ask_spread = base_spread * (1 + position_skew)
        else:  # Neutral
            bid_spread = base_spread
            ask_spread = base_spread

        # Apply constraints
        bid_spread = max(self.params.min_spread, min(self.params.max_spread, bid_spread))
        ask_spread = max(self.params.min_spread, min(self.params.max_spread, ask_spread))

        return bid_spread, ask_spread

    # ========== Order Management (MAKER ONLY) ==========

    def place_rebate_optimized_orders(self, size: float = 0.01) -> Dict:
        """
        Place maker orders optimized for Paradex rebates

        CRITICAL:
        - ALWAYS use post_only=True for maker rebate
        - NEVER use market orders (0.03% taker fee)
        - Tighter spreads for higher fill rate

        Args:
            size: Order size in BTC

        Returns:
            Order placement results
        """
        if not self.order_book or not self.last_price:
            print("[PARADEX] No market data available")
            return {}

        # Calculate rebate-optimized spreads
        bid_spread, ask_spread = self.calculate_optimal_spread_with_rebate()

        # Calculate prices
        mid_price = self.order_book.mid_price
        bid_price = mid_price * (1 - bid_spread)
        ask_price = mid_price * (1 + ask_spread)

        # Ensure maker orders (not crossing spread)
        best_bid, _ = self.order_book.best_bid
        best_ask, _ = self.order_book.best_ask

        # Place just inside best bid/ask for priority
        bid_price = min(bid_price, best_bid - 0.01)
        ask_price = max(ask_price, best_ask + 0.01)

        results = {}

        # Place BUY limit order (maker)
        try:
            bid_order = self.client.create_order(
                market=self.market,
                side='BUY',
                order_type='LIMIT',
                size=str(size),
                price=str(bid_price),
                post_only=True,  # CRITICAL: Ensures maker rebate
                reduce_only=False,
                client_order_id=f"av_bid_{int(time.time()*1000)}"
            )

            if bid_order:
                self.open_orders[bid_order.get('order_id')] = bid_order
                results['bid_order'] = bid_order
                print(f"[PARADEX BID] Placed at ${bid_price:.2f} "
                      f"(spread: {bid_spread*100:.3f}%) - EARNING REBATE")

        except Exception as e:
            print(f"[PARADEX ERROR] Failed to place bid: {e}")

        # Place SELL limit order (maker)
        try:
            ask_order = self.client.create_order(
                market=self.market,
                side='SELL',
                order_type='LIMIT',
                size=str(size),
                price=str(ask_price),
                post_only=True,  # CRITICAL: Ensures maker rebate
                reduce_only=False,
                client_order_id=f"av_ask_{int(time.time()*1000)}"
            )

            if ask_order:
                self.open_orders[ask_order.get('order_id')] = ask_order
                results['ask_order'] = ask_order
                print(f"[PARADEX ASK] Placed at ${ask_price:.2f} "
                      f"(spread: {ask_spread*100:.3f}%) - EARNING REBATE")

        except Exception as e:
            print(f"[PARADEX ERROR] Failed to place ask: {e}")

        return results

    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders

        Returns:
            Number of orders cancelled
        """
        count = 0
        for order_id in list(self.open_orders.keys()):
            try:
                result = self.client.cancel_order(order_id)
                if result:
                    self.open_orders.pop(order_id, None)
                    count += 1
            except Exception as e:
                print(f"[PARADEX ERROR] Failed to cancel {order_id}: {e}")

        print(f"[PARADEX] Cancelled {count} orders")
        return count

    # ========== Position & Inventory Management ==========

    def update_inventory(self):
        """Update inventory from actual positions"""
        positions = self.client.get_active_positions()

        self.inventory_balance = 0.0
        for pos in positions:
            if pos.get('market') == self.market:
                size = float(pos.get('size', 0))
                side = pos.get('side')

                if side == 'LONG':
                    self.inventory_balance += size
                else:  # SHORT
                    self.inventory_balance -= size

                self.current_position = ParadexPosition(
                    market=self.market,
                    side=side,
                    size=size,
                    entry_price=float(pos.get('entry_price', 0)),
                    mark_price=float(pos.get('mark_price', 0)),
                    unrealized_pnl=float(pos.get('unrealized_pnl', 0))
                )

        print(f"[PARADEX INVENTORY] Net: {self.inventory_balance:.4f} BTC")

    def check_funding_impact(self) -> float:
        """
        Check funding rate impact on position

        Returns:
            Expected funding payment (negative = pay, positive = receive)
        """
        if not self.current_position:
            return 0.0

        # Funding payments every 8 hours
        funding_payment = (
            self.current_position.size *
            self.current_position.mark_price *
            self.funding_rate
        )

        if self.current_position.side == 'SHORT':
            funding_payment = -funding_payment

        return funding_payment

    # ========== Main Trading Loop ==========

    async def run_rebate_strategy(self, duration: int = 3600):
        """
        Run Paradex rebate-optimized Avellaneda MM

        Args:
            duration: Run duration in seconds
        """
        print(f"\n[PARADEX START] Rebate-Optimized Avellaneda MM")
        print(f"Market: {self.market}")
        print(f"Maker Rebate: {self.params.maker_rebate*100:.3f}%")

        # Connect WebSocket
        if not self.connect_websocket():
            print("[PARADEX ERROR] Failed to connect WebSocket")
            return

        # Wait for market data
        await asyncio.sleep(2)

        start_time = time.time()
        order_interval = 30  # Place orders every 30 seconds

        while time.time() - start_time < duration:
            try:
                # Update inventory
                self.update_inventory()

                # Check position limits
                if abs(self.inventory_balance) > self.params.position_limit:
                    print("[PARADEX] Position limit reached, rebalancing...")
                    self.cancel_all_orders()
                    # Would implement rebalancing logic here
                    await asyncio.sleep(10)
                    continue

                # Check funding impact
                funding_impact = self.check_funding_impact()
                if abs(funding_impact) > 10:  # More than $10 impact
                    print(f"[PARADEX FUNDING] Impact: ${funding_impact:.2f}")

                # Replace orders periodically
                if time.time() - self.last_order_time > order_interval:
                    # Cancel old orders
                    self.cancel_all_orders()

                    # Place new rebate-optimized orders
                    orders = self.place_rebate_optimized_orders(size=0.01)

                    self.last_order_time = time.time()

                    # Log metrics
                    volatility = self.calculate_volatility()
                    bid_spread, ask_spread = self.calculate_optimal_spread_with_rebate()

                    print(f"\n[PARADEX METRICS]")
                    print(f"  Volatility: {volatility:.3f}")
                    print(f"  Bid spread: {bid_spread*100:.3f}%")
                    print(f"  Ask spread: {ask_spread*100:.3f}%")
                    print(f"  Total rebates: ${self.total_rebates:.2f}")
                    print(f"  Filled orders: {len(self.filled_orders)}")

                await asyncio.sleep(5)

            except Exception as e:
                print(f"[PARADEX ERROR] Strategy loop: {e}")
                await asyncio.sleep(10)

        print(f"\n[PARADEX END] Strategy completed")
        print(f"Total rebates earned: ${self.total_rebates:.2f}")
        print(f"Total orders filled: {len(self.filled_orders)}")

        # Cleanup
        self.cancel_all_orders()
        if self.ws:
            self.ws.close()

    def get_performance_metrics(self) -> Dict:
        """
        Get current performance metrics

        Returns:
            Metrics dictionary
        """
        account = self.client.get_account_summary()

        return {
            'total_equity': account.get('total_equity', 0),
            'unrealized_pnl': account.get('unrealized_pnl', 0),
            'available_balance': account.get('available_balance', 0),
            'inventory_balance': self.inventory_balance,
            'open_orders': len(self.open_orders),
            'filled_orders': len(self.filled_orders),
            'total_rebates': self.total_rebates,
            'funding_rate': self.funding_rate,
            'current_volatility': self.calculate_volatility()
        }


def main():
    """Example usage of Paradex Avellaneda client"""
    load_dotenv()

    # Initialize parameters
    params = AvellanedaParadexParams(
        gamma=0.1,
        sigma=0.02,
        position_limit=1000.0,
        min_spread=0.0001,
        max_spread=0.005,
        rebate_optimization=True  # KEY: Optimize for rebates
    )

    # Create client
    client = AvellanedaParadexClient(
        environment='testnet',
        market='BTC-USD-PERP',
        params=params
    )

    # Show initial status
    print("\n[PARADEX] Initial Account Status:")
    metrics = client.get_performance_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Run strategy
    print("\n[PARADEX] Starting Rebate-Optimized Strategy...")
    asyncio.run(client.run_rebate_strategy(duration=60))

    # Final status
    print("\n[PARADEX] Final Account Status:")
    metrics = client.get_performance_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()