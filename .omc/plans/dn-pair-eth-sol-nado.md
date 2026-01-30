# Implementation Plan: DN Pair Trading Bot (ETH/SOL on Nado) - REFINED v3

## Executive Summary

**CURRENT FILE STATE: PARTIALLY CONVERTED**
- Class name: Already `DNPairBot` (line 91) ✓
- Constructor: Already uses `target_notional` (line 104) ✓
- Instance variables: Already has `eth_client`/`sol_client` (lines 150-151) ✓
- **BUT**: Methods still reference old `primary_client`/`hedge_client` pattern
- **BUT**: TradeMetrics still has `primary_*`/`hedge_*` fields
- **BUT**: CLI arguments still configured for dual-exchange
- **BUT**: No `place_simultaneous_orders()` method exists yet

**TARGET STATE**: Complete conversion to dual-ticker pair trading on single exchange

---

## Critical Issue Resolution

### Issue 1: ACCURATE STATE ASSESSMENT
**STATUS**: File is PARTIALLY converted, NOT a fresh copy
**DONE**:
- Class renamed to `DNPairBot` (line 91)
- Constructor accepts `target_notional` parameter (line 104)
- Instance variables `eth_client`/`sol_client` declared (lines 150-151)
- TradeMetrics declared with new field names (lines 175-184)

**REMAINING**:
- `initialize_clients()` still instantiates `primary_client`/`hedge_client` (lines 408-451)
- `cleanup_connections()` still references old clients (lines 307-314)
- TradeMetrics dataclass still has `primary_entry_price`/`hedge_entry_price` fields (lines 55-56)
- CLI args parse dual-exchange params (--primary, --hedge, --primary-mode, --hedge-mode)
- `main()` instantiates with old parameter pattern
- No `place_simultaneous_orders()` method exists
- No integration point for simultaneous order placement

### Issue 2: API-CORRECT SIGNATURES
**NadoClient.place_open_order() signature** (from `/Users/botfarmer/2dex/exchanges/nado.py` line 152):
```python
async def place_open_order(self, contract_id: str, quantity: Decimal, direction: str) -> OrderResult
```

**OrderResult structure** (from `/Users/botfarmer/2dex/exchanges/base.py` lines 36-45):
```python
@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    side: Optional[str] = None
    size: Optional[Decimal] = None
    price: Optional[Decimal] = None  # ← THIS IS INITIAL PRICE, NOT FILL PRICE
    status: Optional[str] = None
    error_message: Optional[str] = None
    filled_size: Optional[Decimal] = None
```

**CRITICAL INSIGHT**: `place_open_order()` returns `OrderResult` with initial price. To get actual fill price, must call `get_order_info(order_id)` and wait for status='FILLED', then extract `OrderInfo.price`.

### Issue 3: INTEGRATION SPECIFICATION
**WHERE place_simultaneous_orders() IS CALLED FROM**:
- Primary entry point: `execute_dn_cycle()` method (line 1889 in template)
- Called AFTER `_pre_trade_check()` passes
- Returns tuple: `(success, eth_fill_price, sol_fill_price)`
- Integration point in template line 1945-1959 (BUILD) and line 1957-1959 (UNWIND)

### Issue 4: COMPLETE FIELD RENAME AUDIT
**GREP PATTERNS TO FIND ALL OCCURRENCES**:
```bash
# TradeMetrics fields (dataclass definition + all usage)
grep -n "primary_entry_price\|hedge_entry_price\|primary_exit_price\|hedge_exit_price" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py

# Client variables (constructor + initialize_clients + all methods)
grep -n "primary_client\|hedge_client" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py

# Position tracking variables
grep -n "primary_position\|hedge_position\|local_primary_position\|local_hedge_position" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py

# Contract info
grep -n "primary_contract_id\|hedge_contract_id\|primary_tick_size\|hedge_tick_size" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py

# Order status tracking
grep -n "primary_order_status\|hedge_order_status" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
```

**FOUND LOCATIONS** (from actual grep output):
- Lines 55-56: TradeMetrics dataclass field definitions
- Lines 307-314: cleanup_connections() method
- Lines 385-388, 412-451: initialize_clients() and related
- Lines 460-467: connect_websockets() method
- Lines 469-575: Order handler methods
- Lines 592-696: get_positions() and reconcile_positions() methods
- Lines 701-1400+: Order placement methods
- Lines 1792-1843: Current cycle tracking variables and _create_trade_metrics()
- Lines 1945-1959: execute_dn_cycle() usage
- Lines 2260-2261: Logging in trading_loop()

### Issue 5: CLI UPDATES
**CURRENT STATE** (lines 2332-2429):
- Still has `--primary`, `--hedge` exchange selection args
- Still has `--primary-mode`, `--hedge-mode` args
- Still has `--hedge-post-only`, `--hedge-market` args
- Still has `--min-spread` arg (not needed for pair trading)
- Description still says "Delta Neutral Hedge Bot: Backpack + GRVT"

**REQUIRED CHANGES**:
- Remove `--ticker` (hardcoded to ETH/SOL pair)
- Keep `--size` but clarify it's target notional in USD
- Keep `--iter`, `--fill-timeout`, `--sleep`
- Add `--eth-mode`, `--sol-mode` (replace primary/hedge-mode)
- Remove `--primary`, `--hedge`, `--hedge-post-only`, `--hedge-market`, `--min-spread`
- Update description to "DN Pair Trading Bot: ETH/SOL on Nado"

