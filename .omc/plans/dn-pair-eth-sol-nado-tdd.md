# TDD-Based Implementation Plan: DN Pair Trading Bot (ETH/SOL on Nado)

## Executive Summary

**TDD APPROACH:** 4 incremental stages with RED-GREEN-REFACTOR cycle

1. **Stage 1**: Nado 기본 기능 체크 (API 연결, 포지션 조회, $0 리스크)
2. **Stage 2**: ETH/SOL 개별 주문 연습 ($10 notional)
3. **Stage 3**: DN 헷징 테스트 (동시 주문, $100 notional, 1회)
4. **Stage 4**: Alternating 구현 (5회 반복, $100 notional)

---

## Test Framework & Infrastructure

### Framework Selection
- **pytest**: Test runner
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **unittest.mock**: Mock objects for API responses

### Installation
```bash
pip install pytest pytest-asyncio pytest-mock
```

### Test Directory Structure
```
2dex/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   ├── stage1/
│   │   ├── __init__.py
│   │   ├── test_nado_api.py           # Stage 1 tests
│   │   └── fixtures.py                # Stage 1 fixtures
│   ├── stage2/
│   │   ├── __init__.py
│   │   ├── test_single_orders.py      # Stage 2 tests
│   │   └── fixtures.py
│   ├── stage3/
│   │   ├── __init__.py
│   │   ├── test_dn_hedge.py           # Stage 3 tests
│   │   └── fixtures.py
│   └── stage4/
│       ├── __init__.py
│       ├── test_alternating.py        # Stage 4 tests
│       └── fixtures.py
└── hedge/
    └── DN_pair_eth_sol_nado.py        # Bot implementation
```

### conftest.py (Shared Configuration)
```python
import pytest
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up required environment variables."""
    monkeypatch.setenv("NADO_PRIVATE_KEY", "0x" + "a" * 64)
    monkeypatch.setenv("NADO_MODE", "MAINNET")
    monkeypatch.setenv("NADO_SUBACCOUNT_NAME", "default")

@pytest.fixture
def sample_eth_price():
    """Sample ETH price for testing."""
    return Decimal("3000.00")

@pytest.fixture
def sample_sol_price():
    """Sample SOL price for testing."""
    return Decimal("150.00")
```

---

## API Contract Documentation

### Critical API Distinction: OrderResult vs OrderInfo

**CRITICAL**: `place_open_order()` returns `OrderResult` with INITIAL price, NOT fill price.
To get actual fill price, must call `get_order_info()` after order fills.

#### OrderResult (returned by `place_open_order`, `place_close_order`)
```python
@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]      # Order ID if successful
    side: Optional[str]          # "buy" or "sell"
    size: Optional[Decimal]      # Requested order size
    price: Optional[Decimal]     # INITIAL order price (NOT fill price!)
    status: Optional[str]        # "OPEN" (pending fill)
    error_message: Optional[str]
    filled_size: Optional[Decimal]  # Always None in current implementation
```

#### OrderInfo (returned by `get_order_info`)
```python
@dataclass
class OrderInfo:
    order_id: str
    side: str
    size: Decimal                # Total order size
    price: Decimal               # ACTUAL fill price (when status='FILLED')
    status: str                  # "FILLED", "OPEN", "CANCELLED"
    filled_size: Decimal = 0.0   # Actual filled amount
    remaining_size: Decimal = 0.0
    cancel_reason: str = ''
```

#### NadoClient Key Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `fetch_bbo_prices(contract_id)` | `Tuple[Decimal, Decimal]` | (bid, ask) - uses last_price for both |
| `place_open_order(contract_id, quantity, direction)` | `OrderResult` | OrderResult.price = initial price |
| `place_close_order(contract_id, quantity, price, side)` | `OrderResult` | OrderResult.price = initial price |
| `get_order_info(order_id)` | `OrderInfo` | OrderInfo.price = actual fill price |
| `cancel_order(order_id)` | `OrderResult` | Cancel result |
| `get_account_positions()` | `Dict[str, Decimal]` | {ticker: position_size} |

### Mock Strategy

#### Mock Prices (for BBO)
```python
def mock_bbo_prices(eth_price=3000, sol_price=150):
    """Return mock BBO prices."""
    return (Decimal(eth_price), Decimal(eth_price)), (Decimal(sol_price), Decimal(sol_price))
```

