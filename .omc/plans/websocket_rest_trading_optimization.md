# WebSocket & REST Trading Optimization for Nado DN Pair

## Context

**Document Purpose**: Explain how BBO (Best Bid Offer) and BookDepth streams enable optimal trading logic for DN pair strategy.

**Importance**: Market making requires real-time visibility into:
1. Where to place orders (depth analysis)
2. How to size orders (liquidity estimation)
3. When to execute (spread monitoring)
4. How to minimize slippage (order book analysis)

---

## Nado WebSocket Streams for Trading

### Stream Comparison

| Stream | Update Frequency | Data | Use Case | Priority |
|--------|------------------|------|----------|----------|
| **BestBidOffer** | Real-time (instant) | Top bid/ask | Fast pricing, spread monitoring | CRITICAL |
| **BookDepth** | 50ms batches | Full depth (20+ levels) | Order placement, sizing | CRITICAL |
| **Fill** | Event-driven | Order fills | Execution confirmation | CRITICAL |
| **PositionChange** | Event-driven | Position updates | Inventory management | CRITICAL |
| **OrderUpdate** | Event-driven | Order status | Order lifecycle tracking | HIGH |
| **Trade** | Real-time | Public trades | Market sentiment | MEDIUM |

---

## BestBidOffer (BBO) Stream

### Message Format

```json
{
  "type": "best_bid_offer",
  "timestamp": "1676151190656903000",
  "product_id": 4,
  "bid_price": "2930000000000000000000",
  "bid_qty": "1000000000000000000",
  "ask_price": "2931000000000000000000",
  "ask_qty": "1000000000000000000"
}
```

### Parsed Values (ETH example)

- **bid_price**: 2930.00 (in wei, needs /1e18 conversion)
- **bid_qty**: 1.0 (in 18 decimals)
- **ask_price**: 2931.00
- **ask_qty**: 1.0
- **spread**: 1.00 (ask_price - bid_price)

### Trading Uses

#### 1. Real-Time Fair Value Calculation

```python
fair_value = (bid_price + ask_price) / 2
spread_bps = (ask_price - bid_price) / fair_value * 10000

# Trading decision
if spread_bps < 5:  # Tight spread
    # Market is efficient, use IOC orders
    pass
elif spread_bps > 20:  # Wide spread
    # Market inefficient, consider POST_ONLY for maker fee
    pass
```

#### 2. Spread Monitoring

```python
class SpreadMonitor:
    def __init__(self):
        self.spread_history = deque(maxlen=100)

    def on_bbo(self, bid_price, ask_price):
        spread = ask_price - bid_price
        spread_pct = spread / bid_price

        self.spread_history.append(spread_pct)

        # Detect spread widening
        if len(self.spread_history) >= 10:
            avg_spread = mean(self.spread_history)
            if spread_pct > avg_spread * 1.5:
                # Spread widening - volatility increasing
                return "WIDENING"
            elif spread_pct < avg_spread * 0.5:
                # Spread narrowing - market stabilizing
                return "NARROWING"

        return "STABLE"
```

#### 3. Momentum Detection

```python
class MomentumDetector:
    def __init__(self):
        self.bid_history = deque(maxlen=20)
        self.ask_history = deque(maxlen=20)

    def on_bbo(self, bid_price, ask_price, timestamp):
        self.bid_history.append((timestamp, bid_price))
        self.ask_history.append((timestamp, ask_price))

        if len(self.bid_history) < 5:
            return "NEUTRAL"

        # Calculate price trend
        recent_bids = [b for _, b in list(self.bid_history)[-5:]]
        recent_asks = [a for _, a in list(self.ask_history)[-5:]]

        bid_slope = (recent_bids[-1] - recent_bids[0]) / recent_bids[0]
        ask_slope = (recent_asks[-1] - recent_asks[0]) / recent_asks[0]

        if bid_slope > 0.001 and ask_slope > 0.001:
            return "BULLISH"  # Both rising
        elif bid_slope < -0.001 and ask_slope < -0.001:
            return "BEARISH"  # Both falling
        else:
            return "NEUTRAL"
```

#### 4. Fast Execution Decisions

