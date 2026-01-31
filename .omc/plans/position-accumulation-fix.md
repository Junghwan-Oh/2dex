# Position Accumulation Fix Plan - DN Pair Bot (REVISED)

## Executive Summary

**Problem**: DN Pair Bot accumulates positions across cycles (0.074 ETH, 1.6 SOL after 5 cycles) due to Nado API's asynchronous position updates (20+ second delays) and cross-margin configuration causing unintended leverage.

**Root Cause**: Nado API's `get_subaccount_info` has 20+ second delays in updating positions after order fills, while `place_ioc_order` returns immediate confirmation. The bot uses `isolated=False` (cross margin) and has no leverage control.

**Solution**: Implement hybrid position tracking (internal + API reconciliation), switch to isolated margin mode with explicit margin amount, enhance UNWIND logic to reset internal tracking, and add position verification capabilities.

**CRITICAL RESEARCH FINDINGS**:
- Nado SDK `build_appendix()` DOES support `isolated=True` and `isolated_margin` parameter
- Nado SDK does NOT provide a `set_leverage()` method - leverage is determined by `isolated_margin` parameter in each order
- MarginManager provides `calculate_account_leverage()` and `calculate_isolated_position_leverage()` for verification
- `eth_direction` and `sol_direction` variables ARE accessible at BUILD fallback location (line 1390)

---

## 1. Requirements Summary

### Problem Statement
The DN Pair Bot accumulates positions across trading cycles instead of maintaining delta-neutral exposure. After 5 cycles, the bot holds:
- **ETH Position**: 0.074 ETH (unintended accumulation)
- **SOL Position**: 1.6 SOL (unintended accumulation)
- **Unintended Leverage**: ~20x ETH, ~10x SOL (due to cross margin)

### Success Criteria
1. **Zero Position Accumulation**: Positions must close completely each cycle (abs(pos) < 0.001)
2. **API Delay Resilience**: Bot must handle 20+ second position update delays
3. **Controlled Leverage**: Fixed 5x leverage via explicit `isolated_margin` parameter
4. **Isolated Margin**: Each position isolated with explicit margin amount
5. **Internal Tracking Reset**: `_internal_positions` reset after UNWIND completes
6. **Leverage Verification**: Query and log actual leverage via MarginManager

---

## 2. Architecture Changes

### 2.1 Position Tracking Strategy

**Current State**:
- BUILD uses OrderResult.filled_size for tracking (immediate)
- UNWIND only checks API positions (delayed 20+ seconds)
- No internal tracking during UNWIND phase
- Cross-margin mode (`isolated=False`)
- `_internal_positions` NOT reset after UNWIND_COMPLETE

**Target State**:
```
┌─────────────────────────────────────────────────────────┐
│  Hybrid Position Tracking System                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐         ┌──────────────┐            │
│  │   Internal   │         │     API      │            │
│  │   Tracking   │◄────────┤   Reconcile  │            │
│  │  (Optimistic)│         │    (Source)  │            │
│  └──────┬───────┘         └──────────────┘            │
│         │                                                 │
│         │ Primary for UNWIND decisions                   │
│         │                                                 │
│  ┌──────▼──────────────────────────────────┐            │
│  │  UNWIND Logic: Use internal positions   │            │
│  │  Fallback: API if internal = 0          │            │
│  │  CRITICAL: Reset _internal_positions    │            │
│  │  to 0 after UNWIND_COMPLETE              │            │
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Margin Mode Architecture

**Current State** (Cross Margin):
```python
# File: hedge/exchanges/nado.py:553
appendix=build_appendix(order_type=OrderType.IOC, isolated=False)
```
- Problem: Positions share account-level collateral
- Result: Unintended leverage (ETH ~20x, SOL ~10x)

**Target State** (Isolated Margin with Explicit Margin):
```python
# Change to isolated mode with calculated margin
# For 5x leverage: margin = notional / 5
notional_value = quantity * price
isolated_margin = int(notional_value / 5)  # 5x leverage

appendix=build_appendix(
    order_type=OrderType.IOC,
    isolated=True,
    isolated_margin=isolated_margin  # Explicit margin for 5x leverage
)
```

**RESEARCH FINDING**:
- `build_appendix()` signature: `(order_type, isolated=False, isolated_margin=None, ...)`
- `isolated_margin` (Optional[int]): Margin amount for isolated position if isolated is True
- Leverage = notional_value / isolated_margin
- NO separate `set_leverage()` method exists in Nado SDK

### 2.3 Leverage Control

**Current State**: No explicit leverage (uses account defaults)

**Target State**:
- ETH: Fixed 5x leverage via `isolated_margin` parameter
- SOL: Fixed 5x leverage via `isolated_margin` parameter
- Verification: Query leverage via `MarginManager.calculate_account_leverage()`

**RESEARCH FINDING - Leverage Verification**:
```python
from nado_protocol.utils.margin_manager import MarginManager

