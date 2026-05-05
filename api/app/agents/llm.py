import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional, Tuple

from openai import OpenAI, AsyncOpenAI

from app.agents.context import MemoryContext, build_provider_messages
from app.core.config import settings
from app.core.i18n import get_message
from app.core.logging import get_structured_logger, key_fingerprint
from app.models.agent import Agent
from app.schemas.message import MessageOut


llm_logger = get_structured_logger("app.llm_gateway")


@dataclass(frozen=True)
class LLMClientConfig:
    api_key: str
    base_url: str
    model: str
    model_conf: Dict[str, Any]
    gateway_enabled: bool


def normalize_openai_base_url(api_url: str) -> str:
    base_url = api_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    return base_url.rstrip("/")


def build_llm_client_config(agent: Optional[Agent]) -> LLMClientConfig:
    model_conf = dict(agent.model_conf or {}) if agent else {}

    if settings.LLM_GATEWAY_ENABLED:
        if not settings.LLM_GATEWAY_API_KEY:
            raise RuntimeError("LLM_GATEWAY_API_KEY is required when LLM_GATEWAY_ENABLED=true")

        model = settings.LLM_GATEWAY_MODEL_NAME or model_conf.get("model") or settings.AGENT_MODEL_NAME
        return LLMClientConfig(
            api_key=settings.LLM_GATEWAY_API_KEY,
            base_url=normalize_openai_base_url(settings.LLM_GATEWAY_BASE_URL),
            model=model,
            model_conf=model_conf,
            gateway_enabled=True,
        )

    if not agent:
        raise RuntimeError("agent is required when LLM_GATEWAY_ENABLED=false")

    model = model_conf.get("model", settings.AGENT_MODEL_NAME)
    return LLMClientConfig(
        api_key=agent.api_key,
        base_url=normalize_openai_base_url(agent.api_url),
        model=model,
        model_conf=model_conf,
        gateway_enabled=False,
    )


