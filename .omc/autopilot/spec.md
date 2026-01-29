# DN Pair Bot: ETH/SOL on Nado - Specification

## Requirements Analysis

### Functional Requirements

1. **Single Exchange, Dual Ticker Architecture**
   - Use Nado exchange for both ETH and SOL trading
   - Two separate NadoClient instances (one per ticker)
   - Shared API connection but independent state tracking

2. **Notional-Based Position Sizing**
   - Formula: `order_size = target_notional / price`
   - Same USD notional for both ETH and SOL positions
   - Tick size rounding for each ticker

3. **Simultaneous Order Execution**
   - Place both ETH and SOL orders concurrently using asyncio.gather()
   - Maximum time between orders: <100ms target
   - Handle partial fill scenarios

4. **Trading Strategy: BUILD/UNWIND**
   - BUILD: Long ETH / Short SOL (open positions)
   - UNWIND: Sell ETH / Buy SOL (close positions)
   - Alternate: BUILD → (optional sleep) → UNWIND → repeat

5. **Position Management**
   - Track ETH and SOL positions separately
   - Reconcile with exchange API every cycle
   - Handle position drift (1% tolerance)

### Non-Functional Requirements

1. **Performance**
   - Order placement latency: <500ms
   - Fill monitoring: 100ms polling interval
   - Cycle completion time: <30 seconds

2. **Reliability**
   - Handle WebSocket disconnections
   - Graceful handling of partial fills
   - Emergency unwind on critical failures

3. **Safety**
   - Position limits: 5 ETH max, 50 SOL max
   - Daily loss limit: $5 USD
   - Position reconciliation every cycle

### Implicit Requirements

1. **Delta Neutral Execution**: Long ETH / Short SOL maintains market-neutral exposure
2. **Correlation Assumption**: Strategy assumes ETH/SOL positive correlation
3. **Leverage Handling**: Both positions use 5x leverage (via Nado perpetuals)
4. **Fee Optimization**: Use POST_ONLY orders for 0% maker fee
5. **Logging**: Comprehensive logging for debugging and analysis

### Out of Scope

1. **Spread Threshold Entry**: No minimum spread requirement for now
2. **Correlation Monitoring**: No real-time correlation checking
3. **Dynamic Sizing**: Fixed notional per cycle (no volatility adjustment)
4. **Funding Rate Optimization**: No funding rate arbitrage
5. **Multi-Exchange**: Single exchange (Nado) only

### Critical Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Partial fill (one leg fills, other doesn't) | High | Emergency unwind within 1 second |
| Position drift (local vs API mismatch) | High | Reconcile every cycle, 1% tolerance |
| WebSocket disconnect mid-cycle | Medium | Pause trading, reconcile via REST API |
| Insufficient liquidity for one ticker | Medium | Skip cycle, log warning |
| Price moves between fetch and order | Low | 500ms max price age, cancel if stale |

---

## Technical Specification

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DN Pair Bot (Main Controller)            │
│  - Position Management (ETH + SOL)                          │
│  - Notional Calculation                                     │
│  - Order Coordination                                       │
│  - Safety & Risk Controls                                   │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
    ┌────────▼────────┐          ┌────────▼────────┐
    │  NadoClient ETH │          │ NadoClient SOL  │
    │  (Instance 1)   │          │  (Instance 2)   │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                  ┌───────▼────────┐
                  │  Nado Exchange │
                  │  (Single API)  │
                  └────────────────┘
```

### Component Structure

```python
class DNPairBot:
    """Main bot controller for ETH/SOL pair trading on Nado"""

    def __init__(
        self,
        target_notional: Decimal,      # USD notional per position
        fill_timeout: int = 5,         # Order fill timeout (seconds)
        iterations: int = 20,          # Number of cycles
        sleep_time: int = 0,           # Sleep between BUILD/UNWIND
        max_position_eth: Decimal = Decimal("5"),
        max_position_sol: Decimal = Decimal("50"),
        order_mode: PriceMode = PriceMode.BBO,
    )
