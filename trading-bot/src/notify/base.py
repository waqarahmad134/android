"""Notifier interface plus a no-op implementation.

A notifier reports trade events to an external channel (Slack). It must never
raise into the trading loop — a failed alert should be logged and swallowed, not
crash the bot.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    def send(self, text: str, level: str = "info") -> None:
        """Deliver a message. Implementations must not raise."""
        ...

    # --- convenience helpers used by the engine ---
    def startup(self, mode: str, exchange: str, strategy: str, universe: list[str]) -> None:
        self.send(
            f":rocket: *Bot started* — mode=`{mode}` exchange=`{exchange}` "
            f"strategy=`{strategy}`\nUniverse: {', '.join(universe)}",
            level="info",
        )

    def entry(self, symbol: str, amount: float, price: float, reason: str) -> None:
        self.send(
            f":green_circle: *ENTER* {symbol}\n"
            f"qty `{amount:.6f}` @ `{price:.4f}`\n_{reason}_",
            level="trade",
        )

    def exit(self, symbol: str, price: float, pnl: float, reason: str) -> None:
        emoji = ":white_check_mark:" if pnl >= 0 else ":x:"
        self.send(
            f"{emoji} *EXIT* {symbol} @ `{price:.4f}`\n"
            f"PnL `{pnl:+.2f}` — {reason}",
            level="trade",
        )

    def circuit_breaker(self, drawdown_pct: float) -> None:
        self.send(
            f":octagonal_sign: *DAILY CIRCUIT BREAKER* hit "
            f"(-{drawdown_pct:.2f}%). No new entries until tomorrow.",
            level="alert",
        )

    def heartbeat(self, equity: float, reserve: float, open_positions: int, realized: float) -> None:
        self.send(
            f":bar_chart: Equity `{equity:,.2f}` | reserve `{reserve:,.2f}` | "
            f"open `{open_positions}` | realized `{realized:+,.2f}`",
            level="info",
        )


class NullNotifier(Notifier):
    """Does nothing. Used when notifications are disabled."""

    def send(self, text: str, level: str = "info") -> None:
        return None
