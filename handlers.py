"""Обработчики бота. Start, аренда/продажа, подписка, статистика, админ."""
from datetime import datetime
from email.mime import message

from aiogram import Router, F, BaseMiddleware, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
# CancelHandler moved in aiogram 3.x
from aiogram.dispatcher.event.bases import CancelHandler

from config import Config
from database import (
    get_pool,
    user_get_or_create,
    user_get,
    user_accept_terms,
    user_start_trial,
    user_set_mode,
    user_set_rooms,
    user_set_district,
    user_set_notifications,
    user_upgrade,
    sent_was_sent,
    sent_mark,
    sent_count_today,
    stats_increment_new_users,
)
from keyboards import (
    main_kb,
    mode_kb,
    rooms_kb,
    district_kb,
    search_kb,
    terms_kb,
    subscription_kb,
    pay_confirm_kb,
    pay_request_kb,
)
from parser import KrishaParser

router = Router()

TERMS_TEXT = (
    "Бот предоставляет автоматический мониторинг объявлений.\n"
    "Мы не являемся официальным представителем Krisha.kz.\n"
    "Продолжая использование, вы соглашаетесь с условиями."
)

DISTRICT_MAP = {
    "Алмалинский": "almalinskij",
    "Ауэзовский": "aujezovskij",
    "Бостандыкский": "bostandykskij",
    "Жетысуский": "zhetysuskij",
    "Медеуский": "medeuskij",
    "Наурызбайский": "nauryzbajskiy",
    "Турксибский": "turksibskij",
    "Алатауский": "alatauskij",
}


# middleware that verifies user subscription status
class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # only messages and callback queries require a subscription check
        if isinstance(event, types.Message):
            text = event.text or ""
            # onboarding and payment flows are exempt
            if text.startswith("/start") or text.startswith("/help") or text in (
                "💎 Подписка",
                "🎁 Пробный доступ",
            ):
                return await handler(event, data)
        elif isinstance(event, types.CallbackQuery):
            d = event.data or ""
            if d == "terms:accept" or d.startswith("sub:") or d.startswith("pay:"):
                return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        pool = await get_pool()
        u = await user_get(pool, user.id)
        if not u:
            # unregistered users are redirected to /start
            if isinstance(event, types.Message):
                await event.answer("Нажмите /start")
            else:
                await event.message.answer("Нажмите /start")
            raise CancelHandler()

        # block if subscription_until is missing or in the past
        until = u.get("subscription_until")
        if not until or until <= datetime.utcnow():
            msg = "Нет активной подписки. Оформите платный тариф или пробный доступ."
            if isinstance(event, types.Message):
                await event.answer(msg)
            else:
                await event.message.answer(msg)
            raise CancelHandler()

        return await handler(event, data)

ROOM_MAP = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣+": 5}


def _has_access(user: dict, config: Config) -> tuple[bool, str]:
    """Legacy helper kept for backwards compatibility.

    Current middleware no longer uses this, but older functions may still
    call it. It now simply checks the "subscription_until" field.
    """
    until = user.get("subscription_until")
    if until and until > datetime.utcnow():
        return True, ""
    return False, "Нет активной подписки."


def _fmt_amount(n: int) -> str:
    return f"{n:,}".replace(",", " ")


# --- Start ---


@router.message(CommandStart())
async def cmd_start(message: Message):
    if not message.from_user:
        return
    pool = await get_pool()
    config = Config.from_env()
    u = await user_get_or_create(pool, message.from_user.id, message.from_user.username)
    if not u:
        return
    if not u.get("accepted_terms"):
        await message.answer(TERMS_TEXT, reply_markup=terms_kb())
        return
    await message.answer("Выберите действие:", reply_markup=main_kb())


@router.callback_query(F.data == "terms:accept")
async def terms_accept(callback: CallbackQuery):
    await callback.answer()
    pool = await get_pool()
    await user_accept_terms(pool, callback.from_user.id)
    await stats_increment_new_users(pool)
    await callback.message.edit_text("✅ Согласие получено.")
    await callback.message.answer("Выберите действие:", reply_markup=main_kb())


