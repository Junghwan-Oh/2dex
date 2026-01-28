"""성과 추적 유틸리티"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class Trade:
    """거래 기록"""
    timestamp: int
    symbol: str
    side: str  # 'BUY' or 'SELL'
    size: float
    price: float
    fee: float
    pnl: float = 0.0  # 실현 손익
    orderId: Optional[str] = None
    strategyName: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """성과 지표"""
    totalTrades: int = 0
    winningTrades: int = 0
    losingTrades: int = 0
    totalPnl: float = 0.0
    totalFees: float = 0.0
    netPnl: float = 0.0
    winRate: float = 0.0
    profitFactor: float = 0.0
    averageWin: float = 0.0
    averageLoss: float = 0.0
    largestWin: float = 0.0
    largestLoss: float = 0.0
    maxDrawdown: float = 0.0
    sharpeRatio: float = 0.0
    totalVolume: float = 0.0


class PerformanceTracker:
    """성과 추적 클래스"""

    def __init__(self, strategyName: str = "default"):
        """
        Args:
            strategyName: 전략 이름
        """
        self.strategyName = strategyName
        self.trades: List[Trade] = []
        self.balanceHistory: List[Dict[str, Any]] = []
        self.peakBalance: float = 0.0
        self.currentBalance: float = 0.0

    def add_trade(self, trade: Trade) -> None:
        """
        거래 추가

        Args:
            trade: 거래 기록
        """
        trade.strategyName = self.strategyName
        self.trades.append(trade)

    def update_balance(self, balance: float, timestamp: Optional[int] = None) -> None:
        """
        잔고 업데이트

        Args:
            balance: 현재 잔고
            timestamp: 타임스탬프 (None이면 현재 시간)
        """
        if timestamp is None:
            timestamp = int(datetime.now().timestamp() * 1000)

        self.currentBalance = balance
        if balance > self.peakBalance:
            self.peakBalance = balance

        self.balanceHistory.append({
            'timestamp': timestamp,
            'balance': balance
        })

    def calculate_metrics(self) -> PerformanceMetrics:
        """
        성과 지표 계산

        Returns:
            성과 지표
        """
        metrics = PerformanceMetrics()

        if not self.trades:
            return metrics

        # 기본 통계
        metrics.totalTrades = len(self.trades)
        totalWins = 0.0
        totalLosses = 0.0

        for trade in self.trades:
            metrics.totalPnl += trade.pnl
            metrics.totalFees += trade.fee
            metrics.totalVolume += trade.size * trade.price

            if trade.pnl > 0:
                metrics.winningTrades += 1
                totalWins += trade.pnl
                metrics.largestWin = max(metrics.largestWin, trade.pnl)
            elif trade.pnl < 0:
                metrics.losingTrades += 1
                totalLosses += abs(trade.pnl)
                metrics.largestLoss = max(metrics.largestLoss, abs(trade.pnl))

        # 순손익
        metrics.netPnl = metrics.totalPnl - metrics.totalFees

        # 승률
        if metrics.totalTrades > 0:
            metrics.winRate = metrics.winningTrades / metrics.totalTrades

        # 평균 승/패
        if metrics.winningTrades > 0:
            metrics.averageWin = totalWins / metrics.winningTrades
        if metrics.losingTrades > 0:
            metrics.averageLoss = totalLosses / metrics.losingTrades

        # Profit Factor
        if totalLosses > 0:
            metrics.profitFactor = totalWins / totalLosses

        # 최대 낙폭
        if self.peakBalance > 0:
            metrics.maxDrawdown = (self.peakBalance - self.currentBalance) / self.peakBalance

        # Sharpe Ratio (간단 버전 - 일일 수익률 기반)
        if len(self.balanceHistory) > 1:
            returns = []
            for i in range(1, len(self.balanceHistory)):
                prevBalance = self.balanceHistory[i-1]['balance']
                currBalance = self.balanceHistory[i]['balance']
                if prevBalance > 0:
                    dailyReturn = (currBalance - prevBalance) / prevBalance
                    returns.append(dailyReturn)

            if returns:
                avgReturn = sum(returns) / len(returns)
                if len(returns) > 1:
                    variance = sum((r - avgReturn) ** 2 for r in returns) / (len(returns) - 1)
                    stdDev = variance ** 0.5
                    if stdDev > 0:
                        metrics.sharpeRatio = (avgReturn / stdDev) * (365 ** 0.5)  # 연율화

        return metrics

    def save_to_file(self, filepath: str) -> None:
        """
        성과 데이터를 파일로 저장

        Args:
            filepath: 저장 경로
        """
        data = {
            'strategyName': self.strategyName,
            'trades': [
                {
                    'timestamp': t.timestamp,
                    'symbol': t.symbol,
                    'side': t.side,
                    'size': t.size,
                    'price': t.price,
                    'fee': t.fee,
                    'pnl': t.pnl,
                    'orderId': t.orderId
                }
                for t in self.trades
            ],
            'balanceHistory': self.balanceHistory,
            'metrics': self.calculate_metrics().__dict__
        }

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filepath: str) -> None:
        """
        파일에서 성과 데이터 로드

        Args:
            filepath: 파일 경로
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.strategyName = data['strategyName']
        self.trades = [
            Trade(**t)
            for t in data['trades']
        ]
        self.balanceHistory = data['balanceHistory']

        # 피크 잔고 재계산
        if self.balanceHistory:
            self.currentBalance = self.balanceHistory[-1]['balance']
            self.peakBalance = max(h['balance'] for h in self.balanceHistory)

    def print_summary(self) -> None:
        """성과 요약 출력"""
        metrics = self.calculate_metrics()

        print(f"\n{'='*60}")
        print(f"Performance Summary - {self.strategyName}")
        print(f"{'='*60}")
        print(f"Total Trades: {metrics.totalTrades}")
        print(f"Winning Trades: {metrics.winningTrades} ({metrics.winRate:.2%})")
        print(f"Losing Trades: {metrics.losingTrades}")
        print(f"\nP&L:")
        print(f"  Total PnL: ${metrics.totalPnl:,.2f}")
        print(f"  Total Fees: ${metrics.totalFees:,.2f}")
        print(f"  Net PnL: ${metrics.netPnl:,.2f}")
        print(f"\nTrade Stats:")
        print(f"  Average Win: ${metrics.averageWin:,.2f}")
        print(f"  Average Loss: ${metrics.averageLoss:,.2f}")
        print(f"  Largest Win: ${metrics.largestWin:,.2f}")
        print(f"  Largest Loss: ${metrics.largestLoss:,.2f}")
        print(f"  Profit Factor: {metrics.profitFactor:.2f}")
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown: {metrics.maxDrawdown:.2%}")
        print(f"  Sharpe Ratio: {metrics.sharpeRatio:.2f}")
        print(f"\nVolume:")
        print(f"  Total Volume: ${metrics.totalVolume:,.2f}")
        print(f"{'='*60}\n")
