"""Price-tier labelling as an interchangeable Strategy.

``ListingService`` depends on the :class:`PriceTierStrategy` protocol, so a
different tiering policy (for example a per-market one) can be injected
without touching the service (Open/Closed, Dependency Inversion).

Pattern: Strategy.
"""
from decimal import Decimal, InvalidOperation
from typing import Protocol, runtime_checkable


@runtime_checkable
class PriceTierStrategy(Protocol):
    def tier(self, price: Decimal | float | str | None) -> str: ...


class ThresholdPriceTier:
    """Label a nightly price by the first ``(upper_bound, label)`` it fits under."""

    def __init__(self, thresholds: tuple[tuple[Decimal, str], ...], top_label: str):
        self._thresholds = thresholds
        self._top_label = top_label

    def tier(self, price) -> str:
        try:
            value = Decimal(str(price))
        except (InvalidOperation, ValueError):
            value = Decimal(0)  # unparsable prices fall into the cheapest tier
        for upper_bound, label in self._thresholds:
            if value <= upper_bound:
                return label
        return self._top_label


DEFAULT_PRICE_TIER = ThresholdPriceTier(
    ((Decimal("100"), "$"), (Decimal("200"), "$$")), top_label="$$$")
