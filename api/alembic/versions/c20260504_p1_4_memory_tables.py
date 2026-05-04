"""add memory profile and chat summary tables

Revision ID: c20260504p14
Revises: b20260504p03c
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

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
    # This migration may be rerun after a failed production deploy where the
    # tables were created but alembic_version was not advanced.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS student_profiles (
            id SERIAL NOT NULL,
            user_id INTEGER NOT NULL,
            risk_preference VARCHAR,
            trading_style VARCHAR,
            learning_pace VARCHAR,
            profile_summary TEXT,
            important_constraints JSON,
            source_message_id INTEGER,
            is_deleted BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_student_profiles_user_id ON student_profiles (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_profiles_user_id ON student_profiles (user_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_summaries (
            id SERIAL NOT NULL,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            summary_text TEXT DEFAULT '' NOT NULL,
            summarized_message_count INTEGER DEFAULT 0 NOT NULL,
            last_message_id INTEGER,
            last_summarized_at TIMESTAMP WITHOUT TIME ZONE,
            is_deleted BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_summaries_chat_id ON chat_summaries (chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_summaries_chat_id ON chat_summaries (chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_summaries_user_id ON chat_summaries (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_summaries_user_chat ON chat_summaries (user_id, chat_id)")

    tenant_policy = _tenant_policy_expression()
    for table_name, policy_name in (
        ("student_profiles", "student_profiles_tenant_isolation"),
        ("chat_summaries", "chat_summaries_tenant_isolation"),
    ):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
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
