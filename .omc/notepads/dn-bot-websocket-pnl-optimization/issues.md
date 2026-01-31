# Issues - DN Bot WebSocket PNL Optimization

## Critical Issues

### Issue #1: Cycle 2 Position State Failure
**Severity**: HIGH
**Status**: OPEN
**Date**: 2026-01-31

**Symptoms**:
```
INFO: [CYCLE 2] Starting SELL_FIRST cycle
INFO: [FILL] ETH order filled: 0.038 @ $2631.5
INFO: [FILL] SOL order filled: 0.9 @ $115.09
ERROR: [SAFETY] Cycle 2 FAILED! Bot stopping to prevent position accumulation.
ERROR: [SAFETY] Check positions manually before restarting. ETH and SOL positions should be near 0.
```

**Root Cause**:
After successful entry in Cycle 2, the bot detected a failure condition and stopped. The positions were actually filled correctly, but the bot's state check failed.

**Investigation Needed**:
1. Check position monitoring logic after entry
2. Verify `_is_entry_phase` flag handling
3. Review state transition between entry and exit phases
4. Check if positions are properly tracked after fill

**Hypothesis**:
- The bot may be checking positions too quickly after entry
- Position state may not be updated before the safety check
- There may be a race condition in position polling

**Reproduction**:
```bash
python3 DN_pair_eth_sol_nado.py --size 100 --iter 3 --sleep 2 \
    --env-file /Users/botfarmer/2dex/.env \
    --csv-path /tmp/test_dn_trades.csv \
    --min-spread-bps 0 --use-ioc
```

**Workaround**:
Run with `--iter 1` for single cycle testing.

**Files to Check**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Main bot logic
- Position monitoring functions: `get_account_positions()`
- State handling: `_is_entry_phase`, `_is_exit_phase`

---

## Medium Priority Issues

### Issue #2: Spread Filter Too Restrictive
**Severity**: MEDIUM
**Status**: KNOWN
**Date**: 2026-01-31

**Symptoms**:
```
WARNING: [BUILD] SPREAD FILTER SKIP: Spread below threshold: ETH=0.4bps, SOL=0.9bps < 6bps
ERROR: [SAFETY] Cycle 1 FAILED! Bot stopping to prevent position accumulation.
```

**Root Cause**:
Default `min-spread-bps=6` is too high for current market conditions where spreads are typically < 2 bps.

**Impact**:
- Bot skips most trading opportunities
- May prevent any cycles from running in normal market

**Solutions**:
1. Lower default min-spread-bps to 2 or 3
2. Add dynamic spread threshold based on historical data
3. Add `--min-spread-bps 0` option for testing

**Current Workaround**:
Use `--min-spread-bps 0` to disable filter:
```bash
python3 DN_pair_eth_sol_nado.py --size 100 --iter 5 --min-spread-bps 0
```

**Files to Modify**:
- `DN_pair_eth_sol_nado.py` - Default `min_spread_bps` parameter

---

### Issue #3: POST_ONLY Orders Not Filling
**Severity**: MEDIUM
**Status**: KNOWN
**Date**: 2026-01-31

**Symptoms**:
```
INFO: [ORDER] Placing POST_ONLY orders: ETH buy 0.038 @ $2631.7, SOL sell 0.869 @ $115.1
WARNING: [ORDER] POST_ONLY partial/no fill: ETH=False, SOL=False
WARNING: [FILL] ETH order did not fill
WARNING: [FILL] SOL order did not fill
```

**Root Cause**:
POST_ONLY orders rest on the book at the touch price. In fast-moving markets, these orders may not fill if price moves away.

**Impact**:
- POST_ONLY mode may result in zero fills
- Reduces trading frequency
- May cause cycles to fail

**Solutions**:
1. Implement IOC fallback when POST_ONLY doesn't fill within timeout
2. Increase POST_ONLY timeout (currently 5 seconds)
3. Adjust limit price to be more aggressive while still POST_ONLY
4. Add option to use IOC for entry and POST_ONLY for exit

**Current Workaround**:
Use `--use-ioc` flag for guaranteed fills:
```bash
python3 DN_pair_eth_sol_nado.py --size 100 --iter 5 --use-ioc
```

**Code Reference**:
`DN_pair_eth_sol_nado.py` lines 387-461 (POST_ONLY logic)

---

## Low Priority Issues

### Issue #4: 30-Second Entry Timeout
**Severity**: LOW
**Status**: ENHANCEMENT
**Date**: 2026-01-31

