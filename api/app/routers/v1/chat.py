from functools import wraps
import traceback
from typing import Tuple, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse


from app.agents.dify import (
    create_dify_response,
    create_dify_response_stream,
    test_dify_connection,
)
from app.agents.fastgpt import (
    create_fastgpt_response,
    create_fastgpt_response_stream,
    test_fastgpt_connection,
)
from app.agents.llm import (
    create_llm_response,
    create_llm_response_stream,
    test_agent_connection,
    estimate_conversation_tokens,
)
from app.core.i18n import get_message
from app.crud.agent import get_active_agents, get_agent_detail
from app.crud.chat import (
    create_chat,
    get_all_chats,
    get_chat,
    soft_delete_chat,
    update_chat,
)
from app.crud.message import create_message, get_all_messages, update_message_content
from app.db.base import get_session
from app.dependencies.db import LangDep, SessionDep, UserDep
from app.models.agent import Agent, AgentSource
from app.schemas.agent import Agent as AgentSchema
from app.schemas.chat import ChatCreate, ChatOut, ChatUpdate
from app.schemas.message import MessageCreate, MessageOut, MessageRole
from app.services.membership_service import MembershipService

chat_router = APIRouter(prefix="/chat")


class MessageLogger:
    """
    消息记录日志工具类
    
    功能说明:
    - 提供统一的消息记录日志格式
    - 记录消息创建、更新、错误等关键事件
    - 便于调试和监控消息记录功能
    """
    
    @staticmethod
    def log_message_start(user_id: int, chat_id: int, content_length: int, is_stream: bool = False):
        """记录消息处理开始"""
        mode = "流式" if is_stream else "非流式"
        print(f"📝 [消息开始] user_id={user_id}, chat_id={chat_id}, content_length={content_length}, mode={mode}")
    
    @staticmethod
    def log_user_message_saved(message_id: int, chat_id: int):
        """记录用户消息保存成功"""
        print(f"💾 [用户消息] message_id={message_id}, chat_id={chat_id} - 用户消息已保存")
    
    @staticmethod
    def log_ai_response_start(agent_id: int, is_stream: bool = False):
        """记录AI回复开始生成"""
        mode = "流式" if is_stream else "非流式"
        print(f"🤖 [AI回复开始] agent_id={agent_id}, mode={mode}")
    
    @staticmethod
    def log_ai_response_success(message_id: int, content_length: int, tokens: int):
        """记录AI回复生成成功"""
        print(f"✅ [AI回复成功] message_id={message_id}, content_length={content_length}, tokens={tokens}")
    
    @staticmethod
    def log_ai_response_error(error: str, chat_id: int):
        """记录AI回复生成失败"""
        print(f"❌ [AI回复失败] chat_id={chat_id}, error={error}")
    
    @staticmethod
    def log_stream_progress(message_id: int, chunks: int, content_length: int):
        """记录流式响应进度"""
        print(f"🌊 [流式进度] message_id={message_id}, chunks={chunks}, content_length={content_length}")
    
    @staticmethod
    def log_usage_recorded(user_id: int, chat_id: int, tokens: int):
        """记录使用情况统计"""
        print(f"📊 [使用统计] user_id={user_id}, chat_id={chat_id}, tokens={tokens}")
    
    @staticmethod
    def log_emergency_save(message_id: int, chat_id: int, reason: str):
        """记录紧急保存操作"""
        print(f"🚨 [紧急保存] message_id={message_id}, chat_id={chat_id}, reason={reason}")
    
    @staticmethod
    def log_api_error(function_name: str, user_id: int, chat_id: int, error: str):
        """记录API级别错误"""
        print(f"🚨 [API错误] function={function_name}, user_id={user_id}, chat_id={chat_id}, error={error}")


