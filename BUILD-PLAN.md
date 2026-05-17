# Implementation Plan: Kronos Condor Cup

## Overview
Build a Condor-based trading system for the Condor Builders Cup that runs with no manual intervention, starts on Gate.io, trades BTC/ETH plus a small RWA watchlist, and uses multi-strategy controller IDs for clear P&L attribution. Kronos provides forecast and regime input. X-monitor and Geo-Alpha provide external signal context. Condor built-in backtests are the first proof gate.

## Architecture Decisions
- **Single primary venue first: Gate.io.** Keep the first implementation narrow so backtests and failure handling stay tractable.
- **Multi-strategy with controller IDs.** Isolate major-asset, grid, and social-macro strategies so results can be compared cleanly.
- **Kronos is a forecast/filter layer, not a direct executor.** Run it as a separate runtime target on Akash, with a local fallback for development.
- **Signal fusion is required before execution.** A trade needs support from at least two of: Kronos, X-monitor, Geo-Alpha, and Hummingbot market data.
- **Backtests first, live later.** Use Condor's built-in backtesting before any dry-run or live deployment.
- **Public repo only after cleanup.** Keep secrets, credentials, and live config out of git before publishing.

## Task List

### Phase 0: Scope lock and repo hygiene

#### Task 0.1: Finalize build inputs and asset list
**Description:** Lock the first asset universe and the first RWA watchlist so later routines and backtests use one stable target set.

**Acceptance criteria:**
- [ ] Primary venue is fixed to Gate.io.
- [ ] Core assets are fixed to BTC and ETH.
- [ ] RWA watchlist is a short, liquid list with documented inclusion criteria.
- [ ] Drawdown limit and per-trade cap are written down.

**Verification:**
- [ ] `OPEN-QUESTIONS.md` is reduced to only unresolved deployment questions.
- [ ] Asset list appears in `PROJECT.md`.

**Dependencies:** None

**Files likely touched:**
- `PROJECT.md`
- `OPEN-QUESTIONS.md`
- `docs/RISK-POLICY.md`

**Estimated scope:** Small

#### Task 0.2: Choose repo visibility and remote policy
**Description:** Decide how the public GitHub repo will be created and what must stay private.

**Acceptance criteria:**
- [ ] Repo visibility decision is recorded.
- [ ] Secret-handling rules are written.
- [ ] Public release conditions are listed.

**Verification:**
- [ ] `AGENTS.md` includes repo and secret rules.
- [ ] `README.md` states the public-release gate.

**Dependencies:** Task 0.1

**Files likely touched:**
- `AGENTS.md`
- `README.md`
- `docs/EVIDENCE-PLAN.md`

**Estimated scope:** Small

### Phase 1: Context and contracts

#### Task 1.1: Define normalized signal schema
**Description:** Create one structured contract for Kronos forecasts, X-monitor signals, Geo-Alpha reports, and market data.

**Acceptance criteria:**
- [ ] All signal sources map to one schema.
- [ ] Each signal includes timestamp, source, confidence, staleness, asset, and action hint.
- [ ] Schema supports conflict and agreement scoring.

**Verification:**
- [ ] Schema documented in `docs/ARCHITECTURE.md`.
- [ ] Context files agree on the same fields.

**Dependencies:** Task 0.1

**Files likely touched:**
- `docs/ARCHITECTURE.md`
- `context/KRONOS-CONTEXT.md`
- `context/X-MONITOR-CONTEXT.md`
- `context/GEO-ALPHA-CONTEXT.md`

**Estimated scope:** Medium

#### Task 1.2: Define risk policy schema
**Description:** Write the risk rules that control all live decisions and dry-run behavior.

**Acceptance criteria:**
- [ ] Max drawdown, per-trade cap, per-strategy cap, and cooldown rules are documented.
- [ ] Every executor requires exit logic and time limit.
- [ ] Stale-data and API-failure kill switches are defined.

**Verification:**
- [ ] `docs/RISK-POLICY.md` exists and is dry-run safe.
- [ ] `agent-instructions/ALWAYS-ON-AGENT.md` matches the policy.

**Dependencies:** Task 0.1

