# Lighter WebSocket Diagnostic Guide

## Purpose

Use this guide to interpret the new comprehensive logging added to `hedge_mode_bp.py` and diagnose why order fills are not being detected.

## Expected Message Sequence

### On Bot Startup

```
1. Connection established to wss://mainnet.zklighter.elliot.ai/stream
2. Send subscription request:
   {"type": "subscribe", "channel": "order_book/X"}

3. Receive confirmation:
   📨 [LIGHTER WS] Received message type: subscribed/order_book
   📨 [LIGHTER WS] Subscription confirmation: subscribed to order book

4. Send account orders subscription with auth:
   {"type": "subscribe", "channel": "account_orders/X/Y", "auth": "token..."}

5. Receive confirmation (IF AUTH SUCCESS):
   📨 [LIGHTER WS] Received message type: subscribed/account_orders
   📨 [LIGHTER WS] Subscription confirmation: subscribed to account orders

6. Start receiving order book updates periodically
```

### During Order Submission & Fill

```
1. Bot submits order (external to WebSocket handler)

2. Lighter sends order update via WebSocket:
   📨 [LIGHTER WS] Received message type: update/account_orders
   📨 [LIGHTER WS] Account orders update received - Markets: ['0']
   📨 [LIGHTER WS] Market 0: 1 orders
   📨 [LIGHTER WS]   Order 0: id=ABC123, status=pending, side=buy, size=0.5, price=19.50
   📨 [LIGHTER WS] Processing 1 orders for market 0
   📨 [LIGHTER WS] Processing order id=ABC123, status=pending
   📨 [LIGHTER WS] Skipping order id=ABC123 with status=pending (not filled)

3. Order gets filled by matching

4. Lighter sends fill update:
   📨 [LIGHTER WS] Received message type: update/account_orders
   📨 [LIGHTER WS] Account orders update received - Markets: ['0']
   📨 [LIGHTER WS] Market 0: 1 orders
   📨 [LIGHTER WS]   Order 0: id=ABC123, status=filled, side=buy, size=0.5, price=19.50
   📨 [LIGHTER WS] Processing 1 orders for market 0
   📨 [LIGHTER WS] Processing order id=ABC123, status=filled
   ✅ [LIGHTER WS] Order FILLED: id=ABC123
   [handle_lighter_order_result executes and processes fill]
```

## Diagnostic Scenarios

### Scenario 1: No WebSocket Connection

**Signs:**
- No messages starting with `📨 [LIGHTER WS]`
- Error in logs about connection failure
- Bot logs `⚠️ Failed to connect to Lighter websocket`

**Diagnosis:**
- Check network connectivity
- Verify WebSocket URL is correct: `wss://mainnet.zklighter.elliot.ai/stream`
- Check if Lighter API is online
- Look for DNS resolution issues

**Action:**
- Test URL with: `curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" https://mainnet.zklighter.elliot.ai/stream`
- Check firewall/proxy issues
- Verify bot can reach mainnet.zklighter.elliot.ai

---

### Scenario 2: Connection OK, But Order Book Subscription Fails

**Signs:**
- No `subscribed/order_book` message appears
- Bot logs initial order book being loaded but then nothing
- No `📨 [LIGHTER WS]` logs at all after connection

**Diagnosis:**
- Subscription request not being sent
- WebSocket closed immediately after connection
- Wrong market index

**Action:**
- Check `self.lighter_market_index` value
- Verify subscription message format
- Check WebSocket connection doesn't close immediately
- Review Lighter API documentation for correct channel format

---

### Scenario 3: Connection OK, Order Book Works, But NO Account Orders Updates

**Signs:**
- See `subscribed/order_book` message
- See periodic `order_book update` messages
- **NEVER** see `subscribed/account_orders` message
- **NEVER** see `update/account_orders` message

**Diagnosis:**
- Account orders subscription failing (most likely)
- Authentication token not working
- Auth token format incorrect
- Account index wrong

**Action:**
```bash
# Check logs for auth errors:
grep "Failed to create auth token\|Error creating auth token" hedge_mode_bp.log

# Check if subscription message is being sent:
grep "Subscribed to account orders with auth token" hedge_mode_bp.log

# Verify account index is correct:
grep "account_index\|self.account_index" hedge_mode_bp.log
```

**Root Cause Analysis:**
- Check if Lighter API requires different subscription format
- Verify `create_auth_token_with_expiry()` is working
- Check if auth token lifetime (10 minutes) is too short
- Verify `self.account_index` matches the account being traded

---

### Scenario 4: Account Orders Subscription Works, But No Order Updates

**Signs:**
- See both `subscribed/order_book` and `subscribed/account_orders`
- Never see `update/account_orders` message
- Bot may be submitting orders but no updates received

**Diagnosis:**
- Lighter not sending order updates (possible API behavior)
- Orders being submitted to wrong account/market
- WebSocket stopped receiving messages for some reason

**Action:**
```bash
# Check if ANY messages are still being received:
grep "update/order_book" hedge_mode_bp.log | tail -10

# If order_book updates appear but NOT account_orders updates:
# - Lighter API may send order updates differently
# - Check Lighter documentation for order notification format
# - May need to subscribe to different channel

# Check for disconnections:
grep "connection closed\|WebSocket error" hedge_mode_bp.log
```

---

### Scenario 5: Account Orders Updates Appear, But Status NOT "filled"

