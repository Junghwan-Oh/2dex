# DN Pair Bot PNL Tracking & Improvement - V5.3.1

## Context

### Original Request
Implement comprehensive PNL tracking and improvement system for the DN Pair Bot (ETH-SOL pair trading bot) based on the principle: "Install multiple logging/tracking devices → collect data → gradual improvement → achieve PNL >= 0".

### Current State Analysis

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**PNL Logic Status**:
- Lines 333-334, 348-349: `pnl_no_fee="0"`, `pnl_with_fee="0"` (hardcoded)
- Fees are calculated (FEE_RATE = 0.0005 = 5 bps)
- No PNL tracking state (entry/exit prices not stored)
- No spread filter

**Current Trading Costs**:
- Entry: ETH BUY (5 bps) + SOL SELL (5 bps) = 10 bps
- Exit: ETH SELL (5 bps) + SOL BUY (5 bps) = 10 bps
- **Total Fee: 20 bps (0.2%)**

**Preserved from V4.1**:
- WebSocket BBO/BookDepth real-time data
- Conservative pricing (touch price only, no aggressive orders)
- Position verification logic
- UNWIND retry mechanism (MAX_RETRIES=3)

### User Feedback on V4.1
- "6개월은 선택지로 준 적 없다" - Maintain immediate $1M daily volume target
- "하루 100번 거래는 현재도 가능" (1회 10초 이하)
- PNL is currently not >= 0, but logic improvement can make it possible
- "PNL을 백지상태에서 >=0은 어렵다. logging과 트래킹 장치를 여러개 달아놓고 추적하고 점진적 개선하면 >=0 가능"

### Core Philosophy
**Install multiple logging/tracking devices → collect data → gradual improvement → achieve PNL >= 0**

---

## Work Objectives

### Core Objective
Implement comprehensive PNL tracking, analysis, and gradual improvement system for DN Pair Bot to achieve sustainable profitability through data-driven optimization.

### Deliverables
1. **PNL State Management System** - Track entry/exit prices, quantities, timestamps per cycle
2. **Spread Profitability Filter** - 20 bps minimum spread requirement to avoid unprofitable trades
3. **PNL Calculation Logic** - Accurate no-fee and with-fee PNL computation
4. **Enhanced Logging System** - Multiple tracking devices (CSV, real-time, daily reports)
5. **Spread/Slippage Analysis** - Separate analytics for market conditions
6. **POST_ONLY Entry Option** - Optional maker-only entry for reduced fees (2 bps vs 5 bps)
7. **Daily/Weekly PNL Reports** - Performance metrics and trend analysis

### Definition of Done
- [ ] All cycles track entry/exit prices with PNL calculation
- [ ] Spread filter active (configurable, default 20 bps)
- [ ] PNL logged to CSV with all relevant metrics
- [ ] Real-time PNL monitoring (unrealized PNL every 60 seconds)
- [ ] Daily PNL report generation with win rate, average PNL, best/worst cycles
- [ ] Spread/slippage analysis CSV collecting data
- [ ] POST_ONLY entry mode implemented as optional feature
- [ ] All changes tested (mock cycles + live trading validation)

---

## Must Have / Must NOT Have

### Must Have
- PNL state tracking (entry prices, quantities, timestamps per asset)
- Accurate PNL calculation (no-fee and with-fee)
- Spread filter (minimum 20 bps configurable)
- Enhanced CSV logging with new columns (cycle_id, entry/exit prices, PNL metrics)
- Real-time PNL logging (unrealized PNL)
- Daily PNL summary reports
- Spread/slippage analysis tracking
- POST_ONLY entry option (disabled by default)
- Backward compatibility with existing V4.1 functionality

### Must NOT Have
- Breaking changes to existing V4.1 stable features
- Aggressive order types (stick to touch price/IOC)
- Removal of position verification logic
- Removal of UNWIND retry mechanism
- Hardcoded PNL values (currently "0")
- Assumptions about optimal parameters (let data guide decisions)
- Complex ML/AI models (start with simple metrics)
- Changes to WebSocket BBO/BookDepth data sources

---

## Task Flow and Dependencies

```
Phase 1: PNL Tracking Foundation (8h)
├── Task 1.1: PNL State Management (2h)
│   └── Required by: Task 1.2, Task 3.2
├── Task 1.2: Enhanced CSV Logging (2h)
│   └── Required by: Task 3.2, Task 4.3
└── Task 1.3: State Integration (4h)
    └── Depends on: Task 1.1, Task 1.2

Phase 2: Spread Filter (3h)
├── Task 2.1: Spread Profitability Check (2h)
│   └── Required by: Task 2.2
└── Task 2.2: Spread Filter Integration (1h)
    └── Depends on: Task 2.1
    └── Required by: Task 4.3

Phase 3: PNL Calculation Logic (4h)
├── Task 3.1: Cycle PNL Calculation (2h)
│   └── Required by: Task 3.2
└── Task 3.2: PNL Logging Integration (2h)
    └── Depends on: Task 1.1, Task 1.2, Task 3.1

Phase 4: Enhanced Logging System (3h)
├── Task 4.1: Real-time PNL Logger (1h)
├── Task 4.2: Daily PNL Report (1h)
└── Task 4.3: Spread/Slippage Analysis (1h)
    └── Depends on: Task 1.2, Task 2.1

Phase 5: WebSocket-Based Entry/Exit Optimization (5.5h) ⭐ V5.3.1
├── Task 5.1: Optimal Entry Timing using BBO (1.5h)
├── Task 5.2: BookDepth-Based Position Sizing (1.5h)
├── Task 5.3: Optimal Exit Timing with Real-time PNL (1h)
└── Task 5.4: Funding PNL Correction (1.5h) ⭐ BUGFIX V5.3.1
    └── Depends on: Task 1.1, Task 4.1

Phase 6: POST_ONLY Option (2h)
├── Task 6.1: POST_ONLY Entry Mode (1h)
└── Task 6.2: POST_ONLY Order Placement (1h)
    └── Depends on: Task 6.1

Phase 7: Testing & Validation (2h)
├── Task 7.1: PNL Tracking Test
├── Task 7.2: Spread Filter Test
├── Task 7.3: WebSocket Optimization Test ⭐ NEW
└── Task 7.4: Live Trading Test
    └── Depends on: All previous phases
```

---

## Detailed TODOs

### Phase 1: PNL Tracking Foundation (8h)

#### Task 1.1: PNL State Management (2h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `__init__` method

**Changes**:
```python
# Add to __init__ method
class DNPairBot:
    def __init__(self, ...):
        # PNL Tracking State
        self.entry_prices = {
            "ETH": None,  # Decimal: Entry 진입 가격
            "SOL": None   # Decimal: Entry 진입 가격
        }
        self.entry_quantities = {
            "ETH": Decimal("0"),
            "SOL": Decimal("0")
        }
        self.entry_timestamps = {
            "ETH": None,
            "SOL": None
        }
        self.current_cycle_pnl = {
            "pnl_no_fee": Decimal("0"),
            "pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "entry_time": None,
            "exit_time": None
        }
        self.daily_pnl_summary = {
            "total_cycles": 0,
            "profitable_cycles": 0,
            "losing_cycles": 0,
            "total_pnl_no_fee": Decimal("0"),
            "total_pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "best_cycle_pnl": Decimal("0"),
            "worst_cycle_pnl": Decimal("0")
        }
        self.cycle_id = 0  # Unique cycle identifier
```

