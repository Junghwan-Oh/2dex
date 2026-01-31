# Cycle 2 Position State Failure - Fix

## Problem
The bot successfully completed Cycle 1 (entry + exit) but stopped after entry in Cycle 2 with a TypeError:
```
TypeError: log_trade_to_csv() got an unexpected keyword argument 'eth_pnl'
```

## Root Cause
The `place_simultaneous_orders` function was determining whether an order was an "exit" order based on the direction:
- `is_exit=(eth_direction == "sell")` for ETH
- `is_exit=(sol_direction == "buy")` for SOL

This worked for BUY_FIRST cycles:
- BUILD: ETH buy (is_exit=False), SOL sell (is_exit=False) ✓

But failed for SELL_FIRST cycles:
- BUILD: ETH sell (is_exit=True), SOL buy (is_exit=True) ✗
- This caused the code to try to calculate PNL during BUILD phase
- PNL calculation added `eth_pnl` and `sol_pnl` params that `log_trade_to_csv` didn't accept

## Fix
Changed the logic to use phase flags (`_is_entry_phase` and `_is_exit_phase`) instead of direction to determine if it's an exit order:

```python
# OLD (broken):
is_exit=(eth_direction == "sell")  # Wrong for SELL_FIRST BUILD

# NEW (fixed):
is_exit_order = hasattr(self, '_is_exit_phase') and self._is_exit_phase
```

Also removed the unused `eth_pnl` and `sol_pnl` params that were being added to CSV params but not accepted by `log_trade_to_csv`.

## Files Modified
- /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py:
  - Lines ~570-610: Fixed `is_exit` logic in CSV logging
  - Lines ~750-760: Removed unused `eth_pnl`/`sol_pnl` params
  - Lines ~1727-1732: Added exception logging for debugging

## Testing
Verified with --iter 3 --use-ioc --min-spread-bps 0:
- Cycle 1 (BUY_FIRST): BUILD + UNWIND ✓
- Cycle 2 (SELL_FIRST): BUILD + UNWIND ✓
- Cycle 3 (BUY_FIRST): BUILD + UNWIND ✓

All cycles completed successfully.
