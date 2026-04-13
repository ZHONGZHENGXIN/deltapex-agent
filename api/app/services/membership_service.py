from datetime import date, datetime, timedelta
from typing import Tuple

from sqlmodel import Session

from app.core.config import settings
from app.core.i18n import get_message
from app.core.logging import get_logger
from app.crud.membership import (
    create_membership_plan,
    create_user_membership,
    get_active_user_membership,
    get_chat_turn_count,
    get_membership_plan_by_type,
    get_membership_plans,
    get_user_current_membership,
    get_user_daily_usage_with_chat,
    get_user_usage_stats,
    reset_daily_usage,
    update_daily_usage,
)
from app.crud.membership import update_user_membership as crud_update_user_membership
from app.crud.membership import (
    update_user_usage_stats,
    upgrade_user_membership,
)
from app.models.membership import MembershipPlan
from app.schemas.membership import (
    MembershipPlanCreate,
    MembershipStatus,
    MembershipType,
    UpgradeRequest,
    UpgradeResponse,
    UsageLimitCheck,
    UsageStatsUpdate,
    UserMembershipCreate,
    UserUsageStats,
)

logger = get_logger(__name__)


class MembershipService:
    """会员服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_membership_status(self, user_id: int) -> MembershipStatus:
        """获取用户会员状态"""
        # 先重置每日使用量
        reset_daily_usage(self.db, user_id)

        # 获取当前会员信息
        membership = get_user_current_membership(self.db, user_id)

        if not membership:
            # 没有会员，返回免费用户默认配置
            return self._get_free_user_status(user_id)

        # 获取会员计划信息
        plan = self.db.get(MembershipPlan, membership.membership_plan_id)
        if not plan:
            return self._get_free_user_status(user_id)

        # 计算剩余天数
        now = datetime.utcnow()
        days_remaining = (membership.end_date - now).days if membership.end_date > now else 0

        # 从用户会员表获取实际使用情况（统一数据源）
        daily_message_count, daily_token_count, daily_chat_count = get_user_daily_usage_with_chat(self.db, user_id)

        return MembershipStatus(
            has_membership=True,
            membership_type=MembershipType(plan.type),
            plan_name=plan.name,
            # 限制信息
            daily_message_limit=plan.daily_message_limit,
            daily_token_limit=plan.daily_token_limit,
            conversation_turn_limit=plan.conversation_turn_limit,
            # 使用情况（从用户会员表获取，确保数据一致性）
            daily_message_count=daily_message_count,
            daily_token_count=daily_token_count,
            daily_chat_count=daily_chat_count,
            # 剩余额度
            daily_message_remaining=max(0, plan.daily_message_limit - daily_message_count),
            daily_token_remaining=max(0, plan.daily_token_limit - daily_token_count),
            # 总使用统计
            total_message_count=membership.total_message_count,
            total_token_count=membership.total_token_count,
            total_chat_count=membership.total_chat_count,
            # 会员时间信息
            start_date=membership.start_date,
            end_date=membership.end_date,
            days_remaining=days_remaining,
        )

    def _get_free_user_status(self, user_id: int) -> MembershipStatus:
        """获取免费用户状态"""
        # 免费用户默认配置
        free_config = {
            "daily_message_limit": 100,
            "daily_token_limit": 1000000,  # 100w tokens
            "conversation_turn_limit": 10,
        }

        # 从数据库获取免费用户的实际使用情况
        daily_message_count, daily_token_count, daily_chat_count = get_user_daily_usage_with_chat(self.db, user_id)

        # 获取免费用户的总使用统计（如果有会员记录的话）
        membership = get_user_current_membership(self.db, user_id)
        total_message_count = membership.total_message_count if membership else 0
        total_token_count = membership.total_token_count if membership else 0
        total_chat_count = membership.total_chat_count if membership else 0

        return MembershipStatus(
            has_membership=False,
            membership_type=MembershipType.FREE,
            plan_name="免费会员",
            # 限制信息
            daily_message_limit=free_config["daily_message_limit"],
            daily_token_limit=free_config["daily_token_limit"],
            conversation_turn_limit=free_config["conversation_turn_limit"],
            # 使用情况（从数据库获取）
            daily_message_count=daily_message_count,
            daily_token_count=daily_token_count,
            daily_chat_count=daily_chat_count,
            # 剩余额度
            daily_message_remaining=max(0, free_config["daily_message_limit"] - daily_message_count),
            daily_token_remaining=max(0, free_config["daily_token_limit"] - daily_token_count),
            # 总使用统计
            total_message_count=total_message_count,
            total_token_count=total_token_count,
            total_chat_count=total_chat_count,
            # 会员时间信息
            start_date=None,
            end_date=None,
            days_remaining=None,
        )

    def check_usage_limits(self, user_id: int, chat_id: int) -> UsageLimitCheck:
        """检查用户使用限制"""
        # 获取会员状态
        status = self.get_user_membership_status(user_id)

        # 检查每日消息限制
        can_send_message = status.daily_message_remaining > 0
        message_limit_reached = not can_send_message

        # 检查 Token 限制
        # 如果是无限制会员（-1），则不检查 token 限制
        if status.daily_token_limit == -1:
            can_use_tokens = True
            token_limit_reached = False
        else:
            # 检查当前 token 使用量是否超过限制
            can_use_tokens = status.daily_token_remaining > 0
            token_limit_reached = not can_use_tokens

        # 检查对话轮次限制
        current_turns = get_chat_turn_count(self.db, chat_id)
        can_continue_conversation = current_turns < status.conversation_turn_limit
        conversation_limit_reached = not can_continue_conversation

        return UsageLimitCheck(
            can_send_message=can_send_message and can_use_tokens and can_continue_conversation,
            can_use_tokens=can_use_tokens,
            can_continue_conversation=can_continue_conversation,
            # 限制原因
            message_limit_reached=message_limit_reached,
            token_limit_reached=token_limit_reached,
            conversation_limit_reached=conversation_limit_reached,
            # 剩余额度
            remaining_messages=status.daily_message_remaining,
            remaining_tokens=status.daily_token_remaining,
            remaining_turns=max(0, status.conversation_turn_limit - current_turns),
        )

    def record_usage(
        self,
        user_id: int,
        chat_id: int,
        message_count: int = 1,
        token_count: int = 0,
        is_new_chat: bool = False,
    ) -> bool:
        """
        记录用户使用情况

        功能说明:
        更新用户每日使用量统计和总统计数据
        使用 user_membership 表中的统计字段替代原来的 usage_record 表

        参数:
        - user_id: 用户ID
        - chat_id: 对话ID（保留参数兼容性，但不再使用）
        - message_count: 本次消息数增量
        - token_count: 本次Token消耗增量
        - is_new_chat: 是否为新对话（用于统计对话数）

        返回:
        - bool: 记录是否成功
        """
        try:
            # 更新每日使用量（用于限制检查）
            chat_count_increment = 1 if is_new_chat else 0
            update_daily_usage(self.db, user_id, message_count, token_count, chat_count_increment)

            # 更新用户统计数据（替代原来的 usage_record 表）
            stats_update = UsageStatsUpdate(
                message_count_increment=message_count,
                token_count_increment=token_count,
                chat_count_increment=chat_count_increment,
            )
            update_user_usage_stats(self.db, user_id, stats_update)

            return True
        except Exception as e:
            logger.error(f"{get_message('record_usage_service_failed')}: {e}")
            return False

    def upgrade_membership(self, user_id: int, upgrade_request: UpgradeRequest, lang: str = "zh") -> UpgradeResponse:
        """升级用户会员"""
        try:
            # 检查会员计划是否存在
            plan = get_membership_plan_by_type(self.db, upgrade_request.membership_type)
            if not plan:
                return UpgradeResponse(
                    success=False,
                    message=get_message("invalid_plan", lang),
                )

            if not plan.is_active:
                return UpgradeResponse(success=False, message=get_message("plan_not_available", lang))

            # 检查用户当前会员状态
            current_status = self.get_user_membership_status(user_id)
            if current_status.has_membership and current_status.membership_type == upgrade_request.membership_type:
                return UpgradeResponse(success=False, message=get_message("already_member", lang))

            # 检查会员类型限制：月度会员期间不能开通年付会员，年付会员期间不能开通月度会员
            if current_status.has_membership:
                current_type = current_status.membership_type
                target_type = upgrade_request.membership_type

                # 月度会员期间尝试开通年付会员
                if current_type == "monthly" and target_type == "yearly":
                    return UpgradeResponse(success=False, message=get_message("cannot_upgrade_monthly_to_yearly", lang))

                # 年付会员期间尝试开通月度会员
                if current_type == "yearly" and target_type == "monthly":
                    return UpgradeResponse(success=False, message=get_message("cannot_upgrade_yearly_to_monthly", lang))

            # 执行升级
            new_membership = upgrade_user_membership(self.db, user_id, upgrade_request.membership_type)

            if not new_membership:
                return UpgradeResponse(success=False, message=get_message("upgrade_failed", lang))

            # 获取新的会员状态
            new_status = self.get_user_membership_status(user_id)

            return UpgradeResponse(
                success=True,
                message=get_message("upgrade_success", lang),
                membership_status=new_status,
            )

        except Exception:
            return UpgradeResponse(success=False, message=get_message("upgrade_failed", lang))

    def initialize_default_plans(self) -> bool:
        """初始化默认会员计划"""
        # 定义默认计划 - 从环境变量读取配置
        default_plans = [
            {
                "name": settings.MEMBERSHIP_FREE_NAME,
                "type": MembershipType.FREE,
                "daily_message_limit": settings.MEMBERSHIP_FREE_DAILY_MESSAGE_LIMIT,
                "daily_token_limit": settings.MEMBERSHIP_FREE_DAILY_TOKEN_LIMIT,
                "conversation_turn_limit": settings.MEMBERSHIP_FREE_CONVERSATION_TURN_LIMIT,
                "price": settings.MEMBERSHIP_FREE_PRICE,
                "currency": settings.MEMBERSHIP_FREE_CURRENCY,
                "duration_days": settings.MEMBERSHIP_FREE_DURATION_DAYS,
                "description": settings.MEMBERSHIP_FREE_DESCRIPTION,
            },
            {
                "name": settings.MEMBERSHIP_MONTHLY_NAME,
                "type": MembershipType.MONTHLY,
                "daily_message_limit": settings.MEMBERSHIP_MONTHLY_DAILY_MESSAGE_LIMIT,
                "daily_token_limit": settings.MEMBERSHIP_MONTHLY_DAILY_TOKEN_LIMIT,
                "conversation_turn_limit": settings.MEMBERSHIP_MONTHLY_CONVERSATION_TURN_LIMIT,
                "price": settings.MEMBERSHIP_MONTHLY_PRICE,
                "currency": settings.MEMBERSHIP_MONTHLY_CURRENCY,
                "duration_days": settings.MEMBERSHIP_MONTHLY_DURATION_DAYS,
                "description": settings.MEMBERSHIP_MONTHLY_DESCRIPTION,
            },
            {
                "name": settings.MEMBERSHIP_YEARLY_NAME,
                "type": MembershipType.YEARLY,
                "daily_message_limit": settings.MEMBERSHIP_YEARLY_DAILY_MESSAGE_LIMIT,
                "daily_token_limit": settings.MEMBERSHIP_YEARLY_DAILY_TOKEN_LIMIT,
                "conversation_turn_limit": settings.MEMBERSHIP_YEARLY_CONVERSATION_TURN_LIMIT,
                "price": settings.MEMBERSHIP_YEARLY_PRICE,
                "currency": settings.MEMBERSHIP_YEARLY_CURRENCY,
                "duration_days": settings.MEMBERSHIP_YEARLY_DURATION_DAYS,
                "description": settings.MEMBERSHIP_YEARLY_DESCRIPTION,
            },
        ]

        # 创建不存在的计划
        for plan_data in default_plans:
            existing_plan = get_membership_plan_by_type(self.db, plan_data["type"])
            if not existing_plan:
                plan_create = MembershipPlanCreate(**plan_data)
                create_membership_plan(self.db, plan_create)
                logger.info(f"{get_message('create_default_membership_plan')}: {plan_data['name']}")
                logger.info(f"默认会员计划创建成功: {plan_data['name']}")
            else:
                logger.info(f"默认会员计划已存在: {existing_plan.name}")

    def get_membership_plans(self) -> list:
        """获取所有可用的会员计划"""
        plans, _ = get_membership_plans(self.db, is_active=True)
        return plans

    def can_user_send_message(
        self, user_id: int, chat_id: int, lang: str = "zh", estimated_tokens: int = 0
    ) -> Tuple[bool, str]:
        """
        检查用户是否可以发送消息

        功能说明:
        - 检查用户的各种使用限制
        - 包含 token 预估检查
        - 返回多语言的限制消息

        参数:
        - user_id: 用户ID
        - chat_id: 对话ID
        - lang: 语言设置，用于返回对应语言的错误消息
        - estimated_tokens: 预估的 token 消耗量

        返回:
        - Tuple[bool, str]: (是否可以发送, 消息内容)
        """
        limit_check = self.check_usage_limits(user_id, chat_id)

        # 如果基础限制检查失败
        if not limit_check.can_send_message:
            if limit_check.message_limit_reached:
                return False, get_message("daily_message_limit_reached", lang)
            elif limit_check.token_limit_reached:
                return False, get_message("daily_token_limit_reached", lang)
            elif limit_check.conversation_limit_reached:
                return False, get_message("conversation_turn_limit_reached", lang)
            else:
                return False, get_message("usage_limit_reached", lang)

        # 额外检查：如果提供了 token 预估，检查是否会超过限制
        if estimated_tokens > 0 and limit_check.remaining_tokens != -1:  # -1 表示无限制
            if estimated_tokens > limit_check.remaining_tokens:
                return False, get_message("daily_token_limit_reached", lang)

        return True, get_message("can_send_message", lang)

    def update_user_membership(self, user_id: int, membership_type: str) -> bool:
        """更新用户会员类型"""
        try:
            # 获取用户当前的活跃会员记录
            current_membership = get_active_user_membership(self.db, user_id)

            # 如果设置为免费会员，禁用当前的付费会员记录
            if membership_type == "free":
                if current_membership:
                    # 禁用当前会员记录
                    success = crud_update_user_membership(
                        self.db,
                        current_membership.id,
                        {"is_active": False, "end_date": datetime.utcnow()},  # 立即过期
                    )
                    return success is not None
                return True  # 如果本来就没有会员记录，直接返回成功

            # 获取目标会员计划
            target_plan = get_membership_plan_by_type(self.db, membership_type)
            if not target_plan:
                logger.warning(f"{get_message('membership_plan_not_exists')}: {membership_type}")
                return False

            if current_membership:
                # 如果已有会员记录，更新为新的计划
                end_date = datetime.utcnow() + timedelta(days=target_plan.duration_days)
                success = crud_update_user_membership(
                    self.db,
                    current_membership.id,
                    {
                        "membership_plan_id": target_plan.id,
                        "end_date": end_date,
                        "is_active": True,
                    },
                )
                return success is not None
            else:
                # 如果没有会员记录，创建新的

                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=target_plan.duration_days)

                membership_data = UserMembershipCreate(
                    user_id=user_id,
                    membership_plan_id=target_plan.id,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=True,
                )

                new_membership = create_user_membership(self.db, membership_data)
                return new_membership is not None

        except Exception as e:
            logger.error(f"{get_message('update_user_membership_type_failed')}: {e}")
            return False

    def get_user_usage_statistics(self, user_id: int) -> UserUsageStats:
        """
        获取用户使用统计

        功能说明:
        获取用户的总统计、今日统计和最近30天的每日统计数据

        参数:
        - user_id: 用户ID

        返回:
        - UserUsageStats: 用户使用统计数据
        """
        try:
            # 从数据库获取统计数据
            stats_data = get_user_usage_stats(self.db, user_id)

            # 转换为Schema格式

            return UserUsageStats(
                total_message_count=stats_data["total_message_count"],
                total_token_count=stats_data["total_token_count"],
                total_chat_count=stats_data["total_chat_count"],
                today_message_count=stats_data["today_message_count"],
                today_token_count=stats_data["today_token_count"],
                today_chat_count=stats_data["today_chat_count"],
                stats_start_date=stats_data["stats_start_date"],
                stats_end_date=stats_data["stats_end_date"],
            )
        except Exception as e:
            logger.error(f"{get_message('get_user_usage_stats_service_failed')}: {e}")
            # 返回默认统计
            return UserUsageStats(
                total_message_count=0,
                total_token_count=0,
                total_chat_count=0,
                today_message_count=0,
                today_token_count=0,
                today_chat_count=0,
                stats_start_date=date.today().strftime("%Y-%m-%d"),
                stats_end_date=date.today().strftime("%Y-%m-%d"),
            )

    def get_user_total_stats(self, user_id: int) -> dict:
        """
        获取用户总统计数据（简化版本）

        参数:
        - user_id: 用户ID

        返回:
        - dict: 包含总消息数、总Token数、总对话数的字典
        """
        membership = get_user_current_membership(self.db, user_id)

        if not membership:
            return {
                "total_message_count": 0,
                "total_token_count": 0,
                "total_chat_count": 0,
            }

        return {
            "total_message_count": membership.total_message_count,
            "total_token_count": membership.total_token_count,
            "total_chat_count": membership.total_chat_count,
        }
