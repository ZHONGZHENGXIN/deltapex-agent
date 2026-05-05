import contextvars
import hashlib
import logging
import re
import sys
import uuid
from typing import Any, Optional

import colorlog
import structlog

from app.core.config import settings


_trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|password|secret|token)\s*[:=]\s*([^\s,;]+)"
)

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "access_token",
    "refresh_token",
    "service_role_key",
)
NON_SECRET_KEYS = {
    "key_hash",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "tokens",
    "token_usage",
    "token_count",
    "daily_token_count",
    "daily_token_limit",
    "daily_token_remaining",
    "remaining_tokens",
    "required_paid_tokens",
    "available_paid_tokens",
    "remaining_free_tokens",
    "total_token_count",
}


def sanitize_trace_id(value: str | None) -> str | None:
    if not value:
        return None
    trace_id = re.sub(r"[^A-Za-z0-9_.:-]", "", value.strip())
    return trace_id[:128] or None


def new_trace_id() -> str:
    return uuid.uuid4().hex


def set_trace_id(trace_id: str | None = None) -> contextvars.Token:
    return _trace_id_var.set(sanitize_trace_id(trace_id) or new_trace_id())


def reset_trace_id(token: contextvars.Token) -> None:
    _trace_id_var.reset(token)


def get_trace_id() -> str | None:
    return _trace_id_var.get()


def key_fingerprint(secret: str | None) -> str | None:
    if not secret:
        return None
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]


def mask_email(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        first, _rest, domain = match.groups()
        return f"{first}***{domain}"

    return EMAIL_RE.sub(replace, value)


def mask_sensitive_text(value: str) -> str:
    masked = mask_email(value)
    masked = BEARER_RE.sub("Bearer ***", masked)
    masked = OPENAI_KEY_RE.sub("sk-***", masked)
    masked = SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=***", masked)
    return masked


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    if normalized in NON_SECRET_KEYS:
        return False
    if "email" in normalized:
        return False
    if normalized == "token":
        return True
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_log_fields(value: Any, key: str | None = None) -> Any:
    if key and _is_sensitive_key(key):
        return "***"
    if isinstance(value, str):
        return mask_sensitive_text(value)
    if isinstance(value, dict):
        return {item_key: sanitize_log_fields(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_log_fields(item) for item in value]
    return value


def _add_trace_id(_logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict.setdefault("trace_id", get_trace_id() or "none")
    return event_dict


def _sanitize_structured_event(_logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return sanitize_log_fields(event_dict)


def setup_logging(level: Optional[str] = None) -> None:
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    elif settings.ENV == "prod":
        log_level = logging.INFO
    elif settings.ENV == "test":
        log_level = logging.ERROR
    else:
        log_level = logging.DEBUG

    color_formatter = colorlog.ColoredFormatter(
        "%(asctime)s - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(color_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)

    structlog.configure(
        processors=[
            _add_trace_id,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _sanitize_structured_event,
            structlog.processors.JSONRenderer(ensure_ascii=False, sort_keys=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if settings.ENV == "dev":
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)

        if settings.POSTGRES_ECHO:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.INFO)
        else:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    else:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

        if not settings.POSTGRES_ECHO:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_structured_logger(name: str):
    return structlog.get_logger(name)
