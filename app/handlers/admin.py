"""Advanced admin panel with full management capabilities."""
import asyncio
import logging
import psutil
from functools import wraps
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.repositories import StatsRepository, UserRepository
from app.database.connection import get_pool
from app.config import Config
from app.keyboards.admin_keyboards import (
    admin_main_kb,
    admin_broadcast_kb,
    admin_rc_kb,
    admin_back_kb,
    admin_rc_item_kb,
)

logger = logging.getLogger(__name__)
router = Router()


class BroadcastStates(StatesGroup):
    waiting_message = State()


class RCStates(StatesGroup):
    waiting_name = State()
    waiting_category = State()
    waiting_priority = State()


def admin_only(func):
    """Decorator to restrict access to admins only."""
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        config = Config.from_env()
        user_id = event.from_user.id if hasattr(event, 'from_user') else None
        
        if not user_id or user_id not in config.ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer("❌ Доступ запрещен")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        return await func(event, *args, **kwargs)
    return wrapper


@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message):
    """Main admin panel entry point."""
    text = (
        "👑 Админ-панель\n\n"
        "Выберите раздел для управления:"
    )
    await message.answer(text, reply_markup=admin_main_kb())


@router.callback_query(F.data == "admin:back")
@admin_only
async def admin_back(callback: CallbackQuery):
    """Return to main admin menu."""
    text = (
        "👑 Админ-панель\n\n"
        "Выберите раздел для управления:"
    )
    await callback.message.edit_text(text, reply_markup=admin_main_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
@admin_only
async def admin_stats(callback: CallbackQuery):
    """Show detailed statistics."""
    try:
        config = Config.from_env()
        pool = await get_pool(config.DATABASE_URL)
        
        # Basic stats
        users_total = await pool.fetchval("SELECT COUNT(*) FROM users") or 0
        free = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE subscription_type = 'free'"
        ) or 0
        standard = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE subscription_type = 'standard'"
        ) or 0
        pro = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE subscription_type = 'pro'"
        ) or 0
        active_subs = await pool.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE subscription_type IN ('standard', 'pro') 
            AND subscription_until > NOW()
            """
        ) or 0
        
        # RC stats
        total_rc_selections = await pool.fetchval(
            "SELECT COUNT(*) FROM user_residential_complexes"
        ) or 0
        
        # Top 5 complexes
        top_complexes = await pool.fetch(
            """
            SELECT rc.name, COUNT(urc.user_id) as cnt
            FROM user_residential_complexes urc
            JOIN residential_complexes rc ON rc.id = urc.complex_id
            GROUP BY rc.name
            ORDER BY cnt DESC
            LIMIT 5
            """
        )
        
        # Messages sent
        msg_sent = await pool.fetchval(
            "SELECT COALESCE(SUM(messages_sent), 0) FROM stats"
        ) or 0
        
        # Revenue calculation
        revenue = standard * config.PRICE_STANDARD + pro * config.PRICE_PRO
        
        top_rc_text = "\n".join(
            f"   {i+1}. {row['name']}: {row['cnt']}"
            for i, row in enumerate(top_complexes)
        ) if top_complexes else "   -"
        
        text = (
            f"📊 Статистика\n\n"
            f"👥 Всего пользователей: {users_total}\n"
            f"🆓 FREE: {free}\n"
            f"📦 STANDARD: {standard}\n"
            f"💎 PRO: {pro}\n\n"
            f"✅ Активных подписок: {active_subs}\n"
            f"📤 Сообщений отправлено: {msg_sent}\n\n"
            f"🏢 ЖК:\n"
            f"   Всего выборов: {total_rc_selections}\n"
            f"   Топ 5:\n{top_rc_text}\n\n"
            f"💰 Доход:\n"
            f"   STANDARD × {config.PRICE_STANDARD} = {standard * config.PRICE_STANDARD} ₸\n"
            f"   PRO × {config.PRICE_PRO} = {pro * config.PRICE_PRO} ₸\n"
            f"   💵 Итого: {revenue:,} ₸"
        )
        
        await callback.message.edit_text(text, reply_markup=admin_back_kb())
        await callback.answer()
        
    except Exception as e:
        logger.exception("Admin stats error: %s", e)
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)


@router.callback_query(F.data == "admin:users")
@admin_only
async def admin_users(callback: CallbackQuery):
    """Show users summary."""
    try:
        config = Config.from_env()
        pool = await get_pool(config.DATABASE_URL)
        
        users_today = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours'"
        ) or 0
        users_week = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '7 days'"
        ) or 0
        users_month = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '30 days'"
        ) or 0
        
        notifications_on = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE notifications_enabled = TRUE"
        ) or 0
        
        text = (
            f"👥 Пользователи\n\n"
            f"📅 За сегодня: {users_today}\n"
            f"📅 За неделю: {users_week}\n"
            f"📅 За месяц: {users_month}\n\n"
            f"🔔 Уведомления включены: {notifications_on}"
        )
        
        await callback.message.edit_text(text, reply_markup=admin_back_kb())
        await callback.answer()
        
    except Exception as e:
        logger.exception("Admin users error: %s", e)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin:subscriptions")
@admin_only
async def admin_subscriptions(callback: CallbackQuery):
    """Show subscription details."""
    try:
        config = Config.from_env()
        pool = await get_pool(config.DATABASE_URL)
        
        expiring_soon = await pool.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE subscription_type IN ('standard', 'pro')
            AND subscription_until > NOW()
            AND subscription_until < NOW() + INTERVAL '3 days'
            """
        ) or 0
        
        expired_today = await pool.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE subscription_type IN ('standard', 'pro')
            AND subscription_until::date = CURRENT_DATE
            """
        ) or 0
        
        text = (
            f"💎 Подписки\n\n"
            f"⚠ Истекают в течение 3 дней: {expiring_soon}\n"
            f"📅 Истекли сегодня: {expired_today}\n\n"
            f"Используйте /admin для полной статистики"
        )
        
        await callback.message.edit_text(text, reply_markup=admin_back_kb())
        await callback.answer()
        
    except Exception as e:
        logger.exception("Admin subscriptions error: %s", e)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin:broadcast")
@admin_only
async def admin_broadcast_menu(callback: CallbackQuery):
    """Show broadcast menu."""
    text = (
        "📢 Рассылка\n\n"
        "Выберите аудиторию для рассылки:"
    )
    await callback.message.edit_text(text, reply_markup=admin_broadcast_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_bc:"))
@admin_only
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Start broadcast process."""
    target = callback.data.split(":")[-1]
    
    await state.update_data(broadcast_target=target)
    await state.set_state(BroadcastStates.waiting_message)
    
    target_text = {
        "all": "всем пользователям",
        "pro": "PRO пользователям",
        "standard": "STANDARD пользователям",
        "free": "FREE пользователям",
    }.get(target, "выбранной группе")
    
    await callback.message.edit_text(
        f"📢 Рассылка {target_text}\n\n"
        f"Отправьте сообщение для рассылки.\n"
        f"Для отмены отправьте /cancel"
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_message, Command("cancel"))
@admin_only
async def broadcast_cancel(message: Message, state: FSMContext):
    """Cancel broadcast."""
    await state.clear()
    await message.answer("❌ Рассылка отменена", reply_markup=admin_main_kb())


