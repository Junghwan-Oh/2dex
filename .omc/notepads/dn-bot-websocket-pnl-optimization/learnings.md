# Learnings - DN Bot WebSocket PNL Optimization

## WebSocket Integration Patterns

### BBO Handler Momentum Detection
**Pattern**: Get momentum from BBO handler with null safety
```python
try:
    if self.eth_client and self.eth_client.get_bbo_handler():
        eth_momentum = self.eth_client.get_bbo_handler().get_momentum()
except Exception as e:
    self.logger.warning(f"[MOMENTUM] Error getting ETH momentum: {e}")
```

**Key Learning**: Always wrap WebSocket handler access in try-except blocks. WebSocket data may be temporarily unavailable during initialization.

### Dynamic Threshold Calculation
**Pattern**: Use spread state to adjust exit thresholds
```python
def _calculate_dynamic_exit_thresholds(self) -> dict:
    from exchanges.nado import WEBSOCKET_AVAILABLE
    if not WEBSOCKET_AVAILABLE:
        return {"profit_target_bps": 15, "stop_loss_bps": 30, "spread_state": None}

    # Get spread state from BBO handler
    eth_spread_state = self.eth_client.get_bbo_handler().get_spread_state()
    sol_spread_state = self.sol_client.get_bbo_handler().get_spread_state()

    # Adjust thresholds based on state
    if eth_spread_state == "WIDENING" or sol_spread_state == "WIDENING":
        return {"profit_target_bps": 25, "stop_loss_bps": 40, "spread_state": "WIDENING"}
    elif eth_spread_state == "NARROWING" or sol_spread_state == "NARROWING":
        return {"profit_target_bps": 10, "stop_loss_bps": 30, "spread_state": "NARROWING"}
    else:
        return {"profit_target_bps": 15, "stop_loss_bps": 30, "spread_state": "STABLE"}
```

**Key Learning**: Fallback to default thresholds when WebSocket unavailable. Maintain conservative approach.

### Liquidity-Based Skip Logic
**Pattern**: Use qty=0 as signal to skip trade
```python
async def calculate_order_size_with_slippage(self, price, ticker, direction, max_slippage_bps=20):
    LIQUIDITY_THRESHOLD_BPS = 10
    slippage = await client.estimate_slippage(direction, target_qty)

    if slippage > LIQUIDITY_THRESHOLD_BPS:
        self.logger.warning(f"[SLIPPAGE] {ticker} slippage {slippage:.1f} bps > {LIQUIDITY_THRESHOLD_BPS} bps threshold - SKIPPING TRADE")
        return Decimal(0), slippage, False  # qty=0 signals skip

    return target_qty, slippage, True
```

**Key Learning**: Using qty=0 as skip signal allows clean separation between size calculation and execution logic.

## CSV Logging Patterns

### Extended CSV Parameters
**Pattern**: Prepare all parameters in dictionary before logging
```python
def _prepare_csv_params(self, exchange, side, price, quantity, order_type, mode, fee_usd, is_exit) -> dict:
    from exchanges.nado import WEBSOCKET_AVAILABLE

    # Get WebSocket decision factors
    eth_momentum = getattr(self, '_eth_momentum_state', '')
    sol_momentum = getattr(self, '_sol_momentum_state', '')
    spread_state_entry = getattr(self, '_spread_state_entry', '')
    # ... more fields

    params = {
        "exchange": exchange,
        "side": side,
        # ... base fields
        # TASK 6: WebSocket decision factors
        "eth_momentum_state": eth_momentum,
        "sol_momentum_state": sol_momentum,
        "spread_state_entry": spread_state_entry,
        "websocket_available": "true" if WEBSOCKET_AVAILABLE else "false"
    }
    return params
```

**Key Learning**: Use getattr() with default values for optional attributes to avoid KeyError.

## Testing Patterns

### Dry Run Testing
**Command**:
```bash
python3 DN_pair_eth_sol_nado.py --size 100 --iter 3 --sleep 2 \
    --env-file /path/to/.env \
    --csv-path /tmp/test_dn_trades.csv \
    --min-spread-bps 0 --use-ioc
```

**Parameters**:
- `--size 100`: $100 notional per position (small for testing)
- `--iter 3`: Run 3 iterations (quick test)
- `--sleep 2`: 2 second delay between entry/exit (observe spread changes)
- `--min-spread-bps 0`: Disable spread filter for testing
- `--use-ioc`: Use IOC orders for guaranteed fills

**Key Learning**: IOC mode better for testing than POST_ONLY (which may not fill).

### Log Extraction for Validation
**Extract WebSocket Logs**:
```bash
cat output.log | grep -E "\[MOMENTUM\]|\[SLIPPAGE\]|\[LIQUIDITY\]|\[EXIT\]|\[ENTRY\]|WS=|spread_state"
```

