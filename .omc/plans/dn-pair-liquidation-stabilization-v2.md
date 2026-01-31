# DN Pair Bot Liquidation Stabilization Plan V2

## Context

### Original Request
"DN Pair Bot 청산 로직 안정화 (Liquidation Stabilization)" - Stabilize the UNWIND (liquidation) logic for the DN Pair Bot to prevent position accumulation and manual intervention requirements.

### Background

**Critical Failure Scenario (Cycle 6 - 2026-01-31 01:27:46):**
- ETH buy IOC order: **FAILED to fill** (expired)
- SOL sell IOC order: **FILLED** (0.9 SOL @ $116.71)
- Emergency unwind triggered: "SOL filled but ETH failed, closing SOL position"
- **Bot stopped with SAFETY error**
- **User required manual intervention to close positions**

**Root Cause Analysis:**
1. **IOC orders have high failure rate** - No guaranteed fill mechanism
2. **Emergency unwind is NOT guaranteed** - Uses POST_ONLY orders which can fail
3. **No position verification** - Emergency unwind claims success but never verifies
4. **Missing MARKET order support** - NadoClient lacks `place_market_order()` method

### Critic Feedback Summary (V1 Plan REJECTED)

**7 Critical Gaps Identified:**

1. **BLOCKER - SDK OrderType.LIMIT Missing** 
   - Plan assumed `OrderType.LIMIT` exists
   - **Reality**: Nado SDK only has DEFAULT, FOK, IOC, POST_ONLY
   - **Impact**: Task 1.1 implementation is invalid

2. **CRITICAL - Rate Limit Handling Absent**
   - No 429 error prevention
   - API call bursts will trigger rate limits
   - Missing retry-after logic

3. **CRITICAL - WebSocket BBO Stability Unverified**
   - MARKET orders require BBO (bid/ask) data
   - No validation of WebSocket BBO data quality
   - Fallback to REST BBO not defined

4. **CRITICAL - Network Partition Testing Missing**
   - No failure scenario testing
   - Network timeout handling unverified
   - Partition recovery logic absent

5. **HIGH - Rollback Feature Flag Not Implemented**
   - No feature flag for MARKET fallback
   - Cannot quickly disable if issues arise
   - Deployment risk increased

6. **MEDIUM - Partial Fill Handling Incomplete**
   - IOC partial fill scenarios not addressed
   - Remaining quantity after partial fill logic missing
   - MARKET order sizing may be incorrect

7. **MEDIUM - API Downtime Scenarios Absent**
   - Exchange API down scenarios not tested
   - Graceful degradation not defined
   - Circuit breaker logic missing

### Effort Estimate Revision

**V1 Estimate:** 8-12 hours
**V2 Estimate:** 40-55 hours (4-5x increase due to 7 additional tasks)

**Breakdown:**
- Phase 1-3 (Original): 16 hours (revised from 8-12)
- Phase 4 (Testing): 12 hours (expanded)
- Phase 5 (New - Reliability): 8 hours
- Phase 6 (New - Testing): 10 hours
- Phase 7 (New - Operations): 4 hours
- Phase 8 (Documentation): 5 hours

---

## Work Objectives

### Core Objective
**Implement guaranteed position closure for DN Pair Bot UNWIND cycles with 100% position verification to prevent accumulation, addressing all 7 critical gaps from V1 review.**

### Deliverables

1. **SDK-Compatible Order Implementation** (Priority 0 - BLOCKER)
   - Use `OrderType.DEFAULT` instead of LIMIT
   - Aggressive pricing strategy using DEFAULT order type
   - Comprehensive error handling

2. **Rate Limit Resilience** (Priority 1 - CRITICAL)
   - Token bucket rate limiting
   - 429 error detection and backoff
   - Exponential backoff with jitter

3. **Stable BBO Data Source** (Priority 1 - CRITICAL)
   - WebSocket BBO validation
   - REST fallback on WebSocket failure
   - BBO quality checks

4. **Network Failure Resilience** (Priority 1 - CRITICAL)
   - Network partition testing framework
   - Timeout and retry strategies
   - Circuit breaker implementation

5. **Feature Flag Rollback** (Priority 2 - HIGH)
   - Environment variable controls
   - Runtime feature toggles
   - Safe rollback procedures

6. **Partial Fill Handling** (Priority 3 - MEDIUM)
   - IOC partial fill detection
   - Remaining quantity calculation
   - MARKET order sizing correction

7. **API Downtime Resilience** (Priority 3 - MEDIUM)
   - Exchange downtime detection
   - Graceful degradation modes
   - Circuit breaker patterns

8. **Comprehensive Testing** (Priority 1)
   - Unit tests for all new components
   - Integration tests for failure scenarios
   - Chaos engineering tests

### Definition of Done

- [ ] All acceptance criteria met with 100% test coverage
- [ ] No emergency unwind can succeed without position verification
- [ ] All UNWIND failures trigger MARKET order retry
- [ ] Position accumulation is impossible (prevented by code)
- [ ] Rate limiting prevents 429 errors under normal load
- [ ] WebSocket failures gracefully fallback to REST
- [ ] Network partitions handled with circuit breaker
- [ ] Feature flags enable instant rollback
- [ ] Partial fills correctly calculated for MARKET sizing
- [ ] API downtime scenarios tested and handled
- [ ] All existing tests pass
- [ ] Code review completed
- [ ] Documentation updated

---

## Must Have / Must NOT Have

### Must Have (Guardrails)

**Critical Safety Requirements:**
1. **Every position closure MUST be verified via API** - No log-based success claims
2. **Emergency unwind MUST use MARKET orders** - No POST_ONLY for emergency closure
3. **UNWIND failure MUST trigger MARKET retry** - No silent failures
4. **Position check MUST poll until closed OR timeout** - No single-check assumptions
5. **Startup MUST verify residual positions** - Prevent accumulation across restarts
6. **Rate limiting MUST prevent 429 errors** - Token bucket or leaky bucket
7. **WebSocket BBO MUST have validation** - Fallback to REST if invalid
8. **Network failures MUST trigger circuit breaker** - Prevent cascading failures
9. **Feature flags MUST allow instant rollback** - Environment variable controls
10. **Partial fills MUST adjust MARKET size** - Correct quantity calculation

**Code Quality Requirements:**
1. All new methods must have type hints
2. All new code must have docstrings
3. All failure modes must have tests
4. All critical operations must have detailed logging
5. All rate limits must be configurable
6. All circuit breakers must have monitoring

### Must NOT Have

**Prohibited Actions:**
1. **MUST NOT use OrderType.LIMIT** - Does not exist in Nado SDK
2. **MUST NOT use IOC for emergency unwind** - IOC can fail, use MARKET only
3. **MUST NOT assume order success = position closed** - Always verify via API
4. **MUST NOT silently catch exceptions in unwind** - All errors must be logged and surfaced
5. **MUST NOT use POST_ONLY for guaranteed closure** - POST_ONLY can expire unfilled
6. **MUST NOT allow BUILD with residual positions** - Check BEFORE every BUILD
7. **MUST NOT call APIs without rate limiting** - Prevent 429 errors
8. **MUST NOT trust WebSocket BBO without validation** - Verify or fallback
9. **MUST NOT retry indefinitely on network failures** - Use circuit breaker
10. **MUST NOT deploy without feature flags** - Enable instant rollback

**Anti-Patterns to Avoid:**
1. Using `try/except pass` in unwind logic
2. Returning `True` from unwind without position verification
3. Logging "position closing" without verification
4. Assuming `OrderResult.success == True` means position closed
5. Ignoring 429 errors and continuing to retry
6. Using stale WebSocket BBO data without validation
7. Allowing unlimited retries on network failures
8. Hard-coding feature toggle values

---

## Task Flow and Dependencies

```
Phase 0: SDK Verification & Foundation (BLOCKER - 2 hours)
├── Task 0.1: Verify OrderType enum in Nado SDK
│   └── Blocks: All order implementation tasks
└── Task 0.2: Design SDK-compatible MARKET order strategy
    └── Blocks: Phase 1 implementation

Phase 1: Critical Safety Infrastructure (6 hours)
├── Task 1.1: Implement place_market_order() using OrderType.DEFAULT
│   ├── Depends on: Task 0.2
│   └── Blocks: All emergency unwind improvements
├── Task 1.2: Add verify_position_closed() utility
│   ├── Depends on: Task 0.1
│   └── Blocks: Position verification in unwind
└── Task 1.3: Implement rate limiting with token bucket
    ├── Depends on: Task 0.1
│   └── Blocks: All API calling tasks

Phase 2: BBO Data Stability (4 hours)
├── Task 2.1: Validate WebSocket BBO data quality
│   ├── Depends on: Task 1.1
│   └── Blocks: MARKET order pricing
├── Task 2.2: Implement REST BBO fallback
│   ├── Depends on: Task 2.1
│   └── Blocks: MARKET order reliability
└── Task 2.3: Add BBO freshness checks
    └── Depends on: Task 2.1

Phase 3: Network Resilience (6 hours)
├── Task 3.1: Implement circuit breaker for API calls
│   ├── Depends on: Task 1.3
│   └── Blocks: Production readiness
├── Task 3.2: Add timeout and retry with exponential backoff
│   ├── Depends on: Task 3.1
│   └── Blocks: Network failure handling
└── Task 3.3: Create network partition test framework
    └── Depends on: Task 3.2

Phase 4: Emergency Unwind Stabilization (4 hours)
├── Task 4.1: Refactor emergency_unwind_eth() with MARKET + verification
│   ├── Depends on: Task 1.1, Task 1.2, Task 2.2
│   └── Blocks: Task 4.3
├── Task 4.2: Refactor emergency_unwind_sol() with MARKET + verification
│   ├── Depends on: Task 1.1, Task 1.2, Task 2.2
│   └── Blocks: Task 4.3
└── Task 4.3: Update handle_emergency_unwind() with result verification
    └── Depends on: Task 4.1, Task 4.2

Phase 5: Feature Flags & Rollback (3 hours)
├── Task 5.1: Implement environment variable feature flags
│   ├── Depends on: Task 0.1
│   └── Blocks: Production deployment
├── Task 5.2: Add runtime feature toggle checks
│   ├── Depends on: Task 5.1
│   └── Blocks: Safe rollback
└── Task 5.3: Document rollback procedures
    └── Depends on: Task 5.2

Phase 6: Partial Fill Handling (4 hours)
├── Task 6.1: Detect IOC partial fills in OrderResult
│   ├── Depends on: Task 4.3
│   └── Blocks: MARKET sizing logic
├── Task 6.2: Calculate remaining quantity after partial fill
│   ├── Depends on: Task 6.1
│   └── Blocks: Correct MARKET orders
└── Task 6.3: Update MARKET order sizing with partial fill adjustment
    └── Depends on: Task 6.2

Phase 7: Unwind Cycle Robustness (5 hours)
├── Task 7.1: Implement IOC → MARKET fallback in execute_unwind_cycle()
│   ├── Depends on: Task 4.3, Task 6.3
│   └── Blocks: Task 7.3
├── Task 7.2: Increase retry count (3→5) and timeout (2s→5s)
│   ├── Depends on: Task 1.2
│   └── Blocks: Task 7.3
└── Task 7.3: Add graceful retry with MARKET before halt
    └── Depends on: Task 7.1, Task 7.2

Phase 8: API Downtime Resilience (4 hours)
├── Task 8.1: Implement exchange downtime detection
│   ├── Depends on: Task 3.1
│   └── Blocks: Graceful degradation
├── Task 8.2: Add graceful degradation modes
│   ├── Depends on: Task 8.1
│   └── Blocks: Production readiness
└── Task 8.3: Create API downtime test scenarios
    └── Depends on: Task 8.2

Phase 9: Testing & Validation (12 hours)
├── Task 9.1: Unit tests for place_market_order()
│   ├── Depends on: Task 1.1
│   └── Parallel with: Task 9.2
├── Task 9.2: Unit tests for rate limiting
│   ├── Depends on: Task 1.3
│   └── Parallel with: Task 9.1
├── Task 9.3: Unit tests for BBO validation
│   ├── Depends on: Task 2.3
│   └── Parallel with: Task 9.4
├── Task 9.4: Unit tests for circuit breaker
│   ├── Depends on: Task 3.1
│   └── Parallel with: Task 9.3
├── Task 9.5: Integration tests for emergency unwind
│   ├── Depends on: Task 4.3
│   └── Parallel with: Task 9.6
├── Task 9.6: Integration tests for partial fill handling
│   ├── Depends on: Task 6.3
│   └── Parallel with: Task 9.5
├── Task 9.7: Chaos engineering tests for network failures
│   ├── Depends on: Task 3.3
│   └── Parallel with: Task 9.8
├── Task 9.8: End-to-end tests for failure scenarios
│   ├── Depends on: Task 7.3
│   └── Parallel with: Task 9.7
└── Task 9.9: Run existing test suite and fix failures
    └── Depends on: All previous tasks

Phase 10: Documentation & Handoff (5 hours)
├── Task 10.1: Update code documentation
├── Task 10.2: Create runbook for emergency procedures
├── Task 10.3: Document feature flags and rollback procedures
└── Task 10.4: Final review and sign-off
```

