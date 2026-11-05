"""Resolve and validate a requested stay window (dates, duration, times).

Pattern: Chain of Responsibility - ordered rules over a shared draft."""
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import NamedTuple

from ..core.errors import ApiError
from .chain import ChainLink

MAX_NIGHTS = 14


class StayWindow(NamedTuple):
    check_in: date | None
    check_out: date | None
    nights: int | None


def _invalid(message: str, field: str) -> ApiError:
    return ApiError("VALIDATION_ERROR", message, field)


def _parse_nights(nights) -> int:
    try:
        nights = int(nights)
    except (TypeError, ValueError):
        raise _invalid("duration must be a whole number of nights", "nights") from None
    if nights < 1:
        raise _invalid("duration must be at least 1 night", "nights")
    if nights > MAX_NIGHTS:
        raise _invalid("Stay cannot exceed 14 nights", "nights")
    return nights


@dataclass
class StayDraft:
    check_in: date | None
    check_out: date | None
    nights: int | None
    check_in_time: time | None
    check_out_time: time | None
    stay_nights: int | None = None


class StayRule(ChainLink):
    """Chain handler over a :class:`StayDraft`; raises ``ApiError`` on the first problem."""

    def apply(self, draft: StayDraft) -> None:
        raise NotImplementedError  # pragma: no cover - abstract

    def handle(self, draft: StayDraft) -> None:
        for rule in self:
            rule.apply(draft)


class DurationRule(StayRule):
    def apply(self, draft):
        if draft.nights is None:
            return
        draft.nights = _parse_nights(draft.nights)
        if draft.check_in is None:
            raise _invalid("check_in is required when a duration is provided", "check_in")
        derived_out = draft.check_in + timedelta(days=draft.nights)
        if draft.check_out is None:
            draft.check_out = derived_out
        elif draft.check_out != derived_out:
            raise _invalid("check_out must equal check_in plus the requested duration",
                           "check_out")


class PairRule(StayRule):
    def apply(self, draft):
        if (draft.check_in is None) != (draft.check_out is None):
            raise _invalid("check_in and check_out must be provided together", "check_out")


class RangeRule(StayRule):
    def apply(self, draft):
        # Both dates are present from here on (a duration requires check_in and
        # derives check_out, and the pair rule rejects a lone date).
        draft.stay_nights = (draft.check_out - draft.check_in).days
        if draft.stay_nights <= 0:
            raise _invalid("check_out must be after check_in", "check_out")
        if draft.stay_nights > MAX_NIGHTS:
            raise _invalid("Stay cannot exceed 14 nights", "check_out")


class TimesRule(StayRule):
    def apply(self, draft):
        if (draft.check_in_time is None) != (draft.check_out_time is None):
            raise _invalid("check_in_time and check_out_time must be provided together",
                           "check_in_time")


def _build_rules() -> StayRule:
    head = DurationRule()
    head.then(PairRule()).then(RangeRule()).then(TimesRule())
    return head


_RULES = _build_rules()


def resolve_stay_window(check_in: date | None, check_out: date | None,
                        nights: int | None, check_in_time: time | None,
                        check_out_time: time | None) -> StayWindow:
    if check_in is None and check_out is None and nights is None:
        if check_in_time is not None or check_out_time is not None:
            raise _invalid("dates are required when booking times are provided", "check_in")
        return StayWindow(None, None, None)
    draft = StayDraft(check_in, check_out, nights, check_in_time, check_out_time)
    _RULES.handle(draft)
    return StayWindow(draft.check_in, draft.check_out, draft.stay_nights)
