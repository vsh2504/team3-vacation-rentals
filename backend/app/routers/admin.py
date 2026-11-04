"""Core API — Ranadhir Reddy Rikkala
Feature: Identity, Platform & Admin Control (admin half)
Endpoints:
  POST /admin/listings/{id}/approve
  POST /admin/listings/{id}/reject
  DELETE /admin/listings/{id}   (sets status REMOVED)
Only ADMIN may call these. Only APPROVED listings appear in search
(see listings.py) — approval is the gate between Host creation and
Customer search."""
from fastapi import APIRouter, Depends
from ..core.errors import ApiError, ok
from ..domain import ListingStatus
from ..services import ListingService
from .common import get_current_user, get_store

router = APIRouter(tags=["admin — Ranadhir Reddy Rikkala"])

def _admin(user):
    from ..domain import UserRole
    if user.role != UserRole.ADMIN:
        raise ApiError("FORBIDDEN", "Admin only")

@router.post("/admin/listings/{listing_id}/approve")
def approve(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    return ok({"id": listing_id, "status": ListingService(store).approve(user, listing_id, True).status.value})

@router.post("/admin/listings/{listing_id}/reject")
def reject(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    return ok({"id": listing_id, "status": ListingService(store).approve(user, listing_id, False).status.value})

@router.delete("/admin/listings/{listing_id}")
def remove(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    li = next((l for l in store.listings if l.id == listing_id), None)
    if not li:
        raise ApiError("NOT_FOUND", "Listing not found")
    li.status = ListingStatus.REMOVED
    return ok({"id": listing_id, "status": li.status.value})
