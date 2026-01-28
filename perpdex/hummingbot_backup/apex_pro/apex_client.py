"""
ApeX API 클라이언트 래퍼

Public API와 Private API를 쉽게 사용할 수 있도록 래핑한 클래스
"""

import os
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from apexomni.http_private_sign import HttpPrivateSign
from apexomni.http_public import HttpPublic
from apexomni.constants import (
    APEX_OMNI_HTTP_MAIN,
    APEX_OMNI_HTTP_TEST,
    NETWORKID_OMNI_MAIN_ARB,
    NETWORKID_OMNI_TEST_BNB
)


class ApexClient:
    """
    ApeX Omni API 클라이언트

    메인넷과 테스트넷 자동 전환 지원
    Public API와 Private API 통합 관리
    """

    def __init__(
        self,
        environment: str = 'mainnet',
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
        zk_seeds: Optional[str] = None,
        zk_l2_key: Optional[str] = None
    ):
        """
        ApexClient 초기화

        Args:
            environment: 'mainnet' 또는 'testnet' (기본값: 'mainnet')
            api_key: API Key (None이면 .env에서 로드)
            api_secret: API Secret (None이면 .env에서 로드)
            api_passphrase: API Passphrase (None이면 .env에서 로드)
            zk_seeds: Omni Key Seed (None이면 .env에서 로드)
            zk_l2_key: Omni Key L2 Key (None이면 .env에서 로드)
        """
        self.environment = environment.lower()

        # 환경에 따른 엔드포인트 설정
        if self.environment == 'mainnet':
            self.api_url = APEX_OMNI_HTTP_MAIN
            self.network_id = NETWORKID_OMNI_MAIN_ARB
        elif self.environment == 'testnet':
            self.api_url = APEX_OMNI_HTTP_TEST
            self.network_id = NETWORKID_OMNI_TEST_BNB
        else:
            raise ValueError(f"Invalid environment: {environment}. Use 'mainnet' or 'testnet'.")

        # API 자격 증명 로드
        if api_key and api_secret and api_passphrase:
            self.api_key = api_key
            self.api_secret = api_secret
            self.api_passphrase = api_passphrase
        else:
            self.api_key, self.api_secret, self.api_passphrase = self._load_credentials()

        # Omni Key 로드
        if zk_seeds and zk_l2_key:
            self.zk_seeds = zk_seeds
            self.zk_l2_key = zk_l2_key
        else:
            self.zk_seeds, self.zk_l2_key = self._load_omni_key()

        # Public 클라이언트 초기화 (인증 불필요)
        self.public_client = HttpPublic(self.api_url)

        # Private 클라이언트 초기화 (인증 + Omni Key 필요)
        # HttpPrivateSign includes ZK-signature order creation methods
        self.private_client = HttpPrivateSign(
            self.api_url,
            network_id=self.network_id,
            api_key_credentials={
                'key': self.api_key,
                'secret': self.api_secret,
                'passphrase': self.api_passphrase
            },
            zk_seeds=self.zk_seeds,
            zk_l2Key=self.zk_l2_key
        )

    def _load_credentials(self) -> Tuple[str, str, str]:
        """환경 변수에서 API 자격 증명 로드"""
        load_dotenv()

        key = os.getenv('APEX_API_KEY')
        secret = os.getenv('APEX_API_SECRET')
        passphrase = os.getenv('APEX_API_PASSPHRASE')

        if not all([key, secret, passphrase]):
            raise ValueError(
                ".env 파일에 다음 3개 항목이 필요합니다:\n"
                "- APEX_API_KEY\n"
                "- APEX_API_SECRET\n"
                "- APEX_API_PASSPHRASE"
            )

        return key, secret, passphrase

    def _load_omni_key(self) -> Tuple[Optional[str], Optional[str]]:
        """환경 변수에서 Omni Key 로드"""
        load_dotenv()

        zk_seeds = os.getenv('APEX_ZK_SEEDS')
        zk_l2_key = os.getenv('APEX_ZK_L2KEY')

        # Omni Key는 선택사항이지만 주문 생성에 필요
        if not zk_seeds or not zk_l2_key:
            print("[WARNING] Omni Key not configured - order placement may fail")
            print("  Get 'Omni Key Seed' from Apex Pro website and set:")
            print("  APEX_ZK_SEEDS=your-omni-key-seed")
            print("  APEX_ZK_L2KEY=your-omni-key-seed")
            return None, None

        return zk_seeds, zk_l2_key

    # ========== Public API Methods ==========

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        심볼의 현재가 정보 조회

        Args:
            symbol: 심볼 (예: 'BTC-USDT')

        Returns:
            티커 정보 딕셔너리 (lastPrice, markPrice, indexPrice 등)
        """
        try:
            result = self.public_client.ticker_v3(symbol=symbol)
            if result and 'data' in result and len(result['data']) > 0:
                return result['data'][0]
        except Exception as e:
            print(f"[WARNING] Ticker 조회 실패 ({symbol}): {e}")

        return None

    def get_market_configs(self) -> Optional[Dict]:
        """시장 설정 정보 조회"""
        try:
            return self.public_client.configs_v3()
        except Exception as e:
            print(f"[WARNING] Market configs 조회 실패: {e}")
            return None

    def get_depth(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """
        호가창 정보 조회 (Order Book Depth)

        Args:
            symbol: 심볼 (예: 'BTC-USDT')
            limit: 호가 개수 (기본값: 20)

        Returns:
            {'bids': [[price, size], ...], 'asks': [[price, size], ...]}
        """
        try:
            result = self.public_client.depth_v3(symbol=symbol, limit=limit)
            if result and 'data' in result:
                data = result['data']
                # Normalize API response: 'a' → 'asks', 'b' → 'bids'
                return {
                    'bids': data.get('b', []),
                    'asks': data.get('a', [])
                }
        except Exception as e:
            print(f"[WARNING] Depth 조회 실패 ({symbol}): {e}")
            return None

    # ========== Private API Methods ==========

    def get_account(self) -> Optional[Dict]:
        """
        계좌 정보 조회

        Returns:
            계좌 정보 (id, ethereumAddress, positions, contractWallets 등)
        """
        try:
            return self.private_client.get_account_v3()
        except Exception as e:
            print(f"[ERROR] 계좌 조회 실패: {e}")
            return None

    def get_account_balance(self) -> Optional[Dict]:
        """
        계좌 잔액 및 마진 정보 조회

        Returns:
            잔액 정보 (totalEquityValue, availableBalance, initialMargin 등)
        """
        try:
            return self.private_client.get_account_balance_v3()
        except Exception as e:
            print(f"[ERROR] 잔액 조회 실패: {e}")
            return None

    def get_open_orders(self) -> Optional[Dict]:
        """미체결 주문 조회"""
        try:
            return self.private_client.open_orders_v3()
        except Exception as e:
            print(f"[ERROR] 미체결 주문 조회 실패: {e}")
            return None

    def get_fills(self, limit: int = 100) -> Optional[Dict]:
        """
        체결 내역 조회

        Args:
            limit: 조회할 최대 개수 (기본값: 100)
        """
        try:
            return self.private_client.fills_v3(limit=limit)
        except Exception as e:
            print(f"[ERROR] 체결 내역 조회 실패: {e}")
            return None

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        size: str,
        price: Optional[str] = None,
        time_in_force: str = "GOOD_TIL_CANCEL",
        reduce_only: bool = False,
        client_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        주문 생성 (ZK-signature 포함)

        Args:
            symbol: 심볼 (예: 'ETHUSDT')
            side: 'BUY' or 'SELL'
            order_type: 'LIMIT', 'MARKET', 'LIMIT_MAKER'
            size: 주문 수량
            price: 주문 가격 (LIMIT 주문 시 필수)
            time_in_force: 'GOOD_TIL_CANCEL', 'IMMEDIATE_OR_CANCEL', 'FILL_OR_KILL', 'POST_ONLY'
            reduce_only: 포지션 감소만 허용
            client_id: 클라이언트 주문 ID (없으면 자동 생성)

        Returns:
            주문 생성 결과 딕셔너리 (id, status, clientOrderId 등)
        """
        try:
            # Ensure account and config are loaded (required by create_order_v3)
            if not hasattr(self.private_client, 'accountV3') or not self.private_client.accountV3:
                print("[INFO] Loading account info...")
                account_response = self.private_client.get_account_v3()
                # get_account_v3 returns the account data directly (no wrapper)
                self.private_client.accountV3 = account_response

            if not hasattr(self.private_client, 'configV3') or not self.private_client.configV3:
                print("[INFO] Loading market configs...")
                config_response = self.private_client.configs_v3()
                # configs_v3 returns {'data': {...}, ...}
                self.private_client.configV3 = config_response.get('data', {}) if config_response else {}

            # POST_ONLY는 timeInForce로 매핑
            if order_type == "LIMIT_MAKER":
                order_type = "LIMIT"
                time_in_force = "POST_ONLY"

            result = self.private_client.create_order_v3(
                symbol=symbol,
                side=side,
                type=order_type,
                size=size,
                price=price,
                timeInForce=time_in_force,
                reduceOnly=reduce_only,
                clientId=client_id
            )
            return result
        except Exception as e:
            print(f"[ERROR] 주문 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def cancel_order(self, order_id: str) -> Optional[Dict]:
        """
        주문 취소

        Args:
            order_id: 주문 ID 또는 클라이언트 주문 ID

        Returns:
            취소 결과 딕셔너리
        """
        try:
            # Try canceling by order ID first
            result = self.private_client.delete_order_v3(id=order_id)
            return result
        except Exception as e:
            print(f"[ERROR] 주문 취소 실패: {e}")
            return None

    # ========== 편의 메서드 ==========

    def get_active_positions(self) -> List[Dict]:
        """
        활성 포지션 목록 조회

        Returns:
            활성 포지션 리스트 (size > 0인 포지션만)
        """
        account = self.get_account()
        if not account:
            return []

        positions = account.get('positions', [])
        return [p for p in positions if float(p.get('size', '0')) > 0]

    def get_position_details(self) -> Dict:
        """
        포지션 상세 정보 조회 (청산가 계산 포함)

        Returns:
            {
                'positions': [...],
                'balance_info': {...},
                'ticker_info': {...}
            }
        """
        # 계좌 정보 조회
        account = self.get_account()
        if not account:
            return {'positions': [], 'balance_info': None, 'ticker_info': {}}

        # 활성 포지션
        positions = account.get('positions', [])
        active_positions = [p for p in positions if float(p.get('size', '0')) > 0]

        # 잔액 정보 (마진 정보 포함)
        balance_info = self.get_account_balance()

        # 현재가 조회
        ticker_info = {}
        if active_positions:
            active_symbols = list(set([p.get('symbol') for p in active_positions]))
            for symbol in active_symbols:
                ticker = self.get_ticker(symbol)
                if ticker:
                    ticker_info[symbol] = {
                        'lastPrice': float(ticker.get('lastPrice', 0)),
                        'indexPrice': float(ticker.get('indexPrice', 0)),
                        'markPrice': float(ticker.get('markPrice', 0))
                    }

        return {
            'positions': active_positions,
            'balance_info': balance_info,
            'ticker_info': ticker_info
        }

    def get_account_summary(self) -> Dict:
        """
        계좌 요약 정보 조회

        Returns:
            {
                'account_id': str,
                'ethereum_address': str,
                'taker_fee': float,
                'maker_fee': float,
                'usdt_balance': float,
                'total_equity': float,
                'available_balance': float,
                'unrealized_pnl': float
            }
        """
        account = self.get_account()
        balance_info = self.get_account_balance()

        if not account:
            return {}

        # 계좌 기본 정보
        summary = {
            'account_id': account.get('id', 'N/A'),
            'ethereum_address': account.get('ethereumAddress', 'N/A')
        }

        # 수수료 정보
        contract_account = account.get('contractAccount', {})
        summary['taker_fee'] = float(contract_account.get('takerFeeRate', 0))
        summary['maker_fee'] = float(contract_account.get('makerFeeRate', 0))

        # 잔액 정보
        contract_wallets = account.get('contractWallets', [])
        if contract_wallets:
            summary['usdt_balance'] = float(contract_wallets[0].get('balance', 0))

        # 마진 정보
        if balance_info and 'data' in balance_info:
            data = balance_info['data']
            summary['total_equity'] = float(data.get('totalEquityValue', 0))
            summary['available_balance'] = float(data.get('availableBalance', 0))
            summary['unrealized_pnl'] = float(data.get('unrealizedPnl', 0))
            summary['initial_margin'] = float(data.get('initialMargin', 0))
            summary['maintenance_margin'] = float(data.get('maintenanceMargin', 0))

        return summary

    def __repr__(self) -> str:
        return f"ApexClient(environment='{self.environment}', api_url='{self.api_url}')"
