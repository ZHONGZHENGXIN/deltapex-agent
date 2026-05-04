from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.agents.context import MemoryContext
from app.core.config import settings
from app.models.memory import ChatSummary, StudentProfile
from app.schemas.message import MessageOut, MessageRole


class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_student_profile(self, user_id: int) -> StudentProfile:
        profile = self.db.exec(
            select(StudentProfile).where(StudentProfile.user_id == user_id, StudentProfile.is_deleted == False)
        ).first()
        if profile:
            return profile

        profile = StudentProfile(user_id=user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_or_create_chat_summary(self, user_id: int, chat_id: int) -> ChatSummary:
        summary = self.db.exec(
            select(ChatSummary).where(
                ChatSummary.user_id == user_id,
                ChatSummary.chat_id == chat_id,
                ChatSummary.is_deleted == False,
            )
        ).first()
        if summary:
            return summary

        summary = ChatSummary(user_id=user_id, chat_id=chat_id)
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def prepare_memory_context(self, *, user_id: int, chat_id: int, messages: list[MessageOut]) -> MemoryContext:
        if not settings.MEMORY_CONTEXT_ENABLED:
            return MemoryContext()

        profile = self.get_or_create_student_profile(user_id)
        summary = self.get_or_create_chat_summary(user_id, chat_id)
        profile_changed = self._seed_profile_from_early_messages(profile, messages)
        summary_changed = self._refresh_chat_summary(summary, messages)

        if profile_changed or summary_changed:
            self.db.commit()
            self.db.refresh(profile)
            self.db.refresh(summary)

        return MemoryContext(profile_text=self._profile_text(profile), summary_text=summary.summary_text or None)

    def get_student_memory_snapshot(self, user_id: int, *, limit: int = 20) -> dict[str, Any]:
        profile = self.db.exec(
            select(StudentProfile).where(StudentProfile.user_id == user_id, StudentProfile.is_deleted == False)
        ).first()
        summaries = self.db.exec(
            select(ChatSummary)
            .where(ChatSummary.user_id == user_id, ChatSummary.is_deleted == False)
            .order_by(ChatSummary.updated_at.desc())
            .limit(limit)
        ).all()

        return {
            "profile": profile,
            "chat_summaries": summaries,
        }

    def _seed_profile_from_early_messages(self, profile: StudentProfile, messages: list[MessageOut]) -> bool:
        if profile.profile_summary or profile.risk_preference or profile.trading_style or profile.learning_pace:
            return False

        first_user_message = next((message for message in messages if message.role == MessageRole.USER), None)
        if not first_user_message:
            return False

        profile.profile_summary = self._truncate(first_user_message.content, settings.MEMORY_PROFILE_MAX_CHARS)
        profile.source_message_id = first_user_message.id
        profile.updated_at = datetime.utcnow()
        self.db.add(profile)
        return True

    def _refresh_chat_summary(self, summary: ChatSummary, messages: list[MessageOut]) -> bool:
        if len(messages) < settings.MEMORY_SUMMARY_TRIGGER_MESSAGES:
            return False

        recent_window_size = max(settings.AGENT_CONTEXT_WINDOW_MESSAGES, 0)
        batch_size = max(settings.MEMORY_SUMMARY_BATCH_MESSAGES, 1)
        max_summarizable_count = max(0, len(messages) - recent_window_size)

        if summary.summarized_message_count + batch_size > max_summarizable_count:
            return False

        summary_parts = [summary.summary_text.strip()] if summary.summary_text else []
        cursor = summary.summarized_message_count
        last_message_id = summary.last_message_id
        while cursor + batch_size <= max_summarizable_count:
            chunk = messages[cursor : cursor + batch_size]
            summary_parts.append(self._summarize_chunk(cursor, chunk))
            cursor += batch_size
            last_message_id = chunk[-1].id if chunk else last_message_id

        summary.summary_text = self._truncate_from_left(
            "\n\n".join(part for part in summary_parts if part),
            settings.MEMORY_SUMMARY_MAX_CHARS,
        )
        summary.summarized_message_count = cursor
        summary.last_message_id = last_message_id
        summary.last_summarized_at = datetime.utcnow()
        summary.updated_at = datetime.utcnow()
        self.db.add(summary)
        return True

    def _summarize_chunk(self, start_index: int, messages: list[MessageOut]) -> str:
        lines = [f"Compressed earlier messages {start_index + 1}-{start_index + len(messages)}:"]
        for message in messages:
            role = message.role.value if hasattr(message.role, "value") else str(message.role)
            lines.append(f"- {role}: {self._single_line(message.content, 180)}")
        return "\n".join(lines)

    def _profile_text(self, profile: StudentProfile) -> str | None:
        parts: list[str] = []
        if profile.profile_summary:
            parts.append(f"Known facts: {profile.profile_summary}")
        if profile.risk_preference:
            parts.append(f"Risk preference: {profile.risk_preference}")
        if profile.trading_style:
            parts.append(f"Trading style: {profile.trading_style}")
        if profile.learning_pace:
            parts.append(f"Learning pace: {profile.learning_pace}")
        if profile.important_constraints:
            parts.append(f"Important constraints: {self._format_constraints(profile.important_constraints)}")

        if not parts:
            return None
        return "\n".join(parts)

    def _format_constraints(self, constraints: dict[str, Any]) -> str:
        return "; ".join(f"{key}={value}" for key, value in constraints.items())

    def _single_line(self, text: str, max_chars: int) -> str:
        return self._truncate(" ".join(text.split()), max_chars)

    def _truncate(self, text: str, max_chars: int) -> str:
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _truncate_from_left(self, text: str, max_chars: int) -> str:
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text
        return "..." + text[-(max_chars - 3) :]
