import random
import string
from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader
from redis import Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
# initialize Jinja2 environment
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

# initialize Resend
resend.api_key = settings.RESEND_API_KEY


def _get_fastmail_client():
    from fastapi_mail import ConnectionConfig, FastMail

    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )
    return FastMail(conf)


# Generate verification code
def generate_verification_code():
    """Generate a 6-digit numeric verification code, first digit cannot be 0"""
    first_digit = random.choice(string.digits[1:])
    other_digits = "".join(random.choices(string.digits, k=5))
    return first_digit + other_digits


async def send_verification_code(email: str, lang: str, redis: Redis, purpose: str = "login") -> bool:
    """Send verification code to the specified email and store it in Redis, supports multiple language templates and purposes"""
    if settings.AUTH_IS_DEBUG:
        code = settings.AUTH_DEBUG_CODE
    else:
        code = generate_verification_code()
    
    # Store code with purpose prefix
    code_key = f"bait-api:code:{purpose}:{email}"
    redis.setex(code_key, 300, code)  # 5 minutes = 300 seconds

    if not settings.AUTH_IS_DEBUG:
        # Choose template based on purpose and language
        if purpose == "register":
            if lang == "zh":
                template_name = "email_code_register_mail_template_zh.html"
            else:
                template_name = "email_code_register_mail_template_en.html"
            subject = "Build AI Template Registration Code" if lang == "en" else "Build AI Template 的注册验证码"
        elif purpose == "reset":
            if lang == "zh":
                template_name = "email_code_reset_mail_template_zh.html"
            else:
                template_name = "email_code_reset_mail_template_en.html"
            subject = "Build AI Template Password Reset Code" if lang == "en" else "Build AI Template 的密码重置验证码"
        else:  # login
            if lang == "zh":
                template_name = "email_code_login_mail_template_zh.html"
            else:
                template_name = "email_code_login_mail_template_en.html"
            subject = "Build AI Template Login Code" if lang == "en" else "Build AI Template 的登录验证码"
        template = jinja_env.get_template(template_name)
        html_body = template.render(code=code)

        logger.info(f"Send {code} to {email} with {settings.MAIL_SEND_METHOD}")
        if settings.MAIL_SEND_METHOD == "RESEND":
            try:
                r = resend.Emails.send(
                    {
                        "from": settings.RESEND_MAIL_FROM,
                        "to": email,
                        "subject": subject,
                        "html": html_body,
                    }
                )
                logger.info(f"Resend email sent successfully: {r}")
            except Exception as e:
                logger.error(f"Resend email sent failed: {e}")
                raise e
        else:
            try:
                from fastapi_mail import MessageSchema

                fastmail = _get_fastmail_client()
                message = MessageSchema(subject=subject, recipients=[email], body=html_body, subtype="html")
                await fastmail.send_message(message)
                logger.info(f"SMTP email sent successfully: {message}")
            except Exception as e:
                logger.error(f"SMTP email sent failed: {e}")
                raise e


def verify_code(email: str, code: str, redis: Redis, purpose: str = "login") -> bool:
    """Verify email verification code (check from Redis) based on purpose"""
    code_key = f"bait-api:code:{purpose}:{email}"
    stored_code = redis.get(code_key)
    if stored_code and code == stored_code:
        redis.delete(code_key)
        return True
    return False
