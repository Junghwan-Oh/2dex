# PLAN.md - 실행 계획서 (How)

**작성일**: 2025-10-25
**프로젝트**: Volume Farming Bot - Perpetual DEX Point Farming
**현재 단계**: Milestone 1 - Single DEX Validation (Apex Pro)

---

## 📋 이 문서의 목적

"오늘 앉아서 뭘 할 건지"에 대한 구체적인 일일 작업 지시서. TECHSPEC.md의 전략적 마일스톤을 실행 가능한 코드 레벨 작업으로 분해.

**작업 규칙**:
- ✅ 완료된 작업은 체크 표시
- 🔄 진행 중인 작업은 이모지 표시
- 📝 다음 세션을 위한 Notes 남기기
- 🚨 긴급 작업 우선순위 표시

---

## 🎯 현재 세션 목표 (Phase 7.30.4 → Phase 1.1 완료)

### 🚨 CRITICAL: Mainnet 긴급 수정 (즉시 실행)

**배경**: Phase 7.30.1-7.30.3에서 Native TP/SL 테스트 중 Entry Price Mismatch로 -8.43% 손실 발생. Mainnet에 잘못된 orders 3개 남아있음.

#### Task 1: 잘못된 Mainnet Orders 수동 취소
- [ ] **Order IDs 확인**:
  - `769552825186255210`
  - `769552825937035626`
  - `769552802868363626`

- [ ] **취소 방법** (두 가지 옵션):

  **Option A: Apex Pro Web UI 사용**
  1. https://pro.apex.exchange/ 로그인
  2. "Orders" 탭 → "Open Orders"
  3. Order ID로 검색 후 "Cancel" 클릭

  **Option B: Python SDK 사용**
  ```python
  from apex.lib.apex_client import ApexClient

  client = ApexClient(environment='mainnet')

  # Cancel each order
  order_ids = [
      '769552825186255210',
      '769552825937035626',
      '769552802868363626'
  ]

  for order_id in order_ids:
      try:
          result = client.private_client.cancel_order_v3(orderId=order_id)
          print(f"✅ Cancelled {order_id}: {result}")
      except Exception as e:
          print(f"❌ Failed {order_id}: {e}")
  ```

- [ ] **검증**: `get_fills_v3()` 호출하여 취소 확인

**Expected Result**: 3개 orders 모두 취소 완료

---

#### Task 2: ApexClient.get_positions() 구현

**Problem**: `pilot_dynamic_tpsl_fixed.py:monitor_position()`에서 `ApexClient.get_positions()` 호출 시 AttributeError

**File**: `apex/lib/apex_client.py`

**Fix**:
```python
# apex/lib/apex_client.py 에 추가

class ApexClient:
    # ... 기존 코드 ...

    def get_positions(self, symbol: str = None):
        """
        현재 포지션 조회

        Args:
            symbol: 특정 심볼 필터 (optional)

        Returns:
            list: 포지션 리스트
        """
        try:
            # Option 1: private_client.get_account_v3() 사용
            account = self.private_client.get_account_v3()
            positions = account.get('data', {}).get('positions', [])

            # Symbol 필터
            if symbol:
                positions = [p for p in positions if p.get('symbol') == symbol]

            return positions

        except Exception as e:
            print(f"❌ get_positions() error: {e}")
            return []
```

**Test**:
```python
# Test script
from apex.lib.apex_client import ApexClient

client = ApexClient(environment='testnet')
positions = client.get_positions('BTC-USDT')
print(f"Positions: {positions}")
```

- [ ] `apex/lib/apex_client.py` 수정
- [ ] Test script 실행 (testnet)
- [ ] `pilot_dynamic_tpsl_fixed.py:monitor_position()` 동작 확인

---

#### Task 3: Entry Price Mismatch 해결 (MARKET Entry)

**Problem**: LIMIT entry order → 실제 fill price와 계산된 entry price 불일치 → TP/SL 잘못된 방향 trigger

**Solution**: MARKET entry order 사용 (NATIVE_TPSL_CRITICAL_ISSUES.md의 Solution 1)

**File**: `apex/pilot_dynamic_tpsl_fixed.py` (또는 새 파일 `pilot_true_dynamic_tpsl.py` 생성)

