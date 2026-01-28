# Phase 7.6 - Testnet Deployment Guide

**Date**: October 24, 2025
**Status**: READY FOR DEPLOYMENT
**Deployment Script**: `apex/deploy_testnet.py`

---

## Table of Contents

1. [Prerequisites Checklist](#prerequisites-checklist)
2. [Environment Setup](#environment-setup)
3. [Deployment Instructions](#deployment-instructions)
4. [Monitoring & Validation](#monitoring--validation)
5. [Troubleshooting](#troubleshooting)
6. [Success Criteria](#success-criteria)
7. [Post-Deployment Analysis](#post-deployment-analysis)

---

## Prerequisites Checklist

### API Credentials ✅

**Required**:
- [x] Apex Pro API Key (`APEX_API_KEY`)
- [x] Apex Pro API Secret (`APEX_API_SECRET`)
- [x] Apex Pro API Passphrase (`APEX_API_PASSPHRASE`)

**Optional but Recommended**:
- [ ] Omni Key Seed from Apex Pro website
  - Set as `APEX_ZK_SEEDS` in `.env`
  - Set as `APEX_ZK_L2KEY` in `.env` (same value)

**Note**: Omni Key enables order placement. Without it, some operations may fail.
**Important**: Apex Pro provides one "Omni Key Seed" value. Use this same value for both `APEX_ZK_SEEDS` and `APEX_ZK_L2KEY`.

### Python Dependencies ✅

```bash
# Check if installed:
pip list | grep apexomni
pip list | grep websocket-client
pip list | grep python-dotenv

# Install if missing:
pip install apexomni websocket-client python-dotenv
```

### Project Setup ✅

- [x] All Phase 7 components implemented (7.1-7.5)
- [x] Tests passing (20/20 = 100%)
- [x] Log directories created:
  - `logs/`
  - `logs/data/csv/`
  - `logs/data/json/`

### System Requirements

- **OS**: Windows, Linux, or macOS
- **Python**: 3.8+
- **Memory**: 2GB+ available RAM
- **Network**: Stable internet connection (WebSocket required)
- **Disk**: 500MB+ free space (for logs)

---

## Environment Setup

### 1. Configure Environment Variables

Create or update `.env` file in project root:

```bash
# Apex Pro API Credentials (Required)
APEX_API_KEY=your-api-key-here
APEX_API_SECRET=your-api-secret-here
APEX_API_PASSPHRASE=your-passphrase-here

# Omni Key Seed (Optional - for order placement)
# Get "Omni Key Seed" from Apex Pro website, use the SAME value for both:
APEX_ZK_SEEDS=your-omni-key-seed-here
APEX_ZK_L2KEY=your-omni-key-seed-here
```

**Security Notes**:
- Never commit `.env` file to version control
- Store credentials securely
- Use testnet credentials only for testnet deployment

### 2. Verify API Connection

```bash
cd "perpdex farm"
python apex/check_zk_keys.py
```

**Expected Output**:
```
====================================================
OMNI KEY STATUS CHECK
====================================================

APEX_API_KEY: [OK] SET
APEX_API_SECRET: [OK] SET
APEX_API_PASSPHRASE: [OK] SET

APEX_ZK_SEEDS: [OK] SET / [X] NOT SET
APEX_ZK_L2KEY: [OK] SET / [X] NOT SET
(Note: Both should have the same Omni Key Seed value)

====================================================
[OK] API CREDENTIALS CONFIGURED
====================================================
```

### 3. Run Pre-Deployment Checks

The deployment script automatically runs pre-deployment checks, but you can test manually:

```bash
cd "perpdex farm"
python -c "from apex.deploy_testnet import pre_deployment_checks; pre_deployment_checks()"
```

**Expected Output**:
```
================================================================================
PRE-DEPLOYMENT SAFETY CHECKS
================================================================================

[1/5] Checking environment variables...
  ✓ APEX_API_KEY configured
  ✓ APEX_API_SECRET configured
  ✓ APEX_API_PASSPHRASE configured

[2/5] Checking Omni Key...
  ✓ Omni Key configured

[3/5] Checking log directories...
  ✓ logs exists
  ✓ logs/data exists
  ✓ logs/data/csv exists
  ✓ logs/data/json exists

[4/5] Checking Python dependencies...
  ✓ apexomni installed
  ✓ websocket installed

[5/5] Checking test results...
  ✓ Component tests completed

================================================================================
✓ All critical checks passed - Ready for deployment
================================================================================
```

---

## Deployment Instructions

### Step 1: Dry-Run Test (Recommended)

Test the deployment setup without placing real orders:

```bash
cd "perpdex farm"
python apex/deploy_testnet.py --mode static --dry-run
```

**What This Does**:
- Initializes all components
- Validates configuration
- Simulates 5-second execution
- NO real orders placed
- Verifies logging and monitoring work

**Expected Output**:
```
================================================================================
AVELLANEDA MARKET MAKER - TESTNET DEPLOYMENT
================================================================================

Mode:          STATIC
Symbol:        BTC-USDT
Duration:      3600s (1.0h)
Position Limit: 0.001 BTC
Daily Loss Limit: $1.0
Drawdown Limit: 5.0%
Dry-Run:       YES (no real orders)
Environment:   TESTNET

================================================================================

[INIT] Initializing components...
  ✓ Trading client initialized
  ✓ Monitoring dashboard initialized
  ✓ Data logger initialized (avellaneda_static_testnet_20251024_HHMMSS)
  ✓ Logger integrated with client

[START] Starting monitoring dashboard...

[DRY-RUN] Simulating strategy execution...
[DRY-RUN] Simulation complete

[COMPLETE] Strategy execution finished

[CLEANUP] Shutting down...
  ✓ Dashboard stopped
  ✓ Logs flushed

[STATS] Final Statistics:
  Total Trades:  0
  Win Rate:      0.0%
  Net P&L:       $0.00
  Total Fees:    $0.00

[EXPORT] Data exported:
  - trades: logs/data/json/avellaneda_static_testnet_20251024_HHMMSS_trades_export_*.json
  - decisions: logs/data/json/avellaneda_static_testnet_20251024_HHMMSS_decisions_export_*.json
  - errors: logs/data/json/avellaneda_static_testnet_20251024_HHMMSS_errors_export_*.json

================================================================================
DEPLOYMENT COMPLETE
================================================================================
```

### Step 2: Deploy Static Parameters (Control Group)

Deploy the strategy with static Avellaneda parameters:

```bash
cd "perpdex farm"
python apex/deploy_testnet.py --mode static --duration 3600
```

**Parameters**:
- `--mode static`: Use fixed parameters (gamma=0.1, sigma=0.02, k=1.5)
- `--duration 3600`: Run for 1 hour (3600 seconds)

**User Confirmation Prompt**:
```
================================================================================
⚠️  WARNING: This will place REAL ORDERS on TESTNET
================================================================================

Type 'DEPLOY' to confirm deployment:
```

**Type `DEPLOY` and press Enter to proceed.**

### Step 3: Deploy Dynamic Parameters (Test Group)

In a separate terminal, deploy with dynamic parameter estimation:

```bash
cd "perpdex farm"
python apex/deploy_testnet.py --mode dynamic --duration 3600
```

**Parameters**:
- `--mode dynamic`: Use Order Book Analyzer for parameter estimation
- `--duration 3600`: Run for 1 hour (3600 seconds)

**Note**: Run both deployments simultaneously for A/B comparison.

### Step 4: Monitor Execution

Both deployments will display real-time monitoring dashboard:

```
================================================================================
📊 PROFIT & LOSS                      🏦 POSITION
================================================================================
Total Equity:      $100.00           Position:         0.001 BTC
Unrealized P&L:    $0.00            Side:             LONG
Realized P&L:      $0.00            Entry Price:      $67,500.00
Daily P&L:         $0.00            Mark Price:       $67,505.00
                                     Unrealized P&L:   $0.05

================================================================================
⚠️  RISK METRICS                     📈 PERFORMANCE
================================================================================
Max Drawdown:      0.0%             Total Trades:     5
Daily Loss:        $0.00 / $1.00    Win Rate:         60.0%
Position Limit:    0.001 / 0.001    Sharpe Ratio:     1.234
Risk Status:       OK                Avg Spread:       0.025%

================================================================================
📋 RECENT TRADES (Last 5)
================================================================================
[12:34:56] BUY  0.001 BTC @ $67,500.00 | Fee: $0.135 | P&L: +$0.50 | Spread: 0.025%
[12:35:23] SELL 0.001 BTC @ $67,512.50 | Fee: $0.135 | P&L: +$0.12 | Spread: 0.025%
...

================================================================================
🚨 ALERTS
================================================================================
[INFO] Strategy started successfully
[INFO] Order placed: BUY 0.001 BTC @ $67,500.00
...
```

**Dashboard Updates**: Refreshes every 5 seconds

---

## Monitoring & Validation

### Real-Time Monitoring

**What to Watch**:

1. **Position Size**:
   - Should NEVER exceed `position_limit` (default: 0.001 BTC)
   - Check "Position Limit" in Risk Metrics section

2. **Daily P&L**:
   - Should NEVER drop below `-max_daily_loss` (default: -$1.00)
   - Check "Daily Loss" in Risk Metrics section

3. **Drawdown**:
   - Should NEVER exceed `max_total_drawdown` (default: 5%)
   - Check "Max Drawdown" in Risk Metrics section

4. **Order Types**:
   - ALL orders should be POST_ONLY (maker orders)
   - Verify in Recent Trades section

5. **Spread Captured**:
   - Should be positive on most trades
   - Check "Spread" column in Recent Trades

**Expected Behavior**:
- Orders placed every 30-60 seconds
- Inventory oscillates around 0 (market neutral)
- Daily P&L gradually increases (or decreases slowly)
- No risk limit breaches

### Log File Monitoring

**Console Logs**:
```bash
# Real-time log viewing:
tail -f "logs/avellaneda_testnet_20251024.log"
```

**Expected Log Entries**:
```
2025-10-24 12:34:56,123 - INFO - Strategy started with static parameters
2025-10-24 12:34:57,456 - INFO - WebSocket connected successfully
2025-10-24 12:34:58,789 - DEBUG - Order book updated: bid=$67,500.00, ask=$67,501.00
2025-10-24 12:35:00,123 - INFO - Optimal spread calculated: bid=0.025%, ask=0.025%
2025-10-24 12:35:01,456 - INFO - Order placed: BUY 0.001 BTC @ $67,500.00 (POST_ONLY)
2025-10-24 12:35:30,789 - INFO - Trade executed: BUY 0.001 BTC @ $67,500.00
2025-10-24 12:35:31,123 - INFO - P&L: +$0.50, Spread captured: 0.025%
```

**Warning Indicators**:
```
WARNING - Daily loss approaching limit: -$0.80 / -$1.00
WARNING - Drawdown at 4.5% (limit: 5.0%)
WARNING - Position size at 95% of limit
```

**Error Indicators**:
```
ERROR - Order placement failed: [reason]
ERROR - WebSocket disconnected: [reason]
CRITICAL - Risk limit breached: Daily loss -$1.05 > -$1.00
```

### CSV Data Files

Check CSV files for detailed trade history:

```bash
# View trades:
cat "logs/data/csv/avellaneda_static_testnet_20251024_trades.csv"

# View decisions:
cat "logs/data/csv/avellaneda_static_testnet_20251024_decisions.csv"

# View errors:
cat "logs/data/csv/avellaneda_static_testnet_20251024_errors.csv"
```

---

## Troubleshooting

### Issue 1: Pre-Deployment Checks Fail

**Symptom**: "Pre-deployment checks failed. Fix issues before proceeding."

**Cause**: Missing environment variables, dependencies, or directories

**Solution**:
1. Check which check failed in the output
2. Fix the specific issue:
   - **Environment Variables**: Update `.env` file
   - **Dependencies**: Run `pip install apexomni websocket-client`
   - **Directories**: Run `mkdir -p logs/data/csv logs/data/json`
3. Re-run deployment script

### Issue 2: Omni Key Missing

**Symptom**: "⚠ Omni Key not configured (order placement may fail)"

**Cause**: `APEX_ZK_SEEDS` or `APEX_ZK_L2KEY` not set in `.env`

**Solution**:
1. Obtain "Omni Key Seed" from Apex Pro website (API Management → Omni Key)
2. Add to `.env` file (use the SAME value for both):
   ```
   APEX_ZK_SEEDS=your-omni-key-seed-here
   APEX_ZK_L2KEY=your-omni-key-seed-here
   ```
3. Restart deployment

**Note**: Deployment may work without Omni Key on testnet, but order placement might fail.
**Important**: Apex Pro provides one "Omni Key Seed". Copy this value to both environment variables.

### Issue 3: Order Placement Fails

**Symptom**: "ERROR - Order placement failed: [reason]"

**Possible Causes**:
- Insufficient balance
- Invalid API credentials
- Omni Key not configured
- Network connectivity issues

**Solution**:
1. Check API credentials in `.env`
2. Verify testnet balance (should have USDT for fees)
3. Ensure Omni Key is configured (same value for APEX_ZK_SEEDS and APEX_ZK_L2KEY)
4. Check network connection

### Issue 4: WebSocket Disconnects

**Symptom**: "ERROR - WebSocket disconnected: [reason]"

**Cause**: Network instability, API rate limits, or server issues

**Solution**:
- Client automatically attempts reconnection
- Monitor logs for "WebSocket connected successfully"
- If persistent, check network stability

### Issue 5: Risk Limit Breach

**Symptom**: "CRITICAL - Risk limit breached: [reason]"

**Cause**: Daily loss, drawdown, or position limit exceeded

**Expected Behavior**:
- Strategy automatically shuts down
- Logs final statistics
- Exports data to JSON

**Action Required**:
1. Review logs to understand cause
2. Analyze trade history in CSV files
3. Adjust risk parameters if needed:
   ```bash
   python apex/deploy_testnet.py --mode static --max-daily-loss 2.0 --max-drawdown 10.0
   ```

### Issue 6: No Trades Executed

**Symptom**: Dashboard shows "Total Trades: 0" after 10+ minutes

**Possible Causes**:
- Market conditions (no fills at target spreads)
- Order placement failures (check logs)
- Spread too wide (not competitive)

**Solution**:
1. Check logs for order placement errors
2. Verify market is active (check Apex Pro UI)
3. Consider reducing spread parameters (advanced)

### Issue 7: Performance Slower Than Backtest

**Symptom**: Live P&L significantly worse than backtest results

**Expected**: Live performance may differ from backtest due to:
- Real slippage and execution delays
- Different market conditions
- Order book dynamics

**Action**:
1. Run for full 1-hour duration before concluding
2. Compare static vs dynamic performance
3. Review decision logs for parameter differences

---

## Success Criteria

### ✅ Deployment Success

**Minimum Requirements**:
- [x] Pre-deployment checks pass
- [x] Strategy runs for full duration (1 hour)
- [x] No critical errors or crashes
- [x] Risk limits enforced (no breaches)
- [x] Logs capture all events
- [x] Dashboard displays accurate metrics

### ✅ Functional Validation

**Required**:
- [x] Orders placed successfully
- [x] All orders are POST_ONLY (maker)
- [x] Trades executed and recorded
- [x] Position limits enforced
- [x] Daily loss limits enforced
- [x] Drawdown limits enforced

### ✅ Data Quality

**Required**:
- [x] CSV files created with proper headers
- [x] JSON exports complete
- [x] Trade logs accurate (timestamp, price, size, P&L)
- [x] Decision logs capture parameter usage
- [x] Error logs capture any issues

### ✅ Performance Comparison

**Static vs Dynamic**:

| Metric | Static | Dynamic | Winner |
|--------|--------|---------|--------|
| Total Trades | ? | ? | ? |
| Win Rate | ? | ? | ? |
| Net P&L | ? | ? | ? |
| Total Fees | ? | ? | ? |
| Sharpe Ratio | ? | ? | ? |
| Max Drawdown | ? | ? | ? |

**Expected Outcome**:
- Dynamic parameters should show similar or better performance
- Both should remain within risk limits
- Both should achieve positive spread capture

### ✅ Backtest Validation

**Compare to Backtest Results**:

| Metric | Backtest | Static Live | Dynamic Live |
|--------|----------|-------------|--------------|
| Return (%) | +0.20% | ? | ? |
| Win Rate (%) | 55-60% | ? | ? |
| Sharpe Ratio | 0.5-1.0 | ? | ? |
| Max Drawdown (%) | <5% | ? | ? |

**Acceptable Range**:
- Return: Within ±0.10% of backtest
- Win Rate: Within ±5% of backtest
- Sharpe: >0 (positive risk-adjusted return)
- Max Drawdown: <5% (within limit)

---

## Post-Deployment Analysis

### Step 1: Review Final Statistics

After 1-hour deployment completes, review console output:

```
[STATS] Final Statistics:
  Total Trades:  X
  Win Rate:      Y%
  Net P&L:       $Z
  Total Fees:    $F
```

### Step 2: Analyze CSV Data

```bash
cd "perpdex farm/logs/data/csv"

# Count trades:
wc -l avellaneda_static_testnet_20251024_trades.csv

# Calculate average P&L:
awk -F',' 'NR>1 {sum+=$12; count++} END {print "Avg P&L:", sum/count}' \
  avellaneda_static_testnet_20251024_trades.csv

# Check win rate:
awk -F',' 'NR>1 {if($12>0) wins++; total++} END {print "Win Rate:", wins/total*100"%"}' \
  avellaneda_static_testnet_20251024_trades.csv
```

### Step 3: Compare Static vs Dynamic

Create comparison report:

```bash
cd "perpdex farm"
python -c "
import pandas as pd
import glob

# Load both CSV files
static_trades = pd.read_csv(glob.glob('logs/data/csv/*static*trades.csv')[0])
dynamic_trades = pd.read_csv(glob.glob('logs/data/csv/*dynamic*trades.csv')[0])

print('=== STATIC vs DYNAMIC COMPARISON ===')
print(f'Static Trades: {len(static_trades)}')
print(f'Dynamic Trades: {len(dynamic_trades)}')
print(f'Static Win Rate: {(static_trades[\"realized_pnl\"] > 0).mean()*100:.1f}%')
print(f'Dynamic Win Rate: {(dynamic_trades[\"realized_pnl\"] > 0).mean()*100:.1f}%')
print(f'Static Net P&L: \${static_trades[\"realized_pnl\"].sum():.2f}')
print(f'Dynamic Net P&L: \${dynamic_trades[\"realized_pnl\"].sum():.2f}')
"
```

### Step 4: Decision Log Analysis

Analyze parameter usage in dynamic mode:

```bash
cd "perpdex farm"
python -c "
import pandas as pd
import glob
import json

# Load decision log
decisions = pd.read_csv(glob.glob('logs/data/csv/*dynamic*decisions.csv')[0])

# Extract dynamic parameters
spread_calcs = decisions[decisions['decision_type'] == 'spread_calculation']

print('=== DYNAMIC PARAMETER USAGE ===')
for idx, row in spread_calcs.iterrows():
    params = json.loads(row['parameters'])
    if 'dynamic_kappa' in params:
        print(f'{row[\"datetime_utc\"]}: kappa={params[\"dynamic_kappa\"]:.3f}')
"
```

### Step 5: Create Summary Report

Document deployment results in `docs/PHASE_7.6_RESULTS.md`:

```markdown
# Phase 7.6 - Testnet Deployment Results

**Date**: October 24, 2025
**Duration**: 1 hour
**Symbol**: BTC-USDT
**Environment**: Apex Pro Testnet

## Static Parameters

- Total Trades: X
- Win Rate: Y%
- Net P&L: $Z
- Total Fees: $F
- Sharpe Ratio: S
- Max Drawdown: D%

## Dynamic Parameters

- Total Trades: X
- Win Rate: Y%
- Net P&L: $Z
- Total Fees: $F
- Sharpe Ratio: S
- Max Drawdown: D%

## Comparison to Backtest

| Metric | Backtest | Static | Dynamic |
|--------|----------|--------|---------|
| Return | +0.20% | ? | ? |
| Win Rate | 55-60% | ? | ? |
| Sharpe | 0.5-1.0 | ? | ? |
| Drawdown | <5% | ? | ? |

## Observations

1. [Key observation 1]
2. [Key observation 2]
3. [Key observation 3]

## Conclusion

[✅ PASS / ❌ FAIL]

Reasons:
- [Reason 1]
- [Reason 2]

## Next Steps

- [ ] Review and address any issues
- [ ] Proceed to Phase 8 (Mainnet Scaling)
```

---

## Advanced Configuration

### Custom Risk Limits

```bash
# More conservative:
python apex/deploy_testnet.py \
  --mode static \
  --position-limit 0.0005 \
  --max-daily-loss 0.50 \
  --max-drawdown 3.0

# More aggressive (not recommended for testnet):
python apex/deploy_testnet.py \
  --mode static \
  --position-limit 0.002 \
  --max-daily-loss 2.0 \
  --max-drawdown 10.0
```

### Different Trading Pairs

```bash
# ETH-USDT instead of BTC-USDT:
python apex/deploy_testnet.py \
  --mode static \
  --symbol ETH-USDT \
  --position-limit 0.01
```

### Longer Duration

```bash
# 4-hour deployment:
python apex/deploy_testnet.py \
  --mode static \
  --duration 14400

# 24-hour deployment:
python apex/deploy_testnet.py \
  --mode static \
  --duration 86400
```

---

## Safety Reminders

**CRITICAL RULES**:

1. **Always Test First**: Run `--dry-run` before real deployment
2. **Conservative Limits**: Use small position sizes and tight risk limits
3. **Monitor Actively**: Watch dashboard for first 15 minutes
4. **Log Everything**: All logs saved automatically
5. **Testnet Only**: NEVER use mainnet credentials for testnet deployment

**Risk Management**:
- Default limits are VERY conservative ($1 daily loss, 0.001 BTC position)
- Limits enforced automatically (strategy shuts down if breached)
- No override mechanism (by design - safety first)

**Emergency Stop**:
- Press `Ctrl+C` to stop deployment gracefully
- Strategy will:
  1. Cancel all open orders
  2. Close positions (if configured)
  3. Flush logs to disk
  4. Export final data to JSON
  5. Print final statistics

---

## Contact & Support

**Issues**:
- Check troubleshooting section first
- Review logs in `logs/avellaneda_testnet_YYYYMMDD.log`
- Review error CSV in `logs/data/csv/*_errors.csv`

**Documentation**:
- Development methodology: `docs/DEVELOPMENT_METHODOLOGY.md`
- Product requirements: `docs/PRD_VOLUME_FARMING_BOT.md`
- Testing summary: `docs/PHASE_7.5_SUMMARY.md`

---

**Good luck with deployment!** 🚀

*Remember: This is testnet. Use it to learn and validate. Real money comes in Phase 8.*
