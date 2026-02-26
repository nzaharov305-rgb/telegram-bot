"""Монитор парсинга с error isolation и production оптимизациями."""
import asyncio
import logging
from datetime import datetime

from app.config import Config
from app.database.connection import get_pool
from app.database.repositories import (
    UserRepository,
    SentListingsRepository,
    StatsRepository,
)
from app.services.parser import KrishaParser
from app.services.queue import SendQueue

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


async def _process_user_listings(
    user: dict,
    listings: list,
    sent_repo: SentListingsRepository,
    queue: SendQueue,
    config: Config,
) -> int:
    count = 0
    for listing in listings:
        if user.get("from_owner") and not listing.from_owner:
            continue

        if await sent_repo.was_sent(user["user_id"], listing.id):
            continue

        if user.get("subscription_type") == "free":
            sent_today = await sent_repo.count_sent_today(user["user_id"])
            if sent_today >= config.FREE_MAX_LISTINGS_PER_DAY:
                continue

        text = f"🏠 {listing.title}\n💰 {listing.price}\n🔗 {listing.url}"
        is_pro = user.get("subscription_type") == "pro"
        await queue.put(user["user_id"], text, is_pro=is_pro)
        await sent_repo.mark_sent(user["user_id"], listing.id)
        count += 1
    return count


async def _run_tier(
    users: list[dict],
    parser: KrishaParser,
    sent_repo: SentListingsRepository,
    queue: SendQueue,
    config: Config,
) -> None:
    for user in users:
        try:
            district = user.get("district")
            districts = user.get("districts") or []
            if district:
                districts = [district] if district not in districts else districts
            if not districts:
                continue

            mode = user.get("mode") or "rent"
            rooms = user.get("rooms") or 1
            from_owner = user.get("from_owner") or False

            for d in districts:
                district_slug = DISTRICT_MAP.get(d, d.lower().replace(" ", ""))
                listings = await parser.parse(mode, rooms, district_slug, from_owner)
                await _process_user_listings(
                    user, listings, sent_repo, queue, config
                )
        except Exception as e:
            logger.exception(f"Monitor error for user {user.get('user_id')}: {e}")


async def _tier_loop(
    tier: str,
    interval: int,
    user_repo: UserRepository,
    sent_repo: SentListingsRepository,
    parser: KrishaParser,
    queue: SendQueue,
    config: Config,
) -> None:
    while True:
        try:
            if tier == "free":
                users = await user_repo.get_active_free_users()
            else:
                users = await user_repo.get_active_users_by_tier(tier)
            if users:
                await _run_tier(users, parser, sent_repo, queue, config)
        except Exception as e:
            logger.exception(f"Monitor {tier} error: {e}")
        await asyncio.sleep(interval)


async def run_monitor(bot, config: Config) -> None:
    from app.database.repositories import StatsRepository

    queue = SendQueue(bot, config.RATE_LIMIT_PER_SECOND)
    pool = await get_pool(config.DATABASE_URL)
    stats_repo = StatsRepository(pool)
    user_repo = UserRepository(pool, config)
    sent_repo = SentListingsRepository(pool)
    parser = KrishaParser(config)

    async def stats_cb(count: int):
        await stats_repo.increment_messages_sent(count)

    queue.start(stats_callback=stats_cb)

    await asyncio.gather(
        _tier_loop("pro", config.PRO_CHECK_INTERVAL, user_repo, sent_repo, parser, queue, config),
        _tier_loop("standard", config.STANDARD_CHECK_INTERVAL, user_repo, sent_repo, parser, queue, config),
        _tier_loop("free", config.FREE_CHECK_INTERVAL, user_repo, sent_repo, parser, queue, config),
    )
