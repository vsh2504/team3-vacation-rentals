"""Core API — Vinayak Gupta (team lead)
Feature: Find a Stay — Search, Maps, Listing Detail + Host Listing CRUD
Endpoints:
  GET  /listings/search?check_in&check_out&guests&city&state&zip
  GET  /listings/{id}
  POST /listings                    (Host only, starts PENDING_APPROVAL)
  PUT  /listings/{id}               (own listing only)
  DELETE /listings/{id}             (own listing only -> REMOVED)
  GET  /host/listings               (own listings only)
Only APPROVED listings appear in search. Book button logic in the UI
uses is_available() — same rule as bookings.py, not a second rule."""
from datetime import date
from fastapi import APIRouter, Depends, Query
from ..core.errors import ApiError, ok
from ..domain import ListingStatus, UserRole, booked_today
from ..schemas import ListingIn
from ..services import ListingService
from .common import flush_store, get_current_user, get_store

router = APIRouter(tags=["listings/search — Vinayak Gupta"])

def _listing_out(li, store, today):
    return {"id": li.id, "host_id": li.host_id, "title": li.title, "description": li.description,
            "address": li.address, "city": li.city, "state": li.state, "zip": li.zip,
            "lat": li.lat, "lng": li.lng, "price_per_night": str(li.price_per_night),
            "max_guests": li.max_guests, "bedrooms": li.bedrooms, "bathrooms": li.bathrooms,
            "amenities": li.amenities, "available_times": li.available_times,
            "status": li.status.value, "booked_today": booked_today(li.id, store.bookings, today),
            "photos": getattr(li, "photos", []), "videos": getattr(li, "videos", [])}

@router.get("/listings/search")
def search(check_in: date | None = None, check_out: date | None = None, guests: int = 1,
           city: str | None = None, state: str | None = None, zip: str | None = None,
           store=Depends(get_store)):
    from datetime import date as _date
    today = _date.today()
    results = ListingService(store).search(check_in=check_in, check_out=check_out, guests=guests,
                                           city=city, state=state, zip_code=zip)
    return ok([_listing_out(li, store, today) for li in results])

@router.get("/listings/{listing_id}")
def get_listing(listing_id: int, store=Depends(get_store)):
    from datetime import date as _date
    li = next((l for l in store.listings if l.id == listing_id), None)
    if not li:
        raise ApiError("NOT_FOUND", "Listing not found")
    return ok(_listing_out(li, store, _date.today()))

@router.post("/listings")
def create_listing(body: ListingIn, user=Depends(get_current_user), store=Depends(get_store)):
    li = ListingService(store).create(user, body.model_dump())
    return ok({"id": li.id, "status": li.status.value})

@router.put("/listings/{listing_id}")
def update_listing(listing_id: int, body: ListingIn, user=Depends(get_current_user), store=Depends(get_store)):
    li = next((l for l in store.listings if l.id == listing_id), None)
    if not li:
        raise ApiError("NOT_FOUND", "Listing not found")
    if li.host_id != user.id:
        raise ApiError("FORBIDDEN", "Only the listing owner can edit it")
    for k, v in body.model_dump().items():
        setattr(li, k, v)
    flush_store(store)
    return ok({"id": li.id, "status": li.status.value})

@router.delete("/listings/{listing_id}")
def delete_listing(listing_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    li = next((l for l in store.listings if l.id == listing_id), None)
    if not li:
        raise ApiError("NOT_FOUND", "Listing not found")
    if li.host_id != user.id:
        raise ApiError("FORBIDDEN", "Only the listing owner can remove it")
    li.status = ListingStatus.REMOVED; flush_store(store)
    return ok({"id": li.id, "status": li.status.value})

@router.get("/host/listings")
def my_listings(user=Depends(get_current_user), store=Depends(get_store)):
    if user.role != UserRole.HOST:
        raise ApiError("FORBIDDEN", "Host only")
    from datetime import date as _date
    return ok([_listing_out(li, store, _date.today()) for li in store.by_host(user.id)])
