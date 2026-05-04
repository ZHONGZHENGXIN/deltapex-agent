import json
import time
from typing import Any, AsyncIterator, Dict, Optional, Tuple

import httpx

from app.agents.context import MemoryContext, build_provider_messages
from app.core.config import settings
from app.core.i18n import get_message
from app.models.agent import Agent
from app.schemas.message import MessageOut


def _build_messages(messages: list[MessageOut], memory_context: MemoryContext | None = None) -> list[dict[str, str]]:
    return build_provider_messages(messages, memory_context=memory_context)


def _build_payload(
    messages: list[MessageOut],
    agent: Agent,
    user_id: int,
    *,
    stream: bool,
    memory_context: MemoryContext | None = None,
) -> dict[str, Any]:
    model_conf = agent.model_conf or {}
    payload = {
        "model": model_conf.get("model", settings.AGENT_MODEL_NAME),
        "messages": _build_messages(messages, memory_context),
        "temperature": model_conf.get("temperature", settings.AGENT_MODEL_TEMPERATURE),
        "max_tokens": model_conf.get("max_tokens", 2000),
        "top_p": model_conf.get("top_p", 1.0),
        "frequency_penalty": model_conf.get("frequency_penalty", 0.0),
        "presence_penalty": model_conf.get("presence_penalty", 0.0),
        "stream": stream,
        "customUid": str(user_id),
    }
    if stream:
        # FastGPT returns detailed node usage in flowResponses only when detail=true.
        payload["detail"] = True
    return payload


def _headers(agent: Agent) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {agent.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _extract_usage(data: dict[str, Any]) -> Dict[str, int]:
    usage = data.get("usage") or data.get("responseData", {}).get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("inputTokens") or 0
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("outputTokens") or 0
    total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)
    return {
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


def _extract_flow_usage(flow_data: list[dict[str, Any]]) -> Dict[str, int]:
    total_tokens = 0
    for item in flow_data:
        if not isinstance(item, dict):
            continue
        total_tokens += _extract_token_count(item)

    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": total_tokens,
    }


