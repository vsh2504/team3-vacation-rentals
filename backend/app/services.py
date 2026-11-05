"""Service layer — business rules live here, in exactly one place each.
Routers do Pydantic validation -> service call -> JSON. No rule in React.

Listing search composes the domain's frozen rules (approval, capacity,
operating times, booking overlap) with the geocoding provider boundary, so
the API can filter by city/state/ZIP/address without duplicating them.
"""
import os
import re
from dataclasses import dataclass, field, fields as dataclass_fields
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation

from .core.errors import ApiError
from .core.security import check_password, hash_password, make_token
from .domain import (Booking, BookingStatus, Listing, ListingStatus, Review,
                     User, UserRole, _time_in_window, analytics_by_zip,
                     can_cancel, can_review, is_available, price_for,
                     search_listings, validate_stay)
from .geocoding import (GeocodeResult, GeocodingError, distance_km,
                        geocode_address, normalize_state_code)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ZIP_RE = re.compile(r"^\d{5}(?:-\d{4})?$")
_LISTING_FIELDS = {f.name for f in dataclass_fields(Listing)} - {"id", "host_id", "status"}


@dataclass
class SearchOutcome:
    """Search results plus the requested-window context the router serializes."""

    listings: list[Listing]
    nights: int | None = None
    geocoded: GeocodeResult | None = None
    distance_by_id: dict[int, float] = field(default_factory=dict)


_ROLE_NAVIGATION: dict[UserRole, tuple[dict, ...]] = {
    UserRole.CUSTOMER: (
        {"key": "search", "label": "Search stays", "path": "/"},
        {"key": "bookings", "label": "My bookings", "path": "/bookings"},
    ),
    UserRole.HOST: (
        {"key": "search", "label": "Search stays", "path": "/"},
        {"key": "listings", "label": "My listings", "path": "/host"},
        {"key": "bookings", "label": "My bookings", "path": "/bookings"},
        {"key": "analytics", "label": "Analytics", "path": "/analytics"},
    ),
    UserRole.ADMIN: (
        {"key": "search", "label": "Search stays", "path": "/"},
        {"key": "moderation", "label": "Approvals queue", "path": "/admin"},
        {"key": "analytics", "label": "Platform analytics", "path": "/analytics"},
    ),
}


def navigation_for(role: UserRole | str) -> list[dict]:
    """Role-appropriate navigation returned with an authenticated session.

    The frontend may render its own links, but this keeps the session
    response self-describing and makes the role contract testable.
    """
    role = role if isinstance(role, UserRole) else UserRole(role)
    return [dict(item) for item in _ROLE_NAVIGATION.get(role, ())]


