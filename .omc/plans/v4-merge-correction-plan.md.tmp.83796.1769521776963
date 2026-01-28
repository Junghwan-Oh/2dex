# V4 BBO Routing Merge Correction Plan (Final)

**Created**: 2026-01-27
**Status**: Critic-Approved (iteration 2)
**Iteration**: 2/5

---

## Context

### Problem Statement

Previous implementation created a new file `DN_alternate_backpack_grvt_current.py` instead of modifying the existing `DN_alternate_backpack_grvt.py`. This resulted in:
- **Loss of all safety features** (MAX_POSITION, MAX_DAILY_LOSS, pre-trade checks, emergency unwind)
- **Plan specification ambiguity** - target file didn't exist, no explicit creation instruction
- **Safety regression** - new file can expose unlimited position sizes and losses
- **Current production code uses invalid V3 parameters** (max_tick_offset, max_fill_duration)

### Root Cause

The plan specified `DN_alternate_backpack_grvt_current.py` as the target (line 20 of grvt-bbo-routing-integration.md), but this file:
1. Did not exist before implementation
2. No instruction to create it vs. modify existing file
3. No instruction about preserving safety features from existing `DN_alternate_backpack_grvt.py`

### Correct Approach

**Start with**: `DN_alternate_backpack_grvt.py` (existing, with all safety features)
**Add**: V4 BBO routing features from `DN_alternate_backpack_grvt_current.py`
**Remove**: Invalid V3 parameters (max_tick_offset, max_fill_duration)
**Result**: Enhanced `DN_alternate_backpack_grvt.py` (V4 + safety features)

---

## CRITICAL ISSUE: Current Code Uses Invalid V3 Parameters

### Location: Lines 858-859, 1053-1054 in `DN_alternate_backpack_grvt.py`

```python
# CURRENT (WRONG - uses V3 params):
result = await self.hedge_client.place_iterative_market_order(
    contract_id=self.hedge_contract_id,
    target_quantity=quantity,
    side=order_side,
    max_iterations=10,
    max_tick_offset=2,    # V3 PARAM - INVALID IN V4 - REMOVE
    max_fill_duration=30  # V3 PARAM - INVALID IN V4 - REMOVE
)
```

**V4 Signature (CORRECT)**:
```python
# From grvt.py:1218-1226
async def place_iterative_market_order(
    self,
    contract_id: str,
    target_quantity: Decimal,
    side: str,
    max_iterations: int = 20,
    max_slippage_bps: int = 5,
    tick_size: int = 10,  # INT, not Decimal
) -> dict:
```

**FIX NEEDED**: Remove `max_tick_offset` and `max_fill_duration`, use `tick_size=10`.

---

## Full Code Structure Documentation

### Important: Two Separate Conditional Paths

The code has TWO mutually exclusive code paths controlled by `first_build_completed`:

| Condition | Path Used | When |
|-----------|-----------|------|
| `self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and self.first_build_completed` | **Path A**: Use iterative order directly | First BUILD completed |
| `self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and not self.first_build_completed` | **Path B**: Try POST_ONLY first, then MARKET fallback | First BUILD only |

**Path A** (lines 1046-1078): Iterative order directly with V4 signature
**Path B** (lines 1082-1200+): POST_ONLY first to save fees, MARKET fallback if needed

### Key Preservation Points

1. **POST_ONLY logic must be preserved** (lines 890-981 for CLOSE, 1089-1200+ for OPEN)
2. **MARKET fallback must be preserved** (lines 983-1035 for CLOSE)
3. **first_build_completed conditional checks** must be preserved (lines 1046, 1082)
4. **all safety features** (MAX_POSITION, MAX_DAILY_LOSS, etc.) must be preserved

---

## Source Materials

### 1. V4 Implementation Already Verified

