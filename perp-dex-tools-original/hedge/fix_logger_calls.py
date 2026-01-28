# Fix logger calls in place_iterative_market_order
import re

with open('exchanges/grvt.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all self.logger.info() calls in the iterative method
# Need to be careful to only fix the ones in place_iterative_market_order

old_patterns = [
    '''        self.logger.info(
            f"[ITERATIVE] Starting {side.upper()} {target_quantity} ETH fill"
        )''',
    '''        self.logger.error(f"[ITERATIVE] {reason}")''',
    '''            self.logger.info(
                f"[ITERATIVE] Iteration {iteration}: Placing market order for {remaining} ETH "
                f"@ ${adjusted_price:.2f} (offset: {tick_offset} ticks)"
            )''',
    '''                    self.logger.error(
                        f"[ITERATIVE] Market order failed: {e}"
                    )''',
    '''                self.logger.info(
                    f"[ITERATIVE] Iteration {iteration}: Filled {filled_quantity} @ ${fill_price:.2f} "
                    f"(offset: {tick_offset} ticks, total: {total_filled}/{target_quantity})"
                )''',
    '''                    self.logger.warning(
                        f"[ITERATIVE] Partial fill: {filled_quantity}/{remaining} ETH filled"
                    )''',
    '''                self.logger.error(
                    f"[ITERATIVE] {reason}"
                )''',
    '''        self.logger.info(
            f"[ITERATIVE] Successfully filled {total_filled}/{target_quantity} ETH "
            f"@ ${sum(price_history) / len(price_history):.2f} "
            f"({len(price_history)} iterations, {iteration - 1} retries)"
        )''',
    '''        self.logger.error(
            f"[ITERATIVE] Failed to fill {target_quantity} ETH: {reason}"
        )'''
]

new_patterns = [
    '''        self.logger.log(
            f"[ITERATIVE] Starting {side.upper()} {target_quantity} ETH fill",
            "INFO"
        )''',
    '''        self.logger.log(f"[ITERATIVE] {reason}", "ERROR")''',
    '''            self.logger.log(
                f"[ITERATIVE] Iteration {iteration}: Placing market order for {remaining} ETH "
                f"@ ${adjusted_price:.2f} (offset: {tick_offset} ticks)",
                "INFO"
            )''',
    '''                    self.logger.log(
                        f"[ITERATIVE] Market order failed: {e}",
                        "ERROR"
                    )''',
    '''                self.logger.log(
                    f"[ITERATIVE] Iteration {iteration}: Filled {filled_quantity} @ ${fill_price:.2f} "
                    f"(offset: {tick_offset} ticks, total: {total_filled}/{target_quantity})",
                    "INFO"
                )''',
    '''                    self.logger.log(
                        f"[ITERATIVE] Partial fill: {filled_quantity}/{remaining} ETH filled",
                        "WARNING"
                    )''',
    '''                self.logger.log(
                    f"[ITERATIVE] {reason}",
                    "ERROR"
                )''',
    '''        self.logger.log(
            f"[ITERATIVE] Successfully filled {total_filled}/{target_quantity} ETH "
            f"@ ${sum(price_history) / len(price_history):.2f} "
            f"({len(price_history)} iterations, {iteration - 1} retries)",
            "INFO"
        )''',
    '''        self.logger.log(
            f"[ITERATIVE] Failed to fill {target_quantity} ETH: {reason}",
            "ERROR"
        )'''
]

for old, new in zip(old_patterns, new_patterns):
    content = content.replace(old, new)

with open('exchanges/grvt.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('SUCCESS: Fixed all logger.info() calls to logger.log() in place_iterative_market_order')
