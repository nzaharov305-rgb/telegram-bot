"""Middleware для проверки наличия действующей подписки у пользователя."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.dispatcher.event.bases import CancelHandler

from app.database.repositories import UserRepository


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Отфильтровывает апдейты от пользователей без активной подписки.

        Пропускаются только старт/хелп/платежи/пробный доступ, а также любые
        запросы от администраторов (если потребуется).
        """
        # only message and callback-query events are interesting
        if isinstance(event, Message):
            text = event.text or ""
            if text.startswith("/start") or text.startswith("/help") or text in (
                "💎 Подписка",
                "🎁 Пробный доступ",
            ):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            d = event.data or ""
            if d == "terms:accept" or d.startswith("sub:") or d.startswith("pay:"):
                return await handler(event, data)

        # database middleware should have injected user_repo
        user_repo: UserRepository | None = data.get("user_repo")
        if user_repo is None or not event.from_user:
            return await handler(event, data)

        user = await user_repo.get(event.from_user.id)
        if not user or not user_repo.is_subscription_active(user):
            msg = "Нет активной подписки. Перейдите в раздел 💎 Подписка."
            if isinstance(event, Message):
                await event.answer(msg)
            else:
                await event.message.answer(msg)
            raise CancelHandler()

        return await handler(event, data)
