from datetime import datetime, timedelta
from types import SimpleNamespace

from app.agents.context import build_provider_messages, recent_message_window
from app.agents.fastgpt import _build_payload
from app.core.config import settings
from app.schemas.message import MessageOut, MessageRole


PUBLIC_CHAT_ID = "44444444-4444-4444-8444-444444444444"


def _messages(count: int) -> list[MessageOut]:
    base_time = datetime(2026, 1, 1)
    return [
        MessageOut(
            id=index,
            chat_id=PUBLIC_CHAT_ID,
            content=f"message-{index:02d}",
            model_conf=None,
            role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
            is_deleted=False,
            created_at=base_time + timedelta(seconds=index),
            updated_at=base_time + timedelta(seconds=index),
        )
        for index in range(count)
    ]


def test_streaming_uses_recent_messages(monkeypatch):
    monkeypatch.setattr(settings, "AGENT_CONTEXT_WINDOW_MESSAGES", 20)

    provider_messages = build_provider_messages(_messages(50))

    assert len(provider_messages) == 20
    assert provider_messages[0]["content"] == "message-30"
    assert provider_messages[-1]["content"] == "message-49"
    assert "message-00" not in {message["content"] for message in provider_messages}


def test_recent_message_window_can_be_configured(monkeypatch):
    monkeypatch.setattr(settings, "AGENT_CONTEXT_WINDOW_MESSAGES", 8)

    window = recent_message_window(_messages(50))

    assert [message.content for message in window] == [f"message-{index:02d}" for index in range(42, 50)]


def test_fastgpt_payload_uses_recent_messages_for_stream_and_blocking(monkeypatch):
    monkeypatch.setattr(settings, "AGENT_CONTEXT_WINDOW_MESSAGES", 20)
    agent = SimpleNamespace(model_conf={"model": "fastgpt"})

    stream_payload = _build_payload(_messages(50), agent, user_id=7, stream=True)
    blocking_payload = _build_payload(_messages(50), agent, user_id=7, stream=False)

    assert [message["content"] for message in stream_payload["messages"]] == [
        f"message-{index:02d}" for index in range(30, 50)
    ]
    assert blocking_payload["messages"] == stream_payload["messages"]
    assert stream_payload["detail"] is True
