# Session Restoration - Phase 2D Entry Price Analysis & Cleanup
**Date**: 2026-01-05
**Session**: Phase 2D Entry Price Logic Investigation
**Branch**: `feature/phase2d-momentum`
**Status**: Ready for 100 cycles test

---

## 📋 Executive Summary

**Objective**: Investigate Phase 2B loss causes, verify Phase 2D entry price logic, and prepare for 100 cycles test

**Key Findings**:
1. ✅ Entry price logic is **correct** and matches original implementation
2. ✅ All exchanges use unified "Aggressive Maker" strategy
3. ✅ Removed redundant `makerPrice` calculation code
4. ⚠️ Phase 2B losses are **NOT** caused by entry price logic
5. ✅ Phase 2D code is clean and ready for testing

---

## 🔍 Investigation Results

### 1. Entry Price Logic Analysis (All Exchanges)

**Verified Original Sources**:
- `/tmp/perp-dex-tools-original-phase2d/hedge/hedge_mode_grvt.py`
- `/tmp/perp-dex-tools-original-phase2d/hedge/hedge_mode_bp.py`
- `/tmp/perp-dex-tools-original-phase2d/hedge/hedge_mode_nado.py`
- `/tmp/perp-dex-tools-original-phase2d/hedge/hedge_mode_ext.py`

**Unified Logic (All Exchanges)**:
```python
# BUY orders
order_price = best_ask - tick_size  # Place inside spread

# SELL orders
order_price = best_bid + tick_size  # Place inside spread
```

**Strategy Classification**: **Aggressive Maker**

| Strategy | BUY Price | SELL Price | Pros | Cons |
|----------|-----------|------------|------|------|
| **Taker** | ask (highest) | bid (lowest) | Instant fill | Full spread loss |
| **Aggressive Maker** ✅ | ask - tick | bid + tick | Better than Taker, Fast fill | 1 tick worse than BBO |
| **Passive Maker** | bid (lowest) | ask (highest) | Best price | May not fill |

**Design Intent**: Balance between **fill probability** and **price advantage**

---

## 🛠️ Code Changes

### Commit History

**1. `a74d13f` - Incorrect Entry Price Correction Attempt**
```
fix: Correct entry price calculation - BUY (ask-tick) vs SELL (bid+tick)

- BUY: bestAsk - tickSize (place inside spread, lower price)
- SELL: bestBid + tickSize (place inside spread, higher price)
- Matches original perp-dex-tools logic
- Fixes Wintermute's observation: tick advantage directions are opposite
- Applied to both OPEN and CLOSE cycles
```

**Issue**: This change was **redundant** because:
- API already calculates price internally
- `makerPrice` in `hedge_mode_2dex.py` was never passed to API
- Actual price determined by `place_open_order()` inside GRVT/Backpack APIs

**2. `aad107e` - Redundant Code Removal (FINAL) ✅**
```
refactor: Remove redundant makerPrice calculation, use API-determined price

- API already calculates price (aggressive maker: ask-tick for BUY, bid+tick for SELL)
- Remove duplicate price calculation in hedge_mode_2dex.py
- Use OrderResult.price from API response
- Verified all exchanges (GRVT, Backpack, Nado, Extended) use same logic
- Applied to executeOpenCycle, executeCloseCycle, and executeHedgeCycle
```

**Changes**:
- ❌ Removed manual `makerPrice` calculation
- ✅ Use `primaryResult.price` from API
- ✅ Cleaner code, no duplication
- ✅ Logs actual API-determined price

---

## 📊 Phase 2B Performance Analysis (50 Cycles)

**Test Results**:
- **Total P&L**: -$0.61 (avg -$0.012/cycle)
- **Win Rate**: 1/50 (2%)
- **PRIMARY (Maker)**: -$0.63 total
- **HEDGE (Taker)**: +$0.02 total
- **Direction Bias**: 100% SELL (0 BUY cycles)
- **Spread**: Entry $2.05 → Exit $3.27 (+$1.22 expansion)
- **Loss Rate**: 0.0096% of total volume

**Key Observation**:
- Spread **expanded** during Phase 2B (Mean Reversion strategy)
- This contradicts the strategy hypothesis (mean reversion expects convergence)
- User's critical note: *"2d만 하면 스프레드가 축소되고, 2b만 하면 확대되네"*

