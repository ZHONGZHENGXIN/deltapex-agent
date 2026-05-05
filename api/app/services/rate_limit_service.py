import time
from dataclasses import dataclass

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_structured_logger

logger = get_structured_logger("app.rate_limit")

RATE_LIMIT_MESSAGE = "Too many requests. Please slow down and try again."


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(RATE_LIMIT_MESSAGE)


@dataclass(frozen=True)
class ChatRateLimiter:
    enabled: bool
    max_requests: int
    window_seconds: int

    @classmethod
    def from_settings(cls) -> "ChatRateLimiter":
        return cls(
            enabled=settings.CHAT_RATE_LIMIT_ENABLED,
            max_requests=settings.CHAT_RATE_LIMIT_MAX_REQUESTS,
            window_seconds=settings.CHAT_RATE_LIMIT_WINDOW_SECONDS,
        )

    def check_message_send(self, redis_client, user_id: int) -> None:
        if not self.enabled or redis_client is None:
            return

        max_requests = max(1, self.max_requests)
        window_seconds = max(1, self.window_seconds)
        bucket = int(time.time() // window_seconds)
        key = f"rate:chat-message:{user_id}:{bucket}"

        try:
            count = int(redis_client.incr(key))
            if count == 1:
                redis_client.expire(key, window_seconds + 1)
            if count > max_requests:
                retry_after = _get_retry_after(redis_client, key)
                logger.warning(
                    "chat_rate_limit_exceeded",
                    user_id=user_id,
                    window_seconds=window_seconds,
                    max_requests=max_requests,
                    retry_after_seconds=retry_after,
                )
                raise RateLimitExceeded(retry_after)
        except RateLimitExceeded:
            raise
        except RedisError as exc:
            logger.warning(
                "chat_rate_limit_redis_error",
                user_id=user_id,
                error_type=type(exc).__name__,
            )
            raise RateLimitExceeded() from exc


def _get_retry_after(redis_client, key: str) -> int | None:
    try:
        ttl = int(redis_client.ttl(key))
    except (TypeError, ValueError, RedisError):
        return None
    return ttl if ttl > 0 else None
