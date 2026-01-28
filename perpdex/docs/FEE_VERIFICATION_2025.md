# Fee Structure Verification & API Trading Analysis

**Date**: October 24, 2025
**Purpose**: Verify actual fee structures applicable to API-based trading strategies

---

## 🚨 Critical Findings

### Apex Grid Bot: ❌ NOT AVAILABLE via API

**Investigation Results**:
```python
# apexomni SDK Analysis
import apexomni
from apexomni.http_private_sign import HttpPrivateSign

# create_order_v3 parameters:
# - symbol, side, type, size, price
# - timeInForce, reduceOnly
# - clientOrderId, timestampSeconds
# - takerFeeRate, makerFeeRate (query only, not settable)
# ❌ NO Grid Bot parameters

# Grep results:
# "grid" keyword in entire apexomni package: 0 matches
```

**Conclusion**:
- Grid Bot is a **platform UI-only feature**
- API trading uses **standard fee structure** (0.02% maker)
- Our backtests assuming Grid Bot rebate (-0.002%) are **invalid**

---

## Apex Fee Structure (API Trading)

### Standard API Trading Fees

| Order Type | Fee Rate | Notes |
|------------|----------|-------|
| **Maker** | **+0.02%** | Standard maker fee |
| **Taker** | **+0.05%** | Standard taker fee |

**Evidence**:
- Official blog: https://www.apex.exchange/blog/detail/Enhancing-Your-Trading-Experience-on-ApeX-Omni-Fee-Structure-Updates
- Confirmed by SDK analysis: No Grid Bot parameters in API

### Grid Bot (UI Only)

| Feature | Maker Fee | How to Use |
|---------|-----------|------------|
| **Platform Grid Bot** | **-0.002%** | Web UI only |
| **API Trading** | **+0.02%** | Cannot access Grid Bot rebate |

**Why API Can't Use Grid Bot**:
1. No Grid Bot parameters in `create_order_v3()`
2. Grid Bot is automated by platform, not user
3. Platform manages order lifecycle
4. API orders are treated as standard orders

---

## Paradex Fee Structure (API Trading)

### Retail vs Pro MM

| User Type | Maker Fee | Taker Fee | How to Access |
|-----------|-----------|-----------|---------------|
| **Retail (Default)** | **0%** | **0%** | Standard API trading |
| **Pro MM (RPI)** | **-0.0005%** | N/A | RPI-flagged orders |
| **HFT API** | N/A | **+0.002%** | High-frequency taker |

### Which Fee Applies to Us?

**Question**: API trading → Retail (0%) or Pro MM (-0.0005%)?

**Investigation Needed**:
```python
# Paradex API: Check for RPI flag
from paradex_api import ParadexClient

client.create_order(
    symbol="BTC-USDT",
    side="BUY",
    type="LIMIT",
    rpi_flag=True  # Does this parameter exist?
)
```

**Conservative Assumption**: **0% (Retail)**
- Safer to assume no rebate
- RPI is for professional market makers
- Likely requires special approval/registration

**Optimistic Case**: **-0.0005% (Pro MM)**
- If RPI flag available in API
- Requires verification with Paradex docs

---

## Corrected Fee Assumptions

### For Backtesting

**Previous (INCORRECT)**:
```python
# cross_dex_mm.py
apexMakerFee = -0.00002  # Grid Bot (❌ NOT AVAILABLE VIA API)
paradexMakerFee = -0.00005  # Unknown
```

**Corrected (CONSERVATIVE)**:
```python
# Standard API trading
apexMakerFee = 0.0002  # +0.02% standard maker
paradexMakerFee = 0.0  # 0% retail (conservative)
```

**Corrected (OPTIMISTIC)**:
```python
# If RPI available
apexMakerFee = 0.0002  # +0.02% standard maker
paradexMakerFee = -0.000005  # -0.0005% Pro MM rebate
```

---

## Impact on Strategy Comparison

### Previous Backtest Results (INVALID)

