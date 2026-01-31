# Plan V3 Critic Review - REJECTED

**Review Date**: 2026-01-31
**Reviewer**: RALPLAN Critic Agent
**Plan Version**: V3 (dn-pair-liquidation-stabilization-v3.md)
**Verdict**: **REJECTED**

---

## Executive Summary

Plan V3 is **REJECTED** due to **critical PNL violation** and **ignoring architect recommendations**. The aggressive pricing strategy (5-15 bps past touch) guarantees negative PNL on every trade, directly violating the user's requirement of PNL >= 0.

---

## Critical Issues

### Issue 1: PNL >= 0 Requirement VIOLATED (CRITICAL)

**Severity**: CRITICAL
**Status**: VIOLATED
**User Requirement**: PNL >= 0 (zero or positive profit only)

**Analysis**:

Plan V3 implements aggressive pricing strategy:
- IOC orders: 5-15 bps past touch price
- Retry 1: 5 bps aggressive
- Retry 2: 10 bps aggressive
- Retry 3: 15 bps aggressive

**Cost Breakdown Per Trade**:
```
Trading Fees (taker):        10 bps (0.10%)
Aggressive Pricing (retry 1):  5 bps (0.05%)
Slippage (estimated):         5-10 bps (0.05-0.10%)
─────────────────────────────────────────────
Total Cost Per Trade:        20-25 bps (0.20-0.25%)

Worst Case (retry 3):
Trading Fees (taker):        10 bps (0.10%)
Aggressive Pricing (retry 3): 15 bps (0.15%)
Slippage (estimated):         5-10 bps (0.05-0.10%)
─────────────────────────────────────────────
Total Cost Per Trade:        30-35 bps (0.30-0.35%)
```

**Result**: Every IOC trade is guaranteed to lose 20-35 bps (0.20-0.35%)

**Impact**:
- 100 trades/day @ $1,000/trade = $200-$350/day loss
- 500 trades/day @ $1,000/trade = $1,000-$1,750/day loss
- This is the opposite of the $2,000/day profit goal

**Code Evidence from V3**:
```python
# Lines 198-206 in V3 plan
if direction == 'buy':
    # Aggressive buy: slightly above best ask to ensure execution
    # Add 1-2 bps above best ask for aggressive fill
    slippage_buffer_bps = min(estimated_slippage_bps, Decimal('5'))  # Max 5 bps aggressive
    order_price = best_ask * (1 + slippage_buffer_bps / 10000)  # ❌ VIOLATES PNL >= 0
else:
    # Aggressive sell: slightly below best bid to ensure execution
    slippage_buffer_bps = min(estimated_slippage_bps, Decimal('5'))  # Max 5 bps aggressive
    order_price = best_bid * (1 - slippage_buffer_bps / 10000)  # ❌ VIOLATES PNL >= 0
```

---

### Issue 2: Architect Recommendations IGNORED (CRITICAL)

**Severity**: CRITICAL
**Status**: NOT IMPLEMENTED

**Architect Recommended**:
1. **Conservative pricing** - Touch price only (best_bid/best_ask)
2. **Spread filter** - Minimum 20 bps spread required
3. **POST_ONLY entry** - Use 2 bps maker fee instead of 10 bps taker

**Plan V3 Implemented**:
1. **Aggressive pricing** - 5-15 bps past touch ❌
2. **No spread filter** - Trades at any spread width ❌
3. **IOC-only execution** - Always 10 bps taker fee ❌

**Evidence from V3**:

Lines 201-202:
```python
slippage_buffer_bps = min(estimated_slippage_bps, Decimal('5'))  # Max 5 bps aggressive
order_price = best_ask * (1 + slippage_buffer_bps / 10000)  # ❌ Aggressive, not conservative
```

**No Spread Filter Found**:
- Grep for "spread.*filter" in V3: 0 results
- Grep for "min.*spread" in V3: 0 results
- Grep for "20.*bps" in V3: Only in slippage limit context