```python
def should_place_ioc_order(spread_pct, momentum, position_imbalance):
    """
    Decide between IOC (aggressive) vs POST_ONLY (passive)
    """
    # Use IOC when:
    # 1. Spread is tight (low cost of crossing)
    # 2. Momentum favors our direction
    # 3. We need to reduce position imbalance quickly

    if spread_pct < 5:  # Tight spread
        return True  # Use IOC

    if momentum == "BULLISH" and position_imbalance < -0.5:
        return True  # Need to buy quickly

    if momentum == "BEARISH" and position_imbalance > 0.5:
        return True  # Need to sell quickly

    return False  # Use POST_ONLY
```

---

## BookDepth Stream

### Message Format

```json
{
  "type": "book_depth",
  "min_timestamp": "1683805381879572835",
  "max_timestamp": "1683805381879572835",
  "last_max_timestamp": "1683805381771464799",
  "product_id": 4,
  "bids": [
    ["2930000000000000000000", "5000000000000000000"],
    ["2929000000000000000000", "10000000000000000000"]
  ],
  "asks": [
    ["2931000000000000000000", "3000000000000000000"],
    ["2932000000000000000000", "0"]
  ]
}
```

### Parsed Values

- **bids**: List of [price, quantity] levels (sorted descending)
- **asks**: List of [price, quantity] levels (sorted ascending)
- **Quantity = 0**: Delete this level (incremental delta)
- **Quantity > 0**: Update/add this level

### Incremental Delta Processing

```python
class BookDepthHandler:
    def __init__(self, product_id: int):
        self.product_id = product_id
        self.bids = SortedDict()  # price -> quantity (descending)
        self.asks = SortedDict()  # price -> quantity (ascending)
        self.last_timestamp = 0

    def on_book_depth(self, message: dict):
        # Update timestamps
        self.last_timestamp = int(message["max_timestamp"])

        # Process bids (incremental deltas)
        for price_str, qty_str in message["bids"]:
            price = Decimal(price_str) / Decimal(1e18)
            qty = Decimal(qty_str) / Decimal(1e18)

            if qty == 0:
                # Delete level
                if price in self.bids:
                    del self.bids[price]
            else:
                # Add/update level
                self.bids[price] = qty

        # Process asks
        for price_str, qty_str in message["asks"]:
            price = Decimal(price_str) / Decimal(1e18)
            qty = Decimal(qty_str) / Decimal(1e18)

            if qty == 0:
                if price in self.asks:
                    del self.asks[price]
            else:
                self.asks[price] = qty

    def get_best_bid(self) -> Tuple[Decimal, Decimal]:
        """Returns (price, quantity) of best bid"""
        if not self.bids:
            return None, None
        best_price = max(self.bids.keys())
        return best_price, self.bids[best_price]

    def get_best_ask(self) -> Tuple[Decimal, Decimal]:
        """Returns (price, quantity) of best ask"""
        if not self.asks:
            return None, None
        best_price = min(self.asks.keys())
        return best_price, self.asks[best_price]

    def get_depth_at_level(self, level: int, side: str) -> Tuple[Decimal, Decimal]:
        """Returns (price, quantity) at specific depth level"""
        if side == "bid":
            prices = sorted(self.bids.keys(), reverse=True)
        else:
            prices = sorted(self.asks.keys())

        if level >= len(prices):
            return None, None

        price = prices[level]
        return price, (self.bids if side == "bid" else self.asks)[price]
```

### Trading Uses

#### 1. Optimal Order Placement

```python
def find_optimal_order_level(
    book: BookDepthHandler,
    side: str,
    target_quantity: Decimal,
    max_slippage_bps: int = 10
) -> Tuple[Decimal, Decimal]:

    """
    Find the best price level to place an order

    Returns: (price, estimated_fill_quantity)
    """
    if side == "buy":
        # We want to buy, look at asks
        cumulative_qty = Decimal(0)
        for level in range(20):  # Check up to 20 levels
            price, qty = book.get_depth_at_level(level, "ask")
            if price is None:
                break

            cumulative_qty += qty

            # Calculate slippage at this level
            best_ask, _ = book.get_best_ask()
            slippage_bps = (price - best_ask) / best_ask * 10000

            if cumulative_qty >= target_quantity:
                if slippage_bps <= max_slippage_bps:
                    return price, target_quantity
                else:
                    # Too much slippage, reduce quantity
                    return price, qty

        # Not enough liquidity
        return None, None

    else:  # sell
        # We want to sell, look at bids
        cumulative_qty = Decimal(0)
        for level in range(20):
            price, qty = book.get_depth_at_level(level, "bid")
            if price is None:
                break

            cumulative_qty += qty

            best_bid, _ = book.get_best_bid()
            slippage_bps = (best_bid - price) / best_bid * 10000

            if cumulative_qty >= target_quantity:
                if slippage_bps <= max_slippage_bps:
                    return price, target_quantity
                else:
                    return price, qty

        return None, None
```

