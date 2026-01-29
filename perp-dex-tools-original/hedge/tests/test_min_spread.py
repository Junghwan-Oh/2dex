#!/usr/bin/env python3
"""
TDD Tests for Min Spread Feature (Feature D)

This test suite verifies that the default min-spread is 5 bps.
Run with: python3 -m pytest tests/test_min_spread.py -v
"""

import pytest
from pathlib import Path


def test_cli_default_min_spread_is_5():
    """
    TEST 1: CLI argument --min-spread defaults to 5 when not specified.
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that --min-spread argument has default="5"
    assert 'default="5"' in content or "default='5'" in content, \
        "CLI --min-spread argument should default to '5'"

    # Specifically for --min-spread
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '"--min-spread"' in line or "'--min-spread'" in line:
            # Check next few lines for default value
            for j in range(i, min(i+5, len(lines))):
                if 'default=' in lines[j]:
                    assert '"5"' in lines[j] or "'5'" in lines[j], \
                        f"--min-spread default should be '5', found: {lines[j].strip()}"
                    break
            break


def test_cli_min_spread_override_works():
    """
    TEST 2: CLI argument --min-spread can be overridden with custom value.
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that --min-spread argument exists and takes a value
    assert '"--min-spread"' in content or "'--min-spread'" in content, \
        "CLI should have --min-spread argument"

    # Should accept string value (for Decimal conversion)
    assert 'type=str' in content, \
        "--min-spread should accept string value"


def test_init_default_min_spread_is_5():
    """
    TEST 3: __init__ parameter min_spread_bps defaults to Decimal("5").
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that __init__ has min_spread_bps with default Decimal("5")
    assert 'min_spread_bps: Decimal = Decimal("5")' in content or \
           "min_spread_bps: Decimal = Decimal('5')" in content, \
        "__init__ parameter min_spread_bps should default to Decimal('5')"


def test_min_spread_passed_to_bot():
    """
    TEST 4: min_spread_bps is passed from CLI to DNHedgeBot constructor.
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that main() passes min_spread_bps to DNHedgeBot
    assert 'min_spread_bps=Decimal(args.min_spread)' in content or \
           'min_spread_bps = Decimal(args.min_spread)' in content, \
        "main() should pass min_spread_bps from CLI args to DNHedgeBot"


def test_help_text_shows_correct_default():
    """
    TEST 5: Help text shows correct default value (5 bps).
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        lines = f.readlines()

    # Find --min-spread argument definition
    for i, line in enumerate(lines):
        if '"--min-spread"' in line or "'--min-spread'" in line:
            # Check next few lines for help text
            for j in range(i, min(i+5, len(lines))):
                current_line = lines[j]
                if 'help=' in current_line:
                    # Verify help text mentions 5 as default
                    assert 'default: 5' in current_line or 'default=5' in current_line, \
                        f"Help text should show 'default: 5', found: {current_line.strip()}"
                    # Should also mention break-even
                    assert 'break-even' in current_line or 'breakeven' in current_line, \
                        f"Help text should mention break-even, found: {current_line.strip()}"
                    return
            break

    # If we get here, we didn't find the help text
    pytest.fail("Could not find help text for --min-spread argument")


def test_spread_filter_logic_uses_min_spread():
    """
    TEST 6: Spread filter logic compares spread_bps >= self.min_spread_bps.
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that spread filter uses min_spread_bps
    assert 'spread_bps >= self.min_spread_bps' in content or \
           'spread_bps >= min_spread_bps' in content, \
        "Spread filter should compare spread_bps >= self.min_spread_bps"

    # Check for logging that shows the filter value
    assert 'self.min_spread_bps' in content, \
        "Code should reference self.min_spread_bps for logging"


def test_zero_disables_filter():
    """
    TEST 7: min_spread_bps=0 disables the spread filter.
    """
    source_file = Path('/tmp/2dex/perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py')

    with open(source_file, 'r') as f:
        content = f.read()

    # Check that min_spread_bps == 0 disables filter
    assert 'if self.min_spread_bps == Decimal("0")' in content or \
           'if self.min_spread_bps == Decimal("0")' in content or \
           'if self.min_spread_bps == 0' in content, \
        "Code should check if min_spread_bps == 0 to disable filter"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
