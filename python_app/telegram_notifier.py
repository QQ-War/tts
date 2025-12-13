import asyncio
import logging
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

from .cost_tracker import CostTracker, UsageRecord

logger = logging.getLogger(__name__)


@dataclass
class TelegramConfig:
    enabled: bool
    bot_token: str
    chat_id: str
    daily_hour_utc: int = 9


class TelegramNotifier:
    """Send daily usage summaries to a Telegram chat."""

    def __init__(
        self,
        cost_tracker: CostTracker,
        config: TelegramConfig,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.cost_tracker = cost_tracker
        self.enabled = bool(config.enabled and config.bot_token and config.chat_id)
        self.bot_token = config.bot_token
        self.chat_id = config.chat_id
        self.daily_hour_utc = max(0, min(int(config.daily_hour_utc), 23))
        self._client = http_client or httpx.AsyncClient(timeout=10.0)
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if not self.enabled or self._task:
            return
        logger.info(
            "Starting Telegram notifier (daily at %02d:00 UTC)", self.daily_hour_utc
        )
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                pass
        await self._client.aclose()

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._seconds_until_next_trigger())
            await self.send_usage_summary()

    async def send_usage_summary(self) -> None:
        if not self.enabled:
            return
        record = self._load_current_usage()
        text = (
            f"Azure TTS {record.month} 用量：{record.characters} 字符，"
            f"预估费用：${record.estimated_cost:.4f}"
        )
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Telegram 用量通知已发送: %s", record)
        except Exception:  # pragma: no cover - network failures should not crash app
            logger.warning("发送 Telegram 用量通知失败", exc_info=True)

    def _load_current_usage(self) -> UsageRecord:
        month = CostTracker._month_key()  # reuse month key
        path = Path(self.cost_tracker.output_dir) / f"{month}.json"
        if not path.is_file():
            return UsageRecord(month=month, characters=0, estimated_cost=0.0)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return UsageRecord(
                month=data.get("month", month),
                characters=int(data.get("characters", 0)),
                estimated_cost=float(data.get("estimated_cost", 0.0)),
            )
        except Exception:
            logger.warning("Failed to read cost file %s; assuming zero usage", path)
            return UsageRecord(month=month, characters=0, estimated_cost=0.0)

    def _seconds_until_next_trigger(self) -> float:
        now = datetime.utcnow()
        target = now.replace(
            hour=self.daily_hour_utc, minute=0, second=0, microsecond=0
        )
        if target <= now:
            target += timedelta(days=1)
        return max((target - now).total_seconds(), 60.0)
