"""
Paradex Testnet - 주문 테스트 (Maker Rebate 검증)

이 스크립트는 Paradex Testnet에서 다음을 테스트합니다:
- Limit 주문 생성 (POST_ONLY로 Maker 수수료 보장)
- 주문 체결 확인
- Maker Rebate -0.005% 실제 적용 확인
- 포지션 청산

**중요**: Maker Rebate가 실제로 적용되는지 확인하는 것이 핵심!

필수 요구사항:
- .env 파일에 PARADEX_L1_ADDRESS, PARADEX_L1_PRIVATE_KEY 설정 필요
- Testnet 계좌에 충분한 잔액 필요
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.paradex_client import ParadexClient


def wait_for_order_fill(client, order_id, timeout=60):
    """
    주문 체결 대기

    Args:
        client: ParadexClient 인스턴스
        order_id: 주문 ID
        timeout: 타임아웃 (초)

    Returns:
        체결된 주문 정보 또는 None
    """
    print(f"   > 주문 체결 대기 중... (최대 {timeout}초)")

    start_time = time.time()
    while time.time() - start_time < timeout:
        # 주문 내역 조회
        orders = client.get_order_history(limit=10)

        if orders:
            for order in orders:
                if order.get('id') == order_id:
                    status = order.get('status')
                    print(f"      [{time.strftime('%H:%M:%S')}] 주문 상태: {status}")

                    if status in ['FILLED', 'PARTIALLY_FILLED']:
                        return order

        time.sleep(2)

    print("   [WARNING] 타임아웃: 주문이 체결되지 않았습니다.")
    return None


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("Paradex Testnet - 주문 테스트 (Maker Rebate 검증)")
    print("=" * 60)

    # 1. 클라이언트 초기화
    print("\n[1] Paradex Testnet 클라이언트 초기화...")
    try:
        client = ParadexClient(environment='testnet')
        print(f"   [OK] {client}")
    except Exception as e:
        print(f"[ERROR] 클라이언트 초기화 실패: {e}")
        return

    # 2. 계좌 잔액 확인
    print("\n[2] 계좌 잔액 확인...")
    try:
        summary = client.get_account_summary()

        if not summary:
            print("[ERROR] 계좌 조회 실패")
            return

        available = summary.get('available_balance', 0)
        print(f"   - Available Balance: {available:,.6f} USD")

        if available < 100:
            print("[WARNING] 잔액이 부족합니다. Testnet에서 테스트용 자금을 받으세요.")
            print("   Paradex Testnet Faucet: https://testnet.paradex.trade/faucet")
            return

    except Exception as e:
        print(f"[ERROR] 잔액 확인 실패: {e}")
        return

    # 3. 현재가 조회
    print("\n[3] BTC-USD-PERP 현재가 조회...")
    try:
        ticker = client.get_ticker('BTC-USD-PERP')

        if not ticker:
            print("[ERROR] 티커 조회 실패")
            return

        last_price = float(ticker.get('last_price', 0))
        mark_price = float(ticker.get('mark_price', 0))

        current_price = mark_price if mark_price > 0 else last_price

        print(f"   - Current Price: ${current_price:,.2f}")

    except Exception as e:
        print(f"[ERROR] 티커 조회 실패: {e}")
        return

    # 4. LONG 포지션 오픈 (POST_ONLY로 Maker 수수료 보장)
    print("\n[4] LONG 포지션 오픈 (Maker Rebate 테스트)...")

    # 진입가 설정: 현재가보다 0.1% 낮게 설정하여 Maker 주문 보장
    entry_price = current_price * 0.999
    position_size = "0.001"  # 0.001 BTC (최소 테스트)

    print(f"   - Size: {position_size} BTC")
    print(f"   - Entry Price: ${entry_price:,.2f} (현재가 대비 -0.1%)")
    print(f"   - Type: LIMIT (POST_ONLY)")
    print(f"   - Expected Maker Rebate: -0.005%")

    try:
        # LONG 주문 생성
        order = client.create_order(
            market='BTC-USD-PERP',
            side='BUY',
            order_type='LIMIT',
            size=position_size,
            price=str(entry_price),
            post_only=True,  # Maker 수수료 보장
            reduce_only=False
        )

        if not order:
            print("[ERROR] 주문 생성 실패")
            return

        order_id = order.get('id', 'N/A')
        print(f"\n   [OK] LONG 주문 생성 성공")
        print(f"   - Order ID: {order_id}")
        print(f"   - Status: {order.get('status', 'N/A')}")

    except Exception as e:
        print(f"[ERROR] 주문 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 주문 체결 대기
    print("\n[5] 주문 체결 확인...")
    filled_order = wait_for_order_fill(client, order_id, timeout=60)

    if not filled_order:
        print("[WARNING] 주문이 체결되지 않았습니다. 주문을 취소합니다.")
        try:
            client.cancel_order(order_id)
            print("   [OK] 주문 취소 완료")
        except Exception as e:
            print(f"[ERROR] 주문 취소 실패: {e}")
        return

    # 6. Maker Rebate 확인
    print("\n[6] Maker Rebate 확인...")
    try:
        fill_price = float(filled_order.get('fill_price', 0))
        filled_size = float(filled_order.get('filled_size', 0))
        fee = float(filled_order.get('fee', 0))

        position_value = fill_price * filled_size

        print(f"   - Fill Price: ${fill_price:,.2f}")
        print(f"   - Filled Size: {filled_size} BTC")
        print(f"   - Position Value: ${position_value:,.2f}")
        print(f"   - Fee: {fee:+.6f} USD")

        # Maker Rebate 계산
        expected_rebate = position_value * -0.00005  # -0.005%

        print(f"\n   [Maker Rebate 검증]")
        print(f"   - Expected Rebate: {expected_rebate:+.6f} USD")
        print(f"   - Actual Fee: {fee:+.6f} USD")

        if fee < 0:
            print(f"   ✅ Maker Rebate 적용 확인! (리베이트 수령)")
        else:
            print(f"   ⚠️ Taker 수수료 발생 (Maker 미적용)")

    except Exception as e:
        print(f"[WARNING] 수수료 확인 실패: {e}")

    # 7. 포지션 확인
    print("\n[7] 포지션 확인...")
    try:
        positions = client.get_active_positions()

        if not positions:
            print("   [INFO] 활성 포지션 없음")
        else:
            for pos in positions:
                symbol = pos.get('market', 'N/A')
                side = pos.get('side', 'N/A')
                size = pos.get('size', '0')
                entry = pos.get('entry_price', '0')

                print(f"   - {symbol} {side} {size} BTC @ ${float(entry):,.2f}")

    except Exception as e:
        print(f"[WARNING] 포지션 조회 실패: {e}")

    # 8. 포지션 청산 (Take-Profit 주문)
    print("\n[8] 포지션 청산 (Maker 주문으로 청산)...")

    # TP 가격 설정: 진입가 대비 +0.2% 상승
    tp_price = fill_price * 1.002

    print(f"   - TP Price: ${tp_price:,.2f} (+0.2%)")
    print(f"   - Expected Profit: ${(tp_price - fill_price) * filled_size:.6f} USD")

    try:
        # SELL 주문 생성 (포지션 청산)
        close_order = client.create_order(
            market='BTC-USD-PERP',
            side='SELL',
            order_type='LIMIT',
            size=position_size,
            price=str(tp_price),
            post_only=True,  # Maker 수수료 보장
            reduce_only=True  # 포지션 청산 전용
        )

        if not close_order:
            print("[ERROR] 청산 주문 생성 실패")
            return

        close_order_id = close_order.get('id', 'N/A')
        print(f"\n   [OK] 청산 주문 생성 성공")
        print(f"   - Order ID: {close_order_id}")
        print(f"   - Type: LIMIT (POST_ONLY, REDUCE_ONLY)")

    except Exception as e:
        print(f"[ERROR] 청산 주문 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 9. 청산 주문 체결 대기 (옵션)
    print("\n[9] 청산 주문 체결 대기 (30초)...")
    close_filled = wait_for_order_fill(client, close_order_id, timeout=30)

    if close_filled:
        print(f"   ✅ 청산 주문 체결 완료!")

        close_fee = float(close_filled.get('fee', 0))
        print(f"   - Close Fee: {close_fee:+.6f} USD")

        if close_fee < 0:
            print(f"   ✅ 청산에서도 Maker Rebate 수령!")

        # 총 손익 계산
        total_profit = (tp_price - fill_price) * filled_size
        total_rebate = abs(fee) + abs(close_fee) if (fee < 0 and close_fee < 0) else 0
        net_profit = total_profit + total_rebate

        print(f"\n   [거래 요약]")
        print(f"   - 가격 차익: ${total_profit:+.6f} USD")
        print(f"   - Maker Rebate (왕복): ${total_rebate:+.6f} USD")
        print(f"   - 순이익: ${net_profit:+.6f} USD")

    else:
        print(f"   ⏳ 청산 주문 미체결 (주문은 활성 상태로 유지)")
        print(f"   - 나중에 수동으로 취소하거나 체결 대기")

    print("\n" + "=" * 60)
    print("주문 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
