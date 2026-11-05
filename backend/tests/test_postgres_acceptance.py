"""PostgreSQL-backed, role-based API acceptance tests.

These tests intentionally exercise the same FastAPI routes as the browser while
using ``SqlBackedStore`` and PostgreSQL's exclusion constraint. They are skipped
unless ``STAYNEST_TEST_DB_URL`` names a dedicated test/acceptance database.

Run locally after ``./scripts/start_local.sh``:

    createdb -h 127.0.0.1 -p 55432 -U staynest staynest_acceptance
    STAYNEST_TEST_DB_URL=postgresql+psycopg://staynest@127.0.0.1:55432/staynest_acceptance \
      .venv/bin/python -m pytest backend/tests/test_postgres_acceptance.py -q
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.db import SqlBackedStore, metadata
from app.domain import BookingStatus, ListingStatus
from app.main import app
from app.routers.common import get_store


def _dedicated_database_url() -> str:
    value = os.environ.get("STAYNEST_TEST_DB_URL", "")
    if not value:
        pytest.skip("set STAYNEST_TEST_DB_URL to a dedicated PostgreSQL test database")
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        pytest.fail("STAYNEST_TEST_DB_URL must use PostgreSQL")
    database = (parsed.database or "").lower()
    if not any(marker in database for marker in ("test", "acceptance")):
        pytest.fail("refusing to reset a database whose name lacks 'test' or 'acceptance'")
    return value


@pytest.fixture()
def pg_api():
    engine = create_engine(_dedicated_database_url(), future=True)
    with engine.begin() as connection:
        metadata.drop_all(connection)
    store = SqlBackedStore(engine)
    app.dependency_overrides[get_store] = lambda: store
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, store, engine
    finally:
        client.close()
        app.dependency_overrides.clear()
        with engine.begin() as connection:
            metadata.drop_all(connection)
        engine.dispose()


def _register(client: TestClient, email: str, role: str) -> str:
    response = client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": email.split("@")[0].replace("-", " ").title(),
        "role": role,
    })
    assert response.status_code == 200, response.text
    return _login(client, email)


def _login(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _listing_payload(title: str, zip_code: str = "94043") -> dict:
    return {
        "title": title,
        "description": "PostgreSQL acceptance listing with complete details.",
        "address": "1600 Test Avenue",
        "city": "Mountain View",
        "state": "CA",
        "zip": zip_code,
        "lat": 37.422,
        "lng": -122.084,
        "price_per_night": 175,
        "max_guests": 4,
        "bedrooms": 2,
        "bathrooms": 2,
        "host_contact_name": "Acceptance Host",
        "host_contact_email": "host@acceptance.test",
        "host_contact_phone": "408-555-0101",
        "operating_start_time": "08:00",
        "operating_end_time": "22:00",
        "check_in_time": "15:00",
        "check_out_time": "11:00",
        "available_times": "Daily check-in 3pm and check-out 11am",
        "amenities": ["WiFi", "Kitchen", "Parking"],
        "photos": ["https://example.test/home.jpg"],
        "videos": ["https://example.test/tour.mp4"],
    }


def _create_listing(client: TestClient, host_token: str, title: str,
                    zip_code: str = "94043") -> dict:
    response = client.post(
        "/listings", json=_listing_payload(title, zip_code), headers=_headers(host_token)
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _approve(client: TestClient, listing_id: int) -> None:
    admin = _login(client, "admin@staynest.local", "admin12345")
    response = client.post(
        f"/admin/listings/{listing_id}/approve", headers=_headers(admin)
    )
    assert response.status_code == 200, response.text


def test_postgres_search_enforces_duration_time_capacity_and_moderation(pg_api):
    client, _, _ = pg_api
    host = _register(client, "search-host@acceptance.test", "HOST")
    listing = _create_listing(client, host, "Time-window cabin")

    query = (
        "/listings/search?check_in=2027-03-01&check_out=2027-03-04"
        "&check_in_time=15:00&check_out_time=11:00&guests=4&zip=94043"
    )
    assert client.get(query).json()["data"] == []  # pending is never public

    _approve(client, listing["id"])
    available = client.get(query)
    assert available.status_code == 200, available.text
    row = available.json()["data"][0]
    assert row["id"] == listing["id"]
    assert row["available"] is True
    assert row["total_cost"] == "525.0"
    assert row["photos"] and row["videos"] and row["amenities"]
    assert row["map_url"].startswith("https://www.openstreetmap.org/")

    outside_hours = client.get(query.replace("check_in_time=15:00", "check_in_time=07:00"))
    assert outside_hours.status_code == 200
    assert outside_hours.json()["data"] == []
    over_capacity = client.get(query.replace("guests=4", "guests=5"))
    assert over_capacity.status_code == 200
    assert over_capacity.json()["data"] == []

    exact_fourteen = client.get(
        "/listings/search?check_in=2027-03-01&check_out=2027-03-15&guests=2"
    )
    assert exact_fourteen.status_code == 200, exact_fourteen.text
    for bad_out in ("2027-03-01", "2027-02-28", "2027-03-16"):
        rejected = client.get(
            f"/listings/search?check_in=2027-03-01&check_out={bad_out}&guests=2"
        )
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"


def test_postgres_roles_reviews_analytics_and_cancellation(pg_api):
    client, store, _ = pg_api
    first_host = _register(client, "first-host@acceptance.test", "HOST")
    second_host = _register(client, "second-host@acceptance.test", "HOST")
    customer = _register(client, "customer@acceptance.test", "CUSTOMER")
    other_customer = _register(client, "other-customer@acceptance.test", "CUSTOMER")
    admin = _login(client, "admin@staynest.local", "admin12345")

    first = _create_listing(client, first_host, "Host one home", "94043")
    second = _create_listing(client, second_host, "Host two home", "95110")
    _approve(client, first["id"])
    _approve(client, second["id"])

    assert client.get("/admin/listings", headers=_headers(customer)).status_code == 403
    assert client.post(
        f"/admin/listings/{first['id']}/approve", headers=_headers(first_host)
    ).status_code == 403
    assert client.get("/host/listings", headers=_headers(customer)).status_code == 403

    past = client.post("/bookings", headers=_headers(customer), json={
        "listing_id": first["id"], "check_in": "2026-02-01",
        "check_out": "2026-02-03", "guests": 2,
    })
    assert past.status_code == 200, past.text
    past_id = past.json()["data"]["id"]
    assert client.post(f"/bookings/{past_id}/complete", headers=_headers(customer)).status_code == 200

    assert client.post("/reviews", headers=_headers(other_customer), json={
        "booking_id": past_id, "rating": 5, "comment": "Not mine"
    }).status_code == 422
    review = client.post("/reviews", headers=_headers(customer), json={
        "booking_id": past_id, "rating": 5, "comment": "Persisted and excellent"
    })
    assert review.status_code == 200, review.text
    assert client.post("/reviews", headers=_headers(customer), json={
        "booking_id": past_id, "rating": 4, "comment": "Duplicate"
    }).status_code == 422

    future = client.post("/bookings", headers=_headers(customer), json={
        "listing_id": second["id"], "check_in": "2027-06-01",
        "check_out": "2027-06-03", "guests": 2,
    })
    assert future.status_code == 200, future.text
    future_id = future.json()["data"]["id"]
    assert client.post("/reviews", headers=_headers(customer), json={
        "booking_id": future_id, "rating": 5, "comment": "Too soon"
    }).status_code == 422
    cancelled = client.post(f"/bookings/{future_id}/cancel", headers=_headers(customer))
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["stay_state"] == "cancelled"

    host_stats = client.get("/host/analytics?days=30", headers=_headers(first_host))
    assert host_stats.status_code == 200, host_stats.text
    assert host_stats.json()["data"]["total_bookings"] == 1
    assert {row["zip"] for row in host_stats.json()["data"]["by_zip"]} == {"94043"}
    platform = client.get("/admin/analytics?days=30", headers=_headers(admin)).json()["data"]
    assert platform["total_bookings"] == 1  # cancelled booking excluded
    filtered = client.get(
        "/admin/analytics?days=30&zip=95110", headers=_headers(admin)
    ).json()["data"]
    assert filtered["total_bookings"] == 0
    assert filtered["by_zip"] == []
    assert client.get("/admin/analytics?days=45", headers=_headers(admin)).status_code == 422

    assert next(b for b in store.bookings if b.id == future_id).status == BookingStatus.CANCELLED


def test_postgres_restart_reloads_extended_fields_moderation_booking_and_review(pg_api):
    client, store, engine = pg_api
    host = _register(client, "persist-host@acceptance.test", "HOST")
    customer = _register(client, "persist-customer@acceptance.test", "CUSTOMER")
    listing = _create_listing(client, host, "Persistent media home", "94043")
    _approve(client, listing["id"])
    booking = client.post("/bookings", headers=_headers(customer), json={
        "listing_id": listing["id"], "check_in": "2026-01-01",
        "check_out": "2026-01-03", "check_in_time": "16:00",
        "check_out_time": "10:00", "guests": 2,
    })
    assert booking.status_code == 200, booking.text
    booking_id = booking.json()["data"]["id"]
    assert client.post(f"/bookings/{booking_id}/complete", headers=_headers(customer)).status_code == 200
    assert client.post("/reviews", headers=_headers(customer), json={
        "booking_id": booking_id, "rating": 4, "comment": "Still here after restart"
    }).status_code == 200

    reloaded = SqlBackedStore(engine)
    persisted_listing = next(item for item in reloaded.listings if item.id == listing["id"])
    persisted_booking = next(item for item in reloaded.bookings if item.id == booking_id)
    assert persisted_listing.status == ListingStatus.APPROVED
    assert persisted_listing.host_contact_email == "host@acceptance.test"
    assert persisted_listing.operating_start_time.strftime("%H:%M") == "08:00"
    assert persisted_listing.photos == ["https://example.test/home.jpg"]
    assert persisted_listing.videos == ["https://example.test/tour.mp4"]
    assert persisted_booking.status == BookingStatus.COMPLETED
    assert persisted_booking.location_zip == "94043"
    assert any(review.booking_id == booking_id and review.rating == 4
               for review in reloaded.reviews)
    assert any(user.email == "persist-customer@acceptance.test" for user in reloaded.users)
    assert len(reloaded.users) == len(store.users)


def test_postgres_concurrent_api_requests_create_only_one_confirmed_booking(pg_api):
    client, _, engine = pg_api
    host = _register(client, "race-host@acceptance.test", "HOST")
    first_customer = _register(client, "race-one@acceptance.test", "CUSTOMER")
    second_customer = _register(client, "race-two@acceptance.test", "CUSTOMER")
    listing = _create_listing(client, host, "Race-safe home")
    _approve(client, listing["id"])

    barrier = Barrier(2)
    payload = {
        "listing_id": listing["id"], "check_in": "2027-07-01",
        "check_out": "2027-07-04", "check_in_time": "15:00",
        "check_out_time": "11:00", "guests": 2,
    }

    def attempt(token: str) -> int:
        barrier.wait(timeout=5)
        with TestClient(app, raise_server_exceptions=False) as threaded_client:
            return threaded_client.post(
                "/bookings", json=payload, headers=_headers(token)
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(attempt, (first_customer, second_customer)))

    assert statuses == [200, 409]
    reloaded = SqlBackedStore(engine)
    confirmed = [
        booking for booking in reloaded.bookings
        if booking.listing_id == listing["id"] and booking.status == BookingStatus.CONFIRMED
    ]
    assert len(confirmed) == 1
