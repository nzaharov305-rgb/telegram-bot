"""Reply-клавиатуры бота."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


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


DISTRICT_NAMES = [
    "Алмалинский",
    "Ауэзовский",
    "Бостандыкский",
    "Медеуский",
    "Жетысуский",
    "Турксибский",
    "Алатауский",
    "Наурызбайский",
]


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
