from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.i18n import create_response_message, get_message
from app.crud.admin import (
    check_user_can_be_deleted,
    create_user_by_admin,
    delete_or_restore_user,
    get_chat_messages,
    get_chats_with_user_info,
    get_dashboard_stats,
    get_user_detail,
    get_users_with_pagination,
    update_user,
)
from app.crud.agent import (
    create_agent,
    delete_or_restore_agent,
    get_agent_detail,
    get_agents_with_pagination,
    update_agent,
)
from app.dependencies.auth import verify_admin_user
from app.dependencies.db import LangDep, SessionDep
from app.models.user import User, UserType
from app.schemas.admin import (
    AdminDashboard,
    ChatListResponse,
    ChatSearchParams,
    UserActionRequest,
    UserCreateRequest,
    UserListResponse,
    UserSearchParams,
    UserUpdateRequest,
)
from app.schemas.agent import Agent as AgentSchema
from app.schemas.agent import (
    AgentActionRequest,
    AgentCreate,
    AgentListResponse,
    AgentSearchParams,
    AgentUpdate,
)
from app.schemas.membership import MembershipType

admin_router = APIRouter(prefix="/admin")


@admin_router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
) -> AdminDashboard:
    """获取管理员仪表板数据"""
    return await get_dashboard_stats(session)


@admin_router.get("/users", response_model=UserListResponse)
def get_users(
    *,
    session: SessionDep,
    lang: LangDep,
    email: Optional[str] = None,
    username: Optional[str] = None,
    user_type: Optional[UserType] = None,
    membership_type: Optional[MembershipType] = None,
    is_deleted: Optional[bool] = None,
    limit: int = 10,
    offset: int = 0,
    sort_by: Optional[str] = "id",
    sort_order: Optional[str] = "asc",
    admin_user: User = Depends(verify_admin_user),
) -> UserListResponse:
    """获取用户列表（带分页信息）"""
    params = UserSearchParams(
        email=email,
        username=username,
        user_type=user_type,
        membership_type=membership_type,
        is_deleted=is_deleted,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return get_users_with_pagination(session, params)


@admin_router.get("/chats", response_model=ChatListResponse)
def get_chats(
    *,
    session: SessionDep,
    lang: LangDep,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    username: Optional[str] = None,
    title: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = "updated_at",
    sort_order: Optional[str] = "desc",
    admin_user: User = Depends(verify_admin_user),
) -> ChatListResponse:
    """获取对话列表（带分页信息）"""
    params = ChatSearchParams(
        user_id=user_id,
        user_email=user_email,
        username=username,
        title=title,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = get_chats_with_user_info(session, params)
    return ChatListResponse(**result)


@admin_router.get("/users/{user_id}")
def get_user(
    user_id: int,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """获取用户详细信息"""
    user = get_user_detail(session, user_id)
    if not user:
        error_msg = get_message("user_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)
    return user


@admin_router.put("/users/{user_id}")
def update_user_info(
    user_id: int,
    update_data: UserUpdateRequest,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """更新用户信息"""
    user = update_user(session, user_id, update_data)
    if not user:
        error_msg = get_message("user_not_found", update_data.lang)
        raise HTTPException(status_code=404, detail=error_msg)
    return create_response_message("user_updated", update_data.lang, user=user)


@admin_router.get("/chats/{chat_id}/messages")
def get_chat_detail(
    chat_id: int,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """获取对话详细信息和消息列表"""
    messages = get_chat_messages(session, chat_id)
    return {"chat_id": chat_id, "messages": messages}


@admin_router.post("/users")
def create_user(
    user_data: UserCreateRequest,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """管理员创建新用户"""
    try:
        new_user = create_user_by_admin(session, user_data)
        return create_response_message("user_created", user_data.lang, user=new_user)
    except ValueError as e:
        # 返回具体的错误信息，而不是通用错误
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.post("/users/{user_id}/actions")
def user_action(
    user_id: int,
    action_data: UserActionRequest,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """用户操作：删除或恢复"""
    # 防止管理员删除自己
    if user_id == admin_user.id and action_data.action == "delete":
        error_msg = get_message("cannot_delete_self", action_data.lang)
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        updated_user = delete_or_restore_user(session, user_id, action_data)
        action_key = "user_deleted" if action_data.action == "delete" else "user_restored"
        return create_response_message(action_key, action_data.lang, user=updated_user)
    except ValueError:
        error_msg = get_message("error", action_data.lang)
        raise HTTPException(status_code=400, detail=error_msg)


@admin_router.get("/users/{user_id}/delete-check")
def check_user_deletion(
    user_id: int,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """检查用户删除的影响"""
    try:
        return check_user_can_be_deleted(session, user_id)
    except ValueError:
        error_msg = get_message("user_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)


# Agent Management APIs
@admin_router.get("/agents", response_model=AgentListResponse)
def get_agents(
    *,
    session: SessionDep,
    name: Optional[str] = None,
    source: Optional[str] = None,
    is_deleted: Optional[bool] = None,
    limit: int = 10,
    offset: int = 0,
    sort_by: Optional[str] = "id",
    sort_order: Optional[str] = "asc",
    admin_user: User = Depends(verify_admin_user),
) -> AgentListResponse:
    """获取 Agent 列表（带分页信息）"""
    params = AgentSearchParams(
        name=name,
        source=source,
        is_deleted=is_deleted,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return get_agents_with_pagination(session, params)


@admin_router.get("/agents/{agent_id}", response_model=AgentSchema)
def get_agent(
    agent_id: int,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """获取 Agent 详细信息"""
    agent = get_agent_detail(session, agent_id)
    if not agent:
        error_msg = get_message("agent_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)
    return agent


@admin_router.post("/agents", response_model=AgentSchema)
def create_new_agent(
    agent_data: AgentCreate,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """创建新 Agent"""
    try:
        new_agent = create_agent(session, agent_data)
        return new_agent
    except Exception:
        error_msg = get_message("error", lang)
        raise HTTPException(status_code=400, detail=error_msg)


@admin_router.put("/agents/{agent_id}", response_model=AgentSchema)
def update_agent_info(
    agent_id: int,
    agent_data: AgentUpdate,
    *,
    session: SessionDep,
    lang: LangDep,
    admin_user: User = Depends(verify_admin_user),
):
    """更新 Agent 信息"""
    agent = update_agent(session, agent_id, agent_data)
    if not agent:
        error_msg = get_message("agent_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)
    return agent


@admin_router.post("/agents/{agent_id}/actions")
def agent_action(
    agent_id: int,
    action_data: AgentActionRequest,
    *,
    session: SessionDep,
    admin_user: User = Depends(verify_admin_user),
):
    """Agent 操作：删除或恢复"""
    try:
        updated_agent = delete_or_restore_agent(session, agent_id, action_data)
        if not updated_agent:
            error_msg = get_message("agent_not_found", action_data.lang)
            raise HTTPException(status_code=404, detail=error_msg)

        action_key = "agent_deleted" if action_data.action == "delete" else "agent_restored"
        return create_response_message(action_key, action_data.lang, agent=updated_agent)
    except ValueError:
        error_msg = get_message("error", action_data.lang)
        raise HTTPException(status_code=400, detail=error_msg)
