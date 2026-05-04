from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.core.i18n import Language
from app.schemas.agent import AgentPublic
from app.schemas.message import MessageOut


class ChatCreate(BaseModel):
    title: str
    content: Optional[str] = None
    lang: str = Language.ZH
    agent_id: Optional[int] = None
    others: Optional[Dict[str, Any]] = None


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    lang: str = Language.ZH
    others: Optional[Dict[str, Any]] = None


class ChatOut(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    agent_id: Optional[int] = None
    agent: Optional[AgentPublic] = None
    messages: List[MessageOut] = []  
    others: Optional[Dict[str, Any]] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
