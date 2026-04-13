from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.core.i18n import Language
from app.models.user import UserType
from app.schemas.membership import MembershipType


class AdminUserList(BaseModel):
    id: int
    username: Optional[str] = None
    email: str
    user_type: UserType
    membership_type: Optional[MembershipType] = None  # 通过 user_membership 表获取，可能为 None
    is_deleted: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    chat_count: int
    last_active: Optional[datetime] = None


class AdminChatList(BaseModel):
    id: int
    user_id: int
    user_email: str
    username: Optional[str] = None
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class AdminDashboard(BaseModel):
    # 用户统计
    total_users: int
    active_users: int
    admin_users: int
    deleted_users: int
    today_new_users: int
    
    # 会员类型统计
    free_users: int
    monthly_users: int
    yearly_users: int
    
    # 对话统计
    total_chats: int
    active_chats: int
    total_messages: int
    today_new_chats: int
    monthly_chats: int
    seven_days_chats: int
    
    # 订单数量统计
    total_orders: int
    today_orders: int
    seven_days_orders: int
    monthly_orders: int
    
    # 收入统计
    today_revenue: float
    seven_days_revenue: float
    monthly_revenue: float
    total_revenue: float


class UserCreateRequest(BaseModel):
    email: str
    username: Optional[str] = None
    password: str  # 管理员创建用户时的密码
    user_type: UserType = UserType.USER
    membership_type: MembershipType = MembershipType.FREE
    lang: str = Language.ZH


class UserUpdateRequest(BaseModel):
    user_type: Optional[UserType] = None
    membership_type: Optional[MembershipType] = None
    is_deleted: Optional[bool] = None
    username: Optional[str] = None
    lang: str = Language.ZH


class UserActionRequest(BaseModel):
    action: str  # "delete" 或 "restore"
    reason: Optional[str] = None  # 操作原因
    lang: str = Language.ZH


class ChatSearchParams(BaseModel):
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None
    limit: int = 20
    offset: int = 0
    sort_by: Optional[str] = "updated_at"
    sort_order: Optional[str] = "desc"


class UserSearchParams(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    user_type: Optional[UserType] = None
    membership_type: Optional[MembershipType] = None
    is_deleted: Optional[bool] = None
    limit: int = 10
    offset: int = 0
    sort_by: Optional[str] = "id"
    sort_order: Optional[str] = "asc"


class UserListResponse(BaseModel):
    users: List[AdminUserList]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool
    total_pages: int
    current_page: int


class ChatListResponse(BaseModel):
    chats: List[AdminChatList]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool
    total_pages: int
    current_page: int
