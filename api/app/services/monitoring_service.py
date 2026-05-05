from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from time import perf_counter
from typing import Optional

from sqlalchemy import desc
from sqlmodel import Session, select

from app.core.config import settings
from app.core.logging import key_fingerprint
from app.models.agent import Agent, AgentSource
from app.models.chat import Chat
from app.models.membership import UserMembership
from app.models.message import Message
from app.models.user import User
from app.schemas.admin import (
    MonitoringAlert,
    MonitoringDashboard,
    MonitoringExternalLink,
    MonitoringLlmChannelMetrics,
    MonitoringQualitySample,
    MonitoringRequestMetrics,
    MonitoringTokenAlert,
)
from app.schemas.message import MessageRole


@dataclass(frozen=True)
class RequestEvent:
    created_at: datetime
    path: str
    method: str
    status_code: int
    latency_ms: float


@dataclass(frozen=True)
class LlmEvent:
    created_at: datetime
    channel: str
    key_hash: str
    success: bool
    latency_ms: float
    total_tokens: int
    error_type: Optional[str] = None


class MonitoringMetricsCollector:
    def __init__(self, window_size: int):
        self.window_size = max(100, window_size)
        self.request_events: deque[RequestEvent] = deque(maxlen=self.window_size)
        self.llm_events: deque[LlmEvent] = deque(maxlen=self.window_size)
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
            self.request_events.clear()
            self.llm_events.clear()

    def record_request(self, *, path: str, method: str, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self.request_events.append(
                RequestEvent(
                    created_at=datetime.utcnow(),
                    path=path,
                    method=method,
                    status_code=status_code,
                    latency_ms=latency_ms,
                )
            )

    def record_llm(
        self,
        *,
        channel: str,
        key_hash: str,
        success: bool,
        latency_ms: float,
        total_tokens: int = 0,
        error_type: Optional[str] = None,
    ) -> None:
        with self._lock:
            self.llm_events.append(
                LlmEvent(
                    created_at=datetime.utcnow(),
                    channel=channel,
                    key_hash=key_hash,
                    success=success,
                    latency_ms=latency_ms,
                    total_tokens=total_tokens,
                    error_type=error_type,
                )
            )

    def snapshot_requests(self) -> MonitoringRequestMetrics:
        with self._lock:
            events = list(self.request_events)

        request_count = len(events)
        error_count = sum(1 for event in events if event.status_code >= 500)
        return MonitoringRequestMetrics(
            window_started_at=min((event.created_at for event in events), default=None),
            request_count=request_count,
            error_count=error_count,
            error_rate=_ratio(error_count, request_count),
            p99_latency_ms=_percentile([event.latency_ms for event in events], 99),
        )

    def snapshot_llm(self) -> list[MonitoringLlmChannelMetrics]:
        with self._lock:
            events = list(self.llm_events)

        grouped: dict[tuple[str, str], list[LlmEvent]] = defaultdict(list)
        for event in events:
            grouped[(event.channel, event.key_hash)].append(event)

        rows = []
        for (channel, key_hash), channel_events in sorted(grouped.items()):
            request_count = len(channel_events)
            error_count = sum(1 for event in channel_events if not event.success)
            rows.append(
                MonitoringLlmChannelMetrics(
                    channel=channel,
                    key_hash=key_hash,
                    request_count=request_count,
                    error_count=error_count,
                    failure_rate=_ratio(error_count, request_count),
                    total_tokens=sum(event.total_tokens for event in channel_events),
                    p99_latency_ms=_percentile([event.latency_ms for event in channel_events], 99),
                )
            )
        return rows


metrics_collector = MonitoringMetricsCollector(settings.MONITORING_WINDOW_SIZE)


def record_request_metric(*, path: str, method: str, status_code: int, latency_ms: float) -> None:
    metrics_collector.record_request(path=path, method=method, status_code=status_code, latency_ms=latency_ms)


def build_agent_channel(agent: Agent) -> tuple[str, str]:
    if agent.source == AgentSource.LLM and settings.LLM_GATEWAY_ENABLED:
        channel = f"one-api:{settings.LLM_GATEWAY_MODEL_NAME or settings.AGENT_MODEL_NAME}"
        key_hash = key_fingerprint(settings.LLM_GATEWAY_API_KEY or "")
        return channel, key_hash

    model = (agent.model_conf or {}).get("model", settings.AGENT_MODEL_NAME)
    channel = f"{agent.source.value}:{model}"
    return channel, key_fingerprint(agent.api_key or "")


def record_agent_call(
    agent: Agent,
    *,
    success: bool,
    latency_ms: float,
    total_tokens: int = 0,
    error_type: Optional[str] = None,
) -> None:
    channel, key_hash = build_agent_channel(agent)
    metrics_collector.record_llm(
        channel=channel,
        key_hash=key_hash,
        success=success,
        latency_ms=latency_ms,
        total_tokens=total_tokens,
        error_type=error_type,
    )


def elapsed_ms(start_time: float) -> float:
    return round((perf_counter() - start_time) * 1000, 2)


def build_monitoring_dashboard(session: Session) -> MonitoringDashboard:
    request_metrics = metrics_collector.snapshot_requests()
    llm_channels = metrics_collector.snapshot_llm()
    token_alerts = _get_token_alerts(session)
    quality_samples = _get_quality_samples(session)
    alerts = _build_alerts(request_metrics, llm_channels, token_alerts, len(quality_samples))

    return MonitoringDashboard(
        generated_at=datetime.utcnow(),
        request_metrics=request_metrics,
        llm_channels=llm_channels,
        token_alerts=token_alerts,
        quality_samples=quality_samples,
        alerts=alerts,
        external_links=_get_external_links(),
        sample_target=settings.QUALITY_SAMPLE_DAILY_LIMIT,
    )


def _get_token_alerts(session: Session) -> list[MonitoringTokenAlert]:
    threshold = settings.MONITORING_TOKEN_ALERT_DAILY_THRESHOLD
    statement = (
        select(UserMembership, User)
        .join(User, UserMembership.user_id == User.id)
        .where(
            UserMembership.is_active == True,
            UserMembership.is_deleted == False,
            User.is_deleted == False,
            UserMembership.daily_token_count >= threshold,
        )
        .order_by(desc(UserMembership.daily_token_count))
        .limit(10)
    )

    return [
        MonitoringTokenAlert(
            user_id=user.id,
            email=user.email,
            username=user.username,
            daily_token_count=membership.daily_token_count,
            daily_message_count=membership.daily_message_count,
            threshold=threshold,
        )
        for membership, user in session.exec(statement).all()
    ]


def _get_quality_samples(session: Session) -> list[MonitoringQualitySample]:
    since = datetime.utcnow() - timedelta(days=1)
    limit = max(1, settings.QUALITY_SAMPLE_DAILY_LIMIT)
    statement = (
        select(Message, Chat, User)
        .join(Chat, Message.chat_id == Chat.id)
        .join(User, Message.user_id == User.id)
        .where(
            Message.role == MessageRole.ASSISTANT,
            Message.is_deleted == False,
            Chat.is_deleted == False,
            User.is_deleted == False,
            Message.created_at >= since,
        )
        .order_by(desc(Message.created_at))
        .limit(limit)
    )

    return [
        MonitoringQualitySample(
            message_id=message.id,
            chat_id=chat.id,
            user_id=user.id,
            user_email=user.email,
            username=user.username,
            created_at=message.created_at,
            content_preview=_preview(message.content),
            token_usage=message.token_usage,
        )
        for message, chat, user in session.exec(statement).all()
    ]


def _build_alerts(
    request_metrics: MonitoringRequestMetrics,
    llm_channels: list[MonitoringLlmChannelMetrics],
    token_alerts: list[MonitoringTokenAlert],
    quality_sample_count: int,
) -> list[MonitoringAlert]:
    alerts: list[MonitoringAlert] = []
    if request_metrics.p99_latency_ms >= settings.MONITORING_P99_ALERT_MS:
        alerts.append(
            MonitoringAlert(
                type="p99_latency",
                severity="warning",
                message=f"P99 latency is {request_metrics.p99_latency_ms}ms.",
            )
        )
    if request_metrics.error_rate >= settings.MONITORING_ERROR_RATE_ALERT_THRESHOLD:
        alerts.append(
            MonitoringAlert(
                type="error_rate",
                severity="critical",
                message=f"API error rate is {request_metrics.error_rate:.2%}.",
            )
        )
    for channel in llm_channels:
        if channel.failure_rate >= settings.MONITORING_LLM_FAILURE_RATE_ALERT_THRESHOLD:
            alerts.append(
                MonitoringAlert(
                    type="llm_failure_rate",
                    severity="critical",
                    message=f"{channel.channel} failure rate is {channel.failure_rate:.2%}.",
                )
            )
    if token_alerts:
        alerts.append(
            MonitoringAlert(
                type="token_outlier",
                severity="warning",
                message=f"{len(token_alerts)} users exceeded the daily token alert threshold.",
            )
        )
    if quality_sample_count < settings.QUALITY_SAMPLE_DAILY_LIMIT:
        alerts.append(
            MonitoringAlert(
                type="quality_sample_queue",
                severity="info",
                message=(
                    f"Quality sample queue has {quality_sample_count}/"
                    f"{settings.QUALITY_SAMPLE_DAILY_LIMIT} items in the last 24h."
                ),
            )
        )
    return alerts


def _get_external_links() -> list[MonitoringExternalLink]:
    candidates = (
        ("External dashboard", settings.MONITORING_EXTERNAL_DASHBOARD_URL),
        ("one-api dashboard", settings.ONE_API_DASHBOARD_URL),
        ("claude-meter", settings.CLAUDE_METER_DASHBOARD_URL),
    )
    return [MonitoringExternalLink(label=label, url=url) for label, url in candidates if url]


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((percentile / 100) * (len(sorted_values) - 1)))
    return round(sorted_values[index], 2)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _preview(content: str, max_chars: int = 500) -> str:
    normalized = (content or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."
