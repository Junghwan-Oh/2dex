#!/usr/bin/env python3
"""
Calculate PnL from trade metrics CSV file.

CORRECTED: Includes quantity, direction (BUY_FIRST/SELL_FIRST), and delta-neutral hedge logic.
"""

import csv
import sys
import argparse
from pathlib import Path
from decimal import Decimal


def calculate_pnl_from_csv(csv_path):
    """
    Calculate total PnL from CSV file - CORRECTED FORMULA.

    Includes:
    - Quantity (fixed at 0.2 ETH per trade)
    - Direction (BUY_FIRST vs SELL_FIRST)
    - Delta-neutral hedge (opposite sides)
    """
    total_pnl = Decimal('0')
    total_primary_pnl = Decimal('0')
    total_hedge_pnl = Decimal('0')
    quantity = Decimal('0.2')  # Default order size

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Only count completed trades
                    primary_exit = Decimal(row.get('primary_exit_price', '0'))
                    hedge_exit = Decimal(row.get('hedge_exit_price', '0'))

                    if primary_exit > 0 and hedge_exit > 0:
                        primary_entry = Decimal(row.get('primary_entry_price', '0'))
                        hedge_entry = Decimal(row.get('hedge_entry_price', '0'))
                        direction = row.get('direction', 'BUY_FIRST')

                        # Direction multiplier: BUY_FIRST = +1, SELL_FIRST = -1
                        direction_multiplier = Decimal('1') if direction == 'BUY_FIRST' else Decimal('-1')

                        # Primary PnL: (exit - entry) * quantity * direction
                        primary_pnl = (primary_exit - primary_entry) * quantity * direction_multiplier

                        # Hedge PnL: (entry - exit) * quantity * direction (hedge is opposite side)
                        hedge_pnl = (hedge_entry - hedge_exit) * quantity * direction_multiplier

                        # Total PnL for this trade
                        trade_pnl = primary_pnl + hedge_pnl
                        total_pnl += trade_pnl
                        total_primary_pnl += primary_pnl
                        total_hedge_pnl += hedge_pnl

                except Exception as e:
                    print(f"Warning: Skipping row due to error: {e}", file=sys.stderr)
                    continue

    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    return total_pnl, total_primary_pnl, total_hedge_pnl


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate PnL from trade metrics CSV file')
    parser.add_argument('csv_file', help='Path to the CSV file containing trade data')

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.csv_file).exists():
        print(f"Error: File not found: {args.csv_file}")
        sys.exit(1)

    # Calculate PnL
    total_pnl, primary_pnl, hedge_pnl = calculate_pnl_from_csv(args.csv_file)

    # Print results
    print("PnL Analysis")
    print("=" * 60)
    print(f"Primary PnL:  ${primary_pnl:.4f}")
    print(f"Hedge PnL:    ${hedge_pnl:.4f}")
    print(f"Total PnL:    ${total_pnl:.4f}")
