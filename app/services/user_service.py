"""User CRUD service — raises AppError subclasses, never HTTPException."""
from loguru import logger
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_all_users(db: Session) -> list[User]:
    return db.query(User).all()


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(f"User {user_id} not found.")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, payload: UserCreate) -> User:
    if get_user_by_email(db, payload.email):
        logger.warning("User creation failed: Email already exists", email=payload.email)
        raise ConflictError(f"Email '{payload.email}' is already registered.")
    
    logger.info("Creating new user", email=payload.email, name=payload.name)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        logger.success("User created successfully in database", user_id=user.id, email=user.email)
    except Exception as e:
        db.rollback()
        logger.error("Failed to create user in database", error=str(e))
        raise
    return user


def delete_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)  # raises NotFoundError if missing
    logger.info("Deleting user", user_id=user_id, email=user.email)
    db.delete(user)
    try:
        db.commit()
        logger.success("User deleted successfully", user_id=user_id)
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete user", error=str(e))
        raise
