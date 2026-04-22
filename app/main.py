"""FastAPI app factory — wires middleware, routes, logging, and exception handlers."""
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import auth, users, login, projects, video_idea_gen, script_generator, title_suggestor, seo_description
from app.api.routes import youtube as yt
from app.core.config import settings, check_optional_settings
import app.models  # noqa: F401 — registers all models with Base.metadata
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware

# ── debugpy (only in local dev) ─────────────────────────────────────────────
if os.getenv("DEBUG", "false").lower() == "true":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⏳ debugpy listening on port 5678 — attach VS Code debugger")

# ── Logging — must be first ──────────────────────────────────────────────────
setup_logging()
check_optional_settings()

# ── DB bootstrap ─────────────────────────────────────────────────────────────
# Prateek: Schema is managed by Alembic — run `alembic upgrade head` before starting
# the server (handled by the Docker entrypoint). Tests still use create_all() via
# tests/conftest.py.

# ── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,   # hide docs in prod
    redoc_url="/redoc" if settings.debug else None,
)

# ── Rate limiter state ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware (applied in reverse order — last added = outermost) ────────────
app.add_middleware(RequestLoggingMiddleware)   # 3rd — log after IDs assigned
app.add_middleware(TimingMiddleware)           # 2nd — time after ID assigned
app.add_middleware(RequestIDMiddleware)        # 1st — assign request ID first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(login.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(video_idea_gen.router, prefix="/api/v1")
app.include_router(script_generator.router, prefix="/api/v1")
app.include_router(title_suggestor.router, prefix="/api/v1")
app.include_router(seo_description.router, prefix="/api/v1")
app.include_router(yt.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}
