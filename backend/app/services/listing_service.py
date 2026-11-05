"""Listing use-cases: host CRUD, moderation, availability and search.

Business rules live here once; routers only validate transport shapes.
Search composes the domain's frozen rules (approval, capacity, operating
times, booking overlap) with the geocoding provider boundary.

Pattern: Service Layer with injected Strategies (price tier, validator, geocoder) and Memento history.
"""
from datetime import date, time

from ..core.errors import ApiError
from ..domain import Listing, User, UserRole, listing_state_for
from ..events import EVENTS, ListingModerated
from ..factories import ListingFactory
from ..listing_history import LISTING_HISTORY
from ..geocoding import GeocodingError, geocode_address
from .availability import evaluate_availability
from .listing_search import ListingSearch, SearchOutcome
from .listing_validation import ListingValidator
from .pricing import DEFAULT_PRICE_TIER, PriceTierStrategy
from .stay_window import resolve_stay_window


class ListingService:
    def __init__(self, store, *, price_tier: PriceTierStrategy = DEFAULT_PRICE_TIER,
                 validator: ListingValidator | None = None, geocode=None, events=None, history=None):
        self.store = store
        self.history = history or LISTING_HISTORY
        self.events = events or EVENTS
        self._geocode_override = geocode
        self._price_tier = price_tier
        self._validator = validator or ListingValidator()

    def _geocode(self, query: str):
        """Resolve at call time so the provider boundary stays swappable/patchable."""
        return (self._geocode_override or geocode_address)(query)

    # -- lookups / guards -------------------------------------------------
    def _find(self, listing_id: int) -> Listing:
        listing = next((l for l in self.store.listings if l.id == listing_id), None)
        if not listing:
            raise ApiError.not_found("Listing not found")
        return listing

    def _require_host(self, user: User) -> None:
        if user.role != UserRole.HOST:
            raise ApiError("FORBIDDEN", "Only hosts can create or manage listings")

    def _require_owner(self, user: User, listing: Listing, action: str) -> None:
        self._require_host(user)
        if listing.host_id != user.id:
            raise ApiError("FORBIDDEN", f"Only the listing owner can {action} it")

    def _ensure_coordinates(self, payload: dict) -> None:
        """Geocode the address when the host did not supply coordinates."""
        if payload.get("lat") is not None and payload.get("lng") is not None:
            return
        query = ", ".join(part for part in (
            payload.get("address"), payload.get("city"), payload.get("state"),
            payload.get("zip"),
        ) if part)
        try:
            resolved = self._geocode(query)
        except GeocodingError:
            raise ApiError(
                "VALIDATION_ERROR",
                "Coordinates are required because the address could not be geocoded; "
                "provide latitude and longitude or check the address",
                "lat",
            )
        payload["lat"], payload["lng"] = resolved.lat, resolved.lng
        if not payload.get("city") and resolved.city:
            payload["city"] = resolved.city
        if not payload.get("state") and resolved.state:
            payload["state"] = resolved.state
        if not payload.get("zip") and resolved.zip:
            payload["zip"] = resolved.zip

    # -- host CRUD ---------------------------------------------------------
    def create(self, host: User, data: dict) -> Listing:
        self._require_host(host)
        payload = self._validator.validate(data)
        self._ensure_coordinates(payload)
        return self.store.save(ListingFactory.create(self.store.listings, host.id, payload))

    def update(self, host: User, listing_id: int, data: dict) -> Listing:
        listing = self._find(listing_id)
        self._require_owner(host, listing, "edit")
        state = listing_state_for(listing.status)
        if not state.editable:
            raise ApiError("CONFLICT", "Removed listings cannot be edited")
        payload = self._validator.validate(data)
        unchanged_location = (
            payload.get("address") == listing.address
            and payload.get("city") == listing.city
            and payload.get("state") == listing.state
            and payload.get("zip") == listing.zip
        )
        if (payload.get("lat") is None and payload.get("lng") is None
                and unchanged_location):
            # Description/price/media edits keep the existing coordinates.
            payload["lat"], payload["lng"] = listing.lat, listing.lng
        else:
            self._ensure_coordinates(payload)
        self.history.save(listing)
        for key, value in payload.items():
            setattr(listing, key, value)
        # A material edit must be re-moderated (requirement 4.2).
        listing.status = state.after_edit()
        return listing

    def undo_last_edit(self, host: User, listing_id: int) -> Listing:
        listing = self._find(listing_id)
        self._require_owner(host, listing, "undo edits to")
        if not self.history.undo(listing):
            raise ApiError("CONFLICT", "There is no earlier version to restore")
        return listing

    def remove(self, host: User, listing_id: int) -> Listing:
        listing = self._find(listing_id)
        self._require_owner(host, listing, "remove")
        listing.status = listing_state_for(listing.status).after_removal()
        return listing

    def by_host(self, host: User) -> list[Listing]:
        self._require_host(host)
        return self.store.by_host(host.id)

    def detail(self, listing_id: int) -> Listing:
        return self._find(listing_id)

    def approve(self, admin: User, listing_id: int, approve: bool) -> Listing:
        if admin.role != UserRole.ADMIN:
            raise ApiError("FORBIDDEN", "Admin only")
        listing = self._find(listing_id)
        state = listing_state_for(listing.status)
        if not state.moderatable:
            # REMOVED is terminal: a moderator must not silently resurrect a
            # listing that was taken down for inaccuracy.
            raise ApiError("CONFLICT", "Removed listings cannot be approved or rejected")
        listing.status = state.after_moderation(approve)
        self.events.publish(ListingModerated(listing.id, listing.host_id, listing.status.value))
        return listing

    def remove_by_admin(self, admin: User, listing_id: int) -> Listing:
        if admin.role != UserRole.ADMIN:
            raise ApiError("FORBIDDEN", "Admin only")
        listing = self._find(listing_id)
        listing.status = listing_state_for(listing.status).after_removal()
        return listing

    # -- reviews -----------------------------------------------------------
    def review_summary(self, listing_id: int) -> dict:
        reviews = sorted((r for r in self.store.reviews if r.listing_id == listing_id),
                         key=lambda r: r.id, reverse=True)
        names = {u.id: u.full_name for u in self.store.users}
        average = round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else None
        return {
            "average_rating": average,
            "review_count": len(reviews),
            "reviews": [{
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                "customer_id": r.customer_id,
                "customer_name": names.get(r.customer_id),
            } for r in reviews],
        }

    # -- availability ------------------------------------------------------
    def availability(self, listing: Listing, *, check_in: date | None = None,
                     check_out: date | None = None, nights: int | None = None,
                     check_in_time: time | None = None,
                     check_out_time: time | None = None, guests: int = 1) -> dict:
        window = resolve_stay_window(check_in, check_out, nights, check_in_time,
                                     check_out_time)
        return evaluate_availability(
            listing, self.store.bookings, check_in=window.check_in,
            check_out=window.check_out, nights=window.nights,
            check_in_time=check_in_time, check_out_time=check_out_time, guests=guests)

    # -- search ------------------------------------------------------------
    def search(self, **criteria) -> SearchOutcome:
        return ListingSearch(self.store, self._geocode, self.availability).run(**criteria)

    def price_tier(self, listing: Listing) -> str:
        return self._price_tier.tier(listing.price_per_night)
