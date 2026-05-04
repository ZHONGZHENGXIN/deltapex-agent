from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from app.db.base import get_session
from app.dependencies.db import get_user
from app.main import BASE_PREFIX, app
from app.models.agent import Agent, AgentSource
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User, UserType


DIFY_CHAT_ID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture()
def dify_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Agent.__table__.create(engine)
    Chat.__table__.create(engine)
    Message.__table__.create(engine)

    now = datetime(2026, 1, 1)
    student = User(
        id=1,
        username="student",
        email="student@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    admin = User(
        id=2,
        username="admin",
        email="admin@example.test",
        user_type=UserType.ADMIN,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    with Session(engine) as session:
        session.add_all(
            [
                Agent(
                    id=1,
                    name="Dify Coach",
                    source=AgentSource.DIFY,
                    api_url="https://api.dify.ai/v1/chat-messages",
                    api_key="dify-secret",
                    model_conf={"inputs": {}},
                    is_think=False,
                    is_stream=True,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
                Agent(
                    id=2,
                    name="LLM Coach",
                    source=AgentSource.LLM,
                    api_url="http://one-api:3000/v1",
                    api_key="gateway-token-reference",
                    model_conf={"model": "fastgpt"},
                    is_think=False,
                    is_stream=True,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
                Chat(
                    id=10,
                    public_id=DIFY_CHAT_ID,
                    user_id=student.id,
                    title="Legacy Dify Chat",
                    agent_id=1,
                    others={"conversation_id": "provider-state"},
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

    current_user = {"value": student}

    def override_session():
        with Session(engine) as session:
            yield session

    def override_user():
        return current_user["value"]

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_user] = override_user

    try:
        yield TestClient(app), current_user, student, admin, engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_user, None)


def test_student_active_agents_do_not_include_dify(dify_client):
    client, current_user, student, admin, engine = dify_client
    current_user["value"] = student

    response = client.get(f"{BASE_PREFIX}/chat/agents/active")

    assert response.status_code == 200
    payload = response.json()
    assert [agent["source"] for agent in payload] == [AgentSource.LLM.value]
    assert "dify-secret" not in response.text


def test_admin_active_agents_can_still_see_dify(dify_client):
    client, current_user, student, admin, engine = dify_client
    current_user["value"] = admin

    response = client.get(f"{BASE_PREFIX}/chat/agents/active")

    assert response.status_code == 200
    sources = {agent["source"] for agent in response.json()}
    assert AgentSource.DIFY.value in sources
    assert AgentSource.LLM.value in sources
    assert "dify-secret" not in response.text


def test_student_cannot_create_chat_with_dify_agent(dify_client):
    client, current_user, student, admin, engine = dify_client
    current_user["value"] = student

    response = client.post(f"{BASE_PREFIX}/chat", json={"title": "Blocked", "agent_id": 1})

    assert response.status_code == 403
    with Session(engine) as session:
        chats = session.exec(select(Chat).where(Chat.title == "Blocked")).all()
    assert chats == []


def test_student_cannot_send_message_to_existing_dify_chat(dify_client):
    client, current_user, student, admin, engine = dify_client
    current_user["value"] = student

    response = client.post(
        f"{BASE_PREFIX}/chat/message",
        json={"chat_id": DIFY_CHAT_ID, "content": "should not reach Dify"},
    )

    assert response.status_code == 403
    with Session(engine) as session:
        messages = session.exec(select(Message)).all()
    assert messages == []
