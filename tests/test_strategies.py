import numpy as np
import pandas as pd

from src.strategies import create_strategy
from src.strategies.base import Action


def _frame(prices):
    return pd.DataFrame({
        "open": prices, "high": [p * 1.001 for p in prices],
        "low": [p * 0.999 for p in prices], "close": prices,
        "volume": [1.0] * len(prices),
    })


def test_strategies_return_signal():
    df = _frame(list(np.linspace(100, 120, 100)))
    for name in ("ema_crossover", "rsi_mean_reversion", "momentum", "ensemble"):
        sig = create_strategy(name, {}).generate(df)
        assert sig.action in (Action.BUY, Action.SELL, Action.HOLD)
        assert 0.0 <= sig.confidence <= 1.0


def test_momentum_buys_on_strong_uptrend():
    df = _frame([100 * (1.02 ** i) for i in range(60)])  # steep uptrend
    sig = create_strategy("momentum", {"momentum": {"lookback": 24, "threshold_pct": 1.5}}).generate(df)
    assert sig.action is Action.BUY


def test_insufficient_data_holds():
    df = _frame([100, 101, 102])
    assert create_strategy("ema_crossover", {}).generate(df).action is Action.HOLD


def test_unknown_strategy_raises():
    import pytest
    with pytest.raises(ValueError):
        create_strategy("does_not_exist", {})
