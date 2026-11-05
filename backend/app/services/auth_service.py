"""Registration and login."""
import re

from ..core.errors import ApiError
from ..core.security import check_password, make_token
from ..domain import User, UserRole
from ..factories import UserFactory
from .navigation import navigation_for, user_public

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _normalize_email(email) -> str:
        return " ".join(str(email or "").split()).lower()

    def _by_email(self, email: str) -> User | None:
        # Persisted emails may predate normalization, so compare normalized
        # values instead of relying on the store's exact-match lookup.
        return next((u for u in self.store.users
                     if self._normalize_email(u.email) == email), None)

    def register(self, email, password, full_name, role):
        try:
            role = role if isinstance(role, UserRole) else UserRole(str(role).strip().upper())
        except ValueError:
            raise ApiError("FORBIDDEN", "Admin accounts are seeded, not self-registered") from None
        if role not in (UserRole.CUSTOMER, UserRole.HOST):
            raise ApiError("FORBIDDEN", "Admin accounts are seeded, not self-registered")
        email = self._normalize_email(email)
        if not _EMAIL_RE.fullmatch(email):
            raise ApiError("VALIDATION_ERROR", "email must be a valid email address", "email")
        full_name = " ".join(str(full_name or "").split())
        if not full_name:
            raise ApiError("VALIDATION_ERROR", "full_name is required", "full_name")
        if not isinstance(password, str) or len(password) < 8:
            raise ApiError("VALIDATION_ERROR", "password must be at least 8 characters", "password")
        if self._by_email(email):
            raise ApiError("CONFLICT", "Email already registered", "email")
        user = UserFactory.create(self.store.users, email, password, full_name, role)
        self.store.save(user)
        return user

    def login(self, email, password):
        user = self._by_email(self._normalize_email(email))
        if not user or not check_password(password, user.password_hash):
            raise ApiError("UNAUTHORIZED", "Invalid email or password")
        return {"access_token": make_token(user.id, user.role.value),
                "token_type": "bearer", "user": user_public(user),
                "role": user.role.value, "navigation": navigation_for(user.role)}
