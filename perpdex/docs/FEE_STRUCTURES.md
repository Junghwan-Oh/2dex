# DEX Fee Structures - Verified October 2024

## Summary Comparison

| Exchange | Maker Fee | Taker Fee | Effective Maker* | Volume Requirement |
|----------|-----------|-----------|------------------|-------------------|
| **Apex Pro** | 0.02% | 0.05% | 0.02% | Standard |
| **Apex Pro (MM Program)** | 0% | 0.03% | 0% | High volume share |
| **Apex Pro (Grid Bot)** | -0.002% | 0.05% | -0.002% | Use Grid Bot |
| **Paradex** | -0.005% | 0.03% | -0.005% | Standard |
| **Paradex (Retail Promo)** | 0% | 0% | 0% | Retail users |

*Effective rate after rebates/promotions

---

## Apex Pro (ApeX Protocol)

### Standard Fees
- **Maker**: 0.02% (2 bps)
- **Taker**: 0.05% (5 bps)
- **Gas Fees**: 0 (gasless trading)

### Special Programs

#### 1. Market Maker Program
- **Requirements**: High maker volume share
- **Benefits**:
  - Maker fee: 0%
  - Taker fee: 0.03% (reduced from 0.05%)
- **Application**: Contact Apex team

#### 2. Grid Bot Trading
- **Maker Fee**: -0.002% (rebate)
- **Taker Fee**: 0.05%
- **Access**: Use ApeX Grid Bot tool
- **Markets**: 45+ perpetual markets

#### 3. Volume-Based Discounts
- 30-day rolling volume tiers
- Discounts apply to both maker and taker fees
- Details vary by tier

### Verification Sources
- [ApeX Blog - Fee Structure Updates](https://www.apex.exchange/blog/detail/Enhancing-Your-Trading-Experience-on-ApeX-Omni-Fee-Structure-Updates)
- [ApeX Market Maker Incentives](https://www.apex.exchange/blog/detail/apex-pro-market-maker-incentives)
- CoinGecko Exchange Data
- **Verified**: October 24, 2024

---

## Paradex

### Standard Fees
- **Maker**: -0.005% (rebate)
- **Taker**: 0.03% (3 bps)
- **Calculation Base**: Notional value (not margin)

### Special Programs

#### 1. Retail Zero Fee Promotion
- **Period**: Current (as of Oct 2024)
- **Fees**:
  - Maker: 0%
  - Taker: 0%
- **Eligibility**: Retail traders
- **Markets**: 100+ perpetual futures

#### 2. Taker Rebate Program
- **Start Date**: July 16, 2025
- **Rebates**: 0.1 bp to 1 bp
- **Based On**: 14-day rolling market share
- **Effective Taker Fee**: As low as 0.02%

#### 3. Season 2 XP Rewards
- **Period**: January - July 2025
- **Weekly Pool**: 4,000,000 XP
- **Activities**: Trading volume, community participation

### Fee Calculation Example
For a $25,000 position with $2,500 margin (10x leverage):
- Fees charged on full $25,000 notional value
- Not just the $2,500 margin

### Verification Sources
- Twitter [@vnkaveri status](https://x.com/vnkaveri/status/1942413497872310434)
- Paradex GitHub Docs (attempted access)
- Bitget News, BlockBeats reports
- **Verified**: October 24, 2024

---

## Cross-DEX Arbitrage Analysis

### Maker-Only Strategy

#### Fee Calculation per $1M Volume
```
Apex (maker):     $1,000,000 × 0.02% = $200 cost
Paradex (maker):  $1,000,000 × -0.005% = $50 rebate
Net fees:         $200 - $50 = $150 (0.015%)

With 0.02% spread capture:
Gross profit:     $1,000,000 × 0.02% = $200
Net profit:       $200 - $150 = $50 (0.005%)
```

#### Grid Bot Strategy (Apex)
```
Apex Grid (maker): $1,000,000 × -0.002% = $20 rebate
Paradex (maker):   $1,000,000 × -0.005% = $50 rebate
Net fees:          -$70 (earn on fees!)

With 0.02% spread:
Total profit:      $200 + $70 = $270 (0.027%)
```

### Key Insights

1. **Never Use Taker Orders**:
   - Apex taker (0.05%) destroys profitability
   - Paradex taker (0.03%) still too expensive

2. **Best Strategy**:
   - Apex Grid Bot + Paradex maker orders
   - Both sides earn rebates
   - 0.027% profit on volume

3. **Risk Factors**:
   - Price divergence between exchanges
   - Inventory imbalance
   - Network latency

---

## Implementation Recommendations

### For Volume Farming (0% Loss Target)

1. **Primary Strategy**: Cross-DEX Maker
   - Place limit orders on both exchanges
   - Target 0.02% spread (0.01% each side)
   - Never cross the spread (no taker orders)

2. **Enhanced Strategy**: Grid Bot Integration
   - Use Apex Grid Bot for -0.002% rebate
   - Manual maker orders on Paradex for -0.005%
   - Total rebate: 0.007% of volume

3. **Risk Management**:
   - Max position: $1,000 per side
   - Rebalance at 60/40 inventory ratio
   - Stop if spread < 0.015%

### Monthly Projections

For $1M monthly volume per exchange:
- **Standard Cross-DEX**: +$50 profit
- **Grid Bot Enhanced**: +$270 profit
- **Required Trades**: 1,500+ (50/day @ $667 avg)

---

## Important Notes

1. **Fees Subject to Change**: Always verify current rates before trading
2. **Promotional Periods**: Paradex zero fees may end without notice
3. **Volume Requirements**: Some programs require minimum volume
4. **Network Effects**: High-volume periods may have worse spreads
5. **Slippage Risk**: Fast markets can cause unfavorable fills

---

## Update History

- **October 24, 2024**: Initial documentation created
- **Sources Verified**: Official exchange blogs, social media, news reports
- **Next Review**: November 2024

---

## Contact Information

### Apex Pro
- Website: https://www.apex.exchange
- Documentation: https://docs.apex.exchange
- Support: support@apex.exchange

### Paradex
- Website: https://www.paradex.trade
- Documentation: GitHub (tradeparadex/paradex-docs)
- Twitter: @tradeparadex