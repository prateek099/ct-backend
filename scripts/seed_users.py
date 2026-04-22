"""Seed a batch of regular + admin users with random details.

Usage (inside the Docker backend container):
    docker compose exec backend poetry run python -m scripts.seed_users
    docker compose exec backend poetry run python -m scripts.seed_users --users 8 --admins 3
    docker compose exec backend poetry run python -m scripts.seed_users --reset

Or from the host (with the backend's .env loaded):
    cd ct-backend && poetry run python -m scripts.seed_users

Each created user gets:
    email:    <slug>+<4chars>@example.com      (unique per run)
    password: Password123!                      (same for every seeded user)
    name:     "<First> <Last>"                  (random)
    is_admin: True for admins, False otherwise

Existing emails are skipped, so the script is safe to re-run.
"""
from __future__ import annotations

import argparse
import random
import secrets
import string
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


def _random_email(name: str, *, admin: bool) -> str:
    slug = name.lower().replace(" ", ".")
    suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    prefix = "admin" if admin else "user"
    return f"{prefix}.{slug}.{suffix}@example.com"


def _create_one(db, *, is_admin: bool, password: str) -> SeededUser:
    name = _random_name()
    email = _random_email(name, admin=is_admin)
    # Prateek: Collision on the random suffix is astronomically unlikely, but
    # still check — unique constraint would raise IntegrityError otherwise.
    while db.query(User).filter(User.email == email).first():
        email = _random_email(name, admin=is_admin)
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
                .filter(User.email.like("user.%@example.com") | User.email.like("admin.%@example.com"))
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info("Removed previously seeded users", count=deleted)

        for _ in range(users):
            results.append(_create_one(db, is_admin=False, password=password))
        for _ in range(admins):
            results.append(_create_one(db, is_admin=True, password=password))
    finally:
        db.close()
    return results


def _print_table(rows: list[SeededUser]) -> None:
    if not rows:
        print("No users created.")
        return
    print()
    print(f"{'ROLE':<7} {'NAME':<22} {'EMAIL':<52} PASSWORD")
    print("-" * 100)
    for r in rows:
        role = "admin" if r.is_admin else "user"
        print(f"{role:<7} {r.name:<22} {r.email:<52} {r.password}")
    print()
    print(f"Created {len(rows)} user(s). All share password: {rows[0].password}")


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