# Get account leverage
margin_manager = MarginManager.from_client(client)
summary = margin_manager.calculate_account_summary()
print(f"Account leverage: {summary.account_leverage}x")

# Get isolated position leverage
isolated_positions = margin_manager.calculate_isolated_position_metrics(...)
print(f"Position leverage: {iso_pos.leverage}x")
```

---

## 3. Implementation Steps

### Step 1: Isolated Margin Mode Change with Explicit Margin

**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Location 1**: Line 553 - `place_ioc_order` method

**BEFORE**:
```python
order = OrderParams(
    sender=SubaccountParams(
        subaccount_owner=self.owner,
        subaccount_name=self.subaccount_name,
    ),
    priceX18=to_x18(float(str(order_price))),
    amount=to_x18(float(str(rounded_quantity))) if direction == 'buy' else -to_x18(float(str(rounded_quantity))),
    expiration=get_expiration_timestamp(60),  # Short expiration for IOC
    nonce=gen_order_nonce(),
    appendix=build_appendix(order_type=OrderType.IOC, isolated=False)  # Cross margin
)
```

**AFTER**:
```python
# Calculate isolated margin for 5x leverage
# Formula: isolated_margin = (quantity * price) / leverage
notional_value = float(str(rounded_quantity)) * float(str(order_price))
leverage = 5  # Fixed 5x leverage
isolated_margin = int(notional_value / leverage)

order = OrderParams(
    sender=SubaccountParams(
        subaccount_owner=self.owner,
        subaccount_name=self.subaccount_name,
    ),
    priceX18=to_x18(float(str(order_price))),
    amount=to_x18(float(str(rounded_quantity))) if direction == 'buy' else -to_x18(float(str(rounded_quantity))),
    expiration=get_expiration_timestamp(60),  # Short expiration for IOC
    nonce=gen_order_nonce(),
    appendix=build_appendix(
        order_type=OrderType.IOC,
        isolated=True,
        isolated_margin=isolated_margin
    )  # Isolated margin with 5x leverage
)
```

**Location 2**: Line 469 - `place_open_order` method (already isolated, add margin)

**BEFORE**:
```python
appendix=build_appendix(order_type=OrderType.POST_ONLY, isolated=True)
```

**AFTER**:
```python
# Calculate isolated margin for 5x leverage
notional_value = float(str(quantity)) * float(str(price))
leverage = 5  # Fixed 5x leverage
isolated_margin = int(notional_value / leverage)

appendix=build_appendix(
    order_type=OrderType.POST_ONLY,
    isolated=True,
    isolated_margin=isolated_margin
)
```

**Location 3**: Line 694 - `place_close_order` method (already isolated, add margin)

**BEFORE**:
```python
appendix=build_appendix(order_type=OrderType.POST_ONLY, isolated=True)
```

**AFTER**:
```python
# Calculate isolated margin for 5x leverage
notional_value = float(str(quantity)) * float(str(price))
leverage = 5  # Fixed 5x leverage
isolated_margin = int(notional_value / leverage)

appendix=build_appendix(
    order_type=OrderType.POST_ONLY,
    isolated=True,
    isolated_margin=isolated_margin
)
```

---

### Step 2: Add Leverage Verification Method

**File**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**New Method**: Add after `__init__` method (after line 85)

```python
async def verify_leverage(self) -> dict:
    """Verify current leverage settings using MarginManager.

    Returns:
        dict: {
            "account_leverage": Decimal,
            "eth_leverage": Optional[Decimal],
            "sol_leverage": Optional[Decimal],
            "margin_mode": str
        }

    Note:
        Nado SDK does not provide a set_leverage() method.
        Leverage is controlled per-order via isolated_margin parameter.
        This method queries and reports actual leverage settings.
    """
    try:
        from nado_protocol.utils.margin_manager import MarginManager

        # Create margin manager from client
        margin_manager = MarginManager.from_client(self.client)

        # Get account-level summary
        account_summary = margin_manager.calculate_account_summary()

        # Get isolated position metrics
        isolated_positions = margin_manager.calculate_isolated_position_metrics(
            self.client.context.subaccount
        )

        # Extract leverage for our positions
        eth_leverage = None
        sol_leverage = None

        for pos in isolated_positions.isolated_positions:
            if pos.ticker == "ETH":
                eth_leverage = pos.leverage
            elif pos.ticker == "SOL":
                sol_leverage = pos.leverage

        result = {
            "account_leverage": account_summary.account_leverage,
            "eth_leverage": eth_leverage,
            "sol_leverage": sol_leverage,
            "margin_mode": "isolated" if eth_leverage or sol_leverage else "cross"
        }

        self.logger.log(
            f"Leverage verification - Account: {result['account_leverage']:.2f}x, "
            f"ETH: {eth_leverage if eth_leverage else 'N/A'}x, "
            f"SOL: {sol_leverage if sol_leverage else 'N/A'}x",
            "INFO"
        )

        return result

    except Exception as e:
        self.logger.log(f"Error verifying leverage: {e}", "ERROR")
        return {
            "account_leverage": Decimal("0"),
            "eth_leverage": None,
            "sol_leverage": None,
            "margin_mode": "unknown"
        }
