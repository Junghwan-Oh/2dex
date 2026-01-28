"""
Grid Trading Strategy for Volume Farming

그리드 간격으로 매수/매도 주문 배치
가격이 그리드 레벨 통과 시 거래 실행
횡보장에서 높은 거래 빈도 달성
"""

import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class GridStrategy:
    """Grid Trading Strategy"""

    def __init__(
        self,
        gridSpacing: float = 0.002,  # 0.2% 간격
        numGrids: int = 20,  # 그리드 레벨 수
        priceRange: Optional[Tuple[float, float]] = None,  # (min, max) 가격 범위
        leverage: int = 10
    ):
        """
        전략 초기화

        Args:
            gridSpacing: 그리드 간격 (비율, 예: 0.002 = 0.2%)
            numGrids: 그리드 레벨 개수
            priceRange: 가격 범위 (None이면 자동 계산)
            leverage: 레버리지
        """
        self.gridSpacing = gridSpacing
        self.numGrids = numGrids
        self.priceRange = priceRange
        self.leverage = leverage

        self.gridLevels: List[float] = []
        self.currentPosition: Optional[Dict] = None
        self.lastTradePrice: Optional[float] = None

    def initializeGrids(self, currentPrice: float) -> None:
        """
        그리드 레벨 초기화

        Args:
            currentPrice: 현재 가격
        """
        if self.priceRange:
            minPrice, maxPrice = self.priceRange
        else:
            # 현재가 기준으로 위아래 numGrids/2 레벨
            halfGrids = self.numGrids // 2
            minPrice = currentPrice * (1 - self.gridSpacing * halfGrids)
            maxPrice = currentPrice * (1 + self.gridSpacing * halfGrids)

        # 그리드 레벨 생성
        self.gridLevels = []
        for i in range(self.numGrids + 1):
            level = minPrice + (maxPrice - minPrice) * i / self.numGrids
            self.gridLevels.append(level)

        # 초기 포지션 없음
        self.currentPosition = None
        self.lastTradePrice = currentPrice

    def shouldEnter(
        self,
        candles: List[Dict],
        currentIdx: int
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        진입 조건 판단

        Args:
            candles: 캔들 데이터
            currentIdx: 현재 인덱스

        Returns:
            (진입여부, 방향, 진입가격)
        """
        if not self.gridLevels:
            # 첫 실행: 그리드 초기화
            currentCandle = candles[currentIdx]
            self.initializeGrids(currentCandle['close'])
            return False, None, None

        currentCandle = candles[currentIdx]
        currentPrice = currentCandle['close']

        # 포지션이 없으면 진입 안 함 (그리드는 청산 후 즉시 반대 주문)
        if self.currentPosition is None:
            # 현재 가격에서 가장 가까운 그리드 레벨 찾기
            closestLevel = min(self.gridLevels, key=lambda x: abs(x - currentPrice))
            closestIdx = self.gridLevels.index(closestLevel)

            # 가격이 위로 가면 매도, 아래로 가면 매수
            if closestIdx > 0 and closestIdx < len(self.gridLevels) - 1:
                if currentPrice >= closestLevel:
                    # 그리드 위 = 롱 진입 (가격 하락 시 익절)
                    return True, 'BUY', currentPrice
                else:
                    # 그리드 아래 = 숏 진입 (가격 상승 시 익절)
                    return True, 'SELL', currentPrice

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

        # 수익률 계산
        if side == 'BUY':
            profitRate = (currentPrice - entryPrice) / entryPrice
        else:  # SELL
            profitRate = (entryPrice - currentPrice) / entryPrice

        # === 그리드 레벨 통과 체크 ===
        # 다음 그리드 레벨까지 도달하면 청산
        if side == 'BUY':
            # 롱: 가격이 gridSpacing만큼 하락하면 청산
            targetPrice = entryPrice * (1 - self.gridSpacing)
            if currentPrice <= targetPrice:
                return True, f"GRID_DOWN_{profitRate * 100:.3f}%"

            # 또는 gridSpacing만큼 상승하면 익절
            takeProfitPrice = entryPrice * (1 + self.gridSpacing)
            if currentPrice >= takeProfitPrice:
                return True, f"GRID_UP_{profitRate * 100:.3f}%"

        else:  # SELL
            # 숏: 가격이 gridSpacing만큼 상승하면 청산
            targetPrice = entryPrice * (1 + self.gridSpacing)
            if currentPrice >= targetPrice:
                return True, f"GRID_UP_{profitRate * 100:.3f}%"

            # 또는 gridSpacing만큼 하락하면 익절
            takeProfitPrice = entryPrice * (1 - self.gridSpacing)
            if currentPrice <= takeProfitPrice:
                return True, f"GRID_DOWN_{profitRate * 100:.3f}%"

        # === Stop-Loss (안전장치) ===
        # 그리드 간격의 2배 손실 시 강제 청산
        stopLoss = -2 * self.gridSpacing
        if profitRate <= stopLoss:
            return True, f"STOP_LOSS_{profitRate * 100:.3f}%"

        # === 시간 만료 (60분) ===
        elapsedTime = currentTimestamp - position['entryTimestamp']
        if elapsedTime >= 3600:  # 60분
            return True, f"TIME_EXPIRE_{profitRate * 100:+.3f}%"

        return False, "HOLD"


def runBacktest(
    candles: List[Dict],
    gridSpacing: float = 0.002,
    numGrids: int = 20,
    priceRange: Optional[Tuple[float, float]] = None,
    initialEquity: float = 5000.0,
    leverage: int = 10
) -> Dict:
    """
    Grid Trading 전략 백테스팅 실행

    Args:
        candles: 캔들 데이터
        gridSpacing: 그리드 간격
        numGrids: 그리드 레벨 수
        priceRange: 가격 범위
        initialEquity: 초기 자본
        leverage: 레버리지

    Returns:
        백테스팅 결과
    """
    from backtest.framework import BacktestEngine

    # 전략 초기화
    strategy = GridStrategy(
        gridSpacing=gridSpacing,
        numGrids=numGrids,
        priceRange=priceRange,
        leverage=leverage
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
        minInterval=0  # 그리드는 간격 제한 없음
    )

    # 파라미터 정보 추가
    results['parameters'] = {
        'gridSpacing': gridSpacing,
        'numGrids': numGrids,
        'priceRange': priceRange,
        'initialEquity': initialEquity,
        'leverage': leverage
    }

    # 거래 내역 추가
    results['trades'] = engine.trades

    return results