**Count CSV Columns**:
```bash
head -1 test_dn_trades.csv | tr ',' '\n' | nl
```

**Key Learning**: Use grep patterns with log tags (e.g., [MOMENTUM]) for easy log filtering.

## Configuration Patterns

### Environment Setup
**Pattern**: Use absolute path for .env file
```bash
--env-file /Users/botfarmer/2dex/.env
```

**Issue**: Bot looks for .env in current directory by default
**Solution**: Always provide absolute path when running from different directory

### Fee Rate Configuration
**Pattern**: Set fee rate based on order mode
```python
FEE_RATE = Decimal("0.0002") if self.use_post_only else Decimal("0.0005")
fee_bps = float(FEE_RATE * 10000)
```

- POST_ONLY: 2 bps (maker)
- IOC: 5 bps (taker)

**Key Learning**: Calculate fee_bps for logging, use FEE_RATE for calculations.

## Error Handling Patterns

### Emergency Unwind
**Pattern**: Check both legs before unwinding
```python
async def handle_emergency_unwind(self, eth_result, sol_result):
    eth_filled = eth_result.success and eth_result.status == 'FILLED'
    sol_filled = sol_result.success and sol_result.status == 'FILLED'

    if eth_filled and not sol_filled:
        await self.emergency_unwind_eth()
    elif sol_filled and not eth_filled:
        await self.emergency_unwind_sol()
```

**Key Learning**: Only unwind when one leg fills and other fails. If both fail, no unwind needed.

### Position State Validation
**Pattern**: Check positions before starting cycle
```python
[STARTUP] Checking for residual positions...
[STARTUP] ETH position: 0
[STARTUP] SOL position: 0
[STARTUP] No residual positions. Ready to start.
```

**Key Learning**: Always validate clean state before starting new cycle.

## Common Issues and Solutions

### Issue 1: POST_ONLY Orders Not Filling
**Symptom**: `[FILL] ETH order did not fill`
**Cause**: POST_ONLY orders rest on book, may not fill immediately
**Solution**: Use `--use-ioc` flag for testing, or implement fallback to IOC

### Issue 2: Spread Filter Too Restrictive
**Symptom**: `SPREAD FILTER SKIP: Spread below threshold: ETH=0.4bps, SOL=0.9bps < 6bps`
**Cause**: Default min-spread-bps=6 too high for current market
**Solution**: Use `--min-spread-bps 0` to disable filter for testing

### Issue 3: Position State After Cycle
**Symptom**: `ERROR: [SAFETY] Cycle 2 FAILED! Bot stopping`
**Cause**: Position state issue after entry
**Solution**: Investigate position monitoring logic, add more state checks

## Performance Optimization

### Slippage Estimation
**Current**: 10 bps threshold for skip
**Rationale**: Balances fill rate with cost avoidance
**Trade-off**: Lower threshold = more skips but better execution

### Entry Timing
**Current**: 30 second timeout for optimal entry
**Rationale**: Allows BBO monitoring for better entry
**Trade-off**: Longer timeout = fewer cycles but better entries

### Exit Thresholds
**STABLE**: 15 bps profit, 5 bps quick exit, -30 bps stop loss
**WIDENING**: 25 bps profit, -40 bps stop loss (wider exits)
**NARROWING**: 10 bps profit (quick exit)

**Key Learning**: Dynamic thresholds adapt to market conditions.

## Monitoring and Debugging

### Key Log Tags
- `[INIT]`: Initialization and connection
- `[ENTRY]`: Entry phase decisions
- `[BUILD]`: Entry execution
- `[EXIT]`: Exit phase decisions
- `[UNWIND]`: Exit execution
- `[MOMENTUM]`: Momentum filter checks
- `[SLIPPAGE]`: Slippage estimation
- `[LIQUIDITY]`: Liquidity checks
- `[PNL]`: PNL calculations
- `[SAFETY]`: Safety checks and errors

### Real-time PNL Tracking
**Pattern**: Log unrealized PNL during position
```python
[PNL] Real-time: ETH=$-0.02, SOL=$-0.01, Total=$-0.02 (unrealized)
```

**Key Learning**: Real-time PNL helps monitor position health during cycle.

## Future Improvements

1. **WIDENING/NARROWING State Testing**: Need longer test to observe spread state changes
2. **POST_ONLY Fallback**: Implement IOC fallback when POST_ONLY doesn't fill
3. **Position Recovery**: Add logic to recover from position state issues
4. **Spread Filter Calibration**: Adjust min-spread-bps based on market conditions
5. **Funding Rate Tracking**: Add funding rate to PNL calculation

---
**Last Updated**: 2026-01-31
**Status**: Phase 1 Complete - WebSocket Features Validated