**main() FUNCTION UPDATE** (line 2433):
- Change bot instantiation from `DNHedgeBot(...)` to `DNPairBot(...)`
- Update parameters to match new constructor signature

### Issue 6: EXECUTION DEPENDENCY GRAPH

**PHASE PREREQUISITES**:
```
Phase 1 (Dataclass Update)
  ↓ MUST COMPLETE BEFORE
Phase 2 (Constructor Variables) ← MUST COMPLETE BEFORE
  ↓ MUST COMPLETE BEFORE
Phase 3 (initialize_clients) ← MUST COMPLETE BEFORE
  ↓ MUST COMPLETE BEFORE
Phase 4 (New Methods) ← MUST COMPLETE BEFORE
  ↓ MUST COMPLETE BEFORE
Phase 5 (Order Placement) ← MUST COMPLETE BEFORE
  ↓ MUST COMPLETE BEFORE
Phase 6 (Order Handlers) ← CAN RUN IN PARALLEL WITH
Phase 7 (Position Management)
  ↓ MUST COMPLETE BEFORE
Phase 8 (Trading Loop) ← MUST COMPLETE BEFORE
  ↓ MUST COMPLETE BEFORE
Phase 9 (CLI + main)
```

**CRITICAL PATH**:
1. Phase 1 → Phase 2 (dataclass fields used in constructor)
2. Phase 2 → Phase 3 (client vars initialized in initialize_clients)
3. Phase 3 → Phase 4 (clients used in new methods)
4. Phase 4 → Phase 5 (new methods called by order placement)
5. Phase 5 → Phase 8 (order methods called in trading loop)
6. Phase 8 → Phase 9 (main() calls trading loop)

**PARALLEL OPPORTUNITIES**:
- Phase 6 (Order Handlers) can be done alongside Phase 5 (Order Placement)
- Phase 7 (Position Management) can be done alongside Phase 5
- Phase 10 (Logging) can be done anytime after Phase 1

### Issue 7: TESTING VERIFICATION

**EXPECTED LOG OUTPUTS** (after successful implementation):

**Initialization Phase**:
```
[INFO] [INIT] Creating Nado client for ETH
[INFO] [INIT] Creating Nado client for SOL
[INFO] [INIT] ETH contract: 2, tick: 0.01
[INFO] [INIT] SOL contract: 3, tick: 0.001
[INFO] [WS] ETH (NADO) connected
[INFO] [WS] SOL (NADO) connected
```

**Order Placement Phase**:
```
[INFO] [SIZING] Target notional: $100.00, Price: $2500.00, Order size: 0.04000000
[INFO] [SIZING] Target notional: $100.00, Price: $100.00, Order size: 1.00000000
[INFO] [SIMULTANEOUS] Placing orders: ETH BUY 0.04000000 @ $2500.00, SOL SELL 1.00000000 @ $100.00
[INFO] [ETH] Order placed: 0x123abc...
[INFO] [SOL] Order placed: 0x456def...
[INFO] [ETH] Order filled: 0.04000000 @ $2500.50
[INFO] [SOL] Order filled: 1.00000000 @ $100.25
[INFO] [SIMULTANEOUS] Both orders filled successfully
```

**CSV Validation Criteria** (file: `/Users/botfarmer/2dex/hedge/logs/DN_pair_eth_sol_nado_trades.csv`):
```csv
exchange,timestamp,side,price,quantity,order_type,mode
NADO,2026-01-29T12:00:00.000000+00:00,buy,2500.50,0.04,OPEN,bbo
NADO,2026-01-29T12:00:01.000000+00:00,sell,100.25,1.0,OPEN,bbo
```

**Timing Evidence** (logs should show):
- ETH order placed timestamp: T0
- SOL order placed timestamp: T0 (within same second = simultaneous)
- ETH fill timestamp: T1
- SOL fill timestamp: T1 (within 100ms = both filled quickly)

**Validation Commands**:
```bash
# Check for no remaining old variable references
! grep -r "primary_client\|hedge_client" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py

# Verify TradeMetrics fields renamed
! grep -r "primary_entry_price\|hedge_entry_price" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py

# Check CSV output format
head -5 /Users/botfarmer/2dex/hedge/logs/DN_pair_eth_sol_nado_trades.csv

# Verify simultaneous placement (check timestamps in logs)
grep "SIMULTANEOUS\|Order placed" /Users/botfarmer/2dex/hedge/logs/DN_pair_eth_sol_nado_log.txt | tail -20
```

### Issue 8: PLACE_SIMULTANEOUS_ORDERS INTEGRATION

**METHOD SIGNATURE** (to be added):
```python
async def place_simultaneous_orders(
    self,
    eth_side: str,
    sol_side: str,
    eth_price: Decimal,
    sol_price: Decimal
) -> Tuple[bool, Optional[Decimal], Optional[Decimal]]:
    """
    Place both ETH and SOL orders simultaneously for pair entry/exit.
    
    CRITICAL: Uses asyncio.gather() for true simultaneous execution.
    
    Args:
        eth_side: "buy" or "sell" for ETH
        sol_side: "buy" or "sell" for SOL  
        eth_price: Price for ETH order
        sol_price: Price for SOL order
        
    Returns:
        Tuple of (success, eth_fill_price, sol_fill_price)
        - success: True if both orders filled, False otherwise
        - eth_fill_price: Actual fill price from OrderInfo (not OrderResult.price)
        - sol_fill_price: Actual fill price from OrderInfo
        
    Integration Point:
        - Called from: execute_dn_cycle() method (line ~1945 for BUILD, ~1957 for UNWIND)
        - Replaces: Sequential place_primary_order() → place_hedge_order() calls
        - Timing: Uses asyncio.wait_for() with self.fill_timeout (default 5 seconds)
    """
```

