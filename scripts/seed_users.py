"""Seed a batch of users (admins by default) with random details.

Usage (inside the Docker backend container):
    docker compose exec backend poetry run python -m scripts.seed_users
    docker compose exec backend poetry run python -m scripts.seed_users --count 8
    docker compose exec backend poetry run python -m scripts.seed_users --role user
    docker compose exec backend poetry run python -m scripts.seed_users --reset

Or from the host (with the backend's .env loaded):
    cd ct-backend && poetry run python -m scripts.seed_users

Role defaults to 'admin' — use --role user to seed regular accounts.

Each seeded user gets:
    email:    <prefix><N>@example.com  ('admin' for admins, 'test' for users)
    password: Password123!             (same for every seeded user)
    name:     "<First> <Last>"         (random)
    is_admin: True for admins, False for users

The script ensures <prefix>1..<prefix><N> exist — existing emails are skipped,
so it is safe to re-run. Use --reset to wipe prior seeds of the chosen role
before creating new ones.
"""
from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass

from loguru import logger

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


FIRST_NAMES = [
    "Ava", "Noah", "Mia", "Liam", "Zara", "Eli", "Priya", "Kai",
    "Rhea", "Arjun", "Ivy", "Leo", "Sana", "Theo", "Nora", "Raj",
    "Luna", "Dev", "Aarya", "Finn",
]
LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Chen", "Nguyen", "Garcia", "Smith",
    "Jones", "Okafor", "Kovacs", "Fischer", "Rossi", "Park", "Silva",
    "Khan", "Reyes", "Tanaka", "Adebayo",
]

DEFAULT_PASSWORD = "Password123!"
ROLE_CHOICES = ("admin", "user")
# Prateek: Prefix controls the deterministic email (admin1@… vs test1@…) AND
# the LIKE pattern used by --reset. Kept as a single source of truth.
ROLE_EMAIL_PREFIX = {"admin": "admin", "user": "test"}


@dataclass
class SeededUser:
    name: str
    email: str
    password: str
    is_admin: bool
    created: bool  # Prateek: False when skipped (email already existed).


def _random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _email_for(index: int, role: str) -> str:
    return f"{ROLE_EMAIL_PREFIX[role]}{index}@example.com"


def _upsert_one(db, *, index: int, role: str, password: str) -> SeededUser:
    is_admin = role == "admin"
    email = _email_for(index, role)
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        return SeededUser(
            name=existing.name,
            email=existing.email,
            password=password,
            is_admin=existing.is_admin,
            created=False,
        )
    name = _random_name()
    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return SeededUser(
        name=name, email=email, password=password, is_admin=is_admin, created=True
    )


def seed(
    *,
    count: int,
    role: str = "admin",
    password: str = DEFAULT_PASSWORD,
    reset: bool = False,
) -> list[SeededUser]:
    if role not in ROLE_CHOICES:
        raise ValueError(f"role must be one of {ROLE_CHOICES}, got {role!r}")

    results: list[SeededUser] = []
    db = SessionLocal()
    try:
        if reset:
            like_pattern = f"{ROLE_EMAIL_PREFIX[role]}%@example.com"
            deleted = (
                db.query(User)
                .filter(User.email.like(like_pattern))
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info(
                "Removed previously seeded users", role=role, count=deleted
            )

        for i in range(1, count + 1):
            results.append(
                _upsert_one(db, index=i, role=role, password=password)
            )
    finally:
        db.close()
    return results


def _print_table(rows: list[SeededUser]) -> None:
    if not rows:
        print("No users created.")
        return
    print()
    print(f"{'ROLE':<7} {'STATUS':<8} {'NAME':<22} {'EMAIL':<32} PASSWORD")
    print("-" * 90)
    for r in rows:
        role = "admin" if r.is_admin else "user"
        status = "created" if r.created else "exists"
        print(f"{role:<7} {status:<8} {r.name:<22} {r.email:<32} {r.password}")
    created = sum(1 for r in rows if r.created)
    skipped = len(rows) - created
    print()
    print(
        f"Created {created} user(s), skipped {skipped} existing. "
        f"All share password: {rows[0].password}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo users into the DB.")
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Users to create (default: 5)",
    )
    parser.add_argument(
        "--role",
        choices=ROLE_CHOICES,
        default="admin",
        help="Role of seeded users (default: admin)",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Password for every seeded user (default: {DEFAULT_PASSWORD})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Delete previously seeded rows of the chosen role "
            "(admin%%@example.com or test%%@example.com) before creating new ones."
        ),
    )
    args = parser.parse_args()

    if args.count < 0:
        parser.error("--count must be non-negative")
    if args.count == 0 and not args.reset:
        parser.error("Nothing to do — set --count > 0")

    rows = seed(
        count=args.count,
        role=args.role,
        password=args.password,
        reset=args.reset,
    )
    _print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
