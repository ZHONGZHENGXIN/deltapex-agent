from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent, AgentSource
from app.schemas.agent import AgentActionRequest, AgentCreate, AgentList, AgentListResponse, AgentSearchParams, AgentUpdate

logger = get_logger(__name__)

DEFAULT_AGENT_NAME = "Default Assistant"


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
    agent = Agent(**agent_data.model_dump())
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def update_agent(session: Session, agent_id: int, agent_data: AgentUpdate) -> Optional[Agent]:
    agent = session.get(Agent, agent_id)
    if not agent:
        return None

    for key, value in agent_data.model_dump(exclude_unset=True).items():
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
    existing_agent = session.exec(select(Agent).where(Agent.name == DEFAULT_AGENT_NAME, Agent.is_deleted == False)).first()
    if existing_agent:
        logger.info("Default assistant already exists: %s", existing_agent.name)
        return existing_agent

    default_model_conf = {
        "model": settings.AGENT_MODEL_NAME,
        "temperature": settings.AGENT_MODEL_TEMPERATURE,
        "max_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

    default_agent = Agent(
        name=DEFAULT_AGENT_NAME,
        source=AgentSource.FASTGPT,
        api_url=settings.AGENT_BASE_URL,
        api_key=settings.AGENT_API_KEY,
        model_conf=default_model_conf,
        is_think=False,
        is_stream=True,
        is_deleted=False,
    )
    session.add(default_agent)
    session.commit()
    session.refresh(default_agent)
    logger.info("Created default assistant: %s", default_agent.name)
    return default_agent
