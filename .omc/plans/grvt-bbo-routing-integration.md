# GRVT BBO Routing Integration Plan

## Context

### Original Request
Integrate GRVT V4 BBO routing into the DN (dual-notification) hedge bot to resolve timeout issues caused by insufficient liquidity at GRVT.

### V4 BBO 라우팅의 진짜 목적
- GRVT 유동성 부족 → 시장 미세구조 분석 → 유동성 있는 호가(BBO/BAO) 찾기 → Timeout 문제 해결

### 통합된 솔루션
```
calculate_timeout() + analyze_order_book_depth() + BBO-aware routing
+ find_hedge_price_with_liquidity() + place_iterative_market_order()
= 유동성 있는 호가 찾기 → Timeout 문제 해결
```

### Current DN Code Locations

**File:** `perp-dex-tools-original/hedge/DN_alternate_backpack_grvt_current.py`

| Line | Current Code | Issue |
|------|--------------|-------|
| 857 | `quantity=quantity` | Passes raw quantity without liquidity check |
| 862 | `await asyncio.sleep(1.0)` | Fixed sleep doesn't adapt to order size |
| 865 | `position_change = abs(pos_after - pos_before)` | No liquidity-aware pricing |
| 1052 | `if close_side == "buy": close_price = best_ask` | Uses BBO but no depth analysis |

## Work Objectives

### Core Objective
Replace naive `place_market_order` calls with V4's BBO-aware iterative routing that:
1. Checks liquidity depth before routing
2. Uses smart timeout based on order size
3. Routes to liquidity-aware price levels
4. Iteratively fills when single level insufficient

### Deliverables
1. Import V4 BBO routing functions into DN bot
2. Add liquidity check before hedge order placement
3. Replace `place_market_order` with `place_iterative_market_order`
4. Add proper result parsing for all 3 return paths
5. Test with small and large order sizes

### Definition of Done
- [ ] DN bot imports and uses V4 BBO routing functions
- [ ] Liquidity check returns dict format consistently
- [ ] `place_iterative_market_order` called with correct V4 signature (no invalid params)
- [ ] All 3 return paths handled correctly
- [ ] `tick_size` documented as INT (cents)
- [ ] Timeout calculated dynamically based on order size

## Must Have / Must NOT Have

### Must Have
✅ BBO liquidity depth check before routing
✅ Smart timeout based on order size (`calculate_timeout`)
✅ Iterative market order placement with V4 signature
✅ Safe result parsing for all return path formats
✅ `tick_size` as INT (10 = $0.10)

### Must NOT Have
❌ Invalid parameters: `max_tick_offset`, `max_fill_duration` (DO NOT EXIST in V4)
❌ Assuming `result['iterations']` always exists (only in Path 1)
❌ Inconsistent return formats (bool vs dict)
❌ Fixed sleep timeouts (use `calculate_timeout`)
❌ Ambiguous import statements

## Task Flow and Dependencies

```
Phase 1: Understanding (NO CODE CHANGES)
    ↓
Phase 2: Integration (Add imports + helper)
    ↓
Phase 3: OPEN Logic Replacement (Line 857)
    ↓
Phase 4: CLOSE Logic Enhancement (Line 1052)
    ↓
Phase 5: Testing & Verification
```

## Detailed TODOs

### Phase 1: Understanding V4 API (CRITICAL - NO CODE CHANGES)

**Objective:** Verify exact V4 signatures and return paths

**Task 1.1: Read V4 function signatures**
- [ ] Read `grvt.py:1218-1226` for `place_iterative_market_order` signature
- [ ] Confirm parameters: `contract_id`, `target_quantity`, `side`, `max_iterations=20`, `max_slippage_bps=5`, `tick_size=10` (INT!)
- [ ] NOTE: `tick_size=10` means 10 cents = $0.10 (INT type, NOT Decimal)

**Task 1.2: Document all 3 return paths**
- [ ] **Path 1 (Fallback mode)**: Lines 1315-1321
  ```python
  {
      'total_filled': Decimal,
      'total_fees': Decimal,
      'average_price': Decimal,
      'iterations': int,  # ONLY in this path!
      'success': True
  }
  ```
- [ ] **Path 2 (Main success)**: Lines 1374, 1425
  ```python
  # Returns order_result directly from _ws_rpc_submit_order
  # Use extract_filled_quantity() to safely parse
  ```
- [ ] **Path 3 (Failure)**: Line 1433
  ```python
  {'success': False, 'error': 'Max iterations reached'}
  ```

**Task 1.3: Verify helper functions**
- [ ] Read `grvt.py:50-88` for `extract_filled_quantity`
- [ ] Read `grvt.py:18-47` for `calculate_timeout`
- [ ] Read `grvt.py:751-812` for `analyze_order_book_depth`
- [ ] Read `grvt.py:814-870` for `find_hedge_price_with_liquidity`

