import os
from dataclasses import dataclass
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    TOKEN: str
    DATABASE_URL: str

    ADMIN_IDS: Tuple[int, ...] = ()

    PRICE_STANDARD: int = 3900
    PRICE_PRO: int = 9900
    TRIAL_HOURS: int = 2
    FREE_MAX_LISTINGS_PER_DAY: int = 3

    FREE_CHECK_INTERVAL: int = 60
    STANDARD_CHECK_INTERVAL: int = 30
    PRO_CHECK_INTERVAL: int = 15

    PARSER_RETRY_COUNT: int = 5
    PARSER_RETRY_DELAY: int = 3

    PARSER_DELAY_MIN: float = 2.0
    PARSER_DELAY_MAX: float = 5.0
    PARSER_TIMEOUT: int = 15

    RATE_LIMIT_PER_SECOND: float = 3.0
    PROXY_LIST: Tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
        database_url = os.getenv("DATABASE_URL")

        if not token:
            raise RuntimeError("TOKEN не найден")

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
            TOKEN=token,
            DATABASE_URL=database_url,
            ADMIN_IDS=admin_ids,
            PRICE_STANDARD=int(os.getenv("PRICE_STANDARD", "3900")),
            PRICE_PRO=int(os.getenv("PRICE_PRO", "9900")),
            TRIAL_HOURS=int(os.getenv("TRIAL_HOURS", "2")),
            FREE_MAX_LISTINGS_PER_DAY=int(
                os.getenv("FREE_MAX_LISTINGS_PER_DAY", "3")
            ),
            FREE_CHECK_INTERVAL=int(os.getenv("FREE_CHECK_INTERVAL", "60")),
            STANDARD_CHECK_INTERVAL=int(os.getenv("STANDARD_CHECK_INTERVAL", "30")),
            PRO_CHECK_INTERVAL=int(os.getenv("PRO_CHECK_INTERVAL", "15")),
            PARSER_RETRY_COUNT=int(os.getenv("PARSER_RETRY_COUNT", "5")),
            PARSER_RETRY_DELAY=int(os.getenv("PARSER_RETRY_DELAY", "3")),
            PARSER_DELAY_MIN=float(os.getenv("PARSER_DELAY_MIN", "2.0")),
            PARSER_DELAY_MAX=float(os.getenv("PARSER_DELAY_MAX", "5.0")),
            PARSER_TIMEOUT=int(os.getenv("PARSER_TIMEOUT", "15")),
            RATE_LIMIT_PER_SECOND=float(os.getenv("RATE_LIMIT_PER_SECOND", "3.0")),
            PROXY_LIST=proxy_list,
        )

    def masked_summary(self) -> dict:
        token = self.TOKEN or ""
        masked_token = token[:6] + "..." + token[-4:] if len(token) > 10 else "***"
        
        return {
            "TOKEN": masked_token,
            "DATABASE_URL": "***",
            "ADMIN_IDS": self.ADMIN_IDS,
            "PRICE_STANDARD": self.PRICE_STANDARD,
            "PRICE_PRO": self.PRICE_PRO,
            "TRIAL_HOURS": self.TRIAL_HOURS,
            "FREE_MAX_LISTINGS_PER_DAY": self.FREE_MAX_LISTINGS_PER_DAY,
            "FREE_CHECK_INTERVAL": self.FREE_CHECK_INTERVAL,
            "STANDARD_CHECK_INTERVAL": self.STANDARD_CHECK_INTERVAL,
            "PRO_CHECK_INTERVAL": self.PRO_CHECK_INTERVAL,
            "PARSER_RETRY_COUNT": self.PARSER_RETRY_COUNT,
            "PARSER_RETRY_DELAY": self.PARSER_RETRY_DELAY,
            "PARSER_DELAY_MIN": self.PARSER_DELAY_MIN,
            "PARSER_DELAY_MAX": self.PARSER_DELAY_MAX,
            "PARSER_TIMEOUT": self.PARSER_TIMEOUT,
            "RATE_LIMIT_PER_SECOND": self.RATE_LIMIT_PER_SECOND,
            "PROXY_LIST": f"{len(self.PROXY_LIST)} proxies" if self.PROXY_LIST else "none",
        }

    def fingerprint(self) -> str:
        import hashlib
        parts = [
            f"PRICE_STANDARD={self.PRICE_STANDARD}",
            f"PRICE_PRO={self.PRICE_PRO}",
            f"TRIAL_HOURS={self.TRIAL_HOURS}",
            f"FREE_CHECK_INTERVAL={self.FREE_CHECK_INTERVAL}",
            f"STANDARD_CHECK_INTERVAL={self.STANDARD_CHECK_INTERVAL}",
            f"PRO_CHECK_INTERVAL={self.PRO_CHECK_INTERVAL}",
        ]
        payload = "|".join(parts)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def load_config() -> Config:
    return Config.from_env()
