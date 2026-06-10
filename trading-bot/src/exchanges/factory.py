"""Builds the right exchange adapter for the configured mode."""
from __future__ import annotations

from ..utils.config import Config, exchange_credentials
from ..utils.logger import get_logger
from .base import ExchangeAdapter
from .paper import PaperAdapter

log = get_logger(__name__)


def create_exchange(cfg: Config) -> ExchangeAdapter:
    """Return a ready-to-use adapter.

    - paper mode  -> PaperAdapter wrapping a live ccxt data source.
    - live mode   -> raw CCXTAdapter (real orders).
    """
    from .ccxt_adapter import CCXTAdapter

    creds = exchange_credentials(cfg.exchange)
    data_source = CCXTAdapter(cfg.exchange, creds, use_sandbox=cfg.use_sandbox)

    if cfg.mode == "live":
        if not creds.get("apiKey"):
            raise RuntimeError(
                "Live mode requires API keys in .env for "
                f"{cfg.exchange.upper()}_API_KEY / _SECRET."
            )
        log.warning("LIVE MODE: real orders will be placed on %s", cfg.exchange)
        return data_source

    log.info("PAPER MODE: simulated execution, market data from %s", cfg.exchange)
    return PaperAdapter(
        data_source=data_source,
        quote_currency=cfg.quote_currency,
        starting_equity=cfg.paper_starting_equity,
    )