**Acceptance Criteria**:
- [ ] All state variables initialized in `__init__`
- [ ] Type hints added (Dict[str, Optional[Decimal]], etc.)
- [ ] Default values set appropriately (None, Decimal("0"))

---

#### Task 1.2: Enhanced CSV Logging (2h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `TradeLogger` class

**New CSV Columns**:
```python
# Add to TradeLogger initialization
new_columns = [
    "cycle_id",                    # Unique cycle identifier
    "entry_timestamp",             # Entry time
    "exit_timestamp",              # Exit time
    "entry_price_eth",             # ETH entry price
    "entry_price_sol",             # SOL entry price
    "exit_price_eth",              # ETH exit price
    "exit_price_sol",              # SOL exit price
    "pnl_no_fee",                  # PNL without fees
    "pnl_with_fee",                # PNL with fees
    "total_fees",                  # Total fees paid
    "spread_bps_entry",            # Spread at entry (bps)
    "spread_bps_exit",             # Spread at exit (bps)
    "slippage_bps_entry",          # Slippage at entry (bps)
    "slippage_bps_exit",           # Slippage at exit (bps)
    "cycle_skipped",               # Whether cycle was skipped
    "skip_reason"                  # Reason for skipping
]
```

**Acceptance Criteria**:
- [ ] New columns added to CSV header
- [ ] CSV writer updated to handle new columns
- [ ] Backward compatibility maintained (old logs still readable)

---

#### Task 1.3: State Integration (4h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `execute_buy_first_cycle`, `execute_sell_first_cycle`

**Changes**:
```python
# In execute_buy_first_cycle (and similarly in execute_sell_first_cycle)
async def execute_buy_first_cycle(self, ...):
    # Increment cycle_id
    self.cycle_id += 1

    # Store entry data
    self.entry_prices["ETH"] = eth_fill_price
    self.entry_prices["SOL"] = sol_fill_price
    self.entry_quantities["ETH"] = eth_qty
    self.entry_quantities["SOL"] = sol_qty
    self.entry_timestamps["ETH"] = datetime.now()
    self.entry_timestamps["SOL"] = datetime.now()
    self.current_cycle_pnl["entry_time"] = datetime.now()

    self.logger.info(
        f"[CYCLE {self.cycle_id}] Entry recorded - "
        f"ETH: ${eth_fill_price}, SOL: ${sol_fill_price}"
    )
```

**Acceptance Criteria**:
- [ ] Cycle ID increments correctly
- [ ] Entry prices/stores/timestamps saved on BUILD
- [ ] State cleared after UNWIND completes
- [ ] Logging confirms state updates

---

### Phase 2: Spread Filter (3h)

#### Task 2.1: Spread Profitability Check (2h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Implementation**:
```python
async def check_spread_profitability(
    self,
    min_spread_bps: int = 20
) -> Tuple[bool, Dict[str, Decimal]]:
    """
    Spread가 수수료보다 큰지 확인.

    Args:
        min_spread_bps: Minimum spread in bps (default: 20)

    Returns:
        (is_profitable, spread_info)
    """
    eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(
        self.eth_client.config.contract_id
    )
    sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(
        self.sol_client.config.contract_id
    )

    # Spread 계산 (bps)
    eth_spread_bps = ((eth_ask - eth_bid) / eth_bid) * 10000
    sol_spread_bps = ((sol_ask - sol_bid) / sol_bid) * 10000

    spread_info = {
        "eth_spread_bps": eth_spread_bps.quantize(Decimal("0.01")),
        "sol_spread_bps": sol_spread_bps.quantize(Decimal("0.01")),
        "eth_bid": eth_bid,
        "eth_ask": eth_ask,
        "sol_bid": sol_bid,
        "sol_ask": sol_ask
    }

    is_profitable = (
        eth_spread_bps >= min_spread_bps and
        sol_spread_bps >= min_spread_bps
    )

    self.logger.info(
        f"[SPREAD] ETH: {eth_spread_bps:.1f} bps, "
        f"SOL: {sol_spread_bps:.1f} bps, "
        f"Profitable: {is_profitable}"
    )

    return is_profitable, spread_info
```

**Acceptance Criteria**:
- [ ] Method fetches BBO prices for both assets
- [ ] Spread calculated correctly in bps
- [ ] Returns tuple (is_profitable, spread_info)
- [ ] Logging includes spread values and profitability

---

#### Task 2.2: Spread Filter Integration (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `execute_buy_first_cycle`, `execute_sell_first_cycle`

**Changes**:
```python
# In execute_buy_first_cycle (before BUILD phase)
async def execute_buy_first_cycle(self, ...):
    # Check spread profitability
    is_profitable, spread_info = await self.check_spread_profitability(
        min_spread_bps=20
    )

    if not is_profitable:
        self.logger.warning(
            f"[CYCLE] Spread too small, skipping cycle. "
            f"ETH: {spread_info['eth_spread_bps']:.1f} bps, "
            f"SOL: {spread_info['sol_spread_bps']:.1f} bps"
        )
        # Log to spread analysis CSV
        self.log_spread_analysis(
            spread_info=spread_info,
            cycle_executed=False,
            skip_reason="Spread below threshold"
        )
        return False

    # Continue with BUILD phase...
```

**Acceptance Criteria**:
- [ ] Spread check called before BUILD phase
- [ ] Cycle skipped if spread < 20 bps
- [ ] Skip logged with reason
- [ ] Spread analysis CSV updated

---

### Phase 3: PNL Calculation Logic (4h)

#### Task 3.1: Cycle PNL Calculation (2h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Implementation**:
```python
def calculate_cycle_pnl(
    self,
    eth_entry_price: Decimal,
    eth_exit_price: Decimal,
    eth_qty: Decimal,
    sol_entry_price: Decimal,
    sol_exit_price: Decimal,
    sol_qty: Decimal
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Cycle PNL 계산.

    Args:
        eth_entry_price: ETH entry price
        eth_exit_price: ETH exit price
        eth_qty: ETH quantity
        sol_entry_price: SOL entry price
        sol_exit_price: SOL exit price
        sol_qty: SOL quantity

    Returns:
        (pnl_no_fee, pnl_with_fee, total_fees)
    """
    # 수수료 없는 PNL
    # ETH: Long (Exit - Entry)
    eth_pnl = (eth_exit_price - eth_entry_price) * eth_qty
    # SOL: Short (Entry - Exit)
    sol_pnl = (sol_entry_price - sol_exit_price) * sol_qty

    pnl_no_fee = eth_pnl + sol_pnl

    # 수수료 계산
    FEE_RATE = Decimal("0.0005")  # 5 bps
    eth_entry_notional = eth_entry_price * eth_qty
    eth_exit_notional = eth_exit_price * eth_qty
    sol_entry_notional = sol_entry_price * sol_qty
    sol_exit_notional = sol_exit_price * sol_qty

    total_fees = (
        eth_entry_notional + eth_exit_notional +
        sol_entry_notional + sol_exit_notional
    ) * FEE_RATE

    # 수수료 포함 PNL
    pnl_with_fee = pnl_no_fee - total_fees

    return pnl_no_fee, pnl_with_fee, total_fees
```

**Acceptance Criteria**:
- [ ] PNL calculated correctly for long ETH (Exit - Entry)
- [ ] PNL calculated correctly for short SOL (Entry - Exit)
- [ ] Fees calculated on all four legs (entry/exit for both)
- [ ] Returns tuple with all three values
- [ ] Decimal precision maintained throughout

