from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.core.i18n import Language


class MessageRole(str, Enum):
    """消息角色枚举"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    chat_id: int
    content: str
    model_conf: Optional[Dict[str, Any]] = None
    role: MessageRole
    lang: str = Language.ZH
    token_usage: Optional[Dict[str, Any]] = None


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    model_conf: Optional[Dict[str, Any]] = None
    role: Optional[MessageRole] = None
    lang: str = Language.ZH
    token_usage: Optional[Dict[str, Any]] = None


class MessageOut(BaseModel):
    id: int
    chat_id: int
    content: str
    model_conf: Optional[Dict[str, Any]] = None
    role: MessageRole
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    token_usage: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
