"""Unit tests for the single-responsibility modules split out of services.py
(checkpoint 1): navigation, pricing Strategy, completeness, stay window."""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.domain import Listing, User, UserRole
from app.services.completeness import listing_completeness
from app.services.navigation import navigation_for, user_public
from app.services.pricing import PriceTierStrategy, ThresholdPriceTier, DEFAULT_PRICE_TIER
from app.services.stay_window import StayWindow, resolve_stay_window

D = date(2027, 5, 1)


# -- navigation ------------------------------------------------------------
def test_navigation_is_role_specific_and_defensive():
    assert [i["key"] for i in navigation_for("HOST")] == ["search", "listings", "bookings", "analytics"]
    assert [i["key"] for i in navigation_for(UserRole.CUSTOMER)] == ["search", "bookings"]
    admin = navigation_for(UserRole.ADMIN)
    assert admin[1] == {"key": "moderation", "label": "Approvals queue", "path": "/admin"}
    admin[0]["label"] = "mutated"
    assert navigation_for(UserRole.ADMIN)[0]["label"] == "Search stays"


def test_user_public_never_exposes_password_hash():
    out = user_public(User(1, "a@b.co", "SECRET", "A", UserRole.HOST))
    assert "password_hash" not in out and "SECRET" not in str(out)
    assert out["role"] == "HOST" and out["navigation"][0]["key"] == "search"


# -- pricing Strategy -------------------------------------------------------
@pytest.mark.parametrize("price,tier", [
    ("50", "$"), (100, "$"), (150.5, "$$"), (200, "$$"), (201, "$$$"), ("junk", "$"), (None, "$")])
def test_default_price_tier(price, tier):
    assert DEFAULT_PRICE_TIER.tier(price) == tier


def test_price_tier_strategies_are_interchangeable():
    luxury = ThresholdPriceTier(((Decimal("500"), "budget"),), top_label="luxury")
    assert isinstance(luxury, PriceTierStrategy)
    assert luxury.tier(400) == "budget" and luxury.tier(501) == "luxury"
    assert luxury.tier("junk") == "budget"       # unparsable -> cheapest tier


# -- completeness ------------------------------------------------------------
def test_listing_completeness_complete_and_bare():
    full = Listing(1, 1, "t", "d", "a", "c", "CA", "9", 1.0, 2.0, Decimal("1"), 1, 1, 1,
                   host_contact_name="n", amenities=["w"], photos=["/p"],
                   operating_start_time=time(8), operating_end_time=time(20))
    out = listing_completeness(full)
    assert out["complete"] and out["score"] == 100 and out["has_photos"] and out["missing"] == []
    bare = Listing(1, 1, "", "", "", "", "", "", None, None, Decimal("0"), 0, 0, 0,
                   available_times="")
    out = listing_completeness(bare)
    assert not out["complete"] and "media" in out["missing"] and out["score"] < 50
    assert out["photo_count"] == 0 and not out["has_videos"]


# -- stay window ---------------------------------------------------------------
def resolve(**kw):
    base = dict(check_in=None, check_out=None, nights=None, check_in_time=None, check_out_time=None)
    return resolve_stay_window(**{**base, **kw})


def test_stay_window_success_cases():
    assert resolve() == StayWindow(None, None, None)
    assert resolve(check_in=D, nights="3") == StayWindow(D, D + timedelta(3), 3)
    assert resolve(check_in=D, check_out=D + timedelta(2)).nights == 2
    check_in, check_out, nights = resolve(check_in=D, check_out=D + timedelta(2), nights=2)
    assert (check_in, check_out, nights) == (D, D + timedelta(2), 2)


@pytest.mark.parametrize("kwargs,field,message", [
    (dict(check_in_time=time(9), check_out_time=time(10)), "check_in", "dates are required"),
    (dict(nights="abc"), "nights", "whole number"),
    (dict(nights=0), "nights", "at least 1"),
    (dict(nights=15, check_in=D), "nights", "exceed 14"),
    (dict(nights=2), "check_in", "required when a duration"),
    (dict(nights=2, check_in=D, check_out=D + timedelta(3)), "check_out", "plus the requested"),
    (dict(check_in=D), "check_out", "provided together"),
    (dict(check_out=D), "check_out", "provided together"),
    (dict(check_in=D, check_out=D), "check_out", "after check_in"),
    (dict(check_in=D, check_out=D + timedelta(15)), "check_out", "exceed 14"),
    (dict(check_in=D, check_out=D + timedelta(2), check_in_time=time(9)), "check_in_time", "together"),
])
def test_stay_window_errors(kwargs, field, message):
    with pytest.raises(ApiError) as e:
        resolve(**kwargs)
    assert e.value.code == "VALIDATION_ERROR" and e.value.field == field
    assert message in e.value.message
