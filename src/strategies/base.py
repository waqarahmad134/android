"""Strategy interface. A strategy turns OHLCV data into a discrete Signal."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Signal:
    action: Action
    confidence: float = 1.0   # 0..1, used by the ensemble / sizing
    reason: str = ""

    @property
    def is_buy(self) -> bool:
        return self.action is Action.BUY

    @property
    def is_sell(self) -> bool:
        return self.action is Action.SELL


class Strategy(ABC):
    name: str = "base"

    def __init__(self, **params):
        self.params = params

    @abstractmethod
    def generate(self, df: pd.DataFrame) -> Signal:
        """Inspect the candle history and return the latest signal."""
        ...

    @staticmethod
    def _enough(df: pd.DataFrame, n: int) -> bool:
        return df is not None and len(df) >= n
