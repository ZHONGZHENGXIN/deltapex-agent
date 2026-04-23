from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.billing import TokenTopupOrderStatus


class TokenPackageResponse(BaseModel):
    id: int
    code: str
    name: str
    token_amount: int
    price: float
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenPackageListResponse(BaseModel):
    items: List[TokenPackageResponse]
    total: int


class TokenWalletResponse(BaseModel):
    user_id: int
    paid_token_balance: int
    total_recharged_tokens: int
    total_consumed_paid_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenTopupOrderResponse(BaseModel):
    id: int
    order_number: str
    request_id: str
    user_id: int
    token_package_id: int
    status: TokenTopupOrderStatus
    amount: float
    currency: str
    token_amount: int
    creem_checkout_id: Optional[str] = None
    creem_order_id: Optional[str] = None
    creem_customer_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenTopupOrderListResponse(BaseModel):
    items: List[TokenTopupOrderResponse]
    total: int


class CreateCreemCheckoutRequest(BaseModel):
    package_id: int = Field(description="Token package id")
    success_url: str = Field(description="Success redirect url")
    cancel_url: Optional[str] = Field(default=None, description="Cancel redirect url")


class CreateCreemCheckoutResponse(BaseModel):
    checkout_url: str
    request_id: str
    order_number: str
    checkout_id: str


class CreemWebhookResponse(BaseModel):
    success: bool
    message: str
    order_number: Optional[str] = None
