from datetime import datetime
from typing import Any, Optional

from sqlalchemy import delete
from sqlmodel import Session, func, select

from app.models.account_deletion import AccountDeletionAudit
from app.models.billing import TokenTopupOrder, UserTokenWallet
from app.models.chat import Chat
from app.models.memory import ChatSummary, StudentProfile
from app.models.membership import UserMembership
from app.models.message import Message
from app.models.order import Order
from app.models.user import User, UserType
from app.services.supabase_auth import set_supabase_user_ban_state


class AccountDeletionError(ValueError):
    pass


class AccountDeletionService:
    def __init__(self, db: Session):
        self.db = db

    def delete_student_account(self, user: User, *, reason: Optional[str] = None) -> AccountDeletionAudit:
        if user.user_type != UserType.USER:
            raise AccountDeletionError("Only student accounts can use self-service deletion")
        if user.is_deleted:
            raise AccountDeletionError("User account is already deleted")

        requested_at = datetime.utcnow()
        original_user_id = user.id
        if original_user_id is None:
            raise AccountDeletionError("User id is required")

        audit = AccountDeletionAudit(
            user_id=original_user_id,
            actor_user_id=original_user_id,
            actor_type="self",
            status="completed",
            reason=reason,
            requested_at=requested_at,
            scope=self._deletion_scope(),
        )

        try:
            result = self._delete_personal_data(user, requested_at=requested_at)
            audit.result = result
            audit.completed_at = datetime.utcnow()
            self.db.add(audit)
            self.db.commit()
            self.db.refresh(audit)
            return audit
        except Exception as exc:
            self.db.rollback()
            failed_audit = AccountDeletionAudit(
                user_id=original_user_id,
                actor_user_id=original_user_id,
                actor_type="self",
                status="failed",
                reason=reason,
                scope=self._deletion_scope(),
                result={},
                error_message=str(exc),
                requested_at=requested_at,
                completed_at=datetime.utcnow(),
            )
            self.db.add(failed_audit)
            self.db.commit()
            self.db.refresh(failed_audit)
            raise

    def list_deletion_audits(
        self,
        *,
        user_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AccountDeletionAudit], int]:
        filters = []
        if user_id is not None:
            filters.append(AccountDeletionAudit.user_id == user_id)

        count_query = select(func.count(AccountDeletionAudit.id))
        query = select(AccountDeletionAudit)
        if filters:
            count_query = count_query.where(*filters)
            query = query.where(*filters)

        total = self.db.exec(count_query).one() or 0
        items = list(
            self.db.exec(
                query.order_by(AccountDeletionAudit.created_at.desc()).offset(offset).limit(limit)
            ).all()
        )
        return items, total

    def _delete_personal_data(self, user: User, *, requested_at: datetime) -> dict[str, Any]:
        user_id = user.id
        assert user_id is not None

        counts = {
            "messages_deleted": self._count(Message, Message.user_id == user_id),
            "chats_deleted": self._count(Chat, Chat.user_id == user_id),
            "chat_summaries_deleted": self._count(ChatSummary, ChatSummary.user_id == user_id),
            "student_profiles_deleted": self._count(StudentProfile, StudentProfile.user_id == user_id),
            "memberships_deleted": self._count(UserMembership, UserMembership.user_id == user_id),
            "wallets_deleted": self._count(UserTokenWallet, UserTokenWallet.user_id == user_id),
            "orders_anonymized": self._count(Order, Order.user_id == user_id),
            "topup_orders_anonymized": self._count(TokenTopupOrder, TokenTopupOrder.user_id == user_id),
        }

        self.db.exec(delete(Message).where(Message.user_id == user_id))
        self.db.exec(delete(ChatSummary).where(ChatSummary.user_id == user_id))
        self.db.exec(delete(StudentProfile).where(StudentProfile.user_id == user_id))
        self.db.exec(delete(Chat).where(Chat.user_id == user_id))
        self.db.exec(delete(UserMembership).where(UserMembership.user_id == user_id))
        self.db.exec(delete(UserTokenWallet).where(UserTokenWallet.user_id == user_id))

        for order in self.db.exec(select(Order).where(Order.user_id == user_id)).all():
            order.stripe_payment_intent_id = None
            order.stripe_customer_id = None
            order.stripe_session_id = None
            order.notes = None
            order.failure_reason = None
            order.refund_reason = None
            order.updated_at = requested_at
            self.db.add(order)

        for topup_order in self.db.exec(select(TokenTopupOrder).where(TokenTopupOrder.user_id == user_id)).all():
            topup_order.creem_checkout_id = None
            topup_order.creem_order_id = None
            topup_order.creem_customer_id = None
            topup_order.failure_reason = None
            topup_order.raw_payload = None
            topup_order.updated_at = requested_at
            self.db.add(topup_order)

        provider_cleanup = self._disable_supabase_user(user)
        anonymized_email = self._anonymized_email(user_id)
        user.email = anonymized_email
        user.username = self._anonymized_username(user_id)
        user.password_hash = None
        user.last_login_at = None
        user.is_deleted = True
        user.deleted_at = requested_at
        user.updated_at = requested_at
        self.db.add(user)

        return {
            **counts,
            "user_anonymized": True,
            "anonymized_email": anonymized_email,
            "external_provider_cleanup": provider_cleanup,
        }

    def _disable_supabase_user(self, user: User) -> dict[str, Any]:
        if not user.supabase_user_id:
            return {"supabase": "not_configured_for_user"}

        try:
            set_supabase_user_ban_state(user.supabase_user_id, banned=True)
            return {"supabase": "banned"}
        except Exception as exc:
            # Local deletion remains effective because this user row is marked deleted
            # and future requests with the same Supabase subject resolve to it.
            return {"supabase": "ban_failed_local_account_disabled", "error": str(exc)}

    @staticmethod
    def _deletion_scope() -> dict[str, Any]:
        return {
            "hard_deleted": [
                "messages",
                "chats",
                "chat_summaries",
                "student_profiles",
                "user_memberships",
                "user_token_wallet",
            ],
            "anonymized": [
                "user.email",
                "user.username",
                "orders.provider_payment_fields",
                "token_topup_orders.provider_payment_fields",
            ],
            "retained": [
                "orders.financial_amount_status_timestamps",
                "token_topup_orders.financial_amount_status_timestamps",
                "account_deletion_audits",
            ],
            "external_provider": "Dify student-side stateful sessions are disabled; Supabase auth user is banned when configured.",
        }

    @staticmethod
    def _anonymized_email(user_id: int) -> str:
        return f"deleted-user-{user_id}@deleted.local"

    @staticmethod
    def _anonymized_username(user_id: int) -> str:
        return f"deleted_user_{user_id}"

    def _count(self, model: Any, *conditions: Any) -> int:
        return self.db.exec(select(func.count(model.id)).where(*conditions)).one() or 0