def user_public(user: User) -> dict:
    """Serialize a persisted user for /auth responses (never a password hash)."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "navigation": navigation_for(user.role),
    }


def _price_tier(price: Decimal | float | str) -> str:
    try:
        value = Decimal(str(price))
    except (InvalidOperation, ValueError):
        return "$"
    if value <= Decimal("100"):
        return "$"
    if value <= Decimal("200"):
        return "$$"
    return "$$$"


class ListingService:
    def __init__(self, store):
        self.store = store

    # -- lookups / guards -------------------------------------------------
    def _find(self, listing_id: int) -> Listing:
        listing = next((l for l in self.store.listings if l.id == listing_id), None)
        if not listing:
            raise ApiError("NOT_FOUND", "Listing not found")
        return listing

    def _next_id(self) -> int:
        return max((l.id for l in self.store.listings), default=0) + 1

    def _require_host(self, user: User, action: str = "manage listings") -> None:
        if user.role != UserRole.HOST:
            raise ApiError("FORBIDDEN", "Only hosts can create or manage listings")

    def _require_owner(self, user: User, listing: Listing, action: str) -> None:
        self._require_host(user, action)
        if listing.host_id != user.id:
            raise ApiError("FORBIDDEN", f"Only the listing owner can {action} it")

    @staticmethod
    def completeness(listing: Listing) -> dict:
        """Describe how complete a listing is for administrator moderation.

        The queue needs enough evidence to assess accuracy before approving,
        so this reports the individual checks as well as a percentage score.
        Media may be photos or videos (requirement 1.3); contact information
        may be any of name, email, or phone.
        """
        photos = list(getattr(listing, "photos", None) or [])
        videos = list(getattr(listing, "videos", None) or [])
        contact = any(
            str(value or "").strip()
            for value in (listing.host_contact_name, listing.host_contact_email,
                          listing.host_contact_phone)
        )
        checks = {
            "title": bool(str(listing.title or "").strip()),
            "description": bool(str(listing.description or "").strip()),
            "address": bool(str(listing.address or "").strip()),
            "city": bool(str(listing.city or "").strip()),
            "state": bool(str(listing.state or "").strip()),
            "zip": bool(str(listing.zip or "").strip()),
            "coordinates": listing.lat is not None and listing.lng is not None,
            "price_per_night": bool(listing.price_per_night and listing.price_per_night > 0),
            "max_guests": bool(listing.max_guests and listing.max_guests >= 1),
            "amenities": bool(listing.amenities),
            "available_times": bool(str(listing.available_times or "").strip()),
            "operating_hours": listing.operating_start_time != listing.operating_end_time,
            "contact": contact,
            "media": bool(photos or videos),
        }
        missing = [name for name, present in checks.items() if not present]
        return {
            "complete": not missing,
            "score": round(100 * (len(checks) - len(missing)) / len(checks)),
            "missing": missing,
            "checks": checks,
            "photo_count": len(photos),
            "video_count": len(videos),
            "has_photos": bool(photos),
            "has_videos": bool(videos),
        }

    # -- validation --------------------------------------------------------
    @staticmethod
    def _validation_error(errors: list[tuple[str, str]]) -> None:
        if errors:
            field = next((name for name, _ in errors if name), None)
            raise ApiError("VALIDATION_ERROR", "; ".join(message for _, message in errors), field)

    @staticmethod
    def _valid_media_url(value) -> bool:
        return (isinstance(value, str)
                and (value.startswith("https://") or value.startswith("http://")
                     or value.startswith("/")))

    def _validate_listing(self, data: dict) -> dict:
        """Normalize and validate a host payload before persistence."""
        payload = {key: value for key, value in (data or {}).items()
                   if key in _LISTING_FIELDS}
        for key in ("title", "description", "address", "city", "state", "zip",
                    "host_contact_name", "host_contact_email", "host_contact_phone",
                    "available_times"):
            if isinstance(payload.get(key), str):
                payload[key] = " ".join(payload[key].split()).strip()

        errors: list[tuple[str, str]] = []
        for key, label in (
            ("title", "title"), ("description", "description"), ("address", "address"),
            ("city", "city"), ("state", "state"), ("zip", "zip"),
        ):
            if not payload.get(key):
                errors.append((key, f"{label} is required"))

        # ``available_times`` may be omitted (the Listing dataclass supplies a
        # default), but an explicitly blank value is not meaningful.
        if "available_times" in payload and not payload.get("available_times"):
            errors.append(("available_times", "available_times is required"))

        if payload.get("state"):
            payload["state"] = normalize_state_code(payload["state"])
            if len(payload["state"]) != 2:
                errors.append(("state", "state must be a two-letter code (for example CA)"))

        if payload.get("zip"):
            payload["zip"] = str(payload["zip"]).strip()
            if not _ZIP_RE.fullmatch(payload["zip"]):
                errors.append(("zip", "zip must be a 5-digit ZIP code, optionally followed by -1234"))

        try:
            payload["price_per_night"] = Decimal(str(payload["price_per_night"]))
            if payload["price_per_night"] <= 0:
                errors.append(("price_per_night", "price_per_night must be greater than 0"))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            errors.append(("price_per_night", "price_per_night must be a positive number"))

        for key, label in (("max_guests", "max_guests"), ("bedrooms", "bedrooms"),
                           ("bathrooms", "bathrooms")):
            try:
                payload[key] = int(payload[key])
            except (KeyError, TypeError, ValueError):
                errors.append((key, f"{label} must be a whole number"))
                continue
            if key == "max_guests" and payload[key] < 1:
                errors.append((key, "max_guests must be at least 1"))
            if key != "max_guests" and payload[key] < 0:
                errors.append((key, f"{label} cannot be negative"))

        for key, low, high, label in (("lat", -90, 90, "latitude"),
                                      ("lng", -180, 180, "longitude")):
            value = payload.get(key)
            if value is None:
                continue
            try:
                payload[key] = float(value)
            except (TypeError, ValueError):
                errors.append((key, f"{label} must be a number"))
                continue
            if not low <= payload[key] <= high:
                errors.append((key, f"{label} must be between {low} and {high}"))
        if (payload.get("lat") is None) != (payload.get("lng") is None):
            errors.append(("lat", "lat and lng must be provided together"))

        start = payload.get("operating_start_time") or time(0, 0)
        end = payload.get("operating_end_time") or time(23, 59)
        check_in = payload.get("check_in_time") or time(15, 0)
        check_out = payload.get("check_out_time") or time(11, 0)
        if start == end:
            errors.append(("operating_end_time",
                           "operating_start_time and operating_end_time must differ"))
        else:
            if not _time_in_window(check_in, start, end):
                errors.append(("check_in_time",
                               "check_in_time must fall within the operating hours"))
            if not _time_in_window(check_out, start, end):
                errors.append(("check_out_time",
                               "check_out_time must fall within the operating hours"))

        amenities = payload.get("amenities", [])
        if not isinstance(amenities, list) or not all(isinstance(a, str) for a in amenities):
            errors.append(("amenities", "amenities must be a list of text values"))
        else:
            payload["amenities"] = [a.strip() for a in amenities if a.strip()]

        for key in ("photos", "videos"):
            values = payload.get(key, [])
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                errors.append((key, f"{key} must be a list of media URLs"))
            elif any(not self._valid_media_url(v) for v in values):
                errors.append((key, f"{key} entries must be http(s) URLs or site-relative paths"))

        contact_email = payload.get("host_contact_email")
        if contact_email and not _EMAIL_RE.fullmatch(contact_email):
            errors.append(("host_contact_email", "host_contact_email must be a valid email address"))
        phone = payload.get("host_contact_phone")
        if phone and not 7 <= len(re.sub(r"\D", "", phone)) <= 15:
            errors.append(("host_contact_phone", "host_contact_phone must contain 7 to 15 digits"))

        self._validation_error(errors)
        return payload

    def _ensure_coordinates(self, payload: dict, fallback: tuple[float, float] | None = None) -> None:
        """Geocode the address when the host did not supply coordinates."""
        if payload.get("lat") is not None and payload.get("lng") is not None:
            return
        query = ", ".join(part for part in (
            payload.get("address"), payload.get("city"), payload.get("state"),
            payload.get("zip"),
        ) if part)
        try:
            resolved = geocode_address(query)
        except GeocodingError:
            if fallback is not None:
                payload["lat"], payload["lng"] = fallback
                return
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
        payload = self._validate_listing(data)
        self._ensure_coordinates(payload)
        listing = Listing(id=self._next_id(), host_id=host.id,
                          status=ListingStatus.PENDING_APPROVAL, **payload)
        return self.store.save(listing)

    def update(self, host: User, listing_id: int, data: dict) -> Listing:
        listing = self._find(listing_id)
        self._require_owner(host, listing, "edit")
        if listing.status == ListingStatus.REMOVED:
            raise ApiError("CONFLICT", "Removed listings cannot be edited")
        payload = self._validate_listing(data)
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
            self._ensure_coordinates(
                payload,
                fallback=(listing.lat, listing.lng) if unchanged_location else None,
            )
        for key, value in payload.items():
            setattr(listing, key, value)
        # A material edit must be re-moderated (requirement 4.2).
        listing.status = ListingStatus.PENDING_APPROVAL
        return listing

    def remove(self, host: User, listing_id: int) -> Listing:
        listing = self._find(listing_id)
        self._require_owner(host, listing, "remove")
        listing.status = ListingStatus.REMOVED
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
        if listing.status == ListingStatus.REMOVED:
            # REMOVED is terminal: a moderator must not silently resurrect a
            # listing that was taken down for inaccuracy.
            raise ApiError("CONFLICT", "Removed listings cannot be approved or rejected")
        listing.status = ListingStatus.APPROVED if approve else ListingStatus.REJECTED
        return listing

    def remove_by_admin(self, admin: User, listing_id: int) -> Listing:
        if admin.role != UserRole.ADMIN:
            raise ApiError("FORBIDDEN", "Admin only")
        listing = self._find(listing_id)
        listing.status = ListingStatus.REMOVED
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

    # -- stay-window validation / availability -----------------------------
    def _resolve_stay_window(self, check_in: date | None, check_out: date | None,
                             nights: int | None, check_in_time: time | None,
                             check_out_time: time | None):
        if check_in is None and check_out is None and nights is None:
            if check_in_time is not None or check_out_time is not None:
                raise ApiError("VALIDATION_ERROR",
                               "dates are required when booking times are provided",
                               "check_in")
            return None, None, None

        if nights is not None:
            try:
                nights = int(nights)
            except (TypeError, ValueError):
                raise ApiError("VALIDATION_ERROR", "duration must be a whole number of nights", "nights")
            if nights < 1:
                raise ApiError("VALIDATION_ERROR", "duration must be at least 1 night", "nights")
            if nights > 14:
                raise ApiError("VALIDATION_ERROR", "Stay cannot exceed 14 nights", "nights")
            if check_in is None:
                raise ApiError("VALIDATION_ERROR",
                               "check_in is required when a duration is provided", "check_in")
            derived_out = check_in + timedelta(days=nights)
            if check_out is None:
                check_out = derived_out
            elif check_out != derived_out:
                raise ApiError("VALIDATION_ERROR",
                               "check_out must equal check_in plus the requested duration",
                               "check_out")

        if (check_in is None) != (check_out is None):
            raise ApiError("VALIDATION_ERROR",
                           "check_in and check_out must be provided together", "check_out")
        if check_in is not None and check_out is not None:
            stay_nights = (check_out - check_in).days
            if stay_nights <= 0:
                raise ApiError("VALIDATION_ERROR", "check_out must be after check_in", "check_out")
            if stay_nights > 14:
                raise ApiError("VALIDATION_ERROR", "Stay cannot exceed 14 nights", "check_out")
            if nights is not None and stay_nights != nights:
                raise ApiError("VALIDATION_ERROR",
                               "check_out must equal check_in plus the requested duration",
                               "check_out")
            nights = stay_nights

        if (check_in_time is None) != (check_out_time is None):
            raise ApiError("VALIDATION_ERROR",
                           "check_in_time and check_out_time must be provided together",
                           "check_in_time")
        return check_in, check_out, nights

    def availability(self, listing: Listing, *, check_in: date | None = None,
                     check_out: date | None = None, nights: int | None = None,
                     check_in_time: time | None = None,
                     check_out_time: time | None = None, guests: int = 1) -> dict:
        check_in, check_out, nights = self._resolve_stay_window(
            check_in, check_out, nights, check_in_time, check_out_time)
        try:
            guests = int(guests)
        except (TypeError, ValueError):
            guests = 0
        if guests < 1:
            return {"requested": check_in is not None, "available": False,
                    "reason": "guests must be at least 1", "nights": nights,
                    "total_cost": None, "failure": "validation"}

        if check_in is None:
            approved = listing.status == ListingStatus.APPROVED
            return {"requested": False, "available": approved,
                    "reason": None if approved else "Listing is not approved",
                    "nights": None, "total_cost": None,
                    "failure": None if approved else "approval"}

        total = str(price_for(listing, check_in, check_out))
        errors = validate_stay(check_in, check_out, guests, listing.max_guests)
        if errors:
            return {"requested": True, "available": False, "reason": "; ".join(errors),
                    "nights": nights, "total_cost": total, "failure": "validation"}
        if listing.status != ListingStatus.APPROVED:
            return {"requested": True, "available": False,
                    "reason": "Listing is not approved", "nights": nights,
                    "total_cost": total, "failure": "approval"}

        requested_in = check_in_time or listing.check_in_time
        requested_out = check_out_time or listing.check_out_time
        if not _time_in_window(requested_in, listing.operating_start_time,
                               listing.operating_end_time):
            reason = "Requested check-in time is outside the listing's operating hours"
            failure = "time"
        elif not _time_in_window(requested_out, listing.operating_start_time,
                                 listing.operating_end_time):
            reason = "Requested check-out time is outside the listing's operating hours"
            failure = "time"
        elif not is_available(listing, check_in, check_out, guests, self.store.bookings,
                              check_in_time=check_in_time, check_out_time=check_out_time):
            reason = "Listing is already booked for the requested period"
            failure = "overlap"
        else:
            reason = None
            failure = None
        return {"requested": True, "available": reason is None, "reason": reason,
                "nights": nights, "total_cost": total, "failure": failure}

    # -- search ------------------------------------------------------------
    def search(self, *, check_in: date | None = None, check_out: date | None = None,
               nights: int | None = None, check_in_time: time | None = None,
               check_out_time: time | None = None, guests: int = 1,
               city: str | None = None, state: str | None = None,
               zip_code: str | None = None, address: str | None = None,
               radius_km: float | None = None,
               include_unavailable: bool = False) -> SearchOutcome:
        try:
            guests = int(guests)
        except (TypeError, ValueError):
            raise ApiError("VALIDATION_ERROR", "guests must be a whole number", "guests")
        if guests < 1:
            raise ApiError("VALIDATION_ERROR", "guests must be at least 1", "guests")

        check_in, check_out, nights = self._resolve_stay_window(
            check_in, check_out, nights, check_in_time, check_out_time)

        city_filter = " ".join(city.split()).strip() if city else None
        state_filter = normalize_state_code(state) if state else None
        zip_filter = " ".join(zip_code.split()).strip() if zip_code else None
        address_text = " ".join(address.split()).strip() if address else None

        geocoded = None
        geocoding_failed = False
        radius: float | None = None
        if radius_km is not None:
            try:
                radius = float(radius_km)
            except (TypeError, ValueError):
                raise ApiError("VALIDATION_ERROR", "radius_km must be a number", "radius_km")
            if radius <= 0:
                raise ApiError("VALIDATION_ERROR", "radius_km must be greater than 0", "radius_km")
        if address_text:
            try:
                geocoded = geocode_address(address_text)
            except GeocodingError:
                # Offline/unknown address: keep the search useful by falling
                # back to a textual address/city/ZIP match below.
                geocoding_failed = True

        # When the address resolved, radius proximity is more accurate than a
        # loose substring match. When it did not, retain the Week 1 text filter.
        text_address = address_text if geocoding_failed else None
        results = search_listings(
            self.store.listings, self.store.bookings, guests=guests,
            city=city_filter, state=state_filter, zip_code=zip_filter,
            address=text_address)
        if check_in is not None and not include_unavailable:
            # Search and booking deliberately converge here: both make their
            # final decision through ``availability`` rather than maintaining
            # parallel date/time/capacity/approval/overlap rules.
            results = [listing for listing in results if self.availability(
                listing, check_in=check_in, check_out=check_out, nights=nights,
                check_in_time=check_in_time, check_out_time=check_out_time,
                guests=guests)["available"]]

        distances: dict[int, float] = {}
        if geocoded is not None:
            effective_radius = radius if radius is not None else float(
                os.environ.get("STAYNEST_SEARCH_RADIUS_KM", "80"))
            # Keep exact textual matches even when a provider resolves the
            # address to a slightly different point (fictional demo streets,
            # for example); otherwise apply the proximity radius.
            text_match_ids = set()
            if address_text:
                needle = address_text.lower()
                text_match_ids = {
                    listing.id for listing in results
                    if needle in (f"{listing.address} {listing.city} "
                                  f"{listing.state} {listing.zip}").lower()
                }
            nearby = []
            for listing in results:
                distance = distance_km(geocoded.lat, geocoded.lng, listing.lat, listing.lng)
                if distance <= effective_radius or listing.id in text_match_ids:
                    distances[listing.id] = round(distance, 1)
                    nearby.append(listing)
            nearby.sort(key=lambda l: distances.get(l.id, float("inf")))
            results = nearby

        return SearchOutcome(listings=results, nights=nights, geocoded=geocoded,
                             distance_by_id=distances)

    def price_tier(self, listing: Listing) -> str:
        return _price_tier(listing.price_per_night)


class AuthService:
    def __init__(self, store): self.store = store

    @staticmethod
    def _normalize_email(email) -> str:
        return " ".join(str(email or "").split()).lower()

    def _by_email(self, email: str) -> User | None:
        # Persisted emails may predate normalization, so compare normalized
        # values instead of relying on the store's exact-match lookup.
        return next((u for u in self.store.users
                     if self._normalize_email(u.email) == email), None)

    def register(self, email, password, full_name, role):
        try:
            role = role if isinstance(role, UserRole) else UserRole(str(role).strip().upper())
        except ValueError:
            raise ApiError("FORBIDDEN", "Admin accounts are seeded, not self-registered")
        if role not in (UserRole.CUSTOMER, UserRole.HOST):
            raise ApiError("FORBIDDEN", "Admin accounts are seeded, not self-registered")
        email = self._normalize_email(email)
        if not _EMAIL_RE.fullmatch(email):
            raise ApiError("VALIDATION_ERROR", "email must be a valid email address", "email")
        full_name = " ".join(str(full_name or "").split())
        if not full_name:
            raise ApiError("VALIDATION_ERROR", "full_name is required", "full_name")
        if not isinstance(password, str) or len(password) < 8:
            raise ApiError("VALIDATION_ERROR", "password must be at least 8 characters", "password")
        if self._by_email(email):
            raise ApiError("CONFLICT", "Email already registered", "email")
        # Use the highest existing id so registrations cannot collide with
        # seeded hosts or the seeded administrator in a persisted store.
        user = User(id=max((u.id for u in self.store.users), default=0) + 1,
                    email=email, password_hash=hash_password(password),
                    full_name=full_name, role=role)
        self.store.save(user)
        return user

    def login(self, email, password):
        email = self._normalize_email(email)
        user = self._by_email(email)
        if not user or not check_password(password, user.password_hash):
            raise ApiError("UNAUTHORIZED", "Invalid email or password")
        return {"access_token": make_token(user.id, user.role.value),
                "token_type": "bearer", "user": user_public(user),
                "role": user.role.value, "navigation": navigation_for(user.role)}

class BookingService:
    def __init__(self, store): self.store = store
    def book(self, customer: User, listing_id: int, check_in: date, check_out: date,
             guests: int, today: date, *, check_in_time: time | None = None,
             check_out_time: time | None = None) -> Booking:
        if customer.role != UserRole.CUSTOMER:
            raise ApiError("FORBIDDEN", "Only customers can book stays")
        li = next((l for l in self.store.listings if l.id == listing_id), None)
        if not li: raise ApiError("NOT_FOUND", "Listing not found")
        rules = ListingService(self.store).availability(
            li, check_in=check_in, check_out=check_out,
            check_in_time=check_in_time, check_out_time=check_out_time,
            guests=guests)
        if not rules["available"]:
            code = "VALIDATION_ERROR" if rules.get("failure") == "validation" else "CONFLICT"
            raise ApiError(code, rules["reason"] or "Listing is not available",
                           "check_out" if code == "VALIDATION_ERROR" else None)
        b = Booking(id=max((item.id for item in self.store.bookings), default=0) + 1,
                    listing_id=listing_id, customer_id=customer.id,
                    check_in=check_in, check_out=check_out, guests=guests,
                    check_in_time=check_in_time or li.check_in_time,
                    check_out_time=check_out_time or li.check_out_time,
                    total_price=price_for(li, check_in, check_out), booked_date=today,
                    location_name=li.title, location_address=li.address,
                    location_city=li.city, location_state=li.state,
                    location_zip=li.zip, location_lat=li.lat, location_lng=li.lng)
        # SqlBackedStore.save performs one INSERT transaction. PostgreSQL's
        # confirmed-booking exclusion constraint is the final race-safe guard;
        # an IntegrityError is translated by the store into a 409 ApiError.
        return self.store.save(b)
    def cancel(self, customer: User, booking_id: int) -> Booking:
        if customer.role != UserRole.CUSTOMER:
            raise ApiError("FORBIDDEN", "Only customers can cancel stays")
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b: raise ApiError("NOT_FOUND", "Booking not found")
        errors = can_cancel(b, customer.id)
        if errors: raise ApiError("FORBIDDEN" if "owner" in " ".join(errors) else "VALIDATION_ERROR", "; ".join(errors))
        b.status = BookingStatus.CANCELLED
        b.cancelled_at = datetime.now(timezone.utc)
        return b
    def complete(self, customer: User, booking_id: int, today: date) -> Booking:
        """Mark a CONFIRMED stay COMPLETED after check-out.
        This is what unlocks reviews (can_review requires COMPLETED).
        Demo path: book past dates, complete, then review."""
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b: raise ApiError("NOT_FOUND", "Booking not found")
        if b.customer_id != customer.id: raise ApiError("FORBIDDEN", "Only the booking owner can complete it")
        if b.status != BookingStatus.CONFIRMED: raise ApiError("VALIDATION_ERROR", "Only CONFIRMED bookings can be completed")
        if b.check_out > today: raise ApiError("VALIDATION_ERROR", "Stay has not ended yet (check_out is in the future)")
        b.status = BookingStatus.COMPLETED; return b

class ReviewService:
    def __init__(self, store): self.store = store
    def submit(self, customer: User, booking_id: int, rating: int, comment: str = "",
               today: date | None = None) -> Review:
        if customer.role != UserRole.CUSTOMER:
            raise ApiError("FORBIDDEN", "Only customers can review stays")
        if not (1 <= rating <= 5): raise ApiError("VALIDATION_ERROR", "rating must be 1-5", "rating")
        b = next((x for x in self.store.bookings if x.id == booking_id), None)
        if not b: raise ApiError("NOT_FOUND", "Booking not found")
        errors = can_review(b, customer.id, self.store.reviews)
        if b.check_out > (today or date.today()):
            errors.append("Reviews are allowed only after the stay has ended")
        if errors: raise ApiError("VALIDATION_ERROR", "; ".join(errors))
        return self.store.save(Review(id=max((item.id for item in self.store.reviews), default=0) + 1,
                                      booking_id=booking_id,
                                      listing_id=b.listing_id, customer_id=customer.id, rating=rating, comment=comment))

class AnalyticsService:
    def __init__(self, store): self.store = store
    def host_analytics(self, host: User, days: int, today: date, zip_code: str | None = None):
        if host.role != UserRole.HOST:
            raise ApiError("FORBIDDEN", "Host analytics are available to hosts only")
        return analytics_by_zip(self.store.bookings, self.store.listings, days=days,
                                today=today, host_id=host.id, zip_code=zip_code)
    def platform_analytics(self, admin: User, days: int, today: date, zip_code: str | None = None):
        if admin.role != UserRole.ADMIN: raise ApiError("FORBIDDEN", "Admin only")
        return analytics_by_zip(self.store.bookings, self.store.listings, days=days,
                                today=today, zip_code=zip_code)
