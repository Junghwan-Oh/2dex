# DN Bot 100 Trades Lossless - $1M Volume Plan

**Plan ID**: DN-100-LOSSLESS-001
**Created**: 2026-01-31
**Revised**: 2026-01-31 (ITERATION 2 - Critical Fixes)
**Status**: READY FOR EXECUTION
**Target File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

---

## Summary

This plan transforms the existing DN Pair Bot to achieve one clear goal:

**100 completed trades with cumulative PNL >= 0, achieving $1M trading volume**

The bot executes opportunistically (when spread filter passes) and continues until 100 trades are completed. There is NO time constraint - the bot runs for as long as needed (1-3 days depending on market conditions).

**Key Points**:
- 100 trades = $1M volume ($10,000 per trade x 100 = $1,000,000)
- 5x leverage, $2,000 margin
- Cumulative PNL must be >= 0 (lossless)
- Spread filter still applies (6 bps minimum, configurable)
- NOT time-constrained: runs until 100 trades completed

---

## User-Confirmed Math

```
Margin: $2,000
Leverage: 5x
Per-trade notional: $10,000 (ETH + SOL combined)
Trades for $1M: 100 trades ($1,000,000 / $10,000)

Goal: PNL >= 0 AND 100 trades completed = $1M volume
```

---

## Context from Previous Analysis

### Existing Plan V5.4 Status (.omc/plans/spread-filter-optimization.md)

**Implemented**:
- 6 bps spread filter (configurable via `--min-spread-bps`)
- POST_ONLY default mode (2 bps maker fee)
- Isolated margin 5x leverage
- CSV timestamp logging

**Performance Reality** (V5.4 data):
- POST_ONLY (6 bps filter): 20-40 trades/day
- IOC mode: 100+ trades/day possible
- POST_ONLY mode: Lower frequency but better fees (2 bps maker)

**Missing**:
- Trade counter (track progress toward 100)
- Cumulative PNL tracking (must stay >= 0)
- Loss limit enforcement (auto-stop if PNL < -$500)
- PNL>=0 filter (skip trades if previous PNL < 0)
- Continuous execution mode (run until 100 trades)

### Current Implementation Status

**Main Bot**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
- Lines 1-26: Imports (includes `Tuple` from typing, `pytz` needs verification)
- Lines 136-145: daily_pnl_summary initialization (NO start_time field - CRITICAL FIX NEEDED)
- Lines 896-937: Daily PNL summary update and tracking
- Lines 1025-1074: Daily PNL report generation
- Lines 1800-1814: Main alternating strategy loop (buy_first/sell_first)
- NO session persistence: State lost on bot restart

**Progressive Sizing Pattern** (Reference for Session Persistence):
- `/Users/botfarmer/2dex/hedge/helpers/progressive_sizing.py` lines 91-107
- JSON state file pattern with `_load_state()` and `_save_state()` methods
- State fields persisted: current_phase, consecutive_successes, consecutive_failures, phase_validated, pending_approval, approval_granted

**Exchange Client**: `/Users/botfarmer/2dex/hedge/exchanges/nado.py`
- Lines 86-144: Isolated margin leverage verification
- Lines 576-703: IOC order placement with 5x leverage
- Lines 501-573: POST_ONLY order placement with 5x leverage

### Test Results (IOC mode, $100 size, 3 cycles)
- Average PNL: $-0.20/cycle (losing)
- Fees: $0.21/cycle (5 bps taker)
- Leverage: 5x confirmed working

---

## Gap Analysis

### Current State vs. Required State

| Requirement | Current State | Required State | Gap |
|-------------|---------------|----------------|-----|
| **100 trades target** | No trade counter | Track progress toward 100 | Missing trade counter |
| **$1M volume tracking** | No volume tracking | Track cumulative volume | Missing volume counter |
| **Lossless trading** | Daily PNL monitoring only | Cumulative PNL >= 0 | Missing PNL filter |
| **Loss limit** | Monitor only, no auto-stop | Stop at -$500 cumulative loss | Missing enforcement |
| **Continuous execution** | Fixed iteration count | Run until 100 trades | Missing continuous mode |
| **PNL filter** | Always execute | Skip if previous PNL < 0 | Missing filter logic |

### Capital Structure (User-Confirmed)

```
Margin: $2,000
Leverage: 5x
Per-trade notional: $10,000 (ETH + SOL combined)
Volume per trade: target_notional * 2
Trades for $1M: 100 trades

Execution: Opportunistic (when spread >= 6 bps)
Duration: Until 100 trades completed (NOT time-constrained)
```

### Feasibility Analysis

| Mode | Trades/Day | Days for 100 | Fees | Notes |
|------|------------|--------------|------|-------|
| POST_ONLY (6 bps) | 20-40 | 2.5-5 days | 2 bps maker | Conservative, lossless focus |
| IOC (no filter) | 100+ | 1 day | 5 bps taker | Aggressive, faster |
| Hybrid (3-4 bps) | 40-80 | 1.25-2.5 days | Mixed | Balanced approach |

**Conclusion**: 100 trades is achievable but may take 1-5 days depending on mode and market conditions.

---

## Key Design Decisions

### Decision 1: Trade Count Target (NOT Time-Based)

**Rationale**:
- User confirmed: 100 trades with PNL >= 0
- NO time constraint - bot runs until 100 trades completed
- May take 1-3 days depending on spread filter and mode
- More realistic than forcing 100 trades in 24 hours

**Implementation**:
- Trade counter: Track completed trades toward 100
- Volume counter: Track cumulative volume toward $1M
- Auto-stop when trades >= 100 (or user stops manually)

### Decision 2: PNL Filter Behavior

**Decision**: Skip trades if previous PNL < 0 (conservative approach)

**Rationale**:
- Goal is "lossless trading" (cumulative PNL >= 0)
- Skipping losing trades preserves capital
- Can be disabled via `--disable-pnl-filter` if needed

### Decision 3: Loss Limit

**Decision**: -$500 cumulative loss limit (25% of margin)

**Calculation**:
- Margin: $2,000
- Loss limit: 25% = -$500
- If cumulative PNL < -$500, auto-stop immediately

**Formula**: `cumulative_pnl_with_fee < daily_loss_limit` -> STOP

### Decision 4: Execution Mode Selection

**User Choice Based on Market Conditions**:

**POST_ONLY Mode** (Default):
- 2 bps maker fee
- 6 bps spread filter
- 20-40 trades/day
- Lower fees, higher profit per trade
- Takes 2.5-5 days for 100 trades

**IOC Mode** (Optional):
- 5 bps taker fee
- No spread filter (or reduced)
- 100+ trades/day
- Higher fees, faster execution
- Takes ~1 day for 100 trades

**Decision**: User chooses mode based on their priorities (speed vs profitability).

---

## Work Objectives

### Core Objective

Transform the DN Pair Bot into a trade-accumulating execution engine that:
1. Executes opportunistically when spread filter passes
2. Tracks progress toward 100 completed trades
3. Maintains cumulative PNL >= 0 (lossless)
4. Achieves $1M trading volume at completion

### Deliverables

1. **Trade counter**: Count completed trades toward 100
2. **Volume tracking**: Cumulative notional counter (toward $1M)
3. **Loss limit enforcement**: Auto-stop at -$500 cumulative loss
4. **PNL-based trade filtering**: Skip trades if previous PNL < 0
5. **Continuous execution**: Run until 100 trades (not time-constrained)

### Definition of Done

- [ ] Bot runs until 100 trades completed
- [ ] Cumulative PNL >= 0 at completion (lossless)
- [ ] Achieves $1M trading volume (100 x $10,000)
- [ ] Auto-stops if cumulative loss exceeds -$500
- [ ] Progress logged every 10 trades
- [ ] All features configurable via CLI

---

## Must Have / Must NOT Have

### Must Have

1. **Trade Counter**: Count completed trades toward 100
2. **Volume Tracking**: Cumulative notional (ETH + SOL per trade)
3. **Loss Limit Auto-Stop**: Halt if cumulative_pnl_with_fee < -$500
4. **PNL Filter**: Skip trade if previous trade PNL < 0 (uses last_cycle_pnl, NOT current_cycle_pnl)
5. **Progress Logging**: Trade count and volume every 10 trades
6. **start_time Field**: Add to daily_pnl_summary initialization (PERSISTED across restarts)
7. **NO Time Constraint**: Run until 100 trades, not 24 hours
8. **Session Persistence**: JSON state file pattern (progressive_sizing.py lines 91-107)
9. **Graceful Shutdown**: Complete current BUILD + UNWIND before stopping on loss limit
10. **last_cycle_pnl Field**: Store previous trade's PNL for PNL filter (NOT current_cycle_pnl)

### Must NOT Have

1. **Fixed time duration**: NOT constrained to 24 hours
2. **Removal of safety checks**: Keep all existing position verification
3. **Ignoring spread filter**: Maintain 6 bps minimum spread check
4. **Removing POST_ONLY default**: Keep 2 bps maker fee advantage

---

## Task Flow and Dependencies

