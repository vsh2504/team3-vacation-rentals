"""Pattern: Decorator.

A booking total is a :class:`PriceQuote`. ``NightlyRate`` is the concrete
component (nights x rate); ``FlatFee`` and ``PercentAdjustment`` wrap any
quote and add behaviour while keeping the same interface, so fees and
discounts stack without modifying existing code (Open/Closed).
"""
from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

from .domain import Listing, price_for


@runtime_checkable
class PriceQuote(Protocol):
    def quote(self, listing: Listing, check_in: date, check_out: date) -> Decimal: ...


class NightlyRate:
    def quote(self, listing, check_in, check_out) -> Decimal:
        return price_for(listing, check_in, check_out)


class _QuoteDecorator:
    def __init__(self, inner: PriceQuote) -> None:
        self._inner = inner


class FlatFee(_QuoteDecorator):
    def __init__(self, inner: PriceQuote, amount) -> None:
        super().__init__(inner)
        self._amount = Decimal(str(amount))

    def quote(self, listing, check_in, check_out) -> Decimal:
        return self._inner.quote(listing, check_in, check_out) + self._amount


class PercentAdjustment(_QuoteDecorator):
    """Positive = surcharge, negative = discount."""

    def __init__(self, inner: PriceQuote, percent) -> None:
        super().__init__(inner)
        self._factor = 1 + Decimal(str(percent)) / 100

    def quote(self, listing, check_in, check_out) -> Decimal:
        return self._inner.quote(listing, check_in, check_out) * self._factor


DEFAULT_QUOTE = NightlyRate()
