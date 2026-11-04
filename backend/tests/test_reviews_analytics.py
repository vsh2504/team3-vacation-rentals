"""Prajval Sudhir — Trust, Reviews & Analytics tests. Covers US18-US20, US23.
Run: python3 backend/tests/test_reviews_analytics.py -v
"""
import sys, unittest
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
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

if __name__ == "__main__":
    unittest.main()
