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
from app.schemas.message import MessageRole


BOB_CHAT_ID = "22222222-2222-4222-8222-222222222222"
ALICE_CHAT_ID = "11111111-1111-4111-8111-111111111111"
BOB_SECRET = "bob private coaching note"


@pytest.fixture()
def cross_user_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Agent.__table__.create(engine)
    Chat.__table__.create(engine)
    Message.__table__.create(engine)

    now = datetime(2026, 1, 1)
    alice = User(
        id=1,
        username="alice",
        email="alice@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    bob = User(
        id=2,
        username="bob",
        email="bob@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    with Session(engine) as session:
        session.add(
            Agent(
                id=1,
                name="Coach",
                source=AgentSource.FASTGPT,
                api_url="https://example.test/api",
                api_key="secret",
                model_conf=None,
                is_think=False,
                is_stream=False,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add_all(
            [
                Chat(
                    id=10,
                    public_id=ALICE_CHAT_ID,
                    user_id=alice.id,
                    title="Alice chat",
                    agent_id=1,
                    others={},
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
                Chat(
                    id=20,
                    public_id=BOB_CHAT_ID,
                    user_id=bob.id,
                    title="Bob chat",
                    agent_id=1,
                    others={},
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.add_all(
            [
                Message(
                    id=100,
                    chat_id=10,
                    user_id=alice.id,
                    content="alice message",
                    model_conf=None,
                    role=MessageRole.USER,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
                Message(
                    id=200,
                    chat_id=20,
                    user_id=bob.id,
                    content=BOB_SECRET,
                    model_conf=None,
                    role=MessageRole.USER,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

    current_user = {"value": alice}

    def override_session():
        with Session(engine) as session:
            yield session

    def override_user():
        return current_user["value"]

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_user] = override_user

    try:
        yield TestClient(app), current_user, alice, bob, engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_user, None)


def test_alice_cannot_read_bob_chat(cross_user_client):
    client, current_user, alice, bob, engine = cross_user_client
    current_user["value"] = alice

    response = client.get(f"{BASE_PREFIX}/chat/{BOB_CHAT_ID}")

    assert response.status_code == 404
    assert BOB_SECRET not in response.text
    assert "Bob chat" not in response.text


def test_alice_cannot_send_message_to_bob_chat(cross_user_client):
    client, current_user, alice, bob, engine = cross_user_client
    current_user["value"] = alice

    response = client.post(
        f"{BASE_PREFIX}/chat/message",
        json={"chat_id": BOB_CHAT_ID, "content": "attempted intrusion"},
    )

    assert response.status_code == 404
    assert BOB_SECRET not in response.text

    with Session(engine) as session:
        messages = session.exec(select(Message).where(Message.chat_id == 20)).all()
    assert [message.content for message in messages] == [BOB_SECRET]


def test_alice_cannot_update_or_delete_bob_chat(cross_user_client):
    client, current_user, alice, bob, engine = cross_user_client
    current_user["value"] = alice

    update_response = client.put(f"{BASE_PREFIX}/chat/{BOB_CHAT_ID}", json={"title": "hijacked"})
    delete_response = client.delete(f"{BASE_PREFIX}/chat/{BOB_CHAT_ID}")

    assert update_response.status_code == 404
    assert delete_response.status_code == 404

    with Session(engine) as session:
        bob_chat = session.exec(select(Chat).where(Chat.public_id == BOB_CHAT_ID)).one()
    assert bob_chat.title == "Bob chat"
    assert bob_chat.is_deleted is False


def test_alice_chat_list_does_not_include_bob_data(cross_user_client):
    client, current_user, alice, bob, engine = cross_user_client
    current_user["value"] = alice

    response = client.get(f"{BASE_PREFIX}/chat?include_messages=true")

    assert response.status_code == 200
    payload = response.json()
    assert [chat["id"] for chat in payload] == [ALICE_CHAT_ID]
    assert BOB_CHAT_ID not in response.text
    assert BOB_SECRET not in response.text
    assert "Bob chat" not in response.text


def test_bob_can_read_his_own_chat(cross_user_client):
    client, current_user, alice, bob, engine = cross_user_client
    current_user["value"] = bob

    response = client.get(f"{BASE_PREFIX}/chat/{BOB_CHAT_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == BOB_CHAT_ID
    assert payload["messages"][0]["content"] == BOB_SECRET
