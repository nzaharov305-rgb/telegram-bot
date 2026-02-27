"""Admin utility functions and queries."""
import asyncpg
from datetime import datetime, timedelta


async def get_user_stats(pool: asyncpg.Pool) -> dict:
    """Get comprehensive user statistics."""
    users_total = await pool.fetchval("SELECT COUNT(*) FROM users") or 0
    
    free = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type = 'free'"
    ) or 0
    
    standard = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type = 'standard'"
    ) or 0
    
    pro = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE subscription_type = 'pro'"
    ) or 0
    
    active_subs = await pool.fetchval(
        """
        SELECT COUNT(*) FROM users
        WHERE subscription_type IN ('standard', 'pro') 
        AND subscription_until > NOW()
        """
    ) or 0
    
    users_today = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours'"
    ) or 0
    
    return {
        "total": users_total,
        "free": free,
        "standard": standard,
        "pro": pro,
        "active_subs": active_subs,
        "new_today": users_today,
    }


async def get_rc_stats(pool: asyncpg.Pool) -> dict:
    """Get residential complex statistics."""
    total_selections = await pool.fetchval(
        "SELECT COUNT(*) FROM user_residential_complexes"
    ) or 0
    
    total_complexes = await pool.fetchval(
        "SELECT COUNT(*) FROM residential_complexes WHERE is_active = TRUE"
    ) or 0
    
    top_complexes = await pool.fetch(
        """
        SELECT rc.name, rc.category, COUNT(urc.user_id) as users_count
        FROM user_residential_complexes urc
        JOIN residential_complexes rc ON rc.id = urc.complex_id
        GROUP BY rc.id, rc.name, rc.category
        ORDER BY users_count DESC
        LIMIT 5
        """
    )
    
    return {
        "total_selections": total_selections,
        "total_complexes": total_complexes,
        "top_complexes": [dict(r) for r in top_complexes],
    }


async def get_broadcast_targets(
    pool: asyncpg.Pool,
    target: str = "all"
) -> list[int]:
    """Get list of user IDs for broadcast."""
    if target == "all":
        users = await pool.fetch("SELECT user_id FROM users")
    elif target == "pro":
        users = await pool.fetch(
            """
            SELECT user_id FROM users 
            WHERE subscription_type = 'pro'
            AND subscription_until > NOW()
            """
        )
    elif target == "standard":
        users = await pool.fetch(
            """
            SELECT user_id FROM users 
            WHERE subscription_type = 'standard'
            AND subscription_until > NOW()
            """
        )
    elif target == "free":
        users = await pool.fetch(
            "SELECT user_id FROM users WHERE subscription_type = 'free'"
        )
    elif target == "active":
        users = await pool.fetch(
            "SELECT user_id FROM users WHERE notifications_enabled = TRUE"
        )
    else:
        users = []
    
    return [u["user_id"] for u in users]


async def toggle_rc_status(pool: asyncpg.Pool, rc_id: int) -> bool:
    """Toggle residential complex active status. Returns new status."""
    current = await pool.fetchval(
        "SELECT is_active FROM residential_complexes WHERE id = $1",
        rc_id,
    )
    
    if current is None:
        return False
    
    new_status = not current
    
    await pool.execute(
        "UPDATE residential_complexes SET is_active = $1 WHERE id = $2",
        new_status,
        rc_id,
    )
    
    return new_status


async def change_rc_priority(
    pool: asyncpg.Pool,
    rc_id: int,
    delta: int
) -> int:
    """Change RC priority by delta. Returns new priority."""
    current = await pool.fetchval(
        "SELECT priority FROM residential_complexes WHERE id = $1",
        rc_id,
    )
    
    if current is None:
        return 0
    
    new_priority = max(1, min(10, current + delta))
    
    await pool.execute(
        "UPDATE residential_complexes SET priority = $1 WHERE id = $2",
        new_priority,
        rc_id,
    )
    
    return new_priority


async def get_expiring_subscriptions(
    pool: asyncpg.Pool,
    days: int = 3
) -> list[dict]:
    """Get subscriptions expiring in N days."""
    rows = await pool.fetch(
        """
        SELECT user_id, username, subscription_type, subscription_until
        FROM users
        WHERE subscription_type IN ('standard', 'pro')
        AND subscription_until > NOW()
        AND subscription_until < NOW() + $1::interval
        ORDER BY subscription_until ASC
        """,
        f"{days} days",
    )
    
    return [dict(r) for r in rows]


async def cleanup_expired_subscriptions(pool: asyncpg.Pool) -> int:
    """Downgrade expired subscriptions to free. Returns count."""
    result = await pool.execute(
        """
        UPDATE users
        SET subscription_type = 'free'
        WHERE subscription_type IN ('standard', 'pro')
        AND subscription_until < NOW()
        """
    )
    
    # Extract count from result string like "UPDATE 5"
    count = int(result.split()[-1]) if result else 0
    return count
