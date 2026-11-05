"""Host media upload tests."""
import os, sys, tempfile, unittest
sys.path.insert(0, "backend")
os.environ["STAYNEST_UPLOAD_DIR"] = tempfile.mkdtemp()
from fastapi.testclient import TestClient
from app.main import app, seed_demo_data
from app.routers.common import STORE

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

class TestUploads(unittest.TestCase):
    def setUp(self):
        STORE.users.clear(); STORE.listings.clear(); STORE.bookings.clear(); STORE.reviews.clear()
        seed_demo_data()
        self.c = TestClient(app, raise_server_exceptions=False)
        self.h = {}
        for role in ("HOST", "CUSTOMER"):
            email = f"{role.lower()}@up.test"
            self.c.post("/auth/register", json={"email": email, "password": "password123", "full_name": "U", "role": role})
            tok = self.c.post("/auth/login", json={"email": email, "password": "password123"}).json()["data"]["access_token"]
            self.h[role] = {"Authorization": f"Bearer {tok}"}

    def _up(self, role, data, ctype):
        return self.c.post("/uploads", content=data, headers={**self.h[role], "Content-Type": ctype})

    def test_host_uploads_and_file_is_served(self):
        r = self._up("HOST", PNG, "image/png")
        self.assertEqual(200, r.status_code, r.text)
        url = r.json()["data"]["url"]
        self.assertEqual(PNG, self.c.get(url).content)

    def test_customer_forbidden(self):
        self.assertEqual(403, self._up("CUSTOMER", PNG, "image/png").status_code)

    def test_requires_auth(self):
        self.assertEqual(401, self.c.post("/uploads", content=PNG, headers={"Content-Type": "image/png"}).status_code)

    def test_rejects_bad_type_and_spoofed_content(self):
        self.assertEqual(422, self._up("HOST", b"x", "text/html").status_code)
        self.assertEqual(422, self._up("HOST", b"<script>alert(1)</script>", "image/png").status_code)
        self.assertEqual(422, self._up("HOST", b"", "image/png").status_code)

    def test_uploaded_url_accepted_in_listing(self):
        url = self._up("HOST", PNG, "image/png").json()["data"]["url"]
        body = {"title": "T", "description": "D", "address": "1 Main St", "city": "San Jose", "state": "CA",
                "zip": "95110", "lat": 37.3, "lng": -121.9, "price_per_night": 100, "max_guests": 2,
                "bedrooms": 1, "bathrooms": 1, "photos": [url]}
        r = self.c.post("/listings", json=body, headers=self.h["HOST"])
        self.assertEqual(200, r.status_code, r.text)
        self.assertEqual([url], r.json()["data"]["photos"])

if __name__ == "__main__":
    unittest.main()
