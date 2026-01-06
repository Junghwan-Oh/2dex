#!/usr/bin/env python3
"""
Trade Analysis Script for DN Paradex+GRVT Bot

Analyzes CSV trade logs to calculate:
- PnL per exchange (from position changes)
- Fee estimates
- Spread analysis between exchanges
- Position tracking
"""

import csv
import argparse
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict


# Fee rates (in decimal, e.g., 0.0002 = 0.02% = 2bps)
FEE_RATES = {
    "PARADEX": {
        "maker": Decimal("0.0002"),  # 2bps maker
        "taker": Decimal("0.0005"),  # 5bps taker
    },
    "GRVT": {
        "maker": Decimal("0.0001"),  # 1bps maker (estimated)
        "taker": Decimal("0.0005"),  # 5bps taker
    },
}


def parse_csv(filepath: str) -> List[Dict]:
    """Parse CSV file into list of trade dicts."""
    trades = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(
                {
                    "exchange": row["exchange"],
                    "timestamp": row["timestamp"],
                    "side": row["side"],
                    "price": Decimal(row["price"]),
                    "quantity": Decimal(row["quantity"]),
                    "order_type": row["order_type"],
                    "mode": row["mode"],
                }
            )
    return trades


def estimate_fee(
    exchange: str, price: Decimal, quantity: Decimal, is_maker: bool
) -> Decimal:
    """Estimate fee for a trade."""
    notional = price * quantity
    fee_type = "maker" if is_maker else "taker"
    fee_rate = FEE_RATES.get(exchange, {}).get(fee_type, Decimal("0.0005"))
    return notional * fee_rate


def analyze_trades(
    trades: List[Dict], start_line: int = 1, end_line: int = None
) -> Dict:
    """
    Analyze a subset of trades.

    Returns dict with:
    - pnl_by_exchange: realized PnL per exchange
    - fees_by_exchange: estimated fees per exchange
    - final_position: ending position per exchange
    - trade_count: number of trades per exchange
    - volume: total notional volume per exchange
    """
    if end_line is None:
        end_line = len(trades)

    # Filter to requested range (1-indexed)
    subset = trades[start_line - 1 : end_line]

    # Track position and cost basis per exchange
    positions = defaultdict(
        Decimal
    )  # exchange -> quantity (positive=long, negative=short)
    cost_basis = defaultdict(Decimal)  # exchange -> total cost (in USD)
    realized_pnl = defaultdict(Decimal)  # exchange -> realized PnL
    fees = defaultdict(Decimal)  # exchange -> total fees
    volumes = defaultdict(Decimal)  # exchange -> notional volume
    trade_counts = defaultdict(int)  # exchange -> count

    for trade in subset:
        exchange = trade["exchange"]
        price = trade["price"]
        quantity = trade["quantity"]
        side = trade["side"]
        mode = trade["mode"]

        # Determine if maker or taker
        is_maker = (
            mode in ["bbo_minus_1", "bbo_plus_1"] and trade["order_type"] == "primary"
        )
        # Hedge orders that use market mode are taker
        if mode == "market":
            is_maker = False
        # Both maker mode: both sides are maker
        if mode == "bbo_minus_1" and trade["order_type"] == "hedge":
            is_maker = True

        notional = price * quantity
        volumes[exchange] += notional
        trade_counts[exchange] += 1

        # Estimate and accumulate fee
        fee = estimate_fee(exchange, price, quantity, is_maker)
        fees[exchange] += fee

        # Position tracking with FIFO PnL calculation
        current_pos = positions[exchange]

        if side == "buy":
            trade_qty = quantity
        else:
            trade_qty = -quantity

        # Check if this trade increases or decreases position
        if current_pos == 0:
            # Opening new position
            positions[exchange] = trade_qty
            cost_basis[exchange] = price * abs(trade_qty)
        elif (current_pos > 0 and trade_qty > 0) or (current_pos < 0 and trade_qty < 0):
            # Adding to position (same direction)
            positions[exchange] += trade_qty
            cost_basis[exchange] += price * abs(trade_qty)
        else:
            # Reducing or flipping position
            close_qty = min(abs(current_pos), abs(trade_qty))

            # Calculate avg cost of existing position
            if current_pos != 0:
                avg_cost = cost_basis[exchange] / abs(current_pos)
            else:
                avg_cost = Decimal("0")

            # Realized PnL
            if current_pos > 0:  # Was long, now selling
                pnl = (price - avg_cost) * close_qty
            else:  # Was short, now buying
                pnl = (avg_cost - price) * close_qty

            realized_pnl[exchange] += pnl

            # Update position
            remaining = abs(trade_qty) - close_qty
            if abs(trade_qty) <= abs(current_pos):
                # Just reducing
                positions[exchange] += trade_qty
                # Reduce cost basis proportionally
                if current_pos != 0:
                    cost_basis[exchange] *= Decimal("1") - close_qty / abs(current_pos)
            else:
                # Flipping position
                positions[exchange] = trade_qty + current_pos  # net position
                cost_basis[exchange] = price * remaining

    return {
        "pnl_by_exchange": dict(realized_pnl),
        "fees_by_exchange": dict(fees),
        "final_position": dict(positions),
        "trade_count": dict(trade_counts),
        "volume": dict(volumes),
        "trade_range": (start_line, end_line),
        "num_trades": len(subset),
    }


