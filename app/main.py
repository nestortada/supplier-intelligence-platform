from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import Base, engine
from app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.core.profiles import ensure_profile_schema
from app.core.security import RateLimitMiddleware, RequestLoggingMiddleware
from app.models import (
    amazon_data,
    analysis,
    background_job,
    email_campaign,
    product,
    supplier,
    user_profile,
)
from app.routers import catalogs, dashboard, emails, exports, jobs, products, profiles, settings as settings_router, suppliers


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_profile_schema(engine)


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


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}
