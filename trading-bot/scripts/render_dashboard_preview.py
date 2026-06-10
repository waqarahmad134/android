"""Render a static PNG preview of the web dashboard (dark theme, demo data).

Used to visualize the dashboard layout without a browser. Reads logs/state.json.
"""
from __future__ import annotations

import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# Palette mirrors src/web/templates/dashboard.html
BG = "#0b1220"; PANEL = "#131c2e"; PANEL2 = "#0f1726"; LINE = "#243049"
TXT = "#e6edf7"; MUTED = "#8aa0c0"; GREEN = "#27d796"; RED = "#ff5d6c"
ACCENT = "#4f8cff"


def panel(ax, x, y, w, h, color=PANEL, ec=LINE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                fc=color, ec=ec, lw=1, mutation_aspect=1))


def main(state_path="logs/state.json", out="docs/dashboard-preview.png"):
    s = json.load(open(state_path))
    q = s.get("quote_currency", "USDT")
    trades = s.get("closed_trades", [])
    wins = sum(1 for t in trades if t["pnl"] > 0)
    winrate = f"{100*wins/len(trades):.0f}%" if trades else "—"

    fig = plt.figure(figsize=(12, 9), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis("off")

    # --- header ---
    panel(ax, 0, 0.945, 1, 0.055, color=PANEL2)
    ax.scatter(0.022, 0.972, s=90, color=GREEN, zorder=5)
    ax.text(0.04, 0.972, "Multi-Exchange Trading Bot", color=TXT, fontsize=15,
            fontweight="bold", va="center")
    meta = (f"Mode  {s.get('mode','—').upper()}    Exchange  {s.get('exchange','—')}    "
            f"Strategy  {s.get('strategy','—')}    Status  "
            f"{'HALTED' if s.get('halted') else 'TRADING'}")
    ax.text(0.985, 0.972, meta, color=MUTED, fontsize=10.5, va="center", ha="right")

    # --- KPI cards ---
    cards = [
        ("EQUITY", f"{s.get('equity',0):,.2f} {q}", TXT),
        ("REALIZED PNL", f"{s.get('realized_pnl',0):+,.2f} {q}",
         GREEN if s.get("realized_pnl", 0) >= 0 else RED),
        ("LOCKED RESERVE", f"{s.get('reserve',0):,.2f} {q}", TXT),
        ("OPEN POSITIONS", str(len(s.get("positions", []))), TXT),
        ("WIN RATE", winrate, ACCENT),
    ]
    cw, gap, x0, cy, ch = 0.181, 0.012, 0.018, 0.83, 0.085
    for i, (label, value, color) in enumerate(cards):
        x = x0 + i * (cw + gap)
        panel(ax, x, cy, cw, ch)
        ax.text(x + 0.014, cy + ch - 0.022, label, color=MUTED, fontsize=8.5,
                fontweight="bold")
        ax.text(x + 0.014, cy + 0.026, value, color=color, fontsize=15, fontweight="bold")

    # --- equity curve ---
    panel(ax, 0.018, 0.49, 0.964, 0.30)
    ax.text(0.034, 0.764, "Equity curve (compounding)", color=MUTED, fontsize=11,
            fontweight="bold")
    curve = s.get("equity_curve", [])
    chart = fig.add_axes([0.05, 0.52, 0.90, 0.215])
    chart.set_facecolor(PANEL)
    ys = [p["equity"] for p in curve]
    chart.plot(range(len(ys)), ys, color=ACCENT, lw=2)
    chart.fill_between(range(len(ys)), ys, min(ys) if ys else 0, color=ACCENT, alpha=0.12)
    for spine in chart.spines.values():
        spine.set_color(LINE)
    chart.tick_params(colors=MUTED, labelsize=8)
    chart.grid(color=LINE, alpha=0.5)
    chart.margins(x=0)

    # --- open positions table ---
    panel(ax, 0.018, 0.265, 0.964, 0.205)
    ax.text(0.034, 0.448, "Open positions", color=MUTED, fontsize=11, fontweight="bold")
    cols = ["Symbol", "Qty", "Entry", "Price", "Stop", "Target", "Unrealized"]
    colx = [0.035, 0.20, 0.33, 0.46, 0.59, 0.72, 0.86]
    for c, cx in zip(cols, colx):
        ax.text(cx, 0.418, c.upper(), color=MUTED, fontsize=8.5, fontweight="bold")
    yy = 0.388
    for p in s.get("positions", []):
        pnl = p["unrealized_pnl"]; pc = GREEN if pnl >= 0 else RED
        vals = [p["symbol"], f"{p['amount']:.4f}", f"{p['entry_price']:,.2f}",
                f"{p['price']:,.2f}", f"{p['stop_loss']:,.2f}", f"{p['take_profit']:,.2f}"]
        for v, cx in zip(vals, colx[:-1]):
            ax.text(cx, yy, v, color=TXT, fontsize=9.5)
        ax.text(colx[-1], yy, f"{pnl:+,.2f}", color=pc, fontsize=9.5, fontweight="bold")
        yy -= 0.03

    # --- recent trades table ---
    panel(ax, 0.018, 0.03, 0.964, 0.215)
    ax.text(0.034, 0.223, "Recent trades", color=MUTED, fontsize=11, fontweight="bold")
    tcols = ["Symbol", "Entry", "Exit", "Qty", "PnL"]
    tcolx = [0.035, 0.28, 0.45, 0.62, 0.86]
    for c, cx in zip(tcols, tcolx):
        ax.text(cx, 0.193, c.upper(), color=MUTED, fontsize=8.5, fontweight="bold")
    yy = 0.163
    for t in list(reversed(trades))[:5]:
        pc = GREEN if t["pnl"] >= 0 else RED
        ax.text(tcolx[0], yy, t["symbol"], color=TXT, fontsize=9.5)
        ax.text(tcolx[1], yy, f"{t['entry_price']:,.2f}", color=TXT, fontsize=9.5)
        ax.text(tcolx[2], yy, f"{t['exit_price']:,.2f}", color=TXT, fontsize=9.5)
        ax.text(tcolx[3], yy, f"{t['amount']:.4f}", color=TXT, fontsize=9.5)
        ax.text(tcolx[4], yy, f"{t['pnl']:+,.2f}", color=pc, fontsize=9.5, fontweight="bold")
        yy -= 0.03

    ax.text(0.5, 0.012, "Read-only viewer · auto-refreshes every 5s · cannot place orders   "
            "|   Past performance does not predict future results.",
            color=MUTED, fontsize=8.5, ha="center")

    fig.savefig(out, facecolor=BG)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
