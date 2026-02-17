from app.routes.auth import router as auth_router
from app.routes.user import router as user_router

__all__ = ["auth_router", "user_router"]