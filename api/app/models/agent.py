from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlmodel import JSON, Field, SQLModel


class AgentSource(str, Enum):
    LLM = "llm"
    DIFY = "dify"
    FASTGPT = "fastgpt"
    COZE = "coze"
    CUSTOM = "custom"


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(index=True, description="AI assistant name")
    source: AgentSource = Field(default=AgentSource.FASTGPT, description="AI assistant source type")
    api_url: str = Field(description="API endpoint URL")
    api_key: str = Field(description="API key")
    model_conf: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON, description="Model configuration")
    is_think: bool = Field(default=False, description="Whether to show thinking process")
    is_stream: bool = Field(default=True, description="Whether to use streaming response")

    is_deleted: bool = Field(default=False, description="Soft delete flag")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Updated at")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at")
