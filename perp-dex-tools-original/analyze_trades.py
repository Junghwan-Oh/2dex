#!/usr/bin/env python3
"""
2DEX Trade Analysis Script
Analyzes CSV trade data for PnL, fill prices, and spread analysis.
"""

import csv
from decimal import Decimal
from datetime import datetime
from collections import defaultdict

def parseTimestamp(tsStr):
    """Parse ISO timestamp string."""
    return datetime.fromisoformat(tsStr.replace('+00:00', '+00:00'))

def analyzeTrades(csvPath):
    """Analyze trade data from CSV file."""

    trades = []
    with open(csvPath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append({
                'exchange': row['exchange'],
                'role': row['role'],
                'timestamp': row['timestamp'],
                'side': row['side'],
                'price': Decimal(row['price']) if row['price'] != 'N/A' else None,
                'quantity': Decimal(row['quantity']),
                'status': row['status']
            })

    # Find paired trades (PRIMARY filled -> HEDGE filled)
    pairedTrades = []
    i = 0
    while i < len(trades):
        trade = trades[i]

        # Look for PRIMARY filled
        if trade['role'] == 'PRIMARY' and trade['status'] == 'filled':
            # Next trade should be HEDGE
            if i + 1 < len(trades):
                hedgeTrade = trades[i + 1]
                if hedgeTrade['role'] == 'HEDGE' and hedgeTrade['status'] == 'filled':
                    pairedTrades.append({
                        'primary': trade,
                        'hedge': hedgeTrade
                    })
                    i += 2
                    continue
                elif hedgeTrade['role'] == 'HEDGE' and hedgeTrade['status'] == 'FAILED':
                    # Failed hedge - note this
                    print(f"[FAILED HEDGE] Primary {trade['side']} @ {trade['price']} qty={trade['quantity']}")
                    i += 2
                    continue
        i += 1

    print(f"\n{'='*70}")
    print(f"2DEX TRADE ANALYSIS REPORT")
    print(f"{'='*70}")
    print(f"Total CSV rows: {len(trades)}")
    print(f"Successfully paired trades: {len(pairedTrades)}")

    # Analyze each pair
    print(f"\n{'='*70}")
    print(f"PER-TRADE PnL ANALYSIS")
    print(f"{'='*70}")

    totalPnl = Decimal('0')
    totalVolume = Decimal('0')
    grvtStats = {'buy_volume': Decimal('0'), 'sell_volume': Decimal('0'),
                  'buy_value': Decimal('0'), 'sell_value': Decimal('0')}
    bpStats = {'buy_volume': Decimal('0'), 'sell_volume': Decimal('0'),
               'buy_value': Decimal('0'), 'sell_value': Decimal('0')}
    spreads = []
    latencies = []

    for idx, pair in enumerate(pairedTrades, 1):
        primary = pair['primary']
        hedge = pair['hedge']
        qty = primary['quantity']

        primaryPrice = primary['price']
        hedgePrice = hedge['price']

        # Calculate PnL
        # GRVT BUY -> BP SELL: PnL = (BP_sell - GRVT_buy) * qty (should be negative - we pay spread)
        # GRVT SELL -> BP BUY: PnL = (GRVT_sell - BP_buy) * qty (should be positive - we earn spread)

        if primary['side'] == 'buy':
            # GRVT bought, BP sold
            pnl = (hedgePrice - primaryPrice) * qty
            spread = hedgePrice - primaryPrice  # Negative expected
            grvtStats['buy_volume'] += qty
            grvtStats['buy_value'] += primaryPrice * qty
            bpStats['sell_volume'] += qty
            bpStats['sell_value'] += hedgePrice * qty
        else:
            # GRVT sold, BP bought
            pnl = (primaryPrice - hedgePrice) * qty
            spread = primaryPrice - hedgePrice  # Positive expected
            grvtStats['sell_volume'] += qty
            grvtStats['sell_value'] += primaryPrice * qty
            bpStats['buy_volume'] += qty
            bpStats['buy_value'] += hedgePrice * qty

        spreads.append(spread)
        totalPnl += pnl
        totalVolume += qty

        # Calculate latency
        primaryTs = parseTimestamp(primary['timestamp'])
        hedgeTs = parseTimestamp(hedge['timestamp'])
        latencyMs = (hedgeTs - primaryTs).total_seconds() * 1000
        latencies.append(latencyMs)

        # Display trade info
        pnlSign = '+' if pnl >= 0 else ''
        spreadSign = '+' if spread >= 0 else ''
        print(f"\nTrade #{idx}:")
        print(f"  GRVT {primary['side'].upper()} @ ${primaryPrice} x {qty}")
        print(f"  BP   {hedge['side'].upper()} @ ${hedgePrice} x {qty}")
        print(f"  Spread: {spreadSign}${spread:.2f} | PnL: {pnlSign}${pnl:.4f}")
        print(f"  Latency: {latencyMs:.1f}ms")

    # Summary statistics
    print(f"\n{'='*70}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*70}")

    print(f"\n[TOTAL PnL]")
    pnlSign = '+' if totalPnl >= 0 else ''
    print(f"  Total PnL: {pnlSign}${totalPnl:.4f}")
    print(f"  Total Volume: {totalVolume} ETH")
    if totalVolume > 0:
        avgPnlPerEth = totalPnl / totalVolume
        print(f"  Avg PnL per ETH: {'+' if avgPnlPerEth >= 0 else ''}${avgPnlPerEth:.4f}")

    print(f"\n[GRVT (PRIMARY - Maker)]")
    print(f"  Buy Volume: {grvtStats['buy_volume']} ETH")
    if grvtStats['buy_volume'] > 0:
        avgBuyPrice = grvtStats['buy_value'] / grvtStats['buy_volume']
        print(f"  Avg Buy Price: ${avgBuyPrice:.2f}")
    print(f"  Sell Volume: {grvtStats['sell_volume']} ETH")
    if grvtStats['sell_volume'] > 0:
        avgSellPrice = grvtStats['sell_value'] / grvtStats['sell_volume']
        print(f"  Avg Sell Price: ${avgSellPrice:.2f}")

    print(f"\n[BACKPACK (HEDGE - Taker)]")
    print(f"  Buy Volume: {bpStats['buy_volume']} ETH")
    if bpStats['buy_volume'] > 0:
        avgBuyPrice = bpStats['buy_value'] / bpStats['buy_volume']
        print(f"  Avg Buy Price: ${avgBuyPrice:.2f}")
    print(f"  Sell Volume: {bpStats['sell_volume']} ETH")
    if bpStats['sell_volume'] > 0:
        avgSellPrice = bpStats['sell_value'] / bpStats['sell_volume']
        print(f"  Avg Sell Price: ${avgSellPrice:.2f}")

    print(f"\n[SPREAD ANALYSIS]")
    if spreads:
        avgSpread = sum(spreads) / len(spreads)
        minSpread = min(spreads)
        maxSpread = max(spreads)
        print(f"  Avg Spread: ${avgSpread:.2f}")
        print(f"  Min Spread: ${minSpread:.2f}")
        print(f"  Max Spread: ${maxSpread:.2f}")

    print(f"\n[LATENCY ANALYSIS (GRVT fill -> BP fill)]")
    if latencies:
        avgLatency = sum(latencies) / len(latencies)
        minLatency = min(latencies)
        maxLatency = max(latencies)
        print(f"  Avg Latency: {avgLatency:.1f}ms")
        print(f"  Min Latency: {minLatency:.1f}ms")
        print(f"  Max Latency: {maxLatency:.1f}ms")

    # Breakdown by size
    print(f"\n{'='*70}")
    print(f"BREAKDOWN BY SIZE")
    print(f"{'='*70}")

    sizeGroups = defaultdict(lambda: {'count': 0, 'pnl': Decimal('0'), 'spreads': []})

    for pair in pairedTrades:
        qty = pair['primary']['quantity']
        primary = pair['primary']
        hedge = pair['hedge']

        if primary['side'] == 'buy':
            pnl = (hedge['price'] - primary['price']) * qty
            spread = hedge['price'] - primary['price']
        else:
            pnl = (primary['price'] - hedge['price']) * qty
            spread = primary['price'] - hedge['price']

        sizeGroups[str(qty)]['count'] += 1
        sizeGroups[str(qty)]['pnl'] += pnl
        sizeGroups[str(qty)]['spreads'].append(spread)

    for size in sorted(sizeGroups.keys(), key=lambda x: Decimal(x)):
        data = sizeGroups[size]
        avgSpread = sum(data['spreads']) / len(data['spreads'])
        pnlSign = '+' if data['pnl'] >= 0 else ''
        print(f"\nSize: {size} ETH")
        print(f"  Trades: {data['count']}")
        print(f"  Total PnL: {pnlSign}${data['pnl']:.4f}")
        print(f"  Avg Spread: ${avgSpread:.2f}")

if __name__ == '__main__':
    csvPath = 'logs/2dex_grvt_backpack_ETH_trades.csv'
    analyzeTrades(csvPath)
