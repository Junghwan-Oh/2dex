"""
리스크 관리 클래스

포지션 크기, 손실, 노출 등을 모니터링하고 제한하는 클래스
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    maxDrawdown: float          # 최대 낙폭 비율 (예: 0.15 = 15%)
    maxDailyLoss: float         # 일일 최대 손실 금액 (USD)
    maxDailyTrades: int         # 일일 최대 거래 횟수
    maxExposure: float          # 최대 노출 금액 (USD)


class RiskManager:
    """리스크 관리자"""

    def __init__(self, config: RiskConfig):
        """
        RiskManager 초기화

        Args:
            config: 리스크 설정
        """
        self.maxDrawdown = config.maxDrawdown
        self.maxDailyLoss = config.maxDailyLoss
        self.maxDailyTrades = config.maxDailyTrades
        self.maxExposure = config.maxExposure

        # Violation tracking
        self._drawdownViolation = False
        self._dailyLossViolation = False
        self._tradeLimitViolation = False
        self._exposureViolation = False

    def checkDrawdown(self, currentEquity: float, peakEquity: float) -> bool:
        """
        최대 낙폭 체크

        Args:
            currentEquity: 현재 자산
            peakEquity: 최고 자산

        Returns:
            True if within limit, False if breach

        Raises:
            ValueError: peakEquity가 0 이하인 경우
        """
        if peakEquity <= 0:
            raise ValueError("Peak equity must be positive")

        if currentEquity < 0:
            self._drawdownViolation = True
            return False

        # Calculate drawdown
        drawdown = (peakEquity - currentEquity) / peakEquity

        # Check if within limit
        if drawdown > self.maxDrawdown:
            self._drawdownViolation = True
            return False

        return True

    def checkDailyLoss(self, dailyPnl: float) -> bool:
        """
        일일 손실 제한 체크

        Args:
            dailyPnl: 일일 손익 (음수 = 손실)

        Returns:
            True if within limit, False if breach
        """
        # If profit, always OK
        if dailyPnl >= 0:
            return True

        # Check loss amount
        loss = abs(dailyPnl)

        if loss > self.maxDailyLoss:
            self._dailyLossViolation = True
            return False

        return True

    def checkTradeLimit(self, tradesCount: int) -> bool:
        """
        일일 거래 횟수 제한 체크

        Args:
            tradesCount: 현재 거래 횟수

        Returns:
            True if within limit, False if breach

        Raises:
            ValueError: tradesCount가 음수인 경우
        """
        if tradesCount < 0:
            raise ValueError("Trade count cannot be negative")

        if tradesCount > self.maxDailyTrades:
            self._tradeLimitViolation = True
            return False

        return True

    def checkExposure(self, totalNotional: float) -> bool:
        """
        총 노출 금액 체크

        Args:
            totalNotional: 총 노출 금액 (포지션 크기 × 가격)

        Returns:
            True if within limit, False if breach

        Raises:
            ValueError: totalNotional이 음수인 경우
        """
        if totalNotional < 0:
            raise ValueError("Total notional cannot be negative")

        if totalNotional > self.maxExposure:
            self._exposureViolation = True
            return False

        return True

    def shouldHalt(self) -> bool:
        """
        거래 중단 여부 판단

        Returns:
            True if any violation occurred (should halt trading)
        """
        return (
            self._drawdownViolation or
            self._dailyLossViolation or
            self._tradeLimitViolation or
            self._exposureViolation
        )

    def reset(self) -> None:
        """모든 위반 상태 초기화"""
        self._drawdownViolation = False
        self._dailyLossViolation = False
        self._tradeLimitViolation = False
        self._exposureViolation = False

    def getViolationStatus(self) -> dict:
        """
        현재 위반 상태 조회

        Returns:
            각 리스크 항목별 위반 여부
        """
        return {
            'drawdown': self._drawdownViolation,
            'dailyLoss': self._dailyLossViolation,
            'tradeLimit': self._tradeLimitViolation,
            'exposure': self._exposureViolation,
            'shouldHalt': self.shouldHalt()
        }
