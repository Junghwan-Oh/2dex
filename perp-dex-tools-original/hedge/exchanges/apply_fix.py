"""
Apply the fix to extract_filled_quantity function in grvt.py
"""

import re

# Read the current file with UTF-8 encoding
with open('grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The old function pattern
old_function = '''def extract_filled_quantity(order_result: dict) -> Decimal:
    """Extract filled quantity from order result.

    Handles various order result formats:
    - dict with 'state/traded_size'
    - dict with 'size'
    - list/tuple format [price, size]
    - dict with 'metadata' (market orders return 0)

    Args:
        order_result: Order result from REST or WebSocket API

    Returns:
        Filled quantity as Decimal, or 0 if extraction fails
    """
    try:
        # Try direct key access first
        if 'state' in order_result and 'traded_size' in order_result['state']:
            return Decimal(order_result['state']['traded_size'])

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
                return Decimal(order_result['traded_size'])

        return Decimal('0')

    except (KeyError, IndexError, TypeError, ValueError) as e:
        return Decimal('0')'''

# The new fixed function
new_function = '''def extract_filled_quantity(order_result: dict) -> Decimal:
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
        return Decimal('0')'''

# Replace the function
new_content = content.replace(old_function, new_function)

# Write back
with open('grvt.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fix applied successfully!")
print()
print("Changes made:")
print("- Added list format handling for traded_size in state")
print("- Added list format handling for traded_size at top level")
print("- Maintains backward compatibility with string format")
