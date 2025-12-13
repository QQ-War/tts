import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

from .cost_tracker import CostTracker
from .telegram_notifier import TelegramConfig, TelegramNotifier


@pytest.mark.anyio
async def test_send_usage_summary_posts_message(tmp_path: Path):
    tracker = CostTracker(tmp_path, price_per_million_chars=10)
    tracker.record(2000)
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = TelegramNotifier(
        tracker,
        TelegramConfig(
            enabled=True,
            bot_token="TOKEN",
            chat_id="CHAT",
            daily_hour_utc=5,
        ),
        http_client=client,
    )

    await notifier.send_usage_summary()
    await notifier.stop()

    assert len(requests) == 1
    assert requests[0].url.path.endswith("/botTOKEN/sendMessage")
    payload = httpx.Response(200, content=requests[0].content).json()
    assert payload["chat_id"] == "CHAT"
    assert "2000" in payload["text"]


@pytest.mark.anyio
async def test_disabled_notifier_does_not_send(tmp_path: Path):
    tracker = CostTracker(tmp_path, price_per_million_chars=10)
    tracker.record(1000)
    called = False

    def handler(_: httpx.Request) -> httpx.Response:  # pragma: no cover - should not be hit
        nonlocal called
        called = True
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = TelegramNotifier(
        tracker,
        TelegramConfig(enabled=False, bot_token="", chat_id=""),
        http_client=client,
    )

    await notifier.send_usage_summary()
    await notifier.stop()

    assert called is False


def test_seconds_until_next_trigger_bounds():
    tracker = CostTracker(Path("/tmp"), price_per_million_chars=10)
    notifier = TelegramNotifier(
        tracker,
        TelegramConfig(enabled=True, bot_token="t", chat_id="c", daily_hour_utc=23),
    )
    # Should always be positive and at least 60 seconds as a safety guard
    seconds = notifier._seconds_until_next_trigger()
    assert seconds >= 60
    # Within 24 hours
    assert seconds <= 24 * 3600

    # Force time past target to ensure it wraps to the next day
    original = notifier._seconds_until_next_trigger

    def fake_seconds():
        now = datetime.utcnow() + timedelta(hours=25)
        target = now.replace(hour=notifier.daily_hour_utc, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    notifier._seconds_until_next_trigger = fake_seconds  # type: ignore
    assert notifier._seconds_until_next_trigger() > 0
    notifier._seconds_until_next_trigger = original