```
T1: Add 100-trades execution parameters
  ├─ Add --target-trades parameter (default 100)
  ├─ Add --volume-target-usd parameter (default 1000000)
  ├─ Add --cumulative-loss-limit parameter (default -500)
  ├─ Add --disable-pnl-filter flag (default False)
  ├─ Add --use-100-trades-mode flag (explicit strategy selection)
  ├─ Add --state-file parameter (default: logs/dn_bot_100trades_state.json)
  └─ Update constructor to accept new params
  ↓
T2: Fix daily_pnl_summary initialization and add session state
  ├─ ADD start_time field to daily_pnl_summary
  ├─ ADD last_cycle_pnl field to daily_pnl_summary (CRITICAL: use this for PNL filter, NOT current_cycle_pnl)
  ├─ Add daily_volume_usd counter
  ├─ Initialize all fields correctly
  ├─ CRITICAL FIX for missing start_time
  └─ Add state_file_path for session persistence
  ↓
T3: Implement session persistence (JSON state file pattern)
  ├─ Add _load_session_state() method (pattern from progressive_sizing.py lines 91-107)
  ├─ Add _save_session_state() method
  ├─ Persist fields: start_time, last_cycle_pnl, total_cycles, total_volume_usd, total_pnl_with_fee
  ├─ Load state on initialization if exists
  ├─ Save state after each completed trade
  ├─ Handle restart recovery (resume at trade 47 with position validation)
  └─ Add logging for state load/save operations
  ↓
T4: Implement trade and volume tracking
  ├─ Increment trade counter on each completed trade
  ├─ Volume formula: target_notional (PER POSITION, already correct)
  ├─ Add progress logging (every 10 trades)
  ├─ Add trade target completion check
  ├─ Document session-based (no reset)
  └─ Save session state after each trade
  ↓
T5: Implement loss limit enforcement with graceful shutdown
  ├─ Add _check_cumulative_loss_limit() method
  ├─ Call after each UNWIND completes (NOT during BUILD)
  ├─ Set stop_flag if limit exceeded
  ├─ Implement graceful shutdown: complete current BUILD + UNWIND before stopping
  ├─ Document loss limit formula
  ├─ Log loss limit breach with details
  └─ Handle mid-execution stop detection (check stop_flag throughout cycle)
  ↓
T6: Implement PNL-based trade filtering (FIXED data race)
  ├─ Add _should_skip_trade() method
  ├─ Check last_cycle_pnl (NOT current_cycle_pnl) before BUILD
  ├─ Log skip reason and continue
  ├─ Store completed trade PNL to last_cycle_pnl after UNWIND
  ├─ --disable-pnl-filter overrides this check
  └─ Document: last_cycle_pnl is set AFTER trade completes, not before
  ↓
T7: Implement continuous execution until 100 trades
  ├─ Add run_100_trades_strategy() method
  ├─ Check stop conditions (trades, volume, loss)
  ├─ Execute opportunistically (spread-based)
  ├─ Use --use-100-trades-mode flag for selection
  ├─ Handle graceful shutdown (complete BUILD+UNWIND)
  └─ Handle trade skips gracefully
  ↓
T8: Enhanced monitoring and logging
  ├─ Add trade count progress to PNL report
  ├─ Add completion detection (reached 100)
  ├─ Log PNL filter skips
  ├─ Document volume calculation formula (target_notional is PER POSITION)
  ├─ Log loss limit warnings
  └─ Add session recovery logging
  ↓
T9: Testing and deployment
  ├─ Verify pytz import exists
  ├─ Test session persistence (stop at trade 10, restart, resume at 11)
  ├─ Test with --target-trades 5
  ├─ Test loss limit enforcement with graceful shutdown
  ├─ Test trade and volume tracking
  ├─ Verify start_time field persists
  ├─ Verify last_cycle_pnl used for PNL filter
  └─ Deploy for 100-trade lossless run
```

---

## Detailed TODOs with Acceptance Criteria

### T1: Add 100-Trades Execution Parameters

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**CRITICAL FIXES FOR ITERATION 2**:
1. Add `--state-file` parameter for session persistence
2. Verify `pytz` import exists (add if missing)
3. Add `last_cycle_pnl` field initialization

**Step 1**: Verify/Add pytz import

**Location**: Lines 1-26 (imports section)

**BEFORE (lines 1-26)** - Check if pytz exists:
```python
import logging
import os
import asyncio
from decimal import Decimal
from typing import Tuple, List
import csv
from datetime import datetime
# ... other imports
```

**AFTER (add if missing)**:
```python
import logging
import os
import asyncio
from decimal import Decimal
from typing import Tuple, List
import csv
from datetime import datetime
import pytz  # CRITICAL: Required for start_time timezone handling
# ... other imports
```

**Step 2**: Update constructor signature

**Location**: Lines 61-71 (constructor definition)

**BEFORE (lines 61-71)**:
```python
    def __init__(
        self,
        target_notional: Decimal,  # Target USD notional for each position (e.g., 100 = $100)
        iterations: int = 20,
        sleep_time: int = 0,
        csv_path: str = None,  # Optional custom CSV path for testing
        use_post_only: bool = True,  # POST_ONLY mode (maker, 2 bps) vs IOC (taker, 5 bps)
        min_spread_bps: int = 6,  # Minimum spread in bps to enter trade (configurable)
    ):
```

**AFTER (lines 61-79)**:
```python
    def __init__(
        self,
        target_notional: Decimal,  # Target USD notional for each position (e.g., 100 = $100)
        iterations: int = 20,  # DEPRECATED: Use use_100_trades_mode for continuous execution
        sleep_time: int = 0,
        csv_path: str = None,  # Optional custom CSV path for testing
        use_post_only: bool = True,  # POST_ONLY mode (maker, 2 bps) vs IOC (taker, 5 bps)
        min_spread_bps: int = 6,  # Minimum spread in bps to enter trade (configurable)
        target_trades: int = 100,  # Target number of trades to complete (default 100)
        volume_target_usd: Decimal = Decimal("1000000"),  # Volume target in USD (default $1M)
        cumulative_loss_limit: Decimal = Decimal("-500"),  # Auto-stop if cumulative PNL < this
        disable_pnl_filter: bool = False,  # If True, don't skip trades based on previous PNL
        use_100_trades_mode: bool = False,  # If True, use 100-trades continuous strategy
        state_file: str = None,  # Session state file (default: logs/dn_bot_100trades_state.json)
    ):
```

**Step 3**: Fix daily_pnl_summary initialization (CRITICAL - ITERATION 2 FIXES)

**Location**: Lines 136-145 (daily_pnl_summary initialization)

**BEFORE (lines 136-145)**:
```python
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

**AFTER (lines 136-157)**:
```python
        # State file path for session persistence
        if state_file is None:
            self.state_file = "logs/dn_bot_100trades_state.json"
        else:
            self.state_file = state_file

        # Initialize session state (will be loaded from file if exists)
        self.daily_pnl_summary = {
            "start_time": datetime.now(pytz.UTC),  # CRITICAL: Track session start time (PERSISTED)
            "total_cycles": 0,  # Completed trades count
            "profitable_cycles": 0,
            "losing_cycles": 0,
            "total_pnl_no_fee": Decimal("0"),
            "total_pnl_with_fee": Decimal("0"),
            "total_fees": Decimal("0"),
            "best_cycle_pnl": Decimal("0"),
            "worst_cycle_pnl": Decimal("0"),
            "total_volume_usd": Decimal("0"),  # Cumulative trading volume
            "last_cycle_pnl": Decimal("0"),  # CRITICAL: Last completed trade PNL (for PNL filter, NOT current_cycle_pnl)
        }
        self.cycle_id = 0  # Unique cycle identifier

        # Load session state if exists (pattern from progressive_sizing.py lines 91-107)
        self._load_session_state()
```

**Step 3**: Store new parameters after line 87

**Location**: After order_mode logging (after line 87)

**BEFORE (lines 76-87)**:
```python
        self.target_notional = target_notional  # USD notional for each position
        self.iterations = iterations
        self.sleep_time = sleep_time
        self.use_post_only = use_post_only
        self.min_spread_bps = min_spread_bps
        self.order_mode = "post_only" if self.use_post_only else "ioc"

        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/DN_pair_eth_sol_nado_log.txt"

        # Log order mode configuration
        import logging
        self._config_logger = logging.getLogger("dn_config")
        self._config_logger.info(f"[CONFIG] Order mode: {self.order_mode.upper()} (POST_ONLY={self.use_post_only})")
        self._config_logger.info(f"[CONFIG] Min spread filter: {self.min_spread_bps} bps")
```

**AFTER (lines 76-103)**:
```python
        self.target_notional = target_notional  # USD notional for each position
        self.iterations = iterations
        self.sleep_time = sleep_time
        self.use_post_only = use_post_only
        self.min_spread_bps = min_spread_bps
        self.order_mode = "post_only" if self.use_post_only else "ioc"

        # NEW: 100-trades execution parameters
        self.target_trades = target_trades
        self.volume_target_usd = volume_target_usd
        self.cumulative_loss_limit = cumulative_loss_limit
        self.disable_pnl_filter = disable_pnl_filter
        self.use_100_trades_mode = use_100_trades_mode

        os.makedirs("logs", exist_ok=True)
        self.log_filename = f"logs/DN_pair_eth_sol_nado_log.txt"

        # Log order mode configuration
        import logging
        self._config_logger = logging.getLogger("dn_config")
        self._config_logger.info(f"[CONFIG] Order mode: {self.order_mode.upper()} (POST_ONLY={self.use_post_only})")
        self._config_logger.info(f"[CONFIG] Min spread filter: {self.min_spread_bps} bps")

        # NEW: Log 100-trades execution configuration
        if self.use_100_trades_mode:
            self._config_logger.info(f"[CONFIG] 100-TRADES mode: ENABLED")
            self._config_logger.info(f"[CONFIG] Target trades: {target_trades}")
            self._config_logger.info(f"[CONFIG] Volume target: ${volume_target_usd:.0f}")
            self._config_logger.info(f"[CONFIG] Cumulative loss limit: ${cumulative_loss_limit}")
            self._config_logger.info(f"[CONFIG] PNL filter: {'DISABLED' if disable_pnl_filter else 'ENABLED'}")
            self._config_logger.info(f"[CONFIG] Duration: Until {target_trades} trades completed (NOT time-constrained)")
