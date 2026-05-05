from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

import app.routers.v1.chat as chat_api
import app.services.rate_limit_service as rate_limit_module
from app.core.config import settings
from app.crud.membership import increment_user_membership_usage_atomic
from app.db.base import get_session
from app.dependencies.db import get_redis, get_user
from app.main import BASE_PREFIX, app
from app.models.agent import Agent, AgentSource
from app.models.billing import UserTokenWallet
from app.models.chat import Chat
from app.models.membership import MembershipPlan, UserMembership
from app.models.message import Message
from app.models.user import User, UserType
from app.schemas.membership import MembershipType
from app.services.rate_limit_service import ChatRateLimiter, RateLimitExceeded


CHAT_ID = "55555555-5555-4555-8555-555555555555"


class FakeRedis:
    def __init__(self):
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True

    def ttl(self, key: str) -> int:
        return self.expirations.get(key, -1)


def test_chat_rate_limiter_blocks_31st_request_without_internal_detail(monkeypatch):
    monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_777_777_777.0)
    redis_client = FakeRedis()
    limiter = ChatRateLimiter(enabled=True, max_requests=30, window_seconds=1)

    for _ in range(30):
        limiter.check_message_send(redis_client, user_id=1)

    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.check_message_send(redis_client, user_id=1)

    error_text = str(exc_info.value).lower()
    assert "redis" not in error_text
    assert "rate:" not in error_text
    assert "too many requests" in error_text


@pytest.fixture()
def rate_limited_chat_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        Agent.__table__,
        User.__table__,
        MembershipPlan.__table__,
        UserMembership.__table__,
        UserTokenWallet.__table__,
        Chat.__table__,
        Message.__table__,
    ):
        table.create(engine)

    fake_redis = FakeRedis()
    monkeypatch.setattr(settings, "MEMORY_CONTEXT_ENABLED", False)
    monkeypatch.setattr(settings, "CHAT_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "CHAT_RATE_LIMIT_MAX_REQUESTS", 30)
    monkeypatch.setattr(settings, "CHAT_RATE_LIMIT_WINDOW_SECONDS", 1)
    monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_777_777_777.0)

    async def fake_create_agent_response(messages, agent, user_id, chat_id, session=None, memory_context=None):
        return "assistant ok", {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}

    monkeypatch.setattr(chat_api, "create_agent_response", fake_create_agent_response)

    now = datetime.utcnow()
    student_id = 1
    student = User(
        id=student_id,
        username="rate-limited-student",
        email="rate-limited-student@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    auth_user = User(
        id=student_id,
        username="rate-limited-student",
        email="rate-limited-student@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    with Session(engine) as session:
        session.add(
            Agent(
                id=1,
                name="Gateway Coach",
                source=AgentSource.LLM,
                api_url="http://one-api:3000/v1",
                api_key="gateway-reference",
                model_conf={"model": "gateway-model"},
                is_think=False,
                is_stream=False,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(student)
        session.add(
            MembershipPlan(
                id=1,
                name="Monthly",
                type=MembershipType.MONTHLY,
                daily_message_limit=1_000,
                daily_token_limit=1_000_000,
                conversation_turn_limit=1_000,
                price=9.9,
                currency="USD",
                duration_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserMembership(
                id=1,
                user_id=student_id,
                membership_plan_id=1,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=30),
                is_active=True,
                daily_message_count=0,
                daily_token_count=0,
                daily_chat_count=0,
                total_message_count=0,
                total_token_count=0,
                total_chat_count=1,
                last_reset_date=now,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserTokenWallet(
                id=1,
                user_id=student_id,
                paid_token_balance=0,
                total_recharged_tokens=0,
                total_consumed_paid_tokens=0,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Chat(
                id=10,
                public_id=CHAT_ID,
                user_id=student_id,
                title="Rate limited chat",
                agent_id=1,
                others={},
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    def override_user():
        return auth_user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_user] = override_user
    app.dependency_overrides[get_redis] = lambda: fake_redis

    try:
        yield TestClient(app), engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_user, None)
        app.dependency_overrides.pop(get_redis, None)


def test_chat_message_endpoint_blocks_after_30_requests(rate_limited_chat_client):
    client, engine = rate_limited_chat_client

    for index in range(30):
        response = client.post(
            f"{BASE_PREFIX}/chat/message",
            json={"chat_id": CHAT_ID, "content": f"message {index}"},
        )
        assert response.status_code == 200

    blocked = client.post(
        f"{BASE_PREFIX}/chat/message",
        json={"chat_id": CHAT_ID, "content": "message 31"},
    )

    assert blocked.status_code == 429
    assert "redis" not in blocked.text.lower()
    assert "rate:" not in blocked.text
    with Session(engine) as session:
        messages = session.exec(select(Message)).all()
    assert len(messages) == 60


def test_atomic_membership_usage_increment_handles_100_concurrent_requests(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'usage.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        dbapi_connection.execute("PRAGMA busy_timeout=30000")

    MembershipPlan.__table__.create(engine)
    UserMembership.__table__.create(engine)

    now = datetime.utcnow()
    with Session(engine) as session:
        session.add(
            MembershipPlan(
                id=1,
                name="Monthly",
                type=MembershipType.MONTHLY,
                daily_message_limit=1_000,
                daily_token_limit=1_000_000,
                conversation_turn_limit=1_000,
                price=9.9,
                currency="USD",
                duration_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserMembership(
                id=1,
                user_id=1,
                membership_plan_id=1,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=30),
                is_active=True,
                daily_message_count=0,
                daily_token_count=0,
                daily_chat_count=0,
                total_message_count=0,
                total_token_count=0,
                total_chat_count=0,
                last_reset_date=now,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    def increment_once():
        with Session(engine) as session:
            return increment_user_membership_usage_atomic(
                session,
                user_id=1,
                message_count=1,
                token_count=2,
            )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: increment_once(), range(100)))

    assert all(results)
    with Session(engine) as session:
        membership = session.get(UserMembership, 1)
    assert membership.daily_message_count == 100
    assert membership.total_message_count == 100
    assert membership.daily_token_count == 200
    assert membership.total_token_count == 200
