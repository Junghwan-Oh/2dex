# Lighter WebSocket Logging - Testing Checklist

## Pre-Test Verification

- [ ] Code compiled successfully (syntax check passed ✅)
- [ ] Changes reviewed in git diff
- [ ] Documentation files created:
  - [ ] LIGHTER_WS_LOGGING_CHANGES.md
  - [ ] LIGHTER_WS_DIAGNOSTIC_GUIDE.md
  - [ ] LIGHTER_WS_LOGGING_SUMMARY.txt
  - [ ] TESTING_CHECKLIST.md (this file)

## Test Environment Setup

- [ ] Bot has correct config.yaml settings
- [ ] Lighter API credentials are valid
- [ ] Backpack API credentials are valid
- [ ] WebSocket URL is correct: `wss://mainnet.zklighter.elliot.ai/stream`
- [ ] Market index is correct in config
- [ ] Account index is correct in config
- [ ] Sufficient collateral on both exchanges

## Test Execution

### Phase 1: Connection Test (5 minutes)

Run bot and monitor for connection messages:

```bash
tail -f hedge_mode_bp.log | grep "LIGHTER WS"
```

Expected to see within first 30 seconds:
- [ ] `subscribed/order_book` message
- [ ] `subscribed/account_orders` message
- [ ] Periodic `order_book update` messages

**If NOT seeing these:**
- [ ] Check WebSocket connection errors in logs
- [ ] Verify market index in config
- [ ] Verify account index in config
- [ ] Check Lighter API is online
- [ ] Check network connectivity

### Phase 2: Order Book Updates Test (2 minutes)

Verify order book updates are flowing:

```bash
grep "update/order_book" hedge_mode_bp.log | head -20
```

Expected:
- [ ] Regular order book updates (every few seconds)
- [ ] Offset numbers increasing
- [ ] Bid/ask counts reasonable (not 0)

**If NOT seeing order book updates:**
- [ ] Check subscription failed in logs
- [ ] Verify WebSocket connection is stable
- [ ] Check for "connection closed" errors

### Phase 3: Submit Test Order (2 minutes)

Using the bot's order submission (or direct API call):

```
1. Note the order ID that's submitted
2. Wait 10 seconds
3. Check logs for account_orders messages:
   grep "update/account_orders" hedge_mode_bp.log | tail -5
```

Expected:
- [ ] See `update/account_orders` message within 10 seconds
- [ ] Message shows the order you just submitted
- [ ] Order has status like `pending`, `open`, or `submitted`

**If NOT seeing account orders update:**
- [ ] Check for `subscribed/account_orders` confirmation
- [ ] Check for auth token errors in logs
- [ ] Verify account index matches where order was placed
- [ ] Check Lighter API documentation for subscription format changes

### Phase 4: Monitor for Fill (10 seconds - 5 minutes)

Keep watching logs after order submission:

```bash
tail -f hedge_mode_bp.log | grep "update/account_orders\|Order FILLED"
```

Expected:
- [ ] See order status updates as it gets matched
- [ ] Eventually see order with status "filled"
- [ ] See `✅ [LIGHTER WS] Order FILLED` message
- [ ] See `handle_lighter_order_result` executing (in related logs)

**If order status stays "pending" for >30 seconds:**
- [ ] Order may not be matching price
- [ ] Check order book to verify price is in spread
- [ ] May need to manually cancel and resubmit

**If NEVER see order fill:**
- [ ] Check if order price is actually being hit in market
- [ ] Verify order was actually submitted to Lighter
- [ ] Check order status changes to "cancelled" instead of "filled"
- [ ] Consider manual order submission for testing

### Phase 5: Verify Order Result Handling

After order fills:

```bash
grep "Order FILLED\|handle_lighter_order_result\|executed" hedge_mode_bp.log | tail -10
```

Expected:
- [ ] See `✅ [LIGHTER WS] Order FILLED` message
- [ ] See related hedge strategy execution logs
- [ ] See position updated on Lighter

**If fill is detected but not processed:**
- [ ] Check `handle_lighter_order_result()` implementation
- [ ] Verify hedge strategy is running
- [ ] Check for errors in order result processing

## Diagnostic Checks

### Check 1: WebSocket Connection Health

```bash
grep "websocket\|connection" hedge_mode_bp.log | tail -20
```

Look for:
- [ ] No "connection closed" errors (frequent reconnects bad)
- [ ] Successfully subscribed to both channels
- [ ] No auth token creation errors

### Check 2: Message Type Frequency

```bash
grep "Received message type:" hedge_mode_bp.log | cut -d: -f5 | sort | uniq -c
```

Expected breakdown:
- [ ] High count of `order_book` updates (frequent)
- [ ] Lower count of `account_orders` updates (only when orders change)
- [ ] Some `ping` messages (keep-alive)
- [ ] Few or no `subscribed` messages (only at startup)

### Check 3: Check for Unexpected Message Types

```bash
grep "UNEXPECTED MESSAGE TYPE" hedge_mode_bp.log
```

