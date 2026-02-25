"""Репозитории для работы с БД."""
from datetime import datetime, date, timedelta
from typing import Sequence

import asyncpg

from app.config import Config

# --- Users ---


class UserRepository:
    def __init__(self, pool: asyncpg.Pool, config: Config):
        self._pool = pool
        self._config = config

    async def get_or_create(self, user_id: int, username: str | None = None) -> dict | None:
        row = await self._pool.fetchrow(
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

    async def get(self, user_id: int) -> dict | None:
        row = await self._pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None

    async def accept_terms(self, user_id: int) -> None:
        await self._pool.execute(
            "UPDATE users SET accepted_terms = TRUE WHERE user_id = $1",
            user_id,
        )

    async def start_trial(self, user_id: int) -> None:
        until = datetime.utcnow() + timedelta(hours=self._config.TRIAL_HOURS)
        await self._pool.execute(
            """
            UPDATE users SET trial_used = TRUE, trial_until = $1
            WHERE user_id = $2 AND trial_used = FALSE
            """,
            until,
            user_id,
        )

    async def set_mode(self, user_id: int, mode: str) -> None:
        await self._pool.execute(
            "UPDATE users SET mode = $1 WHERE user_id = $2",
            mode,
            user_id,
        )

    async def set_rooms(self, user_id: int, rooms: int | None) -> None:
        await self._pool.execute(
            "UPDATE users SET rooms = $1 WHERE user_id = $2",
            rooms,
            user_id,
        )

    async def set_district(self, user_id: int, district: str | None) -> None:
        await self._pool.execute(
            "UPDATE users SET district = $1 WHERE user_id = $2",
            district,
            user_id,
        )

    async def set_districts(self, user_id: int, districts: list[str]) -> None:
        await self._pool.execute(
            "UPDATE users SET districts = $1 WHERE user_id = $2",
            districts,
            user_id,
        )

    async def set_from_owner(self, user_id: int, value: bool) -> None:
        await self._pool.execute(
            "UPDATE users SET from_owner = $1 WHERE user_id = $2",
            value,
            user_id,
        )

    async def set_notifications(self, user_id: int, enabled: bool) -> None:
        await self._pool.execute(
            "UPDATE users SET notifications_enabled = $1 WHERE user_id = $2",
            enabled,
            user_id,
        )

    async def upgrade_subscription(self, user_id: int, plan: str, days: int = 30) -> None:
        until = datetime.utcnow() + timedelta(days=days)
        await self._pool.execute(
            """
            UPDATE users SET subscription_type = $1, subscription_until = $2
            WHERE user_id = $3
            """,
            plan,
            until,
            user_id,
        )

    async def get_active_users_by_tier(self, tier: str) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT * FROM users
            WHERE subscription_type = $1 AND notifications_enabled = TRUE
            AND (subscription_until IS NULL OR subscription_until > NOW())
            AND (trial_until IS NULL OR trial_until > NOW())
            AND district IS NOT NULL
            """,
            tier,
        )
        return [dict(r) for r in rows]

    async def get_active_free_users(self) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT * FROM users
            WHERE subscription_type = 'free' AND notifications_enabled = TRUE
            AND (trial_until IS NULL OR trial_until > NOW())
            AND district IS NOT NULL
            """
        )
        return [dict(r) for r in rows]

    async def get_active_paid_users(self) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT * FROM users
            WHERE subscription_type IN ('standard', 'pro') AND notifications_enabled = TRUE
            AND subscription_until > NOW()
            AND district IS NOT NULL
            """
        )
        return [dict(r) for r in rows]

    def is_subscription_active(self, user: dict) -> bool:
        if user.get("subscription_type") in ("standard", "pro"):
            until = user.get("subscription_until")
            return until and until > datetime.utcnow()
        if user.get("trial_until"):
            return user["trial_until"] > datetime.utcnow()
        return False


# --- Sent Listings ---


class SentListingsRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def was_sent(self, user_id: int, listing_id: str) -> bool:
        row = await self._pool.fetchrow(
            "SELECT 1 FROM sent_listings WHERE user_id = $1 AND listing_id = $2",
            user_id,
            listing_id,
        )
        return row is not None

    async def mark_sent(self, user_id: int, listing_id: str) -> None:
        await self._pool.execute(
            """
            INSERT INTO sent_listings (user_id, listing_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, listing_id) DO NOTHING
            """,
            user_id,
            listing_id,
        )

    async def count_sent_today(self, user_id: int) -> int:
        row = await self._pool.fetchrow(
            """
            SELECT COUNT(*) FROM sent_listings
            WHERE user_id = $1 AND sent_at > NOW() - INTERVAL '24 hours'
            """,
            user_id,
        )
        return row[0] or 0


# --- Stats ---


class StatsRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def increment_new_users(self) -> None:
        today = date.today()
        await self._pool.execute(
            """
            INSERT INTO stats (date, new_users)
            VALUES ($1, 1)
            ON CONFLICT (date) DO UPDATE SET
                new_users = stats.new_users + 1
            """,
            today,
        )

    async def increment_messages_sent(self, count: int = 1) -> None:
        today = date.today()
        await self._pool.execute(
            """
            INSERT INTO stats (date, messages_sent)
            VALUES ($1, $2)
            ON CONFLICT (date) DO UPDATE SET
                messages_sent = stats.messages_sent + EXCLUDED.messages_sent
            """,
            today,
            count,
        )

    async def get_today_stats(self) -> dict:
        row = await self._pool.fetchrow(
            "SELECT * FROM stats WHERE date = $1",
            date.today(),
        )
        return dict(row) if row else {}

    async def get_user_stats(self, user_id: int) -> dict:
        total_sent = await self._pool.fetchval(
            "SELECT COUNT(*) FROM sent_listings WHERE user_id = $1",
            user_id,
        )
        return {"total_sent": total_sent or 0}

    async def get_global_stats(self) -> dict:
        users_total = await self._pool.fetchval("SELECT COUNT(*) FROM users")
        active_subs = await self._pool.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE subscription_type IN ('standard', 'pro') AND subscription_until > NOW()
            """
        )
        new_today = await self._pool.fetchval(
            "SELECT COALESCE(new_users, 0) FROM stats WHERE date = CURRENT_DATE"
        ) or 0
        msg_sent = await self._pool.fetchval(
            "SELECT COALESCE(SUM(messages_sent), 0) FROM stats"
        ) or 0
        return {
            "users_total": users_total or 0,
            "active_subs": active_subs or 0,
            "new_today": new_today,
            "messages_sent": msg_sent,
        }

    async def get_admin_stats(self, pool: asyncpg.Pool) -> dict:
        users_total = await pool.fetchval("SELECT COUNT(*) FROM users")
        free = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE subscription_type = 'free'"
        )
        standard = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE subscription_type = 'standard'"
        )
        pro = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE subscription_type = 'pro'"
        )
        active_subs = await pool.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE subscription_type IN ('standard', 'pro') AND subscription_until > NOW()
            """
        )
        active_today = await pool.fetchval(
            """
            SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours'
            """
        )
        msg_sent = await pool.fetchval(
            "SELECT COALESCE(SUM(messages_sent), 0) FROM stats"
        )
        cfg = Config.from_env()
        revenue = (standard or 0) * cfg.PRICE_STANDARD + (pro or 0) * cfg.PRICE_PRO
        return {
            "users_total": users_total or 0,
            "free": free or 0,
            "standard": standard or 0,
            "pro": pro or 0,
            "active_subs": active_subs or 0,
            "active_today": active_today or 0,
            "messages_sent": msg_sent or 0,
            "revenue": revenue,
        }
