from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(status_code: int, error: str, details: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error,
            "details": details,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        error = str(detail.get("error") or "Request error")
        details = detail.get("details")
    else:
        error = str(detail)
        details = None
    return error_response(exc.status_code, error, details)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, "Validation error", str(exc.errors()))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "Internal server error", "An unexpected error occurred.")
