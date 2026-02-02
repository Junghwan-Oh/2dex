# Static TP Bug Report

**Date**: 2026-02-02
**Status**: Critical Bug Identified
**Branch**: feature-staticTP

---

## Bug Summary

**Static TP (Take Profit) 기능이 전혀 작동하지 않음**

```
WARNING: [STATIC TP] No entry data available
```

---

## Root Cause Analysis

### Problem Flow

```
1. BUILD Phase - Initial Orders
   ├─ ETH order filled → entry_prices["ETH"] saved (line 873)
   ├─ SOL order timeout → no fill
   └─ Emergency unwind triggered (line 943-946)

2. Emergency Unwind
   ├─ handle_emergency_unwind() called
   ├─ _force_close_position("ETH") → closes ETH position
   └─ _force_close_position("SOL") → SOL was already 0

3. Retry Loop
   ├─ Calculate remaining quantities
   ├─ SOL retry order placed
   ├─ SOL fills → entry_prices["SOL"] SHOULD be saved (line 2938)
   └─ But: entry_prices["ETH"] was from the CLOSED position!

4. UNWIND Phase - TP Check
   ├─ _monitor_static_individual_tp() called
   ├─ Checks entry_prices for both tickers
   └─ Result: "No entry data available"
```

### The Core Issue

**Entry data conflict between initial fills and retry fills:**

1. **Initial ETH fill** (line 873): `entry_prices["ETH"] = $2258.2`
2. **Emergency unwind**: Closes the ETH position that was just filled
3. **SOL retry fill** (line 2938): `entry_prices["SOL"] = $99.74`
4. **Problem**: The ETH entry_price is from a CLOSED position, not the actual current position

### Why TP Doesn't Work

The `_monitor_static_individual_tp()` function checks:
```python
entry_price = self.entry_prices.get(ticker)
if entry_price is None:
    self.logger.warning("[STATIC TP] No entry data available")
    return
```

After emergency unwind + retry:
- `entry_prices["ETH"]` = price from CLOSED position (invalid)
- `entry_prices["SOL"]` = price from retry fill (valid)
- But the positions may not match these prices anymore!

---

## Test Evidence

### Test Run 2026-02-02

```
INFO: [FILL] ETH order fully filled: 0.04428305730227614914533699407 @ $2258.2
ERROR: [FILL] SOL order failed: Limit order timeout after 30s
WARNING: [BUILD] Triggering emergency unwind - ETH filled=True, SOL filled=False
WARNING: [UNWIND] ETH filled but SOL failed - closing BOTH positions
INFO: [FORCE] ETH position confirmed closed (pos=0.0)
INFO: [FORCE] SOL position confirmed closed (pos=0.0)

INFO: [BUILD] Both positions established
INFO: [UNWIND] Checking static TP conditions...
INFO: [STATIC TP] Monitoring: TP=10.0bps, timeout=60s
WARNING: [STATIC TP] No entry data available
```

### Position Log (CSV)

```
NADO,2026-02-02T02:42:27.141866+00:00,SOL,0,-6000000000000000000,-6e+18,...
NADO,2026-02-02T02:42:54.253619+00:00,ETH,0,87000000000000000,8.7e+16,...
NADO,2026-02-02T02:44:31.050307+00:00,SOL,0,-7.000000000000000000,-7.0,...
NADO,2026-02-02T02:44:31.840580+00:00,ETH,0,0.131000000000000000,0.131,...
```

Shows position changes but entry data tracking is broken.

---

## Code References

### Entry Data Storage Locations

| Location | Lines | Description |
|----------|-------|-------------|
| Initial fill save | 868-880 | Saves entry_prices during initial fills |
| Retry fill save | 2933-2938 | Saves entry_prices during retry |
| TP check | ~2150-2200 | _monitor_static_individual_tp() checks entry_prices |
| Emergency unwind | 958-991 | Closes positions but doesn't clear entry data |

### The Bug

**Line 873-874** (Initial fill):
```python
if eth_fill_qty > 0:
    self.entry_prices["ETH"] = eth_fill_price  # Saved
    self.entry_quantities["ETH"] += eth_fill_qty
```

**Line 943-946** (Emergency unwind):
```python
if not eth_filled or not sol_filled:
    self.logger.warning(f"[BUILD] Triggering emergency unwind")
    await self.handle_emergency_unwind(eth_result, sol_result)
```

**Line 2933-2938** (Retry fill):
```python
if hasattr(result, 'price') and result.price:
    self.entry_quantities[ticker] += filled_size
    if result.price > 0:
        self.entry_prices[ticker] = result.price  # Saved during retry
```

**The Problem**: Emergency unwind closes positions AFTER entry data was saved from initial fill. The retry saves NEW entry data, but:
1. The initial fill's entry data is now invalid (position was closed)
2. The retry fill's entry data might be incomplete
3. TP check finds inconsistent/missing data

---

## Solution Options

### Option 1: Clear Entry Data on Emergency Unwind

When emergency_unwind closes positions, also clear entry data:

```python
async def handle_emergency_unwind(self, eth_result, sol_result):
    # Close positions
    await self._force_close_position("ETH")
    await self._force_close_position("SOL")

    # Clear entry data since positions are closed
    self.entry_prices = {"ETH": None, "SOL": None}
    self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
```

Then let retry fill save NEW entry data for the ACTUAL positions.

### Option 2: Track Entry Data with Position IDs

Associate entry data with specific position instances to avoid stale data:

```python
self.entry_data = {
    "ETH": {"price": None, "quantity": Decimal("0"), "position_id": None},
    "SOL": {"price": None, "quantity": Decimal("0"), "position_id": None}
}
```

### Option 3: Verify Entry Data Before TP

Add verification that entry data matches current positions:

```python
def _verify_entry_data(self):
    eth_pos = await self.eth_client.get_account_positions()
    if abs(eth_pos) > Decimal("0.001") and self.entry_prices["ETH"] is None:
        return False
    return True
```

---

## Recommended Fix

**Option 1** is simplest and most reliable:

1. Clear entry data in `handle_emergency_unwind()`
2. Let retry logic save fresh entry data
3. TP will then have valid entry data for actual positions

### Implementation

File: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
Location: `handle_emergency_unwind()` method (~line 958)

```python
async def handle_emergency_unwind(self, eth_result, sol_result):
    # ... existing code ...

    # ALWAYS close both positions
    await self._force_close_position("ETH")
    await self._force_close_position("SOL")

    # CRITICAL: Clear entry data since positions are closed
    # This ensures retry fills save fresh entry data
    self.entry_prices = {"ETH": None, "SOL": None}
    self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
    self.entry_timestamps = {"ETH": None, "SOL": None}
```

---

## Testing Checklist

After fix:
- [ ] Run 1-cycle test with intentional SOL timeout
- [ ] Verify TP triggers with correct entry data
- [ ] Verify no "No entry data available" warning
- [ ] Check positions close properly
- [ ] Verify PNL calculation uses correct entry prices

---

## Related Issues

- Position accumulation bug (FIXED)
- TP leverage calculation (FIXED)
- WebSocket position tracking (ADDED)
- Close side logic (FIXED)

---

## Priority

**CRITICAL** - TP feature completely non-functional when retry is needed.
