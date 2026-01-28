"""
기술적 지표 계산

MA (Moving Average), RSI (Relative Strength Index)
"""

from typing import List, Dict, Tuple


def calculateMa(candles: List[Dict], period: int) -> float:
    """
    이동평균 (Moving Average) 계산

    Args:
        candles: 캔들 데이터 리스트 [{open, high, low, close, volume, timestamp}, ...]
        period: MA 기간

    Returns:
        MA 값

    Raises:
        ValueError: 캔들 데이터가 부족한 경우
    """
    if len(candles) < period:
        raise ValueError(f"Not enough candles: need {period}, got {len(candles)}")

    # 최근 period개의 종가 평균
    recentCloses = [candle['close'] for candle in candles[-period:]]
    ma = sum(recentCloses) / period

    return ma


def calculateRsi(candles: List[Dict], period: int = 14) -> float:
    """
    RSI (Relative Strength Index) 계산

    Args:
        candles: 캔들 데이터 리스트
        period: RSI 기간 (기본 14)

    Returns:
        RSI 값 (0-100)

    Raises:
        ValueError: 캔들 데이터가 부족한 경우
    """
    if len(candles) < period + 1:
        raise ValueError(f"Not enough candles: need {period + 1}, got {len(candles)}")

    # 가격 변화 계산
    priceChanges = []
    for i in range(len(candles) - period, len(candles)):
        change = candles[i]['close'] - candles[i - 1]['close']
        priceChanges.append(change)

    # 상승/하락 분리
    gains = [change if change > 0 else 0 for change in priceChanges]
    losses = [-change if change < 0 else 0 for change in priceChanges]

    # 평균 상승/하락 계산
    avgGain = sum(gains) / period
    avgLoss = sum(losses) / period

    # RSI 계산
    if avgLoss == 0:
        return 100.0  # 하락이 없으면 RSI 100

    rs = avgGain / avgLoss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def detectTrend(
    ma5: float,
    ma10: float,
    ma20: float,
    currentPrice: float,
    threshold: float = 0.0001
) -> str:
    """
    MA를 이용한 추세 판별

    Args:
        ma5: 5기간 MA
        ma10: 10기간 MA
        ma20: 20기간 MA
        currentPrice: 현재 가격
        threshold: 추세 판별 임계값 (기본 0.01%)

    Returns:
        "UPTREND" | "DOWNTREND" | "SIDEWAYS"
    """
    # UPTREND: 현재가 > MA5 > MA10 > MA20
    if currentPrice > ma5 > ma10 > ma20:
        # 각 MA 간 차이가 threshold 이상이어야 명확한 추세
        if (ma5 - ma10) / ma10 >= threshold and (ma10 - ma20) / ma20 >= threshold:
            return "UPTREND"

    # DOWNTREND: 현재가 < MA5 < MA10 < MA20
    if currentPrice < ma5 < ma10 < ma20:
        if (ma10 - ma5) / ma10 >= threshold and (ma20 - ma10) / ma20 >= threshold:
            return "DOWNTREND"

    # 그 외: 횡보
    return "SIDEWAYS"


def calculateVolatility(candles: List[Dict], period: int = 20) -> float:
    """
    가격 변동성 계산 (표준편차 기반)

    Args:
        candles: 캔들 데이터
        period: 계산 기간

    Returns:
        변동성 (비율, 예: 0.05 = 5%)
    """
    if len(candles) < period:
        raise ValueError(f"Not enough candles: need {period}, got {len(candles)}")

    # 가격 변화율 계산
    returns = []
    for i in range(len(candles) - period + 1, len(candles)):
        priceChange = (candles[i]['close'] - candles[i - 1]['close']) / candles[i - 1]['close']
        returns.append(priceChange)

    # 표준편차
    avgReturn = sum(returns) / len(returns)
    variance = sum((r - avgReturn) ** 2 for r in returns) / len(returns)
    volatility = variance ** 0.5

    return volatility


def calculateAveragVolume(candles: List[Dict], period: int = 24) -> float:
    """
    평균 거래량 계산

    Args:
        candles: 캔들 데이터
        period: 계산 기간

    Returns:
        평균 거래량
    """
    if len(candles) < period:
        raise ValueError(f"Not enough candles: need {period}, got {len(candles)}")

    recentVolumes = [candle['volume'] for candle in candles[-period:]]
    avgVolume = sum(recentVolumes) / period

    return avgVolume
