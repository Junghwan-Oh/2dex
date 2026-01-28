# Cryptocurrency Trend Following Strategy Analysis

## Overview
Analysis of MAC (Moving Average Crossover) trend following strategy from TSLA stock notebook
Target: Adapt for crypto backtesting (5 coins × 6 timeframes × 10 leverage = 300 tests)

---

## Original Strategy Summary

**Asset**: TSLA stock (2019-2024)
**Type**: Long/Short trend following
**Performance**: Sharpe 1.91, MDD -33.73%

### Entry/Exit Signals
- **Golden Cross**: Short MA > Long MA → Enter Long (Signal = 2)
- **Death Cross**: Short MA < Long MA → Enter Short (Signal = -2)
- **Position**: Always in market (100% long or 100% short)

### Stop Loss (Version 2)
- **Long SL**: Exit when price drops X% from entry
- **Short SL**: Exit when price rises X% from entry

---

## Core Functions Extracted

### 1. mac_long_short1(df, sw, lw)
Basic long/short without stop loss

```python
# Calculate EMAs
data['Short_MA'] = data['Close'].ewm(span=sw, adjust=False).mean()
data['Long_MA'] = data['Close'].ewm(span=lw, adjust=False).mean()

# Generate position (-1 short, +1 long)
data['Position'] = np.where(data['Short_MA'] > data['Long_MA'], 1, -1)

# Detect changes (2 = enter long, -2 = enter short)
data['Signal'] = data['Position'].diff().fillna(0)
```

### 2. mac_long_short2(df, sw, lw, sll, sls)
Enhanced with stop loss

```python
# Same as above, plus:
if pos == 1 and prices[i] < buy_price * (1 - stop_loss_long):
    # Exit long
if pos == -1 and prices[i] > short_price * (1 + stop_loss_short):
    # Cover short
```

### 3. Performance Metrics

```python
# Sharpe Ratio
mean_return = returns.mean() * 252
std_return = returns.std() * sqrt(252)
sharpe = (mean_return - 0.02) / std_return

# Max Drawdown
drawdown = (cumulative - cummax) / cummax
mdd = drawdown.min()

# Win Rate
win_rate = profitable_trades / total_trades
```

---

## Crypto Adaptations Needed

### 1. Data Loading
Replace yfinance with Binance CSV:

```python
def load_crypto_data(symbol, timeframe):
    path = f"C:\Users\crypto quant\perpdex farm\lighter\data\binance\{symbol}_{timeframe}.csv"
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]
```

### 2. Trading Hours
- **Stock**: 252 days/year, 6.5 hours/day
- **Crypto**: 365 days/year, 24 hours/day
- **Impact**: Adjust annualization factor (252 → 365*24 for hourly)

### 3. Parameter Ranges

**EMA Windows** (adjusted for crypto volatility):

| Timeframe | Short Window | Long Window |
|-----------|--------------|-------------|
| 1m | 3-10 | 15-40 |
| 3m | 5-15 | 20-50 |
| 5m | 5-20 | 25-60 |
| 15m | 8-25 | 30-80 |
| 30m | 10-30 | 40-100 |
| 1h | 12-40 | 50-120 |

**Stop Loss Ranges**:
- Long: 0.05 to 0.25 (5%-25%)
- Short: 0.03 to 0.20 (3%-20%)
- **Constraint**: Must be < (1/leverage) * 0.8

### 4. Leverage Integration

```python
def mac_with_leverage(df, sw, lw, sll, sls, leverage=1):
    cash_init = 10000
    effective_capital = cash_init * leverage
    
    # Same EMA and signal logic
    
    # Modified entry
    if signal == 2:  # Enter long
        buy_qty = effective_capital / price
        
    # Liquidation check
    if leverage > 1:
        max_sl = (1 / leverage) * 0.8
        assert sll < max_sl, "SL too wide"
```

### 5. Fee Structure
- **Stock**: 0.1% flat
- **Crypto**: 0.02% maker, 0.05% taker (Binance)
- **Use**: 0.05% for conservative estimate

---

## Implementation Steps

### Phase 1: Validation (Day 1)
1. Load BTC 1h data
2. Run mac_long_short1(df, sw=12, lw=26)
3. Check: Sharpe > 0, MDD < 50%, Win rate > 40%

### Phase 2: Optimization (Days 2-4)
1. Grid search on BTC 15m
2. Test leverage 1x, 3x, 5x
3. Find optimal (sw, lw, sll, sls)

### Phase 3: Full Backtest (Week 2)
```python
coins = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'SUIUSDT']
timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
leverages = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

for symbol, tf, lev in product(coins, timeframes, leverages):
    best_params = optimize(symbol, tf, lev)
    results.append(run_backtest(symbol, tf, lev, best_params))
```

### Phase 4: Analysis (Days 9-10)
1. Rank by Sharpe ratio
2. Check train/test overfitting
3. Select top 10 strategies

---

## Expected Results

```
TOP 5 STRATEGIES:
1. ETHUSDT 15m 3x: Sharpe 2.45, Return 87%, MDD -22%
   Params: SW=11, LW=35, SLL=0.15, SLS=0.10

2. BTCUSDT 1h 2x: Sharpe 2.31, Return 65%, MDD -18%
   Params: SW=15, LW=50, SLL=0.12, SLS=0.08

INSIGHTS:
- Best: 15m and 1h timeframes (stable trends)
- Optimal: 2x-5x leverage (risk/reward balance)
- Avoid: 1m (noisy), 10x (liquidation risk)
```

---

## Files to Create

1. **crypto_mac_strategy.py** - Core strategy with leverage
2. **crypto_optimizer.py** - Grid search optimization
3. **backtest_runner.py** - Run 300 combinations
4. **analysis.py** - Generate performance report

---

## Risk Checklist

- [ ] Stop loss < (1/leverage) * 0.8
- [ ] No missing candles in data
- [ ] Account for slippage (0.1-0.3%)
- [ ] Include funding costs
- [ ] Kill switch at 30% drawdown

---

## Key Differences from Original

| Original | Crypto |
|----------|--------|
| 252 trading days/year | 365*24 hours/year |
| yfinance API | Binance CSV files |
| 0.1% fee | 0.05% fee |
| No leverage | 1x-10x leverage |
| Market hours only | 24/7 continuous |

---

**Source**: ch_07_trend_following2.ipynb
**Data**: C:\Users\crypto quant\perpdex farm\lighter\data\binance\
**Coins**: BTC, ETH, SOL, XRP, SUI
**Timeframes**: 1m, 3m, 5m, 15m, 30m, 1h
**Created**: 2025-11-07
