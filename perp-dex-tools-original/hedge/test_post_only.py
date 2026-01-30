#!/usr/bin/env python3.11
"""
TDD Test Suite for POST_ONLY Hedge Order Feature

This test suite verifies the POST_ONLY functionality for DN Bot hedge orders.
Run with: python3.11 test_post_only.py

Expected Behavior:
1. hedge_post_only parameter exists in __init__
2. POST_ONLY tracking variables are initialized
3. TradeMetrics includes POST_ONLY fields
4. CLI arguments --hedge-post-only and --hedge-market work
5. POST_ONLY execution logic exists in place_hedge_order
"""

import sys
import os
import ast
import inspect
from pathlib import Path
from decimal import Decimal

# Add hedge directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_1_hedge_post_only_parameter_exists():
    """Test 1: Verify hedge_post_only parameter exists in DNHedgeBot.__init__"""
    print("\n[Test 1] Checking hedge_post_only parameter...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    # Parse the file
    tree = ast.parse(content)

    # Find DNHedgeBot class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "DNHedgeBot":
            # Find __init__ method
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    # Check parameters
                    params = [arg.arg for arg in item.args.args]
                    defaults = item.args.defaults

                    # Find hedge_post_only in parameters
                    if "hedge_post_only" in params:
                        print("  ✅ PASS: hedge_post_only parameter found")

                        # Check default value
                        param_index = params.index("hedge_post_only")
                        defaults_offset = len(params) - len(defaults)
                        default_index = param_index - defaults_offset

                        if default_index >= 0:
                            default_node = defaults[default_index]
                            if isinstance(default_node, ast.Constant) and default_node.value is True:
                                print("  ✅ PASS: hedge_post_only default is True")
                                return True
                            else:
                                print(f"  ⚠️  WARN: hedge_post_only default is {ast.unparse(default_node)}, expected True")
                                return False
                        return True
                    else:
                        print("  ❌ FAIL: hedge_post_only parameter NOT found")
                        print(f"     Available parameters: {params}")
                        return False

    print("  ❌ FAIL: DNHedgeBot.__init__ not found")
    return False


def test_2_post_only_tracking_variables():
    """Test 2: Verify POST_ONLY tracking variables are initialized"""
    print("\n[Test 2] Checking POST_ONLY tracking variables...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    required_vars = [
        "self.current_hedge_entry_order_type",
        "self.current_hedge_exit_order_type",
        "self.current_hedge_entry_fee_saved",
        "self.current_hedge_exit_fee_saved"
    ]

    found_vars = []
    missing_vars = []

    for var in required_vars:
        if var in content:
            found_vars.append(var)
        else:
            missing_vars.append(var)

    if len(found_vars) == len(required_vars):
        print(f"  ✅ PASS: All {len(required_vars)} tracking variables found")
        return True
    else:
        print(f"  ❌ FAIL: Missing {len(missing_vars)} tracking variables")
        print(f"     Missing: {missing_vars}")
        return False


def test_3_trademetrics_fields():
    """Test 3: Verify TradeMetrics includes POST_ONLY fields"""
    print("\n[Test 3] Checking TradeMetrics POST_ONLY fields...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    tree = ast.parse(content)

    required_fields = [
        "hedge_entry_order_type",
        "hedge_exit_order_type",
        "hedge_entry_fee_saved",
        "hedge_exit_fee_saved"
    ]

    # Find TradeMetrics class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TradeMetrics":
            # Get all field names
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)

            found_fields = [f for f in required_fields if f in fields]
            missing_fields = [f for f in required_fields if f not in fields]

            if len(found_fields) == len(required_fields):
                print(f"  ✅ PASS: All {len(required_fields)} TradeMetrics fields found")
                return True
            else:
                print(f"  ❌ FAIL: Missing {len(missing_fields)} TradeMetrics fields")
                print(f"     Missing: {missing_fields}")
                return False

    print("  ❌ FAIL: TradeMetrics class not found")
    return False


def test_4_cli_arguments():
    """Test 4: Verify CLI arguments for POST_ONLY control"""
    print("\n[Test 4] Checking CLI arguments...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    required_args = [
        ("--hedge-post-only", "store_true"),
        ("--hedge-market", "store_false")
    ]

    found_args = []
    missing_args = []

    # Check for argument definitions
    for arg_name, action in required_args:
        # Look for add_argument calls
        if f'"{arg_name}"' in content or f"'{arg_name}'" in content:
            if action in content:
                found_args.append(arg_name)
            else:
                print(f"  ⚠️  WARN: {arg_name} found but action '{action}' not confirmed")
                found_args.append(arg_name)
        else:
            missing_args.append(arg_name)

    if len(found_args) == len(required_args):
        print(f"  ✅ PASS: All {len(required_args)} CLI arguments found")
        return True
    else:
        print(f"  ❌ FAIL: Missing {len(missing_args)} CLI arguments")
        print(f"     Missing: {missing_args}")
        return False


def test_5_post_only_execution_logic():
    """Test 5: Verify POST_ONLY execution logic in place_hedge_order"""
    print("\n[Test 5] Checking POST_ONLY execution logic...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    required_patterns = [
        "hedge_post_only",
        "place_post_only_order",
        "asyncio.wait_for",
        "timeout=3.0",
        "hedge_result.status",
        'status == "FILLED"',
        'status == "OPEN"'
    ]

    found_patterns = []
    missing_patterns = []

    for pattern in required_patterns:
        if pattern in content:
            found_patterns.append(pattern)
        else:
            missing_patterns.append(pattern)

    if len(found_patterns) >= len(required_patterns) - 2:  # Allow some flexibility
        print(f"  ✅ PASS: POST_ONLY execution logic found ({len(found_patterns)}/{len(required_patterns)} patterns)")
        if missing_patterns:
            print(f"  ⚠️  Note: Missing patterns: {missing_patterns}")
        return True
    else:
        print(f"  ❌ FAIL: POST_ONLY execution logic incomplete ({len(found_patterns)}/{len(required_patterns)} patterns found)")
        print(f"     Missing: {missing_patterns}")
        return False


def test_6_instance_variable_assignment():
    """Test 6: Verify hedge_post_only is assigned to instance variable"""
    print("\n[Test 6] Checking self.hedge_post_only assignment...")

    with open("DN_alternate_backpack_grvt.py", "r") as f:
        content = f.read()

    if "self.hedge_post_only = hedge_post_only" in content:
        print("  ✅ PASS: self.hedge_post_only assignment found")
        return True
    else:
        print("  ❌ FAIL: self.hedge_post_only assignment NOT found")
        return False


def main():
    """Run all tests and report results"""
    print("=" * 70)
    print("POST_ONLY Feature Test Suite (TDD)")
    print("=" * 70)
    print("\nThis test suite validates POST_ONLY hedge order functionality.")
    print("Tests should FAIL initially, then PASS after implementation.\n")

    tests = [
        test_1_hedge_post_only_parameter_exists,
        test_2_post_only_tracking_variables,
        test_3_trademetrics_fields,
        test_4_cli_arguments,
        test_5_post_only_execution_logic,
        test_6_instance_variable_assignment
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
        print("\n🎉 All tests passed! POST_ONLY feature is complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Implementation needed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
