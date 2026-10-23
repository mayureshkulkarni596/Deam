import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.kiosk import router as kiosk_router
from app.api.requests import router as requests_router
from app.api.visitors import router as visitors_router
from app.api.ws import router as ws_router
from app.config import get_settings
from app.db import SessionLocal, engine
from app.logging_config import configure_logging
from app.services.cleanup import expire_pending_requests

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


async def _expiry_loop():
    while True:
        try:
            with SessionLocal() as db:
                expire_pending_requests(db)
        except Exception:
            logger.exception("Pending request expiry sweep failed")
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup env=%s gate_mode=%s", settings.app_env, settings.gate_mode)
    expiry_task = asyncio.create_task(_expiry_loop())
    try:
        yield
    finally:
        expiry_task.cancel()
        try:
            await expiry_task
        except asyncio.CancelledError:
            pass
        engine.dispose()
        logger.info("Application shutdown")


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Local-first gate backend. Phase 1 core visitor workflow; hardware remains mock-only.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Kiosk-Key"],
)
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(visitors_router, prefix=settings.api_v1_prefix)
app.include_router(requests_router, prefix=settings.api_v1_prefix)
app.include_router(kiosk_router, prefix=settings.api_v1_prefix)
app.include_router(ws_router)


@app.get("/", include_in_schema=False)
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/health"}
