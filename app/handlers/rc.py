"""Residential Complex handlers."""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.database.connection import get_pool
from app.database.repositories import UserRepository
from app.database.rc_repository import (
    get_active_complexes,
    get_user_selected_complexes,
    add_user_complex,
    remove_user_complex,
    clear_user_complexes,
    set_standard_complex,
    get_standard_complex,
    count_user_complexes,
)
from app.keyboards.rc_keyboards import (
    rc_category_kb,
    rc_list_kb,
    rc_upgrade_kb,
)
from app.config import Config

logger = logging.getLogger(__name__)
router = Router()

# Temporary storage for category filter
_user_category_filter: dict[int, str | None] = {}


@router.callback_query(F.data == "menu:rc")
async def show_rc_categories(callback: CallbackQuery):
    """Show residential complex category selection."""
    await callback.message.edit_text(
        "Выберите категорию ЖК:",
        reply_markup=rc_category_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rc_cat_"))
async def select_category(callback: CallbackQuery):
    """Handle category selection and show complexes."""
    category = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    
    if category == "all":
        category = None
    
    _user_category_filter[user_id] = category
    
    pool = await get_pool(Config.from_env().DATABASE_URL)
    config = Config.from_env()
    
    # Get user data
    user_repo = UserRepository(pool, config)
    user = await user_repo.get(user_id)
    
    if not user:
        await callback.answer("Ошибка получения данных пользователя", show_alert=True)
        return
    
    subscription_type = user.get("subscription_type", "free")
    
    # FREE users cannot select ЖК
    if subscription_type == "free":
        await callback.message.edit_text(
            "❌ Выбор ЖК доступен только для STANDARD и PRO подписок.\n\n"
            "📊 STANDARD: 1 ЖК\n"
            "⭐ PRO: до 5 ЖК + AI анализ\n\n"
            "Обновите подписку для доступа к этой функции.",
            reply_markup=rc_upgrade_kb("standard"),
        )
        await callback.answer()
        return
    
    # Get complexes
    complexes = await get_active_complexes(pool, category)
    
    if not complexes:
        await callback.answer("В этой категории нет доступных ЖК", show_alert=True)
        return
    
    # Get user's selected complexes
    if subscription_type == "pro":
        selected_ids = await get_user_selected_complexes(pool, user_id)
    elif subscription_type == "standard":
        standard_complex = await get_standard_complex(pool, user_id)
        if standard_complex:
            # Find ID by name
            selected_ids = [
                rc["id"] for rc in complexes if rc["name"] == standard_complex
            ]
        else:
            selected_ids = []
    else:
        selected_ids = []
    
    category_text = {
        "premium": "🏆 Premium",
        "business": "🏢 Business",
        "comfort": "🏠 Comfort",
        None: "Все категории",
    }.get(category, "Все категории")
    
    limits_text = {
        "standard": "Выбрано: {}/1",
        "pro": "Выбрано: {}/5",
    }.get(subscription_type, "")
    
    await callback.message.edit_text(
        f"Категория: {category_text}\n"
        f"{limits_text.format(len(selected_ids))}\n\n"
        "Выберите ЖК (нажмите для выбора/отмены):",
        reply_markup=rc_list_kb(complexes, selected_ids, subscription_type),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rc_select_"))
async def toggle_complex(callback: CallbackQuery):
    """Toggle residential complex selection."""
    complex_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    pool = await get_pool(Config.from_env().DATABASE_URL)
    config = Config.from_env()
    
    user_repo = UserRepository(pool, config)
    user = await user_repo.get(user_id)
    
    if not user:
        await callback.answer("Ошибка получения данных", show_alert=True)
        return
    
    subscription_type = user.get("subscription_type", "free")
    
    if subscription_type == "free":
        await callback.answer(
            "❌ Выбор ЖК доступен только для платных подписок",
            show_alert=True,
        )
        return
    
    category = _user_category_filter.get(user_id)
    complexes = await get_active_complexes(pool, category)
    
    # Get complex name
    selected_complex = next((rc for rc in complexes if rc["id"] == complex_id), None)
    if not selected_complex:
        await callback.answer("ЖК не найден", show_alert=True)
        return
    
    if subscription_type == "standard":
        # STANDARD: single selection
        current = await get_standard_complex(pool, user_id)
        
        if current == selected_complex["name"]:
            # Deselect
            await set_standard_complex(pool, user_id, None)
            selected_ids = []
        else:
            # Select new (replaces old)
            await set_standard_complex(pool, user_id, selected_complex["name"])
            selected_ids = [complex_id]
        
    elif subscription_type == "pro":
        # PRO: multi-selection (up to 5)
        selected_ids = await get_user_selected_complexes(pool, user_id)
        
        if complex_id in selected_ids:
            # Deselect
            await remove_user_complex(pool, user_id, complex_id)
            selected_ids.remove(complex_id)
        else:
            # Check limit
            if len(selected_ids) >= 5:
                await callback.answer(
                    "❌ Достигнут лимит: 5 ЖК для PRO подписки",
                    show_alert=True,
                )
                return
            # Select
            await add_user_complex(pool, user_id, complex_id)
            selected_ids.append(complex_id)
    
    else:
        selected_ids = []
    
    # Refresh keyboard
    category_text = {
        "premium": "🏆 Premium",
        "business": "🏢 Business",
        "comfort": "🏠 Comfort",
        None: "Все категории",
    }.get(category, "Все категории")
    
    limits_text = {
        "standard": "Выбрано: {}/1",
        "pro": "Выбрано: {}/5",
    }.get(subscription_type, "")
    
    await callback.message.edit_text(
        f"Категория: {category_text}\n"
        f"{limits_text.format(len(selected_ids))}\n\n"
        "Выберите ЖК (нажмите для выбора/отмены):",
        reply_markup=rc_list_kb(complexes, selected_ids, subscription_type),
    )
    await callback.answer("✅")


@router.callback_query(F.data == "rc_save")
async def save_selection(callback: CallbackQuery):
    """Save residential complex selection."""
    user_id = callback.from_user.id
    
    pool = await get_pool(Config.from_env().DATABASE_URL)
    config = Config.from_env()
    
    user_repo = UserRepository(pool, config)
    user = await user_repo.get(user_id)
    
    if not user:
        await callback.answer("Ошибка", show_alert=True)
        return
    
    subscription_type = user.get("subscription_type", "free")
    
    if subscription_type == "standard":
        selected = await get_standard_complex(pool, user_id)
        if selected:
            await callback.message.edit_text(
                f"✅ Сохранено!\n\n"
                f"Выбранный ЖК: {selected}\n\n"
                f"Теперь вы будете получать уведомления только по объявлениям из этого ЖК.",
            )
        else:
            await callback.message.edit_text(
                "ℹ️ Вы не выбрали ни одного ЖК.\n"
                "Вы будете получать все объявления по вашим фильтрам.",
            )
    elif subscription_type == "pro":
        count = await count_user_complexes(pool, user_id)
        if count > 0:
            await callback.message.edit_text(
                f"✅ Сохранено!\n\n"
                f"Выбрано ЖК: {count}/5\n\n"
                f"Теперь вы будете получать уведомления + AI анализ только по объявлениям из выбранных ЖК.",
            )
        else:
            await callback.message.edit_text(
                "ℹ️ Вы не выбрали ни одного ЖК.\n"
                "Вы будете получать все объявления по вашим фильтрам.",
            )
    
    await callback.answer()


@router.callback_query(F.data == "rc_back_cat")
async def back_to_categories(callback: CallbackQuery):
    """Return to category selection."""
    await callback.message.edit_text(
        "Выберите категорию ЖК:",
        reply_markup=rc_category_kb(),
    )
    await callback.answer()
