#!/usr/bin/env python3
"""
SOL Accumulation Bug Fix Verification

This script verifies that the SOL position accumulation bug has been fixed.
Run this script to confirm the fix is in place.

Usage:
    python3 scripts/verify_fix.py
"""

import sys
import os


def verify_fix():
    """Verify the SOL accumulation bug fix."""
    print("=" * 70)
    print("SOL POSITION ACCUMULATION BUG FIX VERIFICATION")
    print("=" * 70)

    file_path = "/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py"

    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return False

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Verify line 1013
    if len(lines) < 1013:
        print(f"[ERROR] File has fewer than 1013 lines")
        return False

    line_1013 = lines[1012].strip()  # Line 1013 (0-indexed)

    print(f"\nLine 1013: {line_1013}")

    # Check for correct pattern
    has_correct_pattern = (
        "result.success" in line_1013 and
        "result.filled_size > 0" in line_1013 and
        "and" in line_1013
    )

    # Check for buggy pattern
    has_buggy_pattern = (
        line_1013.startswith("if result.success:") and
        "filled_size" not in line_1013
    )

    # Verify ETH lines
    print("\nETH Pattern Verification:")
    for line_num in [941, 969]:
        if len(lines) >= line_num:
            line = lines[line_num - 1].strip()
            print(f"  Line {line_num}: {line}")

    print("\nSOL Pattern Verification:")
    print(f"  Line 1013: {line_1013}")

    # Check if all three match
    eth_line_941 = lines[940].strip() if len(lines) >= 941 else ""
    eth_line_969 = lines[968].strip() if len(lines) >= 969 else ""

    eth_pattern = "result.success and result.filled_size > 0"

    eth_941_matches = eth_pattern in eth_line_941
    eth_969_matches = eth_pattern in eth_line_969
    sol_1013_matches = eth_pattern in line_1013

    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)

    if has_buggy_pattern:
        print("[FAILED] BUGGY CODE DETECTED")
        print(f"  Line 1013 has buggy pattern: 'if result.success:'")
        print(f"  Should be: 'if result.success and result.filled_size > 0:'")
        print("\n[ACTION REQUIRED] Apply fix to line 1013")
        return False

    if not has_correct_pattern:
        print("[FAILED] INCORRECT PATTERN")
        print(f"  Line 1013 does not have expected pattern")
        print(f"  Expected: 'if result.success and result.filled_size > 0:'")
        print(f"  Actual: {line_1013}")
        return False

    if not (eth_941_matches and eth_969_matches and sol_1013_matches):
        print("[WARNING] PATTERNS DO NOT MATCH")
        print(f"  ETH 941 matches: {eth_941_matches}")
        print(f"  ETH 969 matches: {eth_969_matches}")
        print(f"  SOL 1013 matches: {sol_1013_matches}")
        return False

    print("[PASSED] ALL VERIFICATIONS")
    print("\nDetails:")
    print("  ✓ Line 1013 has correct pattern")
    print("  ✓ Line 1013 matches ETH pattern (lines 941, 969)")
    print("  ✓ No buggy pattern detected")
    print("\n[SUCCESS] SOL accumulation bug fix verified!")
    print("\nNext steps:")
    print("  1. Run tests: python3 -m pytest tests/test_sol_accumulation_bug.py -v")
    print("  2. Test on mainnet: Run 5+ cycles and verify no accumulation")
    print("  3. Monitor: Use scripts/check_positions.py and scripts/analyze_csv.py")

    return True


if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)
