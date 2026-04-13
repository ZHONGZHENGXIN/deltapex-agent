import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from sqlmodel import Session

from app.core.i18n import get_message
from app.core.logging import get_logger
from app.crud.chat import get_chat_conversation_id, update_chat_others
from app.models.agent import Agent
from app.schemas.message import MessageOut, MessageRole

logger = get_logger(__name__)


async def create_dify_response(
    messages: List[MessageOut],
    agent: Agent,
    user_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> Tuple[str, Dict[str, int]]:
    """
    创建 Dify 非流式响应

    Args:
        messages: 消息历史
        agent: Agent 配置
        user_id: 用户ID（可选）
        chat_id: 对话ID（可选）
        session: 数据库会话（可选）

    Returns:
        Tuple[str, Dict[str, int]]: Dify API 响应内容和 token 使用统计
    """
    # 获取最后一条用户消息作为查询
    query = ""
    for message in reversed(messages):
        if message.role == MessageRole.USER:
            query = message.content
            break

    if not query:
        raise ValueError(get_message("user_message_not_found"))

    # 获取之前的 conversation_id（如果存在）
    conversation_id = ""
    if chat_id and session:
        existing_conversation_id = get_chat_conversation_id(chat_id, session)
        if existing_conversation_id:
            conversation_id = existing_conversation_id

    # 构建请求数据
    request_data = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",  # 非流式模式
        "conversation_id": conversation_id,
        "user": f"user_{user_id}" if user_id else "",
    }

    # 构建请求头
    headers = {
        "Authorization": f"Bearer {agent.api_key}",
        "Content-Type": "application/json",
    }

    # 发送请求
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(agent.api_url, headers=headers, json=request_data)
            response.raise_for_status()

            result = response.json()

            # 保存新的 conversation_id（如果有的话）
            if chat_id and session and "conversation_id" in result:
                new_conversation_id = result["conversation_id"]
                if new_conversation_id and new_conversation_id != conversation_id:
                    try:
                        others_data = {"conversation_id": new_conversation_id}
                        update_chat_others(chat_id, others_data, session)
                    except Exception as e:
                        # 记录错误但不影响主流程

                        logger.error(f"{get_message('update_chat_others_failed')}: {e}")

            # 解析响应内容
            response_content = ""
            if "answer" in result:
                response_content = result["answer"]
            elif "message" in result:
                response_content = result["message"]
            else:
                response_content = str(result)
            
            # 解析 token 使用统计
            usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            # Dify API 可能在 metadata 或 usage 字段中返回 token 统计
            if "metadata" in result and "usage" in result["metadata"]:
                dify_usage = result["metadata"]["usage"]
                usage_info = {
                    "prompt_tokens": dify_usage.get("prompt_tokens", 0),
                    "completion_tokens": dify_usage.get("completion_tokens", 0),
                    "total_tokens": dify_usage.get("total_tokens", 0)
                }
            elif "usage" in result:
                dify_usage = result["usage"]
                usage_info = {
                    "prompt_tokens": dify_usage.get("prompt_tokens", 0),
                    "completion_tokens": dify_usage.get("completion_tokens", 0),
                    "total_tokens": dify_usage.get("total_tokens", 0)
                }
            
            # 打印 token usage 信息用于调试
            logger.info(f"Dify API token usage: {usage_info}")
            
            return response_content, usage_info

        except httpx.HTTPStatusError as e:
            error_detail = f"{get_message('dify_api_error')} {e.response.status_code}: {e.response.text}"
            raise Exception(error_detail)
        except httpx.RequestError as e:
            raise Exception(f"{get_message('dify_api_request_failed')}: {str(e)}")