**Signs:**
- See `update/account_orders` messages
- See orders listed with status like `pending`, `submitted`, `open`
- Never see status change to `filled`
- See logs: `Skipping order id=XYZ with status=pending (not filled)`

**Diagnosis:**
- Orders aren't matching/filling
- Orders are being cancelled
- Orders have wrong price (not matching market)
- Orders submitted to wrong side

**Action:**
```bash
# Check what order statuses you're seeing:
grep "Order.*status=" hedge_mode_bp.log | sort | uniq -c

# Track a specific order:
grep "id=ABC123" hedge_mode_bp.log

# Check order submission details (in separate logs):
grep "Submitting order\|Order placed" hedge_mode_bp.log
```

---

### Scenario 6: Account Orders Updates Appear WITH "filled" Status

**Signs:**
- See `update/account_orders` messages
- See orders with status `filled`
- See `✅ [LIGHTER WS] Order FILLED` messages
- Bot should be processing fills

**Diagnosis:**
- ✅ Everything is working!
- But fills may not be processed correctly

**Action:**
- Check if `handle_lighter_order_result()` is executing
- Verify trade execution is happening after fills
- Check hedge strategy logs for trade processing

---

## Message Format Reference

### subscribed/order_book
```json
{
  "type": "subscribed/order_book",
  "order_book": {
    "offset": 12345,
    "bids": [[price, size], ...],
    "asks": [[price, size], ...]
  }
}
```
**Log output:**
```
📨 [LIGHTER WS] Received message type: subscribed/order_book
📨 [LIGHTER WS] Subscription confirmation: subscribed to order book
```

### subscribed/account_orders
```json
{
  "type": "subscribed/account_orders"
}
```
**Log output:**
```
📨 [LIGHTER WS] Received message type: subscribed/account_orders
📨 [LIGHTER WS] Subscription confirmation: subscribed to account orders
```

### update/order_book
```json
{
  "type": "update/order_book",
  "order_book": {
    "offset": 12346,
    "bids": [[price, size], ...],
    "asks": [[price, size], ...]
  }
}
```
**Log output:**
```
📨 [LIGHTER WS] Received message type: update/order_book
📨 [LIGHTER WS] Order book update - offset: 12346, bids: 50, asks: 48
```

### update/account_orders
```json
{
  "type": "update/account_orders",
  "orders": {
    "0": [
      {
        "order_id": "ABC123",
        "status": "filled",
        "side": "buy",
        "size": 0.5,
        "price": 19.50,
        ...other fields...
      }
    ]
  }
}
```
**Log output:**
```
📨 [LIGHTER WS] Account orders update received - Markets: ['0']
📨 [LIGHTER WS] Market 0: 1 orders
📨 [LIGHTER WS]   Order 0: id=ABC123, status=filled, side=buy, size=0.5, price=19.50
📨 [LIGHTER WS] Processing 1 orders for market 0
📨 [LIGHTER WS] Processing order id=ABC123, status=filled
✅ [LIGHTER WS] Order FILLED: id=ABC123
```

### ping/pong
```json
// Incoming:
{"type": "ping"}

// Outgoing (bot response):
{"type": "pong"}
```
**Log output:**
```
📨 [LIGHTER WS] Received message type: ping
📨 [LIGHTER WS] Ping received (sending pong)
```

---

## Quick Diagnostics Commands

### 1. Check Connection Health
```bash
grep "subscribed" hedge_mode_bp.log | head -5
```
Expected: Both `subscribed/order_book` and `subscribed/account_orders`

### 2. Check Auth Errors
```bash
grep -i "auth\|token" hedge_mode_bp.log
```
Expected: `Subscribed to account orders with auth token`

### 3. Check for Order Updates
```bash
grep "update/account_orders" hedge_mode_bp.log | wc -l
```
If 0: Account orders subscription not working
If >0: Subscription working, check order statuses

### 4. Find All Filled Orders
```bash
grep "Order FILLED" hedge_mode_bp.log
```
If empty: No orders are filling (check order logic)
If populated: Fills are being detected

### 5. Check Message Types Received
```bash
grep "Received message type:" hedge_mode_bp.log | cut -d: -f5 | sort | uniq -c
```
Shows frequency of each message type

### 6. Check for Unexpected Messages
```bash
grep "UNEXPECTED MESSAGE TYPE" hedge_mode_bp.log
```
If populated: Lighter is sending messages we don't handle

---

## Next Steps After Diagnosis

1. **Identify which scenario matches your situation**
2. **Apply the recommended action** for that scenario
3. **Re-run bot with updated configuration/code**
4. **Collect new logs** for 10-20 minutes
5. **Re-check diagnostics commands**
6. **Document any new unexpected message types**

## Related Files

- Main code: `f:/Dropbox/dexbot/perpdex/hedge/hedge_mode_bp.py` (lines 588-760)
- Logging config: Check bot initialization for logger setup
- API client: Lighter SDK for authentication/API calls

## Key Variables to Check

In bot logs, look for:
- `self.lighter_market_index` - should be market number (e.g., "0")
- `self.account_index` - should be account number
- `auth_token` creation - should succeed within 10 minutes
- WebSocket URL - should be `wss://mainnet.zklighter.elliot.ai/stream`

## Still Not Working?

If after following this guide the issue persists:
1. Save logs with timestamp
2. Document which scenario matched
3. Check Lighter API documentation for changes
4. Consider consulting Lighter support with logs
