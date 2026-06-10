"""Ensemble: combine sub-strategies and act only on majority agreement.

Diversifying across uncorrelated signals reduces whipsaw and false entries —
the single most reliable way to make an automated approach steadier (though
still never guaranteed).
"""
from __future__ import annotations

import pandas as pd

from .base import Action, Signal, Strategy
from .ema_crossover import EMACrossover
from .momentum import Momentum
from .rsi_mean_reversion import RSIMeanReversion


class Ensemble(Strategy):
    name = "ensemble"

    def __init__(self, params: dict | None = None, min_agreement: int = 2, **kwargs):
        super().__init__(min_agreement=min_agreement, **kwargs)
        params = params or {}
        self.min_agreement = min_agreement
        self.members: list[Strategy] = [
            EMACrossover(**params.get("ema_crossover", {})),
            RSIMeanReversion(**params.get("rsi_mean_reversion", {})),
            Momentum(**params.get("momentum", {})),
        ]

    def generate(self, df: pd.DataFrame) -> Signal:
        signals = [m.generate(df) for m in self.members]
        buys = [s for s in signals if s.is_buy]
        sells = [s for s in signals if s.is_sell]

        if len(buys) >= self.min_agreement and len(buys) > len(sells):
            conf = sum(s.confidence for s in buys) / len(buys)
            reasons = "; ".join(s.reason for s in buys)
            return Signal(Action.BUY, conf, f"{len(buys)} agree: {reasons}")

        if len(sells) >= self.min_agreement and len(sells) > len(buys):
            conf = sum(s.confidence for s in sells) / len(sells)
            reasons = "; ".join(s.reason for s in sells)
            return Signal(Action.SELL, conf, f"{len(sells)} agree: {reasons}")

        return Signal(Action.HOLD, 0.0, "no majority")
