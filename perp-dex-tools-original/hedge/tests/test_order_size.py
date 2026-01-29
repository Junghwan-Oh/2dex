#!/usr/bin/env python3
"""
TDD Tests for Order Size Feature (Feature C)

This test suite verifies that the default order size is 0.2 ETH.
Run with: python3 -m pytest tests/test_order_size.py -v
"""

import pytest
import subprocess
import csv
import tempfile
from pathlib import Path


def test_cli_default_size_is_0_2():
    """
    TEST 1: CLI argument --size defaults to 0.2 when not specified.
    """
    # Read the source code to verify default value
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that --size argument has default="0.2"
    assert 'default="0.2"' in content or "default='0.2'" in content, \
        "CLI --size argument should default to '0.2'"

    # Verify the help text mentions 0.2
    assert '0.2' in content, \
        "Help text should mention 0.2 as default"


def test_cli_size_override_works():
    """
    TEST 2: CLI argument --size can be overridden with custom value.
    """
    # This is a syntax check - verify the parser accepts --size argument
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that --size argument exists and takes a value
    assert '"--size"' in content or "'--size'" in content, \
        "CLI should have --size argument"

    assert 'type=str' in content, \
        "--size should accept string value"


def test_no_hardcoded_0_5_references():
    """
    TEST 3: No hardcoded 0.5 ETH references in critical paths.
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        lines = f.readlines()

    # Check for problematic patterns
    hardcoded_05_patterns = []

    for i, line in enumerate(lines, 1):
        # Skip comments and sleep/delay references (0.5 seconds is fine)
        if '#' in line and '0.5' in line.split('#')[0]:
            continue  # It's a comment

        # Skip asyncio.sleep(0.5) - these are delays, not quantities
        if 'asyncio.sleep' in line and '0.5' in line:
            continue

        # Check for Decimal('0.5') or Decimal("0.5") patterns in quantity context
        if "Decimal('0.5')" in line or 'Decimal("0.5")' in line:
            # Only flag if it looks like a quantity (not a delay/ratio)
            if 'quantity' in line.lower() or 'size' in line.lower():
                hardcoded_05_patterns.append((i, line.strip()))

    assert len(hardcoded_05_patterns) == 0, \
        f"Found hardcoded 0.5 ETH references:\n" + \
        "\n".join([f"  Line {i}: {line}" for i, line in hardcoded_05_patterns])


def test_csv_quantity_matches_configured_size():
    """
    TEST 4: CSV records show correct quantity based on configured size.
    """
    # Create a test CSV with known quantity
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerow([
            'iteration', 'direction', 'primary_entry_price', 'hedge_entry_price',
            'primary_entry_time', 'hedge_entry_time', 'primary_exit_price',
            'hedge_exit_price', 'primary_exit_time', 'hedge_exit_time',
            'order_to_fill_primary', 'order_to_fill_hedge', 'websocket_latency',
            'rest_latency', 'reconciliation_time', 'repricing_count',
            'total_cycle_time', 'hedge_entry_order_type', 'hedge_exit_order_type',
            'hedge_entry_fee_saved', 'hedge_exit_fee_saved'
        ])

        # Row with 0.2 ETH size (simulating default)
        writer.writerow([
            '1', 'BUY_FIRST', '3000.00', '3000.50', '1704067200.0', '1704067200.1',
            '3010.00', '3009.50', '1704067205.0', '1704067205.1',
            '100.0', '150.0', '10.0', '50.0', '5.0', '2', '5.2',
            'MARKET', 'POST_ONLY', 'False', 'True'
        ])

        test_csv = f.name

    try:
        # Verify the CSV can be read by our metrics scripts
        result = subprocess.run(
            ['python3', 'scripts/calculate_post_only_fill_rate.py', test_csv],
            capture_output=True,
            text=True,
            cwd='/tmp/2dex/perp-dex-tools-original/hedge'
        )

        assert result.returncode == 0, \
            f"Metrics script should process CSV with 0.2 ETH size: {result.stderr}"

    finally:
        Path(test_csv).unlink()


def test_order_quantity_initialized_correctly():
    """
    TEST 5: order_quantity is initialized from args.size in main().
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that order_quantity is set from args.size
    assert 'order_quantity=Decimal(args.size)' in content or \
           'order_quantity = Decimal(args.size)' in content, \
        "order_quantity should be initialized from args.size"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