Expected:
- [ ] NO unexpected message types (empty result)

**If unexpected types appear:**
- [ ] Document the type name
- [ ] Document the full payload
- [ ] Research in Lighter API docs
- [ ] May need to add handler for that type

### Check 4: Order Status Distribution

```bash
grep "Order.*status=" hedge_mode_bp.log | cut -d= -f3 | cut -d, -f1 | sort | uniq -c
```

Expected:
- [ ] Mostly "filled" for orders that completed
- [ ] Some "pending" or "open" for orders in process
- [ ] Few or no "cancelled" or "rejected"

**If mostly cancelled/rejected:**
- [ ] Check order parameters (price, size)
- [ ] Verify orders are submitting correctly
- [ ] Check if market conditions changed

## Success Criteria

### Minimum Success (Logging Working)
- [ ] See WebSocket connection messages
- [ ] See `subscribed/order_book` confirmation
- [ ] See `update/order_book` messages regularly
- [ ] Logs show message types being received

### Good Success (Subscriptions Working)
- [ ] + See `subscribed/account_orders` confirmation
- [ ] + See `update/account_orders` messages
- [ ] + Can track order status updates

### Complete Success (Full Functionality)
- [ ] + See order fills logged with `✅ [LIGHTER WS] Order FILLED`
- [ ] + Hedge strategy processes fills
- [ ] + Positions updated correctly

## Troubleshooting Decision Tree

```
Seeing any LIGHTER WS logs?
├─ NO
│  └─ WebSocket not connecting
│     ├─ Check network/firewall
│     ├─ Check WebSocket URL
│     └─ Check Lighter API online
│
├─ YES
└─ Seeing subscribed/order_book?
   ├─ NO
   │  └─ Order book subscription failed
   │     ├─ Check market index
   │     └─ Check WebSocket connection
   │
   └─ YES
      └─ Seeing subscribed/account_orders?
         ├─ NO
         │  └─ Account orders subscription failed (most likely)
         │     ├─ Check auth token creation
         │     ├─ Check account index
         │     └─ Verify subscription format with API docs
         │
         └─ YES
            └─ Seeing update/account_orders?
               ├─ NO
               │  └─ Orders aren't being submitted
               │     ├─ Check order submission code
               │     └─ Verify orders placed on correct exchange
               │
               └─ YES
                  └─ Seeing status="filled"?
                     ├─ NO
                     │  └─ Orders filling but not detected
                     │     ├─ Check order matching (price in spread?)
                     │     └─ Check if status uses different name
                     │
                     └─ YES
                        └─ ✅ EVERYTHING WORKING!
                           └─ Check hedge strategy execution
```

## Documentation References

For detailed troubleshooting:
- See: `LIGHTER_WS_DIAGNOSTIC_GUIDE.md`
- For implementation details: `LIGHTER_WS_LOGGING_CHANGES.md`
- For quick reference: `LIGHTER_WS_LOGGING_SUMMARY.txt`

## Performance Monitoring

During test, monitor:

```bash
# CPU usage
top -b -n 1 | grep python

# Memory usage
ps aux | grep python | grep hedge

# Log file size growth
ls -lh hedge_mode_bp.log
```

Expected:
- [ ] No unusual CPU spikes
- [ ] Memory usage stable
- [ ] Log file grows slowly (< 10MB per 10 minutes)

## Data to Collect After Testing

Save for analysis:
- [ ] Last 500 lines of hedge_mode_bp.log
- [ ] Any error messages from the logs
- [ ] Screenshot of which scenario matched (see diagnostic guide)
- [ ] Timestamp of test (helps correlate with order submissions)

## Completion

- [ ] All 5 phases completed
- [ ] Diagnostic checks performed
- [ ] Success criteria verified
- [ ] Documentation reviewed
- [ ] Issues documented (if any)
- [ ] Ready to proceed with next phase

## Date Completed

Test Date: _______________

Tester: _______________

Overall Result: _______________

Notes:
```
_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
```

---

## Next Steps After Testing

1. **If everything working:**
   - Proceed to full integration testing
   - Monitor multiple trades
   - Check hedge strategy execution with fills

2. **If problems found:**
   - Consult LIGHTER_WS_DIAGNOSTIC_GUIDE.md
   - Apply recommended actions for scenario
   - Re-test with corrections
   - Document findings

3. **If unexpected message types:**
   - Save full payloads
   - Check Lighter API documentation
   - Add handlers for new message types
   - Update logging to match

4. **If auth keeps failing:**
   - Verify credentials are current
   - Check if auth token lifetime needs adjustment
   - Consult Lighter authentication documentation
   - May need to add token refresh logic

## Support Information

If stuck:
1. Collect all logs with 📨 [LIGHTER WS] messages
2. Document which diagnostic scenario matched
3. Include:
   - Error messages
   - Message types received
   - Order submissions and status
   - Configuration details (without secrets)
4. Consult Lighter API documentation for format changes
