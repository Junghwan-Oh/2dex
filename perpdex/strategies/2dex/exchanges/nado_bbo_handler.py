"""
Nado BBO (Best Bid Offer) Handler

Processes real-time BBO stream data from Nado WebSocket.
Provides spread monitoring, momentum detection, and fair value calculation.
"""

import asyncio
import logging
from collections import deque
from decimal import Decimal
from statistics import mean
from typing import Dict, Optional, Tuple, List

from .nado_websocket_client import NadoWebSocketClient


class BBOData:
    """Container for BBO data."""

    def __init__(
        self,
        product_id: int,
        bid_price: Decimal,
        bid_qty: Decimal,
        ask_price: Decimal,
        ask_qty: Decimal,
        timestamp: int
    ):
        self.product_id = product_id
        self.bid_price = bid_price
        self.bid_qty = bid_qty
        self.ask_price = ask_price
        self.ask_qty = ask_qty
        self.timestamp = timestamp

    @property
    def spread(self) -> Decimal:
        """Calculate spread in absolute terms."""
        return self.ask_price - self.bid_price

    @property
    def spread_bps(self) -> Decimal:
        """Calculate spread in basis points."""
        mid_price = (self.bid_price + self.ask_price) / 2
        if mid_price == 0:
            return Decimal(0)
        return self.spread / mid_price * 10000

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.bid_price + self.ask_price) / 2


class SpreadMonitor:
    """Monitor spread changes for market making decisions."""

    def __init__(self, window_size: int = 100):
        """
        Initialize spread monitor.

        Args:
            window_size: Number of recent spreads to track
        """
        self.window_size = window_size
        self.spread_history: deque = deque(maxlen=window_size)

    def on_bbo(self, bbo: BBOData) -> str:
        """
        Process BBO update and return spread state.

        Returns:
            Spread state: "WIDENING", "NARROWING", or "STABLE"
        """
        spread_pct = bbo.spread / bbo.bid_price if bbo.bid_price > 0 else Decimal(0)
        self.spread_history.append(spread_pct)

        if len(self.spread_history) < 10:
            return "STABLE"

        # Calculate average spread
        avg_spread = mean(self.spread_history)

        # Detect spread changes
        if spread_pct > avg_spread * Decimal('1.5'):
            return "WIDENING"  # Volatility increasing
        elif spread_pct < avg_spread * Decimal('0.5'):
            return "NARROWING"  # Market stabilizing
        else:
            return "STABLE"

    def get_avg_spread_bps(self) -> Optional[Decimal]:
        """Get average spread in basis points."""
        if not self.spread_history:
            return None
        return Decimal(str(mean(self.spread_history))) * 10000


