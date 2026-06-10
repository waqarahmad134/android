"""Pure-pandas technical indicators (no TA-Lib dependency)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - (100 / (1 + rs))
    # When there are no losses, RSI is 100; when no gains, RSI is 0.
    out = out.where(avg_loss != 0, 100.0)
    out = out.where(avg_gain != 0, out.fillna(0.0))
    return out


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range from an OHLCV dataframe."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def returns(series: pd.Series, lookback: int = 1) -> pd.Series:
    """Percentage return over `lookback` periods."""
    return series.pct_change(periods=lookback) * 100.0
