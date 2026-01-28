"""
Compare Static vs Dynamic Parameter Performance

Tests Avellaneda MM strategy with:
1. Static parameters (original baseline)
2. Dynamic parameters (Hummingbot Order Book Analyzer)

Evaluates performance improvement from dynamic parameter adaptation.
"""

import sys
from pathlib import Path
import pandas as pd
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.strategies.avellaneda_mm import runBacktest


def loadCandleData(csvPath: str):
    """Load candle data from CSV"""
    df = pd.read_csv(csvPath)

    candles = []
    for _, row in df.iterrows():
        candles.append({
            'timestamp': int(row['timestamp']),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume'])
        })

    return candles


def runComparison(dataPath: str):
    """Run static vs dynamic parameter comparison"""

    print("=" * 80)
    print("AVELLANEDA MM: STATIC VS DYNAMIC PARAMETER COMPARISON")
    print("=" * 80)

    # Load data
    print(f"\n[1] Loading data from {dataPath}...")
    candles = loadCandleData(dataPath)
    print(f"   Loaded {len(candles)} candles")

    # Test 1: Static parameters (baseline)
    print("\n[2] Running backtest with STATIC parameters...")
    staticResults = runBacktest(
        candles=candles,
        gamma=0.1,
        sigma=0.02,
        positionLimit=1000.0,
        initialEquity=5000.0,
        useDynamicParams=False
    )

    # Test 2: Dynamic parameters (enhanced)
    print("\n[3] Running backtest with DYNAMIC parameters...")
    dynamicResults = runBacktest(
        candles=candles,
        gamma=0.1,
        sigma=0.02,
        positionLimit=1000.0,
        initialEquity=5000.0,
        useDynamicParams=True
    )

    # Compare results
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    print("\n[STATIC PARAMETERS] (Baseline):")
    print(f"   Return: {staticResults['returnRate']*100:+.2f}%")
    print(f"   Total Trades: {staticResults['totalTrades']}")
    print(f"   Win Rate: {staticResults.get('winRate', 0)*100:.1f}%")
    print(f"   Sharpe Ratio: {staticResults.get('sharpeRatio', 0):.3f}")
    print(f"   Max Drawdown: {staticResults.get('maxDrawdown', 0)*100:.2f}%")
    print(f"   Total Volume: ${staticResults['totalVolume']:,.2f}")

    print("\n[DYNAMIC PARAMETERS] (Enhanced):")
    print(f"   Return: {dynamicResults['returnRate']*100:+.2f}%")
    print(f"   Total Trades: {dynamicResults['totalTrades']}")
    print(f"   Win Rate: {dynamicResults.get('winRate', 0)*100:.1f}%")
    print(f"   Sharpe Ratio: {dynamicResults.get('sharpeRatio', 0):.3f}")
    print(f"   Max Drawdown: {dynamicResults.get('maxDrawdown', 0)*100:.2f}%")
    print(f"   Total Volume: ${dynamicResults['totalVolume']:,.2f}")

    # Calculate improvements
    print("\n[IMPROVEMENT ANALYSIS]:")
    returnImprovement = (dynamicResults['returnRate'] - staticResults['returnRate']) * 100
    tradesImprovement = dynamicResults['totalTrades'] - staticResults['totalTrades']
    sharpeImprovement = dynamicResults.get('sharpeRatio', 0) - staticResults.get('sharpeRatio', 0)

    print(f"   Return Improvement: {returnImprovement:+.3f}%")
    print(f"   Additional Trades: {tradesImprovement:+d}")
    print(f"   Sharpe Improvement: {sharpeImprovement:+.3f}")

    # Verdict
    print("\n[VERDICT]:")
    if returnImprovement > 0.05:  # >0.05% improvement
        print("   [OK] DYNAMIC PARAMETERS OUTPERFORM")
        print("   --> RECOMMENDATION: Use dynamic parameters in production")
    elif returnImprovement < -0.05:  # <-0.05% worse
        print("   [X] DYNAMIC PARAMETERS UNDERPERFORM")
        print("   --> RECOMMENDATION: Stick with static parameters")
    else:
        print("   [=] SIMILAR PERFORMANCE")
        print("   --> RECOMMENDATION: Use static (simpler) unless testing shows clear benefit")

    # Save results
    outputPath = Path(__file__).parent / "results" / "static_vs_dynamic_comparison.json"
    outputPath.parent.mkdir(exist_ok=True)

    comparison = {
        'static': staticResults,
        'dynamic': dynamicResults,
        'improvements': {
            'return': returnImprovement,
            'trades': tradesImprovement,
            'sharpe': sharpeImprovement
        }
    }

    with open(outputPath, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\n[SAVED] Results saved to: {outputPath}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare static vs dynamic parameters")
    parser.add_argument(
        "--data",
        type=str,
        default="backtest/data/binance_btc_5m_30days.csv",
        help="Path to candle data CSV"
    )

    args = parser.parse_args()

    runComparison(args.data)
