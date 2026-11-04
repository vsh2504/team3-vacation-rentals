"""Shared router helpers — NOT a core API. Owned by no single agent;
every core API router imports get_store / get_current_user from here
so the store and auth logic are identical across routers."""
from fastapi import Depends, Header
from ..core.errors import ApiError
from ..core.security import decode_token
from ..repositories import InMemoryStore

# Single in-memory store for Week 1 / Sprint 1 skeleton.
# Sprint 1 swaps this for a SQLAlchemy store behind the same interface.
STORE = InMemoryStore()

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
