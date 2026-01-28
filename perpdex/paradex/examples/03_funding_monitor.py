"""
Paradex + ApeX 펀딩비 모니터링 및 차익거래 기회 탐지

이 스크립트는 다음을 수행합니다:
- Paradex와 ApeX의 BTC-USDT 펀딩비 실시간 조회
- 펀딩비 차이 계산 및 차익거래 기회 탐지
- 델타 뉴트럴 전략 수익성 분석
- JIT 전략 타이밍 표시

필수 요구사항:
- .env 파일에 Paradex 및 ApeX API 자격 증명 설정 필요
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apex'))

from lib.paradex_client import ParadexClient

# ApeX 클라이언트 import 시도
try:
    from lib.apex_client import ApexClient
    APEX_AVAILABLE = True
except ImportError:
    print("[WARNING] ApeX 클라이언트를 찾을 수 없습니다. Paradex 단독 모니터링 모드로 실행합니다.")
    APEX_AVAILABLE = False


def get_next_funding_times():
    """
    다음 3개 펀딩비 지급 시각 계산 (UTC 기준)

    펀딩비는 00:00, 08:00, 16:00 UTC에 지급됩니다.

    Returns:
        다음 3개 펀딩비 지급 시각 리스트
    """
    now = datetime.now(timezone.utc)
    current_hour = now.hour

    # 다음 펀딩비 시각 결정
    funding_hours = [0, 8, 16]

    next_funding_times = []
    for hour in funding_hours:
        if current_hour < hour:
            # 오늘
            next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        else:
            # 다음날
            from datetime import timedelta
            next_time = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)

        next_funding_times.append(next_time)

    # 가장 가까운 3개만 반환
    next_funding_times.sort()
    return next_funding_times[:3]


def format_funding_time(dt):
    """
    펀딩비 시각을 읽기 쉽게 포맷

    Args:
        dt: datetime 객체 (UTC)

    Returns:
        포맷된 시각 문자열 (KST 포함)
    """
    from datetime import timedelta

    utc_str = dt.strftime('%H:%M UTC')
    kst_time = dt + timedelta(hours=9)
    kst_str = kst_time.strftime('%H:%M KST')

    return f"{utc_str} ({kst_str})"


def calculate_arbitrage_profit(
    funding_diff,
    position_size,
    maker_rebate_rate=0.00005
):
    """
    차익거래 예상 수익 계산

    Args:
        funding_diff: 펀딩비 차이 (소수점, 예: 0.0001 = 0.01%)
        position_size: 포지션 크기 (USD)
        maker_rebate_rate: Maker Rebate 비율 (기본값: 0.005%)

    Returns:
        예상 순이익 (USD)
    """
    # 펀딩비 차익
    funding_profit = position_size * funding_diff

    # Maker Rebate (왕복)
    # ApeX: 0% Maker, Paradex: -0.005% Maker
    # 총 리베이트: position_size * 0.00005 * 2 (진입 + 청산)
    maker_rebate = position_size * maker_rebate_rate * 2

    # 총 순이익
    net_profit = funding_profit + maker_rebate

    return net_profit, funding_profit, maker_rebate


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("Paradex + ApeX 펀딩비 모니터링 및 차익거래 기회 탐지")
    print("=" * 80)

    # 1. 클라이언트 초기화
    print("\n[1] API 클라이언트 초기화...")

    # Paradex 클라이언트
    try:
        paradex_client = ParadexClient(environment='testnet')
        print(f"   ✅ Paradex Testnet: {paradex_client}")
    except Exception as e:
        print(f"   ❌ Paradex 초기화 실패: {e}")
        return

    # ApeX 클라이언트 (선택적)
    apex_client = None
    if APEX_AVAILABLE:
        try:
            apex_client = ApexClient(environment='mainnet')
            print(f"   ✅ ApeX Mainnet: {apex_client}")
        except Exception as e:
            print(f"   ⚠️ ApeX 초기화 실패 (Paradex 단독 모니터링 모드): {e}")

    # 2. 다음 펀딩비 지급 시각 표시
    print("\n[2] 다음 펀딩비 지급 스케줄 (JIT 전략 타이밍)...")
    funding_times = get_next_funding_times()

    for i, ft in enumerate(funding_times, 1):
        formatted_time = format_funding_time(ft)
        print(f"   {i}. {formatted_time}")

    # 3. 실시간 펀딩비 모니터링 루프
    print("\n[3] 펀딩비 실시간 모니터링 시작... (Ctrl+C로 종료)")
    print("-" * 80)

    try:
        while True:
            current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"\n[{current_time}]")

            # Paradex 펀딩비 조회
            paradex_funding = None
            try:
                funding_data = paradex_client.get_funding_rate('BTC-USD-PERP')
                if funding_data:
                    paradex_funding = float(funding_data.get('funding_rate', 0))
                    print(f"   Paradex Funding Rate: {paradex_funding * 100:+.4f}%")
            except Exception as e:
                print(f"   ⚠️ Paradex 펀딩비 조회 실패: {e}")

            # ApeX 펀딩비 조회
            apex_funding = None
            if apex_client:
                try:
                    ticker_data = apex_client.get_ticker('BTC-USDT')
                    if ticker_data:
                        apex_funding = float(ticker_data.get('fundingRate', 0))
                        print(f"   ApeX Funding Rate:    {apex_funding * 100:+.4f}%")
                except Exception as e:
                    print(f"   ⚠️ ApeX 펀딩비 조회 실패: {e}")

            # 차익거래 기회 분석
            if paradex_funding is not None and apex_funding is not None:
                funding_diff = apex_funding - paradex_funding

                print(f"\n   📊 차익거래 분석")
                print(f"   - Funding Difference: {funding_diff * 100:+.4f}%")

                # 예상 수익 계산 ($10,000 포지션 기준)
                position_size = 10000
                net_profit, funding_profit, maker_rebate = calculate_arbitrage_profit(
                    funding_diff, position_size
                )

                print(f"\n   💰 예상 수익 (포지션 $10,000 기준)")
                print(f"   - Funding 차익:  ${funding_profit:+.6f}")
                print(f"   - Maker Rebate:  ${maker_rebate:+.6f}")
                print(f"   - 총 순이익:     ${net_profit:+.6f}")

                # 차익거래 기회 판단
                min_threshold = 0.00  # 최소 0% 차이만 있어도 수익 가능 (Maker Rebate 덕분)

                if funding_diff > min_threshold:
                    print(f"\n   🎯 차익거래 기회 발견!")
                    print(f"   - 전략: ApeX LONG + Paradex SHORT")
                    print(f"   - 이유: ApeX 펀딩비가 더 높음 (LONG 포지션이 펀딩비 수령)")
                elif funding_diff < -min_threshold:
                    print(f"\n   🎯 차익거래 기회 발견!")
                    print(f"   - 전략: ApeX SHORT + Paradex LONG")
                    print(f"   - 이유: Paradex 펀딩비가 더 높음 (LONG 포지션이 펀딩비 수령)")
                else:
                    print(f"\n   ⏳ 대기: 펀딩비 차이가 작아 Maker Rebate만으로 수익")

            print("-" * 80)

            # 10초마다 갱신
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n[종료] 사용자가 모니터링을 중단했습니다.")

    print("\n" + "=" * 80)
    print("펀딩비 모니터링 종료")
    print("=" * 80)


if __name__ == "__main__":
    main()
