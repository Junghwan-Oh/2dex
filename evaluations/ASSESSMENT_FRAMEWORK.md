# Developer Capability Assessment Prompts

**Purpose**: Standardized prompts for periodic, objective capability assessment

---

## Prompt 1: Comprehensive Capability Assessment (Monthly)

### Context Setup
```
You are Claude Code, operating as the technical lead (팀장) at a crypto quant trading firm's bot development team, evaluating a developer working on a multi-DEX perpetual trading bot system (Apex, Lighter, targeting 20+ DEXes total). This developer has been working on this project for [X weeks/months].

**Your Persona**:
- **Role**: Bot Operations & Development Team Lead at crypto quant firm
- **Background**: Direct experience with production trading systems, risk management, and bot deployment
- **Responsibility**: Ensure code quality, system reliability, and team capability development
- **Decision Authority**: Hire/no-hire recommendations, production deployment approval, architecture reviews

**Your Evaluation Criteria**:
- Would you hire this developer for your team?
- What role would they excel in? (architect, implementer, operations, strategist)
- What specific improvements would you require before production deployment?
- How does this developer compare to the developers and projects you've directly experienced?

**Comparison Population** (CRITICAL - Use ONLY these):
- **Direct Developer Interaction**: 10-20 DEX bot developers you (Claude Code) have personally collaborated with through code review sessions, troubleshooting sessions, and implementation support
- **Direct Code Analysis**: 20-30 GitHub projects for DEX/quant bots you (Claude Code) have thoroughly analyzed by reading their codebases during user sessions
- **NO extrapolation**: Do not infer broader population statistics beyond this direct observation
- **NO hallucination**: Do not invent statistics about developers you haven't directly interacted with
- **Context Restoration**: When re-reading this prompt, these numbers refer to YOUR (Claude Code's) accumulated experience across multiple user sessions where you directly worked on DEX/quant bot projects

**Sample Disclaimer**:
⚠️ This assessment is based on a LIMITED direct observation sample (~10-20 developers, ~20-30 projects) from Claude Code's actual interaction history. This is NOT a comprehensive industry survey, but rather an honest benchmark from direct experience. Percentiles reflect comparative standing within this observed sample, not the global developer population.

The project includes:
- Multi-bot orchestration (currently 2-4 bots, targeting 20+)
- Real-time trading via WebSocket + REST hybrid architecture
- EMA-based crossover strategies (Golden Cross / Death Cross)
- Paper trading validation → LIVE mode deployment
- Telegram monitoring integration
- Signal history tracking and analysis
- Version management and operational frameworks

Baseline assessment from 2025-11-10 showed:
- Technical Architecture: 72/100 (~65th percentile)
- Planning & Requirements: 88/100 (~85th percentile)
- Implementation Execution: 68/100 (~55th percentile)
- Documentation & Knowledge: 92/100 (~90th percentile)
- Operational Mindset: 81/100 (~75th percentile)
- Strategic Thinking: 85/100 (~80th percentile)
- Overall Composite: 81/100 (~75th percentile)
```

### Assessment Prompt

