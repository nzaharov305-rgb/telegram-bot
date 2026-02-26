"""Подписка, оплата."""
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards import main_kb
from app.database.repositories import UserRepository

router = Router()


def _format_amount(n: int) -> str:
    return f"{n:,}".replace(",", " ")


@router.message(F.text == "💎 Подписка")
async def subscription_info(
    message: Message,
    user_repo: UserRepository,
    config,
):
    u = await user_repo.get(message.from_user.id)
    if not u:
        await message.answer("Нажмите /start")
        return

    sub_type = u.get("subscription_type") or "free"
    until = u.get("subscription_until") or u.get("trial_until")

    if sub_type == "free" and until and until > datetime.utcnow():
        text = f"🎁 Пробный период до {until.strftime('%d.%m.%Y %H:%M')}"
    elif sub_type in ("standard", "pro") and until and until > datetime.utcnow():
        text = f"💎 {sub_type.upper()} до {until.strftime('%d.%m.%Y')}"
    else:
        text = (
            f"STANDARD — {_format_amount(config.PRICE_STANDARD)} ₸/мес\n"
            f"• Все районы, 1-3 комнаты\n"
            f"• Проверка каждые 2 мин\n\n"
            f"PRO — {_format_amount(config.PRICE_PRO)} ₸/мес\n"
            f"• Проверка каждые 30 сек\n"
            f"• Фильтр «от хозяина»\n"
            f"• Несколько районов\n"
            f"• Приоритетная очередь"
        )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text=f"STANDARD {_format_amount(config.PRICE_STANDARD)} ₸",
            callback_data="sub:standard",
        ),
        InlineKeyboardButton(
            text=f"PRO {_format_amount(config.PRICE_PRO)} ₸",
            callback_data="sub:pro",
        ),
    )
    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("sub:"))
async def subscription_request(
    callback: CallbackQuery,
    user_repo: UserRepository,
    config,
):
    await callback.answer()
    plan = callback.data.split(":")[1]
    price = config.PRICE_PRO if plan == "pro" else config.PRICE_STANDARD

    import os
    from app.database.connection import get_pool

    pool = await get_pool(config.DATABASE_URL)
    row = await pool.fetchrow(
        """
        INSERT INTO payment_requests (user_id, amount, plan)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        callback.from_user.id,
        price,
        plan,
    )
    req_id = row["id"]

    payment_card = os.getenv("PAYMENT_CARD", "указана в настройках")

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✅ Оплатил", callback_data=f"pay:request:{req_id}"))
    await callback.message.edit_text(
        f"💳 Оплата {_format_amount(price)} ₸\n\n"
        f"Переведите на карту:\n{payment_card}\n\n"
        f"После перевода нажмите «Оплатил» — администратор подтвердит.",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("pay:request:"))
async def pay_request_sent(
    callback: CallbackQuery,
    config,
):
    await callback.answer("Заявка отправлена администратору.")
    req_id = int(callback.data.split(":")[2])

    from app.database.connection import get_pool
    from aiogram import Bot

    pool = await get_pool(config.DATABASE_URL)
    row = await pool.fetchrow(
        "SELECT user_id, amount, plan FROM payment_requests WHERE id = $1 AND status = 'pending'",
        req_id,
    )
    if not row:
        await callback.message.edit_text("Заявка уже обработана.")
        return

    user_id, amount, plan = row["user_id"], row["amount"], row["plan"]
    u = callback.from_user

    for admin_id in config.ADMIN_IDS:
        if admin_id:
            kb = InlineKeyboardBuilder()
            kb.row(
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pay:ok:{req_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"pay:no:{req_id}"),
            )
            bot = callback.bot
            await bot.send_message(
                admin_id,
                f"💳 Заявка #{req_id}\n\n"
                f"👤 {u.first_name} (@{u.username or '—'})\n"
                f"💰 {amount} ₸ — {plan}\n\n"
                f"Подтвердите после получения перевода:",
                reply_markup=kb.as_markup(),
            )

    await callback.message.edit_text(
        "⏳ Заявка отправлена. Ожидайте подтверждения администратором."
    )


@router.callback_query(F.data.startswith("pay:ok:"))
async def pay_confirm(
    callback: CallbackQuery,
    config,
):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    req_id = int(callback.data.split(":")[2])
    from datetime import datetime, timedelta
    from app.database.connection import get_pool

    pool = await get_pool(config.DATABASE_URL)
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
    until = datetime.utcnow() + timedelta(days=30)
    await pool.execute(
        "UPDATE users SET subscription_type = $1, subscription_until = $2 WHERE user_id = $3",
        row["plan"],
        until,
        row["user_id"],
    )

    await callback.answer("Подписка активирована.")
    await callback.message.edit_text(f"✅ Платёж #{req_id} подтверждён. Подписка на 30 дней.")

    try:
        await callback.bot.send_message(
            row["user_id"],
            f"✅ Платёж подтверждён! Подписка до {until.strftime('%d.%m.%Y')}.",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay:no:"))
async def pay_reject(
    callback: CallbackQuery,
    config,
):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    req_id = int(callback.data.split(":")[2])
    from app.database.connection import get_pool

    pool = await get_pool(config.DATABASE_URL)
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
