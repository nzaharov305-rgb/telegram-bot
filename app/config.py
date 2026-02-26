import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: tuple[int, ...]

    PRICE_STANDARD: int
    PRICE_PRO: int
    TRIAL_HOURS: int
    FREE_MAX_LISTINGS_PER_DAY: int

    PARSER_DELAY_MAX: float = 4.5
    PARSER_TIMEOUT: int = 15

    RATE_LIMIT_PER_SECOND: float = 1.0
    PROXY_LIST: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Config":
        bot_token = os.getenv("BOT_TOKEN")
        database_url = os.getenv("DATABASE_URL")

        if not bot_token:
            raise RuntimeError("BOT_TOKEN не найден")

        if not database_url:
            raise RuntimeError("DATABASE_URL не найден (PostgreSQL)")

        admin_ids = tuple(
            int(x.strip())
            for x in os.getenv("ADMIN_IDS", "").split(",")
            if x.strip().isdigit()
        )

        proxy_str = os.getenv("PROXY_LIST", "")
        proxy_list = tuple(
            p.strip() for p in proxy_str.split(",") if p.strip()
        )

        return cls(
            BOT_TOKEN=bot_token,
            DATABASE_URL=database_url,
            ADMIN_IDS=admin_ids or (0,),
            PRICE_STANDARD=int(os.getenv("PRICE_STANDARD", "4900")),
            PRICE_PRO=int(os.getenv("PRICE_PRO", "9900")),
            TRIAL_HOURS=int(os.getenv("TRIAL_HOURS", "2")),
            FREE_MAX_LISTINGS_PER_DAY=int(
                os.getenv("FREE_MAX_LISTINGS_PER_DAY", "5")
            ),
            PROXY_LIST=proxy_list,
        )
