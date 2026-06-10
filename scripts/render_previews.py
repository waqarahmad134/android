"""Render static PNG previews of the dashboard and settings pages (dark theme,
demo data). Used to visualize the UI without a browser.
"""
from __future__ import annotations

import math
import random
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BG = "#0b1220"; PANEL = "#131c2e"; PANEL2 = "#0f1726"; LINE = "#243049"
TXT = "#e6edf7"; MUTED = "#8aa0c0"; GREEN = "#27d796"; RED = "#ff5d6c"
ACCENT = "#4f8cff"; GOLD = "#f4c84a"


def demo_state():
    random.seed(11)
    eq = 10000.0; curve = []
    t0 = time.time() - 200 * 3600
    for i in range(200):
        eq *= (1 + random.gauss(0.0010, 0.011))
        curve.append({"t": t0 + i * 3600, "equity": round(eq, 2)})
    peak = -1e9; dd = []
    for p in curve:
        peak = max(peak, p["equity"])
        dd.append({"t": p["t"], "dd": round((peak - p["equity"]) / peak * 100, 3)})
    perf = {
        "by_strategy": {
            "ema_crossover": {"trades": 31, "total_pnl": 612.4, "win_rate": 58.0},
            "rsi_mean_reversion": {"trades": 24, "total_pnl": -88.2, "win_rate": 41.0},
            "momentum": {"trades": 19, "total_pnl": 433.7, "win_rate": 63.0},
            "ensemble": {"trades": 27, "total_pnl": 521.9, "win_rate": 66.0},
        },
        "by_symbol_strategy": {
            "BTC/USDT": {"ema_crossover": {"total_pnl": 410.2, "win_rate": 61, "trades": 14}},
            "ETH/USDT": {"momentum": {"total_pnl": 233.1, "win_rate": 64, "trades": 9}},
            "SOL/USDT": {"ensemble": {"total_pnl": 180.5, "win_rate": 67, "trades": 8}},
            "PAXG/USDT": {"rsi_mean_reversion": {"total_pnl": 44.0, "win_rate": 55, "trades": 6}},
        },
    }
    assignments = {"BTC/USDT": "ema_crossover", "ETH/USDT": "momentum",
                   "SOL/USDT": "ensemble", "PAXG/USDT": "rsi_mean_reversion"}
    recommendations = dict(assignments)
    trades = []
    for i in range(20):
        e = random.uniform(95, 105); pnl = random.gauss(12, 38)
        trades.append({"symbol": random.choice(list(assignments)), "entry_price": round(e, 2),
                       "exit_price": round(e * (1 + pnl / 1000), 2), "amount": round(random.uniform(.01, .5), 4),
                       "pnl": round(pnl, 2), "strategy": random.choice(list(perf["by_strategy"]))})
    return {
        "updated_at": time.time(), "mode": "paper", "exchange": "binance",
        "strategy": "router:auto", "strategy_mode": "auto", "quote_currency": "USDT",
        "equity": round(eq, 2), "reserve": 980.0,
        "realized_pnl": round(sum(t["pnl"] for t in trades), 2), "halted": False,
        "positions": [
            {"symbol": "BTC/USDT", "amount": .0182, "entry_price": 61240, "price": 62010, "stop_loss": 60015, "take_profit": 63690, "strategy": "ema_crossover", "unrealized_pnl": 14.0},
            {"symbol": "PAXG/USDT", "amount": .21, "entry_price": 2335, "price": 2351, "stop_loss": 2288, "take_profit": 2428, "strategy": "rsi_mean_reversion", "unrealized_pnl": 3.4}],
        "closed_trades": trades, "equity_curve": curve, "drawdown_curve": dd,
        "assignments": assignments, "recommendations": recommendations, "performance": perf,
    }


def panel(ax, x, y, w, h, color=PANEL, ec=LINE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.01",
                                fc=color, ec=ec, lw=1, mutation_aspect=1))


def style_axes(a):
    a.set_facecolor(PANEL)
    for sp in a.spines.values():
        sp.set_color(LINE)
    a.tick_params(colors=MUTED, labelsize=7)
    a.grid(color=LINE, alpha=0.5)
    a.margins(x=0)


