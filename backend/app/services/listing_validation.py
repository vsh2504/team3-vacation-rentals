"""Host listing validation as a Chain of Responsibility.

Every rule is a small handler that normalizes/validates one concern of the
payload and records problems in a shared :class:`ValidationErrors`. Rules are
linked in order by :func:`build_chain`, so a new rule is added by writing a
class and listing it - existing rules never change (Open/Closed).
"""
from __future__ import annotations

import re
from dataclasses import fields as dataclass_fields
from decimal import Decimal, InvalidOperation
from datetime import time

from ..core.errors import ApiError
from ..domain import Listing, _time_in_window
from ..geocoding import normalize_state_code

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ZIP_RE = re.compile(r"^\d{5}(?:-\d{4})?$")
_LISTING_FIELDS = {f.name for f in dataclass_fields(Listing)} - {"id", "host_id", "status"}
_TEXT_FIELDS = ("title", "description", "address", "city", "state", "zip",
                "host_contact_name", "host_contact_email", "host_contact_phone",
                "available_times")
_REQUIRED_FIELDS = ("title", "description", "address", "city", "state", "zip")


class ValidationErrors:
    """Ordered ``(field, message)`` collector that raises one ``ApiError``."""

    def __init__(self) -> None:
        self._items: list[tuple[str, str]] = []

    def add(self, field: str, message: str) -> None:
        self._items.append((field, message))

    def raise_if_any(self) -> None:
        if self._items:
            field = next((name for name, _ in self._items if name), None)
            raise ApiError("VALIDATION_ERROR", "; ".join(m for _, m in self._items), field)


class ListingRule:
    """Chain handler: ``apply`` does the work, ``handle`` forwards to the next."""

    def __init__(self) -> None:
        self._next: ListingRule | None = None

    def then(self, following: "ListingRule") -> "ListingRule":
        self._next = following
        return following

    def apply(self, payload: dict, errors: ValidationErrors) -> None:
        raise NotImplementedError  # pragma: no cover - abstract

    def handle(self, payload: dict, errors: ValidationErrors) -> None:
        self.apply(payload, errors)
        if self._next is not None:
            self._next.handle(payload, errors)


def build_chain(rules) -> ListingRule:
    rules = list(rules)
    for current, following in zip(rules, rules[1:]):
        current.then(following)
    return rules[0]


# -- rules --------------------------------------------------------------------
class NormalizeText(ListingRule):
    def apply(self, payload, errors):
        for key in _TEXT_FIELDS:
            if isinstance(payload.get(key), str):
                payload[key] = " ".join(payload[key].split()).strip()


class RequiredText(ListingRule):
    def apply(self, payload, errors):
        for key in _REQUIRED_FIELDS:
            if not payload.get(key):
                errors.add(key, f"{key} is required")


class AvailableTimesText(ListingRule):
    """May be omitted (the dataclass supplies a default) but not explicitly blank."""

    def apply(self, payload, errors):
        if "available_times" in payload and not payload.get("available_times"):
            errors.add("available_times", "available_times is required")


class StateCode(ListingRule):
    def apply(self, payload, errors):
        if payload.get("state"):
            payload["state"] = normalize_state_code(payload["state"])
            if len(payload["state"]) != 2:
                errors.add("state", "state must be a two-letter code (for example CA)")


class ZipCode(ListingRule):
    def apply(self, payload, errors):
        if payload.get("zip"):
            payload["zip"] = str(payload["zip"]).strip()
            if not _ZIP_RE.fullmatch(payload["zip"]):
                errors.add("zip", "zip must be a 5-digit ZIP code, optionally followed by -1234")


class NightlyPrice(ListingRule):
    def apply(self, payload, errors):
        try:
            payload["price_per_night"] = Decimal(str(payload["price_per_night"]))
            if payload["price_per_night"] <= 0:
                errors.add("price_per_night", "price_per_night must be greater than 0")
        except (KeyError, InvalidOperation, TypeError, ValueError):
            errors.add("price_per_night", "price_per_night must be a positive number")


