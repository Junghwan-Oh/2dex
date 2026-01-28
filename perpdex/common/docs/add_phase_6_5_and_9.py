#!/usr/bin/env python3
"""
Add Phase 6.5 and Phase 9 to DEX_INTEGRATION_FRAMEWORK.md
"""

def add_phases():
    filepath = "DEX_INTEGRATION_FRAMEWORK.md"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Phase 6.5: Point Farming Validation
    phase_6_5 = '''

---

## Phase 6.5: Point Farming Validation (NEW in v2.0)

**Status**: 🟡 IMPORTANT for PRD compliance
**Duration**: 1 week monitoring
**Owner**: PM + User
**Critical Principle**: Validate volume targets, not just profit targets

### Purpose

Verify that deployed bot achieves point farming goals (volume, trade frequency, ranking).

**Why This Phase Matters**:
- Profit-making strategy ≠ Point farming strategy
- Trend Following: Great for profit, poor for volume ($40K vs $1M target)
- Without validation: Miss point farming rewards entirely

### ✅ Monitoring Metrics

#### 1. Volume Tracking

**Daily Volume**:
```python
def calculate_daily_volume(trades):
    """Sum all trade volumes for the day"""
    total = sum(trade['price'] * trade['size'] for trade in trades)
    return total

# Target:
# - MM strategy: $30K-40K/day → $1M/month ✅
# - DN strategy: $10K-20K/day → $300K-500K/month ✅
# - Trend: $1K-10K/day → $40K-300K/month ⚠️
```

**Monthly Projection**:
```python
def project_monthly_volume(daily_avg, days_elapsed):
    """Project full month volume from partial data"""
    monthly_projection = daily_avg * 30
    return monthly_projection

# Example:
# Day 3: $35K/day avg → $1.05M/month projected ✅
# Day 7: $8K/day avg → $240K/month projected ⚠️
```

#### 2. Trade Frequency

**Trades Per Day**:
```yaml
market_making:
  target: 50-100 trades/day
  acceptable: > 30 trades/day
  red_flag: < 20 trades/day

delta_neutral:
  target: 3 trades/day (funding intervals)
  acceptable: 2-4 trades/day
  red_flag: < 1 trade/day

grid_trading:
  target: 10-30 trades/day
  acceptable: > 5 trades/day
  red_flag: < 3 trades/day

trend_following:
  target: 1-10 trades/day
  acceptable: Any (strategy-dependent)
  note: NOT suitable for volume farming
```

**Alert Triggers**:
```python
def check_trade_frequency(trades_today, strategy_type):
    """Alert if trade frequency below threshold"""
    thresholds = {
        'MM': 30,
        'DN': 1,
        'Grid': 5,
        'Trend': 1
    }

    if trades_today < thresholds[strategy_type]:
        send_alert(f"⚠️ Low trade freq: {trades_today} < {thresholds[strategy_type]}")
        return False
    return True
```

#### 3. Point Ranking Estimate

**Ranking Calculation** (if DEX provides leaderboard):
```python
def estimate_ranking(my_volume, total_participants):
    """Estimate ranking based on volume"""
    # Example: Apex Pro leaderboard shows top 100
    # Your volume: $35K/day = $1.05M/month
    # Top 1% volume threshold: ~$500K/month
    # → Estimated rank: Top 0.5% ✅

    if my_volume > top_1_percent_threshold:
        return "Top 1%"
    elif my_volume > top_5_percent_threshold:
        return "Top 5%"
    else:
        return "Below Top 5%"
```

#### 4. Fee Optimization

**Maker vs Taker Ratio**:
```yaml
target_ratio:
  maker_rebate_dex: 90% maker, 10% taker
  zero_maker_fee: 70% maker, 30% taker
  positive_maker_fee: 50% maker, 50% taker

tracking:
  maker_orders: count + volume
  taker_orders: count + volume
  maker_ratio: maker_volume / total_volume
```

**Fee Impact Analysis**:
```python
def calculate_fee_impact(trades, fee_structure):
    """Calculate total fees paid/earned"""
    maker_fees = sum(
        trade['volume'] * fee_structure['maker']
        for trade in trades if trade['is_maker']
    )

    taker_fees = sum(
        trade['volume'] * fee_structure['taker']
        for trade in trades if not trade['is_maker']
    )

    total_fees = maker_fees + taker_fees

    # Example:
    # Apex MM: $1M volume, 100% maker, 0% fee = $0 ✅
    # Paradex DN: $300K volume, 90% maker, -0.005% = -$13.50 (rebate!) ✅
    # Trend: $100K volume, 30% maker, 0.025% taker = $17.50 cost ⚠️

    return total_fees
```

### 📋 Week 1 Validation Checklist

**Day 1-3: Initial Assessment**
- [ ] Measure daily volume
- [ ] Count trades per day
- [ ] Check maker/taker ratio
- [ ] Project monthly volume
- [ ] Compare vs target ($1M for volume DEXes)

**Day 4-7: Trend Analysis**
- [ ] Calculate 7-day average volume
- [ ] Identify volume patterns (weekday vs weekend)
- [ ] Analyze trade distribution (time of day)
- [ ] Estimate point ranking
- [ ] Decide: GO for full capital OR adjust strategy

### 🎯 Success Criteria

**Volume-Based DEXes** (Apex, dYdX, GMX):
- ✅ Daily volume ≥ $30K/day
- ✅ Monthly projection ≥ $1M
- ✅ Trade frequency ≥ 30/day (MM) or ≥ 5/day (Grid)
- ✅ Estimated ranking: Top 1-5%

**Maker Rebate DEXes** (Paradex, GMX):
- ✅ Daily volume ≥ $10K/day
- ✅ Maker ratio ≥ 80%
- ✅ Positive rebate income (fees < 0)
- ✅ Trade frequency: 3/day (DN)

**Sharpe Bonus DEXes** (Lighter, Hyperliquid):
- ✅ Sharpe ratio ≥ 2.0 (backtest 70%+ achieved)
- ✅ Max drawdown ≤ 120% of backtest
- ✅ Trade frequency: 1-10/day (acceptable)

### ⚠️ Adjustment Triggers

**Trigger 1: Volume Below Target**
```yaml
problem:
  daily_volume: < $20K/day
  monthly_projection: < $600K

actions:
  1. Increase position sizes (2x)
  2. Add more coins (BTC + ETH + SOL)
  3. Consider switching to MM strategy
  4. Test higher leverage (2x → 3x)
```

**Trigger 2: Low Trade Frequency**
```yaml
problem:
  trades_per_day: < 10 (for MM/Grid)

actions:
  1. Tighten grid spacing (Grid)
  2. Reduce spread (MM)
  3. Check liquidity availability
  4. Verify order execution working
```

**Trigger 3: High Taker Ratio**
```yaml
problem:
  taker_ratio: > 50% (for maker rebate DEX)

actions:
  1. Switch to limit orders only
  2. Increase order placement frequency
  3. Improve mid-price calculation
  4. Reduce urgency (accept slower fills)
```

### Real Example: Apex Week 1

**Day 1 Results**:
```yaml
strategy: Trend Following (BTC 1h, ETH 30m)
daily_volume: $2,500
trades: 3
monthly_projection: $75,000
gap: 92.5% below $1M target ❌
```

**Adjustment Decision**:
```yaml
problem: Trend strategy unsuitable for volume farming
decision: Switch to MM strategy

implementation:
  - Phase 1.5: Select MM strategy
  - Phase 2: Backtest MM parameters
  - Phase 4: Implement MM bot
  - Phase 6.5: Re-validate with MM

expected_result:
  daily_volume: $35K
  trades: 60-80/day
  monthly_projection: $1.05M ✅
```

### 📊 Dashboard Metrics

**Telegram Notifications** (Every 10 min while position open):
```
📊 Point Farming Status

💰 Volume (24h): $32,450 / $33,333 target
📈 Projection: $973,500/month (97% of $1M)
⚡ Trades Today: 67 / 50+ target
📊 Maker Ratio: 78% (target: 70%+)
🏆 Est. Ranking: Top 1%

Status: ✅ ON TRACK
```

**Web Dashboard** (Optional):
```
Metrics to Display:
- Volume: Daily, weekly, monthly
- Trade count: Hourly breakdown
- Maker/Taker split: Pie chart
- Fee impact: Cumulative graph
- Ranking estimate: Percentile gauge
- Target achievement: Progress bars
```

### 📋 Deliverables

1. **Week 1 Report**
   - Daily volume data (7 days)
   - Trade frequency analysis
   - Maker/taker ratio
   - Point ranking estimate
   - GO/NO-GO decision for full capital

2. **Strategy Adjustment Plan** (if needed)
   - Identified gaps
   - Proposed changes
   - Expected impact
   - Timeline to implement

3. **Scaling Recommendation**
   - Current capital: $X
   - Recommended scale: $Y
   - Risk assessment
   - Expected monthly volume at scale

### 🎯 Phase 6.5 Outcome

**GO Decision Criteria**:
- ✅ Volume ≥ 80% of target
- ✅ Trade frequency meeting expectations
- ✅ No critical issues discovered
- → Proceed to full capital deployment

**ADJUST Decision Criteria**:
- ⚠️ Volume 50-80% of target
- ⚠️ Strategy tweaks needed
- → Implement adjustments, re-validate

**NO-GO Decision Criteria**:
- ❌ Volume < 50% of target
- ❌ Fundamental strategy mismatch
- → Return to Phase 1.5, select different strategy
'''

    # Insert Phase 6.5 after Phase 6
    phase_6_end = '---\n\n## Phase 7: Post-Mortem (Ongoing)'
    content = content.replace(phase_6_end, phase_6_5 + '\n' + phase_6_end)

    # Phase 9: Multi-DEX Scaling
    phase_9 = '''

---

## Phase 9: Multi-DEX Scaling (NEW in v2.0)

**Status**: 🟢 RECOMMENDED for 20-DEX portfolio
**Duration**: 1 week per 5 DEXes
**Owner**: Architect
**Critical Principle**: Automate Phase 0, parallelize testing

### Purpose

Scale from single DEX to 20+ DEX portfolio with systematic batch testing.

**Why This Phase Matters**:
- Single DEX: 3-6 hours per integration (manual)
- 20 DEXes: 60-120 hours (sequential) = 2-3 weeks
- With automation: 15-20 hours (parallel) = 2-3 days ✅

### ✅ Batch Testing Strategy

#### Batch Structure

**Batch 1: Priority 1 DEXes** (Week 1)
```yaml
dexes: [Apex, Paradex]
characteristics:
  - Phase: initial/extreme_early
  - Point programs: Active
  - Capital allocation: 10% each
  - Strategy: MM (Apex), DN (Paradex)

timeline:
  monday: Phase 0 testing (both DEXes parallel)
  tuesday: Implementation (port from Apex template)
  wednesday: QA testing
  thursday: Deploy Stage 1 ($100 each)
  friday: Phase 6.5 validation
```

**Batch 2: Priority 2 DEXes** (Week 2)
```yaml
dexes: [Lighter, Backpack, Aster]
capital_allocation: 5% each
expected_phase_0_success: 60% (3/5 may fail)
```

**Batch 3-6: Scale to 20** (Weeks 3-6)
```yaml
batch_size: 5 DEXes per week
total_weeks: 4-6 weeks
success_rate: 50-70%
final_count: 10-15 operational DEXes
```

### 🔧 Automation Framework

#### Automated Phase 0 Test Suite

**Script: automated_phase0.py**
```python
class AutomatedPhase0:
    """
    Automated Phase 0 testing for multiple DEXes in parallel
    """

    def __init__(self, dex_configs):
        self.dex_configs = dex_configs
        self.results = {}

    def run_all_tests_parallel(self):
        """Test all DEXes in parallel"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.test_single_dex, name, config): name
                for name, config in self.dex_configs.items()
            }

            for future in as_completed(futures):
                dex_name = futures[future]
                try:
                    result = future.result()
                    self.results[dex_name] = result
                except Exception as e:
                    self.results[dex_name] = {'status': 'FAILED', 'error': str(e)}

        return self.results

    def test_single_dex(self, dex_name, config):
        """Run Phase 0 checkpoints for single DEX"""
        results = {
            'dex': dex_name,
            'checkpoint1': self.checkpoint1_basic(config),
            'checkpoint2': self.checkpoint2_orders(config),
            'checkpoint3': self.checkpoint3_realtime(config),
            'decision': None,
            'quirks': []
        }

        # GO/NO-GO decision
        if all([results['checkpoint1']['passed'],
                results['checkpoint2']['passed']]):
            results['decision'] = 'GO'
        else:
            results['decision'] = 'NO-GO'

        return results

    def checkpoint1_basic(self, config):
        """Phase 0 Checkpoint 1: Basic connection"""
        try:
            client = create_dex_client(config)
            client.authenticate()
            balance = client.get_balance()
            ticker = client.get_ticker('BTC-USDT')

            return {
                'passed': True,
                'balance': balance,
                'ticker': ticker['price']
            }
        except Exception as e:
            return {
                'passed': False,
                'error': str(e)
            }

    def checkpoint2_orders(self, config):
        """Phase 0 Checkpoint 2: Order execution"""
        try:
            client = create_dex_client(config)

            # Small test order ($10-30)
            test_order = client.create_market_order(
                symbol='BTC-USDT',
                side='BUY',
                size=0.0001  # ~$10
            )

            # Close position
            close_order = client.create_market_order(
                symbol='BTC-USDT',
                side='SELL',
                size=0.0001
            )

            return {
                'passed': True,
                'test_order_id': test_order['id'],
                'pnl': close_order['pnl']
            }
        except Exception as e:
            return {
                'passed': False,
                'error': str(e)
            }

    def checkpoint3_realtime(self, config):
        """Phase 0 Checkpoint 3: WebSocket test"""
        try:
            client = create_dex_client(config)
            ws_working = client.test_websocket(['BTC-USDT'])

            return {
                'passed': ws_working,
                'architecture': 'Hybrid' if ws_working else 'REST-only'
            }
        except Exception as e:
            return {
                'passed': False,
                'architecture': 'REST-only',
                'error': str(e)
            }
```

**Usage**:
```python
# Load DEX configurations
dex_configs = load_dex_configs('dex_config.yaml')

# Run automated Phase 0 for 5 DEXes
tester = AutomatedPhase0(dex_configs)
results = tester.run_all_tests_parallel()

# Results:
# {
#   'apex': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...},
#   'paradex': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...},
#   'lighter': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...},
#   'backpack': {'decision': 'NO-GO', 'checkpoint1': {'passed': False}, ...},
#   'aster': {'decision': 'GO', 'checkpoint1': {'passed': True}, ...}
# }

# Time: 15-30 minutes (parallel) vs 3-4 hours (sequential)
```

### 📊 Capital Allocation Strategy

#### Portfolio Structure

**Total Capital**: $200,000 (example)

**Tier 1: Priority DEXes** (30% = $60K)
```yaml
apex:
  allocation: 10% ($20K)
  strategy: Market Making
  expected_volume: $1M/month
  expected_return: 2-5%

paradex:
  allocation: 10% ($20K)
  strategy: Delta Neutral
  expected_volume: $500K/month
  expected_return: 1.5-3%

lighter:
  allocation: 10% ($20K)
  strategy: Trend Following
  expected_volume: $200K/month
  expected_return: 15-25%
```

**Tier 2: Growth DEXes** (40% = $80K)
```yaml
allocation: 5% each ($10K per DEX)
count: 8 DEXes
strategy: Mix (MM, DN, Grid)
expected_volume: $3-5M total
expected_return: 5-15%
```

**Tier 3: Experimental** (20% = $40K)
```yaml
allocation: 2-3% each ($4-6K per DEX)
count: 7-10 DEXes
strategy: Test new approaches
expected_volume: $1-2M total
expected_return: 0-10% (learning focus)
```

**Reserve** (10% = $20K)
```yaml
purpose: Emergency fund, new opportunities
allocation: Unallocated
```

### 🎯 Portfolio Risk Management

#### Diversification Rules

**1. DEX Phase Diversification**
```yaml
extreme_early: Max 20% of capital
initial: Max 40% of capital
mature: Unlimited (stable platforms)

rationale: Newer DEXes higher risk of rug pull, API changes
```

**2. Strategy Diversification**
```yaml
market_making: 30-40%
delta_neutral: 20-30%
trend_following: 15-25%
grid_trading: 10-20%

rationale: Uncorrelated strategies reduce portfolio volatility
```

**3. Geographic Diversification**
```yaml
arbitrum_dexes: Max 30%
optimism_dexes: Max 30%
polygon_dexes: Max 20%
other_chains: Unlimited

rationale: Chain-specific risks (downtime, congestion)
```

#### Portfolio-Wide Limits

**Maximum Drawdown**:
```python
def check_portfolio_drawdown():
    """Kill switch if portfolio MDD > 15%"""
    current_nav = calculate_portfolio_nav()
    all_time_high = get_all_time_high()

    drawdown = (all_time_high - current_nav) / all_time_high

    if drawdown > 0.15:  # 15% portfolio MDD
        emergency_shutdown_all_dexes()
        send_alert("🚨 Portfolio MDD > 15%! All bots stopped.")
```

**Daily Loss Limit**:
```python
def check_daily_loss():
    """Pause trading if daily loss > $2,000"""
    today_pnl = sum(dex.get_today_pnl() for dex in active_dexes)

    if today_pnl < -2000:
        pause_all_trading()
        send_alert("⚠️ Daily loss limit hit: ${today_pnl}")
```

### 📋 Week-by-Week Roadmap

**Week 1: Batch 1 (Apex, Paradex)**
```yaml
monday:
  - Automated Phase 0: Both DEXes ✅
  - Results: Apex GO, Paradex GO

tuesday:
  - Port Apex code to Paradex
  - Implement DN strategy for Paradex
  - QA testing

wednesday-friday:
  - Deploy Stage 1 ($100 each)
  - Phase 6.5 validation
  - Scale to full capital if validated
```

**Week 2: Batch 2 (Lighter, Backpack, Aster)**
```yaml
monday:
  - Automated Phase 0: 3 DEXes parallel
  - Results: Lighter GO, Backpack NO-GO, Aster GO

tuesday-thursday:
  - Implement Lighter (Trend), Aster (MM)
  - Skip Backpack (API issues)
  - QA + Deploy

friday:
  - Phase 6.5 validation
  - Portfolio review
```

**Weeks 3-6: Scale to 20 DEXes**
```yaml
batch_3: Hyperliquid, dYdX, GMX, Kwenta, Gains
batch_4: Vela, Level, MUX, Vertex, Rage Trade
batch_5: Polynomial, Pika, SynFutures, Tigris, Equation
batch_6: (Future DEXes as they launch)
```

### 🔧 Portfolio Management Tools

**Multi-DEX Orchestrator**
```python
class DexPortfolioManager:
    """Manage 20+ DEXes with unified interface"""

    def __init__(self, total_capital):
        self.total_capital = total_capital
        self.active_dexes = {}
        self.performance_tracker = PerformanceTracker()

    def initialize_dex(self, dex_name, config):
        """Add new DEX to portfolio"""
        capital = self.total_capital * config['allocation']
        strategy = select_strategy(config)  # Phase 1.5

        self.active_dexes[dex_name] = {
            'client': create_dex_client(config),
            'strategy': strategy,
            'capital': capital,
            'bot': TradingBot(strategy, capital)
        }

    def get_portfolio_metrics(self):
        """Aggregate metrics across all DEXes"""
        return {
            'total_pnl': sum(dex['bot'].pnl for dex in self.active_dexes.values()),
            'total_volume': sum(dex['bot'].volume for dex in self.active_dexes.values()),
            'total_trades': sum(dex['bot'].trades for dex in self.active_dexes.values()),
            'roi': self.calculate_portfolio_roi(),
            'sharpe': self.calculate_portfolio_sharpe(),
            'max_drawdown': self.calculate_max_drawdown()
        }

    def rebalance_capital(self):
        """Rebalance based on performance"""
        # TODO: Move capital from underperforming to outperforming DEXes
        pass
```

### 📊 Success Metrics

**After Week 1** (2 DEXes):
- ✅ 2 DEXes operational
- ✅ $40K deployed
- ✅ $1.5M+ monthly volume projected
- ✅ Portfolio PnL positive

**After Week 2** (4 DEXes):
- ✅ 4 DEXes operational
- ✅ $60K deployed
- ✅ $3M+ monthly volume projected

**After Week 6** (10-15 DEXes):
- ✅ 10-15 DEXes operational
- ✅ $150K-180K deployed
- ✅ $10M+ monthly volume
- ✅ Portfolio ROI 15-25% monthly
- ✅ Max drawdown < 15%

### 📋 Deliverables

1. **Automated Phase 0 Suite**
   - Python script for parallel testing
   - Results parser and reporting
   - GO/NO-GO decision automation

2. **Multi-DEX Configuration File**
   - YAML with 20 DEX configs
   - Capital allocation strategy
   - Risk limits per DEX

3. **Portfolio Dashboard**
   - Aggregate P&L across all DEXes
   - Volume tracking per DEX
   - Risk metrics (drawdown, exposure)
   - Strategy distribution

4. **Scaling Report**
   - DEXes tested: 20
   - DEXes operational: 10-15
   - Success rate: 50-70%
   - Total volume: $10M+/month
   - Portfolio ROI: 15-25%
'''

    # Insert Phase 9 at the end (before the final sections)
    framework_updates_section = '## 🔄 Framework Updates'
    content = content.replace(framework_updates_section, phase_9 + '\n\n---\n\n' + framework_updates_section)

    # Update version history
    old_version_history = '''**Version History**:
- v0.1 (2025-11-08): Initial framework from Lighter experience
- v0.2 (2025-11-09): Added Phase 0 (learned from Lighter failure)
- v1.0 (2025-11-09): Extracted to common framework (proven with 2 DEXs)'''

    new_version_history = '''**Version History**:
- v0.1 (2025-11-08): Initial framework from Lighter experience
- v0.2 (2025-11-09): Added Phase 0 (learned from Lighter failure)
- v1.0 (2025-11-09): Extracted to common framework (proven with 2 DEXs)
- v2.0 (2025-11-09): Added Phase 1.5 (Strategy Selection), Phase 6.5 (Point Farming Validation), Phase 9 (Multi-DEX Scaling)'''

    content = content.replace(old_version_history, new_version_history)

    # Save
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Done: Updated to v2.0 with Phase 6.5 and Phase 9")
    print("Next: Verify changes and commit to git")

if __name__ == '__main__':
    add_phases()
