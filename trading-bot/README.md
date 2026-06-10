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
| "Safest coins"| BTC, ETH and other top-cap majors (deepest liquidity, lowest slippage) |
| Stablecoin parking | USDT / USDC held when no good signal exists |

The asset universe is fully configurable in `config/config.yaml`.

## Architecture

```
trading-bot/
  src/
    exchanges/      # Unified adapter over Binance / KuCoin / Bybit (ccxt-based)
    strategies/     # Pluggable signal generators (EMA, RSI mean-reversion, momentum, ensemble)
    risk/           # Position sizing, stop-loss / take-profit, daily circuit breaker
    portfolio/      # Equity tracking + compounding engine
    data/           # OHLCV fetch + technical indicators
    utils/          # Logging, config loading
    engine.py       # Main trading loop (paper or live)
    backtest.py     # Historical simulator
    main.py         # CLI entry point
  config/config.yaml
  tests/
```

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
