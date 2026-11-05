"""Characterization tests for the geocoding provider boundary (no network)."""
import io
import json

import pytest

from app import geocoding as g


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    g.clear_cache()
    for name in ("STAYNEST_GOOGLE_GEOCODING_API_KEY", "STAYNEST_GOOGLE_MAPS_API_KEY",
                 "GOOGLE_GEOCODING_API_KEY", "GOOGLE_MAPS_API_KEY",
                 "STAYNEST_GEOCODING_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(g, "_throttle_nominatim", lambda: None)
    yield
    g.clear_cache()


# -- configuration ---------------------------------------------------------
def test_google_key_checks_names_in_priority_order(monkeypatch):
    assert g.google_api_key() == ""
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", " last ")
    assert g.google_api_key() == "last"
    monkeypatch.setenv("STAYNEST_GOOGLE_GEOCODING_API_KEY", "first")
    assert g.google_api_key() == "first"


def test_provider_name_resolution(monkeypatch):
    assert g.provider_name() == "nominatim"
    monkeypatch.setenv("STAYNEST_GEOCODING_PROVIDER", "google")
    assert g.provider_name() == "nominatim"          # forced google, no key
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    assert g.provider_name() == "google"
    monkeypatch.setenv("STAYNEST_GEOCODING_PROVIDER", "nominatim")
    assert g.provider_name() == "nominatim"          # explicit nominatim wins
    monkeypatch.setenv("STAYNEST_GEOCODING_PROVIDER", "")
    assert g.provider_name() == "google"             # auto: key present


def test_get_provider(monkeypatch):
    assert isinstance(g.get_provider(), g.NominatimProvider)
    assert isinstance(g.get_provider("google"), g.NominatimProvider)  # no key
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    assert isinstance(g.get_provider("GOOGLE"), g.GoogleGeocodingProvider)


def test_normalizers():
    assert g.normalize_state_code(None) == ""
    assert g.normalize_state_code(" ca ") == "CA"
    assert g.normalize_state_code("California") == "CA"
    assert g.normalize_state_code("Atlantis") == "Atlantis"
    assert g.normalize_address("  1 Main St., ") == "1 main st"


def test_result_as_dict_contains_map_links():
    r = g.GeocodeResult("q", "d", "a", "c", "CA", "9", "US", 1.0, 2.0, "x")
    d = r.as_dict()
    assert d["provider"] == "x" and "openstreetmap" in d["map_url"]
    assert "embed" in d["osm_embed_url"]


# -- HTTP ------------------------------------------------------------------
class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_http_json_success_and_failure(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["timeout"] = timeout
        return _Resp(json.dumps({"ok": 1}).encode())

    monkeypatch.setattr(g, "urlopen", fake_urlopen)
    assert g._http_json("http://x") == {"ok": 1}
    assert seen["timeout"] == g.DEFAULT_TIMEOUT
    g._http_json("http://x", timeout=2)
    assert seen["timeout"] == 2

    def boom(*a, **k): raise OSError("secret-key-in-url")
    monkeypatch.setattr(g, "urlopen", boom)
    with pytest.raises(g.GeocodingUnavailable) as err:
        g._http_json("http://x?key=secret")
    assert "secret" not in str(err.value) and err.value.__cause__ is None


def test_throttle_sleeps_only_when_called_too_quickly(monkeypatch):
    monkeypatch.undo()  # drop the autouse stub for this test
    sleeps = []
    clock = iter([100.2, 100.2, 105.0, 105.0])
    monkeypatch.setattr(g._time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(g._time, "sleep", sleeps.append)
    monkeypatch.setattr(g, "_nominatim_last_call", 100.0)
    g._throttle_nominatim()
    assert sleeps and sleeps[0] == pytest.approx(0.8)
    monkeypatch.setattr(g, "_nominatim_last_call", 0.0)
    sleeps.clear()
    g._throttle_nominatim()
    assert sleeps == []


# -- Nominatim -------------------------------------------------------------
NOM_ROW = {"lat": "37.1", "lon": "-122.2", "display_name": "1 Main St, San Jose",
           "address": {"house_number": "1", "road": "Main St", "town": "San Jose",
                       "state": "California", "postcode": "95112", "country": "USA"}}


def test_nominatim_parses_result(monkeypatch):
    monkeypatch.setattr(g, "_http_json", lambda url, **k: [NOM_ROW])
    r = g.NominatimProvider("http://nom/").geocode("1 Main St")
    assert (r.address, r.city, r.state, r.zip, r.country) == (
        "1 Main St", "San Jose", "CA", "95112", "USA")
    assert (r.lat, r.lng, r.provider) == (37.1, -122.2, "nominatim")


def test_nominatim_fallback_fields(monkeypatch):
    row = {"lat": 1, "lon": 2, "address": {"country_code": "us"}}
    monkeypatch.setattr(g, "_http_json", lambda url, **k: [row])
    r = g.NominatimProvider().geocode("Somewhere, Far")
    assert r.address == "Somewhere" and r.country == "US" and r.city == ""


@pytest.mark.parametrize("payload", [None, [], {}])
def test_nominatim_not_found(monkeypatch, payload):
    monkeypatch.setattr(g, "_http_json", lambda url, **k: payload)
    with pytest.raises(g.GeocodeNotFound):
        g.NominatimProvider().geocode("x")


def test_nominatim_unusable_location(monkeypatch):
    monkeypatch.setattr(g, "_http_json", lambda url, **k: [{"lat": "n/a", "lon": 1}])
    with pytest.raises(g.GeocodingUnavailable):
        g.NominatimProvider().geocode("x")


# -- Google ----------------------------------------------------------------
GOOGLE_OK = {"status": "OK", "results": [{
    "formatted_address": "1 Main St, San Jose, CA",
    "address_components": [
        {"types": ["street_number"], "short_name": "1"},
        {"types": ["route"], "long_name": "Main St"},
        {"types": ["locality"], "short_name": "San Jose"},
        {"types": ["administrative_area_level_1"], "short_name": "CA"},
        {"types": ["postal_code"], "short_name": "95112"},
        {"types": ["country"], "short_name": "US"}],
    "geometry": {"location": {"lat": 37.1, "lng": -122.2}}}]}


def test_google_requires_key():
    with pytest.raises(g.GeocodingUnavailable):
        g.GoogleGeocodingProvider("")


def test_google_parses_result(monkeypatch):
    monkeypatch.setattr(g, "_http_json", lambda url, **k: GOOGLE_OK)
    r = g.GoogleGeocodingProvider("k", "http://gg/").geocode("1 Main St")
    assert (r.address, r.city, r.state, r.zip, r.country, r.provider) == (
        "1 Main St", "San Jose", "CA", "95112", "US", "google")


def test_google_component_helper_handles_gaps():
    assert g._google_component(None, "x") == ""
    assert g._google_component([{"types": ["x"]}], "x") == ""
    assert g._google_component([{"types": None}], "x") == ""


@pytest.mark.parametrize("payload,exc", [
    ("nope", g.GeocodingUnavailable),
    ({"status": "ZERO_RESULTS"}, g.GeocodeNotFound),
    ({"status": "REQUEST_DENIED"}, g.GeocodingUnavailable),
    ({"status": "OK", "results": []}, g.GeocodingUnavailable),
    ({"status": "OK", "results": [{"geometry": {}}]}, g.GeocodingUnavailable),
])
def test_google_error_paths(monkeypatch, payload, exc):
    monkeypatch.setattr(g, "_http_json", lambda url, **k: payload)
    with pytest.raises(exc):
        g.GoogleGeocodingProvider("k").geocode("x")


# -- cache + public entry point -------------------------------------------
class _Provider:
    name = "fake"

    def __init__(self, behavior):
        self.behavior, self.calls = behavior, 0

    def geocode(self, address):
        self.calls += 1
        if isinstance(self.behavior, Exception):
            raise self.behavior
        return self.behavior


RESULT = g.GeocodeResult("q", "d", "a", "c", "CA", "9", "US", 1.0, 2.0, "fake")


def test_geocode_address_blank_raises_not_found():
    with pytest.raises(g.GeocodeNotFound):
        g.geocode_address("   ")


def test_geocode_address_caches_success():
    p = _Provider(RESULT)
    assert g.geocode_address(" A  b ", provider=p) is RESULT
    assert g.geocode_address("a B", provider=p) is RESULT
    assert p.calls == 1
    g.geocode_address("a b", provider=p, use_cache=False)
    assert p.calls == 2


def test_geocode_address_negative_cache_and_transient_errors():
    p = _Provider(g.GeocodeNotFound("none"))
    for _ in range(2):
        with pytest.raises(g.GeocodeNotFound):
            g.geocode_address("nowhere", provider=p)
    assert p.calls == 1
    with pytest.raises(g.GeocodeNotFound):
        g.geocode_address("nowhere", provider=p, use_cache=False)
    assert p.calls == 2

    down = _Provider(g.GeocodingUnavailable("down"))
    for _ in range(2):
        with pytest.raises(g.GeocodingUnavailable):
            g.geocode_address("flaky", provider=down)
    assert down.calls == 2  # transport errors are not cached


def test_cache_expiry_and_eviction(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(g._time, "monotonic", lambda: now[0])
    cache = g._AddressCache()
    cache.put("a", RESULT)
    assert cache.get("a") == (True, RESULT)
    now[0] += g.CACHE_TTL_SECONDS + 1
    assert cache.get("a") == (False, None)
    assert cache.get("missing") == (False, None)

    monkeypatch.setattr(g, "CACHE_MAX_ENTRIES", 2)
    now[0] = 0
    cache.put("x", RESULT); now[0] = 1
    cache.put("y", RESULT); now[0] = 2
    cache.put("z", None)
    assert cache.get("x") == (False, None)
    assert cache.get("z") == (True, None)