```

### Key Algorithms

**Notional Calculation:**
```python
def calculate_quantities_from_notional(
    target_notional: Decimal,
    eth_price: Decimal,
    sol_price: Decimal,
    eth_tick_size: Decimal,
    sol_tick_size: Decimal,
) -> Tuple[Decimal, Decimal]:
    raw_eth_qty = target_notional / eth_price
    raw_sol_qty = target_notional / sol_price

    eth_qty = (raw_eth_qty / eth_tick_size).quantize(Decimal('1')) * eth_tick_size
    sol_qty = (raw_sol_qty / sol_tick_size).quantize(Decimal('1')) * sol_tick_size

    return eth_qty, sol_qty
```

**Simultaneous Order Placement:**
```python
async def place_simultaneous_orders(
    self,
    eth_quantity: Decimal,
    sol_quantity: Decimal,
    eth_direction: str,
    sol_direction: str,
) -> Tuple[OrderResult, OrderResult]:
    eth_order_result, sol_order_result = await asyncio.gather(
        self.eth_client.place_open_order(...),
        self.sol_client.place_open_order(...),
        return_exceptions=True
    )

    if isinstance(eth_order_result, Exception) or isinstance(sol_order_result, Exception):
        await self.handle_emergency_unwind(eth_order_result, sol_order_result)

    return eth_order_result, sol_order_result
```

### Safety Mechanisms

1. **Emergency Unwind**: If one leg fills and other fails, close filled leg within 1 second
2. **Position Reconciliation**: Compare local vs API positions every cycle (1% tolerance)
3. **Daily Loss Limit**: Halt trading if daily PnL < -$5
4. **Position Limits**: Max 5 ETH, 50 SOL
5. **Order Timeout**: Cancel orders after 5 seconds

### Data Structures

```python
@dataclass
class TradeMetrics:
    iteration: int
    direction: str  # "BUILD" or "UNWIND"

    # Entry prices
    eth_entry_price: Decimal
    sol_entry_price: Decimal
    eth_entry_time: float
    sol_entry_time: float

    # Exit prices
    eth_exit_price: Decimal
    sol_exit_price: Decimal
    eth_exit_time: float
    sol_exit_time: float

    # Timing metrics
    order_to_fill_eth: float
    order_to_fill_sol: float
    total_cycle_time: float
    repricing_count: int
```

### NadoClient API Usage

| Method | Purpose |
|--------|---------|
| `connect()` | Establish WebSocket connection |
| `fetch_bbo_prices()` | Get best bid/ask |
| `place_open_order()` | Place entry order |
| `place_close_order()` | Place exit order |
| `get_order_info()` | Get order status |
| `get_account_positions()` | Get current position |
| `cancel_order()` | Cancel pending order |

### Configuration

```python
# Recommended settings
DNPairBot(
    target_notional=Decimal("100"),  # $100 per position
    iterations=20,
    fill_timeout=5,
    order_mode=PriceMode.BBO,
)

# Safety limits
MAX_POSITION_ETH = Decimal("5")
MAX_POSITION_SOL = Decimal("50")
MAX_DAILY_LOSS = Decimal("5")
POSITION_DRIFT_TOLERANCE = Decimal("0.01")  # 1%
```

---

## Implementation Plan

### Phase 1: Core Structure
1. Rename class from DNHedgeBot to DNPairBot
2. Update TradeMetrics dataclass (primary/hedge → eth/sol)
3. Update constructor parameters (target_notional, eth_mode, sol_mode)
4. Add instance variables for dual ticker tracking

### Phase 2: New Methods
1. `calculate_order_size(price)` - Notional-based sizing
2. `place_simultaneous_orders()` - Concurrent order placement
3. `_place_single_order()` - Helper for single orders
4. `_handle_partial_fill()` - Partial fill safety
5. `_emergency_unwind_ticker()` - Emergency close
6. `_cancel_pending_orders()` - Cancel all pending

### Phase 3: Update Existing Logic
1. Update `execute_dn_cycle()` for simultaneous execution
2. Update `_create_trade_metrics()` for eth/sol fields
3. Update position tracking (two tickers)
4. Update order handlers (ETH and SOL)

### Phase 4: CLI & Main
1. Update `parse_arguments()` (remove --ticker, --primary, --hedge)
2. Update `main()` function
3. Update docstrings

### Phase 5: Verification
1. Syntax check
2. Import check
3. Test with small notional ($10)

---

## Files

- **Target**: `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`
- **Nado Client**: `/Users/botfarmer/2dex/exchanges/nado.py`
- **Template**: `/Users/botfarmer/2dex/hedge/DN_alternate_nado_edgex.py`
