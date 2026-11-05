"""Characterization tests for the service layer (pure, in-memory)."""
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import services as svc
from app.core.errors import ApiError
from app.domain import (Booking, BookingStatus, Listing, ListingStatus, Review,
                        User, UserRole)
from app.geocoding import GeocodeResult, GeocodingUnavailable
from app.repositories import InMemoryStore

HOST = User(1, "host@x.co", "h", "Host", UserRole.HOST)
OTHER_HOST = User(2, "host2@x.co", "h", "Host Two", UserRole.HOST)
CUSTOMER = User(3, "cust@x.co", "h", "Cust", UserRole.CUSTOMER)
ADMIN = User(9, "admin@x.co", "h", "Admin", UserRole.ADMIN)

GOOD = dict(title="  Nice  loft ", description="d", address="1 Main St", city="San Jose",
            state="California", zip="95110", lat=37.3, lng=-121.9, price_per_night=120,
            max_guests=4, bedrooms=1, bathrooms=1, amenities=[" wifi ", ""],
            photos=["/uploads/a.jpg"], videos=["https://x/y.mp4"])


@pytest.fixture()
def store():
    s = InMemoryStore()
    for u in (HOST, OTHER_HOST, CUSTOMER, ADMIN):
        s.save(u)
    return s


@pytest.fixture()
def listings(store):
    return svc.ListingService(store)


def err(callable_, *a, **k) -> ApiError:
    with pytest.raises(ApiError) as e:
        callable_(*a, **k)
    return e.value


def approved(store, **kw):
    base = dict(id=len(store.listings) + 1, host_id=1, title="L", description="d",
                address="1 Main", city="San Jose", state="CA", zip="95110", lat=37.3,
                lng=-121.9, price_per_night=Decimal("100"), max_guests=4, bedrooms=1,
                bathrooms=1, status=ListingStatus.APPROVED)
    base.update(kw)
    return store.save(Listing(**base))


def test_listing_service_price_tier(listings, store):
    assert listings.price_tier(approved(store, price_per_night=Decimal("250"))) == "$$$"


# -- host CRUD ---------------------------------------------------------------
def test_find_and_guards(listings, store):
    assert err(listings.detail, 404).code == "NOT_FOUND"
    assert err(listings.create, CUSTOMER, GOOD).code == "FORBIDDEN"
    li = listings.create(HOST, GOOD)
    assert li.status == ListingStatus.PENDING_APPROVAL and li.id == 1
    assert err(listings.update, OTHER_HOST, li.id, GOOD).code == "FORBIDDEN"
    assert err(listings.remove, OTHER_HOST, li.id).code == "FORBIDDEN"
    assert listings.by_host(HOST) == [li]
    assert err(listings.by_host, CUSTOMER).code == "FORBIDDEN"


def test_create_geocodes_when_coordinates_missing(listings):
    payload = {**GOOD, "lat": None, "lng": None, "city": "San Jose"}
    result = GeocodeResult("q", "d", "a", "c", "CA", "95110", "US", 10.0, 20.0, "fake")
    with patch("app.services.listing_service.geocode_address", return_value=result):
        li = listings.create(HOST, payload)
    assert (li.lat, li.lng) == (10.0, 20.0)
    with patch("app.services.listing_service.geocode_address", side_effect=GeocodingUnavailable("down")):
        e = err(listings.create, HOST, payload)
    assert e.field == "lat"


def test_ensure_coordinates_fills_blank_parts(listings):
    result = GeocodeResult("q", "d", "a", "Oakland", "CA", "94601", "US", 1.0, 2.0, "fake")
    payload = {"address": "x", "city": "", "state": "", "zip": ""}
    with patch("app.services.listing_service.geocode_address", return_value=result):
        listings._ensure_coordinates(payload)
    assert (payload["city"], payload["state"], payload["zip"]) == ("Oakland", "CA", "94601")
    # existing parts are preserved
    full = {"address": "x", "city": "A", "state": "NY", "zip": "10001"}
    with patch("app.services.listing_service.geocode_address", return_value=result):
        listings._ensure_coordinates(full)
    assert (full["city"], full["state"], full["zip"]) == ("A", "NY", "10001")
    # resolved result without parts leaves blanks alone
    sparse = GeocodeResult("q", "d", "a", "", "", "", "US", 1.0, 2.0, "fake")
    blank = {"address": "x"}
    with patch("app.services.listing_service.geocode_address", return_value=sparse):
        listings._ensure_coordinates(blank)
    assert "city" not in blank


