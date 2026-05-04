from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent, AgentSource
from app.schemas.agent import AgentActionRequest, AgentCreate, AgentList, AgentListResponse, AgentSearchParams, AgentUpdate

logger = get_logger(__name__)

DEFAULT_AGENT_NAME = "Default Assistant"
GATEWAY_API_KEY_PLACEHOLDER = "__env:LLM_GATEWAY_API_KEY__"


def _default_model_conf() -> dict:
    return {
        "model": settings.LLM_GATEWAY_MODEL_NAME or settings.AGENT_MODEL_NAME,
        "temperature": settings.AGENT_MODEL_TEMPERATURE,
        "max_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }


def _default_agent_values() -> dict:
    if settings.LLM_GATEWAY_ENABLED:
        return {
            "source": AgentSource.LLM,
            "api_url": settings.LLM_GATEWAY_BASE_URL,
            "api_key": GATEWAY_API_KEY_PLACEHOLDER,
            "model_conf": _default_model_conf(),
        }

    return {
        "source": AgentSource.FASTGPT,
        "api_url": settings.AGENT_BASE_URL,
        "api_key": settings.AGENT_API_KEY or "",
        "model_conf": _default_model_conf(),
    }


def _apply_gateway_reference(payload: dict, source: AgentSource, *, ensure_model_conf: bool = False) -> dict:
    if not settings.LLM_GATEWAY_ENABLED or source != AgentSource.LLM:
        return payload

    normalized = dict(payload)
    normalized["api_url"] = settings.LLM_GATEWAY_BASE_URL
    normalized["api_key"] = GATEWAY_API_KEY_PLACEHOLDER
    if ensure_model_conf and not normalized.get("model_conf"):
        normalized["model_conf"] = _default_model_conf()
    return normalized


def enforce_llm_gateway_references(session: Session) -> int:
    if not settings.LLM_GATEWAY_ENABLED:
        return 0

    agents = session.exec(select(Agent).where(Agent.source == AgentSource.LLM)).all()
    updated_count = 0
    for agent in agents:
        if agent.api_url == settings.LLM_GATEWAY_BASE_URL and agent.api_key == GATEWAY_API_KEY_PLACEHOLDER:
            continue

        agent.api_url = settings.LLM_GATEWAY_BASE_URL
        agent.api_key = GATEWAY_API_KEY_PLACEHOLDER
        agent.updated_at = datetime.utcnow()
        session.add(agent)
        updated_count += 1

    if updated_count:
        session.commit()
        logger.info("Migrated %s LLM agents to gateway references", updated_count)

    return updated_count


def get_agents_with_pagination(session: Session, params: AgentSearchParams) -> AgentListResponse:
    query = select(Agent)
    conditions = []

    if params.name:
        conditions.append(Agent.name.ilike(f"%{params.name}%"))
    if params.source:
        conditions.append(Agent.source == params.source)
    if params.is_deleted is not None:
        conditions.append(Agent.is_deleted == params.is_deleted)

    if conditions:
        query = query.where(*conditions)

    if params.sort_by and hasattr(Agent, params.sort_by):
        sort_column = getattr(Agent, params.sort_by)
        query = query.order_by(sort_column.desc() if params.sort_order == "desc" else sort_column)

    count_query = select(func.count()).select_from(Agent)
    if conditions:
        count_query = count_query.where(*conditions)
    total = session.exec(count_query).one()

    agents = session.exec(query.offset(params.offset).limit(params.limit)).all()

    total_pages = (total + params.limit - 1) // params.limit if params.limit > 0 else 1
    current_page = (params.offset // params.limit) + 1 if params.limit > 0 else 1

    return AgentListResponse(
        agents=[AgentList.model_validate(agent) for agent in agents],
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0,
        total_pages=total_pages,
        current_page=current_page,
    )


def get_agent_detail(session: Session, agent_id: int) -> Optional[Agent]:
    return session.get(Agent, agent_id)


def create_agent(session: Session, agent_data: AgentCreate) -> Agent:
    payload = agent_data.model_dump()
    payload = _apply_gateway_reference(payload, payload["source"], ensure_model_conf=True)
    agent = Agent(**payload)
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def update_agent(session: Session, agent_id: int, agent_data: AgentUpdate) -> Optional[Agent]:
    agent = session.get(Agent, agent_id)
    if not agent:
        return None

    payload = agent_data.model_dump(exclude_unset=True)
    target_source = payload.get("source", agent.source)
    payload = _apply_gateway_reference(
        payload,
        target_source,
        ensure_model_conf=(payload.get("source") == AgentSource.LLM and agent.source != AgentSource.LLM),
    )

    for key, value in payload.items():
        setattr(agent, key, value)

    agent.updated_at = datetime.utcnow()
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def delete_or_restore_agent(session: Session, agent_id: int, action_data: AgentActionRequest) -> Optional[Agent]:
    agent = session.get(Agent, agent_id)
    if not agent:
        return None

    if action_data.action == "delete":
        agent.is_deleted = True
        agent.deleted_at = datetime.utcnow()
    elif action_data.action == "restore":
        agent.is_deleted = False
        agent.deleted_at = None
    else:
        raise ValueError(f"Invalid action: {action_data.action}")

    agent.updated_at = datetime.utcnow()
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def get_active_agents(session: Session) -> List[Agent]:
    return session.exec(select(Agent).where(Agent.is_deleted == False)).all()


def create_default_agent(session: Session) -> Agent:
    values = _default_agent_values()
    enforce_llm_gateway_references(session)
    existing_agent = session.exec(select(Agent).where(Agent.name == DEFAULT_AGENT_NAME, Agent.is_deleted == False)).first()
    if existing_agent:
        if settings.LLM_GATEWAY_ENABLED and (
            existing_agent.source != AgentSource.LLM
            or existing_agent.api_url != values["api_url"]
            or existing_agent.api_key != values["api_key"]
        ):
            existing_agent.source = values["source"]
            existing_agent.api_url = values["api_url"]
            existing_agent.api_key = values["api_key"]
            existing_agent.model_conf = values["model_conf"]
            existing_agent.updated_at = datetime.utcnow()
            session.add(existing_agent)
            session.commit()
            session.refresh(existing_agent)
            logger.info("Migrated default assistant to LLM gateway: %s", existing_agent.name)
            return existing_agent

        logger.info("Default assistant already exists: %s", existing_agent.name)
        return existing_agent

    default_agent = Agent(
        name=DEFAULT_AGENT_NAME,
        source=values["source"],
        api_url=values["api_url"],
        api_key=values["api_key"],
        model_conf=values["model_conf"],
        is_think=False,
        is_stream=True,
        is_deleted=False,
    )
    session.add(default_agent)
    session.commit()
    session.refresh(default_agent)
    logger.info("Created default assistant: %s", default_agent.name)
    return default_agent