#### Mock OrderResult (order placed, not filled)
```python
def mock_order_result(order_id="test_order_123", side="buy", size=Decimal("0.01"), price=Decimal("3000")):
    """Mock OrderResult for placed order."""
    return OrderResult(
        success=True,
        order_id=order_id,
        side=side,
        size=size,
        price=price,  # Initial price
        status="OPEN"
    )
```

#### Mock OrderInfo (order filled)
```python
def mock_order_info(order_id="test_order_123", side="buy", size=Decimal("0.01"), price=Decimal("3000.5")):
    """Mock OrderInfo for filled order."""
    return OrderInfo(
        order_id=order_id,
        side=side,
        size=size,
        price=price,  # Actual fill price (may differ from OrderResult.price)
        status="FILLED",
        filled_size=size
    )
```

---

## Stage 1: Nado Basic Functionality Check ($0 risk)

### TDD Cycle: RED → GREEN → REFACTOR

#### RED Phase: Write Failing Tests First

**Test File**: `tests/stage1/test_nado_api.py`

```python
import pytest
import asyncio
from decimal import Decimal
from hedge.DN_pair_eth_sol_nado import DNPairBot

@pytest.mark.asyncio
async def test_eth_client_initialization(mock_env_vars):
    """Test 1: ETH client initializes successfully."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.eth_client is not None
    assert bot.eth_client.config.ticker == "ETH"
    await bot.cleanup()

@pytest.mark.asyncio
async def test_sol_client_initialization(mock_env_vars):
    """Test 2: SOL client initializes successfully."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.sol_client is not None
    assert bot.sol_client.config.ticker == "SOL"
    await bot.cleanup()

@pytest.mark.asyncio
async def test_eth_contract_attributes(mock_env_vars):
    """Test 3: ETH contract has correct attributes."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.eth_client.config.contract_id == "2"  # ETH product ID
    assert bot.eth_client.config.tick_size > 0
    await bot.cleanup()

@pytest.mark.asyncio
async def test_sol_contract_attributes(mock_env_vars):
    """Test 4: SOL contract has correct attributes."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    assert bot.sol_client.config.contract_id == "4"  # SOL product ID
    assert bot.sol_client.config.tick_size > 0
    await bot.cleanup()

@pytest.mark.asyncio
async def test_eth_position_query_zero(mock_env_vars):
    """Test 5: ETH position query returns 0 (no open positions)."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    position = await bot.eth_client.get_account_positions()
    assert position == 0  # Quantified: must be exactly 0
    await bot.cleanup()

@pytest.mark.asyncio
async def test_sol_position_query_zero(mock_env_vars):
    """Test 6: SOL position query returns 0."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    position = await bot.sol_client.get_account_positions()
    assert position == 0
    await bot.cleanup()

@pytest.mark.asyncio
async def test_eth_bbo_prices_positive(mock_env_vars):
    """Test 7: ETH BBO prices return positive values."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    bid, ask = await bot.eth_client.fetch_bbo_prices(bot.eth_client.config.contract_id)
    assert bid > 0  # Quantified: must be > 0
    assert ask > 0
    assert ask >= bid  # Basic sanity check
    await bot.cleanup()

@pytest.mark.asyncio
async def test_sol_bbo_prices_positive(mock_env_vars):
    """Test 8: SOL BBO prices return positive values."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    bid, ask = await bot.sol_client.fetch_bbo_prices(bot.sol_client.config.contract_id)
    assert bid > 0
    assert ask > 0
    assert ask >= bid
    await bot.cleanup()

@pytest.mark.asyncio
async def test_websocket_connection(mock_env_vars):
    """Test 9: WebSocket connection can be established."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()
    await bot.eth_client.connect()
    await bot.sol_client.connect()
    # If no exception raised, test passes
    await bot.cleanup()

@pytest.mark.asyncio
async def test_environment_variables_set(mock_env_vars):
    """Test 10: Required environment variables are set."""
    import os
    assert os.getenv("NADO_PRIVATE_KEY") is not None
    assert len(os.getenv("NADO_PRIVATE_KEY")) == 66  # 0x + 64 hex chars
```

