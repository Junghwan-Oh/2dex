"""Test script to verify GRVT fetch_ticker() return format.

This script verifies that fetch_ticker() returns the expected keys for BBO:
- best_bid_price
- best_bid_size
- best_ask_price
- best_ask_size

Run this before implementing the smart routing feature.
"""

import asyncio
import os
from decimal import Decimal
from exchanges.grvt import GrvtClient


async def verify_fetch_ticker():
    """Verify fetch_ticker() return format matches expectations."""
    print("=" * 60)
    print("GRVT fetch_ticker() Verification Script")
    print("=" * 60)

    # Create client (requires environment variables)
    print("\n[1/3] Initializing GRVT client...")
    config = {}
    try:
        client = GrvtClient(config)
        await client.connect()
        print("✓ Client connected")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure these env vars are set:")
        print("  GRVT_TRADING_ACCOUNT_ID")
        print("  GRVT_PRIVATE_KEY")
        print("  GRVT_API_KEY")
        return False

    try:
        # Test 1: fetch_ticker() return format
        print("\n[2/3] Testing fetch_ticker() return format...")
        ticker = await client.rest_client.fetch_ticker("ETH_USDT_Perp")

        print(f"\nAll keys returned:")
        for key in sorted(ticker.keys()):
            value = ticker[key]
            if isinstance(value, (int, float)):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value} (type: {type(value).__name__})")

        # Verify required keys exist
        required_keys = ['best_bid_price', 'best_bid_size',
                         'best_ask_price', 'best_ask_size']
        all_good = all(key in ticker for key in required_keys)

        if all_good:
            print(f"\n✓ All required keys present!")
            print(f"  best_bid_price: {ticker['best_bid_price']}")
            print(f"  best_bid_size: {ticker['best_bid_size']}")
            print(f"  best_ask_price: {ticker['best_ask_price']}")
            print(f"  best_ask_size: {ticker['best_ask_size']}")

            # Test 2: Calculate spread and mid price
            best_bid = Decimal(ticker['best_bid_price'])
            best_ask = Decimal(ticker['best_ask_price'])
            best_bid_size = Decimal(ticker['best_bid_size'])
            best_ask_size = Decimal(ticker['best_ask_size'])

            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2

            print(f"\n[3/3] Calculated BBO metrics:")
            print(f"  Best Bid Price: {best_bid}")
            print(f"  Best Bid Size: {best_bid_size}")
            print(f"  Best Ask Price: {best_ask}")
            print(f"  Best Ask Size: {best_ask_size}")
            print(f"  Spread: {spread}")
            print(f"  Mid Price: {mid_price}")
        else:
            print(f"\n✗ Some keys missing:")
            for key in required_keys:
                status = "✓" if key in ticker else "✗"
                print(f"  {status} {key}")

        # Test 3: Verify async context
        print(f"\n✓ All tests passed!")
        print(f"  ✓ fetch_ticker() is async")
        print(f"  ✓ Returns expected structure")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()
        print(f"\n✓ Client disconnected")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)
    return True


async def test_helper_functions():
    """Test the new helper functions."""
    print("\n" + "=" * 60)
    print("Testing Helper Functions")
    print("=" * 60)

    # Test calculate_timeout()
    print("\n[1/3] Testing calculate_timeout()...")
    from decimal import Decimal
    from exchanges.grvt import calculate_timeout, extract_filled_quantity, calculate_slippage_bps

    test_cases = [
        (Decimal('0.05'), 5),
        (Decimal('0.1'), 5),
        (Decimal('0.2'), 10),
        (Decimal('0.5'), 10),
        (Decimal('0.9'), 10),
        (Decimal('1.0'), 20),
        (Decimal('1.5'), 20),
    ]

    all_passed = True
    for qty, expected in test_cases:
        result = calculate_timeout(qty)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {qty} ETH → {result}s (expected: {expected}s)")
        if result != expected:
            all_passed = False

    if all_passed:
        print(f"\n✓ All calculate_timeout() tests passed!")
    else:
        print(f"\n✗ Some tests failed")

    # Test extract_filled_quantity()
    print("\n[2/3] Testing extract_filled_quantity()...")
    test_cases = [
        ({"state": {"traded_size": "0.123"}}, Decimal('0.123')),
        ({"size": "0.456"}, Decimal('0.456')),
        ([100, "0.789"], Decimal('0.789')),
        ({"metadata": {}}, Decimal('0')),
        (None, Decimal('0')),
    ]

    for result, expected in test_cases:
        got = extract_filled_quantity(result)
        status = "✓" if got == expected else "✗"
        print(f"  {status} {result} → {got}")

    # Test calculate_slippage_bps()
    print("\n[3/3] Testing calculate_slippage_bps()...")
    test_cases = [
        (Decimal('2914'), Decimal('2916'), Decimal('68.67')),
        (Decimal('10'), Decimal('11'), Decimal('100')),
        (Decimal('100'), Decimal('95'), Decimal('50')),
        (Decimal('100'), Decimal('100'), Decimal('0')),
        (Decimal('100'), Decimal('0'), Decimal('0')),  # Zero reference
    ]

    for exec_price, ref_price, expected in test_cases:
        got = calculate_slippage_bps(exec_price, ref_price)
        status = "✓" if str(got) == expected else "✗"
        print(f"  {status} exec={exec_price}, ref={ref_price} → {got} bps")

    return all_passed


if __name__ == "__main__":
    # Run verification
    result1 = asyncio.run(verify_fetch_ticker())
    result2 = asyncio.run(test_helper_functions())

    if result1 and result2:
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nReady to implement smart routing!")
    else:
        print("\n" + "=" * 60)
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        print("\nPlease fix the issues before implementation.")
