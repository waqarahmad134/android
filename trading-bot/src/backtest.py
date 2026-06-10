"""Historical backtester — validate a strategy before risking capital.

Replays past candles bar-by-bar through the same strategy + risk logic the live
engine uses, then reports return, win rate, and max drawdown. A strategy that
isn't profitable in backtest will not magically become profitable live.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .data import MarketData
from .risk import RiskManager
from .strategies import Strategy
from .strategies.base import Action
from .utils.logger import get_logger

log = get_logger(__name__)

FEE_RATE = 0.001  # match the paper adapter's assumption


@dataclass
class Trade:
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    reason: str


@dataclass
class BacktestResult:
    symbol: str
    start_equity: float
    end_equity: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)

    @property
    def total_return_pct(self) -> float:
        return (self.end_equity / self.start_equity - 1) * 100

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades) * 100

    @property
    def max_drawdown_pct(self) -> float:
        peak = -float("inf")
        max_dd = 0.0
        for v in self.equity_curve:
            peak = max(peak, v)
            if peak > 0:
                max_dd = max(max_dd, (peak - v) / peak)
        return max_dd * 100

    def summary(self) -> str:
        return (
            f"\n=== Backtest: {self.symbol} ===\n"
            f"  Trades:        {len(self.trades)}\n"
            f"  Win rate:      {self.win_rate:.1f}%\n"
            f"  Start equity:  {self.start_equity:,.2f}\n"
            f"  End equity:    {self.end_equity:,.2f}\n"
            f"  Total return:  {self.total_return_pct:+.2f}%\n"
            f"  Max drawdown:  {self.max_drawdown_pct:.2f}%\n"
            "  NOTE: Past performance does not predict future results.\n"
        )


def run_backtest(
    exchange,
    strategy: Strategy,
    risk_cfg: dict,
    symbol: str,
    timeframe: str = "1h",
    candles: int = 1000,
    start_equity: float = 10000.0,
    warmup: int = 50,
) -> BacktestResult:
    market = MarketData(exchange)
    df = market.ohlcv(symbol, timeframe=timeframe, limit=candles)
    risk = RiskManager(risk_cfg)
    risk.start_day(start_equity)

    cash = start_equity
    position = None          # dict: amount, entry, stop, tp, peak
    result = BacktestResult(symbol=symbol, start_equity=start_equity, end_equity=start_equity)

    for i in range(warmup, len(df)):
        window = df.iloc[: i + 1]
        price = float(window["close"].iloc[-1])
        equity = cash + (position["amount"] * price if position else 0.0)
        result.equity_curve.append(equity)

        # --- manage open position ---
        if position:
            position["peak"] = max(position["peak"], price)
            reason = risk.should_exit(position["entry"], price, position["peak"])
            if reason is None and strategy.generate(window).action is Action.SELL:
                reason = "strategy_sell"
            if reason:
                proceeds = position["amount"] * price * (1 - FEE_RATE)
                pnl = proceeds - (position["entry"] * position["amount"])
                cash += proceeds
                result.trades.append(Trade(position["entry"], price, position["amount"], pnl, reason))
                position = None
            continue

        # --- look for entry ---
        signal = strategy.generate(window)
        if signal.action is not Action.BUY:
            continue
        decision = risk.size_entry(
            equity=equity, price=price, confidence=signal.confidence,
            open_positions=0, current_exposure=0.0,
        )
        if not decision.approved:
            continue
        cost = decision.amount * price * (1 + FEE_RATE)
        if cost > cash:
            continue
        cash -= cost
        position = {
            "amount": decision.amount, "entry": price,
            "stop": decision.stop_loss, "tp": decision.take_profit, "peak": price,
        }

    # Liquidate any open position at the final price.
    final_price = float(df["close"].iloc[-1])
    if position:
        proceeds = position["amount"] * final_price * (1 - FEE_RATE)
        pnl = proceeds - (position["entry"] * position["amount"])
        cash += proceeds
        result.trades.append(Trade(position["entry"], final_price, position["amount"], pnl, "final_liquidation"))

    result.end_equity = cash
    result.equity_curve.append(cash)
    return result
