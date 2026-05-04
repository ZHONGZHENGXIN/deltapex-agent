"""add memory profile and chat summary tables

Revision ID: c20260504p14
Revises: b20260504p03c
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c20260504p14"
down_revision: Union[str, None] = "b20260504p03c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_policy_expression() -> str:
    return """
    (
        current_setting('app.is_admin', true) = 'true'
        OR user_id = nullif(current_setting('app.current_user_id', true), '')::int
    )
    """


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("risk_preference", sa.String(), nullable=True),
        sa.Column("trading_style", sa.String(), nullable=True),
        sa.Column("learning_pace", sa.String(), nullable=True),
        sa.Column("profile_summary", sa.Text(), nullable=True),
        sa.Column("important_constraints", sa.JSON(), nullable=True),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
    )
    op.create_index(op.f("ix_student_profiles_user_id"), "student_profiles", ["user_id"], unique=False)

    op.create_table(
        "chat_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("summarized_message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_message_id", sa.Integer(), nullable=True),
        sa.Column("last_summarized_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="uq_chat_summaries_chat_id"),
    )
    op.create_index(op.f("ix_chat_summaries_chat_id"), "chat_summaries", ["chat_id"], unique=False)
    op.create_index(op.f("ix_chat_summaries_user_id"), "chat_summaries", ["user_id"], unique=False)
    op.create_index("ix_chat_summaries_user_chat", "chat_summaries", ["user_id", "chat_id"], unique=False)

    tenant_policy = _tenant_policy_expression()
    for table_name, policy_name in (
        ("student_profiles", "student_profiles_tenant_isolation"),
        ("chat_summaries", "chat_summaries_tenant_isolation"),
    ):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {policy_name}
            ON {table_name}
            USING ({tenant_policy})
            WITH CHECK ({tenant_policy})
            """
        )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS chat_summaries_tenant_isolation ON chat_summaries")
    op.execute("DROP POLICY IF EXISTS student_profiles_tenant_isolation ON student_profiles")
    op.drop_index("ix_chat_summaries_user_chat", table_name="chat_summaries")
    op.drop_index(op.f("ix_chat_summaries_user_id"), table_name="chat_summaries")
    op.drop_index(op.f("ix_chat_summaries_chat_id"), table_name="chat_summaries")
    op.drop_table("chat_summaries")
    op.drop_index(op.f("ix_student_profiles_user_id"), table_name="student_profiles")
    op.drop_table("student_profiles")
