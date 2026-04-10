import json
import logging
import sys
from typing import Any

from loguru import logger

from app.core.config import settings


# ── Intercept stdlib logging → loguru ─────────────────────────────────────────
class InterceptHandler(logging.Handler):
    """Route all standard library log records through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ── JSON serialiser for loguru ─────────────────────────────────────────────────
def _json_sink(message: Any) -> None:
    record = message.record
    log_entry = {
        "ts": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "msg": record["message"],
        "file": f"{record['file'].name}:{record['line']}",
    }
    if record["extra"]:
        log_entry["extra"] = record["extra"]
    if record["exception"]:
        log_entry["exception"] = str(record["exception"])
    print(json.dumps(log_entry), flush=True)


def setup_logging() -> None:
    """
    Configure loguru as the single logging sink.
    Called once at application startup (inside app/main.py).
    """
    logger.remove()  # drop loguru's default stderr sink

    if settings.log_format == "json":
        logger.add(_json_sink, level=settings.log_level, enqueue=True)
    else:
        # Pretty coloured output for local dev
        logger.add(
            sys.stdout,
            level=settings.log_level,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
                "<level>{message}</level>"
            ),
            enqueue=True,
        )

    # Route uvicorn / sqlalchemy / fastapi logs through loguru
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine", "fastapi"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    logger.info("Logging configured", format=settings.log_format, level=settings.log_level)
