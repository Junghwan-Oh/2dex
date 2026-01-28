# DEX Bot Development Checklist

**Purpose**: Essential checklist for developing trading bots across 20+ DEX platforms
**Based on**: Apex Pro implementation experience (Nov 2025)
**Target**: All DEX bot projects (Apex, Lighter, Paradex, etc.)

---

## 📋 Overview

This checklist captures must-have operational elements for every DEX trading bot. While technical implementation details vary by DEX, these operational requirements remain consistent.

**Related Documents**:
- `IMPLEMENTATION_PLAN_COMMON.md`: Technical implementation (BaseDexClient, RiskManager, strategies)
- `DEX_INTEGRATION_FRAMEWORK.md`: 9-Stage integration process (Phase 0-8)
- `[DEX]/VERSION_HISTORY.md`: DEX-specific version history

---

## ✅ 1. Version Management System (MANDATORY)

Every DEX bot MUST implement semantic versioning with automatic tracking.

### Required Components

- [ ] **bot_version.py**: Version management class
  - Semantic versioning (major.minor.patch)
  - Automatic version increment on restart
  - Version history tracking (last 50 entries)
  - JSON persistence

- [ ] **bot_version.json**: Local version state (GITIGNORED)
  - Current version number
  - Change history with timestamps
  - Change type (patch/minor/major)
  - Change descriptions

- [ ] **VERSION_HISTORY.md**: Human-readable changelog
  - Version number + date
  - Change type (Korean + English)
  - Features added
  - Bug fixes
  - Files modified
  - Breaking changes (if any)

### Version Increment Rules

**Patch** (+0.0.1): 작은 애러 수정/작은 개선
- Small bug fixes
- Configuration tweaks
- Minor improvements
- Documentation updates

**Minor** (+0.1.0): 큰 애러 수정/큰 개선
- New major features
- Significant improvements
- Important bug fixes
- New bot configurations

**Major** (+1.0.0): 전면 수정/개선
- Complete strategy overhaul
- Architecture redesign
- Breaking changes to API/config
- New trading paradigm

### Implementation Example (Apex)

**Files**:
```
apex/
├── bot_version.py          # Version manager class
├── bot_version.json        # Local state (gitignored)
├── VERSION_HISTORY.md      # Changelog
└── telegram_notifier.py    # Integrates version into messages
```

**Usage**:
```python
from bot_version import BotVersion

version = BotVersion()
newVersion = version.increment('minor', 'Add 10-min PnL updates')
# Result: v1.0.0 → v1.1.0
```

---

## ✅ 2. Telegram Alert System (MANDATORY)

Every DEX bot MUST send real-time alerts to Telegram with version tracking.

### Required Alert Types

- [ ] **Bot Restart Notification**
  - Version number (e.g., "v1.1.0")
  - Change type (작은 개선/큰 개선/전면 개선)
  - Change description
  - Optional details (error fixed, improvement, expected outcome)
  - Timestamp

- [ ] **Entry Signal Alert**
  - Bot name
  - Action (ENTER_LONG / ENTER_SHORT)
  - Reason (Golden Cross / Death Cross)
  - Price
  - Position size
  - Leverage
  - Timestamp

- [ ] **Exit Signal Alert**
  - Bot name
  - Action (EXIT_LONG / EXIT_SHORT)
  - Reason (Stop loss / Signal)
  - Entry price
  - Exit price
  - PnL (USD + percentage)
  - Timestamp

- [ ] **Periodic PnL Update** (Every 10 minutes)
  - **ONLY send when positions are open**
  - Total PnL across all bots
  - Total trades
  - Position summary (LONG/SHORT/FLAT count)
  - Individual bot status (position, PnL, win rate)
  - Silent notification (no sound)
  - Version number in message

- [ ] **Error Alert**
  - Error description
  - Affected bot
  - Severity
  - Timestamp

### Alert Configuration

- [ ] **Environment Variables**
  ```bash
  TELEGRAM_BOT_TOKEN=your_bot_token
  TELEGRAM_CHAT_ID=your_chat_id
  ```

- [ ] **Notification Settings**
  - Entry/Exit: Normal notification (with sound)
  - PnL Update: Silent notification
  - Restart: Normal notification
  - Error: Normal notification

### Implementation Example (Apex)

**Files**:
```
apex/
├── telegram_notifier.py    # TelegramNotifier class
└── apex_main_bot.py        # Integrates alerts into bot loop
```

