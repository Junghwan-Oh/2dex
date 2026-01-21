# Trading Strategies

This directory contains various trading strategies for perpetual DEX trading. Each strategy is isolated in its own branch with a self-contained directory structure.

## Branch Structure

```
main (74998cd)
 ├─ feature/2dex
 │   └─ perpdex/strategies/2dex/
 ├─ feature/alternate
 │   └─ perpdex/strategies/alternate/
 ├─ feature/mean-reversion-backpack
 │   └─ perpdex/strategies/mean-reversion-backpack/
 └─ feature/mean-reversion-paradex
     └─ perpdex/strategies/mean-reversion-paradex/
```

## Available Strategies

### 1. 2DEX Strategy (feature/2dex)
- **File**: `hedge_mode_2dex.py`
- **Description**: Dual-exchange hedging strategy with passive maker entry and take profit logic
- **Phase**: Phase 2E complete (Passive TP implementation)
- **Features**:
  - Progressive position sizing ($10 → $20 → $50 → $100 → $200 → $500)
  - Rebate tracking for GRVT
  - Passive maker entry logic
  - Take profit close logic

### 2. Alternate Strategy (feature/alternate)
- **File**: `DN_alternate_grvt_paradex.py`
- **Description**: Alternative trading strategy for GRVT and Paradex exchanges
- **Exchanges**: GRVT, Paradex

### 3. Mean Reversion - Backpack (feature/mean-reversion-backpack)
- **File**: `DN_mean_reversion_grvt_backpack_v1.py`
- **Description**: Mean reversion strategy for GRVT and Backpack exchanges
- **Exchanges**: GRVT, Backpack

### 4. Mean Reversion - Paradex (feature/mean-reversion-paradex)
- **File**: `DN_mean_reversion_grvt_paradex.py`
- **Description**: Mean reversion strategy for GRVT and Paradex exchanges
- **Exchanges**: GRVT, Paradex

## Common Structure

Each strategy directory contains:

```
perpdex/strategies/{strategy-name}/
 ├─ {strategy-file}.py          # Main strategy implementation
 ├─ helpers/                     # Helper modules
 │   ├─ __init__.py
 │   ├─ progressive_sizing.py   # Dynamic position sizing
 │   ├─ rebate_tracker.py       # GRVT rebate tracking
 │   ├─ logger.py               # Logging utilities
 │   ├─ lark_bot.py            # Lark notifications
 │   └─ telegram_bot.py        # Telegram notifications
 └─ exchanges/                   # Exchange client implementations
     ├─ __init__.py
     ├─ base.py                 # Base exchange client
     ├─ factory.py              # Exchange factory
     ├─ apex.py, aster.py, backpack.py, edgex.py
     ├─ extended.py, grvt.py, lighter.py, nado.py, paradex.py
     ├─ bp_client.py
     └─ lighter_custom_websocket.py
```

## Usage

To work with a specific strategy:

```bash
# Switch to the strategy branch
git checkout feature/2dex

# Navigate to the strategy directory
cd perpdex/strategies/2dex/

# Run the strategy
python hedge_mode_2dex.py
```

## Development Workflow

1. **Branch per Strategy**: Each strategy lives in its own feature branch
2. **Isolated Development**: Changes to one strategy don't affect others
3. **Performance Comparison**: Run multiple strategies simultaneously for comparison
4. **Merge to Main**: After performance evaluation, the best strategy can be merged to main

## Progressive Sizing

All strategies include progressive sizing functionality:
- Phase 1: $10 (test mode)
- Phase 2: $20
- Phase 3: $50
- Phase 4: $100
- Phase 5: $200
- Phase 6: $500 (maximum)

Position size increases after successful trades, resets on losses.

## Rebate Tracking

Strategies using GRVT exchange include rebate tracking:
- Maker rebate rate: 0.02%
- Automatic accumulation tracking
- Real-time rebate calculation

## Future Work

- [ ] Integrate Progressive Sizing into 7 other bots
- [ ] Complete Phase 2E development for all strategies
- [ ] Performance comparison across all 4 strategies
- [ ] Merge best-performing strategy to main
- [ ] Archive non-performing strategies

## Support

For questions or issues, refer to the individual strategy README in each branch.

---

**Last Updated**: 2026-01-22
**Main Branch**: main (74998cd)
