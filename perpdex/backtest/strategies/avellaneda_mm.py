"""
Avellaneda-Stoikov Market Making Strategy

Academic optimal market making model that calculates spreads based on:
- Inventory risk (position skew adjustment)
- Time decay (end-of-day inventory risk)
- Volatility (wider spreads in volatile markets)
- Risk aversion parameter

Reference: "High-frequency trading in a limit order book"
by Avellaneda & Stoikov (2008)
"""

import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import math
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.order_book_analyzer import OrderBookAnalyzer, simulate_order_book_from_candles


class AvellanedaMarketMaker:
    """Avellaneda-Stoikov Market Making Strategy"""

    def __init__(
        self,
        gamma: float = 0.1,  # Risk aversion parameter (0.01 to 1.0)
        sigma: float = 0.02,  # Volatility estimate (2% daily)
        k: float = 1.5,  # Liquidity parameter
        eta: float = 1.0,  # Order arrival intensity
        T: int = 86400,  # Trading day length (seconds)
        positionLimit: float = 1000.0,  # Max position size
        minSpread: float = 0.0001,  # Minimum spread (0.01%)
        maxSpread: float = 0.005,  # Maximum spread (0.5%)
        apexMakerFee: float = 0.0002,  # Apex standard maker fee (0.02%)
        paradexMakerFee: float = 0.0,  # Paradex retail (0%) - Conservative
        useDynamicParams: bool = False  # Use dynamic alpha/kappa from order book
    ):
        """
        Initialize Avellaneda MM strategy

        Args:
            gamma: Risk aversion (higher = more conservative)
            sigma: Volatility estimate
            k: Liquidity parameter (market depth)
            eta: Order arrival rate
            T: Trading horizon (seconds)
            positionLimit: Maximum position allowed
            minSpread: Minimum allowed spread
            maxSpread: Maximum allowed spread
            apexMakerFee: Apex maker fee (0.02% standard, Grid Bot not available via API)
            paradexMakerFee: Paradex fee (0% retail conservative, -0.0005% if RPI available)
        """
        self.gamma = gamma
        self.sigma = sigma
        self.k = k
        self.eta = eta
        self.T = T
        self.positionLimit = positionLimit
        self.minSpread = minSpread
        self.maxSpread = maxSpread
        self.apexMakerFee = apexMakerFee
        self.paradexMakerFee = paradexMakerFee
        self.useDynamicParams = useDynamicParams

        # Internal state
        self.currentPosition = 0.0
        self.dayStartTime = None
        self.totalVolume = 0.0

        # Order Book Analyzer (if dynamic params enabled)
        self.analyzer = OrderBookAnalyzer() if useDynamicParams else None

    def calculateVolatility(self, candles: List[Dict], lookback: int = 20) -> float:
        """
        Calculate realized volatility from recent price data

        Args:
            candles: Price history
            lookback: Number of periods to look back

        Returns:
            Volatility estimate
        """
        if len(candles) < lookback + 1:
            return self.sigma  # Use default if not enough data

        # Calculate returns
        returns = []
        for i in range(len(candles) - lookback, len(candles)):
            if i > 0:
                ret = (candles[i]['close'] - candles[i-1]['close']) / candles[i-1]['close']
                returns.append(ret)

        if not returns:
            return self.sigma

        # Calculate volatility (annualized)
        std = np.std(returns)
        # Annualize based on candle frequency (assuming 1-minute candles)
        periods_per_day = 1440
        annualized_vol = std * math.sqrt(periods_per_day * 365)

        # Blend with configured volatility
        return 0.7 * annualized_vol + 0.3 * self.sigma

    def calculateOptimalSpread(
        self,
        currentPrice: float,
        timeRemaining: float,
        currentPosition: float,
        volatility: float,
        kappa: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate optimal bid and ask spreads using Avellaneda-Stoikov model

        Args:
            currentPrice: Current market price
            timeRemaining: Time remaining in trading day (0 to 1)
            currentPosition: Current inventory position
            volatility: Current volatility estimate
            kappa: Liquidity parameter (uses self.k if None)

        Returns:
            (bid_spread, ask_spread) as percentages
        """
        # Use dynamic kappa if provided, otherwise use static
        k_param = kappa if kappa is not None else self.k

        # Reservation price adjustment for inventory risk
        inventoryPenalty = self.gamma * volatility * volatility * timeRemaining
        reservationPrice = currentPrice - currentPosition * inventoryPenalty

        # Optimal spread calculation
        # s* = γσ²T + (2/γ)ln(1 + γ/k)
        baseSpread = (
            self.gamma * volatility * volatility * timeRemaining +
            (2 / self.gamma) * math.log(1 + self.gamma / k_param)
        )

        # Adjust for time decay (wider spreads near end of day)
        timeFactor = 1 + (1 - timeRemaining) * 0.5

        # Adjust for position skew
        # If long, lower ask spread to encourage selling
        # If short, lower bid spread to encourage buying
        positionSkew = abs(currentPosition) / self.positionLimit

        if currentPosition > 0:  # Long position
            bidSpread = baseSpread * timeFactor * (1 + positionSkew)
            askSpread = baseSpread * timeFactor * (1 - positionSkew * 0.5)
        elif currentPosition < 0:  # Short position
            bidSpread = baseSpread * timeFactor * (1 - positionSkew * 0.5)
            askSpread = baseSpread * timeFactor * (1 + positionSkew)
        else:  # Neutral
            bidSpread = baseSpread * timeFactor
            askSpread = baseSpread * timeFactor

        # Apply min/max constraints
        bidSpread = max(self.minSpread, min(self.maxSpread, bidSpread))
        askSpread = max(self.minSpread, min(self.maxSpread, askSpread))

        return bidSpread, askSpread

    def shouldEnter(
        self,
        candles: List[Dict],
        currentIdx: int
    ) -> Tuple[bool, Optional[str], Optional[float], Optional[Dict]]:
        """
        Determine optimal market making orders

        Args:
            candles: Price history
            currentIdx: Current candle index

        Returns:
            (shouldEnter, side, price, metadata)
        """
        if currentIdx < 20:  # Need history for volatility
            return False, None, None, None

        currentCandle = candles[currentIdx]
        currentPrice = currentCandle['close']
        currentTime = currentCandle['timestamp']

        # Initialize day start time
        if self.dayStartTime is None:
            self.dayStartTime = currentTime

        # Calculate time remaining (0 to 1)
        elapsedTime = currentTime - self.dayStartTime
        timeRemaining = max(0, 1 - (elapsedTime / self.T))

        # Check position limits
        if abs(self.currentPosition) >= self.positionLimit:
            return False, None, None, None

        # Get parameters (static or dynamic)
        if self.useDynamicParams and self.analyzer:
            # Simulate order book from candle data
            bids, asks = simulate_order_book_from_candles(candles, currentIdx)

            # Update analyzer with order book snapshot
            self.analyzer.update_order_book_data(
                timestamp=currentTime,
                bids=bids,
                asks=asks
            )

            # Get dynamic parameters
            params = self.analyzer.get_dynamic_parameters()
            kappa = params['kappa']
            volatility = params['sigma']
        else:
            # Use static parameters
            kappa = self.k
            volatility = self.calculateVolatility(candles[:currentIdx + 1])

        # Calculate optimal spreads with dynamic or static parameters
        bidSpread, askSpread = self.calculateOptimalSpread(
            currentPrice,
            timeRemaining,
            self.currentPosition,
            volatility,
            kappa
        )

        # Create limit orders
        bidPrice = currentPrice * (1 - bidSpread)
        askPrice = currentPrice * (1 + askSpread)

        # Metadata for order placement
        metadata = {
            'type': 'avellaneda_mm',
            'bid_price': bidPrice,
            'ask_price': askPrice,
            'bid_spread': bidSpread,
            'ask_spread': askSpread,
            'volatility': volatility,
            'kappa': kappa,
            'dynamic_params': self.useDynamicParams,
            'time_remaining': timeRemaining,
            'position': self.currentPosition,
            'apex_bid': bidPrice,  # Place on Apex
            'paradex_ask': askPrice  # Place on Paradex for rebate
        }

        # For backtesting, simulate order placement
        return True, 'AVELLANEDA', currentPrice, metadata

    def shouldExit(
        self,
        position: Dict,
        currentPrice: float,
        currentTimestamp: int
    ) -> Tuple[bool, str]:
        """
        Determine if positions should be closed

        Args:
            position: Current position
            currentPrice: Current price
            currentTimestamp: Current timestamp

        Returns:
            (shouldExit, reason)
        """
        entryTimestamp = position['entryTimestamp']
        elapsedTime = currentTimestamp - entryTimestamp

        # End of day liquidation
        if self.dayStartTime:
            dayElapsed = currentTimestamp - self.dayStartTime
            if dayElapsed >= self.T * 0.95:  # 95% of day complete
                return True, "END_OF_DAY_LIQUIDATION"

        # Check if spread was captured
        metadata = position.get('metadata', {})
        entryPrice = position['entryPrice']

        # Calculate if we captured our target spread
        bidSpread = metadata.get('bid_spread', self.minSpread)
        askSpread = metadata.get('ask_spread', self.minSpread)
        targetSpread = (bidSpread + askSpread) / 2

        priceMove = abs(currentPrice - entryPrice) / entryPrice
        if priceMove >= targetSpread:
            profit = priceMove - (self.apexMakerFee - self.paradexMakerFee)
            return True, f"SPREAD_CAPTURED_profit:{profit*100:.3f}%"

        # Risk management: cut losses if position moves against us
        if self.currentPosition > 0:  # Long
            loss = (entryPrice - currentPrice) / entryPrice
            if loss > targetSpread * 2:
                return True, f"STOP_LOSS_{loss*100:.3f}%"
        elif self.currentPosition < 0:  # Short
            loss = (currentPrice - entryPrice) / entryPrice
            if loss > targetSpread * 2:
                return True, f"STOP_LOSS_{loss*100:.3f}%"

        # Maximum hold time (fallback)
        maxHold = min(3600, self.T // 10)  # 1 hour or 10% of day
        if elapsedTime >= maxHold:
            return True, f"MAX_HOLD_{elapsedTime}s"

        return False, "HOLD"

    def updatePosition(self, trade: Dict) -> None:
        """Update internal position tracking"""
        size = trade.get('size', 100)
        side = trade.get('side')

        if side == 'BUY':
            self.currentPosition += size
        elif side == 'SELL':
            self.currentPosition -= size

        self.totalVolume += size


def runBacktest(
    candles: List[Dict],
    gamma: float = 0.1,
    sigma: float = 0.02,
    positionLimit: float = 1000.0,
    initialEquity: float = 5000.0,
    useDynamicParams: bool = False
) -> Dict:
    """
    Run Avellaneda MM strategy backtest

    Args:
        candles: Historical price data
        gamma: Risk aversion parameter
        sigma: Volatility estimate
        positionLimit: Maximum position size
        initialEquity: Starting capital
        useDynamicParams: Use dynamic alpha/kappa from order book

    Returns:
        Backtest results
    """
    from backtest.framework import BacktestEngine

    # Initialize strategy
    strategy = AvellanedaMarketMaker(
        gamma=gamma,
        sigma=sigma,
        positionLimit=positionLimit,
        useDynamicParams=useDynamicParams
    )

    # Run backtest
    engine = BacktestEngine(
        candles=candles,
        initialEquity=initialEquity,
        leverage=1,  # Always 1x for safety
        makerFee=0.0,  # Fees handled in strategy
        takerFee=0.0
    )

    results = engine.run(
        shouldEnterFunc=strategy.shouldEnter,
        shouldExitFunc=strategy.shouldExit,
        minInterval=60  # Minimum 1 minute between trades
    )

    # Add strategy parameters
    results['parameters'] = {
        'strategy': 'Avellaneda-Stoikov MM',
        'gamma': gamma,
        'sigma': sigma,
        'positionLimit': positionLimit,
        'k': strategy.k,
        'eta': strategy.eta,
        'useDynamicParams': useDynamicParams
    }

    # Calculate fee impact
    totalVolume = results.get('totalVolume', 0)
    # Assume 50/50 split between exchanges
    apexVolume = totalVolume * 0.5
    paradexVolume = totalVolume * 0.5

    apexFees = apexVolume * strategy.apexMakerFee
    paradexFees = paradexVolume * strategy.paradexMakerFee
    netFees = apexFees + paradexFees

    results['feeBreakdown'] = {
        'apexFees': apexFees,
        'paradexFees': paradexFees,
        'netFees': netFees,
        'effectiveFeeRate': netFees / totalVolume if totalVolume > 0 else 0
    }

    # Check if we achieved 0% target
    results['targetAchieved'] = results.get('returnRate', 0) >= 0

    return results