**Acceptance Criteria:**
- Documented all 3 return path formats
- Verified `tick_size` is INT type
- Identified which keys exist in which return paths

---

### Phase 2: Add Imports and Helper (DN file)

**Objective:** Import V4 functions and add liquidity check helper

**Task 2.1: Add V4 imports to DN file**
- [ ] At top of DN file, add:
  ```python
  from exchanges.grvt import (
      extract_filled_quantity,  # Module-level function
      calculate_timeout,
      GRVTExchange  # For type hints
  )
  ```

**Task 2.2: Add liquidity check helper (DN class method)**
- [ ] Add method to DN class:
  ```python
  async def check_grvt_liquidity(
      self,
      client: GRVTExchange,
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

**Acceptance Criteria:**
- Import statement includes `extract_filled_quantity` as module-level function
- Liquidity check returns dict format (NOT bool)
- Helper method added to DN class
- Proper error handling with fallback return

---

### Phase 3: Replace OPEN Logic (Line 857 area)

**Objective:** Replace naive `place_market_order` with iterative routing

**Task 3.1: Replace order placement call (Line 855-859)**
- [ ] Find current code:
  ```python
  order_info = await self.hedge_client.place_market_order(
      contract_id=self.hedge_contract_id,
      quantity=quantity,
      side=order_side,
  )
  ```
- [ ] Replace with:
  ```python
  # 1. Check liquidity first
  liquidity = await self.check_grvt_liquidity(
      client=self.hedge_client,
      target_quantity=quantity,
      side=order_side
  )

  # 2. Calculate smart timeout
  timeout = calculate_timeout(quantity)

  # 3. Use iterative routing (V4 signature - NO invalid params!)
  order_info = await self.hedge_client.place_iterative_market_order(
      contract_id=self.hedge_contract_id,
      target_quantity=quantity,
      side=order_side,
      max_iterations=20,
      max_slippage_bps=5,
      tick_size=10  # INT: 10 cents = $0.10
  )
  ```

**Task 3.2: Parse result safely (all 3 paths)**
- [ ] Replace old verification (Lines 862-892) with:
  ```python
  # Parse result based on return path
  if not order_info.get('success', True):
      self.logger.error(f"[OPEN] Iterative order failed: {order_info.get('error', 'Unknown')}")
      return False

  # Extract filled quantity (works for all return paths)
  filled = extract_filled_quantity(order_info)

  # Wait with smart timeout
  await asyncio.sleep(timeout)

  pos_after = await self.hedge_client.get_account_positions()
  position_change = abs(pos_after - pos_before)

  if position_change >= quantity * Decimal("0.9"):
      # Calculate actual fill price from result
      if 'average_price' in order_info:
          actual_fill_price = Decimal(order_info['average_price'])
      else:
          actual_fill_price = best_ask if side == "buy" else best_bid

      self.logger.info(
          f"[OPEN] [GRVT] [ITERATIVE_FILL]: "
          f"{filled} @ ~{actual_fill_price} "
          f"(target: {quantity}, iterations: {order_info.get('iterations', 'N/A')})"
      )

      self.log_trade_to_csv(
          exchange=self.hedge_exchange.upper(),
          side=side,
          price=str(actual_fill_price),
          quantity=str(filled),
          order_type="hedge_open",
          mode="iterative_routing"
      )

      self.hedge_order_filled = True
      self.order_execution_complete = True
      self.last_hedge_fill_price = actual_fill_price
      return True
  else:
      self.logger.error(
          f"[OPEN] Insufficient fill: {position_change} vs target {quantity}"
      )
      return False
  ```

**Acceptance Criteria:**
- NO invalid parameters (`max_tick_offset`, `max_fill_duration`)
- Liquidity check called before routing
- `tick_size=10` documented as INT (cents)
- `extract_filled_quantity` used for safe parsing
- All 3 return paths handled (check for `average_price` key)
- Timeout calculated dynamically

---

### Phase 4: Enhance CLOSE Logic (Line 1052 area)

**Objective:** Add liquidity-aware pricing to CLOSE logic

**Task 4.1: Add liquidity check before pricing (Line 1052)**
- [ ] After fetching BBO (Line 1049), add:
  ```python
  # Check liquidity depth
  liquidity = await self.check_grvt_liquidity(
      client=client,
      target_quantity=close_qty,
      side=close_side
  )

  if not liquidity['sufficient_at_bbo']:
      self.logger.warning(
          f"[FORCE_CLOSE] Insufficient BBO liquidity: "
          f"need {close_qty}, available {liquidity['available_size']}"
      )
  ```

**Task 4.2: Use liquidity-aware pricing**
- [ ] Replace simple BBO pricing (Lines 1052-1057) with:
  ```python
  # Use liquidity-aware pricing if available
  try:
      optimal_price, slippage_bps, levels = await client.find_hedge_price_with_liquidity(
          symbol=client.config.contract_id,
          side=close_side,
          target_quantity=close_qty,
          max_slippage_bps=10  # Allow more slippage on close
      )
      close_price = optimal_price
      self.logger.info(
          f"[FORCE_CLOSE] Using liquidity-aware price: {close_price} "
          f"(slippage: {slippage_bps} bps, levels: {levels})"
      )
  except ValueError as e:
      # Fallback to BBO crossing
      if close_side == "buy":
          close_price = best_ask
      else:
          close_price = best_bid
      self.logger.warning(f"[FORCE_CLOSE] Using BBO fallback: {e}")
  ```

**Acceptance Criteria:**
- Liquidity check returns dict format (consistent)
- Tries liquidity-aware pricing first
- Falls back to BBO crossing if insufficient depth
- Logs slippage and levels used

---

### Phase 5: Testing & Verification

**Objective:** Verify integration works correctly

**Task 5.1: Code verification**
- [ ] Run: `python -m py_compile perp-dex-tools-original/hedge/DN_alternate_backpack_grvt_current.py`
- [ ] Confirm NO syntax errors

**Task 5.2: Import verification**
- [ ] Test import in Python REPL:
  ```python
  from exchanges.grvt import extract_filled_quantity, calculate_timeout
  print(extract_filled_quantity.__doc__)
  print(calculate_timeout(Decimal('0.5')))
  ```
- [ ] Confirm `extract_filled_quantity` is module-level function
- [ ] Confirm returns Decimal type

**Task 5.3: Signature verification**
- [ ] Search codebase for any remaining calls with invalid params:
  ```bash
  grep -r "max_tick_offset\|max_fill_duration" perp-dex-tools-original/hedge/
  ```
- [ ] Confirm NO results (these params don't exist in V4)

**Task 5.4: Manual test plan**
- [ ] Test with small order (0.1 ETH) → Should use `tick_size=10` (10 cents)
- [ ] Test with large order (1.0 ETH) → Should use multiple iterations
- [ ] Verify timeout calculation: 0.1 ETH → 5s, 0.5 ETH → 10s, 1.0 ETH → 20s
- [ ] Check logs for `[LIQUIDITY_CHECK]` and `[SMART_ROUTING]` messages

**Acceptance Criteria:**
- Python compiles without errors
- Imports work correctly
- NO invalid parameters found in codebase
- Manual test shows proper iteration behavior
- Timeouts match expected values

---

## Commit Strategy

### Commit 1: Add imports and helper
```
feat(dn-bot): Add GRVT V4 BBO routing imports and liquidity check helper