**Why This Matters**:
- Wide spreads = high execution cost
- Trading at 5 bps spread with 10 bps fee = guaranteed loss
- Architect's spread filter (20 bps minimum) prevents this scenario

---

### Issue 3: Korean Terminology Missing (HIGH)

**Severity**: HIGH
**Status**: MISSING

**Missing Korean Explanations**:

**Financial Terms**:
- BookDepth (호가 깊이/유동성)
- Slippage (슬리피지/가격 미끄러짐)
- bps (베이시스 포인트/기준점)
- Touch Price (최우선 호가/현재가)

**Order Types**:
- IOC (Immediate-Or-Cancel, 즉시-체결-또는-취소)
- POST_ONLY (포스트 온리/지정가만, 메이커 전용)
- FOK (Fill-Or-Kill, 전량-체결-또는-취소)

**Trading Concepts**:
- Spread (스프레드/매수매도호가 차이)
- Taker Fee (테이커 수수료, 즉시 체결 수수료)
- Maker Fee (메이커 수수료, 지정가 수수료)

**Impact**:
- Korean user cannot fully understand the plan
- Technical jargon creates comprehension barriers
- Violates documentation best practices for Korean users

---

### Issue 4: Daily Volume Goals Unrealistic (HIGH)

**Severity**: HIGH
**Status**: CONTRADICTORY

**Plan V3 Claims**:
```
Volume Goals:
- Increase trades/day from 100 to 500
- Target: $2,000/day profit
- Cumulative: $1,000,000
```

**Reality**:
- Every trade loses 20-35 bps (0.20-0.35%)
- More trades = more losses
- 500 trades/day @ 20 bps loss = $1,000/day loss
- This is the OPPOSITE of profit goal

**Missing from V3**:
- Revenue model (how do we make money?)
- Profit per trade calculation
- Spread capture strategy
- Positive PNL scenarios

**Question**: How can we make $2,000/day when every trade loses money?

---

### Issue 5: PNL Calculation Section Missing (MEDIUM)

**Severity**: MEDIUM
**Status**: MISSING

**What's Missing**:
1. Entry PNL calculation (2 bps maker vs 10 bps taker)
2. Exit PNL calculation (2 bps maker vs 10 bps taker)
3. Spread capture PNL (ask - bid spread)
4. Total PNL formula
5. Break-even analysis

**Why This Matters**:
- User cannot verify if PNL >= 0 is achievable
- No way to calculate expected profit/loss
- Cannot optimize strategy parameters

---

## Required Improvements (Top 5)

### 1. Remove Aggressive Pricing (CRITICAL - PNL VIOLATION)

**Change Required**:
```python
# ❌ CURRENT (V3) - Aggressive pricing
if direction == 'buy':
    slippage_buffer_bps = min(estimated_slippage_bps, Decimal('5'))
    order_price = best_ask * (1 + slippage_buffer_bps / 10000)  # 5 bps past ask

# ✅ REQUIRED - Conservative pricing
if direction == 'buy':
    order_price = best_ask  # Touch price only, 0 bps past ask
```

**Impact**:
- Reduces execution cost by 5-15 bps per trade
- Eliminates guaranteed PNL loss from aggressive pricing
- Still allows IOC execution at touch price

---

### 2. Add Spread Filter (CRITICAL - PNL PROTECTION)

**New Code Required**:
```python
async def check_entry_conditions(self, contract_id: str) -> Tuple[bool, str]:
    """
    Check if market conditions allow entry.

    Returns:
        (can_enter, reason)
    """
    # Get BBO prices
    best_bid, best_ask = await self.fetch_bbo_prices(contract_id)

    # Calculate spread in bps
    spread_abs = best_ask - best_bid
    spread_bps = (spread_abs / best_bid) * 10000

    # Check minimum spread requirement
    MIN_SPREAD_BPS = 20  # 0.20% minimum spread

    if spread_bps < MIN_SPREAD_BPS:
        return False, f"Spread too narrow: {spread_bps:.1f} bps < {MIN_SPREAD_BPS} bps"

    # Check liquidity
    bookdepth = self.get_bookdepth_handler()
    if bookdepth:
        liquidity_5bps = bookdepth.get_available_liquidity('buy', 5)  # Liquidity within 5 bps
        if liquidity_5bps < self.min_position_size:
            return False, f"Insufficient liquidity: {liquidity_5bps} < {self.min_position_size}"

    return True, "Entry conditions met"
```

