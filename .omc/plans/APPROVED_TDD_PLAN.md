# Approved TDD Plan: DN Pair Trading Bot (ETH/SOL on Nado)

**Status**: ✅ APPROVED by Critic (Iteration 4/5)
**Date**: 2026-01-29
**File**: `/Users/botfarmer/2dex/.omc/plans/dn-pair-eth-sol-nado-tdd.md`

---

## Executive Summary

**TDD APPROACH:** 4 incremental stages with RED-GREEN-REFACTOR cycle

1. **Stage 1**: Nado 기본 기능 체크 (API 연결, 포지션 조회, $0 리스크) - 10 tests
2. **Stage 2**: ETH/SOL 개별 주문 연습 ($10 notional) - 6 tests
3. **Stage 3**: DN 헷징 테스트 (동시 주문, $100 notional, 1회) - 3 tests
4. **Stage 4**: Alternating 구현 (5회 반복, $100 notional) - 5 tests

**Total**: 24 tests across 4 stages

---

## Test Framework

- **pytest**: Test runner
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities

### Installation
```bash
pip install pytest pytest-asyncio pytest-mock
```

---

## Critical API Contract

**CRITICAL**: `place_open_order()` returns `OrderResult` with INITIAL price, NOT fill price.
To get actual fill price, must call `get_order_info()` after order fills.

| Method | Returns | Description |
|--------|---------|-------------|
| `fetch_bbo_prices(contract_id)` | `Tuple[Decimal, Decimal]` | (bid, ask) - uses last_price |
| `place_open_order(...)` | `OrderResult` | OrderResult.price = initial price |
| `get_order_info(order_id)` | `OrderInfo` | OrderInfo.price = actual fill price |

---

## Stage 1: Nado Basic Functionality ($0 risk)

### Test File: `tests/stage1/test_nado_api.py`

| Test # | Description | Success Criteria |
|--------|-------------|------------------|
| 1 | ETH client initialization | eth_client is not None, ticker == "ETH" |
| 2 | SOL client initialization | sol_client is not None, ticker == "SOL" |
| 3 | ETH contract attributes | contract_id == "2", tick_size > 0 |
| 4 | SOL contract attributes | contract_id == "4", tick_size > 0 |
| 5 | ETH position query | position == 0 |
| 6 | SOL position query | position == 0 |
| 7 | ETH BBO prices | bid > 0, ask > 0, ask >= bid |
| 8 | SOL BBO prices | bid > 0, ask > 0, ask >= bid |
| 9 | WebSocket connection | No exception raised |
| 10 | Environment variables | NADO_PRIVATE_KEY exists, length == 66 |

### Implementation Required
- `initialize_clients()` method in `DNPairBot`
- `cleanup()` method

### Execution Command
```bash
pytest tests/stage1/test_nado_api.py -v
```

---

## Stage 2: Individual Orders ($10 notional)

### Test File: `tests/stage2/test_single_orders.py`

| Test # | Description | Success Criteria |
|--------|-------------|------------------|
| 1 | Calculate ETH order size for $10 | Matches expected within ±0.0001 |
| 2 | Calculate SOL order size for $10 | Matches expected within ±0.0001 |
| 3 | Place ETH BUY order | success=True, price > 0 |
| 4 | Place SOL SELL order | success=True |
| 5 | CSV logging verification | CSV exists, contains data |
| 6 | Position reconciliation | Accurate within ±0.001 |

### Implementation Required
- `calculate_order_size(price, ticker)` method
- `place_single_order(ticker, direction, notional)` method
- `log_trade()` method
- CSV logging infrastructure

### Execution Command
```bash
pytest tests/stage2/test_single_orders.py -v
```

---

## Stage 3: DN Hedge Test ($100 notional, 1 cycle)

### Test File: `tests/stage3/test_dn_hedge.py`

| Test # | Description | Success Criteria |
|--------|-------------|------------------|
| 1 | Simultaneous order placement | Both succeed, elapsed < 1s |
| 2 | Partial fill handling | Emergency unwind called |
| 3 | Position delta check | \|ETH\| < 0.01, \|SOL\| < 0.1 |

### Implementation Required
- `place_simultaneous_orders(eth_direction, sol_direction)` method
- `handle_emergency_unwind()` method
- `execute_build_cycle()` method
- `execute_unwind_cycle()` method
- `execute_dn_cycle()` method

### Execution Command
```bash
pytest tests/stage3/test_dn_hedge.py -v
```

---

## Stage 4: Alternating (5 cycles, $100 notional)

### Test File: `tests/stage4/test_alternating.py`

| Test # | Description | Success Criteria |
|--------|-------------|------------------|
| 1 | Bot initialization | All params set correctly |
| 2 | Single BUY_FIRST cycle | Returns True |
| 3 | Single SELL_FIRST cycle | Returns True |
| 4 | Full 5 iterations | All 5 succeed, alternating pattern |
| 5 | CSV trade history | Exactly 10 entries |

### Implementation Required
- `execute_buy_first_cycle()` method
- `execute_sell_first_cycle()` method
- `run_alternating_strategy()` method

### Execution Command
```bash
pytest tests/stage4/test_alternating.py -v
```

---

## TDD Workflow

For each stage:
1. **RED**: Write failing tests first → Run `pytest` to verify failures
2. **GREEN**: Write minimal code to pass tests
3. **REFACTOR**: Clean up code
4. **VERIFY**: Run all tests → `pytest tests/ -v --cov`

---

## Success Criteria Summary

| Stage | Tests Pass | Coverage | Time Limit |
|-------|------------|----------|------------|
| Stage 1 | 10/10 | >80% | <30s |
| Stage 2 | 6/6 | >80% | <60s |
| Stage 3 | 3/3 | >80% | <60s |
| Stage 4 | 5/5 | >80% | <120s |

**Total**: 24 tests, all passing, 80%+ coverage
