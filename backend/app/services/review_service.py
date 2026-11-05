"""Review submission.

Pattern: Service Layer (publishes Observer events).
"""
from datetime import date

from ..core.errors import ApiError
from ..domain import Review, User, UserRole, can_review
from ..events import EVENTS, ReviewSubmitted
from ..factories import ReviewFactory


class ReviewService:
    def __init__(self, store, events=None):
        self.store = store
        self.events = events or EVENTS

    def submit(self, customer: User, booking_id: int, rating: int, comment: str = "",
               today: date | None = None) -> Review:
        if customer.role != UserRole.CUSTOMER:
            raise ApiError("FORBIDDEN", "Only customers can review stays")
        if not (1 <= rating <= 5):
            raise ApiError("VALIDATION_ERROR", "rating must be 1-5", "rating")
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b:
            raise ApiError("NOT_FOUND", "Booking not found")
        errors = can_review(b, customer.id, self.store.reviews)
        if b.check_out > (today or date.today()):
            errors.append("Reviews are allowed only after the stay has ended")
        if errors:
            raise ApiError("VALIDATION_ERROR", "; ".join(errors))
        review = self.store.save(
            ReviewFactory.create(self.store.reviews, b, customer.id, rating, comment))
        host_id = next((l.host_id for l in self.store.listings if l.id == b.listing_id), None)
        self.events.publish(ReviewSubmitted(b.id, b.listing_id, customer.id, host_id, rating))
        return review
