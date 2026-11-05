"""Construction of the process-wide data store.

Pattern: Abstract Factory (``StorageBackend`` -> ``InMemoryBackend`` /
``SqlBackend``), each creating a store plus the matching flush behaviour, so
callers never branch on the storage technology. ``routers.common.STORE`` is
a Singleton built from the selected backend.

``routers.common.STORE`` is the single shared instance (module-level
Singleton). This factory decides *which* store it is: SQL-backed when
``STAYNEST_DB_URL`` configures one, otherwise the in-memory Week 1 store so
local development needs no database.
"""
from abc import ABC, abstractmethod
from typing import Callable

from .repositories import InMemoryStore


def _default_sql_factory():
    from .db import make_store
    return make_store()


class StorageBackend(ABC):
    kind: str

    @abstractmethod
    def create_store(self): ...

    @abstractmethod
    def flush(self, store) -> None: ...


class InMemoryBackend(StorageBackend):
    kind = "memory"

    def create_store(self):
        return InMemoryStore()

    def flush(self, store) -> None:
        """In-memory mutations are already the source of truth."""


class SqlBackend(StorageBackend):
    kind = "sql"

    def __init__(self, store) -> None:
        self._store = store

    def create_store(self):
        return self._store

    def flush(self, store) -> None:
        from .db import flush_store
        flush_store(store)


def select_backend(sql_factory: Callable[[], object | None] = _default_sql_factory) -> StorageBackend:
    try:
        sql_store = sql_factory()
    except Exception:
        # An unreachable/misconfigured database must not stop local development.
        sql_store = None
    return SqlBackend(sql_store) if sql_store is not None else InMemoryBackend()


def create_store(sql_factory: Callable[[], object | None] = _default_sql_factory):
    return select_backend(sql_factory).create_store()
