"""Production-ready Krisha Monitor SaaS Bot. Railway: TOKEN, DATABASE_URL."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.config import Config
from app.database.connection import init_db, close_db
from app.middleware import DatabaseMiddleware, SubscriptionMiddleware
from app.handlers import setup_routers
from app.services.monitor import run_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = Config.from_env()
    bot = Bot(token=config.TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # attach common middleware
    dp.update.middleware(DatabaseMiddleware(config))
    dp.update.middleware(SubscriptionMiddleware())

    # include all application routers
    dp.include_router(setup_routers())

    await init_db()
    logger.info("Database initialized")

    asyncio.create_task(run_monitor(bot, config))
    logger.info("Monitor started")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    finally:
        asyncio.run(close_db()) 
