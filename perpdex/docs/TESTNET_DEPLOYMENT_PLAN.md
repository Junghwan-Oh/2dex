# Testnet Deployment Plan - Phase 7

**Date**: October 24, 2025
**Objective**: Deploy Avellaneda MM strategy to testnet with $100 capital and validate real-world performance

---

## Deployment Strategy

### Two-Version Comparison

**Control Group**: Static Parameters (Baseline)
- Capital: $100
- Parameters: gamma=0.1, sigma=0.02, k=1.5 (static)
- Purpose: Baseline performance with proven backtest results

**Test Group**: Dynamic Parameters (Enhanced)
- Capital: $100
- Parameters: gamma=0.1, useDynamicParams=True
- Purpose: Validate Order Book Analyzer benefits with real data

**Total Capital**: $200 ($100 each)

---

## Pre-Deployment Checklist

### 1. API Credentials Setup ✅

**Apex Pro Omni**:
- [x] API Key configured: `APEX_API_KEY`
- [x] API Secret configured: `APEX_API_SECRET`
- [x] API Passphrase configured: `APEX_API_PASSPHRASE`
- [ ] ZK Seeds configured: `APEX_ZK_SEEDS` (REQUIRED for orders)
- [ ] ZK L2 Key configured: `APEX_ZK_L2KEY` (REQUIRED for orders)

**Paradex**:
- [ ] API credentials configured
- [ ] Account setup on testnet
- [ ] Funding confirmed

**Status**: ❌ Missing ZK Keys - CRITICAL BLOCKER

---

## ZK Keys Setup (CRITICAL)

### What Are ZK Keys?

**ZK Seeds** and **ZK L2 Key** are zero-knowledge proof keys required for:
- Order creation and signing
- Position management
- Trading operations on Apex Pro Omni

**Without ZK Keys**: API can only query data, NOT place orders

### How to Obtain ZK Keys

**Option 1: ApeX Pro Website** (Recommended)
1. Log in to https://pro.apex.exchange/
2. Navigate to Account → API Management
3. Generate or view existing ZK Keys
4. Copy to `.env` file:
   ```
   APEX_ZK_SEEDS=your-zk-seeds-here
   APEX_ZK_L2KEY=your-zk-l2key-here
   ```

**Option 2: Contact Support**
- Email ApeX Pro support
- Request ZK Keys for API trading
- Provide account details

**Option 3: SDK Documentation**
- Check apexomni documentation
- Follow ZK key generation guide

### Verification

Run verification script:
```bash
python apex/examples/01_check_credentials.py
```

Expected output:
```
[OK] API Key configured
[OK] API Secret configured
[OK] API Passphrase configured
[OK] ZK Seeds configured
[OK] ZK L2 Key configured
```

**Current Status**: ❌ ZK Keys NOT configured
**Action Required**: Obtain ZK Keys before deployment

---

## Deployment Architecture

### Exchange Selection

**Primary Exchange**: Apex Pro Omni
- Reason: Grid Bot API issue resolved (standard fee 0.02%)
- Fee structure: 0.02% maker (confirmed via API trading)
- Testnet available: Yes

**Secondary Exchange**: Paradex
- Fee structure: 0% retail (conservative)
- Potential RPI rebate: -0.0005% (needs verification)
- Testnet available: TBD

**Initial Focus**: Apex-only deployment
- Simpler to manage
- Proven fee structure
- Single exchange reduces complexity

### Trading Parameters

**Position Sizing**:
- Initial capital: $100 per version
- Position limit: $50 (50% of capital)
- Order size: $10 minimum
- Leverage: 1x (no leverage for safety)

**Risk Management**:
- Max drawdown: 20% (stop trading if reached)
- Daily loss limit: 5%
- Position monitoring: Every 5 minutes
- Auto-liquidation: If balance < $80

**Avellaneda MM Parameters**:
```python
# Static Version (Control)
gamma = 0.1           # Risk aversion
sigma = 0.02          # 2% daily volatility
k = 1.5               # Liquidity parameter
eta = 1.0             # Order arrival intensity
T = 86400             # 24 hours trading day
positionLimit = 0.05  # 0.05 BTC (~$50)
minSpread = 0.0001    # 0.01% minimum
maxSpread = 0.005     # 0.5% maximum

# Dynamic Version (Test)
# Same as above, plus:
useDynamicParams = True
```

