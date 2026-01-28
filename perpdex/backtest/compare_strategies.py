"""
Comparative Strategy Backtester

Compares Cross-DEX MM vs Avellaneda MM strategies
targeting 0% loss for volume farming.

Usage:
    python backtest/compare_strategies.py --data backtest/data/binance_btc_5m_30days.csv
"""

import sys
from pathlib import Path
import argparse
import json
from typing import Dict, List
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.data_loader import loadCsvData
from backtest.strategies.cross_dex_mm import runBacktest as runCrossDex
from backtest.strategies.avellaneda_mm import runBacktest as runAvellaneda
from backtest.strategies.ma_rsi_strategy import runBacktest as runMaRsi
from backtest.strategies.grid_strategy import runBacktest as runGrid


def formatResults(results: Dict, strategyName: str) -> Dict:
    """
    Format results for display and comparison

    Args:
        results: Raw backtest results
        strategyName: Name of the strategy

    Returns:
        Formatted results dictionary
    """
    # Extract key metrics
    formatted = {
        'strategy': strategyName,
        'return': results.get('returnRate', 0) * 100,
        'sharpe': results.get('sharpeRatio', 0),
        'winRate': results.get('winRate', 0) * 100,
        'totalTrades': results.get('totalTrades', 0),
        'tradesPerDay': results.get('tradesPerDay', 0),
        'maxDrawdown': results.get('maxDrawdown', 0) * 100,
        'totalPnl': results.get('totalPnl', 0),
        'totalFees': results.get('totalFees', 0),
        'finalEquity': results.get('finalEquity', 0)
    }

    # Add fee breakdown if available
    if 'feeBreakdown' in results:
        formatted['feeBreakdown'] = results['feeBreakdown']

    # Check if 0% target achieved
    formatted['targetAchieved'] = results.get('returnRate', 0) >= 0
    formatted['profitAboveFees'] = results.get('returnRate', 0) > 0

    # Calculate monthly projections
    if results.get('totalTrades', 0) > 0 and results.get('tradesPerDay', 0) > 0:
        avgTradeSize = results.get('avgTradeSize', 667)  # Default
        monthlyTrades = results['tradesPerDay'] * 30
        monthlyVolume = monthlyTrades * avgTradeSize
        formatted['monthlyVolume'] = monthlyVolume
        formatted['monthlyTrades'] = monthlyTrades

    return formatted


def printComparison(allResults: List[Dict]) -> None:
    """
    Print formatted comparison of all strategies

    Args:
        allResults: List of formatted results
    """
    print("\n" + "=" * 100)
    print("STRATEGY COMPARISON - TARGETING 0% LOSS")
    print("=" * 100)

    # Create comparison table
    print("\n[PERFORMANCE METRICS]")
    print("-" * 100)
    print(f"{'Strategy':<25} {'Return %':>10} {'Sharpe':>10} {'Win %':>10} {'Trades/Day':>12} {'0% Target':>12}")
    print("-" * 100)

    for result in allResults:
        targetMet = "[OK]" if result['targetAchieved'] else "[X]"
        profitable = "+" if result['profitAboveFees'] else ""

        print(f"{result['strategy']:<25} "
              f"{profitable}{result['return']:>9.2f}% "
              f"{result['sharpe']:>10.3f} "
              f"{result['winRate']:>9.1f}% "
              f"{result['tradesPerDay']:>12.1f} "
              f"{targetMet:>12}")

    # Volume metrics
    print("\n[VOLUME METRICS]")
    print("-" * 100)
    print(f"{'Strategy':<25} {'Total Trades':>15} {'Monthly Volume':>20} {'48/day Target':>15}")
    print("-" * 100)

    for result in allResults:
        monthlyVol = result.get('monthlyVolume', 0)
        monthlyTrades = result.get('monthlyTrades', 0)
        tradeTargetMet = "[OK]" if result['tradesPerDay'] >= 48 else f"[{result['tradesPerDay']/48*100:.0f}%]"

        print(f"{result['strategy']:<25} "
              f"{result['totalTrades']:>15,} "
              f"${monthlyVol:>19,.0f} "
              f"{tradeTargetMet:>15}")

    # Risk metrics
    print("\n[RISK METRICS]")
    print("-" * 100)
    print(f"{'Strategy':<25} {'Max Drawdown':>15} {'Final Equity':>15} {'Total P&L':>15}")
    print("-" * 100)

    for result in allResults:
        print(f"{result['strategy']:<25} "
              f"{result['maxDrawdown']:>14.2f}% "
              f"${result['finalEquity']:>14,.2f} "
              f"${result['totalPnl']:>14,.2f}")

    # Fee analysis
    print("\n[FEE ANALYSIS]")
    print("-" * 100)

    for result in allResults:
        if 'feeBreakdown' in result:
            fb = result['feeBreakdown']
            print(f"{result['strategy']:<25}")
            print(f"   Apex fees: ${fb.get('apexFees', 0):,.2f}")
            print(f"   Paradex fees: ${fb.get('paradexFees', 0):,.2f}")
            print(f"   Net fees: ${fb.get('netFees', 0):,.2f}")
            print(f"   Effective rate: {fb.get('effectiveFeeRate', 0)*100:.3f}%")
        else:
            print(f"{result['strategy']:<25}")
            print(f"   Total fees: ${result.get('totalFees', 0):,.2f}")
        print()

    # Winner selection
    print("\n[RECOMMENDATION]")
    print("=" * 100)

    # Find best strategy
    validStrategies = [r for r in allResults if r['targetAchieved']]

    if not validStrategies:
        print("[WARNING] No strategy achieved 0% loss target!")
        print("Recommendation: Need parameter tuning or alternative strategies")
    else:
        # Sort by return, then by trades per day
        best = max(validStrategies, key=lambda x: (x['return'], x['tradesPerDay']))
        print(f"[BEST] {best['strategy']}")
        print(f"   Return: {best['return']:+.2f}%")
        print(f"   Trades/Day: {best['tradesPerDay']:.1f}")
        print(f"   Monthly Volume: ${best.get('monthlyVolume', 0):,.0f}")

        if best['tradesPerDay'] < 48:
            print(f"\n   [NOTE] Trade frequency ({best['tradesPerDay']:.1f}/day) below target (48/day)")
            print(f"   Consider reducing spread or using faster timeframe")

    print("\n" + "=" * 100)


