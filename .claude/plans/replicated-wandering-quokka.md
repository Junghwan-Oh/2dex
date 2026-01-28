# Plan: GRVT Order Error Logging Improvement

## Objective
Improve error logging in GRVT exchange client to expose actual API error messages instead of generic "[MARKET] Error placing order"

## Problem Analysis

### Current Behavior
```python
# grvt.py:411-412
if not order_result:
    raise Exception(f"[MARKET] Error placing order")  # Hides actual error
```

### Root Cause Chain
1. GRVT API returns error response (no `result` field)
2. `pysdk/grvt_ccxt.py:129` detects `response.get("result") is None`
3. SDK logs actual error but returns `{}`
4. Our code catches empty dict but throws generic exception

### Evidence
- ETH 0.03: 24% failure rate (marginal liquidity)
- ETH 1.0: 100% failure rate (insufficient liquidity)
- Current error message provides no diagnostic value

## Implementation Plan

### File to Modify
`perp-dex-tools-original/hedge/exchanges/grvt.py`

### Changes Required

#### 1. Capture SDK Error Response (line ~408-415)

**Before:**
```python
order_result = self.rest_client.create_order(
    symbol=contract_id, order_type="market", side=side, amount=quantity
)
if not order_result:
    raise Exception(f"[MARKET] Error placing order")
```

**After:**
```python
order_result = self.rest_client.create_order(
    symbol=contract_id, order_type="market", side=side, amount=quantity
)
if not order_result:
    # Get the actual error from SDK's last response
    # The SDK logs the error but we need to expose it in our exception
    self.logger.log(
        f"[MARKET] Order failed - SDK returned empty result. Check GRVT API logs for details.",
        "ERROR"
    )
    raise Exception(f"[MARKET] Error placing order - SDK returned empty result (likely liquidity insufficient for {quantity} {side} order)")
```

#### 2. Alternative: Direct SDK Error Access

If SDK provides access to last error:
```python
if not order_result:
    last_error = getattr(self.rest_client, '_last_error', 'Unknown error')
    raise Exception(f"[MARKET] Error placing order: {last_error}")
```

### Verification
1. Run test with ETH 1.0 (will fail)
2. Check logs for improved error message
3. Confirm error message indicates liquidity issue vs other errors
4. Test with ETH 0.01 to confirm normal operation

## Estimated Time
15 minutes