"""Vinayak Gupta — Find a Stay (Search, Maps, Listing Detail) tests.
Covers US06-US13 plus the completed search/geocoding/availability/CRUD APIs.
Run: python3 backend/tests/test_listings_search.py -v
"""
import os
import sys, unittest
from unittest.mock import patch

sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.main import app, seed_demo_data
from app.routers.common import STORE
from app.geocoding import (GeocodeResult, GeocodingUnavailable, clear_cache,
                           get_provider, normalize_address, normalize_state_code)


def fresh():
    STORE.users.clear(); STORE.listings.clear(); STORE.bookings.clear(); STORE.reviews.clear()
    seed_demo_data()


FAKE_GEOCODE = GeocodeResult(
    query="1 Test Street, San Jose, CA",
    display_name="1 Test Street, San Jose, CA 95110, United States",
    address="1 Test Street", city="San Jose", state="CA", zip="95110",
    country="United States", lat=37.3382, lng=-121.8863, provider="nominatim",
)


class TestListingsSearch(unittest.TestCase):
    def setUp(self):
        fresh()
        clear_cache()
        self.c = TestClient(app, raise_server_exceptions=False)
    def _host_token(self, email="host@list.test"):
        self.c.post("/auth/register", json={"email": email, "password": "password123", "full_name": "Host", "role": "HOST"})
        return self.c.post("/auth/login", json={"email": email, "password": "password123"}).json()["data"]["access_token"]
    def _customer_token(self, email="cust@list.test"):
        self.c.post("/auth/register", json={"email": email, "password": "password123", "full_name": "Customer", "role": "CUSTOMER"})
        return self.c.post("/auth/login", json={"email": email, "password": "password123"}).json()["data"]["access_token"]
    def _admin_token(self):
        return self.c.post("/auth/login", json={"email": "admin@staynest.local", "password": "admin12345"}).json()["data"]["access_token"]
    def _listing_body(self, **kw):
        b = {"title": "Test Loft", "description": "d", "address": "1 St", "city": "San Jose", "state": "CA", "zip": "95110",
             "lat": 37.33, "lng": -121.88, "price_per_night": 150, "max_guests": 4, "bedrooms": 2, "bathrooms": 1,
             "amenities": ["WiFi"], "photos": ["https://example.com/1.jpg"], "videos": ["https://example.com/1.mp4"]}
        b.update(kw); return b
    def _create(self, body=None, token=None):
        token = token or self._host_token()
        r = self.c.post("/listings", json=body or self._listing_body(),
                        headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, r.status_code, r.text)
        return r.json()["data"], token
    def _approve(self, listing_id):
        r = self.c.post(f"/admin/listings/{listing_id}/approve",
                        headers={"Authorization": f"Bearer {self._admin_token()}"})
        self.assertEqual(200, r.status_code, r.text)
    def _book(self, token, listing_id, check_in, check_out, guests=2):
        return self.c.post("/bookings", json={"listing_id": listing_id, "check_in": check_in,
                                             "check_out": check_out, "guests": guests},
                           headers={"Authorization": f"Bearer {token}"})

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

    # -- completed search / availability contract -------------------------
    def test_search_derives_duration_and_total_cost(self):
        r = self.c.get("/listings/search?check_in=2027-05-01&nights=2&guests=2")
        self.assertEqual(200, r.status_code, r.text)
        results = r.json()["data"]
        self.assertTrue(results)
        # ``duration`` is accepted as an alias for ``nights``.
        alias = self.c.get("/listings/search?check_in=2027-05-01&duration=2&guests=2")
        self.assertEqual(200, alias.status_code, alias.text)
        self.assertTrue(all(item["nights"] == 2 for item in alias.json()["data"]))

        for item in results:
            self.assertEqual(2, item["nights"])
            self.assertEqual(2, item["duration_nights"])
            self.assertAlmostEqual(float(item["price_per_night"]) * 2, float(item["total_cost"]))
            self.assertTrue(item["available"])
            self.assertTrue(item["availability"]["requested"])
            # Every result records its own OpenStreetMap location.
            self.assertIn("openstreetmap.org", item["map_url"])
            self.assertIn(f"/listings/{item['id']}", item["listing_url"])

    def test_search_rejects_zero_negative_and_over_14_nights(self):
        cases = [
            "/listings/search?check_in=2027-05-01&check_out=2027-05-01&guests=1",
            "/listings/search?check_in=2027-05-03&check_out=2027-05-01&guests=1",
            "/listings/search?check_in=2027-05-01&check_out=2027-05-16&guests=1",
            "/listings/search?check_in=2027-05-01&nights=0&guests=1",
            "/listings/search?check_in=2027-05-01&nights=15&guests=1",
            "/listings/search?check_in=2027-05-01&guests=1",
            "/listings/search?check_in=2027-05-01&check_out=2027-05-03&nights=5&guests=1",
        ]
        for url in cases:
            r = self.c.get(url)
            self.assertEqual(422, r.status_code, url)
            self.assertFalse(r.json()["success"], url)
            self.assertEqual("VALIDATION_ERROR", r.json()["error"]["code"], url)
        over = self.c.get("/listings/search?check_in=2027-05-01&check_out=2027-05-16&guests=1")
        self.assertIn("14", over.json()["error"]["message"])
        # Exactly 14 nights is allowed.
        self.assertEqual(200, self.c.get(
            "/listings/search?check_in=2027-05-01&check_out=2027-05-15&guests=1").status_code)

    def test_search_operating_hours_constrain_results(self):
        body = self._listing_body(operating_start_time="09:00", operating_end_time="17:00",
                                  check_in_time="15:00", check_out_time="11:00")
        created, _ = self._create(body)
        self._approve(created["id"])
        base = "check_in=2027-05-01&check_out=2027-05-03&guests=2"
        inside = self.c.get(f"/listings/search?{base}&check_in_time=15:00&check_out_time=11:00")
        outside = self.c.get(f"/listings/search?{base}&check_in_time=18:00&check_out_time=11:00")
        self.assertEqual(200, inside.status_code, inside.text)
        self.assertEqual(200, outside.status_code, outside.text)
        ids_inside = [l["id"] for l in inside.json()["data"]]
        ids_outside = [l["id"] for l in outside.json()["data"]]
        self.assertIn(created["id"], ids_inside)
        self.assertNotIn(created["id"], ids_outside)

    def test_search_excludes_and_marks_unavailable_when_booked(self):
        customer = self._customer_token()
        self.assertEqual(200, self._book(customer, 1, "2027-05-01", "2027-05-03").status_code)
        url = "/listings/search?check_in=2027-05-02&check_out=2027-05-04&guests=2"
        ids = [l["id"] for l in self.c.get(url).json()["data"]]
        self.assertNotIn(1, ids)
        marked = self.c.get(url + "&include_unavailable=true")
        self.assertEqual(200, marked.status_code, marked.text)
        row = next(l for l in marked.json()["data"] if l["id"] == 1)
        self.assertFalse(row["available"])
        self.assertIn("booked", row["availability"]["reason"].lower())
        self.assertIsNotNone(row["total_cost"])

    def test_detail_and_detail_availability_include_reviews_totals_and_map(self):
        customer = self._customer_token()
        self.assertEqual(200, self._book(customer, 1, "2026-01-01", "2026-01-03").status_code)
        bid = self.c.get("/bookings/me", headers={"Authorization": f"Bearer {customer}"}).json()["data"][0]["id"]
        self.assertEqual(200, self.c.post(f"/bookings/{bid}/complete",
                                          headers={"Authorization": f"Bearer {customer}"}).status_code)
        self.assertEqual(200, self.c.post("/reviews", json={"booking_id": bid, "rating": 5, "comment": "Great"},
                                          headers={"Authorization": f"Bearer {customer}"}).status_code)

        detail = self.c.get("/listings/1?check_in=2027-05-01&check_out=2027-05-04&guests=2").json()["data"]
        self.assertEqual(5.0, detail["average_rating"])
        self.assertEqual(1, detail["review_count"])
        self.assertEqual("Great", detail["reviews"][0]["comment"])
        self.assertEqual(3, detail["nights"])
        self.assertAlmostEqual(float(detail["price_per_night"]) * 3, float(detail["total_cost"]))
        self.assertTrue(detail["availability"]["available"])
        self.assertEqual(1, detail["booked_today"])
        self.assertIn("openstreetmap.org", detail["map_url"])
        self.assertIn("openstreetmap.org", detail["osm_embed_url"])

        availability = self.c.get(
            "/listings/1/availability?check_in=2027-05-01&check_out=2027-05-04&guests=2").json()["data"]
        self.assertTrue(availability["available"])
        self.assertEqual(3, availability["nights"])
        self.assertEqual("360", availability["total_cost"])

    def test_detail_marks_booked_period_unavailable(self):
        customer = self._customer_token()
        self.assertEqual(200, self._book(customer, 1, "2027-05-01", "2027-05-03").status_code)
        detail = self.c.get("/listings/1?check_in=2027-05-02&check_out=2027-05-04&guests=2").json()["data"]
        self.assertFalse(detail["available"])
        self.assertFalse(detail["availability"]["available"])
        self.assertIn("booked", detail["availability"]["reason"].lower())
        self.assertEqual("240", detail["total_cost"])
        # Missing dates return a requested=false availability object.
        plain = self.c.get("/listings/1").json()["data"]
        self.assertFalse(plain["availability"]["requested"])
        self.assertTrue(plain["available"])

    # -- geocoding provider boundary --------------------------------------
    def test_geocode_endpoint_caches_and_never_leaks_provider_secret(self):
        clear_cache()
        class FakeProvider:
            name = "nominatim"
            calls = 0
            def geocode(self, address):
                FakeProvider.calls += 1
                return FAKE_GEOCODE
        with patch("app.geocoding.get_provider", return_value=FakeProvider()):
            first = self.c.get("/geocode?address=1%20Test%20Street%2C%20San%20Jose%2C%20CA")
            second = self.c.get("/geocode?address=1%20Test%20Street%2C%20San%20Jose%2C%20CA")
        self.assertEqual(200, first.status_code, first.text)
        self.assertEqual(200, second.status_code, second.text)
        self.assertEqual(1, FakeProvider.calls, "normalized address result must be cached")
        data = first.json()["data"]
        self.assertEqual("nominatim", data["provider"])
        self.assertEqual("San Jose", data["city"])
        self.assertEqual("CA", data["state"])
        self.assertIn("openstreetmap.org", data["map_url"])
        self.assertNotIn("key", {k.lower() for k in data})
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "super-secret-key",
                                     "STAYNEST_GEOCODING_PROVIDER": "google"}, clear=False):
            self.assertEqual("google", get_provider().name)
            self.assertNotIn("super-secret-key", str(get_provider()))

    def test_geocode_rejects_unknown_and_reports_provider_failure(self):
        with patch("app.geocoding.get_provider", side_effect=GeocodingUnavailable("down")):
            r = self.c.get("/geocode?address=nowhere")
        self.assertEqual(500, r.status_code)
        self.assertEqual("SERVER_ERROR", r.json()["error"]["code"])
        self.assertIn("unavailable", r.json()["error"]["message"].lower())
        self.assertEqual(422, self.c.get("/geocode").status_code)

    def test_address_search_geocodes_and_adds_distance_and_radius(self):
        with patch("app.services.geocode_address", return_value=FAKE_GEOCODE):
            r = self.c.get("/listings/search?address=1%20Test%20Street%2C%20San%20Jose%2C%20CA&guests=2")
        self.assertEqual(200, r.status_code, r.text)
        results = r.json()["data"]
        self.assertTrue(results)
        self.assertIn(1, [l["id"] for l in results])
        for item in results:
            self.assertIsNotNone(item["distance_km"])
            self.assertLessEqual(item["distance_km"], 80)
        # A far-away lookup returns nothing inside the radius.
        far = GeocodeResult(query="far", display_name="New York", address="1",
                            city="New York", state="NY", zip="10001", country="US",
                            lat=40.7128, lng=-74.0060, provider="nominatim")
        with patch("app.services.geocode_address", return_value=far):
            r = self.c.get("/listings/search?address=New%20York%2C%20NY&guests=2")
        self.assertEqual([], r.json()["data"])

    def test_address_search_falls_back_to_text_when_provider_is_down(self):
        with patch("app.services.geocode_address", side_effect=GeocodingUnavailable("down")):
            r = self.c.get("/listings/search?address=Demo%20Street&guests=2")
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue(r.json()["data"])
        self.assertTrue(all("Demo Street" in l["address"] for l in r.json()["data"]))

    def test_create_without_coordinates_uses_geocoder(self):
        body = self._listing_body()
        body.pop("lat"); body.pop("lng")
        with patch("app.services.geocode_address", return_value=FAKE_GEOCODE):
            created, _ = self._create(body)
        self.assertAlmostEqual(FAKE_GEOCODE.lat, created["lat"])
        self.assertAlmostEqual(FAKE_GEOCODE.lng, created["lng"])

    def test_create_without_coordinates_and_geocoder_down_is_rejected(self):
        body = self._listing_body()
        body.pop("lat"); body.pop("lng")
        with patch("app.services.geocode_address", side_effect=GeocodingUnavailable("down")):
            r = self.c.post("/listings", json=body,
                            headers={"Authorization": f"Bearer {self._host_token()}"})
        self.assertEqual(422, r.status_code, r.text)
        self.assertEqual("VALIDATION_ERROR", r.json()["error"]["code"])

    # -- expanded host CRUD validation / moderation ------------------------
    def test_host_crud_captures_contact_hours_media_and_reenters_moderation(self):
        body = self._listing_body(
            host_contact_name="Ada Host", host_contact_email="ada@example.com",
            host_contact_phone="408-555-0101", operating_start_time="08:00",
            operating_end_time="20:00", check_in_time="15:00", check_out_time="11:00",
            available_times="Daily 8am to 8pm", amenities=["WiFi", "Kitchen"],
            photos=["https://example.com/a.jpg"], videos=["https://example.com/a.mp4"])
        created, token = self._create(body)
        self.assertEqual("PENDING_APPROVAL", created["status"])
        self.assertEqual("Ada Host", created["host_contact_name"])
        self.assertEqual("ada@example.com", created["host_contact_email"])
        self.assertEqual("08:00", created["operating_start_time"])
        self.assertEqual("20:00", created["operating_end_time"])
        self.assertEqual(["WiFi", "Kitchen"], created["amenities"])
        self.assertEqual(["https://example.com/a.jpg"], created["photos"])
        self.assertEqual(["https://example.com/a.mp4"], created["videos"])
        self.assertNotIn(created["id"], [l["id"] for l in self.c.get(
            "/listings/search?guests=2").json()["data"]])

        self._approve(created["id"])
        self.assertIn(created["id"], [l["id"] for l in self.c.get(
            "/listings/search?guests=2").json()["data"]])
        # A material update must return to moderation and leave public search.
        updated = self.c.put(f"/listings/{created['id']}",
                             json=self._listing_body(title="Renovated Loft"),
                             headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, updated.status_code, updated.text)
        self.assertEqual("PENDING_APPROVAL", updated.json()["data"]["status"])
        self.assertNotIn(created["id"], [l["id"] for l in self.c.get(
            "/listings/search?guests=2").json()["data"]])
        # Other hosts cannot edit or remove it.
        other = self._host_token("other-host@list.test")
        self.assertEqual(403, self.c.put(
            f"/listings/{created['id']}", json=self._listing_body(),
            headers={"Authorization": f"Bearer {other}"}).status_code)
        self.assertEqual(403, self.c.delete(
            f"/listings/{created['id']}",
            headers={"Authorization": f"Bearer {other}"}).status_code)
        # Ownership is rechecked on delete, and the owner can remove it.
        removed = self.c.delete(f"/listings/{created['id']}",
                                headers={"Authorization": f"Bearer {token}"})
        self.assertEqual("REMOVED", removed.json()["data"]["status"])
        mine = self.c.get("/host/listings", headers={"Authorization": f"Bearer {token}"}).json()["data"]
        self.assertEqual("REMOVED", next(l for l in mine if l["id"] == created["id"])["status"])

    def test_host_crud_validation_errors(self):
        token = self._host_token()
        headers = {"Authorization": f"Bearer {token}"}
        invalid_bodies = [
            self._listing_body(title=""),
            self._listing_body(description=""),
            self._listing_body(zip="ABC"),
            self._listing_body(price_per_night=0),
            self._listing_body(max_guests=0),
            self._listing_body(photos=["not-a-url"]),
            self._listing_body(videos=["javascript:alert(1)"]),
            self._listing_body(host_contact_email="not-an-email"),
            self._listing_body(host_contact_phone="12"),
            self._listing_body(available_times=""),
            self._listing_body(operating_start_time="10:00", operating_end_time="10:00"),
            self._listing_body(operating_start_time="09:00", operating_end_time="17:00",
                               check_in_time="18:00"),
            self._listing_body(lat=37.3, lng=None),
        ]
        for body in invalid_bodies:
            r = self.c.post("/listings", json=body, headers=headers)
            self.assertEqual(422, r.status_code, f"{body} -> {r.text}")

    def test_update_keeps_coordinates_when_address_is_unchanged(self):
        created, token = self._create()
        updated = dict(self._listing_body(title="Same address, new title"))
        updated.pop("lat"); updated.pop("lng")
        with patch("app.services.geocode_address", side_effect=GeocodingUnavailable("down")):
            r = self.c.put(f"/listings/{created['id']}", json=updated,
                           headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, r.status_code, r.text)
        self.assertAlmostEqual(created["lat"], r.json()["data"]["lat"])
        self.assertAlmostEqual(created["lng"], r.json()["data"]["lng"])
        self.assertEqual("Same address, new title", r.json()["data"]["title"])

    def test_my_listings_requires_host_role_and_returns_moderation_status(self):
        customer = self._customer_token()
        self.assertEqual(403, self.c.get("/host/listings",
                                         headers={"Authorization": f"Bearer {customer}"}).status_code)
        created, token = self._create()
        mine = self.c.get("/host/listings", headers={"Authorization": f"Bearer {token}"}).json()["data"]
        self.assertEqual("PENDING_APPROVAL", next(l for l in mine if l["id"] == created["id"])["status"])