def test_update_paths(listings, store):
    li = listings.create(HOST, GOOD)
    li.status = ListingStatus.APPROVED
    same_place = {**GOOD, "lat": None, "lng": None, "state": "CA", "title": "New"}
    updated = listings.update(HOST, li.id, same_place)
    assert (updated.lat, updated.lng) == (37.3, -121.9)       # kept
    assert updated.status == ListingStatus.PENDING_APPROVAL   # re-moderated

    moved = {**GOOD, "lat": None, "lng": None, "address": "9 Other Rd"}
    with patch("app.services.listing_service.geocode_address", side_effect=GeocodingUnavailable("x")):
        assert err(listings.update, HOST, li.id, moved).field == "lat"
    explicit = {**GOOD, "address": "9 Other Rd", "lat": 1.0, "lng": 2.0}
    assert listings.update(HOST, li.id, explicit).lat == 1.0

    listings.remove(HOST, li.id)
    assert err(listings.update, HOST, li.id, GOOD).code == "CONFLICT"


def test_update_requires_lat_and_lng_together(listings):
    li = listings.create(HOST, GOOD)
    for partial in ({"lat": 5.0, "lng": None}, {"lat": None, "lng": 7.0}):
        e = err(listings.update, HOST, li.id, {**GOOD, "state": "CA", **partial})
        assert e.field == "lat" and "together" in e.message


def test_admin_moderation(listings, store):
    li = approved(store, status=ListingStatus.PENDING_APPROVAL)
    assert err(listings.approve, HOST, li.id, True).code == "FORBIDDEN"
    assert listings.approve(ADMIN, li.id, False).status == ListingStatus.REJECTED
    assert listings.approve(ADMIN, li.id, True).status == ListingStatus.APPROVED
    assert err(listings.remove_by_admin, HOST, li.id).code == "FORBIDDEN"
    assert listings.remove_by_admin(ADMIN, li.id).status == ListingStatus.REMOVED
    assert err(listings.approve, ADMIN, li.id, True).code == "CONFLICT"


def test_review_summary(listings, store):
    li = approved(store)
    assert listings.review_summary(li.id)["average_rating"] is None
    store.save(Review(1, 1, li.id, 3, 4, "ok"))
    store.save(Review(2, 2, li.id, 77, 5, "great"))
    out = listings.review_summary(li.id)
    assert out["average_rating"] == 4.5 and out["review_count"] == 2
    assert [r["id"] for r in out["reviews"]] == [2, 1]
    assert out["reviews"][0]["customer_name"] is None and out["reviews"][1]["customer_name"] == "Cust"


D = date(2027, 5, 1)


# -- availability -----------------------------------------------------------
def test_availability_variants(listings, store):
    li = approved(store, max_guests=2)
    a = listings.availability(li)
    assert a["available"] and not a["requested"]
    pending = approved(store, status=ListingStatus.PENDING_APPROVAL)
    assert listings.availability(pending)["failure"] == "approval"
    assert listings.availability(li, guests="x")["failure"] == "validation"
    assert listings.availability(li, guests=0)["reason"] == "guests must be at least 1"

    out = listings.availability(li, check_in=D, check_out=D + timedelta(2), guests=5)
    assert out["failure"] == "validation" and out["total_cost"] == "200"
    out = listings.availability(pending, check_in=D, check_out=D + timedelta(2), guests=1)
    assert out["failure"] == "approval"
    out = listings.availability(li, check_in=D, check_out=D + timedelta(2), guests=1)
    assert out["available"] and out["nights"] == 2


def test_availability_time_and_overlap_failures(listings, store):
    li = approved(store, operating_start_time=time(10), operating_end_time=time(18))
    base = dict(check_in=D, check_out=D + timedelta(2), guests=1)
    early = listings.availability(li, **base, check_in_time=time(8), check_out_time=time(12))
    assert early["failure"] == "time" and "check-in" in early["reason"]
    late = listings.availability(li, **base, check_in_time=time(12), check_out_time=time(20))
    assert late["failure"] == "time" and "check-out" in late["reason"]
    store.save(Booking(1, li.id, 3, D, D + timedelta(2), 1, Decimal("200"),
                       check_in_time=time(15), check_out_time=time(11)))
    taken = listings.availability(li, **base, check_in_time=time(15), check_out_time=time(11))
    assert taken["failure"] == "overlap"


