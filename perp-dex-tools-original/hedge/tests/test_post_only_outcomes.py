#!/usr/bin/env python3
"""
ACCEPTANCE TESTS for POST_ONLY Feature Outcomes

This is NOT TDD - we're validating EXISTING code meets business outcomes.
Run with: python3 -m pytest tests/test_post_only_outcomes.py -v
"""

import pytest
import subprocess
import csv
from pathlib import Path
import re


@pytest.fixture
def baseline_csv():
    """Path to baseline CSV (generated before any features)."""
    baseline_path = Path('/tmp/2dex/perp-dex-tools-original/hedge/logs/baseline_backpack_grvt_ETH.csv')
    if not baseline_path.exists():
        pytest.skip(f"Baseline CSV not found: {baseline_path}. Generate baseline first.")
    return str(baseline_path)


@pytest.fixture
def latest_csv():
    """Path to latest feature CSV."""
    logs_dir = Path('/tmp/2dex/perp-dex-tools-original/hedge/logs')
    csv_files = sorted(logs_dir.glob('trade_metrics_backpack_grvt_ETH_*.csv'))

    if not csv_files:
        pytest.skip(f"No trade metrics CSV files found in {logs_dir}")

    return str(csv_files[-1])


def test_outcome_1_post_only_fill_rate_at_least_40_percent(latest_csv):
    """
    ACCEPTANCE CRITERION: POST_ONLY achieves 40%+ fill rate on CLOSE path.

    This validates BUSINESS OUTCOME, not code implementation.
    """
    result = subprocess.run(
        ['python3', 'scripts/calculate_post_only_fill_rate.py', latest_csv],
        capture_output=True,
        text=True,
        cwd='/tmp/2dex/perp-dex-tools-original/hedge'
    )

    assert result.returncode == 0, f"Metrics script failed: {result.stderr}"

    output = result.stdout
    match = re.search(r'(\d+\.?\d*)%', output)

    if not match:
        pytest.fail(f"Could not parse fill rate from output: {output}")

    fill_rate = float(match.group(1))

    # Business outcome: Must achieve 40%+ fill rate
    assert fill_rate >= 40.0, \
        f"POST_ONLY fill rate {fill_rate}% < 40% target. Feature needs improvement."


def test_outcome_2_pnl_improvement_at_least_09_bps(baseline_csv, latest_csv):
    """
    ACCEPTANCE CRITERION: POST_ONLY improves PnL by +0.9 bps vs baseline.

    CORRECTED: Uses CORRECT PnL formula with quantity and direction.
    """
    result = subprocess.run(
        ['python3', 'scripts/calculate_pnl_improvement.py',
         '--before', baseline_csv, '--after', latest_csv],
        capture_output=True,
        text=True,
        cwd='/tmp/2dex/perp-dex-tools-original/hedge'
    )

    assert result.returncode == 0, f"PnL script failed: {result.stderr}"

    output = result.stdout
    match = re.search(r'PnL Improvement: ([-+]?\d+\.?\d*) bps', output)

    if not match:
        # Try alternative format
        match = re.search(r'Improvement:\s*\$[-+]?\d+\.?\d*\s*\(([-+]?\d+\.?\d*)\s*bps\)', output)

    if not match:
        pytest.fail(f"Could not parse PnL improvement from output: {output}")

    pnl_improvement = float(match.group(1))

    # Business outcome: Must improve PnL by +0.9 bps
    assert pnl_improvement >= 0.9, \
        f"PnL improvement {pnl_improvement} bps < +0.9 bps target. Feature needs improvement."


def test_outcome_3_no_infinite_loops_or_crashes(latest_csv):
    """
    ACCEPTANCE CRITERION: POST_ONLY doesn't cause infinite loops or crashes.
    """
    with open(latest_csv, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        # Should have ~20 iterations (plus header)
        assert len(rows) <= 25, \
            f"Too many rows ({len(rows)}) - possible infinite loop. Expected ~20 iterations."

        # All iterations should be numbered sequentially
        iterations = [int(row['iteration']) for row in rows if row.get('iteration')]
        if iterations:
            assert max(iterations) <= 25, \
                f"Highest iteration {max(iterations)} > 25 - possible infinite loop"


def test_outcome_4_net_delta_maintained_near_zero(latest_csv):
    """
    ACCEPTANCE CRITERION: NetDelta maintained near 0 (no position explosion).
    """
    log_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/logs/DN_alternate_backpack_grvt_ETH_log.txt')

    if not log_file.exists():
        pytest.skip(f"Log file not found: {log_file}")

    with open(log_file, 'r') as f:
        log_content = f.read()

        # Check for position explosion warnings
        assert 'position explosion' not in log_content.lower(), \
            "Position explosion detected in logs"

        # Check final NetDelta
        match = re.search(r'Net Delta:\s*([-+]?\d+\.?\d*)', log_content)
        if match:
            net_delta = float(match.group(1))
            assert abs(net_delta) < 0.5, \
                f"NetDelta {net_delta} too large - position not maintained near 0"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