```

**Call Location**: In `DN_pair_eth_sol_nado.py`, modify `initialize_clients` method

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Location**: After line 1812 (after SOL client connection)

**BEFORE**:
```python
        self.logger.info(
            f"[INIT] SOL client initialized (contract: {self.sol_contract_id}, tick: {self.sol_tick_size}, ws: {self.sol_client._ws_connected})"
        )
```

**AFTER**:
```python
        self.logger.info(
            f"[INIT] SOL client initialized (contract: {self.sol_contract_id}, tick: {self.sol_tick_size}, ws: {self.sol_client._ws_connected})"
        )

        # Verify initial leverage settings
        self.logger.info("[INIT] Verifying leverage settings...")
        eth_leverage = await self.eth_client.verify_leverage()
        sol_leverage = await self.sol_client.verify_leverage()

        self.logger.info(
            f"[INIT] Initial leverage - "
            f"ETH: {eth_leverage['account_leverage']:.2f}x ({eth_leverage['margin_mode']}), "
            f"SOL: {sol_leverage['account_leverage']:.2f}x ({sol_leverage['margin_mode']})"
        )
```

---

### Step 3: Fix UNWIND Internal Tracking Reset (CRITICAL)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Location**: Lines 1567-1571 - UNWIND_COMPLETE phase transition

**BEFORE**:
```python
                # Clear entry state for next cycle
                self.entry_prices = {"ETH": None, "SOL": None}
                self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
                self.entry_timestamps = {"ETH": None, "SOL": None}

                # PHASE TRANSITION: UNWIND_COMPLETE -> IDLE
                self._phase = CyclePhase.IDLE
                self.logger.info(f"[PHASE] UNWIND_COMPLETE -> IDLE")

                return True
```

**AFTER**:
```python
                # Clear entry state for next cycle
                self.entry_prices = {"ETH": None, "SOL": None}
                self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
                self.entry_timestamps = {"ETH": None, "SOL": None}

                # CRITICAL FIX: Reset internal position tracking after UNWIND completes
                # This prevents position accumulation across cycles
                self._internal_positions = {"ETH": Decimal("0"), "SOL": Decimal("0")}
                self.logger.info(
                    f"[UNWIND] Reset internal tracking - "
                    f"ETH: {self._internal_positions['ETH']}, "
                    f"SOL: {self._internal_positions['SOL']}"
                )

                # PHASE TRANSITION: UNWIND_COMPLETE -> IDLE
                self._phase = CyclePhase.IDLE
                self.logger.info(f"[PHASE] UNWIND_COMPLETE -> IDLE")

                return True
```

**RATIONALE**:
- The plan correctly identified that `_internal_positions` is NOT reset after UNWIND_COMPLETE
- Without this reset, the next BUILD cycle will use stale internal position values
- This causes position accumulation because UNWIND thinks positions still exist

---

### Step 4: BUILD Verification Enhancement

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Location**: Lines 1346-1414 - BUILD_VERIFYING phase

**Current Issue**: BUILD falls back to OrderResult confirmation when API returns 0, but doesn't update internal tracking.

**Fix**: Update internal tracking when using fallback.

**BEFORE** (lines 1390-1407):
```python
            # Verification failed after all retries
            # FALLBACK: If orders report as filled but API returns 0, proceed with caution
            # This handles testnet API delay issues
            eth_filled_qty = getattr(eth_result, 'filled_size', Decimal('0'))
            sol_filled_qty = getattr(sol_result, 'filled_size', Decimal('0'))

            if eth_filled_qty > 0 and sol_filled_qty > 0:
                self.logger.warning(
                    f"[BUILD_VERIFY] API POSITION DELAY: Orders report filled "
                    f"(ETH={eth_filled_qty}, SOL={sol_filled_qty}) but API positions=0. "
                    f"Proceeding based on order fill confirmation."
                )
                self.logger.warning(
                    f"[BUILD_VERIFY] This is likely a testnet API delay. "
                    f"On production, verify positions manually."
                )
                self._phase = CyclePhase.BUILD_COMPLETE
                self.logger.info(f"[PHASE] BUILD_VERIFYING -> BUILD_COMPLETE (FALLBACK)")
                return True
