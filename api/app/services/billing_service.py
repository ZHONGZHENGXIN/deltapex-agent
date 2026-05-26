import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from fastapi import HTTPException
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.billing import (
    create_or_update_token_package,
    create_topup_order,
    get_or_create_wallet,
    get_token_package,
    get_topup_order_by_checkout_id,
    get_topup_order_by_request_id,
    list_active_token_packages,
    list_topup_orders,
    mark_topup_order_paid,
    update_topup_order_checkout,
)
from app.models.billing import TokenPackage, TokenTopupOrderStatus, UserTokenWallet
from app.models.user import User
from app.services.membership_service import MembershipService

logger = get_logger(__name__)


@dataclass
class BillingBalanceCheck:
    remaining_free_tokens: int
    required_paid_tokens: int
    available_paid_tokens: int


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def initialize_default_token_packages(self) -> None:
        default_packages = [
            {
                "code": "starter",
                "name": "Starter 500K Tokens",
                "creem_product_id": settings.CREEM_TOPUP_STARTER_PRODUCT_ID,
                "token_amount": 500_000,
                "price": 9.90,
                "currency": "USD",
            },
            {
                "code": "growth",
                "name": "Growth 2M Tokens",
                "creem_product_id": settings.CREEM_TOPUP_GROWTH_PRODUCT_ID,
                "token_amount": 2_000_000,
                "price": 29.90,
                "currency": "USD",
            },
            {
                "code": "scale",
                "name": "Scale 8M Tokens",
                "creem_product_id": settings.CREEM_TOPUP_SCALE_PRODUCT_ID,
                "token_amount": 8_000_000,
                "price": 99.00,
                "currency": "USD",
            },
        ]

        for package in default_packages:
            create_or_update_token_package(self.db, **package)

    def list_packages(self) -> list[TokenPackage]:
        return list_active_token_packages(self.db)

    def get_wallet(self, user_id: int) -> UserTokenWallet:
        return get_or_create_wallet(self.db, user_id)

    def list_orders(
        self,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        request_id: Optional[str] = None,
        checkout_id: Optional[str] = None,
        order_number: Optional[str] = None,
    ) -> tuple[list, int]:
        return list_topup_orders(
            self.db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            request_id=request_id,
            checkout_id=checkout_id,
            order_number=order_number,
        )

    @staticmethod
    def _build_success_url(success_url: str, *, request_id: str, order_number: str) -> str:
        parsed = urlparse(success_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.setdefault("topup_request_id", request_id)
        query.setdefault("topup_order_number", order_number)
        return urlunparse(parsed._replace(query=urlencode(query)))

    async def create_creem_checkout(
        self,
        *,
        user: User,
        package_id: int,
        success_url: str,
        cancel_url: Optional[str] = None,
    ) -> dict[str, str]:
        token_package = get_token_package(self.db, package_id)
        if not token_package or not token_package.is_active:
            raise HTTPException(status_code=404, detail="Token package not found")

        if not token_package.creem_product_id:
            raise HTTPException(status_code=400, detail="Token package is not linked to a Creem product")

        if not settings.CREEM_API_KEY:
            raise HTTPException(status_code=500, detail="CREEM_API_KEY is not configured")

        order = create_topup_order(self.db, user_id=user.id, token_package=token_package)
        success_redirect_url = self._build_success_url(
            success_url,
            request_id=order.request_id,
            order_number=order.order_number,
        )
        payload = {
            "product_id": token_package.creem_product_id,
            "request_id": order.request_id,
            "success_url": success_redirect_url,
            "metadata": {
                "user_id": str(user.id),
                "local_order_id": str(order.id),
                "order_number": order.order_number,
                "package_code": token_package.code,
                "cancel_url": cancel_url or "",
            },
            "customer": {
                "email": user.email,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.CREEM_API_BASE_URL.rstrip('/')}/v1/checkouts",
                    headers={
                        "x-api-key": settings.CREEM_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error(f"Failed to create Creem checkout: {exc}")
            raise HTTPException(status_code=502, detail="Failed to create Creem checkout session") from exc

        checkout_id = data.get("id")
        checkout_url = data.get("checkout_url")
        if not checkout_id or not checkout_url:
            raise HTTPException(status_code=502, detail="Creem checkout response is missing required fields")

        update_topup_order_checkout(self.db, order=order, checkout_id=checkout_id)
        return {
            "checkout_url": checkout_url,
            "request_id": order.request_id,
            "order_number": order.order_number,
            "checkout_id": checkout_id,
        }

    def verify_creem_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not settings.CREEM_WEBHOOK_SECRET:
            return False

        computed = hmac.new(
            settings.CREEM_WEBHOOK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    async def handle_creem_webhook(self, *, payload: bytes, signature: str) -> dict[str, Any]:
        if not signature:
            raise HTTPException(status_code=400, detail="Missing Creem signature")

        if not self.verify_creem_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid Creem webhook signature")

        try:
            event = httpx.Response(200, content=payload).json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

        event_type = event.get("eventType")
        if event_type != "checkout.completed":
            return {"success": True, "message": f"Ignored event: {event_type}", "order_number": None}

        event_object = event.get("object") or {}
        request_id = event_object.get("request_id")
        checkout_id = event_object.get("id")
        order_data = event_object.get("order") or {}

        order = None
        if request_id:
            order = get_topup_order_by_request_id(self.db, request_id)
        if not order and checkout_id:
            order = get_topup_order_by_checkout_id(self.db, checkout_id)

        if not order:
            raise HTTPException(status_code=404, detail="Top-up order not found")

        if order.status == TokenTopupOrderStatus.PAID:
            return {"success": True, "message": "Top-up already processed", "order_number": order.order_number}

        wallet = get_or_create_wallet(self.db, order.user_id)
        wallet.paid_token_balance += order.token_amount
        wallet.total_recharged_tokens += order.token_amount
        self.db.add(wallet)
        self.db.commit()

        mark_topup_order_paid(
            self.db,
            order=order,
            creem_order_id=order_data.get("id"),
            creem_customer_id=order_data.get("customer"),
            raw_payload=event,
        )
        return {"success": True, "message": "Top-up payment processed", "order_number": order.order_number}

    def check_token_balance(
        self,
        *,
        user_id: int,
        chat_id: int,
        estimated_tokens: int,
    ) -> BillingBalanceCheck:
        membership_status = MembershipService(self.db).get_user_membership_status(user_id)
        remaining_free_tokens = max(0, membership_status.daily_token_remaining)
        required_paid_tokens = max(0, estimated_tokens - remaining_free_tokens)
        wallet = self.get_wallet(user_id)

        return BillingBalanceCheck(
            remaining_free_tokens=remaining_free_tokens,
            required_paid_tokens=required_paid_tokens,
            available_paid_tokens=wallet.paid_token_balance,
        )

    def ensure_sufficient_balance(
        self,
        *,
        user_id: int,
        chat_id: int,
        estimated_tokens: int,
    ) -> BillingBalanceCheck:
        balance_check = self.check_token_balance(
            user_id=user_id,
            chat_id=chat_id,
            estimated_tokens=estimated_tokens,
        )
        if balance_check.required_paid_tokens > balance_check.available_paid_tokens:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "insufficient_token_balance",
                    "message": "Insufficient token balance",
                    "required_paid_tokens": balance_check.required_paid_tokens,
                    "available_paid_tokens": balance_check.available_paid_tokens,
                    "remaining_free_tokens": balance_check.remaining_free_tokens,
                },
            )
        return balance_check

    def consume_paid_tokens(self, *, user_id: int, message_id: int, paid_tokens: int) -> None:
        if paid_tokens <= 0:
            return

        wallet = self.get_wallet(user_id)
        tokens_to_consume = min(wallet.paid_token_balance, paid_tokens)
        if tokens_to_consume < paid_tokens:
            logger.warning(
                "Paid token balance is out of sync for message %s: requested=%s available=%s",
                message_id,
                paid_tokens,
                wallet.paid_token_balance,
            )

        if tokens_to_consume <= 0:
            return

        wallet.paid_token_balance -= tokens_to_consume
        wallet.total_consumed_paid_tokens += tokens_to_consume
        wallet.updated_at = datetime.utcnow()
        self.db.add(wallet)
        self.db.commit()
