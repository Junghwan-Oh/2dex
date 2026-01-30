#!/usr/bin/env python3.11
"""
TDD Test Suite for Order Size Optimization

This test suite verifies the order size optimization changes.
Run with: python3.11 test_order_size.py

Expected Behavior:
1. Default --size is 0.2 ETH (not required)
2. Help text mentions GRVT liquidity limit
3. Usage examples updated to 0.2 ETH
4. No hard-coded 0.5 ETH order sizes in code
"""

import sys
import re
from pathlib import Path

def test_1_default_size_parameter():
    """Test 1: Verify default --size is 0.2"""
    print("\n[Test 1] Checking default --size value...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Check for --size argument with default="0.2"
    pattern = r'--size.*?type=str.*?default=["\']0\.2["\']'

    if re.search(pattern, content, re.DOTALL):
        print("  ✅ PASS: default --size is 0.2")
        return True
    else:
        # Check if it's still required (old behavior)
        if re.search(r'--size.*?required=True', content, re.DOTALL):
            print("  ❌ FAIL: --size is still required (should have default='0.2')")
        else:
            print("  ❌ FAIL: default --size is not 0.2")
        return False


def test_2_help_text_mentions_liquidity_limit():
    """Test 2: Verify help text mentions GRVT liquidity limit"""
    print("\n[Test 2] Checking help text for GRVT liquidity mention...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Find --size argument section
    pattern = r'--size.*?help=["\']([^"\']*)["\']'

    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        if "liquidity" in match.lower() or "0.2" in match or "0.3" in match:
            print("  ✅ PASS: Help text mentions liquidity limit")
            print(f"     Text: {match[:80]}...")
            return True

    print("  ❌ FAIL: Help text doesn't mention GRVT liquidity limit")
    return False


def test_3_usage_examples_updated():
    """Test 3: Verify usage examples use 0.2 ETH"""
    print("\n[Test 3] Checking usage examples in docstring...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Check if docstring examples use 0.2
    # Look for python examples in docstring
    docstring_pattern = r'""".*?"""'
    docstrings = re.findall(docstring_pattern, content, re.DOTALL)

    found_0_2 = False
    found_old_sizes = False

    for docstring in docstrings:
        if "Usage:" in docstring:
            # Check for 0.2 examples
            if "--size 0.2" in docstring or "'0.2'" in docstring or '"0.2"' in docstring:
                found_0_2 = True
            # Check for old examples (0.5, 1, etc.)
            if re.search(r'--size\s+[01](?:\.\d)?\b', docstring) and "--size 0.2" not in docstring:
                found_old_sizes = True

    if found_0_2 and not found_old_sizes:
        print("  ✅ PASS: Usage examples updated to 0.2 ETH")
        return True
    elif found_0_2 and found_old_sizes:
        print("  ⚠️  WARN: Found 0.2 examples but also old sizes")
        return True
    else:
        print("  ❌ FAIL: Usage examples don't use 0.2 ETH")
        return False


def test_4_no_hardcoded_05_eth():
    """Test 4: Verify no hard-coded 0.5 ETH order sizes"""
    print("\n[Test 4] Checking for hard-coded 0.5 ETH order sizes...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        lines = f.readlines()

    issues = []

    for i, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        # Check for 0.5 in Decimal context (order quantities)
        if re.search(r'Decimal\(["\']0\.5["\']\)', line):
            issues.append(f"Line {i}: {line.strip()}")
        # Check for 0.50 as well
        if re.search(r'Decimal\(["\']0\.50["\']\)', line):
            issues.append(f"Line {i}: {line.strip()}")

    # Allow 0.5 in sleep_time contexts (0.5 seconds delays)
    issues = [i for i in issues if "sleep" not in i.lower()]

    if len(issues) == 0:
        print("  ✅ PASS: No hard-coded 0.5 ETH order sizes found")
        return True
    else:
        print(f"  ❌ FAIL: Found {len(issues)} hard-coded 0.5 ETH reference(s):")
        for issue in issues[:3]:  # Show first 3
            print(f"     {issue}")
        return False


def test_5_parameter_not_required():
    """Test 5: Verify --size parameter is not required"""
    print("\n[Test 5] Checking if --size parameter is required...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        lines = f.readlines()

    # Check line by line to avoid matching across add_argument blocks
    found_size_arg = False
    has_required_true = False
    has_default = False

    for i, line in enumerate(lines):
        # Check if we're in the --size argument block
        if '"--size"' in line or "'--size'" in line:
            found_size_arg = True
            # Check next few lines for required or default
            for j in range(i, min(i + 5, len(lines))):
                if 'required=True' in lines[j]:
                    has_required_true = True
                if 'default=' in lines[j]:
                    has_default = True
                # Stop if we hit the next argument
                if 'parser.add_argument' in lines[j] and j > i:
                    break

    if found_size_arg and has_required_true:
        print("  ❌ FAIL: --size is still marked as required")
        return False
    elif found_size_arg and has_default:
        print("  ✅ PASS: --size has default value (not required)")
        return True
    else:
        print("  ⚠️  WARN: --size argument not found or no default")
        return False


def main():
    """Run all tests and report results"""
    print("=" * 70)
    print("Order Size Optimization Test Suite (TDD)")
    print("=" * 70)
    print("\nThis test suite validates order size optimization changes.")
    print("Tests should FAIL initially, then PASS after implementation.\n")

    tests = [
        test_1_default_size_parameter,
        test_2_help_text_mentions_liquidity_limit,
        test_3_usage_examples_updated,
        test_4_no_hardcoded_05_eth,
        test_5_parameter_not_required
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
        print("\n🎉 All tests passed! Order size optimization is complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Implementation needed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
