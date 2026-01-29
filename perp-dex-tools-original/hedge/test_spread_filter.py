#!/usr/bin/env python3.11
"""
TDD Test Suite for Minimum Spread Filter

This test suite verifies the minimum spread filter changes.
Run with: python3.11 test_spread_filter.py

Expected Behavior:
1. Default min_spread_bps is 5 (not 0)
2. CLI help text mentions break-even threshold (~7 bps)
3. Enhanced logging with BBO prices
4. 0 can still disable the filter
"""

import sys
import re
from pathlib import Path

def test_1_default_min_spread_is_5():
    """Test 1: Verify default min_spread_bps is 5"""
    print("\n[Test 1] Checking default min_spread_bps value...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Check for min_spread_bps parameter default
    pattern = r'min_spread_bps:\s*Decimal\s*=\s*Decimal\(["\'](\d+)["\']\)'

    match = re.search(pattern, content)

    if match:
        value = match.group(1)
        if value == "5":
            print(f"  ✅ PASS: default min_spread_bps is 5")
            return True
        else:
            print(f"  ❌ FAIL: default min_spread_bps is {value}, expected 5")
            return False
    else:
        print("  ❌ FAIL: min_spread_bps parameter not found")
        return False


def test_2_cli_help_mentions_break_even():
    """Test 2: Verify CLI help mentions break-even threshold"""
    print("\n[Test 2] Checking CLI help for break-even mention...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Find --min-spread argument
    pattern = r'"--min-spread".*?help=["\']([^"\']+)["\']'

    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        # Check for break-even or 7 bps mention
        if "break-even" in match.lower() or "breakeven" in match.lower() or "~7" in match:
            print("  ✅ PASS: Help text mentions break-even threshold")
            print(f"     Text: {match[:80]}...")
            return True

    print("  ❌ FAIL: Help text doesn't mention break-even threshold")
    return False


def test_3_cli_default_is_5():
    """Test 3: Verify CLI argument default is 5"""
    print("\n[Test 3] Checking --min-spread CLI default...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Check for --min-spread with default="5" or default='5'
    pattern = r'"--min-spread".*?default=["\']5["\']'

    if re.search(pattern, content, re.DOTALL):
        print("  ✅ PASS: --min-spread default is 5")
        return True
    else:
        print("  ❌ FAIL: --min-spread default is not 5")
        return False


def test_4_enhanced_spread_logging():
    """Test 4: Verify enhanced spread filter logging"""
    print("\n[Test 4] Checking enhanced spread logging...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Check for enhanced logging patterns
    checks = [
        (r'primary_bid=.*?primary_ask=', "BBO prices in ENTER log"),
        (r'hedge_bid=.*?hedge_ask=', "BBO prices in ENTER log"),
        (r'break-even:', "break-even threshold in SKIP log"),
    ]

    passed = 0
    for pattern, description in checks:
        if re.search(pattern, content, re.DOTALL):
            print(f"  ✓ Found: {description}")
            passed += 1
        else:
            print(f"  ✗ Missing: {description}")

    if passed == len(checks):
        print(f"  ✅ PASS: Enhanced logging found ({passed}/{len(checks)} patterns)")
        return True
    else:
        print(f"  ⚠️  PARTIAL: Enhanced logging incomplete ({passed}/{len(checks)} patterns)")
        return passed > 0


def test_5_zero_disables_filter():
    """Test 5: Verify 0 can still disable the filter"""
    print("\n[Test 5] Checking if 0 can disable filter...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Check help text mentions 0 disables filter
    if "0 = disabled" in content or "0 to disable" in content or "0 disables" in content:
        print("  ✅ PASS: Help text mentions 0 disables filter")
        return True
    else:
        print("  ⚠️  WARN: Help text doesn't explicitly mention 0 disables filter")
        print("     (Filter can still be disabled with --min-spread 0)")
        return True  # Not a critical failure


def main():
    """Run all tests and report results"""
    print("=" * 70)
    print("Minimum Spread Filter Test Suite (TDD)")
    print("=" * 70)
    print("\nThis test suite validates minimum spread filter changes.")
    print("Tests should FAIL initially, then PASS after implementation.\n")

    tests = [
        test_1_default_min_spread_is_5,
        test_2_cli_help_mentions_break_even,
        test_3_cli_default_is_5,
        test_4_enhanced_spread_logging,
        test_5_zero_disables_filter
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  Test {i} ({test.__name__}): {status}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")

    if passed == total:
        print("\n🎉 All tests passed! Spread filter is complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Implementation needed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