**CALLER INTEGRATION** (in execute_dn_cycle):
```python
# Current (WRONG - sequential):
if direction == "buy":
    primary_fill_price = await self.place_primary_order("buy")
    hedge_fill_price = await self.place_hedge_order("sell")
    
# New (CORRECT - simultaneous):
if direction == "buy":
    eth_side = "buy"
    sol_side = "sell"
    eth_price = self.calculate_order_price("buy", eth_bid, eth_ask, ...)
    sol_price = self.calculate_order_price("sell", sol_bid, sol_ask, ...)
    success, eth_fill_price, sol_fill_price = await self.place_simultaneous_orders(
        eth_side, sol_side, eth_price, sol_price
    )
```

---

## Refined Implementation Plan (WITH EXECUTION ORDER)

### PHASE 1: TradeMetrics Dataclass Update
**PREREQUISITES**: None
**EXECUTION TIME**: ~5 minutes
**CHANGES**:
1. Update dataclass fields (lines 48-88):
   - `primary_entry_price` → `eth_entry_price`
   - `hedge_entry_price` → `sol_entry_price`
   - `primary_exit_price` → `eth_exit_price`
   - `hedge_exit_price` → `sol_exit_price`
   - `primary_entry_time` → `eth_entry_time`
   - `hedge_entry_time` → `sol_entry_time`
   - `primary_exit_time` → `eth_exit_time`
   - `hedge_exit_time` → `sol_exit_time`
   - `order_to_fill_primary` → `order_to_fill_eth`
   - `order_to_fill_hedge` → `order_to_fill_sol`
   - Remove: `hedge_entry_order_type`, `hedge_exit_order_type`, `hedge_entry_fee_saved`, `hedge_exit_fee_saved`

**VERIFICATION**:
```bash
grep -n "primary_entry_price\|hedge_entry_price" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
# Should return: ONLY lines 55-56 (dataclass definition), no other occurrences
```

**DEPENDENTS**: Phase 2 (Constructor), Phase 8 (trading_loop)

---

### PHASE 2: Constructor Variable Updates
**PREREQUISITES**: Phase 1 complete
**EXECUTION TIME**: ~10 minutes
**CHANGES**:
1. Update `__init__` signature (already done at line 102-111):
   - Already has `target_notional` ✓
   - Change single `order_mode` to `eth_mode` and `sol_mode`
   - Remove `order_quantity` parameter (calculated dynamically)

2. Update instance variable initialization (lines 175-184):
   - Already has `current_eth_entry_price` etc. ✓
   - Remove: `current_primary_entry_price`, `current_hedge_entry_price` (if exist)

**VERIFICATION**:
```bash
grep -n "self.primary_\|self.hedge_" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py | grep -v "def \|class \|#" 
# Should return: Empty (no instance variables with old names)
```

**DEPENDENTS**: Phase 3 (initialize_clients)

---

### PHASE 3: Client Initialization Update
**PREREQUISITES**: Phase 2 complete
**EXECUTION TIME**: ~15 minutes
**CHANGES**:
1. Update `_create_exchange_config()` method (lines 339-356):
   - Remove `quantity` parameter
   - Set `quantity` to Decimal("0") placeholder

2. Update `initialize_clients()` method (lines 408-451):
   ```python
   async def initialize_clients(self):
       # Create ETH client
       eth_config = self._create_exchange_config(self.eth_ticker)
       self.eth_client = NadoClient(eth_config)
       
       # Create SOL client
       sol_config = self._create_exchange_config(self.sol_ticker)
       self.sol_client = NadoClient(sol_config)
       
       # Get contract attributes for both
       (self.eth_contract_id, self.eth_tick_size) = await self.eth_client.get_contract_attributes()
       (self.sol_contract_id, self.sol_tick_size) = await self.sol_client.get_contract_attributes()
       
       self.logger.info(f"[INIT] ETH contract: {self.eth_contract_id}, tick: {self.eth_tick_size}")
       self.logger.info(f"[INIT] SOL contract: {self.sol_contract_id}, tick: {self.sol_tick_size}")
   ```

3. Update `cleanup_connections()` method (lines 307-314):
   ```python
   async def cleanup_connections(self):
       if self.sol_client:
           try:
               await self.sol_client.disconnect()
           except Exception:
               pass
       if self.eth_client:
           try:
               await self.eth_client.disconnect()
           except Exception:
               pass
   ```

4. Update `connect_websockets()` method (lines 453-467):
   ```python
   async def connect_websockets(self):
       def eth_order_handler(order_data):
           self._handle_eth_order_update(order_data)
       
       def sol_order_handler(order_data):
           self._handle_sol_order_update(order_data)
       
       self.eth_client.setup_order_update_handler(eth_order_handler)
       self.sol_client.setup_order_update_handler(sol_order_handler)
       
       await self.eth_client.connect()
       self.logger.info("[WS] ETH (NADO) connected")
       
       await self.sol_client.connect()
       self.logger.info("[WS] SOL (NADO) connected")
   ```

