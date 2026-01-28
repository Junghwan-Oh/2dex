"""
포지션 계산 유틸리티

모든 DEX에서 공통으로 사용하는 포지션 관련 계산 함수
"""

from typing import Optional


def calculateLiquidationPrice(
    entryPrice: float,
    leverage: float,
    side: str,  # 'LONG' or 'SHORT'
    maintenanceMarginRate: float = 0.005
) -> float:
    """
    청산가 계산

    Args:
        entryPrice: 진입가
        leverage: 레버리지
        side: 포지션 방향 ('LONG' or 'SHORT')
        maintenanceMarginRate: 유지증거금률 (기본값 0.5%)

    Returns:
        청산가
    """
    if side == 'LONG':
        # LONG 청산가 = 진입가 × (1 - 1/레버리지 + 유지증거금률)
        liquidationPrice = entryPrice * (1 - 1/leverage + maintenanceMarginRate)
    else:  # SHORT
        # SHORT 청산가 = 진입가 × (1 + 1/레버리지 - 유지증거금률)
        liquidationPrice = entryPrice * (1 + 1/leverage - maintenanceMarginRate)

    return liquidationPrice


def calculateUnrealizedPnl(
    side: str,
    entryPrice: float,
    markPrice: float,
    size: float
) -> float:
    """
    미실현 손익 계산

    Args:
        side: 포지션 방향 ('LONG' or 'SHORT')
        entryPrice: 진입가
        markPrice: 현재가 (Mark Price)
        size: 포지션 크기 (BTC)

    Returns:
        미실현 손익 (USD)
    """
    if side == 'LONG':
        pnl = (markPrice - entryPrice) * size
    else:  # SHORT
        pnl = (entryPrice - markPrice) * size

    return pnl


def calculateRequiredMargin(
    positionSize: float,
    entryPrice: float,
    leverage: float
) -> float:
    """
    필요 증거금 계산

    Args:
        positionSize: 포지션 크기 (BTC)
        entryPrice: 진입가
        leverage: 레버리지

    Returns:
        필요 증거금 (USD)
    """
    notionalValue = positionSize * entryPrice
    requiredMargin = notionalValue / leverage

    return requiredMargin


def calculatePositionSizeFromMargin(
    availableMargin: float,
    entryPrice: float,
    leverage: float,
    marginUsagePercent: float = 0.5
) -> float:
    """
    사용 가능한 증거금으로부터 포지션 크기 계산

    Args:
        availableMargin: 사용 가능한 증거금 (USD)
        entryPrice: 진입가
        leverage: 레버리지
        marginUsagePercent: 증거금 사용 비율 (기본값 50%)

    Returns:
        포지션 크기 (BTC)
    """
    usableMargin = availableMargin * marginUsagePercent
    notionalValue = usableMargin * leverage
    positionSize = notionalValue / entryPrice

    return positionSize


def calculateBreakEvenPrice(
    entryPrice: float,
    side: str,
    makerFeeRate: float,
    takerFeeRate: float = 0.0
) -> float:
    """
    손익분기점 가격 계산

    Args:
        entryPrice: 진입가
        side: 포지션 방향 ('LONG' or 'SHORT')
        makerFeeRate: Maker 수수료율 (음수면 Rebate)
        takerFeeRate: Taker 수수료율 (청산 시)

    Returns:
        손익분기점 가격
    """
    # Maker Rebate는 음수이므로 abs() 처리
    totalFeeRate = abs(makerFeeRate) + takerFeeRate

    if side == 'LONG':
        # LONG 손익분기 = 진입가 × (1 + 수수료)
        breakEvenPrice = entryPrice * (1 + totalFeeRate)
    else:  # SHORT
        # SHORT 손익분기 = 진입가 × (1 - 수수료)
        breakEvenPrice = entryPrice * (1 - totalFeeRate)

    return breakEvenPrice


def calculateFundingPayment(
    positionSize: float,
    markPrice: float,
    fundingRate: float
) -> float:
    """
    펀딩비 지급액 계산

    Args:
        positionSize: 포지션 크기 (BTC, LONG은 양수, SHORT는 음수)
        markPrice: 현재가
        fundingRate: 펀딩비율 (소수점, 예: 0.0001 = 0.01%)

    Returns:
        펀딩비 지급액 (USD)
        - 양수: 수령
        - 음수: 지불
    """
    notionalValue = abs(positionSize) * markPrice
    fundingPayment = -notionalValue * fundingRate

    # LONG일 때: 음의 펀딩비면 수령, 양의 펀딩비면 지불
    # SHORT일 때: 양의 펀딩비면 수령, 음의 펀딩비면 지불
    if positionSize < 0:  # SHORT
        fundingPayment = -fundingPayment

    return fundingPayment
