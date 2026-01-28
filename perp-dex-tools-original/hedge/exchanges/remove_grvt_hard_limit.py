# Read the file
with open('grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the hard 0.2 ETH limit check since we're using iterative approach
old_limit_check = '''        # OMC v4: GRVT liquidity limit enforcement
        MAX_GRVT_ORDER_SIZE = Decimal("0.2")  # 0.2 ETH maximum based on testing
        if quantity > MAX_GRVT_ORDER_SIZE:
            raise ValueError(
                f"[SAFETY] GRVT order size {quantity} ETH exceeds maximum {MAX_GRVT_ORDER_SIZE} ETH. "
                f"Testing shows GRVT cannot reliably fill orders >0.2 ETH. "
                f"Please split into smaller orders or reduce quantity."
            )

'''

new_limit_comment = '''        # NOTE: Hard 0.2 ETH limit removed - using iterative market order approach instead
        # The place_iterative_market_order method handles large orders by:
        # 1. Consuming available liquidity at current price
        # 2. Retrying at 1-tick worse prices until filled
        # 3. This achieves higher fill rates for orders >0.2 ETH

'''

content = content.replace(old_limit_check, new_limit_comment)

# Write the updated content
with open('grvt.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('SUCCESS: Removed hard 0.2 ETH limit from place_market_order')
print('Iterative approach now handles orders of any size')
