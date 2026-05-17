# Risk Policy Draft

## Default posture

Dry-run first. Live trading remains disabled until human approval.

## Required gates before live trades

- Exchange connector selected and tested.
- Backtest completed for selected strategy.
- Dry-run completed for at least one full decision loop.
- Secrets stored outside git.
- Human approval recorded.

## Trading controls

- Max strategy allocation: human decision needed.
- Max asset allocation: human decision needed.
- Max drawdown stop: human decision needed.
- Cooldown after losing streak: required.
- Every executor needs stop loss, take profit or exit condition, and time limit.
- Long-tail tokens need liquidity and contract/token safety checks.

## Kill switches

Stop new entries when:

- Data is stale.
- API errors persist.
- Spread/slippage exceeds threshold.
- Stablecoin peg health fails.
- Drawdown threshold breached.
- Agent journal cannot be written.
