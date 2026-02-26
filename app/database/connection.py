"""PostgreSQL через asyncpg."""
import asyncpg
from typing import AsyncGenerator

from app.config import Config

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        cfg = Config.from_env()
        _pool = await asyncpg.create_pool(
            cfg.DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
    return _pool


async def init_db() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                mode TEXT DEFAULT 'rent',
                rooms INTEGER DEFAULT 1,
                district TEXT,
                districts TEXT[],
                subscription_type TEXT DEFAULT 'free',
                subscription_until TIMESTAMPTZ,
                trial_used BOOLEAN DEFAULT FALSE,
                trial_until TIMESTAMPTZ,
                accepted_terms BOOLEAN DEFAULT FALSE,
                notifications_enabled BOOLEAN DEFAULT TRUE,
                from_owner BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );


            CREATE TABLE IF NOT EXISTS sent_listings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                listing_id TEXT NOT NULL,
                sent_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_sent_listings_unique
                ON sent_listings(user_id, listing_id);

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

            CREATE INDEX IF NOT EXISTS idx_sent_listings_user ON sent_listings(user_id);
            CREATE INDEX IF NOT EXISTS idx_sent_listings_listing ON sent_listings(listing_id);
            CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_type);
            CREATE INDEX IF NOT EXISTS idx_users_active 
                ON users(notifications_enabled) 
                WHERE notifications_enabled = TRUE;
        """)


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
