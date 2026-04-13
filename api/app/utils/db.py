import redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_redis_client():
    """
    获取 Redis 客户端连接

    返回:
    - redis.Redis: Redis 客户端实例

    异常:
    - ConnectionError: Redis 连接失败
    - Exception: 其他 Redis 相关错误
    """
    try:
        logger.info("正在连接 Redis...")
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # 测试连接
        client.ping()
        logger.info("Redis 连接成功")
        return client
    except redis.ConnectionError as e:
        logger.error(f"Redis 连接失败: {e}")
        raise ConnectionError(f"无法连接到 Redis 服务器: {e}")
    except Exception as e:
        logger.error(f"Redis 初始化失败: {e}")
        raise
