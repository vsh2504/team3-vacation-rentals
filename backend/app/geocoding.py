"""Server-side geocoding provider boundary.

OpenStreetMap Nominatim is the local default. Google Geocoding is used only
when a server-side key is configured (``STAYNEST_GEOCODING_PROVIDER`` can
force either provider; a missing Google key always falls back to Nominatim).

Design notes
------------
* Providers implement the tiny :class:`GeocodingProvider` protocol, so the
  rest of the application never talks to a vendor SDK or HTTP API directly.
* Normalized lookups are cached in-process (successful results for a day,
  misses briefly) to respect Nominatim's usage policy and keep search fast.
* Provider credentials are never part of :class:`GeocodeResult` and are never
  echoed in error messages returned to callers.
"""
from __future__ import annotations

import json
import os
import threading
import time as _time
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
DEFAULT_GOOGLE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DEFAULT_USER_AGENT = "StayNest/1.0 (local development; contact@staynest.local)"
DEFAULT_TIMEOUT = 6.0
MIN_NOMINATIM_INTERVAL = 1.0  # Nominatim policy: max one request per second.
CACHE_TTL_SECONDS = 24 * 60 * 60
NEGATIVE_CACHE_TTL_SECONDS = 5 * 60
CACHE_MAX_ENTRIES = 512


class GeocodingError(Exception):
    """Base class for address-provider failures."""


class GeocodingUnavailable(GeocodingError):
    """The provider could not be reached or returned an unusable response."""


class GeocodeNotFound(GeocodingError):
    """The provider responded successfully but had no match for the address."""


@dataclass(frozen=True)
class GeocodeResult:
    """Normalized address returned by a geocoding provider."""

    query: str
    display_name: str
    address: str
    city: str
    state: str
    zip: str
    country: str
    lat: float
    lng: float
    provider: str

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "display_name": self.display_name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip": self.zip,
            "country": self.country,
            "lat": self.lat,
            "lng": self.lng,
            "provider": self.provider,
            "map_url": osm_url(self.lat, self.lng),
            "osm_embed_url": osm_embed_url(self.lat, self.lng),
        }


class GeocodingProvider(Protocol):
    name: str

    def geocode(self, address: str) -> GeocodeResult:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# Configuration / provider selection
# ---------------------------------------------------------------------------

def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def google_api_key() -> str:
    """Return the configured server-side Google key, if any.

    Only server-side variables are considered. ``VITE_*`` values are browser
    configuration and must never be treated as a server secret.
    """
    for name in (
        "STAYNEST_GOOGLE_GEOCODING_API_KEY",
        "STAYNEST_GOOGLE_MAPS_API_KEY",
        "GOOGLE_GEOCODING_API_KEY",
        "GOOGLE_MAPS_API_KEY",
    ):
        value = _env(name)
        if value:
            return value
    return ""


def provider_name() -> str:
    """Resolve the active provider without leaking configuration details."""
    explicit = _env("STAYNEST_GEOCODING_PROVIDER").lower()
    if explicit == "google":
        return "google" if google_api_key() else "nominatim"
    if explicit == "nominatim":
        return "nominatim"
    return "google" if google_api_key() else "nominatim"


def get_provider(name: str | None = None) -> GeocodingProvider:
    selected = (name or provider_name()).lower()
    if selected == "google" and google_api_key():
        return GoogleGeocodingProvider(google_api_key())
    return NominatimProvider()


# ---------------------------------------------------------------------------
# Address normalization, distance and map links
# ---------------------------------------------------------------------------

_US_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "puerto rico": "PR", "guam": "GU", "virgin islands": "VI",
}


def normalize_state_code(value: str | None) -> str:
    """Normalize a US state name or code to a two-letter code.

    Non-US or unknown values are returned trimmed (upper-cased when short)
    rather than discarded, so the provider boundary stays location-agnostic.
    """
    raw = " ".join(str(value or "").split()).strip(" ,.")
    if not raw:
        return ""
    if len(raw) == 2 and raw.isalpha():
        return raw.upper()
    return _US_STATE_CODES.get(raw.lower(), raw)


