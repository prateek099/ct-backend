"""Pydantic schemas for user CRUD responses."""
from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    is_admin: bool = False

    model_config = {"from_attributes": True}
