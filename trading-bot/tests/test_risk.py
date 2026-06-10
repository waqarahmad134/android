from src.risk import RiskManager

RISK_CFG = {
    "max_position_pct": 0.15,
    "max_total_exposure_pct": 0.60,
    "max_open_positions": 4,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "trailing_stop_pct": 0.015,
    "daily_loss_limit_pct": 0.03,
    "per_trade_risk_pct": 0.01,
}


def test_position_sizing_respects_caps():
    rm = RiskManager(RISK_CFG)
    rm.start_day(10000)
    d = rm.size_entry(equity=10000, price=100, confidence=1.0,
                      open_positions=0, current_exposure=0)
    assert d.approved
    # Notional never exceeds max_position_pct of equity.
    assert d.amount * 100 <= 10000 * 0.15 + 1e-6
    assert d.stop_loss < 100 < d.take_profit


def test_circuit_breaker_halts_after_daily_loss():
    rm = RiskManager(RISK_CFG)
    rm.start_day(10000)
    assert not rm.check_circuit_breaker(9800)   # -2%, still ok
    assert rm.check_circuit_breaker(9650)        # -3.5%, halt
    d = rm.size_entry(equity=9650, price=100, confidence=1.0,
                      open_positions=0, current_exposure=0)
    assert not d.approved


def test_max_open_positions_blocks_entry():
    rm = RiskManager(RISK_CFG)
    rm.start_day(10000)
    d = rm.size_entry(equity=10000, price=100, confidence=1.0,
                      open_positions=4, current_exposure=0)
    assert not d.approved


def test_exit_triggers():
    rm = RiskManager(RISK_CFG)
    assert rm.should_exit(100, 97.9, 100) == "stop_loss"
    assert rm.should_exit(100, 104.1, 104.1) == "take_profit"
    # Trailing: peaked at 103, fell >1.5% from peak but not to hard stop.
    assert rm.should_exit(100, 101.4, 103) == "trailing_stop"
    assert rm.should_exit(100, 101, 101) is None


def test_total_exposure_cap():
    rm = RiskManager(RISK_CFG)
    rm.start_day(10000)
    # Already at the exposure ceiling -> no room.
    d = rm.size_entry(equity=10000, price=100, confidence=1.0,
                      open_positions=1, current_exposure=6000)
    assert not d.approved
