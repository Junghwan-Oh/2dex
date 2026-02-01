# Emergency Unwind Functions Fix Plan

**Created**: 2026-02-01
**Priority**: MEDIUM (critical for risk management)
**Complexity**: LOW (simple logic changes)
**Iteration**: RALPLAN 3/5

---

## 1. Context

### Problem Statement

The `emergency_unwind_eth()` and `emergency_unwind_sol()` methods in `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` contain hardcoded position direction assumptions that prevent them from correctly closing positions in all scenarios.

**Current Behavior:**
- Line 787: `if current_pos > 0:` - Only handles ETH long positions
- Line 803: `if current_pos < 0:` - Only handles SOL short positions

**Required Behavior:**
Both methods must handle long and short positions by determining the correct close side dynamically.

### Calling Context (lines 756-779)

`handle_emergency_unwind()` is called after placing simultaneous entry orders. Its purpose is to maintain delta-neutral balance when one leg fills but the other fails:

```python
if eth_filled and not sol_filled:
    await self.emergency_unwind_eth()  # Close ETH
elif sol_filled and not eth_filled:
    await self.emergency_unwind_sol()  # Close SOL
```

**Why Both Directions Must Be Handled:**
- ETH and SOL can each be long OR short depending on the pair configuration
- The emergency unwind must correctly determine: "Is this position long? If so, sell to close. Is it short? If so, buy to close."

### Decimal Comparison Pattern

The codebase uses tolerance-based comparison like `abs(eth_pos) > Decimal("0.001")` (see `test_dn_pair.py` lines 79, 170, 180, 191, 194) rather than exact equality `== 0` because floating-point positions may have tiny residual amounts.

### Design Decision: No None Check Required

