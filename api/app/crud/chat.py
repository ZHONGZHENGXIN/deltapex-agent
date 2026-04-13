from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session, select, func

from app.models.agent import Agent
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatOut, ChatUpdate


def create_chat(chat_in: ChatCreate, session: Session, user: User) -> Chat:
    chat_data = chat_in.dict()
    chat = Chat(**chat_data, user_id=user.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def update_chat(chat_id: int, chat_in: ChatUpdate, session: Session, user: User) -> Optional[Chat]:
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False, Chat.user_id == user.id)).first()
    if not chat:
        return None
    chat_data = chat_in.dict(exclude_unset=True)
    for key, value in chat_data.items():
        setattr(chat, key, value)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def soft_delete_chat(chat_id: int, session: Session, user: User) -> Optional[Chat]:
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False, Chat.user_id == user.id)).first()
    if not chat:
        return None
    chat.is_deleted = True
    chat.deleted_at = datetime.utcnow()  # 设置删除时间戳
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def get_all_chats(session: Session, user: User, limit: int = 20, offset: int = 0, include_messages: bool = False) -> list[ChatOut]:
    """
    获取用户的对话列表，支持分页，包含关联的 Agent 数据
    
    参数:
    - session: 数据库会话
    - user: 用户对象
    - limit: 每页记录数
    - offset: 偏移量
    - include_messages: 是否包含消息数据，默认 False
    
    返回:
    - list[ChatOut]: 对话列表，可选包含消息数据
    """
    # 查询用户的对话，支持分页
    chats = session.exec(
        select(Chat)
        .where(Chat.user_id == user.id, Chat.is_deleted == False)
        .order_by(Chat.updated_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    # 手动加载关联的 Agent 数据
    agent_ids = [chat.agent_id for chat in chats if chat.agent_id]
    agent_map = {}
    if agent_ids:
        agents = session.exec(select(Agent).where(Agent.id.in_(agent_ids), Agent.is_deleted == False)).all()
        # 创建 agent_id 到 agent 对象的映射
        agent_map = {agent.id: agent for agent in agents}

    # 如果需要包含消息，批量加载所有聊天的消息
    messages_map = {}
    if include_messages and chats:
        chat_ids = [chat.id for chat in chats]
        # 批量查询所有聊天的消息
        from app.models.message import Message
        all_messages = session.exec(
            select(Message)
            .where(Message.chat_id.in_(chat_ids), Message.is_deleted == False)
            .order_by(Message.chat_id, Message.created_at.asc())
        ).all()
        
        # 按 chat_id 分组消息
        for message in all_messages:
            if message.chat_id not in messages_map:
                messages_map[message.chat_id] = []
            messages_map[message.chat_id].append(message)

    # 创建 ChatOut 对象列表
    chat_outs = []
    for chat in chats:
        agent = agent_map.get(chat.agent_id) if chat.agent_id else None
        messages = messages_map.get(chat.id, []) if include_messages else []
        
        chat_out = ChatOut(
            id=chat.id,
            title=chat.title,
            content=chat.content,
            agent_id=chat.agent_id,
            agent=agent,
            messages=messages,
            is_deleted=chat.is_deleted,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )
        chat_outs.append(chat_out)

    return chat_outs


def get_chat(chat_id: int, session: Session, user: User) -> Optional[ChatOut]:
    """获取单个对话，包含关联的 Agent 数据和消息数量"""
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False, Chat.user_id == user.id)).first()

    if not chat:
        return None

    # 手动加载关联的 Agent 数据
    agent = None
    if chat.agent_id:
        agent = session.exec(select(Agent).where(Agent.id == chat.agent_id, Agent.is_deleted == False)).first()

    # 不再查询消息数量，由前端直接统计

    # 创建 ChatOut 对象
    chat_out = ChatOut(
        id=chat.id,
        title=chat.title,
        content=chat.content,
        agent_id=chat.agent_id,
        agent=agent,
        messages=[],  # 这里可以根据需要加载消息
        is_deleted=chat.is_deleted,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )

    return chat_out


def update_chat_others(chat_id: int, others_data: Dict[str, Any], session: Session) -> Optional[Chat]:
    """
    更新 chat 的 others 字段

    Args:
        chat_id: 对话ID
        others_data: 要更新的 others 数据
        session: 数据库会话

    Returns:
        更新后的 Chat 对象，如果不存在则返回 None
    """
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)).first()
    if not chat:
        return None

    # 如果 others 字段为空，初始化为空字典
    if chat.others is None:
        chat.others = {}

    # 更新 others 字段
    chat.others.update(others_data)
    chat.updated_at = datetime.utcnow()

    session.add(chat)
    session.commit()
    session.refresh(chat)

    return chat


def get_chat_conversation_id(chat_id: int, session: Session) -> Optional[str]:
    """
    从 chat 的 others 字段中获取 conversation_id

    Args:
        chat_id: 对话ID
        session: 数据库会话

    Returns:
        conversation_id 字符串，如果不存在则返回 None
    """
    chat = session.exec(select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)).first()
    if not chat or not chat.others:
        return None

    return chat.others.get("conversation_id")
