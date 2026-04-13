"""add supabase user id

Revision ID: 5f6f0cf4e5a1
Revises: d936ec56f8e8
Create Date: 2026-04-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5f6f0cf4e5a1"
down_revision: Union[str, None] = "d936ec56f8e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("supabase_user_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_user_supabase_user_id"), "user", ["supabase_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_supabase_user_id"), table_name="user")
    op.drop_column("user", "supabase_user_id")
