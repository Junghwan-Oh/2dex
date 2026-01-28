"""
Final Strategy Validation

Tests both Avellaneda MM and improved Cross-DEX MM strategies
with two capital scenarios:
- $100 testnet (50+ trades/day target)
- $5,000 mainnet ($1M+ monthly volume target)

Compares results and generates comprehensive report.
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


def formatResults(results: Dict, strategyName: str, capital: float) -> Dict:
    """Format results for display"""
    formatted = {
        'strategy': strategyName,
        'capital': capital,
        'return': results.get('returnRate', 0) * 100,
        'sharpe': results.get('sharpeRatio', 0),
        'winRate': results.get('winRate', 0) * 100,
        'totalTrades': results.get('totalTrades', 0),
        'tradesPerDay': results.get('tradesPerDay', 0),
        'maxDrawdown': results.get('maxDrawdown', 0) * 100,
        'totalPnl': results.get('totalPnl', 0),
        'finalEquity': results.get('finalEquity', 0)
    }

    # Calculate monthly metrics
    if results.get('tradesPerDay', 0) > 0:
        avgTradeSize = results.get('avgTradeSize', capital / 10)
        monthlyTrades = results['tradesPerDay'] * 30
        monthlyVolume = monthlyTrades * avgTradeSize
        formatted['monthlyVolume'] = monthlyVolume
        formatted['monthlyTrades'] = monthlyTrades

    # Add fee breakdown if available
    if 'feeBreakdown' in results:
        formatted['feeBreakdown'] = results['feeBreakdown']

    # Check targets
    formatted['targetAchieved'] = results.get('returnRate', 0) >= 0

    # Scenario-specific targets
    if capital == 100:
        formatted['tradesPerDayTarget'] = 50
        formatted['tradesTargetMet'] = results.get('tradesPerDay', 0) >= 50
    else:  # $5000
        formatted['monthlyVolumeTarget'] = 1000000  # $1M
        monthlyVol = formatted.get('monthlyVolume', 0)
        formatted['volumeTargetMet'] = monthlyVol >= 1000000

    return formatted


def printScenarioResults(results: List[Dict], scenarioName: str, capital: float) -> None:
    """Print formatted results for one scenario"""
    print("\n" + "=" * 100)
    print(f"SCENARIO: {scenarioName} (${capital:,.0f} capital)")
    print("=" * 100)

    # Performance comparison
    print("\n[PERFORMANCE COMPARISON]")
    print("-" * 100)
    print(f"{'Strategy':<25} {'Return %':>10} {'Sharpe':>10} {'Trades/Day':>12} {'0% Target':>12}")
    print("-" * 100)

    for result in results:
        targetMet = "[OK]" if result['targetAchieved'] else "[X]"
        profitSign = "+" if result['return'] > 0 else ""

        print(f"{result['strategy']:<25} "
              f"{profitSign}{result['return']:>9.2f}% "
              f"{result['sharpe']:>10.3f} "
              f"{result['tradesPerDay']:>12.1f} "
              f"{targetMet:>12}")

    # Scenario-specific targets
    print("\n[SCENARIO TARGETS]")
    print("-" * 100)

    if capital == 100:
        print(f"{'Strategy':<25} {'Trades/Day':>15} {'Target (50/day)':>20} {'Met':>10}")
        print("-" * 100)
        for result in results:
            targetMet = "[OK]" if result.get('tradesTargetMet', False) else f"[{result['tradesPerDay']/50*100:.0f}%]"
            print(f"{result['strategy']:<25} "
                  f"{result['tradesPerDay']:>15.1f} "
                  f"{'50':>20} "
                  f"{targetMet:>10}")

    else:  # $5000
        print(f"{'Strategy':<25} {'Monthly Volume':>20} {'Target ($1M/mo)':>20} {'Met':>10}")
        print("-" * 100)
        for result in results:
            monthlyVol = result.get('monthlyVolume', 0)
            targetMet = "[OK]" if result.get('volumeTargetMet', False) else f"[{monthlyVol/1000000*100:.0f}%]"
            print(f"{result['strategy']:<25} "
                  f"${monthlyVol:>19,.0f} "
                  f"${'1,000,000':>19} "
                  f"{targetMet:>10}")

    # Fee analysis
    print("\n[FEE ANALYSIS]")
    print("-" * 100)

    for result in results:
        if 'feeBreakdown' in result:
            fb = result['feeBreakdown']
            print(f"{result['strategy']:<25}")
            print(f"   Apex fees: ${fb.get('apexFees', 0):,.2f}")
            print(f"   Paradex fees: ${fb.get('paradexFees', 0):,.2f}")
            print(f"   Net fees: ${fb.get('netFees', 0):,.2f}")
            effectiveRate = fb.get('feeRate', fb.get('effectiveFeeRate', 0))
            print(f"   Effective rate: {effectiveRate*100:.4f}%")
        print()


def printFinalComparison(allResults: Dict) -> None:
    """Print final comparison across both scenarios"""
    print("\n" + "=" * 100)
    print("FINAL COMPARISON: $100 vs $5,000")
    print("=" * 100)

    print("\n[WINNER SELECTION]")
    print("-" * 100)

    # Analyze $100 scenario
    scenario100 = allResults['scenario_100']
    print("\n$100 Testnet Scenario:")
    validStrategies = [r for r in scenario100 if r['targetAchieved'] and r.get('tradesTargetMet', False)]

    if validStrategies:
        best = max(validStrategies, key=lambda x: (x['return'], x['tradesPerDay']))
        print(f"   [BEST] {best['strategy']}")
        print(f"   Return: {best['return']:+.2f}%")
        print(f"   Trades/Day: {best['tradesPerDay']:.1f} (Target: 50+)")
    else:
        print("   [WARNING] No strategy met all targets!")

    # Analyze $5000 scenario
    scenario5000 = allResults['scenario_5000']
    print("\n$5,000 Mainnet Scenario:")
    validStrategies = [r for r in scenario5000 if r['targetAchieved'] and r.get('volumeTargetMet', False)]

    if validStrategies:
        best = max(validStrategies, key=lambda x: (x['return'], x.get('monthlyVolume', 0)))
        print(f"   [BEST] {best['strategy']}")
        print(f"   Return: {best['return']:+.2f}%")
        print(f"   Monthly Volume: ${best.get('monthlyVolume', 0):,.0f} (Target: $1M+)")
    else:
        print("   [WARNING] No strategy met all targets!")

    print("\n" + "=" * 100)


def runScenario(candles: List[Dict], capital: float, scenarioName: str) -> List[Dict]:
    """Run all strategies for one capital scenario"""
    print(f"\n[SCENARIO] Running {scenarioName} (${capital:,.0f})...")

    results = []

    # 1. Cross-DEX MM (standard)
    print(f"\n[1/4] Cross-DEX MM (standard, ${capital:,.0f})...")
    try:
        result = runCrossDex(
            candles=candles,
            spread=0.0002,
            positionLimit=capital,
            initialEquity=capital,
            useGridBot=False
        )
        formatted = formatResults(result, "Cross-DEX MM", capital)
        results.append(formatted)
        print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 2. Cross-DEX MM (Grid Bot)
    print(f"\n[2/4] Cross-DEX MM (Grid Bot, ${capital:,.0f})...")
    try:
        result = runCrossDex(
            candles=candles,
            spread=0.0002,
            positionLimit=capital,
            initialEquity=capital,
            useGridBot=True
        )
        formatted = formatResults(result, "Cross-DEX MM (Grid)", capital)
        results.append(formatted)
        print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 3. Avellaneda MM
    print(f"\n[3/4] Avellaneda MM (${capital:,.0f})...")
    try:
        result = runAvellaneda(
            candles=candles,
            gamma=0.1,
            sigma=0.02,
            positionLimit=capital,
            initialEquity=capital
        )
        formatted = formatResults(result, "Avellaneda MM", capital)
        results.append(formatted)
        print(f"   [OK] Return: {formatted['return']:+.2f}%, Trades/Day: {formatted['tradesPerDay']:.1f}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    return results


def parseArgs():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Final Strategy Validation')

    parser.add_argument(
        '--data',
        type=str,
        default='backtest/data/binance_btc_5m_30days.csv',
        help='CSV data file path'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='backtest/results',
        help='Output directory for results'
    )

    return parser.parse_args()


def main():
    """Main function"""
    args = parseArgs()

    print("\n" + "=" * 100)
    print("FINAL STRATEGY VALIDATION")
    print("=" * 100)
    print(f"\nData: {args.data}")

    # Load data
    print("\n[DATA] Loading candles...")
    candles = loadCsvData(args.data)
    print(f"   [OK] {len(candles)} candles loaded")

    # Scenario 1: $100 (Testnet - 50+ trades/day target)
    results100 = runScenario(candles, 100.0, "Testnet $100")

    # Scenario 2: $5,000 (Mainnet - $1M+ monthly volume target)
    results5000 = runScenario(candles, 5000.0, "Mainnet $5,000")

    # Print results
    printScenarioResults(results100, "Testnet", 100.0)
    printScenarioResults(results5000, "Mainnet", 5000.0)

    # Combined results
    allResults = {
        'scenario_100': results100,
        'scenario_5000': results5000
    }

    printFinalComparison(allResults)

    # Save results
    outputDir = Path(args.output)
    outputDir.mkdir(parents=True, exist_ok=True)

    # Save individual scenarios
    with open(outputDir / 'final_comparison_100.json', 'w', encoding='utf-8') as f:
        json.dump(results100, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVE] $100 results saved to {outputDir}/final_comparison_100.json")

    with open(outputDir / 'final_comparison_5000.json', 'w', encoding='utf-8') as f:
        json.dump(results5000, f, indent=2, ensure_ascii=False)
    print(f"[SAVE] $5,000 results saved to {outputDir}/final_comparison_5000.json")

    # Save combined results
    with open(outputDir / 'final_validation.json', 'w', encoding='utf-8') as f:
        json.dump(allResults, f, indent=2, ensure_ascii=False)
    print(f"[SAVE] Combined results saved to {outputDir}/final_validation.json")

    print("\n[COMPLETE] Final validation completed successfully!")
    print("=" * 100)


if __name__ == "__main__":
    main()