---

## Detailed TODOs with Acceptance Criteria

### Phase 0: SDK Verification & Foundation

#### Task 0.1: Verify OrderType enum in Nado SDK
**File:** Verification script

**Verification Steps:**
1. Run `python3 -c "from nado_protocol.utils.order import OrderType; print([o for o in dir(OrderType) if not o.startswith('_')])"`
2. Confirm available types: DEFAULT, FOK, IOC, POST_ONLY
3. **CONFIRMED: OrderType.LIMIT does NOT exist**

**Acceptance Criteria:**
- [ ] Verified OrderType enum values
- [ ] Documented that LIMIT does not exist
- [ ] Identified DEFAULT as closest equivalent to LIMIT
- [ ] Updated all plan references to use DEFAULT instead of LIMIT
- [ ] Documented DEFAULT behavior in Nado SDK

**Testing:**
- Verification script output saved to `.omc/research/ordertype-verification.txt`

---

#### Task 0.2: Design SDK-compatible MARKET order strategy
**File:** Design document

**Strategy Design:**
1. Use `OrderType.DEFAULT` with aggressive pricing
2. Buy orders: price = ask + 0.1% (deeply cross spread)
3. Sell orders: price = bid - 0.1% (deeply cross spread)
4. Add time-in-force: Immediate-Or-Cancel (IOC) behavior via price
5. Fallback: If DEFAULT not filled, use FOK for guaranteed fill

**Acceptance Criteria:**
- [ ] Design document created with pricing strategy
- [ ] DEFAULT order behavior documented
- [ ] Aggressive pricing formula specified
- [ ] Fallback to FOK documented
- [ ] Slippage tolerance defined (default 50 bps)
- [ ] Edge cases identified (low liquidity, wide spreads)

---

### Phase 1: Critical Safety Infrastructure

#### Task 1.1: Implement `place_market_order()` using OrderType.DEFAULT
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
async def place_market_order(
    self,
    contract_id: str,
    quantity: Decimal,
    side: str,
    max_slippage_bps: int = 50  # Allow 0.5% slippage for guaranteed fill
) -> OrderResult:
    """
    Place a MARKET order with aggressive pricing for guaranteed execution.

    Uses OrderType.DEFAULT with aggressive pricing (deeply cross spread) instead of
    LIMIT (which doesn't exist in Nado SDK) to ensure execution.

    Args:
        contract_id: Contract ID to trade
        quantity: Order quantity (positive for both buy/sell)
        side: 'buy' or 'sell'
        max_slippage_bps: Maximum acceptable slippage in basis points

    Returns:
        OrderResult with execution details
    """
```

**Acceptance Criteria:**
- [ ] Method places DEFAULT order at aggressive price
- [ ] Buy price = ask * (1 + max_slippage_bps/10000) - crosses spread
- [ ] Sell price = bid * (1 - max_slippage_bps/10000) - crosses spread
- [ ] Method uses `OrderType.DEFAULT` (NOT LIMIT - doesn't exist)
- [ ] Method includes `max_slippage_bps` parameter (default 50 bps = 0.5%)
- [ ] Method returns `OrderResult` with all fields populated
- [ ] Method has 5 retries with exponential backoff (0.1s, 0.2s, 0.4s, 0.8s, 1.6s)
- [ ] Method logs pricing details: "MARKET {side} {qty} @ {price} (aggressive)"
- [ ] Error handling: Returns `OrderResult(success=False)` if all retries fail
- [ ] Type hints on all parameters and return value
- [ ] Docstring with usage examples

**Testing:**
- Unit test: Successful market buy order fills
- Unit test: Successful market sell order fills
- Unit test: Retry logic on network errors
- Unit test: Error handling when exchange unavailable
- Unit test: Aggressive pricing crosses spread correctly

---

#### Task 1.2: Add `verify_position_closed()` utility to DNPairBot
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
async def verify_position_closed(
    self,
    ticker: str,
    timeout_seconds: int = 30,
    poll_interval: float = 0.5
) -> Tuple[bool, Decimal, int]:
    """
    Verify position is closed by polling until timeout.

    Args:
        ticker: 'ETH' or 'SOL'
        timeout_seconds: Maximum seconds to poll (default 30)
        poll_interval: Seconds between polls (default 0.5)

    Returns:
        Tuple of (is_closed, final_position, poll_count)
    """
```

**Acceptance Criteria:**
- [ ] Method polls position every `poll_interval` seconds
- [ ] Method stops when `abs(position) < 0.001` (POSITION_TOLERANCE)
- [ ] Method stops after `timeout_seconds` (prevents infinite loops)
- [ ] Returns `(True, final_pos, poll_count)` when position closed
- [ ] Returns `(False, final_pos, poll_count)` when timeout
- [ ] Logs every poll: "[VERIFY] {ticker} position: {pos} (attempt {n})"
- [ ] Uses correct client: `self.eth_client` or `self.sol_client`
- [ ] Type hints on all parameters and return value
- [ ] Docstring with usage examples

**Testing:**
- Unit test: Position closes immediately (poll_count = 1)
- Unit test: Position closes after 3 seconds (poll_count = 6)
- Unit test: Position never closes (timeout after 30s)
- Unit test: Network errors during polling

---

#### Task 1.3: Implement rate limiting with token bucket
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, rate: float, burst: int):
        """
        Initialize rate limiter.
        
        Args:
            rate: Tokens per second (e.g., 10 = 10 requests/second)
            burst: Maximum burst size (bucket capacity)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if rate limited
        """
```

**Acceptance Criteria:**
- [ ] Token bucket algorithm implemented
- [ ] Configurable rate (requests per second)
- [ ] Configurable burst size
- [ ] Thread-safe with asyncio.Lock
- [ ] Returns False if rate limited (caller should retry)
- [ ] Automatic token refill at configured rate
- [ ] Integrated into all NadoClient API calls
- [ ] Logs rate limit events: "[RATE_LIMIT] Throttling API call"
- [ ] Environment variable configuration: NADO_RATE_LIMIT, NADO_BURST_SIZE
- [ ] Default rate: 10 requests/second, burst: 20

**Testing:**
- Unit test: Token bucket refill rate
- Unit test: Burst allowance
- Unit test: Rate limiting enforcement
- Unit test: Concurrent request handling
- Integration test: Prevents 429 errors under load

---

### Phase 2: BBO Data Stability

#### Task 2.1: Validate WebSocket BBO data quality
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
def validate_bbo(self, bid: Decimal, ask: Decimal, timestamp: float) -> bool:
    """
    Validate BBO data quality.
    
    Args:
        bid: Best bid price
        ask: Best ask price
        timestamp: BBO timestamp
        
    Returns:
        True if BBO is valid, False otherwise
    """
    # Check 1: Bid and ask must be positive
    # Check 2: Ask must be > bid (positive spread)
    # Check 3: Spread must be reasonable (< 10% of mid price)
    # Check 4: Timestamp must be recent (< 5 seconds old)
    # Check 5: Prices must be within expected range
```

**Acceptance Criteria:**
- [ ] Validates bid > 0 and ask > 0
- [ ] Validates ask > bid (positive spread)
- [ ] Validates spread < 10% of mid price
- [ ] Validates timestamp < 5 seconds old
- [ ] Validates prices within 50% of last known price
- [ ] Returns False if any validation fails
- [ ] Logs validation failures: "[BBO] Invalid BBO: {reason}"
- [ ] Called before using BBO for MARKET orders
- [ ] Fallback to REST if validation fails

**Testing:**
- Unit test: Valid BBO passes
- Unit test: Invalid spread (ask <= bid) fails
- Unit test: Stale timestamp fails
- Unit test: Price anomaly detection
- Integration test: Fallback to REST on invalid BBO

---

#### Task 2.2: Implement REST BBO fallback
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
async def get_bbo_with_fallback(self) -> Tuple[Decimal, Decimal]:
    """
    Get BBO with WebSocket → REST fallback.
    
    Returns:
        Tuple of (bid, ask)
    
    Raises:
        Exception: If both WebSocket and REST fail
    """
    # Try WebSocket BBO first (fast, real-time)
    # If WebSocket unavailable or invalid, fallback to REST
    # REST is slower but more reliable
```

**Acceptance Criteria:**
- [ ] First tries WebSocket BBO if available
- [ ] Validates WebSocket BBO quality
- [ ] Falls back to REST if WebSocket fails validation
- [ ] Logs fallback: "[BBO] Fallback to REST: {reason}"
- [ ] REST BBO fetched via orderbook API
- [ ] Returns valid (bid, ask) or raises Exception
- [ ] Caches REST BBO for 1 second to reduce API calls
- [ ] Respects rate limiting on REST calls

**Testing:**
- Unit test: WebSocket BBO valid → no fallback
- Unit test: WebSocket BBO invalid → REST fallback
- Unit test: WebSocket unavailable → REST fallback
- Unit test: REST fallback succeeds
- Integration test: End-to-end BBO retrieval

---

#### Task 2.3: Add BBO freshness checks
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
def is_bbo_fresh(self, timestamp: float, max_age_seconds: float = 2.0) -> bool:
    """
    Check if BBO data is fresh enough.
    
    Args:
        timestamp: BBO timestamp
        max_age_seconds: Maximum age in seconds
        
    Returns:
        True if BBO is fresh, False otherwise
    """
    return (time.time() - timestamp) < max_age_seconds
```

**Acceptance Criteria:**
- [ ] Checks timestamp age against max_age_seconds
- [ ] Default max_age_seconds: 2.0
- [ ] Returns True if age < max_age_seconds
- [ ] Returns False if age >= max_age_seconds
- [ ] Called before using BBO for MARKET orders
- [ ] Logs stale BBO: "[BBO] BBO stale: {age}s old"
- [ ] Configurable via environment variable: NADO_BBO_MAX_AGE

**Testing:**
- Unit test: Fresh BBO passes
- Unit test: Stale BBO fails
- Unit test: Configurable max_age
- Integration test: Stale BBO triggers REST fallback

---

### Phase 3: Network Resilience

