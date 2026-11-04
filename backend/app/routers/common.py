"""Shared router helpers — NOT a core API. Owned by no single agent;
every core API router imports get_store / get_current_user from here
so the store and auth logic are identical across routers."""
from fastapi import Depends, Header
from ..core.errors import ApiError
from ..core.security import decode_token
from ..repositories import InMemoryStore

# Sprint 3: if STAYNEST_DB_URL is set, the store is SQL-backed
# (same interface, write-through — see app/db.py). Otherwise the
# Week 1 in-memory store is used, so local dev needs no database.
try:
    from ..db import make_store as _make_sql_store
    STORE = _make_sql_store() or InMemoryStore()
except Exception:
    STORE = InMemoryStore()

def flush_store(store):
    """Persist in-place mutations (approve/cancel/etc.) to SQL, if any. No-op for in-memory."""
    try:
        from ..db import flush_store as _flush
        _flush(store)
    except Exception:
        pass

def get_store() -> InMemoryStore:
    return STORE

def get_current_user(authorization: str | None = Header(default=None), store: InMemoryStore = Depends(get_store)):
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("UNAUTHORIZED", "Missing Bearer token")
    try:
        payload = decode_token(authorization[7:])
    except Exception:
        raise ApiError("UNAUTHORIZED", "Invalid or expired token")
    user = next((u for u in store.users if u.id == payload.get("sub")), None)
    if not user:
        raise ApiError("UNAUTHORIZED", "User not found")
    return user
