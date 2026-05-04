import traceback
from functools import wraps
from typing import Dict, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.dify import create_dify_response, create_dify_response_stream, test_dify_connection
from app.agents.fastgpt import create_fastgpt_response, create_fastgpt_response_stream, test_fastgpt_connection
from app.agents.llm import create_llm_response, create_llm_response_stream, estimate_conversation_tokens, test_agent_connection
from app.core.i18n import get_message
from app.crud.agent import get_active_agents, get_agent_detail
from app.crud.chat import chat_to_out, create_chat, get_all_chats, get_chat, get_chat_record, soft_delete_chat, update_chat
from app.crud.membership import get_chat_turn_count
from app.crud.message import create_message, get_all_messages, message_to_out, update_message_content
from app.db.base import get_session
from app.db.rls import set_rls_context
from app.dependencies.db import LangDep, SessionDep, UserDep
from app.models.agent import Agent, AgentSource
from app.schemas.agent import AgentPublic
from app.schemas.chat import ChatCreate, ChatOut, ChatUpdate
from app.schemas.message import MessageCreate, MessageOut, MessageRole, UserMessageCreate
from app.services.billing_service import BillingService
from app.services.membership_service import MembershipService

chat_router = APIRouter(prefix="/chat")


class MessageLogger:
    @staticmethod
    def log_message_start(user_id: int, chat_id: Union[int, str], content_length: int, is_stream: bool = False):
        print(
            f"[message:start] user_id={user_id} chat_id={chat_id} content_length={content_length} stream={is_stream}"
        )

    @staticmethod
    def log_user_message_saved(message_id: int, chat_id: Union[int, str]):
        print(f"[message:saved] message_id={message_id} chat_id={chat_id}")

    @staticmethod
    def log_ai_response_start(agent_id: int, is_stream: bool = False):
        print(f"[ai:start] agent_id={agent_id} stream={is_stream}")

    @staticmethod
    def log_ai_response_success(message_id: int, content_length: int, tokens: int):
        print(f"[ai:success] message_id={message_id} content_length={content_length} tokens={tokens}")

    @staticmethod
    def log_ai_response_error(error: str, chat_id: Union[int, str]):
        print(f"[ai:error] chat_id={chat_id} error={error}")

    @staticmethod
    def log_stream_progress(message_id: int, chunks: int, content_length: int):
        print(f"[stream:progress] message_id={message_id} chunks={chunks} content_length={content_length}")

    @staticmethod
    def log_usage_recorded(user_id: int, chat_id: Union[int, str], tokens: int):
        print(f"[usage] user_id={user_id} chat_id={chat_id} tokens={tokens}")

    @staticmethod
    def log_api_error(function_name: str, user_id: int, chat_id: Union[int, str], error: str):
        print(f"[api:error] function={function_name} user_id={user_id} chat_id={chat_id} error={error}")


