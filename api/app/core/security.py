import logging
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 获取日志记录器
logger = logging.getLogger(__name__)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    加密密码
    
    功能说明:
    使用 bcrypt 算法对明文密码进行哈希加密
    
    参数:
    - password: 明文密码
    
    返回:
    - str: 加密后的密码哈希值
    """
    logger.debug("开始加密密码")
    hashed = pwd_context.hash(password)
    logger.debug("密码加密完成")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    功能说明:
    验证明文密码与哈希密码是否匹配
    
    参数:
    - plain_password: 明文密码
    - hashed_password: 哈希密码
    
    返回:
    - bool: 密码匹配返回 True，否则返回 False
    """
    logger.debug("开始验证密码")
    is_valid = pwd_context.verify(plain_password, hashed_password)
    if is_valid:
        logger.info("密码验证成功")
    else:
        logger.warning("密码验证失败")
    return is_valid


def create_access_token(data: dict):
    """
    创建访问令牌
    
    功能说明:
    生成 JWT 访问令牌，用于用户身份验证
    
    参数:
    - data: 要编码到令牌中的数据字典
    
    返回:
    - str: JWT 访问令牌
    """
    logger.debug(f"开始创建访问令牌，数据: {data}")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    token = jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.AUTH_ALGORITHM)
    logger.info(f"访问令牌创建成功，过期时间: {expire.isoformat()}")
    return token


def create_refresh_token(data: dict):
    """
    创建刷新令牌
    
    功能说明:
    生成 JWT 刷新令牌，用于延长用户会话
    
    参数:
    - data: 要编码到令牌中的数据字典
    
    返回:
    - str: JWT 刷新令牌
    """
    logger.debug(f"开始创建刷新令牌，数据: {data}")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.AUTH_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    token = jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.AUTH_ALGORITHM)
    logger.info(f"刷新令牌创建成功，过期时间: {expire.isoformat()}")
    return token


def decode_token(token: str) -> dict | None:
    """
    解码 JWT 令牌
    
    功能说明:
    验证并解码 JWT 令牌，提取其中的数据
    
    参数:
    - token: JWT 令牌字符串
    
    返回:
    - dict | None: 解码后的数据字典，失败时返回 None
    """
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT 令牌解码失败: {str(e)}")
        return None
