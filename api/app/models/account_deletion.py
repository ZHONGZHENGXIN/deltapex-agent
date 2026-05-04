from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import JSON, Field, SQLModel


class AccountDeletionAudit(SQLModel, table=True):
    __tablename__ = "account_deletion_audits"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="Deleted local user id")
    actor_user_id: int = Field(index=True, description="Actor local user id")
    actor_type: str = Field(default="self", description="Deletion actor type")
    status: str = Field(default="completed", index=True, description="completed or failed")
    reason: Optional[str] = Field(default=None, description="Optional user supplied reason")
    scope: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON, description="Deletion scope")
    result: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON, description="Deletion result summary")
    error_message: Optional[str] = Field(default=None, description="Failure reason when status is failed")
    requested_at: datetime = Field(default_factory=datetime.utcnow, description="Request time")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
