from unittest.mock import Mock

from src import notifier


def test_payload_format_for_new_skills():
    payload = notifier.build_discord_payload(
        [
            {"name": "abc", "category": "owner/repo", "url": "https://skills.sh/owner/repo/abc"},
            {"name": "xyz", "category": "owner/repo", "url": "https://skills.sh/owner/repo/xyz"},
        ]
    )
    content = payload["content"]
    assert "1. **abc**" in content
    assert "2. **xyz**" in content
    assert "https://skills.sh/owner/repo/abc" in content


def test_no_send_when_empty(monkeypatch):
    called = {"ok": False}

    def fake_post(url, json, timeout):
        called["ok"] = True
        raise AssertionError("Should not call when empty")

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    notifier.notify_if_new([], "https://example.webhook")
    assert called["ok"] is False


def test_send_payload(monkeypatch):
    sent = {}

    def fake_post(url, json, timeout):
        sent["url"] = url
        sent["json"] = json
        sent["timeout"] = timeout
        mock = Mock()
        mock.status_code = 204
        mock.raise_for_status = Mock()
        return mock

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    notifier.notify_if_new(
        [{"name": "abc", "category": "owner/repo", "url": "https://skills.sh/owner/repo/abc"}],
        "https://example.webhook",
    )
    assert sent["url"] == "https://example.webhook"
    assert sent["json"]["content"].startswith("새로운 trending skill")
    assert sent["timeout"] == 15


def test_notify_retries_until_success(monkeypatch):
    calls = {"cnt": 0}

    def fake_post(url, json, timeout):
        calls["cnt"] += 1
        if calls["cnt"] < 3:
            raise RuntimeError("temporary")
        mock = Mock()
        mock.status_code = 204
        mock.raise_for_status = Mock()
        return mock

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    notifier.send_to_discord("https://example.webhook", {"content": "ok"}, retries=3, backoff_seconds=0)
    assert calls["cnt"] == 3


def test_retry_gives_up_on_fail(monkeypatch):
    class E(Exception):
        pass

    def fake_post(url, json, timeout):
        raise E("fail")

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    try:
        notifier.send_to_discord("https://example.webhook", {"content": "ok"}, retries=2, backoff_seconds=0)
    except Exception as exc:
        assert isinstance(exc, E)
    else:
        raise AssertionError("expected exception")


def test_send_multiple_batches(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(json["content"])
        mock = Mock()
        mock.status_code = 204
        mock.raise_for_status = Mock()
        return mock

    monkeypatch.setattr(notifier.requests, "post", fake_post)

    notifier.notify_if_new(
        [{"name": f"s{i}", "category": "owner/repo", "url": f"https://skills.sh/owner/repo/s{i}"}
         for i in range(18)],
        "https://example.webhook",
        retries=1,
    )

    # 18 items => 2 batches with MAX_ITEMS_PER_MESSAGE=15
    assert len(calls) == 2
    assert "1. **s0**" in calls[0]
    assert "15. **s14**" in calls[0]
    assert "16. **s15**" in calls[1]