#### Task 3.1: Implement circuit breaker for API calls
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
class CircuitBreaker:
    """Circuit breaker for API calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Exception = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures before opening circuit
            timeout: Seconds to wait before trying again
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failures = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
```

**Acceptance Criteria:**
- [ ] Three states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
- [ ] Tracks consecutive failures
- [ ] Opens circuit after failure_threshold failures
- [ ] Stays open for timeout seconds
- [ ] Enters HALF_OPEN after timeout
- [ ] Closes again on success
- [ ] Opens again on failure in HALF_OPEN
- [ ] Logs state transitions: "[CIRCUIT] {state}: {reason}"
- [ ] Raises CircuitBreakerOpenException when OPEN
- [ ] Configurable thresholds via environment variables

**Testing:**
- Unit test: Circuit opens after threshold
- Unit test: Circuit closes after successful call
- Unit test: Half-open state transition
- Unit test: Exception when circuit open
- Integration test: Prevents cascading failures

---

#### Task 3.2: Add timeout and retry with exponential backoff
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
async def call_with_timeout_and_retry(
    self,
    func: Callable,
    timeout: float = 10.0,
    max_retries: int = 3,
    base_delay: float = 0.1
) -> Any:
    """
    Call function with timeout and exponential backoff retry.
    
    Args:
        func: Async function to call
        timeout: Timeout for each attempt in seconds
        max_retries: Maximum number of retries
        base_delay: Base delay for exponential backoff
        
    Returns:
        Function result
        
    Raises:
        Exception: If all retries fail
    """
```

**Acceptance Criteria:**
- [ ] Wraps async function with timeout
- [ ] Retries on timeout exceptions
- [ ] Retries on network errors
- [ ] Exponential backoff: base_delay * 2^retry_count
- [ ] Adds jitter: backoff * (0.5 + random())
- [ ] Maximum retries: 3
- [ ] Logs retries: "[RETRY] Attempt {n}/{max}: {error}"
- [ ] Raises last exception if all retries fail
- [ ] Respects circuit breaker state

**Testing:**
- Unit test: Successful call on first attempt
- Unit test: Retry on timeout
- Unit test: Exponential backoff timing
- Unit test: Jitter in backoff
- Unit test: Raises after max retries

---

#### Task 3.3: Create network partition test framework
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_network_partitions.py` (new file)

**Implementation:**
```python
class NetworkPartitionSimulator:
    """Simulate network partitions for testing."""
    
    async def simulate_timeout(self, duration: float):
        """Simulate network timeout."""
        
    async def simulate_connection_refused(self):
        """Simulate connection refused."""
        
    async def simulate_dns_failure(self):
        """Simulate DNS resolution failure."""
        
    async def simulate_packet_loss(self, loss_rate: float):
        """Simulate packet loss."""
```

**Acceptance Criteria:**
- [ ] Can simulate network timeouts
- [ ] Can simulate connection refused
- [ ] Can simulate DNS failures
- [ ] Can simulate packet loss
- [ ] Integrates with test framework
- [ ] Tests circuit breaker behavior
- [ ] Tests retry logic behavior
- [ ] Tests graceful degradation
- [ ] All tests pass with simulated failures

**Testing:**
- Unit test: Timeout simulation
- Unit test: Connection refused simulation
- Unit test: DNS failure simulation
- Integration test: Circuit breaker opens on partition
- Integration test: Retry logic handles partition
- Integration test: Graceful degradation on partition

---

### Phase 4: Emergency Unwind Stabilization

#### Task 4.1: Refactor `emergency_unwind_eth()` with MARKET + verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 382-396

**Current Implementation (PROBLEMATIC):**
```python
async def emergency_unwind_eth(self):
    if self.eth_client:
        try:
            current_pos = await self.eth_client.get_account_positions()
            if current_pos > 0:
                await self.eth_client.place_close_order(
                    self.eth_client.config.contract_id,
                    current_pos,
                    Decimal("0"),  # Assumes market order, but uses POST_ONLY
                    "sell"
                )
        except Exception:
            pass  # Silent failure - CRITICAL BUG
```

**New Implementation:**
```python
async def emergency_unwind_eth(self) -> bool:
    """
    Emergency unwind ETH position using MARKET order with verification.

    Returns:
        True if position closed successfully, False otherwise
    """
    if not self.eth_client:
        self.logger.error("[EMERGENCY] ETH client not available")
        return False

    try:
        # Get current position
        current_pos = await self.eth_client.get_account_positions()
        self.logger.info(f"[EMERGENCY] ETH position BEFORE close: {current_pos}")

        if abs(current_pos) < Decimal("0.001"):
            self.logger.info("[EMERGENCY] ETH position already closed")
            return True

        # Close with MARKET order (guaranteed execution)
        close_qty = abs(current_pos)
        side = "sell" if current_pos > 0 else "buy"

        result = await self.eth_client.place_market_order(
            self.eth_client.config.contract_id,
            close_qty,
            side
        )

        if not result.success:
            self.logger.error(f"[EMERGENCY] ETH MARKET order failed: {result.error_message}")
            return False

        # Verify position closed
        is_closed, final_pos, poll_count = await self.verify_position_closed("ETH")

        self.logger.info(
            f"[EMERGENCY] ETH position AFTER close: {final_pos}, "
            f"verified={is_closed}, polls={poll_count}"
        )

        if not is_closed:
            self.logger.error(
                f"[EMERGENCY] ETH position NOT CLOSED after MARKET order: {final_pos}"
            )
            return False

        return True

    except Exception as e:
        self.logger.error(f"[EMERGENCY] ETH unwind failed with exception: {e}")
        return False
```

**Acceptance Criteria:**
- [ ] Method returns `bool` (success/failure) - **CRITICAL CHANGE**
- [ ] Uses `place_market_order()` instead of `place_close_order()`
- [ ] Logs position BEFORE closing
- [ ] Logs position AFTER closing with verification result
- [ ] Calls `verify_position_closed("ETH")` with 30s timeout
- [ ] Returns `False` if position not closed after MARKET order
- [ ] Returns `False` on any exception (no silent failures)
- [ ] Returns `True` only if position verified closed
- [ ] Side detection: "sell" if current_pos > 0, "buy" if current_pos < 0
- [ ] Type hints on return value
- [ ] Docstring explaining verification logic

**Testing:**
- Unit test: Successful ETH close with MARKET order
- Unit test: Position verification fails (returns False)
- Unit test: MARKET order fails (returns False)
- Unit test: Network exception during close (returns False, no crash)

---

#### Task 4.2: Refactor `emergency_unwind_sol()` with MARKET + verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 398-412

**Current Implementation (PROBLEMATIC):** Same pattern as ETH - silent failures

**New Implementation:** Identical structure to Task 4.1 but for SOL

**Acceptance Criteria:**
- [ ] Method returns `bool` (success/failure) - **CRITICAL CHANGE**
- [ ] Uses `place_market_order()` instead of `place_close_order()`
- [ ] Logs position BEFORE closing
- [ ] Logs position AFTER closing with verification result
- [ ] Calls `verify_position_closed("SOL")` with 30s timeout
- [ ] Returns `False` if position not closed after MARKET order
- [ ] Returns `False` on any exception (no silent failures)
- [ ] Returns `True` only if position verified closed
- [ ] Side detection: "sell" if current_pos > 0, "buy" if current_pos < 0
- [ ] Type hints on return value
- [ ] Docstring explaining verification logic

**Testing:**
- Unit test: Successful SOL close with MARKET order
- Unit test: Position verification fails (returns False)
- Unit test: MARKET order fails (returns False)
- Unit test: Network exception during close (returns False, no crash)

---

#### Task 4.3: Update `handle_emergency_unwind()` with result verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 357-380

**Current Implementation:**
```python
async def handle_emergency_unwind(self, eth_result, sol_result):
    # Check if one succeeded and other failed
    if eth_filled and not sol_filled:
        await self.emergency_unwind_sol()  # No return value check
    elif sol_filled and not eth_filled:
        await self.emergency_unwind_eth()  # No return value check
```

**New Implementation:**
```python
async def handle_emergency_unwind(self, eth_result: OrderResult, sol_result: OrderResult) -> bool:
    """
    Handle emergency unwind when one leg fails.

    Returns:
        True if emergency unwind succeeded, False otherwise
    """
    # Check fill status
    eth_filled = (isinstance(eth_result, OrderResult) and
                  eth_result.success and
                  eth_result.status == 'FILLED')
    sol_filled = (isinstance(sol_result, OrderResult) and
                  sol_result.success and
                  sol_result.status == 'FILLED')

    # Scenario 1: ETH filled, SOL failed → Close ETH
    if eth_filled and not sol_filled:
        self.logger.warning("[UNWIND] ETH filled but SOL failed, closing ETH position")
        success = await self.emergency_unwind_eth()
        if not success:
            self.logger.error("[UNWIND] Emergency ETH close FAILED - position may be open")
            return False
        self.logger.info("[UNWIND] Emergency ETH close succeeded")
        return False  # Unwind failed overall (SOL not filled)

    # Scenario 2: SOL filled, ETH failed → Close SOL
    elif sol_filled and not eth_filled:
        self.logger.warning("[UNWIND] SOL filled but ETH failed, closing SOL position")
        success = await self.emergency_unwind_sol()
        if not success:
            self.logger.error("[UNWIND] Emergency SOL close FAILED - position may be open")
            return False
        self.logger.info("[UNWIND] Emergency SOL close succeeded")
        return False  # Unwind failed overall (ETH not filled)

    # Scenario 3: Both failed or both filled → No emergency unwind needed
    return True
```

**Acceptance Criteria:**
- [ ] Method returns `bool` indicating emergency unwind success
- [ ] Checks return value from `emergency_unwind_eth()` - **CRITICAL**
- [ ] Checks return value from `emergency_unwind_sol()` - **CRITICAL**
- [ ] Logs "[UNWIND] Emergency ETH/SOL close FAILED" if verification fails
- [ ] Returns `False` if emergency unwind fails
- [ ] Returns `False` if one leg filled (unwind incomplete)
- [ ] Returns `True` only if both filled or both failed
- [ ] Type hints on parameters and return value
- [ ] Docstring explaining scenarios

**Testing:**
- Unit test: ETH filled, SOL failed → ETH close succeeds
- Unit test: ETH filled, SOL failed → ETH close fails (returns False)
- Unit test: SOL filled, ETH failed → SOL close succeeds
- Unit test: SOL filled, ETH failed → SOL close fails (returns False)
- Unit test: Both filled → No emergency unwind
- Unit test: Both failed → No emergency unwind

---

### Phase 5: Feature Flags & Rollback

#### Task 5.1: Implement environment variable feature flags
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
class FeatureFlags:
    """Feature flags for DN Pair Bot."""
    
    # MARKET fallback features
    USE_MARKET_FALLBACK = os.getenv('DN_USE_MARKET_FALLBACK', 'true').lower() == 'true'
    MARKET_FALLBACK_MAX_SLIPPAGE_BPS = int(os.getenv('DN_MARKET_MAX_SLIPPAGE_BPS', '50'))
    
    # Rate limiting features
    ENABLE_RATE_LIMITING = os.getenv('DN_ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    RATE_LIMIT_PER_SECOND = float(os.getenv('DN_RATE_LIMIT_PER_SECOND', '10'))
    BURST_SIZE = int(os.getenv('DN_BURST_SIZE', '20'))
    
    # Circuit breaker features
    ENABLE_CIRCUIT_BREAKER = os.getenv('DN_ENABLE_CIRCUIT_BREAKER', 'true').lower() == 'true'
    CIRCUIT_FAILURE_THRESHOLD = int(os.getenv('DN_CIRCUIT_FAILURE_THRESHOLD', '5'))
    CIRCUIT_TIMEOUT_SECONDS = float(os.getenv('DN_CIRCUIT_TIMEOUT_SECONDS', '60'))
    
    # BBO features
    USE_WEBSOCKET_BBO = os.getenv('DN_USE_WEBSOCKET_BBO', 'true').lower() == 'true'
    BBO_MAX_AGE_SECONDS = float(os.getenv('DN_BBO_MAX_AGE_SECONDS', '2'))
    
    @classmethod
    def log_flags(cls):
        """Log all feature flag values."""
        logging.info(f"[FEATURE] USE_MARKET_FALLBACK={cls.USE_MARKET_FALLBACK}")
        logging.info(f"[FEATURE] ENABLE_RATE_LIMITING={cls.ENABLE_RATE_LIMITING}")
        logging.info(f"[FEATURE] ENABLE_CIRCUIT_BREAKER={cls.ENABLE_CIRCUIT_BREAKER}")
        logging.info(f"[FEATURE] USE_WEBSOCKET_BBO={cls.USE_WEBSOCKET_BBO}")
```

**Acceptance Criteria:**
- [ ] FeatureFlags class with all major features
- [ ] Environment variable for each feature
- [ ] Default values for all flags (safe defaults)
- [ ] Type conversion (bool, int, float)
- [ ] log_flags() method to display all flags
- [ ] Called at bot startup
- [ ] Used in conditional logic throughout code
- [ ] Documented in operations manual

**Testing:**
- Unit test: Default values loaded correctly
- Unit test: Environment variables override defaults
- Unit test: Type conversion works correctly
- Unit test: log_flags() outputs all flags
- Integration test: Flags control behavior

---

#### Task 5.2: Add runtime feature toggle checks
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
# In execute_unwind_cycle()
if not FeatureFlags.USE_MARKET_FALLBACK:
    self.logger.warning("[FEATURE] MARKET fallback disabled, using IOC only")
    # Original IOC-only logic
else:
    # IOC → MARKET fallback logic
    
# In place_market_order()
if FeatureFlags.MARKET_FALLBACK_MAX_SLIPPAGE_BPS < max_slippage_bps:
    self.logger.warning(f"[FEATURE] Slippage {max_slippage_bps} exceeds limit {FeatureFlags.MARKET_FALLBACK_MAX_SLIPPAGE_BPS}")
    return OrderResult(success=False, error_message="Slippage exceeds feature flag limit")
```

**Acceptance Criteria:**
- [ ] All MARKET fallback logic gated by USE_MARKET_FALLBACK
- [ ] Rate limiting gated by ENABLE_RATE_LIMITING
- [ ] Circuit breaker gated by ENABLE_CIRCUIT_BREAKER
- [ ] WebSocket BBO gated by USE_WEBSOCKET_BBO
- [ ] Logs when feature is disabled
- [ ] Graceful degradation when features disabled
- [ ] No breaking changes when flags toggled

**Testing:**
- Unit test: MARKET fallback disabled → IOC only
- Unit test: Rate limiting disabled → no throttling
- Unit test: Circuit breaker disabled → no circuit breaking
- Unit test: WebSocket BBO disabled → REST only
- Integration test: All flags can be toggled

---

#### Task 5.3: Document rollback procedures
**File:** `/Users/botfarmer/2dex/docs/dn-pair-rollback-procedures.md` (new file)

**Content:**
```markdown
# DN Pair Bot Rollback Procedures

## Feature Flag Rollback

### Immediate Rollback (Disables MARKET fallback)
```bash
export DN_USE_MARKET_FALLBACK=false
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

### Partial Rollback (Disables specific features)
```bash
# Disable rate limiting (use with caution)
export DN_ENABLE_RATE_LIMITING=false

# Disable circuit breaker (use with caution)
export DN_ENABLE_CIRCUIT_BREAKER=false

# Disable WebSocket BBO (force REST)
export DN_USE_WEBSOCKET_BBO=false
```

### Full Rollback (Revert to V1 behavior)
```bash
export DN_USE_MARKET_FALLBACK=false
export DN_ENABLE_RATE_LIMITING=false
export DN_ENABLE_CIRCUIT_BREAKER=false
export DN_USE_WEBSOCKET_BBO=true
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

## Code Rollback

### Git Revert (Last resort)
```bash
cd /Users/botfarmer/2dex
git log --oneline -10  # Find commit before V2 changes
git revert <commit-hash>
git push
```

### Feature Branch Rollback
```bash
git checkout main
git branch -D dn-pair-v2
git checkout -b dn-pair-v1-rollback
git checkout <v1-commit-hash>
```

## Monitoring After Rollback

### Check Logs
- Look for "[FEATURE]" tags to confirm flags
- Verify no "[MARKET]" orders if fallback disabled
- Verify position verification still active

### Check Positions
- Verify no accumulation after rollback
- Monitor emergency unwind frequency
- Check for position closure failures

## Emergency Contacts
- Developer: [Your contact]
- On-call: [On-call procedure]
```

**Acceptance Criteria:**
- [ ] Document created with rollback procedures
- [ ] Feature flag rollback documented
- [ ] Code rollback documented
- [ ] Monitoring procedures documented
- [ ] Emergency contacts included
- [ ] Step-by-step instructions clear
- [ ] Examples provided for all scenarios

---

### Phase 6: Partial Fill Handling

#### Task 6.1: Detect IOC partial fills in OrderResult
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
def detect_partial_fill(self, result: OrderResult, expected_qty: Decimal) -> bool:
    """
    Detect if order was partially filled.
    
    Args:
        result: OrderResult from exchange
        expected_qty: Expected order quantity
        
    Returns:
        True if partial fill detected, False otherwise
    """
    if not result.success:
        return False
    
    filled_qty = result.filled_quantity if hasattr(result, 'filled_quantity') else Decimal('0')
    return filled_qty > 0 and filled_qty < expected_qty
```

**Acceptance Criteria:**
- [ ] Checks OrderResult for filled_quantity field
- [ ] Compares filled_qty vs expected_qty
- [ ] Returns True if 0 < filled_qty < expected_qty
- [ ] Returns False if fully filled or not filled
- [ ] Logs partial fills: "[PARTIAL] {ticker} filled {filled}/{expected}"
- [ ] Used in execute_unwind_cycle()
- [ ] Type hints on all parameters

**Testing:**
- Unit test: Full fill → returns False
- Unit test: No fill → returns False
- Unit test: Partial fill → returns True
- Unit test: Missing filled_quantity → returns False

---

#### Task 6.2: Calculate remaining quantity after partial fill
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
def calculate_remaining_quantity(self, result: OrderResult, expected_qty: Decimal) -> Decimal:
    """
    Calculate remaining quantity after partial fill.
    
    Args:
        result: OrderResult from exchange
        expected_qty: Expected order quantity
        
    Returns:
        Remaining quantity to close
    """
    if not result.success:
        return expected_qty
    
    filled_qty = result.filled_quantity if hasattr(result, 'filled_quantity') else Decimal('0')
    remaining = expected_qty - filled_qty
    return max(remaining, Decimal('0'))
```

**Acceptance Criteria:**
- [ ] Calculates remaining = expected_qty - filled_qty
- [ ] Returns 0 if over-filled (safety check)
- [ ] Returns expected_qty if no fill
- [ ] Returns remaining qty if partial fill
- [ ] Logs calculation: "[CALC] Remaining {remaining} after partial fill {filled}"
- [ ] Used before MARKET fallback orders
- [ ] Type hints on all parameters

**Testing:**
- Unit test: No fill → returns expected_qty
- Unit test: Full fill → returns 0
- Unit test: Partial fill → returns remaining
- Unit test: Over-fill → returns 0 (safety)

---

#### Task 6.3: Update MARKET order sizing with partial fill adjustment
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
# In execute_unwind_cycle()
if not ioc_success:
    # Check for partial fills
    eth_partial = detect_partial_fill(eth_result, abs(eth_pos_before))
    sol_partial = detect_partial_fill(sol_result, abs(sol_pos_before))
    
    # Calculate remaining quantities
    eth_remaining = calculate_remaining_quantity(eth_result, abs(eth_pos_before))
    sol_remaining = calculate_remaining_quantity(sol_result, abs(sol_pos_before))
    
    self.logger.info(f"[UNWIND] Partial fills: ETH={eth_partial} ({eth_remaining} remaining), SOL={sol_partial} ({sol_remaining} remaining)")
    
    # Place MARKET orders for remaining quantities
    if eth_remaining > 0:
        eth_result = await self.eth_client.place_market_order(
            self.eth_client.config.contract_id,
            eth_remaining,
            eth_side
        )
    
    if sol_remaining > 0:
        sol_result = await self.sol_client.place_market_order(
            self.sol_client.config.contract_id,
            sol_remaining,
            sol_side
        )
```

**Acceptance Criteria:**
- [ ] Detects partial fills before MARKET fallback
- [ ] Calculates remaining quantities correctly
- [ ] Places MARKET orders only for remaining qty
- [ ] Skips MARKET order if fully filled (remaining = 0)
- [ ] Logs partial fill detection and calculations
- [ ] Handles asymmetric partial fills (ETH partial, SOL no fill)
- [ ] Type hints on all variables

**Testing:**
- Unit test: Both partial fill → MARKET for remaining
- Unit test: One partial, one no fill → MARKET for both
- Unit test: One full, one partial → MARKET for partial only
- Unit test: Both full → no MARKET orders
- Integration test: End-to-end partial fill handling

---

### Phase 7: Unwind Cycle Robustness

#### Task 7.1: Implement IOC → MARKET fallback in `execute_unwind_cycle()`
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 436-484

**Current Implementation (IOC only):**
```python
async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
    # Place IOC orders
    eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

    # Check if orders filled
    if not (eth_result.success and sol_result.success):
        return False  # No retry, no fallback

    # Verify positions closed with retries
    for attempt in range(MAX_RETRIES):
        # ... polling logic ...
```

**New Implementation (IOC with MARKET fallback):**
```python
async def execute_unwind_cycle(self, eth_side: str = "sell", sol_side: str = "buy") -> bool:
    """
    Execute UNWIND cycle with IOC → MARKET fallback.

    Strategy:
    1. Try IOC orders first (fast, low fees)
    2. If IOC fails, fallback to MARKET orders (guaranteed fill)
    3. Verify positions closed with polling
    4. Retry if verification fails

    Returns:
        True if both positions verified closed, False otherwise
    """
    if not FeatureFlags.USE_MARKET_FALLBACK:
        self.logger.warning("[FEATURE] MARKET fallback disabled, using IOC only")
        # Original IOC-only logic
        return await self._execute_unwind_ioc_only(eth_side, sol_side)
    
    POSITION_TOLERANCE = Decimal("0.001")
    MAX_RETRIES = 5  # Increased from 3
    RETRY_DELAY = 5.0  # Increased from 2.0

    # Log pre-unwind positions
    eth_pos_before = await self.eth_client.get_account_positions()
    sol_pos_before = await self.sol_client.get_account_positions()
    self.logger.info(f"[UNWIND] POSITIONS BEFORE: ETH={eth_pos_before}, SOL={sol_pos_before}")

    # Attempt 1: IOC orders (fast, low fees)
    self.logger.info(f"[UNWIND] Attempt 1: IOC orders")
    eth_result, sol_result = await self.place_simultaneous_orders(eth_side, sol_side)

    # Check if IOC succeeded
    ioc_success = (
        isinstance(eth_result, OrderResult) and eth_result.success and eth_result.status == 'FILLED' and
        isinstance(sol_result, OrderResult) and sol_result.success and sol_result.status == 'FILLED'
    )

    if not ioc_success:
        # IOC failed - check for partial fills
        eth_partial = self.detect_partial_fill(eth_result, abs(eth_pos_before))
        sol_partial = self.detect_partial_fill(sol_result, abs(sol_pos_before))
        
        # Calculate remaining quantities
        eth_remaining = self.calculate_remaining_quantity(eth_result, abs(eth_pos_before))
        sol_remaining = self.calculate_remaining_quantity(sol_result, abs(sol_pos_before))
        
        self.logger.warning(
            f"[UNWIND] IOC orders failed (ETH: {eth_result.status}, SOL: {sol_result.status})"
        )
        self.logger.info(
            f"[UNWIND] Partial fills: ETH={eth_partial} ({eth_remaining} remaining), "
            f"SOL={sol_partial} ({sol_remaining} remaining)"
        )
        self.logger.info("[UNWIND] Fallback: MARKET orders for guaranteed execution")

        # Place MARKET orders for remaining quantities
        if eth_remaining > 0:
            eth_result = await self.eth_client.place_market_order(
                self.eth_client.config.contract_id,
                eth_remaining,
                eth_side
            )
        
        if sol_remaining > 0:
            sol_result = await self.sol_client.place_market_order(
                self.sol_client.config.contract_id,
                sol_remaining,
                sol_side
            )

        if not eth_result.success or not sol_result.success:
            self.logger.error("[UNWIND] MARKET orders failed - cannot close positions")
            return False

    # Verify positions closed with retries
    for attempt in range(MAX_RETRIES):
        await asyncio.sleep(RETRY_DELAY)

        eth_pos = await self.eth_client.get_account_positions()
        sol_pos = await self.sol_client.get_account_positions()

        self.logger.info(f"[UNWIND] POSITIONS CHECK (attempt {attempt + 1}/{MAX_RETRIES}): ETH={eth_pos}, SOL={sol_pos}")

        eth_closed = abs(eth_pos) < POSITION_TOLERANCE
        sol_closed = abs(sol_pos) < POSITION_TOLERANCE

        if eth_closed and sol_closed:
            self.logger.info("[UNWIND] SUCCESS: Both positions verified closed")
            return True

        if attempt < MAX_RETRIES - 1:
            self.logger.warning(f"[UNWIND] Positions still open, retrying in {RETRY_DELAY}s...")

    self.logger.error(f"[UNWIND] FAILED: Positions still open after {MAX_RETRIES} retries: ETH={eth_pos}, SOL={sol_pos}")
    return False
```

**Acceptance Criteria:**
- [ ] First attempts IOC orders (existing behavior)
- [ ] Checks for partial fills before MARKET fallback
- [ ] Calculates remaining quantities correctly
- [ ] If IOC fails (not FILLED), logs fallback reason
- [ ] Fallback uses `place_market_order()` for remaining quantities
- [ ] MARKET orders use calculated remaining quantities
- [ ] Logs "FALLBACK: MARKET orders" when IOC fails
- [ ] Returns `False` if MARKET orders fail
- [ ] Increases MAX_RETRIES from 3 to 5
- [ ] Increases RETRY_DELAY from 2.0 to 5.0 seconds
- [ ] Verification polls up to 5 times × 5 seconds = 25 seconds max
- [ ] Logs "SUCCESS: Both positions verified closed" only when verified
- [ ] Respects FeatureFlags.USE_MARKET_FALLBACK
- [ ] Type hints on all parameters and return value
- [ ] Docstring explaining IOC → MARKET fallback

**Testing:**
- Unit test: IOC succeeds → No fallback
- Unit test: IOC fails ETH → MARKET fallback for ETH
- Unit test: IOC fails SOL → MARKET fallback for SOL
- Unit test: IOC fails both → MARKET fallback for both
- Unit test: IOC partial fill ETH → MARKET for remaining ETH
- Unit test: MARKET fallback succeeds
- Unit test: MARKET fallback fails (returns False)
- Integration test: Full cycle with IOC failure
- Integration test: Full cycle with partial fill

---

#### Task 7.2: Increase retry count and timeout in position verification
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Changes:**
- `MAX_RETRIES`: 3 → 5 (line 447)
- `RETRY_DELAY`: 2.0 → 5.0 seconds (line 448)
- `verify_position_closed()`: Default timeout 30 seconds, poll interval 0.5s

**Acceptance Criteria:**
- [ ] MAX_RETRIES = 5 in `execute_unwind_cycle()`
- [ ] RETRY_DELAY = 5.0 in `execute_unwind_cycle()`
- [ ] `verify_position_closed()` defaults: timeout=30s, interval=0.5s
- [ ] Total verification time: 5 retries × 5 seconds = 25 seconds max
- [ ] Allow sufficient time for exchange API delays

---

#### Task 7.3: Add graceful retry with MARKET before halt
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`, lines 543-574

**Current Implementation:**
```python
async def run_alternating_strategy(self) -> List[bool]:
    for i in range(self.iterations):
        result = await self.execute_buy_first_cycle() or self.execute_sell_first_cycle()

        # CRITICAL: Stop if UNWIND failed
        if not result:
            self.logger.error(f"[SAFETY] Cycle {iteration_num} FAILED! Bot stopping...")
            break  # Immediate halt - too conservative
```

**New Implementation (Graceful Halt):**
```python
async def run_alternating_strategy(self) -> List[bool]:
    """Run alternating strategy for N iterations with graceful recovery."""
    results = []
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 2  # Allow 1 retry before permanent halt

    for i in range(self.iterations):
        iteration_num = i + 1
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ITERATION {iteration_num}/{self.iterations}")
        self.logger.info(f"{'='*60}")

        # Execute cycle
        if i % 2 == 0:
            result = await self.execute_buy_first_cycle()
        else:
            result = await self.execute_sell_first_cycle()

        # Check for failure
        if not result:
            consecutive_failures += 1
            self.logger.error(f"[SAFETY] Cycle {iteration_num} FAILED!")

            # Graceful retry attempt
            if consecutive_failures < MAX_CONSECUTIVE_FAILURES:
                self.logger.warning(
                    f"[RECOVERY] Attempting emergency MARKET unwind before halt..."
                )

                # Force close both positions with MARKET orders
                recovery_success = await self.emergency_recovery_unwind()

                if recovery_success:
                    self.logger.info("[RECOVERY] Emergency MARKET unwind succeeded - resuming")
                    consecutive_failures = 0  # Reset counter
                    results.append(True)
                    continue
                else:
                    self.logger.error("[RECOVERY] Emergency MARKET unwind FAILED - halting")
            else:
                self.logger.error(
                    f"[SAFETY] {MAX_CONSECUTIVE_FAILURES} consecutive failures! "
                    f"Bot halting to prevent accumulation."
                )

            self.logger.error(
                f"[SAFETY] Check positions manually before restarting. "
                f"ETH and SOL positions should be near 0."
            )
            break
        else:
            consecutive_failures = 0  # Reset on success
            results.append(True)
            self.logger.info(f"[SUCCESS] Cycle {iteration_num} completed successfully")

    return results


async def emergency_recovery_unwind(self) -> bool:
    """
    Emergency recovery: Force close both positions with MARKET orders.

    Returns:
        True if both positions verified closed, False otherwise
    """
    self.logger.info("[RECOVERY] Starting emergency MARKET unwind for both positions")

    # Close both positions with MARKET orders
    eth_success = await self.emergency_unwind_eth()
    sol_success = await self.emergency_unwind_sol()

    if eth_success and sol_success:
        self.logger.info("[RECOVERY] Both positions closed successfully")
        return True
    else:
        self.logger.error(
            f"[RECOVERY] Emergency unwind incomplete: "
            f"ETH={'closed' if eth_success else 'OPEN'}, "
            f"SOL={'closed' if sol_success else 'OPEN'}"
        )
        return False
```

**Acceptance Criteria:**
- [ ] Tracks `consecutive_failures` counter
- [ ] Allows 1 retry before permanent halt (`MAX_CONSECUTIVE_FAILURES = 2`)
- [ ] First failure triggers `emergency_recovery_unwind()`
- [ ] `emergency_recovery_unwind()` closes BOTH positions with MARKET
- [ ] Verifies BOTH positions closed before returning True
- [ ] If recovery succeeds, resets counter and continues trading
- [ ] If recovery fails, halts with SAFETY error
- [ ] Logs "[RECOVERY] Attempting emergency MARKET unwind"
- [ ] Logs "[RECOVERY] Emergency MARKET unwind succeeded/FAILED"
- [ ] Type hints on all new methods
- [ ] Docstrings explaining recovery logic

**Testing:**
- Unit test: Single failure → Recovery succeeds → Resumes trading
- Unit test: Single failure → Recovery fails → Halts
- Unit test: Two consecutive failures → Halts without second recovery
- Unit test: Recovery after IOC failure
- Unit test: Recovery after network error
- Integration test: Full strategy with transient failure

---

### Phase 8: API Downtime Resilience

#### Task 8.1: Implement exchange downtime detection
**File:** `/Users/botfarmer/2dex/hedge/exchanges/nado.py`

**Implementation:**
```python
class ExchangeHealthMonitor:
    """Monitor exchange API health."""
    
    def __init__(self, unhealthy_threshold: int = 3):
        """
        Initialize health monitor.
        
        Args:
            unhealthy_threshold: Consecutive failures before declaring unhealthy
        """
        self.unhealthy_threshold = unhealthy_threshold
        self.consecutive_failures = 0
        self.last_healthy_check = time.time()
        self.is_healthy = True
    
    def record_success(self):
        """Record successful API call."""
        self.consecutive_failures = 0
        self.last_healthy_check = time.time()
        self.is_healthy = True
    
    def record_failure(self):
        """Record failed API call."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.unhealthy_threshold:
            self.is_healthy = False
    
    def check_health(self) -> bool:
        """Check if exchange is healthy."""
        return self.is_healthy