---

#### Task 3.2: PNL Logging Integration (2h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `execute_unwind_cycle`

**Changes**:
```python
# In execute_unwind_cycle (after positions close)
async def execute_unwind_cycle(self, ...):
    # ... existing unwind logic ...

    # After successful unwind
    if eth_closed and sol_closed:
        # Get entry prices
        eth_entry_price = self.entry_prices["ETH"]
        eth_entry_qty = self.entry_quantities["ETH"]
        sol_entry_price = self.entry_prices["SOL"]
        sol_entry_qty = self.entry_quantities["SOL"]

        # Exit prices
        eth_exit_price = eth_fill_price
        sol_exit_price = sol_fill_price

        # Calculate PNL
        pnl_no_fee, pnl_with_fee, total_fees = self.calculate_cycle_pnl(
            eth_entry_price, eth_exit_price, eth_entry_qty,
            sol_entry_price, sol_exit_price, sol_entry_qty
        )

        # Store in current cycle state
        self.current_cycle_pnl["pnl_no_fee"] = pnl_no_fee
        self.current_cycle_pnl["pnl_with_fee"] = pnl_with_fee
        self.current_cycle_pnl["total_fees"] = total_fees
        self.current_cycle_pnl["exit_time"] = datetime.now()

        # Log PNL
        self.logger.info(
            f"[PNL] Cycle {self.cycle_id}: "
            f"PNL (no fee): ${pnl_no_fee:.2f}, "
            f"PNL (with fee): ${pnl_with_fee:.2f}, "
            f"Fees: ${total_fees:.2f}"
        )

        # Update CSV
        self.log_cycle_to_csv(
            cycle_id=self.cycle_id,
            pnl_no_fee=pnl_no_fee,
            pnl_with_fee=pnl_with_fee,
            total_fees=total_fees,
            entry_price_eth=eth_entry_price,
            entry_price_sol=sol_entry_price,
            exit_price_eth=eth_exit_price,
            exit_price_sol=sol_exit_price,
            entry_timestamp=self.current_cycle_pnl["entry_time"],
            exit_timestamp=self.current_cycle_pnl["exit_time"]
        )

        # Update daily summary
        self.daily_pnl_summary["total_cycles"] += 1
        if pnl_with_fee > 0:
            self.daily_pnl_summary["profitable_cycles"] += 1
        else:
            self.daily_pnl_summary["losing_cycles"] += 1
        self.daily_pnl_summary["total_pnl_no_fee"] += pnl_no_fee
        self.daily_pnl_summary["total_pnl_with_fee"] += pnl_with_fee
        self.daily_pnl_summary["total_fees"] += total_fees

        # Update best/worst
        if pnl_with_fee > self.daily_pnl_summary["best_cycle_pnl"]:
            self.daily_pnl_summary["best_cycle_pnl"] = pnl_with_fee
        if pnl_with_fee < self.daily_pnl_summary["worst_cycle_pnl"]:
            self.daily_pnl_summary["worst_cycle_pnl"] = pnl_with_fee

        # Clear entry state
        self.entry_prices = {"ETH": None, "SOL": None}
        self.entry_quantities = {"ETH": Decimal("0"), "SOL": Decimal("0")}
```

**Acceptance Criteria**:
- [ ] PNL calculated and logged after successful unwind
- [ ] CSV updated with all PNL metrics
- [ ] Daily summary statistics updated
- [ ] Best/worst cycle tracking updated
- [ ] Entry state cleared for next cycle

---

### Phase 4: Enhanced Logging System (3h)

#### Task 4.1: Real-time PNL Logger (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Implementation**:
```python
async def log_realtime_pnl(self):
    """실시간 PNL 로깅 (1분마다)."""
    while True:
        await asyncio.sleep(60)  # 1분마다

        if self.entry_prices["ETH"] is not None:
            # 현재 미실현 PNL 계산
            current_eth_bid, _ = await self.eth_client.fetch_bbo_prices(
                self.eth_client.config.contract_id
            )
            _, current_sol_ask = await self.sol_client.fetch_bbo_prices(
                self.sol_client.config.contract_id
            )

            # 미실현 PNL
            eth_unrealized = (current_eth_bid - self.entry_prices["ETH"]) * self.entry_quantities["ETH"]
            sol_unrealized = (self.entry_prices["SOL"] - current_sol_ask) * self.entry_quantities["SOL"]
            total_unrealized = eth_unrealized + sol_unrealized

            self.logger.info(
                f"[REALTIME PNL] Cycle {self.cycle_id} | "
                f"Unrealized: ${total_unrealized:.2f} | "
                f"ETH Entry: ${self.entry_prices['ETH']} | "
                f"SOL Entry: ${self.entry_prices['SOL']} | "
                f"Current ETH: ${current_eth_bid} | "
                f"Current SOL: ${current_sol_ask}"
            )
```

**Acceptance Criteria**:
- [ ] Method runs every 60 seconds
- [ ] Fetches current BBO prices
- [ ] Calculates unrealized PNL
- [ ] Logs with all relevant metrics

---

#### Task 4.2: Daily PNL Report (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Implementation**:
```python
def generate_daily_pnl_report(self) -> str:
    """일일 PNL 리포트 생성."""
    summary = self.daily_pnl_summary

    if summary["total_cycles"] == 0:
        return "No cycles completed today."

    avg_pnl = (
        summary["total_pnl_with_fee"] / summary["total_cycles"]
        if summary["total_cycles"] > 0 else Decimal("0")
    )

    win_rate = (
        summary["profitable_cycles"] / summary["total_cycles"] * 100
        if summary["total_cycles"] > 0 else 0
    )

    report = f"""
=== DAILY PNL REPORT ===
Date: {datetime.now().strftime('%Y-%m-%d')}
Total Cycles: {summary['total_cycles']}
Profitable: {summary['profitable_cycles']} ({win_rate:.1f}%)
Losing: {summary['losing_cycles']}

Total PNL (no fee): ${summary['total_pnl_no_fee']:.2f}
Total PNL (with fee): ${summary['total_pnl_with_fee']:.2f}
Total Fees: ${summary['total_fees']:.2f}

Best Cycle: ${summary['best_cycle_pnl']:.2f}
Worst Cycle: ${summary['worst_cycle_pnl']:.2f}
Average PNL: ${avg_pnl:.2f}
========================
"""

    return report


def log_daily_report(self):
    """일일 리포트를 로그와 파일에 기록."""
    report = self.generate_daily_pnl_report()
    self.logger.info(report)

    # Save to file
    report_path = f"logs/daily_pnl_report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_path, "w") as f:
        f.write(report)
```

**Acceptance Criteria**:
- [ ] Report includes all summary statistics
- [ ] Win rate calculated correctly
- [ ] Average PNL calculated correctly
- [ ] Report saved to dated file
- [ ] Report logged to console

---