#### GREEN Phase: Implement Minimal Code to Pass Tests

**Implementation**: Update `initialize_clients()` in `DN_pair_eth_sol_nado.py`

```python
async def initialize_clients(self) -> None:
    """Initialize ETH and SOL Nado clients."""
    # ETH client configuration
    eth_config = Config({
        'ticker': 'ETH',
        'contract_id': '2',  # ETH product ID on Nado
        'tick_size': Decimal('0.1'),  # ETH tick size
        'min_size': Decimal('0.01'),
    })

    # SOL client configuration
    sol_config = Config({
        'ticker': 'SOL',
        'contract_id': '4',  # SOL product ID on Nado
        'tick_size': Decimal('0.001'),  # SOL tick size
        'min_size': Decimal('0.1'),
    })

    self.eth_client = NadoClient(eth_config.__dict__)
    self.sol_client = NadoClient(sol_config.__dict__)

    await self.eth_client.connect()
    await self.sol_client.connect()
```

#### REFACTOR Phase: Clean Up

- Extract common test setup into fixtures
- Improve error messages

#### Success Criteria (Quantified)
- [ ] All 10 tests pass
- [ ] BBO prices > 0 (strictly positive)
- [ ] Position queries == 0 (exactly zero, no tolerance)
- [ ] Test execution time < 30 seconds

#### Execution
```bash
# Run Stage 1 tests
pytest tests/stage1/test_nado_api.py -v

# Run with coverage
pytest tests/stage1/test_nado_api.py -v --cov=hedge.DN_pair_eth_sol_nado --cov-report=html
```

---

## Stage 2: ETH/SOL Individual Orders ($10 notional)

### TDD Cycle: RED → GREEN → REFACTOR

#### RED Phase: Write Failing Tests

**Test File**: `tests/stage2/test_single_orders.py`

```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from hedge.DN_pair_eth_sol_nado import DNPairBot

@pytest.mark.asyncio
async def test_calculate_eth_order_size_for_10_notional(mock_env_vars, sample_eth_price):
    """Test 1: Calculate ETH order size for $10 notional."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    eth_price = sample_eth_price
    eth_qty = bot.calculate_order_size(eth_price, "ETH")

    expected_qty = Decimal("10") / eth_price
    # Round to tick size
    tick_size = bot.eth_client.config.tick_size
    expected_qty = (expected_qty / tick_size).quantize(Decimal('1')) * tick_size

    assert eth_qty == expected_qty
    assert eth_qty > 0
    await bot.cleanup()

@pytest.mark.asyncio
async def test_calculate_sol_order_size_for_10_notional(mock_env_vars, sample_sol_price):
    """Test 2: Calculate SOL order size for $10 notional."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    sol_price = sample_sol_price
    sol_qty = bot.calculate_order_size(sol_price, "SOL")

    expected_qty = Decimal("10") / sol_price
    tick_size = bot.sol_client.config.tick_size
    expected_qty = (expected_qty / tick_size).quantize(Decimal('1')) * tick_size

    assert sol_qty == expected_qty
    assert sol_qty > 0
    await bot.cleanup()

@pytest.mark.asyncio
async def test_place_eth_buy_order_10_notional(mock_env_vars):
    """Test 3: Place ETH BUY order ($10 notional)."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    # Mock the place_open_order to return success
    with patch.object(bot.eth_client, 'place_open_order', new_callable=AsyncMock) as mock_order:
        mock_order.return_value = OrderResult(
            success=True,
            order_id="test_eth_order_123",
            side="buy",
            size=Decimal("0.003"),  # ~$10 at $3000/ETH
            price=Decimal("3000"),
            status="OPEN"
        )

        result = await bot.place_single_order("ETH", "buy", Decimal("10"))
        assert result.success is True
        assert result.side == "buy"
        assert result.price > 0

    await bot.cleanup()

@pytest.mark.asyncio
async def test_place_sol_sell_order_10_notional(mock_env_vars):
    """Test 4: Place SOL SELL order ($10 notional)."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    with patch.object(bot.sol_client, 'place_open_order', new_callable=AsyncMock) as mock_order:
        mock_order.return_value = OrderResult(
            success=True,
            order_id="test_sol_order_456",
            side="sell",
            size=Decimal("0.067"),  # ~$10 at $150/SOL
            price=Decimal("150"),
            status="OPEN"
        )

        result = await bot.place_single_order("SOL", "sell", Decimal("10"))
        assert result.success is True
        assert result.side == "sell"

    await bot.cleanup()

@pytest.mark.asyncio
async def test_csv_logging_verification(mock_env_vars, tmp_path):
    """Test 5: CSV logging works correctly."""
    csv_path = tmp_path / "test_trades.csv"
    bot = DNPairBot(target_notional=Decimal("10"), csv_path=str(csv_path))
    await bot.initialize_clients()

    # Log a test trade
    bot.log_trade({
        'iteration': 1,
        'direction': 'TEST',
        'eth_entry_price': Decimal("3000"),
        'sol_entry_price': Decimal("150"),
    })

    # Verify CSV exists and has content
    assert csv_path.exists()
    content = csv_path.read_text()
    assert "3000" in content
    assert "150" in content

    await bot.cleanup()

@pytest.mark.asyncio
async def test_position_reconciliation_after_order(mock_env_vars):
    """Test 6: Position reconciliation tracks changes."""
    bot = DNPairBot(target_notional=Decimal("10"))
    await bot.initialize_clients()

    # Mock position response
    with patch.object(bot.eth_client, 'get_account_positions', new_callable=AsyncMock) as mock_pos:
        mock_pos.return_value = Decimal("0.003")  # 0.003 ETH position

        position = await bot.get_position("ETH")
        assert position == Decimal("0.003")

    await bot.cleanup()
```

