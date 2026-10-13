import os
import ssl
from typing import Any, Callable, TypeVar

import pg8000.dbapi

T = TypeVar("T")

# Amazon RDS CA bundle (https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem).
# RDS server certificates aren't signed by a public CA, so verify against this.
_CA_BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rds-global-bundle.pem")

# One connection per warm Lambda container. Reopened on demand if the previous
# one was closed (e.g. RDS restart, idle timeout) — see reset_connection().
_connection: Any = None


def get_connection() -> Any:
    global _connection
    if _connection is None:
        _connection = pg8000.dbapi.connect(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "5432")),
            database=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            ssl_context=ssl.create_default_context(cafile=_CA_BUNDLE),
            timeout=10,
        )
    return _connection


def reset_connection() -> None:
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
    _connection = None


def run_with_reconnect(operation: Callable[[Any], T]) -> T:
    """Run `operation(connection)`, retrying once on a fresh connection if the
    cached one turned out to be dead (warm container outlived the DB session)."""
    try:
        return operation(get_connection())
    except (pg8000.dbapi.InterfaceError, pg8000.dbapi.OperationalError):
        reset_connection()
        return operation(get_connection())
