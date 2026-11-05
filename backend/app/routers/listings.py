"""Core API — Vinayak Gupta (team lead)
Feature: Find a Stay — Search, Maps, Listing Detail + Host Listing CRUD
Endpoints:
  GET  /listings/search?check_in&check_out&nights&check_in_time&check_out_time
                        &guests&city&state&zip&address&include_unavailable
  GET  /geocode?address=             (Nominatim by default, Google if configured)
  GET  /listings/{id}                (detail with reviews + requested availability)
  GET  /listings/{id}/availability   (requested-period availability + total cost)
  POST /listings                     (Host only, starts PENDING_APPROVAL)
  PUT  /listings/{id}                (own listing only; re-enters moderation)
  DELETE /listings/{id}              (own listing only -> REMOVED)
  GET  /host/listings                (own listings only, with moderation status)
Only APPROVED listings appear in search. Book button logic in the UI uses
the same availability rule exposed here (not a second rule in React).
"""
from datetime import date, time

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from ..core.errors import ApiError, ok
from ..geocoding import GeocodeNotFound, GeocodingUnavailable, geocode_address
from ..presenters import listing_out
from ..schemas import ListingIn, SearchQuery
from ..services import ListingService
from .common import flush_store, get_current_user, get_store

router = APIRouter(tags=["listings/search — Vinayak Gupta"])


def _duration_alias(nights: int | None, duration: int | None) -> int | None:
    """Accept either ``nights`` or ``duration`` as the requested stay length."""
    if duration is not None:
        if nights is not None and nights != duration:
            raise ApiError("VALIDATION_ERROR", "nights and duration must match", "duration")
        return duration
    return nights


def _parse_search(**kwargs) -> SearchQuery:
    """Build the shared search DTO, translating Pydantic errors to our envelope."""
    try:
        return SearchQuery(**kwargs)
    except ValidationError as exc:
        first = (exc.errors() or [{}])[0]
        location = first.get("loc") or ()
        message = str(first.get("msg") or "Invalid search parameters")
        if message.startswith("Value error, "):
            message = message[len("Value error, "):]
        field = str(location[0]) if location else None
        if not field:
            lowered = message.lower()
            field = next((name for name in ("check_out_time", "check_in_time", "check_out",
                                            "check_in", "nights", "guests")
                          if name in lowered), None)
        raise ApiError("VALIDATION_ERROR", message, field)


@router.get("/listings/search")
def search(check_in: date | None = None, check_out: date | None = None,
           nights: int | None = None, duration: int | None = None,
           check_in_time: time | None = None,
           check_out_time: time | None = None, guests: int = 1,
           city: str | None = None, state: str | None = None,
           zip: str | None = None, address: str | None = None,
           radius_km: float | None = None, include_unavailable: bool = False,
           store=Depends(get_store)):
    nights = _duration_alias(nights, duration)
    query = _parse_search(
        check_in=check_in, check_out=check_out, nights=nights,
        check_in_time=check_in_time, check_out_time=check_out_time,
        guests=guests, city=city, state=state, zip=zip, address=address,
    )
    service = ListingService(store)
    outcome = service.search(
        check_in=query.check_in, check_out=query.check_out, nights=query.nights,
        check_in_time=query.check_in_time, check_out_time=query.check_out_time,
        guests=query.guests, city=query.city, state=query.state, zip_code=query.zip,
        address=query.address, radius_km=radius_km,
        include_unavailable=include_unavailable,
    )
    today = date.today()
    out = []
    for listing in outcome.listings:
        availability = service.availability(
            listing, check_in=query.check_in, check_out=query.check_out,
            nights=outcome.nights, check_in_time=query.check_in_time,
            check_out_time=query.check_out_time, guests=query.guests)
        out.append(listing_out(listing, store, today, nights=outcome.nights,
                                distance=outcome.distance_by_id.get(listing.id),
                                availability=availability))
    return ok(out)


@router.get("/geocode")
@router.get("/listings/geocode")
def geocode(address: str = ""):
    """Normalize an address through the configured provider (never returns secrets)."""
    if not address.strip():
        raise ApiError("VALIDATION_ERROR", "address is required", "address")
    try:
        result = geocode_address(address)
    except GeocodeNotFound:
        raise ApiError("NOT_FOUND", "Address could not be located", "address")
    except GeocodingUnavailable:
        raise ApiError("SERVER_ERROR",
                       "Address lookup is temporarily unavailable; use city, state, or ZIP instead",
                       "address")
    return ok(result.as_dict())


@router.get("/listings/{listing_id}/availability")
def listing_availability(listing_id: int, check_in: date | None = None,
                         check_out: date | None = None, nights: int | None = None,
                         duration: int | None = None,
                         check_in_time: time | None = None,
                         check_out_time: time | None = None, guests: int = 1,
                         store=Depends(get_store)):
    nights = _duration_alias(nights, duration)
    query = _parse_search(check_in=check_in, check_out=check_out, nights=nights,
                          check_in_time=check_in_time, check_out_time=check_out_time,
                          guests=guests)
    listing = ListingService(store).detail(listing_id)
    return ok(ListingService(store).availability(
        listing, check_in=query.check_in, check_out=query.check_out,
        nights=query.nights, check_in_time=query.check_in_time,
        check_out_time=query.check_out_time, guests=query.guests))


@router.get("/listings/{listing_id}")
def get_listing(listing_id: int, check_in: date | None = None,
                check_out: date | None = None, nights: int | None = None,
                duration: int | None = None,
                check_in_time: time | None = None, check_out_time: time | None = None,
                guests: int = 1, store=Depends(get_store)):
    service = ListingService(store)
    listing = service.detail(listing_id)
    nights = _duration_alias(nights, duration)
    if any(value is not None for value in (check_in, check_out, nights,
                                           check_in_time, check_out_time)):
        query = _parse_search(check_in=check_in, check_out=check_out, nights=nights,
                              check_in_time=check_in_time, check_out_time=check_out_time,
                              guests=guests)
        availability = service.availability(
            listing, check_in=query.check_in, check_out=query.check_out,
            nights=query.nights, check_in_time=query.check_in_time,
            check_out_time=query.check_out_time, guests=query.guests)
        requested_nights = availability.get("nights")
    else:
        availability = service.availability(listing)
        requested_nights = None
    return ok(listing_out(listing, store, date.today(), nights=requested_nights,
                           availability=availability))


@router.post("/listings")
def create_listing(body: ListingIn, user=Depends(get_current_user),
                   store=Depends(get_store)):
    listing = ListingService(store).create(user, body.model_dump())
    return ok(listing_out(listing, store, date.today()))


@router.put("/listings/{listing_id}")
def update_listing(listing_id: int, body: ListingIn,
                   user=Depends(get_current_user), store=Depends(get_store)):
    listing = ListingService(store).update(user, listing_id, body.model_dump())
    flush_store(store)
    return ok(listing_out(listing, store, date.today()))


@router.delete("/listings/{listing_id}")
def delete_listing(listing_id: int, user=Depends(get_current_user),
                   store=Depends(get_store)):
    listing = ListingService(store).remove(user, listing_id)
    flush_store(store)
    return ok({"id": listing.id, "status": listing.status.value})


@router.get("/host/listings")
def my_listings(user=Depends(get_current_user), store=Depends(get_store)):
    return ok([listing_out(listing, store, date.today())
               for listing in ListingService(store).by_host(user)])