class RoomCounts(ListingRule):
    def apply(self, payload, errors):
        for key in ("max_guests", "bedrooms", "bathrooms"):
            try:
                payload[key] = int(payload[key])
            except (KeyError, TypeError, ValueError):
                errors.add(key, f"{key} must be a whole number")
                continue
            if key == "max_guests" and payload[key] < 1:
                errors.add(key, "max_guests must be at least 1")
            if key != "max_guests" and payload[key] < 0:
                errors.add(key, f"{key} cannot be negative")


class Coordinates(ListingRule):
    _BOUNDS = (("lat", -90, 90, "latitude"), ("lng", -180, 180, "longitude"))

    def apply(self, payload, errors):
        for key, low, high, label in self._BOUNDS:
            value = payload.get(key)
            if value is None:
                continue
            try:
                payload[key] = float(value)
            except (TypeError, ValueError):
                errors.add(key, f"{label} must be a number")
                continue
            if not low <= payload[key] <= high:
                errors.add(key, f"{label} must be between {low} and {high}")
        if (payload.get("lat") is None) != (payload.get("lng") is None):
            errors.add("lat", "lat and lng must be provided together")


class OperatingHours(ListingRule):
    def apply(self, payload, errors):
        start = payload.get("operating_start_time") or time(0, 0)
        end = payload.get("operating_end_time") or time(23, 59)
        check_in = payload.get("check_in_time") or time(15, 0)
        check_out = payload.get("check_out_time") or time(11, 0)
        if start == end:
            errors.add("operating_end_time",
                       "operating_start_time and operating_end_time must differ")
            return
        if not _time_in_window(check_in, start, end):
            errors.add("check_in_time", "check_in_time must fall within the operating hours")
        if not _time_in_window(check_out, start, end):
            errors.add("check_out_time", "check_out_time must fall within the operating hours")


class Amenities(ListingRule):
    def apply(self, payload, errors):
        amenities = payload.get("amenities", [])
        if not isinstance(amenities, list) or not all(isinstance(a, str) for a in amenities):
            errors.add("amenities", "amenities must be a list of text values")
        else:
            payload["amenities"] = [a.strip() for a in amenities if a.strip()]


class MediaUrls(ListingRule):
    @staticmethod
    def _valid_url(value) -> bool:
        return isinstance(value, str) and value.startswith(("https://", "http://", "/"))

    def apply(self, payload, errors):
        for key in ("photos", "videos"):
            values = payload.get(key, [])
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                errors.add(key, f"{key} must be a list of media URLs")
            elif not all(self._valid_url(v) for v in values):
                errors.add(key, f"{key} entries must be http(s) URLs or site-relative paths")


class ContactDetails(ListingRule):
    def apply(self, payload, errors):
        email = payload.get("host_contact_email")
        if email and not _EMAIL_RE.fullmatch(email):
            errors.add("host_contact_email", "host_contact_email must be a valid email address")
        phone = payload.get("host_contact_phone")
        if phone and not 7 <= len(re.sub(r"\D", "", phone)) <= 15:
            errors.add("host_contact_phone", "host_contact_phone must contain 7 to 15 digits")


def default_rules() -> list[ListingRule]:
    """Fresh rule instances (a rule holds its ``next`` link, so chains don't share them)."""
    return [NormalizeText(), RequiredText(), AvailableTimesText(), StateCode(), ZipCode(),
            NightlyPrice(), RoomCounts(), Coordinates(), OperatingHours(), Amenities(),
            MediaUrls(), ContactDetails()]


class ListingValidator:
    """Run a rule chain over a host payload and return the normalized copy."""

    def __init__(self, rules=None):
        self._head = build_chain(rules if rules is not None else default_rules())

    def validate(self, data: dict | None) -> dict:
        payload = {key: value for key, value in (data or {}).items()
                   if key in _LISTING_FIELDS}
        errors = ValidationErrors()
        self._head.handle(payload, errors)
        errors.raise_if_any()
        return payload
