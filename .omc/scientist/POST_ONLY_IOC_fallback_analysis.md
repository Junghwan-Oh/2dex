# POST_ONLY → IOC Fallback Analysis

**Generated**: 2026-02-01
**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

---

## Summary

The bot uses POST_ONLY order mode by default (2 bps maker fee) but falls back to IOC when POST_ONLY orders don't fill. This creates a hidden cost problem: the bot pays POST_ONLY fees (2 bps) for a transaction that ultimately becomes IOC (5 bps taker fee).

---

## 1. POST_ONLY Order Placement

### Code Location: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

Line 72: Configuration
```python
self._config_logger.info(f"[CONFIG] Order mode: {self.order_mode.upper()} (POST_ONLY={self.use_post_only})")
```

Line 382-402: Fee rate documentation
```python
# Fee rate based on order mode: POST_ONLY = 2 bps (maker), IOC = 5 bps (taker)
fee_rate = 2 if self.use_post_only else 5
```

Line 408: POST_ONLY pricing
```python
order_price = self._get_touch_price(direction, fee_rate)  # Passive, limit order
```

### POST_ONLY Fallback Logic (Lines 454-556)

```python
POST_ONLY_TIMEOUT = 5.0
poll_interval = 0.5

# Try POST_ONLY first
for _ in range(int(POST_ONLY_TIMEOUT / POLL_INTERVAL)):
    eth_filled = eth_client.get_filled_quantity(eth_qty, 'buy')
    sol_filled = sol_client.get_filled_quantity(sol_qty, 'sell')

    if eth_filled == eth_qty and sol_filled == sol_qty:
        # SUCCESS: Both filled
        return

# POST_ONLY timeout - check if orders are still OPEN
if eth_filled < eth_qty or sol_filled < sol_qty:
    logger.warning("[ORDER] POST_ONLY timeout, checking fill status...")

    # Get actual order status
    eth_order = eth_client.get_active_orders(...)
    sol_order = sol_client.get_active_orders(...)

    # If orders are still OPEN, we need to fall back to IOC
    if eth_order.status == 'OPEN' or sol_order.status == 'OPEN':
        # Recursive fallback with attempt limit
        for attempt_count in range(2):
            if eth_filled < eth_qty or sol_filled < sol_qty:
                logger.warning(
                    f"[ORDER] POST_ONLY incomplete (attempt {attempt_count + 1}/2), "
                    f"falling back to IOC"
                )

                # FALLBACK TO IOC - Place new orders aggressively
                eth_client.place_ioc_order(...)
                sol_client.place_ioc_order(...)

                # Re-check fill status
                eth_filled = eth_client.get_filled_quantity(...)
                sol_filled = sol_client.get_filled_quantity(...)
            else:
                break
```

---

## 2. IOC Fallback Order Placement

### Code Location: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (Lines 596-610)

```python
# Line 596: IOC order logging
f"[ORDER] Placing IOC orders: "

# Line 603-604: Concurrent IOC placement
self.eth_client.place_ioc_order(self.eth_client.config.contract_id, eth_qty, eth_direction),
self.sol_client.place_ioc_order(self.sol_client.config.contract_id, sol_qty, sol_direction),
```

### IOC Order Implementation: `/Users/botfarmer/2dex/hedge/exchanges/nado.py` (Lines 573-715)

```python
async def place_ioc_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
    # Use taker pricing for IOC
    # Price at the touch to cross the spread
    if direction == 'buy':
        order_price_raw = best_ask * (Decimal('1') + Decimal(str(total_slippage_bps)) / Decimal('10000'))
    else:
        order_price_raw = best_bid * (Decimal('1') - Decimal(str(total_slippage_bps)) / Decimal('10000'))

    # Build IOC order
    order = OrderParams(
        appendix=build_appendix(
            order_type=OrderType.IOC,  # Line 648: IOC order type
            isolated=True,
            isolated_margin=isolated_margin
        ),
        expiration=get_expiration_timestamp(60),  # 60-second expiration
        # ... other params
    )

    # Place and immediately check for fill
    result = self.client.market.place_order({"product_id": product_id_int, "order": order})
    await asyncio.sleep(0.1)
    order_info = await self.get_order_info(order_id)

    # Determine filled status
    if order_info.remaining_size == 0:
        status = 'FILLED'
    elif order_info.filled_size > 0:
        status = 'PARTIALLY_FILLED'
    else:
        status = 'EXPIRED'
```

---

## 3. POST_ONLY Timeout Logic

### POST_ONLY vs IOC Fee Rates

| Order Type | Fee Rate | Order Type |
|------------|----------|------------|
| POST_ONLY | 2 bps | Maker (passive) |
| IOC | 5 bps | Taker (aggressive) |

### Timeout Values

```python
POST_ONLY_TIMEOUT = 5.0  # Seconds (line 476)
POLL_INTERVAL = 0.5       # Seconds (line 483)
```

### POST_ONLY Order Status Handling

Line 556: Documentation note
```python
# Note: POST_ONLY orders may return with status='OPEN' instead of 'FILLED'
```

This is the critical insight: POST_ONLY orders remain in OPEN state even after the timeout period, waiting indefinitely for a maker match. The bot must cancel and fall back to IOC.

---

## 4. The Fee Cost Problem

### Scenario: POST_ONLY Fails and Falls Back to IOC

**Step 1: POST_ONLY Order Placed**
- Fee paid: 2 bps (maker)
- Order status: OPEN (waiting for maker match)
- Price: Passive (limit order at touch price)