def print_analysis(result: Dict, title: str = "Analysis"):
    """Pretty print analysis results."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")
    print(f"Trade range: lines {result['trade_range'][0]} - {result['trade_range'][1]}")
    print(f"Total trades: {result['num_trades']}")
    print()

    total_pnl = Decimal("0")
    total_fees = Decimal("0")
    total_volume = Decimal("0")

    for exchange in set(
        list(result["pnl_by_exchange"].keys())
        + list(result["fees_by_exchange"].keys())
        + list(result["volume"].keys())
    ):
        pnl = result["pnl_by_exchange"].get(exchange, Decimal("0"))
        fee = result["fees_by_exchange"].get(exchange, Decimal("0"))
        vol = result["volume"].get(exchange, Decimal("0"))
        pos = result["final_position"].get(exchange, Decimal("0"))
        count = result["trade_count"].get(exchange, 0)

        total_pnl += pnl
        total_fees += fee
        total_volume += vol

        print(f"[{exchange}]")
        print(f"  Trades:        {count}")
        print(f"  Volume:        ${vol:.2f}")
        print(f"  Realized PnL:  ${pnl:.4f}")
        print(f"  Est. Fees:     ${fee:.4f}")
        print(f"  Net PnL:       ${pnl - fee:.4f}")
        print(f"  Final Pos:     {pos:.4f}")
        print()

    print("-" * 40)
    print(f"TOTAL Volume:      ${total_volume:.2f}")
    print(f"TOTAL Realized:    ${total_pnl:.4f}")
    print(f"TOTAL Est. Fees:   ${total_fees:.4f}")
    print(f"TOTAL Net PnL:     ${total_pnl - total_fees:.4f}")

    # Calculate effective cost
    if total_volume > 0:
        cost_bps = (total_fees - total_pnl) / total_volume * 10000
        print(f"Effective cost:    {cost_bps:.2f} bps")


def analyze_spread(trades: List[Dict]) -> None:
    """Analyze price spread between primary and hedge trades."""
    print(f"\n{'=' * 60}")
    print(" Spread Analysis (Primary vs Hedge)")
    print(f"{'=' * 60}")

    # Group trades into pairs
    i = 0
    spreads = []

    while i < len(trades) - 1:
        primary = trades[i]
        hedge = trades[i + 1]

        if primary["order_type"] == "primary" and hedge["order_type"] == "hedge":
            primary_price = primary["price"]
            hedge_price = hedge["price"]

            # Spread in bps
            spread_bps = abs(hedge_price - primary_price) / primary_price * 10000

            # Direction matters for whether spread is favorable
            if primary["side"] == "buy":
                # We buy on primary, sell on hedge
                # Favorable if hedge_price > primary_price
                favorable = hedge_price >= primary_price
                edge = (hedge_price - primary_price) / primary_price * 10000
            else:
                # We sell on primary, buy on hedge
                # Favorable if hedge_price < primary_price
                favorable = hedge_price <= primary_price
                edge = (primary_price - hedge_price) / primary_price * 10000

            spreads.append(
                {
                    "primary_price": primary_price,
                    "hedge_price": hedge_price,
                    "spread_bps": spread_bps,
                    "edge_bps": edge,
                    "favorable": favorable,
                    "mode": hedge["mode"],
                }
            )
            i += 2
        else:
            i += 1

    if not spreads:
        print("No valid trade pairs found.")
        return

    # Separate by mode
    by_mode = defaultdict(list)
    for s in spreads:
        by_mode[s["mode"]].append(s)

    for mode, mode_spreads in by_mode.items():
        avg_spread = sum(s["spread_bps"] for s in mode_spreads) / len(mode_spreads)
        avg_edge = sum(s["edge_bps"] for s in mode_spreads) / len(mode_spreads)
        favorable_count = sum(1 for s in mode_spreads if s["favorable"])

        print(f"\nMode: {mode}")
        print(f"  Pairs:           {len(mode_spreads)}")
        print(f"  Avg Spread:      {avg_spread:.2f} bps")
        print(f"  Avg Edge:        {avg_edge:.2f} bps")
        print(
            f"  Favorable:       {favorable_count}/{len(mode_spreads)} ({favorable_count / len(mode_spreads) * 100:.1f}%)"
        )


def main():
    parser = argparse.ArgumentParser(description="Analyze DN bot trades")
    parser.add_argument(
        "--csv", default="logs/dn_paradex_grvt_SOL_trades.csv", help="Path to CSV file"
    )
    parser.add_argument(
        "--start", type=int, default=1, help="Start line (1-indexed, inclusive)"
    )
    parser.add_argument(
        "--end", type=int, default=None, help="End line (1-indexed, inclusive)"
    )
    parser.add_argument("--spread", action="store_true", help="Include spread analysis")
    parser.add_argument(
        "--all-tests", action="store_true", help="Analyze all test segments separately"
    )
    args = parser.parse_args()

    trades = parse_csv(args.csv)
    print(f"Loaded {len(trades)} trades from {args.csv}")

    if args.all_tests:
        # Analyze known test segments based on summary
        # Test 1: lines 1-85 (Paradex maker, GRVT market hedge)
        # Test 3: lines 86-99 (both maker mode)

        # But let's detect segments by timestamp gaps
        segments = []
        current_start = 0

        for i in range(1, len(trades)):
            prev_ts = datetime.fromisoformat(
                trades[i - 1]["timestamp"].replace("+00:00", "+00:00")
            )
            curr_ts = datetime.fromisoformat(
                trades[i]["timestamp"].replace("+00:00", "+00:00")
            )

            gap = (curr_ts - prev_ts).total_seconds()
            if gap > 300:  # 5 minute gap = new segment
                segments.append((current_start + 1, i))  # 1-indexed
                current_start = i

        segments.append((current_start + 1, len(trades)))  # Last segment

        print(f"\nDetected {len(segments)} test segments:")
        for i, (start, end) in enumerate(segments, 1):
            mode = trades[start - 1]["mode"]
            hedge_mode = trades[start]["mode"] if start < len(trades) else "unknown"
            print(
                f"  Segment {i}: lines {start}-{end} (primary: {mode}, hedge: {hedge_mode})"
            )

        for i, (start, end) in enumerate(segments, 1):
            result = analyze_trades(trades, start, end)
            print_analysis(result, f"Segment {i} Analysis")

        if args.spread:
            analyze_spread(trades)
    else:
        result = analyze_trades(trades, args.start, args.end)
        print_analysis(result, "Trade Analysis")

        if args.spread:
            subset = (
                trades[args.start - 1 : args.end]
                if args.end
                else trades[args.start - 1 :]
            )
            analyze_spread(subset)


if __name__ == "__main__":
    main()
