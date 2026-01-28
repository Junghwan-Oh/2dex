# GRVT Smart Liquidity Routing - Implementation Plan

## User's Proposal Evaluation

### Original Problem
1-tick worsening strategy wasn't working because:
- Simple 1-tick worsening assumes liquidity exists at each tick
- GRVT's order book is thin - 1 ETH requires looking deeper

### User's Solution
**Smart Liquidity Routing via Order Book Analysis**:
1. First order at BBO-1tick
2. If not filled, walk the order book from BAO/BAO
3. Find actual liquidity depth and place orders there
4. Use market microstructure (cumulative depth) instead of fixed ticks

**Verdict**: ✅ **APPROVED** - This is the correct approach for market microstructure-aware routing

---

## Architecture Design

### Core Components

1. **BBO Fetcher** (`fetch_bbo()`):
   - Use `fetch_ticker()` for BBO prices
   - Returns: `{best_bid_price, best_bid_size, best_ask_price, best_ask_size}`

2. **Order Book Depth Analyzer** (`analyze_order_book_depth()`):
   - Use `fetch_order_book(limit=50)` 
   - Walk bids/asks, calculate cumulative size
   - Return: `{price, cumulative_size, position_in_book}`

3. **Smart Price Finder** (`find_hedge_price_with_liquidity()`):
   - Given target quantity, find price where cumulative >= target
   - Return optimal price and estimated slippage
   - Configurable max_slippage_bps (default: 5)

4. **Smart Routing Order Placer** (`place_smart_market_order()`):
   - Wrapper around `place_iterative_market_order()` 
   - Use BBO analysis to determine optimal price levels
   - Adaptive chunk sizes based on found liquidity

---

## Implementation Steps

### Phase 1: TradingLogger Fix
**Priority**: P0 (blocking all orders)

**Problem**: `self.logger.error()` calls fail because TradingLogger only has `log(message, level)`

**Fix Options**:
1. Add direct methods: `error()`, `warning()`, `info()`, `debug()` to TradingLogger
2. Or update all code to use `log(message, level)` consistently

**Recommended**: Option 1 (add methods for backward compatibility)

### Phase 2: Timeout Formula Fix
**Priority**: P0

**Problem**: 30 + 30*quantity seconds is too long

**Solution**:
```python
def calculate_timeout(quantity: Decimal) -> int:
    timeout = 30 + int(10 * float(quantity))  # 10s base + 10s per 0.1 ETH
    return max(5, min(timeout, 20))  # Clamp 5-20 seconds
```

Result:
- 0.1 ETH → 5s
- 0.5 ETH → 10s
- 1.0 ETH → 20s

### Phase 3: Smart Liquidity Routing

#### Step 1: Add BBO Fetcher to GrvtClient

**File**: `exchanges/grvt.py`
**Location**: After `connect()` method

**Add Method**:
```python
async def fetch_bbo(self, symbol: str) -> dict:
    """Fetch Best Bid/Ask prices.
    
    Returns:
        {
            'best_bid_price': Decimal,
            'best_bid_size': Decimal,
            'best_ask_price': Decimal,
            'best_ask_size': Decimal,
            'spread': Decimal,
            'mid_price': Decimal
        }
    """
    ticker = await self.rest_client.fetch_ticker(symbol)
    best_bid = Decimal(ticker.get('best_bid_price', 0))
    best_bid_size = Decimal(ticker.get('best_bid_size', 0))
    best_ask = Decimal(ticker.get('best_ask_price', 0))
    best_ask_size = Decimal(ticker.get('best_ask_size', 0))
    
    spread = best_ask - best_bid
    mid_price = (best_bid + best_ask) / 2
    
    return {
        'best_bid_price': best_bid,
        'best_bid_size': best_bid_size,
        'best_ask_price': best_ask,
        'best_ask_size': best_ask_size,
        'spread': spread,
        'mid_price': mid_price
    }
```

#### Step 2: Add Order Book Analyzer

**File**: `exchanges/grvt.py`
**Location**: After `fetch_bbo()` method

**Add Method**:
```python
async def analyze_order_book_depth(
    self, 
    symbol: str, 
    side: str,  # 'buy' or 'sell'
    depth_limit: int = 50
) -> dict:
    """Analyze order book depth at specific side.
    
    Args:
        symbol: Trading pair
        side: 'buy' (check asks) or 'sell' (check bids)
        depth_limit: Number of levels to analyze (10/50/100/500)
    
    Returns:
        {
            'top_price': Decimal,
            'top_size': Decimal,
            'cumulative_size': Decimal,
            'price_levels': [
                {'price': Decimal, 'size': Decimal, 'cumulative': Decimal},
                ...
            ]
        }
    """
    orderbook = await self.rest_client.fetch_order_book(symbol, limit=depth_limit)
    
    if side == 'buy':
        levels = orderbook['asks']
    else:
        levels = orderbook['bids']
    
    price_levels = []
    cumulative = Decimal('0')
    
    for i, level in enumerate(levels):
        # Handle both GRVT native and CCXT formats
        if isinstance(level, dict):
            price = Decimal(level['price'])
            size = Decimal(level['size'])
        else:
            price = Decimal(level[0])
            size = Decimal(level[1])
        
        cumulative += size
        price_levels.append({
            'price': price,
            'size': size,
            'cumulative': cumulative,
            'position': i + 1
        })
    
    if not price_levels:
        raise ValueError(f"No {side} order book data available")
    
    top = price_levels[0]
    
    return {
        'top_price': top['price'],
        'top_size': top['size'],
        'cumulative_size': top['cumulative'],
        'price_levels': price_levels,
        'total_levels_analyzed': len(price_levels)
    }
```

