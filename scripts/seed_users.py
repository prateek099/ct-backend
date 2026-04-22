"""Seed a batch of regular + admin users with random details.

Usage (inside the Docker backend container):
    docker compose exec backend poetry run python -m scripts.seed_users
    docker compose exec backend poetry run python -m scripts.seed_users --users 8 --admins 3
    docker compose exec backend poetry run python -m scripts.seed_users --reset

Or from the host (with the backend's .env loaded):
    cd ct-backend && poetry run python -m scripts.seed_users

Each created user gets:
    email:    test<N>@example.com   (regular)   or   admin<N>@example.com (admin)
    password: Password123!          (same for every seeded user)
    name:     "<First> <Last>"      (random)
    is_admin: True for admins, False otherwise

The script ensures test1..testN / admin1..adminN exist — existing emails are
skipped, so it is safe to re-run. Use --reset to wipe prior seeds first.
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


@dataclass
class SeededUser:
    name: str
    email: str
    password: str
    is_admin: bool
    created: bool  # Prateek: False when skipped (email already existed).


def _random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _email_for(index: int, *, admin: bool) -> str:
    prefix = "admin" if admin else "test"
    return f"{prefix}{index}@example.com"


def _upsert_one(db, *, index: int, is_admin: bool, password: str) -> SeededUser:
    email = _email_for(index, admin=is_admin)
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
    users: int,
    admins: int,
    password: str = DEFAULT_PASSWORD,
    reset: bool = False,
) -> list[SeededUser]:
    results: list[SeededUser] = []
    db = SessionLocal()
    try:
        if reset:
            deleted = (
                db.query(User)
                .filter(
                    User.email.like("test%@example.com")
                    | User.email.like("admin%@example.com")
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info("Removed previously seeded users", count=deleted)

        for i in range(1, users + 1):
            results.append(_upsert_one(db, index=i, is_admin=False, password=password))
        for i in range(1, admins + 1):
            results.append(_upsert_one(db, index=i, is_admin=True, password=password))
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
    parser.add_argument("--users", type=int, default=5, help="Regular users to create (default: 5)")
    parser.add_argument("--admins", type=int, default=2, help="Admin users to create (default: 2)")
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Password for every seeded user (default: {DEFAULT_PASSWORD})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete previously seeded *@example.com users before creating new ones.",
    )
    args = parser.parse_args()

    if args.users < 0 or args.admins < 0:
        parser.error("--users and --admins must be non-negative")
    if args.users + args.admins == 0 and not args.reset:
        parser.error("Nothing to do — set --users and/or --admins > 0")

    rows = seed(
        users=args.users,
        admins=args.admins,
        password=args.password,
        reset=args.reset,
    )
    _print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