def ensure_message_logging(func):
    """
    装饰器：确保消息记录的完整性
    
    功能说明:
    - 在API异常时也要确保用户消息被记录
    - 提供详细的错误日志记录
    - 保证数据库事务的一致性
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 提取消息相关参数
        message_in = None
        session = None
        user = None
        
        # 从参数中提取关键信息
        for arg in args:
            if hasattr(arg, 'chat_id') and hasattr(arg, 'content'):
                message_in = arg
            elif hasattr(arg, 'exec'):  # Session对象
                session = arg
            elif hasattr(arg, 'id'):  # User对象
                user = arg
        
        # 从kwargs中提取
        if not message_in:
            message_in = kwargs.get('message_in')
        if not session:
            session = kwargs.get('session')
        if not user:
            user = kwargs.get('user')
        
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # 记录详细的错误信息
            error_details = {
                'function': func.__name__,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'user_id': user.id if user else None,
                'chat_id': message_in.chat_id if message_in else None,
                'message_content_length': len(message_in.content) if message_in else 0
            }
            MessageLogger.log_api_error(func.__name__, user.id if user else 0, message_in.chat_id if message_in else 0, str(e))
            
            # 如果是消息创建相关的异常，确保用户消息已被记录
            if message_in and session and user and hasattr(message_in, 'chat_id'):
                try:
                    # 检查用户消息是否已经被保存
                    existing_messages = get_all_messages(message_in.chat_id, session)
                    user_messages = [msg for msg in existing_messages if msg.content == message_in.content and msg.role == MessageRole.USER]
                    
                    if not user_messages:
                        # 用户消息还未保存，立即保存
                        emergency_user_message = create_message(message_in, session)
                        MessageLogger.log_emergency_save(emergency_user_message.id, message_in.chat_id, "API异常时紧急保存用户消息")
                        
                        # 创建错误回复消息
                        error_reply = create_message(
                            MessageCreate(
                                chat_id=message_in.chat_id,
                                content=f"抱歉，处理您的消息时发生了错误: {str(e)}",
                                role=MessageRole.ASSISTANT,
                            ),
                            session,
                        )
                        MessageLogger.log_emergency_save(error_reply.id, message_in.chat_id, "API异常时创建错误回复")
                        
                except Exception as save_error:
                    MessageLogger.log_api_error("emergency_save", user.id if user else 0, message_in.chat_id if message_in else 0, str(save_error))
            
            # 重新抛出原始异常
            raise e
    
    return wrapper


async def create_agent_response(messages: list[MessageOut], agent: Agent, user_id: int, chat_id: int, session=None) -> Tuple[str, Dict[str, int]]:
    """
    根据 agent 类型创建响应

    Args:
        messages: 消息历史
        agent: Agent 配置
        user_id: 用户ID
        chat_id: 对话ID
        session: 数据库会话

    Returns:
        Tuple[str, Dict[str, int]]: 生成的响应内容和 token 使用统计
    """
    if agent.source == AgentSource.DIFY:
        # 使用 Dify API，现在支持 token 统计
        return await create_dify_response(messages, agent, user_id, chat_id, session)
    else:
        # 默认使用 LLM 处理
        return create_llm_response(messages, agent)


async def create_agent_response_stream(messages: list[MessageOut], agent: Agent, user_id: int, chat_id: int, session=None):
    """
    根据 agent 类型创建流式响应

    Args:
        messages: 消息历史
        agent: Agent 配置
        user_id: 用户ID
        chat_id: 对话ID
        session: 数据库会话

    Yields:
        Tuple[str, Optional[Dict[str, int]]]: 流式响应的文本块和可选的 token 统计
    """
    if agent.source == AgentSource.DIFY:
        # 使用 Dify 流式 API，现在支持 token 统计
        async for chunk_data in create_dify_response_stream(messages, agent, user_id, chat_id, session):
            yield chunk_data
    else:
        # 默认使用 LLM 处理
        async for chunk_data in create_llm_response_stream(messages, agent):
            yield chunk_data


async def test_agent_connection_unified(agent: Agent):
    """
    根据 agent 类型测试连接

    Args:
        agent: Agent 配置

    Returns:
        测试结果字典
    """
    if agent.source == AgentSource.DIFY:
        return await test_dify_connection(agent)
    else:
        # 默认使用 LLM 测试
        return await test_agent_connection(agent)


@chat_router.post("", response_model=ChatOut)
async def create_chat_api(chat_in: ChatCreate, session: SessionDep, user: UserDep, lang: LangDep) -> ChatOut:
    """
    创建新的聊天会话

    功能说明:
    - 验证 agent_id 的有效性
    - 创建聊天会话记录
    - 返回包含 agent 信息的聊天对象
    - 不自动创建任何消息，消息需要通过专门的消息接口创建

    参数:
    - chat_in: 聊天创建数据，包含标题、agent_id 等信息
    - session: 数据库会话
    - user: 当前用户
    - lang: 语言设置，默认中文

    返回:
    - ChatOut: 创建的聊天对象，包含 agent 信息

    异常:
    - 404: agent 不存在或已删除
    """
    # 验证 agent_id 是否有效
    if chat_in.agent_id:
        agent = get_agent_detail(session, chat_in.agent_id)
        if not agent or agent.is_deleted:
            error_msg = get_message("agent_not_found_or_inactive", lang)
            raise HTTPException(status_code=404, detail=error_msg)
    else:
        error_msg = get_message("agent_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)

    # 创建聊天会话
    chat = create_chat(chat_in, session, user)

    # 记录新聊天的使用情况
    membership_service = MembershipService(session)
    membership_service.record_usage(user.id, chat.id, message_count=0, token_count=0, is_new_chat=True)

    # 返回包含 agent 信息的聊天对象
    chat_out = ChatOut.model_validate(chat)
    if agent:
        chat_out.agent = AgentSchema.model_validate(agent)

    return chat_out


@chat_router.post("/message", response_model=list[MessageOut])
@ensure_message_logging
async def create_chat_message_api(
    message_in: MessageCreate,
    session: SessionDep,
    user: UserDep,
    lang: LangDep,
    stream: bool = False,
):
    """
    创建聊天消息 API 端点
    
    功能说明:
    - 接收用户消息并立即保存到数据库
    - 调用 AI Agent 生成回复
    - 确保用户问题和 AI 回复都被完整记录
    - 支持流式和非流式响应模式
    
    参数:
    - message_in: 用户消息数据
    - session: 数据库会话
    - user: 当前用户
    - lang: 语言设置
    - stream: 是否使用流式响应
    
    返回:
    - 流式模式: StreamingResponse
    - 非流式模式: 用户消息和AI回复的列表
    """
    user_id = user.id
    MessageLogger.log_message_start(user_id, message_in.chat_id, len(message_in.content), stream)

    # 验证用户是否有权限访问该聊天，并获取聊天关联的 agent
    chat = get_chat(message_in.chat_id, session, user)
    if not chat:
        error_msg = get_message("chat_access_denied", lang)
        MessageLogger.log_api_error("chat_access_check", user_id, message_in.chat_id, "聊天访问被拒绝")
        raise HTTPException(status_code=404, detail=error_msg)

    # 获取历史消息用于 token 预估
    messages = get_all_messages(message_in.chat_id, session)
    messages = [MessageOut.model_validate(m) for m in messages]

    # 预估本次对话的 token 消耗
    estimated_tokens = estimate_conversation_tokens(messages, message_in.content)
    
    # 会员限制检查（包含 token 预估）
    membership_service = MembershipService(session)
    can_send, limit_message = membership_service.can_user_send_message(
        user_id, message_in.chat_id, lang, estimated_tokens
    )

    if not can_send:
        MessageLogger.log_api_error("membership_limit", user_id, message_in.chat_id, limit_message)
        raise HTTPException(status_code=429, detail=limit_message)

    # 立即创建并保存用户消息 - 确保用户问题始终被记录
    user_message = create_message(message_in, session)
    messages.append(user_message)
    MessageLogger.log_user_message_saved(user_message.id, message_in.chat_id)

    if chat.agent_id:
        agent = get_agent_detail(session, chat.agent_id)
    else:
        error_msg = get_message("agent_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)

    if not stream:
        # 非流式模式 - 一次性生成完整回复
        MessageLogger.log_ai_response_start(chat.agent_id, False)
        assistant_message = None
        try:
            llm_response_content, usage_info = await create_agent_response(messages, agent, user_id, chat.id, session)
            
            # 创建并保存AI回复消息，包含 token 统计信息
            assistant_message = create_message(
                MessageCreate(
                    chat_id=message_in.chat_id,
                    content=llm_response_content,
                    role=MessageRole.ASSISTANT,
                    token_usage=usage_info,  # 保存真实的 token 统计
                ),
                session,
            )

            # 使用真实的 token 统计，如果没有则使用 0
            total_tokens = usage_info.get("total_tokens", 0)
            
            membership_service.record_usage(user_id, message_in.chat_id, 1, total_tokens)
            
            MessageLogger.log_ai_response_success(assistant_message.id, len(llm_response_content), total_tokens)
            MessageLogger.log_usage_recorded(user_id, message_in.chat_id, total_tokens)

            return [user_message, assistant_message]
            
        except Exception as e:
            MessageLogger.log_ai_response_error(str(e), message_in.chat_id)
            # 即使AI回复失败，也要创建一个错误消息记录
            error_content = f"抱歉，AI回复生成失败: {str(e)}"
            assistant_message = create_message(
                MessageCreate(
                    chat_id=message_in.chat_id,
                    content=error_content,
                    role=MessageRole.ASSISTANT,
                ),
                session,
            )
            MessageLogger.log_emergency_save(assistant_message.id, message_in.chat_id, "AI回复失败时创建错误消息")
            
            # 记录基础使用情况（AI 回复失败时不计算 token）
            membership_service.record_usage(user_id, message_in.chat_id, 1, 0)
            MessageLogger.log_usage_recorded(user_id, message_in.chat_id, 0)
            
            return [user_message, assistant_message]
    else:

        async def stream_gen():
            """
            增强的流式响应生成器
            
            功能说明:
            - 支持增量消息保存，避免页面刷新时丢失内容
            - 定期保存部分内容到数据库
            - 流式响应完成后保存完整消息
            - 确保所有情况下都能记录用户问题和AI回复
            """
            MessageLogger.log_ai_response_start(chat.agent_id, True)
            content_acc = ""
            message_id = None
            chunk_count = 0
            save_interval = 50  # 每50个chunk保存一次
            
            try:
                # 首先创建一个空的助手消息作为占位符
                with next(get_session()) as temp_session:
                    assistant_message = create_message(
                        MessageCreate(chat_id=message_in.chat_id, content="", role=MessageRole.ASSISTANT),
                        temp_session,
                    )
                    message_id = assistant_message.id
                    temp_session.commit()
                    MessageLogger.log_user_message_saved(message_id, message_in.chat_id)
                
                # 用于收集 token 统计信息
                final_usage_info = None
                
                # 使用统一的流式响应接口
                async for chunk_data in create_agent_response_stream(messages, agent, user_id, chat.id, None):
                    chunk, usage_info = chunk_data
                    
                    # 如果有内容，累积并输出
                    if chunk:
                        content_acc += chunk
                        chunk_count += 1
                        yield chunk
                    
                    # 如果有 token 统计信息，保存它
                    if usage_info:
                        final_usage_info = usage_info
                    
                    # 定期保存部分内容（避免频繁数据库操作）
                    if chunk_count % save_interval == 0 and message_id:
                        try:
                            with next(get_session()) as update_session:
                                # 更新消息内容
                                update_message_content(message_id, content_acc, update_session)
                                update_session.commit()
                                MessageLogger.log_stream_progress(message_id, chunk_count, len(content_acc))
                        except Exception as e:
                            # 增量保存失败不影响流式响应
                            MessageLogger.log_api_error("stream_incremental_save", user_id, message_in.chat_id, str(e))
                
                # 流式响应完成后，保存最终完整内容和 token 统计
                if message_id:
                    with next(get_session()) as final_session:
                        # 确保 token 统计信息被正确保存
                        update_message_content(message_id, content_acc, final_session, final_usage_info)
                        
                        # 使用真实的 token 统计，如果没有则使用 0
                        total_tokens = final_usage_info.get("total_tokens", 0) if final_usage_info else 0
                        
                        new_membership_service = MembershipService(final_session)
                        new_membership_service.record_usage(user_id, message_in.chat_id, 1, total_tokens)
                        
                        final_session.commit()
                        MessageLogger.log_ai_response_success(message_id, len(content_acc), total_tokens)
                        MessageLogger.log_usage_recorded(user_id, message_in.chat_id, total_tokens)
                        
                        # 输出一个特殊的标记，表示流式响应完成并包含 token 统计信息
                        # 前端可以通过这个标记来触发 token 统计的显示更新
                        if final_usage_info:
                            yield f"\n__TOKEN_USAGE__{final_usage_info['prompt_tokens']},{final_usage_info['completion_tokens']},{final_usage_info['total_tokens']}__END__"
                        
            except Exception as e:
                MessageLogger.log_ai_response_error(str(e), message_in.chat_id)
                # 如果流式响应出错，至少保存已生成的内容和错误信息
                if message_id:
                    try:
                        with next(get_session()) as error_session:
                            if content_acc:
                                error_content = content_acc + f"\n\n[响应中断: {str(e)}]"
                            else:
                                error_content = f"抱歉，AI回复生成失败: {str(e)}"
                            
                            update_message_content(message_id, error_content, error_session)
                            
                            # 记录基础使用情况（流式响应失败时不计算 token）
                            error_membership_service = MembershipService(error_session)
                            error_membership_service.record_usage(user_id, message_in.chat_id, 1, 0)
                            
                            error_session.commit()
                            MessageLogger.log_emergency_save(message_id, message_in.chat_id, "流式响应失败时保存错误信息")
                            MessageLogger.log_usage_recorded(user_id, message_in.chat_id, 0)
                    except Exception as save_error:
                        MessageLogger.log_api_error("stream_error_save", user_id, message_in.chat_id, str(save_error))
                
                # 重新抛出原始异常
                raise e

        return StreamingResponse(stream_gen(), media_type="text/plain")


@chat_router.put("/{chat_id}", response_model=ChatOut)
def update_chat_api(
    chat_id: int,
    chat_in: ChatUpdate,
    session: SessionDep,
    user: UserDep,
    lang: LangDep,
) -> ChatOut:
    chat = update_chat(chat_id, chat_in, session, user)
    if not chat:
        error_msg = get_message("chat_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)
    return chat


@chat_router.delete("/{chat_id}")
def delete_chat_api(chat_id: int, session: SessionDep, user: UserDep, lang: LangDep) -> dict:
    chat = soft_delete_chat(chat_id, session, user)
    if not chat:
        error_msg = get_message("chat_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)
    return {"message": get_message("chat_deleted", lang)}


@chat_router.get("", response_model=list[ChatOut])
def get_all_chats_api(
    session: SessionDep, 
    user: UserDep, 
    lang: LangDep,
    limit: int = 20,
    offset: int = 0,
    include_messages: bool = False
) -> list[ChatOut]:
    """
    获取用户的对话列表
    
    功能说明:
    - 支持分页查询，默认每页20条记录
    - 按更新时间倒序排列
    - 只返回未删除的对话
    - 可选择是否包含消息数据，用于一次性加载完整对话内容
    
    参数:
    - limit: 每页记录数，默认20，最大100
    - offset: 偏移量，默认0
    - include_messages: 是否包含消息数据，默认False，设为True时一次性返回所有消息
    - session: 数据库会话
    - user: 当前用户
    - lang: 语言设置
    
    返回:
    - list[ChatOut]: 对话列表，包含agent信息，可选包含完整消息数据
    """
    # 限制每页最大记录数
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 20
    if offset < 0:
        offset = 0
        
    chats = get_all_chats(session, user, limit=limit, offset=offset, include_messages=include_messages)
    return chats


@chat_router.get("/{chat_id}", response_model=ChatOut)
def get_chat_api(chat_id: int, session: SessionDep, user: UserDep, lang: LangDep) -> ChatOut:
    chat = get_chat(chat_id, session, user)
    if not chat:
        error_msg = get_message("chat_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)

    messages = get_all_messages(chat_id, session)
    chat_out = ChatOut.model_validate(chat)

    agent = get_agent_detail(session, chat.agent_id)
    if not agent:
        error_msg = get_message("agent_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)

    chat_out.agent = AgentSchema.model_validate(agent)
    chat_out.messages = [MessageOut.model_validate(m) for m in messages]
    return chat_out


@chat_router.get("/agents/active", response_model=list[AgentSchema])
def get_active_agents_api(session: SessionDep, user: UserDep, lang: LangDep) -> list[AgentSchema]:
    """获取所有活跃的 Agent 供用户选择"""
    agents = get_active_agents(session)
    return [AgentSchema.model_validate(agent) for agent in agents]


@chat_router.post("/agents/{agent_id}/test")
async def test_agent_availability(agent_id: int, session: SessionDep, user: UserDep, lang: LangDep):
    """测试 Agent 可用性"""
    # 获取 Agent 详情
    agent = get_agent_detail(session, agent_id)
    if not agent:
        error_msg = get_message("agent_not_found", lang)
        raise HTTPException(status_code=404, detail=error_msg)

    if agent.is_deleted:
        error_msg = get_message("agent_deleted", lang)
        raise HTTPException(status_code=400, detail=error_msg)

    # 测试 Agent 连接
    try:
        result = await test_agent_connection_unified(agent)
        return {
            "status": "success" if result["success"] else "error",
            "message": result["message"],
            "response_time": result.get("response_time"),
            "details": result.get("details"),
        }
    except Exception as e:
        error_msg = get_message("agent_test_failed", lang)
        return {"status": "error", "message": f"{error_msg}: {str(e)}", "details": None}


async def create_agent_response(messages: list[MessageOut], agent: Agent, user_id: int, chat_id: int, session=None) -> Tuple[str, Dict[str, int]]:
    if agent.source == AgentSource.DIFY:
        return await create_dify_response(messages, agent, user_id, chat_id, session)
    if agent.source == AgentSource.FASTGPT:
        return await create_fastgpt_response(messages, agent, user_id)
    return create_llm_response(messages, agent)


async def create_agent_response_stream(messages: list[MessageOut], agent: Agent, user_id: int, chat_id: int, session=None):
    if agent.source == AgentSource.DIFY:
        async for chunk_data in create_dify_response_stream(messages, agent, user_id, chat_id, session):
            yield chunk_data
        return

    if agent.source == AgentSource.FASTGPT:
        async for chunk_data in create_fastgpt_response_stream(messages, agent, user_id):
            yield chunk_data
        return

    async for chunk_data in create_llm_response_stream(messages, agent):
        yield chunk_data


async def test_agent_connection_unified(agent: Agent):
    if agent.source == AgentSource.DIFY:
        return await test_dify_connection(agent)
    if agent.source == AgentSource.FASTGPT:
        return await test_fastgpt_connection(agent)
    return await test_agent_connection(agent)
