"""Старт, согласие с условиями, пробный доступ."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards import main_kb
from app.database.repositories import UserRepository, StatsRepository

router = Router()

TERMS_TEXT = (
    "Бот предоставляет автоматический мониторинг объявлений.\n"
    "Мы не являемся официальным представителем Krisha.kz.\n"
    "Продолжая использование, вы соглашаетесь с условиями."
)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user_repo: UserRepository,
    stats_repo: StatsRepository,
):
    user = message.from_user
    if not user:
        return

    u = await user_repo.get_or_create(user.id, user.username)
    if not u:
        return

    if not u.get("accepted_terms"):
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="✅ Согласен", callback_data="terms:accept"))
        await message.answer(TERMS_TEXT, reply_markup=kb.as_markup())
        return

    await message.answer("Выберите действие:", reply_markup=main_kb())


@router.callback_query(F.data == "terms:accept")
async def terms_accept(
    callback: CallbackQuery,
    user_repo: UserRepository,
    stats_repo: StatsRepository,
):
    await callback.answer()
    await user_repo.accept_terms(callback.from_user.id)
    await stats_repo.increment_new_users()
    await callback.message.edit_text("✅ Согласие получено.")
    await callback.message.answer("Выберите действие:", reply_markup=main_kb())


@router.message(F.text == "🎁 Пробный доступ")
async def trial_start(
    message: Message,
    user_repo: UserRepository,
):
    u = await user_repo.get(message.from_user.id)
    if not u or not u.get("accepted_terms"):
        await message.answer("Сначала нажмите /start и примите условия.")
        return

    if u.get("trial_used"):
        await message.answer(
            "Пробный период уже использован.\n"
            "Оформите подписку в разделе 💎 Подписка."
        )
        return

    await user_repo.start_trial(message.from_user.id)
    await message.answer(
        f"🎁 Пробный доступ на {user_repo._config.TRIAL_HOURS} часа активирован!\n"
        "Выберите режим и параметры поиска."
    )