**Files likely touched:**
- `docs/RISK-POLICY.md`
- `agent-instructions/ALWAYS-ON-AGENT.md`
- `PROJECT.md`

**Estimated scope:** Medium

#### Task 1.3: Define controller-ID mapping and strategy roles
**Description:** Assign controller IDs to the major-asset, grid, and social-macro strategies so P&L attribution stays separated.

**Acceptance criteria:**
- [ ] Each strategy has a unique controller ID.
- [ ] Each controller has one sentence describing its role.
- [ ] No strategy can execute outside its controller boundary.

**Verification:**
- [ ] `PROJECT.md` documents the controller plan.
- [ ] `docs/ARCHITECTURE.md` shows strategy isolation.

**Dependencies:** Task 1.1, Task 1.2

**Files likely touched:**
- `PROJECT.md`
- `docs/ARCHITECTURE.md`
- `BUILD-PLAN.md`

**Estimated scope:** Small

### Checkpoint: After Phase 1
- [ ] Signal schema documented
- [ ] Risk policy documented
- [ ] Controller-ID mapping documented
- [ ] Human approval before any build code

### Phase 2: Deterministic routines

#### Task 2.1: Build X-monitor ingestion routine
**Description:** Convert X-monitor output into normalized signal records for Condor routines.

**Acceptance criteria:**
- [ ] Routine reads existing X-monitor artifacts.
- [ ] Routine emits structured signal records only.
- [ ] Routine never executes trades directly.

**Verification:**
- [ ] Dry-run output is timestamped and reproducible.
- [ ] Negative case: no trade action appears in output.

**Dependencies:** Task 1.1, Task 1.2

**Files likely touched:**
- `agent-instructions/ALWAYS-ON-AGENT.md`
- `docs/ARCHITECTURE.md`
- future `routines/x_monitor_ingest.py`

**Estimated scope:** Medium

#### Task 2.2: Build Geo-Alpha ingestion routine
**Description:** Parse geopolitical and on-chain regime notes into decision-ready signals.

**Acceptance criteria:**
- [ ] Routine extracts regime, catalyst, affected asset, and invalidation.
- [ ] Routine tags confidence and freshness.
- [ ] Routine never overrides risk policy.

**Verification:**
- [ ] Dry-run output matches the report structure.
- [ ] At least one conflict case is represented.

**Dependencies:** Task 1.1, Task 1.2

**Files likely touched:**
- `context/GEO-ALPHA-CONTEXT.md`
- `docs/ARCHITECTURE.md`
- future `routines/geo_alpha_ingest.py`

**Estimated scope:** Medium

#### Task 2.3: Build Kronos forecast routine
**Description:** Fetch candles, format them for Kronos, and emit forecast bias and range metadata.

**Acceptance criteria:**
- [ ] Inputs follow OHLC or OHLCV format.
- [ ] Output includes forecast bias, range, and model identifier.
- [ ] Routine supports local dev and Akash runtime assumptions.

**Verification:**
- [ ] Forecast output is versioned and timestamped.
- [ ] A long context input is truncated or rejected by policy.

**Dependencies:** Task 1.1

**Files likely touched:**
- `context/KRONOS-CONTEXT.md`
- `ops/DEPLOYMENT-PLAN.md`
- future `routines/kronos_forecast.py`

**Estimated scope:** Medium

#### Task 2.4: Build market data sanity routine
**Description:** Validate that market data is fresh enough before any trade decision proceeds.

**Acceptance criteria:**
- [ ] Routine checks candle freshness and spread/liquidity sanity.
- [ ] Routine can block execution on stale data.
- [ ] Routine returns a simple pass/fail plus reasons.

**Verification:**
- [ ] Stale-data test case returns fail.
- [ ] Fresh-data test case returns pass.

**Dependencies:** Task 1.2

**Files likely touched:**
- `docs/RISK-POLICY.md`
- `docs/ARCHITECTURE.md`
- future `routines/market_sanity.py`

**Estimated scope:** Small

### Checkpoint: After Phase 2
- [ ] All signal routines output structured records
- [ ] No routine can place a trade directly
- [ ] Stale-data gating works
- [ ] Signal logs are journal-ready

### Phase 3: Signal fusion and strategy selection

