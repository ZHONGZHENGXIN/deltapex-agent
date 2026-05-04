"""enable postgres rls for chat and message

Revision ID: b20260504p03c
Revises: a20260504p03
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b20260504p03c"
down_revision: Union[str, None] = "a20260504p03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        create or replace function public.app_current_user_id()
        returns integer
        language sql
        stable
        as $$
            select nullif(current_setting('app.current_user_id', true), '')::integer
        $$;
        """
    )
    op.execute(
        """
        create or replace function public.app_is_admin()
        returns boolean
        language sql
        stable
        as $$
            select coalesce(nullif(current_setting('app.is_admin', true), '')::boolean, false)
        $$;
        """
    )

    op.execute('alter table "chat" enable row level security')
    op.execute('alter table "chat" force row level security')
    op.execute('drop policy if exists chat_tenant_isolation on "chat"')
    op.execute(
        """
        create policy chat_tenant_isolation
        on "chat"
        for all
        using (public.app_is_admin() or user_id = public.app_current_user_id())
        with check (public.app_is_admin() or user_id = public.app_current_user_id())
        """
    )

    op.execute('alter table "message" enable row level security')
    op.execute('alter table "message" force row level security')
    op.execute('drop policy if exists message_tenant_isolation on "message"')
    op.execute(
        """
        create policy message_tenant_isolation
        on "message"
        for all
        using (public.app_is_admin() or user_id = public.app_current_user_id())
        with check (public.app_is_admin() or user_id = public.app_current_user_id())
        """
    )


def downgrade() -> None:
    op.execute('drop policy if exists message_tenant_isolation on "message"')
    op.execute('alter table "message" no force row level security')
    op.execute('alter table "message" disable row level security')

    op.execute('drop policy if exists chat_tenant_isolation on "chat"')
    op.execute('alter table "chat" no force row level security')
    op.execute('alter table "chat" disable row level security')

    op.execute("drop function if exists public.app_is_admin()")
    op.execute("drop function if exists public.app_current_user_id()")