**Changes**:
```python
# OLD (LIMIT entry - WRONG)
def execute_with_native_tpsl_old(self):
    entry_price = current_price * 0.9995  # LIMIT order

    order = self.private_client.create_order_v3(
        type='LIMIT',
        price=str(entry_price),
        # ... TP/SL params
    )

# NEW (MARKET entry - CORRECT)
def execute_with_native_tpsl(self):
    """
    MARKET entry + Native TP/SL with buffer

    Improvements:
    - MARKET entry → guaranteed immediate fill
    - Entry uncertainty buffer (+0.1%)
    - TP/SL calculated from current market price
    """
    current_price = self.get_current_price()

    # Add buffer for entry uncertainty
    entry_uncertainty = 0.001  # 0.1%

    # Calculate TP/SL from CURRENT price (not entry)
    if self.side == 'SHORT':
        # SHORT: Entry ~= current, TP below, SL above
        tp_trigger = current_price * (1 - (self.tp_pct / self.leverage))
        sl_trigger = current_price * (1 + (self.sl_pct / self.leverage) + entry_uncertainty)
    else:  # LONG
        tp_trigger = current_price * (1 + (self.tp_pct / self.leverage))
        sl_trigger = current_price * (1 - (self.sl_pct / self.leverage) - entry_uncertainty)

    # Round to tick size
    tp_trigger = self.round_price(tp_trigger)
    sl_trigger = self.round_price(sl_trigger)

    # MARKET order (no price param)
    order = self.private_client.create_order_v3(
        symbol=self.symbol,
        side='SELL' if self.side == 'SHORT' else 'BUY',
        type='MARKET',  # 🔥 KEY CHANGE
        size=str(self.size),
        # Remove price parameter

        accountId=self.account_id,
        isOpenTpslOrder=True,

        # TP/SL params (unchanged)
        tpTriggerPrice=str(tp_trigger),
        tpSide='BUY' if self.side == 'SHORT' else 'SELL',
        tpSize=str(self.size),

        slTriggerPrice=str(sl_trigger),
        slSide='BUY' if self.side == 'SHORT' else 'SELL',
        slSize=str(self.size),
    )

    return order
```

**Implementation Steps**:
- [ ] 1. `pilot_true_dynamic_tpsl.py` 생성 (clean implementation)
- [ ] 2. `execute_with_native_tpsl()` 메서드 작성 (MARKET entry)
- [ ] 3. Entry uncertainty buffer 추가 (0.1%)
- [ ] 4. TP/SL direction validation 로직 추가
- [ ] 5. Testnet 테스트 (소액 0.001 BTC)

---

#### Task 4: TP/SL Order Type/TimeInForce 파라미터 추가

**Problem**: TP/SL이 MARKET order로 실행됨 → 슬리피지 발생 가능

**Solution**: LIMIT order + GTT (Good-Till-Time) 사용

**File**: `pilot_true_dynamic_tpsl.py`

**Changes**:
```python
def execute_with_native_tpsl(self):
    # ... (Task 3 코드에 추가)

    order = self.private_client.create_order_v3(
        # ... Entry params ...

        # TP Configuration (NEW PARAMS)
        tpOrderType='LIMIT',  # 🔥 ADD THIS
        tpTriggerPrice=str(tp_trigger),
        tpPrice=str(tp_trigger),  # Same as trigger for no slippage
        tpSide='BUY' if self.side == 'SHORT' else 'SELL',
        tpSize=str(self.size),
        tpTimeInForce='GTT',  # 🔥 ADD THIS

        # SL Configuration (NEW PARAMS)
        slOrderType='LIMIT',  # 🔥 ADD THIS
        slTriggerPrice=str(sl_trigger),
        slPrice=str(sl_trigger),  # Same as trigger
        slSide='BUY' if self.side == 'SHORT' else 'SELL',
        slSize=str(self.size),
        slTimeInForce='GTT',  # 🔥 ADD THIS
    )
```

**Checklist**:
- [ ] `tpOrderType='LIMIT'` 추가
- [ ] `slOrderType='LIMIT'` 추가
- [ ] `tpTimeInForce='GTT'` 추가
- [ ] `slTimeInForce='GTT'` 추가
- [ ] `tpPrice` = `tpTriggerPrice` (슬리피지 방지)
- [ ] `slPrice` = `slTriggerPrice` (슬리피지 방지)

---

#### Task 5: pilot_true_dynamic_tpsl.py 테스트

**Test Plan**: Entry 먼저 → TP/SL 나중 (두 단계 검증)

**File**: `apex/pilot_true_dynamic_tpsl.py`

**Test Scenarios**:

1. **Scenario 1: SHORT Position (Testnet)**
   ```bash
   python apex/pilot_true_dynamic_tpsl.py \
       --environment testnet \
       --side SHORT \
       --size 0.001 \
       --take-profit 0.1 \
       --stop-loss 0.05 \
       --duration 600
   ```

   **Expected**:
   - Entry: MARKET order immediate fill
   - TP trigger < Entry price
   - SL trigger > Entry price
   - One fills → Other cancels (OCO)

