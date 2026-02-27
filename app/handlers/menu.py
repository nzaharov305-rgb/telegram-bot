"""Роутинг главного меню по callback."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime

from app.database.repositories import UserRepository
from app.keyboards import rent_sale_kb, notifications_kb, subscription_kb
from app.keyboards.rc_keyboards import rc_category_kb

router = Router()


@router.callback_query(F.data == "menu:rent")
async def menu_rent(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Переход к аренде."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    has_active = user and user_repo.is_subscription_active(user)
    if not has_active:
        await callback.message.edit_text(
            "⏳ Для доступа к объявлениям нужна активная подписка.\n"
            "Перейдите в раздел «💎 Подписка».",
            reply_markup=rent_sale_kb(),
        )
        return
    await callback.message.edit_text(
        "🏠 Аренда — выберите действие:",
        reply_markup=rent_sale_kb(),
    )


@router.callback_query(F.data == "menu:sale")
async def menu_sale(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Переход к продаже."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    has_active = user and user_repo.is_subscription_active(user)
    if not has_active:
        await callback.message.edit_text(
            "⏳ Для доступа к объявлениям нужна активная подписка.\n"
            "Перейдите в раздел «💎 Подписка».",
            reply_markup=rent_sale_kb(),
        )
        return
    await callback.message.edit_text(
        "🏡 Продажа — выберите действие:",
        reply_markup=rent_sale_kb(),
    )


@router.callback_query(F.data == "menu:notifications")
async def menu_notifications(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Настройки уведомлений."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    if not user:
        return
    await callback.message.edit_text(
        "🔔 Настройки уведомлений:",
        reply_markup=notifications_kb(
            rent=user.rent_enabled,
            sale=user.sale_enabled,
            notifications=user.notifications_enabled,
        ),
    )


@router.callback_query(F.data == "menu:subscription")
async def menu_subscription(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Меню подписки."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    has_active = user and user_repo.is_subscription_active(user)
    is_trial = False
    if user:
        is_trial = (
            user.get("subscription_type") == "free"
            and user.get("trial_until")
            and user["trial_until"] > datetime.utcnow()
        )

    if has_active:
        exp = " до " + user.get("subscription_until").strftime("%d.%m.%Y %H:%M") if user.get("subscription_until") else ""
        text = f"💎 Подписка активна{exp}\n\nПлан: {user.get('subscription_type')}"
    else:
        text = (
            "💎 Подписка\n\n"
            "⏳ Trial — 2 часа бесплатно\n"
            "💎 Платная подписка — 299 ₽/мес"
        )

    await callback.message.edit_text(
        text,
        reply_markup=subscription_kb(has_active=has_active, is_trial=is_trial),
    )


@router.callback_query(F.data == "menu:rc")
async def menu_rc(callback: CallbackQuery):
    """Show residential complex categories."""
    await callback.message.edit_text(
        "🏢 Жилые комплексы\n\nВыберите категорию:",
        reply_markup=rc_category_kb(),
    )
    await callback.answer()
