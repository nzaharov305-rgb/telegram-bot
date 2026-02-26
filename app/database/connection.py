"""PostgreSQL через asyncpg."""
import logging

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool(dsn: str) -> asyncpg.Pool:
    global _pool

    if _pool is None:
        logger.info("Database: attempting to create connection pool")
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        logger.info("Database: connection pool created")
    return _pool


async def init_db(dsn: str) -> None:
    try:
        pool = await get_pool(dsn)
    except Exception as exc:
        logger.error("Database: failed to create connection pool: %s", exc)
        logger.info("Database: init_db skipped (database unreachable)")
        return

    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    username TEXT
                );
            """)
    except Exception as exc:
        logger.error("Database: failed to initialize tables: %s", exc)


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
