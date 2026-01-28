# Quick Reference: Crypto MAC Strategy

## What Was Analyzed
- **Source**: ch_07_trend_following2.ipynb (TSLA stock strategy)
- **Strategy**: Moving Average Crossover (MAC) Long/Short
- **Original Performance**: Sharpe 1.91, MDD -33.73%

## Core Strategy Logic

### Signals
```
Golden Cross:  Short EMA > Long EMA → Go LONG  (Signal = 2)
Death Cross:   Short EMA < Long EMA → Go SHORT (Signal = -2)
```

### Position Management
- Always in market (100% long or 100% short)
- Full capital reallocation on every signal
- Optional stop loss for risk control

## Key Functions

### Basic Version (No Stop Loss)
```python
mac_long_short1(df, short_window, long_window)
```

### Enhanced Version (With Stop Loss)
```python
mac_long_short2(df, sw, lw, stop_loss_long, stop_loss_short)
```

## Crypto Adaptations

### 1. Data Loading
```python
# REPLACE yfinance
df = yf.download('TSLA', start='2019-01-01', end='2024-01-01')

# WITH Binance CSV
df = pd.read_csv(f'{symbol}_{timeframe}.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
```

### 2. Parameter Ranges

| Timeframe | Short Window | Long Window | Stop Loss |
|-----------|--------------|-------------|-----------|
| 1m | 3-10 | 15-40 | 5-15% |
| 15m | 8-25 | 30-80 | 8-20% |
| 1h | 12-40 | 50-120 | 10-25% |

### 3. Leverage Constraint
```python
max_stop_loss = (1 / leverage) * 0.8

# Example: 10x leverage → max SL = 8%
# (10% loss = 100% account loss = liquidation)
```

### 4. Fee Adjustment
```python
fee_rate = 0.0005  # 0.05% (Binance taker fee)
```

## Test Matrix

**300 Total Combinations**:
- Coins: BTC, ETH, SOL, XRP, SUI (5)
- Timeframes: 1m, 3m, 5m, 15m, 30m, 1h (6)
- Leverage: 1x to 10x (10)

## Implementation Checklist

- [ ] Create `load_crypto_data(symbol, timeframe)` function
- [ ] Adapt `mac_long_short_leverage(df, sw, lw, sll, sls, leverage)`
- [ ] Build optimizer: `optimize_params(symbol, tf, lev)`
- [ ] Run full backtest loop (300 iterations)
- [ ] Analyze results, rank by Sharpe ratio
- [ ] Select top 10 strategies for paper trading

## Expected Output

```
TOP STRATEGY EXAMPLE:
Symbol: ETHUSDT
Timeframe: 15m
Leverage: 3x
Params: SW=11, LW=35, SLL=0.15, SLS=0.10
Performance: Sharpe 2.45, Return 87%, MDD -22%
```

## Key Warnings

⚠️ **Liquidation Risk**: Stop loss MUST be < (1/leverage) * 0.8
⚠️ **Overfitting**: Use train/test split (e.g., 2 months train, 1 month test)
⚠️ **Slippage**: Real trading will have 0.1-0.3% execution costs
⚠️ **Funding**: Perpetual futures charge hourly funding fees

## Next Steps

1. **Validate**: Test BTC 1h 1x manually
2. **Optimize**: Grid search on one (coin, tf, lev) combo
3. **Scale**: Run all 300 combinations
4. **Analyze**: Rank and select top performers

---

**Full Details**: See `crypto_trend_analysis.md`
**Created**: 2025-11-07
