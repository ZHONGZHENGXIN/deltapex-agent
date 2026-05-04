from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlmodel import Session, create_engine, select

from app.agents.llm import build_llm_client_config, normalize_openai_base_url
from app.core.config import settings
from app.crud.agent import DEFAULT_AGENT_NAME, GATEWAY_API_KEY_PLACEHOLDER, create_agent, create_default_agent, update_agent
from app.models.agent import Agent, AgentSource
from app.schemas.agent import AgentCreate, AgentUpdate


def _agent(**overrides) -> SimpleNamespace:
    data = {
        "api_key": "provider-secret-key",
        "api_url": "https://provider.example.test/v1/chat/completions",
        "model_conf": {"model": "provider-model", "temperature": 0.2},
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_openai_base_url_normalization_accepts_chat_completions_url():
    assert normalize_openai_base_url("https://provider.example.test/v1/chat/completions") == (
        "https://provider.example.test/v1"
    )
    assert normalize_openai_base_url("http://one-api:3000/v1/") == "http://one-api:3000/v1"


def test_llm_gateway_config_uses_one_api_env_not_agent_provider_fields(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_BASE_URL", "http://one-api:3000/v1/")
    monkeypatch.setattr(settings, "LLM_GATEWAY_API_KEY", "one-api-token")
    monkeypatch.setattr(settings, "LLM_GATEWAY_MODEL_NAME", "gpt-4.1-mini")

    config = build_llm_client_config(_agent())

    assert config.gateway_enabled is True
    assert config.api_key == "one-api-token"
    assert config.base_url == "http://one-api:3000/v1"
    assert config.model == "gpt-4.1-mini"
    assert config.model_conf["temperature"] == 0.2
    assert config.api_key != "provider-secret-key"


def test_llm_gateway_requires_gateway_token(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_API_KEY", None)

    with pytest.raises(RuntimeError, match="LLM_GATEWAY_API_KEY"):
        build_llm_client_config(_agent())


def test_llm_legacy_direct_config_is_explicit_fallback(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", False)

    config = build_llm_client_config(_agent())

    assert config.gateway_enabled is False
    assert config.api_key == "provider-secret-key"
    assert config.base_url == "https://provider.example.test/v1"
    assert config.model == "provider-model"


def test_default_agent_uses_gateway_reference_without_provider_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_BASE_URL", "http://one-api:3000/v1")
    monkeypatch.setattr(settings, "LLM_GATEWAY_MODEL_NAME", "gpt-4.1-mini")

    engine = create_engine("sqlite:///:memory:")
    Agent.__table__.create(engine)

    with Session(engine) as session:
        agent = create_default_agent(session)

    assert agent.source == AgentSource.LLM
    assert agent.api_url == "http://one-api:3000/v1"
    assert agent.api_key == GATEWAY_API_KEY_PLACEHOLDER
    assert agent.model_conf["model"] == "gpt-4.1-mini"


def test_existing_default_agent_is_migrated_to_gateway_reference(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_BASE_URL", "http://one-api:3000/v1")
    monkeypatch.setattr(settings, "LLM_GATEWAY_MODEL_NAME", "gpt-4.1-mini")

    engine = create_engine("sqlite:///:memory:")
    Agent.__table__.create(engine)
    now = datetime(2026, 1, 1)

    with Session(engine) as session:
        session.add(
            Agent(
                id=1,
                name=DEFAULT_AGENT_NAME,
                source=AgentSource.FASTGPT,
                api_url="https://cloud.fastgpt.io/api/v1/chat/completions",
                api_key="old-provider-key",
                model_conf={"model": "fastgpt"},
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

        migrated = create_default_agent(session)
        stored = session.exec(select(Agent).where(Agent.id == 1)).one()

    assert migrated.id == 1
    assert stored.source == AgentSource.LLM
    assert stored.api_url == "http://one-api:3000/v1"
    assert stored.api_key == GATEWAY_API_KEY_PLACEHOLDER
    assert stored.model_conf["model"] == "gpt-4.1-mini"


def test_existing_llm_agents_are_scrubbed_to_gateway_reference_on_default_init(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_BASE_URL", "http://one-api:3000/v1")

    engine = create_engine("sqlite:///:memory:")
    Agent.__table__.create(engine)

    with Session(engine) as session:
        session.add(
            Agent(
                id=2,
                name="Old LLM Agent",
                source=AgentSource.LLM,
                api_url="https://provider.example.test/v1/chat/completions",
                api_key="old-provider-key",
                model_conf={"model": "provider-model"},
                is_deleted=False,
            )
        )
        session.commit()

        create_default_agent(session)
        stored = session.exec(select(Agent).where(Agent.id == 2)).one()

    assert stored.api_url == "http://one-api:3000/v1"
    assert stored.api_key == GATEWAY_API_KEY_PLACEHOLDER
    assert stored.model_conf["model"] == "provider-model"


def test_llm_agent_create_overrides_provider_credentials_with_gateway_reference(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_BASE_URL", "http://one-api:3000/v1")
    monkeypatch.setattr(settings, "LLM_GATEWAY_MODEL_NAME", "gpt-4.1-mini")

    engine = create_engine("sqlite:///:memory:")
    Agent.__table__.create(engine)

    with Session(engine) as session:
        agent = create_agent(
            session,
            AgentCreate(
                name="Gateway Coach",
                source=AgentSource.LLM,
                api_url="https://provider.example.test/v1/chat/completions",
                api_key="provider-secret-key",
                model_conf=None,
            ),
        )

    assert agent.source == AgentSource.LLM
    assert agent.api_url == "http://one-api:3000/v1"
    assert agent.api_key == GATEWAY_API_KEY_PLACEHOLDER
    assert agent.model_conf["model"] == "gpt-4.1-mini"


def test_llm_agent_update_does_not_store_submitted_provider_key(monkeypatch):
    monkeypatch.setattr(settings, "LLM_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_GATEWAY_BASE_URL", "http://one-api:3000/v1")

    engine = create_engine("sqlite:///:memory:")
    Agent.__table__.create(engine)

    with Session(engine) as session:
        session.add(
            Agent(
                id=1,
                name="Gateway Coach",
                source=AgentSource.LLM,
                api_url="http://one-api:3000/v1",
                api_key=GATEWAY_API_KEY_PLACEHOLDER,
                model_conf={"model": "gpt-4.1-mini"},
                is_deleted=False,
            )
        )
        session.commit()

        agent = update_agent(
            session,
            1,
            AgentUpdate(
                api_url="https://provider.example.test/v1/chat/completions",
                api_key="new-provider-secret-key",
            ),
        )

    assert agent is not None
    assert agent.api_url == "http://one-api:3000/v1"
    assert agent.api_key == GATEWAY_API_KEY_PLACEHOLDER