```

**Acceptance Criteria:**
- [ ] Tracks consecutive API failures
- [ ] Declares unhealthy after threshold (default 3)
- [ ] Resets on successful API call
- [ ] Provides check_health() method
- [ ] Logs health transitions: "[HEALTH] Exchange {healthy/unhealthy}"
- [ ] Used before placing orders
- [ ] Integrated with circuit breaker

**Testing:**
- Unit test: Healthy → failure → unhealthy after threshold
- Unit test: Unhealthy → success → healthy
- Unit test: Threshold configurable
- Integration test: Health monitoring prevents orders during outage

---

#### Task 8.2: Add graceful degradation modes
**File:** `/Users/botfarmer/2dex/hedge/DN_pair_eth_sol_nado.py`

**Implementation:**
```python
async def execute_unwind_cycle_with_degradation(self, eth_side: str, sol_side: str) -> bool:
    """
    Execute UNWIND cycle with graceful degradation on API issues.
    
    Degradation modes:
    1. NORMAL: Full functionality (IOC + MARKET fallback)
    2. DEGRADED: MARKET only (skip IOC)
    3. MINIMAL: Delay and retry (wait for API recovery)
    4. HALT: Cannot proceed safely
    """
    # Check exchange health
    if not self.eth_client.health_monitor.check_health():
        self.logger.warning("[DEGRADE] ETH exchange unhealthy, entering DEGRADED mode")
        # Skip IOC, go straight to MARKET
        return await self._execute_unwind_market_only(eth_side, sol_side)
    
    if not self.sol_client.health_monitor.check_health():
        self.logger.warning("[DEGRADE] SOL exchange unhealthy, entering DEGRADED mode")
        # Skip IOC, go straight to MARKET
        return await self._execute_unwind_market_only(eth_side, sol_side)
    
    # Both healthy, normal operation
    return await self.execute_unwind_cycle(eth_side, sol_side)

