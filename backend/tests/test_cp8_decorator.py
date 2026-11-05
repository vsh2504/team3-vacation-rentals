"""CP8 - Decorator: stackable price quotes and a retrying geocoding provider."""
from datetime import date
from decimal import Decimal

import pytest

from app.domain import Listing, ListingStatus
from app.factories import BookingFactory
from app.geocoding import (GeocodeNotFound, GeocodeResult, GeocodingUnavailable,
                           NominatimProvider, RetryingProvider, get_provider)
from app.price_quotes import (FlatFee, NightlyRate, PercentAdjustment, PriceQuote,
                              DEFAULT_QUOTE)

IN, OUT = date(2027, 5, 1), date(2027, 5, 4)  # 3 nights


def listing(price=100):
    return Listing(id=1, host_id=1, title="T", description="d", address="a", city="c",
                   state="s", zip="95110", lat=1.0, lng=1.0, price_per_night=price,
                   max_guests=2, bedrooms=1, bathrooms=1, status=ListingStatus.APPROVED)


def test_base_quote_is_nights_times_rate():
    assert NightlyRate().quote(listing(), IN, OUT) == Decimal("300")


def test_decorators_stack_in_order():
    quote = PercentAdjustment(FlatFee(NightlyRate(), Decimal("50")), Decimal("10"))
    # (300 + 50) * 1.10
    assert quote.quote(listing(), IN, OUT) == Decimal("385.00")


def test_discount_is_a_negative_percentage():
    assert PercentAdjustment(NightlyRate(), Decimal("-10")).quote(listing(), IN, OUT) == Decimal("270.00")


def test_decorators_satisfy_the_quote_protocol():
    assert isinstance(FlatFee(NightlyRate(), 1), PriceQuote) and isinstance(DEFAULT_QUOTE, PriceQuote)


def test_factory_uses_injected_quote_and_defaults_to_plain_price():
    plain = BookingFactory.create([], listing(), 5, IN, OUT, 2, IN)
    fee = BookingFactory.create([], listing(), 5, IN, OUT, 2, IN,
                                quote=FlatFee(NightlyRate(), Decimal("25")))
    assert plain.total_price == Decimal("300") and fee.total_price == Decimal("325")


# ---- retrying provider ------------------------------------------------------
class Flaky:
    name = "flaky"

    def __init__(self, failures, error=GeocodingUnavailable):
        self.failures, self.calls, self.error = failures, 0, error

    def geocode(self, address):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error("down")
        return GeocodeResult(query=address, display_name="x", address="", city="", state="",
                             zip="", country="", lat=1.0, lng=2.0, provider="flaky")


def test_retries_transient_failures_then_succeeds():
    inner = Flaky(2)
    result = RetryingProvider(inner, attempts=3).geocode("a")
    assert result.lat == 1.0 and inner.calls == 3


def test_gives_up_after_the_last_attempt():
    inner = Flaky(5)
    with pytest.raises(GeocodingUnavailable):
        RetryingProvider(inner, attempts=3).geocode("a")
    assert inner.calls == 3


def test_not_found_is_never_retried():
    inner = Flaky(5, error=GeocodeNotFound)
    with pytest.raises(GeocodeNotFound):
        RetryingProvider(inner, attempts=3).geocode("a")
    assert inner.calls == 1


def test_decorator_keeps_the_wrapped_name():
    assert RetryingProvider(Flaky(0)).name == "flaky"


def test_get_provider_wraps_only_when_retries_configured(monkeypatch):
    monkeypatch.delenv("STAYNEST_GEOCODING_RETRIES", raising=False)
    assert isinstance(get_provider("nominatim"), NominatimProvider)
    monkeypatch.setenv("STAYNEST_GEOCODING_RETRIES", "3")
    wrapped = get_provider("nominatim")
    assert isinstance(wrapped, RetryingProvider) and wrapped.attempts == 3
    monkeypatch.setenv("STAYNEST_GEOCODING_RETRIES", "nope")
    assert isinstance(get_provider("nominatim"), NominatimProvider)
