"""Shared state file written by the bot and read by the web dashboard.

The trading engine and the dashboard run as separate processes (and separate
Docker containers), so they communicate through a small JSON snapshot written
atomically each loop. This keeps the dashboard a pure read-only viewer that can
never interfere with trading.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any

DEFAULT_STATE_PATH = os.getenv("BOT_STATE_PATH", "logs/state.json")


def write_state(snapshot: dict[str, Any], path: str = DEFAULT_STATE_PATH) -> None:
    """Atomically write the snapshot so readers never see a half-written file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    snapshot = {**snapshot, "updated_at": time.time()}
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh)
        os.replace(tmp, path)  # atomic on POSIX
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_state(path: str = DEFAULT_STATE_PATH) -> dict[str, Any]:
    """Return the latest snapshot, or an empty default if none exists yet."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "updated_at": None,
            "mode": None,
            "exchange": None,
            "strategy": None,
            "equity": 0.0,
            "reserve": 0.0,
            "realized_pnl": 0.0,
            "halted": False,
            "positions": [],
            "closed_trades": [],
            "equity_curve": [],
        }
