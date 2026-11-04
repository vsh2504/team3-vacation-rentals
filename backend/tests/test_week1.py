"""Week 1 acceptance tests — stdlib only, run: python3 -m unittest backend/tests/test_week1.py -v
Covers the frozen rules in domain.py. A failing test here blocks the PR, not the demo."""
import sys, unittest
from datetime import date
from decimal import Decimal
sys.path.insert(0, "backend")
from app.domain import (Booking, BookingStatus, Listing, ListingStatus, Review, User, UserRole,
                        analytics_by_zip, booked_today, can_cancel, can_review, is_available,
                        price_for, search_listings, validate_stay)
from app.repositories import InMemoryStore
from app.services import AuthService, BookingService, ListingService, ReviewService

def listing(**kw):
    d = dict(id=1, host_id=1, title="Loft", description="d", address="1 Demo St", city="San Jose",
             state="CA", zip="95110", lat=37.33, lng=-121.88, price_per_night=Decimal("150"),
             max_guests=4, bedrooms=2, bathrooms=1, status=ListingStatus.APPROVED)
    d.update(kw); return Listing(**d)

class TestStayRules(unittest.TestCase):
    def test_14_day_rule(self):
        self.assertIn("Stay cannot exceed 14 days", validate_stay(date(2027,5,1), date(2027,5,16), 2, 4))
        self.assertEqual([], validate_stay(date(2027,5,1), date(2027,5,15), 2, 4))  # exactly 14 nights: allowed
    def test_guest_cap(self):
        self.assertTrue(validate_stay(date(2027,5,1), date(2027,5,3), 5, 4))
    def test_overlap_blocks(self):
        li = listing()
        existing = [Booking(id=1, listing_id=1, customer_id=2, check_in=date(2027,5,10), check_out=date(2027,5,13),
                            guests=2, total_price=Decimal("450"))]
        self.assertFalse(is_available(li, date(2027,5,12), date(2027,5,14), 2, existing))
        self.assertTrue(is_available(li, date(2027,5,13), date(2027,5,15), 2, existing))  # checkout day is free
    def test_pending_not_in_search(self):
        out = search_listings([listing(status=ListingStatus.PENDING_APPROVAL), listing(id=2)], [], guests=2)
        self.assertEqual([2], [l.id for l in out])
    def test_zip_and_guest_filter(self):
        out = search_listings([listing(id=1, zip="95110", max_guests=2), listing(id=2, zip="95112", max_guests=6)], [], guests=4, zip_code="95112")
        self.assertEqual([2], [l.id for l in out])
    def test_price(self):
        self.assertEqual(Decimal("450"), price_for(listing(), date(2027,5,1), date(2027,5,4)))
    def test_review_only_past_and_owned_and_once(self):
        past = Booking(id=9, listing_id=1, customer_id=7, check_in=date(2026,1,1), check_out=date(2026,1,3),
                       guests=2, total_price=Decimal("300"), status=BookingStatus.COMPLETED)
        self.assertEqual([], can_review(past, 7, []))
        self.assertTrue(can_review(past, 8, []))  # not owner
        self.assertTrue(can_review(past, 7, [Review(id=1, booking_id=9, listing_id=1, customer_id=7, rating=5)]))
        upcoming = Booking(id=10, listing_id=1, customer_id=7, check_in=date(2027,5,1), check_out=date(2027,5,3),
                           guests=2, total_price=Decimal("300"), status=BookingStatus.CONFIRMED)
        self.assertTrue(can_review(upcoming, 7, []))
    def test_cancel_only_confirmed_owned(self):
        b = Booking(id=3, listing_id=1, customer_id=7, check_in=date(2027,5,1), check_out=date(2027,5,3),
                    guests=2, total_price=Decimal("300"))
        self.assertEqual([], can_cancel(b, 7))
        self.assertTrue(can_cancel(b, 8))
    def test_booked_today(self):
        bs = [Booking(id=1, listing_id=1, customer_id=2, check_in=date(2027,5,1), check_out=date(2027,5,3), guests=2, total_price=Decimal("300"), booked_date=date(2027,5,1)),
              Booking(id=2, listing_id=1, customer_id=3, check_in=date(2027,6,1), check_out=date(2027,6,3), guests=2, total_price=Decimal("300"), booked_date=date(2027,5,2))]
        self.assertEqual(1, booked_today(1, bs, date(2027,5,1)))
    def test_analytics_30_60_90_and_host_scope(self):
        lis = [listing(id=1, host_id=1, zip="95110"), listing(id=2, host_id=2, zip="95112")]
        bs = [Booking(id=1, listing_id=1, customer_id=9, check_in=date(2027,5,1), check_out=date(2027,5,2), guests=2, total_price=Decimal("150"), booked_date=date(2027,4,20)),
              Booking(id=2, listing_id=2, customer_id=9, check_in=date(2027,5,1), check_out=date(2027,5,2), guests=2, total_price=Decimal("200"), booked_date=date(2027,4,20)),
              Booking(id=3, listing_id=1, customer_id=9, check_in=date(2027,5,1), check_out=date(2027,5,2), guests=2, total_price=Decimal("150"), booked_date=date(2027,4,20), status=BookingStatus.CANCELLED)]
        r = analytics_by_zip(bs, lis, days=30, today=date(2027,5,1), host_id=1)
        self.assertEqual(1, r["total_bookings"])  # cancelled excluded, other host excluded
        with self.assertRaises(ValueError):
            analytics_by_zip(bs, lis, days=45, today=date(2027,5,1))
    def test_services_end_to_end(self):
        store = InMemoryStore()
        auth = AuthService(store); cust = auth.register("c@example.com", "password123", "Cust", UserRole.CUSTOMER)
        host = auth.register("h@example.com", "password123", "Host", UserRole.HOST)
        ls = ListingService(store); li = ls.create(host, dict(title="T", description="d", address="1 St", city="San Jose", state="CA", zip="95110", lat=37.3, lng=-121.8, price_per_night=Decimal("100"), max_guests=4, bedrooms=2, bathrooms=1))
        self.assertEqual(ListingStatus.PENDING_APPROVAL, li.status)
        ls.approve(User(id=99, email="a@example.com", password_hash="x", full_name="Admin", role=UserRole.ADMIN), li.id, True)
        bs = BookingService(store)
        b = bs.book(cust, li.id, date(2027,5,1), date(2027,5,3), 2, date(2027,4,20))
        self.assertEqual(Decimal("200"), b.total_price)
        with self.assertRaises(Exception):
            bs.book(cust, li.id, date(2027,5,2), date(2027,5,4), 2, date(2027,4,20))

if __name__ == "__main__":
    unittest.main()