**Symptoms**:
```
INFO: [ENTRY] Monitoring BBO for optimal entry (timeout=30s)
INFO: [ENTRY] Timeout after 30.1s, entering with 0.9bps spread (threshold was 25bps)
```

**Root Cause**:
Bot waits 30 seconds for optimal entry conditions. Most of the time, it times out and enters anyway.

**Impact**:
- Reduces trading frequency
- Adds 30 seconds per cycle
- May miss trading opportunities

**Solutions**:
1. Reduce timeout to 10-15 seconds
2. Implement progressive timeout (start short, increase if needed)
3. Skip entry monitoring entirely for faster cycles
4. Add `--entry-timeout` parameter

**Current Behavior**:
Waits 30 seconds, then enters with current spread.

**Code Reference**:
`DN_pair_eth_sol_nado.py` entry monitoring logic

---

### Issue #5: Limited Spread State Observation
**Severity**: LOW
**Status**: TESTING LIMITATION
**Date**: 2026-01-31

**Symptoms**:
Only observed STABLE spread state during testing. WIDENING and NARROWING states not triggered.

**Root Cause**:
Short test duration (2-3 seconds between entry/exit) doesn't allow spread state to change.

**Impact**:
- Cannot validate WIDENING/NARROWING dynamic exit thresholds
- Unknown if these states work correctly

**Solutions**:
1. Run longer test with `--sleep 30` or more
2. Simulate spread state changes for testing
3. Add manual override for spread state
4. Test during high volatility periods

**Current Workaround**:
Assume STABLE state works correctly. Need longer test for other states.

**Testing Command**:
```bash
python3 DN_pair_eth_sol_nado.py --size 100 --iter 10 --sleep 60
```

---

## Gotchas and Pitfalls

### Gotcha #1: .env File Path
**Issue**: Bot looks for .env in current directory by default
**Error**: `Error: .env file not found: /Users/botfarmer/2dex/hedge/.env`
**Solution**: Always provide absolute path: `--env-file /Users/botfarmer/2dex/.env`

### Gotcha #2: Python vs Python3
**Issue**: `python` command not found on macOS
**Error**: `command not found: python`
**Solution**: Use `python3` instead

### Gotcha #3: Position Accumulation Safety
**Issue**: Bot stops if it detects position accumulation
**Error**: `ERROR: [SAFETY] Cycle 2 FAILED! Bot stopping to prevent position accumulation.`
**Solution**: This is a safety feature. Check positions manually before restarting.

### Gotcha #4: CSV File Overwrite
**Issue**: CSV file is overwritten each run
**Impact**: Previous test data lost
**Solution**: Use unique CSV path: `--csv-path /tmp/test_dn_trades_$(date +%s).csv`

### Gotcha #5: Slippage Threshold
**Issue**: 10 bps slippage threshold may skip trades in volatile markets
**Impact**: Low fill rate in high volatility
**Solution**: Adjust threshold in code or accept lower fill rate

---

## Debugging Tips

### Enable Debug Logging
Add to code:
```python
self.logger.setLevel(logging.DEBUG)
```

### Check WebSocket Status
Look for:
```
[NADO WEBSOCKET] Import successful - WEBSOCKET_AVAILABLE = True
[INIT] WebSocket status for ETH: CONNECTED
[INIT] WebSocket status for SOL: CONNECTED
```

### Verify Position State
Check logs for:
```
[STARTUP] Checking for residual positions...
[STARTUP] ETH position: 0
[STARTUP] SOL position: 0
```

### Monitor Order Fills
Look for:
```
[FILL] ETH order filled: 0.038 @ $2631.8
[FILL] SOL order filled: 0.9 @ $115.06
```

### Track PNL
Check:
```
[PNL] Real-time: ETH=$-0.02, SOL=$-0.01, Total=$-0.02 (unrealized)
[PNL] Cycle 1 Final: NoFee=$-0.02, WithFee=$-0.23, Fees=$0.20
```

---

## Resolution Status

| Issue | Severity | Status | Resolution Date |
|-------|----------|--------|-----------------|
| #1 - Position State Failure | HIGH | OPEN | TBD |
| #2 - Spread Filter | MEDIUM | KNOWN | Workaround available |
| #3 - POST_ONLY Fills | MEDIUM | KNOWN | Workaround available |
| #4 - Entry Timeout | LOW | ENHANCEMENT | TBD |
| #5 - Spread State Testing | LOW | TESTING | Need longer test |

---

**Last Updated**: 2026-01-31
**Test Phase**: Dry Run Testing (Phase 1)
**Next Phase**: Extended testing with longer duration
