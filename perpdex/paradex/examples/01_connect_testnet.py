"""
Paradex Testnet - 연결 테스트

이 스크립트는 Paradex Testnet에 연결하여 다음 정보를 조회합니다:
- 계좌 기본 정보 (Account ID, L1 Address)
- 마켓 리스트
- BTC-USD-PERP 현재가 및 펀딩비
- 계좌 잔액

필수 요구사항:
- .env 파일에 PARADEX_L1_ADDRESS, PARADEX_L1_PRIVATE_KEY 설정 필요
- paradex-py SDK 설치: pip install paradex-py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import paradex_client
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.paradex_client import ParadexClient


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("Paradex Testnet - 연결 테스트")
    print("=" * 60)

    # 1. 환경 변수 확인
    print("\n[1] 환경 변수 확인...")
    load_dotenv()

    l1Address = os.getenv('PARADEX_L1_ADDRESS')
    l1PrivateKey = os.getenv('PARADEX_L1_PRIVATE_KEY')

    if not all([l1Address, l1PrivateKey]):
        print("[ERROR] .env 파일에 다음 항목이 필요합니다:")
        print("  - PARADEX_L1_ADDRESS")
        print("  - PARADEX_L1_PRIVATE_KEY")
        return

    print(f"   > L1 Address: {l1Address[:6]}...{l1Address[-4:]}")
    print(f"   > L1 Private Key: [SECURED]")

    # 2. 클라이언트 초기화
    print("\n[2] Paradex Testnet 클라이언트 초기화...")
    try:
        client = ParadexClient(environment='testnet')
        print(f"   [OK] {client}")
    except Exception as e:
        print(f"[ERROR] 클라이언트 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 계좌 정보 조회
    print("\n[3] 계좌 정보 조회...")
    try:
        account = client.get_account()

        if not account:
            print("[ERROR] 계좌 조회 실패")
            return

        print(f"   [OK] API 인증 성공")
        print(f"\n   [계좌 정보]")
        print(f"   - Account ID: {account.get('account_id', 'N/A')}")
        print(f"   - L1 Address: {l1Address[:6]}...{l1Address[-4:]}")

    except Exception as e:
        print(f"[ERROR] 계좌 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. 마켓 리스트 조회
    print("\n[4] 마켓 리스트 조회...")
    try:
        markets = client.get_markets()

        if markets:
            print(f"   > 총 {len(markets)}개 마켓 발견")

            # BTC, ETH 관련 마켓만 표시
            btc_eth_markets = [
                m for m in markets
                if 'BTC' in m.get('symbol', '') or 'ETH' in m.get('symbol', '')
            ]

            print(f"\n   [주요 마켓]")
            for market in btc_eth_markets[:5]:
                symbol = market.get('symbol', 'N/A')
                base = market.get('base_currency', 'N/A')
                quote = market.get('quote_currency', 'N/A')
                print(f"   - {symbol} ({base}/{quote})")

    except Exception as e:
        print(f"[WARNING] 마켓 리스트 조회 실패: {e}")

    # 5. BTC-USD-PERP 현재가 조회
    print("\n[5] BTC-USD-PERP 현재가 조회...")
    try:
        ticker = client.get_ticker('BTC-USD-PERP')

        if ticker:
            last_price = ticker.get('last_price', 0)
            mark_price = ticker.get('mark_price', 0)
            index_price = ticker.get('index_price', 0)

            print(f"   - Last Price: ${float(last_price):,.2f}" if last_price else "   - Last Price: N/A")
            print(f"   - Mark Price: ${float(mark_price):,.2f}" if mark_price else "   - Mark Price: N/A")
            print(f"   - Index Price: ${float(index_price):,.2f}" if index_price else "   - Index Price: N/A")

    except Exception as e:
        print(f"[WARNING] 티커 조회 실패: {e}")

    # 6. 펀딩비 조회
    print("\n[6] BTC-USD-PERP 펀딩비 조회...")
    try:
        funding = client.get_funding_rate('BTC-USD-PERP')

        if funding:
            funding_rate = funding.get('funding_rate', 0)
            next_funding_time = funding.get('next_funding_time', 'N/A')

            print(f"   - Funding Rate: {float(funding_rate) * 100:.4f}%" if funding_rate else "   - Funding Rate: N/A")
            print(f"   - Next Funding Time: {next_funding_time}")

    except Exception as e:
        print(f"[WARNING] 펀딩비 조회 실패: {e}")

    # 7. 계좌 잔액 조회
    print("\n[7] 계좌 잔액 조회...")
    try:
        balances = client.get_balances()

        if balances:
            print(f"\n   [계좌 잔액]")
            for balance in balances:
                currency = balance.get('currency', 'N/A')
                equity = balance.get('equity', '0')
                available = balance.get('available', '0')
                locked = balance.get('locked', '0')

                print(f"   - {currency}:")
                print(f"      Total Equity: {equity}")
                print(f"      Available: {available}")
                print(f"      Locked (Margin): {locked}")

    except Exception as e:
        print(f"[WARNING] 잔액 조회 실패: {e}")

    # 8. 계좌 요약 정보
    print("\n[8] 계좌 요약...")
    try:
        summary = client.get_account_summary()

        if summary:
            print(f"\n   [계좌 요약]")
            print(f"   - Environment: {summary.get('environment', 'N/A')}")
            print(f"   - Total Equity: {summary.get('total_equity', 0):,.6f} USD")
            print(f"   - Available Balance: {summary.get('available_balance', 0):,.6f} USD")
            print(f"   - Used Margin: {summary.get('used_margin', 0):,.6f} USD")
            print(f"   - Unrealized PnL: {summary.get('unrealized_pnl', 0):+,.6f} USD")

    except Exception as e:
        print(f"[WARNING] 계좌 요약 조회 실패: {e}")

    print("\n" + "=" * 60)
    print("연결 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