```

**Step 4**: Add CLI arguments

**Location**: `parse_arguments()` function, after line 1996

**BEFORE (lines 1991-1997)**:
```python
    parser.add_argument(
        "--min-spread-bps",
        type=int,
        default=6,
        help="Minimum spread in bps to enter trade (default: 6)"
    )
    return parser.parse_args()
```

**AFTER (lines 1991-2017)**:
```python
    parser.add_argument(
        "--min-spread-bps",
        type=int,
        default=6,
        help="Minimum spread in bps to enter trade (default: 6)"
    )
    parser.add_argument(
        "--use-100-trades-mode",
        action="store_true",
        help="Enable 100-trades continuous execution mode (run until 100 trades completed)"
    )
    parser.add_argument(
        "--target-trades",
        type=int,
        default=100,
        help="Target number of trades to complete (default: 100)"
    )
    parser.add_argument(
        "--volume-target",
        type=str,
        default="1000000",
        help="Volume target in USD (default: 1000000 = $1M)"
    )
    parser.add_argument(
        "--cumulative-loss-limit",
        type=str,
        default="-500",
        help="Cumulative loss limit in USD (default: -500, auto-stop if exceeded)"
    )
    parser.add_argument(
        "--disable-pnl-filter",
        action="store_true",
        help="Disable PNL-based trade filtering (allow trades after losses)"
    )
    return parser.parse_args()
```

**Step 5**: Pass parameters in main()

**Location**: Lines 2013-2020

**BEFORE (lines 2013-2020)**:
```python
    # DNPairBot uses target_notional (USD notional per position)
    bot = DNPairBot(
        target_notional=Decimal(args.size),  # USD notional per position (e.g., 100 = $100)
        iterations=args.iter,
        sleep_time=args.sleep,
        csv_path=args.csv_path,
        use_post_only=not getattr(args, 'use_ioc', False),  # POST_ONLY mode (default True)
        min_spread_bps=getattr(args, 'min_spread_bps', 6),  # Min spread filter (default 6 bps)
    )
```

**AFTER (lines 2013-2027)**:
```python
    # DNPairBot uses target_notional (USD notional per position)
    bot = DNPairBot(
        target_notional=Decimal(args.size),  # USD notional per position (e.g., 100 = $100)
        iterations=args.iter,
        sleep_time=args.sleep,
        csv_path=args.csv_path,
        use_post_only=not getattr(args, 'use_ioc', False),  # POST_ONLY mode (default True)
        min_spread_bps=getattr(args, 'min_spread_bps', 6),  # Min spread filter (default 6 bps)
        target_trades=getattr(args, 'target_trades', 100),  # Target trade count
        volume_target_usd=Decimal(getattr(args, 'volume_target', '1000000')),  # Volume target
        cumulative_loss_limit=Decimal(getattr(args, 'cumulative_loss_limit', '-500')),  # Loss limit
        disable_pnl_filter=getattr(args, 'disable_pnl_filter', False),  # PNL filter
        use_100_trades_mode=getattr(args, 'use_100_trades_mode', False),  # 100-trades mode flag
    )
```

**Acceptance**:
- [ ] Can run: `--use-100-trades-mode` for 100-trade execution
- [ ] Can run: `--target-trades 50` for custom trade target
- [ ] Can run: `--volume-target 500000` for $500K target
- [ ] Can run: `--cumulative-loss-limit -1000` for custom loss limit
- [ ] Can run: `--disable-pnl-filter` to allow trades after losses
- [ ] start_time field added to daily_pnl_summary
- [ ] All new params logged on startup
- [ ] Backward compatible (old params still work)

---

### T2: Implement Trade and Volume Tracking

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**CRITICAL VOLUME FORMULA CLARIFICATION (ITERATION 2)**:
```
Volume Definition (ARCHITECT CONFIRMED):
- target_notional is PER POSITION (already correct)
- Example: --size 5000 means $5,000 ETH position AND $5,000 SOL position
- Total trade volume = target_notional (ETH) + target_notional (SOL) = target_notional * 2
- Formula: trade_volume_usd = target_notional * 2

Calculation Example:
- --size 5000 → $5K ETH + $5K SOL = $10,000 total volume per trade
- 100 trades → 100 * $10,000 = $1,000,000 volume

NO CHANGE NEEDED: The formula target_notional * 2 is already correct.
```

**Step 1**: Update volume on trade completion

**Location**: In `_update_daily_pnl_summary()`, after line 924

**BEFORE (lines 922-937)**:
```python
            # Accumulate totals
            self.daily_pnl_summary["total_pnl_no_fee"] += pnl_no_fee
            self.daily_pnl_summary["total_pnl_with_fee"] += pnl_with_fee
            self.daily_pnl_summary["total_fees"] += total_fees

            # Log cycle summary
            self.logger.info(
                f"[CYCLE {self.cycle_id}] PNL Summary: "
                f"NoFee=${pnl_no_fee:.2f}, WithFee=${pnl_with_fee:.2f}, "
                f"Fees=${total_fees:.2f}"
            )

            # Generate daily PNL report after each cycle
            self._generate_daily_pnl_report()

        except Exception as e:
            self.logger.error(f"[PNL] Error updating daily summary: {e}")
```

**AFTER (lines 922-970)**:
```python
            # Accumulate totals
            self.daily_pnl_summary["total_pnl_no_fee"] += pnl_no_fee
            self.daily_pnl_summary["total_pnl_with_fee"] += pnl_with_fee
            self.daily_pnl_summary["total_fees"] += total_fees

            # NEW: Update volume tracking
            # CRITICAL (ITERATION 2): target_notional is PER POSITION, so total volume = target_notional * 2
            # Example: --size 5000 → $5K ETH + $5K SOL = $10,000 total volume
            # 100 trades → 100 * $10,000 = $1,000,000 volume
            trade_volume = self.target_notional * 2
            self.daily_pnl_summary["total_volume_usd"] += trade_volume

            # NEW: Store last completed trade PNL for PNL filter (CRITICAL FIX)
            # This MUST be set AFTER trade completes, NOT before (data race fix)
            self.daily_pnl_summary["last_cycle_pnl"] = pnl_with_fee

            # Log trade summary
            self.logger.info(
                f"[TRADE {self.cycle_id}] PNL Summary: "
                f"NoFee=${pnl_no_fee:.2f}, WithFee=${pnl_with_fee:.2f}, "
                f"Fees=${total_fees:.2f}, Volume=${trade_volume:.2f}"
            )

            # NEW: Log progress every 10 trades
            if self.cycle_id % 10 == 0:
                total_volume = self.daily_pnl_summary["total_volume_usd"]
                volume_target = self.volume_target_usd
                progress_pct = (total_volume / volume_target * 100) if volume_target > 0 else 0
                trade_progress = (self.cycle_id / self.target_trades * 100) if self.target_trades > 0 else 0

                self.logger.info(
                    f"[PROGRESS] Trades: {self.cycle_id} / {self.target_trades} ({trade_progress:.1f}%) | "
                    f"Volume: ${total_volume:.0f} / ${volume_target:.0f} ({progress_pct:.1f}%) | "
                    f"PNL: ${self.daily_pnl_summary['total_pnl_with_fee']:.2f}"
                )

            # NEW: Check if trade target reached
            if self.cycle_id >= self.target_trades:
                total_volume = self.daily_pnl_summary["total_volume_usd"]
                total_pnl = self.daily_pnl_summary["total_pnl_with_fee"]
                elapsed_time = datetime.now(pytz.UTC) - self.daily_pnl_summary["start_time"]
                elapsed_hours = elapsed_time.total_seconds() / 3600

                self.logger.info(
                    f"\n{'='*60}\n"
                    f"[TARGET] TRADE TARGET ACHIEVED!\n"
                    f"  Trades: {self.cycle_id} / {self.target_trades}\n"
                    f"  Volume: ${total_volume:.0f} / ${self.volume_target_usd:.0f}\n"
                    f"  PNL: ${total_pnl:.2f} ({'LOSSLESS' if total_pnl >= 0 else 'LOSS'})\n"
                    f"  Time: {elapsed_hours:.2f} hours ({elapsed_hours/24:.1f} days)\n"
                    f"{'='*60}\n"
                )
                self.stop_flag = True

            # Generate daily PNL report after each cycle
            self._generate_daily_pnl_report()

            # NEW: Save session state after each trade (pattern from progressive_sizing.py lines 109-125)
            self._save_session_state()

        except Exception as e:
            self.logger.error(f"[PNL] Error updating daily summary: {e}")
```

**Step 2**: Add volume to daily PNL report

**Location**: In `_generate_daily_pnl_report()`, after line 1073

**BEFORE (lines 1050-1073)**:
```python
        report = {
            "total_cycles": total_cycles,
            "profitable_cycles": profitable_cycles,
            "losing_cycles": losing_cycles,
            "win_rate_pct": float(win_rate),
            "total_pnl_with_fee": float(total_pnl),
            "total_fees": float(total_fees),
            "avg_pnl_per_cycle": float(avg_pnl),
            "best_cycle_pnl": float(best_pnl),
            "worst_cycle_pnl": float(worst_pnl)
        }

        self.logger.info(
            f"[REPORT] ===== DAILY PNL SUMMARY =====\n"
            f"  Total Cycles: {total_cycles}\n"
            f"  Win Rate: {win_rate:.1f}% ({profitable_cycles}W / {losing_cycles}L)\n"
            f"  Total PNL: ${total_pnl:.2f}\n"
            f"  Total Fees: ${total_fees:.2f}\n"
            f"  Avg PNL/Cycle: ${avg_pnl:.2f}\n"
            f"  Best Cycle: ${best_pnl:.2f}\n"
            f"  Worst Cycle: ${worst_pnl:.2f}\n"
            f"================================"
        )
