"""Durable trading-session persistence so a long paper run survives restarts.

The dashboard state file (state.json) is a display snapshot. This session file
(session.json) is the *source of truth* for resuming: paper wallet, open
positions, realized PnL, trade history, equity curve, and the per-strategy
performance the system has learned. Written atomically each loop.

On restart:
  - Learning history (tracker, closed trades, equity curve, realized PnL) is
    always restored, in both paper and live mode.
  - The paper wallet and open positions are restored in PAPER mode only; in
    live mode the exchange is the source of truth for balances/positions.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any

from .strategies.performance import PerformanceTracker, Stat

DEFAULT_SESSION_PATH = os.getenv("BOT_SESSION_PATH", "logs/session.json")


def save_session(data: dict[str, Any], path: str = DEFAULT_SESSION_PATH) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {**data, "saved_at": time.time()}
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_session(path: str = DEFAULT_SESSION_PATH) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def tracker_from_snapshot(snapshot: dict) -> PerformanceTracker:
    """Rebuild a PerformanceTracker from its serialized snapshot."""
    t = PerformanceTracker()

    def _stat(d: dict) -> Stat:
        return Stat(trades=d.get("trades", 0), wins=d.get("wins", 0),
                    losses=d.get("losses", 0), total_pnl=d.get("total_pnl", 0.0))

    for name, d in (snapshot.get("by_strategy") or {}).items():
        t.by_strategy[name] = _stat(d)
    for sym, per in (snapshot.get("by_symbol_strategy") or {}).items():
        t.by_symbol_strategy[sym] = {n: _stat(d) for n, d in per.items()}
    return t
