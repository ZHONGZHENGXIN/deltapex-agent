from datetime import datetime
from typing import Optional

from sqlmodel import Session, func, select

from app.core.security import hash_password
from app.models.user import User, UserType


def get_user_by_email(email: str, session: Session) -> Optional[User]:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_user_by_username(username: str, session: Session) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def get_user_by_supabase_user_id(supabase_user_id: str, session: Session) -> Optional[User]:
    statement = select(User).where(User.supabase_user_id == supabase_user_id)
    return session.exec(statement).first()


def is_first_user(session: Session) -> bool:
    count = session.exec(select(func.count(User.id)).where(User.is_deleted == False)).first()
    return count == 0


def create_user(
    email: str,
    session: Session,
    username: str,
    password: Optional[str] = None,
    *,
    supabase_user_id: Optional[str] = None,
    user_type: Optional[UserType] = None,
) -> User:
    resolved_user_type = user_type or (UserType.ADMIN if is_first_user(session) else UserType.USER)
    user = User(
        email=email,
        username=username,
        supabase_user_id=supabase_user_id,
        password_hash=hash_password(password) if password else None,
        user_type=resolved_user_type,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_password(user: User, new_password: str, session: Session) -> User:
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
