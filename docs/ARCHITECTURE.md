# Architecture

```text
X Monitor ─┐
           ├─ Signal Ingestion Routines ─┐
Geo-Alpha ─┘                              │
                                          ├─ Signal Fusion + Risk Engine ── Condor Trading Agent Session
Hummingbot Candles ─ Kronos Forecast ─────┘                                   │
                                                                              ├─ Position/Grid/TWAP Executors
Portfolio/Orders/Positions ─ Risk State ──────────────────────────────────────┘
                                                                              │
                                                              Hummingbot API / Gateway / Exchanges
```

## Components

### Signal ingestion routines

Normalize X-monitor outputs, Geo-Alpha reports, and Hummingbot market data into timestamped signal objects.

### Kronos forecast routine

Fetches candles from Hummingbot API, formats OHLCV DataFrames, runs selected Kronos model, and outputs directional bias, forecast range, and confidence metadata.

### Signal fusion and risk engine

Combines Kronos, social, macro/on-chain, and market data into trade eligibility. Applies drawdown, sizing, stale-data, liquidity, and conflict gates.

### Executor planner

Maps approved decisions to bounded Condor/Hummingbot executor configs. No raw unbounded trade action should bypass this layer.

### Evidence ledger

Writes session journals, signal snapshots, decisions, rejected alternatives, executor outcomes, P&L attribution, and failure events.

## Repository layout proposal

```text
kronos-condor-cup/
├── PROJECT.md
├── README.md
├── SKILL-SELECTION.md
├── BUILD-PLAN.md
├── AGENTS.md
├── context/
│   ├── CONDOR-CONTEXT.md
│   ├── KRONOS-CONTEXT.md
│   ├── X-MONITOR-CONTEXT.md
│   └── GEO-ALPHA-CONTEXT.md
├── agent-instructions/
│   └── ALWAYS-ON-AGENT.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RISK-POLICY.md
│   └── EVIDENCE-PLAN.md
├── research/
│   └── RESEARCH-MEMO.md
├── ops/
│   └── DEPLOYMENT-PLAN.md
└── work_logs/
```