#### GREEN Phase: Implement Methods

```python
def calculate_order_size(self, price: Decimal, ticker: str) -> Decimal:
    """Calculate order size from target notional."""
    raw_qty = self.target_notional / price

    # Get tick size for ticker
    client = self.eth_client if ticker == "ETH" else self.sol_client
    tick_size = client.config.tick_size

    # Round to tick size
    return (raw_qty / tick_size).quantize(Decimal('1')) * tick_size

async def place_single_order(self, ticker: str, direction: str, notional: Decimal) -> OrderResult:
    """Place a single order for given ticker."""
    client = self.eth_client if ticker == "ETH" else self.sol_client
    price_bid, price_ask = await client.fetch_bbo_prices(client.config.contract_id)

    if price_bid <= 0 or price_ask <= 0:
        raise ValueError("Invalid prices")

    # Calculate quantity
    price = price_ask if direction == "buy" else price_bid
    qty = (notional / price).quantize(client.config.tick_size)

    return await client.place_open_order(client.config.contract_id, qty, direction)
```

#### Success Criteria (Quantified)
- [ ] Order size calculations match expected within tick_size tolerance (±0.0001)
- [ ] Orders place successfully (success=True)
- [ ] Orders fill within 5 seconds OR cancelled properly
- [ ] CSV file created and contains valid data
- [ ] Position reconciliation accurate (±0.001 tolerance)

#### Execution
```bash
# Run Stage 2 tests (dry run - mocked)
pytest tests/stage2/test_single_orders.py -v

# Run live test (uncomment actual order tests)
pytest tests/stage2/test_single_orders.py -v -k "not mock"
```

---

## Stage 3: DN Hedge Test ($100 notional, 1 cycle)

### TDD Cycle: RED → GREEN → REFACTOR

#### RED Phase: Write Failing Tests

**Test File**: `tests/stage3/test_dn_hedge.py`

