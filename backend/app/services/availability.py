"""Availability as a Chain of Responsibility.

Each check inspects an :class:`AvailabilityRequest` and either returns a
:class:`Verdict` (the request fails here) or passes it to the next handler.
New rules (for example a minimum-stay rule) are added by writing another
handler and inserting it in :func:`build_availability_chain`, without
modifying existing ones (Open/Closed).

Pattern: Chain of Responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from .chain import ChainLink
from ..domain import (Booking, Listing, ListingStatus, _time_in_window,
                      has_conflicting_booking, price_for, validate_stay)


@dataclass(frozen=True)
class AvailabilityRequest:
    listing: Listing
    check_in: date
    check_out: date
    nights: int | None
    check_in_time: time | None
    check_out_time: time | None
    guests: int
    bookings: list[Booking]

    @property
    def requested_in(self) -> time:
        return self.check_in_time or self.listing.check_in_time

    @property
    def requested_out(self) -> time:
        return self.check_out_time or self.listing.check_out_time


@dataclass(frozen=True)
class Verdict:
    failure: str            # "validation" | "approval" | "time" | "overlap"
    reason: str
    priced: bool = True     # whether a total cost can still be quoted


class AvailabilityCheck(ChainLink):
    """Base handler: ``check`` decides, ``handle`` walks the chain."""

    def check(self, request: AvailabilityRequest) -> Verdict | None:
        raise NotImplementedError  # pragma: no cover - abstract

    def handle(self, request: AvailabilityRequest) -> Verdict | None:
        for link in self:
            verdict = link.check(request)
            if verdict is not None:
                return verdict
        return None


class GuestCountCheck(AvailabilityCheck):
    def check(self, request):
        if request.guests < 1:
            return Verdict("validation", "guests must be at least 1", priced=False)
        return None


class StayRulesCheck(AvailabilityCheck):
    def check(self, request):
        errors = validate_stay(request.check_in, request.check_out, request.guests,
                               request.listing.max_guests)
        return Verdict("validation", "; ".join(errors)) if errors else None


class ApprovalCheck(AvailabilityCheck):
    def check(self, request):
        if request.listing.status != ListingStatus.APPROVED:
            return Verdict("approval", "Listing is not approved")
        return None


class OperatingHoursCheck(AvailabilityCheck):
    def check(self, request):
        listing = request.listing
        window = (listing.operating_start_time, listing.operating_end_time)
        if not _time_in_window(request.requested_in, *window):
            return Verdict("time", "Requested check-in time is outside the listing's operating hours")
        if not _time_in_window(request.requested_out, *window):
            return Verdict("time", "Requested check-out time is outside the listing's operating hours")
        return None


class OverlapCheck(AvailabilityCheck):
    def check(self, request):
        if has_conflicting_booking(request.listing.id, request.check_in, request.check_out,
                                   request.requested_in, request.requested_out,
                                   request.bookings):
            return Verdict("overlap", "Listing is already booked for the requested period")
        return None


def build_availability_chain() -> AvailabilityCheck:
    head = GuestCountCheck()
    head.then(StayRulesCheck()).then(ApprovalCheck()).then(OperatingHoursCheck()).then(OverlapCheck())
    return head


_CHAIN = build_availability_chain()


def evaluate_availability(listing: Listing, bookings: list[Booking], *,
                          check_in: date | None, check_out: date | None,
                          nights: int | None, check_in_time: time | None,
                          check_out_time: time | None, guests) -> dict:
    """Run the chain and shape the public availability payload."""
    try:
        guests = int(guests)
    except (TypeError, ValueError):
        guests = 0

    if check_in is None:  # no stay requested: only capacity input and approval matter
        request = AvailabilityRequest(listing, date.min, date.min, None, None, None,
                                      guests, bookings)
        verdict = GuestCountCheck().check(request) or ApprovalCheck().check(request)
        return {"requested": False, "available": verdict is None,
                "reason": verdict.reason if verdict else None,
                "nights": None, "total_cost": None,
                "failure": verdict.failure if verdict else None}

    request = AvailabilityRequest(listing, check_in, check_out, nights, check_in_time,
                                  check_out_time, guests, bookings)
    verdict = _CHAIN.handle(request)
    total = str(price_for(listing, check_in, check_out)) if guests >= 1 else None
    return {"requested": True, "available": verdict is None,
            "reason": verdict.reason if verdict else None, "nights": nights,
            "total_cost": total, "failure": verdict.failure if verdict else None}
