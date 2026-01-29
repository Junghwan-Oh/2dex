#!/usr/bin/env python3
"""
Calculate PnL improvement between baseline and feature runs.

CORRECTED: Includes quantity, direction (BUY_FIRST/SELL_FIRST), and delta-neutral hedge logic.
"""

import csv
import sys
import argparse
from pathlib import Path
from decimal import Decimal


def calculate_pnl_from_csv(csv_path):
    """
    Calculate total PnL from CSV file - CORRECTED FORMULA with FEES.

    Includes:
    - Quantity (fixed at 0.2 ETH per trade)
    - Direction (BUY_FIRST vs SELL_FIRST)
    - Delta-neutral hedge (opposite sides)
    - Trading fees (0.04% taker for MARKET, 0% maker for POST_ONLY)
    """
    total_pnl = Decimal('0')
    quantity = Decimal('0.2')  # Default order size
    taker_fee_rate = Decimal('0.0004')  # 0.04% taker fee
    maker_fee_rate = Decimal('0.0')  # 0% maker fee (POST_ONLY)

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

                        # Calculate fees for hedge side only (primary exchange fees assumed same)
                        hedge_exit_order_type = row.get('hedge_exit_order_type', 'MARKET')
                        if hedge_exit_order_type == 'POST_ONLY':
                            # Check if POST_ONLY was filled (fee saved)
                            fee_saved = row.get('hedge_exit_fee_saved', 'False') == 'True'
                            if fee_saved:
                                hedge_fee_rate = maker_fee_rate  # 0% fee
                            else:
                                hedge_fee_rate = taker_fee_rate  # Fell back to taker
                        else:
                            hedge_fee_rate = taker_fee_rate  # MARKET order

                        # Calculate hedge fee (applied to notional value)
                        hedge_notional = hedge_exit * quantity
                        hedge_fee = hedge_notional * hedge_fee_rate

                        # Total PnL for this trade (subtract fees)
                        trade_pnl = primary_pnl + hedge_pnl - hedge_fee
                        total_pnl += trade_pnl

                except Exception as e:
                    print(f"Warning: Skipping row due to error: {e}", file=sys.stderr)
                    continue

    except FileNotFoundError:
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    return total_pnl


def calculate_pnl_improvement_bps(before_csv, after_csv):
    """Calculate PnL improvement in basis points."""
    before_pnl = calculate_pnl_from_csv(before_csv)
    after_pnl = calculate_pnl_from_csv(after_csv)

    # Calculate improvement
    improvement = after_pnl - before_pnl

    # Convert to bps (assuming ~$3000 ETH price, 0.2 ETH size, 20 trades)
    eth_price_approx = Decimal('3000')
    volume_approx = Decimal('20') * Decimal('0.2') * eth_price_approx

    if volume_approx > 0:
        improvement_bps = (improvement / volume_approx) * Decimal('10000')
    else:
        improvement_bps = Decimal('0')

    return float(improvement_bps)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate PnL improvement between two CSV files')
    parser.add_argument('--before', required=True, help='Baseline CSV file')
    parser.add_argument('--after', required=True, help='Feature CSV file')

    args = parser.parse_args()

    # Validate files exist
    if not Path(args.before).exists():
        print(f"Error: Baseline file not found: {args.before}")
        sys.exit(1)

    if not Path(args.after).exists():
        print(f"Error: Feature file not found: {args.after}")
        sys.exit(1)

    # Calculate PnL for both files
    before_pnl = calculate_pnl_from_csv(args.before)
    after_pnl = calculate_pnl_from_csv(args.after)

    # Calculate improvement
    improvement = after_pnl - before_pnl
    improvement_bps = calculate_pnl_improvement_bps(args.before, args.after)

    # Print results
    print("PnL Comparison")
    print("=" * 60)
    print(f"Baseline PnL:   ${before_pnl:.4f}")
    print(f"Feature PnL:    ${after_pnl:.4f}")
    print(f"Improvement:    ${improvement:+.4f} ({improvement_bps:+.2f} bps)")
