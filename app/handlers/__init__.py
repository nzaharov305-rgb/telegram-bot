from aiogram import Router

from .start import router as start_router
from .flow import router as flow_router
from .subscription import router as subscription_router
from .stats import router as stats_router
from .admin import router as admin_router


def setup_routers() -> Router:
    root = Router()

    root.include_router(start_router)
    root.include_router(flow_router)
    root.include_router(subscription_router)
    root.include_router(stats_router)
    root.include_router(admin_router)

    return root