**Key Methods**:
```python
notifier.notifyBotRestart(
    changeType='minor',
    description='Add 10-min PnL updates',
    details={'improvement': '...', 'expected': '...'}
)

notifier.notifyEntrySignal(
    botName='BTC_1h_2x',
    action='ENTER_LONG',
    reason='Golden Cross',
    price=50000.0,
    size=0.001,
    leverage=2
)

notifier.notifyPnLUpdate(botSummaries=[...])  # Every 10 min, positions open only
```

---

## ✅ 3. GitHub Commit Automation (MANDATORY)

Every DEX bot MUST follow consistent commit practices with automatic workflows.

### Commit Message Format

Use **Conventional Commits** format:

```
<type>(<scope>): <description>

<body>

Generated with Claude Code
https://claude.com/claude-code

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

### Auto-Commit Triggers

- [ ] **Version Increment**
  - Trigger: Bot restart with version change
  - Commit: VERSION_HISTORY.md + related files
  - Message: Version-specific details

- [ ] **Configuration Change**
  - Trigger: Bot config modification
  - Commit: bot_config.py + related files
  - Message: Parameter adjustments

- [ ] **Strategy Update**
  - Trigger: Strategy logic modification
  - Commit: Strategy files
  - Message: Strategy improvement details

- [ ] **Bug Fix**
  - Trigger: Error resolution
  - Commit: Fixed files
  - Message: Error description + fix details

- [ ] **Performance Optimization**
  - Trigger: Performance improvement
  - Commit: Optimized files
  - Message: Before/after metrics

### Commit Message Templates

**Version Update**:
```
feat(version): Upgrade to v1.1.0 - 10-min PnL updates

✅ Features:
- Periodic PnL updates every 10 minutes
- Version tracking in all Telegram messages
- Only send updates when positions are open

🔧 Changes:
- apex_main_bot.py: Added _sendPnLUpdateIfDue()
- telegram_notifier.py: Added notifyPnLUpdate()
- bot_version.py: Version management class

Generated with Claude Code
https://claude.com/claude-code

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Bug Fix**:
```
fix(trailing-stop): Fix Decimal/float type mismatch - v1.0.1

❌ Bug:
- TypeError: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'

✅ Fix:
- Changed trailingStop from Decimal to float type
- bot_config_fast.py: Decimal('0.005') → 0.005

⚠️ Impact:
- Trailing stop calculation was failing
- Position had no stop loss protection

Generated with Claude Code
https://claude.com/claude-code

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Pre-Commit Checklist

- [ ] Run tests (`pytest`)
- [ ] Check lint (`flake8`, `black`, `mypy`)
- [ ] Verify version increment (if applicable)
- [ ] Update VERSION_HISTORY.md
- [ ] Ensure .gitignore excludes sensitive files

---

## ✅ 4. Testing Strategy (MANDATORY)

Every DEX bot MUST achieve minimum 80% test coverage.

### Test Types

- [ ] **Unit Tests** (80%+ coverage)
  - Position calculations
  - Signal generation logic
  - Risk management rules
  - Order validation
  - EMA calculation accuracy

- [ ] **E2E Tests** (Testnet)
  - Full trade lifecycle (entry → exit)
  - WebSocket/REST connectivity
  - Order execution
  - Stop loss triggers
  - API error handling

- [ ] **Lint Checks** (Must pass)
  - `flake8`: Code style
  - `black`: Code formatting
  - `mypy`: Type checking

### Test Organization

```
tests/
├── unit/
│   ├── test_position_calculator.py
│   ├── test_strategy_bot.py
│   ├── test_risk_manager.py
│   └── test_price_monitor.py
│
├── e2e/
│   ├── test_full_trade_cycle.py
│   ├── test_websocket_connection.py
│   └── test_stop_loss_trigger.py
│
└── conftest.py  # Pytest fixtures
```

### Test Execution Commands

```bash
# Unit tests
pytest tests/unit/ -v

# E2E tests (Testnet)
pytest tests/e2e/ -m testnet -v

# Coverage report
pytest tests/unit/ --cov=. --cov-report=html

