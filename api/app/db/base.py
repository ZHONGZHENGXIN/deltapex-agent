import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.agent import create_default_agent
from app.services.membership_service import MembershipService

logger = get_logger(__name__)

engine = create_engine(
    settings.POSTGRES_URL, 
    echo=settings.POSTGRES_ECHO,
    # PostgreSQL 连接池配置 - 通过环境变量配置，支持不同环境的灵活调整
    pool_size=settings.POSTGRES_POOL_SIZE,          # 连接池大小，默认 20
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,    # 超出连接池大小时的最大额外连接数，默认 30
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,    # 获取连接的超时时间（秒），默认 30
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,    # 连接回收时间（秒），防止连接过期，默认 3600
    pool_pre_ping=settings.POSTGRES_POOL_PRE_PING,  # 连接前检查连接有效性，默认 True
)


def create_database_if_not_exists():
    """
    检查并创建数据库（如果不存在）

    功能说明:
    - 解析数据库连接字符串
    - 连接到 PostgreSQL 服务器
    - 检查目标数据库是否存在
    - 如果不存在则创建数据库

    异常:
    - psycopg2.Error: 数据库连接或操作失败
    """
    try:
        # 使用拆分的数据库配置变量
        database_name = settings.POSTGRES_DB

        # 构建连接到 postgres 默认数据库的 URL（用于创建新数据库）
        admin_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
        # 连接到 PostgreSQL 服务器
        conn = psycopg2.connect(admin_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # 检查数据库是否存在
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (database_name,))
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"数据库 '{database_name}' 不存在，正在创建...")
            cursor.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(f"数据库 '{database_name}' 创建成功")
        else:
            logger.info(f"数据库 '{database_name}' 已存在")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"创建数据库时出错: {e}")
        raise


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """创建数据库表结构"""
    try:
        logger.info("正在创建数据库...")
        create_database_if_not_exists()
        logger.info("正在创建数据表...")
        SQLModel.metadata.create_all(engine)
        logger.info("数据表创建成功")
    except Exception as e:
        logger.error(f"创建数据表失败: {e}")
        raise


def init_default_agent():
    """初始化默认 Agent（在表创建之后调用）"""
    logger.info("正在初始化默认 Agent...")
    with Session(engine) as session:
        try:
            create_default_agent(session)
        except Exception as e:
            logger.error(f"创建默认 Agent 时出错: {e}")
            raise
    logger.info("默认 Agent 初始化完成")


def init_default_membership_plans():
    """初始化默认会员计划（在表创建之后调用）"""
    logger.info("正在初始化默认会员计划...")
    with Session(engine) as session:
        try:
            membership_service = MembershipService(session)
            membership_service.initialize_default_plans()
        except Exception as e:
            logger.error(f"初始化默认会员计划时出错: {e}")
            raise

    logger.info("默认会员计划初始化完成")
