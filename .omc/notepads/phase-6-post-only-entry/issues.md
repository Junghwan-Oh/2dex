# Phase 6: POST_ONLY Entry Option - Issues

## Issues Encountered

### Issue 1: Python Command Availability
**Problem**: `python` command not found on system

**Solution**: Used `python3` instead

**Impact**: Minor - affected development workflow only, not production code

### Issue 2: Order Status Semantics
**Problem**: POST_ONLY orders return `status='OPEN'` not `status='FILLED'`

**Context**:
- `place_open_order()` uses OrderType.POST_ONLY appendix
- Orders are placed on the order book, not immediately filled
- IOC orders return `status='FILLED'` when successful

**Solution**: Updated fill detection logic:
```python
eth_filled = eth_result.status == 'FILLED' or (self.use_post_only and eth_result.status == 'OPEN')
```

**Status**: Resolved

### Issue 3: Missing Fallback Logic
**Problem**: POST_ONLY orders may not fill within timeout

**Current State**:
- POST_ONLY orders placed with `status='OPEN'`
- No monitoring for fills or cancellation after timeout
- TODO comment added for V5.4 implementation

**Required for V5.4**:
```python
# TODO: V5.4 - Fall back to IOC if POST_ONLY doesn't fill
```

**Status**: Deferred to V5.4

## Known Limitations

### Limitation 1: No Order Monitoring
POST_ONLY orders are placed but not actively monitored for fills. In production:
- Order status should be polled periodically
- Orders should be cancelled after timeout
- IOC fallback should trigger if no fill

### Limitation 2: No Partial Fill Handling
If POST_ONLY order partially fills:
- Current code treats `status='OPEN'` as success
- No tracking of partial fills vs full fills
- PNL calculation assumes full fill

### Limitation 3: Fee Verification
Fees are calculated based on order mode but not verified against exchange:
- Nado charges 2 bps for maker (POST_ONLY)
- Nado charges 5 bps for taker (IOC)
- Actual fees should be confirmed from order results

## Testing Gaps

### Gap 1: Integration Testing
**Missing**: End-to-end test with real Nado API

**Required**:
- Valid .env credentials
- Testnet or devnet environment
- Small order sizes for safety

### Gap 2: Fee Verification
**Missing**: Compare calculated fees vs actual fees from API

**Required**:
- Parse fee data from OrderResult
- Verify FEE_RATE matches actual fees
- Log discrepancies

### Gap 3: POST_ONLY Fill Behavior
**Missing**: Test POST_ONLY order fill behavior in live market

**Required**:
- Observe order status transitions
- Measure fill latency
- Test partial fill scenarios

## Future Work (V5.4)

1. **Order Monitoring**: Implement order status polling
2. **Timeout Handling**: Cancel POST_ONLY orders after timeout
3. **IOC Fallback**: Retry with IOC if POST_ONLY doesn't fill
4. **Fee Verification**: Parse and verify actual fees from API
5. **Partial Fill Tracking**: Track and log partial fills separately
