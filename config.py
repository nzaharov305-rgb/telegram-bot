"""Production-ready конфигурация. Railway: TOKEN, DATABASE_URL."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: tuple[int, ...]

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
            PRICE_STANDARD=int(os.getenv("PRICE_STANDARD", "4900")),
            PRICE_PRO=int(os.getenv("PRICE_PRO", "9900")),
            TRIAL_HOURS=int(os.getenv("TRIAL_HOURS", "2")),
            FREE_MAX_LISTINGS_PER_DAY=int(os.getenv("FREE_MAX_LISTINGS_PER_DAY", "5")),
            PROXY_LIST=proxy_list,
        )