#### Step 3: Add Smart Price Finder

**File**: `exchanges/grvt.py`
**Location**: After `analyze_order_book_depth()`

**Add Method**:
```python
async def find_hedge_price_with_liquidity(
    self,
    symbol: str,
    side: str,
    target_quantity: Decimal,
    max_slippage_bps: int = 5,
    depth_limit: int = 50
) -> tuple[Decimal, Decimal, int]:
    """Find optimal price for hedge order with sufficient liquidity.
    
    Args:
        symbol: Trading pair
        side: 'buy' (we need to buy, so look at asks) or 'sell' (look at bids)
        target_quantity: Size needed
        max_slippage_bps: Maximum acceptable slippage in basis points (default: 5)
        depth_limit: Order book levels to analyze
    
    Returns:
        (optimal_price, slippage_bps, levels_used)
    
    Raises:
        ValueError: If insufficient liquidity at max slippage
    """
    analysis = await self.analyze_order_book_depth(symbol, side, depth_limit)
    
    top_price = analysis['top_price']
    top_size = analysis['top_size']
    price_levels = analysis['price_levels']
    
    # If top of book has enough liquidity, use it
    if top_size >= target_quantity:
        slippage = Decimal('0')
        return top_price, slippage, 1
    
    # Walk the order book to find sufficient liquidity
    worst_price = top_price
    cumulative = top_size
    
    for level in price_levels:
        worst_price = level['price']
        cumulative = level['cumulative']
        
        if cumulative >= target_quantity:
            break
    
    # Calculate slippage
    slippage = abs(worst_price - top_price) / top_price * 10000  # Basis points
    
    # Check against max slippage
    if slippage > max_slippage_bps:
        available = cumulative
        raise ValueError(
            f"Insufficient liquidity: need {target_quantity}, "
            f"available {available} at {max_slippage_bps} bps slippage "
            f"(worst price: {worst_price}, slippage: {slippage:.2f} bps)"
        )
    
    return worst_price, slippage, analysis['total_levels_analyzed']
```

#### Step 4: Rewrite Iterative Market Order with Smart Routing

**File**: `exchanges/grvt.py`
**Location**: Replace `place_iterative_market_order()` method

**Key Changes**:
1. **Initial chunk at BBO-1tick**: Not full BBO
2. **Adaptive chunk sizes**: Based on found liquidity
3. **BBO analysis first**: Determine optimal starting point
4. **Slippage monitoring**: Alert if exceeding thresholds

