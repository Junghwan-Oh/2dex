"""포지션 사이징 계산"""

from typing import Dict, Any


class PositionSizer:
    """포지션 크기 계산 유틸리티"""

    @staticmethod
    def calculate_position_size(
        accountBalance: float,
        riskPercentage: float,
        stopLossDistance: float,
        currentPrice: float
    ) -> float:
        """
        포지션 크기 계산 (고정 리스크 방식)

        Args:
            accountBalance: 계정 잔고
            riskPercentage: 리스크 비율 (0.02 = 2%)
            stopLossDistance: 스탑로스까지 거리 (%)
            currentPrice: 현재 가격

        Returns:
            포지션 크기 (USD)
        """
        riskAmount = accountBalance * riskPercentage
        positionSize = riskAmount / stopLossDistance
        return positionSize

    @staticmethod
    def calculate_kelly_criterion(
        winRate: float,
        avgWin: float,
        avgLoss: float,
        accountBalance: float
    ) -> float:
        """
        Kelly Criterion 방식 포지션 크기 계산

        Args:
            winRate: 승률 (0.0 ~ 1.0)
            avgWin: 평균 이익
            avgLoss: 평균 손실
            accountBalance: 계정 잔고

        Returns:
            최적 포지션 크기 (USD)
        """
        if avgLoss == 0:
            return 0.0

        winLossRatio = avgWin / avgLoss
        kellyPercentage = (winRate * winLossRatio - (1 - winRate)) / winLossRatio

        # Kelly percentage를 절반으로 (더 보수적)
        kellyPercentage = max(0, kellyPercentage / 2)

        return accountBalance * kellyPercentage

    @staticmethod
    def calculate_fixed_percentage(
        accountBalance: float,
        percentage: float = 0.95
    ) -> float:
        """
        고정 비율 방식 포지션 크기 계산

        Args:
            accountBalance: 계정 잔고
            percentage: 사용할 비율 (0.95 = 95%)

        Returns:
            포지션 크기 (USD)
        """
        return accountBalance * percentage
