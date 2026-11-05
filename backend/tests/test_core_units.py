"""Characterization tests for small core modules (security, domain, schemas,
repositories, uploads, shared router helpers, demo seed, app wiring)."""
import io
import os
import tempfile
import time as _time
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import domain as d
from app.core import security
from app.core.errors import ApiError, ok
from app.demo_seed import seed_demo_reviews
from app.main import app
from app.repositories import InMemoryStore
from app.routers import uploads
from app.schemas import BookingIn, ListingIn, SearchQuery

UTC = timezone.utc


def make_listing(**kw):
    base = dict(id=1, host_id=1, title="Loft", description="d", address="1 Demo St",
                city="San Jose", state="CA", zip="95110", lat=37.3, lng=-121.9,
                price_per_night=Decimal("150"), max_guests=4, bedrooms=1, bathrooms=1,
                status=d.ListingStatus.APPROVED)
    base.update(kw)
    return d.Listing(**base)


def make_booking(**kw):
    base = dict(id=1, listing_id=1, customer_id=2, check_in=date(2027, 5, 10),
                check_out=date(2027, 5, 13), guests=2, total_price=Decimal("450"))
    base.update(kw)
    return d.Booking(**base)


# -- security --------------------------------------------------------------
def test_password_roundtrip_and_malformed_hash():
    stored = security.hash_password("hunter22")
    assert security.check_password("hunter22", stored)
    assert not security.check_password("wrong", stored)
    assert not security.check_password("x", "not-a-valid-hash")


def test_token_roundtrip_tamper_and_expiry():
    token = security.make_token(7, "HOST", secret="s")
    assert security.decode_token(token, secret="s")["sub"] == 7
    head, payload, sig = token.split(".")
    with pytest.raises(ValueError, match="bad signature"):
        security.decode_token(f"{head}.{payload}.{sig[:-2]}xx", secret="s")
    expired = security.make_token(7, "HOST", secret="s", ttl_seconds=-10)
    with pytest.raises(ValueError, match="expired"):
        security.decode_token(expired, secret="s")


def test_token_uses_env_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "env-secret")
    assert security.decode_token(security.make_token(1, "ADMIN"))["role"] == "ADMIN"


# -- errors ----------------------------------------------------------------
def test_error_envelope_and_unknown_code():
    err = ApiError("CONFLICT", "m", "f")
    assert err.status == 409
    assert err.envelope() == {"success": False, "data": None,
                              "error": {"code": "CONFLICT", "message": "m", "field": "f"}}
    assert ApiError("WHAT", "m").status == 500
    assert ok(1) == {"success": True, "data": 1, "error": None}


# -- domain ----------------------------------------------------------------
def test_overlaps_is_half_open():
    assert d.overlaps(date(2027, 1, 1), date(2027, 1, 3), date(2027, 1, 2), date(2027, 1, 4))
    assert not d.overlaps(date(2027, 1, 1), date(2027, 1, 3), date(2027, 1, 3), date(2027, 1, 4))


def test_time_window_handles_tz_and_overnight():
    aware = time(10, 0, tzinfo=UTC)
    assert not d._time_in_window(aware, time(0), time(23))
    assert d._time_in_window(time(10), time(9), time(17))
    assert not d._time_in_window(time(18), time(9), time(17))
    assert d._time_in_window(time(23), time(22), time(6))      # overnight
    assert d._time_in_window(time(5), time(22), time(6))
    assert not d._time_in_window(time(12), time(22), time(6))


def test_is_available_rejections():
    li = make_listing()
    ci, co = date(2027, 5, 1), date(2027, 5, 3)
    assert not d.is_available(make_listing(status=d.ListingStatus.PENDING_APPROVAL), ci, co, 2, [])
    assert not d.is_available(li, co, ci, 2, [])
    narrow = make_listing(operating_start_time=time(9), operating_end_time=time(17))
    assert d.is_available(narrow, ci, co, 2, [])      # default 15:00 / 11:00 are inside 09-17