# -- search -----------------------------------------------------------------
def test_search_validation_and_filters(listings, store):
    approved(store, city="San Jose", state="CA", zip="95110")
    approved(store, city="Austin", state="TX", zip="73301")
    assert err(listings.search, guests="x").field == "guests"
    assert err(listings.search, guests=0).field == "guests"
    assert err(listings.search, radius_km="far").field == "radius_km"
    assert err(listings.search, radius_km=0).field == "radius_km"
    ids = lambda **k: [x.id for x in listings.search(**k).listings]
    assert ids() == [1, 2]
    assert ids(city=" austin ") == [2] and ids(state="California") == [1]
    assert ids(zip_code="73301") == [2]
    assert ids(check_in=D, nights=3) == [1, 2]
    store.save(Booking(1, 1, 3, D, D + timedelta(3), 1, Decimal("300")))
    assert ids(check_in=D, nights=3) == [2]
    assert ids(check_in=D, nights=3, include_unavailable=True) == [1, 2]


def test_search_geocoded_radius_and_text_fallback(listings, store, monkeypatch):
    near = approved(store, address="1 Main St", lat=37.0, lng=-122.0)
    far = approved(store, address="2 Far Rd", lat=10.0, lng=10.0)
    point = GeocodeResult("q", "d", "a", "c", "CA", "9", "US", 37.01, -122.01, "fake")
    with patch("app.services.listing_service.geocode_address", return_value=point):
        out = listings.search(address="1 Main St")
        assert [x.id for x in out.listings] == [near.id] and out.geocoded is point
        assert out.distance_by_id[near.id] < 5
        # exact text match survives even outside the radius
        far_point = GeocodeResult("q", "d", "a", "c", "CA", "9", "US", 0.0, 0.0, "fake")
    with patch("app.services.listing_service.geocode_address", return_value=far_point):
        assert [x.id for x in listings.search(address="2 Far Rd").listings] == [far.id]
        monkeypatch.setenv("STAYNEST_SEARCH_RADIUS_KM", "20000")
        assert len(listings.search(address="zzz").listings) == 2   # env radius widens the search
        assert listings.search(address="zzz").listings == listings.search(address="zzz", radius_km=20000).listings
        assert len(listings.search(address="zzz", radius_km=2000).listings) == 1
    with patch("app.services.listing_service.geocode_address", return_value=point):
        wide = listings.search(address="1 Main St", radius_km="20000")
        assert {x.id for x in wide.listings} == {near.id, far.id}
    with patch("app.services.listing_service.geocode_address", side_effect=GeocodingUnavailable("x")):
        out = listings.search(address="2 far rd")
        assert [x.id for x in out.listings] == [far.id] and out.geocoded is None


# -- auth -------------------------------------------------------------------
def test_auth_register_and_login(store):
    auth = svc.AuthService(store)
    user = auth.register(" New@X.co ", "password1", " New  User ", "host")
    assert user.email == "new@x.co" and user.full_name == "New User" and user.role == UserRole.HOST
    assert user.id == 10
    assert auth.register("c@x.co", "password1", "C", UserRole.CUSTOMER).role == UserRole.CUSTOMER
    assert err(auth.register, "a@x.co", "password1", "A", "ADMIN").code == "FORBIDDEN"
    assert err(auth.register, "a@x.co", "password1", "A", "wizard").code == "FORBIDDEN"
    assert err(auth.register, "bad", "password1", "A", "HOST").field == "email"
    assert err(auth.register, "a@x.co", "password1", "  ", "HOST").field == "full_name"
    assert err(auth.register, "a@x.co", "short", "A", "HOST").field == "password"
    assert err(auth.register, "a@x.co", None, "A", "HOST").field == "password"
    assert err(auth.register, "NEW@x.co", "password1", "A", "HOST").code == "CONFLICT"

    session = auth.login(" New@X.co", "password1")
    assert session["role"] == "HOST" and session["token_type"] == "bearer"
    assert err(auth.login, "new@x.co", "wrong").code == "UNAUTHORIZED"
    assert err(auth.login, "ghost@x.co", "password1").code == "UNAUTHORIZED"


