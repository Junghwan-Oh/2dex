"""
Cross-DEX Market Making Strategy

Places maker orders on both Apex and Paradex to capture spread
while earning rebates on Paradex and minimizing fees on Apex.

Key Features:
- Never uses taker orders (always maker)
- Maintains balanced inventory across exchanges
- Targets 0% loss through spread capture
- Optimized for volume farming (48+ trades/day)
"""

import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class CrossDexMarketMaker:
    """Cross-DEX Market Making Strategy"""

    def __init__(
        self,
        spread: float = 0.0002,  # 0.02% total spread
        halfSpread: float = 0.0001,  # 0.01% each side
        positionLimit: float = 1000.0,  # Max position per exchange
        rebalanceThreshold: float = 0.6,  # Rebalance at 60/40 ratio
        minOrderSize: float = 10.0,  # Minimum order size
        maxHoldTime: int = 1800,  # Max 30 minutes hold time
        apexMakerFee: float = 0.0002,  # 0.02% Apex standard maker fee
        paradexMakerFee: float = 0.0,  # 0% Paradex retail (conservative)
        useGridBot: bool = False  # DEPRECATED: Grid Bot not available via API
    ):
        """
        Initialize Cross-DEX MM strategy

        Args:
            spread: Total spread to capture (0.02% default)
            halfSpread: Spread per side (0.01% each exchange)
            positionLimit: Maximum position size per exchange
            rebalanceThreshold: Inventory ratio to trigger rebalance
            minOrderSize: Minimum order size in USD
            maxHoldTime: Maximum time to hold position (seconds)
            apexMakerFee: Apex maker fee (0.02% standard, Grid Bot NOT available via API)
            paradexMakerFee: Paradex fee (0% retail conservative, -0.0005% if RPI)
            useGridBot: DEPRECATED - Grid Bot is platform UI only, not accessible via API
        """
        self.spread = spread
        self.halfSpread = halfSpread
        self.positionLimit = positionLimit
        self.rebalanceThreshold = rebalanceThreshold
        self.minOrderSize = minOrderSize
        self.maxHoldTime = maxHoldTime

        # Fee structure
        if useGridBot:
            import warnings
            warnings.warn(
                "Grid Bot is NOT available via API (platform UI only). "
                "Using standard Apex maker fee (0.02%) instead.",
                DeprecationWarning
            )
        self.apexMakerFee = apexMakerFee  # Always use standard fee (Grid Bot unavailable)
        self.paradexMakerFee = paradexMakerFee

        # Internal state
        self.apexPosition = 0.0  # Current position on Apex
        self.paradexPosition = 0.0  # Current position on Paradex
        self.pendingOrders = []  # Pending limit orders
        self.lastRebalance = 0  # Last rebalance timestamp

    def calculateSpreadCapture(self, entryPrice: float, exitPrice: float, size: float) -> float:
        """
        Calculate profit from spread capture including fees

        Args:
            entryPrice: Entry price
            exitPrice: Exit price
            size: Trade size

        Returns:
            Net profit after fees
        """
        # Spread capture
        spreadProfit = abs(exitPrice - entryPrice) / entryPrice * size

        # Calculate fees (both sides are maker orders)
        apexFee = size * self.apexMakerFee
        paradexFee = size * self.paradexMakerFee

        # Net profit
        return spreadProfit - apexFee - paradexFee

    def needsRebalancing(self) -> bool:
        """
        Check if inventory needs rebalancing

        Returns:
            True if rebalancing needed
        """
        totalPosition = abs(self.apexPosition) + abs(self.paradexPosition)
        if totalPosition == 0:
            return False

        # Check inventory ratio
        apexRatio = abs(self.apexPosition) / totalPosition
        paradexRatio = abs(self.paradexPosition) / totalPosition

        # Rebalance if either exceeds threshold
        return max(apexRatio, paradexRatio) > self.rebalanceThreshold

    def shouldEnter(
        self,
        candles: List[Dict],
        currentIdx: int
    ) -> Tuple[bool, Optional[str], Optional[float], Optional[Dict]]:
        """
        Determine if we should place new maker orders

        Args:
            candles: Candle data
            currentIdx: Current candle index

        Returns:
            (shouldEnter, side, price, metadata)
        """
        if currentIdx < 1:
            return False, None, None, None

        currentCandle = candles[currentIdx]
        currentPrice = currentCandle['close']

        # Check position limits
        if abs(self.apexPosition) >= self.positionLimit:
            return False, None, None, None
        if abs(self.paradexPosition) >= self.positionLimit:
            return False, None, None, None

        # Check if we need rebalancing first
        if self.needsRebalancing():
            # Rebalance by placing opposite orders
            if abs(self.apexPosition) > abs(self.paradexPosition):
                # Too much on Apex, place sell on Apex, buy on Paradex
                metadata = {
                    'type': 'rebalance',
                    'apex_order': 'sell_limit',
                    'apex_price': currentPrice * (1 + self.halfSpread),
                    'paradex_order': 'buy_limit',
                    'paradex_price': currentPrice * (1 - self.halfSpread)
                }
                return True, 'REBALANCE', currentPrice, metadata
            else:
                # Too much on Paradex, place buy on Apex, sell on Paradex
                metadata = {
                    'type': 'rebalance',
                    'apex_order': 'buy_limit',
                    'apex_price': currentPrice * (1 - self.halfSpread),
                    'paradex_order': 'sell_limit',
                    'paradex_price': currentPrice * (1 + self.halfSpread)
                }
                return True, 'REBALANCE', currentPrice, metadata

        # Normal market making: place orders on both sides
        # Inventory-based decision (realistic trading logic)
        if self.apexPosition <= self.paradexPosition:
            # Apex position is lower or equal -> increase Apex, decrease Paradex
            # Apex buy, Paradex sell
            metadata = {
                'type': 'market_make',
                'apex_order': 'buy_limit',
                'apex_price': currentPrice * (1 - self.halfSpread),
                'paradex_order': 'sell_limit',
                'paradex_price': currentPrice * (1 + self.halfSpread)
            }
        else:
            # Paradex position is lower -> increase Paradex, decrease Apex
            # Apex sell, Paradex buy
            metadata = {
                'type': 'market_make',
                'apex_order': 'sell_limit',
                'apex_price': currentPrice * (1 + self.halfSpread),
                'paradex_order': 'buy_limit',
                'paradex_price': currentPrice * (1 - self.halfSpread)
            }

        # For backtesting, we simulate both orders filling
        return True, 'CROSS_MM', currentPrice, metadata

    def shouldExit(
        self,
        position: Dict,
        currentPrice: float,
        currentTimestamp: int
    ) -> Tuple[bool, str]:
        """
        Determine if we should close positions

        Args:
            position: Current position
            currentPrice: Current price
            currentTimestamp: Current timestamp

        Returns:
            (shouldExit, reason)
        """
        entryTimestamp = position['entryTimestamp']
        elapsedTime = currentTimestamp - entryTimestamp

        # Time-based exit (max hold time)
        if elapsedTime >= self.maxHoldTime:
            return True, f"TIME_LIMIT_{elapsedTime}s"

        # Check if opposite orders filled (spread captured)
        metadata = position.get('metadata', {})
        if metadata.get('type') == 'market_make':
            # In real trading, we'd check if opposite orders filled
            # For backtesting, simulate fills based on price movement
            entryPrice = position['entryPrice']
            priceChange = abs(currentPrice - entryPrice) / entryPrice

            # If price moved by our spread, assume both sides filled
            if priceChange >= self.spread:
                return True, f"SPREAD_CAPTURED_{priceChange*100:.3f}%"

        # Inventory limit reached
        if abs(self.apexPosition) >= self.positionLimit * 0.95:
            return True, "APEX_LIMIT"
        if abs(self.paradexPosition) >= self.positionLimit * 0.95:
            return True, "PARADEX_LIMIT"

        return False, "HOLD"

    def updatePositions(self, trade: Dict) -> None:
        """
        Update internal position tracking

        Args:
            trade: Executed trade details
        """
        metadata = trade.get('metadata', {})
        size = trade.get('size', self.minOrderSize)

        # Update positions based on order types
        if metadata.get('apex_order') == 'buy_limit':
            self.apexPosition += size
        elif metadata.get('apex_order') == 'sell_limit':
            self.apexPosition -= size

        if metadata.get('paradex_order') == 'buy_limit':
            self.paradexPosition += size
        elif metadata.get('paradex_order') == 'sell_limit':
            self.paradexPosition -= size


