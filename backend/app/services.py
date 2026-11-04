"""Service layer — business rules live here, in exactly one place each.
Routers do Pydantic validation -> service call -> JSON. No rule in React."""
from datetime import date
from decimal import Decimal
from .core.errors import ApiError
from .domain import (Booking, BookingStatus, Listing, ListingStatus, Review,
                     User, UserRole, analytics_by_zip, booked_today, can_cancel,
                     can_review, is_available, price_for, search_listings, validate_stay)
from .core.security import check_password, hash_password, make_token

class AuthService:
    def __init__(self, store): self.store = store
    def register(self, email, password, full_name, role):
        if role not in (UserRole.CUSTOMER, UserRole.HOST):
            raise ApiError("FORBIDDEN", "Admin accounts are seeded, not self-registered")
        if self.store.by_email(email): raise ApiError("CONFLICT", "Email already registered", "email")
        user = User(id=len(self.store.users) + 1, email=email, password_hash=hash_password(password),
                    full_name=full_name, role=role)
        self.store.save(user); return user
    def login(self, email, password):
        user = self.store.by_email(email)
        if not user or not check_password(password, user.password_hash):
            raise ApiError("UNAUTHORIZED", "Invalid email or password")
        return {"access_token": make_token(user.id, user.role.value), "token_type": "bearer",
                "user": {"id": user.id, "email": user.email, "role": user.role.value}}

class ListingService:
    def __init__(self, store): self.store = store
    def create(self, host: User, data: dict) -> Listing:
        if host.role != UserRole.HOST: raise ApiError("FORBIDDEN", "Only hosts can create listings")
        li = Listing(id=len(self.store.listings) + 1, host_id=host.id, status=ListingStatus.PENDING_APPROVAL, **data)
        return self.store.save(li)
    def search(self, **kwargs): return search_listings(self.store.listings, self.store.bookings, **kwargs)
    def approve(self, admin: User, listing_id: int, approve: bool):
        if admin.role != UserRole.ADMIN: raise ApiError("FORBIDDEN", "Admin only")
        li = next((l for l in self.store.listings if l.id == listing_id), None)
        if not li: raise ApiError("NOT_FOUND", "Listing not found")
        li.status = ListingStatus.APPROVED if approve else ListingStatus.REJECTED; return li

class BookingService:
    def __init__(self, store): self.store = store
    def book(self, customer: User, listing_id: int, check_in: date, check_out: date, guests: int, today: date) -> Booking:
        li = next((l for l in self.store.listings if l.id == listing_id), None)
        if not li: raise ApiError("NOT_FOUND", "Listing not found")
        errors = validate_stay(check_in, check_out, guests, li.max_guests)
        if errors: raise ApiError("VALIDATION_ERROR", "; ".join(errors), "check_out")
        if not is_available(li, check_in, check_out, guests, self.store.bookings):
            raise ApiError("CONFLICT", "Listing is not available for the requested dates")
        b = Booking(id=len(self.store.bookings) + 1, listing_id=listing_id, customer_id=customer.id,
                    check_in=check_in, check_out=check_out, guests=guests,
                    total_price=price_for(li, check_in, check_out), booked_date=today)
        return self.store.save(b)
    def cancel(self, customer: User, booking_id: int) -> Booking:
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b: raise ApiError("NOT_FOUND", "Booking not found")
        errors = can_cancel(b, customer.id)
        if errors: raise ApiError("FORBIDDEN" if "owner" in " ".join(errors) else "VALIDATION_ERROR", "; ".join(errors))
        b.status = BookingStatus.CANCELLED; return b
    def complete(self, customer: User, booking_id: int, today: date) -> Booking:
        """Mark a CONFIRMED stay COMPLETED after check-out.
        This is what unlocks reviews (can_review requires COMPLETED).
        Demo path: book past dates, complete, then review."""
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b: raise ApiError("NOT_FOUND", "Booking not found")
        if b.customer_id != customer.id: raise ApiError("FORBIDDEN", "Only the booking owner can complete it")
        if b.status != BookingStatus.CONFIRMED: raise ApiError("VALIDATION_ERROR", "Only CONFIRMED bookings can be completed")
        if b.check_out > today: raise ApiError("VALIDATION_ERROR", "Stay has not ended yet (check_out is in the future)")
        b.status = BookingStatus.COMPLETED; return b

class ReviewService:
    def __init__(self, store): self.store = store
    def submit(self, customer: User, booking_id: int, rating: int, comment: str = "") -> Review:
        if not (1 <= rating <= 5): raise ApiError("VALIDATION_ERROR", "rating must be 1-5", "rating")
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b: raise ApiError("NOT_FOUND", "Booking not found")
        errors = can_review(b, customer.id, self.store.reviews)
        if errors: raise ApiError("VALIDATION_ERROR", "; ".join(errors))
        return self.store.save(Review(id=len(self.store.reviews) + 1, booking_id=booking_id,
                                      listing_id=b.listing_id, customer_id=customer.id, rating=rating, comment=comment))

class AnalyticsService:
    def __init__(self, store): self.store = store
    def host_analytics(self, host: User, days: int, today: date):
        return analytics_by_zip(self.store.bookings, self.store.listings, days=days, today=today, host_id=host.id)
    def platform_analytics(self, admin: User, days: int, today: date):
        if admin.role != UserRole.ADMIN: raise ApiError("FORBIDDEN", "Admin only")
        return analytics_by_zip(self.store.bookings, self.store.listings, days=days, today=today)
