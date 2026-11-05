"""Factory Method for domain entities.

One place decides how a new entity is built: id allocation, the initial
lifecycle status and the snapshot of data that must not change later (a
booking keeps the listing's location and price as they were at booking time).
Services ask a factory instead of assembling entities and ids themselves.
"""
from datetime import date, time
from typing import Iterable

from .core.security import hash_password
from .domain import (Booking, BookingStatus, Listing, ListingStatus, Review, User,
                     UserRole, price_for)


def next_id(existing: Iterable) -> int:
    """Highest existing id plus one (safe for persisted, non-contiguous ids)."""
    return max((item.id for item in existing), default=0) + 1


class UserFactory:
    @staticmethod
    def create(existing: Iterable[User], email: str, password: str, full_name: str,
               role: UserRole) -> User:
        existing = list(existing)
        return User(id=next_id(existing), email=email, password_hash=hash_password(password),
                    full_name=full_name, role=role)


class ListingFactory:
    @staticmethod
    def create(existing: Iterable[Listing], host_id: int, payload: dict) -> Listing:
        return Listing(id=next_id(existing), host_id=host_id,
                       status=ListingStatus.PENDING_APPROVAL, **payload)


class BookingFactory:
    @staticmethod
    def create(existing: Iterable[Booking], listing: Listing, customer_id: int,
               check_in: date, check_out: date, guests: int, today: date, *,
               check_in_time: time | None = None,
               check_out_time: time | None = None) -> Booking:
        return Booking(
            id=next_id(existing), listing_id=listing.id, customer_id=customer_id,
            check_in=check_in, check_out=check_out, guests=guests,
            check_in_time=check_in_time or listing.check_in_time,
            check_out_time=check_out_time or listing.check_out_time,
            total_price=price_for(listing, check_in, check_out), booked_date=today,
            status=BookingStatus.CONFIRMED,
            location_name=listing.title, location_address=listing.address,
            location_city=listing.city, location_state=listing.state,
            location_zip=listing.zip, location_lat=listing.lat, location_lng=listing.lng)


class ReviewFactory:
    @staticmethod
    def create(existing: Iterable[Review], booking: Booking, customer_id: int,
               rating: int, comment: str = "") -> Review:
        return Review(id=next_id(existing), booking_id=booking.id,
                      listing_id=booking.listing_id, customer_id=customer_id,
                      rating=rating, comment=comment)