2. **Scenario 2: LONG Position (Testnet)**
   ```bash
   python apex/pilot_true_dynamic_tpsl.py \
       --environment testnet \
       --side LONG \
       --size 0.001 \
       --take-profit 0.1 \
       --stop-loss 0.05 \
       --duration 600
   ```

   **Expected**:
   - Entry: MARKET order immediate fill
   - TP trigger > Entry price
   - SL trigger < Entry price
   - OCO behavior

3. **Scenario 3: Mainnet Validation (ONLY IF Testnet Success)**
   ```bash
   python apex/pilot_true_dynamic_tpsl.py \
       --environment mainnet \
       --side SHORT \
       --size 0.001 \
       --take-profit 0.2 \
       --stop-loss 0.2 \
       --duration 600 \
       --yes
   ```

   **Risk**: $110 * 0.001 BTC = $0.11 position (~$10 with 7x leverage)

**Validation Checklist**:
- [ ] Entry order fills immediately (MARKET)
- [ ] TP/SL orders created as conditional (not filled immediately)
- [ ] TP trigger direction correct (SHORT: TP < Entry, LONG: TP > Entry)
- [ ] SL trigger direction correct (SHORT: SL > Entry, LONG: SL < Entry)
- [ ] OCO behavior works (one fills → other cancels)
- [ ] P&L matches expected (±0.2%)
- [ ] No immediate wrong-direction execution
- [ ] Order types are LIMIT (not MARKET)
- [ ] TimeInForce is GTT (not IOC)

**Test Log File**: Save to `apex/test_logs/true_dynamic_tpsl_YYYYMMDD_HHMMSS.log`

---

## 📅 Milestone 1: Single DEX Validation (Apex Pro - 1-2주)

**목표**: Apex Pro 단일 DEX에서 Native TP/SL + Avellaneda-Stoikov 전략 검증, $1M/월 거래량 달성

---

### Phase 1.1: Native TP/SL 안정화 (Day 1-3) ✅

**Status**: 🔄 IN PROGRESS (Task 1-5 위 참조)

**완료 조건**:
- ✅ Entry Price Mismatch 해결
- ✅ ApexClient.get_positions() 구현
- ✅ TP/SL Order Type/TimeInForce 파라미터 추가
- ✅ Testnet 10회 연속 성공 (TP 또는 SL 정상 작동)
- ✅ Mainnet 소액 검증 (0.001 BTC, 3회 성공)

**Files**:
- `apex/lib/apex_client.py` (get_positions 추가)
- `apex/pilot_true_dynamic_tpsl.py` (MARKET entry + buffer)
- `apex/test_logs/` (테스트 로그)

---

### Phase 1.2: Avellaneda-Stoikov 기본 구현 (Day 4-7)

**목표**: Avellaneda-Stoikov Market Making 전략 코드 작성 및 백테스트 검증

#### Task 6: Spread 계산 로직 구현

**Theory** (TECHSPEC.md 참조):
```
δ_bid = γσ²τ + (2/γ)ln(1 + γ/k) + (q/2)(γσ√τ)
δ_ask = γσ²τ + (2/γ)ln(1 + γ/k) - (q/2)(γσ√τ)

where:
- γ: risk aversion (0.1-10)
- σ: volatility (rolling 24h std)
- τ: time to rebalance (e.g., 5 min)
- k: order flow intensity
- q: inventory (normalized -1 to +1)
```

**File**: `apex/strategies/avellaneda_market_maker.py`

