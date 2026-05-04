from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.db import LangDep, SessionDep
from app.models.user import User
from app.schemas.membership import UserUsageStats
from app.schemas.user import AccountDeletionRequest, AccountDeletionResponse, UpgradeRequest, UpgradeResponse
from app.services.account_deletion_service import AccountDeletionError, AccountDeletionService
from app.services.membership_service import MembershipService
from app.services.user_service import upgrade_user_membership

user_router = APIRouter(prefix="/user")


@user_router.post("/upgrade", response_model=UpgradeResponse)
async def upgrade_membership(
    upgrade_data: UpgradeRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> UpgradeResponse:
    """升级用户会员"""
    return upgrade_user_membership(
        user=current_user,
        plan_id=upgrade_data.plan_id,
        session=session,
        lang=upgrade_data.lang,
    )


@user_router.get("/usage-stats", response_model=UserUsageStats)
async def get_user_usage_stats(
    session: SessionDep, lang: LangDep, current_user: User = Depends(get_current_user)
) -> UserUsageStats:
    """
    获取用户使用统计

    功能说明:
    获取当前用户的使用统计数据，包括：
    - 总统计：历史总消息数、总Token数、总对话数
    - 今日统计：今日消息数、今日Token数
    - 按日统计：最近30天的每日使用数据

    返回:
    - UserUsageStats: 用户使用统计数据
    """
    membership_service = MembershipService(session)
    return membership_service.get_user_usage_statistics(current_user.id)


@user_router.get("/total-stats")
async def get_user_total_stats(session: SessionDep, lang: LangDep, current_user: User = Depends(get_current_user)) -> dict:
    """
    获取用户总统计数据（简化版本）

    功能说明:
    获取用户的总统计数据，用于快速显示

    返回:
    - dict: 包含总消息数、总Token数、总对话数的字典
    """
    membership_service = MembershipService(session)
    return membership_service.get_user_total_stats(current_user.id)


@user_router.post("/delete-account", response_model=AccountDeletionResponse)
def delete_my_account(
    deletion_request: AccountDeletionRequest,
    session: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
) -> AccountDeletionResponse:
    """学员自助删除账号和个人对话数据。"""
    if deletion_request.confirm_text != "DELETE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation text must be DELETE")

    try:
        audit = AccountDeletionService(session).delete_student_account(
            current_user,
            reason=deletion_request.reason,
        )
    except AccountDeletionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return AccountDeletionResponse(
        success=True,
        audit_id=audit.id,
        deleted_user_id=audit.user_id,
        anonymized_email=audit.result.get("anonymized_email", ""),
        result=audit.result,
    )
