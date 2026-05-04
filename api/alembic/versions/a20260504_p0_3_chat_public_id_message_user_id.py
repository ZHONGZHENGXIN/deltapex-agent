"""add chat public id and message user id

Revision ID: a20260504p03
Revises: 5f6f0cf4e5a1
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "a20260504p03"
down_revision: Union[str, None] = "5f6f0cf4e5a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat", sa.Column("public_id", sa.String(length=36), nullable=True))

    bind = op.get_bind()
    chat_rows = bind.execute(sa.text('SELECT id FROM "chat" WHERE public_id IS NULL')).fetchall()
    for row in chat_rows:
        bind.execute(
            sa.text('UPDATE "chat" SET public_id = :public_id WHERE id = :id'),
            {"public_id": str(uuid4()), "id": row.id},
        )

    op.alter_column("chat", "public_id", existing_type=sa.String(length=36), nullable=False)
    op.create_index(op.f("ix_chat_public_id"), "chat", ["public_id"], unique=True)

    op.add_column("message", sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            'UPDATE "message" '
            'SET user_id = "chat".user_id '
            'FROM "chat" '
            'WHERE "message".chat_id = "chat".id '
            'AND "message".user_id IS NULL'
        )
    )
    op.alter_column("message", "user_id", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_message_user_id"), "message", ["user_id"], unique=False)
    op.create_index(
        "ix_message_user_id_chat_id_created_at",
        "message",
        ["user_id", "chat_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_message_user_id_chat_id_created_at", table_name="message")
    op.drop_index(op.f("ix_message_user_id"), table_name="message")
    op.drop_column("message", "user_id")
    op.drop_index(op.f("ix_chat_public_id"), table_name="chat")
    op.drop_column("chat", "public_id")
