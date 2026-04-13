from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, func, select

from app.core.i18n import get_message
from app.core.logging import get_logger
from app.models.membership import MembershipPlan, UserMembership
from app.models.message import Message
from app.schemas.membership import (
    MembershipPlanCreate,
    MembershipPlanUpdate,
    MembershipType,
    UsageStatsUpdate,
    UserMembershipCreate,
)
from app.schemas.message import MessageRole

logger = get_logger(__name__)


def create_membership_plan(db: Session, plan_data: MembershipPlanCreate) -> MembershipPlan:
    """创建会员计划"""
    plan = MembershipPlan(**plan_data.dict())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_membership_plan(db: Session, plan_id: int) -> Optional[MembershipPlan]:
    """根据ID获取会员计划"""
    result = db.execute(select(MembershipPlan).where(MembershipPlan.id == plan_id, MembershipPlan.is_deleted == False))
    return result.scalar_one_or_none()


def get_membership_plan_by_type(db: Session, membership_type: MembershipType) -> Optional[MembershipPlan]:
    """根据类型获取会员计划"""
    result = db.execute(
        select(MembershipPlan).where(
            MembershipPlan.type == membership_type.value,
            MembershipPlan.is_active == True,
            MembershipPlan.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


def get_membership_plans(
    db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
) -> Tuple[List[MembershipPlan], int]:
    """获取会员计划列表"""
    query = select(MembershipPlan).where(MembershipPlan.is_deleted == False)

    if is_active is not None:
        query = query.where(MembershipPlan.is_active == is_active)

    # 获取总数
    count_query = select(func.count(MembershipPlan.id)).where(MembershipPlan.is_deleted == False)
    if is_active is not None:
        count_query = count_query.where(MembershipPlan.is_active == is_active)

    total_result = db.execute(count_query)
    total = total_result.scalar()

    # 获取分页数据
    query = query.offset(skip).limit(limit).order_by(MembershipPlan.created_at.desc())
    result = db.execute(query)
    plans = result.scalars().all()

    return list(plans), total


def update_membership_plan(db: Session, plan_id: int, plan_data: MembershipPlanUpdate) -> Optional[MembershipPlan]:
    """更新会员计划"""
    plan = get_membership_plan(db, plan_id)
    if not plan:
        return None

    update_data = plan_data.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        for key, value in update_data.items():
            setattr(plan, key, value)

        db.add(plan)
        db.commit()
        db.refresh(plan)

    return plan


def delete_membership_plan(db: Session, plan_id: int) -> bool:
    """软删除会员计划"""
    plan = get_membership_plan(db, plan_id)
    if not plan:
        return False

    plan.is_deleted = True
    plan.deleted_at = datetime.utcnow()  # 设置删除时间戳
    plan.updated_at = datetime.utcnow()
    db.add(plan)
    db.commit()
    return True


# ==================== 用户会员 CRUD ====================


def create_user_membership(db: Session, membership_data: UserMembershipCreate) -> UserMembership:
    """创建用户会员关系"""
    membership = UserMembership(**membership_data.dict())
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def get_user_current_membership(db: Session, user_id: int) -> Optional[UserMembership]:
    """获取用户当前有效的会员"""
    now = datetime.utcnow()
    result = db.execute(
        select(UserMembership)
        .where(
            UserMembership.user_id == user_id,
            UserMembership.is_active == True,
            UserMembership.start_date <= now,
            UserMembership.end_date > now,
            UserMembership.is_deleted == False,
        )
        .order_by(UserMembership.end_date.desc())
    )
    return result.scalar_one_or_none()


def get_user_memberships(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> Tuple[List[UserMembership], int]:
    """获取用户会员历史"""
    query = select(UserMembership).where(UserMembership.user_id == user_id, UserMembership.is_deleted == False)

    # 获取总数
    count_query = select(func.count(UserMembership.id)).where(
        UserMembership.user_id == user_id, UserMembership.is_deleted == False
    )
    total_result = db.execute(count_query)
    total = total_result.scalar()

    # 获取分页数据
    query = query.offset(skip).limit(limit).order_by(UserMembership.created_at.desc())
    result = db.execute(query)
    memberships = result.scalars().all()

    return list(memberships), total


def upgrade_user_membership(db: Session, user_id: int, membership_type: MembershipType) -> Optional[UserMembership]:
    """升级用户会员"""
    # 获取会员计划
    plan = get_membership_plan_by_type(db, membership_type)
    if not plan:
        return None

    # 停用当前会员
    current_membership = get_user_current_membership(db, user_id)
    if current_membership:
        current_membership.is_active = False
        current_membership.updated_at = datetime.utcnow()
        db.add(current_membership)

    # 创建新会员
    now = datetime.utcnow()
    new_membership = UserMembership(
        user_id=user_id,
        membership_plan_id=plan.id,
        start_date=now,
        end_date=now + timedelta(days=plan.duration_days),
        is_active=True,
    )

    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    return new_membership


def reset_daily_usage(db: Session, user_id: int) -> bool:
    """重置用户每日使用量"""
    membership = get_user_current_membership(db, user_id)
    if not membership:
        return False

    today = date.today()
    if membership.last_reset_date.date() < today:
        membership.daily_message_count = 0
        membership.daily_token_count = 0
        membership.daily_chat_count = 0
        membership.last_reset_date = datetime.utcnow()
        membership.updated_at = datetime.utcnow()

        db.add(membership)
        db.commit()

    return True


def update_daily_usage(
    db: Session,
    user_id: int,
    message_count: int = 0,
    token_count: int = 0,
    chat_count: int = 0,
) -> bool:
    """
    更新用户每日使用量

    功能说明:
    对于有会员记录的用户，更新会员记录中的每日使用量
    对于免费用户（无会员记录），只需要确保使用记录表有数据即可

    参数:
    - user_id: 用户ID
    - message_count: 消息数量增量
    - token_count: Token消耗增量
    - chat_count: 对话次数增量

    返回:
    - bool: 更新是否成功
    """
    # 先重置每日使用量（如果需要）
    reset_daily_usage(db, user_id)

    membership = get_user_current_membership(db, user_id)
    if membership:
        # 有会员记录的用户，更新会员记录
        membership.daily_message_count += message_count
        membership.daily_token_count += token_count
        membership.daily_chat_count += chat_count
        membership.updated_at = datetime.utcnow()

        db.add(membership)
        db.commit()

    # 无论是否有会员记录，都返回True
    # 因为免费用户的使用情况通过user_membership表记录
    return True


# ==================== 使用记录 CRUD（已删除，使用其他数据源替代）====================


def get_chat_turn_count(db: Session, chat_id: int) -> int:
    """获取对话轮次数"""
    # 对话轮次应该基于用户消息数量计算，因为每个用户消息代表一轮对话的开始

    result = db.execute(
        select(func.count(Message.id)).where(
            Message.chat_id == chat_id,
            Message.role == MessageRole.USER,
            Message.is_deleted == False,
        )
    )
    return result.scalar() or 0


# ==================== 统计查询 ====================


def get_user_daily_usage_with_chat(db: Session, user_id: int, target_date: Optional[date] = None) -> Tuple[int, int, int]:
    """
    获取用户每日使用情况（包含对话计数）

    功能说明:
    从 user_membership 表获取用户每日使用情况，替代原来的 usage_record 表
    如果用户没有会员记录，返回 (0, 0, 0)

    参数:
    - db: 数据库会话
    - user_id: 用户ID
    - target_date: 目标日期，默认为今天

    返回:
    - Tuple[int, int, int]: (每日消息使用数, 每日Token使用数, 每日对话次数)
    """
    if not target_date:
        target_date = date.today()

    # 从用户会员表获取每日使用情况
    membership = get_user_current_membership(db, user_id)

    if not membership:
        # 没有会员记录，返回 0
        return (0, 0, 0)

    # 检查是否需要重置每日使用量
    last_reset_date = membership.last_reset_date.date()
    if last_reset_date < target_date:
        # 需要重置，返回 0
        return (0, 0, 0)

    return (
        membership.daily_message_count,
        membership.daily_token_count,
        membership.daily_chat_count,
    )


def get_membership_distribution(db: Session) -> dict:
    """获取会员分布统计"""
    now = datetime.utcnow()

    # 活跃会员统计
    result = db.execute(
        select(MembershipPlan.type, func.count(UserMembership.id).label("count"))
        .select_from(UserMembership)
        .join(MembershipPlan, UserMembership.membership_plan_id == MembershipPlan.id)
        .where(
            UserMembership.is_active == True,
            UserMembership.start_date <= now,
            UserMembership.end_date > now,
            UserMembership.is_deleted == False,
        )
        .group_by(MembershipPlan.type)
    )

    distribution = {membership_type.value: 0 for membership_type in MembershipType}
    for row in result:
        distribution[row.type] = row.count

    return distribution


def get_active_user_membership(db: Session, user_id: int) -> Optional[UserMembership]:
    """获取用户当前活跃的会员记录"""
    now = datetime.utcnow()
    return db.exec(
        select(UserMembership)
        .where(
            UserMembership.user_id == user_id,
            UserMembership.is_active == True,
            UserMembership.is_deleted == False,
            UserMembership.end_date > now,
        )
        .order_by(UserMembership.end_date.desc())
    ).first()


def update_user_membership(db: Session, membership_id: int, update_data: dict) -> Optional[UserMembership]:
    """更新用户会员记录"""
    membership = db.get(UserMembership, membership_id)
    if not membership:
        return None

    for key, value in update_data.items():
        if hasattr(membership, key):
            setattr(membership, key, value)

    membership.updated_at = datetime.utcnow()
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


# ==================== 用户统计相关 CRUD ====================


def update_user_usage_stats(db: Session, user_id: int, stats_update: UsageStatsUpdate) -> bool:
    """
    更新用户使用统计

    功能说明:
    更新用户会员记录中的总统计数据
    如果用户没有会员记录，则创建一个免费会员记录

    参数:
    - user_id: 用户ID
    - stats_update: 统计更新数据

    返回:
    - bool: 更新是否成功
    """
    try:
        # 获取或创建用户会员记录
        membership = get_user_current_membership(db, user_id)
        if not membership:
            # 为免费用户创建会员记录
            membership = _create_free_user_membership(db, user_id)
            if not membership:
                return False

        # 更新总统计（每日使用量在 update_daily_usage 中单独更新）
        membership.total_message_count += stats_update.message_count_increment
        membership.total_token_count += stats_update.token_count_increment
        membership.total_chat_count += stats_update.chat_count_increment

        membership.updated_at = datetime.utcnow()
        db.add(membership)
        db.commit()

        return True
    except Exception as e:
        logger.error(f"{get_message('update_user_stats_failed')}: {e}")
        db.rollback()
        return False


def _create_free_user_membership(db: Session, user_id: int) -> Optional[UserMembership]:
    """为免费用户创建会员记录"""
    try:
        # 获取免费会员
        free_plan = get_membership_plan_by_type(db, MembershipType.FREE)
        if not free_plan:
            return None

        # 创建免费会员记录
        now = datetime.utcnow()
        membership = UserMembership(
            user_id=user_id,
            membership_plan_id=free_plan.id,
            start_date=now,
            end_date=now + timedelta(days=365),  # 免费会员有效期1年
            is_active=True,
            total_message_count=0,
            total_token_count=0,
        )

        db.add(membership)
        db.commit()
        db.refresh(membership)

        return membership
    except Exception as e:
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.error(f"{get_message('create_free_user_membership_failed')}: {e}")
        db.rollback()
        return None


def get_user_usage_stats(db: Session, user_id: int) -> Dict[str, Any]:
    """
    获取用户使用统计

    参数:
    - user_id: 用户ID

    返回:
    - dict: 包含总统计和今日统计的字典
    """
    membership = get_user_current_membership(db, user_id)

    if not membership:
        # 免费用户没有会员记录，返回默认统计
        return {
            "total_message_count": 0,
            "total_token_count": 0,
            "total_chat_count": 0,
            "today_message_count": 0,
            "today_token_count": 0,
            "today_chat_count": 0,
            "stats_start_date": date.today().strftime("%Y-%m-%d"),
            "stats_end_date": date.today().strftime("%Y-%m-%d"),
        }

    # 获取今日统计（从每日使用量字段获取）
    today_message_count = membership.daily_message_count
    today_token_count = membership.daily_token_count
    today_chat_count = membership.daily_chat_count

    # 计算统计时间范围
    today = date.today().strftime("%Y-%m-%d")
    stats_start_date = today
    stats_end_date = today

    return {
        "total_message_count": membership.total_message_count,
        "total_token_count": membership.total_token_count,
        "total_chat_count": membership.total_chat_count,
        "today_message_count": today_message_count,
        "today_token_count": today_token_count,
        "today_chat_count": today_chat_count,
        "stats_start_date": stats_start_date,
        "stats_end_date": stats_end_date,
    }