# -- bookings -----------------------------------------------------------------
def test_booking_lifecycle(store):
    li = approved(store)
    svc_ = svc.BookingService(store)
    assert err(svc_.book, HOST, li.id, D, D + timedelta(2), 1, D).code == "FORBIDDEN"
    assert err(svc_.book, CUSTOMER, 99, D, D + timedelta(2), 1, D).code == "NOT_FOUND"
    e = err(svc_.book, CUSTOMER, li.id, D, D + timedelta(2), 99, D)
    assert e.code == "VALIDATION_ERROR" and e.field == "check_out"
    b = svc_.book(CUSTOMER, li.id, D, D + timedelta(2), 2, D,
                  check_in_time=time(16), check_out_time=time(10))
    assert b.total_price == Decimal("200") and b.check_in_time == time(16)
    assert b.location_zip == "95110" and b.booked_date == D
    e = err(svc_.book, CUSTOMER, li.id, D, D + timedelta(2), 1, D)
    assert e.code == "CONFLICT" and e.field is None

    assert err(svc_.cancel, HOST, b.id).code == "FORBIDDEN"
    assert err(svc_.cancel, CUSTOMER, 99).code == "NOT_FOUND"
    stranger = User(50, "s@x.co", "h", "S", UserRole.CUSTOMER)
    assert err(svc_.cancel, stranger, b.id).code == "FORBIDDEN"
    assert svc_.cancel(CUSTOMER, b.id).status == BookingStatus.CANCELLED
    assert svc_.cancel.__self__ is svc_
    e = err(svc_.cancel, CUSTOMER, b.id)
    assert e.code == "VALIDATION_ERROR"


def test_booking_completion(store):
    li = approved(store)
    svc_ = svc.BookingService(store)
    b = svc_.book(CUSTOMER, li.id, D, D + timedelta(2), 1, D)
    assert err(svc_.complete, CUSTOMER, 99, D).code == "NOT_FOUND"
    other = User(50, "s@x.co", "h", "S", UserRole.CUSTOMER)
    assert err(svc_.complete, other, b.id, D).code == "FORBIDDEN"
    assert "not ended" in err(svc_.complete, CUSTOMER, b.id, D).message
    assert svc_.complete(CUSTOMER, b.id, D + timedelta(2)).status == BookingStatus.COMPLETED
    assert "CONFIRMED" in err(svc_.complete, CUSTOMER, b.id, D + timedelta(3)).message


# -- reviews / analytics -----------------------------------------------------
def test_review_submission(store):
    li = approved(store)
    bookings = svc.BookingService(store)
    b = bookings.book(CUSTOMER, li.id, D, D + timedelta(2), 1, D)
    reviews = svc.ReviewService(store)
    assert err(reviews.submit, HOST, b.id, 5).code == "FORBIDDEN"
    assert err(reviews.submit, CUSTOMER, b.id, 9).field == "rating"
    assert err(reviews.submit, CUSTOMER, 99, 5).code == "NOT_FOUND"
    assert err(reviews.submit, CUSTOMER, b.id, 5, today=D + timedelta(5)).code == "VALIDATION_ERROR"  # not COMPLETED
    bookings.complete(CUSTOMER, b.id, D + timedelta(2))
    assert "after the stay" in err(reviews.submit, CUSTOMER, b.id, 5, today=D).message
    r = reviews.submit(CUSTOMER, b.id, 4, "nice", today=D + timedelta(2))
    assert r.id == 1 and r.listing_id == li.id
    assert err(reviews.submit, CUSTOMER, b.id, 4, today=D + timedelta(2)).code == "VALIDATION_ERROR"


def test_analytics_service_access(store):
    li = approved(store)
    svc.BookingService(store).book(CUSTOMER, li.id, D, D + timedelta(2), 1, D)
    a = svc.AnalyticsService(store)
    assert a.host_analytics(HOST, 30, D)["total_bookings"] == 1
    assert a.host_analytics(OTHER_HOST, 30, D)["total_bookings"] == 0
    assert err(a.host_analytics, CUSTOMER, 30, D).code == "FORBIDDEN"
    assert a.platform_analytics(ADMIN, 30, D, zip_code="95110")["total_bookings"] == 1
    assert err(a.platform_analytics, HOST, 30, D).code == "FORBIDDEN"
