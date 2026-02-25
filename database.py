"""PostgreSQL через asyncpg. Production-ready."""
import asyncpg
from typing import Any

from config import Config

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
        """)


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# --- Repositories ---


async def user_get_or_create(pool: asyncpg.Pool, user_id: int, username: str | None = None) -> dict | None:
    row = await pool.fetchrow(
        """
        INSERT INTO users (user_id, username)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
        RETURNING *
        """,
        user_id,
        username,
    )
    return dict(row) if row else None


async def user_get(pool: asyncpg.Pool, user_id: int) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    return dict(row) if row else None


async def user_accept_terms(pool: asyncpg.Pool, user_id: int) -> None:
    await pool.execute("UPDATE users SET accepted_terms = TRUE WHERE user_id = $1", user_id)


async def user_start_trial(pool: asyncpg.Pool, user_id: int, trial_hours: int) -> None:
    from datetime import datetime, timedelta
    until = datetime.utcnow() + timedelta(hours=trial_hours)
    await pool.execute(
        """
        UPDATE users SET trial_used = TRUE, trial_until = $1
        WHERE user_id = $2 AND trial_used = FALSE
        """,
        until,
        user_id,
    )


async def user_set_mode(pool: asyncpg.Pool, user_id: int, mode: str) -> None:
    await pool.execute("UPDATE users SET mode = $1 WHERE user_id = $2", mode, user_id)


async def user_set_rooms(pool: asyncpg.Pool, user_id: int, rooms: int) -> None:
    await pool.execute("UPDATE users SET rooms = $1 WHERE user_id = $2", rooms, user_id)


async def user_set_district(pool: asyncpg.Pool, user_id: int, district: str | None) -> None:
    await pool.execute("UPDATE users SET district = $1 WHERE user_id = $2", district, user_id)


async def user_set_notifications(pool: asyncpg.Pool, user_id: int, enabled: bool) -> None:
    await pool.execute("UPDATE users SET notifications_enabled = $1 WHERE user_id = $2", enabled, user_id)


async def user_upgrade(pool: asyncpg.Pool, user_id: int, plan: str, days: int = 30) -> None:
    from datetime import datetime, timedelta
    until = datetime.utcnow() + timedelta(days=days)
    await pool.execute(
        "UPDATE users SET subscription_type = $1, subscription_until = $2 WHERE user_id = $3",
        plan,
        until,
        user_id,
    )


async def user_get_active_by_tier(pool: asyncpg.Pool, tier: str) -> list[dict]:
    if tier == "free":
        rows = await pool.fetch(
            """
            SELECT * FROM users
            WHERE subscription_type = 'free' AND notifications_enabled = TRUE
            AND (trial_until IS NULL OR trial_until > NOW())
            AND district IS NOT NULL
            """
        )
    else:
        rows = await pool.fetch(
            """
            SELECT * FROM users
            WHERE subscription_type = $1 AND notifications_enabled = TRUE
            AND subscription_until > NOW() AND district IS NOT NULL
            """,
            tier,
        )
    return [dict(r) for r in rows]


async def sent_was_sent(pool: asyncpg.Pool, user_id: int, listing_id: str) -> bool:
    row = await pool.fetchrow(
        "SELECT 1 FROM sent_listings WHERE user_id = $1 AND listing_id = $2",
        user_id,
        listing_id,
    )
    return row is not None


async def sent_mark(pool: asyncpg.Pool, user_id: int, listing_id: str) -> None:
    await pool.execute(
        """
        INSERT INTO sent_listings (user_id, listing_id)
        VALUES ($1, $2)
        ON CONFLICT (user_id, listing_id) DO NOTHING
        """,
        user_id,
        listing_id,
    )


async def sent_count_today(pool: asyncpg.Pool, user_id: int) -> int:
    row = await pool.fetchrow(
        """
        SELECT COUNT(*) FROM sent_listings
        WHERE user_id = $1 AND sent_at > NOW() - INTERVAL '24 hours'
        """,
        user_id,
    )
    return row[0] or 0


async def stats_increment_messages(pool: asyncpg.Pool, count: int = 1) -> None:
    from datetime import date
    today = date.today()
    await pool.execute(
        """
        INSERT INTO stats (date, messages_sent)
        VALUES ($1, $2)
        ON CONFLICT (date) DO UPDATE SET
            messages_sent = stats.messages_sent + EXCLUDED.messages_sent
        """,
        today,
        count,
    )


async def stats_increment_new_users(pool: asyncpg.Pool) -> None:
    from datetime import date
    today = date.today()
    await pool.execute(
        """
        INSERT INTO stats (date, new_users)
        VALUES ($1, 1)
        ON CONFLICT (date) DO UPDATE SET new_users = stats.new_users + 1
        """,
        today,
    )