async def _execute_unwind_market_only(self, eth_side: str, sol_side: str) -> bool:
    """Execute UNWIND using MARKET orders only (no IOC)."""
    self.logger.info("[DEGRADE] Using MARKET-only mode (IOC skipped)")
    
    # Get current positions
    eth_pos = await self.eth_client.get_account_positions()
    sol_pos = await self.sol_client.get_account_positions()
    
    # Close both with MARKET
    eth_result = await self.eth_client.place_market_order(
        self.eth_client.config.contract_id,
        abs(eth_pos),
        eth_side
    )
    
    sol_result = await self.sol_client.place_market_order(
        self.sol_client.config.contract_id,
        abs(sol_pos),
        sol_side
    )
    
    if not eth_result.success or not sol_result.success:
        self.logger.error("[DEGRADE] MARKET orders failed in DEGRADED mode")
        return False
    
    # Verify positions closed
    is_closed = await self.verify_position_closed("ETH") and await self.verify_position_closed("SOL")
    
    return is_closed
```

**Acceptance Criteria:**
- [ ] Checks exchange health before operations
- [ ] DEGRADED mode: Skip IOC, use MARKET only
- [ ] MINIMAL mode: Delay and retry (implemented in retry logic)
- [ ] HALT mode: Stop if cannot proceed safely
- [ ] Logs mode transitions: "[DEGRADE] Entered {mode} mode"
- [ ] MARKET-only mode bypasses IOC attempts
- [ ] Still verifies position closure in DEGRADED mode

**Testing:**
- Unit test: Normal → DEGRADED transition
- Unit test: DEGRADED → NORMAL transition
- Unit test: MARKET-only execution succeeds
- Unit test: Halt when both exchanges unhealthy
- Integration test: Full degradation cycle

---

#### Task 8.3: Create API downtime test scenarios
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_api_downtime.py` (new file)

