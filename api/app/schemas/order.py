from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentMethod


class OrderBase(BaseModel):
    """订单基础模式"""

    membership_plan_id: int = Field(description="会员计划ID")
    payment_method: PaymentMethod = Field(description="支付方式")
    notes: Optional[str] = Field(default=None, description="订单备注")


class OrderCreate(OrderBase):
    """创建订单请求模式"""

    # 可选的折扣码
    discount_code: Optional[str] = Field(default=None, description="折扣码")


class OrderUpdate(BaseModel):
    """更新订单模式"""

    status: Optional[OrderStatus] = Field(default=None, description="订单状态")
    stripe_payment_intent_id: Optional[str] = Field(default=None, description="Stripe PaymentIntent ID")
    stripe_customer_id: Optional[str] = Field(default=None, description="Stripe Customer ID")
    stripe_session_id: Optional[str] = Field(default=None, description="Stripe Checkout Session ID")
    paid_at: Optional[datetime] = Field(default=None, description="支付时间")
    payment_confirmed_at: Optional[datetime] = Field(default=None, description="支付确认时间")
    processed_at: Optional[datetime] = Field(default=None, description="订单处理时间")
    completed_at: Optional[datetime] = Field(default=None, description="订单完成时间")
    cancelled_at: Optional[datetime] = Field(default=None, description="订单取消时间")
    refund_amount: Optional[float] = Field(default=None, description="退款金额")
    refunded_at: Optional[datetime] = Field(default=None, description="退款时间")
    refund_reason: Optional[str] = Field(default=None, description="退款原因")
    failure_reason: Optional[str] = Field(default=None, description="失败原因")
    notes: Optional[str] = Field(default=None, description="订单备注")


class OrderResponse(BaseModel):
    """订单响应模式"""

    id: int = Field(description="订单ID")
    order_number: str = Field(description="订单号")
    user_id: int = Field(description="用户ID")
    membership_plan_id: int = Field(description="会员计划ID")
    status: OrderStatus = Field(description="订单状态")
    payment_method: PaymentMethod = Field(description="支付方式")

    # 价格信息
    original_price: float = Field(description="原价")
    discount_amount: float = Field(description="折扣金额")
    final_price: float = Field(description="最终价格")
    currency: str = Field(description="货币类型")

    # Stripe 信息
    stripe_payment_intent_id: Optional[str] = Field(description="Stripe PaymentIntent ID")
    stripe_customer_id: Optional[str] = Field(description="Stripe Customer ID")
    stripe_session_id: Optional[str] = Field(description="Stripe Checkout Session ID")

    # 时间信息
    paid_at: Optional[datetime] = Field(description="支付时间")
    payment_confirmed_at: Optional[datetime] = Field(description="支付确认时间")
    processed_at: Optional[datetime] = Field(description="订单处理时间")
    completed_at: Optional[datetime] = Field(description="订单完成时间")
    cancelled_at: Optional[datetime] = Field(description="订单取消时间")

    # 退款信息
    refund_amount: Optional[float] = Field(description="退款金额")
    refunded_at: Optional[datetime] = Field(description="退款时间")
    refund_reason: Optional[str] = Field(description="退款原因")

    # 其他信息
    notes: Optional[str] = Field(description="订单备注")
    failure_reason: Optional[str] = Field(description="失败原因")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    """订单列表项模式"""

    id: int = Field(description="订单ID")
    order_number: str = Field(description="订单号")
    user_id: int = Field(description="用户ID")
    user_email: Optional[str] = Field(description="用户邮箱")
    username: Optional[str] = Field(description="用户名")
    membership_plan_id: int = Field(description="会员计划ID")
    status: OrderStatus = Field(description="订单状态")
    payment_method: PaymentMethod = Field(description="支付方式")
    final_price: float = Field(description="最终价格")
    currency: str = Field(description="货币类型")
    created_at: datetime = Field(description="创建时间")
    paid_at: Optional[datetime] = Field(description="支付时间")

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """订单列表响应模式（带分页信息）"""

    orders: list[OrderListItem] = Field(description="订单列表")
    total: int = Field(description="总数量")
    total_pages: int = Field(description="总页数")
    current_page: int = Field(description="当前页码")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")


class StripeCheckoutRequest(BaseModel):
    """Stripe 结账请求模式"""

    membership_plan_id: int = Field(description="会员计划ID")
    success_url: str = Field(description="支付成功回调URL")
    cancel_url: str = Field(description="支付取消回调URL")
    discount_code: Optional[str] = Field(default=None, description="折扣码")


class ContinuePaymentRequest(BaseModel):
    """继续支付请求模式"""

    success_url: str = Field(description="支付成功回调URL")
    cancel_url: str = Field(description="支付取消回调URL")


class StripeCheckoutResponse(BaseModel):
    """Stripe 结账响应模式"""

    checkout_url: str = Field(description="Stripe 结账页面URL")
    session_id: str = Field(description="Stripe Session ID")
    order_id: int = Field(description="订单ID")


class WebhookEventResponse(BaseModel):
    """Webhook 事件响应模式"""

    success: bool = Field(description="处理是否成功")
    message: str = Field(description="处理结果消息")
    order_id: Optional[int] = Field(default=None, description="相关订单ID")


class OrderStatsResponse(BaseModel):
    """订单统计响应模式"""

    # 基础统计
    total_orders: int = Field(description="总订单数")
    pending_orders: int = Field(description="待支付订单数")
    completed_orders: int = Field(description="已完成订单数")
    cancelled_orders: int = Field(description="已取消订单数")
    
    # 订单数量统计（按时间维度）
    today_orders: int = Field(description="今日订单数")
    seven_days_orders: int = Field(description="7日订单数")
    monthly_orders: int = Field(description="本月订单数")
    
    # 收入统计（按时间维度）
    total_revenue: float = Field(description="总收入")
    daily_revenue: float = Field(description="今日收入")
    seven_days_revenue: float = Field(description="7日收入")
    monthly_revenue: float = Field(description="本月收入")
