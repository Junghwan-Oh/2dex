# Lighter Market ID Lookup Fix

**Status**: COMPLETED
**File**: `f:/Dropbox/dexbot/perpdex/hedge/hedge_mode_bp.py`
**Function**: `get_lighter_market_config()` (lines 1055-1088)
**Date Fixed**: 2025-12-22

## Problem Statement

The `get_lighter_market_config()` function was searching for the bare ticker symbol ("ETH") in Lighter's order books, but Lighter API returns symbols in pair format ("ETH/USDC"). This caused:

- Incorrect market_id assignment: `market_id=0` (bare ETH) instead of `market_id=2048` (ETH/USDC)
- Trading operations using wrong market configuration
- Potential order placement failures or incorrect hedging behavior

## Root Cause Analysis

**Old Logic (Line 1073)**:
```python
if market["symbol"] == self.ticker:  # "ETH" == "ETH" -> WRONG (finds market_id=0)
```

When the bot is initialized with `ticker="ETH"`, this condition matches:
- Market symbol "ETH" (market_id=0) - Base ETH market
- But the correct market is "ETH/USDC" (market_id=2048) - ETH/USDC trading pair

## Solution Implemented

**New Logic (Lines 1072-1084)**:
```python
# Convert ticker to Lighter market symbol format (e.g., ETH -> ETH/USDC)
lighter_symbol = f"{self.ticker}/USDC"
self.logger.info(f"Looking for Lighter market: {lighter_symbol}")

for market in data["order_books"]:
    if market["symbol"] == lighter_symbol:  # "ETH/USDC" == "ETH/USDC" -> CORRECT
        market_id = market["market_id"]
        self.logger.info(f"Found Lighter market: {lighter_symbol} (market_id={market_id})")
        return (market_id,
                pow(10, market["supported_size_decimals"]),
                pow(10, market["supported_price_decimals"]))

raise Exception(f"Market {lighter_symbol} not found in Lighter order books")
```

## Changes Made

| Line(s) | Change | Purpose |
|---------|--------|---------|
| 1072 | Add comment explaining format conversion | Code clarity |
| 1073 | New: Create `lighter_symbol = f"{self.ticker}/USDC"` | Format conversion |
| 1074 | New: Log what symbol we're searching for | Debugging visibility |
| 1077 | Changed comparison from `self.ticker` to `lighter_symbol` | Correct symbol matching |
| 1078-1079 | New: Extract market_id, log success with ID | Debugging and verification |
| 1084 | Updated error message to show full symbol | Better error reporting |

## Impact

**Before Fix**:
- Searching for ticker: "ETH"
- Found market_id: 0 (wrong market)
- Order routing: Incorrect

**After Fix**:
- Searching for ticker: "ETH/USDC"
- Found market_id: 2048 (correct market)
- Order routing: Correct

## Testing Recommendations

1. **Unit Test**: Verify `get_lighter_market_config()` returns market_id=2048 for "ETH"
2. **Integration Test**: Confirm hedge orders use correct Lighter market configuration
3. **Logging Verification**: Check logs show:
   ```
   Looking for Lighter market: ETH/USDC
   Found Lighter market: ETH/USDC (market_id=2048)
   ```

## Files Modified

- `f:/Dropbox/dexbot/perpdex/hedge/hedge_mode_bp.py` (lines 1072-1084)

## Additional Notes

- This fix applies universally to any ticker (BTC -> BTC/USDC, SOL -> SOL/USDC, etc.)
- The `/USDC` suffix is hardcoded as per Lighter market convention
- Error handling improved to show full symbol in error messages
- Logging added for debugging market configuration lookup
