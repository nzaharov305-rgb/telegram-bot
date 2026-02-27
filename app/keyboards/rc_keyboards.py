"""Residential Complex keyboards."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def rc_category_kb() -> InlineKeyboardMarkup:
    """Category selection keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Premium", callback_data="rc_cat_premium"),
    )
    builder.row(
        InlineKeyboardButton(text="🏢 Business", callback_data="rc_cat_business"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Comfort", callback_data="rc_cat_comfort"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Очистить фильтр", callback_data="rc_cat_all"),
    )
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="menu:back"),
    )
    return builder.as_markup()


def rc_list_kb(
    complexes: list[dict],
    selected_ids: list[int],
    subscription_type: str,
) -> InlineKeyboardMarkup:
    """Residential complex list with 2 buttons per row."""
    builder = InlineKeyboardBuilder()
    
    for rc in complexes:
        rc_id = rc["id"]
        name = rc["name"]
        
        # Add checkmark if selected
        if rc_id in selected_ids:
            text = f"✔ {name}"
        else:
            text = name
        
        builder.add(
            InlineKeyboardButton(
                text=text,
                callback_data=f"rc_select_{rc_id}",
            )
        )
    
    # Arrange in rows of 2
    builder.adjust(2)
    
    # Add save and back buttons
    builder.row(
        InlineKeyboardButton(text="💾 Сохранить", callback_data="rc_save"),
    )
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="rc_back_cat"),
    )
    
    return builder.as_markup()


def rc_upgrade_kb(plan: str) -> InlineKeyboardMarkup:
    """Upgrade message keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"💎 Перейти на {plan.upper()}",
            callback_data=f"sub:upgrade_{plan}",
        ),
    )
    builder.row(
        InlineKeyboardButton(text="↩ Назад", callback_data="menu:back"),
    )
    return builder.as_markup()
