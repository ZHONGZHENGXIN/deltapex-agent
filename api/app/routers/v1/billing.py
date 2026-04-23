from fastapi import APIRouter, Depends, Query, Request, status

from app.dependencies.auth import get_current_user
from app.dependencies.db import SessionDep
from app.models.user import User
from app.schemas.billing import (
    CreateCreemCheckoutRequest,
    CreateCreemCheckoutResponse,
    CreemWebhookResponse,
    TokenPackageListResponse,
    TokenTopupOrderListResponse,
    TokenWalletResponse,
)
from app.services.billing_service import BillingService

billing_router = APIRouter(prefix="/billing")


@billing_router.get("/packages", response_model=TokenPackageListResponse)
def get_billing_packages(
    db: SessionDep,
    current_user: User = Depends(get_current_user),
) -> TokenPackageListResponse:
    service = BillingService(db)
    packages = service.list_packages()
    return TokenPackageListResponse(items=packages, total=len(packages))


@billing_router.get("/wallet", response_model=TokenWalletResponse)
def get_billing_wallet(
    db: SessionDep,
    current_user: User = Depends(get_current_user),
) -> TokenWalletResponse:
    service = BillingService(db)
    return TokenWalletResponse.model_validate(service.get_wallet(current_user.id))


@billing_router.get("/orders", response_model=TokenTopupOrderListResponse)
def get_billing_orders(
    db: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    request_id: str | None = Query(default=None),
    checkout_id: str | None = Query(default=None),
) -> TokenTopupOrderListResponse:
    service = BillingService(db)
    items, total = service.list_orders(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        request_id=request_id,
        checkout_id=checkout_id,
    )
    return TokenTopupOrderListResponse(items=items, total=total)


@billing_router.post("/creem/checkout", response_model=CreateCreemCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_creem_checkout(
    checkout_request: CreateCreemCheckoutRequest,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
) -> CreateCreemCheckoutResponse:
    service = BillingService(db)
    result = await service.create_creem_checkout(
        user=current_user,
        package_id=checkout_request.package_id,
        success_url=checkout_request.success_url,
        cancel_url=checkout_request.cancel_url,
    )
    return CreateCreemCheckoutResponse(**result)


@billing_router.post("/creem/webhook", response_model=CreemWebhookResponse)
async def handle_creem_webhook(
    request: Request,
    db: SessionDep,
) -> CreemWebhookResponse:
    signature = request.headers.get("creem-signature")
    payload = await request.body()
    service = BillingService(db)
    result = await service.handle_creem_webhook(payload=payload, signature=signature or "")
    return CreemWebhookResponse(**result)