async def create_dify_response_stream(
    messages: List[MessageOut],
    agent: Agent,
    user_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> AsyncIterator[Tuple[str, Optional[Dict[str, int]]]]:
    """
    创建 Dify 流式响应

    Args:
        messages: 消息历史
        agent: Agent 配置
        user_id: 用户ID（可选）
        chat_id: 对话ID（可选）
        session: 数据库会话（可选）

    Yields:
        Tuple[str, Optional[Dict[str, int]]]: 流式响应的文本块和可选的 token 统计
    """
    # 获取最后一条用户消息作为查询
    query = ""
    for message in reversed(messages):
        if message.role == MessageRole.USER:
            query = message.content
            break

    if not query:
        raise ValueError(get_message("user_message_not_found"))

    # 获取之前的 conversation_id（如果存在）
    conversation_id = ""
    if chat_id and session:
        existing_conversation_id = get_chat_conversation_id(chat_id, session)
        if existing_conversation_id:
            conversation_id = existing_conversation_id

    # 构建请求数据
    request_data = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",  # 流式模式
        "conversation_id": conversation_id,
        "user": f"user_{user_id}" if user_id else "",
    }

    # 构建请求头
    headers = {
        "Authorization": f"Bearer {agent.api_key}",
        "Content-Type": "application/json",
    }

    # 发送流式请求
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 用于收集 token 使用统计
            usage_info = None
            
            async with client.stream("POST", agent.api_url, headers=headers, json=request_data) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        # 处理 Server-Sent Events 格式
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀

                            # 跳过心跳包
                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)

                                # 处理不同类型的事件
                                event = data.get("event", "")

                                if event == "message":
                                    # 消息内容
                                    answer = data.get("answer", "")
                                    if answer:
                                        yield answer, None

                                elif event == "message_end":
                                    new_conversation_id = data.get("conversation_id", "")
                                    # 消息结束，可以获取完整信息和 token 统计
                                    
                                    # 解析 token 使用统计
                                    if "metadata" in data and "usage" in data["metadata"]:
                                        dify_usage = data["metadata"]["usage"]
                                        usage_info = {
                                            "prompt_tokens": dify_usage.get("prompt_tokens", 0),
                                            "completion_tokens": dify_usage.get("completion_tokens", 0),
                                            "total_tokens": dify_usage.get("total_tokens", 0)
                                        }
                                    elif "usage" in data:
                                        dify_usage = data["usage"]
                                        usage_info = {
                                            "prompt_tokens": dify_usage.get("prompt_tokens", 0),
                                            "completion_tokens": dify_usage.get("completion_tokens", 0),
                                            "total_tokens": dify_usage.get("total_tokens", 0)
                                        }
                                    
                                    # 打印 token usage 信息用于调试
                                    if usage_info:
                                        logger.info(f"Dify stream API token usage: {usage_info}")

                                    # 如果有新的 conversation_id 且与之前的不同，更新 chat 表的 others 字段
                                    if new_conversation_id and chat_id and session and new_conversation_id != conversation_id:
                                        try:
                                            others_data = {"conversation_id": new_conversation_id}
                                            update_chat_others(chat_id, others_data, session)
                                        except Exception as e:
                                            # 记录错误但不影响主流程
                                            logger.error(f"更新 chat others 字段失败: {e}")

                                    # 在流式响应结束时返回 token 统计信息
                                    if usage_info:
                                        yield "", usage_info
                                    
                                    break

                                elif event == "error":
                                    # 错误处理
                                    error_msg = data.get("message", get_message("unknown_error"))
                                    raise Exception(f"{get_message('dify_api_error')}: {error_msg}")

                            except json.JSONDecodeError:
                                # 如果不是 JSON 格式，直接输出
                                if data_str.strip():
                                    yield data_str, None

        except httpx.HTTPStatusError as e:
            error_detail = f"{get_message('dify_api_error')} {e.response.status_code}: {e.response.text}"
            raise Exception(error_detail)
        except httpx.RequestError as e:
            raise Exception(f"{get_message('dify_api_request_failed')}: {str(e)}")


async def test_dify_connection(agent: Agent) -> Dict[str, Any]:
    """
    测试 Dify Agent 连接可用性

    Args:
        agent: Agent 配置

    Returns:
        测试结果字典
    """
    start_time = time.time()

    try:
        # 创建测试消息
        test_query = "hi"

        # 构建测试请求数据
        request_data = {
            "inputs": {},
            "query": test_query,
            "response_mode": "blocking",
            "conversation_id": "",
            "user": f"test_user_{int(time.time())}",
        }

        # 构建请求头
        headers = {
            "Authorization": f"Bearer {agent.api_key}",
            "Content-Type": "application/json",
        }

        # 发送测试请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(agent.api_url, headers=headers, json=request_data)

            # 计算响应时间
            response_time = round((time.time() - start_time) * 1000, 2)  # 毫秒

            response.raise_for_status()
            result = response.json()

            # 解析响应
            answer = result.get("answer", result.get("message", ""))

            if answer:
                return {
                    "success": True,
                    "message": get_message("dify_agent_connection_normal"),
                    "response_time": response_time,
                    "details": {
                        "response_content": (answer[:100] + "..." if len(answer) > 100 else answer),
                        "conversation_id": result.get("conversation_id"),
                        "message_id": result.get("message_id"),
                        "metadata": result.get("metadata", {}),
                    },
                }
            else:
                return {
                    "success": False,
                    "message": get_message("dify_agent_response_empty"),
                    "response_time": response_time,
                    "details": {"response": result},
                }

    except httpx.HTTPStatusError as e:
        response_time = round((time.time() - start_time) * 1000, 2)
        error_message = e.response.text

        # 根据错误状态码提供友好的错误信息
        if e.response.status_code == 401:
            friendly_message = get_message("api_key_invalid")
        elif e.response.status_code == 404:
            friendly_message = get_message("api_endpoint_not_found")
        elif e.response.status_code == 429:
            friendly_message = get_message("api_rate_limit")
        elif e.response.status_code == 500:
            friendly_message = get_message("dify_server_error")
        else:
            friendly_message = f"HTTP 错误 {e.response.status_code}: {error_message}"

        return {
            "success": False,
            "message": friendly_message,
            "response_time": response_time,
            "details": {
                "error_type": "HTTPStatusError",
                "status_code": e.response.status_code,
                "error_message": error_message,
                "agent_config": {"api_url": agent.api_url},
            },
        }

    except httpx.RequestError as e:
        response_time = round((time.time() - start_time) * 1000, 2)
        error_message = str(e)

        # 根据错误类型提供友好的错误信息
        if "timeout" in error_message.lower():
            friendly_message = get_message("request_timeout")
        elif "connection" in error_message.lower():
            friendly_message = get_message("connection_failed")
        else:
            friendly_message = f"{get_message('connection_failed')}: {error_message}"

        return {
            "success": False,
            "message": friendly_message,
            "response_time": response_time,
            "details": {
                "error_type": type(e).__name__,
                "error_message": error_message,
                "agent_config": {"api_url": agent.api_url},
            },
        }

    except Exception as e:
        response_time = round((time.time() - start_time) * 1000, 2)
        error_message = str(e)

        return {
            "success": False,
            "message": f"{get_message('test_failed')}: {error_message}",
            "response_time": response_time,
            "details": {
                "error_type": type(e).__name__,
                "error_message": error_message,
                "agent_config": {"api_url": agent.api_url},
            },
        }
