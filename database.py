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
                residential_complex TEXT,
                subscription_type TEXT DEFAULT 'free',
                subscription_until TIMESTAMPTZ,
                trial_used BOOLEAN DEFAULT FALSE,
                trial_until TIMESTAMPTZ,
                accepted_terms BOOLEAN DEFAULT FALSE,
                notifications_enabled BOOLEAN DEFAULT TRUE,
                from_owner BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS residential_complexes (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS user_residential_complexes (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                complex_id INTEGER NOT NULL REFERENCES residential_complexes(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, complex_id)
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
            CREATE INDEX IF NOT EXISTS idx_rc_category ON residential_complexes(category);
            CREATE INDEX IF NOT EXISTS idx_rc_active ON residential_complexes(is_active);
            CREATE INDEX IF NOT EXISTS idx_user_rc_user ON user_residential_complexes(user_id);
        """)
        
        # Insert residential complexes if not exists
        await conn.execute("""
            INSERT INTO residential_complexes (name, category, priority, is_active)
            VALUES
                ('Esentai City', 'premium', 10, TRUE),
                ('Four Seasons', 'premium', 10, TRUE),
                ('Rams City', 'premium', 10, TRUE),
                ('Medeu Park', 'premium', 10, TRUE),
                ('Dostyk Residence', 'premium', 10, TRUE),
                ('Koktobe City', 'premium', 10, TRUE),
                ('Remizovka Hills', 'premium', 10, TRUE),
                ('Terracotta', 'premium', 10, TRUE),
                ('Orion', 'premium', 10, TRUE),
                ('Prime Park', 'premium', 10, TRUE),
                ('Комфорт Сити', 'business', 5, TRUE),
                ('Хан Тенгри', 'business', 5, TRUE),
                ('Асыл Тау', 'business', 5, TRUE),
                ('Нурлы Тау', 'business', 5, TRUE),
                ('Alma City', 'business', 5, TRUE),
                ('Шахристан', 'business', 5, TRUE),
                ('Аккент', 'business', 5, TRUE),
                ('Mega Towers', 'business', 5, TRUE),
                ('City Plus', 'business', 5, TRUE),
                ('Sensata City', 'business', 5, TRUE),
                ('Алтын Булак', 'comfort', 1, TRUE),
                ('Орбита', 'comfort', 1, TRUE),
                ('Таугуль', 'comfort', 1, TRUE),
                ('Аксай', 'comfort', 1, TRUE),
                ('Жетысу', 'comfort', 1, TRUE),
                ('Алмагуль', 'comfort', 1, TRUE),
                ('Коктем', 'comfort', 1, TRUE),
                ('Айгерим', 'comfort', 1, TRUE),
                ('Сайран', 'comfort', 1, TRUE),
                ('Шугыла', 'comfort', 1, TRUE)
            ON CONFLICT (name) DO NOTHING
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


# --- Residential Complexes ---


async def rc_get_active_complexes(
    pool: asyncpg.Pool, category: str | None = None
) -> list[dict]:
    """Fetch active residential complexes, optionally filtered by category."""
    if category:
        rows = await pool.fetch(
            """
            SELECT id, name, category, priority
            FROM residential_complexes
            WHERE is_active = TRUE AND category = $1
            ORDER BY priority DESC, name ASC
            """,
            category,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, name, category, priority
            FROM residential_complexes
            WHERE is_active = TRUE
            ORDER BY priority DESC, name ASC
            """
        )
    return [dict(r) for r in rows]


async def rc_get_user_selected_complexes(pool: asyncpg.Pool, user_id: int) -> list[int]:
    """Get list of complex IDs selected by PRO user."""
    rows = await pool.fetch(
        """
        SELECT complex_id
        FROM user_residential_complexes
        WHERE user_id = $1
        ORDER BY created_at
        """,
        user_id,
    )
    return [r["complex_id"] for r in rows]


async def rc_add_user_complex(pool: asyncpg.Pool, user_id: int, complex_id: int) -> None:
    """Add complex to PRO user's selection."""
    await pool.execute(
        """
        INSERT INTO user_residential_complexes (user_id, complex_id)
        VALUES ($1, $2)
        ON CONFLICT (user_id, complex_id) DO NOTHING
        """,
        user_id,
        complex_id,
    )


async def rc_remove_user_complex(pool: asyncpg.Pool, user_id: int, complex_id: int) -> None:
    """Remove complex from PRO user's selection."""
    await pool.execute(
        """
        DELETE FROM user_residential_complexes
        WHERE user_id = $1 AND complex_id = $2
        """,
        user_id,
        complex_id,
    )


async def rc_clear_user_complexes(pool: asyncpg.Pool, user_id: int) -> None:
    """Clear all complexes for PRO user."""
    await pool.execute(
        "DELETE FROM user_residential_complexes WHERE user_id = $1",
        user_id,
    )


async def rc_set_standard_complex(
    pool: asyncpg.Pool, user_id: int, complex_name: str | None
) -> None:
    """Set single complex for STANDARD user."""
    await pool.execute(
        "UPDATE users SET residential_complex = $1 WHERE user_id = $2",
        complex_name,
        user_id,
    )


async def rc_get_standard_complex(pool: asyncpg.Pool, user_id: int) -> str | None:
    """Get single complex for STANDARD user."""
    row = await pool.fetchrow(
        "SELECT residential_complex FROM users WHERE user_id = $1",
        user_id,
    )
    return row["residential_complex"] if row else None


async def rc_count_user_complexes(pool: asyncpg.Pool, user_id: int) -> int:
    """Count complexes selected by PRO user."""
    row = await pool.fetchrow(
        "SELECT COUNT(*) FROM user_residential_complexes WHERE user_id = $1",
        user_id,
    )
    return row[0] if row else 0
