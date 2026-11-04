"""Frozen Week 1 domain contracts — pure Python, no framework imports.
This is the file every slice imports and nobody redefines.
See docs/contracts.md and proposal section 13.

Rules enforced here (and only here, not duplicated in React):
- max stay 14 days, checkout > checkin, guests >= 1
- guests <= listing.max_guests
- no overlapping CONFIRMED booking for the same listing
- only APPROVED listings appear in search
- reviews only on COMPLETED bookings owned by the reviewer, one per booking
- '# booked today' = bookings for that listing with booked_date == today
  (America/Los_Angeles), regardless of stay dates
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"; HOST = "HOST"; ADMIN = "ADMIN"

class ListingStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"; APPROVED = "APPROVED"
    REJECTED = "REJECTED"; REMOVED = "REMOVED"

class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"; CANCELLED = "CANCELLED"; COMPLETED = "COMPLETED"

@dataclass
class User:
    id: int; email: str; password_hash: str; full_name: str
    role: UserRole; phone: str | None = None

@dataclass
class Listing:
    id: int; host_id: int; title: str; description: str
    address: str; city: str; state: str; zip: str
    lat: float; lng: float; price_per_night: Decimal; max_guests: int
    bedrooms: int; bathrooms: int
    amenities: list[str] = field(default_factory=list)
    available_times: str = "Check-in 3pm, check-out 11am; available year-round unless booked"
    status: ListingStatus = ListingStatus.PENDING_APPROVAL
    photos: list[str] = field(default_factory=list)  # Sprint 2: seed photos; host upload (Blob) in Sprint 3

@dataclass
class Booking:
    id: int; listing_id: int; customer_id: int
    check_in: date; check_out: date; guests: int
    total_price: Decimal; status: BookingStatus = BookingStatus.CONFIRMED
    booked_date: date | None = None; cancelled_at: str | None = None

@dataclass
class Review:
    id: int; booking_id: int; listing_id: int; customer_id: int
    rating: int; comment: str = ""

def validate_stay(check_in: date, check_out: date, guests: int, max_guests: int) -> list[str]:
    errors = []
    if check_out <= check_in: errors.append("check_out must be after check_in")
    if (check_out - check_in).days > 14: errors.append("Stay cannot exceed 14 days")
    if guests < 1: errors.append("guests must be at least 1")
    if guests > max_guests: errors.append(f"guests exceeds max_guests ({max_guests})")
    return errors

def overlaps(a_in: date, a_out: date, b_in: date, b_out: date) -> bool:
    return a_in < b_out and a_out > b_in

def is_available(listing: Listing, check_in: date, check_out: date, guests: int, existing: list[Booking]) -> bool:
    if listing.status != ListingStatus.APPROVED: return False
    if validate_stay(check_in, check_out, guests, listing.max_guests): return False
    return not any(b.status == BookingStatus.CONFIRMED and b.listing_id == listing.id
                   and overlaps(check_in, check_out, b.check_in, b.check_out) for b in existing)

def price_for(listing: Listing, check_in: date, check_out: date) -> Decimal:
    # API layer may pass a float (Pydantic); convert so Decimal * Decimal always holds.
    return Decimal(str(listing.price_per_night)) * Decimal((check_out - check_in).days)

def search_listings(listings: list[Listing], bookings: list[Booking], *,
                   check_in: date | None = None, check_out: date | None = None,
                   guests: int = 1, city: str | None = None, state: str | None = None,
                   zip_code: str | None = None) -> list[Listing]:
    out = []
    for li in listings:
        if li.status != ListingStatus.APPROVED: continue
        if city and li.city.lower() != city.lower(): continue
        if state and li.state.lower() != state.lower(): continue
        if zip_code and li.zip != zip_code: continue
        if check_in and check_out and not is_available(li, check_in, check_out, guests, bookings): continue
        out.append(li)
    return out

def can_review(booking: Booking, customer_id: int, existing_reviews: list[Review]) -> list[str]:
    errors = []
    if booking.status != BookingStatus.COMPLETED: errors.append("Reviews are allowed only on COMPLETED (past) bookings")
    if booking.customer_id != customer_id: errors.append("Reviewer does not own this booking")
    if any(r.booking_id == booking.id for r in existing_reviews): errors.append("One review per booking")
    return errors

def can_cancel(booking: Booking, customer_id: int) -> list[str]:
    errors = []
    if booking.status != BookingStatus.CONFIRMED: errors.append("Only CONFIRMED bookings can be cancelled")
    if booking.customer_id != customer_id: errors.append("Only the booking owner can cancel")
    return errors

def booked_today(listing_id: int, bookings: list[Booking], today: date) -> int:
    return sum(1 for b in bookings if b.listing_id == listing_id and b.booked_date == today)

def analytics_by_zip(bookings: list[Booking], listings: list[Listing], *,
                     days: int, today: date, host_id: int | None = None) -> dict:
    if days not in (30, 60, 90): raise ValueError("days must be 30, 60, or 90")
    start = today - timedelta(days=days)
    by_id = {li.id: li for li in listings}
    by_zip: dict[str, dict] = {}
    total_bookings, total_revenue = 0, Decimal("0")
    seen: dict[str, set] = {}
    for b in bookings:
        if b.status == BookingStatus.CANCELLED: continue
        li = by_id.get(b.listing_id)
        if li is None: continue
        if host_id is not None and li.host_id != host_id: continue
        if not (start <= (b.booked_date or today) <= today): continue
        row = by_zip.setdefault(li.zip, {"zip": li.zip, "rentals": 0, "bookings": 0, "revenue": Decimal("0")})
        row["bookings"] += 1; row["revenue"] += b.total_price; total_bookings += 1; total_revenue += b.total_price
        seen.setdefault(li.zip, set()).add(li.id)
    for row in by_zip.values():
        row["rentals"] = len(seen.get(row["zip"], set()))  # Sprint 3: distinct listings rented in period
        row["revenue"] = str(row["revenue"])
    return {"period_days": days, "by_zip": sorted(by_zip.values(), key=lambda r: r["zip"]),
            "total_bookings": total_bookings, "total_revenue": str(total_revenue)}
