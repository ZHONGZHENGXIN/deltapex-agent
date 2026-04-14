import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _get_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value not in (None, ""):
            return value
    return default


def _get_int_env(*names: str, default: int) -> int:
    value = _get_env(*names)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(*names: str, default: float) -> float:
    value = _get_env(*names)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool_env(*names: str, default: bool) -> bool:
    value = _get_env(*names)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


class Settings:
    ENV: str = _get_env("ENV", default="dev") or "dev"

    AUTH_SECRET_KEY: str = _get_env("AUTH_SECRET_KEY", default="default-secret") or "default-secret"
    AUTH_ALGORITHM: str = _get_env("AUTH_ALGORITHM", default="HS256") or "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int_env("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", default=60)
    AUTH_REFRESH_TOKEN_EXPIRE_DAYS: int = _get_int_env("AUTH_REFRESH_TOKEN_EXPIRE_DAYS", default=7)
    AUTH_IS_DEBUG: bool = _get_bool_env("AUTH_IS_DEBUG", default=False)
    AUTH_DEBUG_CODE: str = _get_env("AUTH_DEBUG_CODE", default="888888") or "888888"

    API_NAME: str = _get_env("API_NAME", default="API") or "API"
    API_VERSION: str = _get_env("API_VERSION", default="0.1.0") or "0.1.0"
    API_HOST: str = _get_env("API_HOST", default="0.0.0.0") or "0.0.0.0"
    API_PORT: int = _get_int_env("API_PORT", "PORT", default=8000)
    API_RELOAD: bool = _get_bool_env("API_RELOAD", default=False)

    POSTGRES_HOST: str = _get_env("POSTGRES_HOST", "DATABASE_HOST", default="localhost") or "localhost"
    POSTGRES_PORT: int = _get_int_env("POSTGRES_PORT", "DATABASE_PORT", default=5432)
    POSTGRES_USER: str = (
        _get_env(
            "POSTGRES_USER",
            "POSTGRES_USERNAME",
            "DATABASE_USER",
            "DATABASE_USERNAME",
            default="postgres",
        )
        or "postgres"
    )
    POSTGRES_PASSWORD: str = _get_env("POSTGRES_PASSWORD", "DATABASE_PASSWORD", default="123456") or "123456"
    POSTGRES_DB: str = (
        _get_env(
            "POSTGRES_DB",
            "POSTGRES_DATABASE",
            "DATABASE_NAME",
            "DATABASE_DATABASE",
            default="bait",
        )
        or "bait"
    )
    POSTGRES_ECHO: bool = _get_bool_env("POSTGRES_ECHO", default=False)
    POSTGRES_POOL_SIZE: int = _get_int_env("POSTGRES_POOL_SIZE", default=20)
    POSTGRES_MAX_OVERFLOW: int = _get_int_env("POSTGRES_MAX_OVERFLOW", default=30)
    POSTGRES_POOL_TIMEOUT: int = _get_int_env("POSTGRES_POOL_TIMEOUT", default=30)
    POSTGRES_POOL_RECYCLE: int = _get_int_env("POSTGRES_POOL_RECYCLE", default=3600)
    POSTGRES_POOL_PRE_PING: bool = _get_bool_env("POSTGRES_POOL_PRE_PING", default=True)

    @property
    def POSTGRES_URL(self) -> str:
        direct_url = _get_env(
            "POSTGRES_URL",
            "POSTGRES_CONNECTION_STRING",
            "DATABASE_URL",
            "DATABASE_CONNECTION_STRING",
        )
        if direct_url:
            return direct_url
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_HOST: str = _get_env("REDIS_HOST", default="localhost") or "localhost"
    REDIS_PORT: int = _get_int_env("REDIS_PORT", default=6379)
    REDIS_USER: str = _get_env("REDIS_USER", default="default") or "default"
    REDIS_PASSWORD: str = _get_env("REDIS_PASSWORD", default="123456") or "123456"
    REDIS_DB: int = _get_int_env("REDIS_DB", default=0)

    @property
    def REDIS_URL(self) -> str:
        direct_url = _get_env("REDIS_URL", "REDIS_CONNECTION_STRING")
        if direct_url:
            return direct_url
        return f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    MAIL_SEND_METHOD: str = _get_env("MAIL_SEND_METHOD", default="SMTP") or "SMTP"
    MAIL_USERNAME: str | None = _get_env("MAIL_USERNAME")
    MAIL_PASSWORD: str | None = _get_env("MAIL_PASSWORD")
    MAIL_FROM: str | None = _get_env("MAIL_FROM")
    MAIL_PORT: int = _get_int_env("MAIL_PORT", default=587)
    MAIL_SERVER: str | None = _get_env("MAIL_SERVER")
    RESEND_API_KEY: str | None = _get_env("RESEND_API_KEY")
    RESEND_MAIL_FROM: str | None = _get_env("RESEND_MAIL_FROM")

    SUPABASE_URL: str | None = _get_env("SUPABASE_URL")
    SUPABASE_JWT_AUDIENCE: str = _get_env("SUPABASE_JWT_AUDIENCE", default="authenticated") or "authenticated"
    SUPABASE_SERVICE_ROLE_KEY: str | None = _get_env("SUPABASE_SERVICE_ROLE_KEY")

    @property
    def SUPABASE_ISSUER(self) -> str | None:
        if not self.SUPABASE_URL:
            return None
        return f"{self.SUPABASE_URL.rstrip('/')}/auth/v1"

    @property
    def SUPABASE_JWKS_URL(self) -> str | None:
        if not self.SUPABASE_ISSUER:
            return None
        return f"{self.SUPABASE_ISSUER}/.well-known/jwks.json"

    AGENT_API_KEY: str | None = _get_env("AGENT_API_KEY")
    AGENT_BASE_URL: str = (
        _get_env("AGENT_BASE_URL", default="https://api.fastgpt.ai/api/v1/chat/completions")
        or "https://api.fastgpt.ai/api/v1/chat/completions"
    )
    AGENT_MODEL_NAME: str = _get_env("AGENT_MODEL_NAME", default="fastgpt") or "fastgpt"
    AGENT_MODEL_TEMPERATURE: float = _get_float_env("AGENT_MODEL_TEMPERATURE", default=0.7)

    STRIPE_PUBLIC_KEY: str | None = _get_env("STRIPE_PUBLIC_KEY")
    STRIPE_PRIVATE_KEY: str | None = _get_env("STRIPE_PRIVATE_KEY")
    STRIPE_WEBHOOK_SECRET: str | None = _get_env("STRIPE_WEBHOOK_SECRET")

    MEMBERSHIP_FREE_NAME: str = _get_env("MEMBERSHIP_FREE_NAME", default="免费会员") or "免费会员"
    MEMBERSHIP_FREE_DAILY_MESSAGE_LIMIT: int = _get_int_env("MEMBERSHIP_FREE_DAILY_MESSAGE_LIMIT", default=100)
    MEMBERSHIP_FREE_DAILY_TOKEN_LIMIT: int = _get_int_env("MEMBERSHIP_FREE_DAILY_TOKEN_LIMIT", default=1000000)
    MEMBERSHIP_FREE_CONVERSATION_TURN_LIMIT: int = _get_int_env("MEMBERSHIP_FREE_CONVERSATION_TURN_LIMIT", default=10)
    MEMBERSHIP_FREE_PRICE: float = _get_float_env("MEMBERSHIP_FREE_PRICE", default=0.0)
    MEMBERSHIP_FREE_CURRENCY: str = _get_env("MEMBERSHIP_FREE_CURRENCY", default="USD") or "USD"
    MEMBERSHIP_FREE_DURATION_DAYS: int = _get_int_env("MEMBERSHIP_FREE_DURATION_DAYS", default=36500)
    MEMBERSHIP_FREE_DESCRIPTION: str = (
        _get_env("MEMBERSHIP_FREE_DESCRIPTION", default="免费用户基础计划") or "免费用户基础计划"
    )

    MEMBERSHIP_MONTHLY_NAME: str = _get_env("MEMBERSHIP_MONTHLY_NAME", default="月度会员") or "月度会员"
    MEMBERSHIP_MONTHLY_DAILY_MESSAGE_LIMIT: int = _get_int_env("MEMBERSHIP_MONTHLY_DAILY_MESSAGE_LIMIT", default=800)
    MEMBERSHIP_MONTHLY_DAILY_TOKEN_LIMIT: int = _get_int_env("MEMBERSHIP_MONTHLY_DAILY_TOKEN_LIMIT", default=8000000)
    MEMBERSHIP_MONTHLY_CONVERSATION_TURN_LIMIT: int = _get_int_env("MEMBERSHIP_MONTHLY_CONVERSATION_TURN_LIMIT", default=30)
    MEMBERSHIP_MONTHLY_PRICE: float = _get_float_env("MEMBERSHIP_MONTHLY_PRICE", default=9.9)
    MEMBERSHIP_MONTHLY_CURRENCY: str = _get_env("MEMBERSHIP_MONTHLY_CURRENCY", default="USD") or "USD"
    MEMBERSHIP_MONTHLY_DURATION_DAYS: int = _get_int_env("MEMBERSHIP_MONTHLY_DURATION_DAYS", default=30)
    MEMBERSHIP_MONTHLY_DESCRIPTION: str = (
        _get_env("MEMBERSHIP_MONTHLY_DESCRIPTION", default="月度付费会员计划") or "月度付费会员计划"
    )

    MEMBERSHIP_YEARLY_NAME: str = _get_env("MEMBERSHIP_YEARLY_NAME", default="年度会员") or "年度会员"
    MEMBERSHIP_YEARLY_DAILY_MESSAGE_LIMIT: int = _get_int_env("MEMBERSHIP_YEARLY_DAILY_MESSAGE_LIMIT", default=1000)
    MEMBERSHIP_YEARLY_DAILY_TOKEN_LIMIT: int = _get_int_env("MEMBERSHIP_YEARLY_DAILY_TOKEN_LIMIT", default=10000000)
    MEMBERSHIP_YEARLY_CONVERSATION_TURN_LIMIT: int = _get_int_env("MEMBERSHIP_YEARLY_CONVERSATION_TURN_LIMIT", default=50)
    MEMBERSHIP_YEARLY_PRICE: float = _get_float_env("MEMBERSHIP_YEARLY_PRICE", default=99.9)
    MEMBERSHIP_YEARLY_CURRENCY: str = _get_env("MEMBERSHIP_YEARLY_CURRENCY", default="USD") or "USD"
    MEMBERSHIP_YEARLY_DURATION_DAYS: int = _get_int_env("MEMBERSHIP_YEARLY_DURATION_DAYS", default=365)
    MEMBERSHIP_YEARLY_DESCRIPTION: str = (
        _get_env("MEMBERSHIP_YEARLY_DESCRIPTION", default="年度付费会员计划") or "年度付费会员计划"
    )

    def log_all_settings(self, logger):
        for attr_name in dir(self):
            if attr_name.startswith("_") or attr_name == "log_all_settings":
                continue

            attr_value = getattr(self, attr_name)
            if callable(attr_value):
                continue

            if attr_value:
                try:
                    parsed = urlparse(str(attr_value))
                    if parsed.scheme and parsed.netloc and parsed.password:
                        masked_value = str(attr_value).replace(f":{parsed.password}@", ":***@")
                        logger.info(f"[{self.ENV}] {attr_name}: {masked_value}")
                    elif any(sensitive in attr_name.upper() for sensitive in ["KEY", "PASSWORD", "SECRET"]):
                        value_str = str(attr_value)
                        masked_value = f"{value_str[:3]}***{value_str[-3:]}" if len(value_str) > 6 else "***"
                        logger.info(f"[{self.ENV}] {attr_name}: {masked_value}")
                    else:
                        logger.info(f"[{self.ENV}] {attr_name}: {attr_value}")
                except Exception:
                    if any(sensitive in attr_name.upper() for sensitive in ["KEY", "PASSWORD", "SECRET"]):
                        value_str = str(attr_value)
                        masked_value = f"{value_str[:3]}***{value_str[-3:]}" if len(value_str) > 6 else "***"
                        logger.info(f"[{self.ENV}] {attr_name}: {masked_value}")
                    else:
                        logger.info(f"[{self.ENV}] {attr_name}: {attr_value}")
            else:
                if any(sensitive in attr_name.upper() for sensitive in ["KEY", "PASSWORD", "SECRET"]):
                    logger.info(f"[{self.ENV}] {attr_name}: [not set]")
                else:
                    logger.info(f"[{self.ENV}] {attr_name}: {attr_value}")


settings = Settings()