#### Task 3.1: Build the signal fusion engine
**Description:** Merge Kronos, X-monitor, Geo-Alpha, and market data into a single decision score.

**Acceptance criteria:**
- [ ] Engine scores agreement and conflict across sources.
- [ ] Engine can return hold, open, reduce, or close recommendations.
- [ ] Engine writes why a trade was rejected.

**Verification:**
- [ ] At least one agreement case and one conflict case are documented.
- [ ] Rejected trades are logged.

**Dependencies:** Task 1.1, Task 1.2, Task 2.1, Task 2.2, Task 2.3, Task 2.4

**Files likely touched:**
- `docs/ARCHITECTURE.md`
- future `routines/signal_fusion.py`
- future `routines/decision_router.py`

**Estimated scope:** Medium

#### Task 3.2: Create the strategy router
**Description:** Route approved decisions into the three strategy archetypes and the correct controller ID.

**Acceptance criteria:**
- [ ] Major-asset strategy can be selected.
- [ ] Grid strategy can be selected.
- [ ] Social-macro strategy can be selected.
- [ ] Each route includes the target controller ID.

**Verification:**
- [ ] Router returns one bounded action per input.
- [ ] Router never emits unbounded execution commands.

**Dependencies:** Task 1.3, Task 3.1

**Files likely touched:**
- `PROJECT.md`
- `docs/ARCHITECTURE.md`
- future `routines/strategy_router.py`

**Estimated scope:** Medium

#### Task 3.3: Define executor templates for Gate.io
**Description:** Prepare bounded executor templates for Gate.io-compatible usage.

**Acceptance criteria:**
- [ ] Templates include stop loss, target or exit rule, and time limit.
- [ ] Templates fit the major, grid, and social-macro archetypes.
- [ ] Templates are controller-aware.

**Verification:**
- [ ] Each template can be described in one backtest case.
- [ ] No template depends on manual intervention.

**Dependencies:** Task 1.2, Task 3.2

**Files likely touched:**
- `docs/ARCHITECTURE.md`
- `docs/RISK-POLICY.md`
- future `executors/*.py`

**Estimated scope:** Medium

### Checkpoint: After Phase 3
- [ ] Fusion engine returns deterministic decisions
- [ ] Strategy router assigns controller IDs
- [ ] Executor templates are bounded
- [ ] Trade/no-trade reasons are logged

### Phase 4: Backtesting and evidence

#### Task 4.1: Build Condor backtest plan for the three archetypes
**Description:** Define how each strategy will be tested with Condor's built-in backtest feature.

**Acceptance criteria:**
- [ ] Each archetype has a backtest scenario.
- [ ] Each scenario has input assumptions and expected outputs.
- [ ] Each scenario is tied to one controller ID.

**Verification:**
- [ ] Backtest spec is written before any code.
- [ ] Each spec produces a judge-readable report template.

**Dependencies:** Task 3.1, Task 3.2

**Files likely touched:**
- `research/RESEARCH-MEMO.md`
- `docs/EVIDENCE-PLAN.md`
- `BUILD-PLAN.md`

**Estimated scope:** Small

#### Task 4.2: Run comparative backtests for majors vs majors+RWA
**Description:** Compare the main asset set with and without the RWA watchlist to see if complexity is worth it.

**Acceptance criteria:**
- [ ] Backtest comparison criteria are written.
- [ ] The RWA list can be justified or removed from the live set.
- [ ] Results are stored in the evidence plan.

**Verification:**
- [ ] The comparison leads to one documented asset decision.
- [ ] Results are reproducible from saved inputs.

**Dependencies:** Task 4.1

**Files likely touched:**
- `docs/EVIDENCE-PLAN.md`
- `PROJECT.md`
- future `reports/backtest-*.md`

**Estimated scope:** Medium

#### Task 4.3: Create the evidence bundle layout
**Description:** Prepare the directory layout and document list for judge-facing evidence.

**Acceptance criteria:**
- [ ] Backtests, journals, signals, and risk logs have dedicated locations.
- [ ] Public repo cleanup requirements are listed.
- [ ] Submission checklist is complete.

**Verification:**
- [ ] Evidence layout is referenced from `README.md`.
- [ ] Human can find each artifact without guessing.

