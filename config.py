import os
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Config:
    # === Core ===
    BOT_TOKEN: str
    DATABASE_URL: str

    # === Redis ===
    REDIS_URL: str | None

    # === Admin ===
    ADMIN_IDS: Tuple[int, ...]

    # === AI ===
    OPENAI_API_KEY: str | None

    # === Pricing ===
    PRICE_STANDARD: int
    PRICE_PRO: int

    # === Trial ===
    TRIAL_HOURS: int

    # === Limits ===
    FREE_MAX_LISTINGS_PER_DAY: int

    # === Proxy (optional) ===
    PROXY_LIST: Tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise RuntimeError("BOT_TOKEN не найден в переменных окружения")

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL не найден (PostgreSQL)")

        # Admin IDs
        admin_raw = os.getenv("ADMIN_IDS", "")
        admin_ids = tuple(
            int(x.strip())
            for x in admin_raw.split(",")
            if x.strip().isdigit()
        )

        # Proxy list
        proxy_raw = os.getenv("PROXY_LIST", "")
        proxy_list = tuple(
            p.strip()
            for p in proxy_raw.split(",")
            if p.strip()
        )

        return cls(
            BOT_TOKEN=token,
            DATABASE_URL=database_url,
            REDIS_URL=os.getenv("REDIS_URL"),
            ADMIN_IDS=admin_ids,
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            PRICE_STANDARD=int(os.getenv("PRICE_STANDARD", "3900")),
            PRICE_PRO=int(os.getenv("PRICE_PRO", "7900")),
            TRIAL_HOURS=int(os.getenv("TRIAL_HOURS", "2")),
            FREE_MAX_LISTINGS_PER_DAY=int(
                os.getenv("FREE_MAX_LISTINGS_PER_DAY", "5")
            ),
            PROXY_LIST=proxy_list,
        )
