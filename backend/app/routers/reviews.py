"""Core API — Prajval Sudhir
Feature: Trust, Reviews & Analytics (reviews half)
Endpoints:
  POST /reviews                     (COMPLETED past booking only, one per booking)
  GET  /listings/{id}/reviews       (public, with aggregate rating)
  GET  /host/analytics?days=30|60|90&zip=
  GET  /admin/analytics?days=30|60|90&zip=
Analytics endpoints are in analytics.py — same owner, same core API.
Host analytics scope = caller's listings only; admin scope = all hosts."""
from datetime import date
from fastapi import APIRouter, Depends
from ..core.errors import ok
from ..schemas import ReviewIn
from ..services import ReviewService
from .common import get_current_user, get_store

router = APIRouter(tags=["reviews/analytics — Prajval Sudhir"])

@router.post("/reviews")
def submit(body: ReviewIn, user=Depends(get_current_user), store=Depends(get_store)):
    r = ReviewService(store).submit(
        user, body.booking_id, body.rating, body.comment, today=date.today())
    return ok({"id": r.id, "booking_id": r.booking_id, "listing_id": r.listing_id,
               "customer_id": r.customer_id, "rating": r.rating, "comment": r.comment})

@router.get("/listings/{listing_id}/reviews")
def listing_reviews(listing_id: int, store=Depends(get_store)):
    rs = [r for r in store.reviews if r.listing_id == listing_id]
    avg = round(sum(r.rating for r in rs) / len(rs), 2) if rs else None
    return ok({"listing_id": listing_id, "average_rating": avg, "count": len(rs),
               "reviews": [{"id": r.id, "rating": r.rating, "comment": r.comment, "customer_id": r.customer_id} for r in rs]})
