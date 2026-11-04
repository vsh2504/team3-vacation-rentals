"""Vinayak Gupta — Find a Stay (Search, Maps, Listing Detail) tests.
Covers US06-US13. Run: python3 backend/tests/test_listings_search.py -v
"""
import sys, unittest
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.main import app, seed_demo_data
from app.routers.common import STORE

def fresh():
    STORE.users.clear(); STORE.listings.clear(); STORE.bookings.clear(); STORE.reviews.clear()
    seed_demo_data()

class TestListingsSearch(unittest.TestCase):
    def setUp(self):
        fresh()
        self.c = TestClient(app, raise_server_exceptions=False)
    def _host_token(self, email="host@list.test"):
        self.c.post("/auth/register", json={"email": email, "password": "password123", "full_name": "Host", "role": "HOST"})
        return self.c.post("/auth/login", json={"email": email, "password": "password123"}).json()["data"]["access_token"]
    def _admin_token(self):
        return self.c.post("/auth/login", json={"email": "admin@staynest.local", "password": "admin12345"}).json()["data"]["access_token"]
    def _listing_body(self, **kw):
        b = {"title": "Test Loft", "description": "d", "address": "1 St", "city": "San Jose", "state": "CA", "zip": "95110",
             "lat": 37.33, "lng": -121.88, "price_per_night": 150, "max_guests": 4, "bedrooms": 2, "bathrooms": 1,
             "amenities": ["WiFi"], "photos": ["https://example.com/1.jpg"], "videos": ["https://example.com/1.mp4"]}
        b.update(kw); return b
    def test_search_zip_and_guests_and_pending_excluded(self):
        r = self.c.get("/listings/search?zip=95110&guests=2")
        self.assertEqual(200, r.status_code)
        ids = [l["id"] for l in r.json()["data"]]
        self.assertTrue(ids)
        self.assertTrue(all(l["zip"] == "95110" and l["max_guests"] >= 2 for l in r.json()["data"]))
        # Pending seed listings (6,12,18,24) must not appear in any search
        all_ids = [l["id"] for l in self.c.get("/listings/search").json()["data"]]
        for pid in (6, 12, 18, 24):
            self.assertNotIn(pid, all_ids)
    def test_search_city_state_and_detail_photos_videos(self):
        r = self.c.get("/listings/search?city=San%20Jose&state=CA")
        self.assertGreater(len(r.json()["data"]), 0)
        d = self.c.get("/listings/1").json()["data"]
        self.assertEqual(1, d["id"])
        self.assertIn("photos", d)
        self.assertIn("booked_today", d)
        self.assertIn("amenities", d)
    def test_host_create_starts_pending_and_customer_create_403(self):
        tok = self._host_token()
        r = self.c.post("/listings", json=self._listing_body(), headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(200, r.status_code)
        self.assertEqual("PENDING_APPROVAL", r.json()["data"]["status"])
        lid = r.json()["data"]["id"]
        # Not in search until approved
        self.assertNotIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])
        # Customer cannot create
        self.c.post("/auth/register", json={"email": "c@list.test", "password": "password123", "full_name": "C", "role": "CUSTOMER"})
        ctok = self.c.post("/auth/login", json={"email": "c@list.test", "password": "password123"}).json()["data"]["access_token"]
        r2 = self.c.post("/listings", json=self._listing_body(), headers={"Authorization": f"Bearer {ctok}"})
        self.assertEqual(403, r2.status_code)
    def test_host_edit_delete_owner_only_and_approved_appears(self):
        tok = self._host_token()
        lid = self.c.post("/listings", json=self._listing_body(), headers={"Authorization": f"Bearer {tok}"}).json()["data"]["id"]
        # Other host cannot edit
        tok2 = self._host_token("host2@list.test")
        r = self.c.put(f"/listings/{lid}", json=self._listing_body(title="Hacked"), headers={"Authorization": f"Bearer {tok2}"})
        self.assertEqual(403, r.status_code)
        # Owner edits, admin approves, appears in search
        r = self.c.put(f"/listings/{lid}", json=self._listing_body(title="Updated Loft"), headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(200, r.status_code)
        admin = self._admin_token()
        self.c.post(f"/admin/listings/{lid}/approve", headers={"Authorization": f"Bearer {admin}"})
        self.assertIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])
        # Owner deletes -> REMOVED, leaves search
        r = self.c.delete(f"/listings/{lid}", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual("REMOVED", r.json()["data"]["status"])
        self.assertNotIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])
    def test_host_listings_only_own(self):
        tok = self._host_token()
        lid = self.c.post("/listings", json=self._listing_body(), headers={"Authorization": f"Bearer {tok}"}).json()["data"]["id"]
        mine = self.c.get("/host/listings", headers={"Authorization": f"Bearer {tok}"}).json()["data"]
        self.assertIn(lid, [l["id"] for l in mine])
        tok2 = self._host_token("host3@list.test")
        others = self.c.get("/host/listings", headers={"Authorization": f"Bearer {tok2}"}).json()["data"]
        self.assertNotIn(lid, [l["id"] for l in others])

if __name__ == "__main__":
    unittest.main()
