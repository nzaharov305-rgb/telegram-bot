"""Reply-клавиатуры бота."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Пробный доступ")],
            [
                KeyboardButton(text="🏠 Аренда"),
                KeyboardButton(text="🏡 Продажа"),
            ],
            [KeyboardButton(text="💎 Подписка")],
            [KeyboardButton(text="📊 Статистика")],
            [
                KeyboardButton(text="⛔ Остановить уведомления"),
                KeyboardButton(text="▶ Запустить уведомления"),
            ],
        ],
        resize_keyboard=True,
    )


def mode_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏠 Аренда"),
                KeyboardButton(text="🏡 Продажа"),
            ],
            [KeyboardButton(text="⬅ Назад")],
        ],
        resize_keyboard=True,
    )


def rooms_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1️⃣"),
                KeyboardButton(text="2️⃣"),
                KeyboardButton(text="3️⃣"),
            ],
            [KeyboardButton(text="4️⃣"), KeyboardButton(text="5️⃣+")],
            [KeyboardButton(text="⬅ Назад")],
        ],
        resize_keyboard=True,
    )


def district_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Алмалинский"),
                KeyboardButton(text="Ауэзовский"),
            ],
            [
                KeyboardButton(text="Бостандыкский"),
                KeyboardButton(text="Медеуский"),
            ],
            [
                KeyboardButton(text="Жетысуский"),
                KeyboardButton(text="Турксибский"),
            ],
            [
                KeyboardButton(text="Алатауский"),
                KeyboardButton(text="Наурызбайский"),
            ],
            [KeyboardButton(text="⬅ Назад")],
        ],
        resize_keyboard=True,
    )


def search_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙ Изменить параметры")],
            [KeyboardButton(text="⛔ Стоп")],
        ],
        resize_keyboard=True,
    )


def terms_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Согласен", callback_data="terms:accept"))
    return builder.as_markup()


def subscription_kb(config) -> InlineKeyboardMarkup:
    def fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"STANDARD {fmt(config.PRICE_STANDARD)} ₸",
            callback_data="sub:standard",
        ),
        InlineKeyboardButton(
            text=f"PRO {fmt(config.PRICE_PRO)} ₸",
            callback_data="sub:pro",
        ),
    )
    return builder.as_markup()


def pay_confirm_kb(req_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pay:ok:{req_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"pay:no:{req_id}"),
    )
    return builder.as_markup()


def pay_request_kb(req_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Оплатил", callback_data=f"pay:request:{req_id}"))
    return builder.as_markup()
