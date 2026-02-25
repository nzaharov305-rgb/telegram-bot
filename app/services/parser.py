"""Парсер Krisha.kz с защитой от блокировки."""
import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Sequence

import aiohttp
from bs4 import BeautifulSoup

from app.config import Config

logger = logging.getLogger(__name__)

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)


@dataclass
class Listing:
    id: str
    title: str
    price: str
    url: str
    from_owner: bool = False


class KrishaParser:
    def __init__(self, config: Config):
        self._config = config
        self._proxy_index = 0

    def _get_proxy(self) -> str | None:
        if not self._config.PROXY_LIST:
            return None
        proxy = self._config.PROXY_LIST[self._proxy_index % len(self._config.PROXY_LIST)]
        self._proxy_index += 1
        return proxy

    def _get_headers(self) -> dict:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }

    def _random_delay(self) -> float:
        return random.uniform(
            self._config.PARSER_DELAY_MIN,
            self._config.PARSER_DELAY_MAX,
        )

    def _build_url(
        self,
        mode: str,
        rooms: int,
        district: str,
        from_owner: bool = False,
    ) -> str:
        if mode == "rent":
            base = f"https://krisha.kz/arenda/kvartiry/almaty-{district}/"
        else:
            base = f"https://krisha.kz/prodazha/kvartiry/almaty-{district}/"
        url = f"{base}?das[who]=1&das[live.rooms]={rooms}"
        if from_owner:
            url += "&das[who]=1"  # от хозяина
        return url

    async def parse(
        self,
        mode: str,
        rooms: int,
        district: str,
        from_owner: bool = False,
    ) -> list[Listing]:
        url = self._build_url(mode, rooms, district, from_owner)
        last_error = None

        for attempt in range(self._config.PARSER_RETRY_COUNT):
            try:
                await asyncio.sleep(self._random_delay())
                proxy = self._get_proxy()
                timeout = aiohttp.ClientTimeout(total=self._config.PARSER_TIMEOUT)

                async with aiohttp.ClientSession(
                    headers=self._get_headers(),
                    timeout=timeout,
                ) as session:
                    async with session.get(url, proxy=proxy) as resp:
                        if resp.status != 200:
                            raise aiohttp.ClientError(f"HTTP {resp.status}")
                        html = await resp.text()

                soup = BeautifulSoup(html, "lxml")
                cards = soup.select("div.a-card")
                results = []

                for card in cards:
                    title_el = card.select_one("a.a-card__title")
                    price_el = card.select_one("div.a-card__price")
                    if not title_el or not price_el:
                        continue

                    href = title_el.get("href", "")
                    listing_id = href.split("/")[-1].split("-")[0] or href
                    if not listing_id or not listing_id.isdigit():
                        listing_id = href

                    link = "https://krisha.kz" + href
                    from_owner_flag = "от хозяина" in card.text.lower() or "собственник" in card.text.lower()

                    results.append(
                        Listing(
                            id=str(listing_id),
                            title=title_el.text.strip(),
                            price=price_el.text.strip(),
                            url=link,
                            from_owner=from_owner_flag,
                        )
                    )

                return results

            except Exception as e:
                last_error = e
                logger.warning(f"Parse attempt {attempt + 1} failed: {e}")
                if attempt < self._config.PARSER_RETRY_COUNT - 1:
                    await asyncio.sleep(self._random_delay() * 2)

        logger.error(f"Parse failed after {self._config.PARSER_RETRY_COUNT} attempts: {last_error}")
        return []
