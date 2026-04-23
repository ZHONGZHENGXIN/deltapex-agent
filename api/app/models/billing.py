from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlmodel import JSON, Column, Field, SQLModel


class TokenPackage(SQLModel, table=True):
    __tablename__ = "token_package"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, description="Internal package code")
    name: str = Field(description="Display name")
    creem_product_id: Optional[str] = Field(default=None, description="Creem product id")
    token_amount: int = Field(description="Paid token amount")
    price: float = Field(description="Package price")
    currency: str = Field(default="USD", description="Currency code")
    is_active: bool = Field(default=True, description="Whether package is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserTokenWallet(SQLModel, table=True):
    __tablename__ = "user_token_wallet"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, unique=True, description="User id")
    paid_token_balance: int = Field(default=0, description="Current paid token balance")
    total_recharged_tokens: int = Field(default=0, description="Total recharged tokens")
    total_consumed_paid_tokens: int = Field(default=0, description="Total consumed paid tokens")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TokenTopupOrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TokenTopupOrder(SQLModel, table=True):
    __tablename__ = "token_topup_order"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(index=True, unique=True, description="Internal order number")
    request_id: str = Field(index=True, unique=True, description="Creem request id")
    user_id: int = Field(index=True, description="User id")
    token_package_id: int = Field(index=True, description="Token package id")
    status: TokenTopupOrderStatus = Field(default=TokenTopupOrderStatus.PENDING, index=True)

    amount: float = Field(description="Order amount")
    currency: str = Field(default="USD", description="Currency code")
    token_amount: int = Field(description="Token amount")

    creem_checkout_id: Optional[str] = Field(default=None, index=True)
    creem_order_id: Optional[str] = Field(default=None, index=True)
    creem_customer_id: Optional[str] = Field(default=None)

    paid_at: Optional[datetime] = Field(default=None)
    failure_reason: Optional[str] = Field(default=None)
    raw_payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