**VERIFICATION**:
```bash
grep -n "primary_client\|hedge_client" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
# Should return: Empty (all references replaced)
```

**DEPENDENTS**: Phase 4 (New Methods), Phase 5 (Order Placement)

---

### PHASE 4: Add New Pair Trading Methods
**PREREQUISITES**: Phase 3 complete
**EXECUTION TIME**: ~30 minutes
**NEW METHODS TO ADD** (after line 356):

#### 4.1 calculate_order_size()
```python
def calculate_order_size(self, price: Decimal) -> Decimal:
    """
    Calculate order size based on target notional value.
    
    Args:
        price: Current price of the asset
        
    Returns:
        Order size in base currency (e.g., ETH or SOL)
    """
    if price <= 0:
        raise ValueError(f"Invalid price: {price}")
    
    order_size = self.target_notional / price
    
    # Round to appropriate precision (8 decimals for crypto)
    order_size = order_size.quantize(Decimal("0.00000001"))
    
    self.logger.info(
        f"[SIZING] Target notional: ${self.target_notional:.2f}, "
        f"Price: ${price:.2f}, Order size: {order_size:.8f}"
    )
    
    return order_size
```

#### 4.2 _place_single_order()
```python
async def _place_single_order(
    self,
    client: NadoClient,
    contract_id: str,
    side: str,
    size: Decimal,
    price: Decimal,
    ticker: str
) -> Optional[Decimal]:
    """
    Place a single order and wait for fill.
    
    CRITICAL: Returns actual fill price from OrderInfo, NOT OrderResult.price
    
    Args:
        client: NadoClient instance
        contract_id: Contract ID
        side: "buy" or "sell"
        size: Order size
        price: Order price (for logging only, actual price from order book)
        ticker: Ticker name for logging
        
    Returns:
        Fill price if successful, None otherwise
    """
    try:
        # Step 1: Place order (returns OrderResult with initial price)
        order_result = await client.place_open_order(
            contract_id=contract_id,
            quantity=size,
            direction=side
        )
        
        if not order_result.success or not order_result.order_id:
            self.logger.error(f"[{ticker}] Failed to place order: {order_result.error_message}")
            return None
        
        order_id = order_result.order_id
        self.logger.info(f"[{ticker}] Order placed: {order_id}")
        
        # Step 2: Wait for fill (poll get_order_info until status='FILLED')
        start_time = time.time()
        while time.time() - start_time < self.fill_timeout:
            order_info = await client.get_order_info(order_id)
            
            if order_info.status == 'FILLED':
                fill_price = order_info.price  # ← ACTUAL FILL PRICE
                self.logger.info(f"[{ticker}] Order filled: {size:.8f} @ ${fill_price:.2f}")
                return fill_price
            
            if order_info.status == 'CANCELLED':
                self.logger.warning(f"[{ticker}] Order cancelled")
                return None
            
            await asyncio.sleep(0.1)
        
        # Step 3: Timeout - cancel order
        await client.cancel_order(order_id)
        self.logger.warning(f"[{ticker}] Order timeout, cancelled")
        return None
        
    except Exception as e:
        self.logger.error(f"[{ticker}] Error placing order: {e}")
        return None
```

#### 4.3 place_simultaneous_orders()
```python
async def place_simultaneous_orders(
    self,
    eth_side: str,
    sol_side: str,
    eth_price: Decimal,
    sol_price: Decimal
) -> Tuple[bool, Optional[Decimal], Optional[Decimal]]:
    """
    Place both ETH and SOL orders simultaneously for pair entry/exit.
    
    CRITICAL: Uses asyncio.gather() for true simultaneous execution.
    Returns actual fill prices from OrderInfo, NOT OrderResult.price
    
    Args:
        eth_side: "buy" or "sell" for ETH
        sol_side: "buy" or "sell" for SOL
        eth_price: Price for ETH order
        sol_price: Price for SOL order
        
    Returns:
        Tuple of (success, eth_fill_price, sol_fill_price)
        
    Integration Point:
        Called from: execute_dn_cycle() method
    """
    self.eth_order_status = None
    self.sol_order_status = None
    
    # Calculate order sizes based on notional
    eth_size = self.calculate_order_size(eth_price)
    sol_size = self.calculate_order_size(sol_price)
    
    self.logger.info(
        f"[SIMULTANEOUS] Placing orders: "
        f"ETH {eth_side.upper()} {eth_size:.8f} @ ${eth_price:.2f}, "
        f"SOL {sol_side.upper()} {sol_size:.8f} @ ${sol_price:.2f}"
    )
    
    # Create tasks for simultaneous execution
    eth_task = asyncio.create_task(
        self._place_single_order(self.eth_client, self.eth_contract_id, eth_side, eth_size, eth_price, "ETH")
    )
    sol_task = asyncio.create_task(
        self._place_single_order(self.sol_client, self.sol_contract_id, sol_side, sol_size, sol_price, "SOL")
    )
    
    # Wait for both orders to complete (with timeout)
    try:
        eth_fill_price, sol_fill_price = await asyncio.wait_for(
            asyncio.gather(eth_task, sol_task, return_exceptions=True),
            timeout=self.fill_timeout
        )
        
        # Check for exceptions
        if isinstance(eth_fill_price, Exception):
            self.logger.error(f"[SIMULTANEOUS] ETH order failed: {eth_fill_price}")
            eth_fill_price = None
        if isinstance(sol_fill_price, Exception):
            self.logger.error(f"[SIMULTANEOUS] SOL order failed: {sol_fill_price}")
            sol_fill_price = None
        
        # Check results
        if eth_fill_price and sol_fill_price:
            self.logger.info("[SIMULTANEOUS] Both orders filled successfully")
            return True, eth_fill_price, sol_fill_price
        else:
            self.logger.error(
                f"[SIMULTANEOUS] Partial fill - ETH: {eth_fill_price}, SOL: {sol_fill_price}"
            )
            # Handle partial fill scenario
            await self._handle_partial_fill(eth_fill_price, sol_fill_price, eth_side, sol_side, eth_size, sol_size)
            return False, eth_fill_price, sol_fill_price
            
    except asyncio.TimeoutError:
        self.logger.error("[SIMULTANEOUS] Timeout waiting for orders to fill")
        # Cancel any pending orders
        await self._cancel_pending_orders()
        return False, None, None
    except Exception as e:
        self.logger.error(f"[SIMULTANEOUS] Error placing orders: {e}")
        return False, None, None
```

