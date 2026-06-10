"""Read-only web dashboard for the trading bot.

Serves a single auto-refreshing page plus a JSON API. It only *reads* the state
file written by the engine, so it can never place orders or affect trading.
"""
from __future__ import annotations

from flask import Flask, jsonify, render_template

from ..state import read_state


def create_app(state_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["STATE_PATH"] = state_path

    def _state():
        path = app.config["STATE_PATH"]
        return read_state(path) if path else read_state()

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/api/state")
    def api_state():
        return jsonify(_state())

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def run(host: str = "0.0.0.0", port: int = 8000, state_path: str | None = None) -> None:
    create_app(state_path).run(host=host, port=port)