**Implementation**:
```python
import numpy as np
from typing import Dict, Tuple

class AvellanedaMarketMaker:
    """
    Avellaneda-Stoikov Optimal Market Making

    Paper: Avellaneda & Stoikov (2008)
    """

    def __init__(
        self,
        risk_aversion: float = 0.5,  # γ
        rebalance_time: float = 300,  # τ (5 min in seconds)
        volatility_window: int = 1440,  # 24h in minutes
        max_inventory: float = 0.01,  # Max position (BTC)
    ):
        self.gamma = risk_aversion
        self.tau = rebalance_time / 86400  # Convert to days
        self.vol_window = volatility_window
        self.max_inventory = max_inventory

    def calculate_volatility(self, price_history: list) -> float:
        """
        Calculate 24h rolling volatility

        Args:
            price_history: List of prices (most recent last)

        Returns:
            float: Annualized volatility
        """
        if len(price_history) < 2:
            return 0.01  # Default 1% daily vol

        returns = np.diff(np.log(price_history))
        volatility = np.std(returns) * np.sqrt(365)  # Annualize

        return volatility

    def calculate_spread(
        self,
        mid_price: float,
        volatility: float,
        inventory: float,
        order_flow_intensity: float = 1.0
    ) -> Tuple[float, float]:
        """
        Calculate optimal bid/ask spread

        Args:
            mid_price: Current mid-market price
            volatility: Annualized volatility (σ)
            inventory: Current inventory (normalized -1 to +1)
            order_flow_intensity: Market activity (k)

        Returns:
            (bid_price, ask_price)
        """
        gamma = self.gamma
        tau = self.tau
        k = order_flow_intensity
        q = inventory / self.max_inventory  # Normalize

        # Base spread (no inventory)
        base_spread = gamma * (volatility ** 2) * tau + \
                      (2 / gamma) * np.log(1 + gamma / k)

        # Inventory skew
        inventory_skew = (q / 2) * gamma * volatility * np.sqrt(tau)

        # Bid/Ask spread
        bid_spread = base_spread + inventory_skew
        ask_spread = base_spread - inventory_skew

        # Convert to prices
        bid_price = mid_price * (1 - bid_spread)
        ask_price = mid_price * (1 + ask_spread)

        return (bid_price, ask_price)

    def get_order_params(
        self,
        current_price: float,
        price_history: list,
        current_inventory: float,
    ) -> Dict:
        """
        Get bid/ask order parameters

        Returns:
            {
                'bid_price': float,
                'ask_price': float,
                'bid_size': float,
                'ask_size': float,
                'spread_bps': float,
            }
        """
        # Calculate volatility
        volatility = self.calculate_volatility(price_history)

        # Calculate spread
        bid_price, ask_price = self.calculate_spread(
            mid_price=current_price,
            volatility=volatility,
            inventory=current_inventory,
        )

        # Calculate sizes (equal for now)
        bid_size = 0.001  # 0.001 BTC
        ask_size = 0.001

        # Spread in bps
        spread_bps = ((ask_price - bid_price) / current_price) * 10000

        return {
            'bid_price': bid_price,
            'ask_price': ask_price,
            'bid_size': bid_size,
            'ask_size': ask_size,
            'spread_bps': spread_bps,
            'volatility': volatility,
            'inventory': current_inventory,
        }
```

**Checklist**:
- [ ] `avellaneda_market_maker.py` 생성
- [ ] `calculate_volatility()` 구현
- [ ] `calculate_spread()` 구현 (base + inventory skew)
- [ ] `get_order_params()` 구현
- [ ] Unit tests 작성 (`tests/test_avellaneda.py`)

---

#### Task 7: Avellaneda MM + Native TP/SL 통합

**File**: `apex/pilot_avellaneda_native_tpsl.py`

**Implementation**:
```python
from apex.lib.apex_client import ApexClient
from apex.strategies.avellaneda_market_maker import AvellanedaMarketMaker
import time

class AvellanedaNativeTPSL:
    """
    Avellaneda MM + Native TP/SL Integration

    Strategy:
    1. Place BID/ASK orders at Avellaneda spread
    2. When filled → Immediately place Native TP/SL
    3. Monitor inventory → Rebalance if > 60/40
    """

    def __init__(self, environment='testnet'):
        self.client = ApexClient(environment=environment)
        self.mm_strategy = AvellanedaMarketMaker(
            risk_aversion=0.5,
            rebalance_time=300,  # 5 min
        )
        self.price_history = []

    def run_cycle(self):
        """Single MM cycle"""
        # 1. Get current price
        current_price = self.client.get_current_price('BTC-USDT')
        self.price_history.append(current_price)

        # 2. Get current inventory
        positions = self.client.get_positions('BTC-USDT')
        inventory = sum([float(p['size']) for p in positions])

        # 3. Calculate Avellaneda spread
        params = self.mm_strategy.get_order_params(
            current_price=current_price,
            price_history=self.price_history[-1440:],  # 24h
            current_inventory=inventory,
        )

        # 4. Place BID order (POST_ONLY)
        bid_order = self.client.place_maker_order(
            symbol='BTC-USDT',
            side='BUY',
            price=params['bid_price'],
            size=params['bid_size'],
        )

        # 5. Place ASK order (POST_ONLY)
        ask_order = self.client.place_maker_order(
            symbol='BTC-USDT',
            side='SELL',
            price=params['ask_price'],
            size=params['ask_size'],
        )

        # 6. Wait for fills → Place TP/SL
        self.monitor_fills_and_add_tpsl()

        # 7. Check inventory rebalance
        if abs(inventory) > 0.006:  # 60/40 threshold
            self.rebalance_inventory(inventory)

    def monitor_fills_and_add_tpsl(self):
        """Monitor fills and add Native TP/SL"""
        # Implementation: WebSocket listen for fills
        # When filled → call execute_with_native_tpsl()
        pass

    def rebalance_inventory(self, inventory: float):
        """Close excess inventory"""
        # Implementation: Market order to close
        pass
```

