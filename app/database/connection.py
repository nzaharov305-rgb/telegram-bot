import asyncio
import logging
import ssl
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import asyncpg

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None
_lock = asyncio.Lock()


def _normalize_dsn(dsn: str) -> str:
    if not (dsn.startswith("postgresql://") or dsn.startswith("postgres://")):
        return dsn

    parsed = urlparse(dsn)
    query_params = parse_qs(parsed.query)

    if "sslmode" not in query_params:
        query_params["sslmode"] = ["require"]
        new_query = urlencode(query_params, doseq=True)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        return normalized

    return dsn


async def get_pool(dsn: str) -> asyncpg.Pool:
    global _pool

    if _pool is not None:
        return _pool

    async with _lock:
        if _pool is not None:
            return _pool

        dsn = _normalize_dsn(dsn)
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Database pool: attempt %d/%d",
                    attempt,
                    max_retries,
                )

                ssl_context = None
                if dsn.startswith("postgresql://") or dsn.startswith("postgres://"):
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                _pool = await asyncpg.create_pool(
                    dsn,
                    min_size=2,
                    max_size=10,
                    command_timeout=30,
                    server_settings={
                        "application_name": "krisha_bot",
                        "jit": "off",
                    },
                    ssl=ssl_context,
                )

                async with _pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")

                logger.info("Database pool: connected (min=2, max=10)")
                return _pool

            except (asyncpg.PostgresError, OSError, asyncio.TimeoutError, ConnectionRefusedError) as exc:
                logger.warning(
                    "Database pool: attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    exc.__class__.__name__,
                )

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("Database pool: failed after %d attempts", max_retries)
                    raise RuntimeError(f"Database connection failed after {max_retries} attempts") from exc

        raise RuntimeError("Unexpected code path")


async def init_db(dsn: str) -> None:
    try:
        pool = await get_pool(dsn)
    except RuntimeError as exc:
        logger.error("Database init: aborted: %s", exc)
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
            logger.info("Database schema: initialized")
    except asyncpg.PostgresError as exc:
        logger.error("Database schema: init failed: %s", exc)


async def close_db() -> None:
    global _pool

    if _pool is None:
        return

    try:
        logger.info("Database pool: closing...")
        await asyncio.wait_for(_pool.close(), timeout=5.0)
        logger.info("Database pool: closed")
    except asyncio.TimeoutError:
        logger.warning("Database pool: close timeout")
    except Exception as exc:
        logger.error("Database pool: close error: %s", exc)
    finally:
        _pool = None
