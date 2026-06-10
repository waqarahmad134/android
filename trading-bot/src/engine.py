"""Main trading loop. Ties together data, strategy routing, risk, and execution.

Works identically in paper and live mode — the only difference is which
exchange adapter the factory injects. A StrategyRouter picks the strategy per
symbol (single / routing / auto), and a PerformanceTracker attributes every
closed trade so the system can learn which strategy fits which coin.
"""
from __future__ import annotations

import os
import time

from .data import MarketData
from .exchanges import ExchangeAdapter
from .notify import Notifier, NullNotifier
from .portfolio import Portfolio
from .risk import RiskManager
from .state import write_state
from .strategies.base import Action
from .strategies.performance import PerformanceTracker
from .strategies.router import StrategyRouter
from .utils import Config
from .utils.config import load_config
from .utils.logger import get_logger

log = get_logger(__name__)


class TradingEngine:
    def __init__(self, cfg: Config, exchange: ExchangeAdapter, router: StrategyRouter,
                 notifier: Notifier | None = None, config_path: str = "config/config.yaml"):
        self.cfg = cfg
        self.exchange = exchange
        self.router = router
        self.tracker: PerformanceTracker = router.tracker
        self.notifier = notifier or NullNotifier()
        self.market = MarketData(exchange)
        self.risk = RiskManager(cfg.risk)
        self.config_path = config_path
        self._config_mtime = self._mtime(config_path)

        comp = cfg.compounding
        self.portfolio = Portfolio(
            quote_currency=cfg.quote_currency,
            cash=exchange.fetch_balance(cfg.quote_currency).free,
            profit_reserve_pct=float(comp.get("profit_reserve_pct", 0.0)),
            compounding_enabled=bool(comp.get("enabled", True)),
        )
        self._day_index: int | None = None
        self._equity_curve: list[dict] = []  # rolling (time, equity) for the dashboard

    # --- helpers ---
    @staticmethod
    def _mtime(path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0

    def _prices(self) -> dict[str, float]:
        return {s: self.exchange.fetch_price(s) for s in self.cfg.universe}

    def _maybe_reload_config(self) -> None:
        """Hot-reload tunable settings when config.yaml changes on disk.

        Risk params, strategy selection, compounding and the universe reload
        live. API keys / exchange / mode require a restart (clients init once).
        """
        mtime = self._mtime(self.config_path)
        if mtime <= self._config_mtime:
            return
        try:
            new_cfg = load_config(self.config_path)
        except Exception as exc:
            log.warning("Config reload skipped (invalid): %s", exc)
            self._config_mtime = mtime
            return
        self._config_mtime = mtime

        # Preserve runtime objects; swap in new tunables.
        self.cfg.raw["universe"] = new_cfg.raw.get("universe", self.cfg.universe)
        self.cfg.raw["risk"] = new_cfg.raw.get("risk", self.cfg.risk)
        self.cfg.raw["strategy"] = new_cfg.raw.get("strategy", self.cfg.strategy)
        self.cfg.raw["strategy_params"] = new_cfg.strategy_params
        self.cfg.raw["strategy_selection"] = new_cfg.raw.get("strategy_selection", {})
        self.cfg.raw["compounding"] = new_cfg.compounding

        self.risk = RiskManager(self.cfg.risk)
        # Rebuild the router but keep the accumulated performance tracker.
        from .strategies.router import create_router
        self.router = create_router(self.cfg, tracker=self.tracker,
                                    recommendations=self.router.recommendations)
        self.portfolio.profit_reserve_pct = float(self.cfg.compounding.get("profit_reserve_pct", 0.0))
        log.info("Config hot-reloaded: risk/strategy/universe updated live.")

    def _drawdown_curve(self) -> list[dict]:
        peak = float("-inf")
        out = []
        for p in self._equity_curve:
            peak = max(peak, p["equity"])
            dd = (peak - p["equity"]) / peak * 100 if peak > 0 else 0.0
            out.append({"t": p["t"], "dd": round(dd, 3)})
        return out

    def _write_snapshot(self, prices: dict[str, float], equity: float) -> None:
        """Persist current state for the web dashboard (read-only viewer)."""
        self._equity_curve.append({"t": time.time(), "equity": round(equity, 2)})
        if len(self._equity_curve) > 1000:
            self._equity_curve = self._equity_curve[-1000:]

        positions = [
            {
                "symbol": s, "amount": p.amount, "entry_price": p.entry_price,
                "price": prices.get(s, p.entry_price),
                "stop_loss": p.stop_loss, "take_profit": p.take_profit,
                "strategy": p.strategy,
                "unrealized_pnl": p.unrealized_pnl(prices.get(s, p.entry_price)),
            }
            for s, p in self.portfolio.positions.items()
        ]
        try:
            write_state({
                "mode": self.cfg.mode,
                "exchange": self.cfg.exchange,
                "strategy": self.router.name,
                "strategy_mode": self.router.mode,
                "quote_currency": self.cfg.quote_currency,
                "equity": round(equity, 2),
                "reserve": round(self.portfolio.reserve, 2),
                "realized_pnl": round(self.portfolio.realized_pnl, 2),
                "halted": self.risk.halted,
                "positions": positions,
                "closed_trades": self.portfolio.closed_trades[-50:],
                "equity_curve": self._equity_curve,
                "drawdown_curve": self._drawdown_curve(),
                "assignments": self.router.assignments(self.cfg.universe),
                "recommendations": self.router.recommendations,
                "performance": self.tracker.snapshot(),
            })
        except Exception as exc:  # dashboard I/O must never break trading
            log.warning("Failed to write dashboard state: %s", exc)

    def _roll_day_if_needed(self, equity: float) -> None:
        day = int(time.time() // 86400)
        if self._day_index != day:
            self._day_index = day
            self.risk.start_day(equity)

    # --- one evaluation pass over the whole universe ---
    def step(self) -> None:
        self._maybe_reload_config()
        prices = self._prices()
        equity = self.portfolio.equity(prices)
        self._roll_day_if_needed(equity)

        # 1) Manage exits first (always allowed, even when halted).
        for symbol in list(self.portfolio.positions.keys()):
            self._manage_exit(symbol, prices[symbol])

        # Recompute after exits.
        prices = self._prices()
        equity = self.portfolio.equity(prices)

        was_halted = self.risk.halted
        if self.risk.check_circuit_breaker(equity):
            if not was_halted:  # notify only on the transition into halt
                drawdown = (self.risk._day_start_equity - equity) / self.risk._day_start_equity
                self.notifier.circuit_breaker(drawdown * 100)
            log.info("Circuit breaker active — skipping new entries.")
            return

        # 2) Look for new entries.
        for symbol in self.cfg.universe:
            if symbol in self.portfolio.positions:
                continue
            self._consider_entry(symbol, prices, equity)

    def _consider_entry(self, symbol: str, prices: dict[str, float], equity: float) -> None:
        strat_name, strategy = self.router.resolve(symbol)
        df = self.market.ohlcv(symbol, timeframe=self.cfg.timeframe, limit=300)
        signal = strategy.generate(df)
        if signal.action is not Action.BUY:
            return

        price = prices[symbol]
        decision = self.risk.size_entry(
            equity=equity, price=price, confidence=signal.confidence,
            open_positions=len(self.portfolio.positions),
            current_exposure=self.portfolio.current_exposure(prices),
        )
        if not decision.approved:
            log.debug("Entry blocked for %s: %s", symbol, decision.reason)
            return

        order = self.exchange.create_market_order(symbol, "buy", decision.amount)
        if order.status != "closed" or order.amount <= 0:
            return
        self.portfolio.open_position(
            symbol, order.amount, order.price, order.cost + order.fee,
            decision.stop_loss, decision.take_profit, strategy=strat_name,
        )
        log.info("ENTER %s via %s (%s) conf=%.2f", symbol, strat_name, signal.reason, signal.confidence)
        self.notifier.entry(symbol, order.amount, order.price, f"{strat_name}: {signal.reason}")

    def _manage_exit(self, symbol: str, price: float) -> None:
        pos = self.portfolio.positions[symbol]
        pos.update_peak(price)

        reason = self.risk.should_exit(pos.entry_price, price, pos.peak_price)
        # Also exit if the strategy that opened it flips to SELL.
        if reason is None:
            _, strategy = self.router.resolve(symbol) if not pos.strategy else \
                (pos.strategy, self.router._get(pos.strategy))
            df = self.market.ohlcv(symbol, timeframe=self.cfg.timeframe, limit=300)
            if strategy.generate(df).is_sell:
                reason = "strategy_sell"
        if reason is None:
            return

        order = self.exchange.create_market_order(symbol, "sell", pos.amount)
        if order.status != "closed" or order.amount <= 0:
            log.warning("Exit order for %s did not fill", symbol)
            return
        strat_name = pos.strategy
        pnl = self.portfolio.close_position(symbol, order.price, order.cost - order.fee)
        self.tracker.record(strat_name, symbol, pnl)
        log.info("EXIT %s via %s (%s) PnL %.2f", symbol, strat_name, reason, pnl)
        self.notifier.exit(symbol, order.price, pnl, reason)

    # --- continuous run ---
    def run_forever(self) -> None:
        log.info(
            "Engine starting | mode=%s exchange=%s router=%s universe=%s",
            self.cfg.mode, self.cfg.exchange, self.router.name, self.cfg.universe,
        )
        self.notifier.startup(self.cfg.mode, self.cfg.exchange, self.router.name, self.cfg.universe)
        while True:
            try:
                self.step()
                prices = self._prices()
                equity = self.portfolio.equity(prices)
                log.info(
                    "Equity %.2f | reserve %.2f | open %d | realized %.2f",
                    equity, self.portfolio.reserve,
                    len(self.portfolio.positions), self.portfolio.realized_pnl,
                )
                self.notifier.heartbeat(
                    equity, self.portfolio.reserve,
                    len(self.portfolio.positions), self.portfolio.realized_pnl,
                )
                self._write_snapshot(prices, equity)
            except KeyboardInterrupt:
                log.info("Interrupted — shutting down.")
                break
            except Exception as exc:  # keep the loop alive on transient errors
                log.exception("Error in trading step: %s", exc)
            time.sleep(self.cfg.poll_interval_seconds)