#### 4.4 _handle_partial_fill()
```python
async def _handle_partial_fill(
    self,
    eth_fill_price: Optional[Decimal],
    sol_fill_price: Optional[Decimal],
    eth_side: str,
    sol_side: str,
    eth_size: Decimal,
    sol_size: Decimal
):
    """
    Handle scenario where only one side of the pair filled.
    
    CRITICAL: Emergency unwind to prevent delta exposure.
    """
    if eth_fill_price and not sol_fill_price:
        self.logger.error("[PARTIAL] ETH filled but SOL failed - emergency unwind ETH")
        await self._emergency_unwind_ticker("ETH", eth_side, eth_size)
    elif sol_fill_price and not eth_fill_price:
        self.logger.error("[PARTIAL] SOL filled but ETH failed - emergency unwind SOL")
        await self._emergency_unwind_ticker("SOL", sol_side, sol_size)
    else:
        self.logger.error("[PARTIAL] Both orders failed - no positions to unwind")

async def _emergency_unwind_ticker(self, ticker: str, side: str, size: Decimal):
    """Emergency unwind of a single ticker position."""
    unwind_side = "sell" if side == "buy" else "buy"
    
    self.logger.error(
        f"[EMERGENCY] Unwinding {ticker}: {unwind_side.upper()} {size:.8f}"
    )
    
    client = self.eth_client if ticker == "ETH" else self.sol_client
    contract_id = self.eth_contract_id if ticker == "ETH" else self.sol_contract_id
    
    try:
        # Use aggressive market order for immediate exit
        best_bid, best_ask = await client.fetch_bbo_prices(contract_id)
        unwind_price = best_ask if unwind_side == "buy" else best_bid
        
        await client.place_open_order(
            contract_id=contract_id,
            quantity=size,
            direction=unwind_side
        )
        self.logger.error(f"[EMERGENCY] Successfully unwound {ticker}")
    except Exception as e:
        self.logger.error(f"[EMERGENCY] Failed to unwind {ticker}: {e}")
        self.stop_flag = True  # Stop trading
```

#### 4.5 _cancel_pending_orders()
```python
async def _cancel_pending_orders(self):
    """Cancel all pending orders for both ETH and SOL."""
    self.logger.warning("[CANCEL] Cancelling all pending orders")
    
    try:
        # Cancel ETH orders
        eth_orders = await self.eth_client.get_active_orders(self.eth_contract_id)
        for order in eth_orders:
            await self.eth_client.cancel_order(order.order_id)
            self.logger.info(f"[CANCEL] Cancelled ETH order: {order.order_id}")
            
        # Cancel SOL orders
        sol_orders = await self.sol_client.get_active_orders(self.sol_contract_id)
        for order in sol_orders:
            await self.sol_client.cancel_order(order.order_id)
            self.logger.info(f"[CANCEL] Cancelled SOL order: {order.order_id}")
            
    except Exception as e:
        self.logger.error(f"[CANCEL] Error cancelling orders: {e}")
```

**VERIFICATION**:
```bash
# Check methods exist
grep -n "def calculate_order_size\|def _place_single_order\|def place_simultaneous_orders\|def _handle_partial_fill\|def _emergency_unwind_ticker\|def _cancel_pending_orders" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
```

**DEPENDENTS**: Phase 5 (Order Placement), Phase 8 (Trading Loop)

---

### PHASE 5: Update Order Placement Methods
**PREREQUISITES**: Phase 3 complete, Phase 4 complete
**EXECUTION TIME**: ~20 minutes
**CHANGES**:

1. Remove `place_primary_order()` method (lines 701-834) - DELETE
2. Remove `place_hedge_order()` method (lines 836-1400) - DELETE
3. Remove `check_arbitrage_opportunity()` method (lines 381-407) - DELETE

**REASON**: These are replaced by `place_simultaneous_orders()` from Phase 4

**VERIFICATION**:
```bash
grep -n "def place_primary_order\|def place_hedge_order\|def check_arbitrage" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
# Should return: Empty (all deleted)
```

**DEPENDENTS**: Phase 8 (Trading Loop)

---

