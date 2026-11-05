"""Review submission."""
from datetime import date

from ..core.errors import ApiError
from ..domain import Review, User, UserRole, can_review
from ..factories import ReviewFactory


class ReviewService:
    def __init__(self, store):
        self.store = store

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
        return self.store.save(
            ReviewFactory.create(self.store.reviews, b, customer.id, rating, comment))
