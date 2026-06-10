"""Mean reversion: buy oversold, sell overbought (RSI based)."""
from __future__ import annotations

import pandas as pd

from ..data import indicators
from .base import Action, Signal, Strategy


class RSIMeanReversion(Strategy):
    name = "rsi_mean_reversion"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70, **kwargs):
        super().__init__(period=period, oversold=oversold, overbought=overbought, **kwargs)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate(self, df: pd.DataFrame) -> Signal:
        if not self._enough(df, self.period + 2):
            return Signal(Action.HOLD, 0.0, "insufficient data")

        rsi = indicators.rsi(df["close"], self.period)
        value = float(rsi.iloc[-1])

        if value <= self.oversold:
            conf = float(min(1.0, (self.oversold - value) / self.oversold + 0.5))
            return Signal(Action.BUY, conf, f"RSI {value:.1f} oversold")
        if value >= self.overbought:
            conf = float(min(1.0, (value - self.overbought) / (100 - self.overbought) + 0.5))
            return Signal(Action.SELL, conf, f"RSI {value:.1f} overbought")
        return Signal(Action.HOLD, 0.0, f"RSI {value:.1f} neutral")