### PHASE 6: Update Order Handlers
**PREREQUISITES**: Phase 3 complete
**EXECUTION TIME**: ~15 minutes
**CHANGES** (CAN RUN IN PARALLEL WITH PHASE 5):

1. Update `_handle_primary_order_update` → `_handle_eth_order_update` (lines 469-523):
   - Rename method
   - Replace `primary_contract_id` → `eth_contract_id`
   - Replace `primary_position` → `eth_position`
   - Replace `local_primary_position` → `local_eth_position`
   - Replace `primary_exchange` → "NADO"
   - Remove hedge trigger logic
   - Update logging to use "ETH" ticker

2. Update `_handle_hedge_order_update` → `_handle_sol_order_update` (lines 531-575):
   - Rename method
   - Replace `hedge_contract_id` → `sol_contract_id`
   - Replace `hedge_position` → `sol_position`
   - Replace `local_hedge_position` → `local_sol_position`
   - Replace `hedge_exchange` → "NADO"
   - Remove `hedge_order_filled` tracking
   - Update logging to use "SOL" ticker

**VERIFICATION**:
```bash
grep -n "def _handle_primary_order_update\|def _handle_hedge_order_update" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
# Should return: Empty (both renamed)
```

**DEPENDENTS**: None (standalone methods)

---

### PHASE 7: Update Position Management
**PREREQUISITES**: Phase 3 complete
**EXECUTION TIME**: ~15 minutes
**CHANGES** (CAN RUN IN PARALLEL WITH PHASE 5):

1. Update `get_positions()` method (lines 582-605):
   ```python
   async def get_positions(
       self,
       force_api: bool = False,
       eth_only: bool = False,
       sol_only: bool = False
   ) -> Tuple[Decimal, Decimal]:
       """
       Get current positions for ETH and SOL.
       
       Returns:
           Tuple of (eth_position, sol_position)
       """
       if self.use_local_tracking and not force_api:
           return self.local_eth_position, self.local_sol_position
       
       eth_pos = await self.eth_client.get_account_positions() if not sol_only else Decimal("0")
       sol_pos = await self.sol_client.get_account_positions() if not eth_only else Decimal("0")
       
       return eth_pos, sol_pos
   ```

2. Update `reconcile_positions()` method (lines 606-700):
   - Replace all `primary_*` → `eth_*`
   - Replace all `hedge_*` → `sol_*`
   - Update logging messages
   - Ensure reconciliation checks both ETH and SOL positions

**VERIFICATION**:
```bash
grep -n "primary_position\|hedge_position" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py | grep -v "def \|class \|#" 
# Should return: Only TradeMetrics dataclass fields (already renamed in Phase 1)
```

**DEPENDENTS**: Phase 8 (Trading Loop)

---

### PHASE 8: Update Trading Loop
**PREREQUISITES**: Phase 4 complete, Phase 5 complete, Phase 7 complete
**EXECUTION TIME**: ~30 minutes
**CHANGES**:

1. Update `execute_dn_cycle()` method (lines 1889-1969):
   ```python
   async def execute_dn_cycle(
       self,
       direction: str
   ) -> Tuple[bool, Optional[Decimal], Optional[Decimal]]:
       """
       Execute one DN cycle: BUILD or UNWIND both positions simultaneously.
       
       Args:
           direction: "buy" for BUILD, "sell" for UNWIND
           
       Returns:
           Tuple of (success, eth_fill_price, sol_fill_price)
       """
       await self._pre_trade_check()
       
       # Get current prices
       eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_contract_id)
       sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_contract_id)
       
       # Determine order sides and prices
       if direction == "buy":
           # BUILD: Long ETH, Short SOL
           eth_side = "buy"
           sol_side = "sell"
           eth_price = self.calculate_order_price("buy", eth_bid, eth_ask, self.eth_tick_size, self.eth_mode)
           sol_price = self.calculate_order_price("sell", sol_bid, sol_ask, self.sol_tick_size, self.sol_mode)
       else:
           # UNWIND: Sell ETH, Buy SOL
           eth_side = "sell"
           sol_side = "buy"
           eth_price = self.calculate_order_price("sell", eth_bid, eth_ask, self.eth_tick_size, self.eth_mode)
           sol_price = self.calculate_order_price("buy", sol_bid, sol_ask, self.sol_tick_size, self.sol_mode)
       
       # Place simultaneous orders
       success, eth_fill_price, sol_fill_price = await self.place_simultaneous_orders(
           eth_side, sol_side, eth_price, sol_price
       )
       
       if not success:
           return False, None, None
       
       # Update tracking
       if direction == "buy":
           # BUILD cycle
           if self.current_eth_entry_price is None:
               self.current_eth_entry_price = eth_fill_price
               self.current_eth_entry_time = time.time()
           if self.current_sol_entry_price is None:
               self.current_sol_entry_price = sol_fill_price
               self.current_sol_entry_time = time.time()
       else:
           # UNWIND cycle
           self.current_eth_exit_price = eth_fill_price
           self.current_eth_exit_time = time.time()
           self.current_sol_exit_price = sol_fill_price
           self.current_sol_exit_time = time.time()
       
       return True, eth_fill_price, sol_fill_price
   ```

2. Update `trading_loop()` method (lines 2016-2318):
   - Remove references to `primary_exchange` and `hedge_exchange`
   - Update logging to show "ETH/SOL Pair Trading"
   - Remove cold start workaround logic
   - Update position initialization to use `get_positions()`
   - Remove residual position auto-close for hedge logic

