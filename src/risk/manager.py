"""Risk management: position sizing, stops, exposure caps, daily circuit breaker.

Capital preservation is the priority. Every rule here exists to make sure a bad
day or a bad signal cannot blow up the account.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class RiskDecision:
    approved: bool
    amount: float = 0.0        # base-asset quantity to trade
    stop_loss: float = 0.0     # price level for hard stop
    take_profit: float = 0.0   # price level for take profit
    reason: str = ""


class RiskManager:
    def __init__(self, risk_cfg: dict):
        self.max_position_pct = float(risk_cfg.get("max_position_pct", 0.15))
        self.max_total_exposure_pct = float(risk_cfg.get("max_total_exposure_pct", 0.60))
        self.max_open_positions = int(risk_cfg.get("max_open_positions", 4))
        self.stop_loss_pct = float(risk_cfg.get("stop_loss_pct", 0.02))
        self.take_profit_pct = float(risk_cfg.get("take_profit_pct", 0.04))
        self.trailing_stop_pct = float(risk_cfg.get("trailing_stop_pct", 0.015))
        self.daily_loss_limit_pct = float(risk_cfg.get("daily_loss_limit_pct", 0.03))
        self.per_trade_risk_pct = float(risk_cfg.get("per_trade_risk_pct", 0.01))

        # Daily circuit-breaker state.
        self._day_start_equity: float | None = None
        self._halted = False

    # --- daily circuit breaker ---
    def start_day(self, equity: float) -> None:
        self._day_start_equity = equity
        self._halted = False
        log.info("Risk: new trading day, start equity %.2f", equity)

    def check_circuit_breaker(self, equity: float) -> bool:
        """Return True if trading is halted for the day."""
        if self._day_start_equity is None:
            self.start_day(equity)
        if self._halted:
            return True
        drawdown = (self._day_start_equity - equity) / self._day_start_equity
        if drawdown >= self.daily_loss_limit_pct:
            self._halted = True
            log.warning(
                "Risk: DAILY LOSS LIMIT hit (-%.2f%%). Halting new entries for the day.",
                drawdown * 100,
            )
        return self._halted

    @property
    def halted(self) -> bool:
        return self._halted

    # --- entry sizing ---
    def size_entry(
        self,
        equity: float,
        price: float,
        confidence: float,
        open_positions: int,
        current_exposure: float,
    ) -> RiskDecision:
        if self._halted:
            return RiskDecision(False, reason="daily circuit breaker active")
        if open_positions >= self.max_open_positions:
            return RiskDecision(False, reason="max open positions reached")

        # Risk-based sizing: never risk more than per_trade_risk_pct of equity,
        # where risk = distance to stop-loss.
        risk_budget = equity * self.per_trade_risk_pct
        stop_distance = price * self.stop_loss_pct
        if stop_distance <= 0:
            return RiskDecision(False, reason="invalid stop distance")
        risk_amount = risk_budget / stop_distance

        # Cap by max position size (scaled by signal confidence).
        max_notional = equity * self.max_position_pct * max(0.3, min(1.0, confidence))
        cap_amount = max_notional / price
        amount = min(risk_amount, cap_amount)

        # Respect total-exposure ceiling.
        room = equity * self.max_total_exposure_pct - current_exposure
        if room <= 0:
            return RiskDecision(False, reason="max total exposure reached")
        amount = min(amount, room / price)

        if amount * price < 1:  # ignore dust-sized orders
            return RiskDecision(False, reason="position too small after risk caps")

        return RiskDecision(
            approved=True,
            amount=amount,
            stop_loss=price * (1 - self.stop_loss_pct),
            take_profit=price * (1 + self.take_profit_pct),
            reason="approved",
        )

    # --- exit checks for an open position ---
    def should_exit(self, entry_price: float, current_price: float, peak_price: float) -> str | None:
        """Return an exit reason ('stop_loss'|'take_profit'|'trailing_stop') or None."""
        if current_price <= entry_price * (1 - self.stop_loss_pct):
            return "stop_loss"
        if current_price >= entry_price * (1 + self.take_profit_pct):
            return "take_profit"
        # Trailing stop: once in profit, lock gains if price falls from the peak.
        if peak_price > entry_price and current_price <= peak_price * (1 - self.trailing_stop_pct):
            return "trailing_stop"
        return None