def ensure_message_logging(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            MessageLogger.log_api_error(func.__name__, 0, 0, traceback.format_exc())
            raise exc

    return wrapper


async def create_agent_response(
    messages: list[MessageOut], agent: Agent, user_id: int, chat_id: int, session=None
) -> Tuple[str, Dict[str, int]]:
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


def _calculate_paid_tokens(total_tokens: int, remaining_free_tokens_before_request: int) -> int:
    free_used = min(total_tokens, remaining_free_tokens_before_request)
    return max(0, total_tokens - free_used)


@chat_router.post("", response_model=ChatOut)
async def create_chat_api(chat_in: ChatCreate, session: SessionDep, user: UserDep, lang: LangDep) -> ChatOut:
    if chat_in.agent_id:
        agent = get_agent_detail(session, chat_in.agent_id)
        if not agent or agent.is_deleted:
            raise HTTPException(status_code=404, detail=get_message("agent_not_found_or_inactive", lang))
    else:
        raise HTTPException(status_code=404, detail=get_message("agent_not_found", lang))

    chat = create_chat(chat_in, session, user)
    MembershipService(session).record_usage(user.id, chat.id, message_count=0, token_count=0, is_new_chat=True)

    return chat_to_out(chat, agent)


@chat_router.post("/message", response_model=list[MessageOut])
@ensure_message_logging
async def create_chat_message_api(
    message_in: UserMessageCreate,
    session: SessionDep,
    user: UserDep,
    lang: LangDep,
    stream: bool = False,
):
    user_id = user.id
    public_chat_id = message_in.chat_id
    MessageLogger.log_message_start(user_id, public_chat_id, len(message_in.content), stream)

    chat = get_chat_record(public_chat_id, session, user)
    if not chat:
        raise HTTPException(status_code=404, detail=get_message("chat_access_denied", lang))

    internal_chat_id = chat.id
    history = get_all_messages(internal_chat_id, user_id, session)
    messages = [message_to_out(message, public_chat_id) for message in history]
    estimated_tokens = estimate_conversation_tokens(messages, message_in.content)

    membership_service = MembershipService(session)
    membership_status = membership_service.get_user_membership_status(user_id)
    current_turns = get_chat_turn_count(session, internal_chat_id, user_id)

    if membership_status.daily_message_remaining <= 0:
        limit_message = get_message("daily_message_limit_reached", lang)
        MessageLogger.log_api_error("membership_limit", user_id, public_chat_id, limit_message)
        raise HTTPException(status_code=429, detail=limit_message)

    if current_turns >= membership_status.conversation_turn_limit:
        limit_message = get_message("conversation_turn_limit_reached", lang)
        MessageLogger.log_api_error("membership_limit", user_id, public_chat_id, limit_message)
        raise HTTPException(status_code=429, detail=limit_message)

    billing_service = BillingService(session)
    balance_check = billing_service.ensure_sufficient_balance(
        user_id=user_id,
        chat_id=internal_chat_id,
        estimated_tokens=estimated_tokens,
    )
    remaining_free_tokens_before_request = balance_check.remaining_free_tokens

    user_message = create_message(
        MessageCreate(
            chat_id=internal_chat_id,
            user_id=user_id,
            content=message_in.content,
            role=MessageRole.USER,
        ),
        session,
    )
    user_message_out = message_to_out(user_message, public_chat_id)
    messages.append(user_message_out)
    MessageLogger.log_user_message_saved(user_message.id, public_chat_id)

    if not chat.agent_id:
        raise HTTPException(status_code=404, detail=get_message("agent_not_found", lang))

    agent = get_agent_detail(session, chat.agent_id)
    if not agent or agent.is_deleted:
        raise HTTPException(status_code=404, detail=get_message("agent_not_found", lang))

    if not stream:
        MessageLogger.log_ai_response_start(chat.agent_id, False)
        try:
            llm_response_content, usage_info = await create_agent_response(messages, agent, user_id, internal_chat_id, session)
            assistant_message = create_message(
                MessageCreate(
                    chat_id=internal_chat_id,
                    user_id=user_id,
                    content=llm_response_content,
                    role=MessageRole.ASSISTANT,
                    token_usage=usage_info,
                ),
                session,
            )
            total_tokens = usage_info.get("total_tokens", 0)
            membership_service.record_usage(user_id, internal_chat_id, 1, total_tokens)
            billing_service.consume_paid_tokens(
                user_id=user_id,
                message_id=assistant_message.id,
                paid_tokens=_calculate_paid_tokens(total_tokens, remaining_free_tokens_before_request),
            )
            MessageLogger.log_ai_response_success(assistant_message.id, len(llm_response_content), total_tokens)
            MessageLogger.log_usage_recorded(user_id, public_chat_id, total_tokens)
            return [user_message_out, message_to_out(assistant_message, public_chat_id)]
        except Exception as exc:
            MessageLogger.log_ai_response_error(str(exc), public_chat_id)
            assistant_message = create_message(
                MessageCreate(
                    chat_id=internal_chat_id,
                    user_id=user_id,
                    content=f"AI response failed: {exc}",
                    role=MessageRole.ASSISTANT,
                ),
                session,
            )
            membership_service.record_usage(user_id, internal_chat_id, 1, 0)
            return [user_message_out, message_to_out(assistant_message, public_chat_id)]

    async def stream_gen():
        MessageLogger.log_ai_response_start(chat.agent_id, True)
        content_acc = ""
        chunk_count = 0
        message_id: Optional[int] = None
        final_usage_info: Optional[Dict[str, int]] = None

        try:
            with next(get_session()) as temp_session:
                set_rls_context(temp_session, user_id=user_id)
                assistant_message = create_message(
                    MessageCreate(chat_id=internal_chat_id, user_id=user_id, content="", role=MessageRole.ASSISTANT),
                    temp_session,
                )
                message_id = assistant_message.id
                temp_session.commit()

            async for chunk, usage_info in create_agent_response_stream(messages, agent, user_id, internal_chat_id, None):
                if chunk:
                    content_acc += chunk
                    chunk_count += 1
                    yield chunk

                if usage_info:
                    final_usage_info = usage_info

                if message_id and chunk_count > 0 and chunk_count % 50 == 0:
                    with next(get_session()) as update_session:
                        set_rls_context(update_session, user_id=user_id)
                        update_message_content(message_id, content_acc, update_session, user_id=user_id)
                        update_session.commit()
                        MessageLogger.log_stream_progress(message_id, chunk_count, len(content_acc))

            if message_id:
                with next(get_session()) as final_session:
                    set_rls_context(final_session, user_id=user_id)
                    update_message_content(message_id, content_acc, final_session, final_usage_info, user_id=user_id)
                    total_tokens = final_usage_info.get("total_tokens", 0) if final_usage_info else 0
                    MembershipService(final_session).record_usage(user_id, internal_chat_id, 1, total_tokens)
                    BillingService(final_session).consume_paid_tokens(
                        user_id=user_id,
                        message_id=message_id,
                        paid_tokens=_calculate_paid_tokens(total_tokens, remaining_free_tokens_before_request),
                    )
                    final_session.commit()
                    MessageLogger.log_ai_response_success(message_id, len(content_acc), total_tokens)
                    MessageLogger.log_usage_recorded(user_id, public_chat_id, total_tokens)

                    if final_usage_info:
                        yield (
                            f"\n__TOKEN_USAGE__{final_usage_info['prompt_tokens']},"
                            f"{final_usage_info['completion_tokens']},{final_usage_info['total_tokens']}__END__"
                        )
        except Exception as exc:
            MessageLogger.log_ai_response_error(str(exc), public_chat_id)
            if message_id:
                with next(get_session()) as error_session:
                    set_rls_context(error_session, user_id=user_id)
                    error_content = content_acc + f"\n\n[response interrupted: {exc}]" if content_acc else f"AI response failed: {exc}"
                    update_message_content(message_id, error_content, error_session, user_id=user_id)
                    MembershipService(error_session).record_usage(user_id, internal_chat_id, 1, 0)
                    error_session.commit()
            raise exc

    return StreamingResponse(stream_gen(), media_type="text/plain")


@chat_router.put("/{chat_id}", response_model=ChatOut)
def update_chat_api(chat_id: str, chat_in: ChatUpdate, session: SessionDep, user: UserDep, lang: LangDep) -> ChatOut:
    chat = update_chat(chat_id, chat_in, session, user)
    if not chat:
        raise HTTPException(status_code=404, detail=get_message("chat_not_found", lang))
    return chat_to_out(chat)


@chat_router.delete("/{chat_id}")
def delete_chat_api(chat_id: str, session: SessionDep, user: UserDep, lang: LangDep) -> dict:
    chat = soft_delete_chat(chat_id, session, user)
    if not chat:
        raise HTTPException(status_code=404, detail=get_message("chat_not_found", lang))
    return {"message": get_message("chat_deleted", lang)}


@chat_router.get("", response_model=list[ChatOut])
def get_all_chats_api(
    session: SessionDep,
    user: UserDep,
    lang: LangDep,
    limit: int = 20,
    offset: int = 0,
    include_messages: bool = False,
) -> list[ChatOut]:
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 20
    if offset < 0:
        offset = 0
    return get_all_chats(session, user, limit=limit, offset=offset, include_messages=include_messages)


@chat_router.get("/agents/active", response_model=list[AgentPublic])
def get_active_agents_api(session: SessionDep, user: UserDep, lang: LangDep) -> list[AgentPublic]:
    agents = get_active_agents(session)
    return [AgentPublic.model_validate(agent) for agent in agents]


@chat_router.get("/{chat_id}", response_model=ChatOut)
def get_chat_api(chat_id: str, session: SessionDep, user: UserDep, lang: LangDep) -> ChatOut:
    chat = get_chat(chat_id, session, user)
    if not chat:
        raise HTTPException(status_code=404, detail=get_message("chat_not_found", lang))

    agent = get_agent_detail(session, chat.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=get_message("agent_not_found", lang))

    chat_record = get_chat_record(chat_id, session, user)
    if not chat_record:
        raise HTTPException(status_code=404, detail=get_message("chat_not_found", lang))
    messages = get_all_messages(chat_record.id, user.id, session)
    chat_out = chat_to_out(chat_record, agent, messages)
    return chat_out


@chat_router.post("/agents/{agent_id}/test")
async def test_agent_availability(agent_id: int, session: SessionDep, user: UserDep, lang: LangDep):
    agent = get_agent_detail(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=get_message("agent_not_found", lang))

    if agent.is_deleted:
        raise HTTPException(status_code=400, detail=get_message("agent_deleted", lang))

    try:
        result = await test_agent_connection_unified(agent)
        return {
            "status": "success" if result["success"] else "error",
            "message": result["message"],
            "response_time": result.get("response_time"),
            "details": result.get("details"),
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"{get_message('agent_test_failed', lang)}: {exc}",
            "details": None,
        }
