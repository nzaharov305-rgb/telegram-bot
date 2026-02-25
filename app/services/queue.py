"""Очередь рассылки с rate limit и приоритетом PRO."""
import asyncio
import logging
from dataclasses import dataclass
from aiogram import Bot

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueueItem:
    priority: int  # 0 = PRO (высший), 1 = STANDARD, 2 = FREE
    user_id: int
    text: str


class SendQueue:
    """Очередь с rate limit 1 msg/sec и приоритетом PRO."""

    def __init__(self, bot: Bot, rate_per_sec: float = 1.0):
        self._bot = bot
        self._rate = rate_per_sec
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._retry_count = 3

    def _priority(self, is_pro: bool) -> int:
        return 0 if is_pro else 1

    async def put(self, user_id: int, text: str, is_pro: bool = False) -> None:
        item = QueueItem(
            priority=self._priority(is_pro),
            user_id=user_id,
            text=text,
        )
        await self._queue.put(item)

    async def _send_with_retry(self, user_id: int, text: str) -> bool:
        for attempt in range(self._retry_count):
            try:
                await self._bot.send_message(user_id, text)
                return True
            except Exception as e:
                logger.warning(f"Send to {user_id} attempt {attempt + 1}: {e}")
                if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                    return False
                await asyncio.sleep(2 ** attempt)
        return False

    async def _worker(self, stats_callback=None) -> None:
        while self._running:
            try:
                item: QueueItem = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue

            ok = await self._send_with_retry(item.user_id, item.text)
            if ok and stats_callback:
                await stats_callback(1)

            await asyncio.sleep(1.0 / self._rate)

    def start(self, stats_callback=None) -> None:
        self._running = True
        asyncio.create_task(self._worker(stats_callback))

    def stop(self) -> None:
        self._running = False
