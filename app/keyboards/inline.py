"""Инлайн-клавиатуры бота."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Аренда", callback_data="menu:rent"),
        InlineKeyboardButton(text="🏡 Продажа", callback_data="menu:sale"),
    )
    builder.row(
        InlineKeyboardButton(text="🏢 ЖК (Комплексы)", callback_data="menu:rc"),
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu:notifications"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Подписка", callback_data="menu:subscription"),
    )
    return builder.as_markup()


def rent_sale_kb() -> InlineKeyboardMarkup:
    """Меню аренда/продажа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Аренда", callback_data="list:rent"),
        InlineKeyboardButton(text="🏡 Продажа", callback_data="list:sale"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"),
    )
    return builder.as_markup()


def notifications_kb(rent: bool, sale: bool, notifications: bool) -> InlineKeyboardMarkup:
    """Настройки уведомлений."""
    builder = InlineKeyboardBuilder()
    rent_text = "🏠 Аренда: ВКЛ" if rent else "🏠 Аренда: ВЫКЛ"
    sale_text = "🏡 Продажа: ВКЛ" if sale else "🏡 Продажа: ВЫКЛ"
    notif_text = "🔔 Уведомления: ВКЛ" if notifications else "🔔 Уведомления: ВЫКЛ"
    builder.row(
        InlineKeyboardButton(text=rent_text, callback_data="notif:toggle_rent"),
        InlineKeyboardButton(text=sale_text, callback_data="notif:toggle_sale"),
    )
    builder.row(
        InlineKeyboardButton(text=notif_text, callback_data="notif:toggle_all"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"),
    )
    return builder.as_markup()


def subscription_kb(has_active: bool, is_trial: bool) -> InlineKeyboardMarkup:
    """Меню подписки."""
    builder = InlineKeyboardBuilder()
    if has_active:
        if is_trial:
            builder.row(
                InlineKeyboardButton(text="💎 Оформить подписку", callback_data="sub:buy"),
            )
    else:
        builder.row(
            InlineKeyboardButton(text="⏳ Начать trial (2 ч)", callback_data="sub:trial"),
        )
        builder.row(
            InlineKeyboardButton(text="💎 Оформить подписку", callback_data="sub:buy"),
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"),
    )
    return builder.as_markup()
