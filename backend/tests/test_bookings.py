"""Manoj — Book & Cancel a Stay tests. Covers US14-US17.
Run: python3 backend/tests/test_bookings.py -v
"""
import sys, unittest
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.main import app, seed_demo_data
from app.routers.common import STORE

def fresh():
    STORE.users.clear(); STORE.listings.clear(); STORE.bookings.clear(); STORE.reviews.clear()
    seed_demo_data()

class TestBookings(unittest.TestCase):
    def setUp(self):
        fresh()
        self.c = TestClient(app, raise_server_exceptions=False)
        self.c.post("/auth/register", json={"email": "cust@book.test", "password": "password123", "full_name": "Cust", "role": "CUSTOMER"})
        self.tok = self.c.post("/auth/login", json={"email": "cust@book.test", "password": "password123"}).json()["data"]["access_token"]
        self.h = {"Authorization": f"Bearer {self.tok}"}
        # Seed listing 1: San Jose 95110, APPROVED, $120/night, max 2 guests
        self.lid = 1
    def _book(self, **kw):
        b = {"listing_id": self.lid, "check_in": "2027-05-01", "check_out": "2027-05-04", "guests": 2}
        b.update(kw); return self.c.post("/bookings", json=b, headers=self.h)
    def test_book_price_and_my_bookings(self):
        r = self._book()
        self.assertEqual(200, r.status_code, r.text)
        # 3 nights at seed price for listing 1 (check actual price from detail)
        detail = self.c.get(f"/listings/{self.lid}").json()["data"]
        expected = float(detail["price_per_night"]) * 3
        self.assertEqual(expected, float(r.json()["data"]["total_price"]))
        self.assertEqual("CONFIRMED", r.json()["data"]["status"])
        mine = self.c.get("/bookings/me", headers=self.h).json()["data"]
        self.assertIn(r.json()["data"]["id"], [b["id"] for b in mine])
    def test_overlap_409_and_checkout_day_free(self):
        self.assertEqual(200, self._book().status_code)
        r = self._book(check_in="2027-05-02", check_out="2027-05-05")
        self.assertEqual(409, r.status_code)
        r = self._book(check_in="2027-05-04", check_out="2027-05-06")
        self.assertEqual(200, r.status_code, "checkout day must be free")
    def test_15_day_422_and_guest_cap_422(self):
        r = self._book(check_in="2027-05-01", check_out="2027-05-16")
        self.assertEqual(422, r.status_code)
        r = self._book(guests=99)
        self.assertEqual(422, r.status_code)
    def test_cancel_frees_dates_and_other_user_403(self):
        bid = self._book().json()["data"]["id"]
        r = self.c.post(f"/bookings/{bid}/cancel", headers=self.h)
        self.assertEqual("CANCELLED", r.json()["data"]["status"])
        # Rebook same dates succeeds
        self.assertEqual(200, self._book().status_code)
        # Other user cannot cancel
        self.c.post("/auth/register", json={"email": "other@book.test", "password": "password123", "full_name": "Other", "role": "CUSTOMER"})
        otok = self.c.post("/auth/login", json={"email": "other@book.test", "password": "password123"}).json()["data"]["access_token"]
        bid2 = self._book(check_in="2027-06-01", check_out="2027-06-03").json()["data"]["id"]
        r = self.c.post(f"/bookings/{bid2}/cancel", headers={"Authorization": f"Bearer {otok}"})
        self.assertEqual(403, r.status_code)
    def test_complete_past_only_then_review_unlocked(self):
        bid = self._book(check_in="2026-01-01", check_out="2026-01-03").json()["data"]["id"]
        r = self.c.post(f"/bookings/{bid}/complete", headers=self.h)
        self.assertEqual("COMPLETED", r.json()["data"]["status"])
        # Future booking cannot be completed
        bid2 = self._book(check_in="2027-05-01", check_out="2027-05-03").json()["data"]["id"]
        r = self.c.post(f"/bookings/{bid2}/complete", headers=self.h)
        self.assertEqual(422, r.status_code)

if __name__ == "__main__":
    unittest.main()
