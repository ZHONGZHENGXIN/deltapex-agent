from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.models.agent import AgentSource


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    source: AgentSource = Field(default=AgentSource.FASTGPT, description="Agent source")
    api_url: str = Field(..., description="API URL")
    api_key: str = Field(..., min_length=1, description="API key")
    model_conf: Optional[Dict[str, Any]] = Field(default=None, description="Model configuration JSON")
    is_think: bool = Field(default=False, description="Whether to show thinking process")
    is_stream: bool = Field(default=True, description="Whether to use streaming response")


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    source: Optional[AgentSource] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = Field(None, min_length=1)
    model_conf: Optional[Dict[str, Any]] = None
    is_think: Optional[bool] = None
    is_stream: Optional[bool] = None


class Agent(AgentBase):
    id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentList(BaseModel):
    id: int
    name: str
    source: AgentSource
    api_url: str
    model_conf: Optional[Dict[str, Any]]
    is_think: bool
    is_stream: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: List[AgentList]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool
    total_pages: int
    current_page: int


class AgentSearchParams(BaseModel):
    name: Optional[str] = None
    source: Optional[AgentSource] = None
    is_deleted: Optional[bool] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: Optional[str] = Field(default="id")
    sort_order: Optional[str] = Field(default="asc")


class AgentActionRequest(BaseModel):
    action: str = Field(..., description="Action to perform: delete, restore")
    lang: str = Field(default="zh", description="Language for response messages")


class DifyFileSchema(BaseModel):
    type: str = Field(default="image", description="File type")
    transfer_method: str = Field(default="remote_url", description="Transfer method")
    url: str = Field(..., description="File URL")

    @validator("type")
    def validate_file_type(cls, value):
        allowed_types = ["image", "document", "audio", "video", "text"]
        if value not in allowed_types:
            raise ValueError(f'File type must be one of: {", ".join(allowed_types)}')
        return value

    @validator("transfer_method")
    def validate_transfer_method(cls, value):
        allowed_methods = ["remote_url", "local_file"]
        if value not in allowed_methods:
            raise ValueError(f'Transfer method must be one of: {", ".join(allowed_methods)}')
        return value


class DifyModelConfSchema(BaseModel):
    files: Optional[List[DifyFileSchema]] = Field(default=None, description="File list")
    inputs: Optional[Dict[str, Any]] = Field(default=None, description="Input parameters")
    user_prefix: Optional[str] = Field(default=None, description="User id prefix")


class AgentCreateDify(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    api_url: str = Field(..., description="Dify API URL")
    api_key: str = Field(..., min_length=1, description="Dify API key")
    model_conf: Optional[DifyModelConfSchema] = Field(default=None, description="Dify model configuration")
    is_think: bool = Field(default=False, description="Whether to show thinking process")
    is_stream: bool = Field(default=True, description="Whether to use streaming response")

    @validator("api_url")
    def validate_dify_api_url(cls, value):
        if not value.startswith(("http://", "https://")):
            raise ValueError("API URL must start with http:// or https://")
        if "dify" not in value.lower():
            raise ValueError("Please provide a valid Dify API URL")
        return value


class AgentUpdateDify(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Agent name")
    api_url: Optional[str] = Field(None, description="Dify API URL")
    api_key: Optional[str] = Field(None, min_length=1, description="Dify API key")
    model_conf: Optional[DifyModelConfSchema] = Field(None, description="Dify model configuration")
    is_think: Optional[bool] = Field(None, description="Whether to show thinking process")
    is_stream: Optional[bool] = Field(None, description="Whether to use streaming response")

    @validator("api_url")
    def validate_dify_api_url(cls, value):
        if value is not None:
            if not value.startswith(("http://", "https://")):
                raise ValueError("API URL must start with http:// or https://")
            if "dify" not in value.lower():
                raise ValueError("Please provide a valid Dify API URL")
        return value


class DifyTestResponse(BaseModel):
    success: bool = Field(description="Whether the test succeeded")
    message: str = Field(description="Response message")
    response_time: float = Field(description="Response time in milliseconds")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")
