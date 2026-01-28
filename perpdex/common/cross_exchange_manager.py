"""
Cross-Exchange Order Manager for Avellaneda Market Making

Coordinates trading between Apex Pro and Paradex to:
- Maximize volume for farming rewards
- Capture spreads while maintaining 0% loss target
- Optimize for Paradex rebates (-0.005%)
- Manage inventory across both exchanges

Based on backtesting showing +0.20% return with 693 trades/day.
"""

import os
import time
import asyncio
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
from dotenv import load_dotenv

# Import both exchange clients
from apex.avellaneda_client import AvellanedaApexClient, AvellanedaParameters
from paradex.avellaneda_client import AvellanedaParadexClient, AvellanedaParadexParams


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class ExchangeRole(Enum):
    """Exchange role in cross-DEX strategy"""
    BID_MAKER = "bid_maker"  # Places bid orders
    ASK_MAKER = "ask_maker"  # Places ask orders
    BALANCED = "balanced"    # Places both sides


@dataclass
class CrossExchangeOrder:
    """Cross-exchange order tracking"""
    apex_order_id: Optional[str] = None
    paradex_order_id: Optional[str] = None
    side: Optional[OrderSide] = None
    price: float = 0.0
    size: float = 0.0
    timestamp: float = field(default_factory=time.time)
    apex_status: str = "PENDING"
    paradex_status: str = "PENDING"

    @property
    def is_filled(self) -> bool:
        """Check if any side is filled"""
        return self.apex_status == "FILLED" or self.paradex_status == "FILLED"

    @property
    def both_filled(self) -> bool:
        """Check if both sides filled"""
        return self.apex_status == "FILLED" and self.paradex_status == "FILLED"


@dataclass
class InventoryBalance:
    """Cross-exchange inventory tracking"""
    apex_position: float = 0.0
    paradex_position: float = 0.0
    apex_notional: float = 0.0
    paradex_notional: float = 0.0
    total_position: float = 0.0
    total_notional: float = 0.0
    imbalance_ratio: float = 0.0

    def update(self, apex_pos: float, paradex_pos: float, current_price: float):
        """Update inventory balances"""
        self.apex_position = apex_pos
        self.paradex_position = paradex_pos
        self.apex_notional = apex_pos * current_price
        self.paradex_notional = paradex_pos * current_price
        self.total_position = apex_pos + paradex_pos
        self.total_notional = self.apex_notional + self.paradex_notional

        # Calculate imbalance ratio
        total_abs = abs(apex_pos) + abs(paradex_pos)
        if total_abs > 0:
            self.imbalance_ratio = abs(apex_pos - paradex_pos) / total_abs
        else:
            self.imbalance_ratio = 0.0

    @property
    def needs_rebalancing(self) -> bool:
        """Check if inventory needs rebalancing"""
        return self.imbalance_ratio > 0.6  # 60/40 threshold


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    total_trades: int = 0
    apex_trades: int = 0
    paradex_trades: int = 0
    total_volume: float = 0.0
    apex_volume: float = 0.0
    paradex_volume: float = 0.0
    total_fees: float = 0.0
    apex_fees: float = 0.0
    paradex_rebates: float = 0.0
    net_pnl: float = 0.0
    spread_captured: float = 0.0
    win_rate: float = 0.0
    trades_per_hour: float = 0.0
    start_time: float = field(default_factory=time.time)

    def add_trade(self, exchange: str, size: float, price: float, fee: float):
        """Record a completed trade"""
        self.total_trades += 1
        volume = size * price

        if exchange == "APEX":
            self.apex_trades += 1
            self.apex_volume += volume
            self.apex_fees += fee
        else:  # PARADEX
            self.paradex_trades += 1
            self.paradex_volume += volume
            self.paradex_rebates += abs(fee)  # Negative fee = rebate

        self.total_volume += volume
        self.total_fees += fee

        # Calculate trades per hour
        elapsed_hours = (time.time() - self.start_time) / 3600
        if elapsed_hours > 0:
            self.trades_per_hour = self.total_trades / elapsed_hours