# --- Trial ---


@router.message(F.text == "🎁 Пробный доступ")
async def trial_start(message: Message):
    pool = await get_pool()
    config = Config.from_env()
    u = await user_get(pool, message.from_user.id)
    if not u or not u.get("accepted_terms"):
        await message.answer("Сначала нажмите /start и примите условия.")
        return
    if u.get("trial_used"):
        await message.answer(
            "Пробный период уже использован. Оформите подписку в разделе 💎 Подписка."
        )
        return
    await user_start_trial(pool, message.from_user.id, config.TRIAL_HOURS)
    await message.answer(
        f"🎁 Пробный доступ на {config.TRIAL_HOURS} часа активирован! Выберите режим и параметры."
    )


# --- Rent / Sale ---


@router.message(F.text.in_(["🏠 Аренда", "🏡 Продажа"]))
async def mode_select(message: Message):
    # middleware guarantees user exists and has access
    pool = await get_pool()
    config = Config.from_env()
    mode = "rent" if message.text == "🏠 Аренда" else "sale"
    await user_set_mode(pool, message.from_user.id, mode)
    await user_set_district(pool, message.from_user.id, None)
    await user_set_rooms(pool, message.from_user.id, 1)
    await message.answer("Выберите количество комнат:", reply_markup=rooms_kb())


@router.message(F.text.in_(list(ROOM_MAP)))
async def rooms_select(message: Message):
    pool = await get_pool()
    config = Config.from_env()
    # middleware has already ensured user exists and is authorized
    rooms = ROOM_MAP[message.text]
    await user_set_rooms(pool, message.from_user.id, rooms)
    await message.answer("Выберите район:", reply_markup=district_kb())



from datetime import datetime
from email.mime import message

from aiogram import Router, F, BaseMiddleware, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
# CancelHandler moved in aiogram 3.x
from aiogram.dispatcher.event.bases import CancelHandler

from config import Config
from database import (
    get_pool,
    user_get_or_create,
    user_get,
    user_accept_terms,
    user_start_trial,
    user_set_mode,
    user_set_rooms,
    user_set_district,
    user_set_notifications,
    user_upgrade,
    sent_was_sent,
    sent_mark,
    sent_count_today,
    stats_increment_new_users,
)
from keyboards import (
    main_kb,
    mode_kb,
    rooms_kb,
    district_kb,
    search_kb,
    terms_kb,
    subscription_kb,
    pay_confirm_kb,
    pay_request_kb,
)
from parser import KrishaParser

router = Router()

TERMS_TEXT = (
    "Бот предоставляет автоматический мониторинг объявлений.\n"
    "Мы не являемся официальным представителем Krisha.kz.\n"
    "Продолжая использование, вы соглашаетесь с условиями."
)

DISTRICT_MAP = {
    "Алмалинский": "almalinskij",
    "Ауэзовский": "aujezovskij",
    "Бостандыкский": "bostandykskij",
    "Жетысуский": "zhetysuskij",
    "Медеуский": "medeuskij",
    "Наурызбайский": "nauryzbajskiy",
    "Турксибский": "turksibskij",
    "Алатауский": "alatauskij",
}


