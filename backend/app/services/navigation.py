"""Role-based navigation returned with an authenticated session.

The frontend may render its own links, but keeping the contract here makes
the session response self-describing and the role contract testable.

Pattern: Strategy (one NavigationStrategy per role).
"""
from ..domain import User, UserRole

class NavigationStrategy:
    """Pattern: Strategy - each role supplies its own navigation policy."""

    def __init__(self, *items: dict) -> None:
        self._items = items

    def links(self) -> list[dict]:
        return [dict(item) for item in self._items]


_SEARCH = {"key": "search", "label": "Search stays", "path": "/"}
NAVIGATION_STRATEGIES: dict[UserRole, NavigationStrategy] = {
    UserRole.CUSTOMER: NavigationStrategy(
        _SEARCH, {"key": "bookings", "label": "My bookings", "path": "/bookings"}),
    UserRole.HOST: NavigationStrategy(
        _SEARCH,
        {"key": "listings", "label": "My listings", "path": "/host"},
        {"key": "bookings", "label": "My bookings", "path": "/bookings"},
        {"key": "analytics", "label": "Analytics", "path": "/analytics"}),
    UserRole.ADMIN: NavigationStrategy(
        _SEARCH,
        {"key": "moderation", "label": "Approvals queue", "path": "/admin"},
        {"key": "analytics", "label": "Platform analytics", "path": "/analytics"}),
}


def navigation_for(role: UserRole | str) -> list[dict]:
    """Return a fresh copy of the navigation items for ``role``."""
    role = role if isinstance(role, UserRole) else UserRole(role)
    return NAVIGATION_STRATEGIES[role].links()


def user_public(user: User) -> dict:
    """Serialize a persisted user for /auth responses (never a password hash)."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "navigation": navigation_for(user.role),
    }