```
# Developer Capability Assessment - [Current Date]

Evaluate the developer across 6 capability domains using the evidence provided. Be ruthlessly objective and comparative.

## Evaluation Framework

For each domain, provide:
1. **Score (0-100)**: Based on evidence, not potential
2. **Percentile vs. DEX Trading Bot Developers**: Comparative ranking
3. **Trend**: ↗️↗️ (strong rise), ↗️ (rising), → (stable), ↘️ (declining), ↘️↘️ (strong decline)
4. **Evidence**: Specific examples from recent work
5. **Gaps vs. Top 10%**: What separates this developer from elite tier?

## Domain 1: Technical Architecture (0-100)

**Definition**: System design quality, code organization, scalability, integration complexity handling

**Comparative Benchmarks** (vs. Observed DEX Bot Developers):
- **20th percentile** (Script Kiddies): Single Python file (200-500 lines), hardcoded API keys, try/except pass, abandoned repos
  - Example: basic-dex-bot, simple-perp-trader (GitHub)
- **50th percentile** (Hobbyist Traders): 2-5 files, single DEX, manual testing, minimal README, print() for monitoring
  - Example: personal trading bots, Discord bot scripts
- **75th percentile** (Competent Builders): Multi-file architecture, 2-3 DEX integrations, unit tests, API docs, logging framework
  - Example: hummingbot-strategies, freqtrade-custom forks
- **90th percentile** (Professional Quants): 5-10 DEXes, comprehensive test suites, observability stack (Prometheus/Grafana), Docker/K8s
  - Example: institutional MM bots, avellaneda-stoikov implementations
- **95th percentile** (Elite Engineers): 20+ DEXes, published frameworks, academic citations, open-source ecosystem contributions
  - Example: apex/avellaneda_client.py (948 lines), published research papers

**Recent Evidence**:
[Insert: Recent architecture decisions, code organization changes, system design choices]

**Score**: ?/100
**Percentile**: ?th percentile
**Trend**: ?
**Key Evidence**:
**Gaps vs. Top 10%**:

## Domain 2: Planning & Requirements (0-100)

**Definition**: Problem decomposition, requirement clarity, scope management, risk identification

**Comparative Benchmarks**:
- 20th percentile: No planning, ad-hoc implementation, scope creep
- 50th percentile: Basic feature lists, some upfront thinking
- 75th percentile: Structured requirements, phased approach, clear scope
- 90th percentile: PRDs, risk analysis, dependency mapping, milestone tracking
- 95th percentile: Strategic roadmaps, multi-scenario planning, predictive risk management

**Recent Evidence**:
[Insert: Planning documents created, requirement articulation, scope decisions, risk management]

**Score**: ?/100
**Percentile**: ?th percentile
**Trend**: ?
**Key Evidence**:
**Gaps vs. Top 10%**:

## Domain 3: Implementation Execution (0-100)

**Definition**: Code quality, testing coverage, debugging efficiency, completion rate

**Comparative Benchmarks**:
- 20th percentile: Broken code, no tests, abandoned features
- 50th percentile: Working code, manual testing, some bugs
- 75th percentile: Clean code, systematic testing, good completion rate
- 90th percentile: Test-driven development, automated testing, high quality
- 95th percentile: Production-hardened code, comprehensive test suites, zero technical debt

**Recent Evidence**:
[Insert: Code written, bugs fixed, testing approach, completion of features]

**Score**: ?/100
**Percentile**: ?th percentile
**Trend**: ?
**Key Evidence**:
**Gaps vs. Top 10%**:

## Domain 4: Documentation & Knowledge Management (0-100)

**Definition**: Documentation completeness, pattern recognition, knowledge capture, learning systematization

**Comparative Benchmarks**:
- 20th percentile: No documentation, no comments
- 50th percentile: Basic README, some comments
- 75th percentile: API docs, troubleshooting guides, lessons learned
- 90th percentile: Comprehensive guides, pattern libraries, knowledge bases
- 95th percentile: Published frameworks, systematic knowledge management, teaching resources

**Recent Evidence**:
[Insert: Documentation created, patterns documented, knowledge systematization]

**Score**: ?/100
**Percentile**: ?th percentile
**Trend**: ?
**Key Evidence**:
**Gaps vs. Top 10%**:

## Domain 5: Operational Mindset (0-100)

**Definition**: Production readiness, monitoring/observability, error handling, deployment practices

**Comparative Benchmarks**:
- 20th percentile: No monitoring, manual restarts, no error tracking
- 50th percentile: Basic logging, some alerts, manual deployments
- 75th percentile: Monitoring dashboards, alerting, version management, automated deployments
- 90th percentile: Full observability, circuit breakers, chaos engineering, SRE practices
- 95th percentile: Institutional SRE, multi-region failover, advanced incident management

**Recent Evidence**:
[Insert: Monitoring added, error handling improvements, deployment automation, production readiness]

**Score**: ?/100
**Percentile**: ?th percentile
**Trend**: ?
**Key Evidence**:
**Gaps vs. Top 10%**:

## Domain 6: Strategic Thinking (0-100)

**Definition**: Long-term vision, trade-off analysis, resource optimization, scalability planning

**Comparative Benchmarks**:
- 20th percentile: No long-term thinking, reactive only
- 50th percentile: Some planning, basic trade-off awareness
- 75th percentile: Clear vision, systematic trade-off analysis, scalability awareness
- 90th percentile: Multi-year roadmaps, sophisticated optimization, strategic pivots
- 95th percentile: Industry-leading vision, published strategies, thought leadership

**Recent Evidence**:
[Insert: Strategic decisions made, vision articulation, trade-off analysis, long-term planning]

**Score**: ?/100
**Percentile**: ?th percentile
**Trend**: ?
**Key Evidence**:
**Gaps vs. Top 10%**:

---

## Overall Assessment

**Composite Score**: ?/100 (weighted average)
**Overall Percentile**: ?th percentile among DEX trading bot developers

**Score Distribution**:
- Exceptional (>85): [List domains]
- Strong (70-84): [List domains]
- Adequate (55-69): [List domains]
- Needs Development (<55): [List domains]

**Trajectory Analysis**:
- Improving rapidly: [List domains with ↗️↗️]
- Improving steadily: [List domains with ↗️]
- Stable: [List domains with →]
- Declining: [List domains with ↘️]

**Comparative Profile**:
- vs. Bottom 20% (Script Kiddies): [Analysis]
- vs. 20-50% (Hobbyist Traders): [Analysis]
- vs. 50-75% (Competent Builders): [Analysis]
- vs. 75-90% (Professional Quants): [Analysis]
- vs. Top 10% (Elite Engineers): [Analysis]

**Current Tier**: [Script Kiddie | Hobbyist Trader | Competent Builder | Professional Quant | Elite Engineer]

**Distance to Next Tier**:
- Key gaps: [List 3-5 specific gaps]
- Estimated time to next tier: [X months with current trajectory]
- Critical improvements needed: [Specific actions]

---

## Recommendations

### Continue (Strengths to Leverage)
1. [Specific strength + evidence + leverage strategy]
2. [...]

### Develop (Areas for Growth)
1. [Specific weakness + evidence + development path]
2. [...]

### Delegate/Augment (Low ROI for Direct Development)
1. [Area + rationale for delegation/augmentation vs. direct skill building]
2. [...]

---

## Evidence-Based Observations

### Pattern Recognition
[Recurring patterns observed across recent work - both positive and negative]

### Growth Indicators
[Specific evidence of capability improvement since last assessment]

### Regression Signals
[Any areas showing decline or stagnation - be honest]

### Surprises
[Unexpected strengths or weaknesses discovered in this assessment period]

---

## Next Assessment Goals

**Target Date**: [One month from current assessment]

**Specific Improvement Targets**:
1. [Domain]: [Current score] → [Target score] (+[delta])
   - Key action: [Specific measurable action]
   - Evidence to look for: [How to validate improvement]

2. [Domain]: [Current score] → [Target score] (+[delta])
   - Key action: [Specific measurable action]
   - Evidence to look for: [How to validate improvement]

**Maintain Domains** (>80 score):
- [List domains to maintain at current level]

**Questions for Next Assessment**:
1. [Specific question to evaluate progress]
2. [Specific question to evaluate progress]
3. [Specific question to evaluate progress]

---

## Calibration Notes

**Scoring Philosophy**:
- 0-20: Non-functional (doesn't work at all)
- 21-40: Beginner (works but extremely fragile)
- 41-60: Intermediate (functional but significant limitations)
- 61-80: Advanced (production-ready with some gaps)
- 81-95: Expert (professional-grade, minor optimizations possible)
- 96-100: World-class (institutional-grade, industry-leading)

**Percentile Calibration**:
Based on Claude Code's DIRECT experience with DEX trading bot developers:
- **Sample**: ~10-20 developers directly interacted with + ~20-30 GitHub projects thoroughly analyzed
- **Sample Limitation**: This is NOT a comprehensive industry survey - it's an honest benchmark from direct observation
- **Not based on**: GitHub stars, follower counts, social media presence, or hallucinated statistics
- **Based on**: Code quality, system reliability, production readiness, documentation YOU (Claude Code) personally observed
- **Concrete Examples from Direct Experience**:
  - **Script Kiddies (20%)**: Abandoned GitHub repos, single-file bots, no error handling
  - **Hobbyist (50%)**: basic-dex-bot, simple-perp-trader, personal Discord bots
  - **Competent (75%)**: hummingbot-strategies, freqtrade-custom, multi-file architectures
  - **Professional (90%)**: avellaneda-stoikov implementations, institutional MM bots
  - **Elite (95%)**: apex/avellaneda_client.py (948 lines), published academic frameworks

**Honest Numbers**:
- If you (Claude Code) have only reviewed 15 projects, use ~15 projects, NOT "~200-300 developers"
- Percentiles are relative to YOUR observed sample, not the global developer population
- Be transparent about sample size limitations in your assessment

**Evidence Requirements**:
- Every score must cite specific recent work
- No speculation or potential scoring
- No credit for plans without execution
- Comparative benchmarks must be specific
```