def normalize_address(value: str | None) -> str:
    """Stable cache key for an address (case/whitespace/punctuation safe)."""
    return " ".join(str(value or "").split()).strip(" ,.").lower()


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    radius = 6371.0088
    d_lat = radians(float(lat2) - float(lat1))
    d_lng = radians(float(lng2) - float(lng1))
    a = (sin(d_lat / 2) ** 2
         + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(d_lng / 2) ** 2)
    return 2 * radius * asin(sqrt(a))


def osm_url(lat: float, lng: float, zoom: int = 15) -> str:
    return (f"https://www.openstreetmap.org/?mlat={float(lat):.6f}"
            f"&mlon={float(lng):.6f}#map={zoom}/{float(lat):.6f}/{float(lng):.6f}")


def osm_embed_url(lat: float, lng: float, span: float = 0.02) -> str:
    lat, lng = float(lat), float(lng)
    return ("https://www.openstreetmap.org/export/embed.html"
            f"?bbox={lng - span},{lat - span / 2},{lng + span},{lat + span / 2}"
            f"&layer=mapnik&marker={lat},{lng}")


# ---------------------------------------------------------------------------
# HTTP + provider implementations
# ---------------------------------------------------------------------------

def _http_json(url: str, *, timeout: float | None = None) -> object:
    request = Request(url, headers={
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en",
    })
    try:
        with urlopen(request, timeout=timeout or DEFAULT_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        # ``from None`` keeps vendor URLs (which may contain keys) out of the
        # exception chain that could otherwise reach logs or clients.
        raise GeocodingUnavailable(
            "Address lookup is temporarily unavailable; try city, state, or ZIP instead"
        ) from None


_nominatim_lock = threading.Lock()
_nominatim_last_call = 0.0


def _throttle_nominatim() -> None:
    global _nominatim_last_call
    with _nominatim_lock:
        elapsed = _time.monotonic() - _nominatim_last_call
        if elapsed < MIN_NOMINATIM_INTERVAL:
            _time.sleep(MIN_NOMINATIM_INTERVAL - elapsed)
        _nominatim_last_call = _time.monotonic()


class NominatimProvider:
    """OpenStreetMap Nominatim provider (the local default)."""

    name = "nominatim"

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or _env("STAYNEST_NOMINATIM_URL", DEFAULT_NOMINATIM_URL)).rstrip("/")

    def geocode(self, address: str) -> GeocodeResult:
        params = urlencode({
            "q": address,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
        })
        _throttle_nominatim()
        payload = _http_json(f"{self.base_url}/search?{params}")
        if not isinstance(payload, list) or not payload:
            raise GeocodeNotFound(f"No location found for '{address}'")
        row = payload[0] or {}
        details = row.get("address") or {}
        try:
            lat, lng = float(row["lat"]), float(row["lon"])
        except (KeyError, TypeError, ValueError):
            raise GeocodingUnavailable("Address lookup returned an unusable location") from None

        street = " ".join(part for part in (
            details.get("house_number"),
            details.get("road") or details.get("pedestrian") or details.get("footway"),
        ) if part)
        city = (details.get("city") or details.get("town") or details.get("village")
                or details.get("hamlet") or details.get("municipality")
                or details.get("suburb") or details.get("county") or "")
        state = normalize_state_code(details.get("state") or details.get("state_code"))
        display = row.get("display_name") or address
        return GeocodeResult(
            query=address,
            display_name=display,
            address=street or display.split(",")[0].strip(),
            city=city,
            state=state,
            zip=details.get("postcode") or "",
            country=details.get("country") or (details.get("country_code") or "").upper(),
            lat=lat,
            lng=lng,
            provider=self.name,
        )


def _google_component(components: list[dict], *types: str) -> str:
    for component in components or []:
        if any(t in (component.get("types") or []) for t in types):
            return component.get("short_name") or component.get("long_name") or ""
    return ""


