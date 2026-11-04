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

if __name__ == "__main__":
    unittest.main()
