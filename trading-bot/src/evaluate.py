"""Strategy evaluation: backtest every strategy across every symbol and
recommend the best strategy per coin.

This is the "result-based finalization" workflow — run it to discover which
indicator/strategy historically fits each coin, then apply the recommended
routing (single click in the dashboard, or copy into config.yaml).
"""
from __future__ import annotations

import time

from .backtest import run_backtest
from .strategies import create_strategy
from .strategies.router import ALL_STRATEGIES
from .utils.logger import get_logger

log = get_logger(__name__)

# Only routable single strategies are evaluated for per-coin recommendation;
# "ensemble" is included as a combine-all-strengths option.
EVAL_STRATEGIES = ALL_STRATEGIES

_METRIC_KEYS = {
    "total_return_pct": lambda r: r.total_return_pct,
    "win_rate": lambda r: r.win_rate,
}


def evaluate_all(
    exchange,
    risk_cfg: dict,
    symbols: list[str],
    timeframe: str = "1h",
    candles: int = 1000,
    start_equity: float = 10000.0,
    metric: str = "total_return_pct",
    min_trades: int = 3,
) -> dict:
    """Return a performance matrix and a recommended {symbol -> strategy} map."""
    score = _METRIC_KEYS.get(metric, _METRIC_KEYS["total_return_pct"])
    matrix: dict[str, dict] = {}
    recommended: dict[str, str] = {}

    for symbol in symbols:
        matrix[symbol] = {}
        best_name, best_score = None, float("-inf")
        for name in EVAL_STRATEGIES:
            try:
                strat = create_strategy(name, {})
                res = run_backtest(
                    exchange=exchange, strategy=strat, risk_cfg=risk_cfg,
                    symbol=symbol, timeframe=timeframe, candles=candles,
                    start_equity=start_equity,
                )
            except Exception as exc:  # one bad symbol/strategy shouldn't abort all
                log.warning("Eval failed for %s/%s: %s", symbol, name, exc)
                continue
            matrix[symbol][name] = {
                "return_pct": round(res.total_return_pct, 2),
                "win_rate": round(res.win_rate, 1),
                "trades": len(res.trades),
                "max_drawdown_pct": round(res.max_drawdown_pct, 2),
            }
            # Require a minimum number of trades to trust a recommendation.
            if len(res.trades) >= min_trades:
                sc = score(res)
                if sc > best_score:
                    best_name, best_score = name, sc
        if best_name:
            recommended[symbol] = best_name

    return {
        "generated_at": time.time(),
        "metric": metric,
        "timeframe": timeframe,
        "candles": candles,
        "matrix": matrix,
        "recommended": recommended,
    }