**Usage**:
```python
# Before placing entry order
can_enter, reason = await self.check_entry_conditions(contract_id)
if not can_enter:
    self.logger.log(f"Skipping entry: {reason}", "WARN")
    return
```

---

### 3. Add Korean Terminology Section (HIGH)

**New Section Required**:
```markdown
## 한국어 용어 설명 (Korean Terminology)

### 거래 관련 용어 (Trading Terms)

**BookDepth (호가 깊이)**
- 정의: 주문장의 매수/매도 호가 깊이 정보
- 설명: 각 가격대별로 얼마나 많은 주문이 대기하고 있는지 보여줌
- 용도: 슬리피지 추정, 유동성 확인

**Slippage (슬리피지/가격 미끄러짐)**
- 정의: 주문 체결 시 예상 가격과 실제 체결 가격의 차이
- 원인: 시장 움직임, 유동성 부족, 큰 수량 주문
- 목표: 5 bps 이내 유지

**Touch Price (최우선 호가/현재가)**
- 정의: 현재 가장 우선순위의 매수/매도 호가
- 매수 시: 최우선 매도 호가 (best_ask)
- 매도 시: 최우선 매수 호가 (best_bid)

### 주문 유형 (Order Types)

**IOC (Immediate-Or-Cancel, 즉시-체결-또는-취소)**
- 정의: 즉시 체결되지 않은 부분은 취소되는 주문
- 특징: 부분 체결 허용
- 수수료: 테이커 수수료 (10 bps)
- 용도: 즉시 체결 필요한 시나리오

**POST_ONLY (포스트 온리/지정가만)**
- 정의: 메이커 주문으로만 체결되는 지정가 주문
- 특징: 즉시 체결 시 전체 취소
- 수수료: 메이커 수수료 (2 bps)
- 용도: 수수료 절감, 스프레드 차익

**FOK (Fill-Or-Kill, 전량-체결-또는-취소)**
- 정의: 전량이 즉시 체결되지 않으면 전체 취소
- 특징: 부분 체결 불가
- 수수료: 테이커 수수료 (10 bps)
- 용도: 전량 체결 필요한 시나리오

### 가격 관련 용어 (Price Terms)

**Spread (스프레드/매수매도호가 차이)**
- 정의: 최우선 매도호가와 최우선 매수호가의 차이
- 계산: spread_bps = (ask - bid) / bid * 10000
- 의미: 시장 유동성 척도 (좁을수록 유동성 높음)

**bps (베이시스 포인트/기준점)**
- 정의: 백분율의 1/100 (0.01%)
- 예시: 1 bps = 0.01%, 100 bps = 1%
- 용도: 수수료, 스프레드, 가격 차이 표현

**Taker Fee (테이커 수수료)**
- 정의: 즉시 체결 주문에 부과되는 수수료
- 비율: 10 bps (0.10%)
- 예시: $1,000 체결 시 $1 수수료

**Maker Fee (메이커 수수료)**
- 정의: 지정가 주문(유동성 제공)에 부과되는 수수료
- 비율: 2 bps (0.02%)
- 예시: $1,000 체결 시 $0.20 수수료
- 절감: 테이커 대비 80% 절감
```

---

### 4. Add PNL Calculation Section (MEDIUM)

