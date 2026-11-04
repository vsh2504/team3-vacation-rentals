"""Core API — Prajval Sudhir
Feature: Trust, Reviews & Analytics (analytics half)
Endpoints:
  GET /host/analytics?days=30|60|90&zip=
  GET /admin/analytics?days=30|60|90&zip=
Response shape (frozen, docs/contracts.md): {period_days, by_zip:
[{zip, rentals, bookings, revenue}], total_bookings, total_revenue}.
Cancelled bookings are excluded; days must be exactly 30, 60, or 90."""
from datetime import date
from fastapi import APIRouter, Depends, Query
from ..core.errors import ApiError, ok
from ..services import AnalyticsService
from .common import get_current_user, get_store

router = APIRouter(tags=["reviews/analytics — Prajval Sudhir"])

@router.get("/host/analytics")
def host_analytics(days: int = Query(30), zip: str | None = None, user=Depends(get_current_user), store=Depends(get_store)):
    try:
        data = AnalyticsService(store).host_analytics(user, days, date.today())
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", str(e), "days")
    if zip:
        data = {**data, "by_zip": [r for r in data["by_zip"] if r["zip"] == zip]}
    return ok(data)

@router.get("/admin/analytics")
def admin_analytics(days: int = Query(30), zip: str | None = None, user=Depends(get_current_user), store=Depends(get_store)):
    try:
        data = AnalyticsService(store).platform_analytics(user, days, date.today())
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", str(e), "days")
    if zip:
        data = {**data, "by_zip": [r for r in data["by_zip"] if r["zip"] == zip]}
    return ok(data)
