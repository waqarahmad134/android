from src.evaluate import evaluate_all

RISK_CFG = {
    "max_position_pct": 0.5, "max_total_exposure_pct": 1.0, "max_open_positions": 1,
    "stop_loss_pct": 0.02, "take_profit_pct": 0.04, "trailing_stop_pct": 0.015,
    "daily_loss_limit_pct": 0.5, "per_trade_risk_pct": 0.05,
}


def test_evaluate_all_builds_matrix_and_recommendation(fake_exchange):
    res = evaluate_all(
        exchange=fake_exchange, risk_cfg=RISK_CFG,
        symbols=["BTC/USDT", "ETH/USDT"], timeframe="1h", candles=400,
        start_equity=10000, metric="total_return_pct", min_trades=1,
    )
    assert set(res["matrix"].keys()) == {"BTC/USDT", "ETH/USDT"}
    # every strategy evaluated for each symbol
    for sym, per in res["matrix"].items():
        assert {"ema_crossover", "rsi_mean_reversion", "momentum", "ensemble"} <= set(per)
        for m in per.values():
            assert "return_pct" in m and "trades" in m
    # recommendation (if any) must be a strategy that was actually evaluated
    for sym, name in res["recommended"].items():
        assert name in res["matrix"][sym]