#### Task 4.3: Spread/Slippage Analysis Log (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Implementation**:
```python
# New CSV file: logs/DN_pair_spread_analysis.csv

def log_spread_analysis(
    self,
    spread_info: Dict[str, Decimal],
    cycle_executed: bool,
    skip_reason: str = None,
    slippage_info: Dict[str, Decimal] = None
):
    """Spread/Slippage 분석 CSV 기록."""
    timestamp = datetime.now().isoformat()

    row = {
        "timestamp": timestamp,
        "eth_spread_bps": spread_info["eth_spread_bps"],
        "sol_spread_bps": spread_info["sol_spread_bps"],
        "eth_bid": spread_info["eth_bid"],
        "eth_ask": spread_info["eth_ask"],
        "sol_bid": spread_info["sol_bid"],
        "sol_ask": spread_info["sol_ask"],
        "cycle_executed": cycle_executed,
        "skip_reason": skip_reason if not cycle_executed else ""
    }

    if slippage_info:
        row.update({
            "eth_slippage_bps": slippage_info.get("eth_slippage_bps", Decimal("0")),
            "sol_slippage_bps": slippage_info.get("sol_slippage_bps", Decimal("0"))
        })

    # Write to CSV
    spread_csv_path = "logs/DN_pair_spread_analysis.csv"
    file_exists = os.path.exists(spread_csv_path)

    with open(spread_csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
```

**Acceptance Criteria**:
- [ ] New CSV file created for spread analysis
- [ ] All spread metrics logged
- [ ] Cycle execution status tracked
- [ ] Skip reasons recorded
- [ ] Slippage data included when available

---

### Phase 5: WebSocket-Based Entry/Exit Optimization (5.5h)

**User Feedback**: "우린 지금 매우 우수한 웹소켓을 갖고 있다. BBO, BookDepth 등을 이용하면 진입로직, 청산로직 최적화하면 PNL, 거래량 둘다 목표 달성 가능"

#### Task 5.1: Optimal Entry Timing using BBO (1.5h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Goal**: WebSocket BBO 실시간 스트림을 활용하여 최적 진입 타이밍 포착

**Implementation**:
```python
async def find_optimal_entry_timing(
    self,
    min_spread_bps: int = 20,
    wait_max_seconds: int = 30
) -> Tuple[bool, Dict[str, Decimal]]:
    """
    WebSocket BBO 스트림을 활용하여 최적 진입 타이밍 포착.

    Returns:
        (opportunity_found, timing_info)
    """
    start_time = time.time()
    best_spread = Decimal("0")
    best_timing_info = None

    self.logger.info("[TIMING] Scanning for optimal entry timing...")

    # WebSocket BBO 실시간 모니터링 (최대 30초)
    while time.time() - start_time < wait_max_seconds:
        # 현재 BBO 확인 (WebSocket 캐시된 데이터 사용)
        eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(
            self.eth_client.config.contract_id
        )
        sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(
            self.sol_client.config.contract_id
        )

        # Spread 계산
        eth_spread_bps = ((eth_ask - eth_bid) / eth_bid) * 10000
        sol_spread_bps = ((sol_ask - sol_bid) / sol_bid) * 10000
        avg_spread = (eth_spread_bps + sol_spread_bps) / 2

        # 최적 Spread 업데이트
        if avg_spread > best_spread:
            best_spread = avg_spread
            best_timing_info = {
                "eth_spread_bps": eth_spread_bps,
                "sol_spread_bps": sol_spread_bps,
                "eth_bid": eth_bid,
                "eth_ask": eth_ask,
                "sol_bid": sol_bid,
                "sol_ask": sol_ask,
                "elapsed_seconds": time.time() - start_time
            }

        # 최적 Spread 찾으면 즉시 진입
        if avg_spread >= min_spread_bps:
            self.logger.info(
                f"[TIMING] Optimal entry found! "
                f"Spread: {avg_spread:.1f} bps "
                f"(ETH: {eth_spread_bps:.1f}, SOL: {sol_spread_bps:.1f}) "
                f"in {time.time() - start_time:.1f}s"
            )
            return True, best_timing_info

        # 0.5초 대기 후 재확인 (WebSocket 업데이트 대기)
        await asyncio.sleep(0.5)

    # 타임아웃: 최적 Spread 찾지 못함
    self.logger.warning(
        f"[TIMING] Timeout - best spread was {best_spread:.1f} bps "
        f"(required: {min_spread_bps} bps)"
    )
    return False, best_timing_info
```

**Acceptance Criteria**:
- [ ] WebSocket BBO 실시간 데이터 사용
- [ ] 최대 30초 동안 최적 Spread 탐색
- [ ] 최적 Spread 찾으면 즉시 진입 신호
- [ ] 타임아웃 시 최고 기록된 Spread 정보 반환

---

#### Task 5.2: BookDepth-Based Position Sizing (1.5h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Enhance existing method

**Goal**: WebSocket BookDepth를 활용하여 Slippage 최소화하는 Position Size 계산

**Current Code** (`calculate_order_size_with_slippage`):
```python
# 현재: 고정 slippage (10 bps) 사용
eth_qty, eth_slippage_bps, eth_full_fill = await self.calculate_order_size_with_slippage(
    eth_price, "ETH", eth_direction, max_slippage_bps=10
)
```

**Enhanced Implementation** (using actual NadoClient API):
```python
async def calculate_optimal_position_size(
    self,
    target_notional: Decimal,
    client,  # eth_client or sol_client
    direction: str,
    max_slippage_bps: int = 10
) -> Tuple[Decimal, Decimal, bool]:
    """
    WebSocket BookDepth를 활용한 최적 Position Size 계산.

    NadoClient.get_bookdepth_handler()와 BookDepthHandler API 사용.

    Actual API:
    - client.get_bookdepth_handler() -> BookDepthHandler or None
    - handler.estimate_slippage(side, quantity) -> Decimal (bps)
    - handler.get_available_liquidity(side, max_depth) -> Decimal
    - handler.bids / handler.asks -> SortedDict (price -> quantity)

    Returns:
        (optimal_quantity, estimated_slippage_bps, sufficient_liquidity)
    """
    # Get BookDepth handler
    handler = client.get_bookdepth_handler()

    if handler is None:
        # WebSocket not available - fallback to conservative sizing
        self.logger.warning("[SIZING] BookDepth not available, using conservative sizing")
        # Use 50% of target as safety
        current_price = await self.get_current_price(client)
        target_qty = target_notional / current_price if current_price > 0 else Decimal("0")
        return target_qty * Decimal("0.5"), Decimal("20"), False

    # Determine which side of the book to use
    # IMPORTANT: estimate_slippage() expects "buy"/"sell"
    #            get_available_liquidity() expects "bid"/"ask"
    if direction == "buy":
        slippage_side = "buy"      # For estimate_slippage
        liquidity_side = "ask"     # For get_available_liquidity (use ask side liquidity)
    else:  # sell
        slippage_side = "sell"     # For estimate_slippage
        liquidity_side = "bid"     # For get_available_liquidity (use bid side liquidity)

    # Method 1: Use estimate_slippage to find max size within limit
    # Binary search for optimal quantity
    low, high = Decimal("0"), target_notional * Decimal("2")  # Start with 2x target

    for _ in range(10):  # 10 iterations enough for precision
        mid = (low + high) / 2
        mid_qty = mid / await self.get_current_price(client)

        # Use actual API: handler.estimate_slippage(side, quantity)
        slippage = handler.estimate_slippage(slippage_side, mid_qty)

        if slippage <= max_slippage_bps:
            low = mid
        else:
            high = mid

    optimal_qty = low / await self.get_current_price(client)

    # Verify with actual API
    final_slippage = handler.estimate_slippage(slippage_side, optimal_qty)

    # Check available liquidity
    available_liquidity = handler.get_available_liquidity(liquidity_side, max_depth=20)
    sufficient_liquidity = available_liquidity >= optimal_qty

    self.logger.info(
        f"[SIZING] {client.config.ticker} {direction}: "
        f"Optimal qty: {optimal_qty:.4f}, "
        f"est. slippage: {final_slippage:.1f} bps, "
        f"available liquidity: {available_liquidity:.4f}"
    )

    return optimal_qty, final_slippage, sufficient_liquidity

async def get_current_price(self, client) -> Decimal:
    """Get current price from BBO."""
    bid, ask = await client.fetch_bbo_prices(client.config.contract_id)
    return (bid + ask) / 2  # Mid price
```