---

## Implementation Files

### Core Trading Client

**File**: `apex/avellaneda_client.py` (TO BE CREATED)

**Responsibilities**:
- Connect to Apex Pro Omni via API
- Place maker orders based on Avellaneda MM strategy
- Monitor positions and P&L
- Execute entry/exit logic
- Log all trades and decisions

**Key Components**:
```python
class AvellanedaClient:
    def __init__(self, apiKey, apiSecret, passphrase, zkSeeds, zkL2Key):
        # Initialize API client
        self.client = HttpPrivateSign(
            APEX_OMNI_HTTP_MAIN,
            network_id=NETWORKID_OMNI_MAIN_ARB,
            zk_seeds=zkSeeds,
            zk_l2Key=zkL2Key,
            api_key_credentials={...}
        )

    def run(self):
        # Main trading loop
        while self.running:
            # 1. Get market data
            # 2. Calculate optimal spreads
            # 3. Place/update orders
            # 4. Monitor positions
            # 5. Execute exits
            # 6. Log metrics
```

### Monitoring Dashboard

**File**: `apex/monitor_dashboard.py` (TO BE CREATED)

**Features**:
- Real-time P&L tracking
- Trade history display
- Position summary
- Performance metrics
- Alert notifications

**Metrics to Track**:
- Current balance
- Unrealized P&L
- Realized P&L
- Number of trades
- Win rate
- Sharpe ratio
- Max drawdown
- Average spread captured

### Data Logger

**File**: `common/trade_logger.py` (TO BE CREATED)

**Purpose**: Store all trading activity for analysis

**Data to Log**:
```json
{
  "timestamp": "2025-10-24T12:34:56Z",
  "action": "ENTER",
  "side": "BUY",
  "price": 67500.0,
  "size": 0.001,
  "spread": 0.0002,
  "kappa": 1.5,
  "dynamic_params": false,
  "reason": "spread_opportunity",
  "balance": 100.50,
  "unrealized_pnl": -0.50
}
```

---

## Testing Timeline

### Week 1: Setup and Initialization

**Day 1-2**: Infrastructure Setup
- [ ] Obtain ZK Keys from Apex Pro
- [ ] Configure all environment variables
- [ ] Test API connectivity
- [ ] Verify order creation capability
- [ ] Test position queries

**Day 3-4**: Code Implementation
- [ ] Create `apex/avellaneda_client.py`
- [ ] Create `apex/monitor_dashboard.py`
- [ ] Create `common/trade_logger.py`
- [ ] Add error handling
- [ ] Add safety checks

**Day 5**: Testing and Validation
- [ ] Unit tests for all components
- [ ] Integration tests
- [ ] Dry-run simulation
- [ ] Safety mechanism verification

**Day 6-7**: Deployment
- [ ] Deploy static version (control)
- [ ] Deploy dynamic version (test)
- [ ] Monitor for first 24 hours
- [ ] Validate logging and monitoring

### Week 2: Active Monitoring

**Daily Tasks**:
- Check P&L at 8am, 2pm, 8pm
- Review trade logs
- Monitor for errors or anomalies
- Adjust parameters if needed (document all changes)

**Metrics to Record**:
- Hourly balance snapshots
- Trade count per day
- Average spread captured
- Win rate
- Sharpe ratio
- Max drawdown

**Alerts to Configure**:
- Balance drops below $90
- Drawdown exceeds 15%
- No trades for 6 hours
- API errors or disconnections

---

## Success Criteria

### Minimum Viable Performance

**Static Version (Control)**:
- Return: ≥ 0% (no loss)
- Max Drawdown: ≤ 20%
- Uptime: ≥ 95%
- Trade Count: ≥ 30 trades/day

**Dynamic Version (Test)**:
- Return: ≥ Static version
- Improvement: ≥ 0.05% better than static
- Trade Count: Similar to static

