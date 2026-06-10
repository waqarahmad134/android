"""Tracks live trade performance per strategy and per (symbol, strategy).

This is how the system "learns" which strategy works best for which coin: every
closed trade is attributed to the strategy that opened it, and these running
stats drive the adaptive router and the dashboard charts.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Stat:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0

    @property
    def win_rate(self) -> float:
        return (self.wins / self.trades * 100) if self.trades else 0.0

    @property
    def avg_pnl(self) -> float:
        return (self.total_pnl / self.trades) if self.trades else 0.0

    def add(self, pnl: float) -> None:
        self.trades += 1
        self.total_pnl += pnl
        if pnl > 0:
            self.wins += 1
        elif pnl < 0:
            self.losses += 1

    def as_dict(self) -> dict:
        return {
            "trades": self.trades, "wins": self.wins, "losses": self.losses,
            "total_pnl": round(self.total_pnl, 4),
            "win_rate": round(self.win_rate, 2), "avg_pnl": round(self.avg_pnl, 4),
        }


_METRICS = {
    "total_pnl": lambda s: s.total_pnl,
    "win_rate": lambda s: s.win_rate,
    "avg_pnl": lambda s: s.avg_pnl,
}


@dataclass
class PerformanceTracker:
    by_strategy: dict[str, Stat] = field(default_factory=dict)
    by_symbol_strategy: dict[str, dict[str, Stat]] = field(default_factory=dict)

    def record(self, strategy: str, symbol: str, pnl: float) -> None:
        if not strategy:
            strategy = "unknown"
        self.by_strategy.setdefault(strategy, Stat()).add(pnl)
        self.by_symbol_strategy.setdefault(symbol, {}).setdefault(strategy, Stat()).add(pnl)

    def best_for_symbol(self, symbol: str, min_trades: int = 5,
                        metric: str = "total_pnl") -> str | None:
        """Return the best strategy for a symbol given enough live evidence."""
        score = _METRICS.get(metric, _METRICS["total_pnl"])
        candidates = {
            name: st for name, st in self.by_symbol_strategy.get(symbol, {}).items()
            if st.trades >= min_trades
        }
        if not candidates:
            return None
        return max(candidates, key=lambda n: score(candidates[n]))

    def snapshot(self) -> dict:
        return {
            "by_strategy": {k: v.as_dict() for k, v in self.by_strategy.items()},
            "by_symbol_strategy": {
                sym: {name: st.as_dict() for name, st in per_strat.items()}
                for sym, per_strat in self.by_symbol_strategy.items()
            },
        }