The `get_account_positions()` method in NadoClient (`/Users/botfarmer/2dex/hedge/exchanges/nado.py` lines 1078-1110`) has a guaranteed return type of `Decimal`:

**Type Annotation** (line 1078):
```python
async def get_account_positions(self) -> Decimal:
```

**Return Paths** (always returns Decimal):
1. Line 1102: `return result` - Found position as `Decimal`
2. Line 1105: `return Decimal(0)` - No position found
3. Line 1110: `return Decimal(0)` - Exception case

**Conclusion**: The method never returns `None`, so explicit `None` checking is unnecessary. The tolerance check `abs(current_pos) > Decimal("0.001")` already handles all edge cases including zero positions.

---

## 2. Work Objectives

### Core Objective

Fix both `emergency_unwind_eth()` and `emergency_unwind_sol()` methods to handle ALL position states (long, short, and zero/dust).

### Deliverables

1. Updated `emergency_unwind_eth()` function handling both long and short positions
2. Updated `emergency_unwind_sol()` function handling both long and short positions
3. Updated docstrings reflecting both position types
4. Improved error handling with logging

### Definition of Done

- Both functions handle long positions (`> 0`) with "sell" orders
- Both functions handle short positions (`< 0`) with "buy" orders
- Both functions skip dust positions using tolerance check `abs(pos) > 0.001`
- Docstrings updated to reflect both position types
- Exception handling includes logging
- No `None` check needed (documented why)

---

## 3. Must Have / Must NOT Have

### Must Have

- Use tolerance check `abs(current_pos) > Decimal("0.001")` (pattern from test_dn_pair.py)
- Use conditional logic to determine order side
- Use `abs()` for quantity parameter
- Update docstrings to reflect both position types
- Add logging to exception handling
- Document why `None` check is not needed (get_account_positions always returns Decimal)

### Must NOT Have

- Do NOT use exact equality `current_pos == 0` (unsafe for Decimal types)
- Do NOT add unnecessary `None` checks
- Do NOT change function signatures
- Do NOT modify the calling code (`handle_emergency_unwind`)
- Do NOT add new dependencies

---

## 4. Detailed TODOs

### Step 1: Fix `emergency_unwind_eth()` (lines 781-795)

**Current Code**:
```python
async def emergency_unwind_eth(self):
    """Emergency unwind ETH position."""
    if self.eth_client:
        try:
            current_pos = await self.eth_client.get_account_positions()
            if current_pos > 0:  # Only handles long positions
                await self.eth_client.place_close_order(
                    self.eth_client.config.contract_id,
                    current_pos,
                    Decimal("0"),
                    "sell"
                )
        except Exception:
            pass
```

**Required Change**:
```python
async def emergency_unwind_eth(self):
    """Emergency unwind ETH position (handles both long and short).

    Determines current position direction and closes with market order.
    Uses tolerance check (abs(pos) > 0.001) to handle Decimal precision.

    Called from handle_emergency_unwind() when ETH fills but SOL fails.
    """
    if self.eth_client:
        try:
            current_pos = await self.eth_client.get_account_positions()
            # NOTE: No None check needed - get_account_positions() always returns Decimal
            # See nado.py:1078 - method signature: async def get_account_positions(self) -> Decimal
            # Tolerance check: skip dust positions below 0.001
            # Pattern from test_dn_pair.py: handles Decimal precision issues
            if abs(current_pos) > Decimal("0.001"):
                # Determine close side: long positions sell, short positions buy
                close_side = "sell" if current_pos > 0 else "buy"
                await self.eth_client.place_close_order(
                    self.eth_client.config.contract_id,
                    abs(current_pos),  # Always use positive quantity
                    Decimal("0"),  # Market order
                    close_side  # Dynamically determined side
                )
        except Exception as e:
            self.logger.error(f"[UNWIND] Failed to close ETH position: {e}")
```

### Step 2: Fix `emergency_unwind_sol()` (lines 797-811)

**Current Code**:
```python
async def emergency_unwind_sol(self):
    """Emergency unwind SOL position."""
    if self.sol_client:
        try:
            current_pos = await self.sol_client.get_account_positions()
            if current_pos < 0:  # Only handles short positions
                await self.sol_client.place_close_order(
                    self.sol_client.config.contract_id,
                    abs(current_pos),
                    Decimal("0"),
                    "buy"
                )
        except Exception:
            pass
```

**Required Change**:
```python
async def emergency_unwind_sol(self):
    """Emergency unwind SOL position (handles both long and short).

    Determines current position direction and closes with market order.
    Uses tolerance check (abs(pos) > 0.001) to handle Decimal precision.

    Called from handle_emergency_unwind() when SOL fills but ETH fails.
    """
    if self.sol_client:
        try:
            current_pos = await self.sol_client.get_account_positions()
            # NOTE: No None check needed - get_account_positions() always returns Decimal
            # See nado.py:1078 - method signature: async def get_account_positions(self) -> Decimal
            # Tolerance check: skip dust positions below 0.001
            # Pattern from test_dn_pair.py: handles Decimal precision issues
            if abs(current_pos) > Decimal("0.001"):
                # Determine close side: long positions sell, short positions buy
                close_side = "sell" if current_pos > 0 else "buy"
                await self.sol_client.place_close_order(
                    self.sol_client.config.contract_id,
                    abs(current_pos),  # Always use positive quantity
                    Decimal("0"),  # Market order
                    close_side  # Dynamically determined side
                )
        except Exception as e:
            self.logger.error(f"[UNWIND] Failed to close SOL position: {e}")
```

### Step 3: Verification Plan

**TODO: Verification Steps**
1. Code Review: Verify tolerance check `abs(current_pos) > Decimal("0.001")` is used
2. Code Review: Verify dynamic side determination logic
3. Code Review: Verify docstrings are updated
4. Code Review: Verify exception logging is added
5. Code Review: Verify comments explain why None check is not needed
6. Unit Test: Test emergency_unwind_eth() with long position (current_pos > 0)
7. Unit Test: Test emergency_unwind_eth() with short position (current_pos < 0)
8. Unit Test: Test emergency_unwind_sol() with long position (current_pos > 0)
9. Unit Test: Test emergency_unwind_sol() with short position (current_pos < 0)
10. Integration Test: Simulate asymmetric fill scenario
11. Manual Test: Run bot and monitor logs for [UNWIND] messages

---

## 5. Risk Analysis

### Low Risk

- The fix follows established patterns in the codebase (test_dn_pair.py)
- No API signature changes
- No changes to calling code
- get_account_positions() has guaranteed Decimal return type

### Medium Risk Considerations

1. **Tolerance Threshold**: Using `0.001` as threshold may skip legitimate small positions
   - **Mitigation**: This is the established pattern in the codebase; matches dust threshold

2. **Logging Added**: Adding `self.logger.error()` may fail if logger not initialized
   - **Mitigation**: Logger is always initialized in DN_pair_bot class

---

## 6. Success Criteria

### Functional Requirements

- ETH long position closes with "sell" order
- ETH short position closes with "buy" order
- SOL long position closes with "sell" order
- SOL short position closes with "buy" order
- Dust positions below 0.001 are skipped

### Code Quality

- Follows existing patterns (test_dn_pair.py tolerance check)
- Clear variable names
- Updated docstrings
- Added exception logging
- Comments explain design decisions

---

## 7. Implementation Summary

**Files Modified**:
- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` (lines 781-795, 797-811)

**Pattern Applied**:
```python
current_pos = await client.get_account_positions()  # Always returns Decimal, never None
if abs(current_pos) > Decimal("0.001"):
    close_side = "sell" if current_pos > 0 else "buy"
    await client.place_close_order(
        contract_id,
        abs(current_pos),
        Decimal("0"),
        close_side
    )
```

### Critical Files

- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Lines 781-811 (functions to fix)
- `/Users/botfarmer/2dex/hedge/test_dn_pair.py` - Lines 79, 170, 180, 191, 194 (tolerance pattern reference)
- `/Users/botfarmer/2dex/hedge/close_position.py` - Lines 33, 55 (position closing pattern reference)
- `/Users/botfarmer/2dex/hedge/exchanges/nado.py` - Lines 1078-1110 (get_account_positions implementation - proves Decimal return type)
