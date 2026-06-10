import numpy as np
import pandas as pd

from src.data import indicators


def test_ema_tracks_constant_series():
    s = pd.Series([10.0] * 50)
    assert indicators.ema(s, 12).iloc[-1] == 10.0


def test_rsi_bounds():
    s = pd.Series(np.linspace(1, 100, 100))  # strictly rising -> RSI near 100
    r = indicators.rsi(s, 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()
    assert r.iloc[-1] > 90


def test_rsi_falling_series_low():
    s = pd.Series(np.linspace(100, 1, 100))
    r = indicators.rsi(s, 14).dropna()
    assert r.iloc[-1] < 10


def test_atr_positive():
    df = pd.DataFrame({
        "high": np.linspace(10, 20, 50),
        "low": np.linspace(9, 19, 50),
        "close": np.linspace(9.5, 19.5, 50),
    })
    atr = indicators.atr(df, 14).dropna()
    assert (atr > 0).all()
