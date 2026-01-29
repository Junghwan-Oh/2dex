#!/usr/bin/env python3
"""
Calculate POST_ONLY fill rate for hedge_exit orders.

This script reads a CSV file and calculates the fill rate for POST_ONLY orders
on the hedge_exit side (CLOSE path).
"""

import csv
import sys
from pathlib import Path


def calculate_post_only_fill_rate(csv_path):
    """
    Calculate POST_ONLY fill rate for hedge exit orders.

    CORRECT FORMULA: Only count POST_ONLY orders on hedge_exit (CLOSE path).
    """
    post_only_total = 0
    post_only_filled = 0

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Only look at exit orders (CLOSE path)
                # CORRECTED: Check hedge_exit_order_type, not hedge_entry_order_type
                if row.get('hedge_exit_order_type') == 'POST_ONLY':
                    post_only_total += 1
                    if row.get('hedge_exit_fee_saved') == 'True':
                        post_only_filled += 1

        if post_only_total == 0:
            return 0.0

        fill_rate = (post_only_filled / post_only_total) * 100
        return fill_rate

    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 calculate_post_only_fill_rate.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not Path(csv_path).exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    fill_rate = calculate_post_only_fill_rate(csv_path)
    print(f"POST_ONLY Fill Rate (CLOSE path): {fill_rate:.2f}%")