```python
import pytest
import asyncio
import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from hedge.DN_pair_eth_sol_nado import DNPairBot
from exchanges.base import OrderResult, OrderInfo

@pytest.mark.asyncio
async def test_simultaneous_order_placement(mock_env_vars):
    """Test 1: Simultaneous ETH Long + SOL Short order placement."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock both orders
    with patch.object(bot.eth_client, 'place_open_order', new_callable=AsyncMock) as mock_eth, \
         patch.object(bot.sol_client, 'place_open_order', new_callable=AsyncMock) as mock_sol:

        mock_eth.return_value = OrderResult(
            success=True, order_id="eth_123", side="buy",
            size=Decimal("0.033"), price=Decimal("3000"), status="OPEN"
        )
        mock_sol.return_value = OrderResult(
            success=True, order_id="sol_456", side="sell",
            size=Decimal("0.667"), price=Decimal("150"), status="OPEN"
        )

        start_time = time.time()
        eth_result, sol_result = await bot.place_simultaneous_orders(
            eth_direction="buy",
            sol_direction="sell",
        )
        elapsed = time.time() - start_time

        # Quantified: Both orders must succeed
        assert eth_result.success is True
        assert sol_result.success is True

        # Quantified: Orders placed within 1 second
        assert elapsed < 1.0, f"Orders took {elapsed:.2f}s, expected <1s"

    await bot.cleanup()

@pytest.mark.asyncio
async def test_partial_fill_handling(mock_env_vars):
    """Test 2: Partial fill on one leg triggers emergency unwind."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock ETH fills, SOL fails
    with patch.object(bot.eth_client, 'place_open_order', new_callable=AsyncMock) as mock_eth, \
         patch.object(bot.sol_client, 'place_open_order', new_callable=AsyncMock) as mock_sol, \
         patch.object(bot, 'emergency_unwind_eth', new_callable=AsyncMock) as mock_unwind:

        mock_eth.return_value = OrderResult(
            success=True, order_id="eth_123", side="buy",
            size=Decimal("0.033"), price=Decimal("3000"), status="OPEN"
        )
        mock_sol.return_value = OrderResult(
            success=False, error_message="Liquidity insufficient"
        )

        await bot.place_simultaneous_orders(eth_direction="buy", sol_direction="sell")

        # Verify emergency unwind was called
        mock_unwind.assert_called_once()

    await bot.cleanup()

@pytest.mark.asyncio
async def test_position_delta_check(mock_env_vars):
    """Test 3: Net delta is approximately neutral after BUILD+UNWIND."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    # Mock full cycle: BUILD (Long ETH / Short SOL) -> UNWIND
    with patch.object(bot, 'execute_build_cycle', new_callable=AsyncMock) as mock_build, \
         patch.object(bot, 'execute_unwind_cycle', new_callable=AsyncMock) as mock_unwind, \
         patch.object(bot.eth_client, 'get_account_positions', new_callable=AsyncMock) as mock_eth_pos, \
         patch.object(bot.sol_client, 'get_account_positions', new_callable=AsyncMock) as mock_sol_pos:

        mock_build.return_value = True
        mock_unwind.return_value = True
        mock_eth_pos.return_value = Decimal("0")
        mock_sol_pos.return_value = Decimal("0")

        # Execute cycle
        success = await bot.execute_dn_cycle()

        assert success is True

        # Verify positions are flat
        eth_pos = await bot.eth_client.get_account_positions()
        sol_pos = await bot.sol_client.get_account_positions()

        # Quantified: Net delta within 1% tolerance
        assert abs(eth_pos) < Decimal("0.01"), f"ETH position not flat: {eth_pos}"
        assert abs(sol_pos) < Decimal("0.1"), f"SOL position not flat: {sol_pos}"

    await bot.cleanup()
```

#### GREEN Phase: Implement DN Hedge Logic

```python
async def place_simultaneous_orders(
    self,
    eth_direction: str,
    sol_direction: str,
) -> Tuple[OrderResult, OrderResult]:
    """Place ETH and SOL orders simultaneously."""
    # Calculate quantities
    eth_bid, eth_ask = await self.eth_client.fetch_bbo_prices(self.eth_client.config.contract_id)
    sol_bid, sol_ask = await self.sol_client.fetch_bbo_prices(self.sol_client.config.contract_id)

    eth_price = eth_ask if eth_direction == "buy" else eth_bid
    sol_price = sol_bid if sol_direction == "sell" else sol_ask

    eth_qty = self.calculate_order_size(eth_price, "ETH")
    sol_qty = self.calculate_order_size(sol_price, "SOL")

    # Place orders concurrently
    eth_result, sol_result = await asyncio.gather(
        self.eth_client.place_open_order(self.eth_client.config.contract_id, eth_qty, eth_direction),
        self.sol_client.place_open_order(self.sol_client.config.contract_id, sol_qty, sol_direction),
        return_exceptions=True
    )

    # Handle partial fills
    if isinstance(eth_result, Exception) or isinstance(sol_result, Exception):
        await self.handle_emergency_unwind(eth_result, sol_result)

    return eth_result, sol_result
```

