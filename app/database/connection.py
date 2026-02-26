"""PostgreSQL через asyncpg (Railway)."""

import asyncpg
from typing import Optional
from app.config import Config

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Ленивая инициализация пула через DATABASE_URL из env."""
    global _pool

    if _pool is None:
        config = Config.from_env()

        _pool = await asyncpg.create_pool(
            dsn=config.DATABASE_URL,
            min_size=1,   # важно для Railway
            max_size=5,
            command_timeout=60,
        )

    return _pool


async def init_db() -> None:
    """Создаёт таблицы + добавляет недостающие колонки."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # 1) Базовые таблицы
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                mode TEXT DEFAULT 'rent',
                rooms INTEGER DEFAULT 1,
                district TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS sent_listings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                listing_id TEXT NOT NULL,
                sent_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS payment_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount INTEGER NOT NULL,
                plan TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                confirmed_at TIMESTAMPTZ,
                confirmed_by BIGINT
            );

            CREATE TABLE IF NOT EXISTS stats (
                date DATE PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                messages_sent INTEGER DEFAULT 0
            );
            """
        )

        # 2) Миграции users
        await conn.execute(
            """
            ALTER TABLE users
                ADD COLUMN IF NOT EXISTS districts TEXT[],
                ADD COLUMN IF NOT EXISTS subscription_type TEXT DEFAULT 'free',
                ADD COLUMN IF NOT EXISTS subscription_until TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS trial_used BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS trial_until TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS accepted_terms BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS from_owner BOOLEAN DEFAULT FALSE;
            """
        )

        # 3) Индексы
        await conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sent_listings_unique
                ON sent_listings(user_id, listing_id);

            CREATE INDEX IF NOT EXISTS idx_sent_listings_user
                ON sent_listings(user_id);

            CREATE INDEX IF NOT EXISTS idx_sent_listings_listing
                ON sent_listings(listing_id);

            CREATE INDEX IF NOT EXISTS idx_users_subscription
                ON users(subscription_type);

            CREATE INDEX IF NOT EXISTS idx_users_active
                ON users(notifications_enabled)
                WHERE notifications_enabled = TRUE;
            """
        )


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
