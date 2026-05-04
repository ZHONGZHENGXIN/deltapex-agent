from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models.message import Message
from app.schemas.message import MessageCreate, MessageOut, MessageUpdate


def create_message(message_in: MessageCreate, session: Session) -> Message:
    message = Message(**message_in.model_dump())
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def message_to_out(message: Message, public_chat_id: str) -> MessageOut:
    return MessageOut(
        id=message.id,
        chat_id=public_chat_id,
        content=message.content,
        model_conf=message.model_conf,
        role=message.role,
        is_deleted=message.is_deleted,
        created_at=message.created_at,
        updated_at=message.updated_at,
        token_usage=message.token_usage,
    )


def update_message(message_id: int, message_in: MessageUpdate, session: Session, user_id: int) -> Optional[Message]:
    message = session.exec(
        select(Message).where(Message.id == message_id, Message.user_id == user_id, Message.is_deleted == False)
    ).first()
    if not message:
        return None
    message_data = message_in.dict(exclude_unset=True)
    for key, value in message_data.items():
        setattr(message, key, value)
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def soft_delete_message(message_id: int, session: Session, user_id: int) -> Optional[Message]:
    message = session.exec(
        select(Message).where(Message.id == message_id, Message.user_id == user_id, Message.is_deleted == False)
    ).first()
    if not message:
        return None
    message.is_deleted = True
    message.deleted_at = datetime.utcnow()  # 设置删除时间戳
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def get_all_messages(chat_id: int, user_id: int, session: Session) -> List[Message]:
    messages = session.exec(
        select(Message)
        .where(Message.chat_id == chat_id, Message.user_id == user_id, Message.is_deleted == False)
        .order_by(Message.created_at.asc())
        .limit(200)
    ).all()
    return messages


def get_message(message_id: int, session: Session, user_id: int) -> Optional[Message]:
    message = session.exec(
        select(Message).where(Message.id == message_id, Message.user_id == user_id, Message.is_deleted == False)
    ).first()
    if not message:
        return None
    return message


def update_message_content(
    message_id: int,
    content: str,
    session: Session,
    token_usage: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
) -> Optional[Message]:
    """
    更新消息内容和 token 统计（用于流式响应的增量保存）
    
    参数:
    - message_id: 消息ID
    - content: 新的消息内容
    - session: 数据库会话
    - token_usage: 可选的 token 使用统计信息
    
    返回:
    - Message: 更新后的消息对象，如果消息不存在返回None
    """
    conditions = [Message.id == message_id, Message.is_deleted == False]
    if user_id is not None:
        conditions.append(Message.user_id == user_id)
    message = session.exec(select(Message).where(*conditions)).first()
    if not message:
        return None
    
    message.content = content
    message.updated_at = datetime.utcnow()
    
    # 如果提供了 token 统计信息，则更新
    if token_usage is not None:
        message.token_usage = token_usage
    
    session.add(message)
    session.commit()
    session.refresh(message)
    return message
