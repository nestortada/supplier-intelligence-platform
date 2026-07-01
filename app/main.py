import asyncio

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import Base, engine
from app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.core.product_schema import ensure_product_selection_schema
from app.core.profiles import ensure_profile_schema
from app.core.security import RateLimitMiddleware, RequestLoggingMiddleware
from app.core.sync_schema import ensure_sync_schema
from app.core import sync_events as sync_events
from app.core.database import SessionLocal
from app.models import (
    amazon_data,
    analysis,
    background_job,
    email_campaign,
    product,
    supplier,
    user_profile,
)
from app.routers import catalogs, dashboard, emails, exports, jobs, products, profiles, realtime, settings as settings_router, suppliers, sync, webhooks
from app.services.sync_service import SyncService


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_profile_schema(engine)
    ensure_product_selection_schema(engine)
    ensure_sync_schema(engine)


create_tables()

app = FastAPI(title=settings.APP_NAME)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(suppliers.router)
app.include_router(emails.router)
app.include_router(catalogs.router)
app.include_router(products.router)
app.include_router(jobs.router)
app.include_router(exports.router)
app.include_router(settings_router.router)
app.include_router(dashboard.router)
app.include_router(profiles.router)
app.include_router(sync.router)
app.include_router(realtime.router)
app.include_router(webhooks.router)


async def periodic_sync_loop() -> None:
    while settings.FIREBASE_ENABLED:
        db = SessionLocal()
        try:
            SyncService(db).run_once()
        finally:
            db.close()
        await asyncio.sleep(max(settings.FIREBASE_SYNC_INTERVAL_SECONDS, 5))


@app.on_event("startup")
async def start_periodic_sync() -> None:
    if settings.FIREBASE_ENABLED:
        asyncio.create_task(periodic_sync_loop())


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}
