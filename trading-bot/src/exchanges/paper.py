"""Paper-trading adapter: simulates fills locally, never sends real orders.

Market data is pulled from a real exchange (via a wrapped ccxt adapter) so
signals are realistic, but balances and order execution are simulated in
memory. This is the SAFE DEFAULT.
"""
from __future__ import annotations

import uuid

from ..utils.logger import get_logger
from .base import Balance, ExchangeAdapter, OrderResult

log = get_logger(__name__)

# Conservative taker-fee assumption for simulated fills (0.1%).
DEFAULT_FEE_RATE = 0.001
# Simulated slippage applied against us on market orders (0.05%).
DEFAULT_SLIPPAGE = 0.0005


class PaperAdapter(ExchangeAdapter):
    def __init__(
        self,
        data_source: ExchangeAdapter,
        quote_currency: str,
        starting_equity: float,
        fee_rate: float = DEFAULT_FEE_RATE,
        slippage: float = DEFAULT_SLIPPAGE,
    ):
        self.name = f"paper:{getattr(data_source, 'name', 'sim')}"
        self._data = data_source
        self._quote = quote_currency
        self._fee_rate = fee_rate
        self._slippage = slippage
        # Simulated wallet: currency -> free amount.
        self._wallet: dict[str, float] = {quote_currency: float(starting_equity)}

    # --- market data delegates to the real source ---
    def fetch_ohlcv(self, symbol, timeframe="1h", limit=500):
        return self._data.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_price(self, symbol):
        return self._data.fetch_price(symbol)

    # --- simulated wallet / execution ---
    def fetch_balance(self, currency):
        amt = float(self._wallet.get(currency, 0.0))
        return Balance(free=amt, used=0.0, total=amt)

    def create_market_order(self, symbol, side, amount):
        base, quote = symbol.split("/")
        price = self.fetch_price(symbol)
        # Slippage works against the trader.
        fill = price * (1 + self._slippage) if side == "buy" else price * (1 - self._slippage)
        cost = fill * amount
        fee = cost * self._fee_rate

        if side == "buy":
            needed = cost + fee
            if self._wallet.get(quote, 0.0) < needed:
                return self._reject(symbol, side, amount, fill)
            self._wallet[quote] = self._wallet.get(quote, 0.0) - needed
            self._wallet[base] = self._wallet.get(base, 0.0) + amount
        else:  # sell
            if self._wallet.get(base, 0.0) < amount:
                return self._reject(symbol, side, amount, fill)
            self._wallet[base] = self._wallet.get(base, 0.0) - amount
            self._wallet[quote] = self._wallet.get(quote, 0.0) + (cost - fee)

        log.info("PAPER %s %.8f %s @ %.4f (fee %.4f)", side.upper(), amount, base, fill, fee)
        return OrderResult(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            amount=amount,
            price=fill,
            cost=cost,
            fee=fee,
            status="closed",
        )

    def _reject(self, symbol, side, amount, price) -> OrderResult:
        log.warning("PAPER order REJECTED (insufficient balance): %s %s %.8f", side, symbol, amount)
        return OrderResult(
            id=str(uuid.uuid4()), symbol=symbol, side=side, amount=0.0,
            price=price, cost=0.0, fee=0.0, status="rejected",
        )