# middleware that verifies user subscription status
class SubscriptionMiddleware(BaseMiddleware):
    async def call(self, handler, event, data):
        # only messages and callback queries require a subscription check
        if isinstance(event, types.Message):
            text = event.text or ""
            # onboarding and payment flows are exempt
            if text.startswith("/start") or text.startswith("/help") or text in (
                "💎 Подписка",
                "🎁 Пробный доступ",
            ):
                return await handler(event, data)
        elif isinstance(event, types.CallbackQuery):
            d = event.data or ""
            if d == "terms:accept" or d.startswith("sub:") or d.startswith("pay:"):
                return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        pool = await get_pool()
        u = await user_get(pool, user.id)
        if not u:
            # unregistered users are redirected to /start
            if isinstance(event, types.Message):
                await event.answer("Нажмите /start")
            else:
                await event.message.answer("Нажмите /start")
            raise CancelHandler()

        # block if subscription_until is missing or in the past
        until = u.get("subscription_until")
        if not until or until <= datetime.utcnow():
            msg = "Нет активной подписки. Оформите платный тариф или пробный доступ."
            if isinstance(event, types.Message):
                await event.answer(msg)
            else:
                await event.message.answer(msg)
            raise CancelHandler()

        return await handler(event, data)

ROOM_MAP = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣+": 5}


def _has_access(user: dict, config: Config) -> tuple[bool, str]:
    """Legacy helper kept for backwards compatibility.

    Current middleware no longer uses this, but older functions may still
    call it. It now simply checks the "subscription_until" field.
    """
    until = user.get("subscription_until")
    if until and until > datetime.utcnow():
        return True, ""
    return False, "Нет активной подписки."


def _fmt_amount(n: int) -> str:
    return f"{n:,}".replace(",", " ")


# --- Start ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not message.from_user:
        return
    pool = await get_pool()
    config = Config.from_env()
    u = await user_get_or_create(pool, message.from_user.id, message.from_user.username)
    if not u:
        return
    if not u.get("accepted_terms"):
        await message.answer(TERMS_TEXT, reply_markup=terms_kb())
        return
    await message.answer("Выберите действие:", reply_markup=main_kb())


@router.callback_query(F.data == "terms:accept")
async def terms_accept(callback: CallbackQuery):
    await callback.answer()
    pool = await get_pool()
    await user_accept_terms(pool, callback.from_user.id)
    await stats_increment_new_users(pool)
    await callback.message.edit_text("✅ Согласие получено.")
    await callback.message.answer("Выберите действие:", reply_markup=main_kb())


# --- Trial ---


@router.message(F.text == "🎁 Пробный доступ")
async def trial_start(message: Message):
    pool = await get_pool()
    config = Config.from_env()
    u = await user_get(pool, message.from_user.id)
    if not u or not u.get("accepted_terms"):
        await message.answer("Сначала нажмите /start и примите условия.")
        return
    if u.get("trial_used"):
        await message.answer(
            "Пробный период уже использован. Оформите подписку в разделе 💎 Подписка."
        )
        return
    await user_start_trial(pool, message.from_user.id, config.TRIAL_HOURS)
    await message.answer(
        f"🎁 Пробный доступ на {config.TRIAL_HOURS} часа активирован! Выберите режим и параметры."
    )


# --- Rent / Sale ---


@router.message(F.text.in_(["🏠 Аренда", "🏡 Продажа"]))
async def mode_select(message: Message):
    # middleware guarantees user exists and has access
    pool = await get_pool()
    config = Config.from_env()
    mode = "rent" if message.text == "🏠 Аренда" else "sale"
    await user_set_mode(pool, message.from_user.id, mode)
    await user_set_district(pool, message.from_user.id, None)
    await user_set_rooms(pool, message.from_user.id, 1)
    await message.answer("Выберите количество комнат:", reply_markup=rooms_kb())


@router.message(F.text.in_(list(ROOM_MAP)))
async def rooms_select(message: Message):
    pool = await get_pool()
    config = Config.from_env()
    # middleware has already ensured user exists and is authorized
    rooms = ROOM_MAP[message.text]
    await user_set_rooms(pool, message.from_user.id, rooms)
    await message.answer("Выберите район:", reply_markup=district_kb())