```

**AFTER (lines 1050-1090)**:
```python
        total_volume = summary.get("total_volume_usd", Decimal("0"))
        volume_target = self.volume_target_usd
        start_time = summary.get("start_time", datetime.now(pytz.UTC))
        elapsed_time = datetime.now(pytz.UTC) - start_time
        elapsed_hours = elapsed_time.total_seconds() / 3600

        report = {
            "total_cycles": total_cycles,
            "profitable_cycles": profitable_cycles,
            "losing_cycles": losing_cycles,
            "win_rate_pct": float(win_rate),
            "total_pnl_with_fee": float(total_pnl),
            "total_fees": float(total_fees),
            "avg_pnl_per_cycle": float(avg_pnl),
            "best_cycle_pnl": float(best_pnl),
            "worst_cycle_pnl": float(worst_pnl),
            "total_volume_usd": float(total_volume),
            "elapsed_hours": float(elapsed_hours),
        }

        volume_progress = (total_volume / volume_target * 100) if volume_target > 0 else 0
        trade_progress = (total_cycles / self.target_trades * 100) if self.target_trades > 0 else 0

        self.logger.info(
            f"[REPORT] ===== CUMULATIVE PNL SUMMARY =====\n"
            f"  Trades: {total_cycles} / {self.target_trades} ({trade_progress:.1f}%)\n"
            f"  Win Rate: {win_rate:.1f}% ({profitable_cycles}W / {losing_cycles}L)\n"
            f"  Cumulative PNL: ${total_pnl:.2f} ({'LOSSLESS' if total_pnl >= 0 else 'LOSS'})\n"
            f"  Total Fees: ${total_fees:.2f}\n"
            f"  Avg PNL/Trade: ${avg_pnl:.2f}\n"
            f"  Best Trade: ${best_pnl:.2f}\n"
            f"  Worst Trade: ${worst_pnl:.2f}\n"
            f"  Total Volume: ${total_volume:.0f} / ${volume_target:.0f} ({volume_progress:.1f}%)\n"
            f"  Elapsed Time: {elapsed_hours:.1f}h ({elapsed_hours/24:.1f} days)\n"
            f"================================"
        )
```

**Acceptance**:
- [ ] Trade counter tracks toward target_trades (default 100)
- [ ] Volume tracked cumulatively (session-based)
- [ ] Volume calculation documented: target_notional is PER POSITION (already correct)
- [ ] Progress logged every 10 trades (trade count + volume + PNL)
- [ ] Volume included in PNL report
- [ ] $1M target displayed, trade progress shown
- [ ] Celebration when trade target reached
- [ ] Elapsed time displayed in hours and days
- [ ] last_cycle_pnl stored after each trade completion (NOT current_cycle_pnl)
- [ ] Session state saved after each trade

---

### T3: Implement Session Persistence (CRITICAL - ITERATION 2 NEW TASK)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Pattern Reference**: `/Users/botfarmer/2dex/hedge/helpers/progressive_sizing.py` lines 91-125

**Step 1**: Add _load_session_state() method

**Location**: After constructor (after daily_pnl_summary initialization)

**ADD NEW METHOD**:
```python
    def _load_session_state(self) -> None:
        """
        Load saved session state from JSON file.

        Pattern from progressive_sizing.py lines 91-107.

        Restores:
        - start_time: Session start time (preserved across restarts)
        - total_cycles: Completed trades count
        - last_cycle_pnl: Last completed trade PNL (for PNL filter)
        - total_pnl_with_fee: Cumulative PNL
        - total_volume_usd: Cumulative volume
        """
        state_path = Path(self.state_file)
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)

                # Restore session start time (CRITICAL: preserved across restarts)
                if 'start_time' in state:
                    start_time_str = state['start_time']
                    self.daily_pnl_summary['start_time'] = datetime.fromisoformat(start_time_str)

                # Restore trade counters
                self.daily_pnl_summary['total_cycles'] = state.get('total_cycles', 0)
                self.cycle_id = self.daily_pnl_summary['total_cycles']

                # Restore last_cycle_pnl (CRITICAL: for PNL filter)
                if 'last_cycle_pnl' in state:
                    self.daily_pnl_summary['last_cycle_pnl'] = Decimal(str(state['last_cycle_pnl']))

                # Restore PNL totals
                if 'total_pnl_with_fee' in state:
                    self.daily_pnl_summary['total_pnl_with_fee'] = Decimal(str(state['total_pnl_with_fee']))
                if 'total_pnl_no_fee' in state:
                    self.daily_pnl_summary['total_pnl_no_fee'] = Decimal(str(state['total_pnl_no_fee']))

                # Restore volume
                if 'total_volume_usd' in state:
                    self.daily_pnl_summary['total_volume_usd'] = Decimal(str(state['total_volume_usd']))

                # Restore other fields
                self.daily_pnl_summary['profitable_cycles'] = state.get('profitable_cycles', 0)
                self.daily_pnl_summary['losing_cycles'] = state.get('losing_cycles', 0)
                self.daily_pnl_summary['total_fees'] = Decimal(str(state.get('total_fees', '0')))
                self.daily_pnl_summary['best_cycle_pnl'] = Decimal(str(state.get('best_cycle_pnl', '0')))
                self.daily_pnl_summary['worst_cycle_pnl'] = Decimal(str(state.get('worst_cycle_pnl', '0')))

                self.logger.info(
                    f"[SESSION] Loaded state from {state_path}\n"
                    f"  Resuming at trade {self.cycle_id}\n"
                    f"  Start time: {self.daily_pnl_summary['start_time'].isoformat()}\n"
                    f"  Cumulative PNL: ${self.daily_pnl_summary['total_pnl_with_fee']:.2f}\n"
                    f"  Total volume: ${self.daily_pnl_summary['total_volume_usd']:.0f}\n"
                    f"  Last trade PNL: ${self.daily_pnl_summary['last_cycle_pnl']:.2f}"
                )

            except Exception as e:
                self.logger.warning(f"[SESSION] Failed to load session state: {e}")
                self.logger.info("[SESSION] Starting fresh session")
```

**Step 2**: Add _save_session_state() method

**Location**: After _load_session_state()

**ADD NEW METHOD**:
```python
    def _save_session_state(self) -> None:
        """
        Save current session state to JSON file.

        Pattern from progressive_sizing.py lines 109-125.

        Saves:
        - start_time: Session start time (for restart recovery)
        - total_cycles: Completed trades count
        - last_cycle_pnl: Last completed trade PNL (for PNL filter)
        - total_pnl_with_fee: Cumulative PNL
        - total_volume_usd: Cumulative volume
        """
        state = {
            'start_time': self.daily_pnl_summary['start_time'].isoformat(),
            'total_cycles': self.daily_pnl_summary['total_cycles'],
            'last_cycle_pnl': str(self.daily_pnl_summary['last_cycle_pnl']),
            'total_pnl_with_fee': str(self.daily_pnl_summary['total_pnl_with_fee']),
            'total_pnl_no_fee': str(self.daily_pnl_summary['total_pnl_no_fee']),
            'total_fees': str(self.daily_pnl_summary['total_fees']),
            'total_volume_usd': str(self.daily_pnl_summary['total_volume_usd']),
            'profitable_cycles': self.daily_pnl_summary['profitable_cycles'],
            'losing_cycles': self.daily_pnl_summary['losing_cycles'],
            'best_cycle_pnl': str(self.daily_pnl_summary['best_cycle_pnl']),
            'worst_cycle_pnl': str(self.daily_pnl_summary['worst_cycle_pnl']),
            'last_updated': datetime.now(pytz.UTC).isoformat(),
        }

        try:
            # Ensure directory exists
            state_path = Path(self.state_file)
            state_path.parent.mkdir(parents=True, exist_ok=True)

            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)

            self.logger.debug(f"[SESSION] Saved state to {state_path}")

        except Exception as e:
            self.logger.error(f"[SESSION] Failed to save session state: {e}")
```

**Step 3**: Add imports for JSON and Path

**Location**: Lines 1-26 (imports section)

**VERIFY imports exist**:
```python
import json  # For session state persistence
from pathlib import Path  # For file path handling
```

**ADD if missing**.

**Acceptance**:
- [ ] Session state loaded from JSON file on startup (pattern from progressive_sizing.py)
- [ ] start_time preserved across restarts (bot restart resumes with original start time)
- [ ] last_cycle_pnl preserved across restarts (PNL filter works after restart)
- [ ] total_cycles restored (resume at trade 47, not start at 0)
- [ ] Session state saved after each completed trade
- [ ] State file created in logs directory
- [ ] Logging shows session recovery on restart
- [ ] Position validation on restart (verify no residual positions before resuming)

---

### T4: Implement Cumulative Loss Limit Enforcement with Graceful Shutdown (ITERATION 2 UPDATE)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Loss Limit Formula**:
```
Stop condition: cumulative_pnl_with_fee < cumulative_loss_limit

