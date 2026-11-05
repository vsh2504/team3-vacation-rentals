"""Core API — Ranadhir Reddy Rikkala
Feature: Identity, Platform & Admin Control (admin half)
Endpoints:
  GET  /admin/listings?status=PENDING_APPROVAL   (approvals queue)
  POST /admin/listings/{id}/approve
  POST /admin/listings/{id}/reject
  DELETE /admin/listings/{id}   (sets status REMOVED)
Only ADMIN may call these. Only APPROVED listings appear in search
(see listings.py) — approval is the gate between Host creation and
Customer search. The queue returns full listing, host, and completeness
evidence so a moderator can judge accuracy before acting."""
from fastapi import APIRouter, Depends
from ..core.errors import ApiError, ok
from ..domain import ListingStatus, UserRole
from ..presenters import admin_listing_out
from ..services import ListingService
from .common import flush_store, get_store, require_role

router = APIRouter(tags=["admin — Ranadhir Reddy Rikkala"])

_admin_only = require_role(UserRole.ADMIN, message="Admin only")

@router.get("/admin/listings")
def admin_listings(status: str | None = None, user=Depends(_admin_only), store=Depends(get_store)):
    out = store.listings
    if status:
        try:
            want = ListingStatus(str(status).strip().upper())
        except ValueError:
            raise ApiError("VALIDATION_ERROR", "status must be PENDING_APPROVAL, APPROVED, REJECTED or REMOVED", "status")
        out = [l for l in out if l.status == want]
    return ok([admin_listing_out(listing, store) for listing in out])

@router.post("/admin/listings/{listing_id}/approve")
def approve(listing_id: int, user=Depends(_admin_only), store=Depends(get_store)):
    listing = ListingService(store).approve(user, listing_id, True)
    flush_store(store)
    return ok({"id": listing_id, "status": listing.status.value,
               "searchable": listing.status == ListingStatus.APPROVED})

@router.post("/admin/listings/{listing_id}/reject")
def reject(listing_id: int, user=Depends(_admin_only), store=Depends(get_store)):
    listing = ListingService(store).approve(user, listing_id, False)
    flush_store(store)
    return ok({"id": listing_id, "status": listing.status.value,
               "searchable": listing.status == ListingStatus.APPROVED})

@router.delete("/admin/listings/{listing_id}")
def remove(listing_id: int, user=Depends(_admin_only), store=Depends(get_store)):
    listing = ListingService(store).remove_by_admin(user, listing_id)
    flush_store(store)
    return ok({"id": listing_id, "status": listing.status.value,
               "searchable": listing.status == ListingStatus.APPROVED})