@router.message(F.text == "⬅️ Назад")
async def back(message: Message):
    pool = await get_pool()
    u = await user_get(pool, message.from_user.id)
    if not u:
        await message.answer("Выберите режим:", reply_markup=mode_kb())
        return
    if u.get("district"):
        await user_set_district(pool, message.from_user.id, None)
        await message.answer("Выберите район:", reply_markup=district_kb())
        return
    if u.get("rooms"):
        await user_set_rooms(pool, message.from_user.id, 1)
        await message.answer("Выберите количество комнат:", reply_markup=rooms_kb())
        return
    await message.answer("Выберите режим:", reply_markup=mode_kb())


@router.message(F.text == "⛔️ Стоп")
async def stop_notifications(message: Message):
    pool = await get_pool()
    await user_set_notifications(pool, message.from_user.id, False)
    await message.answer("❌ Уведомления остановлены.", reply_markup=main_kb())


@router.message(F.text == "▶️ Запустить уведомления")
async def start_notifications(message: Message):
    pool = await get_pool()
    u = await user_get(pool, message.from_user.id)
    if not u or not u.get("district"):
        await message.answer("Сначала выберите режим и район.")
        return
    await user_set_notifications(pool, message.from_user.id, True)
    await message.answer("✅ Уведомления включены.")


@router.message(F.text == "⚙️ Изменить параметры")
async def change_params(message: Message):
    pool = await get_pool()
    await user_set_district(pool, message.from_user.id, None)
    await user_set_rooms(pool, message.from_user.id, 1)
    await message.answer("Выберите режим:", reply_markup=mode_kb())


# --- Subscription ---


@router.message(F.text == "💎 Подписка")
async def subscription_info(message: Message):
    pool = await get_pool()
    config = Config.from_env()
    u = await user_get(pool, message.from_user.id)
    sub_type = u.get("subscription_type") or "free"
    until = u.get("subscription_until") or u.get("trial_until")
    if sub_type in ("standard", "pro") and until and until > datetime.utcnow():
        text = f"💎 {sub_type.upper()} до {until.strftime('%d.%m.%Y')}"
    elif u.get("trial_until") and u["trial_until"] > datetime.utcnow():
        text = f"🎁 Пробный период до {u['trial_until'].strftime('%d.%m.%Y %H:%M')}"
    else:
        text = (
            f"STANDARD — {_fmt_amount(config.PRICE_STANDARD)} ₸/мес\n"
            f"• Все районы, 1-3 комнаты, проверка каждые 2 мин\n\n"
            f"PRO — {_fmt_amount(config.PRICE_PRO)} ₸/мес\n"
            f"• Проверка каждые 30 сек, приоритет, без лимитов"
        )
    await message.answer(text, reply_markup=subscription_kb(config))


@router.callback_query(F.data.startswith("sub:"))
async def subscription_request(callback: CallbackQuery):
    await callback.answer()
    plan = callback.data.split(":")[1]
    pool = await get_pool()
    config = Config.from_env()
    price = config.PRICE_PRO if plan == "pro" else config.PRICE_STANDARD
    row = await pool.fetchrow(
        "INSERT INTO payment_requests (user_id, amount, plan) VALUES ($1, $2, $3) RETURNING id",
        callback.from_user.id,
        price,
        plan,
    )
    req_id = row["id"]
    
    card = "4400430316006763\nПолучатель: NIURGUN"

    await callback.message.edit_text(
        f"💳 Оплата {_fmt_amount(price)} ₸\n\n"
        f"Переведите на карту:\n{card}\n\n"
        f"После перевода нажмите «Оплатил».",
        reply_markup=pay_request_kb(req_id),
    )