Example:
- cumulative_loss_limit = -500
- If cumulative_pnl_with_fee = -600, then -600 < -500 → STOP
- If cumulative_pnl_with_fee = -400, then -400 < -500 → CONTINUE

GRACEFUL SHUTDOWN (ITERATION 2):
- If loss limit hit during BUILD phase: Complete BUILD → Complete UNWIND → Stop
- Stop flag checked throughout cycle execution
- No premature termination during position holding
```

**Step 1**: Add loss limit check method (with graceful shutdown documentation)

**Location**: After `_generate_daily_pnl_report()` (after line 1090)

**ADD NEW METHOD**:
```python
    def _check_cumulative_loss_limit(self) -> bool:
        """
        Check if cumulative loss limit has been exceeded.

        Loss Limit Formula:
            Stop if: cumulative_pnl_with_fee < cumulative_loss_limit

        Example:
            cumulative_loss_limit = -500
            If PNL = -600: -600 < -500 → STOP (loss exceeded)
            If PNL = -400: -400 < -500 → CONTINUE (within limit)

        GRACEFUL SHUTDOWN (ITERATION 2):
            - If limit exceeded: Set stop_flag = True
            - stop_flag checked BEFORE each new trade (in run_100_trades_strategy)
            - If already in BUILD phase: Complete BUILD → Complete UNWIND → Stop
            - No premature termination during position holding

        Returns:
            bool: True if within limit, False if limit exceeded

        Side Effects:
            Sets self.stop_flag = True if limit exceeded
        """
        total_pnl = self.daily_pnl_summary.get("total_pnl_with_fee", Decimal("0"))
        loss_limit = self.cumulative_loss_limit

        # Check if loss limit exceeded
        if total_pnl < loss_limit:
            total_cycles = self.daily_pnl_summary.get("total_cycles", 0)
            self.logger.error(
                f"[LOSS LIMIT] CUMULATIVE LOSS LIMIT EXCEEDED!\n"
                f"  Cumulative PNL: ${total_pnl:.2f}\n"
                f"  Loss Limit: ${loss_limit:.2f}\n"
                f"  Formula: {total_pnl} < {loss_limit} = TRUE\n"
                f"  Trades: {total_cycles}\n"
                f"  Action: Setting stop_flag (graceful shutdown: complete current cycle)"
            )
            self.stop_flag = True
            return False

        # Log warning if approaching limit (within 20%)
        warning_threshold = loss_limit * Decimal("0.8")  # 80% of limit
        if total_pnl < warning_threshold:
            remaining_loss = loss_limit - total_pnl
            self.logger.warning(
                f"[LOSS LIMIT] Approaching cumulative loss limit!\n"
                f"  Current PNL: ${total_pnl:.2f}\n"
                f"  Loss Limit: ${loss_limit:.2f}\n"
                f"  Remaining: ${remaining_loss:.2f} before auto-stop"
            )

        return True
```

**Step 2**: Call loss limit check after each trade

**Location**: In `_update_daily_pnl_summary()`, after generating report

**BEFORE (lines 933-937)**:
```python
            # Generate daily PNL report after each cycle
            self._generate_daily_pnl_report()

        except Exception as e:
            self.logger.error(f"[PNL] Error updating daily summary: {e}")
```

**AFTER (lines 965-971)**:
```python
            # Generate daily PNL report after each cycle
            self._generate_daily_pnl_report()

            # NEW: Check cumulative loss limit after each trade
            self._check_cumulative_loss_limit()

        except Exception as e:
            self.logger.error(f"[PNL] Error updating daily summary: {e}")
```

**Acceptance**:
- [ ] Loss limit formula documented in code
- [ ] Loss limit checked after each completed trade
- [ ] Bot sets stop_flag when limit exceeded
- [ ] Formula logged when limit breached
- [ ] Warning logged when approaching limit (within 20%)
- [ ] Loss limit configurable via `--cumulative-loss-limit`
- [ ] Graceful shutdown: stop_flag checked before each new trade
- [ ] Mid-execution stop handling: Complete BUILD+UNWIND before stopping
- [ ] No premature termination during position holding

---

### T5: Implement PNL-Based Trade Filtering (ITERATION 2 DATA RACE FIX)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**CRITICAL DATA RACE FIX (ITERATION 2)**:
```
OLD BUG (Iteration 1):
  PNL filter checked current_cycle_pnl, which is reset BEFORE the filter check
  Result: Always sees 0, filter never activates

FIX (Iteration 2):
  1. Store completed trade PNL in last_cycle_pnl field
  2. PNL filter checks last_cycle_pnl (NOT current_cycle_pnl)
  3. last_cycle_pnl is set AFTER trade completes (in _update_daily_pnl_summary)
  4. Data race eliminated: last_cycle_pnl contains previous trade's result

Sequence:
  Trade 47 completes → PNL = $5 → last_cycle_pnl = $5
  Trade 48 starts → Check last_cycle_pnl ($5 >= 0, allow)
  Trade 48 completes → PNL = -$3 → last_cycle_pnl = -$3
  Trade 49 starts → Check last_cycle_pnl (-$3 < 0, SKIP)
```

**Note**: `Tuple` is already imported on line 23: `from typing import Tuple, List`

**Step 1**: Add PNL filter check method (FIXED)

**Location**: After `_check_cumulative_loss_limit()` (new method from T4)

**ADD NEW METHOD**:
```python
    def _should_skip_trade(self) -> Tuple[bool, str]:
        """
        Check if current trade should be skipped based on previous PNL.

        CRITICAL FIX (ITERATION 2): Uses last_cycle_pnl, NOT current_cycle_pnl

        PNL Filter Rule:
            Skip if: last_cycle_pnl < 0 (previous trade was a loss)

        Data Flow:
        1. Trade 47 completes → _update_daily_pnl_summary() sets last_cycle_pnl = trade_pnl
        2. Trade 48 starts → _should_skip_trade() checks last_cycle_pnl
        3. If last_cycle_pnl < 0 → Skip trade 48
        4. If last_cycle_pnl >= 0 → Allow trade 48

        This eliminates the data race where current_cycle_pnl was reset before the check.

        Returns:
            Tuple[bool, str]: (should_skip, reason)

        Rules:
        - Skip if last_cycle_pnl < 0 (previous trade was a loss)
        - Don't skip on first trade (no previous PNL)
        - Don't skip if PNL filter disabled via --disable-pnl-filter
        """
        # Skip check if filter disabled
        if self.disable_pnl_filter:
            return False, ""

        # Don't skip first trade (no previous PNL to check)
        if self.cycle_id == 0:
            return False, ""

        # CRITICAL FIX (ITERATION 2): Check last_cycle_pnl, NOT current_cycle_pnl
        # last_cycle_pnl is set in _update_daily_pnl_summary() AFTER each trade completes
        prev_pnl = self.daily_pnl_summary.get("last_cycle_pnl", Decimal("0"))

        if prev_pnl < 0:
            reason = (
                f"[PNL FILTER] Skipping trade after loss:\n"
                f"  Last trade PNL: ${prev_pnl:.2f}\n"
                f"  Action: Waiting for next opportunity\n"
                f"  Override: Use --disable-pnl-filter to disable"
            )
            return True, reason

        return False, ""
```

**Step 2**: Check PNL filter before each BUILD

**Location**: In `execute_buy_first_cycle()` and `execute_sell_first_cycle()`

**For execute_buy_first_cycle()** (around line 1698):

**BEFORE (lines 1696-1704)**:
```python
    async def execute_buy_first_cycle(self) -> bool:
        """Execute BUY_FIRST cycle: BUILD (Long ETH / Short SOL) -> UNWIND."""
        # Increment cycle_id for PNL tracking
        self.cycle_id += 1

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"BUY_FIRST CYCLE {self.cycle_id}")
        self.logger.info(f"{'='*60}")
```

**AFTER (lines 1696-1710)**:
```python
    async def execute_buy_first_cycle(self) -> bool:
        """Execute BUY_FIRST cycle: BUILD (Long ETH / Short SOL) -> UNWIND."""
        # Increment cycle_id for PNL tracking
        self.cycle_id += 1

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"BUY_FIRST TRADE {self.cycle_id}")
        self.logger.info(f"{'='*60}")

        # NEW: Check PNL filter before BUILD
        should_skip, skip_reason = self._should_skip_trade()
        if should_skip:
            self.logger.warning(skip_reason)
            return False  # Skip this trade
```

**For execute_sell_first_cycle()** (around line 1760):

**BEFORE (lines 1760-1768)**:
```python
    async def execute_sell_first_cycle(self) -> bool:
        """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND."""
        # Increment cycle_id for PNL tracking
        self.cycle_id += 1

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"SELL_FIRST CYCLE {self.cycle_id}")
        self.logger.info(f"{'='*60}")
```

**AFTER (lines 1760-1772)**:
```python
    async def execute_sell_first_cycle(self) -> bool:
        """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND."""
        # Increment cycle_id for PNL tracking
        self.cycle_id += 1

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"SELL_FIRST TRADE {self.cycle_id}")
        self.logger.info(f"{'='*60}")

        # NEW: Check PNL filter before BUILD
        should_skip, skip_reason = self._should_skip_trade()
        if should_skip:
            self.logger.warning(skip_reason)
            return False  # Skip this trade
