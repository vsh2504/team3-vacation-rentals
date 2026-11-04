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
from ..schemas import BookingIn
from ..services import BookingService
from .common import flush_store, get_current_user, get_store

router = APIRouter(tags=["bookings — Manoj"])

def _out(b):
    return {"id": b.id, "listing_id": b.listing_id, "customer_id": b.customer_id,
            "check_in": str(b.check_in), "check_out": str(b.check_out), "guests": b.guests,
            "total_price": str(b.total_price), "status": b.status.value, "booked_date": str(b.booked_date)}

@router.post("/bookings")
def book(body: BookingIn, user=Depends(get_current_user), store=Depends(get_store)):
    b = BookingService(store).book(user, body.listing_id, body.check_in, body.check_out, body.guests, date.today())
    return ok(_out(b))

@router.get("/bookings/me")
def my_bookings(user=Depends(get_current_user), store=Depends(get_store)):
    return ok([_out(b) for b in store.by_customer(user.id)])

@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    b = BookingService(store).cancel(user, booking_id); flush_store(store); return ok(_out(b))

@router.post("/bookings/{booking_id}/complete")
def complete(booking_id: int, user=Depends(get_current_user), store=Depends(get_store)):
    b = BookingService(store).complete(user, booking_id, date.today()); flush_store(store); return ok(_out(b))