def runBacktest(
    candles: List[Dict],
    spread: float = 0.0002,
    positionLimit: float = 1000.0,
    initialEquity: float = 5000.0,
    useGridBot: bool = False
) -> Dict:
    """
    Run Cross-DEX MM strategy backtest

    Args:
        candles: Historical price data
        spread: Target spread to capture
        positionLimit: Max position per exchange
        initialEquity: Starting capital
        useGridBot: Use Apex Grid Bot for rebates

    Returns:
        Backtest results
    """
    from backtest.framework import BacktestEngine

    # Initialize strategy
    strategy = CrossDexMarketMaker(
        spread=spread,
        positionLimit=positionLimit,
        useGridBot=useGridBot
    )

    # Custom backtest engine for cross-exchange simulation
    engine = BacktestEngine(
        candles=candles,
        initialEquity=initialEquity,
        leverage=1,  # Always use 1x for safety
        makerFee=0.0,  # Fees handled in strategy
        takerFee=0.0  # Never use taker orders
    )

    # Run backtest with custom entry/exit logic
    results = engine.run(
        shouldEnterFunc=strategy.shouldEnter,
        shouldExitFunc=strategy.shouldExit,
        minInterval=60  # Minimum 1 minute between trades
    )

    # Add strategy-specific metrics
    results['parameters'] = {
        'strategy': 'Cross-DEX Market Maker',
        'spread': spread,
        'positionLimit': positionLimit,
        'apexMakerFee': strategy.apexMakerFee,
        'paradexMakerFee': strategy.paradexMakerFee,
        'useGridBot': useGridBot
    }

    # Calculate effective fees
    totalVolume = results.get('totalVolume', 0)
    apexVolume = totalVolume / 2  # Assume equal split
    paradexVolume = totalVolume / 2

    apexFees = apexVolume * strategy.apexMakerFee
    paradexFees = paradexVolume * strategy.paradexMakerFee

    results['feeBreakdown'] = {
        'apexFees': apexFees,
        'paradexFees': paradexFees,
        'netFees': apexFees + paradexFees,
        'feeRate': (apexFees + paradexFees) / totalVolume if totalVolume > 0 else 0
    }

    # Calculate if we achieved 0% loss target
    finalReturn = results.get('returnRate', 0)
    results['targetAchieved'] = finalReturn >= 0

    return results