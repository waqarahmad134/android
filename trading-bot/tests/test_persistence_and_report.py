import time

from src import persistence
from src.report import build_report


def _session(**over):
    s = {
        "mode": "paper", "start_equity": 10000.0, "cash": 9500.0,
        "realized_pnl": 250.0, "reserve": 50.0,
        "started_at": time.time() - 8 * 86400, "day_index": None,
        "day_start_equity": 10200.0, "halted": False,
        "positions": [{"symbol": "BTC/USDT", "amount": 0.1, "entry_price": 1000,
                       "stop_loss": 980, "take_profit": 1040, "peak_price": 1010,
                       "strategy": "momentum"}],
        "closed_trades": [{"symbol": "BTC/USDT", "pnl": 250, "strategy": "momentum"}],
        "equity_curve": [{"t": 1, "equity": 10000}, {"t": 2, "equity": 9800},
                         {"t": 3, "equity": 10250}],
        "performance": {
            "by_strategy": {"momentum": {"trades": 8, "wins": 6, "losses": 2,
                                         "total_pnl": 250, "win_rate": 75.0}},
            "by_symbol_strategy": {
                "BTC/USDT": {"momentum": {"trades": 8, "wins": 6, "losses": 2,
                                          "total_pnl": 250, "win_rate": 75.0}},
                "ETH/USDT": {"rsi_mean_reversion": {"trades": 6, "wins": 1, "losses": 5,
                                                    "total_pnl": -120, "win_rate": 16.7}},
                "SOL/USDT": {"ensemble": {"trades": 2, "wins": 1, "losses": 1,
                                          "total_pnl": 5, "win_rate": 50.0}},
            },
        },
    }
    s.update(over)
    return s


def test_session_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "session.json")
    persistence.save_session(_session(), p)
    loaded = persistence.load_session(p)
    assert loaded["realized_pnl"] == 250.0
    assert loaded["positions"][0]["symbol"] == "BTC/USDT"
    assert "saved_at" in loaded


def test_tracker_rebuilt_from_snapshot():
    t = persistence.tracker_from_snapshot(_session()["performance"])
    assert t.by_strategy["momentum"].trades == 8
    assert t.by_strategy["momentum"].win_rate == 75.0
    assert t.best_for_symbol("BTC/USDT", min_trades=5) == "momentum"


def test_report_verdicts():
    out = build_report(_session())
    assert "DEMO READINESS REPORT" in out
    assert "BTC/USDT" in out and "READY" in out          # profitable + high win rate
    assert "AVOID" in out                                 # ETH lost money
    assert "NEEDS MORE DATA" in out                       # SOL only 2 trades
    assert "GO-LIVE CHECKLIST" in out


def test_report_handles_empty_session():
    assert "No session data" in build_report(None)
