"""Listing search: text filters, stay availability and geocoded proximity.

The geocoder and the availability evaluator are injected, so the search can
be exercised without the network or the rest of ``ListingService``
(Dependency Inversion). Search and booking deliberately converge on the same
availability evaluator rather than keeping parallel date/time/capacity/
approval/overlap rules.

Pattern: Strategy (injected geocode and availability callables).
"""
import os
from dataclasses import dataclass, field
from datetime import date, time
from typing import Callable

from ..core.errors import ApiError
from ..domain import Listing, search_listings
from ..geocoding import (GeocodeResult, GeocodingError, distance_km,
                         normalize_state_code)
from .stay_window import resolve_stay_window

DEFAULT_RADIUS_ENV = "STAYNEST_SEARCH_RADIUS_KM"
DEFAULT_RADIUS_KM = "80"


@dataclass
class SearchOutcome:
    """Search results plus the requested-window context the router serializes."""

    listings: list[Listing]
    nights: int | None = None
    geocoded: GeocodeResult | None = None
    distance_by_id: dict[int, float] = field(default_factory=dict)


def _clean(value: str | None) -> str | None:
    return " ".join(value.split()).strip() if value else None


def _whole_guests(guests) -> int:
    try:
        guests = int(guests)
    except (TypeError, ValueError):
        raise ApiError("VALIDATION_ERROR", "guests must be a whole number", "guests") from None
    if guests < 1:
        raise ApiError("VALIDATION_ERROR", "guests must be at least 1", "guests")
    return guests


def _positive_radius(radius_km) -> float | None:
    if radius_km is None:
        return None
    try:
        radius = float(radius_km)
    except (TypeError, ValueError):
        raise ApiError("VALIDATION_ERROR", "radius_km must be a number", "radius_km") from None
    if radius <= 0:
        raise ApiError("VALIDATION_ERROR", "radius_km must be greater than 0", "radius_km")
    return radius


class ListingSearch:
    def __init__(self, store, geocode: Callable[[str], GeocodeResult],
                 availability: Callable[..., dict]):
        self._store = store
        self._geocode = geocode
        self._availability = availability

    def run(self, *, check_in: date | None = None, check_out: date | None = None,
            nights: int | None = None, check_in_time: time | None = None,
            check_out_time: time | None = None, guests: int = 1,
            city: str | None = None, state: str | None = None,
            zip_code: str | None = None, address: str | None = None,
            radius_km: float | None = None,
            include_unavailable: bool = False) -> SearchOutcome:
        guests = _whole_guests(guests)
        window = resolve_stay_window(check_in, check_out, nights, check_in_time,
                                     check_out_time)
        radius = _positive_radius(radius_km)
        address_text = _clean(address)
        geocoded = self._geocode_address(address_text)

        # When the address resolved, radius proximity is more accurate than a
        # loose substring match. When it did not, retain the Week 1 text filter.
        text_address = address_text if address_text and geocoded is None else None
        results = search_listings(
            self._store.listings, self._store.bookings, guests=guests,
            city=_clean(city), state=normalize_state_code(state) if state else None,
            zip_code=_clean(zip_code), address=text_address)

        if window.check_in is not None and not include_unavailable:
            results = [listing for listing in results if self._availability(
                listing, check_in=window.check_in, check_out=window.check_out,
                nights=window.nights, check_in_time=check_in_time,
                check_out_time=check_out_time, guests=guests)["available"]]

        distances: dict[int, float] = {}
        if geocoded is not None:
            results, distances = self._within_radius(results, geocoded, radius, address_text)
        return SearchOutcome(listings=results, nights=window.nights, geocoded=geocoded,
                             distance_by_id=distances)

    def _geocode_address(self, address_text: str | None) -> GeocodeResult | None:
        """Offline/unknown addresses degrade to a textual match (``None``)."""
        if not address_text:
            return None
        try:
            return self._geocode(address_text)
        except GeocodingError:
            return None

    @staticmethod
    def _within_radius(results: list[Listing], geocoded: GeocodeResult,
                       radius: float | None, address_text: str):
        effective = radius if radius is not None else float(
            os.environ.get(DEFAULT_RADIUS_ENV, DEFAULT_RADIUS_KM))
        # Keep exact textual matches even when a provider resolves the address
        # to a slightly different point (fictional demo streets, for example);
        # otherwise apply the proximity radius.
        needle = address_text.lower()
        text_matches = {
            listing.id for listing in results
            if needle in f"{listing.address} {listing.city} {listing.state} {listing.zip}".lower()
        }
        distances: dict[int, float] = {}
        nearby = []
        for listing in results:
            distance = distance_km(geocoded.lat, geocoded.lng, listing.lat, listing.lng)
            if distance <= effective or listing.id in text_matches:
                distances[listing.id] = round(distance, 1)
                nearby.append(listing)
        nearby.sort(key=lambda l: distances[l.id])
        return nearby, distances
