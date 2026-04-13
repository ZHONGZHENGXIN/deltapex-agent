import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator

from app.core.i18n import Language
from app.models.user import UserType
from app.schemas.membership import MembershipType


class EmailRequest(BaseModel):
    email: EmailStr
    lang: str
    purpose: str = "login"  # login, register, reset


class VerifyCode(BaseModel):
    email: EmailStr
    code: str
    lang: str = Language.ZH


class UserRegister(BaseModel):
    email: EmailStr
    code: str
    username: str
    password: str
    lang: str

    @validator("username")
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError("用户名不能为空")
        v = v.strip()
        if len(v) < 2 or len(v) > 20:
            raise ValueError("用户名长度必须在2-20字符之间")
        if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", v):
            raise ValueError("用户名只能包含字母、数字、下划线和中文字符")
        return v

    @validator("password")
    def validate_password(cls, v):
        if not v:
            raise ValueError("密码不能为空")
        if len(v) < 6:
            raise ValueError("密码长度至少6位")
        return v


class PasswordReset(BaseModel):
    email: EmailStr
    code: str
    new_password: str
    lang: str = Language.ZH

    @validator("new_password")
    def validate_password(cls, v):
        if not v:
            raise ValueError("密码不能为空")
        if len(v) < 6:
            raise ValueError("密码长度至少6位")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    lang: str = Language.ZH


class Token(BaseModel):
    access_token: str
    refresh_token: str


class RefreshToken(BaseModel):
    refresh_token: str
    lang: str = Language.ZH


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    user_type: UserType
    membership_type: MembershipType
    last_login_at: Optional[datetime]
    created_at: datetime


class UpgradeRequest(BaseModel):
    """用户升级请求"""

    plan_id: str  # monthly, yearly
    lang: str = Language.ZH

    @validator("plan_id")
    def validate_plan_id(cls, v):
        valid_plans = ["monthly", "yearly"]
        if v not in valid_plans:
            raise ValueError(f'无效的套餐类型，只支持: {", ".join(valid_plans)}')
        return v


class UpgradeResponse(BaseModel):
    """用户升级响应"""

    success: bool
    message: str
    user_profile: Optional[UserProfile] = None