# Lint checks
flake8 *.py
black --check *.py
mypy *.py
```

### Coverage Requirements

- **Minimum**: 80% overall
- **Critical paths**: 100% (order execution, risk checks)
- **Nice to have**: 90%+ for production deployment

---

## ✅ 5. Documentation Standards (MANDATORY)

Every DEX bot MUST maintain comprehensive documentation.

### Required Documents

- [ ] **README.md**
  - Project overview
  - Features
  - Installation instructions
  - Configuration guide
  - Usage examples
  - Troubleshooting

- [ ] **VERSION_HISTORY.md**
  - Version changelog (see Section 1)
  - Version increment guidelines
  - Maintenance notes

- [ ] **LESSONS_LEARNED_[DEX]_INTEGRATION.md**
  - Integration challenges
  - Solutions discovered
  - Best practices
  - Mistakes to avoid
  - Time-saving patterns

- [ ] **INTEGRATION_SUMMARY.md**
  - Current status
  - Implementation progress
  - Technical decisions
  - Next steps

- [ ] **API_CONNECTION_GUIDE.md** (if applicable)
  - API endpoints tested
  - Authentication method
  - WebSocket vs REST decision
  - Rate limits
  - Known issues

### Documentation Best Practices

- [ ] **Update on every change**: Documentation != code is unacceptable
- [ ] **Include code examples**: Show don't tell
- [ ] **Explain rationale**: Document *why*, not just *what*
- [ ] **Maintain freshness**: Monthly review, remove outdated info
- [ ] **Use cross-references**: Link related documents

---

## ✅ 6. Configuration Management (MANDATORY)

Every DEX bot MUST use environment-based configuration.

### Configuration Files

- [ ] **bot_config.py**: Bot-specific settings
  ```python
  BOT_CONFIGS = [
      {
          'name': 'BTC_1h_2x',
          'symbol': 'BTC-USDT',
          'timeframe': '1h',
          'leverage': 2,
          'emaShort': 30,
          'emaLong': 80,
          'trailingStop': 0.02  # 2%
      },
      # ...
  ]

  TOTAL_CAPITAL = 90.0
  PAPER_TRADING = True
  ```

- [ ] **.env**: Sensitive credentials (GITIGNORED)
  ```bash
  # DEX API Keys
  APEX_API_KEY=your_api_key
  APEX_API_SECRET=your_api_secret
  APEX_PASSPHRASE=your_passphrase

  # Telegram
  TELEGRAM_BOT_TOKEN=your_bot_token
  TELEGRAM_CHAT_ID=your_chat_id
  ```

- [ ] **.env.example**: Template for new users
  ```bash
  # DEX API Keys
  APEX_API_KEY=
  APEX_API_SECRET=
  APEX_PASSPHRASE=

  # Telegram
  TELEGRAM_BOT_TOKEN=
  TELEGRAM_CHAT_ID=
  ```

### Environment Variables

- [ ] Load with `python-dotenv`
  ```python
  from dotenv import load_dotenv
  load_dotenv()

  apiKey = os.getenv('APEX_API_KEY')
  ```

- [ ] Validate on startup
  ```python
  if not apiKey:
      raise ValueError("APEX_API_KEY not set in .env")
  ```

---

## ✅ 7. Monitoring & Logging (MANDATORY)

Every DEX bot MUST implement structured logging and monitoring.

### Logging Configuration

- [ ] **Log Levels**
  - DEBUG: Detailed diagnostic info
  - INFO: General informational messages
  - WARNING: Warning messages (non-critical)
  - ERROR: Error messages (critical)

- [ ] **Log Rotation**
  ```python
  import logging
  from logging.handlers import RotatingFileHandler

  handler = RotatingFileHandler(
      'bot.log',
      maxBytes=10*1024*1024,  # 10MB
      backupCount=5
  )
  ```

- [ ] **Structured Logging**
  ```python
  logging.info(f"[ENTRY] {botName} - {action}")
  logging.info(f"  Price: ${price:,.2f}")
  logging.info(f"  Size: {size:.4f}")
  ```

### Monitoring Metrics

- [ ] **Performance Metrics**
  - Total PnL
  - Win rate
  - Sharpe ratio
  - Max drawdown
  - Trade count

- [ ] **System Metrics**
  - API latency
  - Order execution time
  - WebSocket/REST uptime
  - Error rate

- [ ] **Risk Metrics**
  - Current drawdown
  - Position exposure
  - Leverage usage
  - Distance to liquidation

---

## ✅ 8. Deployment Checklist (MANDATORY)

Every DEX bot MUST follow staged deployment process.

### Pre-Deployment

- [ ] All tests passing (unit + E2E)
- [ ] Lint checks clean
- [ ] Coverage ≥ 80%
- [ ] Documentation updated
- [ ] .env configured correctly
- [ ] Testnet validation complete

### Staged Rollout

- [ ] **Stage 1**: Small capital ($30-50)
  - Duration: 1-3 days
  - Goal: Validate basic operation
  - Success: Uptime > 95%, no critical errors

- [ ] **Stage 2**: Medium capital ($100-200)
  - Duration: 3-5 days
  - Goal: Validate scaling
  - Success: Performance ≥ 70% of backtest

- [ ] **Stage 3**: Full capital ($500-1000)
  - Duration: 1-2 weeks
  - Goal: Production validation
  - Success: Performance ≥ 80% of backtest

### Post-Deployment

- [ ] Daily monitoring (PnL, trades, errors)
- [ ] Weekly analysis (backtest vs live gap)
- [ ] Monthly review (strategy optimization)

---

## ✅ 9. Risk Management (MANDATORY)

Every DEX bot MUST implement comprehensive risk controls.

### Position Limits

- [ ] Maximum position size per DEX
- [ ] Maximum total exposure across all DEXs
- [ ] Maximum leverage allowed
- [ ] Minimum account balance threshold

### Drawdown Controls

- [ ] Maximum drawdown percentage (e.g., 15%)
- [ ] Daily loss limit (e.g., $500)
- [ ] Kill switch at critical thresholds

### Trade Limits

- [ ] Maximum trades per day per DEX (e.g., 200)
- [ ] Minimum time between trades
- [ ] Maximum consecutive losses before pause

### Implementation Example

```python
from common.lib.risk_manager import RiskManager, RiskLimits

