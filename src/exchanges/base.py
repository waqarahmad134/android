"""Exchange-agnostic interface shared by live (ccxt) and paper adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Balance:
    free: float
    used: float
    total: float


@dataclass
class OrderResult:
    id: str
    symbol: str
    side: str          # "buy" or "sell"
    amount: float      # base-asset quantity
    price: float       # average fill price
    cost: float        # quote-currency cost (amount * price)
    fee: float         # quote-currency fee
    status: str        # "closed", "open", "rejected", ...


class ExchangeAdapter(ABC):
    """Minimal surface the engine needs. Implemented by ccxt + paper adapters."""

    name: str = "base"

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> list[list]:
        ...

    @abstractmethod
    def fetch_price(self, symbol: str) -> float:
        ...

    @abstractmethod
    def fetch_balance(self, currency: str) -> Balance:
        ...

    @abstractmethod
    def create_market_order(self, symbol: str, side: str, amount: float) -> OrderResult:
        ...
