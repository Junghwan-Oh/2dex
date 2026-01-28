"""
PositionCalculator 유닛 테스트

TDD 방식: 테스트를 먼저 작성하고 구현은 나중에
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from common.lib.position_calculator import (
    calculateLiquidationPrice,
    calculateUnrealizedPnl,
    calculateRequiredMargin,
    calculatePositionSizeFromMargin,
    calculateBreakEvenPrice,
    calculateFundingPayment
)


class TestPositionCalculator:
    """포지션 계산 유틸리티 테스트"""

    def test_liquidation_price_long(self):
        """LONG 포지션 청산가 계산"""
        liquidationPrice = calculateLiquidationPrice(
            entryPrice=50000.0,
            leverage=10.0,
            side='LONG',
            maintenanceMarginRate=0.005
        )

        # 예상: 50000 × (1 - 1/10 + 0.005) = 45,250
        assert abs(liquidationPrice - 45250.0) < 1.0

    def test_liquidation_price_short(self):
        """SHORT 포지션 청산가 계산"""
        liquidationPrice = calculateLiquidationPrice(
            entryPrice=50000.0,
            leverage=10.0,
            side='SHORT',
            maintenanceMarginRate=0.005
        )

        # 예상: 50000 × (1 + 1/10 - 0.005) = 54,750
        assert abs(liquidationPrice - 54750.0) < 1.0

    @pytest.mark.parametrize("entryPrice,leverage,expected", [
        (50000.0, 5.0, 40250.0),   # 5x leverage
        (50000.0, 10.0, 45250.0),  # 10x leverage
        (50000.0, 20.0, 47750.0),  # 20x leverage
    ])
    def test_liquidation_price_various_leverage(self, entryPrice, leverage, expected):
        """다양한 레버리지에서 청산가 계산"""
        liquidationPrice = calculateLiquidationPrice(
            entryPrice=entryPrice,
            leverage=leverage,
            side='LONG'
        )

        assert abs(liquidationPrice - expected) < 1.0

    def test_unrealized_pnl_long_profit(self):
        """LONG 포지션 미실현 손익 (수익)"""
        pnl = calculateUnrealizedPnl(
            side='LONG',
            entryPrice=50000.0,
            markPrice=51000.0,
            size=0.001
        )

        # 예상: (51000 - 50000) × 0.001 = 1.0
        assert abs(pnl - 1.0) < 0.01

    def test_unrealized_pnl_long_loss(self):
        """LONG 포지션 미실현 손익 (손실)"""
        pnl = calculateUnrealizedPnl(
            side='LONG',
            entryPrice=50000.0,
            markPrice=49000.0,
            size=0.001
        )

        # 예상: (49000 - 50000) × 0.001 = -1.0
        assert abs(pnl - (-1.0)) < 0.01

    def test_unrealized_pnl_short_profit(self):
        """SHORT 포지션 미실현 손익 (수익)"""
        pnl = calculateUnrealizedPnl(
            side='SHORT',
            entryPrice=50000.0,
            markPrice=49000.0,
            size=0.001
        )

        # 예상: (50000 - 49000) × 0.001 = 1.0
        assert abs(pnl - 1.0) < 0.01

    def test_unrealized_pnl_short_loss(self):
        """SHORT 포지션 미실현 손익 (손실)"""
        pnl = calculateUnrealizedPnl(
            side='SHORT',
            entryPrice=50000.0,
            markPrice=51000.0,
            size=0.001
        )

        # 예상: (50000 - 51000) × 0.001 = -1.0
        assert abs(pnl - (-1.0)) < 0.01

    def test_required_margin(self):
        """필요 증거금 계산"""
        margin = calculateRequiredMargin(
            positionSize=0.001,
            entryPrice=50000.0,
            leverage=10.0
        )

        # 예상: 0.001 × 50000 / 10 = 5.0
        assert abs(margin - 5.0) < 0.01

    @pytest.mark.parametrize("leverage,expected", [
        (5.0, 10.0),   # 5x
        (10.0, 5.0),   # 10x
        (20.0, 2.5),   # 20x
    ])
    def test_required_margin_various_leverage(self, leverage, expected):
        """다양한 레버리지에서 필요 증거금"""
        margin = calculateRequiredMargin(
            positionSize=0.001,
            entryPrice=50000.0,
            leverage=leverage
        )

        assert abs(margin - expected) < 0.01

    def test_position_size_from_margin(self):
        """증거금으로부터 포지션 크기 계산"""
        positionSize = calculatePositionSizeFromMargin(
            availableMargin=1000.0,
            entryPrice=50000.0,
            leverage=10.0,
            marginUsagePercent=0.5
        )

        # 예상: 1000 × 0.5 × 10 / 50000 = 0.1 BTC
        assert abs(positionSize - 0.1) < 0.001

    def test_break_even_price_long_with_fee(self):
        """LONG 포지션 손익분기점 (수수료 포함)"""
        breakEvenPrice = calculateBreakEvenPrice(
            entryPrice=50000.0,
            side='LONG',
            makerFeeRate=0.0,  # Apex: 0% Maker
            takerFeeRate=0.00025  # Apex: 0.025% Taker
        )

        # 예상: 50000 × (1 + 0.00025) = 50012.5
        assert abs(breakEvenPrice - 50012.5) < 0.1

    def test_break_even_price_long_with_rebate(self):
        """LONG 포지션 손익분기점 (Maker Rebate 포함)"""
        breakEvenPrice = calculateBreakEvenPrice(
            entryPrice=50000.0,
            side='LONG',
            makerFeeRate=-0.00005,  # Paradex: -0.005% Maker Rebate
            takerFeeRate=0.0003  # Paradex: 0.03% Taker
        )

        # 예상: 50000 × (1 + 0.00005 + 0.0003) = 50017.5
        # Rebate는 음수이므로 abs() 처리
        assert abs(breakEvenPrice - 50017.5) < 0.1

    def test_break_even_price_short(self):
        """SHORT 포지션 손익분기점"""
        breakEvenPrice = calculateBreakEvenPrice(
            entryPrice=50000.0,
            side='SHORT',
            makerFeeRate=0.0,
            takerFeeRate=0.00025
        )

        # 예상: 50000 × (1 - 0.00025) = 49987.5
        assert abs(breakEvenPrice - 49987.5) < 0.1

    def test_funding_payment_long_positive_rate(self):
        """LONG 포지션, 양의 펀딩비 (지불)"""
        payment = calculateFundingPayment(
            positionSize=0.01,  # LONG (양수)
            markPrice=50000.0,
            fundingRate=0.0001  # 0.01% 양의 펀딩비
        )

        # LONG은 양의 펀딩비에서 지불
        # 예상: -(0.01 × 50000 × 0.0001) = -0.05
        assert abs(payment - (-0.05)) < 0.01

    def test_funding_payment_long_negative_rate(self):
        """LONG 포지션, 음의 펀딩비 (수령)"""
        payment = calculateFundingPayment(
            positionSize=0.01,  # LONG (양수)
            markPrice=50000.0,
            fundingRate=-0.0001  # -0.01% 음의 펀딩비
        )

        # LONG은 음의 펀딩비에서 수령
        # 예상: -(0.01 × 50000 × -0.0001) = 0.05
        assert abs(payment - 0.05) < 0.01

    def test_funding_payment_short_positive_rate(self):
        """SHORT 포지션, 양의 펀딩비 (수령)"""
        payment = calculateFundingPayment(
            positionSize=-0.01,  # SHORT (음수)
            markPrice=50000.0,
            fundingRate=0.0001  # 0.01% 양의 펀딩비
        )

        # SHORT는 양의 펀딩비에서 수령
        # 예상: 0.01 × 50000 × 0.0001 = 0.05
        assert abs(payment - 0.05) < 0.01

    def test_funding_payment_short_negative_rate(self):
        """SHORT 포지션, 음의 펀딩비 (지불)"""
        payment = calculateFundingPayment(
            positionSize=-0.01,  # SHORT (음수)
            markPrice=50000.0,
            fundingRate=-0.0001  # -0.01% 음의 펀딩비
        )

        # SHORT는 음의 펀딩비에서 지불
        # 예상: -(0.01 × 50000 × -0.0001) = -0.05
        assert abs(payment - (-0.05)) < 0.01
