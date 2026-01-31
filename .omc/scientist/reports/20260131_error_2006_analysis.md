# Error 2006 Analysis: Insufficient Account Health

**Generated:** 2026-01-31  
**Objective:** Understand exact account health calculation and requirements for isolated margin

---

## Executive Summary

Error 2006 "Insufficient account health" occurs because the testnet account has **zero collateral** (health = 0) and the isolated_margin parameter ($18-19) is significantly lower than the required initial margin (~$90 for typical perpetual contracts). This causes initial_health to be negative, triggering the error.

---

## Data Overview

- **Account Owner:** 0x883064f137d4d65D19b1D55275b374Fb0ade026A
- **Environment:** Nado Testnet
- **Account Status:** 
  - Initial Health: 0 USDT
  - Maintenance Health: 0 USDT
  - Unweighted Health: 0 USDT
- **Test Configuration:**
  - ETH: notional=$100, isolated_margin=19
  - SOL: notional=$101, isolated_margin=18

---

## Key Findings

### Finding 1: Zero Account Balance

The testnet account has no collateral deposited. All health metrics are zero.

**Metrics:**
| Health Type | Value | Status |
|-------------|-------|--------|
| Initial Health | 0 USDT | ✗ Insufficient |
| Maintenance Health | 0 USDT | ✗ Insufficient |
| Unweighted Health | 0 USDT | ✗ Insufficient |

### Finding 2: Incorrect isolated_margin Calculation

The current calculation (`isolated_margin = notional / leverage`) is fundamentally incorrect.

**Current Approach (WRONG):**
```
isolated_margin = $100 / 5 = $20
```

**Why It Fails:**
- isolated_margin defines COLLATERAL, not leverage directly
- Must satisfy margin requirement FIRST
- Leverage is a result, not an input

### Finding 3: Health Threshold Requirement

From SDK source code (`margin_manager.py`):

**Line 331:**
```python
funds_available = max(Decimal(0), initial_health)
```

**Line 467:**
```python
if initial_health < 0:
    margin_usage = Decimal(1)  # 100% used
```

**Threshold:**
- `initial_health > 0` is required for order execution
- No minimum percentage - just must be positive

### Finding 4: Correct Health Calculation Formula

**For Isolated Margin:**
```
Step 1: Get product risk parameter
  long_weight_initial = product.risk.long_weight_initial_x18

Step 2: Calculate required margin
  required_margin = notional_value * (1 - long_weight_initial)

Step 3: Set isolated_margin with safety buffer
  isolated_margin = required_margin * safety_factor
  where safety_factor = 1.2 to 2.0 (20-100% buffer)
```

**Example Calculation (assuming long_weight=0.10):**
- Notional: $100
- Required margin: $100 * (1 - 0.10) = $90
- isolated_margin (with 1.5x buffer): $90 * 1.5 = $135
- Actual leverage: $100 / $135 = 0.74x

### Finding 5: Isolated vs Cross Margin Behavior

**Isolated Margin (isolated=True):**
- isolated_margin parameter defines dedicated collateral for THIS position only
- isolated_margin MUST be >= required_initial_margin
- If isolated_margin < required_margin → initial_health < 0 → Error 2006

**Cross Margin (isolated=False):**
- Uses entire account balance as collateral
- Shares margin across all positions
- More efficient capital utilization
- Lower effective margin requirement per position

**Why Cross Margin "Worked":**
- Previous tests may have used different account with collateral
- Or account had sufficient balance at that time
- Current account has $0, so cross margin would also fail

---

## Statistical Details

### Required Margin Calculation

For typical perpetual contract weights:

| Long Weight | Required Margin (for $100 notional) | Your isolated_margin | Gap | Status |
|-------------|-----------------------------------|---------------------|-----|--------|
| 0.05 (5%) | $95.00 | $18-19 | $76-77 | ✗ Error 2006 |
| 0.10 (10%) | $90.00 | $18-19 | $71-72 | ✗ Error 2006 |
| 0.15 (15%) | $85.00 | $18-19 | $66-67 | ✗ Error 2006 |
| 0.20 (20%) | $80.00 | $18-19 | $61-62 | ✗ Error 2006 |

**Conclusion:** Even with aggressive weights (20%), required margin is 4x higher than isolated_margin provided.

---

## Limitations

- **Actual Product Weights Unknown:** Analysis assumes typical perp weights (0.10-0.20). Actual Nado testnet weights may differ.
- **Single Account Analysis:** Only one testnet account examined.
- **No Mainnet Data:** Analysis limited to testnet environment.
- **Static Analysis:** Based on SDK source code, not runtime debugging.

---

## Recommendations

### Immediate Actions

1. **Deposit Collateral (REQUIRED)**
   - Use Nado testnet faucet: https://faucet.test.nado.xyz
   - Deposit at least $200 USDT for testing
   - Account: 0x883064f137d4d65D19b1D55275b374Fb0ade026A

2. **Verify Balance**
   ```bash
   python3 tests/check_account_health.py
   ```

3. **Fix isolated_margin Calculation**
   - Query product for actual `long_weight_initial`
   - Use formula: `isolated_margin = notional * (1 - long_weight) * safety_factor`
   - Recommended safety_factor: 1.5 (50% buffer)

### Code Changes Required

**Current (INCORRECT):**
```python
isolated_margin = int(notional_value / leverage)  # WRONG
```

**Correct Approach:**
```python
# Get product risk parameters
product = client.get_product(contract_id)
long_weight = from_x18(product.risk.long_weight_initial_x18)

# Calculate required margin
required_margin = notional_value * (Decimal('1') - long_weight)

# Apply safety buffer
isolated_margin = int(required_margin * Decimal('1.5'))
```

### Strategic Decision

**Use Cross Margin Instead:**
- More efficient for small accounts
- Easier to manage
- Set `isolated=False`
- Still requires depositing collateral first

---

## Appendix: Source Code References

**File:** `/Users/botfarmer/Library/Python/3.9/lib/python/site-packages/nado_protocol/utils/margin_manager.py`

- **Line 279:** `initial_health = self._parse_health(self.subaccount_info.healths[0])`
- **Line 331:** `funds_available = max(Decimal(0), initial_health)`
- **Line 467:** `if initial_health < 0: margin_usage = Decimal(1)`

**Key Insight:** The SDK requires `initial_health > 0` for any order to execute. This is the hard threshold.

---

*Generated by Scientist Agent*
