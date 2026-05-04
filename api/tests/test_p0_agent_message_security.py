from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlmodel import Session, create_engine

from app.main import BASE_PREFIX, app
from app.crud.chat import chat_to_out
from app.crud.message import get_all_messages, message_to_out
from app.db.rls import RLS_IS_ADMIN_KEY, RLS_USER_ID_KEY, set_rls_context
from app.models.chat import Chat
from app.models.agent import AgentSource
from app.models.message import Message
from app.routers.v1.chat import chat_router
from app.schemas.agent import AgentAdminOut, AgentList, AgentPublic
from app.schemas.chat import ChatOut
from app.schemas.message import MessageCreate, MessageRole, UserMessageCreate


FORBIDDEN_PUBLIC_AGENT_FIELDS = {"api_key", "api_url", "model_conf"}
PUBLIC_CHAT_ID = "11111111-1111-4111-8111-111111111111"
API_ROOT = Path(__file__).resolve().parents[1]


def _agent(api_key: str = "secret-key") -> SimpleNamespace:
    now = datetime(2026, 1, 1)
    return SimpleNamespace(
        id=1,
        name="Coach",
        source=AgentSource.FASTGPT,
        api_url="https://example.test/v1/chat/completions",
        api_key=api_key,
        model_conf={"model": "fastgpt"},
        is_think=False,
        is_stream=True,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


def _schema(name: str) -> dict:
    return app.openapi()["components"]["schemas"][name]


def _response_schema(path: str, method: str) -> dict:
    return app.openapi()["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]


def _ref_name(schema: dict) -> str:
    return schema["$ref"].rsplit("/", 1)[-1]


def test_agent_public_serialization_excludes_credentials():
    payload = AgentPublic.model_validate(_agent()).model_dump()

    assert FORBIDDEN_PUBLIC_AGENT_FIELDS.isdisjoint(payload)
    assert set(payload) == {"id", "name", "source", "is_think", "is_stream"}

    schema_props = AgentPublic.model_json_schema()["properties"]
    assert FORBIDDEN_PUBLIC_AGENT_FIELDS.isdisjoint(schema_props)


def test_admin_agent_serialization_excludes_api_key_but_reports_presence():
    payload = AgentAdminOut.model_validate(_agent()).model_dump()

    assert "api_key" not in payload
    assert payload["api_key_set"] is True

    round_tripped_payload = AgentList.model_validate(AgentAdminOut.model_validate(_agent())).model_dump()
    assert "api_key" not in round_tripped_payload
    assert round_tripped_payload["api_key_set"] is True

    empty_key_payload = AgentList.model_validate(_agent(api_key="")).model_dump()
    assert "api_key" not in empty_key_payload
    assert empty_key_payload["api_key_set"] is False

    schema_props = AgentAdminOut.model_json_schema()["properties"]
    assert "api_key" not in schema_props
    assert "api_key_set" in schema_props


def test_chat_out_uses_public_agent_shape():
    now = datetime(2026, 1, 1)
    chat = ChatOut(
        id=PUBLIC_CHAT_ID,
        title="Session",
        content=None,
        agent_id=1,
        agent=_agent(),
        messages=[],
        others={},
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    agent_payload = chat.model_dump()["agent"]
    assert FORBIDDEN_PUBLIC_AGENT_FIELDS.isdisjoint(agent_payload)
    assert set(agent_payload) == {"id", "name", "source", "is_think", "is_stream"}


def test_chat_and_message_public_shapes_use_public_chat_id():
    now = datetime(2026, 1, 1)
    chat = Chat(
        id=123,
        public_id=PUBLIC_CHAT_ID,
        user_id=7,
        title="Session",
        content=None,
        agent_id=1,
        others={},
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    message = Message(
        id=456,
        chat_id=123,
        user_id=7,
        content="hello",
        model_conf=None,
        role=MessageRole.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    chat_payload = chat_to_out(chat, _agent(), [message]).model_dump()
    message_payload = message_to_out(message, PUBLIC_CHAT_ID).model_dump()

    assert chat_payload["id"] == PUBLIC_CHAT_ID
    assert chat_payload["id"] != chat.id
    assert chat_payload["messages"][0]["chat_id"] == PUBLIC_CHAT_ID
    assert message_payload["chat_id"] == PUBLIC_CHAT_ID
    assert message_payload["chat_id"] != message.chat_id


def test_openapi_agent_response_models_do_not_expose_api_key():
    assert FORBIDDEN_PUBLIC_AGENT_FIELDS.isdisjoint(_schema("AgentPublic")["properties"])
    assert "api_key" not in _schema("AgentAdminOut")["properties"]
    assert "api_key_set" in _schema("AgentAdminOut")["properties"]
    assert "api_key" not in _schema("AgentList")["properties"]
    assert "api_key_set" in _schema("AgentList")["properties"]

    active_agents_schema = _response_schema(f"{BASE_PREFIX}/chat/agents/active", "get")
    assert _ref_name(active_agents_schema["items"]) == "AgentPublic"

    admin_detail_schema = _response_schema(f"{BASE_PREFIX}/admin/agents/{{agent_id}}", "get")
    admin_create_schema = _response_schema(f"{BASE_PREFIX}/admin/agents", "post")
    admin_update_schema = _response_schema(f"{BASE_PREFIX}/admin/agents/{{agent_id}}", "put")
    assert _ref_name(admin_detail_schema) == "AgentAdminOut"
    assert _ref_name(admin_create_schema) == "AgentAdminOut"
    assert _ref_name(admin_update_schema) == "AgentAdminOut"

    admin_list_schema = _schema("AgentListResponse")
    assert _ref_name(admin_list_schema["properties"]["agents"]["items"]) == "AgentList"


def test_openapi_chat_ids_are_public_strings():
    chat_out_props = _schema("ChatOut")["properties"]
    message_out_props = _schema("MessageOut")["properties"]
    user_message_props = _schema("UserMessageCreate")["properties"]

    assert chat_out_props["id"]["type"] == "string"
    assert message_out_props["chat_id"]["type"] == "string"
    assert user_message_props["chat_id"]["type"] == "string"

    chat_detail_params = app.openapi()["paths"][f"{BASE_PREFIX}/chat/{{chat_id}}"]["get"]["parameters"]
    assert next(param for param in chat_detail_params if param["name"] == "chat_id")["schema"]["type"] == "string"


def test_active_agents_route_is_registered_before_dynamic_chat_route():
    get_routes = [route.path for route in chat_router.routes if "GET" in route.methods]
    assert get_routes.index("/chat/agents/active") < get_routes.index("/chat/{chat_id}")


def test_user_message_create_accepts_only_chat_id_and_content():
    message = UserMessageCreate.model_validate({"chat_id": PUBLIC_CHAT_ID, "content": "hello"})
    assert message.chat_id == PUBLIC_CHAT_ID
    assert message.content == "hello"


def test_user_message_create_rejects_numeric_chat_id():
    with pytest.raises(ValidationError):
        UserMessageCreate.model_validate({"chat_id": 1, "content": "hello"})


def test_internal_message_create_requires_user_id():
    message = MessageCreate.model_validate(
        {"chat_id": 1, "user_id": 2, "content": "hello", "role": MessageRole.USER}
    )
    assert message.chat_id == 1
    assert message.user_id == 2

    with pytest.raises(ValidationError):
        MessageCreate.model_validate({"chat_id": 1, "content": "hello", "role": MessageRole.USER})


def test_get_all_messages_filters_by_user_id():
    engine = create_engine("sqlite:///:memory:")
    Message.__table__.create(engine)

    now = datetime(2026, 1, 1)
    with Session(engine) as session:
        session.add_all(
            [
                Message(
                    chat_id=10,
                    user_id=1,
                    content="alice",
                    model_conf=None,
                    role=MessageRole.USER,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
                Message(
                    chat_id=10,
                    user_id=2,
                    content="bob",
                    model_conf=None,
                    role=MessageRole.USER,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

        messages = get_all_messages(10, 1, session)

    assert [message.content for message in messages] == ["alice"]


def test_postgres_rls_migration_uses_zeabur_postgres_context():
    migration = API_ROOT / "alembic" / "versions" / "b20260504_p0_3c_postgres_rls.py"
    migration_text = migration.read_text(encoding="utf-8").lower()

    assert "auth.uid" not in migration_text
    assert "enable row level security" in migration_text
    assert "force row level security" in migration_text
    assert "app.current_user_id" in migration_text
    assert "app.is_admin" in migration_text
    assert "chat_tenant_isolation" in migration_text
    assert "message_tenant_isolation" in migration_text


def test_rls_context_is_stored_on_session():
    engine = create_engine("sqlite:///:memory:")

    with Session(engine) as session:
        session.exec(text("select 1"))
        set_rls_context(session, user_id=7, is_admin=True)

        assert session.info[RLS_USER_ID_KEY] == 7
        assert session.info[RLS_IS_ADMIN_KEY] is True


@pytest.mark.parametrize(
    "extra_payload",
    [
        {"role": "assistant"},
        {"role": "system"},
        {"model_conf": {"temperature": 2}},
        {"token_usage": {"total_tokens": 1}},
    ],
)
def test_user_message_create_rejects_client_controlled_fields(extra_payload):
    with pytest.raises(ValidationError):
        UserMessageCreate.model_validate({"chat_id": PUBLIC_CHAT_ID, "content": "hello", **extra_payload})