@router.message(BroadcastStates.waiting_message)
@admin_only
async def admin_broadcast_send(message: Message, state: FSMContext):
    """Execute broadcast."""
    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    
    config = Config.from_env()
    pool = await get_pool(config.DATABASE_URL)
    
    # Get target users
    if target == "all":
        users = await pool.fetch("SELECT user_id FROM users")
    elif target == "pro":
        users = await pool.fetch(
            "SELECT user_id FROM users WHERE subscription_type = 'pro'"
        )
    elif target == "standard":
        users = await pool.fetch(
            "SELECT user_id FROM users WHERE subscription_type = 'standard'"
        )
    elif target == "free":
        users = await pool.fetch(
            "SELECT user_id FROM users WHERE subscription_type = 'free'"
        )
    else:
        users = []
    
    total = len(users)
    
    status_msg = await message.answer(
        f"📢 Начинаю рассылку...\n"
        f"Всего пользователей: {total}"
    )
    
    success = 0
    failed = 0
    
    # Batch sending with rate limit (30 msg/sec)
    for i, user in enumerate(users):
        try:
            await message.bot.copy_message(
                chat_id=user["user_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            success += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for {user['user_id']}: {e}")
            failed += 1
        
        # Update status every 50 messages
        if (i + 1) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"📢 Рассылка в процессе...\n"
                    f"Отправлено: {i + 1}/{total}\n"
                    f"✅ Успешно: {success}\n"
                    f"❌ Ошибок: {failed}"
                )
            except:
                pass
        
        # Rate limiting: 30 msg/sec
        await asyncio.sleep(1 / 30)
    
    await state.clear()
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"Всего: {total}\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}"
    )


@router.callback_query(F.data == "admin:rc")
@admin_only
async def admin_rc_menu(callback: CallbackQuery):
    """Show RC management menu."""
    text = (
        "🏢 Управление ЖК\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(text, reply_markup=admin_rc_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_rc:list")
