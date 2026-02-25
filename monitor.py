"""Монитор парсинга. 3 цикла по тарифам. Очередь с rate limit и приоритетом PRO."""
import asyncio
import logging
from dataclasses import dataclass
from typing import Dict

from aiogram import Bot

from config import Config, get_redis
from database import (
    get_pool,
    user_get_active_by_tier,
    sent_was_sent,
    sent_mark,
    sent_count_today,
    stats_increment_messages,
)
from parser import KrishaParser, Listing
from ai_service import analyze_listing

# limit concurrent AI calls
ai_semaphore = asyncio.Semaphore(3)

logger = logging.getLogger(__name__)

# in-memory cache of pro users -> residential complex
pro_users_cache: Dict[int, str] = {}

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
            # additional delay to avoid 429 errors
            await asyncio.sleep(0.3)
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
    uid = user.get("user_id")
    # pro cache filter
    user_complex = pro_users_cache.get(uid)

    for ls in listings:
        # global redis duplicate cache
        try:
            redis = await get_redis()
            key = f"listing:{ls.id}"
            if await redis.exists(key):
                continue
            await redis.set(key, "sent", ex=3600)
            logger.info(f"Listing cached: {ls.id}")
        except Exception as e:
            logger.warning("Redis cache error: %s", e)

        if user.get("from_owner") and not ls.from_owner:
            continue

        # filter by residential complex for pro users
        if user_complex:
            listing_complex = getattr(ls, "residential_complex", None)
            if listing_complex and listing_complex != user_complex:
                continue

        if await sent_was_sent(pool, uid, ls.id):
            continue
        if user.get("subscription_type") == "free":
            if await sent_count_today(pool, uid) >= config.FREE_MAX_LISTINGS_PER_DAY:
                continue
        text = f"🏠 {ls.title}\n💰 {ls.price}\n🔗 {ls.url}"
        is_pro = user.get("subscription_type") == "pro"

        # AI analysis for PRO users
        if is_pro:
            try:
                async with ai_semaphore:
                    ai_text = await analyze_listing(
                        {
                            "id": ls.id,
                            "title": ls.title,
                            "price": ls.price,
                            "district": user.get("district"),
                            "residential_complex": getattr(ls, "residential_complex", None),
                            "description": getattr(ls, "description", ""),
                        }
                    )
                if ai_text:
                    text += "\n\n🤖 AI Анализ:\n" + ai_text
            except Exception as e:
                logger.warning("AI semaphore error: %s", e)

        await queue.put(uid, text, is_pro=is_pro)
        await sent_mark(pool, uid, ls.id)
        # small delay between outgoing messages to avoid 429
        await asyncio.sleep(0.3)


async def _tier_loop(
    tier: str,
    interval: int,
    config: Config,
    queue: SendQueue,
) -> None:
    pool = await get_pool()
    parser = KrishaParser(config)

    while True:
        logger.info("Monitor heartbeat")
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
                        try:
                            listings = await asyncio.wait_for(
                                parser.parse(mode, rooms, slug, from_owner), timeout=20
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                "Parser timeout for user %s, tier %s, district %s",
                                user.get("user_id"), tier, d,
                            )
                            # skip this district and continue with next one
                            continue
                        await _process_user(user, listings, pool, queue, config)
                except Exception as e:
                    logger.exception("Monitor user %s: %s", user.get("user_id"), e)
        except Exception as e:
            logger.exception("Monitor loop crashed but recovered")
        await asyncio.sleep(interval)


async def refresh_pro_cache() -> None:
    try:
        pool = await get_pool()
        users = await user_get_active_by_tier(pool, "pro")
        pro_users_cache.clear()
        for u in users:
            rc = u.get("residential_complex")
            if rc:
                pro_users_cache[u["user_id"]] = rc
        logger.info("PRO cache refreshed")
    except Exception as e:
        logger.exception("Failed to refresh PRO cache: %s", e)


async def _pro_cache_refresher() -> None:
    while True:
        await refresh_pro_cache()
        await asyncio.sleep(300)  # 5 minutes


async def run_monitor(bot: Bot, config: Config) -> None:
    # ensure redis connection is ready
    try:
        await get_redis()
    except Exception as e:
        logger.warning("Redis init failed: %s", e)

    pool = await get_pool()
    queue = SendQueue(bot, config.RATE_LIMIT_PER_SECOND)

    async def on_sent(count: int):
        await stats_increment_messages(pool, count)

    queue.start(on_sent)

    # initial pro cache and periodic refresh
    await refresh_pro_cache()
    asyncio.create_task(_pro_cache_refresher())

    await asyncio.gather(
        _tier_loop("pro", config.PRO_CHECK_INTERVAL, config, queue),
        _tier_loop("standard", config.STANDARD_CHECK_INTERVAL, config, queue),
        _tier_loop("free", config.FREE_CHECK_INTERVAL, config, queue),
    )
