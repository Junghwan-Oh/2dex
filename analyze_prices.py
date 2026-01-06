#!/usr/bin/env python3
import csv

with open("logs/dn_paradex_grvt_SOL_trades.csv", "r") as f:
    reader = csv.DictReader(f)
    trades = list(reader)

print("Both-maker trades (Segment 3):")
print(f"{'Line':<6} {'Exch':<8} {'Side':<6} {'Price':<10} {'Type':<8} {'Mode':<12}")
print("-" * 56)
for i, t in enumerate(trades[86:98], start=87):
    print(
        f"{i:<6} {t['exchange']:<8} {t['side']:<6} {t['price']:<10} {t['order_type']:<8} {t['mode']:<12}"
    )

print()
print("Price comparison per pair:")
for i in range(86, 98, 2):
    primary = trades[i]
    hedge = trades[i + 1]
    p_price = float(primary["price"])
    h_price = float(hedge["price"])
    diff = h_price - p_price
    diff_bps = diff / p_price * 10000

    primary_side = primary["side"]
    if primary_side == "buy":
        edge = diff_bps
    else:
        edge = -diff_bps

    print(
        f"Primary {primary_side.upper()}: {p_price:.3f} | Hedge {hedge['side'].upper()}: {h_price:.3f} | Diff: {diff:+.3f} ({diff_bps:+.2f} bps) | Edge: {edge:+.2f} bps"
    )