3. Update `_create_trade_metrics()` method (lines 1817-1843):
   ```python
   def _create_trade_metrics(self, iteration: int, direction: str) -> TradeMetrics:
       """Create TradeMetrics object from current cycle data."""
       cycle_time = time.time() - self.current_cycle_start_time if self.current_cycle_start_time else 0
   
       return TradeMetrics(
           iteration=iteration,
           direction=direction,
           eth_entry_price=self.current_eth_entry_price or Decimal("0"),
           sol_entry_price=self.current_sol_entry_price or Decimal("0"),
           eth_entry_time=self.current_eth_entry_time or 0,
           sol_entry_time=self.current_sol_entry_time or 0,
           eth_exit_price=self.current_eth_exit_price or Decimal("0"),
           sol_exit_price=self.current_sol_exit_price or Decimal("0"),
           eth_exit_time=self.current_eth_exit_time or 0,
           sol_exit_time=self.current_sol_exit_time or 0,
           order_to_fill_eth=self.current_order_to_fill_eth,
           order_to_fill_sol=self.current_order_to_fill_sol,
           # ... other fields
       )
   ```

**VERIFICATION**:
```bash
# Check for old variable references in trading loop
grep -n "primary_fill_price\|hedge_fill_price" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
# Should return: Empty
```

**DEPENDENTS**: Phase 9 (CLI + main)

---

### PHASE 9: Update CLI Arguments and Main
**PREREQUISITES**: Phase 8 complete
**EXECUTION TIME**: ~10 minutes
**CHANGES**:

1. Update `parse_arguments()` function (lines 2332-2429):
   ```python
   def parse_arguments():
       import argparse
   
       parser = argparse.ArgumentParser(
           description="DN Pair Trading Bot: ETH/SOL on Nado",
           formatter_class=argparse.RawDescriptionHelpFormatter,
           epilog="""
   Examples:
       # Basic: $100 notional per position, 5 iterations
       python DN_pair_eth_sol_nado.py --size 100 --iter 5
   
       # Custom order modes
       python DN_pair_eth_sol_nado.py --size 100 --iter 10 --eth-mode bbo --sol-mode aggressive
   
       # With sleep between iterations
       python DN_pair_eth_sol_nado.py --size 100 --iter 5 --sleep 1
           """,
       )
   
       parser.add_argument(
           "--size",
           type=lambda x: Decimal(x),
           required=True,
           help="Target notional in USD (e.g., 100 = $100 ETH and $100 SOL positions)"
       )
       parser.add_argument(
           "--iter",
           type=int,
           default=20,
           help="Number of iterations (default: 20)"
       )
       parser.add_argument(
           "--eth-mode",
           type=str,
           default="bbo",
           choices=["bbo_minus_1", "bbo_plus_1", "bbo", "aggressive", "market"],
           help="ETH order mode (default: bbo)"
       )
       parser.add_argument(
           "--sol-mode",
           type=str,
           default="bbo",
           choices=["bbo_minus_1", "bbo_plus_1", "bbo", "aggressive", "market"],
           help="SOL order mode (default: bbo)"
       )
       parser.add_argument(
           "--timeout",
           type=int,
           default=5,
           help="Fill timeout in seconds (default: 5)"
       )
       parser.add_argument(
           "--sleep",
           type=int,
           default=0,
           help="Sleep time between iterations in seconds (default: 0)"
       )
       parser.add_argument(
           "--env-file", 
           type=str, 
           default=".env", 
           help=".env file path (default: .env)"
       )
       
       return parser.parse_args()
   ```

2. Update `main()` function (lines 2433-2472):
   ```python
   async def main():
       args = parse_arguments()
       
       bot = DNPairBot(
           target_notional=args.size,
           iterations=args.iter,
           fill_timeout=args.timeout,
           sleep_time=args.sleep,
           eth_mode=PriceMode(args.eth_mode),
           sol_mode=PriceMode(args.sol_mode),
       )
       
       bot.setup_signal_handlers()
       
       try:
           await bot.run()
       except KeyboardInterrupt:
           bot.logger.info("\n[MAIN] Interrupted by user")
       except Exception as e:
           bot.logger.error(f"[MAIN] Error: {e}")
           import traceback
           bot.logger.error(f"[MAIN] Traceback: {traceback.format_exc()}")
       finally:
           bot.shutdown()
   ```

**VERIFICATION**:
```bash
# Test argument parsing
python /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py --help
# Should show: DN Pair Trading Bot: ETH/SOL on Nado
# Should have: --size, --iter, --eth-mode, --sol-mode, --timeout, --sleep
# Should NOT have: --ticker, --primary, --hedge, --hedge-post-only, --min-spread
```

**DEPENDENTS**: None (final phase)

---

## Testing and Verification Plan

### Phase 10: Pre-Deployment Verification

#### 10.1 Syntax Check
```bash
python -m py_compile /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py
# Expected: No output (success)
```

#### 10.2 Import Check
```bash
python -c "from hedge.DN_pair_eth_sol_nado import DNPairBot; print('Import successful')"
# Expected: Import successful
```

#### 10.3 Reference Audit
```bash
# Check for remaining old references
grep -r "primary_client\|hedge_client" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py && echo "FOUND OLD REFERENCES" || echo "ALL CLEAN"
# Expected: ALL CLEAN

grep -r "primary_entry_price\|hedge_entry_price" /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py && echo "FOUND OLD REFERENCES" || echo "ALL CLEAN"
# Expected: ALL CLEAN (only TradeMetrics dataclass fields should exist, renamed in Phase 1)
```

