from src.backtest import run_backtest
from src.strategies import create_strategy

RISK_CFG = {
    "max_position_pct": 0.5, "max_total_exposure_pct": 1.0, "max_open_positions": 1,
    "stop_loss_pct": 0.02, "take_profit_pct": 0.04, "trailing_stop_pct": 0.015,
    "daily_loss_limit_pct": 0.5, "per_trade_risk_pct": 0.05,
}


def test_backtest_runs_and_reports(fake_exchange):
    strat = create_strategy("ensemble", {})
    result = run_backtest(
        exchange=fake_exchange, strategy=strat, risk_cfg=RISK_CFG,
        symbol="BTC/USDT", timeframe="1h", candles=400, start_equity=10000,
    )
    assert result.start_equity == 10000
    assert result.end_equity > 0
    assert isinstance(result.summary(), str)
    assert 0.0 <= result.win_rate <= 100.0
    assert result.max_drawdown_pct >= 0.0