**Conclusion**: Entry price is NOT the problem. Strategy direction decision may be the issue.

---

## 🔧 Technical Details

### API Entry Price Implementation

**GRVT API** (`exchanges/grvt.py` lines 341-349):
```python
async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
    # Get current market prices
    best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

    # Determine order side and price (aggressive maker - 1 tick from opposite side)
    if direction == 'buy':
        order_price = best_ask - self.config.tick_size  # ← API calculates here
    elif direction == 'sell':
        order_price = best_bid + self.config.tick_size  # ← API calculates here

    # Place the order using GRVT SDK
    order_info = await self.place_post_only_order(contract_id, quantity, order_price, direction)

    return OrderResult(
        success=True,
        order_id=order_id,
        price=order_price,  # ← Returns calculated price
        status=order_status
    )
```

**Backpack API** (`exchanges/backpack.py` lines 336-343):
```python
async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult:
    best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

    if direction == 'buy':
        order_price = best_ask - self.config.tick_size  # ← API calculates
        side = 'Bid'
    else:
        order_price = best_bid + self.config.tick_size  # ← API calculates
        side = 'Ask'

    # Place order with calculated price
    order_result = self.account_client.execute_order(
        symbol=contract_id,
        side=side,
        order_type=OrderTypeEnum.LIMIT,
        quantity=str(quantity),
        price=str(self.round_to_tick(order_price)),
        post_only=True
    )
```

**Key Point**: Price is **always** calculated by API, never by caller.

---

## 📁 Current Code State

### Phase 2D Branch Status

**Branch**: `feature/phase2d-momentum`
**Last Commit**: `aad107e` - Redundant code removal
**Remote**: Pushed to `origin/feature/phase2d-momentum`

**Key Files**:
- `hedge/hedge_mode_2dex.py` - Main bot logic (cleaned)
- `exchanges/grvt.py` - GRVT API (unchanged)
- `exchanges/backpack.py` - Backpack API (unchanged)

**Phase 2D Strategy**:
```python
# Lines 966-969
if primaryMid > hedgeMid:
    direction = 'buy'   # PRIMARY expensive → BUY PRIMARY (momentum)
else:
    direction = 'sell'  # HEDGE expensive → SELL PRIMARY (momentum)
```

**Entry Price** (API-determined):
- BUY: `best_ask - tick_size`
- SELL: `best_bid + tick_size`

---

## 🎯 Next Steps

### Immediate Action: Phase 2D 100 Cycles Test

**Test Configuration**:
- **PRIMARY**: GRVT (maker, POST_ONLY)
- **HEDGE**: Backpack (taker, market)
- **Ticker**: ETH
- **Size**: 0.01
- **Iterations**: 100
- **Expected Duration**: 2-4 hours

**Test Command**:
```bash
cd f:/Dropbox/dexbot/perpdex/2dex/hedge
f:\Dropbox\dexbot\perpdex\venv\Scripts\python.exe hedge_mode_2dex.py --primary grvt --hedge backpack --ticker ETH --size 0.01 --iter 100
```

**Monitoring Points**:
1. Entry/Exit spread behavior (expansion vs contraction)
2. Direction distribution (BUY vs SELL ratio)
3. PRIMARY vs HEDGE P&L breakdown
4. Fill rate and timeout frequency
5. Spread P&L per cycle

**Output Files**:
- `logs/2dex_grvt_backpack_ETH_log.txt`
- `logs/2dex_grvt_backpack_ETH_trades.csv`

---

## 🧪 Comparison Framework

### Phase 2B vs Phase 2D

| Metric | Phase 2B (Mean Reversion) | Phase 2D (Momentum) | Expected Outcome |
|--------|---------------------------|---------------------|------------------|
| **Direction Logic** | PRIMARY > HEDGE → SELL | PRIMARY > HEDGE → BUY | Opposite |
| **Spread Behavior** | Expansion (+$1.22) | TBD | Should contract |
| **Win Rate** | 2% (1/50) | TBD | Should improve |
| **Loss Rate** | 0.0096% | TBD | Should reduce |
| **Direction Bias** | 100% SELL | TBD | More balanced? |

---

## 💡 User's Critical Observations

### Key Quotes

