import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENV: str = os.getenv("ENV", "dev")

    AUTH_SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "default-secret")
    AUTH_ALGORITHM: str = os.getenv("AUTH_ALGORITHM", "HS256")
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    AUTH_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("AUTH_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    AUTH_IS_DEBUG: bool = os.getenv("AUTH_IS_DEBUG", "False").lower() in ("true", "1", "yes")
    AUTH_DEBUG_CODE: str = os.getenv("AUTH_DEBUG_CODE", "888888")

    API_NAME: str = os.getenv("API_NAME", "API")
    API_VERSION: str = os.getenv("API_VERSION", "0.1.0")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "False").lower() in ("true", "1", "yes")

    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "123456")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "bait")
    POSTGRES_ECHO: bool = os.getenv("POSTGRES_ECHO", "False").lower() in ("true", "1", "yes")
    POSTGRES_POOL_SIZE: int = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
    POSTGRES_MAX_OVERFLOW: int = int(os.getenv("POSTGRES_MAX_OVERFLOW", "30"))
    POSTGRES_POOL_TIMEOUT: int = int(os.getenv("POSTGRES_POOL_TIMEOUT", "30"))
    POSTGRES_POOL_RECYCLE: int = int(os.getenv("POSTGRES_POOL_RECYCLE", "3600"))
    POSTGRES_POOL_PRE_PING: bool = os.getenv("POSTGRES_POOL_PRE_PING", "True").lower() in ("true", "1", "yes")

    @property
    def POSTGRES_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_USER: str = os.getenv("REDIS_USER", "default")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "123456")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    MAIL_SEND_METHOD: str = os.getenv("MAIL_SEND_METHOD", "SMTP")
    MAIL_USERNAME: str | None = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str | None = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str | None = os.getenv("MAIL_FROM")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_SERVER: str | None = os.getenv("MAIL_SERVER")
    RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY")
    RESEND_MAIL_FROM: str | None = os.getenv("RESEND_MAIL_FROM")

    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_JWT_AUDIENCE: str = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

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

    AGENT_API_KEY: str | None = os.getenv("AGENT_API_KEY")
    AGENT_BASE_URL: str = os.getenv("AGENT_BASE_URL", "https://api.fastgpt.ai/api/v1/chat/completions")
    AGENT_MODEL_NAME: str = os.getenv("AGENT_MODEL_NAME", "fastgpt")
    AGENT_MODEL_TEMPERATURE: float = float(os.getenv("AGENT_MODEL_TEMPERATURE", "0.7"))

    STRIPE_PUBLIC_KEY: str | None = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_PRIVATE_KEY: str | None = os.getenv("STRIPE_PRIVATE_KEY")
    STRIPE_WEBHOOK_SECRET: str | None = os.getenv("STRIPE_WEBHOOK_SECRET")

    MEMBERSHIP_FREE_NAME: str = os.getenv("MEMBERSHIP_FREE_NAME", "免费会员")
    MEMBERSHIP_FREE_DAILY_MESSAGE_LIMIT: int = int(os.getenv("MEMBERSHIP_FREE_DAILY_MESSAGE_LIMIT", "100"))
    MEMBERSHIP_FREE_DAILY_TOKEN_LIMIT: int = int(os.getenv("MEMBERSHIP_FREE_DAILY_TOKEN_LIMIT", "1000000"))
    MEMBERSHIP_FREE_CONVERSATION_TURN_LIMIT: int = int(os.getenv("MEMBERSHIP_FREE_CONVERSATION_TURN_LIMIT", "10"))
    MEMBERSHIP_FREE_PRICE: float = float(os.getenv("MEMBERSHIP_FREE_PRICE", "0.0"))
    MEMBERSHIP_FREE_CURRENCY: str = os.getenv("MEMBERSHIP_FREE_CURRENCY", "USD")
    MEMBERSHIP_FREE_DURATION_DAYS: int = int(os.getenv("MEMBERSHIP_FREE_DURATION_DAYS", "36500"))
    MEMBERSHIP_FREE_DESCRIPTION: str = os.getenv("MEMBERSHIP_FREE_DESCRIPTION", "免费用户基础计划")

    MEMBERSHIP_MONTHLY_NAME: str = os.getenv("MEMBERSHIP_MONTHLY_NAME", "月度会员")
    MEMBERSHIP_MONTHLY_DAILY_MESSAGE_LIMIT: int = int(os.getenv("MEMBERSHIP_MONTHLY_DAILY_MESSAGE_LIMIT", "800"))
    MEMBERSHIP_MONTHLY_DAILY_TOKEN_LIMIT: int = int(os.getenv("MEMBERSHIP_MONTHLY_DAILY_TOKEN_LIMIT", "8000000"))
    MEMBERSHIP_MONTHLY_CONVERSATION_TURN_LIMIT: int = int(os.getenv("MEMBERSHIP_MONTHLY_CONVERSATION_TURN_LIMIT", "30"))
    MEMBERSHIP_MONTHLY_PRICE: float = float(os.getenv("MEMBERSHIP_MONTHLY_PRICE", "9.9"))
    MEMBERSHIP_MONTHLY_CURRENCY: str = os.getenv("MEMBERSHIP_MONTHLY_CURRENCY", "USD")
    MEMBERSHIP_MONTHLY_DURATION_DAYS: int = int(os.getenv("MEMBERSHIP_MONTHLY_DURATION_DAYS", "30"))
    MEMBERSHIP_MONTHLY_DESCRIPTION: str = os.getenv("MEMBERSHIP_MONTHLY_DESCRIPTION", "月度付费会员计划")

    MEMBERSHIP_YEARLY_NAME: str = os.getenv("MEMBERSHIP_YEARLY_NAME", "年度会员")
    MEMBERSHIP_YEARLY_DAILY_MESSAGE_LIMIT: int = int(os.getenv("MEMBERSHIP_YEARLY_DAILY_MESSAGE_LIMIT", "1000"))
    MEMBERSHIP_YEARLY_DAILY_TOKEN_LIMIT: int = int(os.getenv("MEMBERSHIP_YEARLY_DAILY_TOKEN_LIMIT", "10000000"))
    MEMBERSHIP_YEARLY_CONVERSATION_TURN_LIMIT: int = int(os.getenv("MEMBERSHIP_YEARLY_CONVERSATION_TURN_LIMIT", "50"))
    MEMBERSHIP_YEARLY_PRICE: float = float(os.getenv("MEMBERSHIP_YEARLY_PRICE", "99.9"))
    MEMBERSHIP_YEARLY_CURRENCY: str = os.getenv("MEMBERSHIP_YEARLY_CURRENCY", "USD")
    MEMBERSHIP_YEARLY_DURATION_DAYS: int = int(os.getenv("MEMBERSHIP_YEARLY_DURATION_DAYS", "365"))
    MEMBERSHIP_YEARLY_DESCRIPTION: str = os.getenv("MEMBERSHIP_YEARLY_DESCRIPTION", "年度付费会员计划")

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
