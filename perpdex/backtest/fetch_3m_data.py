"""
Fetch 3-minute BTC data from Binance
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def fetchBinance3mData(symbol='BTCUSDT', days=30):
    """
    Fetch 3-minute candlestick data from Binance

    Args:
        symbol: Trading pair (default BTCUSDT)
        days: Number of days to fetch (default 30)

    Returns:
        List of candle dictionaries
    """
    url = 'https://api.binance.com/api/v3/klines'

    # 3-minute interval
    interval = '3m'
    limit = 500  # Max per request

    # Calculate timestamps
    endTime = int(datetime.now().timestamp() * 1000)
    startTime = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    allCandles = []
    currentStart = startTime

    print(f"[FETCH] Getting {days} days of 3-minute {symbol} data...")
    print(f"   Start: {datetime.fromtimestamp(startTime/1000)}")
    print(f"   End: {datetime.fromtimestamp(endTime/1000)}")

    requestCount = 0
    while currentStart < endTime:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': currentStart,
            'endTime': endTime,
            'limit': limit
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            allCandles.extend(data)
            requestCount += 1

            # Update start time for next batch
            lastTimestamp = data[-1][0]
            if lastTimestamp >= endTime or lastTimestamp <= currentStart:
                break
            currentStart = lastTimestamp + 1

            # Rate limit
            time.sleep(0.1)

            if requestCount % 5 == 0:
                print(f"   Fetched {len(allCandles)} candles...")

        except Exception as e:
            print(f"[ERROR] Failed to fetch data: {e}")
            break

    print(f"[OK] Total candles fetched: {len(allCandles)}")

    # Convert to our format
    formattedCandles = []
    for candle in allCandles:
        formattedCandles.append({
            'timestamp': int(candle[0] / 1000),  # Convert to seconds
            'open': float(candle[1]),
            'high': float(candle[2]),
            'low': float(candle[3]),
            'close': float(candle[4]),
            'volume': float(candle[5])
        })

    return formattedCandles


def saveToCSV(candles, filename):
    """Save candles to CSV file"""
    df = pd.DataFrame(candles)
    df.to_csv(filename, index=False)
    print(f"[SAVE] Data saved to {filename}")

    # Print statistics
    if len(candles) > 0:
        startDate = datetime.fromtimestamp(candles[0]['timestamp'])
        endDate = datetime.fromtimestamp(candles[-1]['timestamp'])
        priceRange = (
            min(c['low'] for c in candles),
            max(c['high'] for c in candles)
        )

        print(f"\n[STATS] 3-Minute Data Summary:")
        print(f"   Period: {startDate} to {endDate}")
        print(f"   Candles: {len(candles)}")
        print(f"   Price range: ${priceRange[0]:,.2f} - ${priceRange[1]:,.2f}")
        print(f"   File size: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")


def main():
    """Main function"""
    print("\n" + "="*60)
    print("[START] Fetching 3-minute BTC data from Binance")
    print("="*60)

    # Fetch 30 days of 3-minute data
    candles = fetchBinance3mData('BTCUSDT', days=30)

    if candles:
        # Save to CSV
        filename = 'backtest/data/binance_btc_3m_30days.csv'
        saveToCSV(candles, filename)

        # Also save to archive
        archiveFilename = 'backtest/data/archive/binance_btc_3m_30days.csv'
        saveToCSV(candles, archiveFilename)

        print("\n[SUCCESS] 3-minute data fetched and saved!")
    else:
        print("\n[ERROR] Failed to fetch data")

    print("="*60 + "\n")


if __name__ == "__main__":
    main()