#### 2. Slippage Estimation

```python
def estimate_slippage(
    book: BookDepthHandler,
    side: str,
    quantity: Decimal
) -> Decimal:

    """
    Estimate slippage for a given order quantity

    Returns: slippage in basis points
    """
    if side == "buy":
        best_price, _ = book.get_best_ask()
        if best_price is None:
            return Decimal(999999)  # No liquidity

        remaining_qty = quantity
        vwap = Decimal(0)
        total_qty = Decimal(0)

        for level in range(20):
            price, qty = book.get_depth_at_level(level, "ask")
            if price is None:
                break

            fill_qty = min(remaining_qty, qty)
            vwap += price * fill_qty
            total_qty += fill_qty
            remaining_qty -= fill_qty

            if remaining_qty <= 0:
                break

        if total_qty < quantity:
            return Decimal(999999)  # Not enough liquidity

        vwap /= total_qty
        slippage = (vwap - best_price) / best_price * 10000
        return slippage

    else:  # sell
        best_price, _ = book.get_best_bid()
        if best_price is None:
            return Decimal(999999)

        remaining_qty = quantity
        vwap = Decimal(0)
        total_qty = Decimal(0)

        for level in range(20):
            price, qty = book.get_depth_at_level(level, "bid")
            if price is None:
                break

            fill_qty = min(remaining_qty, qty)
            vwap += price * fill_qty
            total_qty += fill_qty
            remaining_qty -= fill_qty

            if remaining_qty <= 0:
                break

        if total_qty < quantity:
            return Decimal(999999)

        vwap /= total_qty
        slippage = (best_price - vwap) / best_price * 10000
        return slippage
```

#### 3. Competition Analysis

```python
def detect_market_makers(book: BookDepthHandler) -> Dict[str, Any]:
    """
    Analyze order book to detect other market makers
    """
    # Look for "step" patterns in the order book
    # Market makers often place orders at regular intervals

    bid_levels = []
    for level in range(10):
        price, qty = book.get_depth_at_level(level, "bid")
        if price is not None:
            bid_levels.append((price, qty))

    ask_levels = []
    for level in range(10):
        price, qty = book.get_depth_at_level(level, "ask")
        if price is not None:
            ask_levels.append((price, qty))

    # Check for regular intervals
    if len(bid_levels) >= 3:
        bid_intervals = [
            bid_levels[i][0] - bid_levels[i+1][0]
            for i in range(len(bid_levels)-1)
        ]
        bid_interval_std = stdev(bid_intervals) if len(bid_intervals) > 1 else 0

        # Low standard deviation = regular spacing = likely market maker
        mm_detected = bid_interval_std < Decimal('0.05')  # Tight tolerance
    else:
        mm_detected = False

    return {
        "market_maker_detected": mm_detected,
        "bid_depth_levels": len(bid_levels),
        "ask_depth_levels": len(ask_levels),
        "total_bid_liquidity": sum(qty for _, qty in bid_levels),
        "total_ask_liquidity": sum(qty for _, qty in ask_levels),
    }
```

#### 4. Inventory Management (Exit Liquidity)

```python
def estimate_exit_capacity(
    book: BookDepthHandler,
    current_position: Decimal,
    max_slippage_bps: int = 20
) -> Tuple[bool, Decimal]:

    """
    Check if we can exit our position without excessive slippage

    Returns: (can_exit, exitable_quantity)
    """
    if current_position == 0:
        return True, Decimal(0)

    side = "sell" if current_position > 0 else "buy"
    abs_position = abs(current_position)

    slippage = estimate_slippage(book, side, abs_position)

    if slippage <= max_slippage_bps:
        return True, abs_position
    else:
        # Binary search for max exitable quantity
        low, high = Decimal(0), abs_position
        for _ in range(10):  # 10 iterations enough
            mid = (low + high) / 2
            slippage_mid = estimate_slippage(book, side, mid)

            if slippage_mid <= max_slippage_bps:
                low = mid
            else:
                high = mid

        return False, low
```

