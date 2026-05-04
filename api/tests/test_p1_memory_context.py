from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, create_engine

from app.agents.context import build_provider_messages
from app.core.config import settings
from app.models.memory import ChatSummary, StudentProfile
from app.schemas.message import MessageOut, MessageRole
from app.services.memory_service import MemoryService


PUBLIC_CHAT_ID = "55555555-5555-4555-8555-555555555555"
API_ROOT = Path(__file__).resolve().parents[1]


def _messages(count: int) -> list[MessageOut]:
    base_time = datetime(2026, 1, 1)
    messages = []
    for index in range(count):
        content = f"message-{index:03d}"
        if index == 0:
            content = "我的风险偏好是保守，学习节奏要慢一点。"
        messages.append(
            MessageOut(
                id=index + 1,
                chat_id=PUBLIC_CHAT_ID,
                content=content,
                model_conf=None,
                role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
                is_deleted=False,
                created_at=base_time + timedelta(seconds=index),
                updated_at=base_time + timedelta(seconds=index),
            )
        )
    return messages


def test_memory_service_builds_profile_summary_and_recent_context(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_CONTEXT_ENABLED", True)
    monkeypatch.setattr(settings, "MEMORY_SUMMARY_TRIGGER_MESSAGES", 30)
    monkeypatch.setattr(settings, "MEMORY_SUMMARY_BATCH_MESSAGES", 10)
    monkeypatch.setattr(settings, "MEMORY_SUMMARY_MAX_CHARS", 4000)
    monkeypatch.setattr(settings, "MEMORY_PROFILE_MAX_CHARS", 1500)
    monkeypatch.setattr(settings, "AGENT_CONTEXT_WINDOW_MESSAGES", 20)

    engine = create_engine("sqlite:///:memory:")
    StudentProfile.__table__.create(engine)
    ChatSummary.__table__.create(engine)

    with Session(engine) as session:
        service = MemoryService(session)
        context = service.prepare_memory_context(user_id=7, chat_id=11, messages=_messages(100))
        snapshot = service.get_student_memory_snapshot(7)
        profile = session.get(StudentProfile, 1)
        summary = session.get(ChatSummary, 1)

    assert profile is not None
    assert profile.source_message_id == 1
    assert "风险偏好是保守" in (context.profile_text or "")
    assert summary is not None
    assert summary.summarized_message_count == 80
    assert "Compressed earlier messages 1-10" in (context.summary_text or "")
    assert snapshot["profile"].id == profile.id
    assert snapshot["chat_summaries"][0].id == summary.id

    provider_messages = build_provider_messages(_messages(100), memory_context=context)
    assert provider_messages[0]["role"] == "system"
    assert "风险偏好是保守" in provider_messages[0]["content"]
    assert provider_messages[1]["role"] == "system"
    assert "Compressed earlier messages" in provider_messages[1]["content"]
    assert [message["content"] for message in provider_messages[-20:]] == [
        f"message-{index:03d}" for index in range(80, 100)
    ]


def test_memory_migration_adds_rls_for_personal_memory_tables():
    migration = API_ROOT / "alembic" / "versions" / "c20260504_p1_4_memory_tables.py"
    migration_text = migration.read_text(encoding="utf-8").lower()

    assert "student_profiles" in migration_text
    assert "chat_summaries" in migration_text
    assert "enable row level security" in migration_text
    assert "force row level security" in migration_text
    assert "app.current_user_id" in migration_text
    assert "student_profiles_tenant_isolation" in migration_text
    assert "chat_summaries_tenant_isolation" in migration_text