def test_is_available_time_windows():
    ci, co = date(2027, 5, 1), date(2027, 5, 3)
    li = make_listing(operating_start_time=time(12), operating_end_time=time(18))
    assert not d.is_available(li, ci, co, 2, [])                 # default 11:00 checkout outside
    assert d.is_available(li, ci, co, 2, [], check_in_time=time(13), check_out_time=time(14))
    li2 = make_listing(operating_start_time=time(9), operating_end_time=time(12))
    assert not d.is_available(li2, ci, co, 2, [], check_in_time=time(15), check_out_time=time(10))
    assert not d.is_available(li2, ci, co, 2, [], check_in_time=time(10), check_out_time=time(15))


def test_availability_ignores_non_confirmed_and_other_listings():
    li = make_listing()
    ci, co = date(2027, 5, 10), date(2027, 5, 12)
    cancelled = make_booking(status=d.BookingStatus.CANCELLED)
    other = make_booking(listing_id=99)
    assert d.is_available(li, ci, co, 2, [cancelled, other])
    assert not d.is_available(li, ci, co, 2, [make_booking()])


def test_search_listings_filters():
    a = make_listing(id=1, city="San Jose", state="CA", zip="95110", address="1 Demo St")
    b = make_listing(id=2, city="Austin", state="TX", zip="73301", address="9 Lake Rd")
    ids = lambda **kw: [x.id for x in d.search_listings([a, b], [], **kw)]
    assert ids(city="austin") == [2]
    assert ids(state="ca") == [1]
    assert ids(zip_code="73301") == [2]
    assert ids(address="lake rd") == [2]
    assert ids(guests=0) == []
    assert ids(guests=9) == []
    assert ids(check_in=date(2027, 5, 1), check_out=date(2027, 5, 3)) == [1, 2]
    blocked = make_booking(listing_id=1, check_in=date(2027, 5, 1), check_out=date(2027, 5, 3))
    assert [x.id for x in d.search_listings(
        [a, b], [blocked], check_in=date(2027, 5, 1), check_out=date(2027, 5, 3))] == [2]


def test_can_review_and_cancel_and_booked_today():
    done = make_booking(status=d.BookingStatus.COMPLETED, customer_id=5)
    assert d.can_review(done, 5, []) == []
    assert len(d.can_review(make_booking(), 9, [d.Review(1, 1, 1, 9, 5)])) == 3
    assert d.can_cancel(make_booking(), 2) == []
    assert len(d.can_cancel(make_booking(status=d.BookingStatus.CANCELLED), 9)) == 2
    today = date(2027, 1, 1)
    bs = [make_booking(booked_date=today), make_booking(id=2, booked_date=today - timedelta(1)),
          make_booking(id=3, listing_id=2, booked_date=today)]
    assert d.booked_today(1, bs, today) == 1


def test_analytics_by_zip_filters_and_totals():
    today = date(2027, 6, 1)
    li1 = make_listing(id=1, host_id=1, zip="95110")
    li2 = make_listing(id=2, host_id=2, zip="95112")
    bookings = [
        make_booking(id=1, listing_id=1, booked_date=today, total_price=Decimal("100")),
        make_booking(id=2, listing_id=1, booked_date=today, total_price=Decimal("50"),
                     location_zip="95112"),
        make_booking(id=3, listing_id=2, booked_date=today, total_price=Decimal("10")),
        make_booking(id=4, listing_id=2, booked_date=today - timedelta(100)),
        make_booking(id=5, listing_id=2, booked_date=today, status=d.BookingStatus.CANCELLED),
        make_booking(id=6, listing_id=77, booked_date=today),
        make_booking(id=7, listing_id=2, booked_date=None, total_price=Decimal("5")),
    ]
    out = d.analytics_by_zip(bookings, [li1, li2], days=30, today=today)
    assert out["total_bookings"] == 4 and out["total_revenue"] == "165"
    assert [r["zip"] for r in out["by_zip"]] == ["95110", "95112"]
    host = d.analytics_by_zip(bookings, [li1, li2], days=30, today=today, host_id=2)
    assert host["total_bookings"] == 2
    zipped = d.analytics_by_zip(bookings, [li1, li2], days=30, today=today, zip_code=" 95112 ")
    assert zipped["total_bookings"] == 3 and zipped["total_rentals"] == 2
    with pytest.raises(ValueError):
        d.analytics_by_zip([], [], days=45, today=today)


