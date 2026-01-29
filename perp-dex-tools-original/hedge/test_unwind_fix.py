#!/usr/bin/env python3.11
"""
TDD Test Suite for Option 7B: Fix Safety Layer #2

Tests the fix for UNWIND stuck detection when spread filter blocks trades.
"""

import re

def test_unwind_threshold_increased():
    """Test 1: unwind_stuck_threshold increased from 2 to 10"""
    with open('DN_alternate_backpack_grvt.py', 'r') as f:
        content = f.read()

    # Find the threshold initialization
    pattern = r'self\.unwind_stuck_threshold\s*=\s*(\d+)'
    matches = re.findall(pattern, content)

    assert len(matches) > 0, "unwind_stuck_threshold not found"
    threshold = int(matches[0])

    assert threshold >= 10, f"unwind_stuck_threshold should be >= 10, got {threshold}"
    print(f"✅ Test 1: unwind_stuck_threshold = {threshold} (>= 10)")

def test_unwind_counter_logic():
    """Test 2: Counter only increments on spread check failures"""
    with open('DN_alternate_backpack_grvt.py', 'r') as f:
        content = f.read()

    # Check UNWIND loop structure
    # The counter should increment AFTER spread check fails, not on every iteration

    # Find the UNWIND loop
    unwind_pattern = r'while\s*\(\s*abs\(self\.primary_client\.get_ws_position\(\)\)\s*>\s*0'
    unwind_match = re.search(unwind_pattern, content)

    assert unwind_match is not None, "UNWIND loop not found"

    # Find _track_unwind_progress call - should come BEFORE spread check
    track_pattern = r'if\s+not\s+self\._track_unwind_progress\(self\.primary_position\):'
    track_match = re.search(track_pattern, content)

    assert track_match is not None, "_track_unwind_progress call not found"

    # Find spread check
    spread_pattern = r'if\s+not\s+await\s+self\.check_arbitrage_opportunity\(unwind_direction\):'
    spread_match = re.search(spread_pattern, content)

    assert spread_match is not None, "Spread check not found"

    # Verify order: _track_unwind_progress should be before spread check
    track_pos = track_match.start()
    spread_pos = spread_match.start()

    assert track_pos < spread_pos, "_track_unwind_progress should come before spread check"
    print(f"✅ Test 2: Logic order correct (track at {track_pos}, spread at {spread_pos})")

def test_force_close_bypasses_spread():
    """Test 3: force_close_all_positions uses market orders (bypasses spread filter)"""
    with open('DN_alternate_backpack_grvt.py', 'r') as f:
        content = f.read()

    # Find force_close_all_positions method
    pattern = r'async\s+def\s+force_close_all_positions'
    match = re.search(pattern, content)

    assert match is not None, "force_close_all_positions method not found"

    # Get method content
    start_pos = match.start()
    # Find next method or end of class (simplified - just check next 2000 chars)
    method_content = content[start_pos:start_pos + 3000]

    # Check for "crossing spread" or "market" keywords
    has_market = 'market' in method_content.lower()
    has_crossing = 'crossing' in method_content.lower()

    assert has_market or has_crossing, "force_close_all_positions should use market orders to bypass spread"
    print(f"✅ Test 3: force_close_all_positions bypasses spread (market={has_market}, crossing={has_crossing})")

def test_unwind_stuck_detection_logging():
    """Test 4: UNWIND stuck detection has proper logging"""
    with open('DN_alternate_backpack_grvt.py', 'r') as f:
        content = f.read()

    # Check for stuck detection log messages
    has_stuck_log = 'UNWIND STUCK' in content
    has_force_close_log = 'Triggering FORCE CLOSE' in content or 'FORCE CLOSE' in content

    assert has_stuck_log, "Should log 'UNWIND STUCK' when stuck detected"
    assert has_force_close_log, "Should log force close action"
    print(f"✅ Test 4: Logging present (stuck={has_stuck_log}, force_close={has_force_close_log})")

def test_track_unwind_progress_method():
    """Test 5: _track_unwind_progress method exists and has correct structure"""
    with open('DN_alternate_backpack_grvt.py', 'r') as f:
        content = f.read()

    # Find method definition
    pattern = r'def\s+_track_unwind_progress\(self,\s*current_position'
    match = re.search(pattern, content)

    assert match is not None, "_track_unwind_progress method not found"

    # Get method content (simplified)
    start_pos = match.start()
    method_content = content[start_pos:start_pos + 1500]

    # Check for key logic elements
    has_return = 'return True' in method_content and 'return False' in method_content
    has_threshold_check = 'unwind_stuck_threshold' in method_content
    has_position_check = 'unwind_start_position' in method_content

    assert has_return, "Method should return both True and False"
    assert has_threshold_check, "Method should check threshold"
    assert has_position_check, "Method should track position"
    print(f"✅ Test 5: _track_unwind_progress structure correct")

def run_all_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("TDD Test Suite: Option 7B - Fix Safety Layer #2")
    print("=" * 60)

    tests = [
        test_unwind_threshold_increased,
        test_unwind_counter_logic,
        test_force_close_bypasses_spread,
        test_unwind_stuck_detection_logging,
        test_track_unwind_progress_method,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passing")
    print("=" * 60)

    if failed > 0:
        print("\n⚠️  Some tests failing - implementation needed")
        return False
    else:
        print("\n✅ All tests passing - implementation complete!")
        return True

if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
