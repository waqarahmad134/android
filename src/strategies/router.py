"""Resolves which strategy to use for each symbol.

Three selection modes (config: strategy_selection.mode):
  - single  : one strategy for everything (back-compat with the `strategy` key).
  - routing : an explicit {symbol -> strategy} map you control (or generate with
              `python -m src.main evaluate`).
  - auto    : adaptive. Prefer the strategy with the best *live* track record for
              each symbol once enough trades exist; otherwise use the offline
              evaluation recommendation; otherwise fall back to a default.

All strategies are instantiated once and reused.
"""
from __future__ import annotations

from .base import Strategy
from .factory import create_strategy
from .performance import PerformanceTracker

ALL_STRATEGIES = ["ema_crossover", "rsi_mean_reversion", "momentum", "ensemble"]


class StrategyRouter:
    def __init__(
        self,
        mode: str = "single",
        default: str = "ensemble",
        params: dict | None = None,
        routing: dict | None = None,
        recommendations: dict | None = None,
        tracker: PerformanceTracker | None = None,
        auto_min_trades: int = 5,
        auto_metric: str = "total_pnl",
    ):
        self.mode = mode
        self.default = default
        self.routing = routing or {}
        self.recommendations = recommendations or {}
        self.tracker = tracker or PerformanceTracker()
        self.auto_min_trades = auto_min_trades
        self.auto_metric = auto_metric
        self._params = params or {}
        self._cache: dict[str, Strategy] = {}

    @property
    def name(self) -> str:
        return f"router:{self.mode}"

    def _get(self, name: str) -> Strategy:
        if name not in self._cache:
            self._cache[name] = create_strategy(name, self._params)
        return self._cache[name]

    def resolve_name(self, symbol: str) -> str:
        if self.mode == "single":
            return self.default
        if self.mode == "routing":
            return self.routing.get(symbol, self.routing.get("default", self.default))
        if self.mode == "auto":
            live_best = self.tracker.best_for_symbol(
                symbol, self.auto_min_trades, self.auto_metric
            )
            if live_best:
                return live_best
            if symbol in self.recommendations:
                return self.recommendations[symbol]
            return self.default
        return self.default

    def resolve(self, symbol: str) -> tuple[str, Strategy]:
        name = self.resolve_name(symbol)
        if name not in ALL_STRATEGIES:
            name = self.default
        return name, self._get(name)

    def assignments(self, symbols: list[str]) -> dict[str, str]:
        """Current symbol -> strategy mapping (for the dashboard)."""
        return {s: self.resolve_name(s) for s in symbols}


def create_router(cfg, tracker: PerformanceTracker | None = None,
                  recommendations: dict | None = None) -> StrategyRouter:
    """Build a router from a Config object, with back-compat for `strategy`."""
    sel = cfg.raw.get("strategy_selection", {}) or {}
    mode = sel.get("mode", "single")
    # Back-compat: `strategy: <name>` behaves as single mode with that default.
    default = sel.get("default", cfg.strategy)
    auto = sel.get("auto", {})
    return StrategyRouter(
        mode=mode,
        default=default,
        params=cfg.strategy_params,
        routing=sel.get("routing", {}),
        recommendations=recommendations or {},
        tracker=tracker,
        auto_min_trades=int(auto.get("min_trades", 5)),
        auto_metric=auto.get("metric", "total_pnl"),
    )
