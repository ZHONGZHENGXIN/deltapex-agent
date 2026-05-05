import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

import app.routers.v1.chat as chat_api
from app.core.config import settings
from app.db.base import get_session
from app.dependencies.db import get_user
from app.main import BASE_PREFIX, app
from app.models.agent import Agent, AgentSource
from app.models.billing import UserTokenWallet
from app.models.chat import Chat
from app.models.membership import MembershipPlan, UserMembership
from app.models.message import Message
from app.models.user import User, UserType
from app.schemas.membership import MembershipType
from app.schemas.message import MessageRole
from app.services.content_moderation_service import ContentModerationService, RULES_PATH


CHAT_ID = "66666666-6666-4666-8666-666666666666"


@pytest.fixture()
def moderation_chat_client(monkeypatch):
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

    monkeypatch.setattr(settings, "MEMORY_CONTEXT_ENABLED", False)
    monkeypatch.setattr(settings, "CONTENT_MODERATION_ENABLED", True)
    monkeypatch.setattr(settings, "COMPLIANCE_SUPPORT_CONTACT", "Deltapex support")
    captured = {"provider_called": False}

    async def fake_create_agent_response(messages, agent, user_id, chat_id, session=None, memory_context=None):
        captured["provider_called"] = True
        return "这只股票必涨，保证赚钱，而且无风险。", {
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
        }

    monkeypatch.setattr(chat_api, "create_agent_response", fake_create_agent_response)

    now = datetime.utcnow()
    student_id = 1
    student = User(
        id=student_id,
        username="moderation-student",
        email="moderation-student@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    auth_user = User(
        id=student_id,
        username="moderation-student",
        email="moderation-student@example.test",
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
                title="Moderation chat",
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

    try:
        yield TestClient(app), engine, captured
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_user, None)


def test_rules_file_is_loadable_and_contains_required_categories():
    assert RULES_PATH.exists()
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    assert {"financial_risk", "distress"}.issubset(rules.keys())
    result = ContentModerationService().inspect("保证赚钱 no risk-free strategy")
    assert result.has_financial_risk
    assert "financial_risk" in result.categories


def test_risky_ai_output_gets_compliance_notice(moderation_chat_client):
    client, engine, captured = moderation_chat_client

    response = client.post(
        f"{BASE_PREFIX}/chat/message",
        json={"chat_id": CHAT_ID, "content": "给我一个交易结论"},
    )

    assert response.status_code == 200
    assert captured["provider_called"] is True
    payload = response.json()
    assistant_content = payload[1]["content"]
    assert "保证赚钱" in assistant_content
    assert "不构成投资建议" in assistant_content

    with Session(engine) as session:
        assistant_message = session.exec(select(Message).where(Message.role == MessageRole.ASSISTANT)).one()
    assert "不构成投资建议" in assistant_message.content


def test_distress_input_returns_human_support_and_skips_provider(moderation_chat_client):
    client, engine, captured = moderation_chat_client

    response = client.post(
        f"{BASE_PREFIX}/chat/message?stream=true",
        json={"chat_id": CHAT_ID, "content": "我严重亏损，不想活了"},
    )

    assert response.status_code == 200
    assert captured["provider_called"] is False
    assert "人工支持" in response.text
    assert "紧急救援" in response.text

    with Session(engine) as session:
        messages = session.exec(select(Message).order_by(Message.id)).all()
    assert [message.role for message in messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert "人工支持" in messages[1].content