def _extract_token_count(item: Any) -> int:
    if item is None:
        return 0

    if isinstance(item, (int, float)):
        return int(item)

    if isinstance(item, list):
        return sum(_extract_token_count(child) for child in item)

    if not isinstance(item, dict):
        return 0

    for key in ("tokens", "total_tokens", "totalTokens"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return int(value)

    input_tokens = item.get("inputTokens")
    output_tokens = item.get("outputTokens")
    if isinstance(input_tokens, (int, float)) or isinstance(output_tokens, (int, float)):
        return int(input_tokens or 0) + int(output_tokens or 0)

    nested_candidates = (
        item.get("usage"),
        item.get("responseData"),
        item.get("flowResponses"),
    )
    for nested in nested_candidates:
        token_count = _extract_token_count(nested)
        if token_count > 0:
            return token_count

    return 0


def _extract_content(data: dict[str, Any]) -> str:
    if data.get("choices"):
        return data["choices"][0].get("message", {}).get("content", "") or ""
    return data.get("text") or data.get("content") or ""


async def create_fastgpt_response(
    messages: list[MessageOut],
    agent: Agent,
    user_id: int,
    memory_context: MemoryContext | None = None,
) -> Tuple[str, Dict[str, int]]:
    payload = _build_payload(messages, agent, user_id, stream=False, memory_context=memory_context)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(agent.api_url, headers=_headers(agent), json=payload)
        response.raise_for_status()
        data = response.json()

    return _extract_content(data), _extract_usage(data)


async def create_fastgpt_response_stream(
    messages: list[MessageOut],
    agent: Agent,
    user_id: int,
    memory_context: MemoryContext | None = None,
) -> AsyncIterator[Tuple[str, Optional[Dict[str, int]]]]:
    payload = _build_payload(messages, agent, user_id, stream=True, memory_context=memory_context)
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", agent.api_url, headers=_headers(agent), json=payload) as response:
            response.raise_for_status()
            current_event = ""
            final_usage_info: Optional[Dict[str, int]] = None
            async for line in response.aiter_lines():
                if not line:
                    continue

                raw_line = line.strip()
                if raw_line.startswith("event:"):
                    current_event = raw_line[6:].strip()
                    continue

                if raw_line.startswith("data:"):
                    raw_line = raw_line[5:].strip()

                if raw_line == "[DONE]":
                    # FastGPT sends [DONE] for the answer stream first, then may continue
                    # with detail events such as flowResponses when detail=true.
                    current_event = ""
                    continue

                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                if isinstance(data, list):
                    if current_event == "flowResponses":
                        usage_info = _extract_flow_usage(data)
                        if usage_info["total_tokens"] > 0:
                            final_usage_info = usage_info
                    continue

                if current_event == "flowResponses" and isinstance(data.get("flowResponses"), list):
                    usage_info = _extract_flow_usage(data["flowResponses"])
                    if usage_info["total_tokens"] > 0:
                        final_usage_info = usage_info

                if current_event == "flowResponses" and isinstance(data.get("responseData"), list):
                    usage_info = _extract_flow_usage(data["responseData"])
                    if usage_info["total_tokens"] > 0:
                        final_usage_info = usage_info

                if current_event == "flowResponses" and isinstance(data.get("responseData"), dict):
                    usage_info = _extract_flow_usage([data["responseData"]])
                    if usage_info["total_tokens"] > 0:
                        final_usage_info = usage_info

                usage_info = _extract_usage(data)
                if usage_info["total_tokens"] > 0:
                    final_usage_info = usage_info

                choices = data.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        yield content, None

            if final_usage_info and final_usage_info["total_tokens"] > 0:
                yield "", final_usage_info


async def test_fastgpt_connection(agent: Agent) -> Dict[str, Any]:
    start_time = time.time()
    try:
        payload = {
            "model": (agent.model_conf or {}).get("model", settings.AGENT_MODEL_NAME),
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": min((agent.model_conf or {}).get("max_tokens", 100), 100),
            "temperature": (agent.model_conf or {}).get("temperature", settings.AGENT_MODEL_TEMPERATURE),
            "top_p": (agent.model_conf or {}).get("top_p", 1.0),
            "frequency_penalty": (agent.model_conf or {}).get("frequency_penalty", 0.0),
            "presence_penalty": (agent.model_conf or {}).get("presence_penalty", 0.0),
            "customUid": "0",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(agent.api_url, headers=_headers(agent), json=payload)
            response.raise_for_status()
            data = response.json()

        content = _extract_content(data)
        usage = _extract_usage(data)
        return {
            "success": True,
            "message": get_message("agent_connection_normal"),
            "response_time": round((time.time() - start_time) * 1000, 2),
            "details": {
                "model": (agent.model_conf or {}).get("model", settings.AGENT_MODEL_NAME),
                "response_content": content[:100] + ("..." if len(content) > 100 else ""),
                "usage": usage,
            },
        }
    except Exception as exc:
        error_message = str(exc)
        if "401" in error_message or "Unauthorized" in error_message:
            friendly_message = get_message("api_key_invalid")
        elif "404" in error_message or "Not Found" in error_message:
            friendly_message = get_message("api_endpoint_not_found")
        elif "timeout" in error_message.lower():
            friendly_message = get_message("request_timeout")
        elif "connection" in error_message.lower():
            friendly_message = get_message("connection_failed")
        else:
            friendly_message = f"{get_message('connection_failed')}: {error_message}"

        return {
            "success": False,
            "message": friendly_message,
            "response_time": round((time.time() - start_time) * 1000, 2),
            "details": {
                "error_type": type(exc).__name__,
                "error_message": error_message,
                "agent_config": {
                    "api_url": agent.api_url,
                    "model": (agent.model_conf or {}).get("model", settings.AGENT_MODEL_NAME),
                },
            },
        }
