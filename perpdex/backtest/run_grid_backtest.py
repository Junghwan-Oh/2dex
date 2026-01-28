"""
Grid Trading 백테스팅 실행 스크립트

사용법:
    # 5분봉 데이터로 실행
    python backtest/run_grid_backtest.py --data backtest/data/binance_btc_5m_30days.csv

    # 파라미터 지정
    python backtest/run_grid_backtest.py --spacing 0.002 --grids 20
"""

import sys
from pathlib import Path
import argparse
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.data_loader import loadCsvData, createMockData
from backtest.strategies.grid_strategy import runBacktest


def parseArgs():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description='Grid Trading 백테스팅')

    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='CSV 데이터 파일 경로 (없으면 모의 데이터 사용)'
    )

    parser.add_argument(
        '--spacing',
        type=float,
        default=0.002,
        help='그리드 간격 (비율, 기본 0.002 = 0.2%%)'
    )

    parser.add_argument(
        '--grids',
        type=int,
        default=20,
        help='그리드 레벨 수 (기본 20)'
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
        default=None,
        help='결과 저장 경로 (JSON, 선택사항)'
    )

    return parser.parse_args()


def printResults(results: dict) -> None:
    """결과 출력"""
    print("\n" + "=" * 60)
    print("[GRID BACKTEST] Results")
    print("=" * 60)

    # 파라미터
    params = results['parameters']
    print(f"\n[PARAMETERS]:")
    print(f"   Grid spacing: {params['gridSpacing'] * 100:.2f}%")
    print(f"   Grid levels: {params['numGrids']}")
    print(f"   Initial equity: ${params['initialEquity']:,.2f}")
    print(f"   Leverage: {params['leverage']}x")

    # 거래 통계
    print(f"\n[TRADE STATS]:")
    print(f"   Total trades: {results['totalTrades']}")

    # 거래가 없으면 경고 후 종료
    if results['totalTrades'] == 0:
        print("\n[WARNING] No trades executed!")
        print("   Possible reasons:")
        print("   - Grid spacing too wide")
        print("   - Price range not touched")
        print("\n" + "=" * 60 + "\n")
        return

    print(f"   Winning: {results['winningTrades']}")
    print(f"   Losing: {results['losingTrades']}")
    print(f"   Win rate: {results['winRate'] * 100:.2f}%")
    print(f"   Trades per day: {results['tradesPerDay']:.1f}")
    print(f"   Avg hold time: {results['avgDuration']:.1f} min")

    # 수익 통계
    print(f"\n[PROFIT STATS]:")
    print(f"   Avg profit (win): ${results['avgProfit']:,.2f}")
    print(f"   Avg loss: ${results['avgLoss']:,.2f}")
    print(f"   Total PnL: ${results['totalPnl']:,.2f}")
    print(f"   Total fees: ${results['totalFees']:,.2f}")
    print(f"   Final equity: ${results['finalEquity']:,.2f}")
    print(f"   Return: {results['returnRate'] * 100:+.2f}%")

    # 리스크 지표
    print(f"\n[RISK METRICS]:")
    print(f"   Max drawdown: {results['maxDrawdown'] * 100:.2f}%")
    print(f"   Sharpe Ratio: {results['sharpeRatio']:.3f}")
    print(f"   Max consecutive losses: {results['maxConsecutiveLosses']}")

    # 평가
    print(f"\n[EVALUATION]:")

    if results['winRate'] >= 0.55:
        print(f"   Win rate: [OK] Good ({results['winRate'] * 100:.1f}%)")
    elif results['winRate'] >= 0.45:
        print(f"   Win rate: [~] Average ({results['winRate'] * 100:.1f}%)")
    else:
        print(f"   Win rate: [X] Low ({results['winRate'] * 100:.1f}%)")

    if results['tradesPerDay'] >= 45:
        print(f"   Trade freq: [OK] Target met ({results['tradesPerDay']:.1f}/day)")
    elif results['tradesPerDay'] >= 30:
        print(f"   Trade freq: [~] Almost ({results['tradesPerDay']:.1f}/day)")
    else:
        print(f"   Trade freq: [X] Low ({results['tradesPerDay']:.1f}/day, target 48)")

    if results['sharpeRatio'] >= 0.5:
        print(f"   Sharpe: [OK] Good ({results['sharpeRatio']:.2f})")
    elif results['sharpeRatio'] >= 0.0:
        print(f"   Sharpe: [~] Positive ({results['sharpeRatio']:.2f})")
    else:
        print(f"   Sharpe: [X] Negative ({results['sharpeRatio']:.2f})")

    if results['returnRate'] >= 0.0:
        print(f"   Return: [OK] Profitable ({results['returnRate'] * 100:+.2f}%)")
    elif results['returnRate'] >= -0.10:
        print(f"   Return: [~] Small loss ({results['returnRate'] * 100:+.2f}%)")
    else:
        print(f"   Return: [X] Large loss ({results['returnRate'] * 100:+.2f}%)")

    print("\n" + "=" * 60 + "\n")


def main():
    """메인 함수"""
    args = parseArgs()

    print(f"\n[START] Grid Trading Strategy Backtest...")

    # 데이터 로드
    if args.data:
        print(f"[DATA] Loading: {args.data}")
        candles = loadCsvData(args.data)
        print(f"   [OK] Loaded {len(candles)} candles")
    else:
        print(f"[DATA] Generating mock data...")
        candles = createMockData(
            startPrice=94000.0,
            numCandles=8640,  # 30일 (5분봉)
            volatility=0.002
        )
        print(f"   [OK] Generated {len(candles)} candles")

    # 백테스팅 실행
    print(f"\n[RUN] Running grid backtest...")
    print(f"   Grid spacing: {args.spacing * 100:.2f}%")
    print(f"   Grid levels: {args.grids}")

    results = runBacktest(
        candles=candles,
        gridSpacing=args.spacing,
        numGrids=args.grids,
        priceRange=None,  # 자동 계산
        initialEquity=args.equity,
        leverage=args.leverage
    )

    # 결과 출력
    printResults(results)

    # 결과 저장 (선택사항)
    if args.output:
        # trades 제외 (용량 큼)
        outputResults = {k: v for k, v in results.items() if k != 'trades'}

        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(outputResults, f, indent=2, ensure_ascii=False)

        print(f"[SAVE] Results saved: {args.output}")


if __name__ == "__main__":
    main()
