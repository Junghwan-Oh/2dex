"""
시장 데이터 인터페이스

각 DEX는 이 인터페이스를 구현하여 통일된 시장 데이터 접근을 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class MarketDataInterface(ABC):
    """시장 데이터 인터페이스 (DEX 공통)"""

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """
        현재 가격 조회

        Args:
            symbol: 심볼 (예: 'BTC-USDT')

        Returns:
            현재 가격
        """
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        티커 정보 조회

        Args:
            symbol: 심볼

        Returns:
            티커 정보:
                - symbol: str
                - lastPrice: float
                - bidPrice: float
                - askPrice: float
                - volume24h: float
                - timestamp: int
        """
        pass

    @abstractmethod
    def get_orderbook(
        self,
        symbol: str,
        depth: int = 20
    ) -> Dict[str, Any]:
        """
        오더북 조회

        Args:
            symbol: 심볼
            depth: 깊이 (각 방향별 레벨 수)

        Returns:
            오더북:
                - bids: List[List[float]]  # [[price, size], ...]
                - asks: List[List[float]]
                - timestamp: int
        """
        pass

    @abstractmethod
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        startTime: Optional[int] = None,
        endTime: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        캔들스틱 (OHLCV) 데이터 조회

        Args:
            symbol: 심볼
            interval: 시간 간격 ('1m', '5m', '15m', '1h', '4h', '1d' 등)
            limit: 최대 개수
            startTime: 시작 시간 (밀리초 타임스탬프)
            endTime: 종료 시간 (밀리초 타임스탬프)

        Returns:
            캔들스틱 리스트:
                - timestamp: int
                - open: float
                - high: float
                - low: float
                - close: float
                - volume: float
        """
        pass

    @abstractmethod
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        펀딩레이트 조회 (Perpetual DEX 전용)

        Args:
            symbol: 심볼

        Returns:
            펀딩레이트 정보:
                - fundingRate: float
                - nextFundingTime: int
                - markPrice: float
                - indexPrice: float
        """
        pass

    @abstractmethod
    def get_open_interest(self, symbol: str) -> float:
        """
        미결제약정 조회

        Args:
            symbol: 심볼

        Returns:
            미결제약정 (Open Interest)
        """
        pass

    @abstractmethod
    def subscribe_ticker(
        self,
        symbol: str,
        callback: callable
    ) -> None:
        """
        티커 실시간 구독 (WebSocket)

        Args:
            symbol: 심볼
            callback: 데이터 수신 시 호출될 콜백 함수
        """
        pass

    @abstractmethod
    def subscribe_orderbook(
        self,
        symbol: str,
        callback: callable
    ) -> None:
        """
        오더북 실시간 구독 (WebSocket)

        Args:
            symbol: 심볼
            callback: 데이터 수신 시 호출될 콜백 함수
        """
        pass

    @abstractmethod
    def unsubscribe_all(self) -> None:
        """모든 WebSocket 구독 해제"""
        pass