---

## Combined BBO + BookDepth Strategy

### Market Making Decision Flow

```python
class MarketMakingStrategy:
    def __init__(self):
        self.bbo_handler = BBOHandler()
        self.book_depth = {
            4: BookDepthHandler(4),  # ETH
            8: BookDepthHandler(8),  # SOL
        }
        self.spread_monitor = SpreadMonitor()
        self.momentum_detector = MomentumDetector()

    def on_bbo_update(self, product_id: int, message: dict):
        self.bbo_handler.on_bbo(product_id, message)

        spread_state = self.spread_monitor.on_bbo(
            message["bid_price"],
            message["ask_price"]
        )

        momentum = self.momentum_detector.on_bbo(
            message["bid_price"],
            message["ask_price"],
            message["timestamp"]
        )

        return {
            "spread_state": spread_state,
            "momentum": momentum,
        }

    def on_book_depth_update(self, product_id: int, message: dict):
        self.book_depth[product_id].on_book_depth(message)

    def should_place_order(
        self,
        product_id: int,
        side: str,
        quantity: Decimal
    ) -> Dict[str, Any]:

        """
        Make trading decision based on BBO + BookDepth
        """
        book = self.book_depth[product_id]

        # 1. Check spread (from BBO)
        bid_price, bid_qty = book.get_best_bid()
        ask_price, ask_qty = book.get_best_ask()

        if bid_price is None or ask_price is None:
            return {"action": "WAIT", "reason": "No liquidity"}

        spread_bps = (ask_price - bid_price) / bid_price * 10000

        # 2. Estimate slippage (from BookDepth)
        slippage_bps = estimate_slippage(book, side, quantity)

        if slippage_bps > 20:
            return {
                "action": "REDUCE_QUANTITY",
                "reason": "Too much slippage",
                "max_quantity": self._find_max_quantity(book, side, 20)
            }

        # 3. Check market conditions
        spread_state = self.spread_monitor.get_state()
        momentum = self.momentum_detector.get_state()

        # 4. Make decision
        if spread_state == "WIDENING":
            # Volatility increasing - use IOC for certainty
            return {
                "action": "PLACE_IOC",
                "reason": "Widening spread, prioritize execution"
            }

        elif spread_bps < 5 and slippage_bps < 5:
            # Tight spread, low slippage - either works
            return {
                "action": "PLACE_IOC_OR_POST_ONLY",
                "reason": "Good conditions for either"
            }

        else:
            # Normal conditions - prefer POST_ONLY for maker fee
            return {
                "action": "PLACE_POST_ONLY",
                "reason": "Normal conditions, earn maker fee"
            }

    def _find_max_quantity(
        self,
        book: BookDepthHandler,
        side: str,
        max_slippage_bps: int
    ) -> Decimal:

        """Binary search for max quantity with acceptable slippage"""
        low, high = Decimal(0.01), Decimal(10)  # Reasonable range

        for _ in range(10):
            mid = (low + high) / 2
            slippage = estimate_slippage(book, side, mid)

            if slippage <= max_slippage_bps:
                low = mid
            else:
                high = mid

        return low
```

---

## DN Pair Specific Optimizations

### Simultaneous Order Placement

```python
def place_simultaneous_orders_with_book_analysis(
    eth_book: BookDepthHandler,
    sol_book: BookDepthHandler,
    eth_quantity: Decimal,
    sol_quantity: Decimal
) -> Dict[str, Any]:

    """
    Place simultaneous ETH/SOL orders with BookDepth analysis
    """
    # 1. Check ETH liquidity
    eth_slippage = estimate_slippage(eth_book, "buy", eth_quantity)

    # 2. Check SOL liquidity
    sol_slippage = estimate_slippage(sol_book, "sell", sol_quantity)

    # 3. Adjust quantities if needed
    if eth_slippage > 20:
        eth_quantity = eth_book._find_max_quantity("buy", 20)

    if sol_slippage > 20:
        sol_quantity = sol_book._find_max_quantity("sell", 20)

    # 4. Calculate optimal prices
    eth_bid_price, _ = eth_book.get_best_bid()
    sol_ask_price, _ = sol_book.get_best_ask()

    # For IOC: Cross the spread
    eth_ioc_price = eth_bid_price * Decimal('0.999')  # Slightly below bid
    sol_ioc_price = sol_ask_price * Decimal('1.001')  # Slightly above ask

    # For POST_ONLY: Improve the market
    eth_post_only_price = eth_bid_price * Decimal('1.001')  # Above best bid
    sol_post_only_price = sol_ask_price * Decimal('0.999')  # Below best ask

    return {
        "eth": {
            "quantity": eth_quantity,
            "ioc_price": eth_ioc_price,
            "post_only_price": eth_post_only_price,
            "estimated_slippage": eth_slippage,
        },
        "sol": {
            "quantity": sol_quantity,
            "ioc_price": sol_ioc_price,
            "post_only_price": sol_post_only_price,
            "estimated_slippage": sol_slippage,
        },
    }
```

