"""Read/write helpers for the settings page.

Edits config.yaml (values) and .env (API keys) from the dashboard. Uses
ruamel.yaml when available to preserve comments/formatting, falling back to
PyYAML. Secrets are never sent back to the browser in full — only masked.
"""
from __future__ import annotations

import os
import re
from typing import Any

try:
    from ruamel.yaml import YAML
    _yaml = YAML()
    _yaml.preserve_quotes = True
    _HAS_RUAMEL = True
except Exception:  # pragma: no cover - fallback path
    import yaml as _pyyaml
    _HAS_RUAMEL = False


# --- YAML config ---------------------------------------------------------
def read_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        if _HAS_RUAMEL:
            return _yaml.load(fh) or {}
        return _pyyaml.safe_load(fh) or {}


def _dump_config(data: Any, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        if _HAS_RUAMEL:
            _yaml.dump(data, fh)
        else:
            _pyyaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False)


def _coerce(value: Any, existing: Any) -> Any:
    """Coerce an incoming (often string) value to the type of the existing one."""
    if isinstance(value, (list, dict)):
        return value
    s = str(value).strip()
    if isinstance(existing, bool):
        return s.lower() in ("1", "true", "yes", "on")
    if isinstance(existing, int) and not isinstance(existing, bool):
        try:
            return int(float(s))
        except ValueError:
            return existing
    if isinstance(existing, float):
        try:
            return float(s)
        except ValueError:
            return existing
    if isinstance(existing, list):
        parts = [p.strip() for p in re.split(r"[\n,]", s) if p.strip()]
        return parts
    # Unknown / new key: best-effort number, else string.
    for cast in (int, float):
        try:
            return cast(s)
        except ValueError:
            pass
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    return s


def _set_dotted(data: dict, dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    node = data
    for k in keys[:-1]:
        if k not in node or not isinstance(node[k], dict):
            node[k] = {}
        node = node[k]
    existing = node.get(keys[-1])
    node[keys[-1]] = _coerce(value, existing)


def update_config(path: str, updates: dict[str, Any]) -> dict:
    """Apply {dotted.key: value} updates to config.yaml and validate the result."""
    data = read_config(path)
    for dotted, value in updates.items():
        _set_dotted(data, dotted, value)

    # Validate before persisting so a bad edit can't break the bot.
    from .utils.config import Config
    Config(raw=dict(data)).validate()

    _dump_config(data, path)
    return data


# --- .env API keys -------------------------------------------------------
# Keys the settings UI is allowed to manage.
MANAGED_ENV_KEYS = [
    "BINANCE_API_KEY", "BINANCE_API_SECRET",
    "KUCOIN_API_KEY", "KUCOIN_API_SECRET", "KUCOIN_API_PASSWORD",
    "BYBIT_API_KEY", "BYBIT_API_SECRET",
    "SLACK_WEBHOOK_URL", "ADMIN_TOKEN",
]


def _parse_env(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]


def env_status(path: str = ".env") -> dict[str, dict]:
    """Masked view of managed keys: whether set + last-4 preview. Never the secret."""
    current = _parse_env(path)
    # Also reflect values present in the live process environment.
    return {
        k: {
            "set": bool(current.get(k) or os.getenv(k)),
            "preview": _mask(current.get(k) or os.getenv(k, "")),
        }
        for k in MANAGED_ENV_KEYS
    }


def update_env(path: str, updates: dict[str, str]) -> None:
    """Update .env, preserving unmanaged lines. Empty value clears a key."""
    lines: list[str] = []
    seen: set[str] = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()

    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                seen.add(key)
                val = updates[key]
                out.append(f"{key}={val}" if val != "" else f"{key}=")
                continue
        out.append(line)

    # Append any managed keys that weren't already present.
    for key, val in updates.items():
        if key not in seen and key in MANAGED_ENV_KEYS:
            out.append(f"{key}={val}")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.chmod(path, 0o600)  # tighten perms on a secrets file
