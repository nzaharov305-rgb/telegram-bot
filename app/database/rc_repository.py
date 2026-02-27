"""Residential Complex repository functions."""
import asyncpg


async def get_active_complexes(
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


async def get_user_selected_complexes(pool: asyncpg.Pool, user_id: int) -> list[int]:
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


async def add_user_complex(pool: asyncpg.Pool, user_id: int, complex_id: int) -> None:
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


async def remove_user_complex(pool: asyncpg.Pool, user_id: int, complex_id: int) -> None:
    """Remove complex from PRO user's selection."""
    await pool.execute(
        """
        DELETE FROM user_residential_complexes
        WHERE user_id = $1 AND complex_id = $2
        """,
        user_id,
        complex_id,
    )


async def clear_user_complexes(pool: asyncpg.Pool, user_id: int) -> None:
    """Clear all complexes for PRO user."""
    await pool.execute(
        "DELETE FROM user_residential_complexes WHERE user_id = $1",
        user_id,
    )


async def set_standard_complex(
    pool: asyncpg.Pool, user_id: int, complex_name: str | None
) -> None:
    """Set single complex for STANDARD user."""
    await pool.execute(
        "UPDATE users SET residential_complex = $1 WHERE user_id = $2",
        complex_name,
        user_id,
    )


async def get_standard_complex(pool: asyncpg.Pool, user_id: int) -> str | None:
    """Get single complex for STANDARD user."""
    row = await pool.fetchrow(
        "SELECT residential_complex FROM users WHERE user_id = $1",
        user_id,
    )
    return row["residential_complex"] if row else None


async def count_user_complexes(pool: asyncpg.Pool, user_id: int) -> int:
    """Count complexes selected by PRO user."""
    row = await pool.fetchrow(
        "SELECT COUNT(*) FROM user_residential_complexes WHERE user_id = $1",
        user_id,
    )
    return row[0] if row else 0
