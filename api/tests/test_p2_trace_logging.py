from pathlib import Path

from fastapi.testclient import TestClient

from app.core.logging import (
    key_fingerprint,
    mask_sensitive_text,
    sanitize_log_fields,
    sanitize_trace_id,
    set_trace_id,
    get_trace_id,
    reset_trace_id,
)
from app.main import app


API_ROOT = Path(__file__).resolve().parents[1]


def test_trace_id_header_is_propagated():
    client = TestClient(app)

    response = client.get("/health", headers={"X-Trace-Id": "trace-abc-123"})

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == "trace-abc-123"


def test_trace_id_is_generated_when_missing():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"]
    assert sanitize_trace_id(response.headers["X-Trace-Id"]) == response.headers["X-Trace-Id"]


def test_trace_context_can_be_set_and_reset():
    token = set_trace_id("manual-trace")
    try:
        assert get_trace_id() == "manual-trace"
    finally:
        reset_trace_id(token)


def test_sensitive_log_fields_are_masked_but_key_hash_is_kept():
    key_hash = key_fingerprint("sk-real-provider-secret")
    sanitized = sanitize_log_fields(
        {
            "email": "alice@example.test",
            "api_key": "sk-real-provider-secret",
            "authorization": "Bearer real-secret-token",
            "key_hash": key_hash,
            "input_tokens": 12,
            "error": "failed with api_key=sk-real-provider-secret for bob@example.test",
        }
    )

    assert sanitized["email"] == "a***@example.test"
    assert sanitized["api_key"] == "***"
    assert sanitized["authorization"] == "***"
    assert sanitized["key_hash"] == key_hash
    assert sanitized["input_tokens"] == 12
    assert "sk-real-provider-secret" not in sanitized["error"]
    assert "bob@example.test" not in sanitized["error"]


def test_mask_sensitive_text_removes_provider_tokens_and_emails():
    text = "Authorization: Bearer abc123 email bob@example.test key=sk-provider-secret"
    masked = mask_sensitive_text(text)

    assert "abc123" not in masked
    assert "bob@example.test" not in masked
    assert "sk-provider-secret" not in masked
    assert "b***@example.test" in masked


def test_chat_router_does_not_use_print_logging():
    chat_router = API_ROOT / "app" / "routers" / "v1" / "chat.py"

    assert "print(" not in chat_router.read_text(encoding="utf-8")