```

**Acceptance**:
- [ ] Trade skipped if last_cycle_pnl < 0 (NOT current_cycle_pnl)
- [ ] Skip logged with reason
- [ ] First trade never skipped
- [ ] Filter disabled via `--disable-pnl-filter`
- [ ] Tuple import already exists (line 23)
- [ ] Data race eliminated: last_cycle_pnl contains previous trade result
- [ ] last_cycle_pnl set AFTER trade completes (in _update_daily_pnl_summary)

---

### T6: Implement 100-Trades Continuous Execution (ITERATION 2 UPDATE)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Step 1**: Add new 100-trades strategy runner

**Location**: After `run_alternating_strategy()` (after line 1820)

**ADD NEW METHOD**:
```python
    async def run_100_trades_strategy(self) -> None:
        """
        Run 100-trades trading strategy with opportunistic execution.

        Executes when spread filter passes (not time-based).
        Continues until 100 trades completed.

        Features:
        - Opportunistic execution (spread-based, not time-based)
        - PNL-based trade filtering (skip after losses using last_cycle_pnl)
        - Cumulative loss limit enforcement (auto-stop with graceful shutdown)
        - Volume tracking and reporting (session-based)
        - NO time constraint: runs until 100 trades
        - Session persistence: Resume from state file after restart

        Stop Conditions:
        1. Trade target reached (trades >= target_trades)
        2. Cumulative loss limit exceeded (PNL < cumulative_loss_limit)
        3. Stop flag set (manual or automatic)

        GRACEFUL SHUTDOWN (ITERATION 2):
        - Stop flag checked BEFORE each new trade
        - If stop_flag set during BUILD: Complete BUILD → Complete UNWIND → Exit
        - No premature termination during position holding
        """
        import time

        self.logger.info(
            f"[100-TRADES] Starting 100-trades execution:\n"
            f"  Target trades: {self.target_trades}\n"
            f"  Volume target: ${self.volume_target_usd:.0f}\n"
            f"  Cumulative loss limit: ${self.cumulative_loss_limit}\n"
            f"  PNL filter: {'OFF' if self.disable_pnl_filter else 'ON'}\n"
            f"  Execution: Opportunistic (spread-based)\n"
            f"  Duration: Until {self.target_trades} trades completed (NOT time-constrained)\n"
            f"  Session: {self.daily_pnl_summary['start_time'].isoformat()}"
        )

        start_time = time.time()
        trade_count = 0
        consecutive_skips = 0

        while not self.stop_flag:
            # Check stop flag
            if self.stop_flag:
                self.logger.info("[100-TRADES] Stop flag set, exiting...")
                break

            # Execute alternating trade (opportunistic)
            try:
                # Check PNL filter before attempting trade
                should_skip, skip_reason = self._should_skip_trade()
                if should_skip:
                    self.logger.warning(skip_reason)
                    consecutive_skips += 1
                    # Wait before retrying (don't spam spread checks)
                    await asyncio.sleep(10)
                    continue

                # Execute trade
                if trade_count % 2 == 0:
                    result = await self.execute_buy_first_cycle()
                else:
                    result = await self.execute_sell_first_cycle()

                if result:
                    consecutive_skips = 0
                    trade_count += 1
                else:
                    # Trade was skipped or failed
                    consecutive_skips += 1

                if consecutive_skips > 20:
                    self.logger.warning(
                        f"[100-TRADES] {consecutive_skips} consecutive skips/failures. "
                        f"Check market conditions or spread filter settings."
                    )

            except Exception as e:
                self.logger.error(f"[100-TRADES] Trade failed with error: {e}")
                consecutive_skips += 1

        # Final summary
        total_runtime_hours = (time.time() - start_time) / 3600
        total_volume = self.daily_pnl_summary.get("total_volume_usd", Decimal("0"))
        total_pnl = self.daily_pnl_summary.get("total_pnl_with_fee", Decimal("0"))
        volume_target_pct = (total_volume / self.volume_target_usd * 100) if self.volume_target_usd > 0 else 0
        trade_target_pct = (trade_count / self.target_trades * 100) if self.target_trades > 0 else 0

        self.logger.info(
            f"\n{'='*60}\n"
            f"[100-TRADES] Execution Complete:\n"
            f"  Runtime: {total_runtime_hours:.1f}h ({total_runtime_hours/24:.1f} days)\n"
            f"  Trades: {trade_count} / {self.target_trades} ({trade_target_pct:.1f}%)\n"
            f"  Volume: ${total_volume:.0f} / ${self.volume_target_usd:.0f} ({volume_target_pct:.1f}%)\n"
            f"  Cumulative PNL: ${total_pnl:.2f} ({'LOSSLESS' if total_pnl >= 0 else 'LOSS'})\n"
            f"{'='*60}\n"
        )
```

**Step 2**: Update main() to use 100-trades strategy

**Location**: Line 2046

**BEFORE (lines 2043-2048)**:
```python
    print("[STARTUP] No residual positions. Ready to start.\n")

    # Run alternating strategy
    await bot.run_alternating_strategy()


if __name__ == "__main__":
```

**AFTER (lines 2043-2052)**:
```python
    print("[STARTUP] No residual positions. Ready to start.\n")

    # Choose strategy based on --use-100-trades-mode flag
    if bot.use_100_trades_mode:
        # Use 100-trades strategy for continuous execution
        await bot.run_100_trades_strategy()
    else:
        # Use alternating strategy for short test runs
        await bot.run_alternating_strategy()


if __name__ == "__main__":
```

**Acceptance**:
- [ ] Trades execute opportunistically (not time-based)
- [ ] NO time constraint (runs until 100 trades)
- [ ] Trade target checked after each trade
- [ ] Stop flag checked before each trade (graceful shutdown)
- [ ] Final summary logged with runtime, trades, volume, PNL
- [ ] Strategy selected via explicit --use-100-trades-mode flag
- [ ] Session start time logged
- [ ] Session recovery logged (resuming at trade X)

---

### T7: Enhanced Monitoring and Logging (T6 renamed to T7)

**File**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Step 1**: Add volume statistics method

**ADD NEW METHOD** (after `run_100_trades_strategy()`):
```python
    def _get_volume_stats(self) -> dict:
        """
        Calculate volume statistics for monitoring.

        Volume Calculation (ITERATION 2 CLARIFIED):
            target_notional is PER POSITION
            Total volume = target_notional * 2 (ETH + SOL)
            Example: --size 5000 → $5K ETH + $5K SOL = $10K total volume

        Returns:
            dict with volume metrics
        """
        total_trades = self.daily_pnl_summary.get("total_cycles", 0)
        total_volume = self.daily_pnl_summary.get("total_volume_usd", Decimal("0"))
        volume_target = self.volume_target_usd

        return {
            "total_trades": total_trades,
            "target_trades": self.target_trades,
            "total_volume_usd": float(total_volume),
            "volume_target_usd": float(volume_target),
            "volume_progress_pct": float((total_volume / volume_target * 100) if volume_target > 0 else 0),
            "avg_volume_per_trade": float((total_volume / total_trades) if total_trades > 0 else 0),
            "remaining_volume": float(max(Decimal("0"), volume_target - total_volume)),
        }
```

**Acceptance**:
- [ ] Volume statistics available for monitoring
- [ ] Volume calculation formula documented (target_notional is PER POSITION)
- [ ] PNL filter skips logged separately
- [ ] Loss limit warnings logged
- [ ] Session recovery logged

---

### T8: Testing and Deployment (ITERATION 2 WITH SESSION RECOVERY TESTS)
- [ ] PNL filter skips logged separately
- [ ] Loss limit warnings logged

---

### T9: Testing and Deployment (ITERATION 2 WITH SESSION RECOVERY TESTS)

**Step 1: Verify pytz import and start_time field**

```bash
cd /Users/botfarmer/2dex/hedge

# Check that pytz is imported
python -c "
import DN_pair_eth_sol_nado
print('pytz imported:', 'pytz' in dir(DN_pair_eth_sol_nado))
"

# Check that start_time field exists in daily_pnl_summary
python -c "
from DN_pair_eth_sol_nado import DNPairBot
from decimal import Decimal
bot = DNPairBot(target_notional=Decimal('100'))
print('start_time in daily_pnl_summary:', 'start_time' in bot.daily_pnl_summary)
print('start_time value:', bot.daily_pnl_summary.get('start_time'))
print('last_cycle_pnl in daily_pnl_summary:', 'last_cycle_pnl' in bot.daily_pnl_summary)
"
```

**Expected**: `True` for all checks, datetime object for start_time

**Step 2: Test session persistence (NEW - ITERATION 2)**

```bash
# Test 1: Run 10 trades, stop, restart, verify resume
cd /Users/botfarmer/2dex/hedge

# First run: 10 trades
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 10 \
    --cumulative-loss-limit -1000

# Check state file created
cat logs/dn_bot_100trades_state.json

# Second run: Should resume at trade 11 with same start_time
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 20 \
    --cumulative-loss-limit -1000
```

**Expected**:
- State file created: `logs/dn_bot_100trades_state.json`
- First run stops at trade 10
- Second run logs: "Resuming at trade 10"
- Second run continues to trade 20
- start_time preserved from first run

**Step 3: Test with 5 trades**

```bash
# Test 5-trade run to verify tracking
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 5 \
    --cumulative-loss-limit -100
```

**Expected**:
- Execute until 5 trades completed
- ~$50K volume (5 x $10,000)
- Progress logged every 10 trades (will show at completion)
- Auto-stop at -$100 cumulative loss
- State saved after each trade

**Step 4: Test volume tracking**

```bash
# Run until 20 trades to verify tracking
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 20 \
    --cumulative-loss-limit -200
