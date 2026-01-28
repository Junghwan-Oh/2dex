"""
Paradex API 클라이언트 래퍼

paradex-py SDK를 쉽게 사용할 수 있도록 래핑한 클래스
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv


class ParadexClient:
    """
    Paradex API 클라이언트

    Testnet과 Mainnet 자동 전환 지원
    공식 paradex-py SDK 기반
    """

    def __init__(
        self,
        environment: str = 'testnet',
        l1_address: Optional[str] = None,
        l1_private_key: Optional[str] = None
    ):
        """
        ParadexClient 초기화

        Args:
            environment: 'testnet' 또는 'mainnet' (기본값: 'testnet')
            l1_address: Ethereum L1 주소 (None이면 .env에서 로드)
            l1_private_key: Ethereum L1 개인키 (None이면 .env에서 로드)
        """
        self.environment = environment.lower()

        if self.environment not in ['testnet', 'mainnet']:
            raise ValueError(f"Invalid environment: {environment}. Use 'testnet' or 'mainnet'.")

        # L1 자격 증명 로드
        if l1_address and l1_private_key:
            self.l1Address = l1_address
            self.l1PrivateKey = l1_private_key
        else:
            self.l1Address, self.l1PrivateKey = self._load_credentials()

        # Paradex SDK 클라이언트 초기화
        try:
            from paradex_py import Paradex

            self.client = Paradex(
                env=self.environment,
                l1_address=self.l1Address,
                l1_private_key=self.l1PrivateKey
            )

        except ImportError:
            raise ImportError(
                "paradex-py SDK가 설치되지 않았습니다.\n"
                "다음 명령어로 설치하세요: pip install paradex-py"
            )
        except Exception as e:
            raise RuntimeError(f"Paradex 클라이언트 초기화 실패: {e}")

    def _load_credentials(self):
        """환경 변수에서 L1 자격 증명 로드"""
        load_dotenv()

        l1Address = os.getenv('PARADEX_L1_ADDRESS')
        l1PrivateKey = os.getenv('PARADEX_L1_PRIVATE_KEY')

        if not all([l1Address, l1PrivateKey]):
            raise ValueError(
                ".env 파일에 다음 2개 항목이 필요합니다:\n"
                "- PARADEX_L1_ADDRESS\n"
                "- PARADEX_L1_PRIVATE_KEY"
            )

        return l1Address, l1PrivateKey

    # ========== Public API Methods ==========

    def get_markets(self) -> Optional[List[Dict]]:
        """
        전체 마켓 리스트 조회

        Returns:
            마켓 정보 리스트 (symbol, base_currency, quote_currency 등)
        """
        try:
            response = self.client.fetch_markets()
            return response
        except Exception as e:
            print(f"[WARNING] Markets 조회 실패: {e}")
            return None

    def get_ticker(self, market: str) -> Optional[Dict]:
        """
        특정 마켓의 현재가 정보 조회

        Args:
            market: 마켓 심볼 (예: 'BTC-USD-PERP')

        Returns:
            티커 정보 딕셔너리 (last_price, mark_price, index_price 등)
        """
        try:
            response = self.client.fetch_ticker(market)
            return response
        except Exception as e:
            print(f"[WARNING] Ticker 조회 실패 ({market}): {e}")
            return None

    def get_funding_rate(self, market: str) -> Optional[Dict]:
        """
        펀딩비 정보 조회

        Args:
            market: 마켓 심볼 (예: 'BTC-USD-PERP')

        Returns:
            펀딩비 정보 (funding_rate, next_funding_time 등)
        """
        try:
            response = self.client.fetch_funding_rate(market)
            return response
        except Exception as e:
            print(f"[WARNING] Funding Rate 조회 실패 ({market}): {e}")
            return None

    # ========== Private API Methods ==========

    def get_account(self) -> Optional[Dict]:
        """
        계좌 정보 조회

        Returns:
            계좌 정보 (account_id, balances, positions 등)
        """
        try:
            response = self.client.fetch_account()
            return response
        except Exception as e:
            print(f"[ERROR] 계좌 조회 실패: {e}")
            return None

    def get_balances(self) -> Optional[List[Dict]]:
        """
        잔액 정보 조회

        Returns:
            토큰별 잔액 리스트
        """
        try:
            response = self.client.fetch_balance()
            return response
        except Exception as e:
            print(f"[ERROR] 잔액 조회 실패: {e}")
            return None

    def get_positions(self) -> Optional[List[Dict]]:
        """
        포지션 정보 조회

        Returns:
            활성 포지션 리스트
        """
        try:
            response = self.client.fetch_positions()
            return response
        except Exception as e:
            print(f"[ERROR] 포지션 조회 실패: {e}")
            return None

    def create_order(
        self,
        market: str,
        side: str,
        order_type: str,
        size: str,
        price: Optional[str] = None,
        post_only: bool = True,
        reduce_only: bool = False,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        주문 생성

        Args:
            market: 마켓 심볼 (예: 'BTC-USD-PERP')
            side: 'BUY' 또는 'SELL'
            order_type: 'LIMIT' 또는 'MARKET'
            size: 주문 수량 (BTC 수량, 문자열)
            price: 주문 가격 (LIMIT 주문 시 필수, 문자열)
            post_only: POST_ONLY 플래그 (Maker 수수료 보장)
            reduce_only: 포지션 청산 전용 주문 여부
            client_order_id: 클라이언트 주문 ID (선택)

        Returns:
            주문 응답 딕셔너리 (order_id, status 등)
        """
        try:
            if order_type.upper() == 'LIMIT' and not price:
                raise ValueError("LIMIT 주문은 price 파라미터가 필수입니다.")

            order_params = {
                'market': market,
                'side': side.upper(),
                'type': order_type.upper(),
                'size': size,
                'reduce_only': reduce_only
            }

            if price:
                order_params['price'] = price

            if post_only:
                order_params['post_only'] = True

            if client_order_id:
                order_params['client_order_id'] = client_order_id

            response = self.client.create_order(**order_params)
            return response

        except Exception as e:
            print(f"[ERROR] 주문 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def cancel_order(self, order_id: str) -> Optional[Dict]:
        """
        주문 취소

        Args:
            order_id: 주문 ID

        Returns:
            취소 응답 딕셔너리
        """
        try:
            response = self.client.cancel_order(order_id)
            return response
        except Exception as e:
            print(f"[ERROR] 주문 취소 실패: {e}")
            return None

    def get_open_orders(self, market: Optional[str] = None) -> Optional[List[Dict]]:
        """
        미체결 주문 조회

        Args:
            market: 특정 마켓만 조회 (None이면 전체)

        Returns:
            미체결 주문 리스트
        """
        try:
            if market:
                response = self.client.fetch_open_orders(market)
            else:
                response = self.client.fetch_open_orders()
            return response
        except Exception as e:
            print(f"[ERROR] 미체결 주문 조회 실패: {e}")
            return None

    def get_order_history(
        self,
        market: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        주문 내역 조회

        Args:
            market: 특정 마켓만 조회 (None이면 전체)
            limit: 조회할 최대 개수 (기본값: 100)

        Returns:
            주문 내역 리스트
        """
        try:
            params = {'limit': limit}
            if market:
                params['market'] = market

            response = self.client.fetch_orders(**params)
            return response
        except Exception as e:
            print(f"[ERROR] 주문 내역 조회 실패: {e}")
            return None

    # ========== 편의 메서드 ==========

    def get_active_positions(self) -> List[Dict]:
        """
        활성 포지션 목록 조회

        Returns:
            활성 포지션 리스트 (size > 0인 포지션만)
        """
        positions = self.get_positions()
        if not positions:
            return []

        # size가 0이 아닌 포지션만 필터링
        active_positions = [
            p for p in positions
            if p.get('size') and float(p['size']) != 0
        ]

        return active_positions

    def get_account_summary(self) -> Dict:
        """
        계좌 요약 정보 조회

        Returns:
            {
                'account_id': str,
                'total_equity': float,
                'available_balance': float,
                'used_margin': float,
                'unrealized_pnl': float
            }
        """
        account = self.get_account()
        balances = self.get_balances()

        if not account:
            return {}

        summary = {
            'account_id': account.get('account_id', 'N/A'),
            'environment': self.environment
        }

        # 잔액 정보
        if balances:
            for balance in balances:
                currency = balance.get('currency', 'USD')
                if currency == 'USD':
                    summary['total_equity'] = float(balance.get('equity', 0))
                    summary['available_balance'] = float(balance.get('available', 0))
                    summary['used_margin'] = float(balance.get('locked', 0))
                    summary['unrealized_pnl'] = float(balance.get('unrealized_pnl', 0))

        return summary

    def __repr__(self) -> str:
        return f"ParadexClient(environment='{self.environment}', l1_address='{self.l1Address[:6]}...')"