def build_chat_params(messages: list[dict[str, str]], config: LLMClientConfig, *, stream: bool = False) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.model_conf.get("temperature", settings.AGENT_MODEL_TEMPERATURE),
        "max_tokens": config.model_conf.get("max_tokens", 2000),
        "top_p": config.model_conf.get("top_p", 1.0),
        "frequency_penalty": config.model_conf.get("frequency_penalty", 0.0),
        "presence_penalty": config.model_conf.get("presence_penalty", 0.0),
    }
    if stream:
        params["stream"] = True
    return params


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量
    
    功能说明:
    - 使用简单的启发式方法估算 token 数量
    - 对于中文文本，大约每个字符对应 1.5 个 token
    - 对于英文文本，大约每 4 个字符对应 1 个 token
    - 这是一个粗略估算，实际 token 数可能有差异
    
    参数:
    - text: 要估算的文本
    
    返回:
    - int: 估算的 token 数量
    """
    if not text:
        return 0
    
    # 统计中文字符数量（Unicode 范围：\u4e00-\u9fff）
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    
    # 其余字符按英文处理
    other_chars = len(text) - chinese_chars
    
    # 中文字符：1.5 token/字符，英文字符：0.25 token/字符
    estimated_tokens = int(chinese_chars * 1.5 + other_chars * 0.25)
    
    return max(1, estimated_tokens)  # 至少返回 1


def estimate_conversation_tokens(messages: list[MessageOut], new_message_content: str = "") -> int:
    """
    估算整个对话的 token 消耗
    
    功能说明:
    - 估算历史消息和新消息的总 token 数
    - 包含系统消息、角色标识等的开销
    - 为 AI 回复预留 token 空间
    
    参数:
    - messages: 历史消息列表
    - new_message_content: 新消息内容
    
    返回:
    - int: 估算的总 token 数量
    """
    total_tokens = 0
    
    # 估算历史消息 token
    for message in messages:
        # 消息内容 + 角色标识开销（约 10 token）
        total_tokens += estimate_tokens(message.content) + 10
    
    # 估算新消息 token
    if new_message_content:
        total_tokens += estimate_tokens(new_message_content) + 10
    
    # 为 AI 回复预留空间（假设平均回复 500 token）
    total_tokens += 500
    
    # 系统消息和格式开销（约 50 token）
    total_tokens += 50
    
    return total_tokens


def _create_llm_response_unlogged(
    messages: list[MessageOut],
    agent: Optional[Agent] = None,
    memory_context: MemoryContext | None = None,
) -> Tuple[str, Dict[str, int]]:
    config = build_llm_client_config(agent)
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    params = build_chat_params(build_provider_messages(messages, memory_context=memory_context), config)
    response = client.chat.completions.create(**params)
    
    # 提取真实的 token 使用统计
    usage_info = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    }

    return response.choices[0].message.content, usage_info


async def _create_llm_response_stream_unlogged(
    messages: list[MessageOut],
    agent: Optional[Agent] = None,
    memory_context: MemoryContext | None = None,
) -> AsyncIterator[Tuple[str, Optional[Dict[str, int]]]]:
    """
    创建 LLM 流式响应（异步版本）
    
    功能说明:
    - 使用异步方式处理 OpenAI 流式响应
    - 避免阻塞事件循环，确保其他请求可以并发处理
    - 限制历史消息数量以控制 token 消耗
    
    参数:
    - messages: 消息历史列表
    - agent: Agent 配置对象
    
    返回:
    - AsyncIterator[Tuple[str, Optional[Dict[str, int]]]]: 异步生成器，逐块返回响应内容和 token 统计（仅在最后一个 chunk 中包含）
    """
    config = build_llm_client_config(agent)
    client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
    params = build_chat_params(build_provider_messages(messages, memory_context=memory_context), config, stream=True)
    
    # 使用异步流式处理
    stream = await client.chat.completions.create(**params)
    
    # 异步迭代流式响应
    async for chunk in stream:
        content = chunk.choices[0].delta.content if chunk.choices[0].delta else None
        if content:
            # 对于内容块，返回内容和 None（表示没有 usage 信息）
            yield content, None
        
        # 检查是否是最后一个 chunk，包含 usage 信息
        if hasattr(chunk, 'usage') and chunk.usage:
            usage_info = {
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens,
            }
            # 返回空内容和 usage 信息
            yield "", usage_info


def create_llm_response(
    messages: list[MessageOut],
    agent: Optional[Agent] = None,
    memory_context: MemoryContext | None = None,
    *,
    user_id: int | None = None,
    chat_id: int | None = None,
) -> Tuple[str, Dict[str, int]]:
    start_time = time.perf_counter()
    config: LLMClientConfig | None = None
    try:
        config = build_llm_client_config(agent)
        provider_messages = build_provider_messages(messages, memory_context=memory_context)
        client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        params = build_chat_params(provider_messages, config)
        llm_logger.info(
            "llm_request_start",
            user_id=user_id,
            chat_id=chat_id,
            model=config.model,
            key_hash=key_fingerprint(config.api_key),
            gateway_enabled=config.gateway_enabled,
            message_count=len(provider_messages),
        )
        response = client.chat.completions.create(**params)

        usage_info = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        llm_logger.info(
            "llm_request_success",
            user_id=user_id,
            chat_id=chat_id,
            model=config.model,
            key_hash=key_fingerprint(config.api_key),
            gateway_enabled=config.gateway_enabled,
            input_tokens=usage_info["prompt_tokens"],
            output_tokens=usage_info["completion_tokens"],
            total_tokens=usage_info["total_tokens"],
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )
        return response.choices[0].message.content, usage_info
    except Exception as exc:
        llm_logger.error(
            "llm_request_error",
            user_id=user_id,
            chat_id=chat_id,
            model=config.model if config else settings.AGENT_MODEL_NAME,
            key_hash=key_fingerprint(config.api_key) if config else None,
            gateway_enabled=config.gateway_enabled if config else settings.LLM_GATEWAY_ENABLED,
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


async def create_llm_response_stream(
    messages: list[MessageOut],
    agent: Optional[Agent] = None,
    memory_context: MemoryContext | None = None,
    *,
    user_id: int | None = None,
    chat_id: int | None = None,
) -> AsyncIterator[Tuple[str, Optional[Dict[str, int]]]]:
    start_time = time.perf_counter()
    config: LLMClientConfig | None = None
    final_usage_info: Dict[str, int] | None = None
    chunk_count = 0
    try:
        config = build_llm_client_config(agent)
        provider_messages = build_provider_messages(messages, memory_context=memory_context)
        client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
        params = build_chat_params(provider_messages, config, stream=True)
        llm_logger.info(
            "llm_stream_start",
            user_id=user_id,
            chat_id=chat_id,
            model=config.model,
            key_hash=key_fingerprint(config.api_key),
            gateway_enabled=config.gateway_enabled,
            message_count=len(provider_messages),
        )
        stream = await client.chat.completions.create(**params)

        async for chunk in stream:
            content = chunk.choices[0].delta.content if chunk.choices[0].delta else None
            if content:
                chunk_count += 1
                yield content, None

            if hasattr(chunk, "usage") and chunk.usage:
                final_usage_info = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }
                yield "", final_usage_info

        usage_info = final_usage_info or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        llm_logger.info(
            "llm_stream_success",
            user_id=user_id,
            chat_id=chat_id,
            model=config.model,
            key_hash=key_fingerprint(config.api_key),
            gateway_enabled=config.gateway_enabled,
            input_tokens=usage_info["prompt_tokens"],
            output_tokens=usage_info["completion_tokens"],
            total_tokens=usage_info["total_tokens"],
            chunk_count=chunk_count,
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )
    except Exception as exc:
        llm_logger.error(
            "llm_stream_error",
            user_id=user_id,
            chat_id=chat_id,
            model=config.model if config else settings.AGENT_MODEL_NAME,
            key_hash=key_fingerprint(config.api_key) if config else None,
            gateway_enabled=config.gateway_enabled if config else settings.LLM_GATEWAY_ENABLED,
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


async def test_agent_connection(agent: Agent) -> Dict[str, Any]:
    """测试 Agent 连接可用性"""
    start_time = time.time()

    try:
        config = build_llm_client_config(agent)
        # 创建测试消息
        test_messages = [{"role": "user", "content": "hi"}]

        # 根据 Agent 配置创建客户端
        client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        params = build_chat_params(test_messages, config)
        params["max_tokens"] = min(config.model_conf.get("max_tokens", 100), 100)

        # 执行测试请求
        def sync_test():
            return client.chat.completions.create(**params)

        # 在线程池中运行同步调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, sync_test)

        # 计算响应时间
        response_time = round((time.time() - start_time) * 1000, 2)  # 毫秒

        # 检查响应内容
        if response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content.strip()
            return {
                "success": True,
                "message": get_message("agent_connection_normal"),
                "response_time": response_time,
                "details": {
                    "model": response.model,
                    "response_content": (content[:100] + "..." if len(content) > 100 else content),
                    "usage": (
                        {
                            "prompt_tokens": (response.usage.prompt_tokens if response.usage else 0),
                            "completion_tokens": (response.usage.completion_tokens if response.usage else 0),
                            "total_tokens": (response.usage.total_tokens if response.usage else 0),
                        }
                        if response.usage
                        else None
                    ),
                },
            }
        else:
            return {
                "success": False,
                "message": get_message("agent_response_empty"),
                "response_time": response_time,
                "details": {"response": str(response)},
            }

    except Exception as e:
        response_time = round((time.time() - start_time) * 1000, 2)
        error_message = str(e)

        # 根据错误类型提供更友好的错误信息
        if "401" in error_message or "Unauthorized" in error_message:
            friendly_message = get_message("api_key_invalid")
        elif "404" in error_message or "Not Found" in error_message:
            friendly_message = get_message("api_endpoint_not_found")
        elif "timeout" in error_message.lower():
            friendly_message = get_message("request_timeout")
        elif "connection" in error_message.lower():
            friendly_message = get_message("connection_failed")
        elif "rate limit" in error_message.lower():
            friendly_message = get_message("api_rate_limit")
        else:
            friendly_message = f"{get_message('connection_failed')}: {error_message}"

        return {
            "success": False,
            "message": friendly_message,
            "response_time": response_time,
            "details": {
                "error_type": type(e).__name__,
                "error_message": error_message,
                "agent_config": {
                    "gateway_enabled": settings.LLM_GATEWAY_ENABLED,
                    "model": config.model if "config" in locals() else settings.AGENT_MODEL_NAME,
                },
            },
        }