class CrossExchangeAvellanedaManager:
    """
    Main cross-exchange order manager for Avellaneda MM

    Coordinates Apex and Paradex for optimal volume farming
    """

    def __init__(
        self,
        environment: str = 'testnet',
        symbol_apex: str = 'BTC-USDT',
        market_paradex: str = 'BTC-USD-PERP',
        initial_capital: float = 5000.0,
        position_limit: float = 1000.0,
        order_size: float = 100.0
    ):
        """
        Initialize cross-exchange manager

        Args:
            environment: 'testnet' or 'mainnet'
            symbol_apex: Apex trading pair
            market_paradex: Paradex market
            initial_capital: Starting capital in USD
            position_limit: Max position per exchange
            order_size: Default order size in USD
        """
        load_dotenv()

        self.environment = environment
        self.symbol_apex = symbol_apex
        self.market_paradex = market_paradex
        self.initial_capital = initial_capital
        self.position_limit = position_limit
        self.order_size = order_size

        # Avellaneda parameters (from winning backtest)
        apex_params = AvellanedaParameters(
            gamma=0.1,
            sigma=0.02,
            position_limit=position_limit,
            min_spread=0.0001,
            max_spread=0.005
        )

        paradex_params = AvellanedaParadexParams(
            gamma=0.1,
            sigma=0.02,
            position_limit=position_limit,
            min_spread=0.0001,
            max_spread=0.005,
            rebate_optimization=True  # KEY: Optimize for rebates
        )

        # Initialize exchange clients
        print("[INIT] Creating Apex client...")
        self.apex_client = AvellanedaApexClient(
            environment=environment,
            symbol=symbol_apex,
            params=apex_params
        )

        print("[INIT] Creating Paradex client...")
        self.paradex_client = AvellanedaParadexClient(
            environment=environment,
            market=market_paradex,
            params=paradex_params
        )

        # Cross-exchange state
        self.inventory = InventoryBalance()
        self.active_orders: List[CrossExchangeOrder] = []
        self.completed_orders: List[CrossExchangeOrder] = []
        self.metrics = PerformanceMetrics()

        # Exchange roles (can be dynamic)
        self.apex_role = ExchangeRole.BALANCED
        self.paradex_role = ExchangeRole.BALANCED

        # Timing
        self.last_order_time = 0
        self.last_rebalance_time = 0
        self.strategy_start_time = time.time()

        # Control flags
        self.is_running = False
        self.stop_requested = False

    # ========== Price Aggregation ==========

    def get_aggregated_mid_price(self) -> float:
        """
        Get volume-weighted mid price across exchanges

        Returns:
            Aggregated mid price
        """
        apex_book = self.apex_client.order_book
        paradex_book = self.paradex_client.order_book

        if not apex_book or not paradex_book:
            # Fallback to last prices
            if self.apex_client.last_price and self.paradex_client.last_price:
                return (self.apex_client.last_price + self.paradex_client.last_price) / 2
            return 0.0

        # Volume-weighted average
        apex_mid = apex_book.mid_price
        paradex_mid = paradex_book.mid_price

        # Get volumes at best bid/ask
        apex_vol = apex_book.best_bid[1] + apex_book.best_ask[1]
        paradex_vol = paradex_book.best_bid[1] + paradex_book.best_ask[1]

        total_vol = apex_vol + paradex_vol
        if total_vol > 0:
            return (apex_mid * apex_vol + paradex_mid * paradex_vol) / total_vol

        return (apex_mid + paradex_mid) / 2

    def detect_price_divergence(self) -> float:
        """
        Detect price divergence between exchanges

        Returns:
            Price divergence percentage
        """
        apex_price = self.apex_client.last_price
        paradex_price = self.paradex_client.last_price

        if not apex_price or not paradex_price:
            return 0.0

        divergence = abs(apex_price - paradex_price) / min(apex_price, paradex_price)
        return divergence

    # ========== Cross-Exchange Order Placement ==========

    def place_cross_exchange_orders(self) -> CrossExchangeOrder:
        """
        Place coordinated orders on both exchanges

        Strategy:
        - Apex: Standard maker orders
        - Paradex: Tighter spreads for rebate optimization
        - Avoid crossing own orders

        Returns:
            Cross-exchange order object
        """
        # Get aggregated price
        mid_price = self.get_aggregated_mid_price()
        if not mid_price:
            print("[ERROR] No price data available")
            return None

        # Calculate optimal spreads for each exchange
        apex_bid_spread, apex_ask_spread = self.apex_client.calculate_optimal_spread()
        paradex_bid_spread, paradex_ask_spread = self.paradex_client.calculate_optimal_spread_with_rebate()

        # Check inventory for role assignment
        if self.inventory.needs_rebalancing:
            # Assign roles to rebalance
            if self.inventory.apex_position > self.inventory.paradex_position:
                # Apex has too much, make it sell more
                self.apex_role = ExchangeRole.ASK_MAKER
                self.paradex_role = ExchangeRole.BID_MAKER
            else:
                # Paradex has too much
                self.apex_role = ExchangeRole.BID_MAKER
                self.paradex_role = ExchangeRole.ASK_MAKER
        else:
            # Balanced operation
            self.apex_role = ExchangeRole.BALANCED
            self.paradex_role = ExchangeRole.BALANCED

        # Create cross-exchange order
        cross_order = CrossExchangeOrder()

        # Calculate order size in BTC
        btc_size = self.order_size / mid_price

        # Place orders based on roles
        print(f"\n[CROSS-EXCHANGE] Placing orders...")
        print(f"  Mid price: ${mid_price:.2f}")
        print(f"  Apex role: {self.apex_role.value}")
        print(f"  Paradex role: {self.paradex_role.value}")

        # APEX ORDERS
        if self.apex_role in [ExchangeRole.BID_MAKER, ExchangeRole.BALANCED]:
            # Place bid on Apex
            bid_price = mid_price * (1 - apex_bid_spread)
            try:
                apex_bid = self.apex_client._place_limit_order(
                    side='BUY',
                    price=bid_price,
                    size=btc_size,
                    post_only=True
                )
                if apex_bid:
                    cross_order.apex_order_id = apex_bid.get('id')
                    print(f"  [APEX BID] ${bid_price:.2f} (spread: {apex_bid_spread*100:.3f}%)")
            except Exception as e:
                print(f"  [APEX ERROR] Bid failed: {e}")

        if self.apex_role in [ExchangeRole.ASK_MAKER, ExchangeRole.BALANCED]:
            # Place ask on Apex
            ask_price = mid_price * (1 + apex_ask_spread)
            try:
                apex_ask = self.apex_client._place_limit_order(
                    side='SELL',
                    price=ask_price,
                    size=btc_size,
                    post_only=True
                )
                if apex_ask:
                    if not cross_order.apex_order_id:
                        cross_order.apex_order_id = apex_ask.get('id')
                    print(f"  [APEX ASK] ${ask_price:.2f} (spread: {apex_ask_spread*100:.3f}%)")
            except Exception as e:
                print(f"  [APEX ERROR] Ask failed: {e}")

        # PARADEX ORDERS (Rebate optimized)
        if self.paradex_role in [ExchangeRole.BID_MAKER, ExchangeRole.BALANCED]:
            # Place bid on Paradex
            bid_price = mid_price * (1 - paradex_bid_spread)
            try:
                paradex_bid = self.paradex_client.client.create_order(
                    market=self.market_paradex,
                    side='BUY',
                    order_type='LIMIT',
                    size=str(btc_size),
                    price=str(bid_price),
                    post_only=True  # CRITICAL for rebate
                )
                if paradex_bid:
                    cross_order.paradex_order_id = paradex_bid.get('order_id')
                    print(f"  [PARADEX BID] ${bid_price:.2f} (spread: {paradex_bid_spread*100:.3f}%) +REBATE")
            except Exception as e:
                print(f"  [PARADEX ERROR] Bid failed: {e}")

        if self.paradex_role in [ExchangeRole.ASK_MAKER, ExchangeRole.BALANCED]:
            # Place ask on Paradex
            ask_price = mid_price * (1 + paradex_ask_spread)
            try:
                paradex_ask = self.paradex_client.client.create_order(
                    market=self.market_paradex,
                    side='SELL',
                    order_type='LIMIT',
                    size=str(btc_size),
                    price=str(ask_price),
                    post_only=True  # CRITICAL for rebate
                )
                if paradex_ask:
                    if not cross_order.paradex_order_id:
                        cross_order.paradex_order_id = paradex_ask.get('order_id')
                    print(f"  [PARADEX ASK] ${ask_price:.2f} (spread: {paradex_ask_spread*100:.3f}%) +REBATE")
            except Exception as e:
                print(f"  [PARADEX ERROR] Ask failed: {e}")

        # Track the cross-exchange order
        if cross_order.apex_order_id or cross_order.paradex_order_id:
            cross_order.price = mid_price
            cross_order.size = btc_size
            self.active_orders.append(cross_order)
            return cross_order

        return None

    def cancel_all_orders(self):
        """Cancel all orders on both exchanges"""
        print("\n[CANCEL] Cancelling all orders...")

        apex_cancelled = self.apex_client.cancel_all_orders()
        paradex_cancelled = self.paradex_client.cancel_all_orders()

        print(f"  Apex: {apex_cancelled} orders cancelled")
        print(f"  Paradex: {paradex_cancelled} orders cancelled")

        # Clear active orders
        self.active_orders.clear()

    # ========== Inventory Management ==========

    def update_inventory(self):
        """Update inventory across both exchanges"""
        # Update individual exchange inventories
        self.apex_client.update_inventory()
        self.paradex_client.update_inventory()

        # Get current price
        current_price = self.get_aggregated_mid_price()

        # Update cross-exchange inventory
        self.inventory.update(
            self.apex_client.inventory_balance,
            self.paradex_client.inventory_balance,
            current_price
        )

        print(f"\n[INVENTORY UPDATE]")
        print(f"  Apex: {self.inventory.apex_position:.4f} BTC (${self.inventory.apex_notional:.2f})")
        print(f"  Paradex: {self.inventory.paradex_position:.4f} BTC (${self.inventory.paradex_notional:.2f})")
        print(f"  Total: {self.inventory.total_position:.4f} BTC (${self.inventory.total_notional:.2f})")
        print(f"  Imbalance: {self.inventory.imbalance_ratio:.2%}")

    def should_rebalance(self) -> bool:
        """
        Check if cross-exchange rebalancing is needed

        Returns:
            True if rebalancing required
        """
        # Check inventory imbalance
        if self.inventory.needs_rebalancing:
            return True

        # Check position limits
        if abs(self.inventory.apex_position) > self.position_limit * 0.9:
            return True
        if abs(self.inventory.paradex_position) > self.position_limit * 0.9:
            return True

        # Check end-of-day liquidation
        elapsed = time.time() - self.strategy_start_time
        if elapsed > 86400 * 0.95:  # 95% of day complete
            return abs(self.inventory.total_position) > self.position_limit * 0.1

        return False

    # ========== Main Strategy Loop ==========

    async def run_strategy(self, duration: int = 3600):
        """
        Run the cross-exchange Avellaneda MM strategy

        Args:
            duration: Run duration in seconds (default 1 hour)
        """
        print(f"\n{'='*60}")
        print(f"CROSS-EXCHANGE AVELLANEDA MM STRATEGY")
        print(f"{'='*60}")
        print(f"Environment: {self.environment}")
        print(f"Apex: {self.symbol_apex}")
        print(f"Paradex: {self.market_paradex}")
        print(f"Position Limit: ${self.position_limit}")
        print(f"Order Size: ${self.order_size}")
        print(f"{'='*60}\n")

        self.is_running = True
        self.strategy_start_time = time.time()

        # Connect WebSockets
        print("[INIT] Connecting to exchanges...")
        apex_connected = self.apex_client.connect_websocket()
        paradex_connected = self.paradex_client.connect_websocket()

        if not apex_connected or not paradex_connected:
            print("[ERROR] Failed to connect to one or both exchanges")
            return

        # Wait for initial market data
        await asyncio.sleep(3)

        # Main loop
        order_interval = 30  # Place orders every 30 seconds
        start_time = time.time()

        while time.time() - start_time < duration and not self.stop_requested:
            try:
                # Update inventories
                self.update_inventory()

                # Check for price divergence
                divergence = self.detect_price_divergence()
                if divergence > 0.001:  # 0.1% divergence
                    print(f"[ARBITRAGE] Price divergence detected: {divergence:.3%}")

                # Check rebalancing
                if self.should_rebalance():
                    print("\n[REBALANCE] Inventory rebalancing needed")
                    self.cancel_all_orders()
                    # Rebalancing logic would go here
                    await asyncio.sleep(5)
                    continue

                # Place orders periodically
                if time.time() - self.last_order_time > order_interval:
                    # Cancel old orders
                    self.cancel_all_orders()

                    # Place new cross-exchange orders
                    cross_order = self.place_cross_exchange_orders()

                    self.last_order_time = time.time()

                    # Update metrics
                    self._update_metrics()
                    self._log_metrics()

                await asyncio.sleep(5)

            except Exception as e:
                print(f"\n[ERROR] Strategy loop error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(10)

        # Cleanup
        print(f"\n{'='*60}")
        print("STRATEGY COMPLETED")
        print(f"{'='*60}")

        self.cancel_all_orders()
        self._print_final_metrics()

        self.is_running = False

    def _update_metrics(self):
        """Update performance metrics"""
        # This would track actual fills and calculate metrics
        # For now, using placeholder logic
        elapsed_hours = (time.time() - self.strategy_start_time) / 3600
        if elapsed_hours > 0:
            self.metrics.trades_per_hour = self.metrics.total_trades / elapsed_hours

    def _log_metrics(self):
        """Log current metrics"""
        print(f"\n[METRICS UPDATE]")
        print(f"  Total trades: {self.metrics.total_trades}")
        print(f"  Apex: {self.metrics.apex_trades} trades, ${self.metrics.apex_volume:.2f} volume")
        print(f"  Paradex: {self.metrics.paradex_trades} trades, ${self.metrics.paradex_volume:.2f} volume")
        print(f"  Apex fees: ${self.metrics.apex_fees:.2f}")
        print(f"  Paradex rebates: ${self.metrics.paradex_rebates:.2f}")
        print(f"  Net fees: ${self.metrics.total_fees:.2f}")
        print(f"  Trades/hour: {self.metrics.trades_per_hour:.1f}")

    def _print_final_metrics(self):
        """Print final performance metrics"""
        print(f"\n[FINAL METRICS]")
        print(f"  Duration: {(time.time() - self.strategy_start_time)/3600:.2f} hours")
        print(f"  Total trades: {self.metrics.total_trades}")
        print(f"  Total volume: ${self.metrics.total_volume:,.2f}")
        print(f"  Apex volume: ${self.metrics.apex_volume:,.2f}")
        print(f"  Paradex volume: ${self.metrics.paradex_volume:,.2f}")
        print(f"  Apex fees paid: ${self.metrics.apex_fees:.2f}")
        print(f"  Paradex rebates earned: ${self.metrics.paradex_rebates:.2f}")
        print(f"  Net fees: ${self.metrics.total_fees:.2f}")
        print(f"  Trades per hour: {self.metrics.trades_per_hour:.1f}")

        # Calculate daily projections
        if self.metrics.trades_per_hour > 0:
            daily_trades = self.metrics.trades_per_hour * 24
            daily_volume = (self.metrics.total_volume / self.metrics.total_trades) * daily_trades
            print(f"\n[DAILY PROJECTIONS]")
            print(f"  Trades/day: {daily_trades:.0f}")
            print(f"  Volume/day: ${daily_volume:,.0f}")
            print(f"  Monthly volume: ${daily_volume * 30:,.0f}")

    def stop_strategy(self):
        """Request strategy stop"""
        print("\n[STOP] Stop requested...")
        self.stop_requested = True


def main():
    """Example usage of cross-exchange manager"""
    import sys

    # Parse command line arguments
    environment = 'testnet'
    duration = 60  # 1 minute test

    if len(sys.argv) > 1:
        environment = sys.argv[1]
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])

    # Create manager
    manager = CrossExchangeAvellanedaManager(
        environment=environment,
        initial_capital=5000.0,
        position_limit=1000.0,
        order_size=100.0
    )

    # Run strategy
    try:
        asyncio.run(manager.run_strategy(duration=duration))
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Shutting down...")
        manager.stop_strategy()


if __name__ == "__main__":
    main()