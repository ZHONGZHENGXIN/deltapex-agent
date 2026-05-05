from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.core.config import settings
from app.db.base import get_session
from app.dependencies.auth import verify_admin_user
from app.main import BASE_PREFIX, app
from app.models.chat import Chat
from app.models.membership import UserMembership
from app.models.message import Message
from app.models.user import User, UserType
from app.schemas.message import MessageRole
from app.services.monitoring_service import MonitoringMetricsCollector, metrics_collector


def test_monitoring_collector_tracks_p99_error_and_llm_failure():
    collector = MonitoringMetricsCollector(window_size=100)

    collector.record_request(path="/ok", method="GET", status_code=200, latency_ms=10)
    collector.record_request(path="/slow", method="GET", status_code=200, latency_ms=20)
    collector.record_request(path="/boom", method="GET", status_code=500, latency_ms=1000)
    collector.record_llm(
        channel="fastgpt:coach",
        key_hash="key_abc123",
        success=True,
        latency_ms=100,
        total_tokens=11,
    )
    collector.record_llm(
        channel="fastgpt:coach",
        key_hash="key_abc123",
        success=False,
        latency_ms=900,
        error_type="TimeoutError",
    )

    request_metrics = collector.snapshot_requests()
    llm_metrics = collector.snapshot_llm()

    assert request_metrics.request_count == 3
    assert request_metrics.error_count == 1
    assert request_metrics.error_rate == 0.3333
    assert request_metrics.p99_latency_ms == 1000
    assert len(llm_metrics) == 1
    assert llm_metrics[0].failure_rate == 0.5
    assert llm_metrics[0].total_tokens == 11


def test_admin_monitoring_dashboard_returns_token_alerts_and_samples(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        User.__table__,
        UserMembership.__table__,
        Chat.__table__,
        Message.__table__,
    ):
        table.create(engine)

    monkeypatch.setattr(settings, "MONITORING_TOKEN_ALERT_DAILY_THRESHOLD", 100)
    monkeypatch.setattr(settings, "QUALITY_SAMPLE_DAILY_LIMIT", 50)
    monkeypatch.setattr(settings, "MONITORING_ERROR_RATE_ALERT_THRESHOLD", 0.4)
    monkeypatch.setattr(settings, "MONITORING_LLM_FAILURE_RATE_ALERT_THRESHOLD", 0.4)

    metrics_collector.reset()
    metrics_collector.record_request(path="/ok", method="GET", status_code=200, latency_ms=80)
    metrics_collector.record_request(path="/boom", method="GET", status_code=500, latency_ms=500)
    metrics_collector.record_llm(
        channel="fastgpt:coach",
        key_hash="key_def456",
        success=False,
        latency_ms=700,
        error_type="ProviderError",
    )

    now = datetime.utcnow()
    admin_id = 1
    student_id = 2
    admin_user = User(
        id=admin_id,
        username="admin",
        email="admin@example.test",
        user_type=UserType.ADMIN,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    student = User(
        id=student_id,
        username="student",
        email="student@example.test",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    with Session(engine) as session:
        session.add_all([admin_user, student])
        session.add(
            UserMembership(
                id=1,
                user_id=student_id,
                membership_plan_id=1,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=30),
                is_active=True,
                daily_message_count=8,
                daily_token_count=150,
                total_message_count=8,
                total_token_count=150,
                total_chat_count=1,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Chat(
                id=10,
                public_id="77777777-7777-4777-8777-777777777777",
                user_id=student_id,
                title="Sampling chat",
                agent_id=1,
                others={},
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Message(
                id=100,
                chat_id=10,
                user_id=student_id,
                content="Assistant response selected for manual quality review.",
                model_conf={},
                role=MessageRole.ASSISTANT,
                token_usage={"total_tokens": 12},
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    def override_admin_user():
        return admin_user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[verify_admin_user] = override_admin_user

    try:
        response = TestClient(app).get(f"{BASE_PREFIX}/admin/monitoring")
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(verify_admin_user, None)
        metrics_collector.reset()

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_metrics"]["request_count"] == 2
    assert payload["request_metrics"]["error_rate"] == 0.5
    assert payload["llm_channels"][0]["failure_rate"] == 1.0
    assert payload["token_alerts"][0]["user_id"] == student_id
    assert payload["token_alerts"][0]["daily_token_count"] == 150
    assert payload["quality_samples"][0]["message_id"] == 100
    assert "manual quality review" in payload["quality_samples"][0]["content_preview"]
    assert payload["sample_target"] == 50
    assert {alert["type"] for alert in payload["alerts"]} >= {
        "error_rate",
        "llm_failure_rate",
        "token_outlier",
        "quality_sample_queue",
    }
