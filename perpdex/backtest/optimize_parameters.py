"""
파라미터 최적화 스크립트

그리드 서치를 통해 최적 MA, RSI 파라미터 찾기

사용법:
    python backtest/optimize_parameters.py --data btc_1m.csv
"""

import sys
from pathlib import Path
import argparse
import json
from typing import List, Dict, Tuple
import itertools

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.data_loader import loadCsvData, createMockData
from backtest.strategies.ma_rsi_strategy import runBacktest


# 파라미터 그리드 정의
MA_PERIODS_GRID = [
    (3, 7, 15),   # 빠른 반응
    (5, 10, 20),  # 표준 (추천)
    (7, 14, 30),  # 중간
    (10, 20, 50)  # 느린 반응
]

RSI_PERIODS_GRID = [9, 14, 21]

RSI_THRESHOLDS_GRID = [
    (25, 45),  # 매우 보수적
    (30, 45),  # 보수적
    (30, 50),  # 표준 (사용자 제안)
    (35, 55),  # 완화
]


def parseArgs():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description='MA+RSI 파라미터 최적화')

    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='CSV 데이터 파일 경로 (없으면 모의 데이터 사용)'
    )

    parser.add_argument(
        '--equity',
        type=float,
        default=5000.0,
        help='초기 자본 (USD, 기본 5000)'
    )

    parser.add_argument(
        '--leverage',
        type=int,
        default=10,
        help='레버리지 (기본 10)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='backtest/results/optimization_results.json',
        help='결과 저장 경로 (JSON)'
    )

    parser.add_argument(
        '--metric',
        type=str,
        default='sharpe',
        choices=['sharpe', 'winrate', 'profit', 'trades'],
        help='최적화 지표 (기본 sharpe)'
    )

    return parser.parse_args()


def evaluateParams(
    candles: List[Dict],
    maPeriods: Tuple[int, int, int],
    rsiPeriod: int,
    rsiThreshold: Tuple[int, int],
    initialEquity: float,
    leverage: int
) -> Dict:
    """
    파라미터 조합 평가

    Args:
        candles: 캔들 데이터
        maPeriods: MA 기간
        rsiPeriod: RSI 기간
        rsiThreshold: RSI 임계값
        initialEquity: 초기 자본
        leverage: 레버리지

    Returns:
        백테스팅 결과
    """
    try:
        results = runBacktest(
            candles=candles,
            maPeriods=maPeriods,
            rsiPeriod=rsiPeriod,
            rsiThreshold=rsiThreshold,
            initialEquity=initialEquity,
            leverage=leverage
        )
        return results
    except Exception as e:
        print(f"   [ERROR] {e}")
        return None


def calculateScore(results: Dict, metric: str) -> float:
    """
    결과를 점수로 변환

    Args:
        results: 백테스팅 결과
        metric: 평가 지표

    Returns:
        점수 (높을수록 좋음)
    """
    if results is None:
        return -999999.0

    if metric == 'sharpe':
        return results['sharpeRatio']
    elif metric == 'winrate':
        return results['winRate']
    elif metric == 'profit':
        return results['returnRate']
    elif metric == 'trades':
        return results['tradesPerDay']

    return 0.0


def printTopResults(
    allResults: List[Dict],
    metric: str,
    top: int = 5
) -> None:
    """
    상위 결과 출력

    Args:
        allResults: 모든 결과 리스트
        metric: 평가 지표
        top: 상위 몇 개
    """
    # 점수 기준 정렬
    sorted_results = sorted(
        allResults,
        key=lambda x: calculateScore(x, metric),
        reverse=True
    )

    print(f"\n[TOP] Top {top} parameter combinations (by {metric}):")
    print("=" * 80)

    for i, result in enumerate(sorted_results[:top], 1):
        params = result['parameters']
        score = calculateScore(result, metric)

        print(f"\n{i}. {metric.upper()}: {score:.4f}")
        print(f"   MA: {params['maPeriods']}")
        print(f"   RSI: {params['rsiPeriod']}")
        print(f"   RSI 임계값: {params['rsiThreshold']}")
        print(f"   승률: {result['winRate'] * 100:.2f}%")
        print(f"   하루 거래: {result['tradesPerDay']:.1f}회")
        print(f"   수익률: {result['returnRate'] * 100:+.2f}%")
        print(f"   Sharpe: {result['sharpeRatio']:.3f}")
        print(f"   낙폭: {result['maxDrawdown'] * 100:.2f}%")


