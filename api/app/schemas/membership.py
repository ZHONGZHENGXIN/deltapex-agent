from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class MembershipType(str, Enum):
    """会员类型枚举"""

    FREE = "free"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class MembershipPlanBase(BaseModel):
    """会员计划基础Schema"""

    name: str = Field(max_length=50, description="计划名称")
    type: MembershipType = Field(description="会员类型")
    daily_message_limit: int = Field(gt=0, description="每日消息限制")
    daily_token_limit: int = Field(gt=0, description="每日Token限制")
    conversation_turn_limit: int = Field(gt=0, description="单个对话轮次限制")
    price: float = Field(ge=0, description="价格（元）")
    currency: str = Field(default="USD", description="货币类型")
    duration_days: int = Field(gt=0, description="有效期天数")
    description: Optional[str] = Field(None, description="计划描述")


class MembershipPlanCreate(MembershipPlanBase):
    """创建会员计划Schema"""


class MembershipPlanUpdate(BaseModel):
    """更新会员计划Schema"""

    name: Optional[str] = Field(None, max_length=50, description="计划名称")
    daily_message_limit: Optional[int] = Field(None, gt=0, description="每日消息限制")
    daily_token_limit: Optional[int] = Field(None, gt=0, description="每日Token限制")
    conversation_turn_limit: Optional[int] = Field(None, gt=0, description="单个对话轮次限制")
    price: Optional[float] = Field(None, ge=0, description="价格（元）")
    currency: Optional[str] = Field(default="USD", description="货币类型")
    duration_days: Optional[int] = Field(None, gt=0, description="有效期天数")
    description: Optional[str] = Field(None, description="计划描述")
    is_active: Optional[bool] = Field(None, description="是否激活")


class MembershipPlanResponse(MembershipPlanBase):
    """会员计划响应Schema"""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserMembershipBase(BaseModel):
    """用户会员基础Schema"""

    user_id: int = Field(description="用户ID")
    membership_plan_id: int = Field(description="会员计划ID")
    start_date: datetime = Field(description="开始时间")
    end_date: datetime = Field(description="结束时间")


class UserMembershipCreate(UserMembershipBase):
    """创建用户会员Schema"""


class UserMembershipResponse(UserMembershipBase):
    """用户会员响应Schema"""

    id: int
    is_active: bool
    daily_message_count: int
    daily_token_count: int
    daily_chat_count: int
    last_reset_date: datetime

    # 总使用统计
    total_message_count: int
    total_token_count: int
    total_chat_count: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserMembershipWithPlan(UserMembershipResponse):
    """包含计划信息的用户会员Schema"""

    plan: MembershipPlanResponse


class MembershipStatus(BaseModel):
    """用户会员状态Schema"""

    has_membership: bool = Field(description="是否有会员")
    membership_type: Optional[MembershipType] = Field(None, description="会员类型")
    plan_name: Optional[str] = Field(None, description="计划名称")

    # 限制信息
    daily_message_limit: int = Field(description="每日消息限制")
    daily_token_limit: int = Field(description="每日Token限制")
    conversation_turn_limit: int = Field(description="单个对话轮次限制")

    # 使用情况
    daily_message_count: int = Field(description="今日已使用消息数")
    daily_token_count: int = Field(description="今日已使用Token数")
    daily_chat_count: int = Field(description="今日对话次数")

    # 剩余额度
    daily_message_remaining: int = Field(description="今日剩余消息数")
    daily_token_remaining: int = Field(description="今日剩余Token数")

    # 总使用统计
    total_message_count: int = Field(description="历史总消息数")
    total_token_count: int = Field(description="历史总Token数")
    total_chat_count: int = Field(description="历史总对话次数")

    # 会员时间信息
    start_date: Optional[datetime] = Field(None, description="会员开始时间")
    end_date: Optional[datetime] = Field(None, description="会员到期时间")
    days_remaining: Optional[int] = Field(None, description="剩余天数")


class UpgradeRequest(BaseModel):
    """升级会员请求Schema"""

    membership_type: MembershipType = Field(description="会员类型")

    @validator("membership_type")
    def validate_membership_type(cls, v):
        if v == MembershipType.FREE:
            raise ValueError("不能升级到免费会员")
        return v


class UpgradeResponse(BaseModel):
    """升级会员响应Schema"""

    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    membership_status: Optional[MembershipStatus] = Field(None, description="会员状态")


class UsageLimitCheck(BaseModel):
    """使用限制检查结果Schema"""

    can_send_message: bool = Field(description="是否可以发送消息")
    can_use_tokens: bool = Field(description="是否可以使用Token")
    can_continue_conversation: bool = Field(description="是否可以继续对话")

    # 限制原因
    message_limit_reached: bool = Field(description="消息限制已达到")
    token_limit_reached: bool = Field(description="Token限制已达到")
    conversation_limit_reached: bool = Field(description="对话轮次限制已达到")

    # 剩余额度
    remaining_messages: int = Field(description="剩余消息数")
    remaining_tokens: int = Field(description="剩余Token数")
    remaining_turns: int = Field(description="剩余对话轮次")


class DailyUsageStats(BaseModel):
    """每日使用统计Schema"""

    date: datetime = Field(description="日期")
    total_messages: int = Field(description="总消息数")
    total_tokens: int = Field(description="总Token数")
    unique_users: int = Field(description="活跃用户数")

    # 按会员类型统计
    free_users: int = Field(description="免费用户数")
    monthly_users: int = Field(description="月度会员数")
    yearly_users: int = Field(description="年度会员数")


class MembershipListResponse(BaseModel):
    """会员计划列表响应Schema"""

    items: List[MembershipPlanResponse]
    total: int


class UserMembershipListResponse(BaseModel):
    """用户会员列表响应Schema"""

    items: List[UserMembershipWithPlan]
    total: int


class UserUsageStats(BaseModel):
    """用户使用统计Schema"""

    # 总统计
    total_message_count: int = Field(description="历史总消息数")
    total_token_count: int = Field(description="历史总Token数")
    total_chat_count: int = Field(description="历史总对话次数")

    # 今日统计
    today_message_count: int = Field(description="今日消息数")
    today_token_count: int = Field(description="今日Token数")
    today_chat_count: int = Field(description="今日对话次数")

    # 统计时间范围
    stats_start_date: str = Field(description="统计开始日期")
    stats_end_date: str = Field(description="统计结束日期")


class UsageStatsUpdate(BaseModel):
    """使用统计更新Schema"""

    message_count_increment: int = Field(default=0, description="消息数增量")
    token_count_increment: int = Field(default=0, description="Token数增量")
    chat_count_increment: int = Field(default=0, description="对话次数增量")