riskLimits = RiskLimits(
    maxPositionSizeUsd=10000.0,
    maxTotalExposureUsd=50000.0,
    maxDrawdownPercent=15.0,
    maxDailyLossUsd=500.0,
    maxDailyTradesPerDex=200
)

riskManager = RiskManager(riskLimits)

# Before opening position
canOpen, reason = riskManager.canOpenPosition('apex', 5000.0)
if not canOpen:
    print(f"Risk check failed: {reason}")
```

---

## ✅ 10. Emergency Procedures (MANDATORY)

Every DEX bot MUST have emergency shutdown procedures.

### Emergency Shutdown Triggers

- [ ] Drawdown exceeds maximum threshold
- [ ] Daily loss limit hit
- [ ] Critical API error
- [ ] Exchange downtime
- [ ] Manual intervention required

### Shutdown Actions

- [ ] Close all open positions (MARKET orders)
- [ ] Cancel all pending orders
- [ ] Stop all bot threads
- [ ] Save current state
- [ ] Send Telegram alert
- [ ] Log emergency event

### Implementation Example

```python
def emergencyShutdown(reason: str):
    logging.critical(f"[EMERGENCY] Shutting down: {reason}")

    # Close all positions
    for bot in bots.values():
        bot.closeAllPositions()

    # Stop threads
    for thread in threads.values():
        thread.stop()

    # Save state
    saveState()

    # Alert
    notifier.notifyError(f"EMERGENCY SHUTDOWN: {reason}")
```

---

## 📊 Apex Implementation Status

Apex Pro has implemented all mandatory checklist items:

| Item | Status | Files |
|------|--------|-------|
| 1. Version Management | ✅ Complete | `bot_version.py`, `VERSION_HISTORY.md` |
| 2. Telegram Alerts | ✅ Complete | `telegram_notifier.py` |
| 3. GitHub Automation | ✅ Complete | Commit workflow established |
| 4. Testing | ✅ Complete | Unit + E2E tests, 80%+ coverage |
| 5. Documentation | ✅ Complete | All required docs present |
| 6. Configuration | ✅ Complete | `bot_config.py`, `.env` |
| 7. Monitoring | ✅ Complete | Structured logging implemented |
| 8. Deployment | ✅ Complete | Staged rollout completed |
| 9. Risk Management | ✅ Complete | Risk limits implemented |
| 10. Emergency Procedures | ✅ Complete | Kill switch operational |

---

## 📚 Related Documents

### Common Framework
- `IMPLEMENTATION_PLAN_COMMON.md`: Technical implementation details
- `DEX_INTEGRATION_FRAMEWORK.md`: 9-Stage integration process

### DEX-Specific
- `apex/VERSION_HISTORY.md`: Apex version history
- `apex/LESSONS_LEARNED_APEX_INTEGRATION.md`: Apex-specific learnings
- `apex/INTEGRATION_SUMMARY.md`: Apex integration summary

---

## 🎯 Checklist Usage

**For New DEX Integration**:
1. Copy this checklist
2. Create `[DEX]/DEVELOPMENT_CHECKLIST.md`
3. Check off items as implemented
4. Document DEX-specific adaptations

**For Existing DEX Review**:
1. Review this checklist
2. Identify missing items
3. Prioritize implementation
4. Update VERSION_HISTORY.md

---

**Version**: 1.0
**Last Updated**: 2025-11-09
**Based on**: Apex Pro implementation (v1.0.0 → v1.1.1)
