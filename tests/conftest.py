"""Shared test fixtures, including an offline fake exchange."""
import math
import time

import pytest

from src.exchanges.base import Balance, ExchangeAdapter, OrderResult


class FakeExchange(ExchangeAdapter):
    """Deterministic in-memory exchange: a sine-wave price for repeatable tests."""

    name = "fake"

    def __init__(self, start_price=100.0, bars=500):
        self.bars = bars
        now = int(time.time() * 1000)
        self._candles = {}
        # Build a gently trending + oscillating series.
        self._series = [
            start_price * (1 + 0.0005 * i) + 5 * math.sin(i / 8.0)
            for i in range(bars)
        ]
        self._now = now
        self._wallet = {}

    def _ohlcv_for(self, symbol):
        if symbol not in self._candles:
            rows = []
            for i, price in enumerate(self._series):
                ts = self._now - (self.bars - i) * 3_600_000
                o = price
                c = self._series[min(i + 1, self.bars - 1)]
                h = max(o, c) * 1.001
                low = min(o, c) * 0.999
                rows.append([ts, o, h, low, c, 10.0])
            self._candles[symbol] = rows
        return self._candles[symbol]

    def fetch_ohlcv(self, symbol, timeframe="1h", limit=500):
        return self._ohlcv_for(symbol)[-limit:]

    def fetch_price(self, symbol):
        return float(self._ohlcv_for(symbol)[-1][4])

    def fetch_balance(self, currency):
        amt = self._wallet.get(currency, 0.0)
        return Balance(free=amt, used=0.0, total=amt)

    def create_market_order(self, symbol, side, amount):
        price = self.fetch_price(symbol)
        return OrderResult(
            id="fake", symbol=symbol, side=side, amount=amount,
            price=price, cost=price * amount, fee=0.0, status="closed",
        )


@pytest.fixture
def fake_exchange():
    return FakeExchange()