```

**AFTER**:
```python
            # Verification failed after all retries
            # FALLBACK: If orders report as filled but API returns 0, proceed with caution
            # This handles testnet API delay issues
            eth_filled_qty = getattr(eth_result, 'filled_size', Decimal('0'))
            sol_filled_qty = getattr(sol_result, 'filled_size', Decimal('0'))

            if eth_filled_qty > 0 and sol_filled_qty > 0:
                self.logger.warning(
                    f"[BUILD_VERIFY] API POSITION DELAY: Orders report filled "
                    f"(ETH={eth_filled_qty}, SOL={sol_filled_qty}) but API positions=0. "
                    f"Proceeding based on order fill confirmation."
                )
                self.logger.warning(
                    f"[BUILD_VERIFY] This is likely a testnet API delay. "
                    f"On production, verify positions manually."
                )

                # CRITICAL: Update internal tracking when using fallback
                # This ensures UNWIND has accurate position data even if API delays
                # eth_direction and sol_direction are available in this scope
                if eth_direction == "buy":
                    self._internal_positions['ETH'] += eth_filled_qty
                else:
                    self._internal_positions['ETH'] -= eth_filled_qty

                if sol_direction == "sell":
                    self._internal_positions['SOL'] -= sol_filled_qty
                else:
                    self._internal_positions['SOL'] += sol_filled_qty

                self.logger.warning(
                    f"[BUILD_VERIFY] Updated internal tracking from fallback: "
                    f"ETH={self._internal_positions['ETH']}, SOL={self._internal_positions['SOL']}"
                )

                self._phase = CyclePhase.BUILD_COMPLETE
                self.logger.info(f"[PHASE] BUILD_VERIFYING -> BUILD_COMPLETE (FALLBACK)")
                return True
```

**VERIFICATION**: `eth_direction` and `sol_direction` ARE available at this location (line 1390)
- They are parameters of `execute_build_cycle()` (line 1245)
- They are passed to `place_simultaneous_orders()` (line 1331)
- The fallback code is in the same method, so variables are in scope

---

### Step 5: Isolated Margin Impact Analysis

**CRITICAL CONSIDERATION**: What happens when switching from cross to isolated margin?

**Pre-Deployment Analysis Required**:

1. **Existing Position Impact**:
   - Cross-margin positions use shared collateral
   - Isolated positions require dedicated margin per position
   - Switching margin mode mid-cycle may cause issues

2. **Collateral Requirements**:
   - Isolated margin typically requires MORE collateral than cross
   - Formula: `isolated_margin = notional / leverage`
   - For 5x leverage on $100 notional: $20 margin required
   - Cross margin might allow higher leverage with less collateral

3. **Mixing Margin Modes**:
   - Can you have cross and isolated positions simultaneously?
   - Answer: Likely YES, but need to verify with Nado documentation

**Mitigation Strategy**:
- Start with empty account (close all existing positions)
- Deploy isolated margin changes before starting bot
- Verify via `verify_leverage()` method that mode is isolated
- Monitor first cycle closely for margin/liquidation issues

**Rollback Plan**:
- If isolated margin causes issues, close positions
- Revert `isolated=True` to `isolated=False`
- Remove `isolated_margin` parameter
- Accept position accumulation issue until alternative solution found

---

## 4. Testing Strategy

### 4.1 Pre-Deployment Testing

**Test 1: Isolated Margin Verification**
```bash
# Run single cycle and verify margin mode
python DN_pair_eth_sol_nado.py --size 100 --iter 1 --use-ioc

# Check logs for:
# - "Leverage verification - Account: X.XXx, ETH: 5.00x, SOL: 5.00x"
# - "isolated=True" in order params
# - "isolated_margin" calculated correctly
```

**Test 2: Position Tracking Accuracy**
```bash
# Run 3 cycles and verify positions close
python DN_pair_eth_sol_nado.py --size 100 --iter 3 --use-ioc

# After completion, manually check:
# - API positions: abs(pos) < 0.001 for both ETH and SOL
# - Internal tracking: abs(pos) < 0.001 for both ETH and SOL
# - CSV logs: All cycles show both entry and exit
```

**Test 3: Internal Tracking Reset**
```bash
# Run 5 cycles and check for accumulation
python DN_pair_eth_sol_nado.py --size 100 --iter 5 --use-ioc

# Verify:
# - Log shows "[UNWIND] Reset internal tracking" each cycle
# - Final positions: abs(pos) < 0.001
# - No position accumulation across cycles
```

**Test 4: Leverage Control**
```bash
# After running 1 cycle, verify leverage settings
python -c "
import asyncio
from DN_pair_eth_sol_nado import DNPairBot
from decimal import Decimal

