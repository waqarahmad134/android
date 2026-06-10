from src.notify import NullNotifier, create_notifier
from src.notify.base import Notifier
from src.notify.slack import SlackNotifier


class RecordingNotifier(Notifier):
    def __init__(self):
        self.messages = []

    def send(self, text, level="info"):
        self.messages.append((level, text))


def test_null_notifier_is_silent():
    assert NullNotifier().send("hi") is None


def test_factory_disabled_returns_null():
    assert isinstance(create_notifier({"enabled": False}), NullNotifier)


def test_factory_enabled_without_url_falls_back_to_null(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    n = create_notifier({"enabled": True, "provider": "slack"})
    assert isinstance(n, NullNotifier)


def test_slack_respects_min_level(monkeypatch):
    calls = []
    # Block any real network call; record what would have been sent.
    monkeypatch.setattr(
        "src.notify.slack.urllib.request.urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not send")),
    )
    n = SlackNotifier("http://example.invalid/hook", min_level="trade")
    n.send("info-level", level="info")          # dropped, no network call
    assert calls == []


def test_helper_methods_format_and_dispatch():
    rec = RecordingNotifier()
    rec.entry("BTC/USDT", 0.5, 100.0, "ensemble")
    rec.exit("BTC/USDT", 110.0, 5.0, "take_profit")
    rec.circuit_breaker(3.2)
    levels = [lvl for lvl, _ in rec.messages]
    assert levels == ["trade", "trade", "alert"]
    assert "ENTER" in rec.messages[0][1]
    assert "EXIT" in rec.messages[1][1]


def test_report_helper_sends_as_alert():
    rec = RecordingNotifier()
    rec.report("DEMO READINESS REPORT\n  Total return: +6%")
    assert rec.messages[0][0] == "alert"
    assert "Readiness report" in rec.messages[0][1]
    assert "Total return" in rec.messages[0][1]
