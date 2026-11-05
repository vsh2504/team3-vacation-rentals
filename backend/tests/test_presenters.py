"""Presenters (JSON shaping) and the require_role dependency."""
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import presenters
from app.core import security
from app.core.errors import ApiError
from app.domain import Booking, BookingStatus, Listing, User, UserRole
from app.main import api_error_handler  # noqa: F401  (ensures handler import works)
from app.repositories import InMemoryStore
from app.routers.common import get_store, require_role

TODAY = date(2027, 6, 1)


def booking(**kw):
    base = dict(id=1, listing_id=1, customer_id=2, check_in=date(2027, 7, 1),
                check_out=date(2027, 7, 3), guests=1, total_price=Decimal("10"),
                booked_date=TODAY)
    base.update(kw)
    return Booking(**base)


def test_format_clock():
    assert presenters.format_clock(time(9, 5)) == "09:05"
    assert presenters.format_clock(None) is None


@pytest.mark.parametrize("kw,expected", [
    (dict(), "upcoming"),
    (dict(check_out=date(2027, 6, 1)), "past"),                  # check-out today is past
    (dict(check_out=date(2027, 5, 1), check_in=date(2027, 4, 1)), "past"),
    (dict(status=BookingStatus.CANCELLED), "cancelled"),
])
def test_stay_state(kw, expected):
    assert presenters.stay_state(booking(**kw), TODAY) == expected


def test_booking_out_with_and_without_listing_and_coordinates():
    store = InMemoryStore()
    bare = presenters.booking_out(booking(cancelled_at=datetime(2027, 1, 1, tzinfo=timezone.utc)),
                                  store, TODAY)
    assert bare["map_url"] is None and bare["location"]["osm_embed_url"] is None
    assert bare["listing"] == {"id": 1, "title": "", "price_per_night": None,
                               "max_guests": None, "photos": [], "url": "/listings/1"}
    assert bare["cancelled_at"].startswith("2027-01-01") and bare["has_review"] is False

    li = Listing(1, 1, "Loft", "d", "a", "c", "CA", "9", 1.0, 2.0, Decimal("50"), 3, 1, 1,
                 photos=["/p.jpg"])
    store.save(li)
    full = presenters.booking_out(booking(location_lat=1.0, location_lng=2.0), store, TODAY)
    assert "openstreetmap" in full["map_url"] and full["listing"]["title"] == "Loft"
    assert full["listing"]["price_per_night"] == "50" and full["listing"]["photos"] == ["/p.jpg"]


def test_reviewer_name_privacy():
    store = InMemoryStore()
    store.save(User(1, "a@x.co", "h", "Ann Marie Lee", UserRole.CUSTOMER))
    store.save(User(2, "b@x.co", "h", "Cher", UserRole.CUSTOMER))
    assert presenters.reviewer_name(store, 1) == "Ann L."
    assert presenters.reviewer_name(store, 2) == "Cher"
    assert presenters.reviewer_name(store, 3) == "Guest"


def test_host_out_lookup():
    store = InMemoryStore()
    store.save(User(1, "h@x.co", "SECRET", "Host", UserRole.HOST, "555"))
    out = presenters.host_out(store, 1)
    assert out == {"id": 1, "full_name": "Host", "email": "h@x.co", "phone": "555", "role": "HOST"}
    assert presenters.host_out(store, 9) is None


# -- require_role --------------------------------------------------------------
@pytest.fixture()
def role_app():
    app = FastAPI()
    store = InMemoryStore()
    for uid, role in ((1, UserRole.HOST), (2, UserRole.ADMIN)):
        store.save(User(uid, f"{uid}@x.co", "h", "U", role))

    @app.exception_handler(ApiError)
    async def handler(_, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=exc.status, content=exc.envelope())

    @app.get("/only-admin")
    def only_admin(user=Depends(require_role(UserRole.ADMIN, message="Admin only"))):
        return {"id": user.id}

    @app.get("/staff")
    def staff(user=Depends(require_role(UserRole.ADMIN, UserRole.HOST, message="Staff only"))):
        return {"id": user.id}

    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def _auth(uid, role):
    return {"Authorization": f"Bearer {security.make_token(uid, role)}"}


def test_require_role_allows_and_denies(role_app):
    assert role_app.get("/only-admin", headers=_auth(2, "ADMIN")).json() == {"id": 2}
    denied = role_app.get("/only-admin", headers=_auth(1, "HOST"))
    assert denied.status_code == 403 and denied.json()["error"]["message"] == "Admin only"
    assert role_app.get("/staff", headers=_auth(1, "HOST")).status_code == 200
    assert role_app.get("/only-admin").status_code == 401