**New Section Required**:
```markdown
## PNL Calculation (손익 계산)

### Entry PNL (진입 손익)

**Option 1: POST_ONLY Entry (Recommended)**
- Fee: 2 bps (maker)
- Slippage: 0 bps (we provide liquidity)
- Total Entry Cost: 2 bps

**Option 2: IOC Entry (Conservative)**
- Fee: 10 bps (taker)
- Slippage: 0 bps (touch price only)
- Total Entry Cost: 10 bps

### Exit PNL (청산 손익)

**Option 1: POST_ONLY Exit (Recommended)**
- Fee: 2 bps (maker)
- Slippage: 0-5 bps (depending on market conditions)
- Total Exit Cost: 2-7 bps

**Option 2: IOC Exit (Emergency)**
- Fee: 10 bps (taker)
- Slippage: 0 bps (touch price only, NO aggressive pricing)
- Total Exit Cost: 10 bps

### Total Round-Trip PNL (왕복 손익)

**Scenario 1: Ideal (POST_ONLY entry + POST_ONLY exit)**
```
Entry Cost:     2 bps (maker fee)
Exit Cost:      2 bps (maker fee)
Spread Capture: 20 bps (0.20% spread at 20 bps width)
─────────────────────────────────────────
Net Profit:     16 bps (0.16% per trade)
```

**Scenario 2: Conservative (POST_ONLY entry + IOC exit)**
```
Entry Cost:     2 bps (maker fee)
Exit Cost:     10 bps (taker fee, NO aggressive pricing)
Spread Capture: 20 bps (0.20% spread at 20 bps width)
─────────────────────────────────────────
Net Profit:      8 bps (0.08% per trade)
```

**Scenario 3: Emergency (IOC entry + IOC exit)**
```
Entry Cost:    10 bps (taker fee, touch price)
Exit Cost:     10 bps (taker fee, touch price)
Spread Capture: 20 bps (0.20% spread at 20 bps width)
─────────────────────────────────────────
Net Profit:      0 bps (break-even)
```

### Break-Even Analysis (손익분기점 분석)

**Minimum Spread Required**:
- POST_ONLY + POST_ONLY: >4 bps spread
- POST_ONLY + IOC: >12 bps spread
- IOC + IOC: >20 bps spread

**Recommended Strategy**:
1. Use POST_ONLY for both entry and exit when possible
2. Use IOC for emergency unwind only
3. Never use aggressive pricing (crossing spread)
4. Minimum spread filter: 20 bps

### Daily PNL Projection (일일 손익 예측)

**Assumptions**:
- Average trade size: $1,000
- Average spread: 20 bps
- Trades per day: 100 (conservative start)
- POST_ONLY fill rate: 70%
- IOC fill rate: 100%

**Calculation**:
```
70 trades × POST_ONLY (16 bps profit) = 70 × $1.60 = $112 profit
30 trades × IOC (0 bps profit) = 30 × $0 = $0 profit
─────────────────────────────────────────────────────
Daily Profit: $112 (conservative estimate)

If spread = 30 bps:
70 trades × POST_ONLY (26 bps profit) = 70 × $2.60 = $182 profit
30 trades × IOC (10 bps profit) = 30 × $1.00 = $30 profit
─────────────────────────────────────────────────────
Daily Profit: $212 (better spread conditions)

To reach $2,000/day:
Need 10× more volume or better spread conditions
1,000 trades/day at 20 bps spread = $1,120/day
1,000 trades/day at 30 bps spread = $2,120/day ✅
```
```

---

### 5. Add Spread Monitoring Pre-Check (MEDIUM)

