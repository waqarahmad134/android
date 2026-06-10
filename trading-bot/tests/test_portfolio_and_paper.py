from src.exchanges.paper import PaperAdapter
from src.portfolio import Portfolio


def test_paper_buy_then_sell_updates_wallet(fake_exchange):
    paper = PaperAdapter(fake_exchange, "USDT", starting_equity=10000, fee_rate=0.0, slippage=0.0)
    price = paper.fetch_price("BTC/USDT")

    buy = paper.create_market_order("BTC/USDT", "buy", 1.0)
    assert buy.status == "closed"
    assert paper.fetch_balance("BTC").free == 1.0
    assert abs(paper.fetch_balance("USDT").free - (10000 - price)) < 1e-6

    sell = paper.create_market_order("BTC/USDT", "sell", 1.0)
    assert sell.status == "closed"
    assert paper.fetch_balance("BTC").free == 0.0


def test_paper_rejects_insufficient_balance(fake_exchange):
    paper = PaperAdapter(fake_exchange, "USDT", starting_equity=10, slippage=0.0, fee_rate=0.0)
    res = paper.create_market_order("BTC/USDT", "buy", 100.0)
    assert res.status == "rejected"


def test_portfolio_profit_reserve_skims_gains():
    pf = Portfolio(quote_currency="USDT", cash=10000, profit_reserve_pct=0.2)
    pf.open_position("BTC/USDT", amount=1.0, price=100, cost=100,
                     stop_loss=98, take_profit=104)
    pnl = pf.close_position("BTC/USDT", price=110, proceeds=110)
    assert pnl == 10
    # 20% of the 10 profit is locked away.
    assert abs(pf.reserve - 2.0) < 1e-9
    assert abs(pf.realized_pnl - 10) < 1e-9


def test_portfolio_equity_includes_open_positions():
    pf = Portfolio(quote_currency="USDT", cash=9000)
    pf.open_position("BTC/USDT", amount=1.0, price=1000, cost=1000,
                     stop_loss=980, take_profit=1040)
    # cash 8000 + position worth 1100 at new price.
    assert pf.equity({"BTC/USDT": 1100}) == 9100