class MomentumDetector:
    """Detect price momentum from BBO stream."""

    def __init__(self, window_size: int = 20):
        """
        Initialize momentum detector.

        Args:
            window_size: Number of price points to analyze
        """
        self.window_size = window_size
        self.bid_history: deque = deque(maxlen=window_size)
        self.ask_history: deque = deque(maxlen=window_size)

    def on_bbo(self, bbo: BBOData) -> str:
        """
        Process BBO update and return momentum state.

        Returns:
            Momentum state: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        self.bid_history.append((bbo.timestamp, bbo.bid_price))
        self.ask_history.append((bbo.timestamp, bbo.ask_price))

        if len(self.bid_history) < 5:
            return "NEUTRAL"

        # Calculate price trend
        recent_bids = [price for _, price in list(self.bid_history)[-5:]]
        recent_asks = [price for _, price in list(self.ask_history)[-5:]]

        bid_slope = (recent_bids[-1] - recent_bids[0]) / recent_bids[0] if recent_bids[0] > 0 else Decimal(0)
        ask_slope = (recent_asks[-1] - recent_asks[0]) / recent_asks[0] if recent_asks[0] > 0 else Decimal(0)

        # Detect momentum
        threshold = Decimal('0.001')  # 0.1% change threshold

        if bid_slope > threshold and ask_slope > threshold:
            return "BULLISH"  # Both rising
        elif bid_slope < -threshold and ask_slope < -threshold:
            return "BEARISH"  # Both falling
        else:
            return "NEUTRAL"


class BBOHandler:
    """
    Handle Best Bid Offer stream data.

    Processes real-time BBO updates and provides:
    - Latest prices
    - Spread monitoring
    - Momentum detection
    - Fair value calculation
    """

    def __init__(
        self,
        product_id: int,
        ws_client: NadoWebSocketClient,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize BBO handler.

        Args:
            product_id: Product ID (4 for ETH, 8 for SOL)
            ws_client: WebSocket client instance
            logger: Optional logger instance
        """
        self.product_id = product_id
        self.ws_client = ws_client
        self.logger = logger or logging.getLogger(__name__)

        # Latest BBO data
        self._latest_bbo: Optional[BBOData] = None

        # Analyzers
        self.spread_monitor = SpreadMonitor()
        self.momentum_detector = MomentumDetector()

        # Callbacks
        self._callbacks: List = []

    async def start(self) -> None:
        """Start subscribing to BBO stream."""
        await self.ws_client.subscribe(
            "best_bid_offer",
            self.product_id,
            self._on_bbo_message
        )
        self.logger.info(f"BBO handler started for product_id={self.product_id}")

    async def _on_bbo_message(self, message: Dict) -> None:
        """
        Process BBO message from WebSocket.

        Args:
            message: Raw message from WebSocket
        """
        try:
            # Parse BBO data
            bbo = BBOData(
                product_id=message.get("product_id", self.product_id),
                bid_price=Decimal(message["bid_price"]) / Decimal(1e18),
                bid_qty=Decimal(message["bid_qty"]) / Decimal(1e18),
                ask_price=Decimal(message["ask_price"]) / Decimal(1e18),
                ask_qty=Decimal(message["ask_qty"]) / Decimal(1e18),
                timestamp=int(message.get("timestamp", 0))
            )

            # Update latest BBO
            self._latest_bbo = bbo

            # Run analyzers
            spread_state = self.spread_monitor.on_bbo(bbo)
            momentum = self.momentum_detector.on_bbo(bbo)

            # Log significant changes
            if spread_state != "STABLE":
                self.logger.info(
                    f"BBO Spread {spread_state}: "
                    f"{bbo.bid_price:.2f} - {bbo.ask_price:.2f} "
                    f"({bbo.spread_bps:.1f} bps)"
                )

            if momentum != "NEUTRAL":
                self.logger.info(
                    f"BBO Momentum {momentum}: "
                    f"{bbo.mid_price:.2f}"
                )

            # Call registered callbacks
            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(bbo, spread_state, momentum)
                    else:
                        callback(bbo, spread_state, momentum)
                except Exception as e:
                    self.logger.error(f"Error in BBO callback: {e}")

        except (KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse BBO message: {e}")

    def get_latest_bbo(self) -> Optional[BBOData]:
        """Get the latest BBO data."""
        return self._latest_bbo

    def get_prices(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get current bid and ask prices.

        Returns:
            Tuple of (bid_price, ask_price) or (None, None) if no data
        """
        if self._latest_bbo is None:
            return None, None
        return self._latest_bbo.bid_price, self._latest_bbo.ask_price

    def get_spread(self) -> Optional[Decimal]:
        """Get current spread in price units."""
        if self._latest_bbo is None:
            return None
        return self._latest_bbo.spread

    def get_fair_value(self) -> Optional[Decimal]:
        """Get fair value (mid price)."""
        if self._latest_bbo is None:
            return None
        return self._latest_bbo.mid_price

    def get_spread_state(self) -> str:
        """Get current spread state."""
        if self._latest_bbo is None:
            return "STABLE"
        return self.spread_monitor.on_bbo(self._latest_bbo)

    def get_momentum(self) -> str:
        """Get current momentum state."""
        if self._latest_bbo is None:
            return "NEUTRAL"
        return self.momentum_detector.on_bbo(self._latest_bbo)

    def register_callback(self, callback) -> None:
        """
        Register callback for BBO updates.

        Args:
            callback: Function that receives (bbo, spread_state, momentum)
        """
        self._callbacks.append(callback)
