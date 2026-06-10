"""Tracks open positions, realized PnL, equity, and compounding behaviour."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Position:
    symbol: str
    amount: float
    entry_price: float
    stop_loss: float
    take_profit: float
    peak_price: float = 0.0
    strategy: str = ""        # which strategy opened this position

    def __post_init__(self):
        if self.peak_price == 0.0:
            self.peak_price = self.entry_price

    def update_peak(self, price: float) -> None:
        self.peak_price = max(self.peak_price, price)

    def market_value(self, price: float) -> float:
        return self.amount * price

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.entry_price) * self.amount


@dataclass
class Portfolio:
    """Accounting layer on top of the exchange wallet.

    Compounding is implicit: position sizing reads `equity()`, which grows with
    realized + unrealized PnL, so winnings are automatically reinvested. An
    optional profit reserve skims realized gains into an untouchable balance to
    lock in progress.
    """

    quote_currency: str
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    reserve: float = 0.0                  # locked-in profit, not traded
    profit_reserve_pct: float = 0.0
    compounding_enabled: bool = True
    closed_trades: list[dict] = field(default_factory=list)  # for the dashboard

    def equity(self, prices: dict[str, float]) -> float:
        """Tradable equity = cash + market value of open positions."""
        holdings = sum(p.market_value(prices.get(s, p.entry_price)) for s, p in self.positions.items())
        return self.cash + holdings

    def total_value(self, prices: dict[str, float]) -> float:
        """Everything including the locked reserve."""
        return self.equity(prices) + self.reserve

    def current_exposure(self, prices: dict[str, float]) -> float:
        return sum(p.market_value(prices.get(s, p.entry_price)) for s, p in self.positions.items())

    def open_position(self, symbol: str, amount: float, price: float, cost: float,
                      stop_loss: float, take_profit: float, strategy: str = "") -> None:
        self.cash -= cost
        self.positions[symbol] = Position(
            symbol=symbol, amount=amount, entry_price=price,
            stop_loss=stop_loss, take_profit=take_profit, strategy=strategy,
        )
        log.info("Opened %s: %.8f @ %.4f (cost %.2f)", symbol, amount, price, cost)

    def close_position(self, symbol: str, price: float, proceeds: float) -> float:
        pos = self.positions.pop(symbol)
        pnl = proceeds - (pos.entry_price * pos.amount)
        self.realized_pnl += pnl
        self.cash += proceeds

        # Skim a fraction of *profit* into the locked reserve (lock in gains).
        if self.compounding_enabled and pnl > 0 and self.profit_reserve_pct > 0:
            skim = pnl * self.profit_reserve_pct
            self.cash -= skim
            self.reserve += skim
            log.info("Reserved %.2f of profit (locked total %.2f)", skim, self.reserve)

        self.closed_trades.append({
            "symbol": symbol,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "amount": pos.amount,
            "pnl": pnl,
            "strategy": pos.strategy,
            "closed_at": time.time(),
        })
        # Keep only the most recent trades in memory for the dashboard.
        if len(self.closed_trades) > 200:
            self.closed_trades = self.closed_trades[-200:]

        log.info("Closed %s @ %.4f -> PnL %.2f", symbol, price, pnl)
        return pnl