### Position Rebalancing with BookDepth

```python
def rebalance_with_book_depth(
    eth_book: BookDepthHandler,
    sol_book: BookDepthHandler,
    eth_position: Decimal,
    sol_position: Decimal
) -> Dict[str, Any]:

    """
    Rebalance positions using BookDepth for optimal pricing
    """
    # Calculate delta
    eth_value = eth_position * eth_book.get_best_bid()[0]
    sol_value = sol_position * sol_book.get_best_ask()[0]

    delta = eth_value - sol_value
    delta_pct = delta / ((eth_value + sol_value) / 2)

    # If delta is too large, need to rebalance
    if abs(delta_pct) > 0.02:  # 2% threshold
        if delta_pct > 0:
            # Too much ETH, sell some
            sell_quantity = min(abs(delta) / eth_book.get_best_bid()[0], abs(eth_position))
            slippage = estimate_slippage(eth_book, "sell", sell_quantity)

            return {
                "action": "SELL_ETH",
                "quantity": sell_quantity,
                "estimated_slippage_bps": slippage,
                "reason": f"Delta {delta_pct:.2%} too high"
            }
        else:
            # Too much SOL, sell some
            sell_quantity = min(abs(delta) / sol_book.get_best_ask()[0], abs(sol_position))
            slippage = estimate_slippage(sol_book, "sell", sell_quantity)

            return {
                "action": "SELL_SOL",
                "quantity": sell_quantity,
                "estimated_slippage_bps": slippage,
                "reason": f"Delta {delta_pct:.2%} too low"
            }

    return {"action": "HOLD", "reason": "Delta within tolerance"}
```

---

## WebSocket vs REST Comparison

### Why WebSocket is Essential

| Operation | REST Polling (100ms) | WebSocket (Event) | Improvement |
|-----------|---------------------|-------------------|-------------|
| Fill Detection | 100-600ms latency | 5-15ms latency | **10-100x faster** |
| Position Update | 100-600ms latency | 5-15ms latency | **10-100x faster** |
| BBO Update | Stale (100ms old) | Real-time | **Instant** |
| BookDepth Update | Not feasible | 50ms batches | **Only possible with WS** |
| Rate Limit | 5-10 requests/sec | Unlimited (events) | **No rate limit** |

### Rate Limit Risk with REST-Only

```python
# REST polling scenario (BAD):
# - 100ms polling interval = 10 requests/second
# - Monitoring 2 products (ETH + SOL) = 20 requests/second
# - Plus order queries, position queries = 30+ requests/second
# - Result: RATE LIMIT EXCEEDED

# WebSocket scenario (GOOD):
# - Single connection streams all events
# - No polling needed
# - Rate limit: 5 authenticated connections per wallet (plenty)
# - Result: NO RATE LIMIT ISSUES
```

---

## Implementation Priority

### Phase 1: Critical Streams (Day 1-2)
1. **Fill stream** - Order execution confirmation
2. **PositionChange stream** - Real-time position updates
3. **BBO stream** - Real-time pricing

### Phase 2: Market Making (Day 3-4)
4. **BookDepth stream** - Full order book visibility
5. Implement slippage estimation
6. Implement optimal order placement

### Phase 3: Advanced Features (Day 5+)
7. Competition analysis
8. Momentum detection
9. Dynamic order sizing based on liquidity

---

## Testing Strategy

### Unit Tests

