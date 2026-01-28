"""
과거 데이터 로딩

CSV 파일 또는 API에서 1분봉 캔들 데이터 로드
"""

import csv
from typing import List, Dict, Optional
from datetime import datetime
import os


def loadCsvData(filePath: str) -> List[Dict]:
    """
    CSV 파일에서 캔들 데이터 로드

    CSV 형식:
    timestamp,open,high,low,close,volume

    Args:
        filePath: CSV 파일 경로

    Returns:
        캔들 데이터 리스트 [{timestamp, open, high, low, close, volume}, ...]

    Raises:
        FileNotFoundError: 파일이 없는 경우
        ValueError: 잘못된 CSV 형식
    """
    if not os.path.exists(filePath):
        raise FileNotFoundError(f"File not found: {filePath}")

    candles = []

    with open(filePath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                candle = {
                    'timestamp': int(row['timestamp']),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                }
                candles.append(candle)
            except (KeyError, ValueError) as e:
                raise ValueError(f"Invalid CSV format: {e}")

    if not candles:
        raise ValueError("Empty CSV file")

    # 타임스탬프 순으로 정렬
    candles.sort(key=lambda x: x['timestamp'])

    return candles


def filterByTimeRange(
    candles: List[Dict],
    startTimestamp: Optional[int] = None,
    endTimestamp: Optional[int] = None
) -> List[Dict]:
    """
    시간 범위로 캔들 데이터 필터링

    Args:
        candles: 캔들 데이터 리스트
        startTimestamp: 시작 타임스탬프 (None이면 제한 없음)
        endTimestamp: 종료 타임스탬프 (None이면 제한 없음)

    Returns:
        필터링된 캔들 데이터
    """
    filtered = candles

    if startTimestamp is not None:
        filtered = [c for c in filtered if c['timestamp'] >= startTimestamp]

    if endTimestamp is not None:
        filtered = [c for c in filtered if c['timestamp'] <= endTimestamp]

    return filtered


def resampleCandles(
    candles: List[Dict],
    targetInterval: int = 60
) -> List[Dict]:
    """
    캔들 데이터를 다른 시간 간격으로 리샘플링

    Args:
        candles: 1분봉 캔들 데이터
        targetInterval: 목표 시간 간격 (초, 기본 60 = 1분)

    Returns:
        리샘플링된 캔들 데이터
    """
    if targetInterval == 60:
        return candles  # 이미 1분봉

    resampled = []
    currentBucket = []
    bucketStart = None

    for candle in candles:
        if bucketStart is None:
            bucketStart = candle['timestamp'] // targetInterval * targetInterval

        # 현재 캔들이 버킷에 속하는지 확인
        candleBucket = candle['timestamp'] // targetInterval * targetInterval

        if candleBucket == bucketStart:
            currentBucket.append(candle)
        else:
            # 버킷 완성 → 새로운 캔들 생성
            if currentBucket:
                newCandle = {
                    'timestamp': bucketStart,
                    'open': currentBucket[0]['open'],
                    'high': max(c['high'] for c in currentBucket),
                    'low': min(c['low'] for c in currentBucket),
                    'close': currentBucket[-1]['close'],
                    'volume': sum(c['volume'] for c in currentBucket)
                }
                resampled.append(newCandle)

            # 새 버킷 시작
            currentBucket = [candle]
            bucketStart = candleBucket

    # 마지막 버킷 처리
    if currentBucket:
        newCandle = {
            'timestamp': bucketStart,
            'open': currentBucket[0]['open'],
            'high': max(c['high'] for c in currentBucket),
            'low': min(c['low'] for c in currentBucket),
            'close': currentBucket[-1]['close'],
            'volume': sum(c['volume'] for c in currentBucket)
        }
        resampled.append(newCandle)

    return resampled


def createMockData(
    startPrice: float = 94000.0,
    numCandles: int = 10000,
    volatility: float = 0.002
) -> List[Dict]:
    """
    테스트용 모의 캔들 데이터 생성

    Args:
        startPrice: 시작 가격
        numCandles: 생성할 캔들 수
        volatility: 변동성 (기본 0.2%)

    Returns:
        모의 캔들 데이터
    """
    import random

    candles = []
    currentPrice = startPrice
    timestamp = 1704067200  # 2024-01-01 00:00:00 (UTC)

    for i in range(numCandles):
        # 랜덤 가격 변동
        priceChange = currentPrice * random.uniform(-volatility, volatility)
        openPrice = currentPrice
        closePrice = currentPrice + priceChange

        # High/Low 계산
        highPrice = max(openPrice, closePrice) * (1 + random.uniform(0, volatility / 2))
        lowPrice = min(openPrice, closePrice) * (1 - random.uniform(0, volatility / 2))

        # 거래량 (랜덤)
        volume = random.uniform(10, 100)

        candle = {
            'timestamp': timestamp,
            'open': round(openPrice, 2),
            'high': round(highPrice, 2),
            'low': round(lowPrice, 2),
            'close': round(closePrice, 2),
            'volume': round(volume, 4)
        }
        candles.append(candle)

        # 다음 캔들
        currentPrice = closePrice
        timestamp += 60  # 1분 증가

    return candles


def saveCsvData(candles: List[Dict], filePath: str) -> None:
    """
    캔들 데이터를 CSV 파일로 저장

    Args:
        candles: 캔들 데이터 리스트
        filePath: 저장할 CSV 파일 경로
    """
    with open(filePath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        writer.writeheader()
        writer.writerows(candles)

    print(f"Saved {len(candles)} candles to {filePath}")
