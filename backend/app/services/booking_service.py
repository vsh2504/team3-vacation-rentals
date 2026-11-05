"""Booking, cancellation and completion use-cases."""
from datetime import date, datetime, time, timezone

from ..core.errors import ApiError
from ..domain import Booking, User, UserRole, booking_state_for, can_cancel
from ..factories import BookingFactory
from .listing_service import ListingService


class BookingService:
    def __init__(self, store):
        self.store = store

    def _find(self, booking_id: int) -> Booking:
        booking = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not booking:
            raise ApiError("NOT_FOUND", "Booking not found")
        return booking

    def book(self, customer: User, listing_id: int, check_in: date, check_out: date,
             guests: int, today: date, *, check_in_time: time | None = None,
             check_out_time: time | None = None) -> Booking:
        if customer.role != UserRole.CUSTOMER:
            raise ApiError("FORBIDDEN", "Only customers can book stays")
        li = next((l for l in self.store.listings if l.id == listing_id), None)
        if not li:
            raise ApiError("NOT_FOUND", "Listing not found")
        rules = ListingService(self.store).availability(
            li, check_in=check_in, check_out=check_out,
            check_in_time=check_in_time, check_out_time=check_out_time,
            guests=guests)
        if not rules["available"]:
            code = "VALIDATION_ERROR" if rules.get("failure") == "validation" else "CONFLICT"
            raise ApiError(code, rules["reason"] or "Listing is not available",
                           "check_out" if code == "VALIDATION_ERROR" else None)
        b = BookingFactory.create(
            self.store.bookings, li, customer.id, check_in, check_out, guests, today,
            check_in_time=check_in_time, check_out_time=check_out_time)
        # SqlBackedStore.save performs one INSERT transaction. PostgreSQL's
        # confirmed-booking exclusion constraint is the final race-safe guard;
        # an IntegrityError is translated by the store into a 409 ApiError.
        return self.store.save(b)

    def cancel(self, customer: User, booking_id: int) -> Booking:
        if customer.role != UserRole.CUSTOMER:
            raise ApiError("FORBIDDEN", "Only customers can cancel stays")
        b = self._find(booking_id)
        errors = can_cancel(b, customer.id)
        if errors:
            raise ApiError("FORBIDDEN" if "owner" in " ".join(errors) else "VALIDATION_ERROR",
                           "; ".join(errors))
        booking_state_for(b.status).cancel(b, datetime.now(timezone.utc))
        return b

    def complete(self, customer: User, booking_id: int, today: date) -> Booking:
        """Mark a CONFIRMED stay COMPLETED after check-out.

        This is what unlocks reviews (``can_review`` requires COMPLETED).
        Demo path: book past dates, complete, then review.
        """
        b = self._find(booking_id)
        if b.customer_id != customer.id:
            raise ApiError("FORBIDDEN", "Only the booking owner can complete it")
        state = booking_state_for(b.status)
        if not state.allows_complete:
            raise ApiError("VALIDATION_ERROR", "Only CONFIRMED bookings can be completed")
        if b.check_out > today:
            raise ApiError("VALIDATION_ERROR", "Stay has not ended yet (check_out is in the future)")
        state.complete(b)
        return b
