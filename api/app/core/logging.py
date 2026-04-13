import logging
import sys
from typing import Optional

import colorlog

from app.core.config import settings


def setup_logging(level: Optional[str] = None) -> None:
    """
    配置应用程序日志系统

    功能说明:
    - 根据环境变量设置日志级别
    - 配置彩色日志格式和输出目标
    - 为不同模块设置合适的日志级别

    参数:
    - level: 可选的日志级别覆盖
    """
    # 根据环境确定默认日志级别
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    elif settings.ENV == "prod":
        log_level = logging.WARNING
    elif settings.ENV == "test":
        log_level = logging.ERROR
    else:  # dev - 开发环境使用 DEBUG 级别显示更多信息
        log_level = logging.DEBUG

    # 创建彩色日志格式器 - 只对日志等级部分着色
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

    # 创建控制台处理器并设置格式器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(color_formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 添加彩色处理器
    root_logger.addHandler(console_handler)

    # 配置第三方库的日志级别
    if settings.ENV == "dev":
        # 开发环境显示更多第三方库信息
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)

        # 如果启用数据库日志，显示 SQLAlchemy 详细信息
        if settings.POSTGRES_ECHO:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.INFO)
        else:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    else:
        # 生产和测试环境保持原有设置
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

        # 如果不启用数据库日志，则禁用 SQLAlchemy 的日志
        if not settings.POSTGRES_ECHO:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器

    参数:
    - name: 日志器名称，通常使用模块名

    返回:
    - Logger: 配置好的日志器实例
    """
    return logging.getLogger(name)
