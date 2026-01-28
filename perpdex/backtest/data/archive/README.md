# Archived BTC Historical Data

## Data Files

### Available Timeframes

| File | Timeframe | Period | Candles | Date Range | Size |
|------|-----------|--------|---------|------------|------|
| `binance_btc_1m_30days.csv` | 1 minute | 30 days | 43,200 | Sep 24 - Oct 23, 2024 | 2.5 MB |
| `binance_btc_3m_30days.csv` | 3 minutes | 30 days | 14,400 | Sep 24 - Oct 24, 2025 | 675 KB |
| `binance_btc_5m_30days.csv` | 5 minutes | 30 days | 8,640 | Sep 24 - Oct 23, 2024 | 521 KB |
| `binance_btc_15m_30days.csv` | 15 minutes | 30 days | 2,880 | Sep 24 - Oct 23, 2024 | 175 KB |

## Data Format

All CSV files follow the same structure:

```csv
timestamp,open,high,low,close,volume
1695556800,26562.12,26563.45,26560.89,26561.78,12.345
```

- **timestamp**: Unix timestamp (seconds since epoch)
- **open**: Opening price (USD)
- **high**: Highest price in period (USD)
- **low**: Lowest price in period (USD)
- **close**: Closing price (USD)
- **volume**: Trading volume (BTC)

## Data Source

- **Exchange**: Binance Spot
- **Symbol**: BTCUSDT
- **Collection Date**: October 23-24, 2024
- **Collection Method**: `backtest/fetch_binance_data.py`

## Usage Example

```python
from backtest.data_loader import loadCsvData

# Load 5-minute data
candles = loadCsvData('backtest/data/archive/binance_btc_5m_30days.csv')

# Data structure
# [
#   {'timestamp': 1695556800, 'open': 26562.12, 'high': 26563.45,
#    'low': 26560.89, 'close': 26561.78, 'volume': 12.345},
#   ...
# ]
```

## Optimization Results

Using this data, parameter optimization was performed:

### 1-Minute Timeframe Results
- **Best Sharpe Ratio**: -0.001 (massive losses)
- **Best Parameters**: MA(7,14,30), RSI(21), Threshold(30,45)
- **Return**: -87.06%
- **Win Rate**: 49.01%
- **Trades/Day**: 6.7

### 5-Minute Timeframe Results
- **Best Sharpe Ratio**: 0.262
- **Best Parameters**: MA(3,7,15), RSI(9), Threshold(35,55)
- **Return**: -32.37%
- **Win Rate**: 59.70%
- **Trades/Day**: 11.2

### 15-Minute Timeframe Results
- **Best Sharpe Ratio**: 0.396
- **Best Parameters**: MA(3,7,15), RSI(9), Threshold(35,55)
- **Return**: -3.73%
- **Win Rate**: 52.94%
- **Trades/Day**: 10.5

## Notes

- All backtests used 1x leverage (10x leverage caused catastrophic losses)
- Apex fees: 0.02% maker, 0.05% taker
- MA+RSI strategy is unsuitable for high-frequency volume farming
- Need alternative strategies like Cross-DEX MM or Avellaneda MM

## Archive Date

**Archived**: October 24, 2024