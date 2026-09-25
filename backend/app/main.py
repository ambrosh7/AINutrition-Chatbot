"""FastAPI application factory."""

from __future__ import annotations

import sys

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.chat import empty_message_http_exception, router as chat_router
from app.api.health import router as health_router
from app.config import get_settings
from app.db.session import init_db

MIN_PYTHON = (3, 11)


def require_python() -> None:
    if sys.version_info < MIN_PYTHON:
        raise SystemExit("Python 3.11+ is required")


def create_app(*, database_url: str | None = None) -> FastAPI:
    require_python()
    init_db(database_url)
    app = FastAPI(
        title="AI Nutrition Assistant",
        version="0.6.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    if database_url is not None:
        app.state.database_url = database_url

    origins = list(get_settings().allowed_origins)
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        mapped = empty_message_http_exception(exc)
        if mapped is not None:
            return JSONResponse(
                status_code=mapped.status_code,
                content={"detail": mapped.detail},
            )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    app.include_router(health_router)
    app.include_router(chat_router)
    return app
