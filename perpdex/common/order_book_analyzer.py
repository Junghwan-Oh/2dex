"""
Order Book Liquidity Analyzer

Borrowed concept from Hummingbot's Avellaneda market making strategy.
Dynamically calculates alpha (arrival rate) and kappa (liquidity) parameters
from order book and trade history.

Reference:
- Hummingbot: https://github.com/hummingbot/hummingbot/blob/master/hummingbot/strategy/avellaneda_market_making/
- Strategy guide: https://hummingbot.org/strategies/avellaneda-market-making/
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from collections import deque


class OrderBookAnalyzer:
    """
    Analyzes order book to estimate dynamic market parameters

    Key parameters:
    - alpha: Order arrival intensity (how often orders arrive)
    - kappa: Order book depth coefficient (liquidity measure)
    """

    def __init__(
        self,
        window_size: int = 100,  # Number of ticks to analyze
        depth_levels: int = 10,  # Order book levels to consider
        min_samples: int = 20  # Minimum samples before estimation
    ):
        """
        Initialize Order Book Analyzer

        Args:
            window_size: Number of recent ticks to analyze
            depth_levels: How many order book levels to consider
            min_samples: Minimum data points before estimation
        """
        self.window_size = window_size
        self.depth_levels = depth_levels
        self.min_samples = min_samples

        # Historical data storage
        self.trade_history: deque = deque(maxlen=window_size)
        self.depth_history: deque = deque(maxlen=window_size)

        # Cached parameters
        self.cached_alpha: Optional[float] = None
        self.cached_kappa: Optional[float] = None
        self.last_update_time: Optional[float] = None

    def update_trade_data(
        self,
        timestamp: float,
        price: float,
        volume: float,
        side: str
    ) -> None:
        """
        Update with new trade data

        Args:
            timestamp: Trade timestamp (unix seconds)
            price: Trade price
            volume: Trade volume
            side: 'BUY' or 'SELL'
        """
        self.trade_history.append({
            'timestamp': timestamp,
            'price': price,
            'volume': volume,
            'side': side
        })

    def update_order_book_data(
        self,
        timestamp: float,
        bids: List[Tuple[float, float]],  # [(price, size), ...]
        asks: List[Tuple[float, float]]   # [(price, size), ...]
    ) -> None:
        """
        Update with new order book snapshot

        Args:
            timestamp: Snapshot timestamp
            bids: List of (price, size) tuples for bids
            asks: List of (price, size) tuples for asks
        """
        # Calculate total depth within depth_levels
        bid_depth = sum(size for _, size in bids[:self.depth_levels])
        ask_depth = sum(size for _, size in asks[:self.depth_levels])
        avg_depth = (bid_depth + ask_depth) / 2

        # Calculate mid price
        if bids and asks:
            mid_price = (bids[0][0] + asks[0][0]) / 2
        else:
            mid_price = None

        self.depth_history.append({
            'timestamp': timestamp,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'avg_depth': avg_depth,
            'mid_price': mid_price
        })

    def estimate_arrival_rate(self) -> float:
        """
        Estimate alpha (order arrival intensity)

        Based on trade frequency analysis.
        Higher alpha = more frequent trades = tighter spreads optimal

        Returns:
            Alpha parameter (trades per second)
        """
        if len(self.trade_history) < self.min_samples:
            return 1.0  # Default fallback

        # Calculate time between trades
        trades = list(self.trade_history)
        time_diffs = []

        for i in range(1, len(trades)):
            time_diff = trades[i]['timestamp'] - trades[i-1]['timestamp']
            if time_diff > 0:
                time_diffs.append(time_diff)

        if not time_diffs:
            return 1.0

        # Alpha = 1 / average time between trades
        avg_time_between = np.mean(time_diffs)
        alpha = 1.0 / avg_time_between if avg_time_between > 0 else 1.0

        return alpha

    def estimate_liquidity_parameter(self) -> float:
        """
        Estimate kappa (order book depth coefficient)

        Based on order book depth analysis.
        Higher depth = lower kappa = tighter spreads possible
        Lower depth = higher kappa = wider spreads needed

        Returns:
            Kappa parameter (inverse of liquidity)
        """
        if len(self.depth_history) < self.min_samples:
            return 1.5  # Default fallback

        # Calculate average order book depth
        depths = [snapshot['avg_depth'] for snapshot in self.depth_history]
        avg_depth = np.mean(depths)

        if avg_depth <= 0:
            return 1.5  # Fallback for edge case

        # Kappa = 1 / depth (inverse relationship)
        # Scale by a factor to get reasonable values
        kappa = 10.0 / avg_depth if avg_depth > 0 else 1.5

        # Clamp kappa to reasonable range [0.1, 5.0]
        kappa = max(0.1, min(5.0, kappa))

        return kappa

    def estimate_volatility(self, lookback: int = 20) -> float:
        """
        Estimate market volatility from recent price movements

        Args:
            lookback: Number of samples to use

        Returns:
            Volatility estimate (standard deviation of returns)
        """
        if len(self.depth_history) < lookback:
            return 0.02  # Default 2% daily volatility

        # Get recent mid prices
        recent = list(self.depth_history)[-lookback:]
        prices = [s['mid_price'] for s in recent if s['mid_price'] is not None]

        if len(prices) < 2:
            return 0.02

        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)

        if not returns:
            return 0.02

        # Return standard deviation
        return np.std(returns)

    def get_dynamic_parameters(
        self,
        cache_duration: float = 60.0  # Cache for 60 seconds
    ) -> Dict[str, float]:
        """
        Get dynamically calculated market parameters

        Args:
            cache_duration: How long to cache results (seconds)

        Returns:
            Dictionary with alpha, kappa, and volatility
        """
        import time
        current_time = time.time()

        # Check cache validity
        if (self.cached_alpha is not None and
            self.cached_kappa is not None and
            self.last_update_time is not None and
            current_time - self.last_update_time < cache_duration):
            return {
                'alpha': self.cached_alpha,
                'kappa': self.cached_kappa,
                'sigma': self.estimate_volatility(),
                'cached': True
            }

        # Calculate fresh parameters
        alpha = self.estimate_arrival_rate()
        kappa = self.estimate_liquidity_parameter()
        sigma = self.estimate_volatility()

        # Update cache
        self.cached_alpha = alpha
        self.cached_kappa = kappa
        self.last_update_time = current_time

        return {
            'alpha': alpha,
            'kappa': kappa,
            'sigma': sigma,
            'cached': False
        }

    def get_statistics(self) -> Dict[str, any]:
        """
        Get analyzer statistics for debugging/monitoring

        Returns:
            Statistics dictionary
        """
        return {
            'trade_samples': len(self.trade_history),
            'depth_samples': len(self.depth_history),
            'min_samples': self.min_samples,
            'ready': (len(self.trade_history) >= self.min_samples and
                     len(self.depth_history) >= self.min_samples),
            'cached_alpha': self.cached_alpha,
            'cached_kappa': self.cached_kappa,
            'last_update': self.last_update_time
        }


def simulate_order_book_from_candles(
    candles: List[Dict],
    index: int,
    depth_levels: int = 10
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Simulate order book from candle data for backtesting

    In real trading, you'd get actual order book snapshots.
    For backtesting, we simulate based on OHLC data.

    Args:
        candles: Candle data
        index: Current candle index
        depth_levels: Number of levels to generate

    Returns:
        (bids, asks) tuple of [(price, size), ...] lists
    """
    if index < 0 or index >= len(candles):
        return [], []

    candle = candles[index]
    mid_price = candle['close']

    # Estimate spread from high-low range
    price_range = candle['high'] - candle['low']
    tick_size = price_range / (depth_levels * 2) if price_range > 0 else mid_price * 0.0001

    # Generate synthetic order book
    bids = []
    asks = []

    # Typical order book depth curve: exponential decay
    base_size = 1.0  # Base order size in BTC

    for i in range(depth_levels):
        # Price levels
        bid_price = mid_price - tick_size * (i + 1)
        ask_price = mid_price + tick_size * (i + 1)

        # Size decreases exponentially with distance from mid
        # More liquidity near mid price
        decay_factor = np.exp(-0.1 * i)
        size = base_size * decay_factor

        bids.append((bid_price, size))
        asks.append((ask_price, size))

    return bids, asks