```python
# Test BBO parsing
def test_bbo_message_parsing():
    handler = BBOHandler()
    message = {
        "type": "best_bid_offer",
        "bid_price": "2930000000000000000000",
        "bid_qty": "1000000000000000000",
        "ask_price": "2931000000000000000000",
        "ask_qty": "1000000000000000000",
    }
    handler.on_bbo(4, message)

    assert handler.get_best_bid(4) == (Decimal("2930.0"), Decimal("1.0"))
    assert handler.get_best_ask(4) == (Decimal("2931.0"), Decimal("1.0"))
    assert handler.get_spread(4) == Decimal("1.0")

# Test BookDepth incremental deltas
def test_bookdepth_delta_parsing():
    handler = BookDepthHandler(4)

    # Initial state
    handler.on_book_depth({
        "bids": [["2930000000000000000000", "1000000000000000000"]],
        "asks": [["2931000000000000000000", "1000000000000000000"]],
    })

    assert handler.get_best_bid() == (Decimal("2930.0"), Decimal("1.0"))

    # Update (add level)
    handler.on_book_depth({
        "bids": [
            ["2930000000000000000000", "1000000000000000000"],
            ["2929000000000000000000", "2000000000000000000"]
        ],
        "asks": [["2931000000000000000000", "1000000000000000000"]],
    })

    assert handler.get_depth_at_level(1, "bid") == (Decimal("2929.0"), Decimal("2.0"))

    # Delete level
    handler.on_book_depth({
        "bids": [["2929000000000000000000", "0"]],  # Delete
        "asks": [["2931000000000000000000", "1000000000000000000"]],
    })

    assert handler.get_best_bid() == (Decimal("2929.0"), Decimal("2.0"))
```

### Integration Tests

```python
# Test slippage estimation
def test_slippage_estimation():
    handler = BookDepthHandler(4)

    # Create thin book
    handler.on_book_depth({
        "asks": [
            ["2931000000000000000000", "100000000000000000"],  # 0.1 ETH
            ["2932000000000000000000", "100000000000000000"],  # 0.1 ETH
            ["2933000000000000000000", "100000000000000000"],  # 0.1 ETH
        ],
    })

    # Buying 0.1 ETH should have minimal slippage
    slippage = estimate_slippage(handler, "buy", Decimal("0.1"))
    assert slippage < 1  # < 1 bps

    # Buying 0.3 ETH should have more slippage
    slippage = estimate_slippage(handler, "buy", Decimal("0.3"))
    assert slippage > 10  # > 10 bps

# Test optimal order placement
def test_optimal_order_placement():
    handler = BookDepthHandler(4)

    handler.on_book_depth({
        "asks": [
            ["2931000000000000000000", "100000000000000000"],
            ["2931500000000000000000", "500000000000000000"],
            ["2932000000000000000000", "1000000000000000000"],
        ],
    })

    price, qty = find_optimal_order_level(
        handler, "buy", Decimal("0.2"), max_slippage_bps=10
    )

    # Should place at second level for better fill
    assert price == Decimal("2931.5")
    assert qty == Decimal("0.2")
```

---

## Summary

### Key Takeaways

1. **BBO = Tactical**: Real-time pricing, spread monitoring, fast decisions
2. **BookDepth = Strategic**: Order placement, sizing, liquidity analysis
3. **WebSocket is Mandatory**: REST-only will hit rate limits and have 10-100x worse latency
4. **Combined Strategy**: Use BBO for decisions, BookDepth for execution

### DN Pair Optimization Path

1. **Phase 1**: Implement BBO + Fill + PositionChange streams (critical)
2. **Phase 2**: Add BookDepth stream for market making (optimize entry/exit)
3. **Phase 3**: Implement advanced features (competition analysis, dynamic sizing)

### Expected Performance Improvement

- **Fill Detection**: 100-600ms → 5-15ms (**10-100x faster**)
- **Pricing**: Stale (100ms old) → Real-time (**instant**)
- **Slippage**: Unknown → Calculated from depth (**predictable**)
- **Rate Limits**: 5-10 RPS → Unlimited events (**no limit**)

---

**Document Status**: COMPLETE
**Last Updated**: 2026-01-30
**Related Plans**:
- `.omc/plans/nado-dn-pair-v4-migration.md`
- `.omc/plans/nado-websocket-high-performance.md`
