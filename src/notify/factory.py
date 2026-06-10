"""Builds a Notifier from config + environment."""
from __future__ import annotations

import os

from ..utils.logger import get_logger
from .base import Notifier, NullNotifier
from .slack import SlackNotifier

log = get_logger(__name__)


def create_notifier(notify_cfg: dict) -> Notifier:
    if not notify_cfg.get("enabled", False):
        return NullNotifier()

    provider = str(notify_cfg.get("provider", "slack")).lower()
    if provider == "slack":
        url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
        if not url:
            log.warning("Notifications enabled but SLACK_WEBHOOK_URL is unset — disabling alerts.")
            return NullNotifier()
        return SlackNotifier(
            webhook_url=url,
            username=notify_cfg.get("username", "trading-bot"),
            min_level=notify_cfg.get("min_level", "trade"),
        )

    log.warning("Unknown notifier provider %r — disabling alerts.", provider)
    return NullNotifier()
