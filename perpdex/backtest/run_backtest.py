"""
백테스팅 실행 스크립트

사용법:
    # 모의 데이터로 테스트
    python backtest/run_backtest.py

    # CSV 데이터로 실행
    python backtest/run_backtest.py --data btc_1m.csv

    # 파라미터 지정
    python backtest/run_backtest.py --ma 5,10,20 --rsi 14 --threshold 30,50
"""

import sys
from pathlib import Path
import argparse
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.data_loader import loadCsvData, createMockData, saveCsvData
from backtest.strategies.ma_rsi_strategy import runBacktest


def parseArgs():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description='MA+RSI 전략 백테스팅')

    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='CSV 데이터 파일 경로 (없으면 모의 데이터 사용)'
    )

    parser.add_argument(
        '--ma',
        type=str,
        default='5,10,20',
        help='MA 기간 (예: 5,10,20)'
    )

    parser.add_argument(
        '--rsi',
        type=int,
        default=14,
        help='RSI 기간 (기본 14)'
    )

    parser.add_argument(
        '--threshold',
        type=str,
        default='30,50',
        help='RSI 임계값 (예: 30,50)'
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
    print("[BACKTEST] Results")
    print("=" * 60)

    # 파라미터
    params = results['parameters']
    print(f"\n[PARAMETERS]:")
    print(f"   MA periods: {params['maPeriods']}")
    print(f"   RSI period: {params['rsiPeriod']}")
    print(f"   RSI threshold: {params['rsiThreshold']}")
    print(f"   Initial equity: ${params['initialEquity']:,.2f}")
    print(f"   Leverage: {params['leverage']}x")

    # 거래 통계
    print(f"\n[TRADE STATS]:")
    print(f"   Total trades: {results['totalTrades']}")

    # 거래가 없으면 경고 후 종료
    if results['totalTrades'] == 0:
        print("\n[WARNING] No trades executed!")
        print("   Possible reasons:")
        print("   - Entry conditions too strict")
        print("   - Not enough trend in data")
        print("   - RSI threshold too narrow")
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

    if results['winRate'] >= 0.65:
        print(f"   Win rate: [OK] Excellent ({results['winRate'] * 100:.1f}%)")
    elif results['winRate'] >= 0.55:
        print(f"   Win rate: [~] Average ({results['winRate'] * 100:.1f}%)")
    else:
        print(f"   Win rate: [X] Low ({results['winRate'] * 100:.1f}%)")

    if results['tradesPerDay'] >= 45:
        print(f"   Trade freq: [OK] Target met ({results['tradesPerDay']:.1f}/day)")
    elif results['tradesPerDay'] >= 35:
        print(f"   Trade freq: [~] Almost ({results['tradesPerDay']:.1f}/day)")
    else:
        print(f"   Trade freq: [X] Low ({results['tradesPerDay']:.1f}/day, target 48)")

    if results['sharpeRatio'] >= 1.5:
        print(f"   Sharpe: [OK] Excellent ({results['sharpeRatio']:.2f})")
    elif results['sharpeRatio'] >= 1.0:
        print(f"   Sharpe: [~] Average ({results['sharpeRatio']:.2f})")
    else:
        print(f"   Sharpe: [X] Low ({results['sharpeRatio']:.2f})")

    if results['maxDrawdown'] <= 0.10:
        print(f"   Drawdown: [OK] Good ({results['maxDrawdown'] * 100:.1f}%)")
    elif results['maxDrawdown'] <= 0.15:
        print(f"   Drawdown: [~] Caution ({results['maxDrawdown'] * 100:.1f}%)")
    else:
        print(f"   Drawdown: [X] High risk ({results['maxDrawdown'] * 100:.1f}%)")

    print("\n" + "=" * 60 + "\n")


def main():
    """메인 함수"""
    args = parseArgs()

    # 파라미터 파싱
    maPeriods = tuple(map(int, args.ma.split(',')))
    rsiThreshold = tuple(map(int, args.threshold.split(',')))

    print(f"\n[START] MA+RSI Strategy Backtest...")

    # 데이터 로드
    if args.data:
        print(f"[DATA] Loading: {args.data}")
        candles = loadCsvData(args.data)
        print(f"   [OK] Loaded {len(candles)} candles")
    else:
        print(f"[DATA] Generating mock data...")
        candles = createMockData(
            startPrice=94000.0,
            numCandles=43200,  # 30일 (1분봉)
            volatility=0.002  # 0.2% 변동성
        )
        print(f"   [OK] Generated {len(candles)} candles (30 days)")

        # 모의 데이터 저장 (재사용 가능)
        mockDataPath = "backtest/data/mock_btc_1m.csv"
        Path("backtest/data").mkdir(parents=True, exist_ok=True)
        saveCsvData(candles, mockDataPath)
        print(f"   [SAVE] Saved to: {mockDataPath}")

    # 백테스팅 실행
    print(f"\n[RUN] Running backtest...")
    print(f"   MA: {maPeriods}")
    print(f"   RSI: {args.rsi}")
    print(f"   RSI threshold: {rsiThreshold}")

    results = runBacktest(
        candles=candles,
        maPeriods=maPeriods,
        rsiPeriod=args.rsi,
        rsiThreshold=rsiThreshold,
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
