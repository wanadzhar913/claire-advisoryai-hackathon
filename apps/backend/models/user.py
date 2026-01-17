"""This file contains the user model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

import bcrypt
from sqlmodel import (
    Field,
    Relationship,
)

from backend.models.base import BaseModel

if TYPE_CHECKING:
    from backend.models.goal import Goal
    from backend.models.session import Session
    from backend.models.user_upload import UserUpload


class User(BaseModel, table=True):
    """User model for storing user accounts.

    Attributes:
        id: The primary key
        clerk_id: Clerk user ID (unique identifier from Clerk auth)
        email: User's email (unique)
        hashed_password: Bcrypt hashed password (optional when using Clerk)
        created_at: When the user was created
        sessions: Relationship to user's chat sessions
        uploads: Relationship to user's uploads
        goals: Relationship to user's goals
    """
    __tablename__ = "app_users"

    id: int = Field(default=None, primary_key=True)
    clerk_id: Optional[str] = Field(default=None, unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = Field(default=None)
    sessions: List["Session"] = Relationship(back_populates="user")
    uploads: List["UserUpload"] = Relationship(back_populates="user")
    goals: List["Goal"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Avoid circular imports
from backend.models.goal import Goal  # noqa: E402
from backend.models.session import Session  # noqa: E402
from backend.models.user_upload import UserUpload  # noqa: E402