class TestGeocodingHelpers(unittest.TestCase):
    def test_normalization_and_state_codes(self):
        self.assertEqual("1 main st, san jose, ca", normalize_address("  1 Main St,  San Jose, CA. "))
        self.assertEqual("CA", normalize_state_code("California"))
        self.assertEqual("CA", normalize_state_code(" ca "))
        self.assertEqual("NY", normalize_state_code("New York"))

    def test_google_only_when_server_key_is_configured(self):
        empty_keys = {"STAYNEST_GOOGLE_GEOCODING_API_KEY": "",
                      "STAYNEST_GOOGLE_MAPS_API_KEY": "",
                      "GOOGLE_GEOCODING_API_KEY": "",
                      "GOOGLE_MAPS_API_KEY": ""}
        with patch.dict(os.environ, {**empty_keys, "STAYNEST_GEOCODING_PROVIDER": "google"},
                        clear=False):
            self.assertEqual("nominatim", get_provider().name)
        with patch.dict(os.environ, {"STAYNEST_GEOCODING_PROVIDER": "google",
                                     "GOOGLE_MAPS_API_KEY": "secret"}, clear=False):
            self.assertEqual("google", get_provider().name)
        with patch.dict(os.environ, {"STAYNEST_GEOCODING_PROVIDER": "nominatim",
                                     "GOOGLE_MAPS_API_KEY": "secret"}, clear=False):
            self.assertEqual("nominatim", get_provider().name)


if __name__ == "__main__":
    unittest.main()