**Integration with Existing Code**:
```python
# In place_simultaneous_orders - replace existing sizing logic
eth_qty, eth_slippage_bps, eth_liquidity_ok = await self.calculate_optimal_position_size(
    target_notional=self.target_notional / 2,  # Split between ETH/SOL
    client=self.eth_client,
    direction=eth_direction,
    max_slippage_bps=10
)

sol_qty, sol_slippage_bps, sol_liquidity_ok = await self.calculate_optimal_position_size(
    target_notional=self.target_notional / 2,
    client=self.sol_client,
    direction=sol_direction,
    max_slippage_bps=10
)

# Warning if liquidity insufficient
if not eth_liquidity_ok or not sol_liquidity_ok:
    self.logger.warning(
        f"[SIZING] Low liquidity - ETH: {eth_liquidity_ok}, SOL: {sol_liquidity_ok}"
    )
```

**Acceptance Criteria**:
- [ ] Uses `client.get_bookdepth_handler()` API (actual method)
- [ ] Uses `handler.estimate_slippage(side, quantity)` (actual method)
- [ ] Uses `handler.get_available_liquidity(side, max_depth)` for liquidity check
- [ ] Binary search for optimal quantity within slippage tolerance
- [ ] Fallback to conservative sizing when WebSocket unavailable
- [ ] Logging includes slippage and liquidity metrics

---

#### Task 5.3: Optimal Exit Timing with Real-time PNL (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Goal**: WebSocket 실시간 PNL 모니터링으로 최적 청산 타이밍 포착

**Implementation**:
```python
async def find_optimal_exit_timing(
    self,
    min_profit_bps: int = 10,
    max_wait_seconds: int = 60,
    loss_limit_bps: int = -30
) -> Tuple[bool, str, Dict[str, Decimal]]:
    """
    WebSocket 실시간 PNL 모니터링으로 최적 청산 타이밍 포착.

    Args:
        min_profit_bps: 최소 이익 (bps)
        max_wait_seconds: 최대 대기 시간
        loss_limit_bps: 손실 한도 (bps, 음수)

    Returns:
        (should_exit, reason, exit_info)
    """
    start_time = time.time()

    self.logger.info(
        f"[EXIT TIMING] Monitoring for optimal exit... "
        f"(min_profit: {min_profit_bps} bps, loss_limit: {loss_limit_bps} bps)"
    )

    while time.time() - start_time < max_wait_seconds:
        # 현재 PNL 계산 (실시간 BBO 사용)
        current_eth_bid, _ = await self.eth_client.fetch_bbo_prices(
            self.eth_client.config.contract_id
        )
        _, current_sol_ask = await self.sol_client.fetch_bbo_prices(
            self.sol_client.config.contract_id
        )

        # 미실현 PNL 계산
        eth_unrealized_pnl = (current_eth_bid - self.entry_prices["ETH"]) * self.entry_quantities["ETH"]
        sol_unrealized_pnl = (self.entry_prices["SOL"] - current_sol_ask) * self.entry_quantities["SOL"]
        total_unrealized_pnl = eth_unrealized_pnl + sol_unrealized_pnl

        # Entry notional
        entry_notional = (
            self.entry_prices["ETH"] * self.entry_quantities["ETH"] +
            self.entry_prices["SOL"] * self.entry_quantities["SOL"]
        )

        # PNL in bps
        pnl_bps = (total_unrealized_pnl / entry_notional) * 10000 if entry_notional > 0 else Decimal("0")

        self.logger.info(
            f"[EXIT TIMING] Unrealized PNL: {pnl_bps:.1f} bps "
            f"(${total_unrealized_pnl:.2f}) "
            f"({time.time() - start_time:.1f}s elapsed)"
        )

        # 이익 목표 달성 → 즉시 청산
        if pnl_bps >= min_profit_bps:
            self.logger.info(
                f"[EXIT TIMING] Profit target reached! "
                f"PNL: {pnl_bps:.1f} bps >= {min_profit_bps} bps"
            )
            return True, "PROFIT_TARGET", {
                "pnl_bps": pnl_bps,
                "pnl_usd": total_unrealized_pnl,
                "elapsed_seconds": time.time() - start_time
            }

        # 손실 한도 도달 → 즉시 청산 (손절)
        if pnl_bps <= loss_limit_bps:
            self.logger.warning(
                f"[EXIT TIMING] Loss limit hit! "
                f"PNL: {pnl_bps:.1f} bps <= {loss_limit_bps} bps"
            )
            return True, "LOSS_LIMIT", {
                "pnl_bps": pnl_bps,
                "pnl_usd": total_unrealized_pnl,
                "elapsed_seconds": time.time() - start_time
            }

        # 1초 대기 후 재확인
        await asyncio.sleep(1)

    # 타임아웃: 현재 상태로 청산
    self.logger.info(
        f"[EXIT TIMING] Timeout - exiting with PNL: {pnl_bps:.1f} bps"
    )
    return True, "TIMEOUT", {
        "pnl_bps": pnl_bps,
        "pnl_usd": total_unrealized_pnl,
        "elapsed_seconds": time.time() - start_time
    }
```

**Acceptance Criteria**:
- [ ] 실시간 PNL 모니터링 (WebSocket BBO)
- [ ] 이익 목표 시 즉시 청산
- [ ] 손실 한도 시 손절 청산
- [ ] 타임아웃 시 현재 상태 청산
- [ ] 청산 사유 logging

---

#### Task 5.4: Funding PNL Correction (1.5h) ⭐ NEW V5.3
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - New method

**Goal**: 펀딩 수익을 PNL에 보정하여 PNL >= 0 달성 확률 증가

**Critical Formula Fix (V5.3.1)**:
- **OLD (INCORRECT)**: `Position_Value * Funding_Rate / 365 / 24` (assumed hourly funding)
- **NEW (CORRECT)**: `Position_Value * Funding_Rate / 365 / 3` (8-hour funding interval)
- **Impact**: Previous formula was 8x too low for funding PNL calculation