The V4 BBO routing implementation in `grvt.py` is **solid and complete**:
- ✅ Commit 3d923c1 - All V4 phases implemented
- ✅ Helper functions: `calculate_timeout()`, `extract_filled_quantity()`
- ✅ Order book analysis: `analyze_order_book_depth()`, `find_hedge_price_with_liquidity()`
- ✅ Core routing: `place_iterative_market_order()` (lines 1218-1433)

**Key V4 Files**:
- [exchanges/grvt.py:18-47](perp-dex-tools-original/hedge/exchanges/grvt.py#L18-L47) - `calculate_timeout()`
- [exchanges/grvt.py:50-88](perp-dex-tools-original/hedge/exchanges/grvt.py#L50-L88) - `extract_filled_quantity()`
- [exchanges/grvt.py:751-812](perp-dex-tools-original/hedge/exchanges/grvt.py#L751-L812) - `analyze_order_book_depth()`
- [exchanges/grvt.py:1218-1226](perp-dex-tools-original/hedge/exchanges/grvt.py#L1218-L1226) - `place_iterative_market_order()` signature

### 2. DN File Status

| File | Status | Issues |
|------|--------|--------|
| `DN_alternate_backpack_grvt.py` | ✅ Production-ready, tracked in git | Uses invalid V3 params (lines 858-859, 1053-1054) |
| `DN_alternate_backpack_grvt_current.py` | ❌ Untracked, created today | Missing all safety features |

### 3. Reference Plans

- [grvt-bbo-routing-integration.md](.omc/plans/grvt-bbo-routing-integration.md) - Original V4 integration plan
- [grvt-smart-routing-plan-v4.md](.serena/memories/grvt-smart-routing-plan-v4.md) - V4 implementation plan

---

## Safety Features Preservation Matrix

### Critical Safety Features (MUST PRESERVE)

| Feature | Lines in Original | Purpose | Risk if Removed |
|---------|-------------------|---------|-----------------|
| **MAX_POSITION** | 141 | Hard cap: 5 ETH total position | Unlimited exposure |
| **MAX_DAILY_LOSS** | 142 | Daily loss limit: $5 USD | Unlimited losses |
| **daily_pnl tracking** | 143 | Cumulative daily PnL | No circuit breaker |
| **_pre_trade_check()** | 1786-1828 | Validates before every order | No validation |
| **_emergency_unwind_primary_position()** | 1912-1966 | Exit when hedge fails | Dangerous unhedged exposure |
| **NET_DELTA_WARNING_THRESHOLD** | 637 | 1% drift warning | Silent hedge drift |
| **NET_DELTA_CRITICAL_THRESHOLD** | 638 | 2% drift critical alert | No awareness |
| **first_build_completed** | 130, 1046, 1082 | Cold start workaround | First order failures |
| **hedge_post_only parameter** | 101, 113 | Save 0.05% taker fee | Higher costs |

---

## Merge Strategy

### Approach: Additive Enhancement + V3 Param Removal + Full Context

**Workflow**:
```
1. Base: DN_alternate_backpack_grvt.py (safe, production-tested)
2. Add: V4 imports (line 27)
3. Add: check_grvt_liquidity() method (after print_trade_summary)
4. Remove: Invalid V3 params from BOTH CLOSE and OPEN logic
5. Verify: All safety features still present and functional
```

---

## Detailed TODOs

### Phase 1: Preparation (Read-Only)

**Objective**: Understand codebase structure and V4 signatures

**Task 1.1: Read V4 function signatures from grvt.py**
- [x] Read `grvt.py:18-47` - `calculate_timeout()`
- [x] Read `grvt.py:50-88` - `extract_filled_quantity()`
- [x] Read `grvt.py:1218-1226` - `place_iterative_market_order()` signature
- [x] Confirm: `tick_size=10` is INT (10 cents = $0.10)
- [x] Confirm: NO `max_tick_offset` or `max_fill_duration` in V4

**Task 1.2: Read safety features from DN_alternate_backpack_grvt.py**
- [x] Read lines 141-143 (MAX_POSITION, MAX_DAILY_LOSS, daily_pnl)
- [x] Read lines 1786-1828 (_pre_trade_check method)
- [x] Read lines 1912-1966 (_emergency_unwind_primary_position)
- [x] Read lines 637-652 (NET_DELTA thresholds)
- [x] Read lines 101, 113 (hedge_post_only parameter)
- [x] Read lines 1046, 1082 (first_build_completed conditional checks)

**Task 1.3: Read full code structure**
- [x] Read lines 850-1035: CLOSE logic full block
- [x] Read lines 1037-1200+: OPEN logic full block
- [x] Understand two separate conditional paths
- [x] Identify which sections must be preserved

**Acceptance Criteria**:
- All V4 signatures documented
- All safety feature locations documented
- Full code structure understood
- Clear modification points identified

---

### Phase 2: Add V4 Imports

**Objective**: Import V4 helper functions

**File**: [DN_alternate_backpack_grvt.py:27](perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py#L27)

**Current Code**:
```python
from exchanges.grvt import GrvtClient
```

**New Code**:
```python
from exchanges.grvt import GrvtClient, extract_filled_quantity, calculate_timeout
```

**Verification**:
```bash
cd perp-dex-tools-original/hedge
python -c "from exchanges.grvt import extract_filled_quantity, calculate_timeout; print('V4 imports OK')"
```

**Acceptance Criteria**:
- Import syntax is valid
- Functions import successfully
- No conflicts with existing imports

---

### Phase 3: Add Liquidity Check Helper

**Objective**: Add `check_grvt_liquidity()` method to DN class

**Location**: After `print_trade_summary()` method (after line 293 in original)

**Add Method**:
```python
async def check_grvt_liquidity(
    self,
    client,
    target_quantity: Decimal,
    side: str
) -> dict:
    """Check if GRVT has sufficient liquidity at BBO.

    Returns:
        dict with format:
        {
            'sufficient_at_bbo': bool,
            'available_size': Decimal,
            'depth_levels_used': int,
            'fallback_needed': bool
        }
    """
    try:
        # Check if client has analyze_order_book_depth method
        if not hasattr(client, 'analyze_order_book_depth'):
            self.logger.warning("[LIQUIDITY_CHECK] Client missing analyze_order_book_depth method")
            return {
                'sufficient_at_bbo': False,
                'available_size': Decimal('0'),
                'depth_levels_used': 0,
                'fallback_needed': True
            }

        analysis = await client.analyze_order_book_depth(
            symbol=client.config.contract_id,
            side=side,
            depth_limit=50
        )

        bbo_size = analysis['top_size']
        cumulative = analysis['cumulative']

        return {
            'sufficient_at_bbo': bbo_size >= target_quantity,
            'available_size': cumulative,
            'depth_levels_used': analysis['total_levels_analyzed'],
            'fallback_needed': cumulative < target_quantity
        }
    except Exception as e:
        self.logger.warning(f"[LIQUIDITY_CHECK] Failed: {e}")
        return {
            'sufficient_at_bbo': False,
            'available_size': Decimal('0'),
            'depth_levels_used': 0,
            'fallback_needed': True
        }
```

**Acceptance Criteria**:
- Method added at correct location
- Returns dict format consistently
- Has hasattr guard for method availability
- Handles exceptions gracefully

---

### Phase 4: Remove Invalid V3 Parameters from CLOSE Logic

**Objective**: Remove V3 params from the CLOSE iterative order section

**Location**: Lines 851-883 (within the CLOSE section of place_hedge_order)

**Full Code to Modify**:

```python
# CURRENT CODE (Lines 850-883):
if order_type == "CLOSE":
    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2"):
        self.logger.info(f"[CLOSE] Using ITERATIVE market order for {quantity} ETH")
        result = await self.hedge_client.place_iterative_market_order(
            contract_id=self.hedge_contract_id,
            target_quantity=quantity,
            side=order_side,
            max_iterations=10,   # Line 857
            max_tick_offset=2,    # Line 858 - REMOVE THIS LINE
            max_fill_duration=30  # Line 859 - REMOVE THIS LINE
        )

        if result['success']:
            self.logger.info(
                f"[CLOSE] [ITERATIVE] Filled {result['total_filled']} @ ${result['average_price']:.2f} "
                f"({result['iterations']} iterations)"
            )
            self.log_trade_to_csv(
                exchange=self.hedge_exchange.upper(),
                side=side,
                price=str(result['average_price']),
                quantity=str(result['total_filled']),
                order_type="hedge_close_iterative",
                mode="iterative_market"
            )
            self.hedge_order_filled = True
            self.order_execution_complete = True
            self.last_hedge_fill_price = result['average_price']
            return True
        else:
            self.logger.error(f"[CLOSE] Iterative failed: {result.get('reason', 'unknown')}")
            self.hedge_order_filled = False
            self.order_execution_complete = False
            return False
    else:
        # POST_ONLY fallback (Lines 884-1035) - DO NOT MODIFY THIS ELSE BLOCK
        # ... entire POST_ONLY and MARKET fallback logic ...
```

**Replace With**:

```python
# NEW CODE (Lines 850-883):
if order_type == "CLOSE":
    if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2"):
        self.logger.info(f"[CLOSE] Using ITERATIVE market order for {quantity} ETH")
        result = await self.hedge_client.place_iterative_market_order(
            contract_id=self.hedge_contract_id,
            target_quantity=quantity,
            side=order_side,
            max_iterations=10,
            tick_size=10  # INT: 10 cents = $0.10 - FIXED V4 SIGNATURE
        )

        if result.get('success', True):  # FIXED: Use .get() for safety
            # Use extract_filled_quantity for safe parsing
            filled = extract_filled_quantity(result)
            avg_price = result.get('average_price', None) or result.get('traded_size', result.get('size', {}))

            self.logger.info(
                f"[CLOSE] [GRVT] [ITERATIVE_FILL]: "
                f"{filled} @ ~{avg_price}"
            )

            self.log_trade_to_csv(
                exchange=self.hedge_exchange.upper(),
                side=side,
                price=str(avg_price) if avg_price else "N/A",
                quantity=str(filled),
                order_type="hedge_close_iterative",
                mode="iterative_routing"
            )

            self.hedge_order_filled = True
            self.order_execution_complete = True
            self.last_hedge_fill_price = avg_price
            return True
        else:
            error_msg = result.get('error', 'unknown') or result.get('reason', 'unknown')
            self.logger.error(f"[CLOSE] Iterative failed: {error_msg}")
            self.hedge_order_filled = False
            self.order_execution_complete = False
            return False
    else:
        # POST_ONLY fallback (Lines 884-1035) - DO NOT MODIFY THIS ELSE BLOCK
        # ... entire POST_ONLY and MARKET fallback logic ...
```

**CRITICAL CONSTRAINTS**:
1. ✅ PRESERVE the entire else block (lines 884-1035) - this contains POST_ONLY and MARKET fallback
2. ✅ Only modify lines 851-883 (the iterative order section)
3. ✅ DO NOT modify POST_ONLY logic (lines 889-981)
4. ✅ DO NOT modify MARKET fallback (lines 983-1035)

**Verification**:
```bash
cd perp-dex-tools-original/hedge
python -m py_compile DN_alternate_backpack_grvt.py
# Should compile without errors
grep -n "max_tick_offset" DN_alternate_backpack_grvt.py
# Should return NO RESULTS
```

**Acceptance Criteria**:
- V3 params removed from CLOSE logic
- extract_filled_quantity() used for safe parsing
- POST_ONLY fallback preserved (lines 884-1035)
- MARKET fallback preserved
- Code compiles without errors

---

### Phase 5: Remove Invalid V3 Parameters from OPEN Logic

**Objective**: Remove V3 params from the OPEN logic's two conditional paths

**Location**: Lines 1037-1200+ (OPEN section of place_hedge_order)

**Path A: First Build Completed (Lines 1046-1078)**

**Current Code**:
```python
# Lines 1045-1078:
if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and self.first_build_completed:
    self.logger.info(f"[OPEN] Using ITERATIVE market order for {quantity} ETH")
    result = await self.hedge_client.place_iterative_market_order(
        contract_id=self.hedge_contract_id,
        target_quantity=quantity,
        side=order_side,
        max_iterations=10,   # Line 1052
        max_tick_offset=2,    # Line 1053 - REMOVE THIS LINE
        max_fill_duration=30  # Line 1054 - REMOVE THIS LINE
    )

    if result['success']:
        self.logger.info(
            f"[OPEN] [ITERATIVE] Filled {result['total_filled']} @ ${result['average_price']:.2f} "
            f"({result['iterations']} iterations)"
        )
        self.log_trade_to_csv(
            exchange=self.hedge_exchange.upper(),
            side=side,
            price=str(result['average_price']),
            quantity=str(result['total_filled']),
            order_type="hedge_open_iterative",
            mode="iterative_market"
        )
        self.hedge_order_filled = True
        self.order_execution_complete = True
        self.last_hedge_fill_price = result['average_price']
        return True
    else:
        self.logger.error(f"[OPEN] Iterative failed: {result.get('reason', 'unknown')}")
        self.hedge_order_filled = False
        self.order_execution_complete = False
        return False
```

**Replace With**:
```python
# Lines 1045-1078:
if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and self.first_build_completed:
    self.logger.info(f"[OPEN] Using ITERATIVE market order for {quantity} ETH")
    result = await self.hedge_client.place_iterative_market_order(
        contract_id=self.hedge_contract_id,
        target_quantity=quantity,
        side=order_side,
        max_iterations=10,
        tick_size=10  # INT: 10 cents = $0.10 - FIXED V4 SIGNATURE
    )

    if result.get('success', True):  # FIXED: Use .get() for safety
        # Use extract_filled_quantity for safe parsing
        filled = extract_filled_quantity(result)
        avg_price = result.get('average_price', None) or result.get('traded_size', result.get('size', {}))

        self.logger.info(
            f"[OPEN] [GRVT] [ITERATIVE_FILL]: "
            f"{filled} @ ~{avg_price}"
        )

        self.log_trade_to_csv(
            exchange=self.hedge_exchange.upper(),
            side=side,
            price=str(avg_price) if avg_price else "N/A",
            quantity=str(filled),
            order_type="hedge_open_iterative",
            mode="iterative_routing"
        )

        self.hedge_order_filled = True
        self.order_execution_complete = True
        self.last_hedge_fill_price = avg_price
        return True
    else:
        error_msg = result.get('error', 'unknown') or result.get('reason', 'unknown')
        self.logger.error(f"[OPEN] Iterative failed: {error_msg}")
        self.hedge_order_filled = False
        self.order_execution_complete = False
        return False
```

---

**Path B: First Build NOT Completed (Lines 1082-1200+)**

**Current Code**:
```python
# Lines 1080-1200+:
if self.hedge_exchange.lower() == "grvt" and quantity > Decimal("0.2") and not self.first_build_completed:
    self.logger.info(
        f"[OPEN] [FIRST BUILD] Using POST_ONLY first to avoid cold start issue"
    )

    hedge_filled = False

    if self.hedge_post_only and self.hedge_exchange.lower() == "grvt":
        try:
            # Get BBO for POST_ONLY pricing
            best_bid, best_ask = await self.hedge_client.fetch_bbo_prices(
                self.hedge_contract_id
            )

            # Calculate POST_ONLY price (1 tick inside spread)
            if order_side == "buy":
                hedge_post_only_price = best_ask - self.hedge_tick_size
            else:  # sell
                hedge_post_only_price = best_bid + self.hedge_tick_size

            hedge_post_only_price = self.hedge_client.round_to_tick(hedge_post_only_price)

            self.logger.info(
                f"[OPEN] [FIRST BUILD] Attempting POST_ONLY @ {hedge_post_only_price} "
                f"(side: {order_side}, fee: 0%)"
            )

            # Try POST_ONLY with 3 second timeout
            hedge_result = await asyncio.wait_for(
                self.hedge_client.place_post_only_order(
                    contract_id=self.hedge_contract_id,
                    quantity=quantity,
                    price=hedge_post_only_price,
                    side=order_side
                ),
                timeout=3.0
            )

            if hedge_result.status == "FILLED":
                hedge_filled = True

                self.logger.info(
                    f"[OPEN] [FIRST BUILD] [POST_ONLY FILLED]: {quantity} @ {hedge_result.price} "
                    f"(0% fee saved)"
                )

                # Update local position
                if hasattr(self.hedge_client, '_local_position'):
                    if order_side == "buy":
                        self.hedge_client._local_position += quantity
                    else:
                        self.hedge_client._local_position -= quantity

                # Set flags
                self.hedge_order_filled = True
                self.order_execution_complete = True
                self.last_hedge_fill_price = hedge_result.price

                # Update tracking variables
                self.current_hedge_entry_order_type = "POST_ONLY"
                self.current_hedge_entry_fee_saved = True

                # Log to CSV
                self.log_trade_to_csv(
                    exchange=self.hedge_exchange.upper(),
                    side=side,
                    price=str(hedge_result.price),
                    quantity=str(quantity),
                    order_type="hedge_open_first_build_post_only",
                    mode="post_only_maker",
                )

                return True

            elif hedge_result.status == "OPEN":
                self.logger.warning(
                    f"[OPEN] [FIRST BUILD] POST_ONLY not filled, canceling and falling back"
                )
                await self.hedge_client.cancel_order(hedge_result.order_id)
            else:
                self.logger.warning(
                    f"[OPEN] [FIRST BUILD] POST_ONLY rejected, falling back to MARKET"
                )

        except asyncio.TimeoutError:
            self.logger.warning(f"[OPEN] [FIRST BUILD] POST_ONLY timeout, falling back to MARKET")
        except Exception as e:
            self.logger.warning(
                f"[OPEN] [FIRST BUILD] POST_ONLY failed: {e}, falling back to MARKET"
            )

    # MARKET fallback (Lines 1170+)
    # ... MARKET fallback logic ...
```

**NO CHANGES NEEDED** to Path B - it uses POST_ONLY, not iterative orders, so there are no V3 params to remove.

**CRITICAL CONSTRAINTS**:
1. ✅ PRESERVE the entire Path B section (lines 1082-1200+) - it uses POST_ONLY which is separate from iterative orders
2. ✅ DO NOT remove POST_ONLY logic (lines 1089-1170+)
3. ✅ DO NOT remove MARKET fallback logic
4. ✅ DO NOT remove the conditional check at line 1082

**Verification**:
```bash
cd perp-dex-tools-original/hedge
python -m py_compile DN_alternate_backpack_grvt.py
# Should compile without errors
grep -n "max_tick_offset\|max_fill_duration" DN_alternate_backpack_grvt.py
# Should return NO RESULTS
```

**Acceptance Criteria**:
- V3 params removed from Path A (lines 1046-1078)
- extract_filled_quantity() used for safe parsing
- Path B (lines 1082-1200+) completely preserved
- POST_ONLY logic preserved
- MARKET fallback preserved
- Code compiles without errors

---

### Phase 6: Verification & Testing

**Objective**: Ensure all features work correctly

**Task 6.1: Code verification**
- [ ] Run: `python -m py_compile perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py`
- [ ] Confirm NO syntax errors

**Task 6.2: Safety features verification**
- [ ] Search for `MAX_POSITION` - must exist (line 141)
- [ ] Search for `MAX_DAILY_LOSS` - must exist (line 142)
- [ ] Search for `_pre_trade_check` - method must exist (line 1786)
- [ ] Search for `_emergency_unwind_primary_position` - method must exist (line 1912)
- [ ] Search for `NET_DELTA_WARNING_THRESHOLD` - must exist (line 637)
- [ ] Search for `hedge_post_only` - parameter must exist (line 101)
- [ ] Search for `first_build_completed` - tracking must exist (lines 130, 1046, 1082)

**Task 6.3: V4 features verification**
- [ ] Search for `extract_filled_quantity` import - must exist (line 27)
- [ ] Search for `calculate_timeout` import - must exist (line 27)
- [ ] Search for `check_grvt_liquidity` - method must exist (line ~295)
- [ ] Search for `max_tick_offset` - must NOT exist
- [ ] Search for `max_fill_duration` - must NOT exist
- [ ] Search for `tick_size=10` - must exist in V4 calls

**Task 6.4: Integration verification**
- [ ] Confirm `_pre_trade_check()` is called before every DN cycle (line ~1834)
- [ ] Confirm `_emergency_unwind_primary_position()` is triggered on hedge failure (line ~1877)
- [ ] Confirm `first_build_completed` logic is preserved (lines 1046, 1082)
- [ ] Confirm POST_ONLY logic is preserved (lines 884-1035 for CLOSE, 1089-1170+ for OPEN)
- [ ] Confirm MARKET fallback is preserved

**Task 6.5: Import verification**
```bash
cd perp-dex-tools-original/hedge
python -c "
from exchanges.grvt import extract_filled_quantity, calculate_timeout
print('V4 imports OK')
print('calculate_timeout(0.5) =', calculate_timeout(Decimal('0.5')))
"
```

**Task 6.6: No invalid params check**
```bash
cd perp-dex-tools-original/hedge
grep -n "max_tick_offset\|max_fill_duration" DN_alternate_backpack_grvt.py
# Should return NO RESULTS
```

**Acceptance Criteria**:
- ✅ Python compiles without errors
- ✅ All safety features present
- ✅ All V4 features present
- ✅ NO invalid parameters (max_tick_offset, max_fill_duration)
- ✅ All integration points preserved

---

### Phase 7: Cleanup (Post-Merge)

**Objective**: Remove redundant files and update documentation

**Task 7.1**: Delete incorrect file
```bash
cd perp-dex-tools-original/hedge
rm DN_alternate_backpack_grvt_current.py
rm DN_alternate_backpack_grvt_current.py.tmp.*
```

**Task 7.2**: Update plan references
- [ ] Update `.omc/plans/grvt-bbo-routing-integration.md` line 20 to specify correct file
- [ ] Add note about safety features preservation

**Task 7.3**: Git commit (user responsibility)
```bash
cd perp-dex-tools-original/hedge
git add DN_alternate_backpack_grvt.py
git commit -m "feat(dn-bot): Add V4 BBO routing while preserving all safety features

- Import extract_filled_quantity, calculate_timeout from grvt.py
- Add check_grvt_liquidity() helper method
- Remove invalid V3 params (max_tick_offset, max_fill_duration) from CLOSE and OPEN logic
- Use V4 signature (tick_size=10) in iterative orders
- Use extract_filled_quantity() for safe result parsing
- Preserve ALL safety features: MAX_POSITION, MAX_DAILY_LOSS, _pre_trade_check
- Preserve emergency unwind mechanism
- Preserve net delta monitoring thresholds
- Preserve hedge_post_only logic
- Preserve first_build_completed tracking
- Preserve POST_ONLY fallback logic
- Preserve MARKET fallback logic

This merge corrects the previous approach which created a new file
and lost all safety features. V4 features are now integrated into the
production-tested safe baseline with full code context preservation."
```

---

## Definition of Done

- [ ] Python compiles without errors
- [ ] All safety features from original file preserved:
  - [ ] MAX_POSITION, MAX_DAILY_LOSS, daily_pnl tracking
  - [ ] _pre_trade_check() method and call
  - [ ] _emergency_unwind_primary_position() method and trigger
  - [ ] NET_DELTA_WARNING_THRESHOLD, NET_DELTA_CRITICAL_THRESHOLD
  - [ ] hedge_post_only parameter and logic
  - [ ] first_build_completed tracking
- [ ] All V4 features added:
  - [ ] extract_filled_quantity, calculate_timeout imports
  - [ ] check_grvt_liquidity() method
  - [ ] place_iterative_market_order() in OPEN Path A
- [ ] NO invalid parameters (max_tick_offset, max_fill_duration) - REMOVED
- [ ] POST_ONLY fallback preserved (CLOSE: lines 884-1035, OPEN: lines 1082-1200+)
- [ ] MARKET fallback preserved (CLOSE: lines 983-1035, OPEN: lines 1170+)
- [ ] All integration points verified
- [ ] Redundant file deleted

---

## Risk Mitigation

### High Risk Areas

| Area | Risk | Mitigation |
|------|------|------------|
| **Emergency unwind removal** | Dangerous unhedged exposure | Verify line ~1877 still calls _emergency_unwind |
| **Pre-trade check removal** | Orders without validation | Verify line ~1834 still calls _pre_trade_check |
| **MAX_POSITION removal** | Unlimited exposure | Verify lines 141-143 exist |
| **V3 param removal** | Code breaking | Verify V4 signature works (grvt.py already tested) |
| **POST_ONLY removal** | Higher fees | Verify lines 884-1035 preserved |
| **MARKET fallback removal** | No fallback if POST_ONLY fails | Verify lines 983-1035 preserved |

### Testing Checklist

Before production use:
- [ ] Run `--ticker ETH --size 0.1 --iter 1` (small test)
- [ ] Verify _pre_trade_check logs before first order
- [ ] Verify iterative routing logs appear for Path A
- [ ] Verify POST_ONLY logs appear for Path B (first build)
- [ ] Check all safety features in logs
- [ ] Verify MAX_POSITION prevents oversized orders
- [ ] Verify daily loss limit works
- [ ] Verify no max_tick_offset/max_fill_duration errors

---

## Success Criteria

1. ✅ DN_alternate_backpack_grvt.py has V4 BBO routing
2. ✅ ALL safety features preserved and functional
3. ✅ Code compiles without errors
4. ✅ Integration points verified
5. ✅ Invalid V3 params removed
6. ✅ Redundant file removed
7. ✅ No max_tick_offset or max_fill_duration in codebase
8. ✅ POST_ONLY fallback preserved
9. ✅ MARKET fallback preserved

---

## File References

**Primary Files**:
- [DN_alternate_backpack_grvt.py](perp-dex-tools-original/hedge/DN_alternate_backpack_grvt.py) - Target file (existing, safe)
- [DN_alternate_backpack_grvt_current.py](perp-dex-tools-original/hedge/DN_alternate_backpack_grvt_current.py) - Reference file (V4 features only, DELETE after merge)
- [grvt.py](perp-dex-tools-original/hedge/exchanges/grvt.py) - V4 implementation (verified, commit 3d923c1)

**Key Line Numbers**:
- Line 27: Imports
- Line 101: hedge_post_only parameter
- Line 113: self.hedge_post_only assignment
- Line 130: self.first_build_completed = False
- Lines 141-143: Safety limits (MAX_POSITION, etc.)
- Lines 850-1035: CLOSE logic with POST_ONLY and MARKET fallback
- Lines 1037-1200+: OPEN logic with two conditional paths
- Line 1046: first_build_completed = True path (Path A)
- Line 1082: first_build_completed = False path (Path B)
- Lines 1786-1828: _pre_trade_check() method
- Lines 1912-1966: _emergency_unwind() method
- Line 1834: Pre-trade check call
- Line 1877: Emergency unwind trigger

---

## Notes

- This plan prioritizes **safety preservation** over pure V4 integration
- V4 features are **additive** - they enhance without replacing
- Invalid V3 params are **removed** - they don't exist in V4
- All V4 routing has **fallback mechanisms** to simple market orders
- This approach maintains the **production-tested baseline** while adding intelligence
- Code modifications show **full context** to ensure safe implementation
- Two separate conditional paths are **clearly documented** and preserved
