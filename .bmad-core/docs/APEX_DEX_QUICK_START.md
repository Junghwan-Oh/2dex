# Apex DEX Quick Start Guide

**Version**: 1.0
**Created**: 2025-11-08
**Purpose**: Fast-track Apex DEX bot deployment using framework + BMAD

---

## TL;DR

```bash
/bmad-master

"Apex DEX trend-following bot 개발:
- Strategy: BTC 1h 2x, ETH 30m 1x (Lighter 검증완료)
- Framework: perp-dex-farming-framework.md (9 phases)
- Checklists: architect-checklist-perp-dex-farming.md, pm-checklist-perp-dex-farming.md
- Reuse: Lighter codebase (lighter/ 폴더)"
```

**Expected Timeline**: 5-7 days (vs 4-6 weeks 일반)

---

## Why bmad-master?

**9-phase framework = Single complete project (not multi-story epic)**

- ✅ bmad-master can execute ALL phases without agent switching
- ✅ Checklists ensure quality at each phase
- ✅ Simple: One agent, one workflow, one chat session

**When to use specialized agents**:
- Phase 0 critical validation → `/architect` (optional, for extra rigor)
- Never needed → PM, SM, Dev (bmad-master handles everything)

---

## Framework Overview

### 9-Phase Perp DEX Framework

| Phase | Focus | Duration | Checklist |
|-------|-------|----------|-----------|
| **Phase 0** | API Feasibility | 30-60 min | architect-checklist Section 0 |
| **Phase 1** | Strategy Research | 1-2 hours (reuse) | pm-checklist Section 1 |
| **Phase 2** | Python Backtesting | 2-3 days (reuse) | pm-checklist Section 2 |
| **Phase 3** | PineScript | SKIP | - |
| **Phase 4** | Implementation | 2-3 days (reuse) | architect-checklist Section 4 |
| **Phase 5** | QA Testing | 1 day | architect-checklist Section 5 |
| **Phase 6** | Deployment | 1 day + monitoring | architect-checklist Section 6 |
| **Phase 7** | Post-Mortem | Ongoing | pm-checklist Section 7 |
| **Phase 8** | Improvement | Ongoing | pm-checklist Section 8 |

**Total**: ~5-7 days (85% faster due to Lighter code reuse)

---

## Detailed Execution Guide

### Phase 0: API Feasibility (30-60 min)

**Critical GO/NO-GO gate** - Never skip this!

**Checklist**: `architect-checklist-perp-dex-farming.md` Section 0

**Key Validations**:
- ✅ Futures/Perpetual API (NOT Spot)
- ✅ Isolated margin mode support
- ✅ WebSocket stability (for trend-following)
- ✅ Batch orders API (future Grid/MM bots)
- ✅ API access test (avoid Lighter Error 21511)

**Output**: GO/CONDITIONAL-GO/NO-GO Report

**If GO**: Proceed to Phase 1
**If CONDITIONAL-GO**: Address concerns, then proceed
**If NO-GO**: Report blockers, consider alternative DEX

---

### Phase 1: Strategy Research (1-2 hours)

**Fast-track**: Reuse Lighter validated strategies

**Checklist**: `pm-checklist-perp-dex-farming.md` Section 1

**Actions**:
1. Research Apex point mechanism
2. Confirm bot type: Trend-Following
3. Confirm strategies: BTC 1h 2x, ETH 30m 1x (from Lighter)
4. Document point efficiency expectations

**Output**: Strategy confirmation (BTC 1h 2x, ETH 30m 1x)

---

### Phase 2: Python Backtesting (2-3 days)

**Fast-track**: Adapt Lighter backtest code

**Checklist**: `pm-checklist-perp-dex-farming.md` Section 2

**Actions**:
1. Copy `backtest_lighter.py` → `backtest_apex.py`
2. Update API endpoints (Lighter → Apex)
3. Run 750 combinations (same as Lighter):
   - 5 coins × 6 timeframes × 5 leverage × 5 stop-loss
4. Validate results align with Lighter performance

**Output**: Backtest results confirming Sharpe > 2.0, MDD < 15%

---

### Phase 3: PineScript (SKIP)

**Decision**: Skip for MVP, prioritize fast deployment

**Rationale**: Phase 2 provides sufficient 1-year validation

---

### Phase 4: Implementation (2-3 days)

**Fast-track**: Reuse Lighter bot architecture

**Checklist**: `architect-checklist-perp-dex-farming.md` Section 4

**Actions**:
1. Review Lighter `BOT_ARCHITECTURE.md`
2. Copy components: PriceMonitor, StrategyEngine, OrderExecutor, RiskManager
3. Swap SDK: `from lighter import ...` → `from apex import ...`
4. Update config: Apex API endpoints, credentials
5. Implement Isolated margin enforcement
6. Test with paper trading

**Output**: Working `apex_bot/` codebase

---

### Phase 5: QA Testing (1 day)

**Checklist**: `architect-checklist-perp-dex-farming.md` Section 5

