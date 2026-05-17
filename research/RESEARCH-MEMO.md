# Research Memo

## Condor implications

Condor separates LLM reasoning from deterministic execution through Condor Server and Hummingbot API. This supports competition safety because the agent can reason, but execution still runs through fixed routines, executor configs, and Hummingbot connectors.

Useful Condor primitives:

- Trading agent sessions for tick history, prompts, tool calls, and replayable decisions.
- Routines for deterministic signal scoring, forecasting, risk checks, and report generation.
- Executors for bounded trade operations:
  - Position Executor for TP/SL/trailing/time-limited trades.
  - Grid Executor for range strategies.
  - TWAP/DCA for staged entry/exit.
  - XEMM/arbitrage only after latency and liquidity validation.
- Controller IDs for P&L attribution across strategies.
- Backtesting for parameter research and submission evidence.

## Botcamp Cup implications

The 48-hour live window rewards uptime, defensive risk controls, fast adaptation, and clear decision rules. Because no manual intervention is allowed, the agent needs pre-approved policies, kill-switches, stale-data handling, and automatic reporting.

## Kronos implications

Kronos is an open-source foundation model for OHLCV/K-line sequences trained on 45+ exchanges. The open model options are:

- Kronos-mini: 4.1M params, context length 2048.
- Kronos-small: 24.7M params, context length 512.
- Kronos-base: 102.3M params, context length 512.

Recommended role: forecasting input and sanity filter, not a sole trading trigger. It should output directional bias, predicted volatility/range, and agreement/conflict against social and macro signals.

Constraints:

- Requires clean OHLC columns and optional volume/amount.
- Torch runtime and model download need packaging decisions.
- Forecasts must be logged as probabilistic signals.

## X-monitor and Geo-Alpha implications

X-monitor provides fast social narrative detection from configured accounts, token resolution, liquidity filters, and a dry-run-first trade pipeline. Geo-Alpha provides event-driven macro/on-chain context, stablecoin health checks, gas context, and structured trade plans.

Signal fusion should require at least two independent confirmations before raising exposure:

1. Kronos price-action forecast.
2. Geo-Alpha macro/on-chain regime.
3. X-monitor narrative/social catalyst.
4. Hummingbot market data sanity checks.

## Ranked strategy archetypes

1. Major-asset regime positioning: BTC/ETH/AAVE via Position Executor, driven by Geo-Alpha + Kronos + market data. Best fit for liquidity and explainability.
2. Adaptive grid/range scalping: Grid Executor with Kronos range/volatility calibration. Best fit for consistency if conditions stay range-bound.
3. Social-macro momentum confirmation: X-monitor tokens gated by liquidity, Kronos, and macro filters. Strong narrative but higher noise and liquidity risk.