**Implementation**:
```python
async def calculate_funding_pnl(
    self,
    eth_qty: Decimal,
    sol_qty: Decimal,
    eth_funding_rate: Decimal,  # yearly rate (e.g., 0.01 = 1%)
    sol_funding_rate: Decimal,
    hold_hours: Decimal
) -> Decimal:
    """
    펀딩 PNL 계산 (시간당).

    Funding PNL = Position_Value * Funding_Rate / 365 / 3

    CRITICAL: Nado Exchange uses 8-hour funding intervals (not 24-hour)
    - Formula: hourly_rate = annual_rate / 365 / 3
    - Previous error: /24 assumed hourly, correct is /3 for 8-hour intervals

    DN Pair (LONG ETH / SHORT SOL):
    - LONG ETH: rate > 0 → 수익 받음
    - SHORT SOL: rate > 0 → 수익 받음

    Returns:
        Funding PNL (USD)
    """
    # Position values
    eth_value = eth_qty * self.entry_prices["ETH"]
    sol_value = sol_qty * self.entry_prices["SOL"]

    # Hourly funding (CORRECTED: 8-hour interval, not 24-hour)
    # Funding occurs every 8 hours on Nado Exchange
    eth_hourly_funding = eth_value * eth_funding_rate / Decimal("365") / Decimal("3")
    sol_hourly_funding = sol_value * sol_funding_rate / Decimal("365") / Decimal("3")

    # LONG ETH receives, SHORT SOL pays
    total_funding_pnl = eth_hourly_funding - sol_hourly_funding

    return total_funding_pnl * hold_hours

async def get_funding_rates(self) -> Tuple[Decimal, Decimal]:
    """
    펀딩 레이트 가져오기 (REST API fallback).

    WebSocket funding_rate handler is NOT implemented yet.
    Using REST API fallback for now.

    Returns:
        (eth_funding_rate, sol_funding_rate)
    """
    try:
        # REST API: Get current funding rates
        # This is a REST fallback until WebSocket handler is implemented
        eth_funding_rate = await self._fetch_funding_rate_rest(self.eth_client.config.contract_id)
        sol_funding_rate = await self._fetch_funding_rate_rest(self.sol_client.config.contract_id)

        self.logger.info(
            f"[FUNDING] REST API rates - "
            f"ETH: {eth_funding_rate*100:.4f}%, "
            f"SOL: {sol_funding_rate*100:.4f}%"
        )

        return eth_funding_rate, sol_funding_rate

    except Exception as e:
        self.logger.warning(f"[FUNDING] REST API fetch failed: {e}, using fallback")
        # Fallback to conservative estimate
        return Decimal("0.01"), Decimal("0.01")

async def _fetch_funding_rate_rest(self, contract_id: int) -> Decimal:
    """
    REST API를 통한 펀딩 레이트 조회 (WebSocket 미구현 시 사용).

    TODO: V5.4에서 WebSocket funding_rate handler 구현 예정
    """
    # REST API endpoint call to get current funding rate
    # This is a placeholder - actual API call depends on Nado Exchange REST API
    response = await self.rest_client.get_funding_rate(contract_id)
    return Decimal(str(response["funding_rate"]))
```

**Integration with PNL Calculation**:
```python
# In execute_unwind_cycle (after position close)
hold_hours = Decimal(str(
    (self.current_cycle_pnl["exit_time"] - self.current_cycle_pnl["entry_time"]).total_seconds() / 3600
))

funding_pnl = await self.calculate_funding_pnl(
    eth_entry_qty, sol_entry_qty,
    eth_funding_rate, sol_funding_rate,
    hold_hours
)

# 보정된 PNL
final_pnl_no_fee = base_pnl_no_fee + funding_pnl
final_pnl_with_fee = base_pnl_with_fee + funding_pnl

self.logger.info(
    f"[FUNDING] Hold: {hold_hours:.2f}h | "
    f"Funding PNL: ${funding_pnl:.2f} | "
    f"ETH rate: {eth_funding_rate*100:.4f}%, "
    f"SOL rate: {sol_funding_rate*100:.4f}%"
)
```

**Acceptance Criteria**:
- [ ] 펀딩 PNL 계산 로직 구현 (CORRECTED: /3 for 8-hour interval)
- [ ] 기존 PNL에 펀딩 보정 적용
- [ ] REST API fallback로 funding_rate 가져오기
- [ ] Logging에 펀딩 기여 표시
- [ ] TODO 추가: V5.4에서 WebSocket funding_rate handler 구현

---

### Phase 6: POST_ONLY Option (2h)

#### Task 6.1: POST_ONLY Entry Mode (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `__init__` parameters

**Changes**:
```python
class DNPairBot:
    def __init__(
        self,
        ...,
        use_post_only_entry: bool = False,  # V5 추가
        post_only_timeout_seconds: int = 5,  # POST_ONLY 타임아웃
        ...
    ):
        self.use_post_only_entry = use_post_only_entry
        self.post_only_timeout_seconds = post_only_timeout_seconds
```

**Acceptance Criteria**:
- [ ] Parameter added to `__init__`
- [ ] Default is False (disabled)
- [ ] Timeout parameter configurable
- [ ] Documented in docstring

---

#### Task 6.2: POST_ONLY Order Placement (1h)
**Location**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - `place_simultaneous_orders`

**Changes**:
```python
async def place_simultaneous_orders(self, ...):
    if self.use_post_only_entry and direction == "entry":
        # Entry에 POST_ONLY 사용 (2 bps maker fee)
        self.logger.info("[POST_ONLY] Using POST_ONLY for entry orders")

        # Place limit orders with post_only=True
        eth_result = await self.place_order_with_timeout(
            self.eth_client,
            contract_id,
            qty,
            direction,
            price=limit_price,
            post_only=True,
            timeout=self.post_only_timeout_seconds
        )

        # If POST_ONLY fails/times out, fallback to IOC
        if not eth_result["filled"]:
            self.logger.warning(
                "[POST_ONLY] Entry order not filled, falling back to IOC"
            )
            eth_result = await self.eth_client.place_ioc_order(
                contract_id, qty, direction, price
            )
    else:
        # Exit에 IOC 사용 (5 bps taker fee)
        eth_result = await self.eth_client.place_ioc_order(
            contract_id, qty, direction, price
        )

    # Same for SOL...
```

**Acceptance Criteria**:
- [ ] POST_ONLY used for entry when enabled
- [ ] IOC used for exit (always)
- [ ] Timeout mechanism implemented
- [ ] Fallback to IOC if POST_ONLY fails
- [ ] Logging tracks POST_ONLY attempts

---

### Phase 7: Testing & Validation (2h)

#### Task 7.1: PNL Tracking Test
**Location**: New test file or existing test suite

**Test Cases**:
1. Entry price storage verified
2. Exit price storage verified
3. PNL calculation accuracy (manual verification)
4. CSV logging format verified
5. Daily summary statistics verified

**Acceptance Criteria**:
- [ ] 10 mock cycles executed successfully
- [ ] PNL calculations match manual calculations
- [ ] CSV contains all new columns
- [ ] Daily statistics accurate

---

#### Task 7.2: Spread Filter Test
**Location**: New test file or existing test suite

**Test Cases**:
1. Spread < 20 bps → cycle skipped
2. Spread >= 20 bps → cycle executes
3. Spread analysis CSV populated
4. Skip reasons logged correctly

**Acceptance Criteria**:
- [ ] Various spread scenarios tested
- [ ] Filter behaves correctly at boundary (20 bps)
- [ ] Analysis CSV records all checks

---

#### Task 7.3: WebSocket Optimization Test
**Location**: New test file or existing test suite

**Test Cases**:
1. Optimal entry timing finds best spread within 30 seconds
2. BookDepth position sizing reduces slippage vs fixed sizing
3. Exit timing respects profit target and loss limit
4. WebSocket fallback works when handler unavailable

**Acceptance Criteria**:
- [ ] Entry timing logic tested with mock BBO data
- [ ] Position sizing compared against baseline
- [ ] Exit timing scenarios (profit/loss/timeout) verified
- [ ] Fallback to conservative sizing when WebSocket unavailable

