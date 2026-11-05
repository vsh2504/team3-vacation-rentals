"""Chain of Responsibility: listing validation rules and availability checks."""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.domain import Booking, Listing, ListingStatus
from app.services.availability import (AvailabilityRequest, ApprovalCheck,
                                       GuestCountCheck, OperatingHoursCheck,
                                       OverlapCheck, StayRulesCheck,
                                       build_availability_chain)
from app.services.listing_validation import (default_rules, ListingRule,
                                             ListingValidator, ValidationErrors,
                                             build_chain)

GOOD = dict(title="  Nice  loft ", description="d", address="1 Main St", city="San Jose",
            state="California", zip="95110", lat=37.3, lng=-121.9, price_per_night=120,
            max_guests=4, bedrooms=1, bathrooms=1, amenities=[" wifi ", ""],
            photos=["/uploads/a.jpg"], videos=["https://x/y.mp4"])


def run(rule, payload):
    errors = ValidationErrors()
    rule.handle(payload, errors)
    return errors


# -- error collector ---------------------------------------------------------
def test_validation_errors_collects_and_raises_first_named_field():
    errors = ValidationErrors()
    errors.raise_if_any()                       # nothing to raise
    errors.add("", "general")
    errors.add("zip", "bad zip")
    with pytest.raises(ApiError) as e:
        errors.raise_if_any()
    assert (e.value.code, e.value.field, e.value.message) == (
        "VALIDATION_ERROR", "zip", "general; bad zip")


# -- chain mechanics ---------------------------------------------------------
class Recorder(ListingRule):
    def __init__(self, name, log): super().__init__(); self.name, self.log = name, log
    def apply(self, payload, errors): self.log.append(self.name)


def test_build_chain_runs_every_rule_in_order():
    log = []
    head = build_chain([Recorder("a", log), Recorder("b", log), Recorder("c", log)])
    head.handle({}, ValidationErrors())
    assert log == ["a", "b", "c"]


def test_validator_is_open_for_extension_without_modification():
    class NoShouting(ListingRule):
        def apply(self, payload, errors):
            if payload.get("title", "").isupper():
                errors.add("title", "title must not be all caps")
    validator = ListingValidator(rules=[*default_rules(), NoShouting()])
    with pytest.raises(ApiError) as e:
        validator.validate({**GOOD, "title": "LOUD"})
    assert e.value.field == "title" and "all caps" in e.value.message
    assert ListingValidator().validate(GOOD)["title"] == "Nice loft"


# -- individual rules --------------------------------------------------------
def test_validator_normalizes_a_good_payload():
    out = ListingValidator().validate({**GOOD, "unknown": "dropped", "id": 5, "status": "APPROVED"})
    assert out["title"] == "Nice loft" and out["state"] == "CA"
    assert out["amenities"] == ["wifi"] and out["price_per_night"] == Decimal("120")
    assert "unknown" not in out and "id" not in out and "status" not in out


@pytest.mark.parametrize("override,field", [
    (dict(title=""), "title"), (dict(available_times=" "), "available_times"),
    (dict(state="Atlantis"), "state"), (dict(zip="abc"), "zip"),
    (dict(price_per_night="x"), "price_per_night"), (dict(price_per_night=0), "price_per_night"),
    (dict(max_guests="x"), "max_guests"), (dict(max_guests=0), "max_guests"),
    (dict(bedrooms=-1), "bedrooms"),
    (dict(lat="north"), "lat"), (dict(lat=91), "lat"), (dict(lng=None), "lat"),
    (dict(operating_start_time=time(8), operating_end_time=time(8)), "operating_end_time"),
    (dict(operating_start_time=time(16), operating_end_time=time(20)), "check_in_time"),
    (dict(operating_start_time=time(12), operating_end_time=time(20), check_in_time=time(13),
          check_out_time=time(8)), "check_out_time"),
    (dict(amenities="wifi"), "amenities"), (dict(photos="x"), "photos"),
    (dict(videos=["ftp://x"]), "videos"),
    (dict(host_contact_email="nope"), "host_contact_email"),
    (dict(host_contact_phone="12"), "host_contact_phone"),
])
def test_default_rules_reject(override, field):
    with pytest.raises(ApiError) as e:
        ListingValidator().validate({**GOOD, **override})
    assert e.value.code == "VALIDATION_ERROR" and e.value.field == field


def test_missing_values_report_every_problem_in_rule_order():
    with pytest.raises(ApiError) as e:
        ListingValidator().validate(None)
    assert e.value.message.startswith("title is required; description is required")
    only = {k: v for k, v in GOOD.items() if k not in ("max_guests", "price_per_night")}
    with pytest.raises(ApiError) as e:
        ListingValidator().validate(only)
    assert e.value.message.index("price_per_night") < e.value.message.index("max_guests")


# -- availability chain ------------------------------------------------------
D = date(2027, 5, 1)


def listing(**kw):
    base = dict(id=1, host_id=1, title="L", description="d", address="a", city="c", state="CA",
                zip="9", lat=1.0, lng=2.0, price_per_night=Decimal("100"), max_guests=2,
                bedrooms=1, bathrooms=1, status=ListingStatus.APPROVED)
    base.update(kw)
    return Listing(**base)


def request(li=None, **kw):
    base = dict(listing=li or listing(), check_in=D, check_out=D + timedelta(2), nights=2,
                check_in_time=None, check_out_time=None, guests=1, bookings=[])
    base.update(kw)
    return AvailabilityRequest(**base)


@pytest.mark.parametrize("handler,req,failure", [
    (StayRulesCheck(), request(guests=5), "validation"),
    (ApprovalCheck(), request(listing(status=ListingStatus.PENDING_APPROVAL)), "approval"),
    (OperatingHoursCheck(), request(listing(operating_start_time=time(10), operating_end_time=time(18)),
                                    check_in_time=time(8), check_out_time=time(12)), "time"),
    (OverlapCheck(), request(bookings=[Booking(1, 1, 3, D, D + timedelta(2), 1, Decimal("200"))]),
     "overlap"),
])
def test_each_check_reports_its_failure_kind(handler, req, failure):
    verdict = handler.check(req)
    assert verdict is not None and verdict.failure == failure and verdict.reason


def test_each_check_passes_a_clean_request():
    for handler in (StayRulesCheck(), ApprovalCheck(), OperatingHoursCheck(), OverlapCheck()):
        assert handler.check(request()) is None


def test_chain_returns_first_failure_or_none():
    chain = build_availability_chain()
    assert chain.handle(request()) is None
    # invalid guests beat approval problems: the stay-rules check comes first
    both = request(listing(status=ListingStatus.PENDING_APPROVAL, max_guests=1), guests=5)
    assert chain.handle(both).failure == "validation"
    assert chain.handle(request(listing(status=ListingStatus.REJECTED))).failure == "approval"


def test_guest_count_check_is_standalone():
    assert GuestCountCheck().check(request(guests=0)).failure == "validation"
    assert GuestCountCheck().check(request(guests=1)) is None


def test_hours_check_distinguishes_check_in_from_check_out():
    li = listing(operating_start_time=time(10), operating_end_time=time(18))
    early = OperatingHoursCheck().check(request(li, check_in_time=time(8), check_out_time=time(12)))
    late = OperatingHoursCheck().check(request(li, check_in_time=time(12), check_out_time=time(20)))
    assert "check-in" in early.reason and "check-out" in late.reason
