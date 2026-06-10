"""Strategy lookup by name."""
from __future__ import annotations

from .base import Strategy
from .ema_crossover import EMACrossover
from .ensemble import Ensemble
from .momentum import Momentum
from .rsi_mean_reversion import RSIMeanReversion


def create_strategy(name: str, params: dict | None = None) -> Strategy:
    params = params or {}
    name = name.lower()
    if name == "ema_crossover":
        return EMACrossover(**params.get("ema_crossover", {}))
    if name == "rsi_mean_reversion":
        return RSIMeanReversion(**params.get("rsi_mean_reversion", {}))
    if name == "momentum":
        return Momentum(**params.get("momentum", {}))
    if name == "ensemble":
        ens = params.get("ensemble", {})
        return Ensemble(params=params, min_agreement=ens.get("min_agreement", 2))
    raise ValueError(f"Unknown strategy: {name}")
