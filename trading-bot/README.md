# Multi-Exchange Trading Bot

A risk-first, multi-exchange algorithmic trading framework that runs across
**Binance**, **KuCoin**, and **Bybit** through one unified interface. It focuses
on a curated universe of relatively *safer* crypto assets (large-cap majors plus
tokenized gold/silver) and applies disciplined strategies with strict risk
controls and **equity-based compounding**.

> ⚠️ **Read this first — honest expectations**
>
> **No trading bot can guarantee 1–5% profit every single day.** A steady 1%/day
> compounds to ~3,700% per year; 5%/day to billions of percent. If that were
> achievable on demand, the operator would own the entire market within months.
> Real markets produce **winning days and losing days**. Anyone — human or bot —
> who *promises* fixed daily returns is selling a scam.
>
> What this project actually does:
> - **Targets** modest daily gains while putting **capital preservation first**.
> - Defaults to **paper trading** (no real money) so you validate before risking a cent.
> - Enforces stop-losses, position sizing, and a **daily-loss circuit breaker**.
> - Lets you **backtest** every strategy on historical data before going live.
>
> Trading carries real risk of loss. Only ever trade money you can afford to lose,
> and understand the code before enabling live mode. This is software, not
> financial advice.

## What it trades

These crypto exchanges do **not** list real-world equities or physical
gold/silver. The closest *safer* instruments available on-exchange are:

| You asked for | What the bot actually uses |
|---------------|----------------------------|
| Gold          | **PAXG** (Pax Gold) / **XAUT** (Tether Gold) — 1 token ≈ 1oz gold |
| Silver        | Tokenized silver where listed (e.g. `KAG`/`XAGx` on some venues) |
| "Safest coins"| BTC, ETH, BNB, SOL, XRP, ADA and other top-cap majors (deepest liquidity, lowest slippage) |
| Stablecoin parking | USDT / USDC held when no good signal exists |

The asset universe is fully configurable in `config/config.yaml` — add or remove
any pair your exchange lists. Tokenized gold/silver is optional; the default
universe is a basket of high-liquidity majors.

## Architecture

```
trading-bot/
  src/
    exchanges/      # Unified adapter over Binance / KuCoin / Bybit (ccxt-based)
    strategies/     # Pluggable signal generators (EMA, RSI mean-reversion, momentum, ensemble)
    strategies/     # + router.py (per-coin selection) + performance.py (live stats)
    risk/           # Position sizing, stop-loss / take-profit, daily circuit breaker
    portfolio/      # Equity tracking + compounding engine
    notify/         # Slack alerts (incoming webhook, stdlib only)
    web/            # Flask dashboard + admin settings (charts, config/keys editor)
    data/           # OHLCV fetch + technical indicators
    utils/          # Logging, config loading
    configio.py     # Read/write config.yaml + .env for the settings page
    state.py        # Atomic JSON snapshot shared bot -> dashboard
    engine.py       # Main trading loop (paper or live) + config hot-reload
    backtest.py     # Historical simulator
    evaluate.py     # Rank every strategy on every coin -> recommended routing
    main.py         # CLI entry point
  config/config.yaml
  Dockerfile        # 24/7 container image
  docker-compose.yml
  tests/
```

## Strategies & indicators

**Indicators:** EMA (12/26), RSI (14, Wilder), ATR (14), ROC/Momentum.

| Strategy | Indicators | Best in |
|---|---|---|
| `ema_crossover` | EMA 12/26 | Trends |
| `rsi_mean_reversion` | RSI 14 | Ranges |
| `momentum` | ROC | Breakouts |
| `ensemble` | all three (majority vote) | Mixed — combines their strengths |

**Multi-strategy selection** (`strategy_selection.mode`): `single`, `routing`
(per-coin map), or `auto` (adaptive — picks the best live performer per coin,
falling back to backtest recommendations). Run `python -m src.main evaluate` to
rank every strategy on every coin and generate a recommended routing map, then
apply it from the dashboard. See `docs/STRATEGY.md`.

## Web dashboard & admin

```bash
python -m src.main dashboard      # http://localhost:8000  (or the compose service)
```

- **Dashboard:** equity curve, drawdown, PnL & win-rate **by strategy**,
  per-coin active-vs-recommended table, open positions, recent trades. Read-only.
- **Settings (`/settings`):** edit **every** config value and **all API keys**
  from the browser. Writes are gated behind `ADMIN_TOKEN` (set it in `.env`);
  with it unset the UI is read-only. Risk/strategy/universe edits **hot-reload**
  into the running bot; exchange keys/mode need a restart.

## Quick start

```bash
cd trading-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Configure your universe, risk limits and strategy
cp .env.example .env        # add API keys ONLY when you're ready for live mode
$EDITOR config/config.yaml

# 2. Backtest a strategy on historical data (no keys needed)
python -m src.main backtest --symbol BTC/USDT --strategy ensemble --days 180

# 3. Run live in PAPER mode (default — simulated fills, no real orders)
python -m src.main run

# 4. ONLY after you trust it: enable live trading
#    set mode: live in config.yaml and provide API keys in .env
```

## Run it 24/7 with Docker

```bash
cd trading-bot
cp .env.example .env          # add keys only when going live; Slack URL optional
docker compose up -d --build  # starts in the background (paper mode by default)
docker compose logs -f        # watch live activity
docker compose down           # stop
```

`restart: unless-stopped` auto-recovers the bot across crashes and host reboots.
`config/` is mounted read-only, so you can tweak `config.yaml` and `docker
compose restart` without rebuilding. Logs persist on the host under `./logs`.

## Slack alerts

Telegram can be unreliable in some regions (missed/delayed alerts); Slack
Incoming Webhooks deliver consistently worldwide and need no app token.

1. Create a webhook: <https://api.slack.com/messaging/webhooks>
2. Put the URL in `.env` as `SLACK_WEBHOOK_URL=...`
3. Set `notifications.enabled: true` in `config/config.yaml`

You'll get pinged on **entries, exits, and the daily circuit breaker**. Tune
`notifications.min_level` (`info` = everything incl. heartbeats, `trade` =
trades + alerts, `alert` = circuit-breaker only). Alert delivery never blocks or
crashes the trading loop — a failed send is logged and skipped.

## Demo week → go live

The intended workflow: run in **paper mode for ~1 week** to learn each coin, then
go live. The bot persists its progress to `logs/session.json` every loop, so a
restart **resumes** — your week of learning isn't lost. At the end:

```bash
python -m src.main report     # readiness report with a go/no-go verdict per coin
```

Full step-by-step in **`docs/DEMO_WEEK.md`**.

## Safety defaults

- `mode: paper` — simulated execution until you explicitly switch to `live`.
- `risk.max_position_pct` — capped fraction of equity per position.
- `risk.stop_loss_pct` / `take_profit_pct` — every position gets a hard stop.
- `risk.daily_loss_limit_pct` — bot halts for the day if breached (circuit breaker).
- API keys are read from environment variables, never committed.
- Use **read-only or trade-only** API keys. **Never enable withdrawal permissions.**

## Disclaimer

This software is provided for educational purposes and as an engineering
framework. It is **not** financial advice and comes with **no guarantee of
profit**. You are solely responsible for any trades it places. The authors
accept no liability for financial losses.
