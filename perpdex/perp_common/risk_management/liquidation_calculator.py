"""청산가 계산"""

from typing import Optional


class LiquidationCalculator:
    """청산가 계산 유틸리티"""

    @staticmethod
    def calculate_liquidation_price(
        entryPrice: float,
        leverage: float,
        direction: str,
        maintenanceMarginRate: float = 0.005  # 0.5% 기본값
    ) -> Optional[float]:
        """
        청산가 계산 (Isolated Margin 기준)

        Args:
            entryPrice: 진입 가격
            leverage: 레버리지
            direction: 'LONG' 또는 'SHORT'
            maintenanceMarginRate: 유지 마진율 (DEX별 다름)

        Returns:
            청산가
        """
        if leverage == 0:
            return None

        if direction.upper() == 'LONG':
            # Long: 청산가 = 진입가 * (1 - 1/레버리지 + MMR)
            liquidationPrice = entryPrice * (1 - 1/leverage + maintenanceMarginRate)
        elif direction.upper() == 'SHORT':
            # Short: 청산가 = 진입가 * (1 + 1/레버리지 - MMR)
            liquidationPrice = entryPrice * (1 + 1/leverage - maintenanceMarginRate)
        else:
            raise ValueError(f"Invalid direction: {direction}")

        return liquidationPrice

    @staticmethod
    def calculate_distance_to_liquidation(
        currentPrice: float,
        liquidationPrice: float,
        direction: str
    ) -> float:
        """
        청산가까지 거리 계산 (%)

        Args:
            currentPrice: 현재 가격
            liquidationPrice: 청산가
            direction: 'LONG' 또는 'SHORT'

        Returns:
            청산가까지 거리 (%) - 양수면 안전, 음수면 청산됨
        """
        if direction.upper() == 'LONG':
            # Long: 현재가가 청산가보다 높으면 안전
            distance = (currentPrice - liquidationPrice) / currentPrice
        elif direction.upper() == 'SHORT':
            # Short: 현재가가 청산가보다 낮으면 안전
            distance = (liquidationPrice - currentPrice) / currentPrice
        else:
            raise ValueError(f"Invalid direction: {direction}")

        return distance

    @staticmethod
    def is_safe_from_liquidation(
        currentPrice: float,
        liquidationPrice: float,
        direction: str,
        safetyMargin: float = 0.10  # 10% 안전 마진
    ) -> bool:
        """
        청산 위험 체크

        Args:
            currentPrice: 현재 가격
            liquidationPrice: 청산가
            direction: 'LONG' 또는 'SHORT'
            safetyMargin: 안전 마진 (0.10 = 10%)

        Returns:
            안전하면 True, 위험하면 False
        """
        distance = LiquidationCalculator.calculate_distance_to_liquidation(
            currentPrice, liquidationPrice, direction
        )
        return distance > safetyMargin
