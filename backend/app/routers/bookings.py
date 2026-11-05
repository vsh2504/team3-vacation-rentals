"""Core API — Manoj (Manoj Ganjigatte Manjunatha)
Feature: Book & Cancel a Stay
Endpoints:
  POST /bookings                    (create CONFIRMED booking)
  GET  /bookings/me                 (own bookings only)
  POST /bookings/{id}/cancel        (own CONFIRMED booking only)
  POST /bookings/{id}/complete      (Sprint 2: own CONFIRMED booking whose check_out has passed -> COMPLETED, unlocks reviews)
Rules (from domain.py, not re-implemented here): max stay 14 days,
guests <= max_guests, no overlapping CONFIRMED booking -> 409,
total_price = price_per_night * nights. Cancel frees the dates."""
from datetime import date
from fastapi import APIRouter, Depends
from ..core.errors import ok
from ..domain import BookingStatus
from ..geocoding import osm_embed_url, osm_url
from ..schemas import BookingIn
from ..services import BookingService
from .common import flush_store, get_current_user, get_store

router = APIRouter(tags=["bookings — Manoj"])

def _out(b, store, today: date):
    listing = next((item for item in store.listings if item.id == b.listing_id), None)
    if b.status == BookingStatus.CANCELLED:
        stay_state = "cancelled"
    elif b.check_out <= today:
        stay_state = "past"
    else:
        stay_state = "upcoming"
    map_url = (osm_url(b.location_lat, b.location_lng)
               if b.location_lat is not None and b.location_lng is not None else None)
    embed_url = (osm_embed_url(b.location_lat, b.location_lng)
                 if b.location_lat is not None and b.location_lng is not None else None)
    return {"id": b.id, "listing_id": b.listing_id, "customer_id": b.customer_id,
            "check_in": str(b.check_in), "check_out": str(b.check_out), "guests": b.guests,
            "check_in_time": b.check_in_time.strftime("%H:%M"),
            "check_out_time": b.check_out_time.strftime("%H:%M"),
            "total_price": str(b.total_price), "status": b.status.value,
            "stay_state": stay_state, "booked_date": str(b.booked_date),
            "cancelled_at": b.cancelled_at.isoformat() if b.cancelled_at else None,
            "location": {"name": b.location_name, "address": b.location_address,
                         "city": b.location_city, "state": b.location_state,
                         "zip": b.location_zip, "lat": b.location_lat,
                         "lng": b.location_lng, "map_url": map_url,
                         "osm_embed_url": embed_url},
            "map_url": map_url,
            "listing": {"id": b.listing_id,
                        "title": b.location_name or (listing.title if listing else ""),
                        "price_per_night": str(listing.price_per_night) if listing else None,
                        "max_guests": listing.max_guests if listing else None,
                        "photos": listing.photos if listing else [],
                        "url": f"/listings/{b.listing_id}"}}

@router.post("/bookings")
def book(body: BookingIn, user=Depends(get_current_user), store=Depends(get_store)):
    today = date.today()
    supplied = body.model_fields_set
    b = BookingService(store).book(
        user, body.listing_id, body.check_in, body.check_out, body.guests, today,
        check_in_time=body.check_in_time if "check_in_time" in supplied else None,
        check_out_time=body.check_out_time if "check_out_time" in supplied else None)
    return ok(_out(b, store, today))

@router.get("/bookings/me")
def my_bookings(user=Depends(get_current_user), store=Depends(get_store)):
    today = date.today()
    return ok([_out(b, store, today) for b in store.by_customer(user.id)])

@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    b = BookingService(store).cancel(user, booking_id); flush_store(store); return ok(_out(b, store, date.today()))

@router.post("/bookings/{booking_id}/complete")
def complete(booking_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    today = date.today()
    b = BookingService(store).complete(user, booking_id, today); flush_store(store); return ok(_out(b, store, today))