def render_dashboard(s, out):
    q = s["quote_currency"]
    fig = plt.figure(figsize=(12, 14), dpi=100); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    panel(ax, 0, 0.965, 1, 0.035, color=PANEL2)
    ax.scatter(0.018, 0.982, s=70, color=GREEN, zorder=5)
    ax.text(0.033, 0.982, "Multi-Exchange Trading Bot", color=TXT, fontsize=13, fontweight="bold", va="center")
    ax.text(0.79, 0.982, f"Mode PAPER   Strategy router:{s['strategy_mode']}   Status TRADING",
            color=MUTED, fontsize=9, va="center", ha="right")
    ax.text(0.985, 0.982, "⚙ Settings", color=ACCENT, fontsize=9.5, va="center", ha="right", fontweight="bold")

    cards = [("EQUITY", f"{s['equity']:,.0f} {q}", TXT),
             ("REALIZED PNL", f"{s['realized_pnl']:+,.0f} {q}", GREEN if s['realized_pnl'] >= 0 else RED),
             ("RESERVE", f"{s['reserve']:,.0f} {q}", TXT),
             ("OPEN", str(len(s['positions'])), TXT),
             ("WIN RATE", "62%", ACCENT)]
    cw, gap, x0, cy, ch = 0.186, 0.008, 0.016, 0.905, 0.05
    for i, (lab, val, col) in enumerate(cards):
        x = x0 + i * (cw + gap); panel(ax, x, cy, cw, ch)
        ax.text(x + 0.012, cy + ch - 0.014, lab, color=MUTED, fontsize=8, fontweight="bold")
        ax.text(x + 0.012, cy + 0.013, val, color=col, fontsize=14, fontweight="bold")

    # equity + drawdown
    panel(ax, 0.016, 0.70, 0.482, 0.185); ax.text(0.03, 0.862, "Equity curve (compounding)", color=MUTED, fontsize=10, fontweight="bold")
    panel(ax, 0.508, 0.70, 0.476, 0.185); ax.text(0.522, 0.862, "Drawdown %", color=MUTED, fontsize=10, fontweight="bold")
    a1 = fig.add_axes([0.05, 0.715, 0.42, 0.13]); style_axes(a1)
    ys = [p["equity"] for p in s["equity_curve"]]
    a1.plot(range(len(ys)), ys, color=ACCENT, lw=2); a1.fill_between(range(len(ys)), ys, min(ys), color=ACCENT, alpha=.12)
    a2 = fig.add_axes([0.55, 0.715, 0.41, 0.13]); style_axes(a2)
    dz = [p["dd"] for p in s["drawdown_curve"]]
    a2.plot(range(len(dz)), dz, color=RED, lw=2); a2.fill_between(range(len(dz)), dz, 0, color=RED, alpha=.12)

    # per-strategy charts
    panel(ax, 0.016, 0.50, 0.482, 0.185); ax.text(0.03, 0.662, "Realized PnL by strategy", color=MUTED, fontsize=10, fontweight="bold")
    panel(ax, 0.508, 0.50, 0.476, 0.185); ax.text(0.522, 0.662, "Win rate by strategy %", color=MUTED, fontsize=10, fontweight="bold")
    names = list(s["performance"]["by_strategy"]); short = [n.split("_")[0] for n in names]
    pnls = [s["performance"]["by_strategy"][n]["total_pnl"] for n in names]
    wins = [s["performance"]["by_strategy"][n]["win_rate"] for n in names]
    a3 = fig.add_axes([0.05, 0.515, 0.42, 0.12]); style_axes(a3)
    a3.bar(short, pnls, color=[GREEN if p >= 0 else RED for p in pnls])
    a4 = fig.add_axes([0.55, 0.515, 0.41, 0.12]); style_axes(a4); a4.set_ylim(0, 100)
    a4.bar(short, wins, color=GREEN)

    # per-coin assignment table
    panel(ax, 0.016, 0.345, 0.968, 0.14)
    ax.text(0.03, 0.462, "Per-coin strategy (active vs. backtest recommendation)", color=MUTED, fontsize=10, fontweight="bold")
    cols = ["Symbol", "Active strategy", "Recommended", "Live PnL", "Win %", "Trades"]
    colx = [0.03, 0.22, 0.44, 0.66, 0.80, 0.91]
    for c, cx in zip(cols, colx):
        ax.text(cx, 0.435, c.upper(), color=MUTED, fontsize=8, fontweight="bold")
    yy = 0.408
    for sym, active in s["assignments"].items():
        st = list(s["performance"]["by_symbol_strategy"][sym].values())[0]
        ax.text(colx[0], yy, sym, color=TXT, fontsize=9)
        ax.text(colx[1], yy, active, color=ACCENT, fontsize=9, fontweight="bold")
        ax.text(colx[2], yy, s["recommendations"][sym], color=ACCENT, fontsize=9)
        ax.text(colx[3], yy, f"+{st['total_pnl']:.1f}", color=GREEN, fontsize=9)
        ax.text(colx[4], yy, f"{st['win_rate']}%", color=TXT, fontsize=9)
        ax.text(colx[5], yy, str(st["trades"]), color=TXT, fontsize=9)
        yy -= 0.026

    # open positions
    panel(ax, 0.016, 0.18, 0.968, 0.15)
    ax.text(0.03, 0.305, "Open positions", color=MUTED, fontsize=10, fontweight="bold")
    pc = ["Symbol", "Strategy", "Qty", "Entry", "Price", "Stop", "Target", "Unrealized"]
    pcx = [0.03, 0.16, 0.33, 0.44, 0.55, 0.66, 0.77, 0.89]
    for c, cx in zip(pc, pcx):
        ax.text(cx, 0.282, c.upper(), color=MUTED, fontsize=7.5, fontweight="bold")
    yy = 0.255
    for p in s["positions"]:
        v = [p["symbol"], p["strategy"], f"{p['amount']:.4f}", f"{p['entry_price']:,.0f}",
             f"{p['price']:,.0f}", f"{p['stop_loss']:,.0f}", f"{p['take_profit']:,.0f}"]
        for x, cx in zip(v, pcx[:-1]):
            ax.text(cx, yy, x, color=TXT, fontsize=8.5)
        ax.text(pcx[-1], yy, f"+{p['unrealized_pnl']:.2f}", color=GREEN, fontsize=8.5, fontweight="bold")
        yy -= 0.026

    # recent trades
    panel(ax, 0.016, 0.015, 0.968, 0.15)
    ax.text(0.03, 0.14, "Recent trades", color=MUTED, fontsize=10, fontweight="bold")
    tc = ["Symbol", "Strategy", "Entry", "Exit", "Qty", "PnL"]
    tcx = [0.03, 0.18, 0.40, 0.55, 0.70, 0.88]
    for c, cx in zip(tc, tcx):
        ax.text(cx, 0.117, c.upper(), color=MUTED, fontsize=7.5, fontweight="bold")
    yy = 0.09
    for t in list(reversed(s["closed_trades"]))[:3]:
        col = GREEN if t["pnl"] >= 0 else RED
        ax.text(tcx[0], yy, t["symbol"], color=TXT, fontsize=8.5)
        ax.text(tcx[1], yy, t["strategy"].split("_")[0], color=MUTED, fontsize=8.5)
        ax.text(tcx[2], yy, f"{t['entry_price']:.2f}", color=TXT, fontsize=8.5)
        ax.text(tcx[3], yy, f"{t['exit_price']:.2f}", color=TXT, fontsize=8.5)
        ax.text(tcx[4], yy, f"{t['amount']:.4f}", color=TXT, fontsize=8.5)
        ax.text(tcx[5], yy, f"{t['pnl']:+.2f}", color=col, fontsize=8.5, fontweight="bold")
        yy -= 0.026

    fig.savefig(out, facecolor=BG); print("wrote", out)


