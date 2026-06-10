"""Slack notifier via an Incoming Webhook (no bot token / scopes required).

Create a webhook at https://api.slack.com/messaging/webhooks and put the URL in
the SLACK_WEBHOOK_URL environment variable. Uses only the standard library so it
adds no dependency, and never raises into the trading loop.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..utils.logger import get_logger
from .base import Notifier

log = get_logger(__name__)


class SlackNotifier(Notifier):
    def __init__(self, webhook_url: str, username: str = "trading-bot",
                 min_level: str = "info", timeout: float = 5.0):
        self._url = webhook_url
        self._username = username
        self._timeout = timeout
        # Levels below the threshold are dropped (e.g. mute "info" heartbeats).
        order = {"info": 0, "trade": 1, "alert": 2}
        self._min = order.get(min_level, 0)
        self._order = order

    def send(self, text: str, level: str = "info") -> None:
        if self._order.get(level, 0) < self._min:
            return
        payload = json.dumps({"username": self._username, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            self._url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    log.warning("Slack webhook returned HTTP %s", resp.status)
        except (urllib.error.URLError, OSError) as exc:
            # Network hiccups must never take down the trading loop.
            log.warning("Slack notification failed: %s", exc)