@router.callback_query(F.data.startswith("pay:request:"))
async def pay_request_sent(callback: CallbackQuery):
    await callback.answer("Заявка отправлена администратору.")
    req_id = int(callback.data.split(":")[2])
    pool = await get_pool()
    config = Config.from_env()
    row = await pool.fetchrow(
        "SELECT user_id, amount, plan FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.message.edit_text("Заявка уже обработана.")
        return
    u = callback.from_user
    for admin_id in config.ADMIN_IDS:
        if admin_id:
            await callback.bot.send_message(
                admin_id,
                f"💳 Заявка #{req_id}\n\n👤 {u.first_name} (@{u.username or '—'})\n"
                f"💰 {row['amount']} ₸ — {row['plan']}\n\nПодтвердите после получения:",
                reply_markup=pay_confirm_kb(req_id),
            )
    await callback.message.edit_text("⏳ Заявка отправлена. Ожидайте подтверждения.")


@router.callback_query(F.data.startswith("pay:ok:"))
async def pay_confirm(callback: CallbackQuery):
    config = Config.from_env()
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    req_id = int(callback.data.split(":")[2])
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id, plan FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    await pool.execute(
        "UPDATE payment_requests SET status = 'confirmed', confirmed_at = NOW(), confirmed_by = $1 WHERE id = $2",
        callback.from_user.id,
        req_id,
    )
    await user_upgrade(pool, row["user_id"], row["plan"], 30)
    await callback.answer("Подписка активирована.")
    await callback.message.edit_text(f"✅ Платёж #{req_id} подтверждён.")
    try:
        from datetime import datetime, timedelta
        until = datetime.utcnow() + timedelta(days=30)
        await callback.bot.send_message(
            row["user_id"],
            f"✅ Платёж подтверждён! Подписка до {until.strftime('%d.%m.%Y')}.",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay:no:"))
async def pay_reject(callback: CallbackQuery):
    config = Config.from_env()
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    req_id = int(callback.data.split(":")[2])
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    await pool.execute("UPDATE payment_requests SET status = 'rejected' WHERE id = $1", req_id)
    await callback.answer("Заявка отклонена.")
    await callback.message.edit_text(f"❌ Заявка #{req_id} отклонена.")
    try:
        await callback.bot.send_message(row["user_id"], "❌ Платёж не подтверждён.")
    except Exception:
        pass


# --- Stats ---

# register middleware after all handlers have been defined
router.message.middleware(SubscriptionMiddleware())
router.callback_query.middleware(SubscriptionMiddleware())


@router.message(F.text == "📊 Статистика")
async def user_stats(message: Message):
    pool = await get_pool()
    u = await user_get(pool, message.from_user.id)
    sub_type = u.get("subscription_type") or "free"
    until = u.get("subscription_until") or u.get("trial_until")
    until_str = until.strftime("%d.%m.%Y") if until else "—"
    sent_today = await sent_count_today(pool, message.from_user.id)
    total_sent = await pool.fetchval(
        "SELECT COUNT(*) FROM sent_listings WHERE user_id = $1",
        message.from_user.id,
    ) or 0
    users_total = await pool.fetchval("SELECT COUNT(*) FROM users") or 0
    active_subs = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type IN ('standard', 'pro') AND subscription_until > NOW()"
    ) or 0
    new_today = await pool.fetchval(
        "SELECT COALESCE(new_users, 0) FROM stats WHERE date = CURRENT_DATE"
    ) or 0
    msg_sent = await pool.fetchval("SELECT COALESCE(SUM(messages_sent), 0) FROM stats") or 0
    text = (
        f"📊 Статистика\n\n"
        f"👤 Ваш тариф: {sub_type.upper()}\n"
        f"📅 Окончание: {until_str}\n"
        f"📨 Получено сегодня: {sent_today}\n"
        f"📨 Всего: {total_sent}\n\n"
        f"--- Общая ---\n"
        f"👥 Пользователей: {users_total}\n"
        f"💎 Активных подписок: {active_subs}\n"
        f"🆕 Новых сегодня: {new_today}\n"
        f"📤 Отправлено: {msg_sent}"
    )
    await message.answer(text)


# --- Admin ---


@router.message(Command("admin"))
async def admin_panel(message: Message):
    config = Config.from_env()
    if message.from_user.id not in config.ADMIN_IDS:
        return
    pool = await get_pool()
    users_total = await pool.fetchval("SELECT COUNT(*) FROM users") or 0
    free = await pool.fetchval("SELECT COUNT(*) FROM users WHERE subscription_type = 'free'") or 0
    standard = await pool.fetchval("SELECT COUNT(*) FROM users WHERE subscription_type = 'standard'") or 0
    pro = await pool.fetchval("SELECT COUNT(*) FROM users WHERE subscription_type = 'pro'") or 0
    active_subs = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type IN ('standard', 'pro') AND subscription_until > NOW()"
    ) or 0
    active_today = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours'"
    ) or 0
    msg_sent = await pool.fetchval("SELECT COALESCE(SUM(messages_sent), 0) FROM stats") or 0
    revenue = (standard or 0) * config.PRICE_STANDARD + (pro or 0) * config.PRICE_PRO
    text = (
        f"👑 Админ\n\n"
        f"👥 Всего: {users_total} | FREE: {free} | STANDARD: {standard} | PRO: {pro}\n"
        f"✅ Активных подписок: {active_subs}\n"
        f"📈 Активных сегодня: {active_today}\n"
        f"📤 Сообщений: {msg_sent}\n\n"
        f"💰 Доход: {revenue} ₸"
    )
    await message.answer(text)