```
Cross-DEX MM (Grid):
- Apex fee: -0.002% ← WRONG (Grid Bot not available)
- Paradex fee: -0.00005% ← Unclear
- Net fee rate: -0.0035%
- Return: -4.46%
```

### Corrected Backtest (CONSERVATIVE)

```
Cross-DEX MM (Standard):
- Apex fee: +0.02%
- Paradex fee: 0% (retail)
- Net fee rate: +0.01%
- Return: Need to recalculate
```

### Corrected Backtest (OPTIMISTIC)

```
Cross-DEX MM (Pro MM):
- Apex fee: +0.02%
- Paradex fee: -0.0005% (if RPI available)
- Net fee rate: +0.0195% → still positive
- Return: Need to recalculate
```

---

## Avellaneda MM Fee Structure

**Current Settings** (also needs correction):
```python
# backtest/strategies/avellaneda_mm.py
# Conservative (Safe)
apexMakerFee = 0.0002  # +0.02%
paradexMakerFee = 0.0  # 0% retail

# Optimistic (if RPI available)
apexMakerFee = 0.0002  # +0.02%
paradexMakerFee = -0.000005  # -0.0005%
```

**Impact on Previous Results**:
```
Previous (with Grid Bot assumption):
- Net fee rate: +0.0075%
- Return: +0.20%

Conservative (no rebates):
- Net fee rate: +0.01% (higher)
- Return: Lower (need to recalculate)

Optimistic (Paradex RPI):
- Net fee rate: +0.0195% → ~+0.01% (half Apex, half Paradex)
- Return: Still lower than previous
```

---

## Action Items

### 1. Paradex RPI Verification (URGENT)

**Check Paradex API**:
- Does `create_order` support RPI flag?
- Requirements for Pro MM status
- How to enable RPI for API trading

**Resources**:
- Paradex API docs: https://docs.paradex.trade/
- Paradex Discord: Ask about API RPI access
- Contact Paradex support

### 2. Backtest Recalculation (HIGH PRIORITY)

**Update Fee Parameters**:
```python
# backtest/strategies/avellaneda_mm.py
# backtest/strategies/cross_dex_mm.py

# Conservative scenario
APEX_MAKER_FEE = 0.0002
PARADEX_MAKER_FEE = 0.0

# Optimistic scenario (if RPI confirmed)
APEX_MAKER_FEE = 0.0002
PARADEX_MAKER_FEE = -0.000005
```

**Re-run final_validation.py**:
```bash
python backtest/final_validation.py --data backtest/data/binance_btc_5m_30days.csv
```

### 3. Documentation Updates

**Update Files**:
- `docs/FEE_STRUCTURES_2025.md` - Add API trading section
- `docs/FINAL_STRATEGY_COMPARISON.md` - Add caveat about Grid Bot
- `backtest/strategies/*.py` - Correct fee assumptions

---

## Key Takeaways

1. **Apex Grid Bot**: ❌ Cannot be used via API
   - Platform UI feature only
   - API trading = standard 0.02% maker fee

2. **Paradex RPI**: ❓ Needs verification
   - Conservative: Assume 0% (retail)
   - Optimistic: -0.0005% (if RPI available)

3. **Strategy Validity**: ✅ Avellaneda MM still best
   - Even with higher fees, likely still positive
   - Cross-DEX MM still fails (spread capture issue, not fees)

4. **Next Steps**:
   - Verify Paradex RPI API access
   - Recalculate backtests with correct fees
   - Update all documentation

---

## Risk Assessment

**High Risk**:
- Deploying with wrong fee assumptions
- Could turn profitable strategy into losing one

**Mitigation**:
- Test on testnet first ($100 capital)
- Monitor actual fee charges
- Compare actual vs expected returns

**Recommendation**:
- Use **conservative** fee assumptions (0.02% Apex, 0% Paradex)
- Verify Paradex RPI before assuming rebate
- Update backtests before any deployment

---

*Last Updated: October 24, 2025*