**New Code Required**:
```python
async def validate_market_conditions(
    self,
    contract_id: str,
    min_spread_bps: float = 20.0,
    min_liquidity_usd: float = 5000.0
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate market conditions before trading.

    Args:
        contract_id: Contract to validate
        min_spread_bps: Minimum required spread in bps
        min_liquidity_usd: Minimum liquidity in USD

    Returns:
        (is_valid, reason, metrics)
    """
    metrics = {}

    # 1. Check spread
    best_bid, best_ask = await self.fetch_bbo_prices(contract_id)
    spread_abs = best_ask - best_bid
    spread_bps = float((spread_abs / best_bid) * 10000)
    metrics['spread_bps'] = spread_bps

    if spread_bps < min_spread_bps:
        return False, f"Spread too narrow: {spread_bps:.1f} bps < {min_spread_bps} bps", metrics

    # 2. Check liquidity
    bookdepth = self.get_bookdepth_handler()
    if bookdepth:
        liquidity_bid = bookdepth.get_available_liquidity('buy', depth_bps=5)
        liquidity_ask = bookdepth.get_available_liquidity('sell', depth_bps=5)
        metrics['liquidity_bid_usd'] = float(liquidity_bid * best_bid)
        metrics['liquidity_ask_usd'] = float(liquidity_ask * best_ask)

        min_liquidity = min(metrics['liquidity_bid_usd'], metrics['liquidity_ask_usd'])
        if min_liquidity < min_liquidity_usd:
            return False, f"Insufficient liquidity: ${min_liquidity:,.0f} < ${min_liquidity_usd:,.0f}", metrics

    # 3. Check volatility (optional)
    # Add volatility check if historical data available

    return True, "Market conditions valid", metrics


# Usage in trading logic
async def execute_trade(self, contract_id: str, quantity: Decimal, direction: str):
    # Pre-check market conditions
    is_valid, reason, metrics = await self.validate_market_conditions(
        contract_id,
        min_spread_bps=20.0,
        min_liquidity_usd=5000.0
    )

    if not is_valid:
        self.logger.log(f"Trade skipped: {reason}", "WARN")
        self.logger.log(f"Metrics: {metrics}", "INFO")
        return None

    self.logger.log(
        f"Market conditions OK - Spread: {metrics['spread_bps']:.1f} bps, "
        f"Liquidity: ${metrics['liquidity_bid_usd']:,.0f}/${metrics['liquidity_ask_usd']:,.0f}",
        "INFO"
    )

    # Proceed with trade...
```

---

## Architect Analysis

### What Architect Recommended

From architect analysis of the codebase:

**Conservative Pricing Strategy**:
- Touch price only (best_bid/best_ask)
- No aggressive spread crossing
- Preserve PNL by avoiding unnecessary costs

**Spread Filter**:
- Minimum 20 bps spread required
- Prevents trading in tight spread conditions
- Ensures profit margin after fees

**POST_ONLY Preference**:
- 2 bps maker fee vs 10 bps taker fee
- 80% fee reduction
- Better for PNL

### What Plan V3 Implemented

**Aggressive Pricing Strategy**:
- 5-15 bps past touch price
- Violates conservative pricing principle
- Direct PNL cost on every trade

**No Spread Filter**:
- Trades at any spread width
- Can trade at 5 bps spread with 10 bps fee = guaranteed loss

**IOC-Only Execution**:
- Always uses 10 bps taker fee
- No POST_ONLY option for entry
- Misses 80% fee savings opportunity

### Why This Matters

The architect analyzed the existing codebase and user requirements to recommend a strategy that:
1. Achieves PNL >= 0 (user requirement)
2. Minimizes trading costs
3. Handles liquidation emergencies

Plan V3 ignores all architect recommendations and implements the opposite strategy.

---

## Recommendation

**Plan V3 must be completely revised to address:**

1. ✅ **Remove all aggressive pricing** - Use touch price only
2. ✅ **Add spread filter (20 bps minimum)** - Prevent unprofitable trades
3. ✅ **Add POST_ONLY option** - Reduce fees by 80%
4. ✅ **Add Korean terminology** - Improve user comprehension
5. ✅ **Add PNL calculations** - Show profitability path

**Next Step**: Create Plan V4 with all required improvements

---

**Critic Signature**: RALPLAN Critic Agent
**Status**: REJECTED - Create V4 required
**Date**: 2026-01-31
