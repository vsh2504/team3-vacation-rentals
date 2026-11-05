"""Core API — Prajval Sudhir
Feature: Trust, Reviews & Analytics (analytics half)
Endpoints:
  GET /host/analytics?days=30|60|90&zip=
  GET /admin/analytics?days=30|60|90&zip=
Response shape (frozen, docs/contracts.md): {period_days, by_zip:
[{zip, rentals, bookings, revenue}], total_rentals, total_bookings,
total_revenue}. Cancelled bookings are excluded; days must be exactly
30, 60, or 90. A ZIP filter is applied before aggregation so the summary
totals always equal the visible rows."""
from datetime import date
from fastapi import APIRouter, Depends, Query
from ..core.errors import ApiError, ok
from ..domain import UserRole
from ..services import AnalyticsService
from .common import get_current_user, get_store

router = APIRouter(tags=["reviews/analytics — Prajval Sudhir"])

def _period(days: int) -> int:
    if days not in (30, 60, 90):
        raise ApiError("VALIDATION_ERROR", "days must be 30, 60, or 90", "days")
    return days

@router.get("/host/analytics")
def host_analytics(days: int = Query(30), zip: str | None = None,
                   user=Depends(get_current_user), store=Depends(get_store)):
    if user.role != UserRole.HOST:
        raise ApiError("FORBIDDEN", "Host analytics are available to hosts only")
    days = _period(days)
    data = AnalyticsService(store).host_analytics(user, days, date.today(),
                                                  zip_code=zip)
    return ok(data)

@router.get("/admin/analytics")
def admin_analytics(days: int = Query(30), zip: str | None = None,
                    user=Depends(get_current_user), store=Depends(get_store)):
    if user.role != UserRole.ADMIN:
        raise ApiError("FORBIDDEN", "Admin only")
    days = _period(days)
    data = AnalyticsService(store).platform_analytics(user, days, date.today(),
                                                      zip_code=zip)
    return ok(data)
