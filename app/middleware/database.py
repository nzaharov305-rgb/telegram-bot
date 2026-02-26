"""Middleware для доступа к БД."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import Config
from app.database.connection import get_pool
from app.database.repositories import (
    UserRepository,
    SentListingsRepository,
    StatsRepository,
)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, config: Config):
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        pool = await get_pool(self.config.DATABASE_URL)
        data["pool"] = pool
        data["user_repo"] = UserRepository(pool, self.config)
        data["sent_repo"] = SentListingsRepository(pool)
        data["stats_repo"] = StatsRepository(pool)
        data["config"] = self.config
        return await handler(event, data)
