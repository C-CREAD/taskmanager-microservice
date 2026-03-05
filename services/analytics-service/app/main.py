from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.clients.http_client import close_http_client
from app.core.cache import close_redis
from app.core.config import settings
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    print(f"✅  {settings.APP_NAME} started.")
    yield
    # Shutdown
    await close_http_client()
    await close_redis()
    await engine.dispose()
    print("👋  Analytics Service shut down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=settings.API_PREFIX)

    @app.get("/health", include_in_schema=False)
    async def health():
        return {
            "status": "ok",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


app = create_app()
