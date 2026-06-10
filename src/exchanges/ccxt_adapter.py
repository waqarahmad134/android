"""Live exchange adapter backed by ccxt (Binance, KuCoin, Bybit)."""
from __future__ import annotations

from ..utils.logger import get_logger
from .base import Balance, ExchangeAdapter, OrderResult

log = get_logger(__name__)

# ccxt class names per supported exchange.
_CCXT_IDS = {
    "binance": "binance",
    "kucoin": "kucoin",
    "bybit": "bybit",
}


class CCXTAdapter(ExchangeAdapter):
    """Thin wrapper over a ccxt exchange instance.

    Used for LIVE trading (and live market-data even in paper mode). Order
    placement here hits the real (or sandbox) exchange — guarded by the engine,
    which only calls it when mode == 'live'.
    """

    def __init__(self, exchange_id: str, credentials: dict, use_sandbox: bool = True):
        import ccxt  # imported lazily so paper/backtest don't require network libs

        if exchange_id not in _CCXT_IDS:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        self.name = exchange_id
        klass = getattr(ccxt, _CCXT_IDS[exchange_id])
        params = {"enableRateLimit": True}
        # Only attach credentials if provided (market-data works without them).
        if credentials.get("apiKey"):
            params.update(credentials)

        self._client = klass(params)
        if use_sandbox:
            try:
                self._client.set_sandbox_mode(True)
                log.info("%s sandbox mode enabled", exchange_id)
            except Exception as exc:  # not every exchange supports sandbox
                log.warning("Sandbox not available for %s: %s", exchange_id, exc)

    def fetch_ohlcv(self, symbol, timeframe="1h", limit=500):
        return self._client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_price(self, symbol):
        ticker = self._client.fetch_ticker(symbol)
        return float(ticker["last"])

    def fetch_balance(self, currency):
        bal = self._client.fetch_balance()
        entry = bal.get(currency, {})
        return Balance(
            free=float(entry.get("free", 0) or 0),
            used=float(entry.get("used", 0) or 0),
            total=float(entry.get("total", 0) or 0),
        )

    def create_market_order(self, symbol, side, amount):
        order = self._client.create_order(symbol, "market", side, amount)
        avg = float(order.get("average") or order.get("price") or 0)
        cost = float(order.get("cost") or (avg * amount))
        fee = 0.0
        fee_obj = order.get("fee") or {}
        if fee_obj:
            fee = float(fee_obj.get("cost", 0) or 0)
        return OrderResult(
            id=str(order.get("id", "")),
            symbol=symbol,
            side=side,
            amount=float(order.get("filled") or amount),
            price=avg,
            cost=cost,
            fee=fee,
            status=order.get("status", "closed"),
        )
