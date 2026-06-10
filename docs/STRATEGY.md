# Strategy & risk design

## The honest math on "1–5% daily"

Compounding cuts both ways. Starting from $10,000:

| Daily return | After 1 month (~21 trading days) | After 1 year (~252 days) |
|--------------|----------------------------------|--------------------------|
| 1%           | $12,300                          | $122,000 (12x)           |
| 3%           | $18,600                          | $17.8 million            |
| 5%           | $27,900                          | $1.9 *trillion*          |

These numbers are why **no honest system promises a fixed daily return.** If a
5%/day edge existed, its operator would out-capitalize every hedge fund on earth
within a year. The market does not allow it. A *good* automated system aims for a
positive *expectancy* over many trades and accepts that individual days — and
weeks — will be negative.

Realistic, *good* outcomes for a disciplined retail crypto system look more like
single-digit to low-double-digit percent **per year** after fees, with drawdowns
along the way. Anything dramatically above that is either luck (which mean-reverts)
or undisclosed risk.

## Why this design is "best practice", not "best returns"

There is no single best strategy — only strategies that fit a market regime.
What *is* robust is **process**: diversification, risk limits, and validation.

### 1. Ensemble of uncorrelated signals
- **EMA crossover** — captures sustained *trends*.
- **RSI mean-reversion** — fades *overextended* moves in ranging markets.
- **Momentum** — rides strong short-term *breakouts*.

Each works in a different regime and fails in others. Requiring a **majority
agreement** before acting filters out the noise where any single indicator
whipsaws. This is the cheapest, most reliable improvement available to a retail
system.

### 2. Risk-based position sizing
Size is derived from *how much you'd lose if the stop hits*, capped at
`per_trade_risk_pct` (default 1%) of equity — not a fixed dollar amount. A wider
stop automatically means a smaller position. This is the same rule professional
desks use.

### 3. Hard stops on every position
`stop_loss_pct`, `take_profit_pct`, and a `trailing_stop_pct` are attached to
every entry. A 2:1 reward:risk default means you can be right less than half the
time and still come out ahead.

### 4. Daily circuit breaker
If equity falls `daily_loss_limit_pct` (default 3%) from the day's open, the bot
stops opening new positions until the next day. This caps the damage from a bad
regime or a malfunctioning signal — the single most important survival rule.

### 5. Compounding with a profit reserve
Position sizing reads *current* equity, so gains are automatically reinvested
(true compounding). Optionally, a fraction of each realized profit
(`profit_reserve_pct`) is skimmed into a locked reserve the bot will never trade
— so a winning streak can't be fully given back.

### 6. Validate before you risk anything
Every strategy must be **backtested** (`python -m src.main backtest ...`) and then
run in **paper mode** for a meaningful period before a single real dollar is
deployed. A strategy that loses in backtest will lose live. Backtests also
overstate results (no slippage spikes, no outages, survivorship), so treat live
paper results as the real test.

## Multi-strategy: routing, auto-selection, and "training"

You don't have to commit to one strategy. The system attributes every closed
trade to the strategy that opened it, so it can learn which indicator suits
which coin. Three selection modes (`strategy_selection.mode` in config):

- **single** — one strategy for everything (simplest; back-compatible).
- **routing** — an explicit `{symbol → strategy}` map you control. Set it by
  hand, or generate it automatically (below) and apply it in the dashboard.
- **auto** — adaptive. For each coin it uses the strategy with the best *live*
  track record once enough trades exist (`auto.min_trades`), otherwise the
  backtest recommendation, otherwise the default. This is the "switch if one
  isn't performing, finalize the winner on results" behaviour.

### The training / finalization workflow

```bash
# Backtest EVERY strategy on EVERY coin and rank them:
python -m src.main evaluate --days 180 --metric total_return_pct
```

This prints a per-coin scoreboard and writes `logs/evaluation.json` with a
recommended strategy per coin, e.g.:

```
BTC/USDT:   ema_crossover  <-- recommended   (trends cleanly)
PAXG/USDT:  rsi_mean_reversion <-- recommended (ranges around gold price)
ETH/USDT:   momentum       <-- recommended
```

The dashboard shows this as a **"best strategy per coin"** table, and the
Settings page has **Apply backtest recommendation** to switch routing to those
winners in one click. In `auto` mode the live bot then keeps refining per-coin
choices from real trade results.

### Combining strengths

The `ensemble` strategy already does "use each indicator's powers together": it
runs EMA + RSI + Momentum and only acts when a majority agree. Use it as a coin's
strategy when no single indicator dominates — it trades less but with higher
conviction.

## Tuning checklist

1. Backtest across **multiple symbols and multiple time windows** (bull, bear,
   chop). A strategy that only works in one window is overfit.
2. Watch **max drawdown**, not just total return. A 30% return with a 50%
   drawdown is worse than 12% with an 8% drawdown.
3. Keep fees realistic — at 0.1% taker, over-trading silently bleeds the account.
4. Start live with the **smallest** capital you'd accept losing entirely.
