"""Production-ready конфигурация. Railway: TOKEN, DATABASE_URL."""
import os
import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

import redis.asyncio as aioredis

load_dotenv()

logger = logging.getLogger(__name__)

# global redis client singleton
_redis_client: Optional[aioredis.Redis] = None


@dataclass(frozen=True)
class Config:
    TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: tuple[int, ...]
    OPENAI_API_KEY: str | None = None

    PRICE_STANDARD: int = 4900
    PRICE_PRO: int = 9900
    TRIAL_HOURS: int = 2
    FREE_MAX_LISTINGS_PER_DAY: int = 5
    FREE_CHECK_INTERVAL: int = 600
    STANDARD_CHECK_INTERVAL: int = 120
    PRO_CHECK_INTERVAL: int = 30
    PARSER_RETRY_COUNT: int = 3
    PARSER_DELAY_MIN: float = 1.5
    PARSER_DELAY_MAX: float = 4.5
    PARSER_TIMEOUT: int = 15
    RATE_LIMIT_PER_SECOND: float = 1.0
    PROXY_LIST: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
        db_url = os.getenv("DATABASE_URL")
        openai_key = os.getenv("OPENAI_API_KEY")
        admin_ids = tuple(
            int(x.strip())
            for x in (os.getenv("ADMIN_IDS", "") or os.getenv("ADMIN_ID", "0")).split(",")
            if x.strip().isdigit()
        )
        if not token:
            raise RuntimeError("TOKEN не найден в переменных окружения")
        if not db_url:
            raise RuntimeError("DATABASE_URL не найден (PostgreSQL)")
        proxy_str = os.getenv("PROXY_LIST", "")
        proxy_list = tuple(p.strip() for p in proxy_str.split(",") if p.strip()) if proxy_str else ()
        return cls(
            TOKEN=token,
            DATABASE_URL=db_url,
            ADMIN_IDS=admin_ids or (0,),
            OPENAI_API_KEY=openai_key,
            PRICE_STANDARD=int(os.getenv("PRICE_STANDARD", "4900")),
            PRICE_PRO=int(os.getenv("PRICE_PRO", "9900")),
            TRIAL_HOURS=int(os.getenv("TRIAL_HOURS", "2")),
            FREE_MAX_LISTINGS_PER_DAY=int(os.getenv("FREE_MAX_LISTINGS_PER_DAY", "5")),
            PROXY_LIST=proxy_list,
        )


async def get_redis() -> aioredis.Redis:
    """Return a singleton Redis client. Retry on ping failures."""
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL")
        if not url:
            raise RuntimeError("REDIS_URL is not configured")
        _redis_client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    try:
        await _redis_client.ping()
    except Exception:
        logger.warning("Redis ping failed, recreating connection")
        url = os.getenv("REDIS_URL")
        _redis_client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    return _redis_client
