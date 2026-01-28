# Lighter WebSocket Comprehensive Logging Implementation

## Overview

Added comprehensive logging to the Lighter WebSocket handler (`handle_lighter_ws` function in `hedge_mode_bp.py`) to capture ALL incoming WebSocket messages with detailed breakdowns of their structure and content.

## File Modified

**File**: `f:/Dropbox/dexbot/perpdex/hedge/hedge_mode_bp.py`

**Function**: `handle_lighter_ws` (starting at line 588)

**Changes**: Lines 637-672 (new logging block) + Lines 741-750 (enhanced account_orders handling)

## Changes Made

### 1. Universal Message Type Logging (Lines 637-672)

Added logging immediately after message reception and JSON parsing. Now captures:

**Every message type** with debug log:
```python
msg_type = data.get("type", "UNKNOWN_TYPE")
self.logger.debug(f"📨 [LIGHTER WS] Received message type: {msg_type}")
```

### 2. Message Type-Specific Logging

#### `subscribed/order_book` (Line 642-643)
- Logs when subscription is confirmed

#### `subscribed/account_orders` (Line 644-645)
- Logs when account orders subscription is confirmed
- Useful to verify authentication succeeded

#### `update/order_book` (Lines 646-651)
- Logs offset position
- Logs number of bids and asks in update
- Helps track order book state changes

#### `update/account_orders` (Lines 652-663)
- Logs which markets have orders
- For each market: logs total order count
- **For each order**: logs:
  - Order ID
  - Status (filled, pending, cancelled, etc.)
  - Side (buy/sell)
  - Size
  - Price
- **This is critical** - now we'll see ALL order updates

#### `ping` (Lines 664-665)
- Logs ping reception before sending pong response

#### **Unexpected message types** (Lines 666-672)
- Logs any message types NOT in the above list
- Shows full payload (truncated to 500 chars)
- Uses WARNING level to make it visible

### 3. Enhanced Account Orders Handling (Lines 741-750)

When processing account orders, now logs:
- Number of orders being processed for the market
- **For each order**:
  - Order ID and current status
  - Debug log: shows we're processing each order
  - If status is "filled": INFO log confirming fill
  - If status is NOT "filled": debug log explaining why skipped

## What This Will Reveal

### Key Questions This Logging Will Answer:

1. **Is the WebSocket connection working?**
   - Look for `subscribed/order_book` and `subscribed/account_orders` messages
   - If missing: connection/subscription failed

2. **What message types is Lighter actually sending?**
   - If you see unexpected message types: captures them with full payload
   - Helps identify if API protocol differs from documentation

3. **Are order fills coming through?**
   - Each `update/account_orders` message will show every order with its status
   - Every filled order will show an `✅ [LIGHTER WS] Order FILLED` log

4. **Is the authentication failing?**
   - If `subscribed/account_orders` never appears: auth token issue
   - Check WARNING logs for auth errors

5. **What's in the order updates?**
   - See exact order IDs, statuses, sides, sizes, prices
   - Can trace orders from creation through fill

## Log Output Examples

### Successful Subscription
```
📨 [LIGHTER WS] Received message type: subscribed/order_book
📨 [LIGHTER WS] Subscription confirmation: subscribed to order book
📨 [LIGHTER WS] Received message type: subscribed/account_orders
📨 [LIGHTER WS] Subscription confirmation: subscribed to account orders
```

### Order Book Update
```
📨 [LIGHTER WS] Received message type: update/order_book
📨 [LIGHTER WS] Order book update - offset: 12345, bids: 50, asks: 48
```

### Account Orders Update (NEW - THIS IS THE KEY LOGGING)
```
📨 [LIGHTER WS] Received message type: update/account_orders
📨 [LIGHTER WS] Account orders update received - Markets: ['0']
📨 [LIGHTER WS] Market 0: 1 orders
📨 [LIGHTER WS]   Order 0: id=12345, status=filled, side=buy, size=0.5, price=19.50
✅ [LIGHTER WS] Order FILLED: id=12345
```

### Unexpected Message Type
```
📨 [LIGHTER WS] Received message type: unknown_type_xyz
⚠️ [LIGHTER WS] UNEXPECTED MESSAGE TYPE: unknown_type_xyz
⚠️ [LIGHTER WS] Payload: {"type": "unknown_type_xyz", "data": {...}}
```

## Debug Log vs Info Log

- **DEBUG logs** (📨): Low frequency messages or expected details
  - Enabled when running with DEBUG log level
  - Use for detailed analysis

- **INFO logs** (✅): Important state changes
  - Subscription confirmations
  - Order fills
  - Account orders receipts
  - Always visible at INFO level

- **WARNING logs** (⚠️): Unexpected or problematic
  - Unexpected message types
  - Authentication failures
  - Connection issues

## How to Use This for Debugging

### 1. Check if WebSocket is Connecting
```bash
grep "subscribed/order_book\|subscribed/account_orders" hedge_mode_bp.log
```

### 2. Find All Account Order Updates
```bash
grep "update/account_orders\|Order FILLED" hedge_mode_bp.log
```

### 3. See Unexpected Message Types
```bash
grep "UNEXPECTED MESSAGE TYPE" hedge_mode_bp.log
```

### 4. Track Specific Order
```bash
grep "id=12345" hedge_mode_bp.log
```

### 5. Full Timeline for Testing
```bash
grep "LIGHTER WS" hedge_mode_bp.log | head -100
```

## Syntax Validation

✅ Python syntax check passed (verified with `py_compile`)

## Next Steps After Testing

1. **Run a test trade** and monitor logs
2. **Check for `update/account_orders` messages** - if none appear:
   - Verify authentication token is being sent correctly
   - Check Lighter API documentation for correct subscription format
   - May need to use different message type for order updates

3. **If unexpected message types appear**:
   - Document them
   - Research Lighter API documentation
   - Update message handler accordingly

4. **If fills are logged**:
   - Verify `handle_lighter_order_result` is processing them correctly
   - Check if trades are being executed in the hedge strategy

## Related Code

- Message handling logic: Lines 674-753
- Authentication setup: Lines 607-622
- Order result handler: `handle_lighter_order_result()` function

## Files Changed

- `f:/Dropbox/dexbot/perpdex/hedge/hedge_mode_bp.py` (Lines 637-672, 741-750)

## Date Added

2025-12-22
