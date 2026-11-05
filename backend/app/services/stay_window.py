"""Resolve and validate a requested stay window (dates, duration, times)."""
from datetime import date, time, timedelta
from typing import NamedTuple

from ..core.errors import ApiError

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


def resolve_stay_window(check_in: date | None, check_out: date | None,
                        nights: int | None, check_in_time: time | None,
                        check_out_time: time | None) -> StayWindow:
    if check_in is None and check_out is None and nights is None:
        if check_in_time is not None or check_out_time is not None:
            raise _invalid("dates are required when booking times are provided", "check_in")
        return StayWindow(None, None, None)

    if nights is not None:
        nights = _parse_nights(nights)
        if check_in is None:
            raise _invalid("check_in is required when a duration is provided", "check_in")
        derived_out = check_in + timedelta(days=nights)
        if check_out is None:
            check_out = derived_out
        elif check_out != derived_out:
            raise _invalid("check_out must equal check_in plus the requested duration",
                           "check_out")

    if (check_in is None) != (check_out is None):
        raise _invalid("check_in and check_out must be provided together", "check_out")

    # Both dates are present from here on (a duration requires check_in and
    # derives check_out, and the pair check above rejects a lone date).
    stay_nights = (check_out - check_in).days
    if stay_nights <= 0:
        raise _invalid("check_out must be after check_in", "check_out")
    if stay_nights > MAX_NIGHTS:
        raise _invalid("Stay cannot exceed 14 nights", "check_out")

    if (check_in_time is None) != (check_out_time is None):
        raise _invalid("check_in_time and check_out_time must be provided together",
                       "check_in_time")
    return StayWindow(check_in, check_out, stay_nights)
