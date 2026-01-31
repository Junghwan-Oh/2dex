# Phase 6: POST_ONLY Entry Option - Learnings

## Implementation Summary

### Task 6.1: POST_ONLY Entry Mode Configuration
- Added `use_post_only` parameter to `DNPairBot.__init__()` with default False (IOC mode)
- Added `self.order_mode` to track current mode ("post_only" or "ioc")
- Configuration logged at startup via `_config_logger`

### Task 6.2: POST_ONLY Order Placement
- Modified `place_simultaneous_orders()` to support both IOC and POST_ONLY modes
- POST_ONLY uses `place_open_order()` (which uses OrderType.POST_ONLY via SDK)
- IOC uses `place_ioc_order()` (existing logic)
- Fee rate adjusts dynamically: 2 bps for POST_ONLY (maker) vs 5 bps for IOC (taker)

## Key Technical Decisions

### NadoClient API Discovery
The NadoClient provides:
- `place_ioc_order()`: Immediate-Or-Cancel, aggressive, 5 bps taker fee
- `place_open_order()`: Uses OrderType.POST_ONLY appendix, passive, 2 bps maker fee

### Fee Rate Calculation
```python
FEE_RATE = Decimal("0.0002") if self.use_post_only else Decimal("0.0005")
# 2 bps (0.02%) for POST_ONLY vs 5 bps (0.05%) for IOC
```

### Order Status Handling
- IOC orders: status='FILLED' when successful
- POST_ONLY orders: status='OPEN' when placed on book (may fill later)
- Updated fill detection logic to handle both statuses

### Price Selection
- IOC mode: Aggressive pricing (cross spread)
  - Buy: `eth_ask` (match with standing sells)
  - Sell: `sol_bid` (match with standing buys)
- POST_ONLY mode: Passive pricing (rest on book)
  - Buy: `eth_ask` (limit order at best ask)
  - Sell: `sol_bid` (limit order at best bid)

## Command Line Interface

Added `--use-post-only` flag:
```bash
# IOC mode (default, 5 bps taker fee)
python DN_pair_eth_sol_nado.py --size 100 --iter 5

# POST_ONLY mode (2 bps maker fee)
python DN_pair_eth_sol_nado.py --size 100 --iter 5 --use-post-only
```

## Future Enhancements (V5.4)

As noted in code comments:
- POST_ONLY orders may not fill immediately (status='OPEN')
- Need fallback logic: if POST_ONLY doesn't fill within timeout, retry with IOC
- Would require monitoring order status and cancelling after timeout

## Testing Notes

- Syntax validation: Passed (python3 -m py_compile)
- Help message: Updated with new flag
- Integration testing: Requires running bot with .env credentials

# Error 2006 Research (2026-01-31)

## Root Cause
Error 2006 "Insufficient account health" occurs when:
1. Account has ZERO collateral (all healths = 0)
2. isolated_margin parameter is less than required initial margin
3. initial_health becomes negative

## Health Calculation Formula
- **Threshold:** initial_health must be > 0 (no minimum percentage)
- **Isolated margin:** isolated_margin >= notional * (1 - long_weight_initial)
- **Current calculation:** isolated_margin = notional / 5 (WRONG)
- **Correct calculation:** isolated_margin = notional * (1 - long_weight) * safety_factor

## Key Findings
1. Testnet account (0x883064f1...de026A) has $0 balance
2. isolated_margin=$18-19 is ~4x lower than required margin (~$90)
3. SDK source: margin_manager.py line 331 shows funds_available = max(0, initial_health)
4. long_weight_initial typically 0.10-0.20 for perps

## Solution
1. Deposit USDT via faucet: https://faucet.test.nado.xyz
2. Query product for actual long_weight_initial value
3. Recalculate isolated_margin with proper formula
4. Or use cross margin (isolated=False) after deposit

## Files Modified/Analyzed
- /Users/botfarmer/2dex/hedge/exchanges/nado.py
- nado_protocol/utils/margin_manager.py (SDK)
- Report: .omc/scientist/reports/20260131_error_2006_analysis.md

