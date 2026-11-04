"""Repository pattern (Week 1). Services depend on these Protocols, never
on SQL directly. Tests use the InMemory implementations; production swaps
in SQLAlchemy implementations with the same method names."""
from typing import Protocol
from .domain import Booking, Listing, Review, User

class UserRepository(Protocol):
    def by_email(self, email: str) -> User | None: ...
    def save(self, user: User) -> User: ...

class ListingRepository(Protocol):
    def all(self) -> list[Listing]: ...
    def by_host(self, host_id: int) -> list[Listing]: ...
    def save(self, listing: Listing) -> Listing: ...

class BookingRepository(Protocol):
    def all(self) -> list[Booking]: ...
    def by_customer(self, customer_id: int) -> list[Booking]: ...
    def save(self, booking: Booking) -> Booking: ...

class ReviewRepository(Protocol):
    def all(self) -> list[Review]: ...
    def save(self, review: Review) -> Review: ...

class InMemoryStore:
    def __init__(self):
        self.users: list[User] = []; self.listings: list[Listing] = []
        self.bookings: list[Booking] = []; self.reviews: list[Review] = []
    def by_email(self, email): return next((u for u in self.users if u.email == email), None)
    def save(self, obj):
        coll = {User: self.users, Listing: self.listings, Booking: self.bookings, Review: self.reviews}[type(obj)]
        coll.append(obj); return obj
    def all(self): return list(self.listings)
    def by_host(self, host_id): return [l for l in self.listings if l.host_id == host_id]
    def by_customer(self, customer_id): return [b for b in self.bookings if b.customer_id == customer_id]