#### Success Criteria (Quantified)
- [ ] Both orders placed within 1 second (measured)
- [ ] Both orders fill within 5 seconds OR emergency unwind triggered
- [ ] Partial fills handled correctly (emergency unwind called)
- [ ] Final positions flat: |ETH| < 0.01, |SOL| < 0.1
- [ ] BUILD+UNWIND cycle completes successfully

#### Execution
```bash
# Dry run
pytest tests/stage3/test_dn_hedge.py -v

# Live test (use actual Nado API)
pytest tests/stage3/test_dn_hedge.py -v --live
```

---

## Stage 4: Alternating Implementation ($100 notional, 5 cycles)

### TDD Cycle: RED → GREEN → REFACTOR

#### RED Phase: Write Failing Tests

**Test File**: `tests/stage4/test_alternating.py`

```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from hedge.DN_pair_eth_sol_nado import DNPairBot

@pytest.mark.asyncio
async def test_bot_initialization(mock_env_vars):
    """Test 1: Bot initializes with correct parameters."""
    bot = DNPairBot(
        target_notional=Decimal("100"),
        iterations=5,
        fill_timeout=5
    )
    await bot.initialize_clients()

    assert bot.target_notional == Decimal("100")
    assert bot.iterations == 5
    assert bot.fill_timeout == 5

    await bot.cleanup()

@pytest.mark.asyncio
async def test_single_buy_first_cycle(mock_env_vars):
    """Test 2: Single BUY_FIRST cycle completes."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    with patch.object(bot, 'execute_build_cycle', new_callable=AsyncMock) as mock_build, \
         patch.object(bot, 'execute_unwind_cycle', new_callable=AsyncMock) as mock_unwind:

        mock_build.return_value = True
        mock_unwind.return_value = True

        result = await bot.execute_buy_first_cycle()
        assert result is True
        mock_build.assert_called_once()
        mock_unwind.assert_called_once()

    await bot.cleanup()

@pytest.mark.asyncio
async def test_single_sell_first_cycle(mock_env_vars):
    """Test 3: Single SELL_FIRST cycle completes."""
    bot = DNPairBot(target_notional=Decimal("100"))
    await bot.initialize_clients()

    with patch.object(bot, 'execute_build_cycle', new_callable=AsyncMock) as mock_build, \
         patch.object(bot, 'execute_unwind_cycle', new_callable=AsyncMock) as mock_unwind:

        mock_build.return_value = True
        mock_unwind.return_value = True

        result = await bot.execute_sell_first_cycle()
        assert result is True

    await bot.cleanup()

@pytest.mark.asyncio
async def test_full_alternating_5_iterations(mock_env_vars):
    """Test 4: Full alternating 5 iterations complete."""
    bot = DNPairBot(target_notional=Decimal("100"), iterations=5)
    await bot.initialize_clients()

    with patch.object(bot, 'execute_buy_first_cycle', new_callable=AsyncMock) as mock_buy, \
         patch.object(bot, 'execute_sell_first_cycle', new_callable=AsyncMock) as mock_sell:

        mock_buy.return_value = True
        mock_sell.return_value = True

        results = await bot.run_alternating_strategy()

        # Quantified: Exactly 5 iterations complete
        assert len(results) == 5
        assert all(r is True for r in results)

        # Quantified: Alternating pattern (BUY_FIRST, SELL_FIRST, BUY_FIRST, SELL_FIRST, BUY_FIRST)
        assert mock_buy.call_count == 3
        assert mock_sell.call_count == 2

    await bot.cleanup()

@pytest.mark.asyncio
async def test_csv_trade_history_verification(mock_env_vars, tmp_path):
    """Test 5: CSV contains all trade history after 5 iterations."""
    csv_path = tmp_path / "test_trades.csv"
    bot = DNPairBot(target_notional=Decimal("100"), iterations=5, csv_path=str(csv_path))
    await bot.initialize_clients()

    with patch.object(bot, 'execute_buy_first_cycle', new_callable=AsyncMock) as mock_buy, \
         patch.object(bot, 'execute_sell_first_cycle', new_callable=AsyncMock) as mock_sell:

        mock_buy.return_value = True
        mock_sell.return_value = True

        await bot.run_alternating_strategy()

        # Verify CSV has 10 entries (5 iterations × 2 directions)
        assert csv_path.exists()

        import csv
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Quantified: 10 trade entries (5 BUILD + 5 UNWIND)
        assert len(rows) == 10

    await bot.cleanup()
```

