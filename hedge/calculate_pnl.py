# Phase 2B P&L 계산 (체결 가격 기준)
size = 0.02

# 체결 순서: PRIMARY SELL (OPEN) -> HEDGE BUY (OPEN) -> PRIMARY BUY (CLOSE) -> HEDGE SELL (CLOSE)
fills = [
    # CYCLE 1 OPEN
    ("PRIMARY", "SELL", 3149.65),
    ("HEDGE", "BUY", 3147.14),
    # CYCLE 2 CLOSE
    ("PRIMARY", "BUY", 3150.95),
    ("HEDGE", "SELL", 3148.38),
    # CYCLE 3 OPEN
    ("PRIMARY", "SELL", 3149.18),
    ("HEDGE", "BUY", 3146.80),
    # CYCLE 4 CLOSE
    ("PRIMARY", "BUY", 3149.39),
    ("HEDGE", "SELL", 3146.56),
    # CYCLE 5 OPEN
    ("PRIMARY", "SELL", 3149.01),
    ("HEDGE", "BUY", 3146.96),
    # CYCLE 6 CLOSE
    ("PRIMARY", "BUY", 3150.99),
    ("HEDGE", "SELL", 3148.06),
    # CYCLE 7 OPEN
    ("PRIMARY", "SELL", 3149.76),
    ("HEDGE", "BUY", 3148.08),
    # CYCLE 8 CLOSE
    ("PRIMARY", "BUY", 3151.31),
    ("HEDGE", "SELL", 3148.61),
    # CYCLE 9 OPEN
    ("PRIMARY", "SELL", 3151.06),
    ("HEDGE", "BUY", 3149.76),
    # CYCLE 10 CLOSE
    ("PRIMARY", "BUY", 3152.26),
    ("HEDGE", "SELL", 3149.81),
    # CYCLE 11 OPEN
    ("PRIMARY", "SELL", 3151.99),
    ("HEDGE", "BUY", 3150.25),
    # CYCLE 12 CLOSE
    ("PRIMARY", "BUY", 3155.95),
    ("HEDGE", "SELL", 3153.20),
    # CYCLE 13 OPEN
    ("PRIMARY", "SELL", 3154.69),
    ("HEDGE", "BUY", 3153.25),
    # CYCLE 14 CLOSE
    ("PRIMARY", "BUY", 3156.02),
    ("HEDGE", "SELL", 3152.66),
    # CYCLE 15 OPEN
    ("PRIMARY", "SELL", 3154.69),
    ("HEDGE", "BUY", 3152.62),
    # CYCLE 16 CLOSE
    ("PRIMARY", "BUY", 3156.01),
    ("HEDGE", "SELL", 3152.69),
    # CYCLE 17 OPEN
    ("PRIMARY", "SELL", 3152.30),
    ("HEDGE", "BUY", 3150.83),
    # CYCLE 18 CLOSE
    ("PRIMARY", "BUY", 3154.86),
    ("HEDGE", "SELL", 3152.52),
    # CYCLE 19 OPEN
    ("PRIMARY", "SELL", 3154.69),
    ("HEDGE", "BUY", 3152.88),
    # CYCLE 20 CLOSE
    ("PRIMARY", "BUY", 3156.59),
    ("HEDGE", "SELL", 3153.60),
]

print("=" * 80)
print("Phase 2B 테스트 결과: CYCLE별 P&L 보고 (가격 비교 로직)")
print("=" * 80)
print()

cumulative_pnl = 0
cycle_num = 1

for i in range(0, len(fills), 4):
    # OPEN
    primary_sell = fills[i][2]
    hedge_buy = fills[i+1][2]

    # CLOSE
    primary_buy = fills[i+2][2]
    hedge_sell = fills[i+3][2]

    # P&L 계산 (수수료 제외)
    pnl = (primary_sell - primary_buy) * size + (hedge_sell - hedge_buy) * size
    cumulative_pnl += pnl

    spread_open = primary_sell - hedge_buy
    spread_close = primary_buy - hedge_sell

    print(f"CYCLE {cycle_num} & {cycle_num+1}:")
    print(f"  [OPEN]  PRIMARY SELL {primary_sell:.2f}, HEDGE BUY {hedge_buy:.2f} (spread: +{spread_open:.2f})")
    print(f"  [CLOSE] PRIMARY BUY  {primary_buy:.2f}, HEDGE SELL {hedge_sell:.2f} (spread: +{spread_close:.2f})")
    print(f"  P&L: {pnl:+.4f} USDT (누적: {cumulative_pnl:+.4f} USDT)")
    print()

    cycle_num += 2

print("=" * 80)
print(f"최종 결과:")
print(f"  총 P&L (수수료 제외): {cumulative_pnl:+.4f} USDT")
print(f"  평균 사이클당 P&L: {cumulative_pnl/10:+.5f} USDT")
print("=" * 80)