**Checklist**:
- [ ] `pilot_avellaneda_native_tpsl.py` 생성
- [ ] `run_cycle()` 구현 (Avellaneda spread 계산)
- [ ] `monitor_fills_and_add_tpsl()` 구현
- [ ] `rebalance_inventory()` 구현
- [ ] WebSocket integration for real-time fills

---

#### Task 8: Backtest 검증

**File**: `backtest/strategies/avellaneda_backtest.py`

**Validation**:
- [ ] Backtest with 7 days historical data
- [ ] Expected: +0.20% return (PROJECT_STATUS.md 기준)
- [ ] Expected: 500-700 trades/day
- [ ] Verify spread calculation matches theory
- [ ] Inventory management prevents drift

**Command**:
```bash
python backtest/strategies/avellaneda_backtest.py \
    --start-date 2024-10-18 \
    --end-date 2024-10-25 \
    --capital 5000 \
    --leverage 7
```

---

### Phase 1.3: Volume Optimization (Day 8-10)

**목표**: 거래 빈도 증가 → 1000 trades/day 달성 → $1M/월 거래량

#### Task 9: Rebalance Time 단축

**Current**: τ = 300초 (5분) → ~288 cycles/day
**Target**: τ = 120초 (2분) → ~720 cycles/day

**File**: `apex/strategies/avellaneda_market_maker.py`

**Change**:
```python
def __init__(self, rebalance_time: float = 120):  # 5분 → 2분
    self.tau = rebalance_time / 86400
```

**Trade-offs**:
- ✅ Higher trade frequency → More volume
- ⚠️ Higher gas fees (negligible on Apex)
- ⚠️ Inventory management more critical

---

#### Task 10: Point Farming 추적 시스템

**File**: `apex/monitoring/point_tracker.py`

**Implementation**:
```python
class PointTracker:
    """
    Track DEX point farming metrics
    """

    def __init__(self):
        self.daily_volume = 0
        self.monthly_volume = 0
        self.trade_count = 0

    def log_trade(self, trade: Dict):
        """
        Log single trade

        Args:
            trade: {
                'symbol': 'BTC-USDT',
                'side': 'BUY',
                'price': 110000,
                'size': 0.001,
                'fee': 0.02,
                'timestamp': 1729900000,
            }
        """
        volume = trade['price'] * trade['size']
        self.daily_volume += volume
        self.monthly_volume += volume
        self.trade_count += 1

        # Save to DB/file
        self.save_to_log(trade)

    def get_metrics(self) -> Dict:
        """
        Get current metrics

        Returns:
            {
                'daily_volume': float,
                'monthly_volume': float,
                'trade_count': int,
                'avg_trade_size': float,
                'projected_monthly_volume': float,
            }
        """
        avg_trade_size = self.daily_volume / self.trade_count if self.trade_count > 0 else 0
        projected_monthly = self.daily_volume * 30

        return {
            'daily_volume': self.daily_volume,
            'monthly_volume': self.monthly_volume,
            'trade_count': self.trade_count,
            'avg_trade_size': avg_trade_size,
            'projected_monthly_volume': projected_monthly,
        }
```

**Checklist**:
- [ ] `point_tracker.py` 생성
- [ ] `log_trade()` 구현
- [ ] `get_metrics()` 구현
- [ ] SQLite DB 통합 (optional)
- [ ] Dashboard UI (Streamlit - optional)

---

#### Task 11: 손실률 모니터링

**File**: `apex/monitoring/loss_monitor.py`

**Target**: ≤0.01% loss per trade (TECHSPEC.md 기준)

**Implementation**:
```python
class LossMonitor:
    """
    Monitor trade-by-trade P&L
    """

    def __init__(self, alert_threshold: float = 0.0001):
        self.alert_threshold = alert_threshold  # 0.01%
        self.trades = []

    def log_pnl(self, entry_price: float, exit_price: float, side: str):
        """
        Log P&L for single trade
        """
        if side == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SHORT
            pnl_pct = (entry_price - exit_price) / entry_price

        self.trades.append({
            'entry': entry_price,
            'exit': exit_price,
            'side': side,
            'pnl_pct': pnl_pct,
            'timestamp': time.time(),
        })

        # Alert if loss exceeds threshold
        if pnl_pct < -self.alert_threshold:
            self.send_alert(pnl_pct)

    def get_stats(self) -> Dict:
        """
        Get loss statistics
        """
        if not self.trades:
            return {}

        pnls = [t['pnl_pct'] for t in self.trades]

        return {
            'total_trades': len(self.trades),
            'avg_pnl': np.mean(pnls),
            'max_loss': np.min(pnls),
            'max_profit': np.max(pnls),
            'win_rate': sum([1 for p in pnls if p > 0]) / len(pnls),
        }
```

**Checklist**:
- [ ] `loss_monitor.py` 생성
- [ ] Alert system 구현 (Slack/Discord webhook)
- [ ] Daily report 생성
- [ ] Auto-stop if loss > 0.05% per trade

