# Deployment Plan Draft

## Local development

- Condor repo as source dependency or fork baseline.
- Kronos model cache stored outside git.
- Secrets in `.env` only, never committed.
- Hummingbot API and Condor run locally for dry-run testing.

## Competition runtime

- One always-on Condor agent session.
- Deterministic routines scheduled per signal class.
- Journal and evidence artifacts persisted.
- Health monitor alerts on stale data, API errors, and drawdown.

## Human gates

- Approve connector credentials.
- Approve risk limits.
- Approve live trading switch.
- Approve competition deployment.
