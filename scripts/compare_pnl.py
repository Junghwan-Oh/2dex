#!/usr/bin/env python3
"""
PNL Comparison Script for Baseline vs Static TP Strategies

Compares trading performance metrics between baseline (19bps spread) and
Static TP (individual 10bps) exit strategies.

Usage:
    python3 scripts/compare_pnl.py baseline.csv static_tp.csv
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

def load_trades(csv_path: str) -> pd.DataFrame:
    """Load trades CSV and add derived metrics."""
    df = pd.read_csv(csv_path)

    # Ensure numeric columns
    numeric_cols = ['total_pnl_bps', 'total_pnl_usd', 'entry_spread_bps', 'exit_spread_bps']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Add win/loss indicator
    if 'total_pnl_bps' in df.columns:
        df['is_win'] = df['total_pnl_bps'] > 0

    return df

def calculate_metrics(df: pd.DataFrame, name: str) -> dict:
    """Calculate comprehensive trading metrics."""

    # Count completed cycles
    cycles = len(df)

    # PNL metrics
    total_pnl_bps = df['total_pnl_bps'].sum() if 'total_pnl_bps' in df.columns else 0
    avg_pnl_bps = df['total_pnl_bps'].mean() if 'total_pnl_bps' in df.columns else 0
    std_pnl_bps = df['total_pnl_bps'].std() if 'total_pnl_bps' in df.columns else 0

    total_pnl_usd = df['total_pnl_usd'].sum() if 'total_pnl_usd' in df.columns else 0
    avg_pnl_usd = df['total_pnl_usd'].mean() if 'total_pnl_usd' in df.columns else 0

    # Win rate
    if 'is_win' in df.columns:
        win_rate = (df['is_win'].sum() / len(df)) * 100
        wins = df['is_win'].sum()
        losses = len(df) - wins
    else:
        win_rate = 0
        wins = 0
        losses = 0

    # Entry/exit spread analysis
    avg_entry_spread = df['entry_spread_bps'].mean() if 'entry_spread_bps' in df.columns else 0
    avg_exit_spread = df['exit_spread_bps'].mean() if 'exit_spread_bps' in df.columns else 0

    # Sharpe-like ratio (risk-adjusted return)
    sharpe_ratio = avg_pnl_bps / std_pnl_bps if std_pnl_bps > 0 else 0

    return {
        'strategy': name,
        'cycles': cycles,
        'total_pnl_bps': round(total_pnl_bps, 2),
        'avg_pnl_bps': round(avg_pnl_bps, 4),
        'std_pnl_bps': round(std_pnl_bps, 4),
        'total_pnl_usd': round(total_pnl_usd, 2),
        'avg_pnl_usd': round(avg_pnl_usd, 2),
        'win_rate': round(win_rate, 2),
        'wins': wins,
        'losses': losses,
        'avg_entry_spread_bps': round(avg_entry_spread, 2),
        'avg_exit_spread_bps': round(avg_exit_spread, 2),
        'sharpe_ratio': round(sharpe_ratio, 4),
        'pnl_values': df['total_pnl_bps'].values if 'total_pnl_bps' in df.columns else np.array([])
    }

def run_statistical_test(baseline_pnl: np.ndarray, static_tp_pnl: np.ndarray) -> dict:
    """Run statistical t-test to compare strategies."""

    if len(baseline_pnl) == 0 or len(static_tp_pnl) == 0:
        return {
            't_statistic': None,
            'p_value': None,
            'significant': False,
            'improvement': None,
            'interpretation': 'Insufficient data for statistical test'
        }

    # Independent two-sample t-test
    t_stat, p_value = stats.ttest_ind(static_tp_pnl, baseline_pnl)

    # Calculate improvement
    baseline_mean = np.mean(baseline_pnl)
    static_tp_mean = np.mean(static_tp_pnl)
    improvement = ((static_tp_mean - baseline_mean) / abs(baseline_mean)) * 100 if baseline_mean != 0 else 0

    # Interpret p-value
    alpha = 0.05
    significant = p_value < alpha

    if significant and static_tp_mean > baseline_mean:
        interpretation = f"Static TP is SIGNIFICANTLY BETTER (p={p_value:.4f} < {alpha})"
    elif significant and static_tp_mean < baseline_mean:
        interpretation = f"Static TP is SIGNIFICANTLY WORSE (p={p_value:.4f} < {alpha})"
    else:
        interpretation = f"No statistically significant difference (p={p_value:.4f} >= {alpha})"

    return {
        't_statistic': round(t_stat, 4),
        'p_value': round(p_value, 4),
        'significant': significant,
        'improvement': round(improvement, 2),
        'baseline_mean_bps': round(baseline_mean, 4),
        'static_tp_mean_bps': round(static_tp_mean, 4),
        'interpretation': interpretation
    }

def generate_report(baseline_metrics: dict, static_tp_metrics: dict, stats: dict) -> str:
    """Generate comprehensive comparison report."""

    report = []
    report.append("=" * 80)
    report.append("PNL COMPARISON REPORT: Baseline (19bps spread) vs Static TP (10bps)")
    report.append("=" * 80)
    report.append("")

    # Decision Criteria
    report.append("DECISION CRITERIA:")
    report.append("-" * 40)
    report.append("Merge if: p < 0.05, fill_rate >= 85%, no critical bugs")
    report.append("Discard if: No significant improvement, higher risk/loss")
    report.append("")

    # Baseline Results
    report.append("BASELINE RESULTS (19bps spread exit strategy):")
    report.append("-" * 50)
    for key, value in baseline_metrics.items():
        if key != 'pnl_values' and key != 'strategy':
            report.append(f"  {key}: {value}")
    report.append("")

    # Static TP Results
    report.append("STATIC TP RESULTS (10bps individual exit strategy):")
    report.append("-" * 50)
    for key, value in static_tp_metrics.items():
        if key != 'pnl_values' and key != 'strategy':
            report.append(f"  {key}: {value}")
    report.append("")

    # Statistical Analysis
    report.append("STATISTICAL ANALYSIS:")
    report.append("-" * 40)
    report.append(f"  T-statistic: {stats['t_statistic']}")
    report.append(f"  P-value: {stats['p_value']}")
    report.append(f"  Statistically Significant: {stats['significant']}")
    if stats['improvement'] is not None:
        report.append(f"  Improvement: {stats['improvement']}%")
    report.append(f"  Baseline Mean PNL: {stats['baseline_mean_bps']} bps")
    report.append(f"  Static TP Mean PNL: {stats['static_tp_mean_bps']} bps")
    report.append("")
    report.append(f"INTERPRETATION: {stats['interpretation']}")
    report.append("")

    # Recommendation
    report.append("RECOMMENDATION:")
    report.append("-" * 40)

    if stats['significant'] and stats['static_tp_mean_bps'] > stats['baseline_mean_bps']:
        # Check fill rate proxy (cycles completed vs expected)
        completion_rate = (static_tp_metrics['cycles'] / 50) * 100
        if completion_rate >= 85:
            report.append(">>> MERGE - Static TP shows statistically significant improvement")
            report.append(f">>> Completion rate: {completion_rate:.1f}% (>= 85% threshold)")
        else:
            report.append(f">>> CAUTION - Static TP shows improvement but low completion rate: {completion_rate:.1f}%")
            report.append(">>> Consider additional testing or investigation")
    elif stats['significant'] and stats['static_tp_mean_bps'] < stats['baseline_mean_bps']:
        report.append(">>> DISCARD - Static TP is statistically worse than baseline")
    else:
        report.append(">>> INCONCLUSIVE - No statistically significant difference")
        report.append(">>> Consider running additional cycles (100+) to get more data")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compare_pnl.py <baseline.csv> <static_tp.csv>")
        sys.exit(1)

    baseline_path = sys.argv[1]
    static_tp_path = sys.argv[2]

    # Check files exist
    if not Path(baseline_path).exists():
        print(f"Error: Baseline file not found: {baseline_path}")
        sys.exit(1)

    if not Path(static_tp_path).exists():
        print(f"Error: Static TP file not found: {static_tp_path}")
        sys.exit(1)

    print(f"Loading baseline data from: {baseline_path}")
    print(f"Loading Static TP data from: {static_tp_path}")

    # Load data
    try:
        baseline_df = load_trades(baseline_path)
        static_tp_df = load_trades(static_tp_path)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        sys.exit(1)

    print(f"Baseline loaded: {len(baseline_df)} cycles")
    print(f"Static TP loaded: {len(static_tp_df)} cycles")

    # Calculate metrics
    baseline_metrics = calculate_metrics(baseline_df, "Baseline (19bps spread)")
    static_tp_metrics = calculate_metrics(static_tp_df, "Static TP (10bps individual)")

    # Run statistical test
    stats_results = run_statistical_test(
        baseline_metrics['pnl_values'],
        static_tp_metrics['pnl_values']
    )

    # Generate report
    report = generate_report(baseline_metrics, static_tp_metrics, stats_results)

    print("\n")
    print(report)

    # Save report to file
    report_path = Path("/Users/botfarmer/2dex/logs/comparison_report.txt")
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")

    # Exit with appropriate code
    if stats_results['significant'] and stats_results['static_tp_mean_bps'] > stats_results['baseline_mean_bps']:
        sys.exit(0)  # Success - merge
    else:
        sys.exit(1)  # Failure - don't merge

if __name__ == "__main__":
    main()
