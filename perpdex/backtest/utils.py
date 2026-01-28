"""
백테스팅 보조 함수
"""

from typing import Dict, List
from datetime import datetime


def calculateProfitRate(side: str, entryPrice: float, exitPrice: float) -> float:
    """
    수익률 계산

    Args:
        side: 'BUY' or 'SELL'
        entryPrice: 진입 가격
        exitPrice: 청산 가격

    Returns:
        수익률 (소수, 예: 0.05 = 5%)
    """
    if side == 'BUY':
        # 롱: (청산가 - 진입가) / 진입가
        profitRate = (exitPrice - entryPrice) / entryPrice
    else:  # SELL
        # 숏: (진입가 - 청산가) / 진입가
        profitRate = (entryPrice - exitPrice) / entryPrice

    return profitRate


def formatTimestamp(ts: int) -> str:
    """
    타임스탬프를 읽기 쉬운 형식으로 변환

    Args:
        ts: Unix timestamp (초)

    Returns:
        포맷된 문자열 (예: "2024-01-15 14:30:00")
    """
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def calculateSpread(bid: float, ask: float) -> float:
    """
    스프레드 계산 (비율)

    Args:
        bid: 매수 호가
        ask: 매도 호가

    Returns:
        스프레드 비율 (소수, 예: 0.0005 = 0.05%)
    """
    midPrice = (bid + ask) / 2
    spread = (ask - bid) / midPrice
    return spread


def calculateNotional(price: float, size: float) -> float:
    """
    포지션 명목 가치 계산

    Args:
        price: 가격
        size: 수량 (BTC)

    Returns:
        명목 가치 (USD)
    """
    return price * size


def roundPrice(price: float, tickSize: float = 0.1) -> float:
    """
    가격을 틱 사이즈에 맞춰 반올림

    Args:
        price: 원본 가격
        tickSize: 틱 사이즈 (기본 0.1)

    Returns:
        반올림된 가격
    """
    return round(price / tickSize) * tickSize


def calculateDrawdown(equity: List[float]) -> float:
    """
    최대 낙폭 계산

    Args:
        equity: 자산 곡선 리스트

    Returns:
        최대 낙폭 비율 (소수, 예: 0.15 = 15%)
    """
    if not equity or len(equity) < 2:
        return 0.0

    maxDrawdown = 0.0
    peak = equity[0]

    for value in equity:
        if value > peak:
            peak = value

        drawdown = (peak - value) / peak if peak > 0 else 0.0
        maxDrawdown = max(maxDrawdown, drawdown)

    return maxDrawdown


def calculateSharpeRatio(returns: List[float], riskFreeRate: float = 0.0) -> float:
    """
    Sharpe Ratio 계산

    Args:
        returns: 수익률 리스트
        riskFreeRate: 무위험 수익률 (기본 0)

    Returns:
        Sharpe Ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    avgReturn = sum(returns) / len(returns)

    # 표준편차 계산
    variance = sum((r - avgReturn) ** 2 for r in returns) / len(returns)
    stdDev = variance ** 0.5

    if stdDev == 0:
        return 0.0

    sharpeRatio = (avgReturn - riskFreeRate) / stdDev
    return sharpeRatio
