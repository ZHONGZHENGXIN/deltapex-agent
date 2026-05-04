"""add account deletion audit table

Revision ID: d20260504p15
Revises: c20260504p14
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d20260504p15"
down_revision: Union[str, None] = "c20260504p14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Zeabur deploys may start the app before Alembic is run; create_all() can
    # create this table first, so the migration must be safe to rerun.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS account_deletion_audits (
            id SERIAL NOT NULL,
            user_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            actor_type VARCHAR DEFAULT 'self' NOT NULL,
            status VARCHAR DEFAULT 'completed' NOT NULL,
            reason VARCHAR,
            scope JSON DEFAULT '{}'::json NOT NULL,
            result JSON DEFAULT '{}'::json NOT NULL,
            error_message VARCHAR,
            requested_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            completed_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_account_deletion_audits_user_id ON account_deletion_audits (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_account_deletion_audits_actor_user_id "
        "ON account_deletion_audits (actor_user_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_account_deletion_audits_status ON account_deletion_audits (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_account_deletion_audits_created_at ON account_deletion_audits (created_at)"
    )


def downgrade() -> None:
    op.drop_index("ix_account_deletion_audits_created_at", table_name="account_deletion_audits")
    op.drop_index(op.f("ix_account_deletion_audits_status"), table_name="account_deletion_audits")
    op.drop_index(op.f("ix_account_deletion_audits_actor_user_id"), table_name="account_deletion_audits")
    op.drop_index(op.f("ix_account_deletion_audits_user_id"), table_name="account_deletion_audits")
    op.drop_table("account_deletion_audits")