**Critical Tests**:
- ✅ Liquidation prevention (Isolated margin enforced)
- ✅ Stop-Loss execution (conditional orders working)
- ✅ Position size limits (risk manager enforced)
- ✅ WebSocket reconnection (graceful recovery)
- ✅ API error handling (rate limits, invalid orders)
- ✅ State persistence (no data loss on restart)

**Output**: QA-approved production-ready bot

---

### Phase 6: Staged Deployment (1 day + monitoring)

**Checklist**: `architect-checklist-perp-dex-farming.md` Section 6

**Deployment Strategy**:
```
Stage 1: $100 capital → Monitor 1 week → Evaluate
Stage 2: $500 capital → Monitor 2 weeks → Evaluate
Stage 3: $2K capital → Ongoing production
```

**Rollback Criteria**:
- >10% capital loss
- Repeated API errors
- Liquidation event
- Unexpected behavior vs backtest

**Actions**:
1. Setup monitoring (logs, alerts, dashboard)
2. Deploy Stage 1 ($100)
3. Monitor for 1 week
4. Scale to $500 → $2K if successful

**Output**: Live bot running in production

---

### Phase 7: Post-Mortem (Ongoing)

**Checklist**: `pm-checklist-perp-dex-farming.md` Section 7

**Review Schedule**:
- Week 1: Daily reviews
- Week 2-4: Every 3 days
- Month 2+: Weekly reviews

**Analysis**:
- Live P&L vs backtest projections
- Point accumulation rate
- Sharpe ratio (live) vs backtest
- Error frequency and types
- Deviation root cause analysis

**Output**: `POST_MORTEM_APEX.md` with lessons learned

---

### Phase 8: Strategy Improvement (Ongoing)

**Checklist**: `pm-checklist-perp-dex-farming.md` Section 8

**Improvement Cycle**:
1. Identify improvement opportunity (from Phase 7 data)
2. Propose strategy adjustment
3. Re-backtest with new parameters
4. If successful → Restart Phase 6 with v2.0 ($100 → $500 → $2K)

**Output**: Strategy v2.0, v3.0, etc. with continuous improvement

---

## Key Success Factors

### Critical Rules

1. **Never Skip Phase 0** - 30-60 min prevents 10+ hour failures (Lighter lesson!)
2. **Reuse Lighter Work** - 85% time savings (5-7 days vs 4-6 weeks)
3. **Staged Deployment** - Always $100 → $500 → $2K (never skip)
4. **Document Learnings** - Post-mortem improves framework (v0.1 → v1.0)

### Common Pitfalls

❌ Skip Phase 0 (API validation)
✅ Execute Phase 0 FIRST, always

❌ Deploy without QA approval
✅ Complete Phase 5 before Phase 6

❌ Scale capital without testing
✅ Follow $100 → $500 → $2K progression

❌ Ignore live data deviations
✅ Analyze why live Sharpe differs from backtest

---

## File References

### Framework Files
- `C:\Users\crypto quant\.bmad-core\templates\perp-dex-farming-framework.md` - Complete 9-phase methodology
- `C:\Users\crypto quant\.bmad-core\checklists\architect-checklist-perp-dex-farming.md` - Phase 0, 4, 5, 6
- `C:\Users\crypto quant\.bmad-core\checklists\pm-checklist-perp-dex-farming.md` - Phase 1, 2, 3, 7, 8

### Lighter Reference Files
- `C:\Users\crypto quant\perpdex farm\lighter\docs\FINAL_STRATEGY_SELECTION.md` - Strategy validation
- `C:\Users\crypto quant\perpdex farm\lighter\docs\BOT_ARCHITECTURE.md` - Tech spec reference
- `C:\Users\crypto quant\perpdex farm\lighter\docs\POST_MORTEM_ANALYSIS.md` - Lessons learned
- `C:\Users\crypto quant\perpdex farm\lighter\bot\*` - Reusable codebase

---

## Next Steps

**Ready to start?**

```bash
/bmad-master

"Execute Apex DEX bot development:

Framework: perp-dex-farming-framework.md (9 phases)
Strategy: BTC 1h 2x, ETH 30m 1x (Lighter validated)
Target: 5-7 day deployment

Phase 0 (30-60 min): API Feasibility Check
- Checklist: architect-checklist-perp-dex-farming.md Section 0
- Validate: Futures API, Isolated margin, WebSocket
- Output: GO/NO-GO report

If GO, proceed Phase 1-8:
- Reuse Lighter backtest code (Phase 2)
- Reuse Lighter bot architecture (Phase 4)
- Staged deployment $100→$500→$2K (Phase 6)

Let's start with Phase 0 API Feasibility Check."
```

---

## Framework Evolution

**v0.1** (Current): Created from Lighter post-mortem, untested
**v1.0** (After Apex): Validated with real deployment, refined estimates
**v2.0** (After 3+ DEXs): Patterns identified, common blockers documented
**v3.0** (After 10+ DEXs): Mature framework with automation tools

---

## Summary

**Single Command**: `/bmad-master` + framework reference
**Single Workflow**: 9 phases executed sequentially
**Single Outcome**: Production-ready DEX bot in 5-7 days

**No complex agent switching. No linear process confusion. Just execute.**