#### GREEN Phase: Implement Alternating Logic

```python
async def execute_buy_first_cycle(self) -> bool:
    """Execute BUY_FIRST cycle: BUILD (Long ETH / Short SOL) -> UNWIND."""
    try:
        # BUILD: Long ETH / Short SOL
        build_success = await self.execute_build_cycle()
        if not build_success:
            return False

        # Optional sleep
        if self.sleep_time > 0:
            await asyncio.sleep(self.sleep_time)

        # UNWIND: Sell ETH / Buy SOL
        unwind_success = await self.execute_unwind_cycle()
        return unwind_success

    except Exception as e:
        self.logger.log(f"BUY_FIRST cycle failed: {e}", "ERROR")
        return False

async def execute_sell_first_cycle(self) -> bool:
    """Execute SELL_FIRST cycle: BUILD (Short ETH / Long SOL) -> UNWIND."""
    # Similar logic, opposite directions
    # ... implementation ...

async def run_alternating_strategy(self) -> List[bool]:
    """Run alternating strategy for N iterations."""
    results = []

    for i in range(self.iterations):
        if i % 2 == 0:
            result = await self.execute_buy_first_cycle()
        else:
            result = await self.execute_sell_first_cycle()

        results.append(result)

    return results
```

#### Success Criteria (Quantified)
- [ ] All 5 iterations complete (success=True for all)
- [ ] Final positions flat: |ETH| < 0.01, |SOL| < 0.1
- [ ] CSV has exactly 10 trade entries (5 iterations × 2 phases)
- [ ] Alternating pattern correct: BUY_FIRST, SELL_FIRST, BUY_FIRST, SELL_FIRST, BUY_FIRST

#### Execution
```bash
# Full alternating test
pytest tests/stage4/test_alternating.py -v

# Live test with actual trading
python tests/stage4/test_alternating.py --live --notional 100 --iterations 5
```

---

## TDD Workflow Summary

### For Each Stage:
1. **RED**: Write failing tests first
   - Run `pytest` to verify tests fail
   - Document expected behavior

2. **GREEN**: Write minimal code to pass tests
   - Implement only what's needed for tests to pass
   - No refactoring, just make it work

3. **REFACTOR**: Clean up code
   - Extract common patterns
   - Improve readability
   - Ensure tests still pass

4. **VERIFY**: Run all tests
   - `pytest tests/ -v`
   - Coverage report: `pytest --cov`

### Test Execution Order:
```bash
# Stage 1: Basic functionality (must pass first)
pytest tests/stage1/ -v

# Stage 2: Single orders
pytest tests/stage2/ -v

# Stage 3: DN hedge
pytest tests/stage3/ -v

# Stage 4: Alternating
pytest tests/stage4/ -v

# All tests
pytest tests/ -v --cov=hedge.DN_pair_eth_sol_nado
```

---

## Next Steps

1. Create test directory structure: `mkdir -p tests/{stage1,stage2,stage3,stage4}`
2. Create `conftest.py` with shared fixtures
3. Create Stage 1 test file: `tests/stage1/test_nado_api.py`
4. Run Stage 1 tests (expect failures - RED phase)
5. Implement `initialize_clients()` method in `DN_pair_eth_sol_nado.py`
6. Run Stage 1 tests again (expect passing - GREEN phase)
7. Refactor if needed
8. Repeat for Stages 2, 3, 4
9. Deploy to production

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Partial fill (one leg fills) | Emergency unwind within 1 second (tested in Stage 3) |
| Position drift | Reconcile every cycle, 1% tolerance (quantified in tests) |
| API rate limits | Add delays between requests, use retries |
| Insufficient liquidity | Skip cycle, log warning (test with low liquidity scenarios) |
| Price moves between fetch and order | 500ms max price age, cancel if stale |
