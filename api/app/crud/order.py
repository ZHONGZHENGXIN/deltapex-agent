import math
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models.membership import MembershipPlan
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderUpdate


class OrderCRUD:
    """订单 CRUD 操作类"""

    @staticmethod
    def generate_order_number() -> str:
        """
        生成订单号

        格式: ORD + 时间戳 + 随机字符串
        例如: ORD20240101120000ABC123

        返回:
        - str: 生成的订单号
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(uuid.uuid4()).replace("-", "")[:6].upper()
        return f"ORD{timestamp}{random_suffix}"

    @staticmethod
    async def create_order(db: Session, user_id: int, order_data: OrderCreate) -> Order:
        """
        创建订单

        功能说明:
        1. 验证用户是否存在且激活
        2. 验证会员计划是否存在且激活
        3. 计算订单价格（包含折扣）
        4. 生成唯一订单号
        5. 创建订单记录

        参数:
        - db: 数据库会话
        - user_id: 用户ID
        - order_data: 订单创建数据

        返回:
        - Order: 创建的订单对象

        异常:
        - ValueError: 用户不存在或未激活，会员计划不存在或未激活
        """
        # 验证用户是否存在且激活
        user = (
            db.query(User)
            .filter(
                and_(
                    User.id == user_id,
                    User.is_deleted == False,
                )
            )
            .first()
        )

        if not user:
            raise ValueError("用户不存在或未激活")

        # 验证会员计划
        membership_plan = (
            db.query(MembershipPlan)
            .filter(
                and_(
                    MembershipPlan.id == order_data.membership_plan_id,
                    MembershipPlan.is_active == True,
                    MembershipPlan.is_deleted == False,
                )
            )
            .first()
        )

        if not membership_plan:
            raise ValueError("会员计划不存在或未激活")

        # 计算价格
        original_price = membership_plan.price
        discount_amount = 0.0  # TODO: 实现折扣码逻辑
        final_price = original_price - discount_amount

        # 创建订单 - 使用会员计划中的货币类型
        order = Order(
            order_number=OrderCRUD.generate_order_number(),
            user_id=user_id,
            membership_plan_id=order_data.membership_plan_id,
            status=OrderStatus.PENDING,
            payment_method=order_data.payment_method,
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price,
            currency=membership_plan.currency,  # 使用会员计划的货币类型
            notes=order_data.notes,
        )

        db.add(order)
        db.commit()
        db.refresh(order)

        return order

    @staticmethod
    async def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
        """
        根据ID获取订单

        参数:
        - db: 数据库会话
        - order_id: 订单ID

        返回:
        - Optional[Order]: 订单对象，不存在返回None
        """
        return db.query(Order).filter(and_(Order.id == order_id, Order.is_deleted == False)).first()

    @staticmethod
    async def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
        """
        根据订单号获取订单

        参数:
        - db: 数据库会话
        - order_number: 订单号

        返回:
        - Optional[Order]: 订单对象，不存在返回None
        """
        return db.query(Order).filter(and_(Order.order_number == order_number, Order.is_deleted == False)).first()

    @staticmethod
    async def get_order_by_stripe_session(db: Session, session_id: str) -> Optional[Order]:
        """
        根据 Stripe Session ID 获取订单

        参数:
        - db: 数据库会话
        - session_id: Stripe Session ID

        返回:
        - Optional[Order]: 订单对象，不存在返回None
        """
        return db.query(Order).filter(and_(Order.stripe_session_id == session_id, Order.is_deleted == False)).first()

    @staticmethod
    async def get_user_orders(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
    ):
        """
        获取用户订单列表

        参数:
        - db: 数据库会话
        - user_id: 用户ID
        - skip: 跳过数量
        - limit: 限制数量
        - status: 订单状态过滤

        返回:
        - List[OrderListItem]: 订单列表项
        """
        # 构建查询，包含用户信息
        query = (
            db.query(Order, User.email.label("user_email"), User.username.label("username"))
            .join(User, Order.user_id == User.id)
            .filter(and_(Order.user_id == user_id, Order.is_deleted == False))
        )

        if status:
            query = query.filter(Order.status == status)

        results = query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()

        # 构建订单列表项
        from app.schemas.order import OrderListItem

        orders = []
        for order, user_email, username in results:
            order_item = OrderListItem(
                id=order.id,
                order_number=order.order_number,
                user_id=order.user_id,
                user_email=user_email,
                username=username,
                membership_plan_id=order.membership_plan_id,
                status=order.status,
                payment_method=order.payment_method,
                final_price=order.final_price,
                currency=order.currency,
                created_at=order.created_at,
                paid_at=order.paid_at,
            )
            orders.append(order_item)

        return orders

    @staticmethod
    async def get_all_orders(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        user_id: Optional[int] = None,
    ) -> List[Order]:
        """
        获取所有订单列表（管理员用）

        参数:
        - db: 数据库会话
        - skip: 跳过数量
        - limit: 限制数量
        - status: 订单状态过滤
        - user_id: 用户ID过滤

        返回:
        - List[Order]: 订单列表
        """
        query = db.query(Order).filter(Order.is_deleted == False)

        if status:
            query = query.filter(Order.status == status)

        if user_id:
            query = query.filter(Order.user_id == user_id)

        return query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    async def get_all_orders_with_pagination(
        db: Session,
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
        获取所有订单列表（管理员用，带分页和搜索）

        参数:
        - db: 数据库会话
        - offset: 偏移量
        - limit: 限制数量
        - status: 订单状态过滤
        - user_id: 用户ID过滤
        - user_email: 用户邮箱过滤
        - username: 用户名过滤
        - order_number: 订单号过滤
        - start_date: 开始日期过滤 (YYYY-MM-DD)
        - end_date: 结束日期过滤 (YYYY-MM-DD)
        - sort_by: 排序字段
        - sort_order: 排序方向

        返回:
        - OrderListResponse: 包含订单列表和分页信息
        """
        # 构建基础查询，包含用户信息
        query = (
            db.query(Order, User.email.label("user_email"), User.username.label("username"))
            .join(User, Order.user_id == User.id)
            .filter(Order.is_deleted == False)
        )

        # 应用过滤条件
        if status and status != "all":
            try:
                status_enum = OrderStatus(status)
                query = query.filter(Order.status == status_enum)
            except ValueError:
                pass  # 忽略无效的状态值

        if user_id:
            query = query.filter(Order.user_id == user_id)

        if user_email:
            query = query.filter(User.email.ilike(f"%{user_email}%"))

        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))

        if order_number:
            query = query.filter(Order.order_number.ilike(f"%{order_number}%"))

        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Order.created_at >= start_datetime)
            except ValueError:
                pass  # 忽略无效的日期格式

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                # 设置为当天的23:59:59
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(Order.created_at <= end_datetime)
            except ValueError:
                pass  # 忽略无效的日期格式

        # 获取总数量
        total = query.count()

        # 应用排序
        sort_column = getattr(Order, sort_by, Order.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 应用分页
        results = query.offset(offset).limit(limit).all()

        # 构建订单列表，包含用户邮箱和用户名
        from app.schemas.order import OrderListItem

        orders = []
        for order, user_email, username in results:
            order_item = OrderListItem(
                id=order.id,
                order_number=order.order_number,
                user_id=order.user_id,
                user_email=user_email,
                username=username,
                membership_plan_id=order.membership_plan_id,
                status=order.status,
                payment_method=order.payment_method,
                final_price=order.final_price,
                currency=order.currency,
                created_at=order.created_at,
                paid_at=order.paid_at,
            )
            orders.append(order_item)

        # 计算分页信息
        total_pages = math.ceil(total / limit) if limit > 0 else 0
        current_page = (offset // limit) + 1 if limit > 0 else 1
        has_next = offset + limit < total
        has_prev = offset > 0

        from app.schemas.order import OrderListResponse

        return OrderListResponse(
            orders=orders,
            total=total,
            total_pages=total_pages,
            current_page=current_page,
            has_next=has_next,
            has_prev=has_prev,
        )

    @staticmethod
    async def update_order(db: Session, order_id: int, order_update: OrderUpdate) -> Optional[Order]:
        """
        更新订单信息

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - order_update: 更新数据

        返回:
        - Optional[Order]: 更新后的订单对象
        """
        order = await OrderCRUD.get_order_by_id(db, order_id)
        if not order:
            return None

        # 更新字段
        update_data = order_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(order, field, value)

        order.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(order)

        return order

    @staticmethod
    async def update_order_status(db: Session, order_id: int, status: OrderStatus, **kwargs) -> Optional[Order]:
        """
        更新订单状态

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - status: 新状态
        - **kwargs: 其他更新字段

        返回:
        - Optional[Order]: 更新后的订单对象
        """
        order = await OrderCRUD.get_order_by_id(db, order_id)
        if not order:
            return None

        order.status = status
        order.updated_at = datetime.utcnow()

        # 根据状态设置相应的时间戳
        now = datetime.utcnow()
        if status == OrderStatus.COMPLETED:
            order.completed_at = now
            order.payment_confirmed_at = order.payment_confirmed_at or now
        elif status == OrderStatus.CANCELLED:
            order.cancelled_at = now
        elif status == OrderStatus.PROCESSING:
            order.processed_at = now

        # 设置其他字段
        for key, value in kwargs.items():
            if hasattr(order, key):
                setattr(order, key, value)

        db.commit()
        db.refresh(order)

        return order

    @staticmethod
    async def mark_order_paid(db: Session, order_id: int, payment_intent_id: Optional[str] = None) -> Optional[Order]:
        """
        标记订单为已支付

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - payment_intent_id: Stripe PaymentIntent ID

        返回:
        - Optional[Order]: 更新后的订单对象
        """
        now = datetime.utcnow()

        return await OrderCRUD.update_order_status(
            db=db,
            order_id=order_id,
            status=OrderStatus.PROCESSING,
            paid_at=now,
            payment_confirmed_at=now,
            stripe_payment_intent_id=payment_intent_id,
        )

    @staticmethod
    async def cancel_order(db: Session, order_id: int, reason: Optional[str] = None) -> Optional[Order]:
        """
        取消订单

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - reason: 取消原因

        返回:
        - Optional[Order]: 更新后的订单对象
        """
        return await OrderCRUD.update_order_status(
            db=db,
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            failure_reason=reason,
        )

    @staticmethod
    async def refund_order(db: Session, order_id: int, refund_amount: float, reason: Optional[str] = None) -> Optional[Order]:
        """
        退款订单

        参数:
        - db: 数据库会话
        - order_id: 订单ID
        - refund_amount: 退款金额
        - reason: 退款原因

        返回:
        - Optional[Order]: 更新后的订单对象
        """
        return await OrderCRUD.update_order_status(
            db=db,
            order_id=order_id,
            status=OrderStatus.REFUNDED,
            refund_amount=refund_amount,
            refunded_at=datetime.utcnow(),
            refund_reason=reason,
        )

    @staticmethod
    async def delete_order(db: Session, order_id: int) -> bool:
        """
        软删除订单

        参数:
        - db: 数据库会话
        - order_id: 订单ID

        返回:
        - bool: 删除是否成功
        """
        order = await OrderCRUD.get_order_by_id(db, order_id)
        if not order:
            return False

        order.is_deleted = True
        order.deleted_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        db.commit()
        return True

    @staticmethod
    async def get_order_stats(db: Session) -> dict:
        """
        获取订单统计信息

        参数:
        - db: 数据库会话

        返回:
        - dict: 统计信息，包含订单数量和收入统计
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 基础统计 - 总订单数
        total_orders = db.query(func.count(Order.id)).filter(Order.is_deleted == False).scalar()

        pending_orders = (
            db.query(func.count(Order.id)).filter(and_(Order.status == OrderStatus.PENDING, Order.is_deleted == False)).scalar()
        )

        completed_orders = (
            db.query(func.count(Order.id))
            .filter(and_(Order.status == OrderStatus.COMPLETED, Order.is_deleted == False))
            .scalar()
        )

        cancelled_orders = (
            db.query(func.count(Order.id))
            .filter(and_(Order.status == OrderStatus.CANCELLED, Order.is_deleted == False))
            .scalar()
        )

        # 订单数量统计 - 按时间维度（只统计成功的订单）
        today_orders = (
            db.query(func.count(Order.id))
            .filter(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= today_start,
                    Order.is_deleted == False,
                )
            )
            .scalar()
            or 0
        )

        seven_days_orders = (
            db.query(func.count(Order.id))
            .filter(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= seven_days_ago,
                    Order.is_deleted == False,
                )
            )
            .scalar()
            or 0
        )

        monthly_orders = (
            db.query(func.count(Order.id))
            .filter(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= month_start,
                    Order.is_deleted == False,
                )
            )
            .scalar()
            or 0
        )

        # 收入统计 - 按时间维度（只统计成功的订单）
        total_revenue = (
            db.query(func.sum(Order.final_price))
            .filter(and_(Order.status == OrderStatus.COMPLETED, Order.is_deleted == False))
            .scalar()
            or 0.0
        )

        daily_revenue = (
            db.query(func.sum(Order.final_price))
            .filter(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= today_start,
                    Order.is_deleted == False,
                )
            )
            .scalar()
            or 0.0
        )

        seven_days_revenue = (
            db.query(func.sum(Order.final_price))
            .filter(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= seven_days_ago,
                    Order.is_deleted == False,
                )
            )
            .scalar()
            or 0.0
        )

        monthly_revenue = (
            db.query(func.sum(Order.final_price))
            .filter(
                and_(
                    Order.status == OrderStatus.COMPLETED,
                    Order.created_at >= month_start,
                    Order.is_deleted == False,
                )
            )
            .scalar()
            or 0.0
        )

        return {
            # 基础统计
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            
            # 订单数量统计（按时间维度）
            "today_orders": today_orders,
            "seven_days_orders": seven_days_orders,
            "monthly_orders": monthly_orders,
            
            # 收入统计（按时间维度）
            "total_revenue": total_revenue,
            "daily_revenue": daily_revenue,
            "seven_days_revenue": seven_days_revenue,
            "monthly_revenue": monthly_revenue,
        }

    @staticmethod
    async def get_pending_orders_count(db: Session, user_id: int) -> int:
        """
        获取用户待支付订单数量

        参数:
        - db: 数据库会话
        - user_id: 用户ID

        返回:
        - int: 待支付订单数量
        """
        return (
            db.query(func.count(Order.id))
            .filter(
                and_(
                    Order.user_id == user_id,
                    Order.status == OrderStatus.PENDING,
                    Order.is_deleted == False,
                )
            )
            .scalar()
        )

    @staticmethod
    async def cleanup_expired_orders(db: Session, hours: int = 24) -> int:
        """
        清理过期的待支付订单

        参数:
        - db: 数据库会话
        - hours: 过期时间（小时）

        返回:
        - int: 清理的订单数量
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        expired_orders = (
            db.query(Order)
            .filter(
                and_(
                    Order.status == OrderStatus.PENDING,
                    Order.created_at < cutoff_time,
                    Order.is_deleted == False,
                )
            )
            .all()
        )

        count = 0
        for order in expired_orders:
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.utcnow()
            order.failure_reason = f"订单超时未支付（{hours}小时）"
            order.updated_at = datetime.utcnow()
            count += 1

        if count > 0:
            db.commit()

        return count