def render_settings(out):
    fig = plt.figure(figsize=(11, 9), dpi=100); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    panel(ax, 0, 0.95, 1, 0.05, color=PANEL2)
    ax.text(0.02, 0.975, "⚙ Settings & Admin", color=TXT, fontsize=14, fontweight="bold", va="center")
    ax.text(0.98, 0.975, "← Back to dashboard", color=ACCENT, fontsize=10, va="center", ha="right")

    # admin token
    panel(ax, 0.02, 0.83, 0.96, 0.09)
    ax.text(0.04, 0.895, "Admin token", color=TXT, fontsize=11, fontweight="bold")
    ax.text(0.04, 0.872, "Required to save changes. Stored only in this browser; matches ADMIN_TOKEN on the server.",
            color=MUTED, fontsize=8.5)
    panel(ax, 0.04, 0.842, 0.55, 0.022, color=PANEL2); ax.text(0.05, 0.853, "••••••••••••", color=MUTED, fontsize=9, va="center")
    panel(ax, 0.61, 0.842, 0.10, 0.022, color=PANEL2); ax.text(0.66, 0.853, "Remember", color=TXT, fontsize=9, va="center", ha="center")

    # config values
    panel(ax, 0.02, 0.30, 0.96, 0.51)
    ax.text(0.04, 0.785, "Configuration values", color=TXT, fontsize=11, fontweight="bold")
    ax.text(0.04, 0.762, "Every key from config.yaml. Risk/strategy/universe apply live; mode/exchange need a restart.",
            color=MUTED, fontsize=8.5)
    rows = [("risk", ["risk.max_position_pct", "risk.stop_loss_pct", "risk.take_profit_pct",
                      "risk.daily_loss_limit_pct", "risk.per_trade_risk_pct"],
             ["0.15", "0.02", "0.04", "0.03", "0.01"]),
            ("strategy_selection", ["strategy_selection.mode", "strategy_selection.default",
                                    "strategy_selection.auto.min_trades"], ["auto", "ensemble", "5"]),
            ("universe", ["universe"], ["BTC/USDT, ETH/USDT, SOL/USDT, PAXG/USDT"])]
    y = 0.735
    for sec, keys, vals in rows:
        ax.text(0.04, y, sec.upper(), color=ACCENT, fontsize=9, fontweight="bold"); y -= 0.026
        for k, v in zip(keys, vals):
            ax.text(0.05, y, k, color=MUTED, fontsize=8.5, family="monospace")
            panel(ax, 0.42, y - 0.011, 0.55, 0.02, color=PANEL2)
            ax.text(0.43, y, str(v), color=TXT, fontsize=8.5, va="center")
            y -= 0.027
        y -= 0.006
    panel(ax, 0.04, 0.315, 0.17, 0.025, color=ACCENT)
    ax.text(0.125, 0.327, "Save configuration", color="#fff", fontsize=9, fontweight="bold", va="center", ha="center")
    panel(ax, 0.22, 0.315, 0.24, 0.025, color=PANEL2)
    ax.text(0.34, 0.327, "Apply backtest recommendation", color=TXT, fontsize=9, va="center", ha="center")

    # keys
    panel(ax, 0.02, 0.02, 0.96, 0.26)
    ax.text(0.04, 0.255, "API keys & secrets", color=TXT, fontsize=11, fontweight="bold")
    ax.text(0.04, 0.233, "Stored in .env (never shown in full, never committed). Blank = keep. Use trade-only keys.",
            color=MUTED, fontsize=8.5)
    keys = [("BINANCE_API_KEY", "· ••••wxyz"), ("BINANCE_API_SECRET", "· ••••3a9f"),
            ("KUCOIN_API_KEY", "· not set"), ("BYBIT_API_KEY", "· ••••7b2c"),
            ("SLACK_WEBHOOK_URL", "· ••••T0kn"), ("ADMIN_TOKEN", "· ••••9xQ2")]
    y = 0.205
    for k, prev in keys:
        ax.text(0.05, y, k, color=MUTED, fontsize=8.5, family="monospace")
        ax.text(0.30, y, prev, color=MUTED, fontsize=8)
        panel(ax, 0.42, y - 0.011, 0.55, 0.02, color=PANEL2)
        ax.text(0.43, y, "••••  (keep)", color=MUTED, fontsize=8, va="center")
        y -= 0.029
    panel(ax, 0.04, 0.03, 0.10, 0.025, color=ACCENT)
    ax.text(0.09, 0.042, "Save keys", color="#fff", fontsize=9, fontweight="bold", va="center", ha="center")

    fig.savefig(out, facecolor=BG); print("wrote", out)


if __name__ == "__main__":
    s = demo_state()
    render_dashboard(s, "docs/dashboard-preview.png")
    render_settings("docs/settings-preview.png")
