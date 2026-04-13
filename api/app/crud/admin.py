from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, and_, func, select

from app.core.i18n import get_message
from app.core.logging import get_logger
from app.crud.order import OrderCRUD
from app.models.chat import Chat
from app.models.membership import MembershipPlan, UserMembership
from app.models.message import Message
from app.models.user import User, UserType
from app.schemas.admin import (
    AdminChatList,
    AdminDashboard,
    AdminUserList,
    ChatSearchParams,
    UserActionRequest,
    UserCreateRequest,
    UserListResponse,
    UserSearchParams,
    UserUpdateRequest,
)
from app.schemas.membership import MembershipType
from app.services.membership_service import MembershipService
from app.services.supabase_auth import create_supabase_auth_user, set_supabase_user_ban_state

logger = get_logger(__name__)


async def get_dashboard_stats(session: Session) -> AdminDashboard:
    today = datetime.utcnow().date()
    now = datetime.utcnow()

    total_users = session.exec(select(func.count(User.id))).first() or 0
    active_users = session.exec(select(func.count(User.id)).where(User.is_deleted == False)).first() or 0
    admin_users = (
        session.exec(
            select(func.count(User.id)).where(and_(User.user_type == UserType.ADMIN, User.is_deleted == False))
        ).first()
        or 0
    )
    deleted_users = session.exec(select(func.count(User.id)).where(User.is_deleted == True)).first() or 0
    today_new_users = session.exec(select(func.count(User.id)).where(func.date(User.created_at) == today)).first() or 0

    membership_stats = session.exec(
        select(MembershipPlan.type, func.count(func.distinct(UserMembership.user_id)).label("count"))
        .select_from(UserMembership)
        .join(MembershipPlan, UserMembership.membership_plan_id == MembershipPlan.id)
        .join(User, UserMembership.user_id == User.id)
        .where(
            UserMembership.is_active == True,
            UserMembership.is_deleted == False,
            UserMembership.start_date <= now,
            UserMembership.end_date > now,
            User.is_deleted == False,
        )
        .group_by(MembershipPlan.type)
    ).all()

    monthly_users = 0
    yearly_users = 0
    for row in membership_stats:
        membership_type = row.type.value if hasattr(row.type, "value") else row.type
        if membership_type == MembershipType.MONTHLY.value:
            monthly_users = row.count
        elif membership_type == MembershipType.YEARLY.value:
            yearly_users = row.count

    free_users = max(active_users - monthly_users - yearly_users, 0)

    total_chats = session.exec(select(func.count(Chat.id))).first() or 0
    active_chats = session.exec(select(func.count(Chat.id)).where(Chat.is_deleted == False)).first() or 0
    today_new_chats = session.exec(select(func.count(Chat.id)).where(func.date(Chat.created_at) == today)).first() or 0
    seven_days_ago = now - timedelta(days=7)
    seven_days_chats = session.exec(select(func.count(Chat.id)).where(Chat.created_at >= seven_days_ago)).first() or 0
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_chats = session.exec(select(func.count(Chat.id)).where(Chat.created_at >= month_start)).first() or 0
    total_messages = session.exec(select(func.count(Message.id))).first() or 0

    order_stats = await OrderCRUD.get_order_stats(session)

    return AdminDashboard(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        deleted_users=deleted_users,
        today_new_users=today_new_users,
        free_users=free_users,
        monthly_users=monthly_users,
        yearly_users=yearly_users,
        total_chats=total_chats,
        active_chats=active_chats,
        total_messages=total_messages,
        today_new_chats=today_new_chats,
        monthly_chats=monthly_chats,
        seven_days_chats=seven_days_chats,
        total_orders=order_stats["total_orders"],
        today_orders=order_stats["today_orders"],
        seven_days_orders=order_stats["seven_days_orders"],
        monthly_orders=order_stats["monthly_orders"],
        today_revenue=order_stats["daily_revenue"],
        seven_days_revenue=order_stats["seven_days_revenue"],
        monthly_revenue=order_stats["monthly_revenue"],
        total_revenue=order_stats["total_revenue"],
    )


