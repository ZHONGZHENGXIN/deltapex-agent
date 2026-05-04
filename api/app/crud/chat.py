from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from app.crud.message import message_to_out
from app.models.agent import Agent
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatOut, ChatUpdate


def chat_to_out(chat: Chat, agent: Optional[Agent] = None, messages: Optional[list[Message]] = None) -> ChatOut:
    return ChatOut(
        id=chat.public_id,
        title=chat.title,
        content=chat.content,
        agent_id=chat.agent_id,
        agent=agent,
        messages=[message_to_out(message, chat.public_id) for message in (messages or [])],
        others=chat.others,
        is_deleted=chat.is_deleted,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


def create_chat(chat_in: ChatCreate, session: Session, user: User) -> Chat:
    chat_data = chat_in.model_dump()
    chat = Chat(**chat_data, user_id=user.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def get_chat_record(public_id: str, session: Session, user: User) -> Optional[Chat]:
    return session.exec(
        select(Chat).where(Chat.public_id == public_id, Chat.is_deleted == False, Chat.user_id == user.id)
    ).first()


def update_chat(public_id: str, chat_in: ChatUpdate, session: Session, user: User) -> Optional[Chat]:
    chat = get_chat_record(public_id, session, user)
    if not chat:
        return None

    chat_data = chat_in.model_dump(exclude_unset=True)
    for key, value in chat_data.items():
        setattr(chat, key, value)

    chat.updated_at = datetime.utcnow()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def soft_delete_chat(public_id: str, session: Session, user: User) -> Optional[Chat]:
    chat = get_chat_record(public_id, session, user)
    if not chat:
        return None

    chat.is_deleted = True
    chat.deleted_at = datetime.utcnow()
    chat.updated_at = datetime.utcnow()
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def get_all_chats(session: Session, user: User, limit: int = 20, offset: int = 0, include_messages: bool = False) -> list[ChatOut]:
    chats = session.exec(
        select(Chat)
        .where(Chat.user_id == user.id, Chat.is_deleted == False)
        .order_by(Chat.updated_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    agent_ids = [chat.agent_id for chat in chats if chat.agent_id]
    agent_map = {}
    if agent_ids:
        agents = session.exec(select(Agent).where(Agent.id.in_(agent_ids), Agent.is_deleted == False)).all()
        agent_map = {agent.id: agent for agent in agents}

    messages_map: dict[int, list[Message]] = {}
    if include_messages and chats:
        chat_ids = [chat.id for chat in chats]
        all_messages = session.exec(
            select(Message)
            .where(Message.chat_id.in_(chat_ids), Message.user_id == user.id, Message.is_deleted == False)
            .order_by(Message.chat_id, Message.created_at.asc())
        ).all()

        for message in all_messages:
            messages_map.setdefault(message.chat_id, []).append(message)

    return [
        chat_to_out(
            chat,
            agent_map.get(chat.agent_id) if chat.agent_id else None,
            messages_map.get(chat.id, []) if include_messages else [],
        )
        for chat in chats
    ]


def get_chat(public_id: str, session: Session, user: User) -> Optional[ChatOut]:
    chat = get_chat_record(public_id, session, user)
    if not chat:
        return None

    agent = None
    if chat.agent_id:
        agent = session.exec(select(Agent).where(Agent.id == chat.agent_id, Agent.is_deleted == False)).first()

    return chat_to_out(chat, agent, [])


def update_chat_others(chat_id: int, others_data: Dict[str, Any], session: Session) -> Optional[Chat]:
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)).first()
    if not chat:
        return None

    if chat.others is None:
        chat.others = {}

    chat.others.update(others_data)
    chat.updated_at = datetime.utcnow()

    session.add(chat)
    session.commit()
    session.refresh(chat)

    return chat


def get_chat_conversation_id(chat_id: int, session: Session) -> Optional[str]:
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)).first()
    if not chat or not chat.others:
        return None

    return chat.others.get("conversation_id")
