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
from datetime import time

from fastapi import APIRouter, Depends
from ..core.errors import ApiError, ok
from ..domain import ListingStatus
from ..services import ListingService
from .common import flush_store, get_current_user, get_store

router = APIRouter(tags=["admin — Ranadhir Reddy Rikkala"])

def _admin(user):
    from ..domain import UserRole
    if user.role != UserRole.ADMIN:
        raise ApiError("FORBIDDEN", "Admin only")

def _clock(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None

def _host_out(store, host_id: int) -> dict | None:
    host = next((u for u in store.users if u.id == host_id), None)
    if not host:
        return None
    return {"id": host.id, "full_name": host.full_name, "email": host.email,
            "phone": host.phone, "role": host.role.value}

def _admin_listing_out(listing, store) -> dict:
    """Moderation record: everything needed to assess completeness/accuracy."""
    completeness = ListingService.completeness(listing)
    return {
        "id": listing.id,
        "host_id": listing.host_id,
        "host": _host_out(store, listing.host_id),
        "title": listing.title,
        "description": listing.description,
        "address": listing.address,
        "city": listing.city,
        "state": listing.state,
        "zip": listing.zip,
        "lat": listing.lat,
        "lng": listing.lng,
        "price_per_night": str(listing.price_per_night),
        "max_guests": listing.max_guests,
        "bedrooms": listing.bedrooms,
        "bathrooms": listing.bathrooms,
        "amenities": listing.amenities,
        "available_times": listing.available_times,
        "host_contact_name": listing.host_contact_name,
        "host_contact_email": listing.host_contact_email,
        "host_contact_phone": listing.host_contact_phone,
        "operating_start_time": _clock(listing.operating_start_time),
        "operating_end_time": _clock(listing.operating_end_time),
        "check_in_time": _clock(listing.check_in_time),
        "check_out_time": _clock(listing.check_out_time),
        "photos": listing.photos,
        "videos": listing.videos,
        "status": listing.status.value,
        "searchable": listing.status == ListingStatus.APPROVED,
        "completeness": completeness,
        "photo_count": completeness["photo_count"],
        "video_count": completeness["video_count"],
    }

@router.get("/admin/listings")
def admin_listings(status: str | None = None, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    out = store.listings
    if status:
        try:
            want = ListingStatus(str(status).strip().upper())
        except ValueError:
            raise ApiError("VALIDATION_ERROR", "status must be PENDING_APPROVAL, APPROVED, REJECTED or REMOVED", "status")
        out = [l for l in out if l.status == want]
    return ok([_admin_listing_out(listing, store) for listing in out])

@router.post("/admin/listings/{listing_id}/approve")
def approve(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    listing = ListingService(store).approve(user, listing_id, True)
    flush_store(store)
    return ok({"id": listing_id, "status": listing.status.value,
               "searchable": listing.status == ListingStatus.APPROVED})

@router.post("/admin/listings/{listing_id}/reject")
def reject(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    listing = ListingService(store).approve(user, listing_id, False)
    flush_store(store)
    return ok({"id": listing_id, "status": listing.status.value,
               "searchable": listing.status == ListingStatus.APPROVED})

@router.delete("/admin/listings/{listing_id}")
def remove(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    _admin(user)
    listing = ListingService(store).remove_by_admin(user, listing_id)
    flush_store(store)
    return ok({"id": listing_id, "status": listing.status.value,
               "searchable": listing.status == ListingStatus.APPROVED})
