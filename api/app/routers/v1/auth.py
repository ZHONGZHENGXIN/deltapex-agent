from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.db import LangDep, SessionDep
from app.models.user import User
from app.schemas.user import (
    EmailRequest,
    PasswordReset,
    RefreshToken,
    Token,
    UserLogin,
    UserProfile,
    UserRegister,
    VerifyCode,
)
from app.services.membership_service import MembershipService
from app.services.supabase_auth import update_last_login

auth_router = APIRouter(prefix="/auth")

LEGACY_AUTH_DISABLED_MESSAGE = "Legacy auth endpoints have been removed. Use Supabase Auth from the frontend."


def _raise_legacy_auth_disabled() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=LEGACY_AUTH_DISABLED_MESSAGE,
    )


@auth_router.post("/send_code")
async def send_code(data: EmailRequest) -> dict:
    _raise_legacy_auth_disabled()


@auth_router.post("/verify", response_model=Token)
def verify(data: VerifyCode) -> Token:
    _raise_legacy_auth_disabled()


@auth_router.post("/admin/verify", response_model=Token)
def admin_verify(data: VerifyCode) -> Token:
    _raise_legacy_auth_disabled()


@auth_router.post("/refresh_token", response_model=Token)
async def refresh_token(data: RefreshToken) -> Token:
    _raise_legacy_auth_disabled()


@auth_router.post("/register", response_model=Token)
def register(data: UserRegister) -> Token:
    _raise_legacy_auth_disabled()


@auth_router.post("/login", response_model=Token)
def login(data: UserLogin) -> Token:
    _raise_legacy_auth_disabled()


@auth_router.post("/reset_password")
def reset_user_password(data: PasswordReset) -> dict:
    _raise_legacy_auth_disabled()


@auth_router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    session: SessionDep,
    lang: LangDep,
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    membership_service = MembershipService(session)
    membership_status = membership_service.get_user_membership_status(current_user.id)
    current_user = update_last_login(session, current_user)

    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        user_type=current_user.user_type,
        membership_type=membership_status.membership_type,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
    )