**Test Cases:**
```python
class TestAPIDowntime:
    """Test API downtime scenarios."""
    
    async def test_exchange_unavailable_at_start(self):
        """Test bot behavior when exchange down at startup."""
        
    async def test_exchange_goes_down_during_unwind(self):
        """Test bot behavior when exchange goes down during unwind."""
        
    async def test_partial_outage_one_exchange(self):
        """Test bot behavior when only one exchange is down."""
        
    async def test_degraded_mode_operations(self):
        """Test DEGRADED mode functionality."""
        
    async def test_recovery_after_outage(self):
        """Test bot recovery after exchange comes back online."""
```

**Acceptance Criteria:**
- [ ] Test for exchange unavailable at startup
- [ ] Test for exchange down during unwind
- [ ] Test for partial outage (one exchange)
- [ ] Test degraded mode operations
- [ ] Test recovery after outage
- [ ] All tests pass with simulated downtime
- [ ] Logs show correct mode transitions

**Testing:**
- Unit test: Startup with exchange down
- Unit test: Mid-operation exchange failure
- Unit test: Partial outage handling
- Integration test: Degraded mode execution
- Integration test: Recovery after outage

---

### Phase 9: Testing & Validation

#### Task 9.1: Unit tests for `place_market_order()`
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_market_order.py` (new file)

**Test Cases:**
```python
class TestPlaceMarketOrder:
    """Unit tests for place_market_order() in NadoClient."""

    async def test_market_buy_order_fills(self):
        """Test MARKET buy order fills successfully."""
        # Setup mock client with BBO: bid=2700, ask=2701
        # Expect order at ask+0.1% = 2703.70 (aggressive)
        # Verify order placed and filled

    async def test_market_sell_order_fills(self):
        """Test MARKET sell order fills successfully."""
        # Setup mock client with BBO: bid=2700, ask=2701
        # Expect order at bid-0.1% = 2697.30 (aggressive)
        # Verify order placed and filled

    async def test_market_order_retry_on_network_error(self):
        """Test MARKET order retries on network errors."""
        # Mock first 2 calls to fail, 3rd to succeed
        # Verify retry attempts with exponential backoff
        # Verify success after retries

    async def test_market_order_returns_failure_on_max_retries(self):
        """Test MARKET order fails after max retries."""
        # Mock all calls to fail
        # Verify returns OrderResult(success=False)
        # Verify error message populated

    async def test_market_order_respects_max_slippage(self):
        """Test MARKET order respects max_slippage_bps parameter."""
        # Test with max_slippage_bps=10 (0.1%)
        # Test with max_slippage_bps=100 (1%)
        # Verify pricing within slippage limit

    async def test_market_order_uses_ordertype_default(self):
        """Test MARKET order uses OrderType.DEFAULT (not LIMIT)."""
        # Verify OrderType.DEFAULT is used
        # Verify OrderType.LIMIT is NOT used (doesn't exist)
```

**Acceptance Criteria:**
- [ ] All tests pass with mocked NadoClient
- [ ] Test coverage > 90% for `place_market_order()`
- [ ] Edge cases covered: network errors, retries, slippage
- [ ] Assertions verify OrderResult fields populated correctly
- [ ] Confirms OrderType.DEFAULT usage (not LIMIT)

---

#### Task 9.2: Unit tests for rate limiting
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_rate_limiting.py` (new file)

**Test Cases:**
```python
class TestRateLimiting:
    """Unit tests for rate limiting."""

    async def test_token_bucket_refill_rate(self):
        """Test token bucket refills at configured rate."""

    async def test_token_bucket_burst_allowance(self):
        """Test token bucket allows burst up to capacity."""

    async def test_rate_limiting_enforcement(self):
        """Test rate limiting enforced after burst exhausted."""

    async def test_concurrent_request_handling(self):
        """Test thread-safe handling of concurrent requests."""

    async def test_prevents_429_errors_under_load(self):
        """Test rate limiting prevents 429 errors."""
```

**Acceptance Criteria:**
- [ ] All tests pass with RateLimiter implementation
- [ ] Test coverage > 95% for RateLimiter
- [ ] Edge cases covered: burst, concurrent requests, refill
- [ ] Confirms 429 error prevention

---

#### Task 9.3: Unit tests for BBO validation
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_bbo_validation.py` (new file)

**Test Cases:**
```python
class TestBBOValidation:
    """Unit tests for BBO validation."""

    async def test_valid_bbo_passes(self):
        """Test valid BBO passes validation."""

    async def test_invalid_spread_fails(self):
        """Test invalid spread (ask <= bid) fails."""

    async def test_stale_timestamp_fails(self):
        """Test stale timestamp fails."""

    async def test_price_anomaly_detection(self):
        """Test price anomaly detection works."""

    async def test_fallback_to_rest_on_invalid(self):
        """Test fallback to REST on invalid BBO."""
```

**Acceptance Criteria:**
- [ ] All tests pass with BBO validation
- [ ] Test coverage > 90% for BBO validation
- [ ] Edge cases covered: invalid spread, stale data, anomalies
- [ ] Confirms REST fallback behavior

---

#### Task 9.4: Unit tests for circuit breaker
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_circuit_breaker.py` (new file)

**Test Cases:**
```python
class TestCircuitBreaker:
    """Unit tests for circuit breaker."""

    async def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""

    async def test_circuit_closes_after_successful_call(self):
        """Test circuit closes after successful call."""

    async def test_half_open_state_transition(self):
        """Test half-open state transition."""

    async def test_exception_when_circuit_open(self):
        """Test exception raised when circuit open."""

    async def test_prevents_cascading_failures(self):
        """Test circuit breaker prevents cascading failures."""
```

**Acceptance Criteria:**
- [ ] All tests pass with CircuitBreaker implementation
- [ ] Test coverage > 95% for CircuitBreaker
- [ ] Edge cases covered: state transitions, thresholds
- [ ] Confirms cascading failure prevention

---

#### Task 9.5: Integration tests for emergency unwind
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_emergency_unwind.py` (new file)

**Test Cases:**
```python
class TestEmergencyUnwind:
    """Integration tests for emergency unwind logic."""

    async def test_emergency_unwind_eth_succeeds(self):
        """Test emergency_unwind_eth() succeeds with MARKET order."""

    async def test_emergency_unwind_eth_fails_verification(self):
        """Test emergency_unwind_eth() fails when position not closed."""

    async def test_emergency_unwind_sol_succeeds(self):
        """Test emergency_unwind_sol() succeeds with MARKET order."""

    async def test_emergency_unwind_with_exception(self):
        """Test emergency_unwind handles exceptions gracefully."""
```

**Acceptance Criteria:**
- [ ] All tests pass with integration mocks
- [ ] Test coverage = 100% for emergency unwind methods
- [ ] Exception handling verified
- [ ] Verification logic tested

---

#### Task 9.6: Integration tests for partial fill handling
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_partial_fill.py` (new file)

**Test Cases:**
```python
class TestPartialFill:
    """Integration tests for partial fill handling."""

    async def test_detect_partial_fill(self):
        """Test partial fill detection works."""

    async def test_calculate_remaining_quantity(self):
        """Test remaining quantity calculation."""

    async def test_market_order_sizing_with_partial_fill(self):
        """Test MARKET order sizing adjusted for partial fill."""

    async def test_asymmetric_partial_fills(self):
        """Test asymmetric partial fills (ETH partial, SOL full)."""
```

**Acceptance Criteria:**
- [ ] All tests pass with partial fill logic
- [ ] Test coverage = 100% for partial fill handling
- [ ] Edge cases covered: asymmetric fills, over-fills
- [ ] MARKET sizing verified

---

#### Task 9.7: Chaos engineering tests for network failures
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_chaos_network.py` (new file)

**Test Cases:**
```python
class TestChaosNetwork:
    """Chaos engineering tests for network failures."""

    async def test_timeout_simulation(self):
        """Test behavior during network timeout."""

    async def test_connection_refused_simulation(self):
        """Test behavior on connection refused."""

    async def test_dns_failure_simulation(self):
        """Test behavior on DNS resolution failure."""

    async def test_packet_loss_simulation(self):
        """Test behavior during packet loss."""

    async def test_circuit_breaker_opens_on_partition(self):
        """Test circuit breaker opens on network partition."""

    async def test_retry_logic_handles_partition(self):
        """Test retry logic handles network partition."""

    async def test_graceful_degradation_on_partition(self):
        """Test graceful degradation on network partition."""
```

**Acceptance Criteria:**
- [ ] All chaos tests pass with simulated failures
- [ ] Circuit breaker behavior verified
- [ ] Retry logic verified
- [ ] Graceful degradation verified

---

#### Task 9.8: End-to-end tests for failure scenarios
**File:** `/Users/botfarmer/2dex/tests/stage4/dn_pair/test_failure_scenarios.py` (new file)

**Test Cases:**
```python
class TestFailureScenarios:
    """End-to-end tests for UNWIND failure scenarios."""

    async def test_ioc_fails_market_fallback_succeeds(self):
        """Test IOC failure → MARKET fallback → Success."""

    async def test_ioc_fails_market_fallback_fails(self):
        """Test IOC failure → MARKET fallback → Failure."""

    async def test_cycle_6_scenario_reproduction(self):
        """Test reproduce Cycle 6 failure scenario."""

    async def test_graceful_recovery_after_failure(self):
        """Test graceful recovery with MARKET retry."""

    async def test_permanent_halt_after_recovery_failure(self):
        """Test permanent halt when recovery fails."""

    async def test_api_downtime_degraded_mode(self):
        """Test degraded mode during API downtime."""

    async def test_network_partition_recovery(self):
        """Test recovery after network partition."""
