from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from app.db.base import get_session
from app.dependencies.auth import get_current_user
from app.main import BASE_PREFIX, app
from app.models.account_deletion import AccountDeletionAudit
from app.models.billing import TokenTopupOrder, TokenTopupOrderStatus, UserTokenWallet
from app.models.chat import Chat
from app.models.memory import ChatSummary, StudentProfile
from app.models.membership import UserMembership
from app.models.message import Message
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.user import User, UserType
from app.schemas.message import MessageRole


API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def account_deletion_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        User.__table__,
        Chat.__table__,
        Message.__table__,
        StudentProfile.__table__,
        ChatSummary.__table__,
        UserMembership.__table__,
        UserTokenWallet.__table__,
        Order.__table__,
        TokenTopupOrder.__table__,
        AccountDeletionAudit.__table__,
    ):
        table.create(engine)

    now = datetime(2026, 1, 1)
    student_id = 1
    admin_id = 2
    student = User(
        id=student_id,
        username="alice",
        email="alice@example.test",
        supabase_user_id="supabase-alice",
        user_type=UserType.USER,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    admin = User(
        id=admin_id,
        username="admin",
        email="admin@example.test",
        supabase_user_id="supabase-admin",
        user_type=UserType.ADMIN,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    with Session(engine) as session:
        session.add_all([student, admin])
        session.add(
            Chat(
                id=10,
                public_id="11111111-1111-4111-8111-111111111111",
                user_id=student_id,
                title="Personal chat",
                content="private summary",
                agent_id=1,
                others={"conversation_id": "provider-conversation"},
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
                content="private coaching message",
                model_conf=None,
                role=MessageRole.USER,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            StudentProfile(
                id=20,
                user_id=student_id,
                profile_summary="private profile",
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ChatSummary(
                id=21,
                chat_id=10,
                user_id=student_id,
                summary_text="private summary",
                summarized_message_count=10,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserMembership(
                id=30,
                user_id=student_id,
                membership_plan_id=1,
                start_date=now,
                end_date=now + timedelta(days=30),
                is_active=True,
                daily_message_count=3,
                daily_token_count=100,
                total_message_count=20,
                total_token_count=5000,
                total_chat_count=2,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserTokenWallet(
                id=31,
                user_id=student_id,
                paid_token_balance=100,
                total_recharged_tokens=1000,
                total_consumed_paid_tokens=900,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            Order(
                id=40,
                order_number="M202601010001",
                user_id=student_id,
                membership_plan_id=1,
                status=OrderStatus.COMPLETED,
                payment_method=PaymentMethod.STRIPE,
                original_price=100,
                discount_amount=0,
                final_price=100,
                currency="USD",
                stripe_payment_intent_id="pi_private",
                stripe_customer_id="cus_private",
                stripe_session_id="cs_private",
                notes="private note",
                failure_reason="private failure",
                refund_reason="private refund",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            TokenTopupOrder(
                id=41,
                order_number="TP202601010001",
                request_id="request-private",
                user_id=student_id,
                token_package_id=1,
                status=TokenTopupOrderStatus.PAID,
                amount=50,
                currency="USD",
                token_amount=1000,
                creem_checkout_id="checkout_private",
                creem_order_id="order_private",
                creem_customer_id="customer_private",
                failure_reason="private failure",
                raw_payload={"email": "alice@example.test"},
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    current_user = {"id": student_id}
    banned_supabase_users = []

    def override_session():
        with Session(engine) as session:
            yield session

    def override_user(session: Session = Depends(get_session)):
        return session.get(User, current_user["id"])

    def fake_ban_supabase_user(supabase_user_id: str, *, banned: bool):
        banned_supabase_users.append((supabase_user_id, banned))

    monkeypatch.setattr(
        "app.services.account_deletion_service.set_supabase_user_ban_state",
        fake_ban_supabase_user,
    )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user

    try:
        yield TestClient(app), current_user, student_id, admin_id, engine, banned_supabase_users
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_student_can_delete_account_and_personal_data(account_deletion_client):
    client, current_user, student_id, admin_id, engine, banned_supabase_users = account_deletion_client

    response = client.post(
        f"{BASE_PREFIX}/user/delete-account",
        json={"confirm_text": "DELETE", "reason": "privacy request"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["deleted_user_id"] == student_id
    assert payload["anonymized_email"] == "deleted-user-1@deleted.local"
    assert payload["result"]["messages_deleted"] == 1
    assert payload["result"]["orders_anonymized"] == 1
    assert banned_supabase_users == [("supabase-alice", True)]

    with Session(engine) as session:
        deleted_user = session.get(User, student_id)
        order = session.get(Order, 40)
        topup_order = session.get(TokenTopupOrder, 41)
        audit = session.get(AccountDeletionAudit, payload["audit_id"])

        assert deleted_user.is_deleted is True
        assert deleted_user.email == "deleted-user-1@deleted.local"
        assert deleted_user.username == "deleted_user_1"
        assert deleted_user.password_hash is None
        assert deleted_user.supabase_user_id == "supabase-alice"

        assert session.exec(select(Message)).all() == []
        assert session.exec(select(Chat)).all() == []
        assert session.exec(select(StudentProfile)).all() == []
        assert session.exec(select(ChatSummary)).all() == []
        assert session.exec(select(UserMembership)).all() == []
        assert session.exec(select(UserTokenWallet)).all() == []

        assert order is not None
        assert order.user_id == student_id
        assert order.final_price == 100
        assert order.stripe_payment_intent_id is None
        assert order.stripe_customer_id is None
        assert order.stripe_session_id is None
        assert order.notes is None
        assert order.failure_reason is None
        assert order.refund_reason is None

        assert topup_order is not None
        assert topup_order.user_id == student_id
        assert topup_order.amount == 50
        assert topup_order.creem_checkout_id is None
        assert topup_order.creem_order_id is None
        assert topup_order.creem_customer_id is None
        assert topup_order.raw_payload is None
        assert topup_order.failure_reason is None

        assert audit is not None
        assert audit.status == "completed"
        assert audit.reason == "privacy request"
        assert audit.result["messages_deleted"] == 1


def test_account_deletion_requires_exact_confirmation(account_deletion_client):
    client, current_user, student_id, admin_id, engine, banned_supabase_users = account_deletion_client

    response = client.post(
        f"{BASE_PREFIX}/user/delete-account",
        json={"confirm_text": "delete"},
    )

    assert response.status_code == 400
    with Session(engine) as session:
        user = session.get(User, student_id)
        messages = session.exec(select(Message)).all()
    assert user.is_deleted is False
    assert len(messages) == 1
    assert banned_supabase_users == []


def test_admin_cannot_use_student_self_delete_endpoint(account_deletion_client):
    client, current_user, student_id, admin_id, engine, banned_supabase_users = account_deletion_client
    current_user["id"] = admin_id

    response = client.post(
        f"{BASE_PREFIX}/user/delete-account",
        json={"confirm_text": "DELETE"},
    )

    assert response.status_code == 403
    with Session(engine) as session:
        admin_user = session.get(User, admin_id)
    assert admin_user.is_deleted is False
    assert banned_supabase_users == []


def test_admin_can_query_account_deletion_audits(account_deletion_client):
    client, current_user, student_id, admin_id, engine, banned_supabase_users = account_deletion_client

    delete_response = client.post(
        f"{BASE_PREFIX}/user/delete-account",
        json={"confirm_text": "DELETE"},
    )
    assert delete_response.status_code == 200

    current_user["id"] = admin_id
    audit_response = client.get(f"{BASE_PREFIX}/admin/account-deletion-audits?user_id={student_id}")

    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["user_id"] == student_id
    assert payload["items"][0]["status"] == "completed"
    assert payload["items"][0]["result"]["chats_deleted"] == 1


def test_account_deletion_migration_is_idempotent_for_zeabur_create_all():
    migration = API_ROOT / "alembic" / "versions" / "d20260504_p1_5_account_deletion_audit.py"
    migration_text = migration.read_text(encoding="utf-8").lower()

    assert "account_deletion_audits" in migration_text
    assert "create table if not exists account_deletion_audits" in migration_text
    assert "create index if not exists ix_account_deletion_audits_user_id" in migration_text
    assert "d20260504p15" in migration_text