```

**Expected**:
- Bot stops when 20 trades completed
- Volume progress logged every 10 trades
- Celebration message when target reached
- Elapsed time displayed
- Volume formula: target_notional is PER POSITION (already correct)

**Step 5: Test loss limit with graceful shutdown (NEW - ITERATION 2)**

```bash
# Test graceful shutdown: Simulate losses during BUILD phase
python DN_pair_eth_sol_nado.py \
    --size 100 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 50 \
    --cumulative-loss-limit -20 \
    --use-ioc  # IOC mode for faster execution
```

**Expected**:
- If loss limit hit during BUILD: Complete BUILD → Complete UNWIND → Stop
- Bot stops when cumulative PNL < -$20
- Loss limit formula logged
- Loss limit breach logged with graceful shutdown message
- No premature termination during position holding

**Step 6: Test PNL filter with data race fix (NEW - ITERATION 2)**

```bash
# Test PNL filter: verify last_cycle_pnl is used (not current_cycle_pnl)
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 10 \
    --cumulative-loss-limit -1000
```

**Expected**:
- Trade skipped if last_cycle_pnl < 0
- Skip logged: "Last trade PNL: -$X.XX"
- No data race: last_cycle_pnl contains previous trade result
- First trade never skipped

**Step 7: Production 100-trade run**

```bash
# Full 100-trade lossless run for $1M volume
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 1 \
    --use-100-trades-mode \
    --target-trades 100 \
    --cumulative-loss-limit -500
```

**Expected**:
- Run until 100 trades completed
- $1M volume at completion (100 x $10,000)
- Realistic duration: 2.5-5 days with POST_ONLY + 6 bps
- Cumulative PNL >= 0 at completion (lossless)
- Final volume percentage displayed
- Session can be resumed after restart

**Acceptance**:
- [ ] pytz import verified
- [ ] start_time field verified to exist
- [ ] last_cycle_pnl field verified to exist
- [ ] Session persistence tested (stop at 10, restart, resume at 11)
- [ ] Dry run completes without errors
- [ ] Volume tracking accurate (target_notional is PER POSITION)
- [ ] Loss limit enforced correctly with graceful shutdown
- [ ] PNL filter uses last_cycle_pnl (no data race)
- [ ] Formula documented in logs
- [ ] 100-trade run reports actual vs target

---

## Risk Management (ITERATION 2 UPDATES)

### Safety Mechanisms

1. **Cumulative Loss Limit Auto-Stop**
   - Configurable via `--cumulative-loss-limit`
   - Default: -$500 (25% of $2,000 margin)
   - Formula: `cumulative_pnl_with_fee < cumulative_loss_limit` → STOP
   - Checked after every completed trade
   - Warning at 80% of limit

2. **PNL Filter (ITERATION 2 FIX)**
   - Skips trades after losses (uses last_cycle_pnl, NOT current_cycle_pnl)
   - Preserves capital for recovery
   - Can be disabled with `--disable-pnl-filter`
   - Data race eliminated: last_cycle_pnl contains previous trade result

3. **Position Verification**
   - BUILD verification: Ensures positions opened correctly
   - UNWIND verification: Ensures positions closed completely
   - Residual position check at startup
   - Position validation on restart recovery

4. **Spread Filter**
   - 6 bps minimum spread (configurable)
   - Prevents unprofitable entries
   - Works with POST_ONLY for 2 bps maker fee

5. **Trade Target Completion**
   - Auto-stops when 100 trades reached
   - Prevents over-trading
   - Celebrates achievement

6. **Session Persistence (NEW - ITERATION 2)**
   - State saved to JSON file after each trade
   - Resume after restart without losing progress
   - start_time preserved across restarts
   - last_cycle_pnl preserved for PNL filter
   - Position validation before resuming

7. **Graceful Shutdown (NEW - ITERATION 2)**
   - Stop flag checked before each new trade
   - Complete current BUILD + UNWIND before stopping
   - No premature termination during position holding

### Mitigation Strategies (ITERATION 2 UPDATES)

| Risk | Mitigation |
|------|------------|
| **100 trades takes too long** | User chooses mode: POST_ONLY (2-5 days) or IOC (~1 day) |
| **Insufficient spread opportunities** | No time constraint, wait for quality setups |
| **Spread filter too strict** | Use `--min-spread-bps 3` for more opportunities |
| **Partial fills** | POST_ONLY mode with position verification |
| **Network issues** | Retry logic in order placement (3-5 retries) |
| **Exchange downtime** | Stop flag checked before each trade |
| **Cumulative loss breach** | Auto-stop with graceful shutdown (complete current cycle) |
| **Lossless requirement not met** | PNL filter helps, but no guarantee |
| **Bot restart loses progress** | Session persistence: Resume from JSON state file |
| **PNL filter data race** | FIXED: Uses last_cycle_pnl (set after trade completes) |
| **Mid-execution stop risk** | Graceful shutdown: Complete BUILD+UNWIND before stopping |

### Mode Selection Guide

**POST_ONLY Mode** (Conservative, Lossless Focus):
- 2 bps maker fee
- 6 bps spread filter
- 20-40 trades/day
- Duration: 2.5-5 days for 100 trades
- Best for: Lossless priority, lower fees

**IOC Mode** (Aggressive, Speed Priority):
- 5 bps taker fee
- No spread filter (or reduced)
- 100+ trades/day
- Duration: ~1 day for 100 trades
- Best for: Speed priority, higher volume

---

## Verification

### Pre-Deployment Checklist (ITERATION 2 UPDATES)

- [ ] All code changes reviewed
- [ ] pytz import verified (required for start_time timezone handling)
- [ ] start_time field added to daily_pnl_summary (PERSISTED across restarts)
- [ ] last_cycle_pnl field added to daily_pnl_summary (for PNL filter)
- [ ] Volume calculation formula documented (target_notional is PER POSITION)
- [ ] Cumulative loss limit formula documented
- [ ] Tuple import verified (line 23)
- [ ] JSON and Path imports verified (for session persistence)
- [ ] Session persistence tested (stop at 10, restart, resume at 11)
- [ ] Loss limit tested with dry run and graceful shutdown
- [ ] PNL filter tested with data race fix (uses last_cycle_pnl)
- [ ] Volume tracking verified
- [ ] PNL filter tested (enable/disable)
- [ ] CSV logging checked
- [ ] Backup created: `cp DN_pair_eth_sol_nado.py DN_pair_eth_sol_nado.py.v6.2.backup`

### Runtime Monitoring

**Every 10 trades** (automatic):
- Trade count progress vs 100
- Volume progress vs $1M
- Cumulative PNL vs loss limit
- Elapsed time
- Session state saved to JSON

**Manual checks** (daily):
```bash
# Check trade progress
tail -50 logs/DN_pair_eth_sol_nado_log.txt | grep "PROGRESS"

# Check PNL
tail -50 logs/DN_pair_eth_sol_nado_log.txt | grep "REPORT"

# Check loss limit
tail -50 logs/DN_pair_eth_sol_nado_log.txt | grep "LOSS LIMIT"

# Check session state
cat logs/dn_bot_100trades_state.json

# Check for errors
tail -100 logs/DN_pair_eth_sol_nado_log.txt | grep -i "error\|warning"
```

### Success Criteria (ITERATION 2 UPDATES)

- [ ] **100 trades completed** (primary objective)
- [ ] **$1M volume achieved** (100 x $10,000)
- [ ] **Cumulative PNL >= 0** (lossless trading)
- [ ] **No manual intervention** (auto-handled all situations)
- [ ] **Clean shutdown** (no residual positions)
- [ ] **Opportunistic execution** (not time-based)
- [ ] **start_time field exists** and used for elapsed time
- [ ] **Session persistence works** (resume after restart)
- [ ] **PNL filter uses last_cycle_pnl** (no data race)

---

## Rollback Plan

### Trigger Conditions

- Cumulative PNL < -$500 (automatic)
- 20+ consecutive trade failures
- Exchange API issues > 30 minutes
- Any unexpected error in critical path

### Rollback Procedure

**Option 1: CLI Flags (Preferred)**
```bash
# Revert to V5.4 settings (no 100-trades mode)
python DN_pair_eth_sol_nado.py \
    --size 5000 \
    --iter 20 \
    --min-spread-bps 20 \
    --use-ioc
```

**Option 2: Restore Backup**
```bash
cd /Users/botfarmer/2dex/hedge
cp DN_pair_eth_sol_nado.py.v6.1.backup DN_pair_eth_sol_nado.py
```

**Option 3: Manual Intervention**
```bash
# Stop bot (Ctrl+C)
# Check positions
# Close positions manually if needed
# Review logs for issues
```

---

## Commit Strategy

### Single Commit for All Changes

**Message**:
```
feat(dn-bot): Add 100-trades lossless execution with $1M volume

Changes:
- Add 100-trades execution mode with opportunistic (spread-based) timing
- Add trade counter and volume tracking ($1M target = 100 x $10,000)
- Add cumulative loss limit enforcement with documented formula
- Add PNL-based trade filtering (skip after losses)
- Add target_trades, volume_target_usd, cumulative_loss_limit parameters
- Add disable_pnl_filter flag for override
- Add use_100_trades_mode flag for explicit strategy selection
- Add run_100_trades_strategy() method for continuous execution
- Add trade progress logging (every 10 trades)
- Add trade target completion celebration
- Add cumulative loss limit warnings (at 80% threshold)
- CRITICAL FIX: Add start_time field to daily_pnl_summary

User-Confirmed Math:
  Margin: $2,000
  Leverage: 5x
  Per-trade notional: $10,000 (ETH + SOL combined)
  Trades for $1M: 100 trades
  Goal: PNL >= 0 AND 100 trades completed

