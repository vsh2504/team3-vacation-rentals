"""Core API — Manoj (Manoj Ganjigatte Manjunatha)
Feature: Book & Cancel a Stay
Endpoints:
  POST /bookings                    (create CONFIRMED booking)
  GET  /bookings/me                 (own bookings only)
  POST /bookings/{id}/cancel        (own CONFIRMED booking only)
  POST /bookings/{id}/complete      (Sprint 2: own CONFIRMED booking whose check_out has passed -> COMPLETED, unlocks reviews)
Rules (from domain.py, not re-implemented here): max stay 14 days,
guests <= max_guests, no overlapping CONFIRMED booking -> 409,
total_price = price_per_night * nights. Cancel frees the dates.

Pattern: Controller (MVC) over the BookingService facade.
"""
from datetime import date
from fastapi import APIRouter, Depends
from ..core.errors import ApiError, ok
from ..domain import UserRole
from ..presenters import booking_out, host_booking_out
from ..schemas import BookingIn
from ..services import BookingService
from .common import flush_store, get_current_user, get_store

router = APIRouter(tags=["bookings — Manoj"])

@router.post("/bookings")
def book(body: BookingIn, user=Depends(get_current_user), store=Depends(get_store)):
    today = date.today()
    supplied = body.model_fields_set
    b = BookingService(store).book(
        user, body.listing_id, body.check_in, body.check_out, body.guests, today,
        check_in_time=body.check_in_time if "check_in_time" in supplied else None,
        check_out_time=body.check_out_time if "check_out_time" in supplied else None)
    return ok(booking_out(b, store, today))

@router.get("/bookings/me")
def my_bookings(user=Depends(get_current_user), store=Depends(get_store)):
    today = date.today()
    return ok([booking_out(b, store, today) for b in store.by_customer(user.id)])

@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    b = BookingService(store).cancel(user, booking_id); flush_store(store); return ok(booking_out(b, store, date.today()))

@router.post("/bookings/{booking_id}/complete")
def complete(booking_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    today = date.today()
    b = BookingService(store).complete(user, booking_id, today); flush_store(store); return ok(booking_out(b, store, today))


@router.get("/host/bookings")
def host_bookings(user=Depends(get_current_user), store=Depends(get_store)):
    """Bookings on the host's own listings, with the booking customer's name and
    email and the review (if any). Never exposes other hosts' bookings."""
    if user.role != UserRole.HOST:
        raise ApiError("FORBIDDEN", "Only hosts can view bookings on their listings")
    today = date.today()
    own = {l.id: l for l in store.listings if l.host_id == user.id}
    users = {u.id: u for u in store.users}
    out = []
    for b in sorted((b for b in store.bookings if b.listing_id in own),
                    key=lambda b: (b.check_in, b.id), reverse=True):
        review = next((r for r in store.reviews if r.booking_id == b.id), None)
        row = host_booking_out(b, store, today, own[b.listing_id], users, review)
        out.append(row)
    return ok(out)
