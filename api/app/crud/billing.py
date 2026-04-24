from datetime import datetime
from typing import Optional, Tuple
from uuid import uuid4

from sqlmodel import Session, func, select

from app.models.billing import TokenPackage, TokenTopupOrder, TokenTopupOrderStatus, UserTokenWallet


def list_active_token_packages(db: Session) -> list[TokenPackage]:
    return list(
        db.exec(
            select(TokenPackage).where(TokenPackage.is_active == True).order_by(TokenPackage.price.asc())
        ).all()
    )


def get_token_package(db: Session, package_id: int) -> Optional[TokenPackage]:
    return db.exec(select(TokenPackage).where(TokenPackage.id == package_id)).first()


def get_token_package_by_code(db: Session, code: str) -> Optional[TokenPackage]:
    return db.exec(select(TokenPackage).where(TokenPackage.code == code)).first()


def create_or_update_token_package(
    db: Session,
    *,
    code: str,
    name: str,
    creem_product_id: Optional[str],
    token_amount: int,
    price: float,
    currency: str,
) -> TokenPackage:
    package = get_token_package_by_code(db, code)
    now = datetime.utcnow()

    if package:
        package.name = name
        package.creem_product_id = creem_product_id
        package.token_amount = token_amount
        package.price = price
        package.currency = currency
        package.is_active = True
        package.updated_at = now
    else:
        package = TokenPackage(
            code=code,
            name=name,
            creem_product_id=creem_product_id,
            token_amount=token_amount,
            price=price,
            currency=currency,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def get_wallet(db: Session, user_id: int) -> Optional[UserTokenWallet]:
    return db.exec(select(UserTokenWallet).where(UserTokenWallet.user_id == user_id)).first()


def get_or_create_wallet(db: Session, user_id: int) -> UserTokenWallet:
    wallet = get_wallet(db, user_id)
    if wallet:
        return wallet

    wallet = UserTokenWallet(user_id=user_id)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def generate_topup_order_number() -> str:
    return f"TP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6].upper()}"


def generate_request_id() -> str:
    return f"topup_{uuid4().hex}"


def create_topup_order(
    db: Session,
    *,
    user_id: int,
    token_package: TokenPackage,
) -> TokenTopupOrder:
    order = TokenTopupOrder(
        order_number=generate_topup_order_number(),
        request_id=generate_request_id(),
        user_id=user_id,
        token_package_id=token_package.id,
        status=TokenTopupOrderStatus.PENDING,
        amount=token_package.price,
        currency=token_package.currency,
        token_amount=token_package.token_amount,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_topup_order_by_request_id(db: Session, request_id: str) -> Optional[TokenTopupOrder]:
    return db.exec(select(TokenTopupOrder).where(TokenTopupOrder.request_id == request_id)).first()


def get_topup_order_by_checkout_id(db: Session, checkout_id: str) -> Optional[TokenTopupOrder]:
    return db.exec(select(TokenTopupOrder).where(TokenTopupOrder.creem_checkout_id == checkout_id)).first()


def list_topup_orders(
    db: Session,
    *,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    request_id: Optional[str] = None,
    checkout_id: Optional[str] = None,
    order_number: Optional[str] = None,
) -> Tuple[list[TokenTopupOrder], int]:
    query = select(TokenTopupOrder).where(TokenTopupOrder.user_id == user_id)
    count_query = select(func.count(TokenTopupOrder.id)).where(TokenTopupOrder.user_id == user_id)

    if request_id:
        query = query.where(TokenTopupOrder.request_id == request_id)
        count_query = count_query.where(TokenTopupOrder.request_id == request_id)

    if checkout_id:
        query = query.where(TokenTopupOrder.creem_checkout_id == checkout_id)
        count_query = count_query.where(TokenTopupOrder.creem_checkout_id == checkout_id)

    if order_number:
        query = query.where(TokenTopupOrder.order_number == order_number)
        count_query = count_query.where(TokenTopupOrder.order_number == order_number)

    total = db.exec(count_query).one() or 0
    items = list(db.exec(query.order_by(TokenTopupOrder.created_at.desc()).offset(skip).limit(limit)).all())
    return items, total


def update_topup_order_checkout(
    db: Session,
    *,
    order: TokenTopupOrder,
    checkout_id: str,
) -> TokenTopupOrder:
    order.creem_checkout_id = checkout_id
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def mark_topup_order_paid(
    db: Session,
    *,
    order: TokenTopupOrder,
    creem_order_id: Optional[str],
    creem_customer_id: Optional[str],
    raw_payload: Optional[dict],
) -> TokenTopupOrder:
    order.status = TokenTopupOrderStatus.PAID
    order.creem_order_id = creem_order_id or order.creem_order_id
    order.creem_customer_id = creem_customer_id or order.creem_customer_id
    order.paid_at = order.paid_at or datetime.utcnow()
    order.raw_payload = raw_payload
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
