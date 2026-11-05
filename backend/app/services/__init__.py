"""Service layer facade — business rules live here, in exactly one place each.

Routers do Pydantic validation -> service call -> JSON. No rule in React.
The package re-exports the public use-case classes so callers can keep
``from app.services import ListingService`` while each module owns a single
responsibility.
"""
from .analytics_service import AnalyticsService
from .auth_service import AuthService
from .booking_service import BookingService
from .listing_search import SearchOutcome
from .listing_service import ListingService
from .navigation import navigation_for, user_public
from .review_service import ReviewService

__all__ = ["AnalyticsService", "AuthService", "BookingService", "ListingService",
           "ReviewService", "SearchOutcome", "navigation_for", "user_public"]
