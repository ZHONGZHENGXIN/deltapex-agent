from dataclasses import dataclass

from app.core.config import settings
from app.schemas.message import MessageOut


@dataclass(frozen=True)
class MemoryContext:
    profile_text: str | None = None
    summary_text: str | None = None


def recent_message_window(messages: list[MessageOut], limit: int | None = None) -> list[MessageOut]:
    window_size = settings.AGENT_CONTEXT_WINDOW_MESSAGES if limit is None else limit
    if window_size <= 0:
        return []
    return messages[-window_size:]


def build_provider_messages(
    messages: list[MessageOut],
    limit: int | None = None,
    memory_context: MemoryContext | None = None,
) -> list[dict[str, str]]:
    provider_messages: list[dict[str, str]] = []
    if memory_context and memory_context.profile_text:
        provider_messages.append(
            {
                "role": "system",
                "content": f"Student long-term profile:\n{memory_context.profile_text}",
            }
        )
    if memory_context and memory_context.summary_text:
        provider_messages.append(
            {
                "role": "system",
                "content": f"Earlier conversation summary:\n{memory_context.summary_text}",
            }
        )

    provider_messages.extend(
        {"role": message.role, "content": message.content} for message in recent_message_window(messages, limit)
    )
    return provider_messages
