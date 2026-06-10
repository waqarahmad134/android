"""Main trading loop. Ties together data, strategy, risk, and execution.

Works identically in paper and live mode — the only difference is which
exchange adapter the factory injects.
"""
from __future__ import annotations

import time

from .data import MarketData
from .exchanges import ExchangeAdapter
from .portfolio import Portfolio
from .risk import RiskManager
from .strategies import Strategy
from .strategies.base import Action
from .utils import Config
from .utils.logger import get_logger

log = get_logger(__name__)


class TradingEngine:
    def __init__(self, cfg: Config, exchange: ExchangeAdapter, strategy: Strategy):
        self.cfg = cfg
        self.exchange = exchange
        self.strategy = strategy
        self.market = MarketData(exchange)
        self.risk = RiskManager(cfg.risk)

        comp = cfg.compounding
        self.portfolio = Portfolio(
            quote_currency=cfg.quote_currency,
            cash=exchange.fetch_balance(cfg.quote_currency).free,
            profit_reserve_pct=float(comp.get("profit_reserve_pct", 0.0)),
            compounding_enabled=bool(comp.get("enabled", True)),
        )
        self._day_index: int | None = None

    # --- helpers ---
    def _prices(self) -> dict[str, float]:
        return {s: self.exchange.fetch_price(s) for s in self.cfg.universe}

    def _roll_day_if_needed(self, equity: float) -> None:
        day = int(time.time() // 86400)
        if self._day_index != day:
            self._day_index = day
            self.risk.start_day(equity)

    # --- one evaluation pass over the whole universe ---
    def step(self) -> None:
        prices = self._prices()
        equity = self.portfolio.equity(prices)
        self._roll_day_if_needed(equity)

        # 1) Manage exits first (always allowed, even when halted).
        for symbol in list(self.portfolio.positions.keys()):
            self._manage_exit(symbol, prices[symbol])

        # Recompute after exits.
        prices = self._prices()
        equity = self.portfolio.equity(prices)

        if self.risk.check_circuit_breaker(equity):
            log.info("Circuit breaker active — skipping new entries.")
            return

        # 2) Look for new entries.
        for symbol in self.cfg.universe:
            if symbol in self.portfolio.positions:
                continue
            self._consider_entry(symbol, prices, equity)

    def _consider_entry(self, symbol: str, prices: dict[str, float], equity: float) -> None:
        df = self.market.ohlcv(symbol, timeframe=self.cfg.timeframe, limit=300)
        signal = self.strategy.generate(df)
        if signal.action is not Action.BUY:
            return

        price = prices[symbol]
        decision = self.risk.size_entry(
            equity=equity,
            price=price,
            confidence=signal.confidence,
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
            decision.stop_loss, decision.take_profit,
        )
        log.info("ENTER %s (%s) conf=%.2f", symbol, signal.reason, signal.confidence)

    def _manage_exit(self, symbol: str, price: float) -> None:
        pos = self.portfolio.positions[symbol]
        pos.update_peak(price)

        reason = self.risk.should_exit(pos.entry_price, price, pos.peak_price)
        # Also exit if the strategy itself flips to SELL.
        if reason is None:
            df = self.market.ohlcv(symbol, timeframe=self.cfg.timeframe, limit=300)
            if self.strategy.generate(df).is_sell:
                reason = "strategy_sell"
        if reason is None:
            return

        order = self.exchange.create_market_order(symbol, "sell", pos.amount)
        if order.status != "closed" or order.amount <= 0:
            log.warning("Exit order for %s did not fill", symbol)
            return
        self.portfolio.close_position(symbol, order.price, order.cost - order.fee)
        log.info("EXIT %s (%s)", symbol, reason)

    # --- continuous run ---
    def run_forever(self) -> None:
        log.info(
            "Engine starting | mode=%s exchange=%s strategy=%s universe=%s",
            self.cfg.mode, self.cfg.exchange, self.strategy.name, self.cfg.universe,
        )
        while True:
            try:
                self.step()
                prices = self._prices()
                log.info(
                    "Equity %.2f | reserve %.2f | open %d | realized %.2f",
                    self.portfolio.equity(prices), self.portfolio.reserve,
                    len(self.portfolio.positions), self.portfolio.realized_pnl,
                )
            except KeyboardInterrupt:
                log.info("Interrupted — shutting down.")
                break
            except Exception as exc:  # keep the loop alive on transient errors
                log.exception("Error in trading step: %s", exc)
            time.sleep(self.cfg.poll_interval_seconds)
