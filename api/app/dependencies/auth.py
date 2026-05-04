from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db.base import get_session
from app.db.rls import set_rls_context
from app.models.user import User, UserType
from app.services.supabase_auth import sync_local_user_from_supabase, verify_supabase_access_token

security = HTTPBearer()


def _resolve_authenticated_user(credentials: HTTPAuthorizationCredentials, session: Session) -> User:
    token = credentials.credentials
    claims = verify_supabase_access_token(token)
    user = sync_local_user_from_supabase(session, claims)
    set_rls_context(session, user_id=user.id, is_admin=user.user_type == UserType.ADMIN)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    return _resolve_authenticated_user(credentials, session)


def verify_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
