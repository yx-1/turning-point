"""Application entry point.

What this file does:
    Builds the FastAPI application and attaches the routes the browser can call.

What enters:
    HTTP requests from the React app. GET /health checks that the process is up.
    POST /conversation/start, /conversation/message, and /conversation/restart
    run the guided chat.

What happens inside:
    FastAPI matches the URL to a route function. CORS middleware allows the
    Vite dev server (port 5173) to read the JSON response in the browser.

What it returns:
    JSON from the matched route. Health returns a status object. Conversation
    routes return the next assistant replies. GET /users/{user_id} returns a
    profile that was saved after confirmation.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import init_db
from app.routes.conversation import router as conversation_router
from app.routes.health import router as health_router
from app.routes.readings import router as readings_router
from app.routes.users import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create backend/turning_point.db and the tables before requests arrive.
    init_db()
    yield

# Local Vite addresses only. No production host is configured yet.
LOCAL_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(
    title="Turning Point API",
    summary="Local API for the Turning Point astrology chat prototype.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router)
app.include_router(conversation_router)
app.include_router(users_router)
app.include_router(readings_router)

_frontend_dist = Path(os.environ.get("FRONTEND_DIST", ""))
if _frontend_dist.is_dir():
    # The production container serves the built chat from the same origin as the API.
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")


@app.middleware("http")
async def privacy_headers(request: Request, call_next):
    """Stop browsers and proxies from storing responses that contain personal data."""

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def public_validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    """Drop the submitted text from a validation error.

    FastAPI's default body includes an ``input`` field. For this app that
    field can be a birth date or a life-event description.
    """

    cleaned: list[dict[str, object]] = []
    for error in exc.errors():
        location = error.get("loc", ())
        cleaned.append(
            {
                "type": str(error.get("type", "value_error")),
                "loc": list(location),
                "msg": str(error.get("msg", "Invalid value")),
            }
        )
    return cleaned


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": public_validation_errors(exc)})


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    """Turn an unexpected failure into a short JSON message.

    Validation errors and normal HTTP errors keep their original status.
    The message does not include the exception text, so a birth date or
    event description cannot leak into the browser from a stack trace.
    """

    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": public_validation_errors(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong while handling that request. Please try again."},
    )
