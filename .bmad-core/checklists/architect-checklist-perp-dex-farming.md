<!-- Powered by BMAD™ Core -->

# Architect Checklist: Perp DEX Point Farming Bot

**Version**: v0.1 (Initial - Pre-validation)
**Owner**: Architect Agent (Winston)
**Purpose**: Technical validation and implementation for point farming bots
**Scope**: API feasibility, architecture, implementation, QA, deployment

[[LLM: INITIALIZATION INSTRUCTIONS

This checklist is specifically for **Perp DEX Point Farming Bot** projects. It complements the standard architect-checklist.md with domain-specific validations.

**CRITICAL RULE**: **ALWAYS execute Phase 0 (API Feasibility) FIRST**, before any other architecture or implementation work. This Phase 0 prevents the "Lighter DEX 10-hour waste" scenario.

**EXECUTION ORDER**:
1. ✅ **Phase 0: API Feasibility** (THIS CHECKLIST - MANDATORY FIRST STEP)
2. ✅ Phase 1-3: Strategy work (PM handles, you may advise)
3. ✅ Phase 4-6: Implementation/QA/Deployment (THIS CHECKLIST)
4. ⚠️ Standard architect-checklist.md (if needed for general architecture validation)

**REQUIRED CONTEXT**:
Before proceeding, ensure you have:
- Master framework: perp-dex-farming-framework.md
- DEX name and API documentation URL
- Account credentials or ability to create test account
- PM's strategy selection (after Phase 2, before Phase 4)

**ARCHITECT FOCUS AREAS** (from 9-phase framework):
- ✅ **Phase 0: API Feasibility** (YOUR PRIMARY CRITICAL RESPONSIBILITY - 30-60 min)
- ✅ Phase 4: Implementation (3-5 days)
- ✅ Phase 5: QA (1-2 days)
- ✅ Phase 6: Deployment (1 day)

**PM HANDLES**:
- Phase 1: Strategy Research
- Phase 2: Python Backtesting
- Phase 3: PineScript Validation (optional)
- Phase 7: Post-Mortem
- Phase 8: Strategy Improvement

**VALIDATION APPROACH**:
For each phase:
1. **Evidence-Based** - All claims must be verifiable (API responses, test results)
2. **Document Blockers** - If API fails, stop immediately and report to user
3. **Systematic Testing** - Don't assume, test every critical endpoint
4. **Risk Assessment** - Consider what could go wrong in production

**EXECUTION MODE**:
Ask user which mode:
- **Quick Mode** (Phase 0 only, 30 min) - For initial API validation
- **Full Mode** (Phase 0 + 4-6, 5-8 days) - Complete implementation cycle]]

---

## ⚠️ PHASE 0: API FEASIBILITY CHECK (CRITICAL - 30-60 minutes)

[[LLM: ‼️ **THIS IS THE MOST CRITICAL PHASE** ‼️

**DO NOT SKIP THIS PHASE UNDER ANY CIRCUMSTANCES**

**Real-world failure case**:
- Lighter DEX Integration: 10 hours wasted implementing bot for Private Beta-only API
- Root cause: Skipped Phase 0, went directly to implementation
- Error discovered after 5 hours: "Error 21511: invalid tx type for account"
- Time wasted: 10 hours total → 0 working system

**If Phase 0 executed**:
- 30 minutes: API test → Private Beta blocker discovered
- Decision: NO-GO (switch to Hyperliquid)
- Time saved: 9.5 hours

**Your responsibility**:
- Test API access BEFORE any implementation
- Provide clear GO/NO-GO/CONDITIONAL-GO decision
- Document all access restrictions
- DO NOT proceed to Phase 4 if NO-GO

**Deliverable**:
- API Access Validation Report (see Section 0.6)
- GO → Proceed to Phase 4 (when PM provides strategy)
- CONDITIONAL → Proceed with documented workarounds
- NO-GO → STOP, recommend alternative DEX]]

### 0.1 Public Access Verification (10-15 min)

**Objective**: Confirm API is publicly accessible without special requirements

- [ ] **API Documentation Public Access**
  - Can you access API documentation without NDA or login? (Yes/No)
  - Are there public code examples and SDKs? (Yes/No)
  - Documentation URL: [Link]
  - Quality assessment: [Excellent / Good / Poor / Missing]

- [ ] **Beta/Waitlist Program Check** 🚨 **CRITICAL**
  - Is API in Private Beta, Alpha, or Closed Testing? (Yes/No)
  - Evidence: [Check official website, docs header, Discord announcements]
  - **RED FLAGS** (immediate NO-GO if found):
    - "Private Beta"
    - "Invite Only"
    - "Waitlist Required"
    - "Limited Access"
    - "Approved Accounts Only"
  - If red flag found → **STOP and report NO-GO immediately**

- [ ] **Account Type Requirements**
  - What account types can access API?
    - [ ] Retail (standard user)
    - [ ] Verified (KYC required)
    - [ ] Institutional (special application)
    - [ ] Geographic restrictions? (List countries if any)
  - Minimum requirements to access trading API: [Document]
  - Evidence source: [Terms of Service section, API docs prerequisites]

- [ ] **API Key Generation Test**
  - Can you generate API keys immediately? (Yes/No)
  - Verification steps before API access:
    - [ ] Email confirmation
    - [ ] KYC (ID verification)
    - [ ] 2FA setup
    - [ ] Waiting period? (X hours/days)
  - API key types available:
    - [ ] Read-only
    - [ ] Trading (spot/perp)
    - [ ] Withdrawal (usually not needed for bot)
  - Evidence: [Screenshot of API key settings page or documentation]

**Decision Point 1**:
- ✅ If all checks pass → Proceed to 0.2
- ❌ If Private Beta detected → **STOP, report NO-GO**
- ⚠️ If KYC/verification required → **CONDITIONAL** (document delay)

### 0.2 Functionality Scope Validation (10-15 min)

**Objective**: Confirm required API endpoints are available for your account type

