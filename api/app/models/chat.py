from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import JSON, Field, SQLModel


class Chat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # 基础信息
    user_id: int = Field(description="用户ID")
    title: str = Field(description="对话标题")
    content: Optional[str] = Field(default=None, description="对话内容摘要")
    agent_id: int = Field(description="关联的 Agent ID")
    others: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_type=JSON, description="其他信息JSON字段")

    # 时间戳
    is_deleted: bool = Field(default=False, description="软删除标记")
    deleted_at: Optional[datetime] = Field(default=None, description="软删除时间戳")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