#### 10.4 Dry Run
```bash
python /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py --size 100 --iter 0 --eth-mode bbo --sol-mode bbo
# Expected: Initialization logs, but no trading (iter=0)
```

### Phase 11: Post-Deployment Testing

#### 11.1 Small Scale Test
```bash
python /Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py --size 10 --iter 2 --eth-mode bbo --sol-mode bbo
```

#### 11.2 Log Validation
```bash
# Check initialization
tail -50 /Users/botfarmer/2dex/hedge/logs/DN_pair_eth_sol_nado_log.txt | grep -E "\[INIT\]|\[WS\]|\[SIZING\]|\[SIMULTANEOUS\]"
# Expected:
# [INFO] [INIT] Creating Nado client for ETH
# [INFO] [INIT] Creating Nado client for SOL
# [INFO] [INIT] ETH contract: 2, tick: 0.01
# [INFO] [INIT] SOL contract: 3, tick: 0.001
# [INFO] [WS] ETH (NADO) connected
# [INFO] [WS] SOL (NADO) connected
# [INFO] [SIZING] Target notional: $10.00, Price: $2500.00, Order size: 0.00400000
# [INFO] [SIZING] Target notional: $10.00, Price: $100.00, Order size: 0.10000000
# [INFO] [SIMULTANEOUS] Placing orders: ETH BUY 0.00400000 @ $2500.00, SOL SELL 0.10000000 @ $100.00

# Check simultaneous execution (timestamps should be close)
grep "Order placed" /Users/botfarmer/2dex/hedge/logs/DN_pair_eth_sol_nado_log.txt | tail -10
# Expected: ETH and SOL orders placed within same second
```

#### 11.3 CSV Validation
```bash
head -10 /Users/botfarmer/2dex/hedge/logs/DN_pair_eth_sol_nado_trades.csv
# Expected format:
# exchange,timestamp,side,price,quantity,order_type,mode
# NADO,2026-01-29T...,buy,2500.50,0.004,OPEN,bbo
# NADO,2026-01-29T...,sell,100.25,0.1,OPEN,bbo
```

---

## Critical Files for Implementation

- `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py` - Main file to refactor (2472 lines, PARTIALLY CONVERTED)
- `/Users/botfarmer/2dex/exchanges/nado.py` - NadoClient API reference (lines 152-211 for place_open_order signature)
- `/Users/botfarmer/2dex/exchanges/base.py` - OrderResult/OrderInfo dataclass definitions (lines 36-56)
- `/Users/botfarmer/2dex/hedge/DN_alternate_nado_edgex.py` - Original template for reference patterns

---

## Implementation Checklist

- [ ] Phase 1: TradeMetrics dataclass update (lines 48-88)
- [ ] Phase 2: Constructor variable updates (lines 102-184)
- [ ] Phase 3: Client initialization update (lines 307-467)
- [ ] Phase 4: Add new pair trading methods (after line 356)
  - [ ] 4.1 calculate_order_size()
  - [ ] 4.2 _place_single_order()
  - [ ] 4.3 place_simultaneous_orders()
  - [ ] 4.4 _handle_partial_fill()
  - [ ] 4.5 _emergency_unwind_ticker()
  - [ ] 4.6 _cancel_pending_orders()
- [ ] Phase 5: Remove old order placement methods (lines 381-1400)
- [ ] Phase 6: Update order handlers (lines 469-575)
- [ ] Phase 7: Update position management (lines 582-700)
- [ ] Phase 8: Update trading loop (lines 1817-2318)
- [ ] Phase 9: Update CLI and main (lines 2332-2472)
- [ ] Phase 10: Pre-deployment verification
- [ ] Phase 11: Post-deployment testing

---

## Risk Mitigation

### Critical Risks

1. **Partial Fill Scenario**: If one order fills but the other doesn't
   - **Mitigation**: `_handle_partial_fill()` method with emergency unwind
   - **Fallback**: Stop trading and alert user

2. **API Signature Mismatch**: Incorrect return type handling
   - **Mitigation**: `OrderResult.price` vs `OrderInfo.price` distinction clearly documented
   - **Fallback**: Extensive logging of all API calls

3. **State Inconsistency**: Partial file conversion
   - **Mitigation**: Execute phases in strict dependency order
   - **Verification**: Grep audits after each phase

4. **Integration Point Missing**: place_simultaneous_orders not called
   - **Mitigation**: Explicit integration point documented in Phase 8
   - **Verification**: Execute_dn_cycle() code review

---

## Summary

**KEY INSIGHTS FROM CRITIC FEEDBACK**:
1. File is PARTIALLY converted, not fresh copy
2. NadoClient API returns OrderResult, need to poll for actual fill price
3. place_simultaneous_orders must be integrated into execute_dn_cycle
4. All field renames must be tracked via grep patterns
5. CLI needs complete rewrite for pair trading parameters
6. Strict phase dependencies must be followed
7. Testing must verify log outputs and timing evidence

**CRITICAL PATH**: Phase 1 → 2 → 3 → 4 → 5 → 8 → 9 (Phases 6, 7 can run in parallel with 5)

**TOTAL ESTIMATED TIME**: ~2.5 hours for all phases