---

### Phase 1.4: 24시간 Mainnet 검증 (Day 11-14)

**목표**: 실제 mainnet 환경에서 24시간 연속 운영 → 목표 달성 확인

#### Task 12: Mainnet 배포

**Deployment Checklist**:
- [ ] `.env` 파일 mainnet credentials 확인
- [ ] Position size 0.001 BTC로 제한 (safety)
- [ ] Daily loss limit 5% 설정
- [ ] Monitoring dashboard 준비
- [ ] Emergency stop mechanism 테스트

**Command**:
```bash
# Dry-run first
python apex/pilot_avellaneda_native_tpsl.py \
    --environment mainnet \
    --dry-run \
    --duration 3600

# Real run
python apex/pilot_avellaneda_native_tpsl.py \
    --environment mainnet \
    --size 0.001 \
    --leverage 7 \
    --duration 86400 \
    --yes
```

---

#### Task 13: 24시간 모니터링

**Monitoring Checklist**:
- [ ] Hour 0-6: 매 시간 체크 (손실률, 거래량)
- [ ] Hour 6-12: 2시간 간격 체크
- [ ] Hour 12-24: 4시간 간격 체크
- [ ] Alerts 설정 (손실 > 0.05%, 거래 중단 > 30분)

**Metrics to Track**:
1. **거래량**: 목표 $35K/day (=$1M/month)
2. **거래 빈도**: 목표 700+ trades/day
3. **손실률**: 목표 ≤0.01% per trade
4. **Inventory balance**: 목표 40-60% range
5. **Spread**: 목표 10-50 bps

**Log Files**:
- `apex/logs/mainnet_YYYYMMDD.log`
- `apex/logs/point_farming_YYYYMMDD.csv`

---

#### Task 14: 성과 분석

**File**: `claudedocs/milestone1_report.md`

**Report Template**:
```markdown
# Milestone 1 성과 보고서

**기간**: 2025-10-26 ~ 2025-11-08 (14일)
**DEX**: Apex Pro
**Strategy**: Avellaneda-Stoikov Market Making + Native TP/SL

## 📊 핵심 지표

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| 월 거래량 | $1M | $XXX | ✅/❌ |
| 일 거래 횟수 | 700+ | XXX | ✅/❌ |
| 손실률 (per trade) | ≤0.01% | X.XX% | ✅/❌ |
| 누적 수익률 | ≥0% | +X.XX% | ✅/❌ |
| Uptime | >95% | XX% | ✅/❌ |

## 🔍 상세 분석

### 거래량 분석
- 일평균 거래량: $XXK
- 거래 빈도: XXX trades/day
- 평균 포지션 크기: $XX

### 손익 분석
- 총 수익: +$XX
- 총 손실: -$XX
- 순수익: +$XX
- Sharpe Ratio: X.XX

### 포인트 가치 추정
- Apex Pro Points: XXX points
- 추정 가치 (보수적): $XX
- 추정 가치 (낙관적): $XXX

## ✅ Milestone 1 달성 여부

- [ ] $1M/월 거래량 달성
- [ ] ≥0% 손실 없음 유지
- [ ] Native TP/SL 안정화
- [ ] 24시간 연속 운영 성공

## 🚀 Next: Milestone 2

Paradex 추가 → Delta Neutral 전략...
```

**Checklist**:
- [ ] 14일 데이터 수집
- [ ] `milestone1_report.md` 작성
- [ ] Milestone 1 달성 여부 판단
- [ ] Milestone 2 시작 여부 결정

---

## 📅 Milestone 2: Dual DEX Operation (2-3주)

**목표**: Paradex 추가 → Delta Neutral 전략 → Fee arbitrage

### Phase 2.1: Paradex API 통합 (Day 15-17)

**Status**: ⏳ PENDING (Milestone 1 완료 후)

#### Task 15: Paradex Client 구현

**File**: `paradex/lib/paradex_client.py` (이미 존재 - PROJECT_STATUS.md 참조)

**Verification**:
- [ ] Paradex testnet 연결 확인
- [ ] Place order 테스트
- [ ] Maker rebate 확인 (-0.005%)

---

#### Task 16: Cross-Exchange Manager 통합

**File**: `common/cross_exchange_manager.py` (이미 존재)