**Dependencies:** Task 4.1, Task 4.2

**Files likely touched:**
- `docs/EVIDENCE-PLAN.md`
- `README.md`
- `BUILD-PLAN.md`

**Estimated scope:** Small

### Checkpoint: After Phase 4
- [ ] Backtest plan exists for each archetype
- [ ] Majors vs majors+RWA comparison exists
- [ ] Evidence bundle layout is ready
- [ ] Strategy choice can be defended

### Phase 5: Dry-run integration

#### Task 5.1: Wire the chosen path into a dry-run Condor session
**Description:** Connect the selected strategy path to a no-capital loop so the agent can run autonomously without live orders.

**Acceptance criteria:**
- [ ] Dry-run loop starts and stops cleanly.
- [ ] No live trade execution is possible in this mode.
- [ ] Session journal is written.

**Verification:**
- [ ] One full dry-run cycle completes.
- [ ] Journal shows no manual intervention.

**Dependencies:** Task 3.1, Task 3.2, Task 4.3

**Files likely touched:**
- `agent-instructions/ALWAYS-ON-AGENT.md`
- `docs/ARCHITECTURE.md`
- future `sessions/*.md`

**Estimated scope:** Medium

#### Task 5.2: Validate failure handling in dry-run
**Description:** Make sure the system reacts safely to stale data, API failure, model failure, and risk breaches.

**Acceptance criteria:**
- [ ] Stale data stops new entries.
- [ ] API failure prevents new trades.
- [ ] Drawdown breach triggers risk shutdown.
- [ ] Kronos failure falls back to safe behavior.

**Verification:**
- [ ] Failure cases are listed and tested.
- [ ] No failure case results in uncontrolled execution.

**Dependencies:** Task 5.1

**Files likely touched:**
- `docs/RISK-POLICY.md`
- `docs/EVIDENCE-PLAN.md`
- future test files

**Estimated scope:** Medium

### Checkpoint: After Phase 5
- [ ] Dry-run loop works
- [ ] Failure handling is safe
- [ ] Session journal is complete
- [ ] No manual intervention required

### Phase 6: Competition hardening and release prep

#### Task 6.1: Prepare the public repo cleanup pass
**Description:** Strip secrets, trim private notes, and make the repo safe for public visibility.

**Acceptance criteria:**
- [ ] No secrets or credentials remain in tracked files.
- [ ] README explains setup and scope clearly.
- [ ] Private operational notes are removed or isolated.

**Verification:**
- [ ] Secret scan passes.
- [ ] README is readable by a new builder.

**Dependencies:** Task 5.1, Task 5.2

**Files likely touched:**
- `README.md`
- `AGENTS.md`
- `PROJECT.md`

**Estimated scope:** Small

#### Task 6.2: Write submission package and pitch
**Description:** Build the final judge-facing package with the story, evidence, and key results.

**Acceptance criteria:**
- [ ] README, pitch, and demo notes are complete.
- [ ] Evidence links are organized.
- [ ] Submission checklist is complete.

**Verification:**
- [ ] A reviewer can follow the package without extra context.
- [ ] Package lists the project story in one paragraph.

**Dependencies:** Task 6.1

**Files likely touched:**
- `README.md`
- `docs/EVIDENCE-PLAN.md`
- `PROJECT.md`

**Estimated scope:** Medium

### Checkpoint: After Phase 6
- [ ] Dry-run complete
- [ ] Repo cleaned for publication
- [ ] Submission package ready
- [ ] Human approval required before any live switch

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Too many venues | High | Start with Gate.io only |
| Too many assets | High | Keep RWA list short and liquid |
| Kronos deployment delay on Akash | Medium | Keep local fallback |
| Social signal noise | High | Curate sources and require fusion confirmation |
| Backtest overfit | High | Compare multiple strategy slices and keep sizing conservative |
| Public repo leaks secrets | High | Clean repo before public release |
| Hard live event failures | High | Add stale-data, API-failure, and drawdown kill switches |

## Open Questions
- Which exact RWA assets survive the liquidity filter?
- What is the final drawdown and per-trade cap after backtest results?
- Which strategy wins the first backtest comparison?
- Should the public repo remain public from day one, or go public only after the dry-run package is ready?