def get_users_with_pagination(session: Session, params: UserSearchParams) -> UserListResponse:
    filters = []
    if params.email:
        filters.append(User.email.contains(params.email))
    if params.username:
        filters.append(User.username.contains(params.username))
    if params.user_type is not None:
        filters.append(User.user_type == params.user_type)
    if params.is_deleted is not None:
        filters.append(User.is_deleted == params.is_deleted)

    total_query = select(func.count(func.distinct(User.id))).select_from(User)
    if filters:
        total_query = total_query.where(and_(*filters))
    total = session.exec(total_query).first() or 0

    query = (
        select(
            User.id,
            User.username,
            User.email,
            User.user_type,
            User.is_deleted,
            User.created_at,
            User.last_login_at,
            func.count(Chat.id).label("chat_count"),
            func.max(Chat.updated_at).label("last_active"),
            MembershipPlan.type.label("membership_type"),
        )
        .select_from(User)
        .outerjoin(Chat, User.id == Chat.user_id)
        .outerjoin(
            UserMembership,
            and_(
                User.id == UserMembership.user_id,
                UserMembership.is_active == True,
                UserMembership.is_deleted == False,
                UserMembership.end_date > datetime.utcnow(),
            ),
        )
        .outerjoin(MembershipPlan, UserMembership.membership_plan_id == MembershipPlan.id)
    )

    if filters:
        query = query.where(and_(*filters))

    if params.membership_type is not None:
        if params.membership_type == MembershipType.FREE:
            query = query.where((MembershipPlan.type == MembershipType.FREE) | (MembershipPlan.type.is_(None)))
        else:
            query = query.where(MembershipPlan.type == params.membership_type)

    query = query.group_by(
        User.id,
        User.username,
        User.email,
        User.user_type,
        User.is_deleted,
        User.created_at,
        User.last_login_at,
        MembershipPlan.type,
    )

    sort_mapping = {
        "id": User.id,
        "username": User.username,
        "email": User.email,
        "user_type": User.user_type,
        "created_at": User.created_at,
        "last_login_at": User.last_login_at,
        "membership_type": MembershipPlan.type,
    }
    sort_column = sort_mapping.get(params.sort_by or "id", User.id)
    query = query.order_by(sort_column.desc() if params.sort_order == "desc" else sort_column.asc())
    query = query.offset(params.offset).limit(params.limit)

    users = [
        AdminUserList(
            id=row.id,
            username=row.username,
            email=row.email,
            user_type=row.user_type,
            membership_type=row.membership_type or MembershipType.FREE,
            is_deleted=row.is_deleted,
            created_at=row.created_at,
            last_login_at=row.last_login_at,
            chat_count=row.chat_count or 0,
            last_active=row.last_active,
        )
        for row in session.exec(query).all()
    ]

    total_pages = (total + params.limit - 1) // params.limit if params.limit > 0 else 1
    current_page = (params.offset // params.limit) + 1 if params.limit > 0 else 1

    return UserListResponse(
        users=users,
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0,
        total_pages=total_pages,
        current_page=current_page,
    )


def get_chats_with_user_info(session: Session, params: ChatSearchParams) -> dict:
    base_query = (
        select(
            Chat.id,
            Chat.user_id,
            Chat.title,
            Chat.created_at,
            Chat.updated_at,
            User.email.label("user_email"),
            User.username.label("username"),
            func.count(Message.id).label("message_count"),
        )
        .join(User, Chat.user_id == User.id)
        .outerjoin(Message, Chat.id == Message.chat_id)
        .where(Chat.is_deleted == False)
        .group_by(Chat.id, Chat.user_id, Chat.title, Chat.created_at, Chat.updated_at, User.email, User.username)
    )

    if params.user_id:
        base_query = base_query.where(Chat.user_id == params.user_id)
    if params.user_email:
        base_query = base_query.where(User.email.contains(params.user_email))
    if params.username:
        base_query = base_query.where(User.username.contains(params.username))
    if params.title:
        base_query = base_query.where(Chat.title.contains(params.title))

    total = session.exec(select(func.count()).select_from(base_query.order_by(None).subquery())).one()

    sort_mapping = {
        "id": Chat.id,
        "title": Chat.title,
        "created_at": Chat.created_at,
        "updated_at": Chat.updated_at,
        "user_email": User.email,
        "username": User.username,
        "message_count": func.count(Message.id),
    }
    sort_column = sort_mapping.get(params.sort_by or "updated_at", Chat.updated_at)
    query = base_query.order_by(sort_column.desc() if params.sort_order == "desc" else sort_column.asc())
    query = query.offset(params.offset).limit(params.limit)

    chats = [
        AdminChatList(
            id=row.id,
            user_id=row.user_id,
            user_email=row.user_email,
            username=row.username,
            title=row.title,
            message_count=row.message_count or 0,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in session.exec(query).all()
    ]

    total_pages = (total + params.limit - 1) // params.limit if params.limit > 0 else 1
    current_page = (params.offset // params.limit) + 1 if params.limit > 0 else 1

    return {
        "chats": chats,
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
        "has_next": params.offset + params.limit < total,
        "has_prev": params.offset > 0,
        "total_pages": total_pages,
        "current_page": current_page,
    }


def update_user(session: Session, user_id: int, update_data: UserUpdateRequest) -> Optional[User]:
    user = session.get(User, user_id)
    if not user:
        return None

    if update_data.user_type is not None:
        user.user_type = update_data.user_type

    if update_data.membership_type is not None:
        membership_service = MembershipService(session)
        success = membership_service.update_user_membership(user.id, update_data.membership_type)
        if not success:
            logger.warning("Failed to update membership type for user %s", user.id)

    if update_data.is_deleted is not None:
        user.is_deleted = update_data.is_deleted
        user.deleted_at = datetime.utcnow() if update_data.is_deleted else None

    if update_data.username is not None:
        user.username = update_data.username

    if update_data.is_deleted is not None and user.supabase_user_id:
        set_supabase_user_ban_state(user.supabase_user_id, banned=update_data.is_deleted)

    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def get_user_detail(session: Session, user_id: int) -> Optional[User]:
    return session.get(User, user_id)


def get_chat_messages(session: Session, chat_id: int) -> List[Message]:
    statement = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    return session.exec(statement).all()


def create_user_by_admin(session: Session, user_data: UserCreateRequest) -> User:
    existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise ValueError(f"{get_message('email_already_exists')}: {user_data.email}")

    if user_data.username:
        existing_username = session.exec(select(User).where(User.username == user_data.username)).first()
        if existing_username:
            raise ValueError(f"{get_message('username_already_exists')}: {user_data.username}")

    supabase_user = create_supabase_auth_user(
        email=user_data.email,
        password=user_data.password,
        username=user_data.username,
    )

    new_user = User(
        email=user_data.email,
        username=user_data.username or user_data.email.split("@", 1)[0],
        supabase_user_id=supabase_user.get("id"),
        password_hash=None,
        user_type=user_data.user_type,
        is_deleted=False,
        last_login_at=None,
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    if user_data.membership_type:
        membership_service = MembershipService(session)
        success = membership_service.update_user_membership(new_user.id, user_data.membership_type)
        if not success:
            logger.warning("Failed to set membership type %s for user %s", user_data.membership_type, new_user.id)

    return new_user


def delete_or_restore_user(session: Session, user_id: int, action_data: UserActionRequest) -> User:
    user = session.get(User, user_id)
    if not user:
        raise ValueError(get_message("user_not_found"))

    if action_data.action == "delete":
        if user.is_deleted:
            raise ValueError(get_message("user_already_deleted"))
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
    elif action_data.action == "restore":
        if not user.is_deleted:
            raise ValueError(get_message("user_not_deleted"))
        user.is_deleted = False
        user.deleted_at = None
    else:
        raise ValueError(get_message("invalid_operation_type"))

    if user.supabase_user_id:
        set_supabase_user_ban_state(user.supabase_user_id, banned=user.is_deleted)

    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def check_user_can_be_deleted(session: Session, user_id: int) -> dict:
    user = session.get(User, user_id)
    if not user:
        raise ValueError(get_message("user_not_found"))

    chat_count = (
        session.exec(select(func.count(Chat.id)).where(and_(Chat.user_id == user_id, Chat.is_deleted == False))).first() or 0
    )
    message_count = (
        session.exec(
            select(func.count(Message.id)).where(Message.chat_id.in_(select(Chat.id).where(Chat.user_id == user_id)))
        ).first()
        or 0
    )

    return {
        "can_delete": True,
        "chat_count": chat_count,
        "message_count": message_count,
        "user_type": user.user_type,
        "warning": "Deleting a user keeps business data but blocks sign-in" if chat_count > 0 or message_count > 0 else None,
    }
