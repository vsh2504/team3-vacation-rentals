"""Host and platform analytics (access control + domain aggregation).

Pattern: Service Layer.
"""
from datetime import date

from ..core.errors import ApiError
from ..domain import User, UserRole, analytics_by_zip


class AnalyticsService:
    def __init__(self, store):
        self.store = store

    def host_analytics(self, host: User, days: int, today: date, zip_code: str | None = None):
        if host.role != UserRole.HOST:
            raise ApiError("FORBIDDEN", "Host analytics are available to hosts only")
        return analytics_by_zip(self.store.bookings, self.store.listings, days=days,
                                today=today, host_id=host.id, zip_code=zip_code)

    def platform_analytics(self, admin: User, days: int, today: date, zip_code: str | None = None):
        if admin.role != UserRole.ADMIN:
            raise ApiError("FORBIDDEN", "Admin only")
        return analytics_by_zip(self.store.bookings, self.store.listings, days=days,
                                today=today, zip_code=zip_code)