# -- repositories ----------------------------------------------------------
def test_in_memory_store_queries():
    s = InMemoryStore()
    user = d.User(1, "a@b.co", "h", "A", d.UserRole.HOST)
    s.save(user)
    s.save(make_listing())
    s.save(make_booking())
    s.save(d.Review(1, 1, 1, 2, 5))
    assert s.by_email("a@b.co") is user and s.by_email("zz") is None
    assert [x.id for x in s.all()] == [1]
    assert [x.id for x in s.by_host(1)] == [1] and s.by_host(2) == []
    assert [x.id for x in s.by_customer(2)] == [1] and s.by_customer(3) == []
    assert len(s.reviews) == 1


# -- schemas ---------------------------------------------------------------
LISTING = dict(title="t", description="d", address="a", city="c", state="CA", zip="95110",
               price_per_night=10, max_guests=1, bedrooms=0, bathrooms=0)


def test_schema_time_validators_reject_offsets():
    aware = time(9, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        ListingIn(**LISTING, check_in_time=aware)
    with pytest.raises(ValidationError):
        ListingIn(**LISTING, operating_start_time=time(5), operating_end_time=time(5))
    with pytest.raises(ValidationError):
        BookingIn(listing_id=1, check_in=date(2027, 1, 1), check_out=date(2027, 1, 2),
                  guests=1, check_in_time=aware)
    with pytest.raises(ValidationError):
        SearchQuery(check_in=date(2027, 1, 1), check_out=date(2027, 1, 2),
                    check_in_time=aware, check_out_time=time(9))
    assert SearchQuery().check_in_time is None


def test_schema_stay_date_rules():
    ci = date(2027, 1, 1)
    with pytest.raises(ValidationError):
        BookingIn(listing_id=1, check_in=ci, check_out=ci, guests=1)
    with pytest.raises(ValidationError):
        BookingIn(listing_id=1, check_in=ci, check_out=ci + timedelta(15), guests=1)
    with pytest.raises(ValidationError):
        SearchQuery(check_in=ci)                       # dates must come together
    with pytest.raises(ValidationError):
        SearchQuery(nights=2)                          # nights need check_in
    with pytest.raises(ValidationError):
        SearchQuery(check_in=ci, check_out=ci + timedelta(5), nights=2)
    with pytest.raises(ValidationError):
        SearchQuery(check_in_time=time(9))             # times need dates
    with pytest.raises(ValidationError):
        SearchQuery(check_in=ci, check_out=ci + timedelta(1), check_in_time=time(9))
    q = SearchQuery(check_in=ci, nights=3)
    assert q.check_out == ci + timedelta(3)
    SearchQuery(check_in=ci, check_out=ci + timedelta(3), nights=3)
    with pytest.raises(ValidationError, match="dates are required"):
        SearchQuery(check_in_time=time(9), check_out_time=time(10))


# -- uploads ---------------------------------------------------------------
@pytest.mark.parametrize("ctype,data,ok_", [
    ("image/jpeg", b"\xff\xd8\xff\x00", True), ("image/jpeg", b"nope", False),
    ("image/png", b"\x89PNG\r\n\x1a\n", True),
    ("image/gif", b"GIF89a....", True), ("image/gif", b"GIF00a", False),
    ("image/webp", b"RIFF....WEBP", True), ("image/webp", b"RIFF....WAVE", False),
    ("video/mp4", b"\x00\x00\x00\x18ftypmp42", True), ("video/mp4", b"abcdefgh", False),
    ("video/webm", b"\x1a\x45\xdf\xa3x", True), ("text/html", b"<x>", False),
])
def test_upload_signatures(ctype, data, ok_):
    assert uploads._matches_signature(ctype, data) is ok_


@pytest.fixture()
def upload_client(monkeypatch, tmp_path):
    from app.routers.common import STORE, get_store
    store = InMemoryStore()
    store.save(d.User(1, "h@x.co", "h", "Host", d.UserRole.HOST))
    app.dependency_overrides[get_store] = lambda: store
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    client = TestClient(app, raise_server_exceptions=False)
    token = security.make_token(1, "HOST")
    yield client, {"Authorization": f"Bearer {token}"}
    app.dependency_overrides.clear()


def test_upload_size_limits(upload_client, monkeypatch):
    client, auth = upload_client
    monkeypatch.setattr(uploads, "MAX_IMAGE_BYTES", 8)
    big = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    declared = client.post("/uploads", content=big, headers={**auth, "Content-Type": "image/png"})
    assert declared.status_code == 422 and "too large" in declared.text
    # No declared length: the streaming guard must still reject it.
    streamed = client.post("/uploads", content=iter([big[:6], big[6:]]),
                           headers={**auth, "Content-Type": "image/png"})
    assert streamed.status_code == 422 and "too large" in streamed.text
    empty = client.post("/uploads", content=b"", headers={**auth, "Content-Type": "image/png"})
    assert empty.status_code == 422 and "Empty" in empty.text


def test_upload_video_ok(upload_client):
    client, auth = upload_client
    r = client.post("/uploads", content=b"\x00\x00\x00\x18ftypmp42", headers={**auth, "Content-Type": "video/mp4"})
    assert r.status_code == 200 and r.json()["data"]["kind"] == "video"


# -- shared router helpers / app wiring -------------------------------------
def test_health_endpoint_and_bad_tokens():
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/health").json()["data"]["status"] == "ok"
    assert c.get("/host/listings", headers={"Authorization": "Bearer junk"}).status_code == 401
    ghost = security.make_token(424242, "HOST")
    assert c.get("/host/listings", headers={"Authorization": f"Bearer {ghost}"}).status_code == 401


def test_flush_store_swallows_errors(monkeypatch):
    from app.routers import common

    class Boom:
        def flush(self): raise RuntimeError("db down")
    common.flush_store(Boom())      # must not raise
    common.flush_store(InMemoryStore())


# -- demo seed -------------------------------------------------------------
def test_demo_seed_idempotent_and_skips_missing_listings():
    s = InMemoryStore()
    assert seed_demo_reviews(s) is False                # no approved listings
    s.save(make_listing(id=1))                          # only listing 1 exists
    assert seed_demo_reviews(s, today=date(2027, 1, 1)) is True
    assert seed_demo_reviews(s) is False                # already seeded
    assert all(b.listing_id == 1 for b in s.bookings)
    assert any(r.rating == 5 for r in s.reviews)


# -- router edge cases -----------------------------------------------------
@pytest.fixture()
def api():
    from app.routers.common import get_store
    store = InMemoryStore()
    store.save(d.User(1, "h@x.co", "h", "Host", d.UserRole.HOST))
    store.save(make_listing(id=5, price_per_night=Decimal("80")))
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app, raise_server_exceptions=False), store
    app.dependency_overrides.clear()