- [ ] **Required Endpoints Inventory**
  Based on bot type (from PM's strategy selection):

  **🚨 CRITICAL: Futures/Perpetual API (NOT Spot)**:
  - [ ] `/futures/account` or equivalent (futures account balance)
  - [ ] `/futures/positions` or equivalent (perpetual positions, not spot)
  - [ ] `/futures/orders/create` or equivalent (futures order placement)
  - [ ] `/futures/orders/cancel` or equivalent (cancel futures order)
  - [ ] `/futures/markets` or equivalent (perpetual trading pairs, specs)
  - [ ] `/futures/leverage` or equivalent (set leverage per position)

  **Margin Mode Selection** 🔴 **MANDATORY**:
  - [ ] Cross margin available? (Yes/No)
  - [ ] Isolated margin available? (Yes/No)
  - [ ] **DEFAULT SELECTION: ISOLATED MARGIN (REQUIRED)**
    - Rationale:
      - ✅ Risk isolation (one position liquidation doesn't affect others)
      - ✅ Clear loss limit per position
      - ✅ Safe for multi-strategy bots (each strategy isolated)
      - ✅ Prevents cascading liquidations
    - API endpoint: [/futures/marginType or /futures/positionMode]
    - Test: Verify isolated margin can be set via API
  - Evidence: [API docs section on margin modes]

  **For All Bots**:
  - [ ] `/futures/balance` (futures wallet balance)
  - [ ] `/futures/positions` (current open positions)
  - [ ] `/futures/orders/create` (place futures order - market/limit)
  - [ ] `/futures/orders/cancel` (cancel order)
  - [ ] `/futures/leverage` (set leverage: 1x-100x typically)

  **For Trend-Following Bots**:
  - [ ] WebSocket futures market data (OHLCV, trades for BTC-PERP, ETH-PERP)
  - [ ] Stop loss / take profit order support (conditional orders)
  - [ ] Leverage adjustment per position

  **For Volume Bots**:
  - [ ] High-frequency order placement (Grid/MM need many orders)
  - [ ] Batch order creation (if available - 10x efficiency boost)
  - [ ] WebSocket futures order book feed (for MM strategy)
  - [ ] Maker/taker fee structure (check for maker rebates)

- [ ] **Endpoint Availability Check**
  - For EACH required endpoint above, check documentation:
    - Endpoint exists? (Yes/No)
    - Available for your account type? (Yes/No/Unknown)
    - Evidence: [Link to API docs section]

- [ ] **Read vs Write Access Verification**
  - Does generated API key have write (trading) permission? (Yes/No)
  - Are there separate permission levels?
  - Evidence: [API key permissions settings]

- [ ] **WebSocket/Streaming Access**
  - Real-time market data available? (Yes/No)
  - Real-time account updates (order fills, position changes)? (Yes/No)
  - Separate subscription fees or tiers? (Document if any)
  - Evidence: [WebSocket documentation link]

- [ ] **API Feature Discovery** 🔍 **IMPORTANT**
  **Objective**: Discover advanced features beyond basic trading to optimize bot performance

  **조사 항목** (API docs 전체 스캔):

  **Order Management**:
  - [ ] Batch orders (multiple orders in one API call)
    - Benefit: 10x efficiency for Grid/MM bots
    - Example: Place 50 grid orders in 1 request vs 50 requests
  - [ ] Conditional orders (Stop-Limit, OCO, Trailing Stop)
    - Benefit: Native stop-loss without bot monitoring
  - [ ] Position hedging (양방향 포지션 허용)
    - Benefit: Advanced strategies (long + short same pair)

  **Risk & Liquidation**:
  - [ ] Auto-deleveraging (ADL) info API
    - Benefit: Predict liquidation queue position
  - [ ] Liquidation price calculator API
    - Benefit: Real-time liquidation price without manual calc
  - [ ] Insurance fund info
    - Benefit: Assess exchange safety

  **Funding & Fees**:
  - [ ] Funding rate history API
    - Benefit: DN strategy optimization (historical funding arbitrage)
  - [ ] Fee tier discounts (volume-based)
    - Benefit: Reduce costs at higher volumes
  - [ ] Maker rebate program
    - Benefit: Negative fees for MM strategy

  **Data & Analytics**:
  - [ ] Historical trades API (본인 거래내역)
    - Benefit: Post-mortem analysis, performance tracking
  - [ ] Mark price vs index price API
    - Benefit: Better entry/exit timing
  - [ ] Open interest API
    - Benefit: Market sentiment analysis

  **Other**:
  - [ ] Referral/affiliate API
    - Benefit: Additional revenue stream
  - [ ] Testnet/sandbox environment
    - Benefit: Safe testing before production

  **추천 기능 (봇 타입별)**:
  ```yaml
  Trend-Following:
    필수: Conditional orders (Stop-Loss 자동화)
    권장: Historical trades (성과 분석)
    선택: Mark price API (entry/exit 최적화)

  Grid Trading:
    필수: Batch orders (효율성 10배)
    권장: Fee tier info (비용 최적화)
    선택: Testnet (전략 테스트)

  Market Making:
    필수: Batch orders + Maker rebate info
    권장: Order book WebSocket depth
    선택: Position hedging (advanced MM)

  Delta Neutral:
    필수: Funding rate API (arbitrage 최적화)
    권장: Mark price API (rebalance 타이밍)
    선택: Historical funding (백테스팅 정확도)
  ```

  **문서화**:
  - 발견된 기능: [List all available features]
  - 봇에 적용할 기능: [Select based on bot type]
  - 구현 우선순위: [Critical / High / Medium / Low]

**Decision Point 2**:
- ✅ If all required endpoints available → Proceed to 0.3
- ❌ If critical endpoint missing (e.g., can't place futures orders) → **STOP, report NO-GO**
- ⚠️ If some nice-to-have missing (e.g., batch orders) → **CONDITIONAL** (document limitation)
- 📝 Advanced features discovered → Document for Phase 4 implementation

### 0.3 Community Validation (10-15 min)

**Objective**: Learn from real users before investing development time

- [ ] **Community Channel Access**
  - Official Discord joined: (Yes/No) → [Link]
  - Official Telegram joined: (Yes/No) → [Link]
  - Other communities (Reddit, Twitter): [List]

- [ ] **Search for Bot/Automation Success Stories**
  - Search keywords: "API", "trading bot", "automation", "script", "[DEX name] bot"
  - Found successful bot users: [Count, e.g., "5+ users confirmed"]
  - Evidence: [Discord message links, GitHub repos, blog posts]
  - Confidence level: [High / Medium / Low]

- [ ] **Known Issues Research**
  - Search for: "API error", "bug", "issue", "not working"
  - Common error codes found: [List, e.g., "21511", "21109"]
  - Known API limitations: [Document]
  - Workarounds mentioned: [Document if any]
  - Evidence: [Discord FAQ, GitHub issues, support tickets]

- [ ] **Open-Source Examples**
  - GitHub repositories using this API: [Count, links]
  - Code quality/recency: [Assessment]
  - Can use as reference: (Yes/No)

**Decision Point 3**:
- ✅ If 3+ success stories found → High confidence, proceed to 0.4
- ⚠️ If 1-2 success stories → Medium confidence, proceed with caution
- ❌ If 0 success stories + known blockers → **STOP, report NO-GO or CONDITIONAL**

### 0.4 Technical Quick Test (15-20 min) 🚨 **MOST CRITICAL**

**Objective**: Perform ACTUAL API calls to validate access BEFORE implementation

[[LLM: This is where the Lighter DEX failure would have been caught. Always execute real API calls. Do not skip this section.]]

- [ ] **Authentication Test**
  - API keys generated: (Yes/No)
  - Test authentication endpoint (e.g., `/account` GET request):
    ```bash
    # Example using curl (adapt to DEX API)
    curl -X GET "https://api.[dex].com/account" \
      -H "API-Key: YOUR_KEY" \
      -H "API-Secret: YOUR_SECRET"
    ```
  - **Result**:
    - ✅ Success: [HTTP 200, account data returned]
    - ❌ Failure: [Error code, message]
  - Evidence: [Paste successful response or error]

- [ ] **Basic Read Operation Test**
  - Endpoint tested: [e.g., `/markets`, `/account/balance`]
  - Test command:
    ```bash
    curl -X GET "https://api.[dex].com/markets"
    ```
  - **Result**:
    - ✅ Success: [Data returned, format looks correct]
    - ❌ Failure: [Error details]
  - Response sample: [Paste first few lines]

- [ ] **Critical Write Operation Test** 🚨 **BLOCKER CHECK**
  - **USE TESTNET/PAPER TRADING IF AVAILABLE**
  - If no testnet, use MINIMUM order size on mainnet

  - Endpoint tested: [e.g., `/order/create`]
  - Test order parameters:
    ```json
    {
      "symbol": "BTC/USDT",
      "side": "buy",
      "type": "limit",
      "quantity": 0.001,  // MINIMUM
      "price": [far from market, won't fill]
    }
    ```
  - **Result**:
    - ✅ Success: Order placed (ID: [order_id])
    - ❌ Failure: [Error code, message]

  - **If failure, analyze error code**:
    - Error 21511 ("invalid tx type for account") → **Private Beta blocker, NO-GO**
    - Error 21109 ("api key not found") → **Account not approved, NO-GO**
    - Error 429 ("rate limit") → Retry with delay
    - Other errors: [Investigate, determine if blocker]

- [ ] **Order Cancellation Test** (if previous test succeeded)
  - Cancel test order: [Command]
  - **Result**: ✅ Success / ❌ Failure
  - Evidence: [Response]

**Decision Point 4** (FINAL GO/NO-GO):
- ✅ **GO** if:
  - Authentication: ✅
  - Read operations: ✅
  - Write operations (order placement): ✅
  - No Private Beta errors
  → **Proceed to 0.5**

- ❌ **NO-GO** if:
  - Error 21511, 21109, or similar "account not authorized" errors
  - Write operations fail due to account restrictions
  - Private Beta blocker confirmed
  → **STOP, create report (0.6), recommend alternative DEX**

- ⚠️ **CONDITIONAL-GO** if:
  - Minor issues (rate limits, non-critical endpoints unavailable)
  - Workarounds available
  → **Proceed to 0.5, document limitations**

### 0.5 Rate Limits and Constraints (5-10 min)

**Objective**: Understand operational constraints for architecture design

- [ ] **API Rate Limit Documentation**
  - Requests per second (RPS): [X]
  - Requests per minute (RPM): [X]
  - Scope: Per IP, per API key, per account?
  - Evidence: [API docs rate limit section]

- [ ] **Rate Limit Behavior**
  - What happens when exceeded?
    - [ ] HTTP 429 error (rate limit exceeded)
    - [ ] Temporary IP ban (duration: [X min/hour])
    - [ ] Account suspension (rare but document if possible)
  - Backoff strategy recommended: [Exponential, fixed delay, etc.]

- [ ] **WebSocket Connection Limits**
  - Max concurrent connections: [X]
  - Max subscriptions per connection: [X]
  - Message rate limit: [X messages/sec]
  - Evidence: [WebSocket docs]

- [ ] **Order Limits**
  - Max open orders: [X]
  - Min/max order size: [X to Y]
  - Max position size: [X] (if applicable)

- [ ] **Data Access Restrictions**
  - Historical data: [Real-time / 15-min delayed / Not available]
  - OHLCV candle limits: [X candles per request, Y lookback period]
  - Order book depth: [L1 (top) / L2 (partial) / L3 (full)]

**Architecture Implications** (document for Phase 4):
- Rate limits will require: [Request queueing / Throttling / Batching]
- WebSocket strategy: [Single connection / Multiple / Reconnect logic]
- Data caching: [Cache OHLCV for X minutes to reduce API calls]

### 0.6 Communication Protocol Decision (10-15 min) 🎯 **CRITICAL**

**Objective**: Choose REST vs WebSocket based on bot type and strategy requirements

[[LLM: This decision impacts entire architecture. Use the predefined guide below to make optimal choice early.]]

#### Bot Type Communication Protocol Guide

| Bot Type | Strategy | Update Freq | **Primary Protocol** | Secondary | Rationale |
|----------|----------|-------------|---------------------|-----------|-----------|
| **Trend-Following** | MA Crossover | Real-time | ✅ **WebSocket** | REST fallback | Golden/Death Cross needs instant detection |
| **Trend-Following** | MACD, RSI | Real-time | ✅ **WebSocket** | REST fallback | Divergence requires continuous monitoring |
| **Volume** | Grid Trading | 15m-1h | ✅ **REST** | WS optional | Periodic rebalancing sufficient |
| **Volume** | Market Making | Real-time | ✅ **WebSocket** + REST | N/A | WS for order book, REST for orders |
| **Volume** | Delta Neutral | 15m-1h | ✅ **REST** | WS optional | Periodic hedge ratio check |
| **Hybrid** | Trend + Volume | Variable | ✅ **Hybrid** (WS+REST) | N/A | Both components needed |

#### Decision Checklist

- [ ] **Identify Bot Type & Strategy**
  - Bot type: [Trend-Following / Grid / MM / DN / Hybrid]
  - Strategy: [MA Cross / MACD / Grid / MM / DN / Other]
  - From: PM's Phase 2 strategy selection

- [ ] **Determine Update Frequency Requirement**
  - Strategy update frequency: [Real-time / 1-5min / 15min-1h / >1h]
  - Critical latency: [<1s / <5s / <30s / <1min / >1min]
  - Signal response time: [Instant / Fast / Moderate / Slow]

- [ ] **Protocol Selection (Based on Guide)**
  - **If Real-time (<5 min updates)**: → **WebSocket Primary**
  - **If Periodic (>15 min updates)**: → **REST Primary**
  - **If MM Strategy**: → **WebSocket + REST Hybrid**

- [ ] **Validate Protocol Availability** (from Section 0.2)
  - WebSocket available? (Yes/No)
  - WebSocket stable? (Test 12h uptime in Section 0.4)
  - REST rate limits acceptable? (From Section 0.5)
  - Decision influenced by availability:
    - If WebSocket preferred but unstable → Use REST with shorter polling
    - If REST preferred but rate limited → Use WebSocket

#### Protocol Specifications

**WebSocket (Real-time Strategies)**

**When to Use**:
- ✅ Update frequency < 5 minutes
- ✅ Order book depth needed (MM strategy)
- ✅ Instant signal response critical (Trend-following)
- ✅ WebSocket API stable (validated in Section 0.4)

**Requirements**:
- Stable connection (>95% uptime over 12h test)
- Auto-reconnect with exponential backoff (3s → 6s → 12s → ...)
- Message rate limit acceptable (check Section 0.5)
- State management (track connection status, resubscribe on reconnect)

**Data Types**:
- Market data: `futures/ticker`, `futures/candles`, `futures/trades`
- Order book: `futures/orderbook` (for MM bots)
- Account updates: `futures/orders`, `futures/positions`

**Architecture Components Needed**:
- WebSocket manager (connection, reconnect, subscriptions)
- Message queue (buffer during reconnect)
- Heartbeat/ping mechanism (keep-alive)

**Trade-offs**:
- ✅ Pros: Real-time, low latency (<100ms), push-based, efficient
- ❌ Cons: Complex reconnect logic, state management, debugging harder

---

**REST (Periodic Strategies)**

**When to Use**:
- ✅ Update frequency > 15 minutes
- ✅ Simple OHLCV data sufficient (no order book depth)
- ✅ WebSocket unstable or unavailable
- ✅ Simpler implementation preferred

**Requirements**:
- Acceptable rate limits (>10 requests/min for bot operation)
- Reasonable latency (<500ms per request)
- Polling interval respects rate limits

**Endpoints Used**:
- Market data: `GET /futures/candles`, `GET /futures/ticker`
- Account: `GET /futures/positions`, `GET /futures/balance`
- Orders: `POST /futures/orders`, `DELETE /futures/orders/{id}`

**Architecture Components Needed**:
- Polling scheduler (asyncio timer or cron)
- Request queue (rate limit management)
- Response caching (reduce redundant calls)

**Trade-offs**:
- ✅ Pros: Simple, stateless, reliable, easier debugging
- ❌ Cons: Polling overhead, not real-time, higher latency (500ms-5s)

---

**Hybrid (Advanced - MM Bots)**

**When to Use**:
- ✅ Market Making strategy (order book depth + order placement)
- ✅ Need both real-time data AND control operations
- ✅ Want best of both worlds

**Pattern**:
- **WebSocket**: Real-time order book depth, market data
- **REST**: Order placement, cancellation, position queries
- **Rationale**: WebSocket for data (continuous), REST for control (occasional)

**Example Flow**:
```
WebSocket: Order book updates (100ms intervals)
     ↓
Strategy Engine: Calculate optimal bid/ask spread
     ↓
REST: Place/update orders (as needed, <10 req/min)
```

**Architecture Components Needed**:
- All WebSocket components (manager, queue, reconnect)
- All REST components (rate limiter, request queue)
- Coordination layer (sync WS data with REST actions)

**Trade-offs**:
- ✅ Pros: Optimal performance, real-time data with reliable control
- ❌ Cons: Most complex, highest development/maintenance cost

---

#### Final Decision

- [ ] **Selected Protocol**: [WebSocket / REST / Hybrid]

- [ ] **Rationale**:
  ```
  Bot Type: [e.g., Trend-Following]
  Strategy: [e.g., MA Crossover 50/200]
  Update Frequency: [e.g., Real-time]
  Decision: WebSocket Primary
  Reason: Golden Cross detection requires instant price updates (<1s latency)
  Fallback: REST polling every 30s if WebSocket fails
  ```

- [ ] **Architecture Implications for Phase 4**:
  - Components to implement: [List based on protocol]
  - Expected latency: [e.g., <100ms for WS, <500ms for REST]
  - Data caching strategy: [How to cache data]
  - Error handling: [Reconnect for WS, retry for REST]

- [ ] **Document in API Report (Section 0.7)**:
  - Include protocol decision in final GO/NO-GO report
  - Pass to Phase 4 implementation team

### 0.7 Phase 0 Deliverable: GO/NO-GO Decision Report

[[LLM: Create this report and present to user immediately after completing Sections 0.1-0.5]]

**Template**:

```markdown
# API Access Validation Report: [DEX Name]
**Date**: [YYYY-MM-DD]
**Architect**: Winston
**Project**: [Bot Name, e.g., "Lighter Point Farming Bot"]

---

## Executive Summary

**Decision**: ✅ GO / ⚠️ CONDITIONAL GO / ❌ NO-GO

**Confidence**: High / Medium / Low

**Critical Blockers**: [None] OR [List blockers]

**Recommended Next Step**:
- If GO: Proceed to Phase 4 implementation after PM provides strategy
- If CONDITIONAL: Proceed with documented workarounds
- If NO-GO: [Switch to alternative DEX: Hyperliquid / dYdX / etc.]

---

## Detailed Findings

### 0.1 Public Access
- **Account Type**: [Retail / Verified / Institutional]
- **Beta Status**: [Public / Private Beta / N/A]
- **API Key Generated**: ✅ Yes / ❌ No
- **Blockers**: [None] OR [List]

### 0.2 Functionality Scope
- **API Type**: ✅ Futures/Perpetual API (NOT Spot)
- **Margin Mode**: ✅ Isolated (default) / Cross (available)
- **Required Endpoints Available**: [X/Y available]
- **Write Access**: ✅ Yes / ❌ No
- **WebSocket Available**: ✅ Yes / ❌ No / ⚠️ Limited

**Advanced Features Discovered**:
- Batch orders: [Yes/No]
- Conditional orders: [Yes/No]
- Funding rate API: [Yes/No]
- Historical trades: [Yes/No]
- [Other features found]

**Missing Features**: [None] OR [List]

### 0.3 Community Validation
- **Success Stories Found**: [Count]
- **Evidence**: [Links to Discord messages, GitHub repos, etc.]
- **Known Issues**: [None] OR [List with workarounds]
- **Confidence from Community**: High / Medium / Low

### 0.4 Technical Testing
**Authentication**:
- ✅ Success OR ❌ Failed ([Error code])

**Read Operations**:
- ✅ Success OR ❌ Failed ([Error code])

**Write Operations** (ORDER PLACEMENT TEST):
- ✅ Success: Order ID [12345] placed and cancelled
- ❌ Failed: [Error code, error message]
  - **If Error 21511 / 21109**: Private Beta blocker, NO-GO

**Test Evidence**:
```json
// Paste successful API response or error
{
  "orderId": "12345",
  "status": "open",
  ...
}
```

### 0.5 Rate Limits & Constraints
- **API Rate Limits**: [X RPS, Y RPM]
- **WebSocket Limits**: [X connections, Y subscriptions]
- **Order Limits**: [Min: A, Max: B, Max open: C]
- **Data Access**: [Real-time / Delayed / Restricted]

**Architecture Implications**:
- [e.g., "Need request throttling to stay under 10 RPS"]
- [e.g., "WebSocket reconnect logic required (unstable connection observed)"]

### 0.6 Communication Protocol Decision
- **Bot Type**: [Trend-Following / Grid / MM / DN / Hybrid]
- **Strategy**: [MA Cross / MACD / Grid / MM / DN]
- **Update Frequency**: [Real-time / 15m-1h / Other]
- **Selected Protocol**: ✅ WebSocket / REST / Hybrid
- **Rationale**: [Brief explanation based on bot type guide]
- **Fallback**: [Secondary protocol if primary fails]

**Components to Implement** (Phase 4):
- [e.g., "WebSocket manager with auto-reconnect"]
- [e.g., "REST API rate limiter (10 req/min max)"]
- [e.g., "Message queue for reconnect buffering"]

---

## Recommendations

### If GO ✅
1. Proceed to Phase 4 implementation when PM provides final strategy
2. **Communication Protocol**: [WebSocket / REST / Hybrid] selected
3. Architecture considerations:
   - Protocol implementation: [Components needed]
   - Rate limit handling: [Strategy]
   - WebSocket management: [If applicable]
   - Advanced features to use: [Batch orders, conditional orders, etc.]
   - Error handling: [For known issues]

### If CONDITIONAL GO ⚠️
1. Proceed with following workarounds:
   - [Workaround 1: e.g., "Use polling instead of WebSocket for X data"]
   - [Workaround 2: ...]
2. Document limitations in architecture.md
3. Inform user of constraints

### If NO-GO ❌
1. **DO NOT proceed with implementation**
2. Recommended alternatives:
   - Hyperliquid (reason: [Public API, proven bot support])
   - dYdX (reason: [Institutional-grade API])
   - [Other DEX]
3. Estimated time to pivot: [X hours to set up new DEX account + re-run Phase 0]

---

## Time Investment

- Phase 0 execution time: [X minutes]
- Time saved by early detection: [Estimated, e.g., "Avoided 10-hour implementation waste (Lighter case)"]

---

## Next Steps

1. **If GO**: Await PM's Phase 2 strategy selection, then proceed to Phase 4
2. **If CONDITIONAL**: Document workarounds, proceed with caution
3. **If NO-GO**: Present alternative DEX options to user for decision

---

**Report End**
```

**Action**: Present this report to user and await decision before any further work.

---

## PHASE 4: IMPLEMENTATION (3-5 days)

[[LLM: Only execute Phase 4 if Phase 0 resulted in GO or CONDITIONAL-GO.

Prerequisites:
- Phase 0: API validated (GO/CONDITIONAL)
- Phase 1-2: PM provided final strategy selection (e.g., "BTC 1h MA Crossover 2x leverage")
- Phase 3: (Optional) PineScript validation done

Your task: Implement working bot based on PM's strategy spec.]]

### 4.1 Architecture Design (1 day)

**Objective**: Design bot architecture aligned with strategy requirements

- [ ] **Strategy Requirements Review**
  - Strategy type: [Trend-Following / Grid / MM / DN / Hybrid]
  - Required indicators: [e.g., MA(50), MA(200), RSI(14)]
  - Timeframe: [e.g., 1h]
  - Entry/exit rules: [Document logic from PM's spec]
  - Risk management: [Leverage: 2x, Stop Loss: 2%, Position size: 95%]

- [ ] **Core Components Definition**

  **1. Price Monitor Component**:
  - Responsibility: Fetch real-time market data
  - Data source: [WebSocket / REST polling / Hybrid]
  - Outputs: Current price, OHLCV history, order book (if needed)
  - Update frequency: [e.g., Real-time via WebSocket]

  **2. Strategy Engine Component**:
  - Responsibility: Calculate indicators, generate BUY/SELL/HOLD signals
  - Inputs: Price data from Price Monitor
  - Logic: [PM's strategy algorithm]
  - Outputs: Signal (BUY/SELL/HOLD), entry price, quantity
  - State tracking: Current position, unrealized P&L

  **3. Order Executor Component**:
  - Responsibility: Place, cancel, modify orders
  - Inputs: Signals from Strategy Engine
  - API integration: [DEX API order endpoints]
  - Order types: [Market / Limit / Stop-Loss]
  - Retry logic: Handle API errors, rate limits

  **4. Risk Manager Component**:
  - Responsibility: Enforce risk limits, prevent catastrophic loss
  - Checks:
    - Position size limits (max $ per position)
    - Leverage limits (max leverage per strategy)
    - Stop loss enforcement (auto-close if SL hit)
    - Drawdown monitoring (kill switch if MDD > threshold)
  - Kill switch: Emergency shutdown mechanism

- [ ] **Data Flow Diagram**
  ```
  [WebSocket] → Price Monitor → Strategy Engine → Risk Manager → Order Executor → [DEX API]
                      ↓                                ↓
                [Historical Cache]            [Position State DB]
  ```
  - Document: Which component talks to which, what data is passed

- [ ] **Technology Stack Selection**
  - Language: [Python (recommended for backtesting alignment)]
  - Libraries:
    - WebSocket: [`websockets`, `ccxt` (if supported)]
    - Indicators: [`pandas`, `ta-lib`, `pandas-ta`]
    - API client: [Official SDK if available, or `requests` + custom]
  - Database (if needed): [SQLite for logs, Redis for state, or in-memory]
  - Logging: [`logging` module, file-based]

- [ ] **Error Handling Strategy**
  - WebSocket disconnection: Auto-reconnect with exponential backoff
  - API errors:
    - 429 (rate limit): Retry after delay
    - 500 (server error): Retry with backoff, alert user if persistent
    - 4xx (client error): Log and alert, may indicate bug
  - Strategy errors: Invalid signal → Log and skip (no trade)
  - Risk Manager override: Always log and alert user

- [ ] **Configuration Management**
  - Config file format: [YAML / JSON / .env]
  - Config parameters:
    - API keys (secure storage)
    - Strategy parameters (leverage, SL, timeframe)
    - Risk limits (max position, max drawdown)
    - Operational (log level, WebSocket URL)

**Deliverable**: **Architecture Document** (architecture.md)
```markdown
# Bot Architecture: [Bot Name]

## System Overview
[Diagram]

## Components
### 1. Price Monitor
- **Tech**: WebSocket (ccxt + websockets)
- **Data**: BTC/USDT 1h OHLCV
- **Update**: Real-time

### 2. Strategy Engine
- **Algorithm**: MA Crossover (50/200)
- **Indicators**: pandas-ta
- **State**: In-memory dict

### 3. Order Executor
- **API**: [DEX] REST API
- **Orders**: Market + Stop-Loss
- **Retry**: 3 attempts with 2s delay

### 4. Risk Manager
- **Max Position**: $1,900 (95% of $2K)
- **Stop Loss**: 2% (auto-close)
- **Kill Switch**: Manual via keyboard interrupt

## Data Flow
[Detailed flow description]

## Error Handling
[Strategies for each error type]

## Configuration
[Config file structure]
```

### 4.2 Core Implementation (2-3 days)

**Objective**: Implement all components

[[LLM: Guide user through implementation if they are coding, or implement yourself if user requests. Follow architecture from 4.1 strictly.]]

- [ ] **Price Monitor Implementation**
  - [ ] WebSocket connection setup
  - [ ] Auto-reconnect logic (exponential backoff)
  - [ ] Real-time price updates
  - [ ] Historical data caching (for indicator calculation)
  - [ ] Testing: Can retrieve current price + last 200 candles

- [ ] **Strategy Engine Implementation**
  - [ ] Indicator calculation (MA, MACD, RSI, etc. per PM spec)
  - [ ] Signal generation logic (PM's entry/exit rules)
  - [ ] Position state tracking
  - [ ] Testing: Indicators match backtest values, signals correct

- [ ] **Order Executor Implementation**
  - [ ] Order placement (market, limit, stop-loss)
  - [ ] Order cancellation
  - [ ] Position management (close, update SL)
  - [ ] API error handling and retries
  - [ ] Testing: Can place order, cancel order, query position

- [ ] **Risk Manager Implementation**
  - [ ] Position size validation (before order)
  - [ ] Leverage validation
  - [ ] Stop loss enforcement (monitor position, close if SL hit)
  - [ ] Drawdown monitoring (rolling MDD calculation)
  - [ ] Kill switch (emergency stop, close all positions)
  - [ ] Testing: Rejects oversized orders, auto-closes at SL

- [ ] **Logging System**
  - [ ] Log file setup (logs/bot.log)
  - [ ] Log levels: DEBUG, INFO, WARNING, ERROR
  - [ ] Log rotation (daily or size-based)
  - [ ] Log all: Signals, orders, fills, errors, state changes

- [ ] **Configuration System**
  - [ ] Load config from file (.env or config.yaml)
  - [ ] Validate config (required fields present, types correct)
  - [ ] Secure API key storage (not hardcoded)

**Code Quality Checks**:
- [ ] Code structured into modules (one file per component)
- [ ] Functions documented (docstrings)
- [ ] Error handling in all API calls
- [ ] No hardcoded values (use config)
- [ ] Type hints (if Python 3.6+)

**Deliverable**: **Working Bot Code** (main.py + modules)

### 4.3 Paper Trading Validation (1 day)

**Objective**: Validate bot with virtual balance before risking real money

- [ ] **Paper Trading Mode Setup**
  - [ ] Virtual balance: $10,000 (or similar)
  - [ ] Simulate order fills (market orders fill at current price)
  - [ ] Track virtual position and P&L
  - [ ] No real API orders placed

- [ ] **Run Bot for 24-48 hours**
  - [ ] Start bot in paper trading mode
  - [ ] Monitor logs for errors
  - [ ] Observe strategy signals and simulated trades
  - [ ] Check for crashes, hangs, memory leaks

- [ ] **Validation Checks**
  - [ ] Bot runs continuously without crashes
  - [ ] Strategy signals match expected logic
  - [ ] Risk Manager enforces limits (test with manual SL trigger)
  - [ ] WebSocket reconnects successfully after manual disconnect
  - [ ] Error handling works (test with API downtime simulation)

- [ ] **Bug Fixes**
  - [ ] Document all bugs found: [List]
  - [ ] Fix critical bugs (crashes, wrong signals)
  - [ ] Re-test after fixes

- [ ] **Paper Trading Results**
  - Virtual P&L: $[±X]
  - Signals generated: [N]
  - Trades simulated: [N]
  - Issues found: [List]
  - Readiness assessment: Ready / Needs more testing

**Deliverable**: **Paper Trading Log** + **Bug Fix Report**

---

## PHASE 5: QA (QUALITY ASSURANCE) (1-2 days)

[[LLM: Comprehensive testing before production deployment. Do not skip this phase for bots with >$500 capital.]]

### 5.1 Unit Testing (0.5 day)

**Objective**: Test individual components in isolation

- [ ] **Price Monitor Tests**
  - [ ] Test: WebSocket connection and data parsing
  - [ ] Test: Auto-reconnect after disconnect
  - [ ] Test: Historical data caching (correct data returned)
  - [ ] Coverage: Key functions tested

- [ ] **Strategy Engine Tests**
  - [ ] Test: Indicator calculation (MA, MACD, etc.)
  - [ ] Test: Signal generation (BUY/SELL/HOLD logic)
  - [ ] Test: Edge cases (no data, invalid data, extreme values)
  - [ ] Coverage: All entry/exit conditions tested

- [ ] **Order Executor Tests**
  - [ ] Test: Order formatting (correct API request structure)
  - [ ] Test: Error handling (429, 500, etc.)
  - [ ] Test: Retry logic (retries correct number of times)

- [ ] **Risk Manager Tests**
  - [ ] Test: Position size limit enforcement
  - [ ] Test: Stop loss trigger (simulated price drop)
  - [ ] Test: Kill switch activation
  - [ ] Coverage: All risk scenarios tested

**Testing Framework**: [pytest / unittest / manual]

**Deliverable**: **Unit Test Suite** (test_*.py files) + **Test Results Report**

### 5.2 Integration Testing (0.5 day)

**Objective**: Test end-to-end bot operation

- [ ] **Scenario 1: Normal Operation**
  - Price update → Indicator calculation → Signal → Order placement → Fill
  - Expected: All components work together smoothly
  - Result: ✅ Pass / ❌ Fail ([Details])

- [ ] **Scenario 2: WebSocket Disconnect/Reconnect**
  - Simulate: Kill WebSocket connection mid-operation
  - Expected: Auto-reconnect within 30s, no data loss
  - Result: ✅ Pass / ❌ Fail

- [ ] **Scenario 3: API Errors (Rate Limit)**
  - Simulate: Rapid API calls to trigger 429 error
  - Expected: Bot throttles requests, retries after delay
  - Result: ✅ Pass / ❌ Fail

- [ ] **Scenario 4: Stop Loss Trigger**
  - Simulate: Price drops to SL level
  - Expected: Risk Manager closes position automatically
  - Result: ✅ Pass / ❌ Fail

- [ ] **Scenario 5: Emergency Shutdown**
  - Simulate: User triggers kill switch (Ctrl+C)
  - Expected: Bot closes all positions gracefully, saves state
  - Result: ✅ Pass / ❌ Fail

**Deliverable**: **Integration Test Report** (scenarios + results)

### 5.3 Stress Testing (0.5 day)

**Objective**: Validate bot under extreme conditions

- [ ] **High Volatility Simulation**
  - Simulate: Price moves ±10% in 1 minute
  - Expected: Bot handles rapid signal changes without crashing
  - Result: ✅ Pass / ❌ Fail

- [ ] **High Frequency Signals**
  - Simulate: Strategy generates 100+ signals in 1 hour
  - Expected: Bot processes all signals, respects rate limits
  - Result: ✅ Pass / ❌ Fail

- [ ] **API Rate Limit Testing**
  - Test: Intentionally exceed rate limits
  - Expected: Bot throttles, queues requests, no failed orders
  - Result: ✅ Pass / ❌ Fail

- [ ] **Memory Leak Testing**
  - Test: Run bot for 24+ hours, monitor RAM usage
  - Expected: Memory usage stable (<500MB growth over 24h)
  - Result: ✅ Pass / ❌ Fail ([Memory usage: X MB → Y MB])

- [ ] **Prolonged Operation Test**
  - Test: Run bot for 48+ hours continuously
  - Expected: No crashes, no degraded performance
  - Result: ✅ Pass / ❌ Fail

**Deliverable**: **Stress Test Report**

### 5.4 QA Sign-Off

**Objective**: Final production readiness assessment

- [ ] **All Tests Passed**
  - Unit tests: ✅ Pass rate [X%]
  - Integration tests: ✅ All scenarios pass
  - Stress tests: ✅ All conditions handled

- [ ] **Known Issues Documented**
  - Critical issues: [None] OR [List with workarounds]
  - Non-critical issues: [List]

- [ ] **Production Readiness Checklist**
  - [ ] Code reviewed (if team project)
  - [ ] Logs configured (appropriate level, rotation)
  - [ ] Config validated (no test API keys, correct parameters)
  - [ ] Error alerts configured (Discord/Telegram/Email)
  - [ ] Backup plan documented (what if bot fails)

**Decision**:
- ✅ **Production Ready**: Proceed to Phase 6 deployment
- ⚠️ **Conditional**: Minor issues, deploy to Stage 1 ($100) with monitoring
- ❌ **Not Ready**: Fix critical issues, re-test

**Deliverable**: **QA Sign-Off Document**

---

## PHASE 6: DEPLOYMENT (1 day + ongoing monitoring)

[[LLM: Safe staged rollout to minimize risk. Start small, scale gradually.]]

### 6.1 Staged Rollout Plan (1 day setup, 1-2 weeks execution)

**Objective**: Incremental capital deployment with validation gates

- [ ] **Stage 1: $100 Capital (1-3 days)**
  - **Goal**: Validate basic operation in production
  - **Capital**: $100
  - **Max Loss**: $100 (acceptable risk)
  - **Success Criteria**:
    - Bot runs 24h without crash
    - Strategy executes as expected
    - No critical bugs discovered
  - **Monitoring**: Check every 4-6 hours
  - **Decision Gate**:
    - ✅ If successful → Proceed to Stage 2 after 1-3 days
    - ❌ If issues → Fix, re-deploy to Stage 1

- [ ] **Stage 2: $500 Capital (3-5 days)**
  - **Goal**: Validate point efficiency and scaling
  - **Capital**: $500 (5x increase)
  - **Max Loss**: $500
  - **Success Criteria**:
    - Point farming rate acceptable (vs backtest estimate)
    - P&L stable (not worse than Stage 1)
    - No new issues from higher capital
  - **Monitoring**: Check every 8-12 hours
  - **Decision Gate**:
    - ✅ If successful → Proceed to Stage 3 after 3-5 days
    - ⚠️ If marginal → Extend Stage 2, tune parameters
    - ❌ If issues → Fix, rollback to Stage 1

- [ ] **Stage 3: $2,000+ Capital (full scale)**
  - **Goal**: Full-scale point farming
  - **Capital**: $2,000 - $10,000 (user-defined)
  - **Max Loss**: Managed by stop loss (e.g., -15% max)
  - **Success Criteria**:
    - Sustained point farming rate
    - Sharpe ratio / volume targets met
    - No scaling issues
  - **Monitoring**: Daily review (Phase 7)

**Staged Rollout Schedule**:
```
Day 1-3: Stage 1 ($100)
Day 4-8: Stage 2 ($500)
Day 9+: Stage 3 ($2K+)
```

**Deliverable**: **Deployment Plan Document**

### 6.2 Monitoring & Alerting Setup (0.5 day)

**Objective**: Proactive issue detection

- [ ] **Logging System**
  - Log file location: [e.g., logs/bot.log]
  - Log rotation: [Daily / 10MB max file size]
  - Log retention: [30 days]
  - Log shipping: [Optional: Send to cloud, e.g., CloudWatch, Datadog]

- [ ] **Alert Channels**
  - **Discord** (recommended):
    - Webhook URL configured
    - Alerts: Errors, SL triggers, daily P&L summary
  - **Telegram** (alternative):
    - Bot token configured
    - Alerts: Same as Discord
  - **Email** (fallback):
    - SMTP configured
    - Alerts: Critical errors only

- [ ] **Alert Rules**
  - [ ] **Error Alerts** (immediate):
    - WebSocket disconnect (after 3 failed reconnects)
    - API errors (after 5 failures in 1 minute)
    - Strategy errors (invalid signal, unexpected state)
    - Order placement failures

  - [ ] **Risk Alerts** (immediate):
    - Position nearing liquidation (leverage >8x or margin <20%)
    - Stop loss triggered
    - Drawdown exceeds threshold (e.g., -10%)

  - [ ] **Performance Alerts** (daily):
    - Daily P&L summary (+$X or -$Y)
    - Points earned today (X points)
    - Win rate rolling 7d (X%)

  - [ ] **Health Checks** (every 6-12 hours):
    - Bot heartbeat (bot alive and running)
    - No crashes in last 12h

- [ ] **Dashboard (Optional)**
  - Tool: [Grafana / Custom HTML / Google Sheets]
  - Metrics displayed:
    - Real-time P&L
    - Current position (size, entry, unrealized)
    - Points earned (daily, weekly, monthly)
    - Win rate, Sharpe ratio (rolling)
    - Error count (last 24h)

**Deliverable**: **Monitoring Setup Documentation** + **Test Alerts Sent**

### 6.3 Kill Switch & Emergency Procedures (0.5 day)

**Objective**: Ability to shut down bot safely in emergency

- [ ] **Manual Kill Switch**
  - Method 1: Keyboard interrupt (Ctrl+C)
    - Behavior: Bot catches signal, closes all positions, saves state, exits
  - Method 2: Kill switch file (touch kill.switch)
    - Behavior: Bot checks for file every 10s, if exists → emergency shutdown
  - Method 3: Discord/Telegram command (/stop)
    - Behavior: Receive command → close positions → stop bot

- [ ] **Automatic Kill Switch Triggers**
  - [ ] Max Drawdown Exceeded (e.g., -15% from peak)
  - [ ] Sustained API Failures (>10 failures in 5 minutes)
  - [ ] Unexpected Position Size (>110% of intended)
  - [ ] Manual override via config (EMERGENCY_STOP=true in .env)

- [ ] **Emergency Shutdown Procedure**
  1. Stop accepting new signals
  2. Cancel all open orders
  3. Close all positions (market orders for immediate execution)
  4. Save state to disk (position history, P&L, logs)
  5. Send emergency alert to all channels
  6. Exit process cleanly

- [ ] **Recovery Procedure**
  - [ ] Document: How to restart bot after emergency stop
  - [ ] Checklist:
    - Identify root cause of shutdown
    - Fix issue (code bug, API issue, etc.)
    - Verify fix in paper trading mode
    - Re-deploy to production (restart at appropriate stage)

**Deliverable**: **Emergency Procedures Document** + **Tested Kill Switch**

### 6.4 Deployment Execution

**Objective**: Deploy bot to production

- [ ] **Pre-Deployment Checklist**
  - [ ] QA sign-off received (Phase 5.4)
  - [ ] Config validated (production API keys, correct parameters)
  - [ ] Monitoring and alerts tested
  - [ ] Kill switch tested
  - [ ] User aware of deployment and monitoring plan

- [ ] **Stage 1 Deployment** ($100)
  - [ ] Load $100 to exchange account
  - [ ] Start bot with Stage 1 config
  - [ ] Monitor for 4-6 hours (first critical period)
  - [ ] Check logs, alerts, performance
  - [ ] Decision: Proceed to Stage 2 / Fix issues / Abort

- [ ] **Stage 2 Deployment** ($500)
  - [ ] Load additional $400 ($100 → $500)
  - [ ] Update config (capital: $500)
  - [ ] Restart bot
  - [ ] Monitor for 8-12 hours
  - [ ] Decision: Proceed to Stage 3 / Extend Stage 2 / Rollback

- [ ] **Stage 3 Deployment** ($2K+)
  - [ ] Load additional capital ($500 → $2K)
  - [ ] Update config (capital: $2K)
  - [ ] Restart bot
  - [ ] Monitor daily (Phase 7)

**Deliverable**: **Deployment Log** (timestamps, stages, decisions)

---

## Architect Success Criteria (Overall)

**Phase 0: API Feasibility**:
- ✅ API validated within 30-60 minutes
- ✅ Clear GO/NO-GO decision with evidence
- ✅ If NO-GO, blocker identified early (saved 10+ hours)

**Phase 4: Implementation**:
- ✅ Architecture designed and documented
- ✅ All components implemented and working
- ✅ Paper trading successful (24-48h without crashes)

**Phase 5: QA**:
- ✅ All unit, integration, stress tests passed
- ✅ Production readiness confirmed
- ✅ Known issues documented with workarounds

**Phase 6: Deployment**:
- ✅ Staged rollout executed safely ($100 → $500 → $2K)
- ✅ Monitoring and alerts operational
- ✅ Kill switch tested and ready
- ✅ Bot running in production with no critical issues

**Code Quality**:
- ✅ Modular architecture (easy to maintain)
- ✅ Comprehensive error handling
- ✅ Logging and observability
- ✅ Configuration-driven (no hardcoded values)

**Risk Management**:
- ✅ No catastrophic failures (no 100% loss)
- ✅ Stop losses enforced automatically
- ✅ Kill switch available and functional

---

## Appendix: Architect-PM Collaboration Points

**PM Provides to Architect**:
- Phase 1 Output: Point mechanism summary (for Phase 0 context)
- Phase 2 Output: **Final strategy specification** (required for Phase 4)
  - Strategy logic (entry/exit rules)
  - Indicators and parameters
  - Risk management (leverage, SL, position size)
- Phase 3 Output: PineScript validation (if done)

**Architect Provides to PM**:
- **Phase 0 Output: API Access Report (GO/NO-GO decision)**
  - Critical for PM to know if DEX is viable
  - If NO-GO, PM doesn't waste time on strategy research
- Phase 4 Output: Implemented bot (for PM to monitor in Phase 7)
- Phase 6 Output: Deployed bot with monitoring access

**Handoff Points**:
1. **Before Phase 1**: Architect completes Phase 0 → GO/NO-GO to PM
2. **After Phase 2**: PM completes strategy selection → Hands off spec to Architect for Phase 4
3. **After Phase 6**: Architect completes deployment → Hands off monitoring to PM for Phase 7

---

## Appendix: Common Blockers & Solutions

### Blocker: Private Beta API (Lighter Case)
**Symptoms**:
- Error 21511: "invalid tx type for account"
- Error 21109: "api key not found"
- Community confirms: "Only beta users can trade"

**Solution**:
- Phase 0 detects this immediately (30 min)
- Decision: NO-GO
- Alternative: Switch to public API DEX (Hyperliquid, dYdX)
- Time saved: 10+ hours

### Blocker: High Slippage (Volume Bots)
**Symptoms**:
- Backtest: 0.02% slippage assumed
- Live: 0.10% slippage observed (5x worse)
- Reason: Low liquidity, large order size

**Solution**:
- Phase 0: Check order book depth, test with real orders
- Architecture: Implement adaptive order sizing (split large orders)
- PM: Re-backtest with realistic slippage, adjust strategy

### Blocker: Rate Limits
**Symptoms**:
- Error 429 every few minutes
- Orders delayed or rejected

**Solution**:
- Phase 0: Document rate limits, test threshold
- Architecture: Request queue with throttling
- Monitor: Alert if approaching rate limit

### Blocker: WebSocket Instability
**Symptoms**:
- Disconnects every 2-3 hours
- Missed signals during disconnection

**Solution**:
- Phase 0: Test WebSocket stability (run for 12h)
- Architecture: Auto-reconnect with exponential backoff
- Fallback: REST polling if WebSocket fails repeatedly

---

## Checklist Metadata

**Version**: v0.1
**Status**: DRAFT - Awaiting validation through first deployment
**Owner**: Architect Agent (Winston)
**Created**: 2025-11-08
**Related Documents**:
- `perp-dex-farming-framework.md` - Master framework (all 9 phases)
- `pm-checklist-perp-dex-farming.md` - PM's checklist (Phases 1-3, 7-8)
- `api-bot-prerequisites.md` - Original Phase 0 (now integrated into Section 0)
- `POST_MORTEM_ANALYSIS.md` - Lighter failure analysis (motivation for Phase 0)

**Validation Plan**: Refine after each bot deployment (targeting 20+ DEXs)

---

**END OF ARCHITECT CHECKLIST v0.1**