@router.message(F.text.in_(list(DISTRICT_MAP)))
async def district_select(message: Message):
    pool = await get_pool()
    config = Config.from_env()

    district = message.text

    await user_set_district(pool, message.from_user.id, district)
    await user_set_notifications(pool, message.from_user.id, True)

    u = await pool.fetchrow(
        """
        SELECT mode, rooms, price_min, price_max, district
        FROM users
        WHERE user_id = $1
        """,
        message.from_user.id,
    )

    mode = u.get("mode") or "rent"
    rooms = u.get("rooms") or 1

    parser = KrishaParser(config)
    slug = DISTRICT_MAP[u.get("district")]

    listings = await parser.parse(
        mode,
        rooms,
        slug,
        u.get("price_min"),
        u.get("price_max"),
    )

    await message.answer(
        "🔎 Поиск настроен. Отправляю первую страницу...",
        reply_markup=search_kb(),
    )

    for ls in listings[:10]:
        if await sent_was_sent(pool, message.from_user.id, ls.id):
            continue

        text = f"🏠 {ls.title}\n💰 {ls.price}\n🔗 {ls.url}"
        await message.answer(text)
        await sent_mark(pool, message.from_user.id, ls.id)


@router.message(F.text == "⬅ Назад")
async def back(message: Message):
    pool = await get_pool()
    u = await user_get(pool, message.from_user.id)
    if not u:
        await message.answer("Выберите режим:", reply_markup=mode_kb())
        return
    if u.get("district"):
        await user_set_district(pool, message.from_user.id, None)
        await message.answer("Выберите район:", reply_markup=district_kb())
        return
    if u.get("rooms"):
        await user_set_rooms(pool, message.from_user.id, 1)
        await message.answer("Выберите количество комнат:", reply_markup=rooms_kb())
        return
    await message.answer("Выберите режим:", reply_markup=mode_kb())


@router.message(F.text == "⛔ Стоп")
async def stop_notifications(message: Message):
    pool = await get_pool()
    await user_set_notifications(pool, message.from_user.id, False)
    await message.answer("❌ Уведомления остановлены.", reply_markup=main_kb())


@router.message(F.text == "▶ Запустить уведомления")
async def start_notifications(message: Message):
    pool = await get_pool()
    u = await user_get(pool, message.from_user.id)
    if not u or not u.get("district"):
        await message.answer("Сначала выберите режим и район.")
        return
    await user_set_notifications(pool, message.from_user.id, True)
    await message.answer("✅ Уведомления включены.")


@router.message(F.text == "⚙ Изменить параметры")
async def change_params(message: Message):
    pool = await get_pool()
    await user_set_district(pool, message.from_user.id, None)
    await user_set_rooms(pool, message.from_user.id, 1)
    await message.answer("Выберите режим:", reply_markup=mode_kb())