---

#### Task 7.4: Live Trading Test
**Location**: Production environment with small size

**Test Parameters**:
- Size: $100 (small, controlled)
- Cycles: 5 actual trades
- Duration: ~1 hour

**Acceptance Criteria**:
- [ ] 5 cycles complete successfully
- [ ] PNL tracked accurately
- [ ] WebSocket optimization active
- [ ] Real-time logging works
- [ ] Daily report generated correctly
- [ ] No liquidations or errors

---

## Verification Criteria

### Phase 1: PNL Tracking Foundation
- [ ] Entry/Exit prices stored accurately in state
- [ ] Cycle ID increments and tracks correctly
- [ ] CSV contains new columns (cycle_id, entry/exit prices, etc.)
- [ ] State cleared/reset properly between cycles

### Phase 2: Spread Filter
- [ ] Spread < 20 bps results in cycle skip
- [ ] Spread >= 20 bps allows cycle execution
- [ ] Spread values logged to console
- [ ] Spread analysis CSV created and populated

### Phase 3: PNL Calculation
- [ ] PNL calculations verified against manual computation
- [ ] Both no-fee and with-fee PNL calculated
- [ ] Fees calculated correctly (20 bps total)
- [ ] Daily summary statistics updated per cycle

### Phase 4: Enhanced Logging
- [ ] Real-time PNL logger runs every 60 seconds
- [ ] Daily report contains all required metrics
- [ ] Spread/slippage analysis CSV created
- [ ] All logs timestamped and readable

### Phase 5: WebSocket-Based Entry/Exit Optimization
- [ ] Optimal entry timing uses BBO real-time data
- [ ] Entry wait loop respects 30-second timeout
- [ ] BookDepth position sizing uses actual API
- [ ] Exit timing monitors real-time PNL
- [ ] Exit conditions (profit/loss/timeout) all tested
- [ ] WebSocket fallback verified

### Phase 6: POST_ONLY Option
- [ ] POST_ONLY mode can be enabled/disabled
- [ ] POST_ONLY orders placed for entry when enabled
- [ ] Fallback to IOC works when POST_ONLY times out
- [ ] Maker fees (2 bps) applied correctly

### Phase 7: Testing
- [ ] 10 mock cycles PNL calculations accurate
- [ ] Spread filter works at test boundaries
- [ ] WebSocket optimization tests pass
- [ ] 5 live trades complete successfully
- [ ] All verification criteria met

---

## Success Metrics

### Short-term (Week 1)
- **PNL Tracking**: 100% (all cycles tracked with entry/exit prices)
- **Spread Filter**: Active (spread < 20 bps cycles skipped)
- **Logging Coverage**: 100% (all PNL data recorded to CSV)
- **Real-time Monitoring**: Operational (unrealized PNL every 60s)

### Medium-term (Month 1)
- **PNL >= 0 Ratio**: Target: 60%+ (data-driven goal after analysis)
- **Average PNL per Cycle**: Establish baseline from collected data
- **Win Rate**: Calculate from 1000+ cycles
- **Spread Analysis**: Identify optimal spread threshold (may adjust from 20 bps)

### Long-term (Month 3)
- **PNL >= 0 Achievement**: Through data-driven optimization
- **Daily Volume**: Maintain $1,000,000
- **Trades per Day**: 100+
- **Strategy Refinement**: Based on spread/slippage analysis

---

## Effort Estimate

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| **Phase 1** | PNL State Management | 2h | None |
| **Phase 1** | Enhanced CSV Logging | 2h | None |
| **Phase 1** | State Integration | 4h | Task 1.1, 1.2 |
| **Phase 2** | Spread Filter | 2h | None |
| **Phase 2** | Spread Integration | 1h | Task 2.1 |
| **Phase 3** | PNL Calculation | 2h | None |
| **Phase 3** | PNL Logging Integration | 2h | Task 3.1, Phase 1 |
| **Phase 4** | Real-time PNL Logger | 1h | Phase 1 |
| **Phase 4** | Daily PNL Report | 1h | Phase 1, Phase 3 |
| **Phase 4** | Spread/Slippage Analysis | 1h | Phase 2 |
| **Phase 5** ⭐ | Optimal Entry Timing (BBO) | 1.5h | Phase 2 |
| **Phase 5** ⭐ | BookDepth Position Sizing | 1.5h | Phase 1 |
| **Phase 5** ⭐ | Optimal Exit Timing (PNL) | 1h | Phase 1, Phase 4 |
| **Phase 5** ⭐ | Funding PNL Correction (BUGFIX) | 1.5h | Phase 1, Phase 4 |
| **Phase 6** | POST_ONLY Entry Mode | 1h | None |
| **Phase 6** | POST_ONLY Order Placement | 1h | Task 6.1 |
| **Phase 7** | PNL Tracking Test | 0.5h | All prior phases |
| **Phase 7** | Spread Filter Test | 0.5h | Phase 2 |
| **Phase 7** ⭐ | WebSocket Opt. Test | 0.5h | Phase 5 |
| **Phase 7** | Live Trading Test | 0.5h | All prior phases |
| **Total** | | **26.5h** | |

**⭐ V5.3.1 Changes**:
- Task 5.4: Funding PNL formula bugfix (/24 → /3 for 8-hour intervals)
- Task 5.4: REST API fallback implementation (0.5h added)
- Task 5.5: REMOVED - Trend Filter deferred to V5.4 (API unconfirmed, strategy untested)
- Total effort: 27h → 26.5h (-0.5h net)

**V5.1 Fixes** (from Critic feedback):
- Fixed typo: `fetch_badio_prices` → `fetch_bbo_prices`
- Rewrote Task 5.2 to use actual `get_bookdepth_handler()` API
- Uses `handler.estimate_slippage()` and `handler.get_available_liquidity()`
- Fixed task numbering (Phase 6 POST_ONLY, Phase 7 Testing)
- Added Task 7.3 WebSocket Optimization Test

---

## Risk Mitigation

### Risk 1: PNL Tracking Errors
**Impact**: High - Incorrect PNL calculations could mislead strategy optimization
**Probability**: Medium - Complex calculations with multiple components

**Mitigation**:
- Unit tests for PNL calculation logic
- Manual verification of first 50 cycles
- Logging all intermediate calculation values
- Sanity checks (e.g., total fees should be ~0.2% of notional)

**Fallback**: If errors detected, disable PNL tracking temporarily, rely on logging for forensic analysis

---

### Risk 2: Spread Filter Excessive Skipping
**Impact**: Medium - Too few trades could reduce volume below $1M target
**Probability**: Medium - 20 bps threshold may be too conservative

**Mitigation**:
- Log all skipped cycles with spread values
- Analyze skip rate after first 100 opportunities
- Make threshold configurable (easy adjustment)
- Monitor daily trade count

**Adjustment Protocol**:
- If skip rate > 70%: Lower threshold to 15 bps
- If skip rate < 20%: Raise threshold to 25 bps
- Target: 40-60% execution rate

---

### Risk 3: POST_ONLY Order Non-Fills
**Impact**: Medium - Reduced trade frequency if many POST_ONLY orders timeout
**Probability**: High - POST_ONLY is conservative by design

**Mitigation**:
- Implement 5-second timeout (configurable)
- Automatic fallback to IOC on timeout
- Track fill rate metric
- Start with POST_ONLY disabled (default)