def parseArgs():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Compare MM Strategies')

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
        help='Initial equity (default 5000)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='backtest/results/strategy_comparison.json',
        help='Output file for results (JSON)'
    )

    parser.add_argument(
        '--include-legacy',
        action='store_true',
        help='Include MA+RSI and Grid strategies in comparison'
    )

    return parser.parse_args()


def main():
    """Main function"""
    args = parseArgs()

    print("\n[COMPARE] Strategy Comparison Starting...")
    print(f"   Data: {args.data}")
    print(f"   Initial Equity: ${args.equity:,.2f}")

    # Load data
    print("\n[DATA] Loading candles...")
    candles = loadCsvData(args.data)
    print(f"   [OK] {len(candles)} candles loaded")

    allResults = []

    # 1. Cross-DEX Market Maker (standard)
    print("\n[1/4] Running Cross-DEX MM (standard)...")
    try:
        result = runCrossDex(
            candles=candles,
            spread=0.0002,  # 0.02% spread
            positionLimit=1000.0,
            initialEquity=args.equity,
            useGridBot=False
        )
        formatted = formatResults(result, "Cross-DEX MM")
        allResults.append(formatted)
        print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 2. Cross-DEX Market Maker (with Grid Bot)
    print("\n[2/4] Running Cross-DEX MM (Grid Bot)...")
    try:
        result = runCrossDex(
            candles=candles,
            spread=0.0002,
            positionLimit=1000.0,
            initialEquity=args.equity,
            useGridBot=True  # Enable Grid Bot rebates
        )
        formatted = formatResults(result, "Cross-DEX MM (Grid)")
        allResults.append(formatted)
        print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 3. Avellaneda Market Maker
    print("\n[3/4] Running Avellaneda MM...")
    try:
        result = runAvellaneda(
            candles=candles,
            gamma=0.1,  # Risk aversion
            sigma=0.02,  # Volatility
            positionLimit=1000.0,
            initialEquity=args.equity
        )
        formatted = formatResults(result, "Avellaneda MM")
        allResults.append(formatted)
        print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 4. Include legacy strategies if requested
    if args.include_legacy:
        # MA+RSI Strategy (best params from optimization)
        print("\n[4/5] Running MA+RSI (optimized)...")
        try:
            result = runMaRsi(
                candles=candles,
                maPeriods=(3, 7, 15),
                rsiPeriod=9,
                rsiThreshold=(35, 55),
                targetProfitRange=(0.001, 0.002),  # 0.1-0.2%
                stopLoss=-0.0015,
                timeExpire=45,
                initialEquity=args.equity,
                leverage=1
            )
            formatted = formatResults(result, "MA+RSI (optimized)")
            allResults.append(formatted)
            print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
        except Exception as e:
            print(f"   [ERROR] {e}")

        # Grid Strategy
        print("\n[5/5] Running Grid Trading...")
        try:
            result = runGrid(
                candles=candles,
                gridSpacing=0.001,  # 0.1% spacing
                numGrids=20,
                initialEquity=args.equity,
                leverage=1
            )
            formatted = formatResults(result, "Grid Trading")
            allResults.append(formatted)
            print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
        except Exception as e:
            print(f"   [ERROR] {e}")

    # Print comparison
    if allResults:
        printComparison(allResults)

        # Save results
        outputPath = Path(args.output)
        outputPath.parent.mkdir(parents=True, exist_ok=True)

        with open(outputPath, 'w', encoding='utf-8') as f:
            json.dump(allResults, f, indent=2, ensure_ascii=False)

        print(f"\n[SAVE] Results saved to {args.output}")
    else:
        print("\n[ERROR] No strategies completed successfully!")


if __name__ == "__main__":
    main()