**Changes**:
```python
class CrossExchangeManager:
    """
    Dual DEX orchestration

    Strategy:
    - Apex: SHORT bias (fees 0.02%)
    - Paradex: LONG bias (rebate -0.005%)
    - Net: Delta neutral + fee arbitrage
    """

    def __init__(self):
        self.apex_client = ApexClient(environment='mainnet')
        self.paradex_client = ParadexClient(environment='mainnet')

    def run_dual_cycle(self):
        """
        Single dual-DEX cycle
        """
        # 1. Get prices from both DEXs
        apex_price = self.apex_client.get_current_price('BTC-USDT')
        paradex_price = self.paradex_client.get_current_price('BTC-USD')

        # 2. Check price divergence
        divergence = abs(apex_price - paradex_price) / apex_price

        if divergence > 0.001:  # 0.1% arbitrage opportunity
            self.execute_arbitrage(apex_price, paradex_price)
        else:
            # Normal MM on both
            self.execute_mm_both_exchanges()

    def execute_arbitrage(self, apex_price, paradex_price):
        """Execute cross-DEX arbitrage"""
        if apex_price > paradex_price:
            # Sell on Apex (expensive), Buy on Paradex (cheap)
            self.apex_client.place_maker_order('SELL', apex_price, 0.001)
            self.paradex_client.place_maker_order('BUY', paradex_price, 0.001)
        else:
            # Opposite
            self.paradex_client.place_maker_order('SELL', paradex_price, 0.001)
            self.apex_client.place_maker_order('BUY', apex_price, 0.001)

    def execute_mm_both_exchanges(self):
        """Run Avellaneda MM on both"""
        # Apex: Avellaneda spread
        # Paradex: Avellaneda spread (tighter for rebate)
        pass
```

**Checklist**:
- [ ] `cross_exchange_manager.py` 수정
- [ ] `run_dual_cycle()` 구현
- [ ] Price divergence monitor
- [ ] Inventory tracking across both DEXs
- [ ] Testnet 검증

---

### Phase 2.2: Delta Neutral 검증 (Day 18-21)

#### Task 17: Position Balance Monitor

**File**: `common/position_monitor.py`

**Implementation**:
```python
class PositionMonitor:
    """
    Monitor net position across DEXs
    """

    def get_net_position(self) -> float:
        """
        Calculate net BTC exposure

        Returns:
            float: Net BTC (positive = LONG, negative = SHORT)
        """
        apex_pos = self.apex_client.get_positions('BTC-USDT')
        paradex_pos = self.paradex_client.get_positions('BTC-USD')

        apex_size = sum([float(p['size']) for p in apex_pos])
        paradex_size = sum([float(p['size']) for p in paradex_pos])

        return apex_size + paradex_size

    def is_delta_neutral(self, threshold: float = 0.002) -> bool:
        """
        Check if net position within threshold

        Args:
            threshold: Max allowed net position (BTC)
        """
        net = self.get_net_position()
        return abs(net) < threshold

    def rebalance_to_neutral(self):
        """
        Rebalance to delta neutral
        """
        net = self.get_net_position()

        if net > 0:  # Net LONG → Close on cheaper exchange
            # Close LONG on Apex or SHORT on Paradex
            pass
        elif net < 0:  # Net SHORT → opposite
            pass
```

**Checklist**:
- [ ] `position_monitor.py` 생성
- [ ] `get_net_position()` 구현
- [ ] `is_delta_neutral()` 구현
- [ ] `rebalance_to_neutral()` 구현
- [ ] Alert system for >0.002 BTC drift

---

#### Task 18: Fee Arbitrage 분석

**Analysis**: Compare net fees across strategies

**File**: `claudedocs/fee_arbitrage_analysis.md`

**Calculation**:
```
Scenario 1: Apex만 운영
- Volume: $1M/월
- Fees: $1M * 0.0002 = $200/월

Scenario 2: Paradex만 운영
- Volume: $1M/월
- Rebate: $1M * (-0.00005) = -$50/월 (수익!)

Scenario 3: Dual DEX (50/50)
- Apex: $500K * 0.0002 = $100
- Paradex: $500K * (-0.00005) = -$25
- Net: $75/월

Scenario 4: Dual DEX (30/70 - Paradex bias)
- Apex: $300K * 0.0002 = $60
- Paradex: $700K * (-0.00005) = -$35
- Net: $25/월
```

**Optimal Strategy**: Paradex 70%, Apex 30% → Lowest net fees

---

### Phase 2.3: 7일 Dual-DEX 검증 (Day 22-28)

#### Task 19: Mainnet Dual-DEX 배포

**Command**:
```bash
python common/cross_exchange_manager.py \
    --environment mainnet \
    --duration 604800 \
    --paradex-weight 0.7 \
    --apex-weight 0.3 \
    --yes
```

**Monitoring**: Same as Task 13

---

## 📅 Milestone 3: Portfolio Expansion (1-2개월)

**Status**: ⏳ PENDING (Milestone 2 완료 후)

**목표**: 5개 DEXs 동시 운영 → $5-10M/월 거래량

