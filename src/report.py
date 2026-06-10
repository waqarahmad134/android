"""End-of-demo readiness report.

Summarizes a paper-trading session — overall return, per-strategy and per-coin
performance — and gives a go/no-go verdict per coin to help decide what to take
live. Reads the persisted session file written by the engine.
"""
from __future__ import annotations

import time

from .persistence import load_session

# Thresholds for the per-coin verdict.
MIN_TRADES = 5            # below this, not enough evidence to judge
GOOD_WIN_RATE = 50.0


def _max_drawdown(curve: list[dict]) -> float:
    peak = float("-inf")
    mdd = 0.0
    for p in curve:
        peak = max(peak, p["equity"])
        if peak > 0:
            mdd = max(mdd, (peak - p["equity"]) / peak)
    return mdd * 100


def _coin_verdict(trades: int, total_pnl: float, win_rate: float) -> str:
    if trades < MIN_TRADES:
        return "NEEDS MORE DATA"
    if total_pnl > 0 and win_rate >= GOOD_WIN_RATE:
        return "READY"
    if total_pnl > 0:
        return "PROMISING"
    return "AVOID"


def build_report(session: dict) -> str:
    if not session:
        return ("No session data found. Run the bot in paper mode first:\n"
                "    python -m src.main run\n")

    curve = session.get("equity_curve", [])
    start_eq = session.get("start_equity", 0.0) or (curve[0]["equity"] if curve else 0.0)
    cur_eq = curve[-1]["equity"] if curve else start_eq
    ret_pct = (cur_eq / start_eq - 1) * 100 if start_eq else 0.0
    days = (time.time() - session.get("started_at", time.time())) / 86400
    perf = session.get("performance", {})
    by_strat = perf.get("by_strategy", {})
    by_sym = perf.get("by_symbol_strategy", {})

    lines = []
    lines.append("=" * 64)
    lines.append("  DEMO READINESS REPORT")
    lines.append("=" * 64)
    lines.append(f"  Mode:           {session.get('mode', '?')}")
    lines.append(f"  Running for:    {days:.1f} days")
    lines.append(f"  Start equity:   {start_eq:,.2f}")
    lines.append(f"  Current equity: {cur_eq:,.2f}")
    lines.append(f"  Total return:   {ret_pct:+.2f}%")
    lines.append(f"  Realized PnL:   {session.get('realized_pnl', 0):+,.2f}")
    lines.append(f"  Reserve locked: {session.get('reserve', 0):,.2f}")
    lines.append(f"  Max drawdown:   {_max_drawdown(curve):.2f}%")
    lines.append(f"  Closed trades:  {len(session.get('closed_trades', []))}")

    lines.append("\n  PER-STRATEGY")
    lines.append(f"  {'strategy':<22}{'trades':>7}{'win%':>8}{'pnl':>12}")
    lines.append("  " + "-" * 47)
    for name, st in sorted(by_strat.items(), key=lambda kv: -kv[1].get("total_pnl", 0)):
        lines.append(f"  {name:<22}{st.get('trades', 0):>7}"
                     f"{st.get('win_rate', 0):>8.1f}{st.get('total_pnl', 0):>12.2f}")

    lines.append("\n  PER-COIN  (best strategy + verdict)")
    lines.append(f"  {'symbol':<14}{'best strategy':<22}{'trades':>7}{'win%':>7}{'pnl':>10}  verdict")
    lines.append("  " + "-" * 74)
    ready, avoid = [], []
    for sym, per in by_sym.items():
        # Aggregate across strategies for the coin, and find its best strategy.
        tot_trades = sum(s.get("trades", 0) for s in per.values())
        tot_pnl = sum(s.get("total_pnl", 0) for s in per.values())
        best = max(per.items(), key=lambda kv: kv[1].get("total_pnl", 0))
        best_name, best_stat = best
        wr = best_stat.get("win_rate", 0)
        verdict = _coin_verdict(tot_trades, tot_pnl, wr)
        if verdict == "READY":
            ready.append(sym)
        elif verdict == "AVOID":
            avoid.append(sym)
        lines.append(f"  {sym:<14}{best_name:<22}{tot_trades:>7}{wr:>7.1f}"
                     f"{tot_pnl:>10.2f}  {verdict}")

    lines.append("\n  GO-LIVE CHECKLIST")
    lines.append(f"  [{'x' if days >= 7 else ' '}] Ran at least 7 days in paper mode ({days:.1f} so far)")
    lines.append(f"  [{'x' if ready else ' '}] At least one coin reached READY ({len(ready)}: {', '.join(ready) or '—'})")
    lines.append( "  [ ] Cross-checked with `python -m src.main evaluate` (months of history)")
    lines.append( "  [ ] Set mode: live and added TRADE-ONLY keys (no withdrawals)")
    lines.append( "  [ ] Starting live with the smallest capital you can afford to lose")
    if avoid:
        lines.append(f"\n  Consider dropping from the universe: {', '.join(avoid)}")

    lines.append("\n  NOTE: One week is enough to validate execution and get a feel,")
    lines.append("  but usually too few trades to *finalize* per-coin strategies. Weight")
    lines.append("  the `evaluate` backtest (months of data) more heavily for that.")
    lines.append("  Past performance does not guarantee future results.")
    lines.append("=" * 64)
    return "\n".join(lines)


def print_report(session_path: str | None = None) -> None:
    sess = load_session(session_path) if session_path else load_session()
    print(build_report(sess))
