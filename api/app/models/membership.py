from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.schemas.membership import MembershipType


class MembershipPlan(SQLModel, table=True):
    """会员计划配置表"""

    __tablename__ = "membership_plan"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 基础信息
    name: str = Field(max_length=50, description="计划名称")
    type: MembershipType = Field(description="会员类型", index=True)

    # 使用限制
    daily_message_limit: int = Field(description="每日消息限制")
    daily_token_limit: int = Field(description="每日Token限制")
    conversation_turn_limit: int = Field(description="单个对话轮次限制")

    # 价格信息
    price: float = Field(default=0.0, description="价格（元）")
    currency: str = Field(default="USD", description="货币类型")
    duration_days: int = Field(description="有效期天数")

    # 其他配置
    is_active: bool = Field(default=True, description="是否激活")
    description: Optional[str] = Field(default=None, description="计划描述")

    # 时间戳
    is_deleted: bool = Field(default=False, description="软删除标记")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    deleted_at: Optional[datetime] = Field(default=None, description="软删除时间戳")


class UserMembership(SQLModel, table=True):
    """用户会员关系表"""

    __tablename__ = "user_membership"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 基础信息
    user_id: int = Field(description="用户ID", index=True)
    membership_plan_id: int = Field(description="会员计划ID", index=True)

    # 会员状态
    start_date: datetime = Field(description="开始时间")
    end_date: datetime = Field(description="结束时间")
    is_active: bool = Field(default=True, description="是否激活", index=True)

    # 每日使用统计
    daily_message_count: int = Field(default=0, description="今日已使用消息数")
    daily_token_count: int = Field(default=0, description="今日已使用Token数")
    daily_chat_count: int = Field(default=0, description="今日对话次数")

    # 总使用统计
    total_message_count: int = Field(default=0, description="历史总消息数")
    total_token_count: int = Field(default=0, description="历史总Token数")
    total_chat_count: int = Field(default=0, description="历史总对话次数")

    # 时间戳
    last_reset_date: datetime = Field(default_factory=datetime.utcnow, description="上次使用的重置日期")
    is_deleted: bool = Field(default=False, description="软删除标记")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    deleted_at: Optional[datetime] = Field(default=None, description="软删除时间戳")