1. **"BUY일 때 1틱 유리와 SELL일 때 1틱 유리는 반대방향"**
   - ✅ Verified: BUY uses `ask - tick`, SELL uses `bid + tick`
   - ✅ Directions are indeed opposite

2. **"2d만 하면 스프레드가 축소되고, 2b만 하면 확대되네 웃픈 현실"**
   - Phase 2D (Momentum): Spread contracts
   - Phase 2B (Mean Reversion): Spread expands
   - This suggests **Phase 2D might be the correct strategy**

3. **"WINTERMUTE 얘도 간과한 것처럼"**
   - Even my "Wintermute DeFi Team Lead" analysis missed the detail
   - Simple direction flip is not enough without considering tick direction

---

## 🔍 Debugging References

### If Tests Fail

**Check Entry Prices**:
```bash
# View recent trades
head -50 logs/2dex_grvt_backpack_ETH_trades.csv

# Analyze spread behavior
grep "PRIMARY_MAKER" logs/2dex_grvt_backpack_ETH_trades.csv | head -20
```

**Verify API Price Calculation**:
```python
# In exchanges/grvt.py line 341
if direction == 'buy':
    order_price = best_ask - self.config.tick_size
elif direction == 'sell':
    order_price = best_bid + self.config.tick_size
```

**Check Cancel-and-Replace Logic**:
```python
# In hedge_mode_2dex.py lines 446-456
if elapsed > 10:  # After 10s, check staleness
    shouldCancel = False
    if direction == 'buy':
        if makerPrice < bestBid:  # Our buy order below best bid
            shouldCancel = True
    else:
        if makerPrice > bestAsk:  # Our sell order above best ask
            shouldCancel = True
```

---

## 📚 Reference Documents

### Previous Session
- `SESSION_RESTORATION_2026-01-04.md` - Phase 2B 50 cycles analysis

### Original Source
- **Repo**: https://github.com/your-quantguy/perp-dex-tools
- **Branch**: main
- **Local Clone**: `/tmp/perp-dex-tools-original-phase2d/`

### Key Files Modified
1. `hedge/hedge_mode_2dex.py` (OPEN cycle lines 356-377)
2. `hedge/hedge_mode_2dex.py` (CLOSE cycle lines 585-608)
3. `hedge/hedge_mode_2dex.py` (executeHedgeCycle lines 777-799)

---

## ✅ Checklist Before Test

- [x] Phase 2D branch checked out
- [x] Entry price logic verified (API-determined)
- [x] Redundant code removed and committed
- [x] Remote pushed to GitHub
- [x] Log files backed up
- [x] Test parameters confirmed (ETH, 0.01, 100 iter)
- [ ] User approval to start test
- [ ] Position cleanup confirmed (no open positions)

---

## 🎯 Success Criteria

**Phase 2D should outperform Phase 2B if**:
1. Spread **contracts** instead of expands
2. Win rate > 2%
3. Loss rate < 0.0096%
4. Direction distribution more balanced (not 100% bias)
5. Total P&L > -$0.61 (Phase 2B baseline)

---

## 📞 Contact Points

**If Issues Occur**:
1. Check position status on both exchanges
2. Verify no hanging orders: `await get_active_orders()`
3. Review WebSocket connection: logs should show order updates
4. Cancel-and-replace should trigger after 10s if price stale
5. Hard timeout at 180s per order (should not be reached often)

---

**End of Session Restoration Document**
**Next Action**: Await user approval to start Phase 2D 100 cycles test

---

## 🧮 Quick Reference

**Git Commands**:
```bash
# Check current branch
git branch

# View recent commits
git log --oneline -5

# Switch branches
git checkout feature/phase2d-momentum

# View changes
git diff HEAD~1
```

**Test Monitoring**:
```bash
# Watch log in real-time
tail -f logs/2dex_grvt_backpack_ETH_log.txt

# Count completed cycles
grep "DONE" logs/2dex_grvt_backpack_ETH_log.txt | wc -l

# Check for timeouts
grep "TIMEOUT" logs/2dex_grvt_backpack_ETH_log.txt

# View spread changes
grep "PHASE 2D MOMENTUM" logs/2dex_grvt_backpack_ETH_log.txt
```

**Python Process Management**:
```bash
# Check running Python processes
powershell.exe -Command "Get-Process python -ErrorAction SilentlyContinue"

# Kill all Python processes (if needed)
powershell.exe -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"
```
