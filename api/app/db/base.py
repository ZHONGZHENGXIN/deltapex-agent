import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.agent import create_default_agent
from app.models.billing import TokenPackage, TokenTopupOrder, UserTokenWallet
from app.models.chat import Chat
from app.models.memory import ChatSummary, StudentProfile
from app.models.membership import MembershipPlan, UserMembership
from app.models.message import Message
from app.models.order import Order
from app.models.user import User
from app.services.billing_service import BillingService
from app.services.membership_service import MembershipService

logger = get_logger(__name__)

engine = create_engine(
    settings.POSTGRES_URL,
    echo=settings.POSTGRES_ECHO,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
    pool_pre_ping=settings.POSTGRES_POOL_PRE_PING,
)


def create_database_if_not_exists():
    database_name = settings.POSTGRES_DB
    admin_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )

    try:
        conn = psycopg2.connect(admin_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (database_name,))
        exists = cursor.fetchone()

        if not exists:
            logger.info(f"Database '{database_name}' does not exist, creating it")
            cursor.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(f"Database '{database_name}' created")
        else:
            logger.info(f"Database '{database_name}' already exists")

        cursor.close()
        conn.close()
    except Exception as exc:
        logger.error(f"Failed to create database: {exc}")
        raise


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    try:
        logger.info("Creating database and tables")
        create_database_if_not_exists()
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables are ready")
    except Exception as exc:
        logger.error(f"Failed to create database tables: {exc}")
        raise


def init_default_agent():
    logger.info("Initializing default agent")
    with Session(engine) as session:
        create_default_agent(session)


def init_default_membership_plans():
    logger.info("Initializing default membership plans")
    with Session(engine) as session:
        membership_service = MembershipService(session)
        membership_service.initialize_default_plans()


def init_default_token_packages():
    logger.info("Initializing default token packages")
    with Session(engine) as session:
        billing_service = BillingService(session)
        billing_service.initialize_default_token_packages()
