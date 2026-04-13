from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class OrderStatus(str, Enum):
    """订单状态枚举"""

    PENDING = "pending"  # 待支付
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款
    FAILED = "failed"  # 支付失败


class PaymentMethod(str, Enum):
    """支付方式枚举"""

    STRIPE = "stripe"  # Stripe 支付


class Order(SQLModel, table=True):
    """订单表 - 记录用户购买会员计划的订单信息"""

    id: Optional[int] = Field(default=None, primary_key=True, description="订单ID")
    order_number: str = Field(unique=True, index=True, description="订单号")

    # 关联字段 - 使用业务逻辑保证数据一致性，不使用数据库外键约束
    user_id: int = Field(description="用户ID", index=True)
    membership_plan_id: int = Field(description="会员计划ID", index=True)

    # 订单基本信息
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="订单状态", index=True)
    payment_method: PaymentMethod = Field(description="支付方式", default=PaymentMethod.STRIPE)

    # 价格信息
    original_price: float = Field(description="原价（元）")
    discount_amount: float = Field(default=0.0, description="折扣金额（元）")
    final_price: float = Field(description="最终价格（元）")
    currency: str = Field(default="CNY", description="货币类型")

    # Stripe 相关字段
    stripe_payment_intent_id: Optional[str] = Field(default=None, description="Stripe PaymentIntent ID")
    stripe_customer_id: Optional[str] = Field(default=None, description="Stripe Customer ID")
    stripe_session_id: Optional[str] = Field(default=None, description="Stripe Checkout Session ID")

    # 支付信息
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")
    payment_confirmed_at: Optional[datetime] = Field(default=None, description="支付确认时间")

    # 订单处理信息
    processed_at: Optional[datetime] = Field(default=None, description="订单处理时间")
    completed_at: Optional[datetime] = Field(default=None, description="订单完成时间")
    cancelled_at: Optional[datetime] = Field(default=None, description="订单取消时间")

    # 退款信息
    refund_amount: Optional[float] = Field(default=None, description="退款金额（元）")
    refunded_at: Optional[datetime] = Field(default=None, description="退款时间")
    refund_reason: Optional[str] = Field(default=None, description="退款原因")

    # 备注信息
    notes: Optional[str] = Field(default=None, description="订单备注")
    failure_reason: Optional[str] = Field(default=None, description="失败原因")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    is_deleted: bool = Field(default=False, description="软删除标记")
    deleted_at: Optional[datetime] = Field(default=None, description="软删除时间戳")