def test_nights_and_duration_must_match(api):
    client, _ = api
    r = client.get("/listings/search", params={"nights": 2, "duration": 3, "check_in": "2027-05-01"})
    assert r.status_code == 422 and r.json()["error"]["field"] == "duration"
    ok_ = client.get("/listings/search", params={"duration": 2, "check_in": "2027-05-01"})
    assert ok_.status_code == 200 and ok_.json()["data"][0]["nights"] == 2


def test_listing_detail_total_cost_from_nights_without_availability_total(api):
    client, _ = api
    r = client.get("/listings/5")
    assert r.status_code == 200 and r.json()["data"]["total_cost"] is None
    from app.presenters import listing_out as _listing_out
    _, store = api
    out = _listing_out(store.listings[0], store, date(2027, 1, 1), nights=3,
                       availability={"available": True, "nights": None, "total_cost": None})
    assert out["total_cost"] == "240"


def test_geocode_endpoint_errors(api, monkeypatch):
    client, _ = api
    from app import geocoding
    from app.routers import listings as router

    def not_found(_): raise geocoding.GeocodeNotFound("x")
    monkeypatch.setattr(router, "geocode_address", not_found)
    r = client.get("/geocode", params={"address": "nowhere"})
    assert r.status_code == 404 and r.json()["error"]["field"] == "address"
    assert client.get("/geocode", params={"address": " "}).status_code == 422


def test_startup_seed_keeps_existing_data():
    from app.main import seed_demo_data
    from app.routers.common import STORE
    for coll in (STORE.users, STORE.listings, STORE.bookings, STORE.reviews):
        coll.clear()
    seed_demo_data()
    count_l, count_u = len(STORE.listings), len(STORE.users)
    seed_demo_data()           # second run is a no-op
    assert (len(STORE.listings), len(STORE.users)) == (count_l, count_u)
    STORE.users.clear()
    seed_demo_data()           # listings present, admin missing -> admin only
    assert len(STORE.listings) == count_l and len(STORE.users) == 1
