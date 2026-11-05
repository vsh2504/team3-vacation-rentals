"""Shared router helpers — NOT a core API. Owned by no single agent;
every core API router imports get_store / get_current_user from here
so the store and auth logic are identical across routers.

Pattern: Singleton (STORE/BACKEND) and Protection Proxy (require_role).
"""
from fastapi import Depends, Header
from ..core.errors import ApiError
from ..core.security import decode_token
from ..repositories import InMemoryStore
from ..store import select_backend

# The one shared store (Singleton). SQL-backed when STAYNEST_DB_URL is set
# (same interface, write-through - see app/db.py), otherwise in-memory.
BACKEND = select_backend()
STORE = BACKEND.create_store()

def flush_store(store):
    """Persist in-place mutations (approve/cancel/etc.) to SQL, if any. No-op for in-memory."""
    try:
        BACKEND.flush(store)
    except Exception:
        pass

def get_store() -> InMemoryStore:
    return STORE

def get_current_user(authorization: str | None = Header(default=None), store: InMemoryStore = Depends(get_store)):
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("UNAUTHORIZED", "Missing Bearer token")
    try:
        payload = decode_token(authorization[7:])
        user_id = int(payload.get("sub"))
    except Exception:
        raise ApiError("UNAUTHORIZED", "Invalid or expired token")
    # Always resolve authorization against the persisted user record. The
    # token's role claim is informational; a stale or forged claim must never
    # grant a role that the stored account does not have.
    user = next((u for u in store.users if u.id == user_id), None)
    if not user:
        raise ApiError("UNAUTHORIZED", "User not found")
    return user


def require_role(*roles, message: str):
    """Dependency factory: the authenticated user must hold one of ``roles``."""
    def dependency(user=Depends(get_current_user)):
        if user.role not in roles:
            raise ApiError("FORBIDDEN", message)
        return user
    return dependency