- Import extract_filled_quantity (module-level function)
- Import calculate_timeout for dynamic timeout calculation
- Add check_grvt_liquidity() helper method (returns dict format)
```

### Commit 2: Replace OPEN logic
```
feat(dn-bot): Replace naive place_market_order with iterative routing (OPEN)

- Use place_iterative_market_order with correct V4 signature
- NO invalid params (max_tick_offset, max_fill_duration)
- tick_size=10 (INT, 10 cents = $0.10)
- Parse all 3 return paths safely with extract_filled_quantity
- Use calculate_timeout() for dynamic sleep
```

### Commit 3: Enhance CLOSE logic
```
feat(dn-bot): Add liquidity-aware pricing to CLOSE logic

- Check liquidity depth before pricing
- Use find_hedge_price_with_liquidity() for optimal price
- Fallback to BBO crossing if insufficient depth
- Log slippage and levels used
```

---

## Success Criteria

1. ✅ DN bot compiles without errors
2. ✅ NO invalid parameters in any `place_iterative_market_order` call
3. ✅ Liquidity check returns dict format consistently
4. ✅ All 3 return paths handled correctly
5. ✅ `tick_size` documented as INT (10 = $0.10)
6. ✅ `extract_filled_quantity` imported as module-level function
7. ✅ Timeout calculated dynamically based on order size
8. ✅ Manual test shows proper BBO routing behavior

---

## Critical Reminders (DO NOT IGNORE)

1. **V4 Signature (CORRECT):**
   ```python
   place_iterative_market_order(
       contract_id, target_quantity, side,
       max_iterations=20,
       max_slippage_bps=5,
       tick_size=10  # INT, not Decimal!
   )
   ```
   NO `max_tick_offset`, NO `max_fill_duration`

2. **3 Return Paths:**
   - Path 1 (fallback): Has `iterations` key
   - Path 2 (main): Use `extract_filled_quantity()`
   - Path 3 (failure): `{'success': False}`

3. **Import Format:**
   ```python
   from exchanges.grvt import extract_filled_quantity  # Module-level!
   ```

4. **Liquidity Check Returns:**
   ```python
   {
       'sufficient_at_bbo': bool,
       'available_size': Decimal,
       'depth_levels_used': int,
       'fallback_needed': bool
   }
   ```

5. **Tick Size is INT:**
   `tick_size=10` means 10 cents = $0.10 (INT type, NOT Decimal)