@admin_only
async def admin_rc_list(callback: CallbackQuery):
    """Show list of all residential complexes."""
    try:
        config = Config.from_env()
        pool = await get_pool(config.DATABASE_URL)
        
        complexes = await pool.fetch(
            """
            SELECT id, name, category, priority, is_active
            FROM residential_complexes
            ORDER BY priority DESC, name ASC
            LIMIT 30
            """
        )
        
        if not complexes:
            await callback.answer("Нет ЖК в базе", show_alert=True)
            return
        
        lines = []
        for rc in complexes:
            status = "🟢" if rc["is_active"] else "🔴"
            lines.append(
                f"{status} {rc['name']} ({rc['category']}, p:{rc['priority']})"
            )
        
        text = "🏢 Список ЖК:\n\n" + "\n".join(lines[:20])
        if len(complexes) > 20:
            text += f"\n\n...и еще {len(complexes) - 20}"
        
        await callback.message.edit_text(text, reply_markup=admin_back_kb())
        await callback.answer()
        
    except Exception as e:
        logger.exception("Admin RC list error: %s", e)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_rc:add")
@admin_only
async def admin_rc_add_start(callback: CallbackQuery, state: FSMContext):
    """Start adding new RC."""
    await state.set_state(RCStates.waiting_name)
    await callback.message.edit_text(
        "➕ Добавление нового ЖК\n\n"
        "Введите название ЖК:\n"
        "(для отмены отправьте /cancel)"
    )
    await callback.answer()


@router.message(RCStates.waiting_name, Command("cancel"))
@admin_only
async def rc_add_cancel(message: Message, state: FSMContext):
    """Cancel RC addition."""
    await state.clear()
    await message.answer("❌ Отменено")


@router.message(RCStates.waiting_name)
@admin_only
async def admin_rc_add_name(message: Message, state: FSMContext):
    """Receive RC name."""
    name = message.text.strip()
    await state.update_data(rc_name=name)
    await state.set_state(RCStates.waiting_category)
    
    await message.answer(
        f"Название: {name}\n\n"
        f"Введите категорию (premium/business/comfort):"
    )


@router.message(RCStates.waiting_category)
@admin_only
async def admin_rc_add_category(message: Message, state: FSMContext):
    """Receive RC category."""
    category = message.text.strip().lower()
    
    if category not in ["premium", "business", "comfort"]:
        await message.answer("❌ Неверная категория. Используйте: premium, business, comfort")
        return
    
    await state.update_data(rc_category=category)
    await state.set_state(RCStates.waiting_priority)
    
    await message.answer(
        f"Категория: {category}\n\n"
        f"Введите приоритет (число 1-10):"
    )


@router.message(RCStates.waiting_priority)
@admin_only
async def admin_rc_add_priority(message: Message, state: FSMContext):
    """Receive RC priority and save."""
    try:
        priority = int(message.text.strip())
        if not 1 <= priority <= 10:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 10")
        return
    
    data = await state.get_data()
    name = data["rc_name"]
    category = data["rc_category"]
    
    config = Config.from_env()
    pool = await get_pool(config.DATABASE_URL)
    
    try:
        await pool.execute(
            """
            INSERT INTO residential_complexes (name, category, priority, is_active)
            VALUES ($1, $2, $3, TRUE)
            """,
            name,
            category,
            priority,
        )
        
        await message.answer(
            f"✅ ЖК добавлен!\n\n"
            f"Название: {name}\n"
            f"Категория: {category}\n"
            f"Приоритет: {priority}"
        )
        
    except Exception as e:
        logger.exception("RC add error: %s", e)
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()


@router.callback_query(F.data == "admin:system")
@admin_only
async def admin_system_status(callback: CallbackQuery):
    """Show system status."""
    try:
        config = Config.from_env()
        pool = await get_pool(config.DATABASE_URL)
        
        # DB check
        try:
            await pool.fetchval("SELECT 1")
            db_status = "🟢 OK"
        except:
            db_status = "🔴 ERROR"
        
        # Redis check
        try:
            from config import get_redis
            redis = await get_redis()
            await redis.ping()
            redis_status = "🟢 OK"
        except:
            redis_status = "🔴 ERROR"
        
        # Async tasks
        tasks = len([t for t in asyncio.all_tasks() if not t.done()])
        
        # Memory
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # CPU
        cpu_percent = process.cpu_percent(interval=0.1)
        
        text = (
            f"⚙ Статус системы\n\n"
            f"🗄 Database: {db_status}\n"
            f"🔴 Redis: {redis_status}\n"
            f"⚡ Async tasks: {tasks}\n"
            f"💾 Memory: {memory_mb:.1f} MB\n"
            f"🔧 CPU: {cpu_percent:.1f}%\n"
            f"⏰ Uptime: running\n\n"
            f"📦 Python: {psutil.PROCFS_PATH or 'N/A'}"
        )
        
        await callback.message.edit_text(text, reply_markup=admin_back_kb())
        await callback.answer()
        
    except Exception as e:
        logger.exception("System status error: %s", e)
        await callback.answer("❌ Ошибка", show_alert=True)
