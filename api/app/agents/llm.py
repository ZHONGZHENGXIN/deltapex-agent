import asyncio
import time
from typing import Any, AsyncIterator, Dict, Optional, Tuple

from openai import OpenAI, AsyncOpenAI

from app.core.config import settings
from app.core.i18n import get_message
from app.models.agent import Agent
from app.schemas.message import MessageOut


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


def create_llm_response(messages: list[MessageOut], agent: Optional[Agent] = None) -> Tuple[str, Dict[str, int]]:
    _messages = []
    for message in messages:
        _messages.append({"role": message.role, "content": message.content})

    # Use agent configuration if provided
    client = OpenAI(api_key=agent.api_key, base_url=agent.api_url.replace("/chat/completions", ""))
    model_conf = agent.model_conf or {}
    model = model_conf.get("model", settings.AGENT_MODEL_NAME)
    # Extract other parameters from model_conf
    params = {
        "model": model,
        "messages": _messages,
        "temperature": model_conf.get("temperature", settings.AGENT_MODEL_TEMPERATURE),
        "max_tokens": model_conf.get("max_tokens", 2000),
        "top_p": model_conf.get("top_p", 1.0),
        "frequency_penalty": model_conf.get("frequency_penalty", 0.0),
        "presence_penalty": model_conf.get("presence_penalty", 0.0),
    }
    response = client.chat.completions.create(**params)
    
    # 提取真实的 token 使用统计
    usage_info = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    }

    return response.choices[0].message.content, usage_info


async def create_llm_response_stream(messages: list[MessageOut], agent: Optional[Agent] = None) -> AsyncIterator[Tuple[str, Optional[Dict[str, int]]]]:
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
    _messages = []
    # only use first 20 messages
    for message in messages[:20]:
        _messages.append({"role": message.role, "content": message.content})

    client = AsyncOpenAI(api_key=agent.api_key, base_url=agent.api_url.replace("/chat/completions", ""))
    model_conf = agent.model_conf or {}
    model = model_conf.get("model", settings.AGENT_MODEL_NAME)
    # Extract other parameters from model_conf
    params = {
        "model": model,
        "messages": _messages,
        "temperature": model_conf.get("temperature", settings.AGENT_MODEL_TEMPERATURE),
        "max_tokens": model_conf.get("max_tokens", 2000),
        "top_p": model_conf.get("top_p", 1.0),
        "frequency_penalty": model_conf.get("frequency_penalty", 0.0),
        "presence_penalty": model_conf.get("presence_penalty", 0.0),
        "stream": True,
    }
    
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


async def test_agent_connection(agent: Agent) -> Dict[str, Any]:
    """测试 Agent 连接可用性"""
    start_time = time.time()

    try:
        # 创建测试消息
        test_messages = [{"role": "user", "content": "hi"}]

        # 根据 Agent 配置创建客户端
        client = OpenAI(
            api_key=agent.api_key,
            base_url=agent.api_url.replace("/chat/completions", ""),
        )

        # 获取模型配置
        model_conf = agent.model_conf or {}
        model = model_conf.get("model", settings.AGENT_MODEL_NAME)

        # 构建请求参数
        params = {
            "model": model,
            "messages": test_messages,
            "temperature": model_conf.get("temperature", settings.AGENT_MODEL_TEMPERATURE),
            "max_tokens": min(model_conf.get("max_tokens", 100), 100),  # 限制测试时的 token 数量
            "top_p": model_conf.get("top_p", 1.0),
            "frequency_penalty": model_conf.get("frequency_penalty", 0.0),
            "presence_penalty": model_conf.get("presence_penalty", 0.0),
        }

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
                    "api_url": agent.api_url,
                    "model": (model_conf.get("model", settings.AGENT_MODEL_NAME) if model_conf else settings.AGENT_MODEL_NAME),
                },
            },
        }