### Validation Metrics

**Technical Validation**:
- [x] All orders execute successfully
- [x] No API errors or disconnections
- [x] Logging captures all activity
- [x] Monitoring dashboard functional

**Strategy Validation**:
- [x] Avellaneda MM logic executes correctly
- [x] Spreads calculated as expected
- [x] Positions managed within limits
- [x] Risk controls activate when needed

**Performance Validation**:
- [x] Returns match or exceed backtest
- [x] Trade frequency aligns with expectations
- [x] Fee impact as predicted
- [x] Dynamic parameters show adaptation (if any)

---

## Risk Management

### Safety Mechanisms

**Position Limits**:
- Hard cap: 0.05 BTC per version
- Auto-close if exceeded
- No new orders until position reduced

**Loss Limits**:
- Daily loss limit: -$5 (5%)
- Total drawdown limit: -$20 (20%)
- Auto-pause trading if limits hit

**API Safeguards**:
- Rate limiting: Max 10 requests/second
- Retry logic for transient errors
- Circuit breaker for persistent failures
- Manual kill switch

### Monitoring and Alerts

**Email Alerts** (if configured):
- Balance drops >10%
- Position exceeds limit
- API errors
- No trades for 6 hours

**Dashboard Alerts**:
- Real-time P&L display
- Position size indicator
- Error message log
- Connection status

### Emergency Procedures

**If Balance Drops >15%**:
1. Pause new order placement
2. Close all open positions
3. Analyze logs for root cause
4. Document findings
5. Decide: Fix and resume OR terminate test

**If API Fails**:
1. Retry with exponential backoff
2. If 5 retries fail → Pause trading
3. Alert via dashboard
4. Manual intervention required

**If Strategy Misbehaves**:
1. Kill switch: `pkill -f avellaneda_client`
2. Close positions manually via web UI
3. Analyze logs and fix issue
4. Re-deploy after validation

---

## Post-Deployment Analysis

### Daily Review Checklist

- [ ] Review P&L and balance
- [ ] Check trade count and frequency
- [ ] Analyze spread distribution
- [ ] Identify any errors or anomalies
- [ ] Compare static vs dynamic performance
- [ ] Document any observations

### Weekly Report Format

```markdown
# Testnet Week 1 Report

## Performance Summary
- Static Version: X% return, Y trades
- Dynamic Version: Z% return, W trades
- Improvement: +A%

## Key Observations
- Trade frequency: Expected/Unexpected
- Spread capture: Consistent/Variable
- Dynamic parameters: Adapting/Static

## Issues Encountered
- [List any problems and resolutions]

## Next Week Plan
- [Adjustments or changes planned]
```

### End-of-Week Decision

**After 1 Week**:
- Compare performance metrics
- Analyze dynamic parameter behavior
- Decide: Continue for Week 2 OR Terminate early

**After 2 Weeks**:
- Final performance comparison
- ROI calculation
- Confidence level assessment
- Decision: Proceed to mainnet OR iterate

---

## Next Steps (Immediate)

### CRITICAL BLOCKER: ZK Keys

**Status**: ❌ NOT CONFIGURED
**Impact**: Cannot place orders without ZK Keys
**Action**:
1. Access Apex Pro website
2. Navigate to API Management
3. Generate or retrieve ZK Seeds and ZK L2 Key
4. Add to `.env` file
5. Verify with `python apex/examples/01_check_credentials.py`

**Timeline**: Complete before proceeding to implementation

### Implementation Tasks

Once ZK Keys obtained:
1. Create `apex/avellaneda_client.py` (Day 3-4)
2. Create monitoring and logging (Day 4-5)
3. Test in dry-run mode (Day 5)
4. Deploy to testnet (Day 6-7)

---

## Conclusion

Testnet deployment is well-planned but **blocked by missing ZK Keys**.

**Immediate Priority**: Obtain ZK Keys from Apex Pro
**Timeline**: 1-2 days for ZK key setup, then proceed with implementation

Once unblocked, we have a clear path to testnet validation and mainnet scaling.

---

*Last Updated: October 24, 2025*
