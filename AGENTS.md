# Agent Instructions for Contributors

- Plan before coding.
- Keep trading disabled by default.
- Do not commit secrets, keys, wallets, or real account data.
- Any live trading change requires human approval.
- Every feature must leave evidence: tests, dry-run logs, or backtest output.
- Prefer small vertical slices with clear acceptance criteria.
- Use Condor/Hummingbot executors for bounded execution; avoid raw unbounded order placement.
