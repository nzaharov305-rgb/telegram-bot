"""Админ-панель."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.database.repositories import StatsRepository
from app.config import Config

router = Router()


@router.message(Command("admin"))
async def admin_panel(
    message: Message,
    config: Config,
    pool,
):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    stats_repo = StatsRepository(pool)
    stats = await stats_repo.get_admin_stats(pool)
    cfg = Config.from_env()

    text = (
        f"👑 Админ-панель\n\n"
        f"👥 Всего пользователей: {stats['users_total']}\n"
        f"🆓 FREE: {stats['free']}\n"
        f"📦 STANDARD: {stats['standard']}\n"
        f"💎 PRO: {stats['pro']}\n\n"
        f"✅ Активных подписок: {stats['active_subs']}\n"
        f"📈 Активных сегодня: {stats['active_today']}\n"
        f"📤 Сообщений отправлено: {stats['messages_sent']}\n\n"
        f"💰 Расчёт дохода:\n"
        f"   STANDARD × {cfg.PRICE_STANDARD} ₸ = {(stats['standard'] or 0) * cfg.PRICE_STANDARD} ₸\n"
        f"   PRO × {cfg.PRICE_PRO} ₸ = {(stats['pro'] or 0) * cfg.PRICE_PRO} ₸\n"
        f"   Итого: {stats['revenue']} ₸"
    )
    await message.answer(text)
