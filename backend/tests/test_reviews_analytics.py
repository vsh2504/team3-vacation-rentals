"""Prajval Sudhir — Trust, Reviews & Analytics tests. Covers US18-US20, US23.
Run: python3 backend/tests/test_reviews_analytics.py -v
"""
import sys, unittest
from datetime import date, timedelta
from decimal import Decimal
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.domain import BookingStatus
from app.main import app, seed_demo_data
from app.routers.common import STORE

def fresh():
    STORE.users.clear(); STORE.listings.clear(); STORE.bookings.clear(); STORE.reviews.clear()
    seed_demo_data()

class TestReviewsAnalytics(unittest.TestCase):
    def setUp(self):
        fresh()
        self.c = TestClient(app, raise_server_exceptions=False)
        self.c.post("/auth/register", json={"email": "cust@rev.test", "password": "password123", "full_name": "Cust", "role": "CUSTOMER"})
        self.tok = self.c.post("/auth/login", json={"email": "cust@rev.test", "password": "password123"}).json()["data"]["access_token"]
        self.h = {"Authorization": f"Bearer {self.tok}"}
    def _completed_booking(self, lid=1, check_in="2026-01-01", check_out="2026-01-03"):
        bid = self.c.post("/bookings", json={"listing_id": lid, "check_in": check_in, "check_out": check_out, "guests": 2}, headers=self.h).json()["data"]["id"]
        self.c.post(f"/bookings/{bid}/complete", headers=self.h)
        return bid
    def test_review_completed_only_once_and_rating_bounds(self):
        bid = self._completed_booking()
        r = self.c.post("/reviews", json={"booking_id": bid, "rating": 5, "comment": "Great"}, headers=self.h)
        self.assertEqual(200, r.status_code, r.text)
        # Second review on same booking: 422 (one per booking)
        r = self.c.post("/reviews", json={"booking_id": bid, "rating": 4, "comment": "Again"}, headers=self.h)
        self.assertEqual(422, r.status_code)
        # Rating out of bounds: Pydantic 422
        bid2 = self._completed_booking(check_in="2026-02-01", check_out="2026-02-03")
        r = self.c.post("/reviews", json={"booking_id": bid2, "rating": 6, "comment": "Too high"}, headers=self.h)
        self.assertEqual(422, r.status_code)
        # Aggregate rating updates on listing
        rev = self.c.get("/listings/1/reviews").json()["data"]
        self.assertEqual(5, rev["average_rating"])
        self.assertEqual(1, rev["count"])
    def test_review_upcoming_blocked(self):
        bid = self.c.post("/bookings", json={"listing_id": 1, "check_in": "2027-05-01", "check_out": "2027-05-03", "guests": 2}, headers=self.h).json()["data"]["id"]
        r = self.c.post("/reviews", json={"booking_id": bid, "rating": 5, "comment": "Too early"}, headers=self.h)
        self.assertEqual(422, r.status_code)

    def test_review_rejects_future_booking_even_if_status_is_completed(self):
        bid = self.c.post(
            "/bookings",
            json={"listing_id": 1, "check_in": "2027-05-01",
                  "check_out": "2027-05-03", "guests": 2},
            headers=self.h,
        ).json()["data"]["id"]
        next(item for item in STORE.bookings if item.id == bid).status = BookingStatus.COMPLETED

        response = self.c.post(
            "/reviews",
            json={"booking_id": bid, "rating": 5, "comment": "Too early"},
            headers=self.h,
        )
        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(0, len(STORE.reviews))
    def test_host_analytics_scope_and_admin_totals_and_days(self):
        # Host creates own listing, admin approves, customer books it
        self.c.post("/auth/register", json={"email": "host@rev.test", "password": "password123", "full_name": "Host", "role": "HOST"})
        htok = self.c.post("/auth/login", json={"email": "host@rev.test", "password": "password123"}).json()["data"]["access_token"]
        lid = self.c.post("/listings", json={"title": "H Loft", "description": "d", "address": "1 St", "city": "San Jose", "state": "CA", "zip": "95110", "lat": 37.33, "lng": -121.88, "price_per_night": 100, "max_guests": 4, "bedrooms": 2, "bathrooms": 1, "amenities": []}, headers={"Authorization": f"Bearer {htok}"}).json()["data"]["id"]
        atok = self.c.post("/auth/login", json={"email": "admin@staynest.local", "password": "admin12345"}).json()["data"]["access_token"]
        self.c.post(f"/admin/listings/{lid}/approve", headers={"Authorization": f"Bearer {atok}"})
        self.c.post("/bookings", json={"listing_id": lid, "check_in": "2027-05-01", "check_out": "2027-05-03", "guests": 2}, headers=self.h)
        host_data = self.c.get("/host/analytics?days=30", headers={"Authorization": f"Bearer {htok}"}).json()["data"]
        self.assertEqual(1, host_data["total_bookings"])
        self.assertEqual("95110", host_data["by_zip"][0]["zip"])
        # Other host sees nothing for this listing
        self.c.post("/auth/register", json={"email": "host2@rev.test", "password": "password123", "full_name": "Host2", "role": "HOST"})
        h2tok = self.c.post("/auth/login", json={"email": "host2@rev.test", "password": "password123"}).json()["data"]["access_token"]
        other = self.c.get("/host/analytics?days=30", headers={"Authorization": f"Bearer {h2tok}"}).json()["data"]
        self.assertEqual(0, other["total_bookings"])
        # Admin sees platform totals >= host totals, zip filter narrows
        admin_data = self.c.get("/admin/analytics?days=30&zip=95110", headers={"Authorization": f"Bearer {atok}"}).json()["data"]
        self.assertGreaterEqual(admin_data["total_bookings"], 1)
        self.assertTrue(all(r["zip"] == "95110" for r in admin_data["by_zip"]))
        # Invalid days rejected
        r = self.c.get("/admin/analytics?days=45", headers={"Authorization": f"Bearer {atok}"})
        self.assertEqual(422, r.status_code)
        # Customer cannot call admin analytics
        r = self.c.get("/admin/analytics?days=30", headers=self.h)
        self.assertEqual(403, r.status_code)

    # -- analytics scope, filtering, and period boundaries ----------------
    def _create_approved_listing(self, htok, zip_code="95110", price=100,
                                 title="Analytics Loft"):
        body = {"title": title, "description": "Analytics test listing", "address": "1 Analytics St",
                "city": "San Jose", "state": "CA", "zip": zip_code, "lat": 37.33, "lng": -121.88,
                "price_per_night": price, "max_guests": 4, "bedrooms": 2, "bathrooms": 1,
                "amenities": ["WiFi"], "photos": ["https://example.com/a.jpg"]}
        lid = self.c.post("/listings", json=body,
                          headers={"Authorization": f"Bearer {htok}"}).json()["data"]["id"]
        atok = self.c.post("/auth/login", json={"email": "admin@staynest.local",
                                                "password": "admin12345"}).json()["data"]["access_token"]
        approved = self.c.post(f"/admin/listings/{lid}/approve",
                               headers={"Authorization": f"Bearer {atok}"})
        self.assertEqual(200, approved.status_code, approved.text)
        return lid

    def _host_with_listing(self, email="analytics-host@rev.test", zip_code="95110",
                           price=100, title="Analytics Loft"):
        self.c.post("/auth/register", json={"email": email, "password": "password123",
                                            "full_name": "Analytics Host", "role": "HOST"})
        htok = self.c.post("/auth/login", json={"email": email, "password": "password123"}).json()["data"]["access_token"]
        lid = self._create_approved_listing(htok, zip_code, price, title)
        return htok, lid

    def test_analytics_zip_filter_recomputes_totals(self):
        htok, first = self._host_with_listing(zip_code="95110", price=100, title="First")
        second = self._create_approved_listing(htok, zip_code="95112", price=200, title="Second")
        h = {"Authorization": f"Bearer {htok}"}
        self.assertEqual(200, self.c.post("/bookings", json={"listing_id": first,
                            "check_in": "2027-05-01", "check_out": "2027-05-03", "guests": 2},
                            headers=self.h).status_code)
        self.assertEqual(200, self.c.post("/bookings", json={"listing_id": second,
                            "check_in": "2027-05-05", "check_out": "2027-05-07", "guests": 2},
                            headers=self.h).status_code)

        all_data = self.c.get("/host/analytics?days=30", headers=h).json()["data"]
        self.assertEqual(2, all_data["total_bookings"])
        self.assertEqual(Decimal("600"), Decimal(all_data["total_revenue"]))
        self.assertEqual(2, all_data["total_rentals"])
        self.assertEqual({"95110", "95112"}, {row["zip"] for row in all_data["by_zip"]})

        filtered = self.c.get("/host/analytics?days=30&zip=95110", headers=h).json()["data"]
        self.assertEqual(1, filtered["total_bookings"])
        self.assertEqual(Decimal("200"), Decimal(filtered["total_revenue"]))
        self.assertEqual(1, filtered["total_rentals"])
        self.assertEqual(1, len(filtered["by_zip"]))
        self.assertEqual({"zip": "95110", "rentals": 1, "bookings": 1},
                         {key: filtered["by_zip"][0][key]
                          for key in ("zip", "rentals", "bookings")})
        self.assertEqual(Decimal("200"), Decimal(filtered["by_zip"][0]["revenue"]))
        # Summary totals equal the visible rows after filtering.
        self.assertEqual(sum(r["bookings"] for r in filtered["by_zip"]),
                         filtered["total_bookings"])
        self.assertEqual(sum(Decimal(r["revenue"]) for r in filtered["by_zip"]),
                         Decimal(filtered["total_revenue"]))

        empty = self.c.get("/host/analytics?days=30&zip=00000", headers=h).json()["data"]
        self.assertEqual(0, empty["total_bookings"])
        self.assertEqual("0", empty["total_revenue"])
        self.assertEqual([], empty["by_zip"])

    def test_analytics_period_windows_and_cancelled_exclusion(self):
        htok, lid = self._host_with_listing()
        h = {"Authorization": f"Bearer {htok}"}
        booking_ids = []
        for check_in, check_out in (("2027-05-01", "2027-05-03"),
                                    ("2027-06-01", "2027-06-03"),
                                    ("2027-07-01", "2027-07-03")):
            r = self.c.post("/bookings", json={"listing_id": lid, "check_in": check_in,
                                              "check_out": check_out, "guests": 2}, headers=self.h)
            self.assertEqual(200, r.status_code, r.text)
            booking_ids.append(r.json()["data"]["id"])

        today = date.today()
        STORE_BOOKING = {b.id: b for b in STORE.bookings}
        STORE_BOOKING[booking_ids[1]].booked_date = today - timedelta(days=40)
        STORE_BOOKING[booking_ids[2]].booked_date = today - timedelta(days=80)

        self.assertEqual(1, self.c.get("/host/analytics?days=30", headers=h).json()["data"]["total_bookings"])
        sixty = self.c.get("/host/analytics?days=60", headers=h).json()["data"]
        self.assertEqual(2, sixty["total_bookings"])
        self.assertEqual(60, sixty["period_days"])
        ninety = self.c.get("/host/analytics?days=90", headers=h).json()["data"]
        self.assertEqual(3, ninety["total_bookings"])
        self.assertEqual(90, ninety["period_days"])

        cancelled = self.c.post(f"/bookings/{booking_ids[1]}/cancel", headers=self.h)
        self.assertEqual(200, cancelled.status_code, cancelled.text)
        self.assertEqual(1, self.c.get("/host/analytics?days=60", headers=h).json()["data"]["total_bookings"])

        for invalid in (45, 31, 120):
            r = self.c.get(f"/host/analytics?days={invalid}", headers=h)
            self.assertEqual(422, r.status_code, r.text)
            self.assertEqual("VALIDATION_ERROR", r.json()["error"]["code"])

    def test_analytics_requires_host_or_admin_scope(self):
        self.assertEqual(403, self.c.get("/host/analytics?days=30", headers=self.h).status_code)
        htok, _ = self._host_with_listing()
        host = {"Authorization": f"Bearer {htok}"}
        self.assertEqual(403, self.c.get("/admin/analytics?days=30", headers=host).status_code)
        self.assertEqual(200, self.c.get("/host/analytics?days=90", headers=host).status_code)
        atok = self.c.post("/auth/login", json={"email": "admin@staynest.local",
                                                "password": "admin12345"}).json()["data"]["access_token"]
        admin = {"Authorization": f"Bearer {atok}"}
        self.assertEqual(403, self.c.get("/host/analytics?days=30", headers=admin).status_code)
        self.assertEqual(200, self.c.get("/admin/analytics?days=30", headers=admin).status_code)


if __name__ == "__main__":
    unittest.main()
