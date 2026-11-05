"""Demo customers, past stays and reviews for local/dev databases.

Dates are relative to today so the stays are always in the past and the
30/60/90-day analytics windows have data. Seeding happens once per database
(skipped when the first demo customer already exists) and never overwrites
anything; ids are allocated after the highest existing id.

Demo logins (password ``password123``): customer1@staynest.local,
customer2@staynest.local, customer3@staynest.local.
customer1 also has one completed stay with no review yet, to try the
review form from "My bookings".
"""
from datetime import date, timedelta
from decimal import Decimal

from .core.security import hash_password
from .domain import Booking, BookingStatus, Review, User, UserRole

DEMO_PASSWORD = "password123"
DEMO_CUSTOMERS = (
    ("customer1@staynest.local", "Alice Carter"),
    ("customer2@staynest.local", "Ben Ortiz"),
    ("customer3@staynest.local", "Chloe Nguyen"),
)

# (customer index, listing id, days since check-out, nights, rating, comment);
# rating None = completed stay that has not been reviewed yet.
STAYS = (
    (0, 1, 8, 3, 5, "Spotless loft with a great view. Check-in was effortless and the host answered within minutes."),
    (1, 1, 21, 2, 4, "Great location. A little noisy on Friday night, but we would happily stay again."),
    (2, 2, 14, 4, 5, "The garden was a lovely surprise. Quiet, comfortable beds and a very well equipped kitchen."),
    (0, 3, 35, 5, 4, "Plenty of room for the family and close to everything. Parking was tight."),
    (1, 4, 12, 2, 3, "Cozy and clean, though smaller than the photos suggest. Fine for a short stay."),
    (2, 5, 27, 3, 5, "The pool made the trip. Everything matched the listing and checkout was easy."),
    (0, 7, 50, 4, 4, "Good value and a comfortable bed. Wi-Fi was fast enough to work from."),
    (1, 8, 44, 3, 5, "Peaceful, tidy and thoughtfully stocked. One of our best stays."),
    (2, 9, 63, 6, 4, "Spacious home near the tech hub. Heating took a while to warm up."),
    (0, 2, 4, 2, None, None),
)


def seed_demo_reviews(store, today: date | None = None) -> bool:
    """Add demo customers, completed stays and reviews. Returns True if seeded."""
    today = today or date.today()
    if any(u.email == DEMO_CUSTOMERS[0][0] for u in store.users):
        return False
    approved = {l.id: l for l in store.listings if l.status.value == "APPROVED"}
    if not approved:
        return False

    next_user = max((u.id for u in store.users), default=0) + 1
    customers = []
    for offset, (email, name) in enumerate(DEMO_CUSTOMERS):
        user = User(id=max(next_user + offset, 100 + offset), email=email,
                    password_hash=hash_password(DEMO_PASSWORD), full_name=name,
                    role=UserRole.CUSTOMER, phone=f"408-555-02{offset:02d}")
        customers.append(store.save(user))

    next_booking = max((b.id for b in store.bookings), default=0) + 1
    next_review = max((r.id for r in store.reviews), default=0) + 1
    for index, (who, listing_id, ago, nights, rating, comment) in enumerate(STAYS):
        listing = approved.get(listing_id)
        if listing is None:
            continue
        check_out = today - timedelta(days=ago)
        check_in = check_out - timedelta(days=nights)
        booking = store.save(Booking(
            id=next_booking + index, listing_id=listing.id, customer_id=customers[who].id,
            check_in=check_in, check_out=check_out, guests=min(2, listing.max_guests),
            total_price=Decimal(str(listing.price_per_night)) * nights,
            status=BookingStatus.COMPLETED, booked_date=check_in - timedelta(days=14)))
        if rating is not None:
            store.save(Review(id=next_review, booking_id=booking.id, listing_id=listing.id,
                              customer_id=customers[who].id, rating=rating, comment=comment or ""))
            next_review += 1
    return True
