from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserType(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    username: str = Field(index=True, unique=True, description="Unique username")
    email: str = Field(index=True, unique=True, description="User email")
    supabase_user_id: Optional[str] = Field(default=None, index=True, unique=True, description="Supabase auth user id")
    password_hash: Optional[str] = Field(default=None, description="Legacy local password hash")
    user_type: UserType = Field(default=UserType.USER, description="User role")

    last_login_at: Optional[datetime] = Field(default=None, description="Last login time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Updated at")
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at")
