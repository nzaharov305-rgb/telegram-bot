"""Production-ready Krisha Monitor SaaS Bot. Railway: TOKEN, DATABASE_URL."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

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

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Middleware
    dp.update.middleware(DatabaseMiddleware(config))
    dp.update.middleware(SubscriptionMiddleware())

    # Routers
    dp.include_router(setup_routers())

    # Init database (один раз!)
    await init_db(config.DATABASE_URL)
    logger.info("Database initialized")

    # Background monitor
    monitor_task = asyncio.create_task(run_monitor(bot, config))
    logger.info("Monitor started")

    # Clean webhook (если вдруг был)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        # Останавливаем монитор и корректно закрываем БД/бота
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        await close_db()
        await bot.session.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
