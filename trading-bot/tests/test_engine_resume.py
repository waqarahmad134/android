import time

from src.engine import TradingEngine
from src.exchanges.paper import PaperAdapter
from src.persistence import save_session
from src.strategies.router import create_router
from src.utils.config import Config

RISK = {"max_position_pct": 0.5, "max_total_exposure_pct": 1.0, "max_open_positions": 2,
        "stop_loss_pct": 0.02, "take_profit_pct": 0.04, "trailing_stop_pct": 0.015,
        "daily_loss_limit_pct": 0.5, "per_trade_risk_pct": 0.05}


def _cfg():
    return Config(raw={
        "mode": "paper", "exchange": "binance", "quote_currency": "USDT",
        "universe": ["BTC/USDT"], "timeframe": "1h", "strategy": "momentum",
        "strategy_selection": {"mode": "auto", "default": "ensemble"},
        "strategy_params": {}, "risk": RISK, "compounding": {}, "logging": {}})


def test_engine_resumes_paper_session(tmp_path, monkeypatch, fake_exchange):
    # save_session/load_session use the relative logs/session.json path.
    monkeypatch.chdir(tmp_path)
    save_session({
        "mode": "paper", "start_equity": 10000, "cash": 9500,
        "realized_pnl": 175.0, "reserve": 40.0, "started_at": time.time() - 3 * 86400,
        "day_index": None,
        "positions": [{"symbol": "BTC/USDT", "amount": 0.1, "entry_price": 1000,
                       "stop_loss": 980, "take_profit": 1040, "peak_price": 1015,
                       "strategy": "momentum"}],
        "closed_trades": [{"symbol": "BTC/USDT", "pnl": 175, "strategy": "momentum"}],
        "equity_curve": [{"t": 1, "equity": 10000}, {"t": 2, "equity": 10175}],
        "performance": {"by_strategy": {"momentum": {"trades": 6, "wins": 4, "losses": 2, "total_pnl": 175}},
                        "by_symbol_strategy": {"BTC/USDT": {"momentum": {"trades": 6, "wins": 4, "losses": 2, "total_pnl": 175}}}},
        "wallet": {"USDT": 9500, "BTC": 0.1},
    })

    paper = PaperAdapter(fake_exchange, "USDT", starting_equity=10000)
    eng = TradingEngine(_cfg(), paper, create_router(_cfg()), resume_session=True)

    assert eng.portfolio.realized_pnl == 175.0
    assert eng.portfolio.reserve == 40.0
    assert "BTC/USDT" in eng.portfolio.positions
    assert eng.portfolio.positions["BTC/USDT"].peak_price == 1015
    assert eng.tracker.by_strategy["momentum"].trades == 6
    assert paper.wallet["BTC"] == 0.1
    # auto router should now prefer momentum for BTC from restored live stats
    assert eng.router.resolve_name("BTC/USDT") == "momentum"


def test_engine_starts_fresh_without_session(tmp_path, monkeypatch, fake_exchange):
    monkeypatch.chdir(tmp_path)  # no session file here
    paper = PaperAdapter(fake_exchange, "USDT", starting_equity=10000)
    eng = TradingEngine(_cfg(), paper, create_router(_cfg()), resume_session=True)
    assert eng.portfolio.realized_pnl == 0.0
    assert eng.portfolio.positions == {}