```

**Acceptance Criteria:**
- [ ] All tests pass with full integration mocks
- [ ] Cycle 6 scenario reproducible and fixable
- [ ] Recovery logic tested end-to-end
- [ ] Permanent halt logic verified
- [ ] Degraded mode tested
- [ ] Network partition recovery tested

---

#### Task 9.9: Run existing test suite and fix failures
**Files:** All existing tests

**Actions:**
1. Run existing test suite: `pytest tests/stage4/dn_pair/ -v`
2. Fix any breaking changes from refactoring
3. Ensure all existing tests still pass
4. Update tests if needed (e.g., return value changes)

**Acceptance Criteria:**
- [ ] All existing tests pass
- [ ] `test_priority1_unwind_position_verification.py` passes
- [ ] No regressions introduced
- [ ] Test coverage maintained or increased

---

### Phase 10: Documentation & Handoff

#### Task 10.1: Update code documentation
**Files:** All modified files

**Actions:**
- Update docstrings for modified methods
- Add usage examples for new methods
- Document emergency unwind flow in comments
- Update type hints for all modified signatures

**Acceptance Criteria:**
- [ ] All new methods have comprehensive docstrings
- [ ] All modified methods have updated docstrings
- [ ] Type hints present on all public methods
- [ ] Complex logic has inline comments

---

#### Task 10.2: Create runbook for emergency procedures
**File:** `/Users/botfarmer/2dex/docs/dn-pair-emergency-runbook.md` (new file)

**Content:**
```markdown
# DN Pair Bot Emergency Runbook

## Automatic Recovery Procedures

### IOC Order Failure
**Trigger:** IOC order expires without fill
**Automatic Action:**
1. Bot detects IOC failure (OrderResult.status != 'FILLED')
2. Logs: "[UNWIND] IOC orders failed - Fallback: MARKET orders"
3. Places MARKET orders for both legs
4. Verifies positions closed with polling (30s timeout)
5. Resumes trading if successful, halts if failed

**Manual Intervention Required:** No (automatic)

### Emergency Unwind Triggered
**Trigger:** One leg fills, other fails
**Automatic Action:**
1. Bot detects asymmetric fill (e.g., ETH filled, SOL failed)
2. Logs: "[UNWIND] SOL filled but ETH failed, closing SOL position"
3. Closes filled leg with MARKET order
4. Verifies position closed with polling
5. Returns False (cycle failed)

**Manual Intervention Required:** No (automatic)

### Graceful Recovery Attempt
**Trigger:** First cycle failure
**Automatic Action:**
1. Bot logs: "[RECOVERY] Attempting emergency MARKET unwind"
2. Closes BOTH positions with MARKET orders
3. Verifies BOTH positions closed
4. Resumes trading if successful
5. Halts if recovery fails

**Manual Intervention Required:** No (automatic)

## Manual Recovery Procedures

### Bot Halted with Open Positions
**Trigger:** Automatic recovery failed
**Symptoms:**
- Log: "[SAFETY] Cycle N FAILED! Bot stopping..."
- Log: "[SAFETY] Check positions manually before restarting"

**Manual Steps:**
1. Check positions on exchange UI
2. If positions exist, run manual close script:
   ```bash
   cd /Users/botfarmer/2dex/hedge
   python close_positions.py
   ```
3. Verify positions closed (output should show "✅ Positions closed successfully!")
4. Do NOT restart bot until positions = 0

### Feature Flag Rollback
**Trigger:** Issues with MARKET fallback
**Symptoms:**
- High slippage on MARKET orders
- Frequent MARKET fallback failures
- Excessive 429 errors

**Manual Steps:**
1. Disable MARKET fallback:
   ```bash
   export DN_USE_MARKET_FALLBACK=false
   ```
2. Restart bot with IOC-only mode
3. Monitor for IOC failure rate
4. If IOC failures acceptable, continue with IOC-only
5. If IOC failures high, investigate root cause

### Exchange API Downtime
**Trigger:** Exchange API unavailable
**Symptoms:**
- Log: "[HEALTH] Exchange unhealthy"
- Log: "[DEGRADE] Entered DEGRADED mode"
- Bot continues with MARKET-only mode

**Manual Steps:**
1. Check exchange status page
2. If exchange outage confirmed, let bot run in DEGRADED mode
3. Bot will automatically exit DEGRADED mode when API recovers
4. If bot halts, follow "Bot Halted with Open Positions" procedure
5. Do NOT restart bot until exchange API is healthy

## Monitoring and Alerts

### Key Log Patterns to Monitor
- `[UNWIND] IOC orders failed` - IOC failure rate
- `[RECOVERY] Attempting emergency MARKET unwind` - Recovery attempts
- `[UNWIND] FAILED: Positions still open` - Verification failures
- `[SAFETY] Cycle N FAILED` - Cycle failures
- `[RATE_LIMIT] Throttling API call` - Rate limit events
- `[CIRCUIT] Circuit breaker opened` - Circuit breaker events
- `[HEALTH] Exchange unhealthy` - Exchange health issues
- `[DEGRADE] Entered DEGRADED mode` - Degradation events

### Healthy Operation Indicators
- Most cycles: `[SUCCESS] Cycle N completed successfully`
- Few IOC fallbacks: <10% of cycles
- Zero emergency unwinds: Should never happen in healthy operation
- Zero recovery attempts: Should never happen in healthy operation
- Zero circuit breaker events: Should rarely happen
- Zero 429 errors: Rate limiting working

### Degraded Operation Indicators
- Frequent IOC fallbacks: >20% of cycles
- Emergency unwinds occurring: Indicates asymmetric fills
- Recovery attempts: Indicates IOC + MARKET failures
- Circuit breaker events: Indicates network issues
- Exchange unhealthy events: Indicates API issues

## Configuration Tuning

### Conservative Mode (Highest Safety)
```python
# In DN_pair_eth_sol_nado.py or environment variables
MAX_RETRIES = 10  # More retries
RETRY_DELAY = 10.0  # Longer delay
MAX_CONSECUTIVE_FAILURES = 1  # Halt immediately
DN_MARKET_MAX_SLIPPAGE_BPS = 100  # Allow 1% slippage
DN_RATE_LIMIT_PER_SECOND = 5  # Conservative rate limiting
DN_BURST_SIZE = 10  # Smaller burst
```

### Balanced Mode (Default)
```python
MAX_RETRIES = 5
RETRY_DELAY = 5.0
MAX_CONSECUTIVE_FAILURES = 2  # Allow 1 recovery
DN_MARKET_MAX_SLIPPAGE_BPS = 50  # Allow 0.5% slippage
DN_RATE_LIMIT_PER_SECOND = 10  # Standard rate limiting
DN_BURST_SIZE = 20  # Standard burst
```

### Aggressive Mode (Lowest Safety, Not Recommended)
```python
MAX_RETRIES = 3
RETRY_DELAY = 2.0
MAX_CONSECUTIVE_FAILURES = 3  # Allow 2 recoveries
DN_MARKET_MAX_SLIPPAGE_BPS = 20  # Allow 0.2% slippage
DN_RATE_LIMIT_PER_SECOND = 20  # Aggressive rate limiting
DN_BURST_SIZE = 40  # Larger burst
```

## Contact and Escalation
- Developer: [Your contact]
- On-call: [On-call procedure]
- Emergency: [Emergency shutdown procedure]
```

**Acceptance Criteria:**
- [ ] Runbook covers all emergency scenarios
- [ ] Manual procedures are clear and step-by-step
- [ ] Automatic procedures documented with log examples
- [ ] Monitoring guidelines included
- [ ] Configuration tuning options documented

---

#### Task 10.3: Document feature flags and rollback procedures
**File:** `/Users/botfarmer/2dex/docs/dn-pair-feature-flags.md` (new file)

**Content:**
```markdown
# DN Pair Bot Feature Flags

## Overview
Feature flags allow runtime control of bot behavior without code changes.

## Available Feature Flags

### MARKET Fallback Features
- `DN_USE_MARKET_FALLBACK`: Enable/disable IOC → MARKET fallback (default: true)
- `DN_MARKET_MAX_SLIPPAGE_BPS`: Maximum slippage for MARKET orders in bps (default: 50)

### Rate Limiting Features
- `DN_ENABLE_RATE_LIMITING`: Enable/disable rate limiting (default: true)
- `DN_RATE_LIMIT_PER_SECOND`: API calls per second (default: 10)
- `DN_BURST_SIZE`: Maximum burst size (default: 20)

### Circuit Breaker Features
- `DN_ENABLE_CIRCUIT_BREAKER`: Enable/disable circuit breaker (default: true)
- `DN_CIRCUIT_FAILURE_THRESHOLD`: Failures before opening circuit (default: 5)
- `DN_CIRCUIT_TIMEOUT_SECONDS`: Seconds before trying again (default: 60)

### BBO Features
- `DN_USE_WEBSOCKET_BBO`: Enable/disable WebSocket BBO (default: true)
- `DN_BBO_MAX_AGE_SECONDS`: Maximum BBO age in seconds (default: 2)

## Usage Examples

### Disable MARKET Fallback
```bash
export DN_USE_MARKET_FALLBACK=false
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

### Increase Slippage Tolerance
```bash
export DN_MARKET_MAX_SLIPPAGE_BPS=100  # Allow 1% slippage
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

### Disable Rate Limiting (Use with Caution)
```bash
export DN_ENABLE_RATE_LIMITING=false
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

### Adjust Circuit Breaker Threshold
```bash
export DN_CIRCUIT_FAILURE_THRESHOLD=10  # Allow more failures before opening
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

## Rollback Procedures

See [Rollback Procedures](dn-pair-rollback-procedures.md) for detailed rollback steps.
```

**Acceptance Criteria:**
- [ ] All feature flags documented
- [ ] Default values specified
- [ ] Usage examples provided
- [ ] Rollback procedures referenced

---

#### Task 10.4: Final review and sign-off
**Actions:**
- Review all code changes
- Review all test results
- Review documentation
- Sign-off on deployment readiness

**Acceptance Criteria:**
- [ ] All tasks completed
- [ ] All tests pass (unit + integration + e2e)
- [ ] Code review approved
- [ ] Documentation complete
- [ ] Ready for deployment

---

## Commit Strategy

### Commit 1: Phase 0-1 - Foundation & Infrastructure
```
feat(nado): Implement SDK-compatible MARKET orders and rate limiting

- Verify OrderType enum (DEFAULT, FOK, IOC, POST_ONLY - no LIMIT)
- Implement place_market_order() using OrderType.DEFAULT
- Add verify_position_closed() utility with polling
- Implement token bucket rate limiting
- Enhance position logging throughout bot lifecycle

Critical fixes:
- OrderType.LIMIT does not exist in Nado SDK
- Use OrderType.DEFAULT with aggressive pricing instead
- Rate limiting prevents 429 errors

Closes: Task 0.1, Task 0.2, Task 1.1, Task 1.2, Task 1.3
Risk: Critical - Foundation for all subsequent fixes
Test: Unit tests for new methods
```

### Commit 2: Phase 2-3 - Reliability Infrastructure
```
feat(nado): Add BBO stability and network resilience

- Validate WebSocket BBO data quality
- Implement REST BBO fallback
- Add BBO freshness checks
- Implement circuit breaker for API calls
- Add timeout and retry with exponential backoff
- Create network partition test framework

Benefits:
- Stable BBO data for MARKET pricing
- Circuit breaker prevents cascading failures
- Network resilience with retry logic

Closes: Task 2.1, Task 2.2, Task 2.3, Task 3.1, Task 3.2, Task 3.3
Risk: High - Core reliability infrastructure
Test: Unit and integration tests
```

### Commit 3: Phase 4-5 - Emergency Unwind & Feature Flags
```
fix(dn-pair): Stabilize emergency unwind and add feature flags

- Refactor emergency_unwind_eth() with MARKET + verification
- Refactor emergency_unwind_sol() with MARKET + verification
- Update handle_emergency_unwind() with result verification
- Implement environment variable feature flags
- Add runtime feature toggle checks
- Document rollback procedures

