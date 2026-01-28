#!/usr/bin/env python3
"""
Update DEX_INTEGRATION_FRAMEWORK.md from v1.0 to v2.0
Adds:
- Phase 1.5: Strategy Selection
- Phase 6.5: Point Farming Validation
- Phase 9: Multi-DEX Scaling
"""

def update_framework():
    filepath = "DEX_INTEGRATION_FRAMEWORK.md"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update version
    content = content.replace(
        '**Version**: v1.0 (Extracted from Apex/Lighter experience)',
        '**Version**: v2.0 (Enhanced with Point Farming & Multi-DEX Scaling)'
    )

    # Update overview section
    content = content.replace(
        '- **Apex**: Framework refinement (saved 13 hours + 3 weeks)',
        '- **Apex**: Framework refinement (saved 13 hours + 3 weeks)\n- **v2.0 Update**: Added strategy selection, point farming validation, multi-DEX scaling'
    )

    # Update key principles
    content = content.replace(
        '**Key Principle**: API connection first, strategy second',
        '''**Key Principles**:
1. API connection first, strategy second
2. Strategy selection based on DEX point farming rules
3. Volume targets as important as profit targets'''
    )

    # Update phase progression diagram
    old_diagram = '''```
✅ Phase 0: API Connection Test (CRITICAL - Never skip)
   ↓
⏸️ Phase 1: Strategy Research (Can reuse across DEXs)
   ↓
⏸️ Phase 2: Python Backtesting (Can reuse across DEXs)
   ↓
⏸️ Phase 3: PineScript Validation (OPTIONAL if high confidence)
   ↓
🔄 Phase 4: Implementation (DEX-specific)
   ↓
⏸️ Phase 5: QA Testing
   ↓
⏸️ Phase 6: Deployment (Staged rollout)
   ↓
⏸️ Phase 7: Post-Mortem (Daily/weekly reviews)
   ↓
⏸️ Phase 8: Strategy Improvement (Ongoing optimization)
```'''

    new_diagram = '''```
✅ Phase 0: API Connection Test (CRITICAL - Never skip)
   ↓
⏸️ Phase 1: Strategy Research (Can reuse across DEXs)
   ↓
🆕 Phase 1.5: Strategy Selection (Match DEX characteristics)
   ↓
⏸️ Phase 2: Python Backtesting (Can reuse across DEXs)
   ↓
⏸️ Phase 3: PineScript Validation (OPTIONAL if high confidence)
   ↓
🔄 Phase 4: Implementation (DEX-specific)
   ↓
⏸️ Phase 5: QA Testing
   ↓
⏸️ Phase 6: Deployment (Staged rollout)
   ↓
🆕 Phase 6.5: Point Farming Validation (Volume & trade frequency)
   ↓
⏸️ Phase 7: Post-Mortem (Daily/weekly reviews)
   ↓
⏸️ Phase 8: Strategy Improvement (Ongoing optimization)
   ↓
🆕 Phase 9: Multi-DEX Scaling (Scale to 20+ DEXes)
```'''

    content = content.replace(old_diagram, new_diagram)

    # Add Phase 1.5 after Phase 1
    phase_1_5 = '''

---

## Phase 1.5: Strategy Selection (NEW in v2.0)

**Status**: 🔴 CRITICAL for point farming
**Duration**: 1-2 hours
**Owner**: PM + User
**Critical Principle**: Match strategy to DEX characteristics

### Purpose

Select optimal trading strategy based on DEX point farming rules and fee structure.

**Why This Phase Matters**:
- Different DEXes reward different behaviors
- Wrong strategy = 96% gap in volume targets (Apex lesson learned)
- Right strategy = Point farming goals achievable

### ✅ Decision Matrix

#### Analyze DEX Characteristics

**1. Point Farming Metric**
```yaml
volume_based:
  Examples: Apex, dYdX, GMX
  Metric: Trading volume ($)
  Target: $1M/month
  → Recommended Strategy: Market Making (MM)

tvl_based:
  Examples: Lighter, Vertex
  Metric: Total Value Locked
  Target: High TVL + capital efficiency
  → Recommended Strategy: Delta Neutral (DN)

sharpe_bonus:
  Examples: Lighter, Hyperliquid
  Metric: Risk-adjusted returns
  Target: Sharpe ratio > 2.0
  → Recommended Strategy: Trend Following

hybrid:
  Examples: Paradex, Backpack
  Metric: Volume + TVL + Sharpe
  Target: Balanced approach
  → Recommended Strategy: MM + DN portfolio
```

**2. Fee Structure Analysis**
```yaml
maker_rebate:
  Fee: Maker < 0% (rebate)
  Examples: Paradex (-0.005%), GMX (-0.003%)
  → Primary: Delta Neutral (maximize maker rebates)
  → Secondary: Market Making

zero_maker_fee:
  Fee: Maker = 0%
  Examples: Apex (0%), Lighter (0%)
  → Primary: Market Making (no cost to provide liquidity)
  → Secondary: Grid Trading

positive_maker_fee:
  Fee: Maker > 0%
  Examples: dYdX (0.02% maker)
  → Primary: Trend Following (lower frequency)
  → Secondary: DN (3x/day only)
```

**3. Liquidity Depth**
```yaml
high_liquidity:
  Spread: < 2 bps
  → Market Making viable (tight spreads profitable)

medium_liquidity:
  Spread: 2-10 bps
  → Grid Trading (wider ranges needed)

low_liquidity:
  Spread: > 10 bps
  → Trend Following (avoid MM, too risky)
```

### Strategy Performance Profiles

| Strategy | Trade Freq | Monthly Volume | Profit Target | Risk | Farming Score |
|----------|-----------|----------------|---------------|------|---------------|
| **Market Making** | 50-100/day | $1M+ | 0.05-0.10% | Low | ⭐⭐⭐⭐⭐ |
| **Delta Neutral** | 3/day | $300K-500K | 1.5-3% | Very Low | ⭐⭐⭐⭐ |
| **Grid Trading** | 10-30/day | $500K-800K | 2-5% | Medium | ⭐⭐⭐ |
| **Trend Following** | 1-10/day | $40K-300K | 15-25% | High | ⭐⭐ |

### Selection Process

**Step 1: Identify Primary Metric**
```python
def get_primary_metric(dex_config):
    """Determine what DEX optimizes for"""
    if dex_config['points']['metric'] == 'volume':
        return 'volume_farming'
    elif dex_config['fees']['maker'] < 0:
        return 'maker_rebate'
    elif 'sharpe_bonus' in dex_config['points']:
        return 'profit_optimization'
    else:
        return 'balanced'
```

**Step 2: Select Strategy**
```python
def select_strategy(primary_metric, dex_config):
    """Choose optimal strategy"""
    if primary_metric == 'volume_farming':
        return {
            'primary': 'Market Making',
            'backup': 'Grid Trading',
            'expected_volume': '$1M+/month',
            'trade_freq': '50-100/day'
        }

    elif primary_metric == 'maker_rebate':
        return {
            'primary': 'Delta Neutral',
            'backup': 'Market Making',
            'expected_volume': '$300K-500K/month',
            'trade_freq': '3/day'
        }

    elif primary_metric == 'profit_optimization':
        return {
            'primary': 'Trend Following',
            'backup': 'Delta Neutral',
            'expected_volume': '$100K-300K/month',
            'trade_freq': '1-10/day'
        }

    else:  # balanced
        return {
            'primary': 'Multi-Strategy Portfolio',
            'strategies': ['MM', 'DN', 'Trend'],
            'expected_volume': '$500K-1M/month',
            'trade_freq': '20-50/day'
        }
```

**Step 3: Validate Capital Requirements**
```yaml
market_making:
  min_capital: $10,000
  reason: "Need inventory for both sides"

delta_neutral:
  min_capital: $5,000 per DEX (2 DEXes needed)
  reason: "Hedged positions across 2 platforms"

grid_trading:
  min_capital: $3,000
  reason: "Multiple grid levels"

trend_following:
  min_capital: $500
  reason: "Single directional position"
```

### 📋 Deliverables

1. **Strategy Selection Document**
   - Primary strategy chosen
   - Backup strategy identified
   - Expected monthly volume
   - Expected trade frequency
   - Capital requirements

2. **Point Farming Projection**
   - Volume target: $X/month
   - Trade frequency: Y/day
   - Expected ranking: Top Z%
   - Point value estimate: $A-$B/month

3. **Implementation Roadmap**
   - Phase 2 backtest focus
   - Phase 4 implementation priorities
   - Phase 6.5 validation metrics

### 🎯 Success Criteria

- ✅ Strategy matches DEX primary metric
- ✅ Capital requirements validated
- ✅ Volume target achievable (≥ $1M/month for volume-based)
- ✅ Trade frequency realistic for bot automation

### ⚠️ Common Mistakes

**❌ Using Trend-Following for Volume Farming**
```yaml
Problem:
  Trend strategy: 1-10 trades/day
  Volume achieved: $40K/month
  Volume needed: $1M/month
  Gap: 96%

Solution:
  Switch to MM or Grid for volume DEXes
```

**❌ Ignoring Maker Rebates**
```yaml
Problem:
  DEX offers -0.005% maker rebate
  Using taker-heavy strategy (Trend)
  Missing rebate income: $500+/month

Solution:
  Implement DN or MM strategy
  Maximize maker orders
```

### Real Example: Apex

**Apex Characteristics**:
```yaml
point_metric: volume
maker_fee: 0.00%
taker_fee: 0.025%
liquidity: high (< 2 bps spread)
target_volume: $1M/month
```

**Initial Strategy** (Wrong):
```yaml
strategy: Trend Following
trade_freq: 1-10/day
monthly_volume: $40K
gap: 96% below target ❌
```

**Corrected Strategy** (Right):
```yaml
strategy: Market Making
trade_freq: 50-100/day
monthly_volume: $1M+
achievement: 100%+ of target ✅
```

**Lesson**: Always complete Phase 1.5 before proceeding to Phase 2.
'''

    # Insert Phase 1.5 after Phase 1
    phase_1_end = '---\n\n## Phase 2: Python Backtesting'
    content = content.replace(phase_1_end, phase_1_5 + '\n' + phase_1_end)

    # Save updated content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Updated to v2.0: Added Phase 1.5 (Strategy Selection)")
    print("📝 Next: Adding Phase 6.5 and Phase 9...")

if __name__ == '__main__':
    update_framework()
