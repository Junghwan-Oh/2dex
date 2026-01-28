"""
기본 리스크 관리 클래스

모든 전략의 리스크 관리 기본 클래스.
각 전략은 이 클래스를 상속받아 전략별 리스크 관리를 구현합니다.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from decimal import Decimal


class BaseRiskManager(ABC):
    """모든 전략의 리스크 관리 기본 클래스"""

    def __init__(
        self,
        maxPositionSize: float,
        maxLeverage: float,
        maxDrawdown: float = 0.20  # 20% 최대 손실
    ):
        """
        Args:
            maxPositionSize: 최대 포지션 크기 (USD)
            maxLeverage: 최대 레버리지
            maxDrawdown: 최대 허용 손실 비율 (0.20 = 20%)
        """
        self.maxPositionSize = maxPositionSize
        self.maxLeverage = maxLeverage
        self.maxDrawdown = maxDrawdown

        # 내부 상태
        self._peakBalance = 0.0
        self._currentBalance = 0.0

    def check_position_size(self, size: float) -> bool:
        """
        포지션 사이즈 체크 (공통)

        Args:
            size: 체크할 포지션 크기 (USD)

        Returns:
            허용 가능하면 True, 아니면 False
        """
        return size <= self.maxPositionSize

    def check_leverage(self, leverage: float) -> bool:
        """
        레버리지 체크 (공통)

        Args:
            leverage: 체크할 레버리지

        Returns:
            허용 가능하면 True, 아니면 False
        """
        return leverage <= self.maxLeverage

    def update_balance(self, balance: float) -> None:
        """
        잔고 업데이트 및 피크 추적

        Args:
            balance: 현재 잔고
        """
        self._currentBalance = balance
        if balance > self._peakBalance:
            self._peakBalance = balance

    def check_drawdown(self) -> bool:
        """
        현재 드로우다운 체크

        Returns:
            허용 범위 내이면 True, 초과하면 False
        """
        if self._peakBalance == 0:
            return True

        drawdown = (self._peakBalance - self._currentBalance) / self._peakBalance
        return drawdown < self.maxDrawdown

    def get_current_drawdown(self) -> float:
        """
        현재 드로우다운 비율 반환

        Returns:
            드로우다운 비율 (0.0 ~ 1.0)
        """
        if self._peakBalance == 0:
            return 0.0
        return (self._peakBalance - self._currentBalance) / self._peakBalance

    @abstractmethod
    def calculate_stop_loss(
        self,
        entryPrice: float,
        direction: str
    ) -> Optional[float]:
        """
        스탑로스 계산 (전략별 구현 필수)

        Args:
            entryPrice: 진입 가격
            direction: 'LONG' 또는 'SHORT'

        Returns:
            스탑로스 가격, 또는 None (스탑로스 사용하지 않는 경우)
        """
        pass

    @abstractmethod
    def calculate_take_profit(
        self,
        entryPrice: float,
        direction: str
    ) -> Optional[float]:
        """
        이익실현 가격 계산 (전략별 구현 필수)

        Args:
            entryPrice: 진입 가격
            direction: 'LONG' 또는 'SHORT'

        Returns:
            이익실현 가격, 또는 None (TP 사용하지 않는 경우)
        """
        pass

    def validate_order(
        self,
        size: float,
        leverage: float,
        orderType: str = "MARKET"
    ) -> Dict[str, Any]:
        """
        주문 전 검증 (공통)

        Args:
            size: 주문 크기 (USD)
            leverage: 레버리지
            orderType: 주문 타입

        Returns:
            검증 결과 딕셔너리:
                - valid: bool
                - reason: str (실패 시)
        """
        # 포지션 사이즈 체크
        if not self.check_position_size(size):
            return {
                'valid': False,
                'reason': f'Position size {size} exceeds max {self.maxPositionSize}'
            }

        # 레버리지 체크
        if not self.check_leverage(leverage):
            return {
                'valid': False,
                'reason': f'Leverage {leverage} exceeds max {self.maxLeverage}'
            }

        # 드로우다운 체크
        if not self.check_drawdown():
            return {
                'valid': False,
                'reason': f'Drawdown {self.get_current_drawdown():.2%} exceeds max {self.maxDrawdown:.2%}'
            }

        return {'valid': True}