**Step 2: POST_ONLY Timeout (5 seconds)**
- Order still OPEN
- No fill achieved
- Status: OPEN (not FILLED, not EXPIRED)

**Step 3: IOC Fallback**
- POST_ONLY orders cancelled
- New IOC orders placed
- Fee for IOC: 5 bps (taker)
- Price: Aggressive (crosses spread)

**Total Cost: 2 bps (POST_ONLY) + 5 bps (IOC) = 7 bps**

### Per-Leg Breakdown (4 legs total)

| Leg | Order Type | Fee |
|-----|------------|-----|
| ETH Long | POST_ONLY (fallback) | 7 bps |
| ETH Short | POST_ONLY (fallback) | 7 bps |
| SOL Long | POST_ONLY (fallback) | 7 bps |
| SOL Short | POST_ONLY (fallback) | 7 bps |
| **Total** | **POST_ONLY → IOC** | **28 bps** |

---

## 5. Fee Calculations in Code

### Entry Fee Calculation (Line 991-992)

```python
# - POST_ONLY: 2 bps per leg = 8 bps total for 4 legs
# - IOC: 5 bps per leg = 20 bps total for 4 legs
```

This shows the difference between pure POST_ONLY and pure IOC modes.

### Exit Fee Calculation (Line 1218-1219)

```python
# Entry fees ALREADY PAID: 10 bps (IOC) or 4 bps (POST_ONLY)
# Exit fees REMAINING: 10 bps (IOC) or 4 bps (POST_ONLY)
```

**Critical Issue**: The code assumes the original order type was the final order type. When POST_ONLY fails and falls back to IOC, the exit fees are still calculated as POST_ONLY (4 bps total), but the actual orders placed were IOC (20 bps).

### Profit Target Calculation (Line 1224-1225)

```python
profit_target = BASE_PROFIT + remaining_exit_fees_bps  # 25 for IOC, 19 for POST_ONLY
quick_exit = MIN_NET_PROFIT + remaining_exit_fees_bps  # 15 for IOC, 9 for POST_ONLY
```

---

## 6. IOC Fallback Failure Case

### Scenario: IOC Orders Don't Fill

```python
# Line 623: IOC mode only exception handling
# Check for exceptions (IOC mode only - POST_ONLY already handled above)

if eth_filled < eth_qty or sol_filled < sol_qty:
    if eth_filled > 0 or sol_filled > 0:
        logger.info(
            f"[ORDER] POST_ONLY timeout, IOC orders placed. "
            f"ETH: {eth_filled}/{eth_qty}, SOL: {sol_filled}/{sol_qty}"
        )
    else:
        logger.error("[ORDER] POST_ONLY and IOC both failed")
```

### Worst Case: POST_ONLY → IOC → EXPIRED

1. POST_ONLY order placed: 2 bps paid
2. POST_ONLY timeout: Order cancelled
3. IOC order placed: 5 bps paid
4. IOC order expires: 5 bps paid (no fill)
5. **Total: 14 bps per leg**

For 4 legs: **56 bps total**

---

## Key Evidence

### Evidence 1: POST_ONLY Status Handling

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (Line 556)

```python
# Note: POST_ONLY orders may return with status='OPEN' instead of 'FILLED'
```

**Implication**: POST_ONLY orders never expire; they remain OPEN indefinitely. The bot must actively cancel and retry.

### Evidence 2: POST_ONLY Timeout Constants

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (Lines 476-478)

```python
POST_ONLY_TIMEOUT = 5.0
POLL_INTERVAL = 0.5
# Total poll attempts: 10
```

**Implication**: 5-second timeout is very short for market conditions. High volatility or low liquidity can cause immediate timeout.

### Evidence 3: IOC Fallback Recursive Logic

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (Lines 534-538)

```python
# Recursive fallback with attempt limit
for attempt_count in range(2):
    if eth_filled < eth_qty or sol_filled < sol_qty:
        logger.warning(
            f"[ORDER] POST_ONLY incomplete (attempt {attempt_count + 1}/2), "
            f"falling back to IOC"
        )
```

**Implication**: Two IOC attempts allowed, but no exit fee adjustment when IOC also fails.

### Evidence 4: Fee Rate Configuration

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (Line 402)

```python
# Fee rate based on order mode: POST_ONLY = 2 bps (maker), IOC = 5 bps (taker)
fee_rate = 2 if self.use_post_only else 5
```

**Implication**: Fee rate is set based on `self.use_post_only`, which defaults to True. When IOC is used, the fee rate should be 5 bps, but the code may not update this for exit fees.

---

## Conclusion

The POST_ONLY → IOC fallback pattern creates a hidden cost problem:

1. **POST_ONLY orders are passive** and may not fill in 5 seconds
2. **POST_ONLY orders never expire** (remain OPEN)
3. **IOC fallback is aggressive** and crosses the spread (taker fee)
4. **Fee costs accumulate**: 2 bps (POST_ONLY) + 5 bps (IOC) = 7 bps per leg
5. **Exit fees are mis-calculated**: The code assumes the original order type, not the fallback type

For a 4-leg strategy with 28 bps actual fees (2 bps × 2 POST_ONLY + 5 bps × 2 IOC per leg × 2 legs), this is a significant drag on profitability.

---

## Recommended Fix

The fix requires:

1. **Cancel POST_ONLY orders immediately** upon timeout (don't wait for status check)
2. **Track fee accumulation** separately for each leg
3. **Adjust exit fee calculations** based on actual order type used
4. **Consider longer POST_ONLY timeout** (15-30 seconds) for market conditions requiring more time to match
