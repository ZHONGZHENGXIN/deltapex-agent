from datetime import datetime
from typing import Optional, Dict, Any

from sqlmodel import JSON, Column, Field, SQLModel

from app.schemas.message import MessageRole


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # 基础信息
    chat_id: int = Field(description="关联的对话ID")
    content: str = Field(description="消息内容")
    model_conf: str = Field(default_factory=dict, sa_column=Column(JSON), description="模型配置参数")
    role: MessageRole = Field(description="消息角色：user/assistant/system")
    
    # Token 使用统计（仅对 assistant 消息有效）
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None, 
        sa_column=Column(JSON), 
        description="Token使用统计信息，包含prompt_tokens、completion_tokens、total_tokens"
    )

    # 时间戳
    is_deleted: bool = Field(default=False, description="软删除标记")
    deleted_at: Optional[datetime] = Field(default=None, description="软删除时间戳")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
