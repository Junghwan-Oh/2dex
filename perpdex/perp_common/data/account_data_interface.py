"""
계정 데이터 인터페이스

각 DEX는 이 인터페이스를 구현하여 통일된 계정 데이터 접근을 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class AccountDataInterface(ABC):
    """계정 데이터 인터페이스 (DEX 공통)"""

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """
        계정 잔고 조회

        Returns:
            잔고 정보:
                - totalBalance: float  # 총 잔고
                - availableBalance: float  # 사용 가능 잔고
                - marginBalance: float  # 마진 잔고
                - unrealizedPnl: float  # 미실현 손익
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        포지션 목록 조회

        Returns:
            포지션 리스트:
                - symbol: str
                - side: str  # 'LONG' or 'SHORT'
                - size: float
                - entryPrice: float
                - markPrice: float
                - liquidationPrice: float
                - unrealizedPnl: float
                - leverage: float
                - marginType: str  # 'ISOLATED' or 'CROSS'
        """
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        특정 심볼의 포지션 조회

        Args:
            symbol: 심볼

        Returns:
            포지션 정보 (없으면 None)
        """
        pass

    @abstractmethod
    def get_open_orders(
        self,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        미체결 주문 조회

        Args:
            symbol: 심볼 (None이면 전체)

        Returns:
            주문 리스트:
                - orderId: str
                - symbol: str
                - side: str  # 'BUY' or 'SELL'
                - type: str  # 'MARKET', 'LIMIT', etc.
                - price: float
                - size: float
                - filledSize: float
                - status: str
                - createTime: int
        """
        pass

    @abstractmethod
    def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        주문 이력 조회

        Args:
            symbol: 심볼 (None이면 전체)
            limit: 최대 개수

        Returns:
            주문 이력 리스트
        """
        pass

    @abstractmethod
    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        거래 이력 조회

        Args:
            symbol: 심볼 (None이면 전체)
            limit: 최대 개수

        Returns:
            거래 이력 리스트:
                - tradeId: str
                - orderId: str
                - symbol: str
                - side: str
                - price: float
                - size: float
                - fee: float
                - feeAsset: str
                - timestamp: int
        """
        pass

    @abstractmethod
    def get_pnl_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        손익 이력 조회

        Args:
            symbol: 심볼 (None이면 전체)
            limit: 최대 개수

        Returns:
            손익 이력 리스트:
                - symbol: str
                - realizedPnl: float
                - timestamp: int
        """
        pass
