#!/usr/bin/env python3
"""
Calculate overall fill rate for trades.

This script reads a CSV file and calculates the fill rate based on
both primary_exit and hedge_exit being greater than 0.
"""

import csv
import sys
from pathlib import Path


def calculate_fill_rate(csv_path):
    """
    Calculate the fill rate for trades.

    A trade is considered filled if both primary_exit > 0 AND hedge_exit > 0.

    Args:
        csv_path: Path to the CSV file

    Returns:
        Fill rate percentage (0-100)
    """
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            total_trades = 0
            filled_trades = 0

            for row in reader:
                total_trades += 1

                # Check if both exits are filled (price > 0)
                primary_exit = row.get('primary_exit_price', '0')
                hedge_exit = row.get('hedge_exit_price', '0')

                try:
                    primary_exit_val = float(primary_exit) if primary_exit else 0
                    hedge_exit_val = float(hedge_exit) if hedge_exit else 0

                    if primary_exit_val > 0 and hedge_exit_val > 0:
                        filled_trades += 1
                except ValueError:
                    # Skip rows with invalid price data
                    continue

        if total_trades == 0:
            return 0.0

        fill_rate = (filled_trades / total_trades) * 100
        return fill_rate

    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 calculate_fill_rate.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not Path(csv_path).exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    fill_rate = calculate_fill_rate(csv_path)
    print(f"Overall Fill Rate: {fill_rate:.2f}%")