**New Implementation**:
```python
async def place_iterative_market_order(
    self,
    contract_id: str,
    target_quantity: Decimal,
    side: str,
    max_iterations: int = 20,
    max_slippage_bps: int = 5,
    tick_size: int = 10,  # GRVT tick size for ETH
) -> dict:
    """Place iterative market orders with smart liquidity routing.
    
    Strategy:
    1. Analyze order book at BBO level
    2. Place first chunk at BBO-1tick (not full BBO)
    3. After each fill, re-analyze BBO for fresh data
    4. Increase tick offset adaptively based on found liquidity
    5. Stop when fully filled or max_iterations reached
    
    Args:
        contract_id: Trading pair
        target_quantity: Total quantity to fill
        side: 'buy' or 'sell'
        max_iterations: Maximum iterations (default: 20)
        max_slippage_bps: Maximum acceptable slippage (default: 5 bps)
        tick_size: GRVT tick size in cents (default: 10 for ETH)
    
    Returns:
        Standard order result dict
    """
    remaining = target_quantity
    tick_offset = 0
    total_slippage_bps = Decimal('0')
    
    # Initial BBO analysis to determine optimal starting point
    try:
        bbo = await self.fetch_bbo(contract_id)
        
        if side == 'buy':
            start_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
        else:
            start_price = bbo['best_bid_price'] + (Decimal(tick_size) * Decimal(tick_offset))
        
        self.logger.log(
            f"[SMART_ROUTING] Starting with {side} order at "
            f"{start_price:.2f}, target: {target_quantity}, "
            f"BBO spread: {bbo['spread']:.2f}",
            "INFO"
        )
    except Exception as e:
        self.logger.log(
            f"[SMART_ROUTING] BBO fetch failed, using direct market order: {e}",
            "WARNING"
        )
        return await self.place_market_order(
            contract_id, target_quantity, side
        )
    
    for iteration in range(1, max_iterations + 1):
        # Re-analyze BBO at each iteration for fresh market data
        try:
            bbo = await self.fetch_bbo(contract_id)
        except Exception as e:
            self.logger.log(
                f"[SMART_ROUTING] BBO re-fetch failed, continuing with current price: {e}",
                "WARNING"
            )
        
        # Calculate current price with tick offset
        if side == 'buy':
            current_price = bbo['best_ask_price'] - (Decimal(tick_size) * Decimal(tick_offset))
        else:
            current_price = bbo['best_bid_price'] + (Decimal(tick_size) * Decimal(tick_offset))
        
        # Determine chunk size based on remaining and current liquidity
        chunk_size = min(
            remaining,
            bbo['best_ask_size'] if side == 'buy' else bbo['best_bid_size']
        )
        
        # If top of book has enough liquidity, use it directly
        if chunk_size >= remaining:
            self.logger.log(
                f"[SMART_ROUTING] Iteration {iteration}: Placing {remaining} at "
                f"{current_price:.2f} (BBO level {tick_offset})",
                "INFO"
            )
            
            order_result = await self._ws_rpc_submit_order(
                symbol=contract_id,
                order_type='market',
                side=side,
                amount=remaining,
                price=current_price,
                verify_with_rest=True
            )
            
            if order_result.get('success'):
                filled = extract_filled_quantity(order_result)
                remaining -= filled
                
                if remaining <= Decimal('0'):
                    self.logger.log(
                        f"[SMART_ROUTING] ✅ Fully filled in {iteration} iterations",
                        "INFO"
                    )
                    return order_result
            
            # If failed, increment tick offset and continue
            tick_offset += 1
            continue
        
        # Otherwise, use incremental chunking
        self.logger.log(
            f"[SMART_ROUTING] Iteration {iteration}: Placing chunk {chunk_size} at "
            f"{current_price:.2f} (BBO level {tick_offset}), remaining: {remaining}",
            "INFO"
        )
        
        order_result = await self._ws_rpc_submit_order(
            symbol=contract_id,
            order_type='market',
            side=side,
            amount=chunk_size,
            price=current_price,
            verify_with_rest=True
        )
        
        if not order_result.get('success'):
            tick_offset += 1
            if tick_offset > max_iterations:
                self.logger.log(
                    f"[SMART_ROUTING] ❌ Failed after {iteration} iterations, "
                    f"last price: {current_price:.2f}",
                    "ERROR"
                )
                return order_result
            continue
        
        # Calculate slippage
        filled = extract_filled_quantity(order_result)
        remaining -= filled
        
        # Recalculate slippage based on initial price vs final price
        if iteration == 1:
            total_slippage_bps = calculate_slippage_bps(
                current_price,
                bbo['best_bid_price'] if side == 'sell' else bbo['best_ask_price']
            )
        
        self.logger.log(
            f"[SMART_ROUTING] Filled {filled}, remaining: {remaining}, "
            f"current price: {current_price:.2f}, "
            f"slippage: {total_slippage_bps:.2f} bps",
            "DEBUG"
        )
        
        if remaining <= Decimal('0'):
            self.logger.log(
                f"[SMART_ROUTING] ✅ Fully filled in {iteration} iterations, "
                f"total slippage: {total_slippage_bps:.2f} bps",
                "INFO"
            )
            return order_result
        
        # Increment tick offset and continue
        tick_offset += 1
    
    self.logger.log(
        f"[SMART_ROUTING] ❌ Failed to fill {target_quantity} after {max_iterations} iterations",
        "ERROR"
    )
    return {'success': False, 'error': 'Max iterations reached'}
```

---

## Testing Strategy

### Unit Tests
1. Test `fetch_bbo()` with valid symbols
2. Test `analyze_order_book_depth()` for both 'buy' and 'sell'
3. Test `find_hedge_price_with_liquidity()` with various quantities
4. Test slippage calculation
5. Test TradingLogger methods

### Integration Tests
1. Test 0.1 ETH orders (should fill at BBO-1tick)
2. Test 0.5 ETH orders (may need 1-2 ticks)
3. Test 1.0 ETH orders (may need 3-5 ticks)

### Edge Cases
1. Empty order book
2. Insufficient liquidity
3. WebSocket disconnection during analysis
4. Rapid price movement during iteration

---

## Success Criteria

1. **TradingLogger**: All `error()`, `warning()`, `info()`, `debug()` methods work
2. **Timeout**: 1 ETH orders complete within 20s
3. **1 ETH Fills**: Orders execute successfully on GRVT
4. **Slippage Monitoring**: Slippage stays under 5 bps
5. **Iterations**: Average 2-5 iterations for 1 ETH orders

---

## Rollback Plan

If smart routing fails:
1. Revert to simple `place_market_order()` with chunking
2. Disable smart routing in configuration
3. Use 0.2 ETH limit for stability

---

**End of Implementation Plan**