class GoogleGeocodingProvider:
    """Google Geocoding provider, usable only when a server-side key exists."""

    name = "google"

    def __init__(self, api_key: str, base_url: str | None = None):
        if not api_key:
            raise GeocodingUnavailable("Google geocoding is not configured")
        self._api_key = api_key
        self.base_url = (base_url or _env("STAYNEST_GOOGLE_GEOCODING_URL", DEFAULT_GOOGLE_URL)).rstrip("/")

    def geocode(self, address: str) -> GeocodeResult:
        params = urlencode({"address": address, "key": self._api_key})
        payload = _http_json(f"{self.base_url}?{params}")
        if not isinstance(payload, dict):
            raise GeocodingUnavailable("Address lookup returned an unusable response")
        status = payload.get("status")
        if status == "ZERO_RESULTS":
            raise GeocodeNotFound(f"No location found for '{address}'")
        if status != "OK" or not payload.get("results"):
            # Deliberately generic: never surface provider error payloads.
            raise GeocodingUnavailable("Google address lookup is unavailable")
        row = payload["results"][0] or {}
        components = row.get("address_components") or []
        location = ((row.get("geometry") or {}).get("location") or {})
        try:
            lat, lng = float(location["lat"]), float(location["lng"])
        except (KeyError, TypeError, ValueError):
            raise GeocodingUnavailable("Address lookup returned an unusable location") from None
        street = " ".join(part for part in (
            _google_component(components, "street_number"),
            _google_component(components, "route"),
        ) if part)
        city = _google_component(components, "locality", "postal_town", "sublocality")
        state = normalize_state_code(_google_component(components, "administrative_area_level_1"))
        display = row.get("formatted_address") or address
        return GeocodeResult(
            query=address,
            display_name=display,
            address=street or display.split(",")[0].strip(),
            city=city,
            state=state,
            zip=_google_component(components, "postal_code"),
            country=_google_component(components, "country"),
            lat=lat,
            lng=lng,
            provider=self.name,
        )


# ---------------------------------------------------------------------------
# Cached public entry point
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    expires_at: float
    result: GeocodeResult | None


class _AddressCache:
    def __init__(self) -> None:
        self._data: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[bool, GeocodeResult | None]:
        now = _time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False, None
            if entry.expires_at <= now:
                self._data.pop(key, None)
                return False, None
            return True, entry.result

    def put(self, key: str, result: GeocodeResult | None) -> None:
        ttl = CACHE_TTL_SECONDS if result is not None else NEGATIVE_CACHE_TTL_SECONDS
        with self._lock:
            if len(self._data) >= CACHE_MAX_ENTRIES:
                # Cheap bounded cache: drop the entry closest to expiry.
                oldest = min(self._data, key=lambda k: self._data[k].expires_at)
                self._data.pop(oldest, None)
            self._data[key] = _CacheEntry(_time.monotonic() + ttl, result)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_CACHE = _AddressCache()


def clear_cache() -> None:
    """Clear the normalized-address cache (used by tests and local tooling)."""
    _CACHE.clear()


def geocode_address(address: str, *, provider: GeocodingProvider | None = None,
                    use_cache: bool = True) -> GeocodeResult:
    """Geocode an address through the configured provider, with caching.

    Raises :class:`GeocodeNotFound` when there is no match and
    :class:`GeocodingUnavailable` when the provider cannot be reached.
    """
    query = " ".join(str(address or "").split()).strip()
    if not query:
        raise GeocodeNotFound("An address is required for lookup")
    active = provider or get_provider()
    key = f"{active.name}:{normalize_address(query)}"
    if use_cache:
        hit, cached = _CACHE.get(key)
        if hit:
            if cached is None:
                raise GeocodeNotFound(f"No location found for '{query}'")
            return cached
    try:
        result = active.geocode(query)
    except GeocodeNotFound:
        if use_cache:
            _CACHE.put(key, None)
        raise
    except GeocodingError:
        # Do not negative-cache transport errors: a transient outage should
        # recover immediately once the provider is reachable again.
        raise
    if use_cache:
        _CACHE.put(key, result)
    return result
