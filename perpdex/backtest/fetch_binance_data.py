"""
Binance에서 BTC-USDT 1분봉 데이터 수집

Binance Public REST API 사용 (API 키 불필요)
"""

import requests
import time
import csv
from datetime import datetime, timedelta
from pathlib import Path


def fetchBinanceKlines(
    symbol: str = "BTCUSDT",
    interval: str = "1m",
    startTime: int = None,
    endTime: int = None,
    limit: int = 1000
) -> list:
    """
    Binance Klines (캔들) 데이터 가져오기

    Args:
        symbol: 거래 페어 (기본 BTCUSDT)
        interval: 시간 간격 (1m, 5m, 15m, 1h 등)
        startTime: 시작 타임스탬프 (밀리초)
        endTime: 종료 타임스탬프 (밀리초)
        limit: 최대 개수 (최대 1000)

    Returns:
        캔들 데이터 리스트
    """
    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    if startTime:
        params['startTime'] = startTime
    if endTime:
        params['endTime'] = endTime

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Binance API request failed: {e}")
        return []


def convertKlinesToCandles(klines: list) -> list:
    """
    Binance Klines 형식 → 캔들 데이터 변환

    Binance Klines 형식:
    [
      openTime, open, high, low, close, volume,
      closeTime, quoteVolume, trades, takerBuyBase, takerBuyQuote, ignore
    ]

    Args:
        klines: Binance klines 데이터

    Returns:
        캔들 데이터 리스트
    """
    candles = []

    for kline in klines:
        candle = {
            'timestamp': int(kline[0] // 1000),  # 밀리초 → 초
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5])
        }
        candles.append(candle)

    return candles


def fetchHistoricalData(
    symbol: str = "BTCUSDT",
    days: int = 30,
    interval: str = "1m"
) -> list:
    """
    과거 데이터 수집 (여러 번 API 호출)

    Args:
        symbol: 거래 페어
        days: 수집할 일수
        interval: 시간 간격

    Returns:
        전체 캔들 데이터
    """
    print(f"[FETCH] Fetching {days} days of {symbol} {interval} data from Binance...")

    # 종료 시간: 현재
    endTime = int(time.time() * 1000)

    # 시작 시간: days일 전
    startTime = endTime - (days * 24 * 60 * 60 * 1000)

    allCandles = []
    currentStart = startTime

    # 1분봉 기준 1000개 = 약 16.7시간
    # 30일 = 43,200분 → 약 44번 요청 필요
    batchCount = 0

    while currentStart < endTime:
        batchCount += 1
        print(f"   [BATCH {batchCount}] Fetching from {datetime.fromtimestamp(currentStart / 1000).strftime('%Y-%m-%d %H:%M:%S')}...")

        klines = fetchBinanceKlines(
            symbol=symbol,
            interval=interval,
            startTime=currentStart,
            endTime=endTime,
            limit=1000
        )

        if not klines:
            print(f"   [WARNING] No data returned, stopping")
            break

        # 변환
        candles = convertKlinesToCandles(klines)
        allCandles.extend(candles)

        # 다음 배치 시작 시간 (마지막 캔들 종료 시간 + 1ms)
        currentStart = klines[-1][6] + 1

        # Rate limit 방지 (1초에 최대 1200 요청, 우리는 여유있게)
        time.sleep(0.5)

        print(f"   [OK] Got {len(candles)} candles, total: {len(allCandles)}")

    print(f"\n[DONE] Total {len(allCandles)} candles fetched")
    return allCandles


def saveToCsv(candles: list, filePath: str) -> None:
    """
    캔들 데이터를 CSV 파일로 저장

    Args:
        candles: 캔들 데이터 리스트
        filePath: 저장 경로
    """
    # 디렉토리 생성
    Path(filePath).parent.mkdir(parents=True, exist_ok=True)

    with open(filePath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        writer.writeheader()
        writer.writerows(candles)

    print(f"[SAVE] Saved to {filePath}")


def main():
    """메인 함수"""
    print("[START] Binance Data Fetcher")
    print("=" * 60)

    # 설정
    symbol = "BTCUSDT"
    days = 30  # 30일 데이터
    interval = "1m"
    outputPath = "backtest/data/binance_btc_1m_30days.csv"

    # 데이터 수집
    candles = fetchHistoricalData(
        symbol=symbol,
        days=days,
        interval=interval
    )

    if not candles:
        print("[ERROR] No data fetched!")
        return

    # CSV 저장
    saveToCsv(candles, outputPath)

    # 통계
    print("\n" + "=" * 60)
    print("[STATS]")
    print(f"   Total candles: {len(candles)}")
    print(f"   Start time: {datetime.fromtimestamp(candles[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End time: {datetime.fromtimestamp(candles[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   First price: ${candles[0]['close']:,.2f}")
    print(f"   Last price: ${candles[-1]['close']:,.2f}")
    print(f"   Price change: {((candles[-1]['close'] - candles[0]['close']) / candles[0]['close']) * 100:+.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
