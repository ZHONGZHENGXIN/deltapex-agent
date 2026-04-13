from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.i18n import get_message
from app.crud.membership import (
    create_membership_plan,
    delete_membership_plan,
    get_membership_distribution,
    get_membership_plan,
    get_membership_plans,
    get_user_memberships,
    update_membership_plan,
)
from app.dependencies.auth import get_current_user, verify_admin_user
from app.dependencies.db import LangDep, SessionDep
from app.models.user import User
from app.schemas.membership import (
    MembershipListResponse,
    MembershipPlanCreate,
    MembershipPlanResponse,
    MembershipPlanUpdate,
    MembershipStatus,
    UpgradeRequest,
    UpgradeResponse,
    UsageLimitCheck,
    UserMembershipListResponse,
)
from app.services.membership_service import MembershipService

membership_router = APIRouter(prefix="/membership")


# ==================== 会员计划管理 (管理员) ====================


@membership_router.post(
    "/plans",
    response_model=MembershipPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建会员计划",
    description="创建新的会员计划（仅管理员）",
)
def create_plan(
    plan_data: MembershipPlanCreate,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(verify_admin_user),
):
    """创建会员计划"""
    try:
        plan = create_membership_plan(db, plan_data)
        return plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{get_message('create_membership_plan_failed', lang)}: {str(e)}",
        )


@membership_router.get(
    "/plans",
    response_model=MembershipListResponse,
    summary="获取会员计划列表",
    description="获取所有会员计划列表",
)
def get_plans(
    db: SessionDep,
    lang: LangDep,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    current_user: User = Depends(get_current_user),
):
    """获取会员计划列表"""
    plans, total = get_membership_plans(db, skip=skip, limit=limit, is_active=is_active)
    return MembershipListResponse(items=plans, total=total)


@membership_router.get(
    "/plans/{plan_id}",
    response_model=MembershipPlanResponse,
    summary="获取会员计划详情",
    description="根据ID获取会员计划详情",
)
def get_plan(
    plan_id: int,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """获取会员计划详情"""
    plan = get_membership_plan(db, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_message("membership_plan_not_found", lang),
        )
    return plan


@membership_router.put(
    "/plans/{plan_id}",
    response_model=MembershipPlanResponse,
    summary="更新会员计划",
    description="更新会员计划信息（仅管理员）",
)
def update_plan(
    plan_id: int,
    plan_data: MembershipPlanUpdate,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(verify_admin_user),
):
    """更新会员计划"""
    plan = update_membership_plan(db, plan_id, plan_data)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_message("membership_plan_not_found", lang),
        )
    return plan


@membership_router.delete(
    "/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除会员计划",
    description="删除会员计划（仅管理员）",
)
def delete_plan(
    plan_id: int,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(verify_admin_user),
):
    """删除会员计划"""
    success = delete_membership_plan(db, plan_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_message("membership_plan_not_found", lang),
        )


# ==================== 用户会员管理 ====================


@membership_router.get(
    "/status",
    response_model=MembershipStatus,
    summary="获取当前用户会员状态",
    description="获取当前登录用户的会员状态和使用情况",
)
def get_my_membership_status(db: SessionDep, lang: LangDep, current_user: User = Depends(get_current_user)):
    """获取当前用户会员状态"""
    service = MembershipService(db)
    return service.get_user_membership_status(current_user.id)


@membership_router.get(
    "/users/{user_id}/status",
    response_model=MembershipStatus,
    summary="获取指定用户会员状态",
    description="获取指定用户的会员状态（仅管理员）",
)
def get_user_membership_status(
    user_id: int,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(verify_admin_user),
):
    """获取指定用户会员状态"""
    service = MembershipService(db)
    return service.get_user_membership_status(user_id)


@membership_router.get(
    "/history",
    response_model=UserMembershipListResponse,
    summary="获取当前用户会员历史",
    description="获取当前用户的会员购买和使用历史",
)
def get_my_membership_history(
    db: SessionDep,
    lang: LangDep,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户会员历史"""
    memberships, total = get_user_memberships(db, current_user.id, skip=skip, limit=limit)
    return UserMembershipListResponse(items=memberships, total=total)


@membership_router.post(
    "/upgrade",
    response_model=UpgradeResponse,
    summary="升级会员",
    description="升级当前用户的会员等级",
)
def upgrade_membership(
    upgrade_request: UpgradeRequest,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """升级会员"""
    service = MembershipService(db)
    return service.upgrade_membership(current_user.id, upgrade_request, lang)


@membership_router.post(
    "/users/{user_id}/upgrade",
    response_model=UpgradeResponse,
    summary="管理员升级用户会员",
    description="管理员为指定用户升级会员等级",
)
def admin_upgrade_user_membership(
    user_id: int,
    upgrade_request: UpgradeRequest,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(verify_admin_user),
):
    """管理员升级用户会员"""
    service = MembershipService(db)
    return service.upgrade_membership(user_id, upgrade_request, lang)


# ==================== 使用限制检查 ====================


@membership_router.get(
    "/check-limits/{chat_id}",
    response_model=UsageLimitCheck,
    summary="检查使用限制",
    description="检查当前用户在指定对话中的使用限制",
)
def check_usage_limits(
    chat_id: int,
    db: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
):
    """检查使用限制"""
    service = MembershipService(db)
    return service.check_usage_limits(current_user.id, chat_id)


@membership_router.post(
    "/record-usage/{chat_id}",
    summary="记录使用情况",
    description="记录用户在指定对话中的使用情况",
)
def record_usage(
    chat_id: int,
    db: SessionDep,
    lang: LangDep,
    message_count: int = Query(1, ge=1, description="消息数量"),
    token_count: int = Query(0, ge=0, description="Token消耗"),
    current_user: User = Depends(get_current_user),
):
    """记录使用情况"""
    service = MembershipService(db)
    success = service.record_usage(current_user.id, chat_id, message_count, token_count)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_message("record_usage_failed", lang),
        )

    return {"success": True, "message": get_message("usage_recorded_success", lang)}


# ==================== 统计和分析 (管理员) ====================


@membership_router.get(
    "/stats/distribution",
    summary="获取会员分布统计",
    description="获取当前会员类型分布统计（仅管理员）",
)
def get_membership_stats(db: SessionDep, lang: LangDep, current_user: User = Depends(verify_admin_user)):
    """获取会员分布统计"""
    distribution = get_membership_distribution(db)
    return {
        "success": True,
        "data": distribution,
        "message": get_message("membership_stats_success", lang),
    }
