"""
Exit Parameter Optimization for MA+RSI Strategy

Test different combinations of:
- Target profit ranges
- Stop-loss values
- Time expiry values

Usage:
    python backtest/optimize_exit_params.py --data backtest/data/binance_btc_5m_30days.csv
"""

import sys
from pathlib import Path
import argparse
import json
from typing import List, Dict, Tuple
import itertools

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.data_loader import loadCsvData
from backtest.strategies.ma_rsi_strategy import runBacktest


# Exit parameter grids
TARGET_PROFIT_RANGES = [
    (0.0002, 0.0005),  # 0.02-0.05% (tighter)
    (0.0003, 0.0008),  # 0.03-0.08% (current baseline)
    (0.0005, 0.0015),  # 0.05-0.15% (wider)
    (0.0010, 0.0020),  # 0.10-0.20% (much wider)
]

STOP_LOSS_VALUES = [
    -0.0005,  # -0.05% (tight)
    -0.0008,  # -0.08% (current baseline)
    -0.0010,  # -0.10%
    -0.0015,  # -0.15% (wider)
    -0.0020,  # -0.20% (much wider)
]

TIME_EXPIRY_VALUES = [
    15,   # 15 minutes (faster)
    30,   # 30 minutes (current baseline)
    45,   # 45 minutes
    60,   # 60 minutes (1 hour)
]


def parseArgs():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Exit Parameter Optimization for MA+RSI')

    parser.add_argument(
        '--data',
        type=str,
        required=True,
        help='CSV data file path'
    )

    parser.add_argument(
        '--equity',
        type=float,
        default=5000.0,
        help='Initial equity (USD, default 5000)'
    )

    parser.add_argument(
        '--leverage',
        type=int,
        default=1,
        help='Leverage (default 1)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='backtest/results/exit_optimization_results.json',
        help='Output file path (JSON)'
    )

    parser.add_argument(
        '--metric',
        type=str,
        default='return',
        choices=['return', 'sharpe', 'winrate', 'trades'],
        help='Optimization metric (default return)'
    )

    return parser.parse_args()


def evaluateParams(
    candles: List[Dict],
    targetProfitRange: Tuple[float, float],
    stopLoss: float,
    timeExpire: int,
    initialEquity: float,
    leverage: int
) -> Dict:
    """
    Evaluate a parameter combination

    Args:
        candles: Candle data
        targetProfitRange: Target profit range (min, max)
        stopLoss: Stop-loss value
        timeExpire: Time expiry in minutes
        initialEquity: Initial equity
        leverage: Leverage

    Returns:
        Backtest results
    """
    try:
        # Use best MA+RSI parameters from previous optimization
        results = runBacktest(
            candles=candles,
            maPeriods=(3, 7, 15),  # Best from 5m optimization
            rsiPeriod=9,
            rsiThreshold=(35, 55),
            targetProfitRange=targetProfitRange,
            stopLoss=stopLoss,
            timeExpire=timeExpire,
            initialEquity=initialEquity,
            leverage=leverage
        )
        return results
    except Exception as e:
        print(f"   [ERROR] {e}")
        return None


def calculateScore(results: Dict, metric: str) -> float:
    """
    Calculate score based on metric

    Args:
        results: Backtest results
        metric: Evaluation metric

    Returns:
        Score (higher is better)
    """
    if results is None or results['totalTrades'] == 0:
        return -999999.0

    if metric == 'return':
        return results['returnRate']
    elif metric == 'sharpe':
        return results['sharpeRatio']
    elif metric == 'winrate':
        return results['winRate']
    elif metric == 'trades':
        return results['tradesPerDay']

    return 0.0


