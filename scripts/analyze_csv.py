#!/usr/bin/env python3
"""
CSV BUY/SELL Ratio Analyzer

Usage:
    python3 scripts/analyze_csv.py [csv_file]

Features:
- Analyzes trade CSV for BUY/SELL ratio
- Detects position accumulation (imbalance)
- Shows trade history and statistics
- Exits with code 1 if ratio imbalance > 2:1
"""

import sys
import os
import csv
from decimal import Decimal
from collections import defaultdict
from datetime import datetime


def analyze_csv(csv_file=None):
    """Analyze CSV file for BUY/SELL ratio."""
    # Find CSV file
    if csv_file is None:
        # Default to most recent CSV in current directory
        import glob
        csv_files = glob.glob("*.csv")
        if csv_files:
            csv_file = sorted(csv_files)[-1]
        else:
            print("No CSV file found")
            return 1

    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        return 1

    print("=" * 60)
    print("CSV BUY/SELL RATIO ANALYZER")
    print("=" * 60)
    print(f"File: {csv_file}")
    print("-" * 60)

    # Read CSV
    trades = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            trades = list(reader)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return 1

    if not trades:
        print("No trades found in CSV")
        return 0

    # Analyze trades
    eth_buys = 0
    eth_sells = 0
    sol_buys = 0
    sol_sells = 0

    eth_buy_qty = Decimal("0")
    eth_sell_qty = Decimal("0")
    sol_buy_qty = Decimal("0")
    sol_sell_qty = Decimal("0")

    for trade in trades:
        side = trade.get('side', '')
        qty = Decimal(trade.get('quantity', '0'))

        if 'ETH' in side:
            if 'BUY' in side.upper():
                eth_buys += 1
                eth_buy_qty += qty
            elif 'SELL' in side.upper():
                eth_sells += 1
                eth_sell_qty += qty

        elif 'SOL' in side:
            if 'BUY' in side.upper():
                sol_buys += 1
                sol_buy_qty += qty
            elif 'SELL' in side.upper():
                sol_sells += 1
                sol_sell_qty += qty

    # Display results
    print(f"\nETH Trades:")
    print(f"  BUY:  {eth_buys} trades (${eth_buy_qty:.2f})")
    print(f"  SELL: {eth_sells} trades (${eth_sell_qty:.2f})")
    if eth_buys + eth_sells > 0:
        eth_ratio = eth_buys / max(eth_sells, 1)
        print(f"  Ratio: {eth_ratio:.2f}:1 (BUY/SELL)")
        if eth_ratio > Decimal("2"):
            print(f"  [WARNING] ETH accumulation detected (ratio > 2:1)")
        elif eth_ratio < Decimal("0.5"):
            print(f"  [WARNING] ETH inverse accumulation detected (ratio < 0.5:1)")

    print(f"\nSOL Trades:")
    print(f"  BUY:  {sol_buys} trades (${sol_buy_qty:.2f})")
    print(f"  SELL: {sol_sells} trades (${sol_sell_qty:.2f})")
    if sol_buys + sol_sells > 0:
        sol_ratio = sol_buys / max(sol_sells, 1)
        print(f"  Ratio: {sol_ratio:.2f}:1 (BUY/SELL)")
        if sol_ratio > Decimal("2"):
            print(f"  [CRITICAL] SOL accumulation detected (ratio > 2:1)")
        elif sol_ratio < Decimal("0.5"):
            print(f"  [WARNING] SOL inverse accumulation detected (ratio < 0.5:1)")

    # Total imbalance
    print(f"\nTotal Trades: {len(trades)}")
    print(f"ETH Net Position: ${eth_buy_qty - eth_sell_qty:.2f}")
    print(f"SOL Net Position: ${sol_buy_qty - sol_sell_qty:.2f}")

    # Check for critical imbalance
    critical_imbalance = False

    if sol_buys > 0 and sol_sells > 0:
        sol_ratio = sol_buys / sol_sells
        if sol_ratio > Decimal("2"):
            print(f"\n[CRITICAL] SOL BUY/SELL ratio is {sol_ratio:.2f}:1 (> 2:1)")
            print(f"  SOL position accumulation detected!")
            critical_imbalance = True
        elif sol_ratio < Decimal("0.5"):
            print(f"\n[CRITICAL] SOL BUY/SELL ratio is {sol_ratio:.2f}:1 (< 0.5:1)")
            print(f"  SOL inverse accumulation detected!")
            critical_imbalance = True

    # Recent trades (last 10)
    print(f"\nRecent Trades (last 10):")
    for trade in trades[-10:]:
        timestamp = trade.get('timestamp', 'N/A')
        side = trade.get('side', 'N/A')
        qty = trade.get('quantity', '0')
        price = trade.get('price', '0')
        mode = trade.get('mode', 'NORMAL')
        print(f"  [{timestamp}] {side} {qty} @ ${price} ({mode})")

    if critical_imbalance:
        print("\n[CRITICAL] Position accumulation detected - manual intervention required")
        return 1

    print("\n[OK] BUY/SELL ratios within acceptable range")
    return 0


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(analyze_csv(csv_file))