Critical fixes:
- Emergency unwind now GUARANTEED to close positions or report failure
- Feature flags enable instant rollback
- Previous behavior: Logged "closing position" but never verified

Closes: Task 4.1, Task 4.2, Task 4.3, Task 5.1, Task 5.2, Task 5.3
Risk: Critical - Fixes root cause of position accumulation
Test: Integration tests for emergency unwind
```

### Commit 4: Phase 6 - Partial Fill Handling
```
feat(dn-pair): Add partial fill detection and handling

- Detect IOC partial fills in OrderResult
- Calculate remaining quantity after partial fill
- Update MARKET order sizing with partial fill adjustment
- Handle asymmetric partial fills

Benefits:
- Correct MARKET order sizing after partial fills
- Prevents over-trading on partial fills
- Handles real-world IOC behavior

Closes: Task 6.1, Task 6.2, Task 6.3
Risk: Medium - Edge case handling
Test: Integration tests for partial fill scenarios
```

### Commit 5: Phase 7 - Unwind Cycle Robustness
```
feat(dn-pair): Add IOC → MARKET fallback and graceful recovery

- Implement IOC → MARKET fallback in execute_unwind_cycle()
- Increase retry count (3→5) and timeout (2s→5s)
- Add graceful recovery with MARKET retry before halt
- Implement emergency_recovery_unwind() for forced closure

Benefits:
- IOC orders still fast when they work (low fees)
- Automatic MARKET fallback when IOC fails (guaranteed close)
- Graceful recovery before permanent halt (reduces manual intervention)
- Partial fill handling ensures correct MARKET sizing

Closes: Task 7.1, Task 7.2, Task 7.3
Risk: High - Changes core unwind logic
Test: End-to-end tests for failure scenarios
```

### Commit 6: Phase 8 - API Downtime Resilience
```
feat(dn-pair): Add API downtime detection and graceful degradation

- Implement exchange downtime detection
- Add graceful degradation modes (NORMAL, DEGRADED, MINIMAL, HALT)
- Create API downtime test scenarios

Benefits:
- Bot continues operation during partial outages
- Automatic degradation when exchanges unhealthy
- Safe halt when cannot proceed

Closes: Task 8.1, Task 8.2, Task 8.3
Risk: Medium - Degradation mode logic
Test: Chaos engineering tests
```

### Commit 7: Phase 9 - Comprehensive Testing
```
test(dn-pair): Add comprehensive test coverage for V2 features

- Unit tests for place_market_order() (6 test cases)
- Unit tests for rate limiting (5 test cases)
- Unit tests for BBO validation (5 test cases)
- Unit tests for circuit breaker (6 test cases)
- Integration tests for emergency unwind (4 test cases)
- Integration tests for partial fill handling (4 test cases)
- Chaos engineering tests for network failures (7 test cases)
- End-to-end tests for failure scenarios (7 test cases)
- Fix any failures in existing test suite

Coverage: 100% of emergency unwind paths, 95%+ of new code
Closes: Task 9.1, Task 9.2, Task 9.3, Task 9.4, Task 9.5, Task 9.6, Task 9.7, Task 9.8, Task 9.9
Risk: Low - Test-only changes
Test: All tests pass
```

### Commit 8: Phase 10 - Documentation
```
docs(dn-pair): Add comprehensive documentation for V2 features

- Update code documentation for all modified methods
- Create emergency runbook
- Document feature flags and rollback procedures
- Add V2 gap analysis and migration guide

Closes: Task 10.1, Task 10.2, Task 10.3, Task 10.4
Risk: Low - Documentation only
Test: N/A
```

---

## Success Criteria

### Functional Requirements
- [ ] **100% of emergency unwinds verify position closure** - No more "assumed" closures
- [ ] **100% of UNWIND failures trigger MARKET retry** - No silent failures
- [ ] **0% position accumulation possible** - Code prevents accumulation at every level
- [ ] **99%+ of UNWIND cycles succeed on first attempt** - IOC → MARKET fallback effective
- [ ] **OrderType.DEFAULT used for MARKET orders** - Not LIMIT (doesn't exist in SDK)
- [ ] **Rate limiting prevents 429 errors** - Under normal load (10 req/s)
- [ ] **WebSocket BBO validated before use** - Falls back to REST if invalid
- [ ] **Circuit breaker prevents cascading failures** - Opens after 5 consecutive failures
- [ ] **Feature flags enable instant rollback** - All features toggled via environment
- [ ] **Partial fills handled correctly** - MARKET orders sized for remaining quantity
- [ ] **API downtime handled gracefully** - Degraded modes during outages

### Quality Requirements
- [ ] **Test coverage > 90%** for all new code
- [ ] **All existing tests pass** - No regressions
- [ ] **Type hints on all public methods** - Maintainability
- [ ] **Comprehensive logging** - All critical operations logged
- [ ] **Network failures tested** - Chaos engineering tests pass
- [ ] **API downtime scenarios tested** - Degradation mode verified

### Safety Requirements
- [ ] **Emergency unwind cannot succeed without verification** - Enforced by return type
- [ ] **No silent exception handling** - All errors logged and surfaced
- [ ] **Position accumulation impossible** - Multiple safeguards prevent
- [ ] **Manual intervention still works** - close_positions.py script maintained
- [ ] **Feature flags allow instant rollback** - Zero-downtime rollback
- [ ] **Rate limiting prevents API abuse** - Token bucket enforcement
- [ ] **Circuit breaker prevents cascading failures** - Automatic isolation

### Performance Requirements
- [ ] **Normal UNWIND (IOC success): < 2 seconds** - No performance regression
- [ ] **IOC → MARKET fallback: < 10 seconds** - Acceptable for safety
- [ ] **Emergency unwind: < 35 seconds** - 30s verification timeout + 5s execution
- [ ] **Graceful recovery: < 40 seconds** - Both positions closed + verification
- [ ] **Rate limiting: 10 req/s with burst 20** - Prevents 429 errors
- [ ] **BBO freshness: < 2 seconds** - WebSocket or REST fallback

### Operational Requirements
- [ ] **Deployment requires zero config changes** - Drop-in replacement
- [ ] **Backward compatible with existing scripts** - No breaking changes
- [ ] **Feature flags enabled by default** - Safe defaults (true)
- [ ] **Emergency runbook available** - Ops team trained on procedures
- [ ] **Monitoring alerts defined** - Log patterns for alerting
- [ ] **Rollback procedures documented** - Step-by-step instructions
- [ ] **Network partition recovery tested** - Chaos engineering validated

---

## Risk Mitigation

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| OrderType.LIMIT doesn't exist | Use OrderType.DEFAULT with aggressive pricing | Verified DEFAULT works like LIMIT |
| MARKET order slippage | Limit to 50 bps (0.5%) via feature flag | Add max slippage config |
| Exchange API delays | 30s verification timeout | Increase to 60s if needed |
| Network errors | 5 retries with exponential backoff | Circuit breaker to halt |
| Position check failures | Poll until timeout, then halt | Manual close script |
| Test flakiness | Mock all external dependencies | Run tests multiple times |
| Deployment issues | Feature flags for all features | Instant rollback via env vars |
| Rate limit errors | Token bucket rate limiting | Adjust rate limit if needed |
| WebSocket BBO failures | REST fallback with validation | Force REST via feature flag |
| Circuit breaker false positives | Configurable thresholds | Adjust via environment variables |
| Partial fill miscalculation | Comprehensive test coverage | Manual verification in tests |
| API downtime | Graceful degradation modes | Manual halt if needed |

---

## Rollback Plan

### Immediate Rollback (Feature Flags)
If critical issues discovered after deployment:

```bash
# Disable all V2 features
export DN_USE_MARKET_FALLBACK=false
export DN_ENABLE_RATE_LIMITING=false
export DN_ENABLE_CIRCUIT_BREAKER=false
export DN_USE_WEBSOCKET_BBO=false

# Restart bot with V1 behavior
python DN_pair_eth_sol_nado.py --size 100 --iter 5
```

### Partial Rollback (Selective Features)
If specific features cause issues:

```bash
# Disable MARKET fallback only (keep rate limiting and circuit breaker)
export DN_USE_MARKET_FALLBACK=false

# Disable rate limiting only (use with caution)
export DN_ENABLE_RATE_LIMITING=false

# Disable circuit breaker only (use with caution)
export DN_ENABLE_CIRCUIT_BREAKER=false
```

### Code Rollback (Git Revert)
If feature flags insufficient:

```bash
cd /Users/botfarmer/2dex
git log --oneline -10  # Find commit before V2 changes
git revert <commit-hash>
git push
```

### Rollback Verification Steps
1. Check logs for "[FEATURE]" tags to confirm flags
2. Verify no "[MARKET]" orders if fallback disabled
3. Verify position verification still active
4. Monitor for position accumulation
5. Check emergency unwind frequency
6. Verify no 429 errors (if rate limiting disabled)

---

## Notes

### Critical Findings from V1 Review

1. **OrderType.LIMIT Does Not Exist**
   - Nado SDK only has: DEFAULT, FOK, IOC, POST_ONLY
   - V1 plan incorrectly assumed LIMIT exists
   - V2 uses DEFAULT with aggressive pricing

2. **Rate Limiting Was Missing**
   - V1 had no 429 error prevention
   - V2 adds token bucket rate limiting
   - Default: 10 req/s with burst 20

3. **WebSocket BBO Was Unvalidated**
   - V1 assumed WebSocket BBO always valid
   - V2 adds BBO quality checks and REST fallback
   - Prevents MARKET orders with stale prices

4. **Network Partitions Not Tested**
   - V1 had no failure scenario testing
   - V2 adds chaos engineering tests
   - Circuit breaker prevents cascading failures

5. **Feature Flags Were Missing**
   - V1 had no rollback mechanism
   - V2 adds environment variable controls
   - Enables instant rollback without code changes

6. **Partial Fills Not Addressed**
   - V1 assumed IOC always fills or doesn't fill
   - V2 handles partial fills correctly
   - MARKET orders sized for remaining quantity

7. **API Downtime Not Considered**
   - V1 had no exchange outage handling
   - V2 adds graceful degradation modes
   - Bot continues operation in DEGRADED mode

### Effort Estimate Justification

**V1 Estimate: 8-12 hours** (underestimated)
**V2 Estimate: 40-55 hours** (realistic)

**Reasons for increase:**
- SDK verification required (OrderType.LIMIT doesn't exist)
- Rate limiting infrastructure (token bucket, throttling)
- BBO validation system (quality checks, REST fallback)
- Circuit breaker implementation (state machine, testing)
- Feature flag system (environment variables, runtime checks)
- Partial fill handling (detection, calculation, sizing)
- API downtime resilience (health monitoring, degradation modes)
- Comprehensive testing (chaos engineering, failure scenarios)
- Documentation (runbooks, rollback procedures)

**Per-phase breakdown:**
- Phase 0-1 (Foundation): 8 hours
- Phase 2-3 (Reliability): 10 hours
- Phase 4-5 (Emergency + Flags): 7 hours
- Phase 6 (Partial Fills): 4 hours
- Phase 7 (Unwind Robustness): 5 hours
- Phase 8 (API Downtime): 4 hours
- Phase 9 (Testing): 12 hours
- Phase 10 (Documentation): 5 hours

**Total: 40-55 hours** (accounts for testing and debugging)

---

**Plan Version:** 2.0
**Created:** 2026-01-31
**Priority:** CRITICAL - Position accumulation is causing financial losses
**Estimated Effort:** 40-55 hours (5-7 full days)
**Dependencies:** Nado exchange API access for testing MARKET orders
**Status:** Ready for Critic review