def printTopResults(
    allResults: List[Dict],
    metric: str,
    top: int = 10
) -> None:
    """
    Print top results

    Args:
        allResults: All results list
        metric: Evaluation metric
        top: Number of top results to show
    """
    # Sort by score
    sorted_results = sorted(
        allResults,
        key=lambda x: calculateScore(x, metric),
        reverse=True
    )

    print(f"\n[TOP] Top {top} parameter combinations (by {metric}):")
    print("=" * 100)

    for i, result in enumerate(sorted_results[:top], 1):
        params = result['parameters']
        score = calculateScore(result, metric)

        print(f"\n{i}. {metric.upper()}: {score:.4f}")
        print(f"   Target profit: {params['targetProfitRange'][0]*100:.2f}-{params['targetProfitRange'][1]*100:.2f}%")
        print(f"   Stop-loss: {params['stopLoss']*100:.2f}%")
        print(f"   Time expiry: {params['timeExpire']} min")
        print(f"   Win rate: {result['winRate']*100:.2f}%")
        print(f"   Trades/day: {result['tradesPerDay']:.1f}")
        print(f"   Return: {result['returnRate']*100:+.2f}%")
        print(f"   Sharpe: {result['sharpeRatio']:.3f}")
        print(f"   Max drawdown: {result['maxDrawdown']*100:.2f}%")


def main():
    """Main function"""
    args = parseArgs()

    print(f"\n[OPTIMIZE] Exit parameter optimization starting...")
    print(f"   Optimization metric: {args.metric.upper()}")

    # Load data
    print(f"\n[DATA] Loading: {args.data}")
    candles = loadCsvData(args.data)
    print(f"   [OK] {len(candles)} candles ready")

    # Grid search
    totalCombinations = (
        len(TARGET_PROFIT_RANGES) *
        len(STOP_LOSS_VALUES) *
        len(TIME_EXPIRY_VALUES)
    )

    print(f"\n[RUN] Grid search: {totalCombinations} combinations")
    print("=" * 100)

    allResults = []
    completed = 0

    for targetProfit, stopLoss, timeExpire in itertools.product(
        TARGET_PROFIT_RANGES,
        STOP_LOSS_VALUES,
        TIME_EXPIRY_VALUES
    ):
        completed += 1
        print(f"\n[{completed}/{totalCombinations}] Testing...")
        print(f"   Target: {targetProfit[0]*100:.2f}-{targetProfit[1]*100:.2f}%, Stop: {stopLoss*100:.2f}%, Time: {timeExpire}min")

        # Run backtest
        results = evaluateParams(
            candles=candles,
            targetProfitRange=targetProfit,
            stopLoss=stopLoss,
            timeExpire=timeExpire,
            initialEquity=args.equity,
            leverage=args.leverage
        )

        if results and results['totalTrades'] > 0:
            score = calculateScore(results, args.metric)
            print(f"   [OK] {args.metric}: {score:.4f}, Win: {results['winRate']*100:.1f}%, Trades: {results['tradesPerDay']:.1f}/day, Return: {results['returnRate']*100:+.2f}%")

            # Remove trades to save space
            results_copy = {k: v for k, v in results.items() if k != 'trades'}
            allResults.append(results_copy)
        else:
            print(f"   [SKIP] No trades or error")

    if not allResults:
        print("\n[ERROR] No valid results!")
        return

    # Print top results
    print("\n" + "=" * 100)
    printTopResults(allResults, args.metric, top=10)

    # Best parameters
    best = max(allResults, key=lambda x: calculateScore(x, args.metric))
    bestParams = best['parameters']

    print(f"\n[BEST] Optimal parameters:")
    print("=" * 100)
    print(f"   Target profit range: {bestParams['targetProfitRange'][0]*100:.2f}-{bestParams['targetProfitRange'][1]*100:.2f}%")
    print(f"   Stop-loss: {bestParams['stopLoss']*100:.2f}%")
    print(f"   Time expiry: {bestParams['timeExpire']} minutes")
    print(f"\nPerformance:")
    print(f"   Win rate: {best['winRate']*100:.2f}%")
    print(f"   Trades per day: {best['tradesPerDay']:.1f}")
    print(f"   Return: {best['returnRate']*100:+.2f}%")
    print(f"   Sharpe Ratio: {best['sharpeRatio']:.3f}")
    print(f"   Max drawdown: {best['maxDrawdown']*100:.2f}%")

    # Monthly metrics
    monthlyVolume = best['avgTradeSize'] * best['totalTrades'] * (30 / (len(candles) * 5 / 1440))
    monthlyReturn = best['returnRate'] * (30 / (len(candles) * 5 / 1440))
    print(f"\n   Monthly volume: ${monthlyVolume:,.0f}")
    print(f"   Monthly return: {monthlyReturn*100:+.2f}%")

    # Save results
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
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
