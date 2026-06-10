"""OHLCV market-data access, returned as tidy pandas DataFrames."""
from __future__ import annotations

import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class MarketData:
    """Fetches and normalizes candle data from an exchange adapter."""

    def __init__(self, exchange):
        self._exchange = exchange

    def ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """Return OHLCV candles as a DataFrame indexed by UTC timestamp."""
        raw = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return self.to_frame(raw)

    @staticmethod
    def to_frame(raw: list[list]) -> pd.DataFrame:
        df = pd.DataFrame(raw, columns=OHLCV_COLUMNS)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp").astype(float)
        return df
