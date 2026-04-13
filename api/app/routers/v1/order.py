"""
订单管理 API 路由

功能:
- 创建订单
- 查询订单
- Stripe 支付集成
- Webhook 处理
- 订单管理（管理员）
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.crud.order import OrderCRUD
from app.dependencies.auth import get_current_user, verify_admin_user
from app.dependencies.db import LangDep, SessionDep
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import (
    ContinuePaymentRequest,
    OrderCreate,
    OrderListItem,
    OrderListResponse,
    OrderResponse,
    OrderStatsResponse,
    StripeCheckoutRequest,
    StripeCheckoutResponse,
    WebhookEventResponse,
)
from app.utils.pay import StripeService

order_router = APIRouter(prefix="/orders")


@order_router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """
    创建订单

    权限: 登录用户

    功能说明:
    1. 验证会员计划有效性
    2. 检查用户是否有支付中的订单
    3. 创建新订单

    请求参数:
    - order_data: 订单创建数据

    响应:
    - 201: 创建成功，返回订单信息
    - 400: 参数错误或业务规则限制
    - 401: 未登录
    - 404: 会员计划不存在
    """
    try:
        # 检查用户是否有过多支付中的订单
        pending_count = await OrderCRUD.get_pending_orders_count(db, current_user.id)
        if pending_count >= 1:  # 限制最多1个支付中的订单
            raise HTTPException(
                status_code=400,
                detail="您有支付中的订单，请先完成支付或取消现有订单",
            )

        # 创建订单
        order = await OrderCRUD.create_order(db=db, user_id=current_user.id, order_data=order_data)

        return order

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="创建订单失败")


@order_router.get("", response_model=List[OrderListItem])
async def get_my_orders(
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[OrderStatus] = None,
):
    """
    获取当前用户的订单列表

    权限: 登录用户

    查询参数:
    - skip: 跳过数量，默认0
    - limit: 限制数量，默认100，最大100
    - status: 订单状态过滤

    响应:
    - 200: 返回订单列表
    - 401: 未登录
    """
    if limit > 100:
        limit = 100

    orders = await OrderCRUD.get_user_orders(db=db, user_id=current_user.id, skip=skip, limit=limit, status=status)

    return orders


@order_router.get("/session/{session_id}", response_model=OrderResponse)
async def get_order_by_session(
    session_id: str,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """
    通过Stripe Session ID获取订单详情

    权限: 订单所有者

    路径参数:
    - session_id: Stripe Session ID

    响应:
    - 200: 返回订单详情
    - 401: 未登录
    - 403: 无权限访问
    - 404: 订单不存在
    """
    order = await OrderCRUD.get_order_by_stripe_session(db, session_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查权限：只能查看自己的订单
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限访问此订单")

    return order


@order_router.get("/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: int,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """
    获取订单详情

    权限: 订单所有者或管理员

    路径参数:
    - order_id: 订单ID

    响应:
    - 200: 返回订单详情
    - 401: 未登录
    - 403: 无权限访问
    - 404: 订单不存在
    """
    order = await OrderCRUD.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查权限：只能查看自己的订单
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限访问此订单")

    return order


@order_router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
    reason: Optional[str] = None,
):
    """
    取消订单

    权限: 订单所有者

    路径参数:
    - order_id: 订单ID

    请求体:
    - reason: 取消原因（可选）

    响应:
    - 200: 取消成功
    - 400: 订单状态不允许取消
    - 401: 未登录
    - 403: 无权限
    - 404: 订单不存在
    """
    order = await OrderCRUD.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查权限
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限操作此订单")

    # 检查订单状态
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能取消待支付的订单")

    # 取消订单
    updated_order = await OrderCRUD.cancel_order(db=db, order_id=order_id, reason=reason or "用户主动取消")

    return updated_order


@order_router.post("/{order_id}/continue-payment", response_model=StripeCheckoutResponse)
async def continue_order_payment(
    order_id: int,
    checkout_data: ContinuePaymentRequest,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """
    为现有订单继续支付

    权限: 登录用户（只能操作自己的订单）

    功能说明:
    1. 验证订单存在性和权限
    2. 检查订单状态是否为待支付
    3. 创建新的 Stripe Checkout Session
    4. 返回支付链接

    路径参数:
    - order_id: 订单ID

    请求参数:
    - checkout_data: 结账请求数据（包含成功和取消回调URL）

    响应:
    - 200: 返回支付链接和会话信息
    - 400: 订单状态不允许支付
    - 401: 未登录
    - 403: 无权限
    - 404: 订单不存在
    """
    try:
        # 获取订单信息
        order = await OrderCRUD.get_order_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        # 检查权限
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限操作此订单")

        # 检查订单状态
        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=400, detail="只能为待支付订单继续支付")

        # 创建 Stripe Checkout Session
        checkout_result = await StripeService.create_checkout_session(
            db=db,
            order_id=order.id,
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url,
        )

        return StripeCheckoutResponse(
            checkout_url=checkout_result["checkout_url"],
            session_id=checkout_result["session_id"],
            order_id=order.id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 如果是已知的HTTP异常，直接抛出
        if isinstance(e, HTTPException):
            raise e
        # 其他异常统一处理
        raise HTTPException(status_code=500, detail="创建支付会话失败")


@order_router.post("/stripe/checkout", response_model=StripeCheckoutResponse)
async def create_stripe_checkout(
    checkout_data: StripeCheckoutRequest,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """
    创建 Stripe 支付会话

    权限: 登录用户

    功能说明:
    1. 检查用户是否有待支付订单
    2. 创建订单
    3. 创建 Stripe Checkout Session
    4. 返回支付链接

    请求参数:
    - checkout_data: 结账请求数据

    响应:
    - 200: 返回支付链接和会话信息
    - 400: 参数错误或有待支付订单
    - 401: 未登录
    """
    try:
        # 检查用户是否有待支付订单
        pending_count = await OrderCRUD.get_pending_orders_count(db, current_user.id)
        if pending_count >= 1:  # 限制最多1个待支付订单
            raise HTTPException(
                status_code=400,
                detail="您有支付中的订单，请先完成支付或取消现有订单",
            )

        # 创建订单
        order_create = OrderCreate(
            membership_plan_id=checkout_data.membership_plan_id,
            payment_method="stripe",
            discount_code=checkout_data.discount_code,
        )

        order = await OrderCRUD.create_order(db=db, user_id=current_user.id, order_data=order_create)

        # 创建 Stripe Checkout Session
        checkout_result = await StripeService.create_checkout_session(
            db=db,
            order_id=order.id,
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url,
        )

        return StripeCheckoutResponse(
            checkout_url=checkout_result["checkout_url"],
            session_id=checkout_result["session_id"],
            order_id=order.id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 如果是已知的HTTP异常，直接抛出
        if isinstance(e, HTTPException):
            raise e
        # 其他异常统一处理
        raise HTTPException(status_code=500, detail="创建支付会话失败")


@order_router.post("/stripe/webhook", response_model=WebhookEventResponse)
async def stripe_webhook(
    request: Request,
    db: SessionDep,
    lang: LangDep,
):
    """
    Stripe Webhook 处理端点

    权限: 无需认证（通过 Stripe 签名验证）

    功能说明:
    1. 验证 Stripe 签名
    2. 处理支付事件
    3. 更新订单状态
    4. 激活会员权益

    响应:
    - 200: 处理成功
    - 400: 签名验证失败
    - 500: 处理失败
    """
    try:
        # 获取请求体和签名
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not sig_header:
            raise HTTPException(status_code=400, detail="缺少 Stripe 签名")

        # 处理 webhook 事件
        result = await StripeService.handle_webhook_event(db=db, payload=payload, sig_header=sig_header)

        return WebhookEventResponse(**result)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="处理 webhook 失败")


# 管理员订单管理 API
@order_router.get("/admin/all", response_model=OrderListResponse)
async def get_all_orders_admin(
    db: SessionDep,
    lang: LangDep,
    current_admin: User = Depends(verify_admin_user),
    offset: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    username: Optional[str] = None,
    order_number: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
):
    """
    获取所有订单列表（管理员）

    权限: 管理员

    查询参数:
    - offset: 偏移量，默认0
    - limit: 限制数量，默认100，最大1000
    - status: 订单状态过滤
    - user_id: 用户ID过滤
    - user_email: 用户邮箱过滤
    - username: 用户名过滤
    - order_number: 订单号过滤
    - start_date: 开始日期过滤 (YYYY-MM-DD)
    - end_date: 结束日期过滤 (YYYY-MM-DD)
    - sort_by: 排序字段，默认created_at
    - sort_order: 排序方向，默认desc

    响应:
    - 200: 返回订单列表和分页信息
    - 401: 未登录
    - 403: 非管理员
    """
    if limit > 1000:
        limit = 1000

    # 构建搜索参数
    search_params = {
        "offset": offset,
        "limit": limit,
        "status": status,
        "user_id": user_id,
        "user_email": user_email,
        "username": username,
        "order_number": order_number,
        "start_date": start_date,
        "end_date": end_date,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }

    result = await OrderCRUD.get_all_orders_with_pagination(db=db, **search_params)

    return result


@order_router.get("/admin/{order_id}", response_model=OrderResponse)
async def get_order_detail_admin(
    order_id: int,
    db: SessionDep,
    lang: LangDep,
    current_admin: User = Depends(verify_admin_user),
):
    """
    获取订单详情（管理员）

    权限: 管理员

    路径参数:
    - order_id: 订单ID

    响应:
    - 200: 返回订单详情
    - 401: 未登录
    - 403: 非管理员
    - 404: 订单不存在
    """
    order = await OrderCRUD.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return order


@order_router.post("/admin/{order_id}/refund")
async def refund_order_admin(
    order_id: int,
    db: SessionDep,
    lang: LangDep,
    current_admin: User = Depends(verify_admin_user),
    amount: Optional[float] = None,
    reason: Optional[str] = None,
):
    """
    退款订单（管理员）

    权限: 管理员

    路径参数:
    - order_id: 订单ID

    请求体:
    - amount: 退款金额（可选，默认全额退款）
    - reason: 退款原因（可选）

    响应:
    - 200: 退款成功
    - 400: 订单状态不允许退款
    - 401: 未登录
    - 403: 非管理员
    - 404: 订单不存在
    """
    order = await OrderCRUD.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查订单状态
    if order.status not in [OrderStatus.COMPLETED, OrderStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail="只能退款已完成或处理中的订单")

    # 创建退款
    result = await StripeService.create_refund(db=db, order_id=order_id, amount=amount, reason=reason or "管理员操作退款")

    return result


@order_router.get("/admin/stats", response_model=OrderStatsResponse)
async def get_order_stats_admin(
    db: SessionDep,
    lang: LangDep,
    current_admin: User = Depends(verify_admin_user),
):
    """
    获取订单统计信息（管理员）

    权限: 管理员

    响应:
    - 200: 返回统计信息
    - 401: 未登录
    - 403: 非管理员
    """
    stats = await OrderCRUD.get_order_stats(db)
    return OrderStatsResponse(**stats)


@order_router.post("/admin/cleanup-expired")
async def cleanup_expired_orders_admin(
    db: SessionDep,
    lang: LangDep,
    current_admin: User = Depends(verify_admin_user),
    hours: int = 24,
):
    """
    清理过期订单（管理员）

    权限: 管理员

    查询参数:
    - hours: 过期时间（小时），默认24小时

    响应:
    - 200: 返回清理数量
    - 401: 未登录
    - 403: 非管理员
    """
    if hours < 1 or hours > 168:  # 限制在1小时到7天之间
        raise HTTPException(status_code=400, detail="过期时间必须在1-168小时之间")

    cleaned_count = await OrderCRUD.cleanup_expired_orders(db, hours)

    return {
        "success": True,
        "message": f"已清理 {cleaned_count} 个过期订单",
        "cleaned_count": cleaned_count,
    }
