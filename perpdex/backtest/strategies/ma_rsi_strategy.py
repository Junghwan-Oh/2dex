"""
MA + RSI 볼륨 파밍 전략

사용자 제안:
- UPTREND + RSI ≤ 50 → 롱 진입
- DOWNTREND + RSI ≥ 50 → 숏 진입
- 목표 수익: +0.03~0.08%
- Stop-Loss: -0.08%
- 시간 만료: 30분
"""

import sys
from pathlib import Path
import random
from typing import Tuple, Optional, List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest.indicators import calculateMa, calculateRsi, detectTrend


class MaRsiStrategy:
    """MA + RSI 전략"""

    def __init__(
        self,
        maPeriods: Tuple[int, int, int] = (5, 10, 20),
        rsiPeriod: int = 14,
        rsiThreshold: Tuple[int, int] = (30, 50),
        minSpread: float = 0.0003,
        targetProfitRange: Tuple[float, float] = (0.0003, 0.0008),
        stopLoss: float = -0.0008,
        timeExpire: int = 30
    ):
        """
        전략 초기화

        Args:
            maPeriods: MA 기간 (ma5, ma10, ma20)
            rsiPeriod: RSI 기간
            rsiThreshold: RSI 임계값 (longMin, longMax)
            minSpread: 최소 스프레드
            targetProfitRange: 목표 수익 범위 (min, max)
            stopLoss: Stop-Loss
            timeExpire: 시간 만료 (분)
        """
        self.ma5Period, self.ma10Period, self.ma20Period = maPeriods
        self.rsiPeriod = rsiPeriod
        self.rsiLongMin, self.rsiLongMax = rsiThreshold
        self.rsiShortMin = rsiThreshold[1]  # 50
        self.rsiShortMax = 70  # 고정

        self.minSpread = minSpread
        self.targetProfitMin, self.targetProfitMax = targetProfitRange
        self.stopLoss = stopLoss
        self.timeExpire = timeExpire * 60  # 초로 변환

    def shouldEnter(
        self,
        candles: List[Dict],
        currentIdx: int
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        진입 조건 판단

        Args:
            candles: 캔들 데이터 (현재까지)
            currentIdx: 현재 캔들 인덱스

        Returns:
            (진입여부, 방향, 진입가격)
        """
        # 지표 계산에 필요한 최소 캔들 수 확인
        minCandles = max(self.ma20Period, self.rsiPeriod) + 1
        if len(candles) < minCandles:
            return False, None, None

        try:
            # 현재 가격
            currentCandle = candles[currentIdx]
            currentPrice = currentCandle['close']

            # Spread 체크 (간단화: bid/ask가 없으므로 스킵하거나 임의 설정)
            # 실제 백테스팅에서는 spread를 항상 충족한다고 가정
            # (실제 봇에서는 ticker에서 bid/ask로 계산)

            # MA 계산
            ma5 = calculateMa(candles[:currentIdx + 1], self.ma5Period)
            ma10 = calculateMa(candles[:currentIdx + 1], self.ma10Period)
            ma20 = calculateMa(candles[:currentIdx + 1], self.ma20Period)

            # 추세 판별
            trend = detectTrend(ma5, ma10, ma20, currentPrice)

            if trend == "SIDEWAYS":
                return False, None, None  # 명확한 추세 없음

            # RSI 계산
            rsi = calculateRsi(candles[:currentIdx + 1], self.rsiPeriod)

            # === 롱 진입 조건 ===
            if trend == "UPTREND":
                # RSI가 longMin <= RSI <= longMax
                if self.rsiLongMin <= rsi <= self.rsiLongMax:
                    # 진입가: 현재가 약간 위 (실제 체결 시뮬레이션)
                    entryPrice = currentPrice * 1.0001
                    return True, 'BUY', entryPrice

            # === 숏 진입 조건 ===
            if trend == "DOWNTREND":
                # RSI가 shortMin <= RSI <= shortMax
                if self.rsiShortMin <= rsi <= self.rsiShortMax:
                    # 진입가: 현재가 약간 아래
                    entryPrice = currentPrice * 0.9999
                    return True, 'SELL', entryPrice

            return False, None, None

        except (ValueError, IndexError) as e:
            # 지표 계산 실패 (데이터 부족 등)
            return False, None, None

    def shouldExit(
        self,
        position: Dict,
        currentPrice: float,
        currentTimestamp: int
    ) -> Tuple[bool, str]:
        """
        청산 조건 판단

        Args:
            position: 현재 포지션
            currentPrice: 현재 가격
            currentTimestamp: 현재 타임스탬프

        Returns:
            (청산여부, 청산이유)
        """
        side = position['side']
        entryPrice = position['entryPrice']
        entryTimestamp = position['entryTimestamp']

        # 수익률 계산
        if side == 'BUY':
            profitRate = (currentPrice - entryPrice) / entryPrice
        else:  # SELL
            profitRate = (entryPrice - currentPrice) / entryPrice

        # === 조건 1: 목표 수익 ===
        targetProfit = random.uniform(self.targetProfitMin, self.targetProfitMax)
        if profitRate >= targetProfit:
            return True, f"TARGET_{profitRate * 100:.3f}%"

        # === 조건 2: Stop-Loss ===
        if profitRate <= self.stopLoss:
            return True, f"STOP_LOSS_{profitRate * 100:.3f}%"

        # === 조건 3: 시간 만료 ===
        elapsedTime = currentTimestamp - entryTimestamp
        if elapsedTime >= self.timeExpire:
            return True, f"TIME_EXPIRE_{profitRate * 100:+.3f}%"

        return False, "HOLD"


def runBacktest(
    candles: List[Dict],
    maPeriods: Tuple[int, int, int] = (5, 10, 20),
    rsiPeriod: int = 14,
    rsiThreshold: Tuple[int, int] = (30, 50),
    targetProfitRange: Tuple[float, float] = (0.0003, 0.0008),
    stopLoss: float = -0.0008,
    timeExpire: int = 30,
    initialEquity: float = 5000.0,
    leverage: int = 10
) -> Dict:
    """
    MA+RSI 전략 백테스팅 실행

    Args:
        candles: 1분봉 캔들 데이터
        maPeriods: MA 기간
        rsiPeriod: RSI 기간
        rsiThreshold: RSI 임계값
        targetProfitRange: 목표 수익 범위 (min, max)
        stopLoss: Stop-Loss
        timeExpire: 시간 만료 (분)
        initialEquity: 초기 자본
        leverage: 레버리지

    Returns:
        백테스팅 결과
    """
    from backtest.framework import BacktestEngine

    # 전략 초기화
    strategy = MaRsiStrategy(
        maPeriods=maPeriods,
        rsiPeriod=rsiPeriod,
        rsiThreshold=rsiThreshold,
        targetProfitRange=targetProfitRange,
        stopLoss=stopLoss,
        timeExpire=timeExpire
    )

    # 백테스팅 엔진 초기화
    engine = BacktestEngine(
        candles=candles,
        initialEquity=initialEquity,
        leverage=leverage,
        makerFee=0.0,  # Apex maker fee
        takerFee=0.0005  # Apex taker fee 0.05%
    )

    # 백테스팅 실행
    results = engine.run(
        shouldEnterFunc=strategy.shouldEnter,
        shouldExitFunc=strategy.shouldExit,
        minInterval=180  # 최소 3분 간격 (보수적)
    )

    # 파라미터 정보 추가
    results['parameters'] = {
        'maPeriods': maPeriods,
        'rsiPeriod': rsiPeriod,
        'rsiThreshold': rsiThreshold,
        'targetProfitRange': targetProfitRange,
        'stopLoss': stopLoss,
        'timeExpire': timeExpire,
        'initialEquity': initialEquity,
        'leverage': leverage
    }

    # 거래 내역 추가
    results['trades'] = engine.trades

    return results
