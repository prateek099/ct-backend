import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import users
from app.core.config import settings
from app.core.database import Base, engine

# ── debugpy (only in local dev) ─────────────────────────────────────────────
if os.getenv("DEBUG", "false").lower() == "true":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("⏳ debugpy listening on port 5678 — attach VS Code debugger")

# ── DB bootstrap ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
