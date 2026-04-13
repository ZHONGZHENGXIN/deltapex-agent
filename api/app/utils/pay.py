"""
Stripe 支付集成模块

功能:
- 创建 Stripe Checkout Session
- 处理 Stripe Webhook 事件
- 管理客户和支付意图
- 处理退款操作
"""

import logging
from typing import Any, Dict, Optional

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.membership import get_membership_plan, upgrade_user_membership
from app.crud.order import OrderCRUD
from app.models.membership import MembershipPlan
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.order import OrderUpdate

logger = logging.getLogger(__name__)

# 配置 Stripe
stripe.api_key = settings.STRIPE_PRIVATE_KEY


class StripeService:
    """Stripe 支付服务类"""

    @staticmethod
    async def create_checkout_session(db: Session, order_id: int, success_url: str, cancel_url: str) -> Dict[str, Any]:
        """
        创建 Stripe Checkout Session

        功能说明:
        1. 获取订单信息
        2. 创建或获取 Stripe 客户
        3. 创建 Checkout Session
        4. 更新订单的 Stripe 信息

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - success_url: 支付成功回调URL
        - cancel_url: 支付取消回调URL

        返回:
        - Dict: 包含 checkout_url 和 session_id

        异常:
        - HTTPException: 订单不存在或 Stripe 操作失败
        """
        try:
            # 获取订单信息
            order = await OrderCRUD.get_order_by_id(db, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            if order.status != OrderStatus.PENDING:
                raise HTTPException(status_code=400, detail="订单状态不允许支付")

            # 获取会员计划信息
            membership_plan = db.query(MembershipPlan).filter(MembershipPlan.id == order.membership_plan_id).first()

            if not membership_plan:
                raise HTTPException(status_code=404, detail="会员计划不存在")

            # 创建或获取 Stripe 客户
            customer_id = await StripeService._get_or_create_customer(db, order.user_id)

            # 在success_url中添加order_id参数
            success_url_with_params = (
                f"{success_url}&order_id={order.id}" if "?" in success_url else f"{success_url}?order_id={order.id}"
            )

            # 创建 Checkout Session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": order.currency.lower(),
                            "product_data": {
                                "name": membership_plan.name,
                                "description": membership_plan.description or f"{membership_plan.name} 会员计划",
                            },
                            "unit_amount": int(order.final_price * 100),  # Stripe 使用分为单位
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url_with_params,
                cancel_url=cancel_url,
                metadata={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "user_id": str(order.user_id),
                },
            )

            # 更新订单的 Stripe 信息
            await OrderCRUD.update_order(
                db=db,
                order_id=order_id,
                order_update=OrderUpdate(
                    stripe_session_id=session.id,
                    stripe_customer_id=customer_id,
                ),
            )

            return {"checkout_url": session.url, "session_id": session.id}

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe 错误: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise HTTPException(status_code=500, detail="创建支付会话失败")

    @staticmethod
    async def _get_or_create_customer(db: Session, user_id: int) -> str:
        """
        获取或创建 Stripe 客户

        参数:
        - db: 数据库会话
        - user_id: 用户ID

        返回:
        - str: Stripe Customer ID
        """

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 检查是否已有 Stripe 客户ID（可以扩展 User 模型添加此字段）
        # 这里简化处理，每次都创建新客户
        customer = stripe.Customer.create(
            email=user.email,
            name=user.username,
            metadata={
                "user_id": str(user.id),
            },
        )

        return customer.id

    @staticmethod
    async def handle_webhook_event(db: Session, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        处理 Stripe Webhook 事件

        参数:
        - db: 数据库会话
        - payload: 请求体
        - sig_header: Stripe 签名头

        返回:
        - Dict: 处理结果
        """
        try:
            # 验证 webhook 签名
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)

            logger.info(f"Received Stripe webhook event: {event['type']}")

            # 处理不同类型的事件
            if event["type"] == "checkout.session.completed":
                return await StripeService._handle_checkout_completed(db, event)
            elif event["type"] == "payment_intent.succeeded":
                return await StripeService._handle_payment_succeeded(db, event)
            elif event["type"] == "payment_intent.payment_failed":
                return await StripeService._handle_payment_failed(db, event)
            elif event["type"] == "charge.dispute.created":
                return await StripeService._handle_dispute_created(db, event)
            else:
                logger.info(f"Unhandled event type: {event['type']}")
                return {"success": True, "message": f"事件类型 {event['type']} 已忽略"}

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="签名验证失败")
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise HTTPException(status_code=500, detail="处理 webhook 失败")

    @staticmethod
    async def _handle_checkout_completed(db: Session, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理结账完成事件

        参数:
        - db: 数据库会话
        - event: Stripe 事件对象

        返回:
        - Dict: 处理结果
        """
        session = event["data"]["object"]
        session_id = session["id"]

        # 根据 session_id 查找订单
        order = await OrderCRUD.get_order_by_stripe_session(db, session_id)
        if not order:
            logger.error(f"Order not found for session {session_id}")
            return {"success": False, "message": "订单不存在"}

        # 更新订单状态为已支付
        await OrderCRUD.mark_order_paid(db=db, order_id=order.id, payment_intent_id=session.get("payment_intent"))

        # TODO: 激活用户会员权益
        await StripeService._activate_membership(db, order)

        logger.info(f"Order {order.order_number} marked as paid")

        return {"success": True, "message": "订单支付成功", "order_id": order.id}

    @staticmethod
    async def _handle_payment_succeeded(db: Session, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理支付成功事件

        参数:
        - db: 数据库会话
        - event: Stripe 事件对象

        返回:
        - Dict: 处理结果
        """
        payment_intent = event["data"]["object"]
        payment_intent_id = payment_intent["id"]

        # 查找相关订单
        order = db.query(Order).filter(Order.stripe_payment_intent_id == payment_intent_id).first()

        if order:
            await OrderCRUD.update_order_status(db=db, order_id=order.id, status=OrderStatus.COMPLETED)

            logger.info(f"Payment succeeded for order {order.order_number}")

            return {"success": True, "message": "支付确认成功", "order_id": order.id}

        return {"success": True, "message": "支付成功但未找到相关订单"}

    @staticmethod
    async def _handle_payment_failed(db: Session, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理支付失败事件

        参数:
        - db: 数据库会话
        - event: Stripe 事件对象

        返回:
        - Dict: 处理结果
        """
        payment_intent = event["data"]["object"]
        payment_intent_id = payment_intent["id"]
        failure_reason = payment_intent.get("last_payment_error", {}).get("message", "支付失败")

        # 查找相关订单
        order = db.query(Order).filter(Order.stripe_payment_intent_id == payment_intent_id).first()

        if order:
            await OrderCRUD.update_order_status(
                db=db,
                order_id=order.id,
                status=OrderStatus.FAILED,
                failure_reason=failure_reason,
            )

            logger.warning(f"Payment failed for order {order.order_number}: {failure_reason}")

            return {"success": True, "message": "支付失败已记录", "order_id": order.id}

        return {"success": True, "message": "支付失败但未找到相关订单"}

    @staticmethod
    async def _handle_dispute_created(db: Session, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理争议创建事件

        参数:
        - db: 数据库会话
        - event: Stripe 事件对象

        返回:
        - Dict: 处理结果
        """
        dispute = event["data"]["object"]
        charge_id = dispute["charge"]
        reason = dispute.get("reason", "未知原因")

        logger.warning(f"Dispute created for charge {charge_id}: {reason}")

        # TODO: 实现争议处理逻辑
        # 1. 查找相关订单
        # 2. 通知管理员
        # 3. 暂停相关服务

        return {
            "success": True,
            "message": "争议事件已记录",
        }

    @staticmethod
    async def _activate_membership(db: Session, order) -> None:
        """
        激活用户会员权益

        参数:
        - db: 数据库会话
        - order: 订单对象
        """

        try:
            # 检查订单是否已经完成，避免重复处理
            if order.status == OrderStatus.COMPLETED:
                logger.info(f"Order {order.order_number} already completed, skipping membership activation")
                return

            # 获取会员计划
            membership_plan = get_membership_plan(db, order.membership_plan_id)

            if membership_plan:
                # 激活或升级用户会员
                membership_result = upgrade_user_membership(
                    db=db,
                    user_id=order.user_id,
                    membership_type=membership_plan.type,
                )

                if membership_result:
                    # 会员激活成功后，将订单状态更新为已完成
                    await OrderCRUD.update_order_status(db=db, order_id=order.id, status=OrderStatus.COMPLETED)

                    logger.info(f"Membership activated and order {order.order_number} completed for user {order.user_id}")
                else:
                    logger.error(f"Failed to activate membership for user {order.user_id}, order {order.order_number}")
            else:
                logger.error(f"Membership plan {order.membership_plan_id} not found for order {order.order_number}")

        except Exception as e:
            logger.error(f"Error activating membership for order {order.order_number}: {e}")
            # 即使会员激活失败，也要记录错误但不影响支付状态

    @staticmethod
    async def create_refund(
        db: Session,
        order_id: int,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建退款

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - amount: 退款金额（None 表示全额退款）
        - reason: 退款原因

        返回:
        - Dict: 退款结果
        """
        try:
            order = await OrderCRUD.get_order_by_id(db, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            if not order.stripe_payment_intent_id:
                raise HTTPException(status_code=400, detail="订单没有有效的支付记录")

            # 计算退款金额
            refund_amount = amount or order.final_price

            # 创建 Stripe 退款
            refund = stripe.Refund.create(
                payment_intent=order.stripe_payment_intent_id,
                amount=int(refund_amount * 100),  # 转换为分
                reason="requested_by_customer",
                metadata={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                },
            )

            # 更新订单状态
            await OrderCRUD.refund_order(db=db, order_id=order_id, refund_amount=refund_amount, reason=reason)

            logger.info(f"Refund created for order {order.order_number}: {refund_amount}")

            return {
                "success": True,
                "refund_id": refund.id,
                "amount": refund_amount,
                "message": "退款成功",
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating refund: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe 错误: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating refund: {e}")
            raise HTTPException(status_code=500, detail="创建退款失败")

    @staticmethod
    async def get_payment_status(payment_intent_id: str) -> Dict[str, Any]:
        """
        获取支付状态

        参数:
        - payment_intent_id: Stripe PaymentIntent ID

        返回:
        - Dict: 支付状态信息
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return {
                "id": payment_intent.id,
                "status": payment_intent.status,
                "amount": payment_intent.amount / 100,  # 转换为元
                "currency": payment_intent.currency.upper(),
                "created": payment_intent.created,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving payment status: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe 错误: {str(e)}")
