"""Web dashboard + admin settings for the trading bot.

The dashboard is read-only. The settings page can edit config values and API
keys, but every write is gated behind an admin token (ADMIN_TOKEN env var) so an
exposed instance can't be reconfigured by strangers. If ADMIN_TOKEN is unset,
all writes are refused.
"""
from __future__ import annotations

import json
import os

from flask import Flask, abort, jsonify, render_template, request

from ..configio import env_status, read_config, update_config, update_env
from ..state import read_state

EVALUATION_PATH = os.getenv("BOT_EVAL_PATH", "logs/evaluation.json")


def create_app(state_path: str | None = None, config_path: str = "config/config.yaml",
               env_path: str = ".env") -> Flask:
    app = Flask(__name__)
    app.config.update(STATE_PATH=state_path, CONFIG_PATH=config_path, ENV_PATH=env_path)

    def _state():
        path = app.config["STATE_PATH"]
        return read_state(path) if path else read_state()

    def _require_admin():
        token = os.getenv("ADMIN_TOKEN", "")
        if not token:
            abort(403, "Admin writes are disabled: set ADMIN_TOKEN to enable.")
        supplied = request.headers.get("X-Admin-Token", "")
        if supplied != token:
            abort(401, "Invalid admin token.")

    # --- pages ---
    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/settings")
    def settings():
        return render_template("settings.html")

    # --- read APIs ---
    @app.route("/api/state")
    def api_state():
        return jsonify(_state())

    @app.route("/api/evaluation")
    def api_evaluation():
        try:
            with open(EVALUATION_PATH, "r", encoding="utf-8") as fh:
                return jsonify(json.load(fh))
        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify({"matrix": {}, "recommended": {}, "generated_at": None})

    @app.route("/api/config")
    def api_config():
        return jsonify({
            "config": read_config(app.config["CONFIG_PATH"]),
            "keys": env_status(app.config["ENV_PATH"]),
            "admin_enabled": bool(os.getenv("ADMIN_TOKEN", "")),
        })

    # --- write APIs (admin only) ---
    @app.route("/api/config", methods=["POST"])
    def api_config_update():
        _require_admin()
        updates = request.get_json(force=True) or {}
        data = update_config(app.config["CONFIG_PATH"], updates)
        return jsonify({"ok": True, "config": data})

    @app.route("/api/keys", methods=["POST"])
    def api_keys_update():
        _require_admin()
        updates = request.get_json(force=True) or {}
        update_env(app.config["ENV_PATH"], updates)
        return jsonify({"ok": True, "keys": env_status(app.config["ENV_PATH"])})

    @app.route("/api/apply-recommendation", methods=["POST"])
    def api_apply_recommendation():
        _require_admin()
        try:
            with open(EVALUATION_PATH, "r", encoding="utf-8") as fh:
                rec = json.load(fh).get("recommended", {})
        except (FileNotFoundError, json.JSONDecodeError):
            abort(400, "No evaluation results found — run `evaluate` first.")
        updates = {"strategy_selection.mode": "routing"}
        for symbol, strat in rec.items():
            updates[f"strategy_selection.routing.{symbol}"] = strat
        data = update_config(app.config["CONFIG_PATH"], updates)
        return jsonify({"ok": True, "applied": rec, "config": data})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def run(host: str = "0.0.0.0", port: int = 8000, state_path: str | None = None,
        config_path: str = "config/config.yaml", env_path: str = ".env") -> None:
    create_app(state_path, config_path, env_path).run(host=host, port=port)
