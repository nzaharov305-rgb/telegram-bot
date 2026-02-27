"""Admin panel keyboards."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_main_kb() -> InlineKeyboardMarkup:
    """Main admin menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users"),
    )
    builder.row(
        InlineKeyboardButton(text="🏢 ЖК управление", callback_data="admin:rc"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Подписки", callback_data="admin:subscriptions"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙ Система", callback_data="admin:system"),
    )
    return builder.as_markup()


def admin_broadcast_kb() -> InlineKeyboardMarkup:
    """Broadcast menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📢 Всем", callback_data="admin_bc:all"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 PRO", callback_data="admin_bc:pro"),
    )
    builder.row(
        InlineKeyboardButton(text="📦 STANDARD", callback_data="admin_bc:standard"),
    )
    builder.row(
        InlineKeyboardButton(text="🆓 FREE", callback_data="admin_bc:free"),
    )
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="admin:back"),
    )
    return builder.as_markup()


def admin_rc_kb() -> InlineKeyboardMarkup:
    """RC management menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить ЖК", callback_data="admin_rc:add"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Список ЖК", callback_data="admin_rc:list"),
    )
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="admin:back"),
    )
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    """Simple back button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="admin:back"),
    )
    return builder.as_markup()


def admin_rc_item_kb(rc_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """RC item actions."""
    builder = InlineKeyboardBuilder()
    
    status_text = "🔴 Отключить" if is_active else "🟢 Включить"
    builder.row(
        InlineKeyboardButton(
            text=status_text,
            callback_data=f"admin_rc_toggle:{rc_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="⬆ Priority +1",
            callback_data=f"admin_rc_priority_up:{rc_id}",
        ),
        InlineKeyboardButton(
            text="⬇ Priority -1",
            callback_data=f"admin_rc_priority_down:{rc_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="admin_rc:list"),
    )
    return builder.as_markup()