async def check():
    bot = DNPairBot(target_notional=Decimal('100'), iterations=1)
    await bot.initialize_clients()

    eth_lev = await bot.eth_client.verify_leverage()
    sol_lev = await bot.sol_client.verify_leverage()

    print(f'ETH Leverage: {eth_lev[\"account_leverage\"]}x (mode: {eth_lev[\"margin_mode\"]})')
    print(f'SOL Leverage: {sol_lev[\"account_leverage\"]}x (mode: {sol_lev[\"margin_mode\"]})')

    # Expected: Both ~5x leverage (isolated)
    await bot.cleanup()

asyncio.run(check())
"
```

**Test 5: API Delay Resilience**
```bash
# Run 5 cycles with sleep time to allow API to catch up
python DN_pair_eth_sol_nado.py --size 100 --iter 5 --sleep 10 --use-ioc

# Verify:
# - No "UNWIND FAILED" errors
# - All cycles complete successfully
# - Final positions: abs(pos) < 0.001
```

### 4.2 Manual Verification Steps

**Step 1**: Before running bot
```bash
# Check starting positions
python -c "
import asyncio
from DN_pair_eth_sol_nado import DNPairBot
from decimal import Decimal

async def check():
    bot = DNPairBot(target_notional=Decimal('100'), iterations=1)
    await bot.initialize_clients()
    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()
    print(f'Starting positions - ETH: {eth_pos}, SOL: {sol_pos}')
    await bot.cleanup()

asyncio.run(check())
"
```

**Step 2**: After running bot
```bash
# Check final positions
python -c "
import asyncio
from DN_pair_eth_sol_nado import DNPairBot
from decimal import Decimal

async def check():
    bot = DNPairBot(target_notional=Decimal('100'), iterations=1)
    await bot.initialize_clients()
    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()
    print(f'Final positions - ETH: {eth_pos}, SOL: {sol_pos}')
    await bot.cleanup()

asyncio.run(check())
"

# Expected: abs(eth_pos) < 0.001 and abs(sol_pos) < 0.001
```

### 4.3 Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Position Accumulation | 0.000 (abs(pos) < 0.001) | API query after each cycle |
| Internal Tracking Reset | Every cycle | Log for "[UNWIND] Reset internal tracking" |
| API Delay Resilience | 100% UNWIND success | Log analysis for UNWIND errors |
| Leverage Consistency | ~5x for both ETH/SOL | verify_leverage() query |
| Margin Mode | Isolated (not cross) | verify_leverage() query |
| Cycle Completion Rate | >95% (5/5 cycles) | Log analysis for cycle completion |

---

## 5. Verification Steps

### 5.1 Pre-Deployment Checklist

- [ ] **Code Changes Applied**:
  - [ ] `nado.py:553` - Changed to `isolated=True` with `isolated_margin` calculation
  - [ ] `nado.py:469` - Added `isolated_margin` calculation to `place_open_order`
  - [ ] `nado.py:694` - Added `isolated_margin` calculation to `place_close_order`
  - [ ] `nado.py` - Added `verify_leverage()` method
  - [ ] `DN_pair_eth_sol_nado.py:1567` - Added internal tracking reset after UNWIND_COMPLETE
  - [ ] `DN_pair_eth_sol_nado.py:1390` - Enhanced BUILD fallback with internal tracking
  - [ ] `DN_pair_eth_sol_nado.py:1812` - Added leverage verification call

- [ ] **Testing Completed**:
  - [ ] Test 1: Isolated margin verification (1 cycle)
  - [ ] Test 2: Position tracking accuracy (3 cycles)
  - [ ] Test 3: Internal tracking reset (5 cycles)
  - [ ] Test 4: Leverage control verification
  - [ ] Test 5: API delay resilience (5 cycles with sleep)

- [ ] **Manual Verification**:
  - [ ] Starting positions verified (abs(pos) < 0.001)
  - [ ] Final positions verified (abs(pos) < 0.001)
  - [ ] CSV logs show complete entry/exit for all cycles
  - [ ] No UNWIND failures in logs
  - [ ] Leverage verified at ~5x for both ETH/SOL
  - [ ] Margin mode confirmed as "isolated"

### 5.2 Post-Deployment Monitoring

**Monitor for First 10 Cycles**:
```bash
# Run bot with monitoring
tail -f logs/DN_pair_eth_sol_nado_log.txt | grep -E "(UNWIND|POSITION|LEVERAGE|ISOLATED|Reset internal)"

# Key indicators to watch:
# - "[BUILD_VERIFY] API POSITION DELAY" - Should see internal tracking updates
# - "[UNWIND] Reset internal tracking" - Should see EVERY cycle
# - "[INIT] Initial leverage - Account: X.XXx" - Should be ~5x
# - "[PHASE] UNWIND_COMPLETE -> IDLE" - Should see this every cycle
# - "[SAFETY] Cycle X FAILED" - Should NOT see this
```

**Position Verification Script**:
```bash
# Create script: verify_positions.py
import asyncio
from decimal import Decimal

