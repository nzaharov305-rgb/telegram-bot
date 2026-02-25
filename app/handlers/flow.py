"""Аренда, продажа, выбор параметров."""
from aiogram import Router, F
from aiogram.types import Message

from app.keyboards import main_kb, mode_kb, rooms_kb, district_kb, search_kb
from app.database.repositories import UserRepository
from app.services.parser import KrishaParser
from app.services.queue import SendQueue

router = Router()

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

ROOM_MAP = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣+": 5}





@router.message(F.text.in_(list(ROOM_MAP)))
async def rooms_select(
    message: Message,
    user_repo: UserRepository,
    config,
):
    rooms = ROOM_MAP[message.text]
    await user_repo.set_rooms(message.from_user.id, rooms)
    await message.answer("Выберите район:", reply_markup=district_kb())


@router.message(F.text.in_(list(DISTRICT_MAP)))
async def district_select(
    message: Message,
    user_repo: UserRepository,
    config,
):
    u = await user_repo.get(message.from_user.id)
    if not u:
        return
    district = message.text
    await user_repo.set_district(message.from_user.id, district)
    await user_repo.set_notifications(message.from_user.id, True)

    mode = u.get("mode") or "rent"
    rooms = u.get("rooms") or 1

    await message.answer(
        "🔎 Поиск настроен. Отправляю первую страницу...",
        reply_markup=search_kb(),
    )

    parser = KrishaParser(config)
    slug = DISTRICT_MAP[district]
    listings = await parser.parse(mode, rooms, slug, u.get("from_owner") or False)

    from app.database.connection import get_pool
    from app.database.repositories import SentListingsRepository

    pool = await get_pool()
    sent_repo = SentListingsRepository(pool)

    for i, ls in enumerate(listings[:10]):
        if await sent_repo.was_sent(message.from_user.id, ls.id):
            continue
        text = f"🏠 {ls.title}\n💰 {ls.price}\n🔗 {ls.url}"
        await message.answer(text)
        await sent_repo.mark_sent(message.from_user.id, ls.id)


@router.message(F.text == "⬅ Назад")
async def back(
    message: Message,
    user_repo: UserRepository,
):
    u = await user_repo.get(message.from_user.id)
    if not u:
        await message.answer("Выберите режим:", reply_markup=mode_kb())
        return

    if u.get("district"):
        await user_repo.set_district(message.from_user.id, None)
        await message.answer("Выберите район:", reply_markup=district_kb())
        return
    if u.get("rooms"):
        await user_repo.set_rooms(message.from_user.id, 1)
        await message.answer("Выберите количество комнат:", reply_markup=rooms_kb())
        return
    await message.answer("Выберите режим:", reply_markup=mode_kb())


@router.message(F.text == "⛔ Стоп")
async def stop_notifications(
    message: Message,
    user_repo: UserRepository,
):
    await user_repo.set_notifications(message.from_user.id, False)
    await message.answer("❌ Уведомления остановлены.", reply_markup=main_kb())


@router.message(F.text == "▶ Запустить уведомления")
async def start_notifications(
    message: Message,
    user_repo: UserRepository,
):
    u = await user_repo.get(message.from_user.id)
    if not u or not u.get("district"):
        await message.answer("Сначала выберите режим и район.")
        return
    await user_repo.set_notifications(message.from_user.id, True)
    await message.answer("✅ Уведомления включены.")


@router.message(F.text == "⚙ Изменить параметры")
async def change_params(
    message: Message,
    user_repo: UserRepository,
):
    await user_repo.set_district(message.from_user.id, None)
    await user_repo.set_rooms(message.from_user.id, 1)
    await message.answer("Выберите режим:", reply_markup=mode_kb())
