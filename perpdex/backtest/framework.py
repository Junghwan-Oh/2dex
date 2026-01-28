"""
백테스팅 프레임워크

과거 데이터로 전략 시뮬레이션 실행
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime
import random


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(
        self,
        candles: List[Dict],
        initialEquity: float = 5000.0,
        leverage: int = 10,
        makerFee: float = 0.0,
        takerFee: float = 0.0005,
        tickSize: float = 0.1
    ):
        """
        백테스팅 엔진 초기화

        Args:
            candles: 1분봉 캔들 데이터
            initialEquity: 초기 자본 (USD)
            leverage: 레버리지
            makerFee: 메이커 수수료 (기본 0% for Apex)
            takerFee: 테이커 수수료 (기본 0.05%)
            tickSize: 틱 사이즈 (기본 0.1)
        """
        self.candles = candles
        self.initialEquity = initialEquity
        self.leverage = leverage
        self.makerFee = makerFee
        self.takerFee = takerFee
        self.tickSize = tickSize

        # 상태
        self.currentEquity = initialEquity
        self.currentPosition: Optional[Dict] = None
        self.trades: List[Dict] = []
        self.equityCurve: List[float] = [initialEquity]

    def roundPrice(self, price: float) -> float:
        """가격을 틱 사이즈에 맞춰 반올림"""
        return round(price / self.tickSize) * self.tickSize

    def calculatePositionSize(self, entryPrice: float) -> float:
        """
        포지션 크기 계산

        Args:
            entryPrice: 진입 가격

        Returns:
            포지션 크기 (BTC)
        """
        # 레버리지 적용한 가용 자금
        availableFunds = self.currentEquity * self.leverage

        # BTC 수량 계산
        size = availableFunds / entryPrice

        return size

    def enterPosition(
        self,
        side: str,
        entryPrice: float,
        timestamp: int,
        reason: str = "SIGNAL"
    ) -> bool:
        """
        포지션 진입

        Args:
            side: 'BUY' or 'SELL'
            entryPrice: 진입 가격
            timestamp: 진입 시간
            reason: 진입 이유

        Returns:
            진입 성공 여부
        """
        if self.currentPosition is not None:
            return False  # 이미 포지션 있음

        # 가격 반올림
        entryPrice = self.roundPrice(entryPrice)

        # 포지션 크기 계산
        size = self.calculatePositionSize(entryPrice)

        # 수수료 (테이커 가정)
        notional = entryPrice * size
        fee = notional * self.takerFee

        # 포지션 생성
        self.currentPosition = {
            'side': side,
            'entryPrice': entryPrice,
            'size': size,
            'entryTimestamp': timestamp,
            'entryFee': fee,
            'reason': reason
        }

        # 수수료 차감
        self.currentEquity -= fee

        return True

    def exitPosition(
        self,
        exitPrice: float,
        timestamp: int,
        reason: str = "TARGET"
    ) -> Optional[Dict]:
        """
        포지션 청산

        Args:
            exitPrice: 청산 가격
            timestamp: 청산 시간
            reason: 청산 이유

        Returns:
            거래 기록 (없으면 None)
        """
        if self.currentPosition is None:
            return None  # 포지션 없음

        # 가격 반올림
        exitPrice = self.roundPrice(exitPrice)

        position = self.currentPosition
        side = position['side']
        entryPrice = position['entryPrice']
        size = position['size']

        # 수익 계산
        if side == 'BUY':
            pnl = (exitPrice - entryPrice) * size
        else:  # SELL
            pnl = (entryPrice - exitPrice) * size

        # 청산 수수료
        notional = exitPrice * size
        exitFee = notional * self.takerFee

        # 총 수익 (수수료 포함)
        totalPnl = pnl - exitFee

        # 수익률
        profitRate = pnl / (entryPrice * size)

        # 자산 업데이트
        self.currentEquity += totalPnl

        # 거래 기록
        trade = {
            'side': side,
            'entryPrice': entryPrice,
            'exitPrice': exitPrice,
            'size': size,
            'entryTimestamp': position['entryTimestamp'],
            'exitTimestamp': timestamp,
            'duration': (timestamp - position['entryTimestamp']) / 60,  # 분
            'pnl': pnl,
            'fees': position['entryFee'] + exitFee,
            'totalPnl': totalPnl,
            'profitRate': profitRate,
            'entryReason': position['reason'],
            'exitReason': reason
        }

        self.trades.append(trade)

        # 자산 곡선 업데이트
        self.equityCurve.append(self.currentEquity)

        # 포지션 초기화
        self.currentPosition = None

        return trade

    def run(
        self,
        shouldEnterFunc: Callable,
        shouldExitFunc: Callable,
        minInterval: int = 60
    ) -> Dict:
        """
        백테스팅 실행

        Args:
            shouldEnterFunc: 진입 조건 함수 (candles, currentIdx) -> (shouldEnter, side, price)
            shouldExitFunc: 청산 조건 함수 (position, currentPrice, currentTime) -> (shouldExit, reason)
            minInterval: 최소 거래 간격 (초)

        Returns:
            백테스팅 결과
        """
        lastTradeTimestamp = 0

        for i in range(100, len(self.candles)):  # 최소 100개 캔들은 지표 계산에 필요
            candle = self.candles[i]
            currentPrice = candle['close']
            currentTimestamp = candle['timestamp']

            # 포지션 없음 → 진입 조건 체크
            if self.currentPosition is None:
                # 최소 거래 간격 체크
                if currentTimestamp - lastTradeTimestamp < minInterval:
                    continue

                # 진입 조건 체크
                result = shouldEnterFunc(
                    self.candles[:i + 1],
                    i
                )

                # Handle both 3 and 4 return values (backward compatibility)
                if len(result) == 3:
                    shouldEnter, side, entryPrice = result
                    metadata = None
                elif len(result) == 4:
                    shouldEnter, side, entryPrice, metadata = result
                else:
                    shouldEnter = result[0]
                    side = result[1] if len(result) > 1 else None
                    entryPrice = result[2] if len(result) > 2 else None
                    metadata = result[3] if len(result) > 3 else None

                if shouldEnter:
                    success = self.enterPosition(
                        side,
                        entryPrice if entryPrice else currentPrice,
                        currentTimestamp,
                        reason="SIGNAL"
                    )
                    if success and metadata:
                        # Store metadata in position
                        self.currentPosition['metadata'] = metadata
                    if success:
                        lastTradeTimestamp = currentTimestamp

            # 포지션 있음 → 청산 조건 체크
            else:
                shouldExit, reason = shouldExitFunc(
                    self.currentPosition,
                    currentPrice,
                    currentTimestamp
                )

                if shouldExit:
                    trade = self.exitPosition(
                        currentPrice,
                        currentTimestamp,
                        reason
                    )
                    if trade:
                        lastTradeTimestamp = currentTimestamp

        # 마지막 포지션이 있으면 강제 청산
        if self.currentPosition is not None:
            lastCandle = self.candles[-1]
            self.exitPosition(
                lastCandle['close'],
                lastCandle['timestamp'],
                reason="END_OF_DATA"
            )

        # 결과 계산
        return self.calculateResults()

    def calculateResults(self) -> Dict:
        """
        백테스팅 결과 계산

        Returns:
            결과 딕셔너리
        """
        if not self.trades:
            return {
                'totalTrades': 0,
                'winRate': 0.0,
                'avgProfit': 0.0,
                'avgLoss': 0.0,
                'totalPnl': 0.0,
                'finalEquity': self.currentEquity,
                'returnRate': 0.0,
                'maxDrawdown': 0.0,
                'sharpeRatio': 0.0
            }

        # 승패 분류
        winningTrades = [t for t in self.trades if t['totalPnl'] > 0]
        losingTrades = [t for t in self.trades if t['totalPnl'] <= 0]

        # 기본 지표
        totalTrades = len(self.trades)
        winRate = len(winningTrades) / totalTrades if totalTrades > 0 else 0.0

        avgProfit = sum(t['totalPnl'] for t in winningTrades) / len(winningTrades) if winningTrades else 0.0
        avgLoss = sum(t['totalPnl'] for t in losingTrades) / len(losingTrades) if losingTrades else 0.0

        totalPnl = sum(t['totalPnl'] for t in self.trades)
        finalEquity = self.currentEquity
        returnRate = (finalEquity - self.initialEquity) / self.initialEquity

        # 최대 낙폭
        maxDrawdown = 0.0
        peak = self.initialEquity
        for equity in self.equityCurve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0.0
            maxDrawdown = max(maxDrawdown, drawdown)

        # Sharpe Ratio
        returns = [t['profitRate'] for t in self.trades]
        avgReturn = sum(returns) / len(returns) if returns else 0.0
        variance = sum((r - avgReturn) ** 2 for r in returns) / len(returns) if returns else 0.0
        stdDev = variance ** 0.5
        sharpeRatio = avgReturn / stdDev if stdDev > 0 else 0.0

        # 거래 간격 통계
        durations = [t['duration'] for t in self.trades]
        avgDuration = sum(durations) / len(durations) if durations else 0.0

        # 연속 손실
        maxConsecutiveLosses = 0
        currentLosses = 0
        for trade in self.trades:
            if trade['totalPnl'] <= 0:
                currentLosses += 1
                maxConsecutiveLosses = max(maxConsecutiveLosses, currentLosses)
            else:
                currentLosses = 0

        # Calculate total volume and average trade size
        totalVolume = sum(t['size'] * t['entryPrice'] + t['size'] * t['exitPrice'] for t in self.trades)
        avgTradeSize = totalVolume / (totalTrades * 2) if totalTrades > 0 else 0

        return {
            'totalTrades': totalTrades,
            'winningTrades': len(winningTrades),
            'losingTrades': len(losingTrades),
            'winRate': winRate,
            'avgProfit': avgProfit,
            'avgLoss': avgLoss,
            'totalPnl': totalPnl,
            'totalFees': sum(t['fees'] for t in self.trades),
            'totalVolume': totalVolume,
            'avgTradeSize': avgTradeSize,
            'finalEquity': finalEquity,
            'returnRate': returnRate,
            'maxDrawdown': maxDrawdown,
            'sharpeRatio': sharpeRatio,
            'avgDuration': avgDuration,
            'maxConsecutiveLosses': maxConsecutiveLosses,
            'tradesPerDay': totalTrades / (len(self.candles) / 1440) if len(self.candles) > 1440 else 0
        }