async def verify():
    from DN_pair_eth_sol_nado import DNPairBot

    bot = DNPairBot(target_notional=Decimal('100'), iterations=1)
    await bot.initialize_clients()

    eth_pos = await bot.eth_client.get_account_positions()
    sol_pos = await bot.sol_client.get_account_positions()

    # Verify leverage
    eth_lev = await bot.eth_client.verify_leverage()
    sol_lev = await bot.sol_client.verify_leverage()

    print(f"\n{'='*60}")
    print(f"POSITION AND LEVERAGE VERIFICATION")
    print(f"{'='*60}")
    print(f"ETH Position: {eth_pos}")
    print(f"SOL Position: {sol_pos}")
    print(f"ETH Internal: {bot._internal_positions['ETH']}")
    print(f"SOL Internal: {bot._internal_positions['SOL']}")
    print(f"ETH Leverage: {eth_lev['account_leverage']:.2f}x ({eth_lev['margin_mode']})")
    print(f"SOL Leverage: {sol_lev['account_leverage']:.2f}x ({sol_lev['margin_mode']})")

    tolerance = Decimal("0.001")
    if abs(eth_pos) > tolerance or abs(sol_pos) > tolerance:
        print(f"\n⚠️  WARNING: Position accumulation detected!")
        print(f"   ETH: {eth_pos} (tolerance: ±{tolerance})")
        print(f"   SOL: {sol_pos} (tolerance: ±{tolerance})")
        print(f"\n   MANUAL INTERVENTION REQUIRED")
    else:
        print(f"\n✓ Positions clean (abs(pos) < {tolerance})")

    await bot.cleanup()

asyncio.run(verify())
```

---

## 6. Rollback Plan

### 6.1 Rollback Triggers

**Immediate Rollback If**:
- Position accumulation > 0.01 for either ETH or SOL
- UNWIND failure rate > 20% (1 failure in 5 cycles)
- Leverage not ~5x (isolated margin not working)
- Unexpected liquidation or margin call
- Isolated margin positions can't be closed due to insufficient collateral

### 6.2 Rollback Procedure

**Step 1**: Immediate Position Closure
```bash
# Manual position closure via Nado UI or API
# Use verify_positions.py to confirm closure
python verify_positions.py
```

**Step 2**: Revert Code Changes
```bash
# Revert to commit before changes
git log --oneline -10  # Identify pre-fix commit
git reset --hard <commit-hash>

# Specifically revert these changes:
# - nado.py:553 (isolated=True → isolated=False, remove isolated_margin)
# - nado.py:469 (remove isolated_margin calculation)
# - nado.py:694 (remove isolated_margin calculation)
# - nado.py verify_leverage() method (remove)
# - DN_pair_eth_sol_nado.py internal tracking reset (remove)
# - DN_pair_eth_sol_nado.py BUILD fallback enhancement (revert)
```

**Step 3**: Restore Previous Configuration
```bash
# Verify reverted changes
grep -n "isolated=" hedge/exchanges/nado.py
# Should show: isolated=False (line 553)

# No isolated_margin calculations
# No verify_leverage() method
# No internal tracking reset
```

**Step 4**: Post-Rollback Verification
```bash
# Run single cycle test
python DN_pair_eth_sol_nado.py --size 100 --iter 1 --use-ioc

# Verify positions close (even with accumulation issue)
python verify_positions.py
```

### 6.3 Recovery from Failed Rollback

**If Rollback Fails** (positions still don't close):
```bash
# Emergency manual closure
# 1. Log into Nado exchange UI
# 2. Manually close all positions
# 3. Verify closure via API
python verify_positions.py

