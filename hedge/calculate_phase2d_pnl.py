# Phase 2D P&L Calculation (Partial Test - 4 Cycles)
size = 0.02

# Fill data from Phase 2D partial test (4 cycles from timeout)
fills = [
    # CYCLE 1 OPEN
    ("PRIMARY", "BUY", 3140.90),
    ("HEDGE", "SELL", 3138.02),
    # CYCLE 2 CLOSE
    ("PRIMARY", "SELL", 3139.68),
    ("HEDGE", "BUY", 3138.27),
    # CYCLE 3 OPEN
    ("PRIMARY", "BUY", 3139.79),
    ("HEDGE", "SELL", 3137.40),
    # CYCLE 4 CLOSE
    ("PRIMARY", "SELL", 3134.88),
    ("HEDGE", "BUY", 3133.72),
]

print("=" * 80)
print("Phase 2D Test Results: CYCLE-by-CYCLE P&L Analysis (MOMENTUM STRATEGY)")
print("=" * 80)
print()
print("CONTEXT:")
print("  - Phase 2B (mean reversion): -0.1958 USDT across 10 cycles (100% loss rate)")
print("  - Phase 2D (momentum): REVERSED direction logic")
print("  - Test TIMEOUT after 4 cycles (partial results)")
print()
print("=" * 80)
print()

cumulative_pnl = 0
cycle_num = 1

for i in range(0, len(fills), 4):
    # OPEN
    primary_buy = fills[i][2]
    hedge_sell = fills[i+1][2]

    # CLOSE
    primary_sell = fills[i+2][2]
    hedge_buy = fills[i+3][2]

    # P&L calculation (excluding fees)
    # PRIMARY: Buy low, sell high → profit if sell > buy
    # HEDGE: Sell high, buy low → profit if sell > buy
    pnl_primary = (primary_sell - primary_buy) * size
    pnl_hedge = (hedge_sell - hedge_buy) * size
    pnl = pnl_primary + pnl_hedge
    cumulative_pnl += pnl

    spread_open = primary_buy - hedge_sell
    spread_close = primary_sell - hedge_buy

    print(f"CYCLE {cycle_num} & {cycle_num+1}:")
    print(f"  [OPEN]  PRIMARY BUY  {primary_buy:.2f}, HEDGE SELL {hedge_sell:.2f} (spread: +{spread_open:.2f})")
    print(f"  [CLOSE] PRIMARY SELL {primary_sell:.2f}, HEDGE BUY  {hedge_buy:.2f} (spread: +{spread_close:.2f})")
    print(f"  P&L Breakdown:")
    print(f"    PRIMARY: ({primary_sell:.2f} - {primary_buy:.2f}) × {size} = {pnl_primary:+.4f} USDT")
    print(f"    HEDGE:   ({hedge_sell:.2f} - {hedge_buy:.2f}) × {size} = {pnl_hedge:+.4f} USDT")
    print(f"  Total P&L: {pnl:+.4f} USDT (Cumulative: {cumulative_pnl:+.4f} USDT)")

    # Determine if profitable
    status = "[PROFIT]" if pnl > 0 else "[LOSS]"
    print(f"  Result: {status}")
    print()

    cycle_num += 2

print("=" * 80)
print(f"FINAL RESULTS (Partial - 4 Cycles):")
print(f"  Total P&L (excl. fees): {cumulative_pnl:+.4f} USDT")
print(f"  Average per cycle pair: {cumulative_pnl/2:+.5f} USDT")
print()
print("COMPARISON TO PHASE 2B:")
print(f"  Phase 2B (10 cycles): -0.1958 USDT total, -0.01958 USDT per cycle pair")
print(f"  Phase 2D (4 cycles):  {cumulative_pnl:+.4f} USDT total, {cumulative_pnl/2:+.5f} USDT per cycle pair")
print()
if cumulative_pnl > 0:
    print("[SUCCESS] Phase 2D shows POSITIVE P&L (momentum hypothesis validated)")
    print("   - Gap expansion strategy appears to work")
    print("   - Need full 20-cycle test for statistical confidence")
else:
    print("[CONCERN] Phase 2D still shows negative P&L")
    print("   - Momentum hypothesis may need refinement")
    print("   - Test was incomplete (timeout), may not be representative")
print("=" * 80)