# --- Subscription ---


@router.message(F.text == "💎 Подписка")
async def subscription_info(message: Message):
    pool = await get_pool()
    config = Config.from_env()
    u = await user_get(pool, message.from_user.id)
    sub_type = u.get("subscription_type") or "free"
    until = u.get("subscription_until") or u.get("trial_until")
    if sub_type in ("standard", "pro") and until and until > datetime.utcnow():
        text = f"💎 {sub_type.upper()} до {until.strftime('%d.%m.%Y')}"
    elif u.get("trial_until") and u["trial_until"] > datetime.utcnow():
        text = f"🎁 Пробный период до {u['trial_until'].strftime('%d.%m.%Y %H:%M')}"
    else:
        text = (
            f"STANDARD — {_fmt_amount(config.PRICE_STANDARD)} ₸/мес\n"
            f"• Все районы, 1-3 комнаты, проверка каждые 2 мин\n\n"
            f"PRO — {_fmt_amount(config.PRICE_PRO)} ₸/мес\n"
            f"• Проверка каждые 30 сек, приоритет, без лимитов"
        )
    await message.answer(text, reply_markup=subscription_kb(config))


@router.callback_query(F.data.startswith("sub:"))
async def subscription_request(callback: CallbackQuery):
    await callback.answer()
    plan = callback.data.split(":")[1]
    pool = await get_pool()
    config = Config.from_env()
    price = config.PRICE_PRO if plan == "pro" else config.PRICE_STANDARD
    row = await pool.fetchrow(
        "INSERT INTO payment_requests (user_id, amount, plan) VALUES ($1, $2, $3) RETURNING id",
        callback.from_user.id,
        price,
        plan,
    )
    req_id = row["id"]
    
    card = "4400430316006763\nПолучатель: NIURGUN"

    await callback.message.edit_text(
        f"💳 Оплата {_fmt_amount(price)} ₸\n\n"
        f"Переведите на карту:\n{card}\n\n"
        f"После перевода нажмите «Оплатил».",
        reply_markup=pay_request_kb(req_id),
    )


