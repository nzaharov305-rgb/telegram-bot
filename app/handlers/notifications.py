"""Обработчики уведомлений."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.database.repositories import UserRepository
from app.keyboards import notifications_kb

router = Router()


@router.callback_query(F.data == "notif:toggle_rent")
async def toggle_rent(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Вкл/выкл уведомления по аренде."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    if not user:
        return
    new_val = not user.rent_enabled
    await user_repo.set_rent_enabled(callback.from_user.id, new_val)
    user = await user_repo.get(callback.from_user.id)
    await callback.message.edit_reply_markup(
        reply_markup=notifications_kb(
            rent=user.rent_enabled,
            sale=user.sale_enabled,
            notifications=user.notifications_enabled,
        ),
    )


@router.callback_query(F.data == "notif:toggle_sale")
async def toggle_sale(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Вкл/выкл уведомления по продаже."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    if not user:
        return
    new_val = not user.sale_enabled
    await user_repo.set_sale_enabled(callback.from_user.id, new_val)
    user = await user_repo.get(callback.from_user.id)
    await callback.message.edit_reply_markup(
        reply_markup=notifications_kb(
            rent=user.rent_enabled,
            sale=user.sale_enabled,
            notifications=user.notifications_enabled,
        ),
    )


@router.callback_query(F.data == "notif:toggle_all")
async def toggle_all(
    callback: CallbackQuery,
    user_repo: UserRepository,
):
    """Вкл/выкл все уведомления."""
    await callback.answer()
    user = await user_repo.get(callback.from_user.id)
    if not user:
        return
    new_val = not user.notifications_enabled
    await user_repo.set_notifications(callback.from_user.id, new_val)
    user = await user_repo.get(callback.from_user.id)
    await callback.message.edit_reply_markup(
        reply_markup=notifications_kb(
            rent=user.rent_enabled,
            sale=user.sale_enabled,
            notifications=user.notifications_enabled,
        ),
    )
