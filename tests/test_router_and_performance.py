from src.strategies.performance import PerformanceTracker
from src.strategies.router import StrategyRouter, create_router
from src.utils.config import Config


def test_performance_tracking_and_best_for_symbol():
    t = PerformanceTracker()
    # ema wins 3 trades on BTC, rsi loses 3.
    for pnl in (10, 20, 5):
        t.record("ema_crossover", "BTC/USDT", pnl)
    for pnl in (-5, -10, -2):
        t.record("rsi_mean_reversion", "BTC/USDT", pnl)

    assert t.by_strategy["ema_crossover"].trades == 3
    assert t.by_strategy["ema_crossover"].win_rate == 100.0
    assert t.best_for_symbol("BTC/USDT", min_trades=3, metric="total_pnl") == "ema_crossover"
    # Not enough trades -> no recommendation.
    assert t.best_for_symbol("BTC/USDT", min_trades=10) is None


def test_router_single_mode():
    r = StrategyRouter(mode="single", default="momentum")
    name, strat = r.resolve("BTC/USDT")
    assert name == "momentum"
    assert strat.name == "momentum"


def test_router_routing_mode_with_default():
    r = StrategyRouter(mode="routing", default="ensemble",
                       routing={"BTC/USDT": "ema_crossover", "default": "rsi_mean_reversion"})
    assert r.resolve_name("BTC/USDT") == "ema_crossover"
    assert r.resolve_name("ETH/USDT") == "rsi_mean_reversion"   # falls to routing default


def test_router_auto_prefers_live_then_recommendation():
    t = PerformanceTracker()
    r = StrategyRouter(mode="auto", default="ensemble",
                       recommendations={"ETH/USDT": "momentum"}, tracker=t,
                       auto_min_trades=2, auto_metric="total_pnl")
    # No live data yet -> use recommendation; unknown coin -> default.
    assert r.resolve_name("ETH/USDT") == "momentum"
    assert r.resolve_name("SOL/USDT") == "ensemble"
    # Once live evidence accrues, it overrides the recommendation.
    t.record("ema_crossover", "ETH/USDT", 50)
    t.record("ema_crossover", "ETH/USDT", 50)
    assert r.resolve_name("ETH/USDT") == "ema_crossover"


def test_router_assignments():
    r = StrategyRouter(mode="single", default="ensemble")
    assert r.assignments(["BTC/USDT", "ETH/USDT"]) == {
        "BTC/USDT": "ensemble", "ETH/USDT": "ensemble"}


def test_create_router_backcompat_single():
    cfg = Config(raw={"strategy": "momentum", "universe": ["BTC/USDT"],
                      "exchange": "binance", "mode": "paper"})
    r = create_router(cfg)
    assert r.mode == "single"
    assert r.resolve_name("BTC/USDT") == "momentum"