@router.callback_query(F.data.startswith("pay:request:"))
async def pay_request_sent(callback: CallbackQuery):
    await callback.answer("Заявка отправлена администратору.")
    req_id = int(callback.data.split(":")[2])
    pool = await get_pool()
    config = Config.from_env()
    row = await pool.fetchrow(
        "SELECT user_id, amount, plan FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.message.edit_text("Заявка уже обработана.")
        return
    u = callback.from_user
    for admin_id in config.ADMIN_IDS:
        if admin_id:
            await callback.bot.send_message(
                admin_id,
                f"💳 Заявка #{req_id}\n\n👤 {u.first_name} (@{u.username or '—'})\n"
                f"💰 {row['amount']} ₸ — {row['plan']}\n\nПодтвердите после получения:",
                reply_markup=pay_confirm_kb(req_id),
            )
    await callback.message.edit_text("⏳ Заявка отправлена. Ожидайте подтверждения.")


@router.callback_query(F.data.startswith("pay:ok:"))
async def pay_confirm(callback: CallbackQuery):
    config = Config.from_env()
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    req_id = int(callback.data.split(":")[2])
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id, plan FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    await pool.execute(
        "UPDATE payment_requests SET status = 'confirmed', confirmed_at = NOW(), confirmed_by = $1 WHERE id = $2",
        callback.from_user.id,
        req_id,
    )
    await user_upgrade(pool, row["user_id"], row["plan"], 30)
    await callback.answer("Подписка активирована.")
    await callback.message.edit_text(f"✅ Платёж #{req_id} подтверждён.")
    try:
        from datetime import datetime, timedelta
        until = datetime.utcnow() + timedelta(days=30)
        await callback.bot.send_message(
            row["user_id"],
            f"✅ Платёж подтверждён! Подписка до {until.strftime('%d.%m.%Y')}.",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay:no:"))
async def pay_reject(callback: CallbackQuery):
    config = Config.from_env()
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return
    req_id = int(callback.data.split(":")[2])
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT user_id FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return
    await pool.execute("UPDATE payment_requests SET status = 'rejected' WHERE id = $1", req_id)
    await callback.answer("Заявка отклонена.")
    await callback.message.edit_text(f"❌ Заявка #{req_id} отклонена.")
    try:
        await callback.bot.send_message(row["user_id"], "❌ Платёж не подтверждён.")
    except Exception:
        pass


# --- Stats ---

# register middleware after all handlers have been defined
router.message.middleware(SubscriptionMiddleware())
router.callback_query.middleware(SubscriptionMiddleware())


@router.message(F.text == "📊 Статистика")
async def user_stats(message: Message):
    pool = await get_pool()
    u = await user_get(pool, message.from_user.id)
    sub_type = u.get("subscription_type") or "free"
    until = u.get("subscription_until") or u.get("trial_until")
    until_str = until.strftime("%d.%m.%Y") if until else "—"
    sent_today = await sent_count_today(pool, message.from_user.id)
    total_sent = await pool.fetchval(
        "SELECT COUNT(*) FROM sent_listings WHERE user_id = $1",
        message.from_user.id,
    ) or 0
    users_total = await pool.fetchval("SELECT COUNT(*) FROM users") or 0
    active_subs = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type IN ('standard', 'pro') AND subscription_until > NOW()"
    ) or 0
    new_today = await pool.fetchval(
        "SELECT COALESCE(new_users, 0) FROM stats WHERE date = CURRENT_DATE"
    ) or 0
    msg_sent = await pool.fetchval("SELECT COALESCE(SUM(messages_sent), 0) FROM stats") or 0
    text = (
        f"📊 Статистика\n\n"
        f"👤 Ваш тариф: {sub_type.upper()}\n"
        f"📅 Окончание: {until_str}\n"
        f"📨 Получено сегодня: {sent_today}\n"
        f"📨 Всего: {total_sent}\n\n"
        f"--- Общая ---\n"
        f"👥 Пользователей: {users_total}\n"
        f"💎 Активных подписок: {active_subs}\n"
        f"🆕 Новых сегодня: {new_today}\n"
        f"📤 Отправлено: {msg_sent}"
    )
    await message.answer(text)


# --- Admin ---


@router.message(Command("admin"))
async def admin_panel(message: Message):
    config = Config.from_env()
    if message.from_user.id not in config.ADMIN_IDS:
        return
    pool = await get_pool()
    users_total = await pool.fetchval("SELECT COUNT(*) FROM users") or 0
    free = await pool.fetchval("SELECT COUNT(*) FROM users WHERE subscription_type = 'free'") or 0
    standard = await pool.fetchval("SELECT COUNT(*) FROM users WHERE subscription_type = 'standard'") or 0
    pro = await pool.fetchval("SELECT COUNT(*) FROM users WHERE subscription_type = 'pro'") or 0
    active_subs = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type IN ('standard', 'pro') AND subscription_until > NOW()"
    ) or 0
    active_today = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours'"
    ) or 0
    msg_sent = await pool.fetchval("SELECT COALESCE(SUM(messages_sent), 0) FROM stats") or 0
    revenue = (standard or 0) * config.PRICE_STANDARD + (pro or 0) * config.PRICE_PRO
    text = (
        f"👑 Админ\n\n"
        f"👥 Всего: {users_total} | FREE: {free} | STANDARD: {standard} | PRO: {pro}\n"
        f"✅ Активных подписок: {active_subs}\n"
        f"📈 Активных сегодня: {active_today}\n"
        f"📤 Сообщений: {msg_sent}\n\n"
        f"💰 Доход: {revenue} ₸"
    )
    await message.answer(text)
