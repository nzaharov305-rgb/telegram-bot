"""Статистика пользователя."""
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from app.database.repositories import UserRepository, SentListingsRepository, StatsRepository

router = Router()


@router.message(F.text == "📊 Статистика")
async def user_stats(
    message: Message,
    user_repo: UserRepository,
    sent_repo: SentListingsRepository,
    stats_repo: StatsRepository,
):
    u = await user_repo.get(message.from_user.id)
    if not u:
        await message.answer("Нажмите /start")
        return

    sub_type = u.get("subscription_type") or "free"
    until = u.get("subscription_until") or u.get("trial_until")
    until_str = until.strftime("%d.%m.%Y") if until else "—"

    sent_today = await sent_repo.count_sent_today(message.from_user.id)
    user_stats = await stats_repo.get_user_stats(message.from_user.id)
    global_stats = await stats_repo.get_global_stats()

    text = (
        f"📊 Статистика\n\n"
        f"👤 Ваш тариф: {sub_type.upper()}\n"
        f"📅 Окончание: {until_str}\n"
        f"📨 Получено сегодня: {sent_today}\n"
        f"📨 Всего получено: {user_stats['total_sent']}\n\n"
        f"--- Общая ---\n"
        f"👥 Пользователей: {global_stats['users_total']}\n"
        f"💎 Активных подписок: {global_stats['active_subs']}\n"
        f"🆕 Новых сегодня: {global_stats['new_today']}\n"
        f"📤 Отправлено объявлений: {global_stats['messages_sent']}"
    )
    await message.answer(text)
