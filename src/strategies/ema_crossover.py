"""Trend-following: fast EMA crossing above/below a slow EMA."""
from __future__ import annotations

import pandas as pd

from ..data import indicators
from .base import Action, Signal, Strategy


class EMACrossover(Strategy):
    name = "ema_crossover"

    def __init__(self, fast: int = 12, slow: int = 26, **kwargs):
        super().__init__(fast=fast, slow=slow, **kwargs)
        self.fast = fast
        self.slow = slow

    def generate(self, df: pd.DataFrame) -> Signal:
        if not self._enough(df, self.slow + 2):
            return Signal(Action.HOLD, 0.0, "insufficient data")

        close = df["close"]
        fast = indicators.ema(close, self.fast)
        slow = indicators.ema(close, self.slow)

        prev_diff = fast.iloc[-2] - slow.iloc[-2]
        curr_diff = fast.iloc[-1] - slow.iloc[-1]

        # Confidence scales with how separated the EMAs are (relative to price).
        sep = abs(curr_diff) / close.iloc[-1]
        conf = float(min(1.0, sep * 50))

        if prev_diff <= 0 < curr_diff:
            return Signal(Action.BUY, max(conf, 0.5), "fast EMA crossed above slow")
        if prev_diff >= 0 > curr_diff:
            return Signal(Action.SELL, max(conf, 0.5), "fast EMA crossed below slow")
        # Hold, but bias the confidence toward the prevailing trend direction.
        return Signal(Action.HOLD, conf, "no cross")