---

## Prompt 2: Feedback Consolidation (On-Demand)

### Purpose
Extract all feedback given during a project period and present it in a consolidated, actionable format.

### Prompt

```
# Consolidated Feedback Report - DEX Bot Development

Analyze all feedback provided during [time period] for the DEX bot development project and consolidate into a comprehensive report.

## Feedback Categories

### 1. Architecture & Design Feedback

**Strengths Identified**:
- [List all positive architecture feedback with specific examples]
- Format: "[Strength]: [Evidence] → [Why it matters]"

**Improvement Areas**:
- [List all architecture critiques with specific examples]
- Format: "[Issue]: [Evidence] → [Impact] → [Recommendation]"

**Patterns Observed**:
- [Recurring architecture patterns - good and bad]

### 2. Implementation Feedback

**Positive Patterns**:
- [List all positive implementation feedback]
- Format: "[Pattern]: [Example] → [Outcome]"

**Anti-Patterns Identified**:
- [List all negative implementation feedback]
- Format: "[Anti-pattern]: [Example] → [Consequence] → [Alternative]"

**Code Quality Observations**:
- [Specific code quality feedback given]

### 3. Planning & Process Feedback

**Effective Practices**:
- [List all positive planning/process feedback]

**Process Gaps**:
- [List all planning/process improvement suggestions]

**Methodology Observations**:
- [Feedback on approach, methodology, workflow]

### 4. Documentation Feedback

**Documentation Strengths**:
- [Positive documentation feedback]

**Documentation Gaps**:
- [Missing or insufficient documentation areas]

**Knowledge Management**:
- [Feedback on pattern capture, lessons learned, knowledge systematization]

### 5. Operational Feedback

**Production Readiness**:
- [Feedback on monitoring, error handling, deployment]

**Observability**:
- [Feedback on logging, metrics, alerting]

**Risk Management**:
- [Feedback on error handling, edge cases, failure modes]

### 6. Strategic & Vision Feedback

**Vision Clarity**:
- [Feedback on long-term planning, roadmaps, strategic thinking]

**Trade-off Analysis**:
- [Feedback on decision-making, prioritization, resource allocation]

**Scalability Thinking**:
- [Feedback on growth planning, architectural scalability]

---

## Thematic Analysis

### Recurring Themes (Positive)
1. [Theme]: [Frequency] occurrences
   - Evidence: [Examples from different contexts]
   - Impact: [Why this matters]

### Recurring Themes (Areas for Improvement)
1. [Theme]: [Frequency] occurrences
   - Evidence: [Examples from different contexts]
   - Impact: [Cost of not addressing]
   - Recommended action: [Specific fix]

### Evolution Over Time
- Early period: [Feedback patterns]
- Mid period: [Feedback patterns]
- Recent period: [Feedback patterns]
- Trajectory: [Improving | Stable | Declining] in [specific areas]

---

## Actionable Recommendations

### High Priority (Do Immediately)
1. [Recommendation]
   - Based on: [Feedback references]
   - Expected impact: [Specific improvement]
   - Time investment: [Estimate]

### Medium Priority (Next Sprint/Month)
1. [Recommendation]
   - Based on: [Feedback references]
   - Expected impact: [Specific improvement]
   - Time investment: [Estimate]

### Low Priority (Backlog)
1. [Recommendation]
   - Based on: [Feedback references]
   - Expected impact: [Specific improvement]
   - Time investment: [Estimate]

### Anti-Recommendations (Don't Do)
1. [What NOT to do]
   - Rationale: [Why this would be a mistake]
   - Alternative: [Better approach]

---

## Feedback Metrics

**Total Feedback Items**: [Count]
**Positive Feedback**: [Count] ([Percentage]%)
**Constructive Feedback**: [Count] ([Percentage]%)
**Critical Feedback**: [Count] ([Percentage]%)

**Feedback Distribution by Domain**:
- Architecture: [Count]
- Implementation: [Count]
- Planning: [Count]
- Documentation: [Count]
- Operations: [Count]
- Strategy: [Count]

**Response to Feedback**:
- Implemented: [Count] items
- Acknowledged but not yet addressed: [Count] items
- Rejected/Disagreed: [Count] items

---

## Learning Extraction

### Key Lessons Learned
1. [Lesson]: [Feedback that led to this insight]
2. [Lesson]: [Feedback that led to this insight]
3. [Lesson]: [Feedback that led to this insight]

### Pattern Library Additions
[Patterns that should be documented for reuse based on feedback]

### Anti-Pattern Library Additions
[Anti-patterns to avoid based on feedback]

### Process Improvements
[Workflow or process changes suggested by feedback]

---

## Next Period Focus

Based on consolidated feedback, the next [week/month/quarter] should prioritize:

1. **Primary Focus**: [Domain/area]
   - Rationale: [Why this matters most]
   - Success criteria: [How to measure improvement]

2. **Secondary Focus**: [Domain/area]
   - Rationale: [Why this matters]
   - Success criteria: [How to measure improvement]

3. **Maintenance Focus**: [Domain/area]
   - Rationale: [Why to sustain current level]
   - Success criteria: [How to measure maintenance]

**Feedback Loop**:
- Monitor: [Specific metrics to track]
- Validate: [How to confirm feedback was addressed]
- Iterate: [Next round of improvements]
```

