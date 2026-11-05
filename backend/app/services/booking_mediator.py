"""Pattern: Mediator.

Placing a booking involves four collaborators - the availability rules, the
price quote, the persistence store and the event bus. ``BookingMediator``
is the only object that knows how they interact, so none of them refer to
each other and ``BookingService`` stays a thin use-case entry point.
"""
from datetime import date, time

from ..core.errors import ApiError
from ..domain import Booking, Listing
from ..events import BookingConfirmed
from ..factories import BookingFactory


class BookingMediator:
    def __init__(self, store, availability, events, quote) -> None:
        self._store = store
        self._availability = availability
        self._events = events
        self._quote = quote

    def place(self, listing: Listing, customer_id: int, check_in: date, check_out: date,
              guests: int, today: date, check_in_time: time | None,
              check_out_time: time | None) -> Booking:
        rules = self._availability(
            listing, check_in=check_in, check_out=check_out,
            check_in_time=check_in_time, check_out_time=check_out_time, guests=guests)
        if not rules["available"]:
            code = "VALIDATION_ERROR" if rules.get("failure") == "validation" else "CONFLICT"
            raise ApiError(code, rules["reason"] or "Listing is not available",
                           "check_out" if code == "VALIDATION_ERROR" else None)
        booking = BookingFactory.create(
            self._store.bookings, listing, customer_id, check_in, check_out, guests, today,
            check_in_time=check_in_time, check_out_time=check_out_time, quote=self._quote)
        # SqlBackedStore.save performs one INSERT transaction. PostgreSQL's
        # confirmed-booking exclusion constraint is the final race-safe guard;
        # an IntegrityError is translated by the store into a 409 ApiError.
        saved = self._store.save(booking)
        self._events.publish(BookingConfirmed(saved.id, saved.listing_id, customer_id,
                                              listing.host_id))
        return saved