# 4. Investigate root cause
# - Check Nado exchange status
# - Verify API credentials
# - Review error logs
# - Check if isolated margin caused collateral lock
```

---

## 7. Implementation Dependencies

### 7.1 Nado SDK Capabilities (VERIFIED)

**Confirmed Capabilities**:
1. **Isolated Margin**: Fully supported via `isolated=True` parameter
2. **Isolated Margin Amount**: Controlled via `isolated_margin` parameter (int)
3. **Leverage Calculation**: `leverage = notional_value / isolated_margin`
4. **MarginManager**: Provides leverage calculation and verification

**Confirmed Limitations**:
1. **No `set_leverage()` Method**: Leverage is controlled per-order, not account-level
   - **Solution**: Calculate `isolated_margin` for each order based on desired leverage
   - **Formula**: `isolated_margin = (quantity * price) / leverage`

2. **Position Update Delay**: 20+ second delay is inherent to testnet
   - **Solution**: Hybrid tracking (internal + API) + internal tracking reset

3. **Leverage Verification**: Must use `MarginManager` to query actual leverage
   - **Solution**: Added `verify_leverage()` method using `MarginManager`

### 7.2 External Dependencies

**Required**:
- Nado SDK (current version with `isolated_margin` support)
- Python 3.11+
- Decimal for precision arithmetic
- Asyncio for concurrent operations

**Optional**:
- WebSocket for real-time data (already implemented)
- Funding rate API (for PNL accuracy)

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Isolated margin requires more collateral | High | Medium | Pre-deployment collateral analysis, start with smaller notional |
| Internal tracking reset fails | Low | High | Test with 5 cycles, verify accumulation is fixed |
| Leverage calculation errors | Low | Medium | Verify via `verify_leverage()` after each order |
| Margin mode switch breaks existing positions | Medium | High | Start with empty account, close all positions before deploy |
| API delay worsens | Low | High | Hybrid tracking already handles this |

### 8.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Position accumulation continues | Low | High | Pre-deployment testing (5 cycles) with internal reset |
| Liquidation due to insufficient isolated margin | Medium | Critical | Start with conservative leverage (5x) and small notional |
| Rollback fails | Low | Medium | Manual closure procedure documented |
| Bot stops unexpectedly | Medium | Low | Safety checks stop bot on failure |

---

## 9. Success Criteria Summary

### Must Have (Blockers if not met)
1. ✅ Position accumulation < 0.001 after each cycle
2. ✅ UNWIND success rate > 95%
3. ✅ Isolated margin mode confirmed via `verify_leverage()`
4. ✅ Leverage verified at ~5x for both ETH and SOL
5. ✅ Internal tracking reset occurs every cycle

### Should Have (Warnings if not met)
1. API delay handling works (BUILD fallback updates internal tracking)
2. Internal tracking accuracy > 99%
3. No safety stops in 10 cycles

### Nice to Have (Future enhancements)
1. WebSocket position updates (real-time)
2. Automatic leverage adjustment based on volatility
3. Position reconciliation dashboard

---

## 10. Deployment Timeline

### Phase 1: Code Changes (45 minutes)
- [ ] Apply isolated margin changes to all three order methods
- [ ] Add `isolated_margin` calculation (5x leverage)
- [ ] Add `verify_leverage()` method
- [ ] Add internal tracking reset after UNWIND_COMPLETE
- [ ] Enhance BUILD fallback with internal tracking update
- [ ] Add leverage verification initialization call

### Phase 2: Testing (1.5 hours)
- [ ] Test 1: Single cycle isolated margin
- [ ] Test 2: Three cycles position tracking
- [ ] Test 3: Five cycles (verify internal reset works)
- [ ] Test 4: Leverage control verification
- [ ] Test 5: API delay resilience
- [ ] Manual position verification

### Phase 3: Deployment (15 minutes)
- [ ] Close all existing positions
- [ ] Pre-deployment checklist
- [ ] Deploy to production
- [ ] Post-deployment monitoring

### Phase 4: Validation (Ongoing)
- [ ] Monitor first 10 cycles
- [ ] Verify no position accumulation
- [ ] Confirm leverage settings via `verify_leverage()`
- [ ] Confirm internal tracking reset every cycle

---

## Appendix A: File Change Summary

### Modified Files
1. **hedge/exchanges/nado.py**
   - Line 553: Add `isolated=True` with `isolated_margin` calculation (IOC orders)
   - Line 469: Add `isolated_margin` calculation (POST_ONLY open orders)
   - Line 694: Add `isolated_margin` calculation (POST_ONLY close orders)
   - Add `verify_leverage()` method after `__init__`

2. **hedge/DN_pair_eth_sol_nado.py**
   - Line 1567: Add internal tracking reset after UNWIND_COMPLETE
   - Line 1390: Enhance BUILD fallback with internal tracking update
   - Line 1812: Add leverage verification initialization call

### No Changes Required
- UNWIND logic (already uses internal tracking for decisions)
- Position tracking infrastructure (already implemented)
- Phase state machine (already robust)

---

## Appendix B: Command Reference

### Testing Commands
```bash
# Single cycle test
python DN_pair_eth_sol_nado.py --size 100 --iter 1 --use-ioc

# Multi-cycle test
python DN_pair_eth_sol_nado.py --size 100 --iter 5 --use-ioc

# With sleep (API delay test)
python DN_pair_eth_sol_nado.py --size 100 --iter 5 --sleep 10 --use-ioc

# Position verification
python verify_positions.py

# Leverage verification
python -c "
import asyncio
from DN_pair_eth_sol_nado import DNPairBot
from decimal import Decimal

async def check():
    bot = DNPairBot(target_notional=Decimal('100'), iterations=1)
    await bot.initialize_clients()
    eth_lev = await bot.eth_client.verify_leverage()
    sol_lev = await bot.sol_client.verify_leverage()
    print(f'ETH: {eth_lev[\"account_leverage\"]:.2f}x ({eth_lev[\"margin_mode\"]})')
    print(f'SOL: {sol_lev[\"account_leverage\"]:.2f}x ({sol_lev[\"margin_mode\"]})')
    await bot.cleanup()