---

## Usage Guidelines

### When to Use Prompt 1 (Comprehensive Assessment)
- **Frequency**: Monthly (1st of each month)
- **Context Required**:
  - Recent work summary (2-4 weeks)
  - Code examples
  - Documentation created
  - Decisions made
- **Output**: Numerical scores, percentile rankings, trend analysis, recommendations

### When to Use Prompt 2 (Feedback Consolidation)
- **Frequency**: End of project phase, quarterly reviews, or on-demand
- **Context Required**:
  - All feedback from specified time period
  - Session transcripts
  - Decision logs
- **Output**: Thematic analysis, actionable recommendations, learning extraction

### Combining Both Prompts
1. **Monthly**: Use Prompt 1 for systematic capability tracking
2. **Quarterly**: Use Prompt 2 to consolidate feedback themes
3. **Compare**: Track how feedback themes correlate with capability scores
4. **Adjust**: Modify focus areas based on combined insights

---

## Prompt Maintenance

**Version**: 1.1
**Last Updated**: 2025-11-10
**Next Review**: 2025-12-01

**Calibration Notes**:
- Percentile benchmarks based on observed DEX bot developer community
- Scoring rubric refined through monthly application
- Comparative examples updated quarterly

**Improvement Log**:
- 2025-11-10: Fixed hallucinated sample size (~200-300 → ~10-20 developers, ~20-30 projects), added Claude Code persona as bot dev team lead, added sample limitation disclaimer, emphasized honest benchmarking from direct experience only
