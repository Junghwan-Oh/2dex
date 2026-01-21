# 2DEX Hedging Strategy

Dual-exchange hedging strategy with passive maker entry and take profit logic.

## Overview

This strategy implements a sophisticated hedging approach across two exchanges, utilizing passive maker orders for entry and dynamic take profit logic for exits.

### Key Features

- **Passive Maker Entry**: Place passive maker orders to earn rebates
- **Take Profit Logic**: Dynamic TP calculation based on market conditions
- **Progressive Position Sizing**: Automatic position scaling from $10 to $500
- **Rebate Tracking**: Real-time GRVT maker rebate accumulation (0.02%)
- **Risk Management**: Built-in stop loss and position limits

## Current Status

- **Phase**: Phase 2E Complete
- **Implementation**: Passive TP close logic fully integrated
- **Testing**: Ready for performance evaluation

## Quick Start

```bash
# Switch to this branch
git checkout feature/2dex

# Navigate to strategy directory
cd perpdex/strategies/2dex/

# Configure environment (if needed)
# cp .env.example .env
# Edit .env with your API keys

# Run the strategy
python hedge_mode_2dex.py
```

## Configuration

### Progressive Sizing Phases

| Phase | Position Size | Trigger |
|-------|--------------|---------|
| 1 | $10 | Initial (test mode) |
| 2 | $20 | After successful Phase 1 |
| 3 | $50 | After successful Phase 2 |
| 4 | $100 | After successful Phase 3 |
| 5 | $200 | After successful Phase 4 |
| 6 | $500 | After successful Phase 5 (max) |

Position size automatically increases after profitable trades and resets on losses.

### Rebate Tracking

- **Exchange**: GRVT
- **Maker Rebate**: 0.02%
- **Tracking**: Automatic accumulation
- **Reporting**: Real-time balance updates

## Architecture

```
perpdex/strategies/2dex/
 ├─ hedge_mode_2dex.py          # Main strategy (68,776 bytes)
 ├─ helpers/
 │   ├─ progressive_sizing.py   # Position sizing manager (12,386 bytes)
 │   ├─ rebate_tracker.py       # Rebate tracking (9,386 bytes)
 │   ├─ logger.py               # Logging utilities (4,489 bytes)
 │   ├─ lark_bot.py            # Lark notifications (2,365 bytes)
 │   └─ telegram_bot.py        # Telegram notifications (1,809 bytes)
 └─ exchanges/
     ├─ base.py                 # Base exchange interface
     ├─ factory.py              # Exchange factory pattern
     └─ [14 exchange implementations]
```

## Strategy Logic

### Entry Phase

1. Monitor market conditions across both exchanges
2. Identify price discrepancies suitable for hedging
3. Place passive maker orders to capture spread + rebate
4. Wait for order fills on both sides

### Execution Phase

1. Monitor filled positions across exchanges
2. Track PnL in real-time
3. Apply progressive sizing based on performance
4. Calculate take profit targets dynamically

### Exit Phase

1. Monitor take profit conditions
2. Execute passive TP orders when targets hit
3. Handle partial fills and position rebalancing
4. Track rebates and net PnL

## Performance Metrics

The strategy tracks:
- Total trades executed
- Win rate percentage
- Average profit per trade
- Total rebates earned
- Progressive sizing phase reached
- Net PnL (including rebates)

## Dependencies

- Python 3.8+
- asyncio for async operations
- Exchange API clients (in exchanges/ module)
- Helper utilities (in helpers/ module)

## Development History

- **Initial**: Basic dual-exchange hedging
- **Phase 2A**: Passive maker entry implemented
- **Phase 2B**: Progressive sizing integrated
- **Phase 2C**: Rebate tracking added
- **Phase 2D**: Enhanced risk management
- **Phase 2E**: Passive TP close logic (current)

## Future Enhancements

- [ ] Multi-pair support
- [ ] Advanced risk metrics
- [ ] Machine learning price prediction
- [ ] Automated parameter optimization
- [ ] Enhanced monitoring dashboard

## Troubleshooting

### Common Issues

**Issue**: Orders not filling
- Check spread requirements in config
- Verify API key permissions
- Ensure sufficient balance on both exchanges

**Issue**: Rebate tracking incorrect
- Verify GRVT API connection
- Check maker order confirmation
- Review rebate rate configuration

**Issue**: Progressive sizing not advancing
- Check win rate requirements
- Verify profit thresholds met
- Review position sizing logs

## Support

For questions or issues specific to this strategy:
1. Check logs in `logs/` directory
2. Review error messages in console output
3. Verify exchange API connectivity
4. Consult main strategies README: `perpdex/strategies/README.md`

---

**Branch**: feature/2dex
**Strategy File**: hedge_mode_2dex.py
**Last Updated**: 2026-01-22