asyncio.run(check())
"
```

### Log Analysis Commands
```bash
# Check for UNWIND failures
grep -i "unwind.*failed" logs/DN_pair_eth_sol_nado_log.txt

# Check internal tracking reset
grep "Reset internal tracking" logs/DN_pair_eth_sol_nado_log.txt

# Check leverage verification
grep "Leverage verification" logs/DN_pair_eth_sol_nado_log.txt

# Check phase transitions
grep "\[PHASE\]" logs/DN_pair_eth_sol_nado_log.txt

# Check position accumulation
grep "POSITION.*BEFORE\|POSITION.*AFTER" logs/DN_pair_eth_sol_nado_log.txt
```

---

## Appendix C: Research Summary

### Nado SDK Capabilities (VERIFIED)

1. **`build_appendix()` Signature**:
```python
def build_appendix(
    order_type: OrderType,
    isolated: bool = False,
    reduce_only: bool = False,
    trigger_type: Optional[OrderAppendixTriggerType] = None,
    isolated_margin: Optional[int] = None,  # <-- KEY PARAMETER
    twap_times: Optional[int] = None,
    twap_slippage_frac: Optional[float] = None,
    _version: Optional[int] = 1
) -> int
```

2. **Leverage Control**:
   - NO `set_leverage()` method exists in Nado SDK
   - Leverage is controlled per-order via `isolated_margin` parameter
   - Formula: `leverage = (quantity * price) / isolated_margin`
   - For 5x leverage: `isolated_margin = (quantity * price) / 5`

3. **Leverage Verification**:
```python
from nado_protocol.utils.margin_manager import MarginManager

margin_manager = MarginManager.from_client(client)
summary = margin_manager.calculate_account_summary()
print(f"Account leverage: {summary.account_leverage}x")

isolated_positions = margin_manager.calculate_isolated_position_metrics(...)
for pos in isolated_positions.isolated_positions:
    print(f"{pos.ticker}: {pos.leverage}x")
```

4. **Build Fallback Variables**:
   - `eth_direction` and `sol_direction` ARE available at line 1390
   - They are parameters of `execute_build_cycle()` method
   - Can be used to update internal tracking correctly

---

## Appendix D: Isolated Margin Analysis

### Margin Mode Comparison

| Aspect | Cross Margin | Isolated Margin |
|--------|-------------|-----------------|
| Collateral | Shared across positions | Dedicated per position |
| Leverage | Account-level | Position-level (via `isolated_margin`) |
| Liquidation Risk | Lower (shared collateral) | Higher (dedicated collateral) |
| Capital Efficiency | Higher | Lower |
| Position Isolation | No | Yes |
| Recommended For | Portfolio strategies | Single-asset strategies |

### Isolated Margin Requirements

**Formula**: `isolated_margin = (quantity * price) / leverage`

**Example**:
- Target notional: $100
- Leverage: 5x
- Required margin: $100 / 5 = $20

**Verification**:
```python
# After placing order
leverage_info = await client.verify_leverage()
assert leverage_info['eth_leverage'] == 5.0  # Verify 5x leverage
```

### Risk Considerations

1. **Insufficient Collateral**:
   - Isolated margin requires more collateral than cross
   - Mitigation: Start with small notional ($50-$100)

2. **Margin Calculation Errors**:
   - Incorrect `isolated_margin` can cause unexpected leverage
   - Mitigation: Verify leverage after first order via `verify_leverage()`

3. **Position Closure Issues**:
   - Isolated positions may not close if margin insufficient
   - Mitigation: Monitor UNWIND phase closely, have manual closure ready

---

## Appendix E: Contact and Escalation

### Technical Contacts
- **Nado Documentation**: https://nado_protocol.readthedocs.io/
- **SDK Issues**: Check Nado GitHub issues
- **Emergency**: Manual position closure via exchange UI

### Escalation Path
1. **Level 1**: Verify logs, run diagnostic scripts
2. **Level 2**: Manual position closure, investigate root cause
3. **Level 3**: Contact Nado support for API/SDK issues
4. **Level 4**: Emergency rollback to previous version

---

**Document Version**: 2.0 (REVISED)
**Last Updated**: 2026-01-31
**Status**: Ready for Implementation (All Research Complete)

**Key Changes from v1.0**:
1. ✅ Verified Nado SDK capabilities (isolated_margin parameter exists)
2. ✅ Removed `set_leverage()` method (not supported by SDK)
3. ✅ Added internal tracking reset after UNWIND_COMPLETE
4. ✅ Added `verify_leverage()` method using MarginManager
5. ✅ Confirmed `eth_direction`/`sol_direction` available at BUILD fallback
6. ✅ Added isolated margin impact analysis
7. ✅ All success criteria are now verifiable