def main():
    """메인 함수"""
    args = parseArgs()

    print(f"\n[OPTIMIZE] Parameter optimization starting...")
    print(f"   Optimization metric: {args.metric.upper()}")

    # 데이터 로드
    if args.data:
        print(f"\n[DATA] Loading: {args.data}")
        candles = loadCsvData(args.data)
    else:
        print(f"\n[DATA] Generating mock data...")
        candles = createMockData(
            startPrice=94000.0,
            numCandles=43200,  # 30일
            volatility=0.002
        )

    print(f"   [OK] {len(candles)} candles ready")

    # 그리드 서치
    totalCombinations = (
        len(MA_PERIODS_GRID) *
        len(RSI_PERIODS_GRID) *
        len(RSI_THRESHOLDS_GRID)
    )

    print(f"\n[RUN] Grid search: {totalCombinations} combinations")
    print("=" * 80)

    allResults = []
    completed = 0

    for maPeriods, rsiPeriod, rsiThreshold in itertools.product(
        MA_PERIODS_GRID,
        RSI_PERIODS_GRID,
        RSI_THRESHOLDS_GRID
    ):
        completed += 1
        print(f"\n[{completed}/{totalCombinations}] 테스트 중...")
        print(f"   MA: {maPeriods}, RSI: {rsiPeriod}, 임계값: {rsiThreshold}")

        # 백테스팅 실행
        results = evaluateParams(
            candles=candles,
            maPeriods=maPeriods,
            rsiPeriod=rsiPeriod,
            rsiThreshold=rsiThreshold,
            initialEquity=args.equity,
            leverage=args.leverage
        )

        if results:
            score = calculateScore(results, args.metric)
            print(f"   [OK] {args.metric}: {score:.4f}, Win rate: {results['winRate'] * 100:.1f}%, Trades: {results['tradesPerDay']:.1f}/day")

            # trades 제거 (용량)
            results_copy = {k: v for k, v in results.items() if k != 'trades'}
            allResults.append(results_copy)

    # 상위 결과 출력
    print("\n" + "=" * 80)
    printTopResults(allResults, args.metric, top=10)

    # 최적 파라미터 선정
    best = max(allResults, key=lambda x: calculateScore(x, args.metric))
    bestParams = best['parameters']

    print(f"\n[BEST] Optimal parameters:")
    print("=" * 80)
    print(f"   MA periods: {bestParams['maPeriods']}")
    print(f"   RSI period: {bestParams['rsiPeriod']}")
    print(f"   RSI threshold: {bestParams['rsiThreshold']}")
    print(f"\nPerformance:")
    print(f"   Win rate: {best['winRate'] * 100:.2f}%")
    print(f"   Trades per day: {best['tradesPerDay']:.1f}")
    print(f"   Return: {best['returnRate'] * 100:+.2f}%")
    print(f"   Sharpe Ratio: {best['sharpeRatio']:.3f}")
    print(f"   Max drawdown: {best['maxDrawdown'] * 100:.2f}%")

    # 결과 저장
    outputPath = Path(args.output)
    outputPath.parent.mkdir(parents=True, exist_ok=True)

    outputData = {
        'optimization_metric': args.metric,
        'best_parameters': bestParams,
        'best_results': {k: v for k, v in best.items() if k != 'parameters'},
        'all_results': allResults
    }

    with open(outputPath, 'w', encoding='utf-8') as f:
        json.dump(outputData, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVE] Results saved: {args.output}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
