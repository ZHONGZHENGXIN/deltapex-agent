from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlmodel import Session


RLS_USER_ID_KEY = "rls_user_id"
RLS_IS_ADMIN_KEY = "rls_is_admin"


def _apply_rls_context(session: Session, connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    user_id = session.info.get(RLS_USER_ID_KEY)
    if user_id is None:
        return

    is_admin = bool(session.info.get(RLS_IS_ADMIN_KEY, False))
    connection.exec_driver_sql("select set_config('app.current_user_id', %s, true)", (str(user_id),))
    connection.exec_driver_sql("select set_config('app.is_admin', %s, true)", ("true" if is_admin else "false",))


@event.listens_for(Session, "after_begin")
def _set_rls_context_after_begin(session: Session, transaction, connection: Connection) -> None:
    _apply_rls_context(session, connection)


def set_rls_context(session: Session, *, user_id: int, is_admin: bool = False) -> None:
    session.info[RLS_USER_ID_KEY] = int(user_id)
    session.info[RLS_IS_ADMIN_KEY] = bool(is_admin)

    if session.in_transaction():
        _apply_rls_context(session, session.connection())