**Monitoring**:
- If POST_ONLY fill rate < 30%: Disable POST_ONLY
- If fill rate > 70%: Keep enabled
- Log timeout events for analysis

---

### Risk 4: State Corruption Between Cycles
**Impact**: High - Incorrect state could cause wrong PNL calculations
**Probability**: Low - Simple state management

**Mitigation**:
- Clear all entry state after UNWIND completes
- Verify state reset before next cycle
- Log state transitions
- Add assertions for state validity

---

### Risk 5: CSV Logging Failures
**Impact**: Low - Redundant logging (console + file)
**Probability**: Low - CSV writing is well-tested

**Mitigation**:
- Try-except around CSV writes
- Console logging as backup
- Verify CSV file creation on startup
- Monitor file sizes for anomalies

---

## Operational Targets

### Trading Parameters
- **Capital**: $2,000
- **Leverage**: 5× (user specified)
- **Daily Volume Target**: $1,000,000
- **Target Trades per Day**: 100+
- **Average Trade Duration**: ~10 seconds

### PNL Goals
- **Short-term (Week 1)**: Establish baseline PNL per cycle
- **Medium-term (Month 1)**: PNL >= 0 in 60%+ of cycles
- **Long-term (Month 3)**: Sustainable PNL >= 0

### Performance Monitoring
- **Real-time**: Unrealized PNL every 60 seconds
- **Per-cycle**: Entry/exit prices, PNL, fees, spread, slippage
- **Daily**: Win rate, average PNL, best/worst cycles, total fees
- **Weekly**: Trend analysis, parameter optimization recommendations

---

## Conclusion

V5 Plan implements a comprehensive PNL tracking and WebSocket-based optimization system for the DN Pair Bot, following the core philosophy: **"Install multiple logging/tracking devices → collect data → gradual improvement → achieve PNL >= 0"**.

### User's Strategic Vision
> "우린 지금 매우 우수한 웹소켓을 갖고 있다. BBO, BookDepth 등을 이용하면 진입로직, 청산로직 최적화하면 PNL, 거래량 둘다 목표 달성 가능"

This plan places WebSocket-based entry/exit optimization at the core of the PNL improvement strategy.

### Key Improvements Over V4.1
1. **PNL State Management**: Track entry/exit prices, quantities, timestamps per cycle
2. **Spread Filter**: 20 bps minimum spread to avoid unprofitable trades
3. **PNL Calculation**: Accurate no-fee and with-fee computation
4. **Enhanced Logging**: Multiple tracking devices (CSV, real-time, daily reports)
5. **Spread/Slippage Analysis**: Separate analytics for market conditions
6. **⭐ WebSocket-Based Entry Optimization**: Real-time BBO monitoring for optimal entry timing
7. **⭐ BookDepth Position Sizing**: Liquidity-aware order sizing to minimize slippage
8. **⭐ Real-Time Exit Timing**: Dynamic exit based on live PNL monitoring
9. **POST_ONLY Option**: Optional maker-only entry for reduced fees (2 bps vs 5 bps)
10. **Daily/Weekly Reports**: Performance metrics and trend analysis

### WebSocket Optimization Strategy (Phase 5 - Core Differentiator)

**Entry Optimization**:
- Real-time BBO streaming to find optimal spread moments
- Wait up to 30 seconds for best entry opportunity
- Target: Enter when spread >= 20 bps (minimum profitability)

**Position Sizing**:
- BookDepth analysis to estimate slippage
- Calculate max size within 10 bps slippage tolerance
- Adapt size to available liquidity

**Exit Optimization**:
- Real-time PNL monitoring every 1 second
- Exit on profit target (10 bps) or loss limit (-30 bps)
- Maximum 60 second wait for optimal exit

### Implementation Approach
- **Data-First**: Collect comprehensive data before making optimization decisions
- **WebSocket-Native**: Leverage existing BBO/BookDepth infrastructure
- **Incremental**: Add tracking devices first, analyze, then optimize
- **Conservative**: Preserve V4.1 stability features
- **Configurable**: All thresholds and options easily adjustable

### Next Steps
1. Review this plan
2. Adjust based on feedback
3. Begin implementation with Phase 1 (PNL Tracking Foundation)
4. Implement Phase 5 (WebSocket Optimization) as core differentiator
5. Test thoroughly in mock environment
6. Deploy to production with small size
7. Scale up as confidence increases

---

**Plan Created**: 2026-01-31
**Version**: V5.3.1 (Bugfix Revision - Formula + Scope Reduction)
**Estimated Completion**: 26.5 hours of development + testing
**Target File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
**Success Criteria**: All cycles track PNL, WebSocket optimization active, PNL >= 0 through funding correction

**V5.3.1 Changes** (Bugfix Revision):
- **Task 5.4 BUGFIX**: Funding formula corrected (/24 → /3 for 8-hour funding intervals) - CRITICAL FIX
- **Task 5.4 ENHANCED**: REST API fallback implementation added (0.5h)
- **Task 5.5 REMOVED**: Trend Filter deferred to V5.4 (API unconfirmed, strategy untested)
- **Total effort**: 27h → 26.5h (-0.5h net reduction)

---

## V5.4 Deferred Tasks (Future Work)

### Task 5.5: Trend Filter using Candles (DEFERRED from V5.3.1)

**Deferral Reason**:
- WebSocket `latest_candlestick` handler does NOT exist
- Message format undocumented (requires runtime testing)
- REST API fallback for candle data UNCONFIRMED
- 5/20 MA strategy NOT backtested for 10-second holds
- High risk for 10-second hold cycles

**Future Implementation Requirements**:
1. Confirm WebSocket `latest_candlestick` handler availability
2. Document message format (test with runtime inspection)
3. Verify REST API fallback for candle data
4. Backtest 5/20 MA strategy for 10-second hold periods
5. Validate trend filter effectiveness before production

**Estimated Effort**: 2h (when prerequisites are met)

---

### WebSocket Funding Rate Handler (DEFERRED to V5.4)

**Current State**: REST API fallback implementation in Task 5.4

**Future Enhancement**:
- Implement WebSocket `funding_rate` stream handler
- Replace REST API calls with real-time WebSocket data
- Reduce latency for funding rate updates

**Estimated Effort**: 1.5h (when API is confirmed)

---

## Architect Recommendations (Footnotes)

1. **Critical Bug Found (Task 5.4)**: Original formula used `/ 24` assuming hourly funding. Nado Exchange uses 8-hour funding intervals. Corrected formula uses `/ 3`. This was an 8x error in funding PNL calculation.

2. **WebSocket Handlers Unconfirmed**:
   - `funding_rate` handler: Does NOT exist (using REST fallback)
   - `latest_candlestick` handler: Does NOT exist (Task 5.5 deferred)
   - Message formats undocumented - requires runtime testing or external docs

3. **REST API Fallback Strategy**:
   - Task 5.4 now includes REST API implementation for funding rates
   - Candle data REST fallback UNCONFIRMED (reason for Task 5.5 deferral)

4. **Strategy Validation Gap**:
   - 5/20 MA trend filter NOT validated for 10-second holds
   - Typical MA strategies designed for longer timeframes (hours/days)
   - High risk of false signals on 10-second cycles

5. **V5.4 Recommended Approach**:
   - First confirm WebSocket handler availability
   - Document message formats via runtime testing
   - Backtest strategies for 10-second hold periods
   - Implement with confirmed APIs and validated strategies
