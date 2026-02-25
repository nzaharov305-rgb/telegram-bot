"""Монитор парсинга. 3 цикла по тарифам. Очередь с rate limit и приоритетом PRO."""
import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot

from config import Config
from database import (
    get_pool,
    user_get_active_by_tier,
    sent_was_sent,
    sent_mark,
    sent_count_today,
    stats_increment_messages,
)
from parser import KrishaParser, Listing

logger = logging.getLogger(__name__)

DISTRICT_MAP = {
    "Алмалинский": "almalinskij",
    "Ауэзовский": "aujezovskij",
    "Бостандыкский": "bostandykskij",
    "Жетысуский": "zhetysuskij",
    "Медеуский": "medeuskij",
    "Наурызбайский": "nauryzbajskiy",
    "Турксибский": "turksibskij",
    "Алатауский": "alatauskij",
}


@dataclass(order=True)
class QueueItem:
    priority: int
    user_id: int
    text: str


class SendQueue:
    def __init__(self, bot: Bot, rate: float = 1.0):
        self._bot = bot
        self._rate = rate
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False

    async def put(self, user_id: int, text: str, is_pro: bool = False) -> None:
        p = 0 if is_pro else 1
        await self._queue.put(QueueItem(p, user_id, text))

    async def _worker(self, stats_cb) -> None:
        while self._running:
            try:
                item: QueueItem = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            try:
                await self._bot.send_message(item.user_id, item.text)
                if stats_cb:
                    await stats_cb(1)
            except Exception as e:
                logger.warning("Send to %s failed: %s", item.user_id, e)
            await asyncio.sleep(1.0 / self._rate)

    def start(self, stats_cb=None) -> None:
        self._running = True
        asyncio.create_task(self._worker(stats_cb))


async def _process_user(
    user: dict,
    listings: list[Listing],
    pool,
    queue: SendQueue,
    config: Config,
) -> None:
    for ls in listings:
        if user.get("from_owner") and not ls.from_owner:
            continue
        if await sent_was_sent(pool, user["user_id"], ls.id):
            continue
        if user.get("subscription_type") == "free":
            if await sent_count_today(pool, user["user_id"]) >= config.FREE_MAX_LISTINGS_PER_DAY:
                continue
        text = f"🏠 {ls.title}\n💰 {ls.price}\n🔗 {ls.url}"
        is_pro = user.get("subscription_type") == "pro"
        await queue.put(user["user_id"], text, is_pro=is_pro)
        await sent_mark(pool, user["user_id"], ls.id)


async def _tier_loop(
    tier: str,
    interval: int,
    config: Config,
    queue: SendQueue,
) -> None:
    pool = await get_pool()
    parser = KrishaParser(config)

    while True:
        try:
            users = await user_get_active_by_tier(pool, tier)
            for user in users:
                try:
                    district = user.get("district")
                    districts = user.get("districts") or []
                    if district and district not in districts:
                        districts = [district]
                    if not districts:
                        continue

                    mode = user.get("mode") or "rent"
                    rooms = user.get("rooms") or 1
                    from_owner = user.get("from_owner") or False

                    for d in districts:
                        slug = DISTRICT_MAP.get(d, d.lower().replace(" ", ""))
                        listings = await parser.parse(mode, rooms, slug, from_owner)
                        await _process_user(user, listings, pool, queue, config)
                except Exception as e:
                    logger.exception("Monitor user %s: %s", user.get("user_id"), e)
        except Exception as e:
            logger.exception("Monitor tier %s: %s", tier, e)
        await asyncio.sleep(interval)


async def run_monitor(bot: Bot, config: Config) -> None:
    pool = await get_pool()
    queue = SendQueue(bot, config.RATE_LIMIT_PER_SECOND)

    async def on_sent(count: int):
        await stats_increment_messages(pool, count)

    queue.start(on_sent)

    await asyncio.gather(
        _tier_loop("pro", config.PRO_CHECK_INTERVAL, config, queue),
        _tier_loop("standard", config.STANDARD_CHECK_INTERVAL, config, queue),
        _tier_loop("free", config.FREE_CHECK_INTERVAL, config, queue),
    )
