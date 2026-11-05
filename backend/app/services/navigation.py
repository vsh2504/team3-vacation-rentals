"""Role-based navigation returned with an authenticated session.

The frontend may render its own links, but keeping the contract here makes
the session response self-describing and the role contract testable.
"""
from ..domain import User, UserRole

_ROLE_NAVIGATION: dict[UserRole, tuple[dict, ...]] = {
    UserRole.CUSTOMER: (
        {"key": "search", "label": "Search stays", "path": "/"},
        {"key": "bookings", "label": "My bookings", "path": "/bookings"},
    ),
    UserRole.HOST: (
        {"key": "search", "label": "Search stays", "path": "/"},
        {"key": "listings", "label": "My listings", "path": "/host"},
        {"key": "bookings", "label": "My bookings", "path": "/bookings"},
        {"key": "analytics", "label": "Analytics", "path": "/analytics"},
    ),
    UserRole.ADMIN: (
        {"key": "search", "label": "Search stays", "path": "/"},
        {"key": "moderation", "label": "Approvals queue", "path": "/admin"},
        {"key": "analytics", "label": "Platform analytics", "path": "/analytics"},
    ),
}


def navigation_for(role: UserRole | str) -> list[dict]:
    """Return a fresh copy of the navigation items for ``role``."""
    role = role if isinstance(role, UserRole) else UserRole(role)
    return [dict(item) for item in _ROLE_NAVIGATION[role]]


def user_public(user: User) -> dict:
    """Serialize a persisted user for /auth responses (never a password hash)."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "navigation": navigation_for(user.role),
    }
