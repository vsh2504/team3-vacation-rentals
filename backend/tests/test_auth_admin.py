"""Ranadhir Reddy Rikkala — Identity, Platform & Admin Control tests.
Covers US01, US02, US03, US21, US22. Run: python3 backend/tests/test_auth_admin.py -v
These are API tests (TestClient), not domain tests: they prove the
router + service + error envelope together, per requirement.
"""
import sys, unittest
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.main import app, seed_demo_data
from app.routers.common import STORE

def fresh():
    STORE.users.clear(); STORE.listings.clear(); STORE.bookings.clear(); STORE.reviews.clear()
    seed_demo_data()

class TestAuthAdmin(unittest.TestCase):
    def setUp(self):
        fresh()
        self.c = TestClient(app, raise_server_exceptions=False)
    def _login(self, email, pw="password123"):
        r = self.c.post("/auth/login", json={"email": email, "password": pw})
        self.assertEqual(200, r.status_code, r.text)
        return r.json()["data"]["access_token"]
    def _register(self, email, role):
        r = self.c.post("/auth/register", json={"email": email, "password": "password123", "full_name": "Test", "role": role})
        self.assertEqual(200, r.status_code, r.text)
        return r.json()["data"]
    def test_register_customer_and_login_and_me(self):
        u = self._register("cust@auth.test", "CUSTOMER")
        self.assertEqual("CUSTOMER", u["role"])
        tok = self._login("cust@auth.test")
        me = self.c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(200, me.status_code)
        self.assertEqual("cust@auth.test", me.json()["data"]["email"])
    def test_register_host_and_duplicate_email_409(self):
        self._register("host@auth.test", "HOST")
        r = self.c.post("/auth/register", json={"email": "host@auth.test", "password": "password123", "full_name": "Dup", "role": "HOST"})
        self.assertEqual(409, r.status_code)
        self.assertEqual("CONFLICT", r.json()["error"]["code"])
    def test_register_admin_forbidden_and_wrong_password_401(self):
        r = self.c.post("/auth/register", json={"email": "a@auth.test", "password": "password123", "full_name": "A", "role": "ADMIN"})
        self.assertEqual(403, r.status_code)
        self._register("cust2@auth.test", "CUSTOMER")
        r = self.c.post("/auth/login", json={"email": "cust2@auth.test", "password": "wrongpass123"})
        self.assertEqual(401, r.status_code)
        self.assertFalse(r.json()["success"])
    def test_me_without_token_401_and_error_envelope(self):
        r = self.c.get("/auth/me")
        self.assertEqual(401, r.status_code)
        body = r.json()
        self.assertEqual({"success": False, "data": None}, {k: body[k] for k in ("success", "data")})
        self.assertIn("code", body["error"])
    def test_admin_queue_and_approve_reject_and_non_admin_403(self):
        admin = self._login("admin@staynest.local", "admin12345")
        q = self.c.get("/admin/listings?status=PENDING_APPROVAL", headers={"Authorization": f"Bearer {admin}"})
        self.assertEqual(200, q.status_code)
        pending = q.json()["data"]
        self.assertGreater(len(pending), 0)
        first = pending[0]["id"]
        ok = self.c.post(f"/admin/listings/{first}/approve", headers={"Authorization": f"Bearer {admin}"})
        self.assertEqual("APPROVED", ok.json()["data"]["status"])
        # Approved listing now appears in search
        s = self.c.get(f"/listings/search?zip={pending[0]['zip']}")
        self.assertIn(first, [l["id"] for l in s.json()["data"]])
        # Non-admin cannot approve
        self._register("cust3@auth.test", "CUSTOMER")
        cust = self._login("cust3@auth.test")
        r = self.c.post(f"/admin/listings/{first}/approve", headers={"Authorization": f"Bearer {cust}"})
        self.assertEqual(403, r.status_code)
    def test_admin_remove_listing_leaves_search(self):
        admin = self._login("admin@staynest.local", "admin12345")
        all_ = self.c.get("/admin/listings", headers={"Authorization": f"Bearer {admin}"}).json()["data"]
        target = all_[0]["id"]
        r = self.c.delete(f"/admin/listings/{target}", headers={"Authorization": f"Bearer {admin}"})
        self.assertEqual("REMOVED", r.json()["data"]["status"])
        s = self.c.get("/listings/search")
        self.assertNotIn(target, [l["id"] for l in s.json()["data"]])

    # -- registration / login / persisted-user identity -------------------
    def test_registration_normalizes_email_and_allocates_unique_ids(self):
        u = self._register("  Mixed.Case@Auth.Test ", "CUSTOMER")
        self.assertEqual("mixed.case@auth.test", u["email"])
        # The seeded demo admin owns id 99; new accounts must not reuse it.
        self.assertGreater(u["id"], 99)
        self.assertEqual("CUSTOMER", u["role"])
        tok = self._login("MIXED.CASE@AUTH.TEST")
        me = self.c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["data"]
        self.assertEqual(u["id"], me["id"])
        # Duplicate detection is case-insensitive too.
        r = self.c.post("/auth/register", json={"email": " mixed.case@auth.test ",
                                                "password": "password123",
                                                "full_name": "Dup", "role": "CUSTOMER"})
        self.assertEqual(409, r.status_code, r.text)
        self.assertEqual("CONFLICT", r.json()["error"]["code"])

    def test_login_and_me_return_role_appropriate_navigation(self):
        self._register("host@nav.test", "HOST")
        login = self.c.post("/auth/login", json={"email": "host@nav.test", "password": "password123"})
        self.assertEqual(200, login.status_code, login.text)
        user = login.json()["data"]["user"]
        self.assertEqual("HOST", user["role"])
        keys = {item["key"] for item in user["navigation"]}
        self.assertTrue({"search", "listings", "analytics", "bookings"}.issubset(keys))
        me = self.c.get("/auth/me",
                        headers={"Authorization": f"Bearer {login.json()['data']['access_token']}"}).json()["data"]
        self.assertEqual(user["navigation"], me["navigation"])

        self._register("cust@nav.test", "CUSTOMER")
        cust = self.c.post("/auth/login", json={"email": "cust@nav.test", "password": "password123"}).json()["data"]["user"]
        cust_keys = {item["key"] for item in cust["navigation"]}
        self.assertNotIn("moderation", cust_keys)
        self.assertNotIn("analytics", cust_keys)

        admin_tok = self._login("admin@staynest.local", "admin12345")
        admin = self.c.get("/auth/me", headers={"Authorization": f"Bearer {admin_tok}"}).json()["data"]
        self.assertIn("moderation", {item["key"] for item in admin["navigation"]})

    def test_invalid_registration_inputs_are_rejected(self):
        cases = [
            ({"email": "not-an-email", "password": "password123", "full_name": "X", "role": "CUSTOMER"}, 422),
            ({"email": "short@auth.test", "password": "short", "full_name": "X", "role": "CUSTOMER"}, 422),
            ({"email": "blank@auth.test", "password": "password123", "full_name": "   ", "role": "CUSTOMER"}, 422),
            ({"email": "role@auth.test", "password": "password123", "full_name": "X", "role": "SUPERUSER"}, 422),
            ({"email": "admin2@auth.test", "password": "password123", "full_name": "X", "role": "ADMIN"}, 403),
        ]
        for body, expected in cases:
            r = self.c.post("/auth/register", json=body)
            self.assertEqual(expected, r.status_code, f"{body} -> {r.text}")

    def test_tokens_for_removed_users_are_rejected(self):
        self._register("gone@auth.test", "CUSTOMER")
        tok = self._login("gone@auth.test")
        STORE.users[:] = [u for u in STORE.users if u.email != "gone@auth.test"]
        r = self.c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        self.assertEqual(401, r.status_code, r.text)
        self.assertEqual("UNAUTHORIZED", r.json()["error"]["code"])

    # -- moderation queue / state transitions -----------------------------
    def _listing_body(self, token, **kw):
        body = {"title": "Moderated Loft", "description": "Sunny loft near the station.",
                "address": "10 Approval Way", "city": "San Jose", "state": "CA", "zip": "95110",
                "lat": 37.3382, "lng": -121.8863, "price_per_night": 150,
                "max_guests": 4, "bedrooms": 2, "bathrooms": 1,
                "amenities": ["WiFi", "Kitchen"], "available_times": "Daily 3pm-11am",
                "host_contact_name": "Queue Host", "host_contact_email": "queue@host.test",
                "host_contact_phone": "408-555-0101",
                "photos": ["https://example.com/loft.jpg"],
                "videos": ["https://example.com/loft.mp4"]}
        body.update(kw)
        r = self.c.post("/listings", json=body,
                        headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, r.status_code, r.text)
        return r.json()["data"]

    def test_moderation_queue_includes_completeness_and_host_context(self):
        self._register("queue-host@auth.test", "HOST")
        host_tok = self._login("queue-host@auth.test")
        complete = self._listing_body(host_tok)
        incomplete = self._listing_body(host_tok, title="Sparse Listing", amenities=[],
                                        photos=[], videos=[], host_contact_name="",
                                        host_contact_email="", host_contact_phone="")

        admin = self._login("admin@staynest.local", "admin12345")
        queue = self.c.get("/admin/listings?status=PENDING_APPROVAL",
                           headers={"Authorization": f"Bearer {admin}"}).json()["data"]
        complete_row = next(row for row in queue if row["id"] == complete["id"])
        self.assertEqual("queue-host@auth.test", complete_row["host"]["email"])
        self.assertEqual("queue@host.test", complete_row["host_contact_email"])
        self.assertEqual("Test", complete_row["host"]["full_name"])
        self.assertEqual("Sunny loft near the station.", complete_row["description"])
        self.assertEqual(["WiFi", "Kitchen"], complete_row["amenities"])
        self.assertEqual(1, complete_row["photo_count"])
        self.assertEqual(1, complete_row["video_count"])
        self.assertEqual(["https://example.com/loft.jpg"], complete_row["photos"])
        self.assertFalse(complete_row["searchable"])
        self.assertTrue(complete_row["completeness"]["complete"], complete_row)
        self.assertEqual(100, complete_row["completeness"]["score"])
        self.assertEqual([], complete_row["completeness"]["missing"])

        sparse_row = next(row for row in queue if row["id"] == incomplete["id"])
        self.assertFalse(sparse_row["completeness"]["complete"])
        self.assertLess(sparse_row["completeness"]["score"], 100)
        for field in ("amenities", "contact", "media"):
            self.assertIn(field, sparse_row["completeness"]["missing"])

    def test_moderation_state_transitions_control_public_search(self):
        self._register("owner@auth.test", "HOST")
        token = self._login("owner@auth.test")
        listing = self._listing_body(token)
        lid = listing["id"]
        admin = self._login("admin@staynest.local", "admin12345")
        headers = {"Authorization": f"Bearer {admin}"}

        approved = self.c.post(f"/admin/listings/{lid}/approve", headers=headers)
        self.assertEqual(200, approved.status_code, approved.text)
        self.assertTrue(approved.json()["data"]["searchable"])
        self.assertIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])

        rejected = self.c.post(f"/admin/listings/{lid}/reject", headers=headers)
        self.assertEqual(200, rejected.status_code, rejected.text)
        self.assertEqual("REJECTED", rejected.json()["data"]["status"])
        self.assertFalse(rejected.json()["data"]["searchable"])
        self.assertNotIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])

        # A rejected listing may be reconsidered and approved again.
        self.c.post(f"/admin/listings/{lid}/approve", headers=headers)
        self.assertIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])

        removed = self.c.delete(f"/admin/listings/{lid}", headers=headers)
        self.assertEqual("REMOVED", removed.json()["data"]["status"])
        self.assertNotIn(lid, [l["id"] for l in self.c.get("/listings/search?zip=95110").json()["data"]])
        # REMOVED is terminal for moderation.
        self.assertEqual(409, self.c.post(f"/admin/listings/{lid}/approve", headers=headers).status_code)
        self.assertEqual(409, self.c.post(f"/admin/listings/{lid}/reject", headers=headers).status_code)
        self.assertEqual(422, self.c.get("/admin/listings?status=UNKNOWN",
                                         headers=headers).status_code)

    def test_role_guards_reject_out_of_scope_api_calls(self):
        self._register("plain-customer@auth.test", "CUSTOMER")
        customer = {"Authorization": f"Bearer {self._login('plain-customer@auth.test')}"}
        self._register("plain-host@auth.test", "HOST")
        host = {"Authorization": f"Bearer {self._login('plain-host@auth.test')}"}
        admin = {"Authorization": f"Bearer {self._login('admin@staynest.local', 'admin12345')}"}

        self.assertEqual(401, self.c.get("/admin/listings").status_code)
        for headers in (customer, host):
            self.assertEqual(403, self.c.get("/admin/listings", headers=headers).status_code)
            self.assertEqual(403, self.c.post("/admin/listings/1/approve", headers=headers).status_code)
            self.assertEqual(403, self.c.post("/admin/listings/1/reject", headers=headers).status_code)
            self.assertEqual(403, self.c.delete("/admin/listings/1", headers=headers).status_code)
            self.assertEqual(403, self.c.get("/admin/analytics?days=30", headers=headers).status_code)
        self.assertEqual(403, self.c.get("/host/analytics?days=30", headers=customer).status_code)
        self.assertEqual(200, self.c.get("/host/analytics?days=30", headers=host).status_code)
        # Analytics scopes are distinct: admin uses the platform route.
        self.assertEqual(403, self.c.get("/host/analytics?days=30", headers=admin).status_code)
        self.assertEqual(200, self.c.get("/admin/analytics?days=30", headers=admin).status_code)


if __name__ == "__main__":
    unittest.main()