### Target DEXs:
1. ✅ Apex Pro (already live)
2. ✅ Paradex (Milestone 2)
3. dYdX v4
4. Hyperliquid
5. Orderly Network

**Phase 3.1**: dYdX v4 통합 (Week 1-2)
**Phase 3.2**: Hyperliquid 통합 (Week 3-4)
**Phase 3.3**: Orderly 통합 (Week 5-6)
**Phase 3.4**: 5-DEX 검증 (Week 7-8)

---

## 📅 Milestone 4: Scale & Optimize (3-6개월)

**Status**: ⏳ PENDING (Milestone 3 완료 후)

**목표**: 20개 DEXs → $20-100M/월 거래량 → 상위 1% point farmers

**Optimizations**:
- Multi-region deployment (US, EU, Asia)
- Advanced inventory management (Kelly Criterion)
- ML-based spread prediction
- HFT-level latency optimization (<10ms)
- Automatic DEX discovery and integration

---

## 📝 Session Notes (다음 세션을 위한 메모)

### ✅ 완료된 작업 (이 섹션은 AI가 자동 업데이트)
-

### 🔄 진행 중인 작업
- Task 1-5: Native TP/SL 수정 (Phase 7.30.4 → Phase 1.1)

### ⏭️ 다음 세션 우선순위
1. Task 1: Mainnet orders 수동 취소 (URGENT)
2. Task 2: ApexClient.get_positions() 구현
3. Task 3: pilot_true_dynamic_tpsl.py 작성 (MARKET entry)
4. Task 5: Testnet 테스트 10회

### 🚨 Blockers
- Mainnet에 잘못된 orders 3개 남아있음 (즉시 취소 필요)

### 💡 Lessons Learned
- Native TP/SL은 entry order와 동시 제출 → Entry price uncertainty 반드시 고려
- LIMIT entry는 위험 → MARKET entry 더 안전
- TP/SL Order Type/TimeInForce 파라미터 명시 필수

### 🔗 Related Files
- `NATIVE_TPSL_CRITICAL_ISSUES.md`: 문제 분석 및 해결책
- `pilot_dynamic_tpsl_fixed.py`: 기존 구현 (LIMIT entry)
- `pilot_true_dynamic_tpsl.py`: 새 구현 (MARKET entry - 생성 예정)

---

## 🧪 TDD Checklist

### Unit Tests
- [ ] `tests/test_apex_client.py::test_get_positions()`
- [ ] `tests/test_avellaneda.py::test_calculate_spread()`
- [ ] `tests/test_avellaneda.py::test_inventory_skew()`

### Integration Tests
- [ ] `tests/test_native_tpsl.py::test_market_entry()`
- [ ] `tests/test_native_tpsl.py::test_tpsl_direction()`
- [ ] `tests/test_native_tpsl.py::test_oco_behavior()`

### E2E Tests
- [ ] Testnet: 10회 연속 성공 (SHORT + LONG)
- [ ] Mainnet: 3회 소액 검증 (0.001 BTC)
- [ ] 24시간 연속 운영 (no crashes)

---

## 📚 References

### Documentation
- TECHSPEC.md: 전략적 비전 (Why & What)
- NATIVE_TPSL_CRITICAL_ISSUES.md: Entry Price Mismatch 해결책
- PROJECT_STATUS.md: 현재 프로젝트 상태 (Phase 1-3 완료)
- IMPLEMENTATION_GUIDE.md: 기존 API 사용법

### Research Papers
- Avellaneda & Stoikov (2008): High-frequency Trading in a Limit Order Book
- Kelly (1956): A New Interpretation of Information Rate

### API Documentation
- Apex Pro API: https://api-docs.pro.apex.exchange
- Paradex API: https://docs.paradex.trade

---

## 🔄 Auto-Update Instructions (for AI)

이 문서는 세션마다 자동 업데이트됩니다:

1. **완료된 작업**: ✅ 체크박스 표시 → "Session Notes - 완료된 작업"에 이동
2. **새로운 작업**: 다음 phase에서 tasks 추가
3. **Blockers**: 해결 시 삭제, 새로운 blocker 추가
4. **Lessons Learned**: 실수 발생 시 교훈 추가

**Git Commit Rule**: PLAN.md 변경 시 관련 코드와 함께 커밋
```bash
git add docs/PLAN.md apex/pilot_true_dynamic_tpsl.py
git commit -m "완료: Task 3 - MARKET entry Native TP/SL 구현

- pilot_true_dynamic_tpsl.py 생성 (MARKET entry)
- Entry uncertainty buffer 0.1% 추가
- Testnet 10회 연속 성공 확인

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

**Last Updated**: 2025-10-25
**Next Review**: 완료된 Task 개수가 5개 이상일 때 또는 Milestone 완료 시
