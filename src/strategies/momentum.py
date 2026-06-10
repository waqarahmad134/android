"""Momentum: ride assets showing strong recent returns, exit on reversal."""
from __future__ import annotations

import pandas as pd

from ..data import indicators
from .base import Action, Signal, Strategy


class Momentum(Strategy):
    name = "momentum"

    def __init__(self, lookback: int = 24, threshold_pct: float = 1.5, **kwargs):
        super().__init__(lookback=lookback, threshold_pct=threshold_pct, **kwargs)
        self.lookback = lookback
        self.threshold_pct = threshold_pct

    def generate(self, df: pd.DataFrame) -> Signal:
        if not self._enough(df, self.lookback + 2):
            return Signal(Action.HOLD, 0.0, "insufficient data")

        ret = float(indicators.returns(df["close"], self.lookback).iloc[-1])
        conf = float(min(1.0, abs(ret) / (self.threshold_pct * 3)))

        if ret >= self.threshold_pct:
            return Signal(Action.BUY, max(conf, 0.5), f"+{ret:.2f}% over {self.lookback} bars")
        if ret <= -self.threshold_pct:
            return Signal(Action.SELL, max(conf, 0.5), f"{ret:.2f}% over {self.lookback} bars")
        return Signal(Action.HOLD, conf, f"{ret:.2f}% momentum below threshold")
