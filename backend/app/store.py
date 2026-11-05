"""Construction of the process-wide data store.

``routers.common.STORE`` is the single shared instance (module-level
Singleton). This factory decides *which* store it is: SQL-backed when
``STAYNEST_DB_URL`` configures one, otherwise the in-memory Week 1 store so
local development needs no database.
"""
from typing import Callable

from .repositories import InMemoryStore


def _default_sql_factory():
    from .db import make_store
    return make_store()


def create_store(sql_factory: Callable[[], object | None] = _default_sql_factory):
    try:
        return sql_factory() or InMemoryStore()
    except Exception:
        # An unreachable/misconfigured database must not stop local development.
        return InMemoryStore()
