"""CLI entry point.

Usage:
    python -m src.main run                       # live/paper trading loop
    python -m src.main backtest --symbol BTC/USDT --strategy ensemble --days 180
    python -m src.main balance                   # show account balances
"""
from __future__ import annotations

import argparse
import sys

from .backtest import run_backtest
from .engine import TradingEngine
from .exchanges import create_exchange
from .strategies import create_strategy
from .utils import load_config
from .utils.logger import configure_logging, get_logger

log = get_logger(__name__)

# Candles per day for common timeframes (used to convert --days -> candle count).
_BARS_PER_DAY = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24, "4h": 6, "1d": 1}


def _setup(args):
    cfg = load_config(args.config)
    log_cfg = cfg.logging
    configure_logging(level=log_cfg.get("level", "INFO"), file=log_cfg.get("file"))
    return cfg


def cmd_run(args):
    cfg = _setup(args)
    if cfg.mode == "live":
        log.warning("=" * 60)
        log.warning("LIVE MODE — real orders will be placed with real funds.")
        log.warning("Ctrl-C within 5s to abort.")
        log.warning("=" * 60)
        import time
        time.sleep(5)
    exchange = create_exchange(cfg)
    strategy = create_strategy(cfg.strategy, cfg.strategy_params)
    TradingEngine(cfg, exchange, strategy).run_forever()


def cmd_backtest(args):
    cfg = _setup(args)
    # Backtests always use a live data source (read-only) regardless of mode.
    from .exchanges.ccxt_adapter import CCXTAdapter
    from .utils.config import exchange_credentials

    exchange = CCXTAdapter(cfg.exchange, exchange_credentials(cfg.exchange), use_sandbox=False)
    strategy = create_strategy(args.strategy or cfg.strategy, cfg.strategy_params)

    timeframe = args.timeframe or cfg.timeframe
    bars = args.days * _BARS_PER_DAY.get(timeframe, 24)
    bars = min(bars, 1000)  # most exchanges cap a single OHLCV request

    result = run_backtest(
        exchange=exchange,
        strategy=strategy,
        risk_cfg=cfg.risk,
        symbol=args.symbol,
        timeframe=timeframe,
        candles=bars,
        start_equity=cfg.paper_starting_equity,
    )
    print(result.summary())


def cmd_balance(args):
    cfg = _setup(args)
    exchange = create_exchange(cfg)
    bal = exchange.fetch_balance(cfg.quote_currency)
    print(f"{cfg.quote_currency}: free={bal.free:.2f} used={bal.used:.2f} total={bal.total:.2f}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multi-exchange, risk-first trading bot")
    p.add_argument("--config", default="config/config.yaml", help="path to config YAML")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="start the trading loop (paper or live)").set_defaults(func=cmd_run)

    bt = sub.add_parser("backtest", help="backtest a strategy on historical data")
    bt.add_argument("--symbol", required=True, help="e.g. BTC/USDT")
    bt.add_argument("--strategy", help="override the configured strategy")
    bt.add_argument("--timeframe", help="override the configured timeframe")
    bt.add_argument("--days", type=int, default=180, help="lookback window in days")
    bt.set_defaults(func=cmd_backtest)

    sub.add_parser("balance", help="show account balance").set_defaults(func=cmd_balance)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:
        log.error("Fatal: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
