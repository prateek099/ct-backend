"""Run Alembic migrations against the configured database.

Usage (from ct-backend/, with .env loaded):
    poetry run python -m scripts.migrate                      # upgrade to head
    poetry run python -m scripts.migrate --revision 0010      # upgrade to a specific rev
    poetry run python -m scripts.migrate --downgrade -1       # step back one rev
    poetry run python -m scripts.migrate --downgrade 0009     # roll back to a specific rev
    poetry run python -m scripts.migrate --history            # print the full chain
    poetry run python -m scripts.migrate --current            # print the current rev

Inside Docker, the dev and prod entrypoints already run `alembic upgrade head`
before uvicorn starts, so this script is for the bare-metal local flow where
uvicorn runs outside the container.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from loguru import logger

from app.core.config import _mask_db_url, settings


# Prateek: resolve alembic.ini relative to the repo, not the CWD, so the script
# works whether invoked from ct-backend/ or the monorepo root.
ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    # Prateek: env.py reads settings.database_url itself, but set it here too so
    # offline/SQL-mode subcommands (not used today) also see the right URL.
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Alembic migrations locally.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--revision",
        default=None,
        help="Target revision to upgrade to (default: head).",
    )
    group.add_argument(
        "--downgrade",
        default=None,
        help="Revision to downgrade to (e.g. -1, 0009, base).",
    )
    group.add_argument(
        "--history", action="store_true", help="Print the full migration chain."
    )
    group.add_argument(
        "--current", action="store_true", help="Print the current database revision."
    )
    args = parser.parse_args()

    cfg = _alembic_config()
    logger.info("Alembic target DB: {}", _mask_db_url(settings.database_url))

    if args.history:
        command.history(cfg, verbose=True)
        return 0
    if args.current:
        command.current(cfg, verbose=True)
        return 0
    if args.downgrade:
        logger.info("Downgrading to {}", args.downgrade)
        command.downgrade(cfg, args.downgrade)
        return 0

    target = args.revision or "head"
    logger.info("Upgrading to {}", target)
    command.upgrade(cfg, target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
