"""
Fix for extract_filled_quantity to handle list format in traded_size.

This script patches the function to handle:
- traded_size as list: ["0.5"] 
- traded_size as string: "0.25"
"""

# The fix: Handle list format in traded_size
fixed_code = '''def extract_filled_quantity(order_result: dict) -> Decimal:
    """Extract filled quantity from order result.

    Handles various order result formats:
    - dict with 'state/traded_size' (list or string format)
    - dict with 'size'
    - list/tuple format [price, size]
    - dict with 'metadata' (market orders return 0)

    Args:
        order_result: Order result from REST or WebSocket API

    Returns:
        Filled quantity as Decimal, or 0 if extraction fails
    """
    try:
        # Try direct key access first (WebSocket RPC raw_rest_response format)
        if 'state' in order_result and 'traded_size' in order_result['state']:
            traded_size = order_result['state']['traded_size']
            # Handle list format: ["0.5"]
            if isinstance(traded_size, list):
                return Decimal(traded_size[0]) if len(traded_size) > 0 else Decimal('0')
            # Handle string format: "0.5"
            return Decimal(traded_size)

        # Try metadata access (WebSocket format - market orders don't have metadata)
        if 'metadata' in order_result:
            return Decimal('0')

        # Try list format [price, size]
        if isinstance(order_result, (list, tuple)) and len(order_result) >= 2:
            return Decimal(order_result[1])

        # Try dict format {'price': ..., 'size': ...}
        if isinstance(order_result, dict):
            if 'size' in order_result:
                return Decimal(order_result['size'])
            if 'traded_size' in order_result:
                traded_size = order_result['traded_size']
                # Handle list format at top level
                if isinstance(traded_size, list):
                    return Decimal(traded_size[0]) if len(traded_size) > 0 else Decimal('0')
                return Decimal(traded_size)

        return Decimal('0')

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return Decimal('0')
'''

print("FIXED CODE:")
print("=" * 80)
print(fixed_code)
print("=" * 80)
print()
print("KEY CHANGES:")
print("- Added list format handling for traded_size in state")
print("- Added list format handling for traded_size at top level")
print("- Maintains backward compatibility with string format")
print()

# Test the fix
from decimal import Decimal

def extract_filled_quantity_fixed(order_result: dict) -> Decimal:
    """Fixed version with list format support."""
    try:
        # Try direct key access first (WebSocket RPC raw_rest_response format)
        if 'state' in order_result and 'traded_size' in order_result['state']:
            traded_size = order_result['state']['traded_size']
            # Handle list format: ["0.5"]
            if isinstance(traded_size, list):
                return Decimal(traded_size[0]) if len(traded_size) > 0 else Decimal('0')
            # Handle string format: "0.5"
            return Decimal(traded_size)

        # Try metadata access (WebSocket format - market orders don't have metadata)
        if 'metadata' in order_result:
            return Decimal('0')

        # Try list format [price, size]
        if isinstance(order_result, (list, tuple)) and len(order_result) >= 2:
            return Decimal(order_result[1])

        # Try dict format {'price': ..., 'size': ...}
        if isinstance(order_result, dict):
            if 'size' in order_result:
                return Decimal(order_result['size'])
            if 'traded_size' in order_result:
                traded_size = order_result['traded_size']
                # Handle list format at top level
                if isinstance(traded_size, list):
                    return Decimal(traded_size[0]) if len(traded_size) > 0 else Decimal('0')
                return Decimal(traded_size)

        return Decimal('0')

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return Decimal('0')


# Run tests
print("TESTING FIXED VERSION:")
print("=" * 80)
print()

test_cases = [
    {
        'name': 'List format in state',
        'input': {'state': {'traded_size': ['0.5']}},
        'expected': Decimal('0.5')
    },
    {
        'name': 'String format in state',
        'input': {'state': {'traded_size': '0.25'}},
        'expected': Decimal('0.25')
    },
    {
        'name': 'No traded_size',
        'input': {'state': {'status': 'OPEN'}},
        'expected': Decimal('0')
    },
    {
        'name': 'List format at top level',
        'input': {'traded_size': ['1.0']},
        'expected': Decimal('1.0')
    },
    {
        'name': 'String format at top level',
        'input': {'traded_size': '0.75'},
        'expected': Decimal('0.75')
    }
]

all_passed = True
for test in test_cases:
    result = extract_filled_quantity_fixed(test['input'])
    passed = result == test['expected']
    all_passed = all_passed and passed
    
    status = "PASS" if passed else "FAIL"
    print(f"{status}: {test['name']}")
    print(f"  Input:    {test['input']}")
    print(f"  Expected: {test['expected']}")
    print(f"  Got:      {result}")
    print()

print("=" * 80)
if all_passed:
    print("ALL TESTS PASSED!")
else:
    print("SOME TESTS FAILED!")
print("=" * 80)