Volume Calculation Formula (ITERATION 2 CLARIFIED):
  target_notional is PER POSITION (already correct)
  Total volume = target_notional * 2 (ETH + SOL)
  Example: --size 5000 → $5K ETH + $5K SOL = $10K total volume

Cumulative Loss Limit Formula:
  Stop if: cumulative_pnl_with_fee < cumulative_loss_limit
  Example: PNL=-600, limit=-500 → -600 < -500 → STOP
  Graceful shutdown: Complete BUILD+UNWIND before stopping

PNL Filter Formula (ITERATION 2 DATA RACE FIX):
  Skip if: last_cycle_pnl < 0 (previous trade was a loss)
  NOT current_cycle_pnl (which is reset before the check)

New Parameters:
- --use-100-trades-mode: Enable 100-trades continuous execution
- --target-trades: Target trade count (default 100)
- --volume-target: Volume target in USD (default 1000000 = $1M)
- --cumulative-loss-limit: Auto-stop threshold (default -500)
- --disable-pnl-filter: Allow trades after losses
- --state-file: Session state file (default: logs/dn_bot_100trades_state.json)

ITERATION 2 CRITICAL FIXES:
- Session persistence: JSON state file (pattern from progressive_sizing.py)
- PNL filter data race: Uses last_cycle_pnl (NOT current_cycle_pnl)
- Graceful shutdown: Complete BUILD+UNWIND before stopping on loss limit
- Volume formula clarified: target_notional is PER POSITION
- pytz import verified: Required for start_time timezone handling

Objectives:
- 100 trades completed (NOT time-constrained)
- $1M volume achieved (100 x $10,000)
- Cumulative PNL >= 0 (lossless)
- $2000 margin with 5x leverage
- Session can be resumed after restart

Capital Structure:
- Margin: $2,000
- Leverage: 5x
- Per-trade notional: $10,000 (ETH + SOL, --size 5000 * 2)
- Trades for $1M: 100 trades
- Execution: Opportunistic (spread-based, NOT time-based)

Feasibility:
- POST_ONLY + 6 bps: 20-40 trades/day → 2.5-5 days for 100 trades
- IOC mode: 100+ trades/day → ~1 day for 100 trades
- Hybrid: 40-80 trades/day → 1.25-2.5 days for 100 trades

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```

---

## File Changes Summary (ITERATION 2 UPDATES)

### Modified Files

1. **`/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`**
   - Imports: **ADD** `import pytz` (required for start_time timezone handling)
   - Imports: **ADD** `import json`, `from pathlib import Path` (for session persistence)
   - Constructor: Add target_trades, volume_target_usd, cumulative_loss_limit, disable_pnl_filter, use_100_trades_mode, state_file
   - daily_pnl_summary: **CRITICAL FIX** Add start_time field (PERSISTED), total_volume_usd field, last_cycle_pnl field (for PNL filter)
   - CLI: Add --use-100-trades-mode, --target-trades, --volume-target, --cumulative-loss-limit, --disable-pnl-filter, --state-file
   - New methods: _load_session_state(), _save_session_state(), _check_cumulative_loss_limit(), _should_skip_trade(), run_100_trades_strategy(), _get_volume_stats()
   - Update: _update_daily_pnl_summary() (volume tracking, last_cycle_pnl storage, loss limit check, trade target check, celebration, session state save)
   - Update: _generate_daily_pnl_report() (trade count, volume display, elapsed time)
   - Update: execute_buy_first_cycle() (PNL filter check with last_cycle_pnl)
   - Update: execute_sell_first_cycle() (PNL filter check with last_cycle_pnl)
   - Update: main() (explicit strategy selection via use_100_trades_mode)

### Backup Files

1. **`/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py.v6.2.backup`**
   - Pre-modification backup for rollback (ITERATION 2)

### Session State File (NEW)

1. **`/Users/botfarmer/2dex/hedge/logs/dn_bot_100trades_state.json`**
   - Created automatically on first run
   - Contains: start_time, total_cycles, last_cycle_pnl, total_pnl_with_fee, total_volume_usd
   - Used for session recovery after restart

---

## Dependencies (ITERATION 2 UPDATES)

### External Dependencies
- pytz: **NEW** Required for start_time timezone handling
- json: **NEW** Required for session state persistence
- pathlib: **NEW** Required for file path handling

### Internal Dependencies
- Existing CSV logging structure
- Existing spread calculation logic
- Existing POST_ONLY/IOC order execution
- Existing position verification
- Existing daily PNL tracking
- Tuple import (line 23): Already exists
- Progressive sizing pattern: `/Users/botfarmer/2dex/hedge/helpers/progressive_sizing.py` lines 91-125

---

## Risk Assessment (ITERATION 2 UPDATES)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 100 trades takes too long | Medium | Low | User chooses mode (POST_ONLY: 2-5 days, IOC: ~1 day) |
| Insufficient spread opportunities | Medium | Low | No time constraint, wait for setups |
| Cumulative loss breach | Medium | Low | PNL filter + auto-stop + graceful shutdown |
| Exchange downtime | Low | Medium | Stop flag checked each trade |
| Network issues | Medium | Low | 3-5 retry logic |
| Partial fills | Low | Low | Position verification |
| Missing start_time field | Low | High | **FIXED** Added in T1, persisted across restarts |
| Lossless requirement not met | Medium | Medium | PNL filter helps, no guarantee |
| Software bugs | Low | Medium | Extensive testing before 100-trade run |
| **Bot restart loses progress** | Medium | High | **FIXED** Session persistence (JSON state file) |
| **PNL filter data race** | High | High | **FIXED** Uses last_cycle_pnl (not current_cycle_pnl) |
| **Mid-execution stop risk** | Medium | Medium | **FIXED** Graceful shutdown (complete BUILD+UNWIND) |

---

## Timeline (ITERATION 2 UPDATES)

### Development: 1 day
- **Hour 1-2**: Implement T1-T2 (parameters, start_time fix, pytz import, volume)
- **Hour 3**: Implement T3 (session persistence - _load_session_state, _save_session_state)
- **Hour 4**: Implement T4 (loss limit with graceful shutdown)
- **Hour 5**: Implement T5 (PNL filter with data race fix - last_cycle_pnl)
- **Hour 6**: Implement T6-T7 (100-trades strategy, monitoring)
- **Hour 7-8**: Testing T9 (session recovery, graceful shutdown, PNL filter data race)

### Deployment: 1-5 days (depending on mode)
- **Day 1 Morning**: Verify pytz import, start_time field, last_cycle_pnl field
- **Day 1 Midday**: Dry run testing (5 trades)
- **Day 1 Afternoon**: Session persistence test (stop at 10, restart, resume at 11)
- **Day 1 Evening**: Loss limit graceful shutdown test, PNL filter data race test
- **Day 1 Night**: Start 100-trade run
- **Day 2-5**: Monitor progress (POST_ONLY: 2.5-5 days, IOC: ~1 day)
- **Completion**: Verify 100 trades, $1M volume, PNL >= 0, session recovery works

---

## Success Criteria (ITERATION 2 UPDATES)

### Phase 1: Development
- [ ] All 9 tasks completed (T1-T9)
- [ ] Code compiles without errors
- [ ] pytz import verified
- [ ] start_time field verified to exist (PERSISTED)
- [ ] last_cycle_pnl field verified to exist (for PNL filter)
- [ ] Volume calculation formula documented (target_notional is PER POSITION)
- [ ] Cumulative loss limit formula documented
- [ ] PNL filter formula documented (uses last_cycle_pnl)
- [ ] Dry run tests pass
- [ ] Volume tracking verified
- [ ] Session persistence tested
- [ ] Graceful shutdown tested

### Phase 2: 100-Trade Run
- [ ] Bot runs until 100 trades completed
- [ ] Achieves $1M volume (100 x $10,000)
- [ ] Completes with cumulative PNL >= 0 (lossless)
- [ ] No residual positions at end
- [ ] All logs and CSV data complete
- [ ] Session can be resumed after restart
- [ ] PNL filter uses last_cycle_pnl (no data race)
- [ ] Graceful shutdown completes current cycle before stopping

### Overall Success
- [ ] **100 trades**: Completed (primary objective)
- [ ] **$1M volume**: Achieved (100 x $10,000)
- [ ] **Lossless trading**: Cumulative PNL >= 0
- [ ] **Session persistence**: Resume after restart works
- [ ] **Data race fixed**: PNL filter uses last_cycle_pnl
- [ ] **Graceful shutdown**: Complete BUILD+UNWIND before stop
- [ ] **Reusable**: Framework for future trade-based strategies
- [ ] **Documented**: Formulas and calculations explicit

---

**Plan Status**: READY FOR EXECUTION (ITERATION 2 - ALL CRITICAL ISSUES ADDRESSED)

**ITERATION 2 CRITICAL FIXES SUMMARY**:
1. Session persistence: JSON state file (progressive_sizing.py pattern)
2. PNL filter data race: Uses last_cycle_pnl (NOT current_cycle_pnl)
3. Graceful shutdown: Complete BUILD+UNWIND before stopping
4. Volume formula clarified: target_notional is PER POSITION
5. pytz import verified: Required for start_time timezone handling

**Next Step**: Run `/oh-my-claudecode:start-work dn-bot-1M-volume-1day-lossless` to begin implementation.

**Signal**: `PLAN_READY: .omc/plans/dn-bot-1M-volume-1day-lossless.md`
