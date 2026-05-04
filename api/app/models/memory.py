from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import JSON, Field, SQLModel


class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_student_profiles_user_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="Owner user id")
    risk_preference: Optional[str] = Field(default=None, description="Risk preference")
    trading_style: Optional[str] = Field(default=None, description="Trading style")
    learning_pace: Optional[str] = Field(default=None, description="Learning pace")
    profile_summary: Optional[str] = Field(default=None, description="Long-term student profile summary")
    important_constraints: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_type=JSON,
        description="Important constraints and structured profile facts",
    )
    source_message_id: Optional[int] = Field(default=None, description="First message used to seed the profile")

    is_deleted: bool = Field(default=False, description="Soft delete flag")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Updated at")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at")


class ChatSummary(SQLModel, table=True):
    __tablename__ = "chat_summaries"
    __table_args__ = (
        UniqueConstraint("chat_id", name="uq_chat_summaries_chat_id"),
        Index("ix_chat_summaries_user_chat", "user_id", "chat_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(index=True, description="Internal chat id")
    user_id: int = Field(index=True, description="Owner user id")
    summary_text: str = Field(default="", description="Rolling chat summary")
    summarized_message_count: int = Field(default=0, description="Number of raw messages compressed into summary")
    last_message_id: Optional[int] = Field(default=None, description="Last summarized message id")
    last_summarized_at: Optional[datetime] = Field(default=None, description="Last summary update time")

    is_deleted: bool = Field(default=False, description="Soft delete flag")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Updated at")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at")
