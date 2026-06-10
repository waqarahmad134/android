"""Configuration loading with light validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional at runtime
    load_dotenv = None


@dataclass
class Config:
    """Typed-ish wrapper around the parsed YAML config.

    Values are kept in a plain dict (`raw`) and exposed via convenience
    properties so the rest of the codebase doesn't sprinkle string keys
    everywhere.
    """

    raw: dict[str, Any] = field(default_factory=dict)

    # --- top level ---
    @property
    def mode(self) -> str:
        return self.raw.get("mode", "paper").lower()

    @property
    def exchange(self) -> str:
        return self.raw.get("exchange", "binance").lower()

    @property
    def use_sandbox(self) -> bool:
        return bool(self.raw.get("use_sandbox", True))

    @property
    def quote_currency(self) -> str:
        return self.raw.get("quote_currency", "USDT")

    @property
    def paper_starting_equity(self) -> float:
        return float(self.raw.get("paper_starting_equity", 10000))

    @property
    def universe(self) -> list[str]:
        return list(self.raw.get("universe", []))

    @property
    def timeframe(self) -> str:
        return self.raw.get("timeframe", "1h")

    @property
    def poll_interval_seconds(self) -> int:
        return int(self.raw.get("poll_interval_seconds", 300))

    @property
    def strategy(self) -> str:
        return self.raw.get("strategy", "ensemble")

    @property
    def strategy_params(self) -> dict[str, Any]:
        return self.raw.get("strategy_params", {})

    @property
    def risk(self) -> dict[str, Any]:
        return self.raw.get("risk", {})

    @property
    def compounding(self) -> dict[str, Any]:
        return self.raw.get("compounding", {})

    @property
    def logging(self) -> dict[str, Any]:
        return self.raw.get("logging", {})

    def validate(self) -> None:
        if self.mode not in ("paper", "live"):
            raise ValueError(f"mode must be 'paper' or 'live', got {self.mode!r}")
        if self.exchange not in ("binance", "kucoin", "bybit"):
            raise ValueError(
                f"exchange must be one of binance/kucoin/bybit, got {self.exchange!r}"
            )
        if not self.universe:
            raise ValueError("universe must contain at least one symbol")
        risk = self.risk
        for key in ("max_position_pct", "stop_loss_pct", "daily_loss_limit_pct"):
            if key in risk and not (0 < float(risk[key]) <= 1):
                raise ValueError(f"risk.{key} must be in (0, 1]")


def load_config(path: str = "config/config.yaml") -> Config:
    """Load YAML config and `.env` (for API keys) into a Config object."""
    if load_dotenv is not None:
        load_dotenv()  # populate os.environ from .env if present

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    cfg = Config(raw=raw)
    cfg.validate()
    return cfg


def exchange_credentials(exchange: str) -> dict[str, str]:
    """Pull API credentials for an exchange from environment variables."""
    ex = exchange.upper()
    creds = {
        "apiKey": os.getenv(f"{ex}_API_KEY", ""),
        "secret": os.getenv(f"{ex}_API_SECRET", ""),
    }
    # KuCoin also needs a passphrase.
    password = os.getenv(f"{ex}_API_PASSWORD", "")
    if password:
        creds["password"] = password
    return creds
