# Demo week → go live: the safe playbook

Your plan — **run in paper (demo) mode for ~1 week to learn each coin, then go
live with real money** — is exactly the right approach. This is the step-by-step.

## Day 0 — set up the demo

1. **Seed the per-coin knowledge from history** (months of data, not just a week):
   ```bash
   python -m src.main evaluate --days 180
   ```
   This backtests every strategy on every coin and writes a recommended
   strategy-per-coin map to `logs/evaluation.json`.

2. **Confirm demo settings** in `config/config.yaml`:
   - `mode: paper`  ← no real money
   - `strategy_selection.mode: auto`  ← learns the best strategy per coin
   - Keep the conservative `risk:` defaults (2% stop, 3% daily circuit breaker).

3. **Start the bot + dashboard** (runs unattended, survives restarts):
   ```bash
   docker compose up -d --build
   # dashboard: http://localhost:8000
   ```
   Optional: set up Slack alerts and `ADMIN_TOKEN` so you can watch and tweak
   from your phone.

## Days 1–7 — let it learn

- The bot trades on simulated balances and **records every trade per coin and
  per strategy**. Progress is saved to `logs/session.json` every loop, so a
  restart (or container redeploy) **resumes** — your week of learning is not lost.
- Watch the dashboard: equity curve, drawdown, **PnL by strategy**, and the
  **per-coin active-vs-recommended** table fill in as trades happen.
- In `auto` mode, once a coin has enough trades (`auto.min_trades`, default 5)
  the bot switches that coin to its best-performing strategy automatically.
- **Stay updated without watching:** set `notifications.report_every_hours: 24`
  to get the readiness report in Slack every day, or download it anytime from the
  dashboard's **⬇ Report** link.

## Day 7 — decide what goes live

```bash
python -m src.main report
```

You get a **readiness report** with a verdict per coin:

| Verdict | Meaning | Action |
|---|---|---|
| **READY** | Profitable with a healthy win rate over enough trades | Keep for live |
| **PROMISING** | Profitable but lower win rate | Keep, watch closely |
| **NEEDS MORE DATA** | Too few trades to judge | Demo longer before risking money |
| **AVOID** | Lost money in demo | Drop from the universe |

Trim your `universe:` to the READY/PROMISING coins (you can do this right from
the **Settings** page).

> ⚠️ **Honest caveat:** one week is enough to validate that the plumbing works
> and to get a feel — but it's usually **too few trades to *finalize* per-coin
> strategies** with confidence. Weight the `evaluate` backtest (months of data)
> more heavily than a single week of live demo when deciding. A coin that looks
> great for 7 days can still be noise.

## Going live (only when you're satisfied)

1. Create **trade-only** API keys on the exchange — **never enable withdrawals**.
   Restrict by IP if possible. Add them via the Settings page or `.env`.
2. In `config/config.yaml`:
   - `mode: live`
   - `use_sandbox: false` (or keep `true` to test live plumbing on the testnet first)
3. **Start small** — the smallest amount you can afford to lose entirely.
4. `docker compose up -d` and watch the first live trades closely.

The same risk controls (stop-loss, exposure caps, daily circuit breaker) and
compounding apply automatically in live mode. Scale up only after live results
match your demo expectations over time.

## Reality check (read once more)

No bot can guarantee 1–5% **daily**. Markets have losing days and weeks. This
framework is built to pursue steady gains while **protecting your capital** —
the demo week exists precisely so you risk real money only on what you've seen
work. See `docs/STRATEGY.md` for the math.
