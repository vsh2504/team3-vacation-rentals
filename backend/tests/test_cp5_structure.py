"""Checkpoint 5: injectable geocoder + ListingSearch, Template Method providers,
store factory (Singleton construction)."""
from decimal import Decimal

import pytest

from app import geocoding as g
from app.domain import Listing, ListingStatus, User, UserRole
from app.repositories import InMemoryStore
from app.services import ListingService
from app.services.listing_search import ListingSearch
from app.store import create_store

POINT = g.GeocodeResult("q", "d", "a", "San Jose", "CA", "95110", "US", 37.0, -122.0, "fake")


def li(id, address, lat, lng, **kw):
    base = dict(id=id, host_id=1, title="L", description="d", address=address, city="SJ",
                state="CA", zip="95110", lat=lat, lng=lng, price_per_night=Decimal("10"),
                max_guests=2, bedrooms=1, bathrooms=1, status=ListingStatus.APPROVED)
    base.update(kw)
    return Listing(**base)


# -- injectable geocoder -----------------------------------------------------
def test_listing_service_uses_injected_geocoder_for_create():
    calls = []

    def fake(query):
        calls.append(query)
        return POINT

    store = InMemoryStore()
    host = User(1, "h@x.co", "h", "H", UserRole.HOST)
    payload = dict(title="t", description="d", address="1 Main", city="SJ", state="CA",
                   zip="95110", price_per_night=10, max_guests=1, bedrooms=1, bathrooms=1)
    listing = ListingService(store, geocode=fake).create(host, payload)
    assert calls == ["1 Main, SJ, CA, 95110"] and (listing.lat, listing.lng) == (37.0, -122.0)


def test_listing_search_with_injected_geocoder_filters_by_radius():
    store = InMemoryStore()
    store.save(li(1, "1 Near St", 37.01, -122.01))
    store.save(li(2, "2 Far Rd", 10.0, 10.0))
    search = ListingSearch(store, lambda q: POINT, availability=lambda *a, **k: {"available": True})
    out = search.run(address="zzz", radius_km=50)
    assert [x.id for x in out.listings] == [1] and out.distance_by_id[1] < 5
    assert out.geocoded is POINT


def test_listing_search_falls_back_to_text_when_geocoder_fails():
    store = InMemoryStore()
    store.save(li(1, "1 Near St", 37.01, -122.01))
    store.save(li(2, "2 Far Rd", 10.0, 10.0))

    def down(_): raise g.GeocodingUnavailable("down")
    out = ListingSearch(store, down, availability=lambda *a, **k: {"available": True}).run(address="far rd")
    assert [x.id for x in out.listings] == [2] and out.geocoded is None


# -- Template Method providers ---------------------------------------------------
class FakeProvider(g.HttpGeocodingProvider):
    name = "fake-http"

    def __init__(self): self.events = []
    def _before_request(self): self.events.append("before")
    def _request_url(self, address): self.events.append(f"url:{address}"); return "http://x"
    def _parse(self, address, payload): self.events.append(f"parse:{payload}"); return POINT


def test_http_provider_template_runs_hooks_in_order(monkeypatch):
    monkeypatch.setattr(g, "_http_json", lambda url, **k: {"ok": url})
    provider = FakeProvider()
    assert provider.geocode("addr") is POINT
    assert provider.events == ["before", "url:addr", "parse:{'ok': 'http://x'}"]


def test_template_defaults_are_abstract_or_noop():
    base = g.HttpGeocodingProvider()
    base._before_request()                    # default hook: nothing
    with pytest.raises(NotImplementedError):
        base._request_url("a")
    with pytest.raises(NotImplementedError):
        base._parse("a", {})


def test_build_result_uses_street_then_display_head():
    r = g.build_result("q", "Head, Tail", "", "C", "ca", "9", "US", 1, 2, "p")
    assert r.address == "Head" and r.state == "ca"
    r = g.build_result("q", "Head, Tail", "1 Main", "C", "CA", "9", "US", 1, 2, "p")
    assert r.address == "1 Main"


# -- store factory ---------------------------------------------------------------
def test_create_store_prefers_sql_then_falls_back():
    sql = object()
    assert create_store(lambda: sql) is sql
    assert isinstance(create_store(lambda: None), InMemoryStore)

    def broken(): raise RuntimeError("no db")
    assert isinstance(create_store(broken), InMemoryStore)


def test_shared_store_is_a_singleton():
    from app.routers.common import STORE, get_store
    assert get_store() is STORE
