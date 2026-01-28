# DEX Integration & Mainnet Testing Checklist

**📍 Location**: `common/DEX_INTEGRATION_CHECKLIST.md`
**🎯 Purpose**: **DEX 공통 통합 테스트 템플릿** (Apex Pro, Paradex, 20+ DEX)
**📅 Created**: 2025-10-24
**📖 Based On**: Apex Pro mainnet pilot testing experience (15시간 실전 테스트)

---

## 🔥 이 문서를 사용하는 시점

**새로운 DEX 통합을 시작할 때**:
1. ✅ SDK 설치 전에 이 체크리스트 읽기
2. ✅ 각 섹션을 순서대로 따라가며 테스트
3. ✅ 발견한 문제를 Common Pitfalls에 추가
4. ✅ DEX별 차이점을 Exchange Comparison Matrix에 기록

**Apex Pro 경험으로 15시간 → 다음 DEX는 5-7시간으로 단축 가능**

---

## Table of Contents

1. [Pre-Integration Checklist](#pre-integration-checklist)
2. [SDK Installation & Verification](#sdk-installation--verification)
3. [Credentials Setup](#credentials-setup)
4. [Public API Testing](#public-api-testing)
5. [Private API Testing](#private-api-testing)
6. [Order Placement Testing](#order-placement-testing)
7. [Risk Management Testing](#risk-management-testing)
8. [OCO & Position Management](#oco--position-management)
9. [P&L Calculation Verification](#pnl-calculation-verification)
10. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
11. [Production Readiness Checklist](#production-readiness-checklist)

---

## Pre-Integration Checklist

### Documentation Research
- [ ] Read official API documentation thoroughly
- [ ] Identify authentication method (API Key, Private Key, OAuth)
- [ ] Check supported order types (MARKET, LIMIT, STOP, STOP_LIMIT)
- [ ] Verify maker/taker fee structure
- [ ] Check if OCO (One Cancels Other) is natively supported
- [ ] Identify minimum order sizes and tick sizes
- [ ] Check leverage options (Cross vs Isolated margin)

### SDK Selection
- [ ] Official SDK available? (Python, JavaScript, etc.)
- [ ] SDK version and last update date
- [ ] Community support and GitHub issues
- [ ] Known bugs or workarounds

### Network Selection
- [ ] Testnet available?
- [ ] Testnet vs Mainnet differences
- [ ] How to get testnet funds

---

## SDK Installation & Verification

### Installation
```bash
# Example: Apex Pro
pip install apexomni

# Verify installation
python -c "from apexomni import HttpPublic, HttpPrivateSign; print('SDK installed successfully')"
```

### Version Check
```bash
pip show apexomni  # Check version and dependencies
```

### SDK Capabilities Test
```python
# Test what methods are available
from apexomni.http_private_sign import HttpPrivateSign
import inspect

methods = [m for m in dir(HttpPrivateSign) if not m.startswith('_')]
print("Available methods:", methods)
```

**Checklist**:
- [ ] SDK installed without errors
- [ ] Dependencies compatible with Python version
- [ ] Can import all required modules
- [ ] Method signatures match documentation

---

## Credentials Setup

### Environment Variables
Create `.env` file in project root:

```bash
# Apex Pro Example
APEX_API_KEY=your_api_key_here
APEX_API_SECRET=your_api_secret_here
APEX_API_PASSPHRASE=your_passphrase_here
APEX_ZK_SEEDS=your_omni_seeds_here
APEX_ZK_L2KEY=your_l2key_here

# Paradex Example (Ethereum Private Key)
PARADEX_PRIVATE_KEY=0x...your_eth_private_key
```

### Credential Validation
```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = ['APEX_API_KEY', 'APEX_API_SECRET', 'APEX_API_PASSPHRASE']
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"[ERROR] Missing credentials: {missing}")
else:
    print("[OK] All credentials loaded")
```

**Checklist**:
- [ ] `.env` file created and NOT committed to git
- [ ] All required credentials present
- [ ] Credentials verified on exchange web UI
- [ ] API permissions set correctly (read + trade)

---

## Public API Testing

### Test 1: Market Data (No Auth Required)
```python
from apexomni.http_public import HttpPublic
from apexomni.constants import APEX_OMNI_HTTP_MAIN

client = HttpPublic(APEX_OMNI_HTTP_MAIN)

# Test ticker
ticker = client.ticker_v3(symbol='BTC-USDT')
print(f"[TICKER] Result: {ticker}")

# Test order book
depth = client.depth_v3(symbol='BTC-USDT', limit=20)
print(f"[DEPTH] Result: {depth}")
```

**Expected Results**:
- Valid JSON response
- Current market price in reasonable range
- Bid/ask spreads present

**Checklist**:
- [ ] Ticker data retrieved successfully
- [ ] Order book depth working
- [ ] Prices within expected market range
- [ ] Response structure matches documentation

---

## Private API Testing

### Test 2: Account Information
```python
from apexomni.http_private_sign import HttpPrivateSign
from apexomni.constants import APEX_OMNI_HTTP_MAIN, NETWORKID_OMNI_MAIN_ARB
import os
from dotenv import load_dotenv

load_dotenv()

client = HttpPrivateSign(
    APEX_OMNI_HTTP_MAIN,
    network_id=NETWORKID_OMNI_MAIN_ARB,
    api_key_credentials={
        'key': os.getenv('APEX_API_KEY'),
        'secret': os.getenv('APEX_API_SECRET'),
        'passphrase': os.getenv('APEX_API_PASSPHRASE')
    },
    zk_seeds=os.getenv('APEX_ZK_SEEDS'),
    zk_l2Key=os.getenv('APEX_ZK_L2KEY')
)

account = client.get_account_v3()
print(f"[ACCOUNT] Data: {account}")
```

**Expected Results**:
- Account ID returned
- Balance information present
- Position data (if any positions open)

**Checklist**:
- [ ] Account data retrieved successfully
- [ ] Balance matches web UI
- [ ] Leverage settings visible
- [ ] No authentication errors

---

## Order Placement Testing

### Test 3: Market Order (Small Size)
```python
# ALWAYS test with MINIMUM size first
symbol = 'BTC-USDT'
size = 0.001  # Minimum size for BTC

# Get current mark price
ticker = public_client.ticker_v3(symbol=symbol)
mark_price = float(ticker['data']['markPrice'])

print(f"[TEST] Placing BUY market order")
print(f"  Symbol: {symbol}")
print(f"  Size: {size} BTC")
print(f"  Estimated cost: ${mark_price * size:.2f}")

# Place market order
order = private_client.create_order_v3(
    symbol=symbol,
    side='BUY',
    type='MARKET',
    size=str(size)
    # Note: Some exchanges require 'price' even for MARKET orders (SDK bug)
)

print(f"[RESULT] Order ID: {order['data']['id']}")
```

**Checklist**:
- [ ] Order placed successfully
- [ ] Order ID returned
- [ ] Fill confirmed (check via get_order or positions)
- [ ] Balance updated correctly

**Common SDK Bugs to Test**:
- [ ] MARKET orders requiring `price` parameter
- [ ] `postOnly` parameter not supported
- [ ] STOP_MARKET failing (use LIMIT + triggerPrice instead)

---

## Risk Management Testing

### Test 4: Leverage Verification
```python
account = client.get_account_v3()

# Check leverage settings
for position in account['data']['positions']:
    if position['symbol'] == 'BTC-USDT':
        margin_rate = float(position.get('customInitialMarginRate', 0))
        if margin_rate > 0:
            leverage = 1 / margin_rate
            print(f"[LEVERAGE] {position['symbol']}: {leverage:.1f}x")
            print(f"[MARGIN MODE] {'Cross' if position.get('marginMode') == 'CROSS' else 'Isolated'}")
```

**Checklist**:
- [ ] Leverage matches expected setting
- [ ] Margin mode verified (Cross vs Isolated)
- [ ] Understand margin calculation:
  - `Margin = Position Value ÷ Leverage`
  - Example: $111 position ÷ 7x = $15.86 margin

### Test 5: Take Profit / Stop Loss Orders
```python
# Entry price from filled market order
entry_price = 111159.10
tp_pct = 0.1  # 0.1% TP
sl_pct = 0.05  # 0.05% SL

# Calculate TP/SL prices
tp_price = entry_price * (1 + tp_pct / 100)
sl_price = entry_price * (1 - sl_pct / 100)

# Round to tick size
tick_size = 0.1
tp_price = round(tp_price / tick_size) * tick_size
sl_price = round(sl_price / tick_size) * tick_size

print(f"[TP/SL] Entry: ${entry_price:.2f}")
print(f"[TP/SL] TP: ${tp_price:.2f} (+{tp_pct}%)")
print(f"[TP/SL] SL: ${sl_price:.2f} (-{sl_pct}%)")

# Place Take Profit (LIMIT SELL)
tp_order = client.create_order_v3(
    symbol='BTC-USDT',
    side='SELL',
    type='LIMIT',
    size='0.001',
    price=str(tp_price)
)

# Place Stop Loss (LIMIT + triggerPrice)
sl_order = client.create_order_v3(
    symbol='BTC-USDT',
    side='SELL',
    type='LIMIT',
    size='0.001',
    price=str(sl_price),
    triggerPrice=str(sl_price),
    triggerPriceType='MARK_PRICE'
)

print(f"[TP] Order ID: {tp_order['data']['id']}")
print(f"[SL] Order ID: {sl_order['data']['id']}")
```

**Checklist**:
- [ ] TP order placed successfully
- [ ] SL order placed successfully
- [ ] Prices rounded to correct tick size
- [ ] Orders visible in open orders

**Leverage P&L Math**:
- TP 0.1% spot = +0.7% position P&L at 7x leverage
- SL 0.05% spot = -0.35% position P&L at 7x leverage
- Formula: `Position P&L % = Spot % × Leverage`

---

## OCO & Position Management

### Test 6: Native TP/SL Discovery (CRITICAL)

**🚨 ALWAYS CHECK FOR NATIVE TP/SL FIRST**

Before implementing manual OCO, **thoroughly research** if the DEX has built-in TP/SL:

- [ ] Check API documentation for `isOpenTpslOrder`, `tpTriggerPrice`, `slTriggerPrice` parameters
- [ ] Look for OCO-related order flags in SDK
- [ ] Test with single entry order + TP/SL parameters
- [ ] Verify one fill → other auto-cancels

**Apex Pro Native TP/SL (DISCOVERED AFTER 15 HOURS)**:
```python
order = client.create_order_v3(
    symbol='BTC-USDT',
    side='SELL',  # SHORT entry
    type='MARKET',  # or 'LIMIT'
    size='0.001',

    # ENABLE NATIVE TP/SL
    isOpenTpslOrder=True,

    # Take Profit
    isSetOpenTp=True,
    tpTriggerPrice='110496.3',
    tpPrice='110496.3',  # Same as trigger (no slippage)
    tpSide='BUY',  # Opposite of entry
    tpSize='0.001',

    # Stop Loss
    isSetOpenSl=True,
    slTriggerPrice='110520.0',
    slPrice='110520.0',  # Same as trigger
    slSide='BUY',
    slSize='0.001'
)
```

**SUCCESS**: One fills → Other auto-cancels (OCO built-in!)

**🚨 CRITICAL ISSUES WITH NATIVE TP/SL**:

1. **Entry Price Mismatch Problem**
   - TP/SL submitted WITH entry order (before fill known)
   - If entry fills at different price → TP/SL triggers wrong
   - **Order 769561569622229354**: Entry $110,559.60 but SL @ $110,520.00 → Instant trigger → -8.43% loss

   **Solution**: Use MARKET entry OR conservative LIMIT pricing + safety buffer

2. **Order Type: MARKET vs LIMIT TP/SL**
   - Add `tpOrderType='LIMIT'`, `slOrderType='LIMIT'` for better control
   - Default is MARKET (more slippage)

3. **Time-In-Force**
   - Default: IOC (Immediate-Or-Cancel)
   - Better: GTT (Good-Till-Time) for persistent orders
   - Add `tpTimeInForce='GTT'`, `slTimeInForce='GTT'`

**See**: `apex/NATIVE_TPSL_CRITICAL_ISSUES.md` for full details

### Test 6 (Legacy): Manual OCO Logic

**If Native TP/SL NOT available**:
- TP and SL are **separate orders**, NOT sub-orders
- When TP fills, SL remains **ACTIVE** and can trigger wrong position
- **Solution**: Manual OCO monitoring + cancel

**Manual OCO Implementation**:
```python
def monitor_oco(tp_order_id, sl_order_id):
    while True:
        orders = client.get_open_orders()

        tp_exists = any(o['id'] == tp_order_id for o in orders)
        sl_exists = any(o['id'] == sl_order_id for o in orders)

        # OCO Logic
        if not tp_exists and sl_exists:
            # TP filled, cancel SL
            client.delete_order_v3(id=sl_order_id, symbol='BTC-USDT')
            print("[OCO] TP filled, SL cancelled")
            break
        elif not sl_exists and tp_exists:
            # SL filled, cancel TP
            client.delete_order_v3(id=tp_order_id, symbol='BTC-USDT')
            print("[OCO] SL filled, TP cancelled")
            break
        elif not tp_exists and not sl_exists:
            print("[OCO] Both orders cleared")
            break

        time.sleep(10)  # Poll every 10 seconds
```

**Checklist**:
- [ ] OCO logic tested with small position
- [ ] TP fill triggers SL cancel
- [ ] SL fill triggers TP cancel
- [ ] No residual orders left active
- [ ] Position closed correctly

**Known Issue**:
- **Apex Cancel API Bug**: `delete_order_v3()` returns success but order remains ACTIVE
- **Error**: `code: 20016, msg: 'rpc error: code = Unauthenticated desc = Failed to check signature!'`
- **Workaround**: Manual cancellation via web UI until WebSocket implementation

---

## P&L Calculation Verification

### Apex Pro P&L Formula

**Official Formula** (verified from Apex UI):

```
Long Position:
  Realized P&L = Close Value - Open Value - Trading Fees + Funding Fees

Short Position:
  Realized P&L = Open Value - Close Value - Trading Fees + Funding Fees

P&L (%) = P&L / (Entry Price × Qty × IMR) × 100%
```

Where:
- `IMR` = Initial Margin Rate = `1 / Leverage`
- Close Value = Exit price × Quantity
- Open Value = Entry price × Quantity
- Trading Fees = (Entry fee + Exit fee)

**Example Calculation**:
```
Entry: 111159.10 × 0.001 = 111.159
Exit: 111159.10 × 0.001 = 111.159 (same price)
Trading Fees: 0.105730 (0.02% maker + 0.05% taker)

Realized P&L = 111.159 - 111.159 - 0.105730 = -0.105730 USDT
```

**Fee Breakdown**:
- Maker fee: 0.02% (LIMIT orders)
- Taker fee: 0.05% (MARKET orders)
- Round-trip cost: ~0.07% (if mix of maker/taker)

**Checklist**:
- [ ] P&L calculation matches exchange UI
- [ ] Fees correctly deducted
- [ ] Funding fees accounted for (if any)
- [ ] P&L % formula verified

**Common Issue**:
Small TP/SL ranges can result in net loss due to fees:
- TP 0.02% - Fees 0.07% = **Net loss**
- Recommendation: TP ≥ 0.1%, SL ≥ 0.05% (for 7x leverage)

---

## Common Pitfalls & Solutions

### 1. SDK Method Parameter Bugs
**Problem**: SDK documentation doesn't match actual API requirements

**Examples from Apex Pro**:
- MARKET orders require `price` parameter (shouldn't be needed)
- `postOnly` parameter causes errors (not supported)
- STOP_MARKET type fails → Use `LIMIT` + `triggerPrice`

**Solution**:
- Always test methods with minimal parameters first
- Add parameters incrementally
- Check SDK source code for actual implementation
- Read GitHub issues for known bugs

### 2. Price Rounding Issues
**Problem**: Order rejected due to invalid price precision

**Solution**:
```python
def round_to_tick(price: float, tick_size: float) -> float:
    """Round price to exchange tick size"""
    return round(price / tick_size) * tick_size

# Example
tp_price = round_to_tick(111270.34, 0.1)  # → 111270.3
```

### 3. Minimum Order Size
**Problem**: Order rejected for being too small

**Solution**:
- Check exchange minimum size requirements
- Always test with MINIMUM size first
- Account for position sizing vs account size

### 4. Leverage & Margin Confusion
**Problem**: Unclear how leverage affects P&L and margin

**Key Concepts**:
```
Leverage = 1 / Initial Margin Rate (IMR)

Example: IMR = 0.14285
Leverage = 1 / 0.14285 = 7x

Margin Required = Position Value / Leverage
Margin Required = $111 / 7 = $15.86

Position P&L % = Spot Price Change % × Leverage
Spot +0.1% → Position +0.7% (at 7x)
```

### 5. Cross vs Isolated Margin
**Cross Margin** (Apex Pro default):
- Uses entire account balance as collateral
- Liquidation affects all positions
- Cannot set per-position margin

**Isolated Margin**:
- Only position margin at risk
- Each position independent
- **Not available on Apex Pro**

### 6. Cancel API Failures
**Problem**: `delete_order_v3()` returns success but order not cancelled

**Symptoms**:
- Error code: 20016
- Message: "Failed to check signature"
- Order remains ACTIVE

**Root Causes**:
- Incorrect signature generation
- Missing required parameters
- SDK bug in authentication

**Workarounds**:
1. **Manual Cancellation**: Use web UI
2. **Force Retry**: Retry cancel every 10 seconds
3. **WebSocket Migration**: Real-time order management (recommended)

### 7. OCO Not Natively Supported
**Problem**: No native One-Cancels-Other order type

**Solution**: Implement manual OCO monitoring
- Poll open orders every 10 seconds
- When one order fills, immediately cancel the other
- Include retry logic for failed cancellations

### 8. REST API Polling Limitations
**Structural Issues**:
- 10-second polling interval too slow for real-time trading
- Cannot detect manual cancellations in real-time
- Cannot distinguish between fill and cancel

**Solution**: Migrate to WebSocket for:
- Real-time order updates (50-100ms latency)
- Fill notifications
- Reduced slippage
- True OCO implementation

---

## Production Readiness Checklist

### Code Quality
- [ ] Error handling for all API calls
- [ ] Retry logic for transient failures
- [ ] Logging for all operations
- [ ] Input validation (price, size, leverage)
- [ ] Rate limiting respected

### Risk Management
- [ ] Position size limits enforced
- [ ] Maximum daily loss limit
- [ ] Maximum drawdown protection
- [ ] Emergency shutdown mechanism
- [ ] Manual override capability

### Monitoring
- [ ] Real-time position monitoring
- [ ] P&L tracking
- [ ] Fee tracking
- [ ] Fill rate metrics
- [ ] Error rate monitoring
- [ ] Alert system (Telegram, email, etc.)

### Testing
- [ ] Testnet validation complete
- [ ] All order types tested
- [ ] OCO logic verified
- [ ] Edge cases handled
- [ ] Stress testing done

### Documentation
- [ ] API credentials documented
- [ ] Configuration parameters explained
- [ ] Common errors documented
- [ ] Runbook for production issues
- [ ] Recovery procedures defined

### Deployment
- [ ] Start with minimum position sizes
- [ ] Monitor for 24 hours before scaling
- [ ] Gradual increase of position sizes
- [ ] Daily performance review
- [ ] Weekly strategy optimization

---

## DEX-Specific Adaptations

### Template for New DEX Integration

When integrating a new DEX, adapt this checklist:

1. **Replace SDK**: Change `apexomni` to target DEX SDK
2. **Update Credentials**: Modify `.env` template for DEX auth method
3. **Adjust Parameters**: Update symbol format, order types, etc.
4. **Test Fee Structure**: Verify maker/taker fees
5. **Check OCO Support**: Native or manual implementation
6. **Validate P&L Formula**: May differ per exchange

### Exchange Comparison Matrix

| Feature | Apex Pro | Paradex | [DEX 3] | [DEX 4] |
|---------|----------|---------|---------|---------|
| **Auth Method** | API Key + Omni Key | Ethereum Private Key | TBD | TBD |
| **Maker Fee** | 0.02% | 0% (retail) | TBD | TBD |
| **Taker Fee** | 0.05% | 0.025% | TBD | TBD |
| **Native OCO** | ❌ | TBD | TBD | TBD |
| **Margin Types** | Cross only | TBD | TBD | TBD |
| **WebSocket** | ✅ (needs impl) | TBD | TBD | TBD |
| **SDK Quality** | Moderate (bugs) | TBD | TBD | TBD |

---

## Lessons Learned from Apex Pro Integration

### What Went Well
1. ✅ Public API worked immediately
2. ✅ Order placement successful
3. ✅ Mark price tracking accurate
4. ✅ System stability (no crashes)

### What Failed
1. ❌ Dynamic mode OrderBookAnalyzer not working
2. ❌ Cancel API authentication failing
3. ❌ OCO not natively supported
4. ❌ REST polling too slow for HFT
5. ❌ Initial TP/SL too tight (fees > profit)

### Time Investment
- **SDK setup**: 1 hour
- **Basic testing**: 2 hours
- **Order placement debugging**: 3 hours
- **TP/SL + leverage optimization**: 2 hours
- **OCO implementation**: 4 hours
- **Cancel API troubleshooting**: 3 hours
- **Total**: ~15 hours

### Recommendations for Future DEX Integrations
1. **Start with testnet** if available
2. **Test public API first** (no auth needed)
3. **Minimum order sizes** for all tests
4. **Check SDK GitHub issues** before implementation
5. **Document all workarounds** immediately
6. **Budget 2-3 days** for full integration
7. **Plan WebSocket migration** from the start

---

## Next Steps After Testing

### Immediate Actions
1. [ ] Fix Critical Bugs
   - Cancel API authentication
   - Dynamic mode OrderBookAnalyzer
2. [ ] Implement WebSocket
   - Real-time order updates
   - True OCO support
   - Reduced latency
3. [ ] Add Telegram Alerts
   - Order fills
   - Position updates
   - Error notifications

### Optimization
1. [ ] Measure fill rate over 1 hour
2. [ ] Optimize TP/SL ranges
3. [ ] Test higher leverage settings
4. [ ] Compare mainnet vs testnet liquidity

### Production Preparation
1. [ ] Set up monitoring dashboards
2. [ ] Define kill switches
3. [ ] Create incident response plan
4. [ ] Prepare rollback procedures

---

## Appendix: Quick Reference

### Apex Pro API Endpoints
- **Mainnet**: `https://pro.apex.exchange`
- **Testnet**: `https://pro.apex-test.cloud`

### Common Commands
```bash
# Check open orders
python -c "from apex_client import ApexClient; client = ApexClient('mainnet'); print(client.get_open_orders())"

# Get account balance
python -c "from apex_client import ApexClient; client = ApexClient('mainnet'); print(client.get_account())"

# Cancel all orders
python -c "from apex_client import ApexClient; client = ApexClient('mainnet'); client.cancel_all_orders()"
```

### Emergency Contacts
- Apex Pro Support: [support email]
- Telegram Community: [link]
- GitHub Issues: https://github.com/ApeX-Protocol/apexpro-openapi-python-sdk/issues

---

**Last Updated**: 2025-10-24
**Next Review**: After Paradex integration (Phase 8)
**Maintained By**: Strategy Team
